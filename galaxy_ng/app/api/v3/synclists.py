import logging

from rest_framework import serializers

from pulp_ansible.app import models as pulp_ansible_models

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app import models


log = logging.getLogger(__name__)


class SyncListCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = pulp_ansible_models.Collection
        fields = ['namespace', 'name']


class SyncListSerializer(serializers.ModelSerializer):
    # namespaces = serializers.PrimaryKeyRelatedField(many=True, allow_null=True,
    #                                                queryset=models.Namespace.objects.all())
    namespaces = serializers.SlugRelatedField(many=True, slug_field='name',
                                              queryset=models.Namespace.objects.all())

    # collections = serializers.PrimaryKeyRelatedField(many=True, allow_null=True,
    #                                                 queryset=onsible_models.Collection.objects.all())

    collections = SyncListCollectionSerializer(many=True)
    # collections = serializers.SlugRelatedField(many=True, slug_field='name',
    #                                           allow_null=True,
    #                                           source='*',
    #                                           queryset=pulp_ansible_models.Collection.objects.all())

    def get_collection_label(self):
        pass

    def create(self, validated_data):
        collections_data = validated_data.pop('collections')
        log.debug('collections_data: %s', collections_data)

        namespaces_data = validated_data.pop('namespaces')
        log.debug('ns_data: %s', namespaces_data)

        instance = models.SyncList.objects.create(**validated_data)
        for collection_data in collections_data:
            instance.collections.add(pulp_ansible_models.Collection.objects.get(**collection_data))

        for namespace_data in namespaces_data:
            log.debug('namespace_data: %s %s', namespace_data, type(namespace_data))
            # instance.namespaces.add(models.Namespace.objects.get(**namespace_data))
            instance.namespaces.add(namespace_data)
        return instance

    class Meta:
        model = models.SyncList
        fields = ['id', 'name', 'policy',
                  'repository', 'collections', 'namespaces']


class SyncListViewSet(api_base.ModelViewSet):
    queryset = models.SyncList.objects.all()
    serializer_class = SyncListSerializer
