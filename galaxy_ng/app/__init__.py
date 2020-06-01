from django.db.models.signals import post_save

from pulpcore.plugin import PulpPluginAppConfig


class PulpGalaxyPluginAppConfig(PulpPluginAppConfig):
    """Entry point for the galaxy plugin."""

    name = "galaxy_ng.app"
    label = "galaxy"

    def ready(self):
        super().ready()

        from .models import Namespace
        from .signals import namespace_post_save_handler
        post_save.connect(namespace_post_save_handler, sender=Namespace)
