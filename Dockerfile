FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

# Copy uv directly from the official Astral image (Fastest & most reliable method)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Set up Hugging Face cache
ENV HF_HOME=/app/.cache/huggingface
RUN mkdir -p $HF_HOME 

# Install standard Python 
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt
COPY requirements.txt .

# Install PyTorch with CUDA 12.4 support first, then install remaining dependencies
# Removed --retries and --timeout as they are unsupported by uv
RUN uv pip install --system --no-cache torch==2.5.* --index-url https://download.pytorch.org/whl/cu124 && \
    uv pip install --system --no-cache -r requirements.txt

# Copy the project
COPY . .

# Expose the port
EXPOSE 8000

# Start the application
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]