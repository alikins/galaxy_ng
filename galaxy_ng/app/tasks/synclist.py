import logging

from pulp_ansible.app.models import AnsibleRepository

from galaxy_ng.app import models

log = logging.getLogger(__name__)


def curate_all_synclist_repository(upstream_repository_pk, **kwargs):
    """When upstream_repository has changed, update all synclists repos associated with it.

    The synclist repos will be updated to upstream_repository

    This will create a lot of curate_synclist_repository tasks.
    It will create a TaskGroup containing those tasks.

    If neccasary, it may create many TaskGroups.

    It may need to schedule a series of TaskGroups, potentially
    in order of priority.

    This task need to be cancelable."""

    upstream_repository = AnsibleRepository.objects.get(pk=upstream_repository_pk)
    synclist_qs = models.SyncList.objects.filter(upstream_repository=upstream_repository)
    log.debug("upstream_repository_pk: %s", upstream_repository_pk)
    log.debug("kwargs: %r", kwargs)
    for synclist in synclist_qs:
        log.debug("curating synclist repo %s from %s", synclist, upstream_repository)
        log.debug("curating %s based on policy=%s", synclist, synclist.policy)
        log.debug("curating %s for collections=%s", synclist, synclist.collections)
        log.debug("curating %s for namespaces=%s", synclist, synclist.namespaces)

    log.debug("Finishing curating %s synclist repos based on %s update",
              synclist_qs.count(), upstream_repository)


def curate_synclist_repository(synclist_pk, **kwargs):
    """Update a synclist repo based on it's policy and spec.

    Update a curated synclist repo to use the latest versions from
    upstream as specified by the synclist's policy and it's collections
    and namespaces fields.

    This is intended to work on one synclist and synclist repo at a time.
    """

    # Lookup synclist by synclist_pk, which will include the
    # synclist repo and the upstream_repo.

    # For 'include' policy cases, move the latest version of the specified collections to
    # the synclist repos.
    #   - Apply the collection 'specs' to the upstream repository version to
    #     filter down to candidates

    # For 'exclude' policy cases, updated everything except for the excludes.

    # moving/updating means creating at least a 'added' and 'removed' delta and using
    # repository /move (ideally in as few steps as possible to limit number RepoVersions

    # This likely means enqueue galaxy.app.tasks.promotion.[add|remote]_content_to_repository
    # tasks. Or possible pulpcore.app.tasks.repository.add_and_remove()

    # Also see pulp_ansible.app.tasks.test_tasks for examples of tasks that operate over many repos
    # and pulpcore.app.tasks.import for examples of tasks that work on lots of Content

    # And pulp_ansible.tests.performance
    log.debug("synclist_pk: %s", synclist_pk)
    log.debug("kwargs: %r", kwargs)

    synclist = models.SyncList.objects.get(pk=synclist_pk)
    log.debug('synclist instance: %s', synclist)

    upstream_repository = synclist.upstream_repository

    log.debug("curating synclist repo %s from %s", synclist, upstream_repository)
    log.debug("synclist %s policy=%s", synclist, synclist.policy)
    log.debug("synclist %s collections(repr)=%r", synclist, synclist.collections)
    log.debug("synclist %s collections.all()=%s", synclist, synclist.collections.all())
    log.debug("synclsit %s collections.count=%s", synclist, synclist.collections.count())
    log.debug("synclist %s namespaces=%s", synclist, synclist.namespaces.all())
