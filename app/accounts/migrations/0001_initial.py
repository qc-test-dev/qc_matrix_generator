# Generated for accounts.User

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(max_length=15, unique=True)),
                ('nombre', models.CharField(max_length=20, verbose_name='Nombre(s)')),
                ('apellido', models.CharField(max_length=30, verbose_name='Apellido(s)')),
                ('cargo', models.CharField(choices=[('Lider', 'LIDER'), ('Tester', 'TESTER')], default='Tester', verbose_name='Cargo')),
                ('equipo', models.CharField(choices=[('Roku', 'Roku'), ('STV(TATA)', 'STV(TATA)'), ('STB', 'STB'), ('WEB', 'WEB'), ('IOS', 'IOS')], default='STB', verbose_name='Equipo')),
                ('is_staff', models.BooleanField(default=False)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'User',
                'verbose_name_plural': 'Users',
            },
        ),
    ]