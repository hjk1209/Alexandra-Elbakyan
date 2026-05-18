FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt requirements-prod.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements-prod.txt

# Copy application
COPY . .

# Create logs directory
RUN mkdir -p logs && \
    chmod -R 755 logs

# Collect static files with the base settings used during image build.
RUN python manage.py collectstatic --noinput --settings=juventude_mst.settings || true

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn_config.py", "juventude_mst.wsgi:application"]
