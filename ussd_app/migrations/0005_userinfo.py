# Generated by Django 5.1 on 2024-12-23 13:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ussd_app', '0004_alter_shoppinglist_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('digital_address', models.CharField(blank=True, max_length=255, null=True)),
                ('area_name', models.CharField(blank=True, max_length=255, null=True)),
                ('payment_preference', models.CharField(blank=True, max_length=255, null=True)),
            ],
        ),
    ]
