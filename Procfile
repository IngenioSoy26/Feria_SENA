release: python manage.py migrate --noinput && python manage.py crear_roles_iniciales
web: python manage.py collectstatic --noinput --clear && gunicorn config.wsgi --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:${PORT:-8000}
