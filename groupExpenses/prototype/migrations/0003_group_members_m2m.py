from django.conf import settings
from django.db import migrations, models


def copy_members(apps, schema_editor):
    Group = apps.get_model('prototype', 'Group')
    User = apps.get_model(settings.AUTH_USER_MODEL)

    for group in Group.objects.all():
        members = getattr(group, 'members', []) or []
        for username in members:
            user = User.objects.filter(username__iexact=username).first()
            if user:
                group.members_temp.add(user)


class Migration(migrations.Migration):
    dependencies = [
        ('prototype', '0002_group_owner'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='members_temp',
            field=models.ManyToManyField(blank=True, related_name='member_groups_temp', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(copy_members, reverse_code=migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='group',
            name='members',
        ),
        migrations.RenameField(
            model_name='group',
            old_name='members_temp',
            new_name='members',
        ),
    ]
