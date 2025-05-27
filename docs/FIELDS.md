Fields
===

YDB backend support django builtin fields.

**Note:** [ForeignKey](https://docs.djangoproject.com/en/dev/ref/models/fields/#foreignkey), [ManyToManyField](https://docs.djangoproject.com/en/dev/ref/models/fields/#manytomanyfield)
or even [OneToOneField](https://docs.djangoproject.com/en/dev/ref/models/fields/#onetoonefield) could be used with YDB backend.
However, it's important to note that these relationships won't enforce database-level constraints, which may lead to potential data consistency issues.


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
| django.db.models.DateField                 | Date     | datetime.date     | Range of values for all time types except Interval: From 00:00 01.01.1970 to 00:00 01.01.2106. Internal Date representation: Unsigned 16-bit integer |
| django.db.models.DateTimeField             | DateTime | datetime.datetime | Internal representation: Unsigned 32-bit integer                                                                                                     |
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
