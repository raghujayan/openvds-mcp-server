FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip

# Install openvds separately first to debug
RUN pip install --no-cache-dir openvds==3.4.8 -vv || \
    (echo "Failed to install openvds from PyPI, trying specific wheel..." && \
     pip install --no-cache-dir https://files.pythonhosted.org/packages/48/97/ef3cbbd21681fc745d7bc82f90c5d19eab5df71f6036d3d385cdd936c090/openvds-3.4.8-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl)

# Install remaining requirements
RUN pip install --no-cache-dir anthropic>=0.18.0 mcp>=0.9.0 pydantic>=2.0.0 numpy>=1.24.0 aiohttp>=3.9.0

COPY src/ ./src/
COPY test_server.py .

ENV PYTHONUNBUFFERED=1
ENV VDS_DATA_PATH=/data

CMD ["python", "src/openvds_mcp_server.py"]
