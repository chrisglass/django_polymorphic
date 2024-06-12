"""
The parent admin displays the list view of the base model.
"""

from django.contrib import admin
from django.contrib.admin.helpers import AdminErrorList, AdminForm
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.db import models
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import URLResolver
from django.utils.encoding import force_str
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from polymorphic.utils import get_base_polymorphic_model

from .forms import PolymorphicModelChoiceForm


class RegistrationClosed(RuntimeError):
    "The admin model can't be registered anymore at this point."


class ChildAdminNotRegistered(RuntimeError):
    "The admin site for the model is not registered."


class PolymorphicParentModelAdmin(admin.ModelAdmin):
    """
    A admin interface that can displays different change/delete pages, depending on the polymorphic model.
    To use this class, one attribute need to be defined:

    * :attr:`child_models` should be a list models.

    Alternatively, the following methods can be implemented:

    * :func:`get_child_models` should return a list of models.
    * optionally, :func:`get_child_type_choices` can be overwritten to refine the choices for the add dialog.

    This class needs to be inherited by the model admin base class that is registered in the site.
    The derived models should *not* register the ModelAdmin, but instead it should be returned by :func:`get_child_models`.
    """

    #: The base model that the class uses (auto-detected if not set explicitly)
    base_model = None

    #: The child models that should be displayed
    child_models = None

    #: Whether the list should be polymorphic too, leave to ``False`` to optimize
    polymorphic_list = False

    add_type_template = None
    add_type_form = PolymorphicModelChoiceForm

    #: The regular expression to filter the primary key in the URL.
    #: This accepts only numbers as defensive measure against catch-all URLs.
    #: If your primary key consists of string values, update this regular expression.
    pk_regex = r"(\d+|__fk__)"

    def __init__(self, model, admin_site, *args, **kwargs):
        super().__init__(model, admin_site, *args, **kwargs)
        self._is_setup = False

        if self.base_model is None:
            self.base_model = get_base_polymorphic_model(model)

    def _lazy_setup(self):
        if self._is_setup:
            return

        self._child_models = self.get_child_models()

        # Make absolutely sure that the child models don't use the old 0.9 format,
        # as of polymorphic 1.4 this deprecated configuration is no longer supported.
        # Instead, register the child models in the admin too.
        if self._child_models and not issubclass(self._child_models[0], models.Model):
            raise ImproperlyConfigured(
                "Since django-polymorphic 1.4, the `child_models` attribute "
                "and `get_child_models()` method should be a list of models only.\n"
                "The model-admin class should be registered in the regular Django admin."
            )

        self._child_admin_site = self.admin_site
        self._is_setup = True

    def register_child(self, model, model_admin):
        """
        Register a model with admin to display.
        """
        # After the get_urls() is called, the URLs of the child model can't be exposed anymore to the Django URLconf,
        # which also means that a "Save and continue editing" button won't work.
        if self._is_setup:
            raise RegistrationClosed("The admin model can't be registered anymore at this point.")

        if not issubclass(model, self.base_model):
            raise TypeError(f"{model.__name__} should be a subclass of {self.base_model.__name__}")
        if not issubclass(model_admin, admin.ModelAdmin):
            raise TypeError(
                f"{model_admin.__name__} should be a subclass of {admin.ModelAdmin.__name__}"
            )

        self._child_admin_site.register(model, model_admin)

    def get_child_models(self):
        """
        Return the derived model classes which this admin should handle.
        This should return a list of tuples, exactly like :attr:`child_models` is.

        The model classes can be retrieved as ``base_model.__subclasses__()``,
        a setting in a config file, or a query of a plugin registration system at your option
        """
        if self.child_models is None:
            raise NotImplementedError("Implement get_child_models() or child_models")

        return self.child_models

    def get_child_type_choices(self, request, action):
        """
        Return a list of polymorphic types for which the user has the permission to perform the given action.
        """
        self._lazy_setup()
        choices = []
        content_types = ContentType.objects.get_for_models(
            *self.get_child_models(), for_concrete_models=False
        )

        for model, ct in content_types.items():
            perm_function_name = f"has_{action}_permission"
            model_admin = self._get_real_admin_by_model(model)
            perm_function = getattr(model_admin, perm_function_name)
            if not perm_function(request):
                continue
            choices.append((ct.id, model._meta.verbose_name))
        return choices

    def _get_real_admin(self, object_id, super_if_self=True):
        try:
            obj = (
                self.model.objects.non_polymorphic().values("polymorphic_ctype").get(pk=object_id)
            )
        except self.model.DoesNotExist:
            raise Http404
        return self._get_real_admin_by_ct(obj["polymorphic_ctype"], super_if_self=super_if_self)

    def _get_real_admin_by_ct(self, ct_id, super_if_self=True):
        try:
            ct = ContentType.objects.get_for_id(ct_id)
        except ContentType.DoesNotExist as e:
            raise Http404(e)  # Handle invalid GET parameters

        model_class = ct.model_class()
        if not model_class:
            # Handle model deletion
            app_label, model = ct.natural_key()
            raise Http404(f"No model found for '{app_label}.{model}'.")

        return self._get_real_admin_by_model(model_class, super_if_self=super_if_self)

    def _get_real_admin_by_model(self, model_class, super_if_self=True):
        # In case of a ?ct_id=### parameter, the view is already checked for permissions.
        # Hence, make sure this is a derived object, or risk exposing other admin interfaces.
        if model_class not in self._child_models:
            raise PermissionDenied(
                f"Invalid model '{model_class}', it must be registered as child model."
            )

        try:
            # HACK: the only way to get the instance of an model admin,
            # is to read the registry of the AdminSite.
            real_admin = self._child_admin_site._registry[model_class]
        except KeyError:
            raise ChildAdminNotRegistered(
                f"No child admin site was registered for a '{model_class}' model."
            )

        if super_if_self and real_admin is self:
            return super()
        else:
            return real_admin

    def get_queryset(self, request):
        # optimize the list display.
        qs = super().get_queryset(request)
        if not self.polymorphic_list:
            qs = qs.non_polymorphic()
        return qs

    def add_view(self, request, form_url="", extra_context=None):
        """Redirect the add view to the real admin."""
        ct_id = int(request.GET.get("ct_id", 0))
        if not ct_id:
            # Display choices
            return self.add_type_view(request)
        else:
            real_admin = self._get_real_admin_by_ct(ct_id)
            # rebuild form_url, otherwise libraries below will override it.
            form_url = add_preserved_filters(
                {
                    "preserved_filters": urlencode({"ct_id": ct_id}),
                    "opts": self.model._meta,
                },
                form_url,
            )
            return real_admin.add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, *args, **kwargs):
        """Redirect the change view to the real admin."""
        real_admin = self._get_real_admin(object_id)
        return real_admin.change_view(request, object_id, *args, **kwargs)

    def changeform_view(self, request, object_id=None, *args, **kwargs):
        # The `changeform_view` is available as of Django 1.7, combining the add_view and change_view.
        # As it's directly called by django-reversion, this method is also overwritten to make sure it
        # also redirects to the child admin.
        if object_id:
            real_admin = self._get_real_admin(object_id)
            return real_admin.changeform_view(request, object_id, *args, **kwargs)
        else:
            # Add view. As it should already be handled via `add_view`, this means something custom is done here!
            return super().changeform_view(request, object_id, *args, **kwargs)

    def history_view(self, request, object_id, extra_context=None):
        """Redirect the history view to the real admin."""
        real_admin = self._get_real_admin(object_id)
        return real_admin.history_view(request, object_id, extra_context=extra_context)

    def delete_view(self, request, object_id, extra_context=None):
        """Redirect the delete view to the real admin."""
        real_admin = self._get_real_admin(object_id)
        return real_admin.delete_view(request, object_id, extra_context)

    def get_preserved_filters(self, request):
        if "_changelist_filters" in request.GET:
            request.GET = request.GET.copy()
            filters = request.GET.get("_changelist_filters")
            f = filters.split("&")
            for x in f:
                c = x.split("=")
                request.GET[c[0]] = c[1]
            del request.GET["_changelist_filters"]
        return super().get_preserved_filters(request)

    def get_urls(self):
        """
        Expose the custom URLs for the subclasses and the URL resolver.
        """
        urls = super().get_urls()

        # At this point. all admin code needs to be known.
        self._lazy_setup()

        return urls

    def subclass_view(self, request, path):
        """
        Forward any request to a custom view of the real admin.
        """
        ct_id = int(request.GET.get("ct_id", 0))
        if not ct_id:
            # See if the path started with an ID.
            try:
                pos = path.find("/")
                if pos == -1:
                    object_id = int(path)
                else:
                    object_id = int(path[0:pos])
            except ValueError:
                raise Http404(
                    f"No ct_id parameter, unable to find admin subclass for path '{path}'."
                )

            ct_id = self.model.objects.values_list("polymorphic_ctype_id", flat=True).get(
                pk=object_id
            )

        real_admin = self._get_real_admin_by_ct(ct_id)
        resolver = URLResolver("^", real_admin.urls)
        resolvermatch = resolver.resolve(path)  # May raise Resolver404
        if not resolvermatch:
            raise Http404(f"No match for path '{path}' in admin subclass.")

        return resolvermatch.func(request, *resolvermatch.args, **resolvermatch.kwargs)

    def add_type_view(self, request, form_url=""):
        """
        Display a choice form to select which page type to add.
        """
        if not self.has_add_permission(request):
            raise PermissionDenied

        extra_qs = ""
        if request.META["QUERY_STRING"]:
            # QUERY_STRING is bytes in Python 3, using force_str() to decode it as string.
            # See QueryDict how Django deals with that.
            # TODO: should this use a Django method instead of manipulating the string directly?
            extra_qs = f"&{force_str(request.META['QUERY_STRING'])}"

        choices = self.get_child_type_choices(request, "add")
        if len(choices) == 0:
            raise PermissionDenied
        if len(choices) == 1:
            return HttpResponseRedirect(f"?ct_id={choices[0][0]}{extra_qs}")

        # Create form
        form = self.add_type_form(
            data=request.POST if request.method == "POST" else None,
            initial={"ct_id": choices[0][0]},
        )
        form.fields["ct_id"].choices = choices

        if form.is_valid():
            return HttpResponseRedirect(f"?ct_id={form.cleaned_data['ct_id']}{extra_qs}")

        # Wrap in all admin layout
        fieldsets = ((None, {"fields": ("ct_id",)}),)
        adminForm = AdminForm(form, fieldsets, {}, model_admin=self)
        media = self.media + adminForm.media
        opts = self.model._meta

        context = {
            "title": _("Add %s") % force_str(opts.verbose_name),
            "adminform": adminForm,
            "is_popup": ("_popup" in request.POST or "_popup" in request.GET),
            "media": mark_safe(media),
            "errors": AdminErrorList(form, ()),
            "app_label": opts.app_label,
        }
        return self.render_add_type_form(request, context, form_url)

    def render_add_type_form(self, request, context, form_url=""):
        """
        Render the page type choice form.
        """
        opts = self.model._meta
        app_label = opts.app_label
        context.update(
            {
                "has_change_permission": self.has_change_permission(request),
                "form_url": mark_safe(form_url),
                "opts": opts,
                "add": True,
                "save_on_top": self.save_on_top,
                **self.admin_site.each_context(request),
            }
        )

        templates = self.add_type_template or [
            f"admin/{app_label}/{opts.object_name.lower()}/add_type_form.html",
            f"admin/{app_label}/add_type_form.html",
            "admin/polymorphic/add_type_form.html",  # added default here
            "admin/add_type_form.html",
        ]

        request.current_app = self.admin_site.name
        return self.admin_site.admin_view(TemplateResponse)(request, templates, context)

    @property
    def change_list_template(self):
        opts = self.model._meta
        app_label = opts.app_label

        # Pass the base options
        base_opts = self.base_model._meta
        base_app_label = base_opts.app_label

        return [
            f"admin/{app_label}/{opts.object_name.lower()}/change_list.html",
            f"admin/{app_label}/change_list.html",
            # Added base class:
            f"admin/{base_app_label}/{base_opts.object_name.lower()}/change_list.html",
            f"admin/{base_app_label}/change_list.html",
            "admin/change_list.html",
        ]
