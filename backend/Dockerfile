FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl

COPY requirements.txt .

RUN pip install uv && \
    uv pip install --system -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]