from galaxy_ng.app.api.v3.viewsets.namespace import (
    MyNamespaceViewSet,
    NamespaceViewSet,
)

from .collection import CollectionViewSet, CollectionVersionViewSet, CollectionImportViewSet
from .tags import TagsViewSet
from .user import UserViewSet, CurrentUserViewSet

__all__ = (
    'NamespaceViewSet',
    'MyNamespaceViewSet',
    'CollectionViewSet',
    'CollectionVersionViewSet',
    'CollectionImportViewSet',
    'TagsViewSet',
    'CurrentUserViewSet',
    'UserViewSet'
)
