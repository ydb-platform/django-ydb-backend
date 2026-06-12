Operations
===

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

## UPSERT Operation
UPSERT (which stands for UPDATE or INSERT) updates or inserts multiple rows to a table based on a comparison by the primary key.
Missing rows are added. For the existing rows, the values of the specified columns are updated, but the values of the other columns are preserved.

To use the pert method when creating a model, specify objects = YDBManager():
```python
  class NFTToken(models.Model):
      contract_address = models.CharField(max_length=42)
      token_id = models.CharField(max_length=78, primary_key=True)
      owner = models.CharField(max_length=42)
      metadata_url = models.CharField(max_length=256)
      last_price = models.FloatField()
  
      objects = YDBManager()
  
      def __str__(self):
          return (
              f"{self.contract_address} "
              f"{self.token_id} "
              f"{self.owner} "
              f"{self.metadata_url} "
              f"{self.last_price}"
          )
```
An examples of using upsert:
```python
token1_data = {
    "contract_address": "0x1a2b3c4d5e",
    "token_id": "12345",
    "owner": "0xAlice123",
    "metadata_url": "ipfs://QmXyZ123",
    "last_price": 1.5
}
token2_data = {
    "contract_address": "0x1a2b3c4d5d",
    "token_id": "12346",
    "owner": "0xBob450",
    "metadata_url": "ipfs://QmXyZ456r04",
    "last_price": 5.7
}
update_data = {
    "token_id": "12345",
    "contract_address": "0x1a2b3c4d5e",
    "owner": "0xBob456",
    "last_price": 2.5,
    "metadata_url": "ipfs://QmXyZ456"
}
NFTToken.objects.create(token1_data)
NFTToken.objects.create(token2_data)
NFTToken.objects.upsert(update_data)
NFTToken.objects.create(token2_data)
```