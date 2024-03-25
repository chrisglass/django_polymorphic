import uuid

import django.db.models.deletion
import django.db.models.manager
from django.db import migrations, models

import polymorphic.showfields


class Migration(migrations.Migration):
    initial = True

    dependencies = [("contenttypes", "0002_remove_content_type_name")]

    operations = [
        migrations.CreateModel(
            name="SwappableModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tests.swappablemodel_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
            ],
            options={"swappable": "POLYMORPHIC_TEST_SWAPPABLE"},
        ),
        migrations.CreateModel(
            name="Base",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("field_b", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldType, models.Model),
        ),
        migrations.CreateModel(
            name="BlogBase",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldTypeAndContent, models.Model),
        ),
        migrations.CreateModel(
            name="BlogEntry",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("text", models.CharField(max_length=10)),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tests.blogentry_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldTypeAndContent, models.Model),
        ),
        migrations.CreateModel(
            name="BlogEntry_limit_choices_to",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("text", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldTypeAndContent, models.Model),
        ),
        migrations.CreateModel(
            name="ChildModelWithManager",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                )
            ],
            options={"abstract": False, "base_manager_name": "objects"},
        ),
        migrations.CreateModel(
            name="CustomPkBase",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("b", models.CharField(max_length=1)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldTypeAndContent, models.Model),
        ),
        migrations.CreateModel(
            name="DateModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date", models.DateTimeField()),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tests.datemodel_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
        ),
        migrations.CreateModel(
            name="Enhance_Base",
            fields=[
                ("base_id", models.AutoField(primary_key=True, serialize=False)),
                ("field_b", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldTypeAndContent, models.Model),
        ),
        migrations.CreateModel(
            name="Enhance_Plain",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("field_p", models.CharField(max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name="InitTestModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("bar", models.CharField(max_length=100)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldType, models.Model),
        ),
        migrations.CreateModel(
            name="MgrInheritA",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("field1", models.CharField(max_length=10)),
            ],
            managers=[("mgrA", django.db.models.manager.Manager())],
        ),
        migrations.CreateModel(
            name="Model2A",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("field1", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldType, models.Model),
        ),
        migrations.CreateModel(
            name="ModelExtraA",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("field1", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldTypeAndContent, models.Model),
        ),
        migrations.CreateModel(
            name="ModelExtraExternal",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("topic", models.CharField(max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name="ModelFieldNameTest",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("modelfieldnametest", models.CharField(max_length=10)),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tests.modelfieldnametest_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldType, models.Model),
        ),
        migrations.CreateModel(
            name="ModelShow1",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("field1", models.CharField(max_length=10)),
                (
                    "m2m",
                    models.ManyToManyField(
                        related_name="_modelshow1_m2m_+", to="tests.ModelShow1"
                    ),
                ),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tests.modelshow1_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldType, models.Model),
        ),
        migrations.CreateModel(
            name="ModelShow1_plain",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("field1", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
        ),
        migrations.CreateModel(
            name="ModelShow2",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("field1", models.CharField(max_length=10)),
                (
                    "m2m",
                    models.ManyToManyField(
                        related_name="_modelshow2_m2m_+", to="tests.ModelShow2"
                    ),
                ),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tests.modelshow2_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldContent, models.Model),
        ),
        migrations.CreateModel(
            name="ModelShow3",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("field1", models.CharField(max_length=10)),
                (
                    "m2m",
                    models.ManyToManyField(
                        related_name="_modelshow3_m2m_+", to="tests.ModelShow3"
                    ),
                ),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tests.modelshow3_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldTypeAndContent, models.Model),
        ),
        migrations.CreateModel(
            name="ModelUnderRelChild",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("_private2", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
        ),
        migrations.CreateModel(
            name="ModelUnderRelParent",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("field1", models.CharField(max_length=10)),
                ("_private", models.CharField(max_length=10)),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tests.modelunderrelparent_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
        ),
        migrations.CreateModel(
            name="MROBase1",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("field1", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldType, models.Model),
        ),
        migrations.CreateModel(
            name="MROBase3",
            fields=[("base_3_id", models.AutoField(primary_key=True, serialize=False))],
        ),
        migrations.CreateModel(
            name="One2OneRelatingModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("field1", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
        ),
        migrations.CreateModel(
            name="ParentModelWithManager",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tests.parentmodelwithmanager_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
        ),
        migrations.CreateModel(
            name="PlainA",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("field1", models.CharField(max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name="PlainChildModelWithManager",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                )
            ],
        ),
        migrations.CreateModel(
            name="PlainParentModelWithManager",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                )
            ],
        ),
        migrations.CreateModel(
            name="ProxiedBase",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=10)),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tests.proxiedbase_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldTypeAndContent, models.Model),
        ),
        migrations.CreateModel(
            name="ProxyBase",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("some_data", models.CharField(max_length=128)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
        ),
        migrations.CreateModel(
            name="RelatedNameClash",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="contenttypes.ContentType",
                    ),
                ),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tests.relatednameclash_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldType, models.Model),
        ),
        migrations.CreateModel(
            name="RelatingModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                )
            ],
        ),
        migrations.CreateModel(
            name="RelationBase",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("field_base", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldTypeAndContent, models.Model),
        ),
        migrations.CreateModel(
            name="SwappedModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tests.swappedmodel_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="Top",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=50)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
        ),
        migrations.CreateModel(
            name="UUIDPlainA",
            fields=[
                (
                    "uuid_primary_key",
                    models.UUIDField(default=uuid.uuid1, primary_key=True, serialize=False),
                ),
                ("field1", models.CharField(max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name="UUIDProject",
            fields=[
                (
                    "uuid_primary_key",
                    models.UUIDField(default=uuid.uuid1, primary_key=True, serialize=False),
                ),
                ("topic", models.CharField(max_length=30)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldTypeAndContent, models.Model),
        ),
        migrations.CreateModel(
            name="BlogA",
            fields=[
                (
                    "blogbase_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.BlogBase",
                    ),
                ),
                ("info", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.blogbase",),
        ),
        migrations.CreateModel(
            name="BlogB",
            fields=[
                (
                    "blogbase_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.BlogBase",
                    ),
                )
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.blogbase",),
        ),
        migrations.CreateModel(
            name="CustomPkInherit",
            fields=[
                (
                    "custompkbase_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        to="tests.CustomPkBase",
                    ),
                ),
                ("custom_id", models.AutoField(primary_key=True, serialize=False)),
                ("i", models.CharField(max_length=1)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.custompkbase",),
        ),
        migrations.CreateModel(
            name="Enhance_Inherit",
            fields=[
                (
                    "enhance_plain_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        to="tests.Enhance_Plain",
                    ),
                ),
                (
                    "enhance_base_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.Enhance_Base",
                    ),
                ),
                ("field_i", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.enhance_base", "tests.enhance_plain"),
        ),
        migrations.CreateModel(
            name="InitTestModelSubclass",
            fields=[
                (
                    "inittestmodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.InitTestModel",
                    ),
                )
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.inittestmodel",),
        ),
        migrations.CreateModel(
            name="MgrInheritB",
            fields=[
                (
                    "mgrinherita_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.MgrInheritA",
                    ),
                ),
                ("field2", models.CharField(max_length=10)),
            ],
            bases=("tests.mgrinherita",),
            managers=[("mgrB", django.db.models.manager.Manager())],
        ),
        migrations.CreateModel(
            name="Middle",
            fields=[
                (
                    "top_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.Top",
                    ),
                ),
                ("description", models.TextField()),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.top",),
        ),
        migrations.CreateModel(
            name="Model2B",
            fields=[
                (
                    "model2a_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.Model2A",
                    ),
                ),
                ("field2", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.model2a",),
        ),
        migrations.CreateModel(
            name="ModelExtraB",
            fields=[
                (
                    "modelextraa_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.ModelExtraA",
                    ),
                ),
                ("field2", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.modelextraa",),
        ),
        migrations.CreateModel(
            name="ModelShow2_plain",
            fields=[
                (
                    "modelshow1_plain_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.ModelShow1_plain",
                    ),
                ),
                ("field2", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.modelshow1_plain",),
        ),
        migrations.CreateModel(
            name="ModelWithMyManager",
            fields=[
                (
                    "model2a_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.Model2A",
                    ),
                ),
                ("field4", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldTypeAndContent, "tests.model2a"),
        ),
        migrations.CreateModel(
            name="ModelWithMyManager2",
            fields=[
                (
                    "model2a_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.Model2A",
                    ),
                ),
                ("field4", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldTypeAndContent, "tests.model2a"),
        ),
        migrations.CreateModel(
            name="ModelWithMyManagerDefault",
            fields=[
                (
                    "model2a_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.Model2A",
                    ),
                ),
                ("field4", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldTypeAndContent, "tests.model2a"),
            managers=[
                ("my_objects", django.db.models.manager.Manager()),
                ("objects", django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name="ModelWithMyManagerNoDefault",
            fields=[
                (
                    "model2a_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.Model2A",
                    ),
                ),
                ("field4", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=(polymorphic.showfields.ShowFieldTypeAndContent, "tests.model2a"),
        ),
        migrations.CreateModel(
            name="ModelX",
            fields=[
                (
                    "base_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.Base",
                    ),
                ),
                ("field_x", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.base",),
        ),
        migrations.CreateModel(
            name="ModelY",
            fields=[
                (
                    "base_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.Base",
                    ),
                ),
                ("field_y", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.base",),
        ),
        migrations.CreateModel(
            name="MROBase2",
            fields=[
                (
                    "mrobase1_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.MROBase1",
                    ),
                )
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.mrobase1",),
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("base_objects", django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name="NonProxyChild",
            fields=[
                (
                    "proxybase_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.ProxyBase",
                    ),
                ),
                ("name", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.proxybase",),
        ),
        migrations.CreateModel(
            name="One2OneRelatingModelDerived",
            fields=[
                (
                    "one2onerelatingmodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.One2OneRelatingModel",
                    ),
                ),
                ("field2", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.one2onerelatingmodel",),
        ),
        migrations.CreateModel(
            name="PlainB",
            fields=[
                (
                    "plaina_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.PlainA",
                    ),
                ),
                ("field2", models.CharField(max_length=10)),
            ],
            bases=("tests.plaina",),
        ),
        migrations.CreateModel(
            name="RelationA",
            fields=[
                (
                    "relationbase_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.RelationBase",
                    ),
                ),
                ("field_a", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.relationbase",),
        ),
        migrations.CreateModel(
            name="RelationB",
            fields=[
                (
                    "relationbase_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.RelationBase",
                    ),
                ),
                ("field_b", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.relationbase",),
        ),
        migrations.CreateModel(
            name="TestParentLinkAndRelatedName",
            fields=[
                (
                    "superclass",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        related_name="related_name_subclass",
                        serialize=False,
                        to="tests.ModelShow1_plain",
                    ),
                )
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.modelshow1_plain",),
        ),
        migrations.CreateModel(
            name="UUIDArtProject",
            fields=[
                (
                    "uuidproject_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.UUIDProject",
                    ),
                ),
                ("artist", models.CharField(max_length=30)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.uuidproject",),
        ),
        migrations.CreateModel(
            name="UUIDPlainB",
            fields=[
                (
                    "uuidplaina_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.UUIDPlainA",
                    ),
                ),
                ("field2", models.CharField(max_length=10)),
            ],
            bases=("tests.uuidplaina",),
        ),
        migrations.CreateModel(
            name="UUIDResearchProject",
            fields=[
                (
                    "uuidproject_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.UUIDProject",
                    ),
                ),
                ("supervisor", models.CharField(max_length=30)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.uuidproject",),
        ),
        migrations.AddField(
            model_name="uuidproject",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.uuidproject_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.AddField(
            model_name="top",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.top_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.AddField(
            model_name="relationbase",
            name="fk",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="relationbase_set",
                to="tests.RelationBase",
            ),
        ),
        migrations.AddField(
            model_name="relationbase",
            name="m2m",
            field=models.ManyToManyField(
                related_name="_relationbase_m2m_+", to="tests.RelationBase"
            ),
        ),
        migrations.AddField(
            model_name="relationbase",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.relationbase_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.AddField(
            model_name="relatingmodel",
            name="many2many",
            field=models.ManyToManyField(to="tests.Model2A"),
        ),
        migrations.AddField(
            model_name="proxybase",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.proxybase_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.AddField(
            model_name="plainchildmodelwithmanager",
            name="fk",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="childmodel_set",
                to="tests.PlainParentModelWithManager",
            ),
        ),
        migrations.AddField(
            model_name="one2onerelatingmodel",
            name="one2one",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE, to="tests.Model2A"
            ),
        ),
        migrations.AddField(
            model_name="one2onerelatingmodel",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.one2onerelatingmodel_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.AddField(
            model_name="mrobase1",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.mrobase1_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.AddField(
            model_name="modelunderrelchild",
            name="parent",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="children",
                to="tests.ModelUnderRelParent",
            ),
        ),
        migrations.AddField(
            model_name="modelunderrelchild",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.modelunderrelchild_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.AddField(
            model_name="modelshow1_plain",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.modelshow1_plain_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.AddField(
            model_name="modelextraa",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.modelextraa_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.AddField(
            model_name="model2a",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.model2a_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.AddField(
            model_name="inittestmodel",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.inittestmodel_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.AddField(
            model_name="enhance_base",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.enhance_base_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.AddField(
            model_name="custompkbase",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.custompkbase_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.AddField(
            model_name="childmodelwithmanager",
            name="fk",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="childmodel_set",
                to="tests.ParentModelWithManager",
            ),
        ),
        migrations.AddField(
            model_name="childmodelwithmanager",
            name="field1",
            field=models.CharField(
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="childmodelwithmanager",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.childmodelwithmanager_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.AddField(
            model_name="blogentry_limit_choices_to",
            name="blog",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="tests.BlogBase"
            ),
        ),
        migrations.AddField(
            model_name="blogentry_limit_choices_to",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.blogentry_limit_choices_to_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.AddField(
            model_name="blogbase",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.blogbase_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.AddField(
            model_name="base",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.base_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.CreateModel(
            name="ProxyChild",
            fields=[],
            options={"proxy": True},
            bases=("tests.proxybase",),
        ),
        migrations.CreateModel(
            name="ProxyModelBase",
            fields=[],
            options={"proxy": True},
            bases=("tests.proxiedbase",),
        ),
        migrations.CreateModel(
            name="Bottom",
            fields=[
                (
                    "middle_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.Middle",
                    ),
                ),
                ("author", models.CharField(max_length=50)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.middle",),
        ),
        migrations.CreateModel(
            name="MgrInheritC",
            fields=[
                (
                    "mgrinheritb_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.MgrInheritB",
                    ),
                )
            ],
            bases=(polymorphic.showfields.ShowFieldTypeAndContent, "tests.mgrinheritb"),
        ),
        migrations.CreateModel(
            name="Model2C",
            fields=[
                (
                    "model2b_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.Model2B",
                    ),
                ),
                ("field3", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.model2b",),
        ),
        migrations.CreateModel(
            name="ModelExtraC",
            fields=[
                (
                    "modelextrab_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.ModelExtraB",
                    ),
                ),
                ("field3", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.modelextrab",),
        ),
        migrations.CreateModel(
            name="MRODerived",
            fields=[
                (
                    "mrobase3_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        to="tests.MROBase3",
                    ),
                ),
                (
                    "mrobase2_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.MROBase2",
                    ),
                ),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.mrobase2", "tests.mrobase3"),
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("base_objects", django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name="PlainC",
            fields=[
                (
                    "plainb_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.PlainB",
                    ),
                ),
                ("field3", models.CharField(max_length=10)),
            ],
            bases=("tests.plainb",),
        ),
        migrations.CreateModel(
            name="ProxyModelA",
            fields=[
                (
                    "proxiedbase_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.ProxiedBase",
                    ),
                ),
                ("field1", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.proxymodelbase",),
        ),
        migrations.CreateModel(
            name="ProxyModelB",
            fields=[
                (
                    "proxiedbase_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.ProxiedBase",
                    ),
                ),
                ("field2", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.proxymodelbase",),
        ),
        migrations.CreateModel(
            name="RelationBC",
            fields=[
                (
                    "relationb_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.RelationB",
                    ),
                ),
                ("field_c", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.relationb",),
        ),
        migrations.CreateModel(
            name="UUIDPlainC",
            fields=[
                (
                    "uuidplainb_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.UUIDPlainB",
                    ),
                ),
                ("field3", models.CharField(max_length=10)),
            ],
            bases=("tests.uuidplainb",),
        ),
        migrations.AddField(
            model_name="blogentry",
            name="blog",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="tests.BlogA"),
        ),
        migrations.CreateModel(
            name="Model2D",
            fields=[
                (
                    "model2c_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.Model2C",
                    ),
                ),
                ("field4", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.model2c",),
        ),
        migrations.CreateModel(
            name="InlineModelBase",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                )
            ],
            options={"abstract": False, "base_manager_name": "objects"},
        ),
        migrations.CreateModel(
            name="InlineParent",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name="InlineModelA",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("field1", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
        ),
        migrations.CreateModel(
            name="InlineModelB",
            fields=[
                (
                    "inlinemodela_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.InlineModelA",
                    ),
                ),
                ("field2", models.CharField(max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.inlinemodela",),
        ),
        migrations.AddField(
            model_name="inlinemodela",
            name="parent",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="tests.InlineParent",
                related_name="inline_children",
            ),
        ),
        migrations.AddField(
            model_name="inlinemodela",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.inlinemodela_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.CreateModel(
            name="ArtProject",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("topic", models.CharField(max_length=30)),
                ("artist", models.CharField(max_length=30)),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tests.artproject_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="Duck",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=30)),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tests.duck_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="MultiTableBase",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("field1", models.CharField(max_length=10)),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="MultiTableDerived",
            fields=[
                (
                    "multitablebase_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.MultiTableBase",
                    ),
                ),
                ("field2", models.CharField(max_length=10)),
            ],
            options={"abstract": False},
            bases=("tests.multitablebase",),
        ),
        migrations.AddField(
            model_name="multitablebase",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.multitablebase_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.CreateModel(
            name="RedheadDuck",
            fields=[],
            options={"proxy": True},
            bases=("tests.duck",),
        ),
        migrations.CreateModel(
            name="RubberDuck", fields=[], options={"proxy": True}, bases=("tests.duck",)
        ),
        migrations.CreateModel(
            name="SubclassSelectorAbstractBaseModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("base_field", models.CharField(default="test_bf", max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
        ),
        migrations.CreateModel(
            name="SubclassSelectorProxyBaseModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("base_field", models.CharField(default="test_bf", max_length=10)),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tests.subclassselectorproxybasemodel_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
        ),
        migrations.CreateModel(
            name="SubclassSelectorAbstractConcreteModel",
            fields=[
                (
                    "subclassselectorabstractbasemodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.SubclassSelectorAbstractBaseModel",
                    ),
                ),
                ("abstract_field", models.CharField(default="test_af", max_length=10)),
                ("concrete_field", models.CharField(default="test_cf", max_length=10)),
            ],
            options={"abstract": False},
            bases=("tests.subclassselectorabstractbasemodel",),
        ),
        migrations.AddField(
            model_name="subclassselectorabstractbasemodel",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_tests.subclassselectorabstractbasemodel_set+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.CreateModel(
            name="SubclassSelectorProxyModel",
            fields=[],
            options={"proxy": True, "indexes": []},
            bases=("tests.subclassselectorproxybasemodel",),
        ),
        migrations.CreateModel(
            name="SubclassSelectorProxyConcreteModel",
            fields=[
                (
                    "subclassselectorproxybasemodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.SubclassSelectorProxyBaseModel",
                    ),
                ),
                ("concrete_field", models.CharField(default="test_cf", max_length=10)),
            ],
            options={"abstract": False, "base_manager_name": "objects"},
            bases=("tests.subclassselectorproxymodel",),
        ),
        migrations.CreateModel(
            name="NonPolymorphicParent",
            fields=[
                (
                    "group_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="auth.Group",
                    ),
                ),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tests.nonpolymorphicparent_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
                (
                    "test",
                    models.CharField(max_length=255, default="test_non_polymorphic_parent"),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("auth.group", models.Model),
        ),
        migrations.CreateModel(
            name="NonSymRelationBase",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("field_base", models.CharField(max_length=10)),
                (
                    "fk",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="relationbase_set",
                        to="tests.nonsymrelationbase",
                    ),
                ),
                ("m2m", models.ManyToManyField(to="tests.nonsymrelationbase")),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_%(app_label)s.%(class)s_set+",
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
        ),
        migrations.CreateModel(
            name="ParentModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=10)),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_%(app_label)s.%(class)s_set+",
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
        ),
        migrations.CreateModel(
            name="PlainModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "relation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="tests.parentmodel"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PlainModelWithM2M",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("field1", models.CharField(max_length=10)),
                ("m2m", models.ManyToManyField(to="tests.parentmodel")),
            ],
        ),
        migrations.CreateModel(
            name="AltChildModel",
            fields=[
                (
                    "parentmodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.parentmodel",
                    ),
                ),
                ("other_name", models.CharField(max_length=10)),
                (
                    "link_on_altchild",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="tests.plaina",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("tests.parentmodel",),
        ),
        migrations.CreateModel(
            name="ChildModel",
            fields=[
                (
                    "parentmodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.parentmodel",
                    ),
                ),
                ("other_name", models.CharField(max_length=10)),
                (
                    "link_on_child",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="tests.modelextraexternal",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("tests.parentmodel",),
        ),
        migrations.CreateModel(
            name="NonSymRelationA",
            fields=[
                (
                    "nonsymrelationbase_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.nonsymrelationbase",
                    ),
                ),
                ("field_a", models.CharField(max_length=10)),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("tests.nonsymrelationbase",),
        ),
        migrations.CreateModel(
            name="NonSymRelationB",
            fields=[
                (
                    "nonsymrelationbase_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.nonsymrelationbase",
                    ),
                ),
                ("field_b", models.CharField(max_length=10)),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("tests.nonsymrelationbase",),
        ),
        migrations.CreateModel(
            name="NonSymRelationBC",
            fields=[
                (
                    "nonsymrelationbase_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.nonsymrelationbase",
                    ),
                ),
                ("field_c", models.CharField(max_length=10)),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("tests.nonsymrelationbase",),
        ),
        migrations.CreateModel(
            name="AltChildAsBaseModel",
            fields=[
                (
                    "altchildmodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.altchildmodel",
                    ),
                ),
                ("more_name", models.CharField(max_length=10)),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("tests.altchildmodel",),
        ),
        migrations.CreateModel(
            name="AltChildWithM2MModel",
            fields=[
                (
                    "altchildmodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.altchildmodel",
                    ),
                ),
                ("m2m", models.ManyToManyField(to="tests.plaina")),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("tests.altchildmodel",),
        ),
    ]
