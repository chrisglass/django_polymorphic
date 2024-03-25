import uuid

import django
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.query import QuerySet

from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel
from polymorphic.query import (
    PolymorphicQuerySet,
    PolymorphicRelatedQuerySetMixin,
    PolymorphicRelatedQuerySet,
)
from polymorphic.showfields import ShowFieldContent, ShowFieldType, ShowFieldTypeAndContent


class PlainA(models.Model):
    field1 = models.CharField(max_length=10)


class PlainB(PlainA):
    field2 = models.CharField(max_length=10)


class PlainC(PlainB):
    field3 = models.CharField(max_length=10)


class Model2A(ShowFieldType, PolymorphicModel):
    field1 = models.CharField(max_length=10)
    polymorphic_showfield_deferred = True


class Model2B(Model2A):
    field2 = models.CharField(max_length=10)


class Model2C(Model2B):
    field3 = models.CharField(max_length=10)


class Model2D(Model2C):
    field4 = models.CharField(max_length=10)


class ModelExtraA(ShowFieldTypeAndContent, PolymorphicModel):
    field1 = models.CharField(max_length=10)


class ModelExtraB(ModelExtraA):
    field2 = models.CharField(max_length=10)


class ModelExtraC(ModelExtraB):
    field3 = models.CharField(max_length=10)


class ModelExtraExternal(models.Model):
    topic = models.CharField(max_length=10)


class ModelShow1(ShowFieldType, PolymorphicModel):
    field1 = models.CharField(max_length=10)
    m2m = models.ManyToManyField("self")


class ModelShow2(ShowFieldContent, PolymorphicModel):
    field1 = models.CharField(max_length=10)
    m2m = models.ManyToManyField("self")


class ModelShow3(ShowFieldTypeAndContent, PolymorphicModel):
    field1 = models.CharField(max_length=10)
    m2m = models.ManyToManyField("self")


class ModelShow1_plain(PolymorphicModel):
    field1 = models.CharField(max_length=10)


class ModelShow2_plain(ModelShow1_plain):
    field2 = models.CharField(max_length=10)


class Base(ShowFieldType, PolymorphicModel):
    polymorphic_showfield_deferred = True
    field_b = models.CharField(max_length=10)


class ModelX(Base):
    field_x = models.CharField(max_length=10)


class ModelY(Base):
    field_y = models.CharField(max_length=10)


class Enhance_Plain(models.Model):
    field_p = models.CharField(max_length=10)


class Enhance_Base(ShowFieldTypeAndContent, PolymorphicModel):
    base_id = models.AutoField(primary_key=True)
    field_b = models.CharField(max_length=10)


class Enhance_Inherit(Enhance_Base, Enhance_Plain):
    field_i = models.CharField(max_length=10)


class RelationBase(ShowFieldTypeAndContent, PolymorphicModel):
    field_base = models.CharField(max_length=10)
    fk = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, related_name="relationbase_set"
    )
    m2m = models.ManyToManyField("self")


class RelationA(RelationBase):
    field_a = models.CharField(max_length=10)


class RelationB(RelationBase):
    field_b = models.CharField(max_length=10)


class RelationBC(RelationB):
    field_c = models.CharField(max_length=10)


class RelatingModel(models.Model):
    many2many = models.ManyToManyField(Model2A)


class One2OneRelatingModel(PolymorphicModel):
    one2one = models.OneToOneField(Model2A, on_delete=models.CASCADE)
    field1 = models.CharField(max_length=10)


class One2OneRelatingModelDerived(One2OneRelatingModel):
    field2 = models.CharField(max_length=10)


class ModelUnderRelParent(PolymorphicModel):
    field1 = models.CharField(max_length=10)
    _private = models.CharField(max_length=10)


class ModelUnderRelChild(PolymorphicModel):
    parent = models.ForeignKey(
        ModelUnderRelParent, on_delete=models.CASCADE, related_name="children"
    )
    _private2 = models.CharField(max_length=10)


class MyManagerQuerySet(PolymorphicQuerySet):
    def my_queryset_foo(self):
        # Just a method to prove the existence of the custom queryset.
        return self.all()


class MyManager(PolymorphicManager):
    queryset_class = MyManagerQuerySet

    def get_queryset(self):
        return super().get_queryset().order_by("-field1")

    def my_queryset_foo(self):
        return self.all().my_queryset_foo()


class ModelWithMyManager(ShowFieldTypeAndContent, Model2A):
    objects = MyManager()
    field4 = models.CharField(max_length=10)


class ModelWithMyManagerNoDefault(ShowFieldTypeAndContent, Model2A):
    objects = PolymorphicManager()
    my_objects = MyManager()
    field4 = models.CharField(max_length=10)


class ModelWithMyManagerDefault(ShowFieldTypeAndContent, Model2A):
    my_objects = MyManager()
    objects = PolymorphicManager()
    field4 = models.CharField(max_length=10)


class ModelWithMyManager2(ShowFieldTypeAndContent, Model2A):
    objects = MyManagerQuerySet.as_manager()
    field4 = models.CharField(max_length=10)


class MROBase1(ShowFieldType, PolymorphicModel):
    objects = MyManager()
    field1 = models.CharField(max_length=10)  # needed as MyManager uses it


class MROBase2(MROBase1):
    pass
    # No manager_inheritance_from_future or Meta set. test that polymorphic restores that.


class MROBase3(models.Model):
    # make sure 'id' field doesn't clash, detected by Django 1.11
    base_3_id = models.AutoField(primary_key=True)
    objects = models.Manager()


class MRODerived(MROBase2, MROBase3):
    pass


class ParentModelWithManager(PolymorphicModel):
    pass


class ChildModelWithManager(PolymorphicModel):
    # Also test whether foreign keys receive the manager:
    field1 = models.CharField(max_length=10)  # needed as MyManager uses it
    fk = models.ForeignKey(
        ParentModelWithManager, on_delete=models.CASCADE, related_name="childmodel_set"
    )
    objects = MyManager()


class PlainMyManagerQuerySet(QuerySet):
    def my_queryset_foo(self):
        # Just a method to prove the existence of the custom queryset.
        return self.all()


class PlainMyManager(models.Manager):
    def my_queryset_foo(self):
        return self.get_queryset().my_queryset_foo()

    def get_queryset(self):
        return PlainMyManagerQuerySet(self.model, using=self._db)


class PlainParentModelWithManager(models.Model):
    pass


class PlainChildModelWithManager(models.Model):
    fk = models.ForeignKey(
        PlainParentModelWithManager,
        on_delete=models.CASCADE,
        related_name="childmodel_set",
    )
    objects = PlainMyManager()


class BlogBase(ShowFieldTypeAndContent, PolymorphicModel):
    name = models.CharField(max_length=10)


class BlogA(BlogBase):
    info = models.CharField(max_length=10)


class BlogB(BlogBase):
    pass


class BlogEntry(ShowFieldTypeAndContent, PolymorphicModel):
    blog = models.ForeignKey(BlogA, on_delete=models.CASCADE)
    text = models.CharField(max_length=10)


class BlogEntry_limit_choices_to(ShowFieldTypeAndContent, PolymorphicModel):
    blog = models.ForeignKey(BlogBase, on_delete=models.CASCADE)
    text = models.CharField(max_length=10)


class ModelFieldNameTest(ShowFieldType, PolymorphicModel):
    modelfieldnametest = models.CharField(max_length=10)


class InitTestModel(ShowFieldType, PolymorphicModel):
    bar = models.CharField(max_length=100)

    def __init__(self, *args, **kwargs):
        kwargs["bar"] = self.x()
        super().__init__(*args, **kwargs)


class InitTestModelSubclass(InitTestModel):
    def x(self):
        return "XYZ"


# models from github issue


class Top(PolymorphicModel):
    name = models.CharField(max_length=50)


class Middle(Top):
    description = models.TextField()


class Bottom(Middle):
    author = models.CharField(max_length=50)


class UUIDProject(ShowFieldTypeAndContent, PolymorphicModel):
    uuid_primary_key = models.UUIDField(primary_key=True, default=uuid.uuid1)
    topic = models.CharField(max_length=30)


class UUIDArtProject(UUIDProject):
    artist = models.CharField(max_length=30)


class UUIDResearchProject(UUIDProject):
    supervisor = models.CharField(max_length=30)


class UUIDPlainA(models.Model):
    uuid_primary_key = models.UUIDField(primary_key=True, default=uuid.uuid1)
    field1 = models.CharField(max_length=10)


class UUIDPlainB(UUIDPlainA):
    field2 = models.CharField(max_length=10)


class UUIDPlainC(UUIDPlainB):
    field3 = models.CharField(max_length=10)


# base -> proxy


class ProxyBase(PolymorphicModel):
    some_data = models.CharField(max_length=128)


class ProxyChild(ProxyBase):
    class Meta:
        proxy = True


class NonProxyChild(ProxyBase):
    name = models.CharField(max_length=10)


# base -> proxy -> real models




class ProxiedBase(ShowFieldTypeAndContent, PolymorphicModel):
    name = models.CharField(max_length=10)


class ProxyModelBase(ProxiedBase):
    class Meta:
        proxy = True


class ProxyModelA(ProxyModelBase):
    field1 = models.CharField(max_length=10)


class ProxyModelB(ProxyModelBase):
    field2 = models.CharField(max_length=10)


# test bad field name
# class TestBadFieldModel(ShowFieldType, PolymorphicModel):
#    instance_of = models.CharField(max_length=10)


# validation error: "polymorphic.relatednameclash: Accessor for field 'polymorphic_ctype' clashes
# with related field 'ContentType.relatednameclash_set'." (reported by Andrew Ingram)
# fixed with related_name
class RelatedNameClash(ShowFieldType, PolymorphicModel):
    ctype = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, editable=False)


# class with a parent_link to superclass, and a related_name back to subclass


class TestParentLinkAndRelatedName(ModelShow1_plain):
    superclass = models.OneToOneField(
        ModelShow1_plain,
        on_delete=models.CASCADE,
        parent_link=True,
        related_name="related_name_subclass",
    )


class CustomPkBase(ShowFieldTypeAndContent, PolymorphicModel):
    b = models.CharField(max_length=1)


class CustomPkInherit(CustomPkBase):
    custom_id = models.AutoField(primary_key=True)
    i = models.CharField(max_length=1)


class DateModel(PolymorphicModel):
    date = models.DateTimeField()


# Define abstract and swappable (being swapped for SwappedModel) models
# To test manager validation (should be skipped for such models)
class AbstractModel(PolymorphicModel):
    class Meta:
        abstract = True


class SwappableModel(AbstractModel):
    class Meta:
        swappable = "POLYMORPHIC_TEST_SWAPPABLE"


class SwappedModel(AbstractModel):
    pass


class InlineParent(models.Model):
    title = models.CharField(max_length=10)


class InlineModelA(PolymorphicModel):
    parent = models.ForeignKey(
        InlineParent, related_name="inline_children", on_delete=models.CASCADE
    )
    field1 = models.CharField(max_length=10)


class InlineModelB(InlineModelA):
    field2 = models.CharField(max_length=10)


class AbstractProject(PolymorphicModel):
    topic = models.CharField(max_length=30)

    class Meta:
        abstract = True


class ArtProject(AbstractProject):
    artist = models.CharField(max_length=30)


class Duck(PolymorphicModel):
    name = models.CharField(max_length=30)


class RedheadDuck(Duck):
    class Meta:
        proxy = True


class RubberDuck(Duck):
    class Meta:
        proxy = True


class MultiTableBase(PolymorphicModel):
    field1 = models.CharField(max_length=10)


class MultiTableDerived(MultiTableBase):
    field2 = models.CharField(max_length=10)


class SubclassSelectorAbstractBaseModel(PolymorphicModel):
    base_field = models.CharField(max_length=10, default="test_bf")


class SubclassSelectorAbstractModel(SubclassSelectorAbstractBaseModel):
    abstract_field = models.CharField(max_length=10, default="test_af")

    class Meta:
        abstract = True


class SubclassSelectorAbstractConcreteModel(SubclassSelectorAbstractModel):
    concrete_field = models.CharField(max_length=10, default="test_cf")


class SubclassSelectorProxyBaseModel(PolymorphicModel):
    base_field = models.CharField(max_length=10, default="test_bf")


class SubclassSelectorProxyModel(SubclassSelectorProxyBaseModel):
    class Meta:
        proxy = True


class SubclassSelectorProxyConcreteModel(SubclassSelectorProxyModel):
    concrete_field = models.CharField(max_length=10, default="test_cf")


class NonPolymorphicParent(PolymorphicModel, Group):
    test = models.CharField(max_length=22, default="test_non_polymorphic_parent")


class NonSymRelationBase(PolymorphicModel):
    field_base = models.CharField(max_length=10)
    fk = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, related_name="relationbase_set"
    )
    m2m = models.ManyToManyField("self", symmetrical=False)


class NonSymRelationA(NonSymRelationBase):
    field_a = models.CharField(max_length=10)


class NonSymRelationB(NonSymRelationBase):
    field_b = models.CharField(max_length=10)


class NonSymRelationBC(NonSymRelationBase):
    field_c = models.CharField(max_length=10)


class CustomPolySupportingQuerySet(PolymorphicRelatedQuerySetMixin, models.QuerySet):
    pass


class ParentModel(PolymorphicModel):
    name = models.CharField(max_length=10)


class ChildModel(ParentModel):
    other_name = models.CharField(max_length=10)
    link_on_child = models.ForeignKey(
        ModelExtraExternal, on_delete=models.CASCADE, null=True, related_name="+"
    )


class AltChildModel(ParentModel):
    other_name = models.CharField(max_length=10)
    link_on_altchild = models.ForeignKey(
        PlainA, on_delete=models.CASCADE, null=True, related_name="+"
    )


class AltChildAsBaseModel(AltChildModel):
    more_name = models.CharField(max_length=10)


class PlainModel(models.Model):
    relation = models.ForeignKey(ParentModel, on_delete=models.CASCADE)
    objects = models.Manager.from_queryset(PolymorphicRelatedQuerySet)()


class PlainModelWithM2M(models.Model):
    field1 = models.CharField(max_length=10)
    m2m = models.ManyToManyField(ParentModel)
    objects = models.Manager.from_queryset(PolymorphicRelatedQuerySet)()


class AltChildWithM2MModel(AltChildModel):
    m2m = models.ManyToManyField(PlainA)
