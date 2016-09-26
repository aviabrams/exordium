# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-22 01:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exordium', '0008_auto_20160921_2032'),
    ]

    operations = [
        migrations.AddField(
            model_name='song',
            name='raw_composer',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.AddField(
            model_name='song',
            name='raw_conductor',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.AddField(
            model_name='song',
            name='raw_group',
            field=models.CharField(default='', max_length=255),
        ),
    ]
