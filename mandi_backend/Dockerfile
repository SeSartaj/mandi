FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-calc ffmpeg && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --uid 10001 --create-home mandi
COPY --chown=mandi:mandi . .
RUN mkdir -p media staticfiles && chown -R mandi:mandi media staticfiles
USER mandi
RUN DJANGO_DEBUG=1 python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "600", "--graceful-timeout", "30", "--access-logfile", "-", "--error-logfile", "-"]
