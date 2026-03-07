FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl

COPY requirements.in requirements.txt ./

RUN pip install uv && \
    uv pip install --system -r requirements.txt

COPY . .

ENV OLLAMA_BASE_URL=http://ollama_server:11434

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]