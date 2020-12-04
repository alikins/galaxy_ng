
# This is based heavily on https://github.com/rsinger86/drf-access-policy
# in particular:
# https://github.com/rsinger86/drf-access-policy/blob/master/rest_access_policy/access_policy.py
#
# drf-access-policy is MIT licensed
# https://github.com/rsinger86/drf-access-policy/blob/master/LICENSE.md
#
# This version is based on commit 9d7c34b38628c1fa0b888c201e6476b55051a4ab
# (~0.8.0 of rest_access_policy)
#

import logging
from typing import List

from rest_access_policy import AccessPolicyException


log = logging.getLogger(__name__)


class AccessPolicyVerboseMixin:
    """Mixin to make AccessPolicy checks verbose

    This has to reimplement / cut&paste most of rest_access_policy.AccessPolicy
    to instrument the low level permissions checks.
    """

    def has_permission(self, request, view):
        result = super().has_permission(request, view)
        log.debug('"%s" perm check was %s for "%s %s" view="%s-%s-%s" for user="%s" with groups=%s',
                  self.NAME,
                  result,
                  request._request.method,
                  request._request.path,
                  getattr(view, 'basename', 'NotAViewSet'),
                  getattr(view, 'action', 'NotAViewSet'),
                  getattr(view, 'detail', 'NotAViewSet'),
                  request.user, ','.join([x.name for x in request.user.groups.all()]),
                  )
        return result

    def has_object_permission(self, request, view, obj):
        result = super().has_object_permission(request, view, obj)
        log.debug('"%s" %s %s view=%s-%s-%s for user=%s, groups=%s obj=%s had result: %s',
                  self.NAME,
                  request._request.method,
                  request._request.path,
                  view.basename, view.action, view.detail,
                  request.user,
                  ','.join([x.name for x in request.user.groups.all()]),
                  obj,
                  result)
        return result

    def _evaluate_statements(
        self, statements: List[dict], request, view, action: str
    ) -> bool:

        statements = self._normalize_statements(statements)

        user = request.user
        user_groups = self.get_user_group_values(user)

        matched = self._get_statements_matching_principal(request, statements)
        matched_principals = set()
        for match in matched:
            for principal in match['principal']:
                matched_principals.add(principal)

        log.debug('"%s" user "%s" in groups %s matched access policy principals %s',
                  self.NAME,
                  request.user,
                  ",".join(['"%s"' % ug for ug in user_groups]),
                  matched_principals)

        matched = self._get_statements_matching_action(request, action, matched)

        log.debug('"%s" action "%s" matched statements %s',
                  self.NAME, action, matched)

        matched = self._get_statements_matching_context_conditions(
            request, view, action, matched
        )

        denied = [_ for _ in matched if _["effect"] != "allow"]

        if len(matched) == 0 or len(denied) > 0:
            return False

        return True

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

        if type(result) is not bool:
            raise AccessPolicyException(
                "condition '%s' must return true/false, not %s"
                % (condition, type(result))
            )

        res_blurb = "failed"
        if result:
            res_blurb = "passed"

        log.debug('"%s" action "%s" for user "%s" %s conditions "%s"',
                  self.NAME,
                  action,
                  request.user,
                  res_blurb,
                  condition,
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

            if "*" in principals:
                found = True
            elif "authenticated" in principals:
                found = not user.is_anonymous
            elif "anonymous" in principals:
                found = user.is_anonymous
            elif self.id_prefix + str(user.pk) in principals:
                found = True
            else:
                log.debug("No '*', 'authenticated', 'anonymous', or user id in %s,"
                          + "trying groups %s",
                          principals,
                          user_roles)

                if not user_roles:
                    user_roles = self.get_user_group_values(user)

                for user_role in user_roles:
                    if self.group_prefix + user_role in principals:
                        found = True
                        break

            if found:
                matched.append(statement)

        return matched
