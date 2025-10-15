FROM --platform=linux/amd64 ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-dev \
    build-essential git curl \
    libssl3 libcurl4 zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip
RUN pip3 install --upgrade pip

# Install OpenVDS with multiple fallback strategies (matching vds-metadata-crawler)
RUN pip3 install openvds==3.4.6 || \
    pip3 install openvds --only-binary=:all: || \
    pip3 install openvds --no-deps || \
    echo "OpenVDS installation failed, continuing without it"

# Install remaining requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt || \
    pip3 install --no-cache-dir anthropic>=0.18.0 mcp>=0.9.0 pydantic>=2.0.0 numpy>=1.24.0 aiohttp>=3.9.0

# Test OpenVDS installation and create fallback mock module if needed
RUN python3 -c "import openvds; print('OpenVDS installed successfully')" || \
    (python3 -c "import os; os.makedirs('/usr/local/lib/python3.10/dist-packages', exist_ok=True); open('/usr/local/lib/python3.10/dist-packages/openvds.py', 'w').write('def open(path): return None\\ndef getVersion(): return \"Mock\"\\n__MOCK_MODULE__ = True\\n'); print('Mock OpenVDS created')")

COPY src/ ./src/
COPY test_server.py .

ENV PYTHONUNBUFFERED=1
ENV VDS_DATA_PATH=/data

CMD ["python3", "src/openvds_mcp_server.py"]
