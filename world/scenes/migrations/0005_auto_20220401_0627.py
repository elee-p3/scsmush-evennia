# Generated by Django 3.2.12 on 2022-04-01 06:27

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('scenes', '0004_auto_20220311_0558'),
    ]

    operations = [
        migrations.AddField(
            model_name='logentry',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='logentry',
            name='type',
            field=models.IntegerField(choices=[(1, 'Emit'), (2, 'Say'), (3, 'Pose'), (4, 'Dice')]),
        ),
    ]
