# Use a lightweight Python image
FROM python:3.12.12-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies (needed for some NLP libraries)
RUN apt-get update && apt-get install -y build-essential


# Copy the requirements file first (to cache dependencies)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m pip install --upgrade pip

# Copy the rest of your application code
# (main.py, security.py, prompts.py, knowledge/, etc.)

COPY . .

# The command to run your app
CMD ["python", "main.py"]