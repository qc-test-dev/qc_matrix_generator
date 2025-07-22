FROM python:3.11-bullseye

# Establecer locales (opcional, agrega según tu idioma preferido)
RUN apt-get update && \
    apt-get install -y locales netcat curl procps && \
    echo "es_MX.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen es_MX.UTF-8 && \
    update-locale LANG=es_MX.UTF-8

ENV LANG=es_MX.UTF-8
ENV LANGUAGE=es_MX:es
ENV LC_ALL=es_MX.UTF-8

# Instalar dependencias del sistema necesarias
RUN apt-get install -y --no-install-recommends \
    gcc libpq-dev postgresql-client \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 libglib2.0-0 shared-mime-info \
    libxml2 libxslt1.1 fontconfig libjpeg62-turbo zlib1g \
    libharfbuzz0b libfribidi0 \
    libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev libffi-dev \
    libxml2-dev libxslt1-dev fontconfig-config zlib1g-dev libjpeg-dev \
    libharfbuzz-dev libfribidi-dev && \
    pip install --upgrade pip

# Copiar requirements y luego instalar paquetes python
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Crear usuario no-root para seguridad
RUN useradd -ms /bin/bash usr_admin

# Copiar el código de la app y setear permisos
COPY . /app/
WORKDIR /app
RUN chmod +x /app/scripts/entrypoint.sh && chown -R usr_admin:usr_admin /app

USER usr_admin

# Entrypoint ejecuta script que espera servicios, migra, collectstatic y lanza Daphne
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
