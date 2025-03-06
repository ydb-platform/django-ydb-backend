import os
import signal
import subprocess
import re

from django.db.backends.base.client import BaseDatabaseClient


def is_safe_arguments(args):
    # A regular expression for searching for potentially dangerous characters
    dangerous_chars_pattern = re.compile(r'[;&|\`\'\"]')

    for arg in args:
        if dangerous_chars_pattern.search(arg):
            return False
    return True


class DatabaseClient(BaseDatabaseClient):
    executable_name = "ydb-client"

    @classmethod
    def settings_to_cmd_args_env(cls, settings_dict, parameters):
        args = [cls.executable_name]

        if "HOST" in settings_dict:
            args.extend(["--host", settings_dict["host"]])

        if "PORT" in settings_dict:
            args.extend(["--port", settings_dict["PORT"]])

        if "DATABASE" in settings_dict:
            args.extend(["--database", settings_dict["DATABASE"]])

        if "CREDENTIALS" in settings_dict:
            args.extend(["--credentials", settings_dict["CREDENTIALS"]])

        if parameters:
            args.extend(parameters)

        env = {
            "YDB_ROOT_CERTIFICATES": settings_dict.get("ROOT_CERTIFICATES", ""),
        }

        return args, env

    def runshell(self, parameters):
        args, env = self.settings_to_cmd_args_env(
            self.connection.settings_dict, parameters
        )
        env = {**os.environ, **env} if env else None

        sigint_handler = signal.getsignal(signal.SIGINT)
        try:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            # Checking the safety of arguments before executing
            if is_safe_arguments(args):
                subprocess.run(args, env=env, check=True)
            else:
                raise ValueError("Unsafe arguments detected")
        finally:
            signal.signal(signal.SIGINT, sigint_handler)
