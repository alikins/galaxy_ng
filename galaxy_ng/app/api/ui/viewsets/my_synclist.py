import logging

from galaxy_ng.app import models
from galaxy_ng.app.api import permissions
from .synclist import SyncListViewSet

log = logging.getLogger(__name__)


class MySyncListViewSet(SyncListViewSet):
    def get_queryset(self):
        """
        Returns all synclists for the user.
        """
        log.debug('self.request.user: %s', self.request.user)
        if permissions.IsPartnerEngineer().has_permission(self.request, self):
            log.debug('Viewing mysynclist as partner user=%s, groups=%s',
                      self.request.user,
                      self.request.user.groups)
            return models.SyncList.objects.all()
        else:
            log.debug('Viewing mysynclist as user=%s with groups=%s',
                      self.request.user,
                      self.request.user.groups)
            return models.SyncList.objects.filter(
                groups__in=self.request.user.groups.all()
            )
