FROM python:3.8-slim

LABEL maintainer="qc-lab"
LABEL description="apk web matrix creator"

ENV PATH="/scripts:${PATH}"

# Actualizar, instalar herramientas necesarias y paquetes de compilación
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
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt
COPY requirements.txt /requirements.txt

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r /requirements.txt

# Crear usuario ANTES de copiar archivos
RUN useradd -ms /bin/bash qc-lab

# Crear directorios con permisos correctos
RUN mkdir -p /vol/static && \
    mkdir -p /vol/web/media && \
    mkdir -p /app && \
    chown -R qc-lab:qc-lab /vol && \
    chown -R qc-lab:qc-lab /app

# Preparar el directorio de la aplicación
COPY . /app/
WORKDIR /app

# Cambiar permisos DESPUÉS de copiar archivos
RUN chown -R qc-lab:qc-lab /app && \
    chmod -R 755 /app && \
    chmod +x scripts/entrypoint.sh

# IMPORTANTE: Cambiar a usuario sin privilegios ANTES de collectstatic
USER qc-lab



# Comando de inicio
CMD ["bash", "scripts/entrypoint.sh"]