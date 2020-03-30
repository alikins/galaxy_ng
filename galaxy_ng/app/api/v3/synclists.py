import logging

from rest_framework import serializers

from pulp_ansible.app import models as pulp_ansible_models

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app import models


log = logging.getLogger(__name__)


class SyncListSerializer(serializers.ModelSerializer):
    namespaces = serializers.PrimaryKeyRelatedField(many=True, allow_null=True,
                                                    queryset=models.Namespace.objects.all())
    collections = serializers.PrimaryKeyRelatedField(many=True, allow_null=True,
                                                     queryset=pulp_ansible_models.Collection.objects.all())

    class Meta:
        model = models.SyncList
        fields = ['id', 'name', 'policy',
                  'repository', 'collections', 'namespaces']


class SyncListViewSet(api_base.ModelViewSet):
    queryset = models.SyncList.objects.all()
    serializer_class = SyncListSerializer
