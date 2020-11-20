import logging
import pprint
from typing import List

from django.conf import settings
from rest_access_policy import AccessPolicy, AccessPolicyException
from rest_framework.exceptions import NotFound

from galaxy_ng.app.api.ui.serializers import UserSerializer
from galaxy_ng.app import models

from galaxy_ng.app.access_control.statements import STANDALONE_STATEMENTS, INSIGHTS_STATEMENTS

log = logging.getLogger(__name__)
pf = pprint.pformat

STATEMENTS = {'insights': INSIGHTS_STATEMENTS,
              'standalone': STANDALONE_STATEMENTS}


class AccessPolicyVerboseMixin:
    """Mixin to make AccessPolicy checks verbose

    This has to reimplement / cut&paste most of rest_access_policy.AccessPolicy
    to instrument the low level permissions checks.
    """

    def has_permission(self, request, view):
        result = super().has_permission(request, view)
        log.debug('view.get_authenticators: %s', view.get_authenticators())
        log.debug('view.get_perms(): %s', view.get_permissions())
        log.debug('%s %s view=%s-%s-%s for user=%s with groups=%s and had result: %s',
                  request._request.method,
                  request._request.path,
                  getattr(view, 'basename', 'NotAViewSet'),
                  getattr(view, 'action', 'NotAViewSet'),
                  getattr(view, 'detail', 'NotAViewSet'),
                  request.user, ','.join([x.name for x in request.user.groups.all()]),
                  # self.inner_permission.__class__.__name__,
                  result)
        return result

    def has_object_permission(self, request, view, obj):
        result = super().has_object_permission(request, view, obj)
        log.debug('%s %s view=%s-%s-%s for user=%s, groups=%s obj=%s had result: %s',
                  request._request.method,
                  request._request.path,
                  view.basename, view.action, view.detail,
                  request.user,
                  ','.join([x.name for x in request.user.groups.all()]),
                  # self.inner_permission.__class__.__name__,
                  obj,
                  result)
        return result

    def _evaluate_statements(
        self, statements: List[dict], request, view, action: str
    ) -> bool:
        log.debug('policy.Name: %s', self.NAME)
        log.debug('action: %s', action)

        statements = self._normalize_statements(statements)
        log.debug('norm statements:\n%s', pf(statements))

        matched = self._get_statements_matching_principal(request, statements)
        log.debug('matched(principal):\n%s', pf(matched))

        matched = self._get_statements_matching_action(request, action, matched)
        log.debug('matched(action):\n%s', pf(matched))

        matched = self._get_statements_matching_context_conditions(
            request, view, action, matched
        )

        log.debug('matched(context):\n%s', pf(matched))

        denied = [_ for _ in matched if _["effect"] != "allow"]
        for deny in denied:
            log.debug('deny: %s', deny)

        if len(matched) == 0 or len(denied) > 0:
            return False

        return True

    def _check_condition_foo(self, condition: str, request, view, action: str):
        """
            Evaluate a custom context condition; if method does not exist on
            the access policy class, then return False.
            Condition value can contain a value that is passed to method, if
            formatted as `<method_name>:<arg_value>`.
        """
        result = super()._check_condition(condition, request, view, action)
        log.debug('_check_condition: condition=%s, request=%s, view=%s, action=%s, result=%s',
                  condition, request, view, action, result)
        return result

    def _check_condition(self, condition: str, request, view, action: str):
        """
            Evaluate a custom context condition; if method does not exist on
            the access policy class, then return False.
            Condition value can contain a value that is passed to method, if
            formatted as `<method_name>:<arg_value>`.
        """
        parts = condition.split(":", 1)
        method_name = parts[0]
        arg = parts[1] if len(parts) == 2 else None
        method = self._get_condition_method(method_name)

        if arg is not None:
            result = method(request, view, action, arg)
        else:
            result = method(request, view, action)

        log.debug('condition=%s', condition)
        log.debug('method_name=%s', method_name)
        log.debug('method=%s', method)
        log.debug('request=%s', request)
        log.debug('view=%s', view)
        log.debug('action=%s', action)
        log.debug('result=%s', result)

        if type(result) is not bool:
            raise AccessPolicyException(
                "condition '%s' must return true/false, not %s"
                % (condition, type(result))
            )

        return result

    def _get_statements_matching_principal(
        self, request, statements: List[dict]
    ) -> List[dict]:
        user = request.user
        user_roles = None
        matched = []

        for statement in statements:
            log.debug("statement: %s", statement)

            principals = statement["principal"]
            found = False

            log.debug('principals: %s', principals)

            if "*" in principals:
                found = True
            elif "authenticated" in principals:
                found = not user.is_anonymous
            elif "anonymous" in principals:
                found = user.is_anonymous
            elif self.id_prefix + str(user.pk) in principals:
                found = True
            else:
                log.debug("No '*', 'authenticated', 'anonymous', or user id in %s", principals)
                log.debug('trying groups now')
                log.debug("user_roles: %s", user_roles)
                log.debug("request.auth: %s", pf(request.auth))
                if not user_roles:
                    user_roles = self.get_user_group_values(user)

                log.debug('user_roles / groups: %s', user_roles)
                for user_role in user_roles:
                    log.debug('group_prefix %s + user_role %s: %s', self.group_prefix,
                              user_role, self.group_prefix + user_role)
                    if self.group_prefix + user_role in principals:
                        found = True
                        break

            log.debug("found: %s", found)
            if found:
                log.debug("matched %s", statement)
                matched.append(statement)

        return matched


class AccessPolicyBase(AccessPolicyVerboseMixin, AccessPolicy):
    def _get_statements(self, deployment_mode):
        return STATEMENTS[deployment_mode]

    def get_policy_statements(self, request, view):
        statements = self._get_statements(settings.GALAXY_DEPLOYMENT_MODE)
        return statements.get(self.NAME, [])

    # used by insights access policy
    def has_rh_entitlements(self, request, view, permission):
        log.debug('request: %s', request)
        log.debug('permission: %s', permission)
        log.debug('request.auth: %s', request.auth)
        if not isinstance(request.auth, dict):
            return False
        header = request.auth.get('rh_identity')
        log.debug('header: %s', header)
        if not header:
            return False
        entitlements = header.get('entitlements', {})
        entitlement = entitlements.get(settings.RH_ENTITLEMENT_REQUIRED, {})
        return entitlement.get('is_entitled', False)

    # # used by insights access policy
    # def has_rh_entitlements(self, request, view, permission):
    #     if not isinstance(request.auth, dict):
    #         return False
    #     header = request.auth.get('rh_identity')
    #     if not header:
    #         return False
    #     entitlements = header.get('entitlements', {})
    #     entitlement = entitlements.get(settings.RH_ENTITLEMENT_REQUIRED, {})
    #     return entitlement.get('is_entitled', False)


class NamespaceAccessPolicy(AccessPolicyBase):
    NAME = 'NamespaceViewSet'


class CollectionAccessPolicy(AccessPolicyBase):
    NAME = 'CollectionViewSet'

    def can_update_collection(self, request, view, permission):
        collection = view.get_object()
        namespace = models.Namespace.objects.get(name=collection.namespace)
        return request.user.has_perm('galaxy.upload_to_namespace', namespace)

    def can_create_collection(self, request, view, permission):
        data = view._get_data(request)
        try:
            namespace = models.Namespace.objects.get(name=data['filename'].namespace)
        except models.Namespace.DoesNotExist:
            raise NotFound('Namespace in filename not found.')
        return request.user.has_perm('galaxy.upload_to_namespace', namespace)


class CollectionRemoteAccessPolicy(AccessPolicyBase):
    NAME = 'CollectionRemoteViewSet'


class UserAccessPolicy(AccessPolicyBase):
    NAME = 'UserViewSet'

    def is_current_user(self, request, view, action):
        log.debug("request.user %s == view.get_object(): %s", request.user, view.get_object())
        return request.user == view.get_object()

    def get_user_group_values(self, user) -> List[str]:
        log.debug("user: %s", user)
        log.debug("user dict:\n%s", pf(user.__dict__))
        res = super().get_user_group_values(user)
        log.debug("res: %s", res)
        return res
        # return list(user.roles.values_list("title", flat=True))

    def has_groups_param_obj_perms(self, request, view, action, permission):
        """
        Checks if the current user has object-level permission on the ``groups`` object.

        The object in this case is the one specified by the ``remote`` parameter. For example when
        syncing the ``remote`` parameter is passed in as an argument.

        """
        log.debug("permission: %s", permission)

        user_instance = view.get_object()
        log.debug("user_instance: %s", user_instance)
        log.debug("request.user: %s", request.user)

        user_serializer = UserSerializer()
        log.debug("user_serializer: %r", user_serializer)

        serializer = UserSerializer(data=request.data, context={"request": request})
        # serializer = UserSerializer(user_instance, context={"request": request})
        log.debug("serializer: %r", serializer)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as exc:
            log.exception(exc)
            raise

        log.debug("validated_data\n%s", pf(serializer.validated_data))

        groups = serializer.validated_data.get("groups")
        log.debug('groups: %s', groups)

        res = request.user.has_perm(permission, groups)
        log.debug('res: %s', res)

        return res


class MyUserAccessPolicy(UserAccessPolicy):
    NAME = 'MyUserViewSet'


class SyncListAccessPolicy(AccessPolicyBase):
    NAME = 'SyncListViewSet'


class MySyncListAccessPolicy(AccessPolicyBase):
    NAME = 'MySyncListViewSet'


class TagsAccessPolicy(AccessPolicyBase):
    NAME = 'TagViewSet'


class TaskAccessPolicy(AccessPolicyBase):
    NAME = 'TaskViewSet'


class LoginAccessPolicy(AccessPolicyBase):
    NAME = 'LoginView'


class LogoutAccessPolicy(AccessPolicyBase):
    NAME = 'LogoutView'


class TokenAccessPolicy(AccessPolicyBase):
    NAME = 'TokenView'


class GroupAccessPolicy(AccessPolicyBase):
    NAME = 'GroupViewSet'


class DistributionAccessPolicy(AccessPolicyBase):
    NAME = 'DistributionViewSet'


class MyDistributionAccessPolicy(AccessPolicyBase):
    NAME = 'MyDistributionViewSet'
