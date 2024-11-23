# Use an official Python runtime as a base image
FROM python:3.11-slim AS base

# Set environment variables to disable buffered output and enable pip's new resolver
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# Set the working directory in the container
WORKDIR /app

# Dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    && apt-get clean

RUN pip3 install --upgrade pip

COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt
RUN pip3 install --upgrade boto3 botocore

RUN apt-get update && apt-get install -y \
    libpq-dev \
    ffmpeg \
    && apt-get clean

RUN pip3 install python-ffmpeg

# Copy application code
COPY . /app/

# Expose port
EXPOSE 8000

FROM base AS development

RUN chmod +x /app/entrypoint.sh

# Set the working directory before entrypoint
WORKDIR /app

# Debug: List files in /app
RUN ls -R /app

# Set the entry point for the container
ENTRYPOINT ["/app/entrypoint.sh"]
