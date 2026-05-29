FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt requirements-prod.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements-prod.txt

COPY . .

RUN mkdir -p logs && \
    chmod -R 755 logs

# Collect static files with the base settings used during image build.
RUN python manage.py collectstatic --noinput --settings=juventude_mst.settings

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn_config.py", "juventude_mst.wsgi:application"]
