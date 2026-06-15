Operations
===

> See the [support contract](SUPPORT.md#upsert) for the UPSERT support level and
> the [ORM query features](SUPPORT.md#orm-query-features) matrix.

The operations implement the Django ORM query compilation system in a YDB-specific syntax, taking into account the features of this distributed database.

Features:
- All string types (CharField, TextField) are mapped to Utf 8.
- Datetime is used for the DateTimeField, and timestamps are processed via .timestamp().

## Query parameters

YDB requires typed query parameters. The backend types each parameter from the
Django expression that produced it — a lookup's value is typed from the
left-hand side's field, nested expressions and subqueries from their own
compilation — rather than by inspecting the generated SQL. A parameter whose
type cannot be resolved is typed from its Python value.

This covers joins, foreign-key filters, `__in`, `F()`, `Case`/`When`,
annotations, aggregate (`HAVING`) filters and non-correlated subqueries.

## Limitations

- **Correlated subqueries are not supported.** `Exists()` / `Subquery()` with
  `OuterRef` reference the outer table from inside the subquery, which YDB
  cannot resolve. Non-correlated subqueries work.

## UPSERT

UPSERT (UPDATE or INSERT) writes rows keyed on the **primary key**: a missing
row is inserted, and an existing row has the written columns overwritten while
its other columns are preserved. The backend uses YDB's native `UPSERT INTO`,
which runs as a **single atomic statement** — there is no read-modify-write
step, so concurrent upserts of the same key cannot create duplicates.

### Manager setup

UPSERT is provided by `YDBManager`. Set it as the model's manager:

```python
from django.db import models
from ydb_backend.models.manager import YDBManager


class NFTToken(models.Model):
    contract_address = models.CharField(max_length=42)
    token_id = models.CharField(max_length=78, primary_key=True)
    owner = models.CharField(max_length=42)
    metadata_url = models.CharField(max_length=256)
    last_price = models.FloatField()

    objects = YDBManager()
```

### upsert() and bulk_upsert()

Both accept a model instance or a dict (`bulk_upsert` accepts a list, and may
mix the two) and return the persisted instances:

```python
# Insert: the row does not exist yet.
NFTToken.objects.upsert({
    "contract_address": "0x1a2b3c4d5e",
    "token_id": "12345",
    "owner": "0xAlice123",
    "metadata_url": "ipfs://QmXyZ123",
    "last_price": 1.5,
})

# Update: same primary key — the listed columns are overwritten.
NFTToken.objects.upsert({
    "contract_address": "0x1a2b3c4d5e",
    "token_id": "12345",
    "owner": "0xBob456",
    "metadata_url": "ipfs://QmXyZ456",
    "last_price": 2.5,
})

# Bulk: one statement upserts every row.
tokens = NFTToken.objects.bulk_upsert([
    {"contract_address": "0x11", "token_id": "100", "owner": "0xA",
     "metadata_url": "ipfs://a", "last_price": 10.0},
    NFTToken(contract_address="0x22", token_id="200", owner="0xB",
             metadata_url="ipfs://b", last_price=20.0),
])
```

### Conflict target

UPSERT is always keyed on the primary key. `conflict_target` may be omitted (it
defaults to the primary key) or set to the primary key explicitly; any other
target raises `NotSupportedError`, because YDB has no unique constraints to
match on:

```python
NFTToken.objects.upsert(data, conflict_target="token_id")  # ok — the PK
NFTToken.objects.upsert(data, conflict_target="owner")     # NotSupportedError
```

### Writing a subset of columns

`update_fields` restricts which columns are written; columns left out are
preserved on existing rows. YDB's `UPSERT INTO` requires **every NOT NULL
column** to be present, so `update_fields` may only drop nullable columns —
omitting a NOT NULL column raises `NotSupportedError`.

```python
class InventoryItem(models.Model):
    sku = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)          # NOT NULL
    reorder_level = models.IntegerField(null=True)   # nullable
    quantity = models.IntegerField()                 # NOT NULL

    objects = YDBManager()


# Writes name + quantity; the nullable reorder_level is left untouched.
InventoryItem.objects.upsert(
    {"sku": "A1", "name": "Widget", "quantity": 9},
    update_fields=["name", "quantity"],
)

# Raises NotSupportedError: omits the NOT NULL column `quantity`.
InventoryItem.objects.upsert(
    {"sku": "A1", "name": "Widget"},
    update_fields=["name"],
)
```

The behavior above is covered by `tests/compiler/test_upsert.py`.