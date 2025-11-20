web: cd djangoapp && python manage.py migrate && python manage.py collectstatic --noinput && gunicorn project.wsgi:application --bind 0.0.0.0:$PORT
worker: cd djangoapp && celery -A project worker -l info
beat: cd djangoapp && celery -A project beat -l info

