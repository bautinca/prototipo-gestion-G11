from django.db import migrations, models


def populate_participants(apps, schema_editor):
    Group = apps.get_model('prototype', 'Group')
    Expense = apps.get_model('prototype', 'Expense')

    for expense in Expense.objects.all():
        if expense.transaction_type == 'expense' and not expense.participants:
            group = Group.objects.get(id=expense.group_id)
            expense.participants = [member.username for member in group.members.all()]
            expense.save(update_fields=['participants'])


class Migration(migrations.Migration):

    dependencies = [
        ('prototype', '0003_group_members_m2m'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='participants',
            field=models.JSONField(default=list),
        ),
        migrations.RunPython(populate_participants, reverse_code=migrations.RunPython.noop),
    ]
