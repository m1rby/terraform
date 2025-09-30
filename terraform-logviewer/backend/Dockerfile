FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]



