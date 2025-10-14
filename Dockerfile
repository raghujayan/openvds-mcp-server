FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY test_server.py .

ENV PYTHONUNBUFFERED=1
ENV VDS_DATA_PATH=/data

CMD ["python", "src/openvds_mcp_server.py"]
