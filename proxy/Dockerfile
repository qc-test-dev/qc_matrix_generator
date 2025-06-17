FROM nginxinc/nginx-unprivileged:1-alpine

COPY --chown=nginx:nginx ./default.conf /etc/nginx/conf.d/default.conf
COPY --chown=nginx:nginx ./uwsgi_params /etc/nginx/uwsgi_params

USER root
RUN mkdir -p /vol/static && chown nginx:nginx /vol/static && chmod 755 /vol/static
USER nginx
