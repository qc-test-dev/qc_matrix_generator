FROM nginxinc/nginx-unprivileged:1-alpine

# Copiamos la configuración de Nginx para UAT (default.conf) y el archivo uwsgi_params
COPY --chown=nginx:nginx ./default.conf /etc/nginx/conf.d/default.conf
COPY --chown=nginx:nginx ./uwsgi_params /etc/nginx/uwsgi_params

USER root
# Creamos la carpeta donde se servirán los archivos estáticos, con permisos correctos
RUN mkdir -p /vol/static && chown nginx:nginx /vol/static && chmod 755 /vol/static

USER nginx
