FROM python:3.12-slim-bookworm

# The installer requires curl (and certificates) to download the release archive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh


RUN mkdir -p /data \
    && chmod 755 /data \
    && useradd -ms /bin/bash appuser \
    && chown -R appuser:appuser /data

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt
    
# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

WORKDIR /app

COPY . .  

CMD ["uv", "run", "app.py"]