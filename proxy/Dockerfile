FROM nginxinc/nginx-unprivileged:1-alpine
LABEL maintainer="qc-lab"
LABEL description="nginx web matrix creator"

COPY ./default.conf /etc/nginx/conf.d/default.conf
COPY ./uwsgi_params /etc/nginx/uwsgi_params

USER root

# Crear directorios para static y media
RUN mkdir -p /vol/static && \
    mkdir -p /vol/web/media && \
    chmod -R 755 /vol/static && \
    chmod -R 755 /vol/web/media && \
    chown -R nginx:nginx /vol/static && \
    chown -R nginx:nginx /vol/web/media

USER nginx