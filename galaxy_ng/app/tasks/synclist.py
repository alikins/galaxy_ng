import logging
import pprint
import time

from django.db.models import F

from pulpcore.app.models import (
    CreatedResource,
    GroupProgressReport,
    # RepositoryVersion,
    Task,
    TaskGroup,
)

from pulpcore.app.tasks.repository import add_and_remove
from pulpcore.tasking.tasks import enqueue_with_reservation

from pulp_ansible.app.models import (
    AnsibleRepository,
    CollectionVersion,
)

from galaxy_ng.app import models
from galaxy_ng.app.models.progress import LoggingProgressReport


log = logging.getLogger(__name__)

# progress_report_factory = ProgressReport
progress_report_factory = LoggingProgressReport.create

pf = pprint.pformat


def curate_all_synclist_repository(upstream_repository_name, **kwargs):
    """When upstream_repository has changed, update all synclists repos associated with it.

    The synclist repos will be updated to upstream_repository

    This will create a lot of curate_synclist_repository tasks.
    It will create a TaskGroup containing those tasks.

    If neccasary, it may create many TaskGroups.

    It may need to schedule a series of TaskGroups, potentially
    in order of priority.

    This task need to be cancelable."""
    task_start = time.time()
    upstream_repository = AnsibleRepository.objects.get(name=upstream_repository_name)
    synclist_qs = models.SyncList.objects.filter(upstream_repository=upstream_repository)

    log.debug("upstream_repository_name: %s", upstream_repository_name)
    log.debug("kwargs: %r", kwargs)

    task_group = TaskGroup.objects.create(
        description=f"Curating all synclists repos that curate from {upstream_repository_name}")
    task_group.save()
    CreatedResource.objects.create(content_object=task_group)
    current_task = Task.current()
    current_task.task_group = task_group
    current_task.save()

    GroupProgressReport(
        message="Synclists curating upstream repo",
        code="synclist.curate",
        total=synclist_qs.count(),
        task_group=task_group).save()

    with progress_report_factory(message="Synclists curating upstream repo task",
                                 code="synclist.curate.log",
                                 total=synclist_qs.count()) as task_progress_report:

        for synclist in synclist_qs:
            log.debug("curating synclist repo %s from upstream repo %s",
                      synclist, upstream_repository)
            log.debug("synclist %s policy=%s", synclist, synclist.policy)
            log.debug("sycnlist %s collections=%s", synclist, synclist.collections.all())
            log.debug("synclist %s namespaces=%s", synclist, synclist.namespaces.all())

            # TODO: filter down to just synclists that have a synclist repo
            # locks need to be Model or str not int
            locks = [str(synclist.id)]

            task_args = (synclist.id,)
            task_kwargs = {}

            subtask = enqueue_with_reservation(curate_synclist_repository,
                                               locks,
                                               args=task_args,
                                               kwargs=task_kwargs,
                                               task_group=task_group,
                                               )
            task_progress_report.increment()
            log.debug('subtask: %s', subtask)

            progress_report = task_group.group_progress_reports.filter(code='synclist.curate')
            log.debug('progress_report: %s', progress_report)

            progress_report.update(done=F('done') + 1)

    log.debug('progress_report: %s', progress_report)
    log.debug("Finishing curating %s synclist repos based on %s update",
              synclist_qs.count(), upstream_repository)

    task_group.finish()
    log.debug('Big Task finished after %s seconds', time.time() - task_start)


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
    task_start = time.time()

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

    log.debug('Task finished after %s seconds', time.time() - task_start)
    log.debug('Task finished after %s seconds', time.time() - task_start)

    # locks need to be Model or str not int
    log.debug('synclist.repository: %s', synclist.repository)

    locks = [synclist.repository]

    # FIXME: add enum constants to models.SyncList
    if synclist.policy == 'exclude':
        latest_upstream = upstream_repository.latest_version()

        if latest_upstream:
            # all the content pk's in the latest version of the upstream repository
            latest_upstream_content_pks = \
                [str(vpk) for vpk in latest_upstream.content.values_list("pk", flat=True)]

        log.debug('latest_upstrean_content_pks:\n%s',
                  pf(sorted(latest_upstream_content_pks)))

        log.debug('latest_upstream: %s %s', latest_upstream, type(latest_upstream))

        excluded_content_pks = \
            CollectionVersion.objects.filter(collection_id__in=synclist.collections.all(),
                                             is_highest=True)

        excluded_this_repo_version = \
            latest_upstream.content.filter(ansible_collectionversion__in=excluded_content_pks)
        log.debug('excluded_this_repo_version: %s', excluded_this_repo_version)

        log.debug('excluded_content_pks:\n%s',
                  pf(excluded_content_pks))

        expected_synclist_repo_content_unit_uuids = \
            set(latest_upstream_content_pks) - set(excluded_content_pks)

        expected_synclist_repo_content_units = \
            [str(exp) for exp in sorted(list(expected_synclist_repo_content_unit_uuids))]

        log.debug('expected_synclist_repo_content_units:\n%s',
                  pf(sorted(list(expected_synclist_repo_content_units))))

        task_kwargs = {'base_version_pk': str(upstream_repository.latest_version().pulp_id),
                       'repository_pk': str(synclist.repository.pulp_id),
                       'add_content_units': [],
                       'remove_content_units': excluded_content_pks,
                       }

        log.debug('task_kwargs: %s', pf(task_kwargs))

        subtask = enqueue_with_reservation(add_and_remove,
                                           locks,
                                           kwargs=task_kwargs,
                                           )

        log.debug('subtask(exclude): %s', subtask)

        return

    if synclist.policy == 'include':
        latest_upstream = upstream_repository.latest_version()

        if latest_upstream:
            # all the content pk's in the latest version of the upstream repository
            latest_upstream_content_pks = \
                [str(vpk) for vpk in latest_upstream.content.values_list("pk", flat=True)]
        log.debug('latest_upstrean_content_pks:\n%s',
                  pf(sorted(latest_upstream_content_pks)))

        added_all_content_pks = \
            CollectionVersion.objects.filter(collection_id__in=synclist.collections.all(),
                                             is_highest=True)

        log.debug('added_all_content_pks: %s', added_all_content_pks)

        added_this_repo_version = \
            latest_upstream.content.filter(ansible_collectionversion__in=added_all_content_pks)

        log.debug('added_this_repo_version: %s', added_this_repo_version)

        log.debug('added_all_content_pks:\n%s',
                  pf(added_all_content_pks))

        task_kwargs = {'repository_pk': str(synclist.repository.pulp_id),
                       'add_content_units': added_all_content_pks,
                       # remove all existing content before adding add_content_units
                       'remove_content_units': ['*']}

        log.debug('task_kwargs: %s', task_kwargs)

        subtask = enqueue_with_reservation(add_and_remove,
                                           locks,
                                           kwargs=task_kwargs,
                                           )

        log.debug('subtask(include): %s', subtask)
        return
