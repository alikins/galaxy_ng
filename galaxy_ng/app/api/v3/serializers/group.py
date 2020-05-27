from rest_framework import serializers

from galaxy_ng.app.models import auth as auth_models


class GroupSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False, allow_blank=False)

    # class Meta:
    #     model = auth_models.Group
    #     fields = (
    #         'id',
    #         'name'
    #     )
    #     read_only_fields = ("id", "name")
