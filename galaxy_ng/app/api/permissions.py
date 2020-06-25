import logging

from rest_framework.permissions import BasePermission, SAFE_METHODS

from galaxy_ng.app.models import Namespace
from galaxy_ng.app.models.auth import SYSTEM_SCOPE
from django.conf import settings
from galaxy_ng.app.constants import DeploymentMode

log = logging.getLogger(__name__)


class InstrumentedPermission(BasePermission):
    """Adds additional logging and diagnostics to permissions checks."""
    inner_class = BasePermission

    def __init__(self, inner_permission):
        self.inner_permission = inner_permission

    def __repr__(self):
        return "%s(inner_permission=%s)" % (self.__class__.__name__, self.inner_permission)

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        import pprint
        # log.debug('request: %s', pprint.pformat(request.__dict__))
        # log.debug('request._request: %s', pprint.pformat(request._request.__dict__))
        # log.debug('view: %s', pprint.pformat(view.__dict__))

        result = self.inner_permission.has_permission(request, view)

        log.debug('%s %s view=%s-%s-%s for user=%s with groups=%s and perm: %s had result: %s',
                  request._request.method,
                  request._request.path,
                  view.basename, view.action, view.detail,
                  request.user, ','.join([x.name for x in request.user.groups.all()]),
                  self.inner_permission.__class__.__name__, result)

        return result
        # return True

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        # log.debug('request: %s', request)
        # log.debug('view: %s', view)
        log.debug('obj: %s', obj)

        result = self.inner_permission.has_object_permission(request, view, obj)

        log.debug('%s %s view=%s-%s-%s for user=%s, groups=%s perm=%s obj=%s had result: %s',
                  request._request.method,
                  request._request.path,
                  view.basename, view.action, view.detail,
                  request.user, ','.join([x.name for x in request.user.groups.all()]),
                  self.inner_permission.__class__.__name__,
                  obj,
                  result)

        return result
        # return True


class IsPartnerEngineer(BasePermission):
    """Checks if user is in partner engineers group."""

    GROUP_NAME = f'{SYSTEM_SCOPE}:partner-engineers'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name=self.GROUP_NAME).exists()


class IsNamespaceOwner(BasePermission):
    """Checks if user is in namespace owners group."""

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if isinstance(obj, Namespace):
            namespace = obj
        elif hasattr(obj, 'namespace'):
            namespace = obj.namespace
        else:
            obj_type = type(obj).__name__
            raise RuntimeError(
                f"Object {obj_type} is not a Namespace and does"
                f" not have \"namespace\" attribute. "
            )

        return namespace.groups.filter(pk__in=request.user.groups.all()).exists()


class IsNamespaceOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return IsNamespaceOwner().has_object_permission(request, view, obj)


class IsNamespaceOwnerOrPartnerEngineer(BasePermission):
    """Checks if user is owner of namespace or a partner engineer."""

    def has_object_permission(self, request, view, obj):
        if IsPartnerEngineer().has_permission(request, view):
            return True
        return IsNamespaceOwnerOrReadOnly().has_object_permission(
            request, view, obj)


class RestrictOnCloudDeployments(BasePermission):
    def has_permission(self, request, view):
        return settings.GALAXY_DEPLOYMENT_MODE == DeploymentMode.STANDALONE.value


class RestrictUnsafeOnCloudDeployments(RestrictOnCloudDeployments):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return super().has_permission(request, view)
