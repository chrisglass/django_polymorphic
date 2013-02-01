# -*- coding: utf-8 -*-
""" QuerySet for PolymorphicModel
    Please see README.rst or DOCS.rst or http://bserve.webhop.org/wiki/django_polymorphic
"""

from compatibility_tools import defaultdict

from django.db import connections
from django.db.models.query import QuerySet, get_klass_info, get_cached_row
from django.contrib.contenttypes.models import ContentType

from query_translate import translate_polymorphic_filter_definitions_in_kwargs, translate_polymorphic_filter_definitions_in_args
from query_translate import translate_polymorphic_field_path

# chunk-size: maximum number of objects requested per db-request
# by the polymorphic queryset.iterator() implementation; we use the same chunk size as Django
from django.db.models.query import CHUNK_SIZE               # this is 100 for Django 1.1/1.2
Polymorphic_QuerySet_objects_per_request = CHUNK_SIZE


###################################################################################


from django.db.backends import util
from django.db.models.query_utils import DeferredAttribute


class BulkDeferredAttribute(DeferredAttribute):
    def __get__(self, instance, owner):
        """
        Retrieves and caches the value from the datastore on the first lookup.
        Returns the cached value.
        """
        assert instance is not None
        cls = self.model_ref()
        data = instance.__dict__
        if data.get(self.field_name, self) is self:
            fields = {}
            for field in cls._meta.fields:
                field_name = field.attname
                if isinstance(instance.__class__.__dict__.get(field_name), BulkDeferredAttribute):
                    fields[field_name] = field.name
            # We use only() instead of values() here because we want the
            # various data coersion methods (to_python(), etc.) to be called
            # here.
            if fields and self.field_name in fields:
                try:
                    obj = cls.base_objects.filter(pk=instance.pk).only(*fields.values()).using(
                            instance._state.db).get()
                except cls.DoesNotExist:
                    # re-create missing objects:
                    o = cls()
                    bo = instance
                    for k, v in bo.__dict__.items():
                        o.__dict__[k] = v
                    o.pk = bo.pk
                    obj = o
                for field_name in fields.keys():
                    val = getattr(obj, field_name)
                    data[field_name] = val
        return data[self.field_name]

    def __set__(self, instance, value):
        """
        Deferred loading attributes can be set normally (which means there will
        never be a database lookup involved.
        """
        cls = self.model_ref()
        for field in cls._meta.fields:
            if field.attname == self.field_name:
                if hasattr(field, '__set__'):
                    field.__set__(instance, value)
                    if hasattr(field, '__get__'):
                        value = field.__get__(instance, cls)
                break
        instance.__dict__[self.field_name] = value


def deferred_class_factory(model, attrs, bulk_attrs):
    """
    Returns a class object that is a copy of "model" with the specified "attrs"
    being replaced with BulkDeferredAttribute objects. The "pk_value" ties the
    deferred attributes to a particular instance of the model.
    """
    class Meta:
        proxy = True
        app_label = model._meta.app_label

    # The app_cache wants a unique name for each model, otherwise the new class
    # won't be created (we get an old one back). Therefore, we generate the
    # name using the passed in attrs. It's OK to reuse an existing class
    # object if the attrs are identical.
    name = "%s_Deferred_%s" % (model.__name__, '_'.join(sorted(list(attrs | bulk_attrs))))
    name = util.truncate_name(name, 80, 32)

    overrides = dict([(attr, BulkDeferredAttribute(attr, model))
            for attr in bulk_attrs - attrs])
    overrides.update(dict([(attr, DeferredAttribute(attr, model))
            for attr in attrs]))
    overrides["Meta"] = Meta
    overrides["__module__"] = model.__module__
    overrides["_deferred"] = True
    return type(name, (model,), overrides)

# The above function is also used to unpickle model instances with deferred
# fields.
deferred_class_factory.__safe_for_unpickling__ = True


###################################################################################
### PolymorphicQuerySet


class PolymorphicQuerySet(QuerySet):
    """
    QuerySet for PolymorphicModel

    Contains the core functionality for PolymorphicModel

    Usually not explicitly needed, except if a custom queryset class
    is to be used.
    """

    def __init__(self, *args, **kwargs):
        "init our queryset object member variables"
        super(PolymorphicQuerySet, self).__init__(*args, **kwargs)
        self.polymorphic_disabled = self.model.polymorphic_disabled
        self.deferred = False

    def _clone(self, *args, **kwargs):
        "Django's _clone only copies its own variables, so we need to copy ours here"
        new = super(PolymorphicQuerySet, self)._clone(*args, **kwargs)
        new.polymorphic_disabled = self.polymorphic_disabled
        new.deferred = self.deferred
        return new

    def defer(self, *fields):
        clone = self._clone()
        if fields == (None,):
            clone.deferred = False
        else:
            clone.deferred = True
        if fields:
            clone = super(PolymorphicQuerySet, clone).aggregate(*fields)
        return clone

    # FIXME: If django's delete() is patched to accept polymorphic queries, comment this method:
    # def delete(self, *args, **kwargs):
    #     """deletes the records in the current QuerySet.
    #     We need non-polymorphic object retrieval for aggregate => switch it off."""
    #     clone = self._clone()
    #     clone.polymorphic_disabled = True
    #     _polymorphic_disabled = clone.model.polymorphic_disabled
    #     clone.model.polymorphic_disabled = clone.polymorphic_disabled
    #     try:
    #         super(PolymorphicQuerySet, clone).delete(*args, **kwargs)
    #     finally:
    #         clone.model.polymorphic_disabled = _polymorphic_disabled

    def non_polymorphic(self, *args, **kwargs):
        """switch off polymorphic behaviour for this query.
        When the queryset is evaluated, only objects of the type of the
        base class used for this query are returned."""
        clone = self._clone()
        clone.polymorphic_disabled = True
        return clone

    def instance_of(self, *args):
        """Filter the queryset to only include the classes in args (and their subclasses).
        Implementation in _translate_polymorphic_filter_defnition."""
        return self.filter(instance_of=args)

    def not_instance_of(self, *args):
        """Filter the queryset to exclude the classes in args (and their subclasses).
        Implementation in _translate_polymorphic_filter_defnition."""
        return self.filter(not_instance_of=args)

    def _filter_or_exclude(self, negate, *args, **kwargs):
        "We override this internal Django functon as it is used for all filter member functions."
        translate_polymorphic_filter_definitions_in_args(self.model, args)  # the Q objects
        additional_args = translate_polymorphic_filter_definitions_in_kwargs(self.model, kwargs)  # filter_field='data'
        return super(PolymorphicQuerySet, self)._filter_or_exclude(negate, *(list(args) + additional_args), **kwargs)

    def order_by(self, *args, **kwargs):
        """translate the field paths in the args, then call vanilla order_by."""
        new_args = [translate_polymorphic_field_path(self.model, a) for a in args]
        return super(PolymorphicQuerySet, self).order_by(*new_args, **kwargs)

    def _process_aggregate_args(self, args, kwargs):
        """for aggregate and annotate kwargs: allow ModelX___field syntax for kwargs, forbid it for args.
        Modifies kwargs if needed (these are Aggregate objects, we translate the lookup member variable)"""
        for a in args:
            assert not '___' in a.lookup, 'PolymorphicModel: annotate()/aggregate(): ___ model lookup supported for keyword arguments only'
        for a in kwargs.values():
            a.lookup = translate_polymorphic_field_path(self.model, a.lookup)

    def annotate(self, *args, **kwargs):
        """translate the polymorphic field paths in the kwargs, then call vanilla annotate.
        _get_real_instances will do the rest of the job after executing the query."""
        self._process_aggregate_args(args, kwargs)
        return super(PolymorphicQuerySet, self).annotate(*args, **kwargs)

    def aggregate(self, *args, **kwargs):
        """translate the polymorphic field paths in the kwargs, then call vanilla aggregate.
        We need non-polymorphic object retrieval for aggregate => switch it off."""
        clone = self._clone()
        clone._process_aggregate_args(args, kwargs)
        clone.polymorphic_disabled = True
        return super(PolymorphicQuerySet, clone).aggregate(*args, **kwargs)

    # Since django_polymorphic 'V1.0 beta2', extra() always returns polymorphic results.^
    # The resulting objects are required to have a unique primary key within the result set
    # (otherwise an error is thrown).
    # The "polymorphic" keyword argument is not supported anymore.
    #def extra(self, *args, **kwargs):

    def _get_real_instances(self, base_result_objects):
        """
        Polymorphic object loader

        Does the same as:

            return [ o.get_real_instance() for o in base_result_objects ]

        but more efficiently.

        The list base_result_objects contains the objects from the executed
        base class query. The class of all of them is self.model (our base model).

        Some, many or all of these objects were not created and stored as
        class self.model, but as a class derived from self.model. We want to re-fetch
        these objects from the db as their original class so we can return them
        just as they were created/saved.

        We identify these objects by looking at o.polymorphic_ctype, which specifies
        the real class of these objects (the class at the time they were saved).

        First, we sort the result objects in base_result_objects for their
        subclass (from o.polymorphic_ctype), and then we execute one db query per
        subclass of objects. Here, we handle any annotations from annotate().

        Finally we re-sort the resulting objects into the correct order and
        return them as a list.
        """
        ordered_id_list = []    # list of ids of result-objects in correct order
        results = {}            # polymorphic dict of result-objects, keyed with their id (no order)

        # dict contains one entry per unique model type occurring in result,
        # in the format idlist_per_model[modelclass]=[list-of-object-ids]
        idlist_per_model = defaultdict(list)

        # - sort base_result_object ids into idlist_per_model lists, depending on their real class;
        # - also record the correct result order in "ordered_id_list"
        # - store objects that already have the correct class into "results"
        base_result_objects_by_id = {}
        self_model_content_type_id = ContentType.objects.get_for_proxied_model(self.model).pk
        self_model_unproxied_content_type_id = ContentType.objects.get_for_model(self.model).pk
        for base_object in base_result_objects:
            ordered_id_list.append(base_object.pk)

            # # check if id of the result object occures more than once - this can happen e.g. with base_objects.extra(tables=...)
            # assert base_object.pk not in base_result_objects_by_id, (
            #     "django_polymorphic: result objects do not have unique primary keys - model " + unicode(self.model)
            # )

            if base_object.pk not in base_result_objects_by_id:
                base_result_objects_by_id[base_object.pk] = base_object

                # this object is not a derived object and already the real instance => store it right away
                if (base_object.polymorphic_ctype_id == self_model_content_type_id):
                    results[base_object.pk] = base_object

                else:
                    modelclass = base_object.get_real_instance_class()

                    # this object is a proxied object of the real instence and already has all the data it needs
                    if (ContentType.objects.get_for_model(modelclass).pk == self_model_unproxied_content_type_id):
                        o = modelclass()
                        for k, v in base_object.__dict__.items():
                            o.__dict__[k] = v

                        results[base_object.pk] = o

                    # this object is derived and its real instance needs to be retrieved
                    # => store it's id into the bin for this model type
                    else:
                        idlist_per_model[modelclass].append(base_object.pk)

        # django's automatic ".pk" field does not always work correctly for
        # custom fields in derived objects (unclear yet who to put the blame on).
        # We get different type(o.pk) in this case.
        # We work around this by using the real name of the field directly
        # for accessing the primary key of the the derived objects.
        # We might assume that self.model._meta.pk.name gives us the name of the primary key field,
        # but it doesn't. Therefore we use polymorphic_primary_key_name, which we set up in base.py.
        pk_name = self.model.polymorphic_primary_key_name

        # For each model in "idlist_per_model" request its objects (the real model)
        # from the db and store them in results[].
        # Then we copy the annotate fields from the base objects to the real objects.
        # Then we copy the extra() select fields from the base objects to the real objects.
        # TODO: defer(), only(): support for these would be around here
        for modelclass, idlist in idlist_per_model.items():
            if self.deferred:
                attrs = set(f.attname for f in modelclass._meta.fields) - set([f.attname for f in self.model._meta.fields])
                attrs.remove(modelclass._meta.pk.attname)
                deferred_modelclass = deferred_class_factory(modelclass, set(), attrs)
                for o_pk in idlist:
                    bo = base_result_objects_by_id[o_pk]

                    if bo._deferred:
                        if bo.__class__._meta.proxy_for_model == modelclass:
                            results[o_pk] = bo
                            continue  # Skip already deferred objects of the same class

                    o = deferred_modelclass()

                    for k, v in bo.__dict__.items():
                        o.__dict__[k] = v
                    o.pk = bo.pk

                    if self.query.aggregates:
                        for anno_field_name in self.query.aggregates.keys():
                            attr = getattr(bo, anno_field_name)
                            setattr(o, anno_field_name, attr)

                    if self.query.extra_select:
                        for select_field_name in self.query.extra_select.keys():
                            attr = getattr(bo, select_field_name)
                            setattr(o, select_field_name, attr)

                    results[o_pk] = o
            else:
                qs = modelclass.base_objects.filter(pk__in=idlist)  # use pk__in instead ####
                qs.dup_select_related(self)  # copy select related configuration to new qs

                for o in qs:
                    o_pk = getattr(o, pk_name)
                    bo = base_result_objects_by_id[o_pk]

                    if self.query.aggregates:
                        for anno_field_name in self.query.aggregates.keys():
                            attr = getattr(bo, anno_field_name)
                            setattr(o, anno_field_name, attr)

                    if self.query.extra_select:
                        for select_field_name in self.query.extra_select.keys():
                            attr = getattr(bo, select_field_name)
                            setattr(o, select_field_name, attr)

                    results[o_pk] = o

            # re-create missing objects:
            for o_pk in idlist:
                if o_pk not in results:
                    o = modelclass()
                    bo = base_result_objects_by_id[o_pk]

                    for k, v in bo.__dict__.items():
                        o.__dict__[k] = v
                    o.pk = bo.pk

                    if self.query.aggregates:
                        for anno_field_name in self.query.aggregates.keys():
                            attr = getattr(bo, anno_field_name)
                            setattr(o, anno_field_name, attr)

                    if self.query.extra_select:
                        for select_field_name in self.query.extra_select.keys():
                            attr = getattr(bo, select_field_name)
                            setattr(o, select_field_name, attr)

                    results[o_pk] = o

        # re-create correct order and return result list
        resultlist = [results[ordered_id] for ordered_id in ordered_id_list if ordered_id in results]

        # set polymorphic_annotate_names in all objects (currently just used for debugging/printing)
        if self.query.aggregates:
            annotate_names = self.query.aggregates.keys()  # get annotate field list
            for o in resultlist:
                o.polymorphic_annotate_names = annotate_names

        # set polymorphic_extra_select_names in all objects (currently just used for debugging/printing)
        if self.query.extra_select:
            extra_select_names = self.query.extra_select.keys()  # get extra select field list
            for o in resultlist:
                o.polymorphic_extra_select_names = extra_select_names

        return resultlist

    def _iterator(self):
        """
        An iterator over the results from applying this QuerySet to the
        database.
        """
        fill_cache = False
        if connections[self.db].features.supports_select_related:
            fill_cache = self.query.select_related
        if isinstance(fill_cache, dict):
            requested = fill_cache
        else:
            requested = None
        max_depth = self.query.max_depth

        extra_select = self.query.extra_select.keys()
        aggregate_select = self.query.aggregate_select.keys()

        only_load = self.query.get_loaded_field_names()
        if not fill_cache:
            fields = self.model._meta.fields

        load_fields = []
        # If only/defer clauses have been specified,
        # build the list of fields that are to be loaded.
        if only_load:
            for field, model in self.model._meta.get_fields_with_model():
                if model is None:
                    model = self.model
                try:
                    if field.name in only_load[model]:
                        # Add a field that has been explicitly included
                        load_fields.append(field.name)
                except KeyError:
                    # Model wasn't explicitly listed in the only_load table
                    # Therefore, we need to load all fields from this model
                    load_fields.append(field.name)

        index_start = len(extra_select)
        aggregate_start = index_start + len(load_fields or self.model._meta.fields)

        skip = None
        if not fill_cache:
            skip = set()
            # Some fields have been deferred, so we have to initialise
            # via keyword arguments.
            init_list = []
            for idx, field in enumerate(fields):
                if load_fields and field.name not in load_fields:
                    skip.add(field.attname)
                else:
                    init_list.append(field.attname)
            deferred_classes = {}

        # Cache db and model outside the loop
        db = self.db
        compiler = self.query.get_compiler(using=db)
        if fill_cache:
            klass_info = get_klass_info(self.model, max_depth=max_depth,
                                        requested=requested, only_load=only_load)
        for row in compiler.results_iter():
            if fill_cache:
                obj, _ = get_cached_row(row, index_start, db, klass_info,
                                        offset=len(aggregate_select))
            else:
                kwargs = dict(zip(init_list, row[index_start:aggregate_start]))
                # Get the polymorphic child model class
                model = ContentType.objects.get_for_id(kwargs['polymorphic_ctype_id']).model_class()
                # Find out what fields belong to the polymorphic child class and bulk defer them
                bulk_skip = set(f.attname for f in model._meta.fields) - set([f.attname for f in self.model._meta.fields])
                if model._meta.pk.attname in bulk_skip:
                    bulk_skip.remove(model._meta.pk.attname)
                if skip or bulk_skip:
                    if model in deferred_classes:
                        model_cls = deferred_classes[model]
                    else:
                        model_cls = deferred_class_factory(model, skip, bulk_skip)
                        deferred_classes[model] = model_cls
                else:
                    # Omit aggregates in object creation.
                    model_cls = model

                kwargs[model._meta.pk.attname] = kwargs[self.model._meta.pk.attname]

                obj = model_cls(**kwargs)

                # Models keep a track of modified attrs to choose which
                # fields to save. Since we're just pulling from the
                # database, nothing has changed yet.
                obj._reset_modified_attrs()

                # Store the source database of the object
                obj._state.db = db
                # This object came from the database; it's not being added.
                obj._state.adding = False

            if extra_select:
                for i, k in enumerate(extra_select):
                    setattr(obj, k, row[i])

            # Add the aggregates to the model
            if aggregate_select:
                for i, aggregate in enumerate(aggregate_select):
                    setattr(obj, aggregate, row[i + aggregate_start])

            yield obj

    def iterator(self):
        """
        This function is used by Django for all object retrieval.
        By overriding it, we modify the objects that this queryset returns
        when it is evaluated (or its get method or other object-returning methods are called).

        Here we do the same as:

            base_result_objects=list(super(PolymorphicQuerySet, self).iterator())
            real_results=self._get_real_instances(base_result_objects)
            for o in real_results: yield o

        but it requests the objects in chunks from the database,
        with Polymorphic_QuerySet_objects_per_request per chunk
        """
        # disabled => work just like a normal queryset
        if self.polymorphic_disabled:
            base_iter = super(PolymorphicQuerySet, self).iterator()

            for o in base_iter:
                yield o
            raise StopIteration

        while True:
            base_iter = self._iterator()

            base_result_objects = []
            reached_end = False

            for i in range(Polymorphic_QuerySet_objects_per_request):
                try:
                    o = base_iter.next()
                    base_result_objects.append(o)
                except StopIteration:
                    reached_end = True
                    break

            real_results = self._get_real_instances(base_result_objects)

            for o in real_results:
                yield o

            if reached_end:
                raise StopIteration

    def __repr__(self, *args, **kwargs):
        if self.model.polymorphic_query_multiline_output:
            result = [repr(o) for o in self.all()]
            return  '[ ' + ',\n  '.join(result) + ' ]'
        else:
            return super(PolymorphicQuerySet, self).__repr__(*args, **kwargs)

    class _p_list_class(list):
        def __repr__(self, *args, **kwargs):
            result = [repr(o) for o in self]
            return  '[ ' + ',\n  '.join(result) + ' ]'

    def get_real_instances(self, base_result_objects=None):
        "same as _get_real_instances, but make sure that __repr__ for ShowField... creates correct output"
        if not base_result_objects:
            base_result_objects = self
        olist = self._get_real_instances(base_result_objects)
        if not self.model.polymorphic_query_multiline_output:
            return olist
        clist = PolymorphicQuerySet._p_list_class(olist)
        return clist
