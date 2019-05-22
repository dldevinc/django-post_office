# Generated by Django 2.2.1 on 2019-05-22 13:21

from django.db import migrations
import post_office.fields


class Migration(migrations.Migration):

    dependencies = [
        ('post_office', '0008_attachment_headers'),
    ]

    operations = [
        migrations.AlterField(
            model_name='email',
            name='to',
            field=post_office.fields.CommaSeparatedEmailField(default='', verbose_name='Email To'),
        ),
    ]
