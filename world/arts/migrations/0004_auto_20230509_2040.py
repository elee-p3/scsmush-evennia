# Generated by Django 2.2.28 on 2023-05-10 03:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('arts', '0003_auto_20230502_2231'),
    ]

    operations = [
        migrations.AlterField(
            model_name='arts',
            name='characters',
            field=models.ManyToManyField(related_name='arts', to='objects.ObjectDB'),
        ),
    ]
