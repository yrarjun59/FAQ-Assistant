FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

ENV OLLAMA_BASE_URL=http://ollama_server:11434

EXPOSE 8000

# Default command
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]