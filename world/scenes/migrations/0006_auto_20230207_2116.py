# Generated by Django 2.2.28 on 2023-02-08 03:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scenes', '0005_auto_20220401_0627'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='scene',
            options={'ordering': ['-start_time']},
        ),
        migrations.AlterField(
            model_name='logentry',
            name='type',
            field=models.IntegerField(choices=[(1, 'Emit'), (2, 'Say'), (3, 'Pose'), (4, 'Dice'), (5, 'Combat')]),
        ),
    ]