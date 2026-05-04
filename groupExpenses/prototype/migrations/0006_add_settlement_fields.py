from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prototype', '0005_remove_group_total_alter_group_currency_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='paid_to',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='expense',
            name='transaction_type',
            field=models.CharField(choices=[('expense', 'Gasto'), ('settlement', 'Liquidación')], default='expense', max_length=12),
        ),
    ]
