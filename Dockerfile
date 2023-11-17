# This Dockerfile is for running the automation API in ./app
FROM python:3.11.4-buster

# set env
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive
ENV BAM_ENV=docker

# Install system requirements
RUN apt update
RUN apt install -y \
	curl \
	build-essential \
	python3-pip \
	uwsgi \
	uwsgi-plugin-python3

# get pip striaght
RUN pip3.11 install --upgrade pip

# Configure system
RUN export PATH=~/.local/bin:$PATH
ENV PYTHONPATH "/opt/bam:$PYTHONPATH"

# Install API requirements

WORKDIR /opt/bam

# Install core.
ADD core /opt/bam-core
RUN pip3.11 install -e /opt/bam-core
# Install api requirements.
COPY app/requirements.txt /opt/bam/requirements.txt
RUN pip3.11 install -r /opt/bam/requirements.txt
# Install api.
ADD app /opt/bam
RUN pip3.11 install -e /opt/bam

# Start app
CMD ["uvicorn", "bam_app.main:app", "--port", "3030", "--host", "0.0.0.0"]
