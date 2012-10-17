# -*- coding: utf-8 -*-
""" PolymorphicModel Meta Class
    Please see README.rst or DOCS.rst or http://bserve.webhop.org/wiki/django_polymorphic
"""

import sys

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

from django.db import models
from django.db.models.base import ModelBase
from django.contrib.contenttypes.models import ContentType

from manager import PolymorphicManager
from query import PolymorphicQuerySet

# PolymorphicQuerySet Q objects (and filter()) support these additional key words.
# These are forbidden as field names (a descriptive exception is raised)
POLYMORPHIC_SPECIAL_Q_KWORDS = ['instance_of', 'not_instance_of']


###################################################################################
### PolymorphicModel meta class

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

    def __new__(self, model_name, bases, attrs):
        #print; print '###', model_name, '- bases:', bases

        # Setup as proxied model if possible
        parents = [b for b in bases if isinstance(b, ModelBase)]
        if parents:
            is_proxy = True

            if is_proxy:
                attr_meta = attrs.get('Meta', None)
                abstract = getattr(attr_meta, 'abstract', False)
                if abstract:
                    is_proxy = False

            if is_proxy:
                base = None
                for parent in [cls for cls in parents if hasattr(cls, '_meta')]:
                    if parent._meta.abstract:
                        if parent._meta.fields:
                            is_proxy = False  # Abstract parent classes with fields cannot be proxied
                            break
                    if base is not None:
                        is_proxy = False
                        break
                    else:
                        base = parent
                if base is None:
                    is_proxy = False

            if is_proxy:
                fields = [f for f in attrs.values() if isinstance(f, models.Field)]
                if fields:
                    is_proxy = False

            if is_proxy:
                if 'Meta' in attrs:
                    parent = (attrs['Meta'], object,)
                else:
                    parent = (object,)
                meta = type('Meta', parent, {'proxy': True})
                #print '** model %s proxied' % model_name
                attrs['Meta'] = meta

        # create new model
        new_class = self.call_superclass_new_method(model_name, bases, attrs)
        if not new_class._deferred:
            # check if the model fields are all allowed
            self.validate_model_fields(new_class)

            # create list of all managers to be inherited from the base classes
            inherited_managers = new_class.get_inherited_managers(attrs)

            # add the managers to the new model
            for source_name, mgr_name, manager in inherited_managers:
                #print '** add inherited manager from model %s, manager %s, %s' % (source_name, mgr_name, manager.__class__.__name__)
                new_manager = manager._copy_to_model(new_class)
                new_class.add_to_class(mgr_name, new_manager)

            # get first user defined manager; if there is one, make it the _default_manager
            user_manager = new_class.get_first_user_defined_manager()
            if user_manager:
                def_mgr = user_manager._copy_to_model(new_class)
                #print '## add default manager', type(def_mgr)
                new_class.add_to_class('_default_manager', def_mgr)
                new_class._default_manager._inherited = False   # the default mgr was defined by the user, not inherited

            # validate resulting default manager
            _default_manager = super(PolymorphicModelBase, new_class).__getattribute__('_default_manager')
            self.validate_model_manager(_default_manager, model_name, '_default_manager')

            # for __init__ function of this class (monkeypatching inheritance accessors)
            new_class.polymorphic_super_sub_accessors_replaced = False

            # determine the name of the primary key field and store it into the class variable
            # polymorphic_primary_key_name (it is needed by query.py)
            for f in new_class._meta.fields:
                if f.primary_key and type(f) != models.OneToOneField:
                    new_class.polymorphic_primary_key_name = f.name
                    break

        return new_class

    def get_inherited_managers(self, attrs):
        """
        Return list of all managers to be inherited/propagated from the base classes;
        use correct mro, only use managers with _inherited==False (they are of no use),
        skip managers that are overwritten by the user with same-named class attributes (in attrs)
        """
        add_managers = []
        add_managers_keys = set()
        for base in self.__mro__[1:]:
            if not issubclass(base, models.Model):
                continue
            if not getattr(base, 'polymorphic_model_marker', None):
                continue  # leave managers of non-polym. models alone

            for key, manager in base.__dict__.items():
                if type(manager) == models.manager.ManagerDescriptor:
                    manager = manager.manager
                if not isinstance(manager, models.Manager):
                    continue
                if key in ['_base_manager']:
                    continue       # let Django handle _base_manager
                if key in attrs:
                    continue
                if key in add_managers_keys:
                    continue       # manager with that name already added, skip
                if manager._inherited:
                    continue             # inherited managers (on the bases) have no significance, they are just copies
                #print >>sys.stderr,'##',self.__name__, key
                if isinstance(manager, PolymorphicManager):  # validate any inherited polymorphic managers
                    self.validate_model_manager(manager, self.__name__, key)
                add_managers.append((base.__name__, key, manager))
                add_managers_keys.add(key)
        return add_managers

    @classmethod
    def get_first_user_defined_manager(self):
        mgr_list = []
        for key, val in self.__dict__.items():
            item = getattr(self, key)
            if not isinstance(item, models.Manager):
                continue
            mgr_list.append((item.creation_counter, key, item))
        # if there are user defined managers, use first one as _default_manager
        if mgr_list:
            _, manager_name, manager = sorted(mgr_list)[0]
            #sys.stderr.write( '\n# first user defined manager for model "{model}":\n#  "{mgrname}": {mgr}\n#  manager model: {mgrmodel}\n\n'
            #    .format( model=model_name, mgrname=manager_name, mgr=manager, mgrmodel=manager.model ) )
            return manager
        return None

    @classmethod
    def call_superclass_new_method(self, model_name, bases, attrs):
        """call __new__ method of super class and return the newly created class.
        Also work around a limitation in Django's ModelBase."""
        # There seems to be a general limitation in Django's app_label handling
        # regarding abstract models (in ModelBase). See issue 1 on github - TODO: propose patch for Django
        # We run into this problem if polymorphic.py is located in a top-level directory
        # which is directly in the python path. To work around this we temporarily set
        # app_label here for PolymorphicModel.
        meta = attrs.get('Meta', None)
        model_module_name = attrs['__module__']
        do_app_label_workaround = (meta
                                    and model_module_name == 'polymorphic'
                                    and model_name == 'PolymorphicModel'
                                    and getattr(meta, 'app_label', None) is None)

        if do_app_label_workaround:
            meta.app_label = 'poly_dummy_app_label'
        new_class = super(PolymorphicModelBase, self).__new__(self, model_name, bases, attrs)
        if do_app_label_workaround:
            del(meta.app_label)
        return new_class

    def validate_model_fields(self):
        "check if all fields names are allowed (i.e. not in POLYMORPHIC_SPECIAL_Q_KWORDS)"
        for f in self._meta.fields:
            if f.name in POLYMORPHIC_SPECIAL_Q_KWORDS:
                e = 'PolymorphicModel: "%s" - field name "%s" is not allowed in polymorphic models'
                raise AssertionError(e % (self.__name__, f.name))

    @classmethod
    def validate_model_manager(self, manager, model_name, manager_name):
        """check if the manager is derived from PolymorphicManager
        and its querysets from PolymorphicQuerySet - throw AssertionError if not"""

        if not issubclass(type(manager), PolymorphicManager):
            e = 'PolymorphicModel: "' + model_name + '.' + manager_name + '" manager is of type "' + type(manager).__name__
            e += '", but must be a subclass of PolymorphicManager'
            raise AssertionError(e)
        if not getattr(manager, 'queryset_class', None) or not issubclass(manager.queryset_class, PolymorphicQuerySet):
            e = 'PolymorphicModel: "' + model_name + '.' + manager_name + '" (PolymorphicManager) has been instantiated with a queryset class which is'
            e += ' not a subclass of PolymorphicQuerySet (which is required)'
            raise AssertionError(e)
        return manager

    def __getattribute__(self, name):
        if name in ('_default_manager', '_base_manager'):
            if self.polymorphic_disabled:
                return self.base_objects
        return super(PolymorphicModelBase, self).__getattribute__(name)

    def __init__(self, *args, **kwargs):
        # hack: a small patch to Django would be a better solution.
        # Django's management command 'dumpdata' relies on non-polymorphic
        # behaviour of the _default_manager. Therefore, we disable all polymorphism
        # if the system command contains 'dumpdata'.
        # This way we don't need to patch django.core.management.commands.dumpdata
        # for all supported Django versions.
        # TODO: investigate Django how this can be avoided
        self.polymorphic_disabled = ('dumpdata' in sys.argv)
        super(PolymorphicModelBase, self).__init__(*args, **kwargs)

    _polymorphic_disabled = local()

    def _get_polymorphic_disabled(self):
        """Polymorphic behavior can be disabled for each model at any time by setting `polymorphic_disabled` to True."""
        return getattr(self.__class__._polymorphic_disabled, 'disabled', False)

    def _set_polymorphic_disabled(self, disabled):
        self.__class__._polymorphic_disabled.disabled = disabled

    polymorphic_disabled = property(_get_polymorphic_disabled, _set_polymorphic_disabled, doc=_get_polymorphic_disabled.__doc__)
