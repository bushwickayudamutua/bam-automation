# This Dockerfile is for running the automation API in ./app
FROM astral/uv:0.12.10-python3.11-trixie

# set env
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive
ENV BAM_ENV=docker
ENV UV_NO_DEV=1

# Install API requirements

WORKDIR /opt/bam

# Install core, api, and configured dependencies.
ADD core /opt/core
ADD app /opt/bam
RUN uv sync --locked

# Start app
CMD ["uv", "run", "uvicorn", "bam_app.main:app", "--port", "3030", "--host", "0.0.0.0"]
