# Terraform LogViewer

> Мощный веб-сервис для интерактивного анализа Terraform логов с диаграммой Ганта и расширяемой плагинной системой

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![gRPC](https://img.shields.io/badge/gRPC-4285F4?style=flat&logo=google&logoColor=white)](https://grpc.io/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)

---

## Возможности

###  Визуализация
- **Диаграмма Ганта** — временная последовательность операций с зумом 1x-50x
- **Drill-down** — клик по операции показывает детальную диаграмму всех логов
- **Цветовая индикация** — error, warning, info, debug, trace
- **Интерактивные tooltip** — умное позиционирование, не вылазят за края экрана

###  Фильтрация и поиск
- **Быстрые фильтры** — уровень, секция, Request ID с автодополнением
- **Расширенные фильтры** — дата, диапазон, invalid логи
- **Полнотекстовый поиск** — с подсветкой найденных слов
- **Кнопка сброса** — одним кликом очистить все фильтры

###  Управление данными
- **Множественные вкладки** — работа с несколькими наборами логов
- **Drag & Drop** — переупорядочивание вкладок
- **IndexedDB** — автосохранение в браузере
- **Экспорт JSON** — сохранение отфильтрованных логов

###  Плагинная система (gRPC)
- **Языковая независимость** — Python, Go, Rust, Java
- **3 типа операций** — Filter, Process, Aggregate
- **Изоляция** — плагины в отдельных процессах
- **UI управление** — регистрация и управление через веб-интерфейс

---

##  Компоненты

```
terraform-logviewer/
├── backend/          # FastAPI + Python 3.13
├── frontend/         # Vanilla JS + IndexedDB
└── plugins/          # gRPC плагины
    └── error_aggregator/  # Пример: группировка ошибок
```

##  Установка и запуск

### Windows PowerShell

```powershell
cd C:\HACKATON\terraform-logviewer\backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Linux/macOS

```bash
cd terraform-logviewer/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

##  UI

Откройте в браузере: `http://127.0.0.1:8000/ui`


##  Плагинная система

Подключайте собственные обработчики логов через gRPC.

### Быстрый старт с плагинами

```bash
# 1. Генерация proto файлов
cd backend
python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/plugin.proto

# 2. Запуск примера плагина (Error Aggregator)
cd ../plugins/error_aggregator
python plugin_server.py --port 50051

# 3. Регистрация плагина
curl -X POST http://localhost:8000/api/plugins/register \
  -H "Content-Type: application/json" \
  -d '{"name": "error-aggregator", "address": "localhost:50051", "enabled": true}'
```

### Доступные тестовые плагины

- **error-aggregator** — автоматическая группировка ошибок по типу и подсчет повторяемости

## API

### Основные endpoints

#### Загрузка логов
```http
POST /upload
Content-Type: multipart/form-data

file: <log_file.json>
```

#### Список плагинов
```http
GET /api/plugins
```

#### Агрегация через плагин
```http
POST /api/plugins/{plugin_name}/aggregate
Content-Type: application/json

{
  "logs": [...],
  "aggregation_type": "error_grouping",
  "agg_params": {"min_count": "2"}
}
```

Полная документация API: `http://127.0.0.1:8000/docs`


##  Диаграмма Ганта

Визуализирует временную последовательность операций:

- Каждая строка = одна операция (по `tf_req_id`)
- Цвет бара = уровень логов (error/warn/info/trace)
- Hover = детали (начало, конец, длительность, количество логов)
- Клик = фильтрация по этой операции


















