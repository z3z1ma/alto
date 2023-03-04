FROM python:3.9-slim-buster
# Install system dependencies
RUN apt-get update && \
    apt-get install -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    # Create non-root user
    useradd -m dev && \
    # Create poetry directory
    mkdir -p /opt/poetry && \
    chown dev:dev /opt/poetry
# Use non-root user
USER dev
WORKDIR /home/dev
# Install poetry
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python -
# Add poetry to PATH
ENV PATH="/opt/poetry/bin:${PATH}"
# Copy project files
COPY . .
# Install dependencies
RUN poetry config virtualenvs.in-project true --local && \
    poetry install --with dev --no-interaction --no-ansi
