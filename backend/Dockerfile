FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# cpu — по умолчанию; gpu — PyTorch CUDA 12.1 (см. infra/docker-compose.gpu.yml)
ARG PYTORCH_VARIANT=cpu

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN if [ "$PYTORCH_VARIANT" = "gpu" ]; then \
      pip install --no-cache-dir "torch==2.5.1" --index-url https://download.pytorch.org/whl/cu121; \
    else \
      pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu; \
    fi \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
