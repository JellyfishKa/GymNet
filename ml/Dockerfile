FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

ARG REQUIREMENTS_FILE=requirements.pipeline.txt

COPY requirements.txt /workspace/requirements.txt
COPY requirements.pipeline.txt /workspace/requirements.pipeline.txt
COPY requirements.notebook.txt /workspace/requirements.notebook.txt
COPY requirements.gpu.txt /workspace/requirements.gpu.txt
RUN pip install --no-cache-dir -r /workspace/${REQUIREMENTS_FILE}

COPY . /workspace

EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token="]
