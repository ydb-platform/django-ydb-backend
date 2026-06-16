Fields
===

> See the [support contract](SUPPORT.md#fields) for the per-field support level
> (supported / best-effort / unsupported). This page documents the type mapping.

YDB backend support django builtin fields.

## Relationship fields

[ForeignKey](https://docs.djangoproject.com/en/dev/ref/models/fields/#foreignkey),
[ManyToManyField](https://docs.djangoproject.com/en/dev/ref/models/fields/#manytomanyfield),
and [OneToOneField](https://docs.djangoproject.com/en/dev/ref/models/fields/#onetoonefield)
can be used by the Django ORM, but YDB doesn't enforce database-level foreign
key constraints or uniqueness constraints.

The backend stores `ForeignKey` values as regular scalar columns. For example:

```python
class Product(models.Model):
    sku = models.CharField(max_length=20, primary_key=True)


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    rating = models.IntegerField()
```

`ProductReview.product` is stored as a `product_id` column with the same YDB type
as `Product.sku`. The schema doesn't include `FOREIGN KEY`, `REFERENCES`,
database-level `ON DELETE` rules, or unique constraints for relation fields.

This means inserts and updates write the referenced primary key value only:

```python
ProductReview.objects.create(product_id="SKU-1", rating=5)
```

YDB accepts this row even if no `Product(sku="SKU-1")` exists. Django ORM
cascade behavior applies only when deleting objects through Django. Raw SQL,
external writers, or direct `*_id` assignments may create orphan rows.

`OneToOneField` is stored like a `ForeignKey`; its one-to-one uniqueness is not
guaranteed by YDB. `ManyToManyField` uses a Django through table with scalar
`*_id` columns, but uniqueness of pairs and database-level cascade behavior are
not enforced by YDB.


Django fields
---

The following django fields are supported:


| Class                                      | DB Type  | Pythonic Type     | Comments                                                                                                                                             |
|--------------------------------------------|----------|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| django.db.models.SmallAutoField            | Int16    | int               | YDB type `SmalSerial` will generate value automatically.  Range -32768 to 32767                                                                      |
| django.db.models.AutoField                 | Int32    | int               | YDB type `Serial` will generate value automatically.  Range -2147483648 to 2147483647                                                                |
| django.db.models.BigAutoField              | Int64    | int               | YDB type `BigSerial` will generate value automatically.  Range -9223372036854775808 to 9223372036854775807                                           |
| django.db.models.CharField                 | UTF-8    | str               |                                                                                                                                                      |
| django.db.models.TextField                 | UTF-8    | str               |                                                                                                                                                      |
| django.db.models.BinaryField               | String   | bytes             |                                                                                                                                                      |
| django.db.models.SlugField                 | UTF-8    | str               |                                                                                                                                                      |
| django.db.models.FileField                 | String   | bytes             |                                                                                                                                                      |
| django.db.models.FilePathField             | UTF-8    | str               |                                                                                                                                                      |
| django.db.models.DateField                 | Date32      | datetime.date     | Signed wide date type, so dates before 1970 round-trip (range ~144169 BCE to 148107 CE)                                                              |
| django.db.models.DateTimeField             | Timestamp64 | datetime.datetime | Signed wide type with microsecond precision; supports instants before 1970 (range ~144169 BCE to 148107 CE)                                          |
| django.db.models.TimeField                 | Int64       | datetime.time     | YDB has no native time type; stored as microseconds since midnight (introspects back as BigIntegerField)                                             |
| django.db.models.DurationField             | Interval | int               | The range of values is from -136 years to +136 years. The internal representation is a 64–bit signed integer. Cannot be used in the primary key      |
| django.db.models.SmallIntegerField         | Int16    | int               | Range -32768 to 32767                                                                                                                                |
| django.db.models.IntegerField              | Int32    | int               | Range -2147483648 to 2147483647                                                                                                                      |
| django.db.models.BigIntegerField           | Int64    | int               | Range -9223372036854775808 to 9223372036854775807                                                                                                    |
| django.db.models.PositiveSmallIntegerField | UInt16   | int               | Range 0 to 65535                                                                                                                                     |
| django.db.models.PositiveIntegerField      | UInt32   | int               | Range 0 to 4294967295                                                                                                                                |
| django.db.models.PositiveBigIntegerField   | UInt64   | int               | Range 0 to 18446744073709551615                                                                                                                      |
| django.db.models.FloatField                | Float    | float             | A real number with variable precision, 4 bytes in size. Can't be used in the primary key                                                             |
| django.db.models.DecimalField              | Decimal  | Decimal           | Pythonic values are rounded to fit the scale of the database field. Supports only Decimal(22,9)                                                      |
| django.db.models.UUIDField                 | UUID     | uuid.UUID         |                                                                                                                                                      |
| django.db.models.IPAddressField            | UTF-8    | str               |                                                                                                                                                      |
| django.db.models.GenericIPAddressField     | UTF-8    | str               |                                                                                                                                                      |
| django.db.models.BooleanField              | Bool     | boolean           |                                                                                                                                                      |
| django.db.models.EmailField                | UTF-8    | str               |                                                                                                                                                      |
| django.db.models.JSONField                 | Json     | dict / list / str / int / float / bool | Stored as a JSON text column. Equality filter (`filter(data=value)`) is not supported by YDB. `null=True` is supported (stored as SQL NULL; `__isnull` filtering works). |
