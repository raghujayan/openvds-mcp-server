FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip

# Install openvds - using Python 3.10 for better wheel compatibility
RUN pip install --no-cache-dir openvds==3.4.8

# Install remaining requirements
RUN pip install --no-cache-dir anthropic>=0.18.0 mcp>=0.9.0 pydantic>=2.0.0 numpy>=1.24.0 aiohttp>=3.9.0

COPY src/ ./src/
COPY test_server.py .

ENV PYTHONUNBUFFERED=1
ENV VDS_DATA_PATH=/data

CMD ["python", "src/openvds_mcp_server.py"]
