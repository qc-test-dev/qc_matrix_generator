#!/bin/bash

# Reemplaza estos valores
JENKINS_URL="http://200.57.172.7:8080/jenkins/"
JENKINS_USER="qc_admin"
JENKINS_TOKEN="cla_ax44"
JOB_NAME="docker_web_uat_ci"


RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$JENKINS_URL/job/$JOB_NAME/build?token=$BUILD_TOKEN")

# Verifica si fue exitoso
if [ "$RESPONSE" -eq 201 ] || [ "$RESPONSE" -eq 200 ]; then
    echo "Build lanzado correctamente."
    exit 0
else
    echo "Error al lanzar build, HTTP status: $RESPONSE"
    exit 1
fi
