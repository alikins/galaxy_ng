import logging

from galaxy_ng.app.api.v3.viewsets.namespace import NamespaceViewSet

log = logging.getLogger(__name__)


class UiNamespaceViewSet(NamespaceViewSet):

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.NamespaceSummarySerializer
        elif self.action == 'update':
            return serializers.NamespaceUpdateSerializer
        else:
            return serializers.NamespaceSerializer

