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
        linux-headers-amd64 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt
COPY requirements.txt /requirements.txt

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r /requirements.txt

# Preparar el directorio de la aplicación
RUN mkdir /app
COPY . /app/
WORKDIR /app

# Permisos de los scripts
RUN chmod +x /app/scripts/*.sh

# Crear usuario sin privilegios
RUN useradd -ms /bin/bash qc-lab
RUN chown -R qc-lab:qc-lab /app
RUN chmod -R 777 /app


USER qc-lab

# Comando de inicio
CMD ["entrypoint.sh"]
