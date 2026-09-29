FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8
WORKDIR /app

# The root requirements file is the documented local installation source.
# RSA support is needed by PyMySQL for MySQL's caching_sha2_password login.
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt "PyMySQL[rsa]>=1.1.0"
COPY backend/ ./backend/

EXPOSE 5000
CMD ["python", "backend/docker-entrypoint.py"]
