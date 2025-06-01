# Use an official Python runtime as a base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy application files
COPY . /app

# Install dependencies
RUN pip install --upgrade pip && \
    pip install flask waitress

# Expose port
EXPOSE 8080

# Run the app with Waitress (better than Flask dev server)
CMD ["python", "main.py"]
