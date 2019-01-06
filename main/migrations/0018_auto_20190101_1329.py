# Generated by Django 2.0.6 on 2019-01-01 13:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0017_auto_20181212_1625'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicationdocument',
            name='returned',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='license',
            name='application',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='licenses', to='main.Application'),
        ),
    ]
