# Use a lightweight Python image
FROM python:3.11-slim

# System deps: ffmpeg (audio), tesseract (OCR), node (prettier).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    tesseract-ocr \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Prettier globally (used by the format_file operation).
RUN npm install -g prettier@3.4.2

WORKDIR /app

# Install Python dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project source.
COPY . .

# Run as a non-root user.
RUN useradd --create-home --uid 10001 agent && chown -R agent:agent /app

# The agent operates on /data (TDS convention). Create it and give the agent
# ownership so it can generate + write fixtures there at runtime.
RUN mkdir -p /data && chown agent:agent /data
USER agent

ENV DATA_DIR=/data
ENV DATAGEN_EMAIL=23f2002592@ds.study.iitm.ac.in

EXPOSE 8000

# Generate the /data fixtures with datagen.py, then serve. AIPROXY_TOKEN (and
# optional AGENT_TOKEN) come from the environment. Plain HTTP; TLS is terminated
# by the platform. Honours the platform's $PORT (defaults to 8000 locally).
CMD ["sh", "-c", "python datagen.py ${DATAGEN_EMAIL} && gunicorn wsgi:app --bind 0.0.0.0:${PORT:-8000} --workers 1"]
