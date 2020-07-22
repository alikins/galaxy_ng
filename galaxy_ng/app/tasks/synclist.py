import logging

# from galaxy.app import models

log = logging.getLogger(__name__)


def curate_all_synclist_repository(upstream_repository_version_pk, **kwargs):
    """When upstream_repository has changed, update all synclists repos associated with it.

    The synclist repos will be updated to upstream_repository_version.

    This will create a lot of curate_synclist_repository tasks.
    It will create a TaskGroup containing those tasks.

    If neccasary, it may create many TaskGroups.

    It may need to schedule a series of TaskGroups, potentially
    in order of priority.

    This task need to be cancelable."""
    log.debug("upstream_repository_version_pk: %s", upstream_repository_version_pk)
    log.debug("kwargs: %r", kwargs)


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
    # tasks

    log.debug("synclist_pk: %s", synclist_pk)
    log.debug("kwargs: %r", kwargs)
