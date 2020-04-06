import logging
import pprint

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

    groups = serializers.SlugRelatedField(many=True,
                                          slug_field='name',
                                          queryset=models.Group.objects.all())

    users = serializers.SlugRelatedField(many=True,
                                         slug_field='username',
                                         queryset=models.User.objects.all())

    def get_collection_label(self):
        pass

    def create(self, validated_data):
        log.debug('self: %s', pprint.pformat(self))
        log.debug('self.__dict__: %s', pprint.pformat(self.__dict__))
        log.debug('validated_data: %s', pprint.pformat(validated_data))
        log.debug('self.instance: %s %s', self.instance, self.instance)

        collections_data = validated_data.pop('collections')

        log.debug('collections_data: %s', collections_data)

        namespaces_data = validated_data.pop('namespaces')

        log.debug('ns_data: %s', namespaces_data)

        users_data = validated_data.pop('users')
        groups_data = validated_data.pop('groups')

        instance = models.SyncList.objects.create(**validated_data)
        for collection_data in collections_data:
            instance.collections.add(pulp_ansible_models.Collection.objects.get(**collection_data))

        for namespace_data in namespaces_data:

            log.debug('namespace_data: %s %s', namespace_data, type(namespace_data))

            # instance.namespaces.add(models.Namespace.objects.get(**namespace_data))
            instance.namespaces.add(namespace_data)

        instance.groups.set(groups_data)
        instance.users.set(users_data)
        # for group_data in validated_data.pop('groups', []):
        #    instance.groups.set

        return instance

    class Meta:
        model = models.SyncList
        fields = ['id', 'name', 'policy',
                  'repository', 'collections',
                  'namespaces',
                  'users', 'groups',
                  ]


class SyncListViewSet(api_base.ModelViewSet):
    queryset = models.SyncList.objects.all()
    serializer_class = SyncListSerializer

    def get_queryset(self):
        log.debug(pprint.pformat(self.__dict__))
        log.debug('perms: %s', self.permission_classes)
        log.debug('auth_classes: %s', self.authentication_classes)
        return models.SyncList.objects.all()
