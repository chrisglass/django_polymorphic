"""
PolymorphicModel Meta Class
"""

import inspect
import os
import sys
import warnings

from django.db import models
from django.db.models.base import ModelBase

from .managers import PolymorphicManager
from .query import PolymorphicQuerySet

# PolymorphicQuerySet Q objects (and filter()) support these additional key words.
# These are forbidden as field names (a descriptive exception is raised)
POLYMORPHIC_SPECIAL_Q_KWORDS = ["instance_of", "not_instance_of"]

DUMPDATA_COMMAND = os.path.join("django", "core", "management", "commands", "dumpdata.py")


class ManagerInheritanceWarning(RuntimeWarning):
    pass


###################################################################################
# PolymorphicModel meta class


class PolymorphicModelBase(ModelBase):
    """
    Manager inheritance is a pretty complex topic which may need
    more thought regarding how this should be handled for polymorphic
    models.

    In any case, we probably should propagate 'objects' and 'base_objects'
    from PolymorphicModel to every subclass. We also want to somehow
    inherit/propagate _default_manager as well, as it needs to be polymorphic.

    The current implementation below is an experiment to solve this
    problem with a very simplistic approach: We unconditionally
    inherit/propagate any and all managers (using _copy_to_model),
    as long as they are defined on polymorphic models
    (the others are left alone).

    Like Django ModelBase, we special-case _default_manager:
    if there are any user-defined managers, it is set to the first of these.

    We also require that _default_manager as well as any user defined
    polymorphic managers produce querysets that are derived from
    PolymorphicQuerySet.
    """

    def __new__(self, model_name, bases, attrs, **kwargs):
        # Workaround compatibility issue with six.with_metaclass() and custom Django model metaclasses:
        if not attrs and model_name == "NewBase":
            return super().__new__(self, model_name, bases, attrs, **kwargs)

        # create new model
        new_class = self.call_superclass_new_method(model_name, bases, attrs, **kwargs)

        # check if the model fields are all allowed
        self.validate_model_fields(new_class)

        # validate resulting default manager
        if not new_class._meta.abstract and not new_class._meta.swapped:
            self.validate_model_manager(new_class.objects, model_name, "objects")

        # for __init__ function of this class (monkeypatching inheritance accessors)
        new_class.polymorphic_super_sub_accessors_replaced = False

        # determine the name of the primary key field and store it into the class variable
        # polymorphic_primary_key_name (it is needed by query.py)
        for f in new_class._meta.fields:
            if f.primary_key and not isinstance(f, models.OneToOneField):
                new_class.polymorphic_primary_key_name = f.name
                break

        return new_class

    @classmethod
    def call_superclass_new_method(self, model_name, bases, attrs, **kwargs):
        """call __new__ method of super class and return the newly created class.
        Also work around a limitation in Django's ModelBase."""
        # There seems to be a general limitation in Django's app_label handling
        # regarding abstract models (in ModelBase). See issue 1 on github - TODO: propose patch for Django
        # We run into this problem if polymorphic.py is located in a top-level directory
        # which is directly in the python path. To work around this we temporarily set
        # app_label here for PolymorphicModel.
        meta = attrs.get("Meta", None)
        do_app_label_workaround = (
            meta
            and attrs["__module__"] == "polymorphic"
            and model_name == "PolymorphicModel"
            and getattr(meta, "app_label", None) is None
        )

        if do_app_label_workaround:
            meta.app_label = "poly_dummy_app_label"
        new_class = super().__new__(self, model_name, bases, attrs, **kwargs)
        if do_app_label_workaround:
            del meta.app_label
        return new_class

    @classmethod
    def validate_model_fields(self, new_class):
        "check if all fields names are allowed (i.e. not in POLYMORPHIC_SPECIAL_Q_KWORDS)"
        for f in new_class._meta.fields:
            if f.name in POLYMORPHIC_SPECIAL_Q_KWORDS:
                raise AssertionError(
                    f'PolymorphicModel: "{new_class.__name__}" - '
                    f'field name "{f.name}" is not allowed in polymorphic models'
                )

    @classmethod
    def validate_model_manager(self, manager, model_name, manager_name):
        """check if the manager is derived from PolymorphicManager
        and its querysets from PolymorphicQuerySet - throw AssertionError if not"""

        if not issubclass(type(manager), PolymorphicManager):
            extra = ""
            e = (
                f'PolymorphicModel: "{model_name}.{manager_name}" manager is of type "{type(manager).__name__}", '
                f"but must be a subclass of PolymorphicManager.{extra} to support retrieving subclasses"
            )
            warnings.warn(e, ManagerInheritanceWarning, stacklevel=3)
            return manager

        if not getattr(manager, "queryset_class", None) or not issubclass(
            manager.queryset_class, PolymorphicQuerySet
        ):
            e = (
                f'PolymorphicModel: "{model_name}.{manager_name}" has been instantiated with a queryset class '
                f"which is not a subclass of PolymorphicQuerySet (which is required)"
            )
            warnings.warn(e, ManagerInheritanceWarning, stacklevel=3)
        return manager

    @property
    def base_objects(self):
        warnings.warn(
            "Using PolymorphicModel.base_objects is deprecated.\n"
            f"Use {self.__class__.__name__}.objects.non_polymorphic() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._base_objects

    @property
    def _base_objects(self):
        # Create a manager so the API works as expected. Just don't register it
        # anymore in the Model Meta, so it doesn't substitute our polymorphic
        # manager as default manager for the third level of inheritance when
        # that third level doesn't define a manager at all.
        manager = models.Manager()
        manager.name = "base_objects"
        manager.model = self
        return manager

    @property
    def _default_manager(self):
        if len(sys.argv) > 1 and sys.argv[1] == "dumpdata":
            # TODO: investigate Django how this can be avoided
            # hack: a small patch to Django would be a better solution.
            # Django's management command 'dumpdata' relies on non-polymorphic
            # behaviour of the _default_manager. Therefore, we catch any access to _default_manager
            # here and return the non-polymorphic default manager instead if we are called from 'dumpdata.py'
            # Otherwise, the base objects will be upcasted to polymorphic models, and be outputted as such.
            # (non-polymorphic default manager is 'base_objects' for polymorphic models).
            # This way we don't need to patch django.core.management.commands.dumpdata
            # for all supported Django versions.
            frm = inspect.stack()[1]  # frm[1] is caller file name, frm[3] is caller function name
            if DUMPDATA_COMMAND in frm[1]:
                return self._base_objects

        manager = super()._default_manager
        if not isinstance(manager, PolymorphicManager):
            warnings.warn(
                f"{self.__class__.__name__}._default_manager is not a PolymorphicManager",
                ManagerInheritanceWarning,
            )

        return manager
