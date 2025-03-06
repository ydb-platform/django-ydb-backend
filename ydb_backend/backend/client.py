from django.db.backends.base.client import BaseDatabaseClient


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
