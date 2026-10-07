# This Dockerfile is for running the automation API in ./app
FROM astral/uv:bookworm

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

# Configure system
RUN export PATH=~/.local/bin:$PATH
ENV PYTHONPATH "/opt/bam:$PYTHONPATH"

# Install API requirements

WORKDIR /opt/bam

# Install api.
ADD core /opt/core
ADD app /opt/bam
RUN uv sync --locked --no-dev

# Start app
CMD ["uvicorn", "bam_app.main:app", "--port", "3030", "--host", "0.0.0.0"]
