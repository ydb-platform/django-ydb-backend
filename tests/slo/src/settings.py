"""Minimal Django settings for the SLO workload.

The workload runs as a standalone container that the YDB SLO Action launches
alongside the YDB cluster. Connection details come from the environment the
action injects (``YDB_ENDPOINT`` / ``YDB_DATABASE``); for local runs they fall
back to the docker-compose YDB on ``localhost:2136`` / ``/local``.
"""

import os


def _endpoint_to_host_port(endpoint, default_host, default_port):
    """Split ``grpc://ydb:2136`` (or ``ydb:2136``) into ``(host, port)``."""
    if not endpoint:
        return default_host, default_port
    if "://" in endpoint:
        endpoint = endpoint.split("://", 1)[1]
    host, _, port = endpoint.partition(":")
    return host or default_host, port or default_port


_HOST, _PORT = _endpoint_to_host_port(
    os.environ.get("YDB_ENDPOINT", ""), "localhost", "2136"
)
_DATABASE = os.environ.get("YDB_DATABASE", "/local")

SECRET_KEY = "slo-workload-not-a-secret"  # noqa: S105
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = ["slo_app"]

DATABASES = {
    "default": {
        "ENGINE": "ydb_backend.backend",
        "NAME": "slo",
        "HOST": _HOST,
        "PORT": str(_PORT),
        "DATABASE": _DATABASE,
        "OPTIONS": {
            # Anonymous auth against the local/CI cluster, matching the
            # reference workloads in ydb-slo-action.
            "credentials": None,
            # Keep gRPC channels probed so a chaos-killed node is dropped
            # quickly instead of blocking a worker thread indefinitely.
            "driver_config_kwargs": {"grpc_keep_alive_timeout": 10000},
        },
    }
}
