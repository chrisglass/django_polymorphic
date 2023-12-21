"""
QuerySet for PolymorphicModel
"""
import copy
from collections import defaultdict

from django import get_version as get_django_version
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db.models import FilteredRelation
from django.db.models.query import ModelIterable, Q, QuerySet

from .query_translate import (
    translate_polymorphic_field_path,
    translate_polymorphic_filter_definitions_in_args,
    translate_polymorphic_filter_definitions_in_kwargs,
    translate_polymorphic_Q_object,
)

# chunk-size: maximum number of objects requested per db-request
# by the polymorphic queryset.iterator() implementation
Polymorphic_QuerySet_objects_per_request = 100


class PolymorphicModelIterable(ModelIterable):
    """
    ModelIterable for PolymorphicModel

    Yields real instances if qs.polymorphic_disabled is False,
    otherwise acts like a regular ModelIterable.
    """

    def __iter__(self):
        base_iter = super().__iter__()
        if self.queryset.polymorphic_disabled:
            return base_iter
        return self._polymorphic_iterator(base_iter)

    def _polymorphic_iterator(self, base_iter):
        """
        Here we do the same as::

            real_results = queryset._get_real_instances(list(base_iter))
            for o in real_results: yield o

        but it requests the objects in chunks from the database,
        with Polymorphic_QuerySet_objects_per_request per chunk
        """
        while True:
            base_result_objects = []
            reached_end = False

            # Make sure the base iterator is read in chunks instead of
            # reading it completely, in case our caller read only a few objects.
            for i in range(Polymorphic_QuerySet_objects_per_request):
                try:
                    o = next(base_iter)
                    base_result_objects.append(o)
                except StopIteration:
                    reached_end = True
                    break

            real_results = self.queryset._get_real_instances(base_result_objects)

            for o in real_results:
                yield o

            if reached_end:
                return


def transmogrify(cls, obj):
    """
    Upcast a class to a different type without asking questions.
    """
    if "__init__" not in obj.__dict__:
        # Just assign __class__ to a different value.
        new = obj
        new.__class__ = cls
    else:
        # Run constructor, reassign values
        new = cls()
        for k, v in obj.__dict__.items():
            new.__dict__[k] = v
    return new


###################################################################################
# PolymorphicQuerySet


class PolymorphicQuerySet(QuerySet):
    """
    QuerySet for PolymorphicModel

    Contains the core functionality for PolymorphicModel

    Usually not explicitly needed, except if a custom queryset class
    is to be used.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._iterable_class = PolymorphicModelIterable

        self.polymorphic_disabled = False
        # A parallel structure to django.db.models.query.Query.deferred_loading,
        # which we maintain with the untranslated field names passed to
        # .defer() and .only() in order to be able to retranslate them when
        # retrieving the real instance (so that the deferred fields apply
        # to that queryset as well).
        self.polymorphic_deferred_loading = (set(), True)

        self._polymorphic_select_related = {}
        self._polymorphic_prefetch_related = {}
        self._polymorphic_custom_queryset = {}

    def _clone(self, *args, **kwargs):
        # Django's _clone only copies its own variables, so we need to copy ours here
        new = super()._clone(*args, **kwargs)
        new.polymorphic_disabled = self.polymorphic_disabled
        new.polymorphic_deferred_loading = (
            copy.copy(self.polymorphic_deferred_loading[0]),
            self.polymorphic_deferred_loading[1],
        )
        new._polymorphic_select_related = copy.copy(self._polymorphic_select_related)
        new._polymorphic_prefetch_related = copy.copy(self._polymorphic_prefetch_related)
        new._polymorphic_custom_queryset = copy.copy(self._polymorphic_custom_queryset)
        return new

    def as_manager(cls):
        from .managers import PolymorphicManager

        manager = PolymorphicManager.from_queryset(cls)()
        manager._built_with_as_manager = True
        return manager

    as_manager.queryset_only = True
    as_manager = classmethod(as_manager)

    def bulk_create(self, objs, batch_size=None, ignore_conflicts=False):
        objs = list(objs)
        for obj in objs:
            obj.pre_save_polymorphic()
        return super().bulk_create(objs, batch_size, ignore_conflicts=ignore_conflicts)

    def non_polymorphic(self):
        """switch off polymorphic behaviour for this query.
        When the queryset is evaluated, only objects of the type of the
        base class used for this query are returned."""
        qs = self._clone()
        qs.polymorphic_disabled = True
        if issubclass(qs._iterable_class, PolymorphicModelIterable):
            qs._iterable_class = ModelIterable
        return qs

    def instance_of(self, *args):
        """Filter the queryset to only include the classes in args (and their subclasses)."""
        # Implementation in _translate_polymorphic_filter_defnition.
        return self.filter(instance_of=args)

    def not_instance_of(self, *args):
        """Filter the queryset to exclude the classes in args (and their subclasses)."""
        # Implementation in _translate_polymorphic_filter_defnition."""
        return self.filter(not_instance_of=args)

    # Makes _filter_or_exclude compatible with the change in signature introduced in django at 9c9a3fe
    if get_django_version() >= "3.2":

        def _filter_or_exclude(self, negate, args, kwargs):
            # We override this internal Django function as it is used for all filter member functions.
            q_objects = translate_polymorphic_filter_definitions_in_args(
                queryset_model=self.model, args=args, using=self.db
            )
            # filter_field='data'
            additional_args = translate_polymorphic_filter_definitions_in_kwargs(
                queryset_model=self.model, kwargs=kwargs, using=self.db
            )
            args = list(q_objects) + additional_args
            return super()._filter_or_exclude(negate=negate, args=args, kwargs=kwargs)

    else:

        def _filter_or_exclude(self, negate, *args, **kwargs):
            # We override this internal Django function as it is used for all filter member functions.
            q_objects = translate_polymorphic_filter_definitions_in_args(
                self.model, args, using=self.db
            )
            # filter_field='data'
            additional_args = translate_polymorphic_filter_definitions_in_kwargs(
                self.model, kwargs, using=self.db
            )
            return super()._filter_or_exclude(
                negate, *(list(q_objects) + additional_args), **kwargs
            )

    def order_by(self, *field_names):
        """translate the field paths in the args, then call vanilla order_by."""
        field_names = [
            translate_polymorphic_field_path(self.model, a)
            if isinstance(a, str)
            else a  # allow expressions to pass unchanged
            for a in field_names
        ]
        return super().order_by(*field_names)

    def defer(self, *fields):
        """
        Translate the field paths in the args, then call vanilla defer.

        Also retain a copy of the original fields passed, which we'll need
        when we're retrieving the real instance (since we'll need to translate
        them again, as the model will have changed).
        """
        new_fields = [translate_polymorphic_field_path(self.model, a) for a in fields]
        clone = super().defer(*new_fields)
        clone._polymorphic_add_deferred_loading(fields)
        return clone

    def only(self, *fields):
        """
        Translate the field paths in the args, then call vanilla only.

        Also retain a copy of the original fields passed, which we'll need
        when we're retrieving the real instance (since we'll need to translate
        them again, as the model will have changed).
        """
        new_fields = [translate_polymorphic_field_path(self.model, a) for a in fields]
        clone = super().only(*new_fields)
        clone._polymorphic_add_immediate_loading(fields)
        return clone

    def _polymorphic_add_deferred_loading(self, field_names):
        """
        Follows the logic of django.db.models.query.Query.add_deferred_loading(),
        but for the non-translated field names that were passed to self.defer().
        """
        existing, defer = self.polymorphic_deferred_loading
        if defer:
            # Add to existing deferred names.
            self.polymorphic_deferred_loading = existing.union(field_names), True
        else:
            # Remove names from the set of any existing "immediate load" names.
            self.polymorphic_deferred_loading = existing.difference(field_names), False

    def _polymorphic_add_immediate_loading(self, field_names):
        """
        Follows the logic of django.db.models.query.Query.add_immediate_loading(),
        but for the non-translated field names that were passed to self.only()
        """
        existing, defer = self.polymorphic_deferred_loading
        field_names = set(field_names)
        if "pk" in field_names:
            field_names.remove("pk")
            field_names.add(self.model._meta.pk.name)

        if defer:
            # Remove any existing deferred names from the current set before
            # setting the new names.
            self.polymorphic_deferred_loading = field_names.difference(existing), False
        else:
            # Replace any existing "immediate load" field names.
            self.polymorphic_deferred_loading = field_names, False

    def _process_aggregate_args(self, args, kwargs):
        """for aggregate and annotate kwargs: allow ModelX___field syntax for kwargs, forbid it for args.
        Modifies kwargs if needed (these are Aggregate objects, we translate the lookup member variable)
        """
        ___lookup_assert_msg = "PolymorphicModel: annotate()/aggregate(): ___ model lookup supported for keyword arguments only"

        def patch_lookup(a):
            # The field on which the aggregate operates is
            # stored inside a complex query expression.
            if isinstance(a, Q):
                translate_polymorphic_Q_object(self.model, a)
            elif isinstance(a, FilteredRelation):
                patch_lookup(a.condition)
            elif hasattr(a, "get_source_expressions"):
                for source_expression in a.get_source_expressions():
                    if source_expression is not None:
                        patch_lookup(source_expression)
            else:
                a.name = translate_polymorphic_field_path(self.model, a.name)

        def test___lookup(a):
            """*args might be complex expressions too in django 1.8 so
            the testing for a '___' is rather complex on this one"""
            if isinstance(a, Q):

                def tree_node_test___lookup(my_model, node):
                    "process all children of this Q node"
                    for i in range(len(node.children)):
                        child = node.children[i]

                        if type(child) == tuple:
                            # this Q object child is a tuple => a kwarg like Q( instance_of=ModelB )
                            assert "___" not in child[0], ___lookup_assert_msg
                        else:
                            # this Q object child is another Q object, recursively process this as well
                            tree_node_test___lookup(my_model, child)

                tree_node_test___lookup(self.model, a)
            elif hasattr(a, "get_source_expressions"):
                for source_expression in a.get_source_expressions():
                    test___lookup(source_expression)
            else:
                assert "___" not in a.name, ___lookup_assert_msg

        for a in args:
            test___lookup(a)
        for a in kwargs.values():
            patch_lookup(a)

    def annotate(self, *args, **kwargs):
        """translate the polymorphic field paths in the kwargs, then call vanilla annotate.
        _get_real_instances will do the rest of the job after executing the query."""
        self._process_aggregate_args(args, kwargs)
        return super().annotate(*args, **kwargs)

    def aggregate(self, *args, **kwargs):
        """translate the polymorphic field paths in the kwargs, then call vanilla aggregate.
        We need no polymorphic object retrieval for aggregate => switch it off."""
        self._process_aggregate_args(args, kwargs)
        qs = self.non_polymorphic()
        return super(PolymorphicQuerySet, qs).aggregate(*args, **kwargs)

    # Starting with Django 1.9, the copy returned by 'qs.values(...)' has the
    # same class as 'qs', so our polymorphic modifications would apply.
    # We want to leave values queries untouched, so we set 'polymorphic_disabled'.
    def _values(self, *args, **kwargs):
        clone = super()._values(*args, **kwargs)
        clone.polymorphic_disabled = True
        return clone

    # Since django_polymorphic 'V1.0 beta2', extra() always returns polymorphic results.
    # The resulting objects are required to have a unique primary key within the result set
    # (otherwise an error is thrown).
    # The "polymorphic" keyword argument is not supported anymore.
    # def extra(self, *args, **kwargs):

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
        resultlist = []  # polymorphic list of result-objects

        # dict contains one entry per unique model type occurring in result,
        # in the format idlist_per_model[modelclass]=[list-of-object-ids]
        idlist_per_model = defaultdict(list)
        indexlist_per_model = defaultdict(list)

        # django's automatic ".pk" field does not always work correctly for
        # custom fields in derived objects (unclear yet who to put the blame on).
        # We get different type(o.pk) in this case.
        # We work around this by using the real name of the field directly
        # for accessing the primary key of the the derived objects.
        # We might assume that self.model._meta.pk.name gives us the name of the primary key field,
        # but it doesn't. Therefore we use polymorphic_primary_key_name, which we set up in base.py.
        pk_name = self.model.polymorphic_primary_key_name

        # - sort base_result_object ids into idlist_per_model lists, depending on their real class;
        # - store objects that already have the correct class into "results"
        content_type_manager = ContentType.objects.db_manager(self.db)
        self_model_class_id = content_type_manager.get_for_model(
            self.model, for_concrete_model=False
        ).pk
        self_concrete_model_class_id = content_type_manager.get_for_model(
            self.model, for_concrete_model=True
        ).pk

        for i, base_object in enumerate(base_result_objects):
            if base_object.polymorphic_ctype_id == self_model_class_id:
                # Real class is exactly the same as base class, go straight to results
                resultlist.append(base_object)
            else:
                real_concrete_class = base_object.get_real_instance_class()
                real_concrete_class_id = base_object.get_real_concrete_instance_class_id()

                if real_concrete_class_id is None:
                    # Dealing with a stale content type
                    continue
                elif real_concrete_class_id == self_concrete_model_class_id:
                    # Real and base classes share the same concrete ancestor,
                    # upcast it and put it in the results
                    resultlist.append(transmogrify(real_concrete_class, base_object))
                else:
                    # This model has a concrete derived class, track it for bulk retrieval.
                    real_concrete_class = content_type_manager.get_for_id(
                        real_concrete_class_id
                    ).model_class()
                    idlist_per_model[real_concrete_class].append(getattr(base_object, pk_name))
                    indexlist_per_model[real_concrete_class].append((i, len(resultlist)))
                    resultlist.append(None)

        # For each model in "idlist_per_model" request its objects (the real model)
        # from the db and store them in results[].
        # Then we copy the annotate fields from the base objects to the real objects.
        # Then we copy the extra() select fields from the base objects to the real objects.
        # TODO: defer(), only(): support for these would be around here
        for real_concrete_class, idlist in idlist_per_model.items():
            indices = indexlist_per_model[real_concrete_class]
            if self._polymorphic_custom_queryset.get(real_concrete_class):
                real_objects = self._polymorphic_custom_queryset[real_concrete_class]
            else:
                real_objects = real_concrete_class._base_objects.db_manager(self.db)

            real_objects = real_objects.filter(
                **{("%s__in" % pk_name): idlist}
            )

            # copy select_related() fields from base objects to real objects
            real_objects.query.select_related = self.query.select_related

            # polymorphic select_related() fields if any
            if real_concrete_class in self._polymorphic_select_related:
                real_objects = real_objects.select_related(
                    *self._polymorphic_select_related[real_concrete_class]
                )

                # polymorphic prefetch related configuration to new qs
            if real_concrete_class in self._polymorphic_prefetch_related:
                real_objects = real_objects.prefetch_related(
                    *self._polymorphic_prefetch_related[real_concrete_class]
                )

            # Copy deferred fields configuration to the new queryset
            deferred_loading_fields = []
            existing_fields = self.polymorphic_deferred_loading[0]
            for field in existing_fields:
                try:
                    translated_field_name = translate_polymorphic_field_path(
                        real_concrete_class, field
                    )
                except AssertionError:
                    if "___" in field:
                        # The originally passed argument to .defer() or .only()
                        # was in the form Model2B___field2, where Model2B is
                        # now a superclass of real_concrete_class. Thus it's
                        # sufficient to just use the field name.
                        translated_field_name = field.rpartition("___")[-1]

                        # Check if the field does exist.
                        # Ignore deferred fields that don't exist in this subclass type.
                        try:
                            real_concrete_class._meta.get_field(translated_field_name)
                        except FieldDoesNotExist:
                            continue
                    else:
                        raise

                deferred_loading_fields.append(translated_field_name)
            real_objects.query.deferred_loading = (
                set(deferred_loading_fields),
                self.query.deferred_loading[1],
            )

            real_objects_dict = {
                getattr(real_object, pk_name): real_object for real_object in real_objects
            }

            for i, j in indices:
                base_object = base_result_objects[i]
                o_pk = getattr(base_object, pk_name)
                real_object = real_objects_dict.get(o_pk)
                if real_object is None:
                    continue

                # need shallow copy to avoid duplication in caches (see PR #353)
                real_object = copy.copy(real_object)
                real_class = real_object.get_real_instance_class()

                # If the real class is a proxy, upcast it
                if real_class != real_concrete_class:
                    real_object = transmogrify(real_class, real_object)

                if self.query.annotations:
                    for anno_field_name in self.query.annotations.keys():
                        attr = getattr(base_object, anno_field_name)
                        setattr(real_object, anno_field_name, attr)

                if self.query.extra_select:
                    for select_field_name in self.query.extra_select.keys():
                        attr = getattr(base_object, select_field_name)
                        setattr(real_object, select_field_name, attr)

                resultlist[j] = real_object

        resultlist = [i for i in resultlist if i]

        # set polymorphic_annotate_names in all objects (currently just used for debugging/printing)
        if self.query.annotations:
            # get annotate field list
            annotate_names = list(self.query.annotations.keys())
            for real_object in resultlist:
                real_object.polymorphic_annotate_names = annotate_names

        # set polymorphic_extra_select_names in all objects (currently just used for debugging/printing)
        if self.query.extra_select:
            # get extra select field list
            extra_select_names = list(self.query.extra_select.keys())
            for real_object in resultlist:
                real_object.polymorphic_extra_select_names = extra_select_names

        return resultlist

    def __repr__(self, *args, **kwargs):
        if self.model.polymorphic_query_multiline_output:
            result = [repr(o) for o in self.all()]
            return "[ " + ",\n  ".join(result) + " ]"
        else:
            return super().__repr__(*args, **kwargs)

    class _p_list_class(list):
        def __repr__(self, *args, **kwargs):
            result = [repr(o) for o in self]
            return "[ " + ",\n  ".join(result) + " ]"

    def get_real_instances(self, base_result_objects=None):
        """
        Cast a list of objects to their actual classes.

        This does roughly the same as::

            return [ o.get_real_instance() for o in base_result_objects ]

        but more efficiently.

        :rtype: PolymorphicQuerySet
        """
        "same as _get_real_instances, but make sure that __repr__ for ShowField... creates correct output"
        if base_result_objects is None:
            base_result_objects = self
        olist = self._get_real_instances(base_result_objects)
        if not self.model.polymorphic_query_multiline_output:
            return olist
        clist = PolymorphicQuerySet._p_list_class(olist)
        return clist

    def select_polymorphic_related(self, polymorphic_subclass, *fields):
        if self.query.select_related is True:
            raise ValueError(
                "select_polymorphic_related() cannot be used together with select_related=True"
            )
        clone = self._clone()
        clone._polymorphic_select_related[polymorphic_subclass] = fields
        return clone

    def prefetch_polymorphic_related(self, polymorphic_subclass, *lookups):
        clone = self._clone()
        clone._polymorphic_prefetch_related[polymorphic_subclass] = lookups
        return clone

    def custom_queryset(self, polymorphic_subclass, queryset):
        clone = self._clone()
        clone._polymorphic_custom_queryset[polymorphic_subclass] = queryset
        return clone
