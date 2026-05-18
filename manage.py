import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'juventude_mst.settings')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Nao foi possivel importar Django. Verifique se:\n"
            "1. Django esta instalado (py -3.14 -m pip install -r requirements.txt)\n"
            "2. O ambiente Python correto esta em uso\n"
            "3. PYTHONPATH esta configurado corretamente"
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
