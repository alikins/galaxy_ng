from django.db import models
from django.urls import reverse
from django_lifecycle import LifecycleModel

from pulpcore.plugin.models import AutoDeleteObjPermsMixin
from .namespace import Namespace


__all__ = (
    "CollectionImport",
)


class CollectionImport(LifecycleModel, AutoDeleteObjPermsMixin):
    """
    A model representing a mapping between pulp task id and task parameters.

    Fields:
        task_id: Task UUID.
        created_at: Task creation date time.
        name: Collection name.
        version: Collection version.

    Relations:
        namespace: Reference to a namespace.
    """
    task_id = models.UUIDField(primary_key=True)

    created_at = models.DateTimeField()

    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE)
    name = models.CharField(max_length=64, editable=False)
    version = models.CharField(max_length=32, editable=False)

    class Meta:
        ordering = ['-task_id']

    def get_absolute_url(self):
        return reverse('galaxy:api:content:collection-import', args=[str(self.task_id)])

    def label(self):
        return f"{self.namespace}.{self.name}"

    def label_and_version(self):
        return f"{self.namespace}.{self.name}-{self.version}"
