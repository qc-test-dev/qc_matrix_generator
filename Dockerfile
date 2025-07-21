FROM python:3.9-slim

# Para poner /scripts y /app en el PATH
ENV PATH="/scripts:${PATH}"
ENV PATH="/app:${PATH}"

# Soporte para locales, especialmente es_MX.UTF-8
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      locales && \
    echo "es_MX.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen && \
    update-locale LANG=es_MX.UTF-8

ENV LANG=es_MX.UTF-8
ENV LANGUAGE=es_MX:es
ENV LC_ALL=es_MX.UTF-8

# Copiamos requirements
COPY ./requirements.txt /requirements.txt

# Instalamos dependencias de sistema y de desarrollo, luego limpiamos
RUN apt-get install -y --no-install-recommends \
      gcc libpq-dev postgresql-client \
      libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
      libgdk-pixbuf2.0-0 libglib2.0-0 shared-mime-info \
      libxml2 libxslt1.1 fontconfig libjpeg62-turbo zlib1g \
      libharfbuzz0b libfribidi0 \
      libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev libffi-dev \
      libxml2-dev libxslt1-dev fontconfig-config zlib1g-dev libjpeg-dev \
      netcat-traditional \
      libharfbuzz-dev libfribidi-dev && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r /requirements.txt \
                          daphne channels channels_redis whitenoise && \
    apt-get remove -y \
      gcc libpq-dev libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev \
      libffi-dev libxml2-dev libxslt1-dev libjpeg-dev libharfbuzz-dev libfribidi-dev && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Creamos usuario no-root
RUN useradd -ms /bin/bash usr_admin

# Preparamos código
RUN mkdir /app
COPY . /app/
WORKDIR /app

# Permisos y volúmenes
RUN chmod +x /app/scripts/entrypoint.sh && \
    mkdir -p /vol/web/media /vol/web/static && \
    chown -R usr_admin:usr_admin /app /vol

USER usr_admin

# El entrypoint lanza Daphne
CMD ["entrypoint.sh"]
