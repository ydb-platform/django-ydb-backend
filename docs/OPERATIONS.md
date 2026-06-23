Operations
===

The backend compiles the Django ORM into YDB's YQL dialect, adapting to the
features of a distributed database. This page covers query support, query
parameters, and UPSERT.

## ORM query features at a glance

| Feature | Status | Notes |
|---------|:------:|-------|
| CRUD (`create` / `get` / `filter` / `update` / `delete`) | ✅ | |
| Most field lookups | ✅ | `exact`, `in`, ranges, `icontains`, date extraction (`week_day` / `week` / `quarter` / …), and more. |
| Backslash / `%` / `_` escaping in pattern and exact lookups | ✅ | Escaped correctly. `Substr()` on a text column works; a pattern lookup whose right-hand side is a *nullable* expression is not yet supported. |
| Built-in scalar functions | ✅ | `Pi()`, `Random()`, `Now()` / `CURRENT_TIMESTAMP`, `Upper`, `Lower`, `Substr`, etc. map to YQL built-ins. |
| Coercing lookups (`int`-as-`str`, `date`-as-`str`), regex on NULL / non-string | ❌ | Raise during parameter handling. |
| Correlated subqueries (`Exists` / `Subquery` / `OuterRef`) | ❌ | YDB cannot resolve the outer reference. Non-correlated subqueries work. |
| Aggregation / annotation | 🟡 | Common aggregates and `GROUP BY` work; a few edge cases remain. |
| `union()` | ✅ | |
| `intersection()` / `difference()` | ❌ | Not supported by YDB. |
| UNION with `order_by` / `values_list` ordering | 🟡 | Several orderings are not yet handled. |
| UNION as a subquery / wrapped for `COUNT` | ❌ | Generates invalid SQL. |
| `bulk_create` | ✅ | Reads back generated primary keys. |
| `bulk_update` | 🟡 | Works; partial with database functions, `JSONField`, or multi-table inheritance. |
| `F()`, `Case` / `When` | ✅ | |
| Window functions (`OVER`) | ✅ | Supports `ROWS BETWEEN N PRECEDING / FOLLOWING`. |
| `RANGE BETWEEN N PRECEDING …` (bounded offsets) | ❌ | Only unbounded `PRECEDING` / `FOLLOWING` are supported. |
| `select_for_update(..., limit=...)` | ❌ | Not supported with a limit. |
| Insert into a primary-key-only / multi-table-inheritance table | ❌ | Raises `NotSupportedError` — see [Compatibility](SUPPORT.md). |
| `ignore_conflicts=True` | ❌ | Not supported. Use UPSERT (below) for race-free writes keyed on the primary key. |

## Query parameters

YDB requires typed query parameters. The backend types each parameter from the
Django expression that produced it — a lookup's value is typed from the
left-hand side's field, and nested expressions and subqueries from their own
compilation — rather than by inspecting the generated SQL. A parameter whose
type cannot be resolved is typed from its Python value.

This covers joins, foreign-key filters, `__in`, `F()`, `Case` / `When`,
annotations, aggregate (`HAVING`) filters, and non-correlated subqueries.

## Correlated subqueries

Correlated subqueries are **not supported**. `Exists()` / `Subquery()` with
`OuterRef` reference the outer table from inside the subquery, which YDB cannot
resolve. Non-correlated subqueries — for example `field__in=<queryset>` — work.

## UPSERT

UPSERT (UPDATE or INSERT) writes rows keyed on the **primary key**: a missing
row is inserted, and an existing row has the written columns overwritten while
its other columns are preserved. The backend uses YDB's native `UPSERT INTO`,
which runs as a **single atomic statement** — there is no read-modify-write
step, so concurrent upserts of the same key cannot create duplicates.

| Aspect | Status | Notes |
|--------|:------:|-------|
| `YDBManager.upsert()` / `bulk_upsert()` | ✅ | One native `UPSERT INTO` statement; no read-modify-write and no race window. |
| Conflict target | ✅ (primary key only) | UPSERT is keyed on the primary key; `conflict_target` defaults to it, and any other target raises `NotSupportedError`. |
| `update_fields` (write a subset of columns) | 🟡 | Restricts the written columns; omitted columns are preserved. YDB requires every NOT NULL column to be present, so `update_fields` may only drop nullable columns. |

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
