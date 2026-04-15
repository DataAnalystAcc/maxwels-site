FROM python:3.12-slim

WORKDIR /app

# Install Playwright system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install browsers and their system dependencies
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

CMD ["python", "worker.py"]
