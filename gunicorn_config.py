import os
import multiprocessing

bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
worker_connections = 1000
max_requests = 10000
max_requests_jitter = 1000
timeout = 30
keepalive = 5
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
access_log = '-'
error_log = '-'
log_level = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
