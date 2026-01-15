FROM python:3.12-slim

# Install git (and ca-certificates so https works), then clean apt cache to keep the image small
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /home/app

# Copy only requirements.txt first (so Docker can cache dependencies layer)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
