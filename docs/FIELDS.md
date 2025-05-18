Fields
===

Clickhouse backend support django builtin fields.

**Note:** [ForeignKey](https://docs.djangoproject.com/en/5.1/ref/models/fields/#foreignkey), [ManyToManyField](https://docs.djangoproject.com/en/5.1/ref/models/fields/#manytomanyfield)
or even [OneToOneField](https://docs.djangoproject.com/en/5.1/ref/models/fields/#onetoonefield) could be used with clickhouse backend.
But no database level constraints will be added, so there could be some consistency problems.


Django fields
---

The following django fields are supported:


| Class                                      | DB Type    | Pythonic Type     | Comments                                                                                                                                    |
|--------------------------------------------|------------|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| django.db.models.SmallAutoField            | Int16      | int               | YDB type `SmalSerial` will generate value automatically.  Range -32768 to 32767                                                             |
| django.db.models.AutoField                 | Int32      | int               | YDB type `Serial` will generate value automatically.  Range -2147483648 to 2147483647                                                       |
| django.db.models.BigAutoField              | Int64      | int               | YDB type `BigSerial` will generate value automatically.  Range -9223372036854775808 to 9223372036854775807                                  |
| django.db.models.CharField                 | UTF-8      | bytes             | Encoded as byte when written to YDB                                                                                                         |
| django.db.models.TextField                 | UTF-8      | bytes             | Encoded as byte when written to YDB                                                                                                         |
| django.db.models.BinaryField               | UTF-8      | bytes             | Encoded as byte when written to YDB                                                                                                         |
| django.db.models.SlugField                 | UTF-8      | bytes             | Encoded as byte when written to YDB                                                                                                         |
| django.db.models.FileField                 | UTF-8      | bytes             | Encoded as byte when written to YDB                                                                                                         |
| django.db.models.FilePathField             | UTF-8      | bytes             | Encoded as byte when written to YDB                                                                                                         |
| django.db.models.DateField                 | Date32     | datetime.date     | Range 1900-01-01 to 2299-12-31; Date exceed this range will be stored as min value or max value.                                            |
| django.db.models.DateTimeField             | DateTime64 | datetime.datetime | Range 1900-01-01 00:00:00, 2299-12-31 23:59:59.999999; Timezone aware; Datetime exceed this range will be stored as min value or max value. |
| django.db.models.SmallIntegerField         | Int16      | int               | Range -32768 to 32767                                                                                                                       |
| django.db.models.IntegerField              | Int32      | int               | Range -2147483648 to 2147483647                                                                                                             |
| django.db.models.BigIntegerField           | Int64      | int               | Range -9223372036854775808 to 9223372036854775807                                                                                           |
| django.db.models.PositiveSmallIntegerField | UInt16     | int               | Range 0 to 32767                                                                                                                            |
| django.db.models.PositiveIntegerField      | UInt32     | int               | Range 0 to 2147483647                                                                                                                       |
| django.db.models.PositiveBigIntegerField   | UInt64     | int               | Range 0 to 9223372036854775807                                                                                                              |
| django.db.models.FloatField                | Float64    | float             |                                                                                                                                             |
| django.db.models.DecimalField              | Decimal    | Decimal           | Pythonic values are rounded to fit the scale of the database field. supports only Decimal(22,9)                                             |
| django.db.models.UUIDField                 | UUID       | uuid.UUID         |                                                                                                                                             |
| django.db.models.IPAddressField            | UTF-8      | bytes             | Encoded as byte when written to YDB                                                                                                         |
| django.db.models.GenericIPAddressField     | UTF-8      | bytes             | Encoded as byte when written to YDB                                                                                                         |
| django.db.models.BooleanField              | Bool       | boolean           |                                                                                                                                             |
| django.db.models.EmailField                | UTF-8      | bytes             | Encoded as byte when written to YDB                                                                                                         |
