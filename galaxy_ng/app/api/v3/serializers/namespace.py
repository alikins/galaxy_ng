import logging
import re

from django.db import transaction

from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from galaxy_ng.app import models
from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.api.v3.serializers.group import GroupSummarySerializer

log = logging.getLogger(__name__)


class NamespaceLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NamespaceLink
        fields = ('name', 'url')


class NamespaceSerializer(serializers.ModelSerializer):
    links = NamespaceLinkSerializer(many=True, required=False)

    groups = GroupSummarySerializer(many=True)

    class Meta:
        model = models.Namespace
        fields = (
            'id',
            'name',
            'company',
            'email',
            'avatar_url',
            'description',
            'links',
            'groups',
            'resources'
        )

    # replace with a NamespaceNameSerializer and validate_name() ?
    def validate_name(self, name):
        if not name:
            raise ValidationError(detail={
                'name': "Attribute 'name' is required"})
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            raise ValidationError(detail={
                'name': 'Name can only contain [A-Za-z0-9_]'})
        if len(name) <= 2:
            raise ValidationError(detail={
                'name': 'Name must be longer than 2 characters'})
        if name.startswith('_'):
            raise ValidationError(detail={
                'name': "Name cannot begin with '_'"})
        return name

    def create(self, validated_data):
        log.debug('serializer.create validated_data=%s', validated_data)

        links_data = validated_data.pop('links', [])
        groups_data = validated_data.pop('groups', None)

        instance = models.Namespace.objects.create(**validated_data)

        ngs = auth_models.Group.objects.in_bulk([x['name'] for x in groups_data], field_name="name")

        # create NamespaceLink objects if needed
        new_links = []
        for link_data in links_data:
            ns_link, created = models.NamespaceLink.objects.get_or_create(**link_data)
            new_links.append(ns_link)

        instance.groups.set(list(ngs.values()))
        instance.links.set(new_links)

        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        links = validated_data.pop('links', None)

        if links is not None:
            instance.set_links(links)

        groups_data = validated_data.pop('groups', [])

        new_groups = []
        for group_data in groups_data:
            new_groups.append(auth_models.Group.objects.get(**group_data))

        if groups_data:
            instance.groups.clear()
            instance.groups.set(new_groups)

        instance = super().update(instance, validated_data)

        instance.save()

        return instance


class NamespaceSummarySerializer(NamespaceSerializer):
    """NamespaceSerializer but without 'links' or 'resources'.

    For use in _ui/collection detail views."""

    class Meta:
        model = models.Namespace
        fields = (
            'id',
            'name',
            'company',
            'email',
            'avatar_url',
            'description',
        )

        read_only_fields = ('name', )
