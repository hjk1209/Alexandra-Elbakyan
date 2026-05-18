from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='securityevent',
            name='event_type',
            field=models.CharField(
                choices=[
                    ('login_success', 'Login bem-sucedido'),
                    ('login_failure', 'Falha de login'),
                    ('logout', 'Logout'),
                    ('lockout', 'Bloqueio temporario'),
                    ('signup', 'Cadastro'),
                    ('throttle', 'Limitacao de frequencia'),
                    ('user_created', 'Usuario criado'),
                    ('user_deactivated', 'Usuario desativado'),
                    ('user_reactivated', 'Usuario reativado'),
                ],
                max_length=40,
            ),
        ),
    ]
