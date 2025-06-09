FROM python:3.8-slim

LABEL maintainer="qc-lab"
LABEL description="apk web matrix creator"

ENV PATH="/scripts:${PATH}"
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        bash \
        git \
        curl \
        wget \
        unzip \
        zip \
        build-essential \
        gfortran \
        libblas-dev \
        liblapack-dev \
        nginx \
        uwsgi \
        uwsgi-plugin-python3 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Crear usuario
RUN useradd -ms /bin/bash qc-lab

# Crear directorios
RUN mkdir -p /vol/static && \
    mkdir -p /vol/web/media && \
    mkdir -p /app && \
    mkdir -p /tmp/sockets && \
    chown -R qc-lab:qc-lab /vol && \
    chown -R qc-lab:qc-lab /app && \
    chown -R qc-lab:qc-lab /tmp/sockets

# Instalar dependencias de Python
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Copiar aplicación
COPY . /app/
WORKDIR /app

# Configurar permisos
RUN chown -R qc-lab:qc-lab /app && \
    chmod -R 755 /app && \
    chmod +x scripts/entrypoint.sh

USER qc-lab

CMD ["bash", "scripts/entrypoint.sh"]