FROM python:3.11-slim

# SET WORK DIRECTORY
WORKDIR /app

# INSTALL DEPENDENCIES
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# COPY PROJECT FILES
COPY . .

# EXPOSE FastAPI PORT
EXPOSE 8000

# START SERVER
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
