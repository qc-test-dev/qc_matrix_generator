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

# Preparar el directorio de la aplicación
RUN mkdir /app
COPY . /app/
WORKDIR /app

# Hacer ejecutable el entrypoint
RUN chmod +x scripts/entrypoint.sh

# Cambiar permisos DESPUÉS de copiar archivos
RUN chown -R qc-lab:qc-lab /app
RUN chmod -R 755 /app

# IMPORTANTE: Cambiar a usuario sin privilegios
USER qc-lab

# Comando de inicio
CMD ["bash", "entrypoint.sh"]