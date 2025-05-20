Configurations
---

To set up your Django project to use a YDB backend, you only need to modify a few of Django's built-in configuration settings. This project does not require any additional custom configuration options.
(Summary: Just adjust standard Django settings for YDB—no extra YDB-specific configurations are needed.)

### DATABASES

- NAME (required): traditional Django databases use this as the database name.
- ENGINE (required): required, set to `ydb_backend.backend`.
- HOST (required): the hostname or IP address of the YDB server (e.g., "localhost").
- PORT (required): The gRPC port YDB is running on (default is 2136).
- DATABASE (required): The full path to your YDB database (e.g., "/local" for local testing or "/my_production_db").
- OPTIONS (optional): Additional settings for the YDB connection (e.g., credentials)

 ```python
 DATABASES = {
     "default": {
         "NAME": "ydb_db",
         "ENGINE": "ydb_backend.backend",
         "HOST": "localhost",
         "PORT": "2136",
         "DATABASE": "/local",
         "OPTIONS": {
             "credentials": None,
         },
     }
 }
 ```