#!/bin/bash
echo "entrypoint.sh: Starting server..."


# Load all environment variables from the .env file into the shell
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(grep -v '^#' .env | xargs)
else
    echo ".env file not found!"
fi

# Verify environment variables are set
if [ -z "$DUMMY_SECRET_KEY" ]; then
    echo "DUMMY_SECRET_KEY is not set!"
else
    echo "DUMMY_SECRET_KEY=${DUMMY_SECRET_KEY}"
fi

uvicorn main:app --host 0.0.0.0 --port 8090 --reload
echo "Running."


