import argparse
import os
import sys
from pathlib import Path

import django
from django.conf import settings
from django.test.utils import get_runner

RUNTESTS_DIR = Path(__file__).resolve().parent
SKIP_DIRS = ["unsupported"]


def get_test_modules():
    """
    Scan the tests directory and yield the names of all test modules.
    """
    with os.scandir(RUNTESTS_DIR) as entries:
        for f in entries:
            if (
                    "." in f.name
                    or Path(f.name).name in SKIP_DIRS
                    or f.is_file()
                    or not (Path(f.path) / "__init__.py").exists()
            ):
                continue
            test_module = f.name
            yield test_module


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the Django test suite for YDB backend."
    )
    parser.add_argument(
        "modules",
        nargs="*",
        metavar="module",
        help='Optional path(s) to test modules; e.g. "tests.test_basic".',
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        default=1,
        type=int,
        choices=[0, 1, 2, 3],
        help="Verbosity level; 0=minimal output, 1=normal output, 2=all output",
    )
    parser.add_argument(
        "--noinput",
        action="store_false",
        dest="interactive",
        help="Tells Django to NOT prompt the user for input of any kind.",
    )
    parser.add_argument(
        "--failfast",
        action="store_true",
        help="Tells Django to stop running the test suite after the first failed test.",
    )
    parser.add_argument(
        "--keepdb",
        action="store_true",
        help="Tells Django to preserve the test database between runs.",
    )
    parser.add_argument(
        "--debug-sql",
        action="store_true",
        help="Turn on the SQL query logger within tests.",
    )

    options = parser.parse_args()
    options.modules = [os.path.normpath(labels) for labels in options.modules]

    os.environ["DJANGO_SETTINGS_MODULE"] = "settings"
    modules = list(get_test_modules())
    settings.INSTALLED_APPS.extend(modules)
    django.setup()

    TestRunner = get_runner(settings)
    test_runner = TestRunner(
        verbosity=options.verbosity,
        noinput=options.interactive,
        failfast=options.failfast,
        keepdb=options.keepdb,
        debug_sql=options.debug_sql,
    )
    failures = test_runner.run_tests(options.modules or modules)
    sys.exit(bool(failures))
