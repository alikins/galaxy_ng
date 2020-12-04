from django.core.exceptions import PermissionDenied
from django.http import Http404

from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.settings import api_settings

import logging
log = logging.getLogger(__name__)


def _get_errors(detail, *, status, title, source=None, context=None):
    if isinstance(detail, list):
        for item in detail:
            yield from _get_errors(item, status=status, title=title, source=source)
    elif isinstance(detail, dict):
        for key, value in detail.items():
            yield from _get_errors(value, status=status, title=title, source=key)
    else:
        error = {
            'status': str(status),
            'code': detail.code,
            'title': title,
        }

        # TODO: if the context has a request object, use it to build a
        #       unique error id so we can send it to client and log it and
        #       cross reference later

        if title != detail:
            error['detail'] = str(detail)
        if source and source != api_settings.NON_FIELD_ERRORS_KEY:
            error['source'] = {'parameter': source}

        yield error


def _handle_drf_api_exception(exc, context):
    headers = {}
    if getattr(exc, 'auth_header', None):
        headers['WWW-Authenticate'] = exc.auth_header
    if getattr(exc, 'wait', None):
        headers['Retry-After'] = '%d' % exc.wait

    title = exc.__class__.default_detail
    errors = _get_errors(exc.detail, status=exc.status_code, title=title, context=context)
    data = {'errors': list(errors)}
    return Response(data, status=exc.status_code, headers=headers)


def exception_handler(exc, context):
    """Custom exception handler."""

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    # Handle drf permission exceptions as drf exceptions extracting more detail
    elif isinstance(exc,
                    (exceptions.PermissionDenied,
                     exceptions.AuthenticationFailed,
                     exceptions.NotAuthenticated)):
        return _handle_drf_api_exception(exc, context)
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, exceptions.APIException):
        return _handle_drf_api_exception(exc, context)

    return None
