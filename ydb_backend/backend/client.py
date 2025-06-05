from django.db.backends.base.client import BaseDatabaseClient


class DatabaseClient(BaseDatabaseClient):
    """Encapsulate backends-specific methods for opening a client shell."""

    # This should be a string representing the name of the executable
    # (e.g., "psql"). Subclasses must override this.
    executable_name = "ydb-client"

    @classmethod
    def settings_to_cmd_args_env(cls, settings_dict, parameters):
        args = [cls.executable_name]

        if "HOST" in settings_dict:
            args.extend(["--host", settings_dict["HOST"]])

        if "PORT" in settings_dict:
            args.extend(["--port", settings_dict["PORT"]])

        if "DATABASE" in settings_dict:
            args.extend(["--database", settings_dict["DATABASE"]])

        if "CREDENTIALS" in settings_dict:
            args.extend(["--credentials", settings_dict["CREDENTIALS"]])

        if parameters:
            args.extend(parameters)

        env = {}

        return args, env
