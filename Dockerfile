FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Install Tesseract OCR and other dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download spaCy English model for faster runtime launch
RUN python -m spacy download en_core_web_sm

# Copy the rest of the application files
COPY . .

# Expose the Flask port
EXPOSE 5000

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Command to start the application
CMD ["python", "app.py"]
