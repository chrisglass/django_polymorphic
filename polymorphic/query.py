"""
QuerySet for PolymorphicModel
"""

import copy
import functools
import operator
from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db.models import FilteredRelation, Manager
from django.db.models.constants import LOOKUP_SEP
from django.db.models.query import ModelIterable, Q, QuerySet
from django.db.models.query import BaseIterable, RelatedPopulator
from .query_translate import (
    translate_polymorphic_field_path,
    translate_polymorphic_filter_definitions_in_args,
    translate_polymorphic_filter_definitions_in_kwargs,
    translate_polymorphic_Q_object,
    _get_query_related_name,
    _get_all_sub_models,
    _create_base_path,
)

# chunk-size: maximum number of objects requested per db-request
# by the polymorphic queryset.iterator() implementation
Polymorphic_QuerySet_objects_per_request = 100


def merge_dicts(primary, secondary):
    """Deep merge two dicts

    Items from the primary dict are preserved in preference to those on the
    secondary dict"""

    for k, v in secondary.items():
        if k in primary:
            primary[k] = merge_dicts(primary[k], v)
        else:
            primary[k] = copy.deepcopy(v)
    return primary


def search_object_cache(obj, source_model, target_model):
    for search_part in _create_base_path(source_model, target_model).split("__"):
        try:
            obj = obj._state.fields_cache[search_part]
        except KeyError:
            return
    return obj


class VanillaRelatedPopulator(RelatedPopulator):
    def __init__(self, klass_info, select, db):
        super().__init__(klass_info, select, db)
        self.field = klass_info["field"]
        self.reverse = klass_info["reverse"]
        # replace replated populator with possibly a polymorphic version
        # this is needed for relation across a non poly model
        self.related_populators = get_related_populators(klass_info, select, self.db)

    def build_related(self, row, from_obj, *_):
        self.populate(row, from_obj)


class RelatedPolymorphicPopulator:
    """
    RelatedPopulator is used for select_related() object instantiation.
    The idea is that each select_related() model will be populated by a
    different RelatedPopulator instance. The RelatedPopulator instances get
    klass_info and select (computed in SQLCompiler) plus the used db as
    input for initialization. That data is used to compute which columns
    to use, how to instantiate the model, and how to populate the links
    between the objects.
    The actual creation of the objects is done in populate() method. This
    method gets row and from_obj as input and populates the select_related()
    model instance.
    """

    def __init__(self, klass_info, select, db):
        self.db = db
        # Pre-compute needed attributes. The attributes are:
        #  - model_cls: the possibly deferred model class to instantiate
        #  - either:
        #    - cols_start, cols_end: usually the columns in the row are
        #      in the same order model_cls.__init__ expects them, so we
        #      can instantiate by model_cls(*row[cols_start:cols_end])
        #    - reorder_for_init: When select_related descends to a child
        #      class, then we want to reuse the already selected parent
        #      data. However, in this case the parent data isn't necessarily
        #      in the same order that Model.__init__ expects it to be, so
        #      we have to reorder the parent data. The reorder_for_init
        #      attribute contains a function used to reorder the field data
        #      in the order __init__ expects it.
        #  - pk_idx: the index of the primary key field in the reordered
        #    model data. Used to check if a related object exists at all.
        #  - init_list: the field attnames fetched from the database. For
        #    deferred models this isn't the same as all attnames of the
        #    model's fields.
        #  - related_populators: a list of RelatedPopulator instances if
        #    select_related() descends to related models from this model.
        #  - local_setter, remote_setter: Methods to set cached values on
        #    the object being populated and on the remote object. Usually
        #    these are Field.set_cached_value() methods.
        select_fields = klass_info["select_fields"]
        from_parent = klass_info["from_parent"]
        if not from_parent:
            self.cols_start = select_fields[0]
            self.cols_end = select_fields[-1] + 1
            self.init_list = [f[0].target.attname for f in select[self.cols_start : self.cols_end]]
            self.reorder_for_init = None
        else:
            attname_indexes = {select[idx][0].target.attname: idx for idx in select_fields}
            model_init_attnames = (f.attname for f in klass_info["model"]._meta.concrete_fields)
            self.init_list = [
                attname for attname in model_init_attnames if attname in attname_indexes
            ]
            self.reorder_for_init = operator.itemgetter(
                *[attname_indexes[attname] for attname in self.init_list]
            )

        self.model_cls = klass_info["model"]
        self.pk_idx = self.init_list.index(self.model_cls._meta.pk.attname)
        self.related_populators = get_related_populators(klass_info, select, self.db)
        self.local_setter = klass_info["local_setter"]
        self.remote_setter = klass_info["remote_setter"]
        self.field = klass_info["field"]
        self.reverse = klass_info["reverse"]
        self.content_type_manager = ContentType.objects.db_manager(self.db)
        self.model_class_id = self.content_type_manager.get_for_model(
            self.model_cls, for_concrete_model=False
        ).pk
        self.concrete_model_class_id = self.content_type_manager.get_for_model(
            self.model_cls, for_concrete_model=True
        ).pk

    def build_related(self, row, from_obj, post_actions):
        if self.reorder_for_init:
            obj_data = self.reorder_for_init(row)
        else:
            obj_data = row[self.cols_start : self.cols_end]

        if obj_data[self.pk_idx] is None:
            obj = None
        else:
            obj = self.model_cls.from_db(self.db, self.init_list, obj_data)
            self.post_build_modify(
                obj,
                from_obj,
                post_actions,
                functools.partial(self._populate, row, from_obj, post_actions),
            )

    def _populate(self, row, from_obj, post_actions, obj):
        for rel_iter in self.related_populators:
            rel_iter.build_related(row, obj, post_actions)

        self.local_setter(from_obj, obj)
        if obj is not None:
            self.remote_setter(obj, from_obj)

    def post_build_modify(self, base_object, from_obj, post_actions, populate_fn):
        if not hasattr(base_object, "polymorphic_ctype_id"):
            populate_fn(base_object)
        elif base_object.polymorphic_ctype_id == self.model_class_id:
            # Real class is exactly the same as base class, go straight to results
            populate_fn(base_object)
        else:
            real_concrete_class = base_object.get_real_instance_class()
            real_concrete_class_id = base_object.get_real_concrete_instance_class_id()

            if real_concrete_class_id is None:
                # Dealing with a stale content type
                populate_fn(None)
                return False
            elif real_concrete_class_id == self.concrete_model_class_id:
                # Real and base classes share the same concrete ancestor,
                # upcast it and put it in the results
                populate_fn(transmogrify(real_concrete_class, base_object))
                return False
            else:
                # This model has a concrete derived class: either track it for bulk
                # retrieval or if it is already fetched as part of a select_related
                # enable pivoting to that object
                real_concrete_class = self.content_type_manager.get_for_id(
                    real_concrete_class_id
                ).model_class()
                populate_fn(base_object)
                post_actions.append(
                    (
                        functools.partial(
                            self.pivot_onto_cached_subclass,
                            from_obj,
                            base_object,
                            real_concrete_class,
                        ),
                        populate_fn,
                    )
                )

    def pivot_onto_cached_subclass(self, from_obj, obj, model_target_cls):
        """Pivot to final polymorphic class.

        Pivot the object created from the base query onto the true polymorphic
        instance, we need to ensure that this is only done on objects that are
        from non parent-child type relationships.

        If we cannot pivot we return info to be used in the PolymorphicModelIterable
        to ensure the correct model loaded from the additional bulk queries
        """

        original = obj
        parents = model_target_cls()._get_inheritance_relation_fields_and_models()
        for cls in reversed(model_target_cls.mro()[: -len(self.model_cls.mro())]):
            for rel_iter in self.related_populators:
                if not isinstance(
                    rel_iter, (VanillaRelatedPopulator, RelatedPolymorphicPopulator)
                ):
                    # NOTE: We don't know how to handle this type of populator!
                    continue
                if rel_iter.reverse and rel_iter.model_cls is cls:
                    if rel_iter.field.name in parents.keys():
                        obj = getattr(obj, rel_iter.field.remote_field.name)

        if not isinstance(obj, model_target_cls):
            # This allow pivoting of object that are descendants of the original field
            if not original._meta.get_path_to_parent(from_obj._meta.model):
                obj = search_object_cache(original, original._meta.model, model_target_cls)

        if isinstance(obj, model_target_cls):
            # We only want to pivot onto a field from a different object, ie not a parent/child
            # relationship as this will break the cache and other object
            if not original._meta.get_path_to_parent(from_obj._meta.model):
                self.local_setter(from_obj, obj)
                if obj is not None:
                    self.remote_setter(obj, from_obj)
            return None, None

        pk_name = self.model_cls.polymorphic_primary_key_name
        return model_target_cls, (getattr(original, pk_name), self.field.name)


def get_related_populators(klass_info, select, db):
    from .models import PolymorphicModel

    iterators = []
    related_klass_infos = klass_info.get("related_klass_infos", [])
    for rel_klass_info in related_klass_infos:
        model = rel_klass_info["model"]
        rel_cls = VanillaRelatedPopulator(rel_klass_info, select, db)
        if issubclass(model, PolymorphicModel):
            rel_cls = RelatedPolymorphicPopulator(rel_klass_info, select, db)
        else:
            for col, *_ in select:
                if issubclass(col.target.model, PolymorphicModel):
                    rel_cls = RelatedPolymorphicPopulator(rel_klass_info, select, db)
                    break
        iterators.append(rel_cls)
    return iterators


class PolymorphicModelIterable(ModelIterable):
    """
    ModelIterable for PolymorphicModel

    Yields real instances if qs.polymorphic_disabled is False,
    otherwise acts like a regular ModelIterable. We inherit from
    ModelIterable non base BaseIterable even though we completely
    replace it, but this allows Django test in Prefetch to work
    """

    def __iter__(self):
        queryset = self.queryset
        db = queryset.db
        compiler = queryset.query.get_compiler(using=db)
        # Execute the query. This will also fill compiler.select, klass_info,
        # and annotations.
        results = compiler.execute_sql(
            chunked_fetch=self.chunked_fetch, chunk_size=self.chunk_size
        )
        select, klass_info, annotation_col_map = (
            compiler.select,
            compiler.klass_info,
            compiler.annotation_col_map,
        )
        model_cls = klass_info["model"]
        select_fields = klass_info["select_fields"]
        model_fields_start, model_fields_end = select_fields[0], select_fields[-1] + 1
        init_list = [f[0].target.attname for f in select[model_fields_start:model_fields_end]]
        related_populators = get_related_populators(klass_info, select, db)
        known_related_objects = [
            (
                field,
                related_objs,
                operator.attrgetter(
                    *[
                        (
                            field.attname
                            if from_field == "self"
                            else queryset.model._meta.get_field(from_field).attname
                        )
                        for from_field in field.from_fields
                    ]
                ),
            )
            for field, related_objs in queryset._known_related_objects.items()
        ]
        base_iter = compiler.results_iter(results)
        while True:
            result_objects = []
            base_result_objects = []
            reached_end = False

            # Make sure the base iterator is read in chunks instead of
            # reading it completely, in case our caller read only a few objects.
            post_actions = list()
            for i in range(Polymorphic_QuerySet_objects_per_request):
                # dict contains one entry per unique model type occurring in result,
                # in the format idlist_per_model[modelclass]=[list-of-object-ids]
                try:
                    row = next(base_iter)
                    obj = model_cls.from_db(
                        db, init_list, row[model_fields_start:model_fields_end]
                    )
                    for rel_populator in related_populators:
                        rel_populator.build_related(row, obj, post_actions)
                    base_result_objects.append([row, obj])
                except StopIteration:
                    reached_end = True
                    break

            if not self.queryset.polymorphic_disabled:
                self.fetch_polymorphic(post_actions, base_result_objects)

            for row, obj in base_result_objects:
                if annotation_col_map:
                    for attr_name, col_pos in annotation_col_map.items():
                        setattr(obj, attr_name, row[col_pos])

                # Add the known related objects to the model.
                for field, rel_objs, rel_getter in known_related_objects:
                    # Avoid overwriting objects loaded by, e.g., select_related().
                    if field.is_cached(obj):
                        continue
                    rel_obj_id = rel_getter(obj)
                    try:
                        rel_obj = rel_objs[rel_obj_id]
                    except KeyError:
                        pass  # May happen in qs1 | qs2 scenarios.
                    else:
                        setattr(obj, field.name, rel_obj)
                result_objects.append(obj)

            if not self.queryset.polymorphic_disabled:
                result_objects = self.queryset._get_real_instances(result_objects)

            for o in result_objects:
                yield o

            if reached_end:
                return

    def apply_select_related(self, qs, relations):
        if self.queryset.query.select_related is True:
            return qs.select_related()

        model_name = qs.model.__name__.lower()
        if isinstance(self.queryset.query.select_related, dict):
            select_related = {}
            if isinstance(qs.query.select_related, dict):
                select_related = qs.query.select_related
            for k, v in self.queryset.query.select_related.items():
                if k in relations:
                    if not isinstance(select_related, dict):
                        select_related = {}
                    if isinstance(v, dict):
                        if model_name in v:
                            select_related = merge_dicts(
                                select_related, v[model_name])
                        else:
                            for field in qs.model._meta.fields:
                                if field.name in v:
                                    select_related = merge_dicts(
                                        select_related, v[field.name])
                    else:
                        select_related = merge_dicts(select_related, v)
            qs.query.select_related = select_related
        return qs

    def fetch_polymorphic(self, post_actions, base_result_objects):
        update_fn_per_model = defaultdict(list)
        idlist_per_model = defaultdict(list)

        for action, populate_fn in post_actions:
            target_class, pk_info = action()
            if target_class:
                pk, name = pk_info
                idlist_per_model[target_class].append((pk, name))
                update_fn_per_model[target_class].append((populate_fn, pk))

        # For each model in "idlist_per_model" request its objects (the real model)
        # from the db and store them in results[].
        # Then we copy the annotate fields from the base objects to the real objects.
        # Then we copy the extra() select fields from the base objects to the real objects.
        # TODO: defer(), only(): support for these would be around here
        for real_concrete_class, data in idlist_per_model.items():
            idlist, names = zip(*data)
            updates = update_fn_per_model[real_concrete_class]
            pk_name = real_concrete_class.polymorphic_primary_key_name
            real_objects = real_concrete_class._base_objects.db_manager(self.queryset.db).filter(
                **{("%s__in" % pk_name): idlist}
            )

            real_objects = self.apply_select_related(real_objects, set(names))
            real_objects_dict = {
                getattr(real_object, pk_name): real_object for real_object in real_objects
            }

            for populate_fn, o_pk in updates:
                real_object = real_objects_dict.get(o_pk)
                if real_object is None:
                    continue

                # need shallow copy to avoid duplication in caches (see PR #353)
                real_object = copy.copy(real_object)
                real_class = real_object.get_real_instance_class()

                # If the real class is a proxy, upcast it
                if real_class != real_concrete_class:
                    real_object = transmogrify(real_class, real_object)

                populate_fn(real_object)


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


class PolymorphicQuerySetMixin(QuerySet):
    def select_related(self, *fields):
        if fields == (None,) or not len(fields):
            return super().select_related(*fields)
        field_with_poly = set(self.convert_related_fieldnames(fields))
        return super().select_related(*sorted(list(field_with_poly)))

    def _convert_field_name_part(self, field_parts, model):
        """
        recursively convert a fieldname into (model, filedname)
        """
        field = None
        part = field_parts[0]
        next_parts = field_parts[1:]
        field_path = []
        rel_model = None
        try:
            field = model._meta.get_field(part)
            field_path = [part]
            yield field_path

            if field.is_relation:
                rel_model = field.related_model
                if next_parts:
                    child_selectors = self._convert_field_name_part(next_parts, rel_model)
                    for selector in child_selectors:
                        yield field_path + selector
            else:
                rel_model = model
        except FieldDoesNotExist:
            submodels = _get_all_sub_models(model)
            if part == "*":
                for rel_model in submodels.values():
                    if model is rel_model:
                        continue
                    yield from self._convert_submodel_fields_parts(next_parts, model, rel_model)
            else:
                rel_model = submodels.get(part, None)
                if model is not rel_model:
                    yield from self._convert_submodel_fields_parts(next_parts, model, rel_model)
                else:
                    raise

    def _convert_submodel_fields_parts(self, field_parts, model, rel_model):
        field_path = list(_create_base_path(model, rel_model).split("__"))
        for field_part_idx in range(0, len(field_path)):
            yield field_path[0 : 1 + field_part_idx]
        yield field_path
        if field_parts:
            child_selectors = self._convert_field_name_part(field_parts, rel_model)
            for selector in child_selectors:
                yield field_path + selector

    def convert_related_fieldnames(self, fields, opts=None):
        """
        convert the field name which may contain polymorphic models names into
        raw filed names that can be used with django select_related and
        prefetch_related.
        """
        if not opts:
            opts = self.model
        for field_name in fields:
            field_parts = field_name.split(LOOKUP_SEP)
            selectors = self._convert_field_name_part(field_parts, opts)
            for selector in selectors:
                yield "__".join(selector)


class PolymorphicQuerySet(PolymorphicQuerySetMixin, QuerySet):
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

    def _clone(self, *args, **kwargs):
        # Django's _clone only copies its own variables, so we need to copy ours here
        new = super()._clone(*args, **kwargs)
        new.polymorphic_disabled = self.polymorphic_disabled
        new.polymorphic_deferred_loading = (
            copy.copy(self.polymorphic_deferred_loading[0]),
            self.polymorphic_deferred_loading[1],
        )
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

    def order_by(self, *field_names):
        """translate the field paths in the args, then call vanilla order_by."""
        field_names = [
            (
                translate_polymorphic_field_path(self.model, a) if isinstance(a, str) else a
            )  # allow expressions to pass unchanged
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

                        if isinstance(child, tuple):
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

                    cached_obj = search_object_cache(base_object, self.model, real_concrete_class)
                    if cached_obj:
                        resultlist.append(cached_obj)
                    else:
                        idlist_per_model[real_concrete_class].append(getattr(base_object, pk_name))
                        indexlist_per_model[real_concrete_class].append((i, len(resultlist)))
                        resultlist.append(None)

        # For each model in "idlist_per_model" request its objects (the real model)
        # from the db and store them in results[].
        # Then we copy the annotate fields from the base objects to the real objects.
        # Then we copy the extra() select fields from the base objects to the real objects.
        # TODO: defer(), only(): support for these would be around here
        # Also see PolymorphicModelIterable.fetch_polymorphic

        filter_relations = [
            _get_query_related_name(mdl_cls)
            for mdl_cls in _get_all_sub_models(self.model).values()
        ]

        for real_concrete_class, idlist in idlist_per_model.items():
            indices = indexlist_per_model[real_concrete_class]
            real_objects = real_concrete_class._base_objects.db_manager(self.db).filter(
                **{(f"{pk_name}__in"): idlist}
            )
            # copy select related configuration to new qs
            current_relation = real_objects.model.__name__.lower()
            real_objects = self.apply_select_related(
                real_objects, current_relation, filter_relations
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

    def apply_select_related(self, qs, relation, filtered):
        if self.query.select_related is True:
            return qs.select_related()

        model_name = qs.model.__name__.lower()
        if isinstance(self.query.select_related, dict):
            select_related = {}
            if isinstance(qs.query.select_related, dict):
                select_related = qs.query.select_related
            for k, v in self.query.select_related.items():
                if k in filtered and k != relation:
                    continue
                else:
                    if not isinstance(select_related, dict):
                        select_related = {}
                    if k == relation:
                        if isinstance(v, dict):
                            if model_name in v:
                                select_related = merge_dicts(select_related, v[model_name])
                            else:
                                for field in qs.model._meta.fields:
                                    if field.name in v:
                                        select_related = merge_dicts(select_related, v[field.name])
                        else:
                            select_related = merge_dicts(select_related, v)
                    else:
                        select_related[k] = v

            qs.query.select_related = select_related
        return qs

    def __repr__(self, *args, **kwargs):
        if self.model.polymorphic_query_multiline_output:
            result = ",\n  ".join(repr(o) for o in self.all())
            return f"[ {result} ]"
        else:
            return super().__repr__(*args, **kwargs)

    class _p_list_class(list):
        def __repr__(self, *args, **kwargs):
            result = ",\n  ".join(repr(o) for o in self)
            return f"[ {result} ]"

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


###################################################################################
# PolymorphicRelatedQuerySet


class PolymorphicRelatedQuerySetMixin(PolymorphicQuerySetMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._iterable_class = PolymorphicModelIterable
        self.polymorphic_disabled = False

    def _clone(self, *args, **kwargs):
        # Django's _clone only copies its own variables, so we need to copy ours here
        new = super()._clone(*args, **kwargs)
        new.polymorphic_disabled = self.polymorphic_disabled
        return new

    def _get_real_instances(self, base_result_objects):
        return base_result_objects


class PolymorphicRelatedQuerySet(PolymorphicRelatedQuerySetMixin, QuerySet):
    pass


def convert_to_polymorphic_queryset(qs):
    "Convert a queryset to one that support polymorphic evaluation"

    if isinstance(qs, Manager):
        qs = qs.get_queryset()

    if issubclass(qs.__class__, PolymorphicQuerySetMixin):
        return qs

    assert issubclass(QuerySet, qs.__class__), (
        "PolymorphicModel: cannot guarantee conversion of"
        f" {qs.__class__} to polymorphic queryset")

    class RelatedPolyQuerySet(PolymorphicRelatedQuerySetMixin, qs.__class__):
        @classmethod
        def _convert_to(cls, qs):
            c = cls(
                model=qs.model,
                query=qs.query.chain(),
                using=qs._db,
                hints=qs._hints,
            )
            c._sticky_filter = qs._sticky_filter
            c._for_write = qs._for_write
            c._prefetch_related_lookups = qs._prefetch_related_lookups[:]
            c._known_related_objects = qs._known_related_objects
            c._fields = qs._fields
            return c

    poly_qs = RelatedPolyQuerySet._convert_to(qs)
    return poly_qs