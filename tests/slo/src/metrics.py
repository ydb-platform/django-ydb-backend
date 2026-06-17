"""OTLP metrics for the SLO workload.

Implements the metric contract expected by ydb-slo-action: per-operation
counters and pre-computed latency-percentile gauges, all carrying the ``ref``
label (current vs baseline) plus ``operation_type`` and ``operation_status``.

Latency percentiles (p50/p95/p99) are computed client-side per push window with
an HdrHistogram and emitted as gauges — the action does not derive percentiles
from histograms. Instrument names use dots; the Prometheus OTLP receiver maps
them to ``sdk_operations_total`` / ``sdk_operation_latency_p50_seconds`` / etc.,
which is what deploy/metrics.yaml queries.
"""

import logging
import threading
import time
from abc import ABC
from abc import abstractmethod
from contextlib import contextmanager
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version
from os import environ

OP_TYPE_READ = "read"
OP_TYPE_WRITE = "write"
OP_STATUS_SUCCESS = "success"
OP_STATUS_ERROR = "error"

REF = environ.get("WORKLOAD_REF") or environ.get("REF") or "current"
WORKLOAD = environ.get("WORKLOAD_NAME") or environ.get("WORKLOAD") or "django-kv"

logger = logging.getLogger(__name__)


def _backend_version():
    try:
        return version("django-ydb-backend")
    except PackageNotFoundError:
        return "0.0.0"


class BaseMetrics(ABC):
    @abstractmethod
    def start(self, op_type):
        ...

    @abstractmethod
    def stop(self, op_type, start_time, attempts=1, error=None):
        ...

    @abstractmethod
    def push(self):
        ...

    def shutdown(self):
        pass

    @contextmanager
    def measure(self, op_type):
        start_ts = self.start(op_type)
        error = None
        attempts = 1
        try:
            yield
        except BaseException as err:  # noqa: BLE001 - recorded then re-raised
            error = err
            raise
        finally:
            self.stop(op_type, start_ts, attempts=attempts, error=error)


class DummyMetrics(BaseMetrics):
    """No-op exporter used when no OTLP endpoint is configured."""

    def start(self, op_type):
        return time.time()

    def stop(self, op_type, start_time, attempts=1, error=None):
        return None

    def push(self):
        return None


class OtlpMetrics(BaseMetrics):
    _HDR_MIN_US = 1
    _HDR_MAX_US = 60_000_000  # 60s
    _HDR_SIG_FIGS = 3
    _PERCENTILES = (("p50", 50.0), ("p95", 95.0), ("p99", 99.0))

    def __init__(self, otlp_metrics_endpoint):
        from hdrh.histogram import HdrHistogram
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource

        self._HdrHistogram = HdrHistogram

        resource = Resource.create(
            {
                "service.name": f"workload-{WORKLOAD}",
                "service.instance.id": environ.get(
                    "SLO_INSTANCE_ID", f"{REF}-{WORKLOAD}"
                ),
                "ref": REF,
                "sdk": "django-ydb-backend",
                "sdk_version": _backend_version(),
                "workload": WORKLOAD,
            }
        )

        exporter = OTLPMetricExporter(endpoint=otlp_metrics_endpoint)
        reader = PeriodicExportingMetricReader(exporter)
        self._provider = MeterProvider(resource=resource, metric_readers=[reader])
        self._meter = self._provider.get_meter("ydb-slo")

        self._operations_total = self._meter.create_counter(
            name="sdk.operations.total",
            description="Total number of logical operations attempted.",
        )
        self._operations_success_total = self._meter.create_counter(
            name="sdk.operations.success.total",
            description="Total number of successful operations.",
        )
        self._operations_failure_total = self._meter.create_counter(
            name="sdk.operations.failure.total",
            description="Total number of failed operations.",
        )
        self._retry_attempts_total = self._meter.create_counter(
            name="sdk.retry.attempts.total",
            description="Total number of attempts including the first one.",
        )
        self._errors = self._meter.create_counter(
            name="sdk.errors.total",
            description="Total number of errors by error type.",
        )
        self._pending = self._meter.create_up_down_counter(
            name="sdk.pending.operations",
            description="Number of in-flight operations.",
        )
        self._latency_gauges = {
            name: self._meter.create_gauge(
                name=f"sdk.operation.latency.{name}.seconds",
                unit="s",
                description=f"Operation latency {name} over the last push window.",
            )
            for name, _ in self._PERCENTILES
        }

        self._lock = threading.Lock()
        self._hdr = {}

    def _get_hdr(self, op_type, op_status):
        key = (op_type, op_status)
        hist = self._hdr.get(key)
        if hist is None:
            hist = self._HdrHistogram(
                self._HDR_MIN_US, self._HDR_MAX_US, self._HDR_SIG_FIGS
            )
            self._hdr[key] = hist
        return hist

    def start(self, op_type):
        self._pending.add(1, attributes={"ref": REF, "operation_type": op_type})
        return time.time()

    def stop(self, op_type, start_time, attempts=1, error=None):
        duration = time.time() - start_time
        duration_us = min(
            max(int(duration * 1_000_000), self._HDR_MIN_US), self._HDR_MAX_US
        )

        op_status = OP_STATUS_SUCCESS if error is None else OP_STATUS_ERROR
        base_attrs = {"ref": REF, "operation_type": op_type}
        op_attrs = {**base_attrs, "operation_status": op_status}

        self._retry_attempts_total.add(int(attempts), attributes=base_attrs)
        self._pending.add(-1, attributes=base_attrs)
        self._operations_total.add(1, attributes=op_attrs)

        if error is not None:
            self._errors.add(
                1, attributes={**base_attrs, "error_type": type(error).__name__}
            )
            self._operations_failure_total.add(1, attributes=base_attrs)
        else:
            self._operations_success_total.add(1, attributes=base_attrs)

        with self._lock:
            self._get_hdr(op_type, op_status).record_value(duration_us)

    def push(self):
        with self._lock:
            for (op_type, op_status), hist in self._hdr.items():
                if hist.get_total_count() == 0:
                    continue
                attrs = {
                    "ref": REF,
                    "operation_type": op_type,
                    "operation_status": op_status,
                }
                for name, percentile in self._PERCENTILES:
                    value_s = hist.get_value_at_percentile(percentile) / 1_000_000
                    self._latency_gauges[name].set(value_s, attributes=attrs)
            for hist in self._hdr.values():
                hist.reset()
        self._provider.force_flush()

    def shutdown(self):
        try:
            self.push()
        finally:
            self._provider.shutdown()


def _resolve_metrics_endpoint(cli_endpoint):
    """Resolve the OTLP metrics endpoint from env vars, then the CLI flag.

    Order: ``OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`` (as-is), then
    ``OTEL_EXPORTER_OTLP_ENDPOINT`` (with ``/v1/metrics`` appended), then the
    explicit ``--otlp-endpoint`` value.
    """
    metrics_env = environ.get("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", "").strip()
    if metrics_env:
        return metrics_env

    base_env = environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if base_env:
        base = base_env.rstrip("/")
        if base.endswith("/v1/metrics"):
            return base
        return f"{base}/v1/metrics"

    return (cli_endpoint or "").strip()


def create_metrics(otlp_endpoint):
    endpoint = _resolve_metrics_endpoint(otlp_endpoint)
    if not endpoint:
        logger.info("Metrics disabled (no OTLP endpoint); using DummyMetrics")
        return DummyMetrics()

    logger.info("Creating OTLP metrics exporter to: %s", endpoint)
    try:
        return OtlpMetrics(endpoint)
    except Exception:
        logger.exception("Failed to init OTLP exporter; falling back to DummyMetrics")
        return DummyMetrics()
