FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.hf_cache \
    TRANSFORMERS_NO_ADVISORY_WARNINGS=1

WORKDIR /app

# Dependencias del sistema (lxml/trafilatura pueden requerir toolchain)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar torch CPU-only primero para no arrastrar CUDA (imagen ~1GB menos)
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

COPY . .

# Raiz del paquete en la ruta de busqueda (necesario para `streamlit run ...`)
ENV PYTHONPATH=/app

RUN mkdir -p data/raw data/clean

EXPOSE 8000

# Comando por defecto: API. La UI sobreescribe este CMD en docker-compose.
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
