ARG ALTO_VERSION=0.1.6
ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim-buster

# Add non-root user
RUN useradd -m dev
# Use non-root user
USER dev
# Set working directory
WORKDIR /home/dev
# Install dependencies
RUN pip install --user singer-alto==${ALTO_VERSION}

ENTRYPOINT ["alto"]
