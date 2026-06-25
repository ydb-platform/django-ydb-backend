Configurations
===

To use the YDB backend you only need to adjust a few of Django's built-in
database settings. The single YDB-specific knob is the transaction isolation
level, set through `OPTIONS` (see below).

### DATABASES

- NAME (required): traditional Django databases use this as the database name.
- ENGINE (required): required, set to `ydb_backend.backend`.
- HOST (required): the hostname or IP address of the YDB server (e.g., "localhost").
- PORT (required): The gRPC port YDB is running on (default is 2136).
- DATABASE (required): The full path to your YDB database (e.g., "/local" for local testing or "/my_production_db").

 ```python
 DATABASES = {
     "default": {
         "NAME": "ydb_db",
         "ENGINE": "ydb_backend.backend",
         "HOST": "localhost",
         "PORT": "2136",
         "DATABASE": "/local",
     }
 }
 ```

### OPTIONS

`OPTIONS` is a dict forwarded to the YDB driver. The backend reads one key,
`isolation_level`, and passes the rest through to `ydb_dbapi.connect`.

- `isolation_level` (optional): the transaction mode applied to every
  transaction on the connection. Given as a case-insensitive string; defaults
  to `"serializable"`. An unknown value raises `ImproperlyConfigured`.

| Value | Reads | Writes |
|---|---|---|
| `"serializable"` (default) — interactive, serializable read-write | yes | yes |
| `"snapshot readonly"` — consistent snapshot | yes | no |
| `"online readonly"` — latest committed data | yes | no |
| `"online readonly inconsistent"` — latest data, reads may be inconsistent | yes | no |
| `"stale readonly"` — possibly stale replica reads (cheapest) | yes | no |

YDB permits writes only under the serializable read-write mode, so the
read-only modes suit read-only workloads (reporting, analytics): any write —
`INSERT`/`UPDATE`/`DELETE`, and migrations — is rejected by YDB. Use a
read-only mode only on a connection you query for reads only, e.g. a second
`DATABASES` alias pointed at the same database. (The full set of accepted
values mirrors `ydb_dbapi`'s isolation levels.)

```python
DATABASES = {
    "default": {
        "ENGINE": "ydb_backend.backend",
        "HOST": "localhost",
        "PORT": "2136",
        "DATABASE": "/local",
        "OPTIONS": {"isolation_level": "serializable"},
    }
}
```

### Authentication Methods

#### Anonymous Credentials
To use `Anonymous Credentials`, you don't have to pass any additional params.

#### Static Credentials
To use `Static Credentials` you should provide `username`/`password`.

```python
DATABASES = {
    "default": {
        "ENGINE": "ydb_backend.backend",
        "CREDENTIALS": {
            "username": "..."
            "password": "..."
        }
    }
}
```

#### Access Token Credentials
To use `Access Token Credentials` you should provide `token`.

```python
DATABASES = {
    "default": {
        "ENGINE": "ydb_backend.backend",
        "CREDENTIALS": {
            "token": "..."
        },
    }
}
```

#### Service Account Credentials
To use `Service Account Credentials`, you should provide `service_account_json`.

```python
DATABASES = {
    "default": {
        "ENGINE": "ydb_backend.backend",
        "CREDENTIALS": {
            "service_account_json": {
                "id": "...",
                "service_account_id": "...",
                "created_at": "...",
                "key_algorithm": "...",
                "public_key": "...",
                "private_key": "..."
            }
        }
    }
}
```
