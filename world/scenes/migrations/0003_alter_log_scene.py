# Generated by Django 3.2.12 on 2022-02-18 07:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('scenes', '0002_auto_20220218_0655'),
    ]

    operations = [
        migrations.AlterField(
            model_name='log',
            name='scene',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='scenes.scene'),
        ),
    ]
