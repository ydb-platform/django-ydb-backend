# from django.test import TestCase
# from django.core.exceptions import ValidationError
# from decimal import Decimal
# from .models import FloatingPointModel
#
#
# class TestFloatingPointFields(TestCase):
#     databases = {"default"}
#
#     @pytest.mark.parametrize("value, expected", [
#         (1.23e-10, 1.23e-10),  # Маленькое значение
#         (1.23e+10, 1.23e+10),  # Большое значение
#         (-1.23e+10, -1.23e+10),  # Отрицательное значение
#         (float('inf'), float('inf')),  # Бесконечность
#     ])
#     def test_float_field_edge_cases(self, value, expected):
#         """Тестируем граничные случаи для FloatField."""
#         obj = FloatingPointModel.objects.create(float_field=value)
#         obj.refresh_from_db()
#         self.assertEqual(obj.float_field, expected)
#
#     def test_decimal_field_precision(self):
#         """Тестируем ограничение точности DecimalField."""
#         # Значение с большей точностью, чем разрешено
#         value = Decimal('0.1234567890123456789')
#         obj = FloatingPointModel.objects.create(decimal_field=value)
#         obj.refresh_from_db()
#
#         # Должно быть округлено до 9 знаков после запятой
#         self.assertEqual(obj.decimal_field, Decimal('0.123456789'))
#
#     def test_decimal_field_max_digits(self):
#         """Тестируем ограничение по количеству цифр."""
#         # Максимально допустимое значение (22 цифры, 9 после запятой)
#         valid_value = Decimal('999999999999.999999999')
#         obj = FloatingPointModel.objects.create(decimal_field=valid_value)
#         obj.refresh_from_db()
#         self.assertEqual(obj.decimal_field, valid_value)
#
#         # Слишком длинное значение
#         invalid_value = Decimal('1000000000000.000000000')  # 23 цифры
#         with transaction.atomic(), self.assertRaises(Exception):
#             FloatingPointModel.objects.create(decimal_field=invalid_value)
#
#     def test_float_field_operations(self):
#         """Тестируем арифметические операции с FloatField."""
#         from django.db.models import F
#         obj = FloatingPointModel.objects.create(float_field=10.5)
#
#         FloatingPointModel.objects.filter(pk=obj.pk).update(
#             float_field=F('float_field') * 2 + 1
#         )
#         obj.refresh_from_db()
#         self.assertAlmostEqual(obj.float_field, 22.0)
#
#     def test_decimal_field_operations(self):
#         """Тестируем точные арифметические операции с DecimalField."""
#         from django.db.models import F
#         obj = FloatingPointModel.objects.create(decimal_field=Decimal('10.5'))
#
#         FloatingPointModel.objects.filter(pk=obj.pk).update(
#             decimal_field=F('decimal_field') / Decimal('2.0') + Decimal('1.0')
#         )
#         obj.refresh_from_db()
#         self.assertEqual(obj.decimal_field, Decimal('6.25'))
#
#     def test_ydb_decimal_precision(self):
#         """Тестируем точность Decimal в YDB."""
#         test_values = [
#             ('123456789012.123456789', '123456789012.123456789'),  # Максимальная точность
#             ('0.000000001', '0.000000001'),  # Минимальное значение
#             ('-123456789012.123456789', '-123456789012.123456789'),  # Отрицательное
#         ]
#
#         for input_val, expected in test_values:
#             obj = FloatingPointModel.objects.create(decimal_field=Decimal(input_val))
#             retrieved = FloatingPointModel.objects.get(pk=obj.pk)
#             assert retrieved.decimal_field == Decimal(expected)
#
#     def test_float_field_validation(self):
#         """Тестируем валидацию FloatField."""
#         # Должно работать
#         FloatingPointModel(float_field=1.23).full_clean()
#
#         # Нечисловые значения должны вызывать ошибку
#         with self.assertRaises(ValidationError):
#             FloatingPointModel(float_field='not_a_number').full_clean()
#
#     def test_decimal_field_validation(self):
#         """Тестируем валидацию DecimalField."""
#         # Корректные значения
#         FloatingPointModel(decimal_field=Decimal('123.456')).full_clean()
#         FloatingPointModel(decimal_field='123.456').full_clean()  # Строка конвертируется
#
#         # Некорректные значения
#         with self.assertRaises(ValidationError):
#             FloatingPointModel(decimal_field='not_a_number').full_clean()
#
#         # Слишком большие значения
#         with self.assertRaises(ValidationError):
#             FloatingPointModel(decimal_field=Decimal('1e30')).full_clean()
#
#         # Слишком высокая точность
#         with self.assertRaises(ValidationError):
#             FloatingPointModel(decimal_field=Decimal('0.1234567890123')).full_clean()
#
#     def test_basic_insert(self):
#         """Тест базовой вставки значений."""
#         record = NumericOperationsModel.objects.create(
#             float_val=3.1415926535,
#             decimal_val=Decimal('2.718281828'),
#             description="Basic values"
#         )
#         self.assertEqual(record.float_val, pytest.approx(3.1415926535))
#         self.assertEqual(record.decimal_val, Decimal('2.718281828'))
#
#     def test_bulk_insert(self):
#         """Тест массовой вставки."""
#         data = [
#             NumericOperationsModel(
#                 float_val=i * 1.1,
#                 decimal_val=Decimal(str(i * 0.1)),
#                 description=f"Item {i}"
#             ) for i in range(1, 101)
#         ]
#         created = NumericOperationsModel.objects.bulk_create(data)
#         self.assertEqual(len(created), 100)
#         self.assertEqual(created[0].float_val, pytest.approx(1.1))
#
#     def test_simple_update(self):
#         """Тест простого обновления."""
#         self.record.float_val = 20.0
#         self.record.decimal_val = Decimal('10.0')
#         self.record.save()
#
#         updated = NumericOperationsModel.objects.get(pk=self.record.pk)
#         self.assertEqual(updated.float_val, 20.0)
#         self.assertEqual(updated.decimal_val, Decimal('10.0'))
#
#     def test_f_expressions(self):
#         """Тест обновления с F()-выражениями."""
#         from django.db.models import F
#         NumericOperationsModel.objects.filter(pk=self.record.pk).update(
#             float_val=F('float_val') * 1.5,
#             decimal_val=F('decimal_val') + Decimal('2.5')
#         )
#
#         updated = NumericOperationsModel.objects.get(pk=self.record.pk)
#         self.assertEqual(updated.float_val, 15.0)
#         self.assertEqual(updated.decimal_val, Decimal('7.5'))
#
#     def test_precision_update(self):
#         """Тест сохранения точности при обновлении."""
#         new_decimal = Decimal('123456789.987654321')
#         NumericOperationsModel.objects.filter(pk=self.record.pk).update(
#             decimal_val=new_decimal
#         )
#
#         updated = NumericOperationsModel.objects.get(pk=self.record.pk)
#         self.assertEqual(updated.decimal_val, new_decimal)
#
#     def test_invalid_update(self):
#         """Тест обработки невалидных значений."""
#         from django.db.utils import DataError
#         with self.assertRaises(DataError):
#             NumericOperationsModel.objects.filter(pk=self.record.pk).update(
#                 decimal_val=Decimal('1e30')  # Превышение max_digits
#             )
#
#     def test_simple_delete(self):
#         """Тест простого удаления."""
#         pk = self.record.pk
#         self.record.delete()
#         with self.assertRaises(NumericOperationsModel.DoesNotExist):
#             NumericOperationsModel.objects.get(pk=pk)
#
#     def test_bulk_delete(self):
#         """Тест массового удаления."""
#         # Создаем дополнительные записи
#         for i in range(10):
#             NumericOperationsModel.objects.create(
#                 float_val=i * 10.0,
#                 decimal_val=Decimal(str(i * 5.0))
#             )
#
#         # Удаляем все записи с float_val > 50.0
#         deleted_count, _ = NumericOperationsModel.objects.filter(
#             float_val__gt=50.0
#         ).delete()
#
#         self.assertEqual(deleted_count, 4)  # Удалится 60.0, 70.0, 80.0, 90.0
#         self.assertEqual(NumericOperationsModel.objects.count(), 7)
#
#     def test_cascade_delete(self):
#         """Тест каскадного удаления (если есть связанные модели)."""
#         from django.db import models
#
#         class RelatedModel(models.Model):
#             numeric = models.ForeignKey(
#                 NumericOperationsModel,
#                 on_delete=models.CASCADE
#             )
#
#         related = RelatedModel.objects.create(numeric=self.record)
#         self.record.delete()
#
#         with self.assertRaises(RelatedModel.DoesNotExist):
#             RelatedModel.objects.get(pk=related.pk)
