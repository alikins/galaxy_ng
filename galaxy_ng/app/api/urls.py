from django.conf import settings
from django.urls import include, path

from . import views
from .ui import urls as ui_urls
from .v3 import urls as v3_urls
from .v3 import viewsets as v3_viewsets

DEFAULT_DISTRIBUTION_BASE_PATH = settings.GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH.strip('/')

app_name = "api"
urlpatterns = [
    path("v3/_ui/", include(ui_urls)),

    # A set of galaxy v3 API urls per Distribution.base_path
    # which is essentially per Repository
    path("content/<str:path>/v3/",
         include(v3_urls, namespace='content')),

    path("content/<str:path>/",
         v3_viewsets.ApiRootView.as_view(),
         name="content"),

    # This can be removed when ansible-galaxy stops appending '/api' to the
    # urls.
    path("content/<str:path>/api/",
         v3_viewsets.SlashApiRedirectPerDistroView.as_view(),
         name="content-redirect"),


    # Set an instance of the v3 urls/viewsets at the same
    # url path as the former galaxy_api.api.v3.viewsets
    # ie (/api/automation-hub/v3/collections etc
    # and pass in path param 'path' that actually means
    # the base_path of the Distribution. For the default case,
    # use the hard coded 'default' distro (ie, 'automation-hub')
    path("v3/",
         include(v3_urls, namespace='default-content'),
         {'path': DEFAULT_DISTRIBUTION_BASE_PATH}),

    # This path is to redirect requests to /api/automation-hub/api/
    # to /api/automation-hub/

    # This is a workaround for https://github.com/ansible/ansible/issues/62073.
    # ansible-galaxy in ansible 2.9 always appends '/api' to any configured
    # galaxy server urls to try to find the API root. So add a redirect from
    # "/api" to actual API root at "/".

    path("",
         views.ApiRootView.as_view(),
         name="root"
         ),

    # This can be removed when ansible-galaxy stops appending '/api' to the
    # urls.
    path("api/",
         views.SlashApiRedirectView.as_view(),
         name="api-redirect"),
]
