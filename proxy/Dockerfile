FROM nginx:1.21

RUN rm /etc/nginx/conf.d/default.conf
COPY default.conf /etc/nginx/conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]