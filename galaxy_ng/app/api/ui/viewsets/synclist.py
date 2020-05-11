import logging

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app import models
from galaxy_ng.app.api.ui import serializers


log = logging.getLogger(__name__)


class SyncListViewSet(api_base.ModelViewSet):
    queryset = models.SyncList.objects.all()
    serializer_class = serializers.SyncListSerializer

    def get_queryset(self):
        return models.SyncList.objects.all()
