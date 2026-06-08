from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prototype', '0005_alter_expense_id_alter_group_id_alter_group_members_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='description',
            field=models.CharField(blank=True, default='', max_length=300),
        ),
        migrations.AddField(
            model_name='expense',
            name='description',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
    ]
