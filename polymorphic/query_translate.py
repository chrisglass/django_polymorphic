"""
PolymorphicQuerySet support functions
"""

import copy
from collections import deque

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, FieldError
from django.db import models
from django.db.models import Q
from django.db.models.fields.related import ForeignObjectRel, RelatedField
from django.db.utils import DEFAULT_DB_ALIAS

# These functions implement the additional filter- and Q-object functionality.
# They form a kind of small framework for easily adding more
# functionality to filters and Q objects.
# Probably a more general queryset enhancement class could be made out of them.

###################################################################################
# PolymorphicQuerySet support functions


def translate_polymorphic_filter_definitions_in_kwargs(
    queryset_model, kwargs, using=DEFAULT_DB_ALIAS
):
    """
    Translate the keyword argument list for PolymorphicQuerySet.filter()

    Any kwargs with special polymorphic functionality are replaced in the kwargs
    dict with their vanilla django equivalents.

    For some kwargs a direct replacement is not possible, as a Q object is needed
    instead to implement the required functionality. In these cases the kwarg is
    deleted from the kwargs dict and a Q object is added to the return list.

    Modifies: kwargs dict
    Returns: a list of non-keyword-arguments (Q objects) to be added to the filter() query.
    """
    additional_args = []
    for field_path, val in kwargs.copy().items():  # `copy` so we're not mutating the dict
        new_expr = _translate_polymorphic_filter_definition(
            queryset_model, field_path, val, using=using
        )

        if isinstance(new_expr, tuple):
            # replace kwargs element
            del kwargs[field_path]
            kwargs[new_expr[0]] = new_expr[1]

        elif isinstance(new_expr, models.Q):
            del kwargs[field_path]
            additional_args.append(new_expr)

    return additional_args


def translate_polymorphic_Q_object(queryset_model, potential_q_object, using=DEFAULT_DB_ALIAS):
    def tree_node_correct_field_specs(my_model, node):
        "process all children of this Q node"
        for i in range(len(node.children)):
            child = node.children[i]

            if isinstance(child, (tuple, list)):
                # this Q object child is a tuple => a kwarg like Q( instance_of=ModelB )
                key, val = child
                new_expr = _translate_polymorphic_filter_definition(
                    my_model, key, val, using=using
                )
                if new_expr:
                    node.children[i] = new_expr
            else:
                # this Q object child is another Q object, recursively process this as well
                tree_node_correct_field_specs(my_model, child)

    if isinstance(potential_q_object, models.Q):
        tree_node_correct_field_specs(queryset_model, potential_q_object)

    return potential_q_object


def translate_polymorphic_filter_definitions_in_args(queryset_model, args, using=DEFAULT_DB_ALIAS):
    """
    Translate the non-keyword argument list for PolymorphicQuerySet.filter()

    In the args list, we return all kwargs to Q-objects that contain special
    polymorphic functionality with their vanilla django equivalents.
    We traverse the Q object tree for this (which is simple).


    Returns: modified Q objects
    """
    return [
        translate_polymorphic_Q_object(queryset_model, copy.deepcopy(q), using=using) for q in args
    ]


def _translate_polymorphic_filter_definition(
    queryset_model, field_path, field_val, using=DEFAULT_DB_ALIAS
):
    """
    Translate a keyword argument (field_path=field_val), as used for
    PolymorphicQuerySet.filter()-like functions (and Q objects).

    A kwarg with special polymorphic functionality is translated into
    its vanilla django equivalent, which is returned, either as tuple
    (field_path, field_val) or as Q object.

    Returns: kwarg tuple or Q object or None (if no change is required)
    """

    # handle instance_of expressions or alternatively,
    # if this is a normal Django filter expression, return None
    if field_path == "instance_of":
        return create_instanceof_q(field_val, using=using)
    elif field_path == "not_instance_of":
        return create_instanceof_q(field_val, not_instance_of=True, using=using)
    elif "___" not in field_path:
        return None  # no change

    # filter expression contains '___' (i.e. filter for polymorphic field)
    # => get the model class specified in the filter expression
    newpath = translate_polymorphic_field_path(queryset_model, field_path)
    return (newpath, field_val)


def translate_polymorphic_field_path(queryset_model, field_path):
    """
    Translate a field path from a keyword argument, as used for
    PolymorphicQuerySet.filter()-like functions (and Q objects).
    Supports leading '-' (for order_by args).

    E.g.: if queryset_model is ModelA, then "ModelC___field3" is translated
    into modela__modelb__modelc__field3.
    Returns: translated path (unchanged, if no translation needed)
    """
    if not isinstance(field_path, str):
        raise ValueError(f"Expected field name as string: {field_path}")

    classname, sep, pure_field_path = field_path.partition("___")
    if not sep:
        return field_path
    assert classname, f"PolymorphicModel: {field_path}: bad field specification"

    negated = False
    if classname[0] == "-":
        negated = True
        classname = classname.lstrip("-")

    if "__" in classname:
        # the user has app label prepended to class name via __ => use Django's get_model function
        appname, sep, classname = classname.partition("__")
        model = apps.get_model(appname, classname)
        assert model, f"PolymorphicModel: model {model.__name__} (in app {appname}) not found!"
        if not issubclass(model, queryset_model):
            e = (
                'PolymorphicModel: queryset filter error: "'
                + model.__name__
                + '" is not derived from "'
                + queryset_model.__name__
                + '"'
            )
            raise AssertionError(e)

    else:
        # the user has only given us the class name via ___
        # => select the model from the sub models of the queryset base model

        # Test whether it's actually a regular relation__ _fieldname (the field starting with an _)
        # so no tripple ClassName___field was intended.
        try:
            # This also retreives M2M relations now (including reverse foreign key relations)
            field = queryset_model._meta.get_field(classname)

            if isinstance(field, (RelatedField, ForeignObjectRel)):
                # Can also test whether the field exists in the related object to avoid ambiguity between
                # class names and field names, but that never happens when your class names are in CamelCase.
                return field_path  # No exception raised, field does exist.
        except FieldDoesNotExist:
            pass

        submodels = _get_all_sub_models(queryset_model)
        model = submodels.get(classname, None)
        assert model, (
            f"PolymorphicModel: model {classname} not found (not a subclass of {queryset_model.__name__})!"
        )

    basepath = _create_base_path(queryset_model, model)

    if negated:
        newpath = "-"
    else:
        newpath = ""

    newpath += basepath
    if basepath:
        newpath += "__"

    newpath += pure_field_path
    return newpath


def _get_all_sub_models(base_model):
    """#Collect all sub-models, this should be optimized (cached)"""
    result = {}
    queue = deque([base_model])

    while queue:
        model = queue.popleft()
        if issubclass(model, models.Model) and model != models.Model:
            # model name is occurring twice in submodel inheritance tree => Error
            if model.__name__ in result and model != result[model.__name__]:
                name1 = f"{model._meta.app_label}.{model.__name__}"
                name2 = (
                    f"{result[model.__name__]._meta.app_label}.{result[model.__name__].__name__}"
                )
                raise FieldError(
                    f"PolymorphicModel: model name alone is ambiguous: {name1} and {name2} match!\n"
                    f"In this case, please use the syntax: applabel__ModelName___field"
                )

            result[model.__name__] = model
        queue.extend(model.__subclasses__())

    return result


def _create_base_path(baseclass, myclass):
    # create new field path for expressions, e.g. for baseclass=ModelA, myclass=ModelC
    # 'modelb__modelc" is returned
    for b in myclass.__bases__:
        if b == baseclass:
            return _get_query_related_name(myclass)

        path = _create_base_path(baseclass, b)
        if path:
            if b._meta.abstract or b._meta.proxy:
                return _get_query_related_name(myclass)
            else:
                return f"{path}__{_get_query_related_name(myclass)}"
    return ""


def _get_query_related_name(myclass):
    for f in myclass._meta.local_fields:
        if isinstance(f, models.OneToOneField) and f.remote_field.parent_link:
            return f.related_query_name()

    # Fallback to undetected name,
    # this happens on proxy models (e.g. SubclassSelectorProxyModel)
    return myclass.__name__.lower()


def create_instanceof_q(modellist, not_instance_of=False, using=DEFAULT_DB_ALIAS):
    """
    Helper function for instance_of / not_instance_of
    Creates and returns a Q object that filters for the models in modellist,
    including all subclasses of these models (as we want to do the same
    as pythons isinstance() ).
    .
    We recursively collect all __subclasses__(), create a Q filter for each,
    and or-combine these Q objects. This could be done much more
    efficiently however (regarding the resulting sql), should an optimization
    be needed.
    """
    if not modellist:
        return None

    if not isinstance(modellist, (list, tuple)):
        from .models import PolymorphicModel

        if issubclass(modellist, PolymorphicModel):
            modellist = [modellist]
        else:
            raise TypeError(
                "PolymorphicModel: instance_of expects a list of (polymorphic) "
                "models or a single (polymorphic) model"
            )

    contenttype_ids = _get_mro_content_type_ids(modellist, using)
    q = Q(polymorphic_ctype__in=sorted(contenttype_ids))
    if not_instance_of:
        q = ~q
    return q


def _get_mro_content_type_ids(models, using):
    contenttype_ids = set()
    for model in models:
        ct = ContentType.objects.db_manager(using).get_for_model(model, for_concrete_model=False)
        contenttype_ids.add(ct.pk)
        subclasses = model.__subclasses__()
        if subclasses:
            contenttype_ids.update(_get_mro_content_type_ids(subclasses, using))
    return contenttype_ids
