# Use a lightweight Python base image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies (optional, but good practice)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python libraries
RUN pip install --no-cache-dir aiohttp python-socketio

# Copy your specific project files
COPY k-city_server.py .
COPY k-city_index.html .

# Expose the port
EXPOSE 9005

# Run the server
CMD ["python", "k-city_server.py"]