# Dockerfile extending the generic Python image with application files for a
# single application.
FROM gcr.io/google_appengine/python-compat

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install mysql-server mysql-client mysql-common python-mysqldb
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install python-pip
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install build-essential
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install python-dev
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install --reinstall python-crypto python-m2crypto python3-crypto

ADD . /app