import logging

from rest_framework import serializers

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api import permissions
from galaxy_ng.app import models
# from galaxy_ng.app.api.v3 import serializers


log = logging.getLogger(__name__)


class SyncListSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SyncList
        fields = ['id', 'name', 'policy',
                  'repository', 'collections', 'namespaces']


class SyncListViewSet(api_base.ModelViewSet):
    queryset = models.SyncList.objects.all()
    serializer_class = SyncListSerializer


