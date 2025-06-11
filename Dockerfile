FROM python:3.9-slim
ENV PATH="/scripts:${PATH}" 
ENV PATH="/app:${PATH}"

COPY ./requirements.txt /requirements.txt

RUN apt-get update && apt-get install -y gcc libpq-dev linux-headers-generic \
    && apt-get install -y postgresql postgresql-contrib \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r /requirements.txt \
    && apt-get remove -y gcc libpq-dev linux-headers-generic \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash usr_admin

RUN mkdir /app
COPY . /app/
WORKDIR /app


RUN chmod +x /app/scripts/entrypoint.sh
RUN mkdir -p /vol/web/media
RUN mkdir -p /vol/web/

RUN chown -R usr_admin:usr_admin /app
RUN chown -R usr_admin:usr_admin /vol
RUN chmod -R 755 /vol/web
RUN chmod -R 755 /app/scripts


USER usr_admin
CMD [ "entrypoint.sh" ]