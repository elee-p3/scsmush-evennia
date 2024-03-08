# Generated by Django 4.2.9 on 2024-03-01 06:32

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("objects", "0014_defaultobject_defaultcharacter_defaultexit_and_more"),
        ("boards", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="readers",
            field=models.ManyToManyField(
                related_name="posts_read", to="objects.objectdb"
            ),
        ),
    ]
