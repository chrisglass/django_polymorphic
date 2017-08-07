from unittest import TestCase

from polymorphic.models import PolymorphicTypeUndefined
from polymorphic.tests import Model2A, Model2B, Model2C, Model2D
from polymorphic.tests.test_orm import qrepr
from polymorphic.utils import sort_by_subclass, reset_polymorphic_ctype


class UtilsTests(TestCase):

    def test_sort_by_subclass(self):
        self.assertEqual(
            sort_by_subclass(Model2D, Model2B, Model2D, Model2A, Model2C),
            [Model2A, Model2B, Model2C, Model2D, Model2D]
        )

    def test_reset_polymorphic_ctype(self):
        """
        Test the the polymorphic_ctype_id can be restored.
        """
        Model2A.objects.create(field1='A1')
        Model2D.objects.create(field1='A1', field2='B2', field3='C3', field4='D4')
        Model2B.objects.create(field1='A1', field2='B2')
        Model2B.objects.create(field1='A1', field2='B2')
        Model2A.objects.all().update(polymorphic_ctype_id=None)

        with self.assertRaises(PolymorphicTypeUndefined):
            list(Model2A.objects.all())

        reset_polymorphic_ctype(Model2D, Model2B, Model2D, Model2A, Model2C)

        field_reprs = [
            "<Model2A: id 1, field1 (CharField)>",
            "<Model2D: id 2, field1 (CharField), field2 (CharField), field3 (CharField), field4 (CharField)>",
            "<Model2B: id 3, field1 (CharField), field2 (CharField)>",
            "<Model2B: id 4, field1 (CharField), field2 (CharField)>",
        ]

        for f, f_repr in zip(Model2A.objects.order_by("pk"), field_reprs):
            self.assertEqual(qrepr(f), f_repr)
