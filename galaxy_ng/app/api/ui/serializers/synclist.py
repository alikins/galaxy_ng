import logging

from django.db import transaction

from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from pulp_ansible.app.models import Collection

from galaxy_ng.app import models


log = logging.getLogger(__name__)


class SyncListCollectionSummarySerializer(serializers.Serializer):
    namespace = serializers.CharField(max_length=64)
    name = serializers.CharField(max_length=64)


class SyncListSerializer(serializers.ModelSerializer):
    namespaces = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=models.Namespace.objects.all()
    )

    collections = SyncListCollectionSummarySerializer(many=True)

    groups = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=models.Group.objects.all()
    )

    users = serializers.SlugRelatedField(
        many=True, slug_field="username", queryset=models.User.objects.all()
    )

    @transaction.atomic
    def create(self, validated_data):
        collections_data = validated_data.pop("collections")

        namespaces_data = validated_data.pop("namespaces")

        users_data = validated_data.pop("users")
        groups_data = validated_data.pop("groups")

        instance = models.SyncList.objects.create(**validated_data)

        collections = []
        for collection_data in collections_data:
            try:
                collections.append(Collection.objects.get(**collection_data))
            except Collection.DoesNotExist:
                errmsg = \
                    'Collection "{namespace}.{name}" not found while creating synclist {synclist}'
                raise ValidationError(
                    errmsg.format(namespace=collection_data["namespace"],
                                  name=collection_data["name"],
                                  synclist=instance.name))

        instance.collections.clear()
        instance.collections.set(collections)

        instance.namespaces.add(*namespaces_data)

        instance.groups.set(groups_data)
        instance.users.set(users_data)

        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        collections_data = validated_data.get("collections")

        namespaces_data = validated_data.get("namespaces")

        users_data = validated_data.get("users")

        if users_data:
            instance.users.set(users_data)

        groups_data = validated_data.get("groups")
        if groups_data:
            instance.groups.set(groups_data)

        instance.policy = validated_data.get("policy", instance.policy)

        instance.name = validated_data.get("name", instance.name)

        new_collections = []
        for collection_data in collections_data:
            try:
                new_collections.append(Collection.objects.get(**collection_data))
            except Collection.DoesNotExist:
                errmsg = \
                    'Collection "{namespace}.{name}" not found while updating synclist {synclist}'
                raise ValidationError(
                    errmsg.format(namespace=collection_data["namespace"],
                                  name=collection_data["name"],
                                  synclist=instance.name))
        instance.collections.set(new_collections)

        instance.namespaces.set(namespaces_data)

        instance.save()

        return instance

    class Meta:
        model = models.SyncList
        fields = [
            "id",
            "name",
            "policy",
            "repository",
            "collections",
            "namespaces",
            "users",
            "groups",
        ]
