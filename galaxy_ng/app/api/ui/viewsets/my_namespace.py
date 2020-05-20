
from galaxy_ng.app import models
from galaxy_ng.app.api import permissions
from galaxy_ng.app.api.v3.viewsets.namespace import NamespaceViewSet


class MyNamespaceViewSet(NamespaceViewSet):
    def get_queryset(self):
        # All namespaces for users in the partner-engineers groups

        if permissions.IsPartnerEngineer().has_permission(self.request, self):
            queryset = models.Namespace.objects.all()
            return queryset

        # Just the namespaces with groups the user is in
        queryset = models.Namespace.objects.filter(
            groups__in=self.request.user.groups.all())
        return queryset
