import logging
import pprint
from typing import List

from django.conf import settings
from rest_access_policy import AccessPolicy, AccessPolicyException

from galaxy_ng.app import models

from galaxy_ng.app.access_control.statements import STANDALONE_STATEMENTS, INSIGHTS_STATEMENTS

log = logging.getLogger(__name__)

STATEMENTS = {'insights': INSIGHTS_STATEMENTS,
              'standalone': STANDALONE_STATEMENTS}
pf = pprint.pformat


class AccessPolicyBase(AccessPolicy):
    def _get_statements(self, deployment_mode):
        return STATEMENTS[deployment_mode]

    def get_policy_statements(self, request, view):
        statements = self._get_statements(settings.GALAXY_DEPLOYMENT_MODE)
        return statements.get(self.NAME, [])

    def has_permission(self, request, view):
        result = super().has_permission(request, view)
        log.debug('%s %s view=%s-%s-%s for user=%s with groups=%s and had result: %s',
                  request._request.method,
                  request._request.path,
                  view.basename, view.action, view.detail,
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

    def _evaluate_statements(
        self, statements: List[dict], request, view, action: str
    ) -> bool:
        statements = self._normalize_statements(statements)
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
                log.debug('trying groups now')
                if not user_roles:
                    user_roles = self.get_user_group_values(user)

                log.debug('user_roles / groups: %s', user_roles)
                for user_role in user_roles:
                    log.debug('group_prefix %s + user_role %s: %s', self.group_prefix,
                              user_role, self.group_prefix + user_role)
                    if self.group_prefix + user_role in principals:
                        found = True
                        break

            if found:
                matched.append(statement)

        return matched


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
        namespace = models.Namespace.objects.get(name=data['filename'].namespace)
        return request.user.has_perm('galaxy.upload_to_namespace', namespace)


class CollectionRemoteAccessPolicy(AccessPolicyBase):
    NAME = 'CollectionRemoteViewSet'


class UserAccessPolicy(AccessPolicyBase):
    NAME = 'UserViewSet'

    def is_current_user_or_has_perms(self, request, view, action, permission):
        if (request.user.has_perm(permission)):
            return True

        return self.is_current_user(request, view, action)

    def is_current_user(self, request, view, action):
        return request.user == view.get_object()


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
