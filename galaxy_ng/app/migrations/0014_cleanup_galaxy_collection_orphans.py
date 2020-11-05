from django.db import migrations, models
import django.db.models.deletion

DELETE_ORPHAN_GALAXY_COLLECTION_IMPORTS = """
DELETE
FROM galaxy_collectionimport
WHERE task_id in
    (SELECT task_id
     FROM galaxy_collectionimport
     WHERE task_id not in
         (SELECT task_id
          FROM ansible_collectionimport));
"""

class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0010_add_staging_rejected_repos'),
    ]

    operations = [
        migrations.RunSQL(sql=DELETE_ORPHAN_GALAXY_COLLECTION_IMPORTS,
                          reverse_sql=RunSQL.noop),
    ]
