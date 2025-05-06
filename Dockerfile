FROM python:3.12-slim

WORKDIR /app

# -- Подготовка окружения --------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# -- Копируем исходники ----------------------------------------------------
COPY . .

CMD ["python", "main.py"] 