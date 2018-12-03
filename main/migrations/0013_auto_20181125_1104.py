# Generated by Django 2.0.6 on 2018-11-25 11:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0012_auto_20181122_1411'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicantCommercialRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('relation_id', models.IntegerField()),
                ('applicant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.Applicant')),
            ],
        ),
        migrations.CreateModel(
            name='CommercialRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(max_length=20)),
                ('business_type_id', models.IntegerField()),
            ],
        ),
        migrations.AddField(
            model_name='applicantcommercialrecord',
            name='commercial_record',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='main.CommercialRecord'),
        ),
        migrations.AddField(
            model_name='applicant',
            name='commercial_records',
            field=models.ManyToManyField(related_name='related', through='main.ApplicantCommercialRecord', to='main.CommercialRecord'),
        ),
    ]
