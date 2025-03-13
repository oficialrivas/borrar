FROM python:3.9

WORKDIR /app

COPY ./app /app
COPY requirements.txt /app/

# Instalamos las dependencias necesarias
RUN apt-get update && apt-get install -y \
    xvfb xauth \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libxcomposite1 libxrandr2 libgbm1 \
    libasound2 libpangocairo-1.0-0 libpango-1.0-0 \
    libcups2 libxdamage1 libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

# Instalamos Playwright y sus navegadores
RUN playwright install --with-deps chromium

# Ejecutamos Celery con xvfb-run para evitar problemas con el servidor gráfico
CMD ["xvfb-run", "--auto-servernum", "celery", "-A", "celery_worker", "worker", "--loglevel=info"]