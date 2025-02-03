from django.conf import settings
from django.contrib.admin import AdminSite
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.contrib.auth.models import User
from django.contrib.messages.middleware import MessageMiddleware
from django.http.response import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import clear_url_caches, include, path, reverse, set_urlconf


class AdminTestCase(TestCase):
    """
    Testing the admin site
    """

    #: The model to test
    model = None
    #: The admin class to test
    admin_class = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user = User.objects.create_superuser(
            "admin", "admin@example.org", password="admin"
        )

    def setUp(self):
        super().setUp()

        # Have a separate site, to avoid dependency on polymorphic wrapping or standard admin configuration
        self.admin_site = AdminSite()

        if self.model is not None:
            self.admin_register(self.model, self.admin_class)

    def tearDown(self):
        clear_url_caches()
        set_urlconf(None)

    def register(self, model):
        """Decorator, like admin.register()"""

        def _dec(admin_class):
            self.admin_register(model, admin_class)
            return admin_class

        return _dec

    def admin_register(self, model, admin_site):
        """Register an model with admin to the test case, test client and URL reversing code."""
        self.admin_site.register(model, admin_site)

        # Make sure the URLs are reachable by reverse()
        clear_url_caches()
        set_urlconf(tuple([path("tmp-admin/", self.admin_site.urls)]))

    def get_admin_instance(self, model):
        try:
            return self.admin_site._registry[model]
        except KeyError:
            raise ValueError(f"Model not registered with admin: {model}")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        clear_url_caches()
        set_urlconf(None)

    def get_add_url(self, model):
        admin_instance = self.get_admin_instance(model)
        return reverse(admin_urlname(admin_instance.opts, "add"))

    def get_changelist_url(self, model):
        admin_instance = self.get_admin_instance(model)
        return reverse(admin_urlname(admin_instance.opts, "changelist"))

    def get_change_url(self, model, object_id):
        admin_instance = self.get_admin_instance(model)
        return reverse(admin_urlname(admin_instance.opts, "change"), args=(object_id,))

    def get_history_url(self, model, object_id):
        admin_instance = self.get_admin_instance(model)
        return reverse(admin_urlname(admin_instance.opts, "history"), args=(object_id,))

    def get_delete_url(self, model, object_id):
        admin_instance = self.get_admin_instance(model)
        return reverse(admin_urlname(admin_instance.opts, "delete"), args=(object_id,))

    def admin_get_add(self, model, qs=""):
        """
        Make a direct "add" call to the admin page, circumvening login checks.
        """
        admin_instance = self.get_admin_instance(model)
        request = self.create_admin_request("get", self.get_add_url(model) + qs)
        response = admin_instance.add_view(request)
        assert response.status_code == 200
        return response

    def admin_post_add(self, model, formdata, qs=""):
        """
        Make a direct "add" call to the admin page, circumvening login checks.
        """
        admin_instance = self.get_admin_instance(model)
        request = self.create_admin_request("post", self.get_add_url(model) + qs, data=formdata)
        response = admin_instance.add_view(request)
        self.assertFormSuccess(request.path, response)
        return response

    def admin_get_changelist(self, model):
        """
        Make a direct "add" call to the admin page, circumvening login checks.
        """
        admin_instance = self.get_admin_instance(model)
        request = self.create_admin_request("get", self.get_changelist_url(model))
        response = admin_instance.changelist_view(request)
        assert response.status_code == 200
        return response

    def admin_get_change(self, model, object_id, query=None, **extra):
        """
        Perform a GET request on the admin page
        """
        admin_instance = self.get_admin_instance(model)
        request = self.create_admin_request(
            "get", self.get_change_url(model, object_id), data=query, **extra
        )
        response = admin_instance.change_view(request, str(object_id))
        assert response.status_code == 200
        return response

    def admin_post_change(self, model, object_id, formdata, **extra):
        """
        Make a direct "add" call to the admin page, circumvening login checks.
        """
        admin_instance = self.get_admin_instance(model)
        request = self.create_admin_request(
            "post", self.get_change_url(model, object_id), data=formdata, **extra
        )
        response = admin_instance.change_view(request, str(object_id))
        self.assertFormSuccess(request.path, response)
        return response

    def admin_get_history(self, model, object_id, query=None, **extra):
        """
        Perform a GET request on the admin page
        """
        admin_instance = self.get_admin_instance(model)
        request = self.create_admin_request(
            "get", self.get_history_url(model, object_id), data=query, **extra
        )
        response = admin_instance.history_view(request, str(object_id))
        assert response.status_code == 200
        return response

    def admin_get_delete(self, model, object_id, query=None, **extra):
        """
        Perform a GET request on the admin delete page
        """
        admin_instance = self.get_admin_instance(model)
        request = self.create_admin_request(
            "get", self.get_delete_url(model, object_id), data=query, **extra
        )
        response = admin_instance.delete_view(request, str(object_id))
        assert response.status_code == 200
        return response

    def admin_post_delete(self, model, object_id, **extra):
        """
        Make a direct "add" call to the admin page, circumvening login checks.
        """
        if not extra:
            extra = {"data": {"post": "yes"}}

        admin_instance = self.get_admin_instance(model)
        request = self.create_admin_request("post", self.get_delete_url(model, object_id), **extra)
        response = admin_instance.delete_view(request, str(object_id))
        assert response.status_code == 302, f"Form errors in calling {request.path}"
        return response

    def create_admin_request(self, method, url, data=None, **extra):
        """
        Construct an Request instance for the admin view.
        """
        factory_method = getattr(RequestFactory(), method)

        if data is not None:
            if method != "get":
                data["csrfmiddlewaretoken"] = "foo"
            dummy_request = factory_method(url, data=data)
            dummy_request.user = self.admin_user

            # Add the management form fields if needed.
            # base_data = self._get_management_form_data(dummy_request)
            # base_data.update(data)
            # data = base_data

        request = factory_method(url, data=data, **extra)
        request.COOKIES[settings.CSRF_COOKIE_NAME] = "foo"
        request.csrf_processing_done = True

        # Add properties which middleware would typically do
        request.session = {}
        request.user = self.admin_user
        MessageMiddleware(lambda r: HttpResponse("OK?")).process_request(request)
        return request

    def assertFormSuccess(self, request_url, response):
        """
        Assert that the response was a redirect, not a form error.
        """
        assert response.status_code in [200, 302]
        if response.status_code != 302:
            context_data = response.context_data
            if "errors" in context_data:
                errors = response.context_data["errors"]
            elif "form" in context_data:
                errors = context_data["form"].errors
            else:
                raise KeyError("Unknown field for errors in the TemplateResponse!")

            assert response.status_code == 302, (
                f"Form errors in calling {request_url}:\n{errors.as_text()}"
            )
        assert "/login/?next=" not in response["Location"], (
            f"Received login response for {request_url}"
        )
