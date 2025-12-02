#!/bin/bash
# Pre-deploy hook: Ensure Docker is running

if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "Docker is running. Proceeding with deployment..."
