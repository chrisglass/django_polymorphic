from collections import OrderedDict

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.forms.models import (
    BaseInlineFormSet,
    BaseModelFormSet,
    ModelForm,
    inlineformset_factory,
    modelform_factory,
    modelformset_factory,
)
from django.utils.functional import cached_property

from polymorphic.models import PolymorphicModel

from .utils import add_media


class UnsupportedChildType(LookupError):
    pass


class PolymorphicFormSetChild(object):
    """
    Metadata to define the inline of a polymorphic child.
    Provide this information in the :func:'polymorphic_inlineformset_factory' construction.
    """

    def __init__(
        self,
        model,
        form=ModelForm,
        fields=None,
        exclude=None,
        formfield_callback=None,
        widgets=None,
        localized_fields=None,
        labels=None,
        help_texts=None,
        error_messages=None,
    ):

        self.model = model

        # Instead of initializing the form here right away,
        # the settings are saved so get_form() can receive additional exclude kwargs.
        # This is mostly needed for the generic inline formsets
        self._form_base = form
        self.fields = fields
        self.exclude = exclude or ()
        self.formfield_callback = formfield_callback
        self.widgets = widgets
        self.localized_fields = localized_fields
        self.labels = labels
        self.help_texts = help_texts
        self.error_messages = error_messages

    @cached_property
    def content_type(self):
        """
        Expose the ContentType that the child relates to.
        This can be used for the ''polymorphic_ctype'' field.
        """
        return ContentType.objects.get_for_model(self.model, for_concrete_model=False)

    def get_form(self, **kwargs):
        """
        Construct the form class for the formset child.
        """
        # Do what modelformset_factory() / inlineformset_factory() does to the 'form' argument;
        # Construct the form with the given ModelFormOptions values

        # Fields can be overwritten. To support the global 'polymorphic_child_forms_factory' kwargs,
        # that doesn't completely replace all 'exclude' settings defined per child type,
        # we allow to define things like 'extra_...' fields that are amended to the current child settings.

        exclude = list(self.exclude)
        extra_exclude = kwargs.pop("extra_exclude", None)
        if extra_exclude:
            exclude += list(extra_exclude)

        defaults = {
            "form": self._form_base,
            "formfield_callback": self.formfield_callback,
            "fields": self.fields,
            "exclude": exclude,
            # 'for_concrete_model': for_concrete_model,
            "localized_fields": self.localized_fields,
            "labels": self.labels,
            "help_texts": self.help_texts,
            "error_messages": self.error_messages,
            # 'field_classes': field_classes,
        }
        defaults.update(kwargs)

        return modelform_factory(self.model, **defaults)


def polymorphic_child_forms_factory(formset_children, **kwargs):
    """
    Construct the forms for the formset children.
    This is mostly used internally, and rarely needs to be used by external projects.
    When using the factory methods (:func:'polymorphic_inlineformset_factory'),
    this feature is called already for you.
    """
    child_forms = OrderedDict()

    for formset_child in formset_children:
        child_forms[formset_child.model] = formset_child.get_form(**kwargs)

    return child_forms


class BasePolymorphicModelFormSet(BaseModelFormSet):
    """
    A formset that can produce different forms depending on the object type.

    Note that the 'add' feature is therefore more complex,
    as all variations need ot be exposed somewhere.

    When switching existing formsets to the polymorphic formset,
    note that the ID field will no longer be named ''model_ptr'',
    but just appear as ''id''.
    """

    # Assigned by the factory
    child_forms = OrderedDict()

    def __init__(self, *args, **kwargs):
        super(BasePolymorphicModelFormSet, self).__init__(*args, **kwargs)
        self.queryset_data = self.get_queryset()

    def _construct_form(self, i, **kwargs):
        """
        Create the form, depending on the model that's behind it.
        """
        # BaseModelFormSet logic
        if self.is_bound and i < self.initial_form_count():
            pk_key = "%s-%s" % (self.add_prefix(i), self.model._meta.pk.name)
            pk = self.data[pk_key]
            pk_field = self.model._meta.pk
            to_python = self._get_to_python(pk_field)
            pk = to_python(pk)
            kwargs["instance"] = self._existing_object(pk)
        if i < self.initial_form_count() and "instance" not in kwargs:
            kwargs["instance"] = self.get_queryset()[i]
        if i >= self.initial_form_count() and self.initial_extra:
            # Set initial values for extra forms
            try:
                kwargs["initial"] = self.initial_extra[i - self.initial_form_count()]
            except IndexError:
                pass

        # BaseFormSet logic, with custom formset_class
        defaults = {
            "auto_id": self.auto_id,
            "prefix": self.add_prefix(i),
            "error_class": self.error_class,
        }
        if self.is_bound:
            defaults["data"] = self.data
            defaults["files"] = self.files
        if self.initial and "initial" not in kwargs:
            try:
                defaults["initial"] = self.initial[i]
            except IndexError:
                pass
        # Allow extra forms to be empty, unless they're part of
        # the minimum forms.
        if i >= self.initial_form_count() and i >= self.min_num:
            defaults["empty_permitted"] = True
            defaults["use_required_attribute"] = False
        defaults.update(kwargs)

        # Need to find the model that will be displayed in this form.
        # Hence, peeking in the self.queryset_data beforehand.
        if self.is_bound:
            if "instance" in defaults:
                # Object is already bound to a model, won't change the content type
                model = defaults[
                    "instance"
                ].get_real_instance_class()  # allow proxy models
            else:
                # Extra or empty form, use the provided type.
                # Note this completely tru
                prefix = defaults["prefix"]
                try:
                    ct_id = int(self.data["{0}-polymorphic_ctype".format(prefix)])
                except (KeyError, ValueError):
                    raise ValidationError(
                        "Formset row {0} has no 'polymorphic_ctype' defined!".format(
                            prefix
                        )
                    )

                model = ContentType.objects.get_for_id(ct_id).model_class()
                if model not in self.child_forms:
                    # Perform basic validation, as we skip the ChoiceField here.
                    raise UnsupportedChildType(
                        "Child model type {0} is not part of the formset".format(model)
                    )
        else:
            if "instance" in defaults:
                model = defaults[
                    "instance"
                ].get_real_instance_class()  # allow proxy models
            elif "polymorphic_ctype" in defaults.get("initial", {}):
                model = defaults["initial"]["polymorphic_ctype"].model_class()
            elif i < len(self.queryset_data):
                model = self.queryset_data[i].__class__
            else:
                # Extra forms, cycle between all types
                # TODO: take the 'extra' value of each child formset into account.
                total_known = len(self.queryset_data)
                child_models = list(self.child_forms.keys())
                model = child_models[(i - total_known) % len(child_models)]

        form_class = self.get_form_class(model)
        form = form_class(**defaults)
        self.add_fields(form, i)
        return form

    def add_fields(self, form, index):
        """Add a hidden field for the content type."""
        ct = ContentType.objects.get_for_model(
            form._meta.model, for_concrete_model=False
        )
        choices = [(ct.pk, ct)]  # Single choice, existing forms can't change the value.
        form.fields["polymorphic_ctype"] = forms.TypedChoiceField(
            choices=choices, initial=ct.pk, required=False, widget=forms.HiddenInput, coerce=int,
        )
        super(BasePolymorphicModelFormSet, self).add_fields(form, index)

    def get_form_class(self, model):
        """
        Return the proper form class for the given model.
        """
        if not self.child_forms:
            raise ImproperlyConfigured(
                "No 'child_forms' defined in {0}".format(self.__class__.__name__)
            )
        if not issubclass(model, PolymorphicModel):
            raise TypeError("Expect polymorphic model type, not {0}".format(model))

        try:
            return self.child_forms[model]
        except KeyError:
            # This may happen when the query returns objects of a type that was not handled by the formset.
            raise UnsupportedChildType(
                "The '{0}' found a '{1}' model in the queryset, "
                "but no form class is registered to display it.".format(
                    self.__class__.__name__, model.__name__
                )
            )

    def is_multipart(self):
        """
        Returns True if the formset needs to be multipart, i.e. it
        has FileInput. Otherwise, False.
        """
        return any(f.is_multipart() for f in self.empty_forms)

    @property
    def media(self):
        # Include the media of all form types.
        # The form media includes all form widget media
        media = forms.Media()
        for form in self.empty_forms:
            add_media(media, form.media)
        return media

    @cached_property
    def empty_forms(self):
        """
        Return all possible empty forms
        """
        forms = []
        for model, form_class in self.child_forms.items():
            kwargs = self.get_form_kwargs(None)

            form = form_class(
                auto_id=self.auto_id,
                prefix=self.add_prefix("__prefix__"),
                empty_permitted=True,
                use_required_attribute=False,
                **kwargs
            )
            self.add_fields(form, None)
            forms.append(form)
        return forms

    @property
    def empty_form(self):
        # TODO: make an exception when can_add_base is defined?
        raise RuntimeError(
            "'empty_form' is not used in polymorphic formsets, use 'empty_forms' instead."
        )


def polymorphic_modelformset_factory(
    model,
    formset_children,
    formset=BasePolymorphicModelFormSet,
    # Base field
    # TODO: should these fields be removed in favor of creating
    # the base form as a formset child too?
    form=ModelForm,
    fields=None,
    exclude=None,
    extra=1,
    can_order=False,
    can_delete=True,
    max_num=None,
    formfield_callback=None,
    widgets=None,
    validate_max=False,
    localized_fields=None,
    labels=None,
    help_texts=None,
    error_messages=None,
    min_num=None,
    validate_min=False,
    field_classes=None,
    child_form_kwargs=None,
):
    """
    Construct the class for an polymorphic model formset.

    All arguments are identical to :func:'~django.forms.models.modelformset_factory',
    with the exception of the ''formset_children'' argument.

    :param formset_children: A list of all child :class:'PolymorphicFormSetChild' objects
                             that tell the inline how to render the child model types.
    :type formset_children: Iterable[PolymorphicFormSetChild]
    :rtype: type
    """
    kwargs = {
        "model": model,
        "form": form,
        "formfield_callback": formfield_callback,
        "formset": formset,
        "extra": extra,
        "can_delete": can_delete,
        "can_order": can_order,
        "fields": fields,
        "exclude": exclude,
        "min_num": min_num,
        "max_num": max_num,
        "widgets": widgets,
        "validate_min": validate_min,
        "validate_max": validate_max,
        "localized_fields": localized_fields,
        "labels": labels,
        "help_texts": help_texts,
        "error_messages": error_messages,
        "field_classes": field_classes,
    }
    FormSet = modelformset_factory(**kwargs)

    child_kwargs = {
        # 'exclude': exclude,
    }
    if child_form_kwargs:
        child_kwargs.update(child_form_kwargs)

    FormSet.child_forms = polymorphic_child_forms_factory(
        formset_children, **child_kwargs
    )
    return FormSet


class BasePolymorphicInlineFormSet(BaseInlineFormSet, BasePolymorphicModelFormSet):
    """
    Polymorphic formset variation for inline formsets
    """

    def _construct_form(self, i, **kwargs):
        return super(BasePolymorphicInlineFormSet, self)._construct_form(i, **kwargs)


def polymorphic_inlineformset_factory(
    parent_model,
    model,
    formset_children,
    formset=BasePolymorphicInlineFormSet,
    fk_name=None,
    # Base field
    # TODO: should these fields be removed in favor of creating
    # the base form as a formset child too?
    form=ModelForm,
    fields=None,
    exclude=None,
    extra=1,
    can_order=False,
    can_delete=True,
    max_num=None,
    formfield_callback=None,
    widgets=None,
    validate_max=False,
    localized_fields=None,
    labels=None,
    help_texts=None,
    error_messages=None,
    min_num=None,
    validate_min=False,
    field_classes=None,
    child_form_kwargs=None,
):
    """
    Construct the class for an inline polymorphic formset.

    All arguments are identical to :func:'~django.forms.models.inlineformset_factory',
    with the exception of the ''formset_children'' argument.

    :param formset_children: A list of all child :class:'PolymorphicFormSetChild' objects
                             that tell the inline how to render the child model types.
    :type formset_children: Iterable[PolymorphicFormSetChild]
    :rtype: type
    """
    kwargs = {
        "parent_model": parent_model,
        "model": model,
        "form": form,
        "formfield_callback": formfield_callback,
        "formset": formset,
        "fk_name": fk_name,
        "extra": extra,
        "can_delete": can_delete,
        "can_order": can_order,
        "fields": fields,
        "exclude": exclude,
        "min_num": min_num,
        "max_num": max_num,
        "widgets": widgets,
        "validate_min": validate_min,
        "validate_max": validate_max,
        "localized_fields": localized_fields,
        "labels": labels,
        "help_texts": help_texts,
        "error_messages": error_messages,
        "field_classes": field_classes,
    }
    FormSet = inlineformset_factory(**kwargs)

    child_kwargs = {
        # 'exclude': exclude,
    }
    if child_form_kwargs:
        child_kwargs.update(child_form_kwargs)

    FormSet.child_forms = polymorphic_child_forms_factory(
        formset_children, **child_kwargs
    )
    return FormSet
