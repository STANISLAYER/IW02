# Lab 02 — Currency Exchange Rate CLI (for provided PHP service)

Этот скрипт взаимодействует с приложением из бандла `lab02prep` (PHP + Apache в Docker) и:
- запрашивает курс одной валюты к другой на указанную дату;
- сохраняет ответ в `../data/` как JSON (`FROM_TO_YYYY-MM-DD.json`);
- пишет ошибки в корневой `error.log` (одновременно выводит в консоль).

## 1) Запуск сервиса

В корне бандла есть `docker-compose.yaml` и `sample.env`.

```bash
cd /mnt/data/appbundle/lab02prep
# создадим .env с ключом (или скопируй sample.env)
cp sample.env .env
# при желании поменяй API_KEY в .env
docker compose up -d
# сервис будет доступен на http://localhost:8080
```

Контракт API (согласно коду `app/index.php`):
- метод: **POST** (в теле передаём `key=<API_KEY>`);
- query-параметры (GET): `from`, `to`, `date` (необязательный, формат YYYY-MM-DD; если пропущен — берутся последние доступные курсы);
- пример запроса:
```bash
curl "http://localhost:8080/?from=USD&to=EUR&date=2025-06-01" -X POST -d "key=EXAMPLE_API_KEY"
```
- ответ:
```json
{"error":"","data":{"from":"USD","to":"EUR","rate":1.2345,"date":"2025-06-01"}}
```
- валидный период данных: **2025-01-01 .. 2025-09-15**.

## 2) Установка зависимостей

Требуется Python 3.9+ (рекомендую 3.10+).
```bash
pip install -r requirements.txt
# или
pip install requests
```

## 3) Запуск скрипта

Одиночный запрос:
```bash
python lab02/currency_exchange_rate.py --from USD --to EUR --date 2025-01-01
```

Пакетный режим (равные интервалы, ≥ 5 дат в диапазоне 2025-01-01..2025-09-15):
```bash
python lab02/currency_exchange_rate.py --from USD --to EUR --start-date 2025-01-01 --end-date 2025-09-15 --num-dates 5 --warn-outside-range
```

Полезные опции:
- `--base-url` (по умолчанию `http://localhost:8080` или env `API_BASE_URL`)
- `--api-key` (по умолчанию env `API_KEY` или `EXAMPLE_API_KEY` из .env)

Примеры c переопределением:
```bash
python lab02/currency_exchange_rate.py --from RON --to USD --date 2025-03-01 --api-key EXAMPLE_API_KEY
python lab02/currency_exchange_rate.py --from USD --to UAH --start-date 2025-01-01 --end-date 2025-09-15 --num-dates 7
```

Все успешные ответы сохраняются в `./data/` рядом с корнем бандла.
Ошибки печатаются в консоль и пишутся в `./error.log` (в корне бандла).

## 4) Структура и логика

- **`parse_args`** — разбор аргументов (single/batch, `--base-url`, `--api-key`).
- **`validate_currency`** — проверка 3-буквенного кода валюты.
- **`parse_date`** — парсинг даты `YYYY-MM-DD`.
- **`evenly_spaced_dates`** — равномерная выборка дат от `start` до `end`.
- **`build_url`** — формирует URL вида `http://host:port/?from=...&to=...&date=...`.
- **`call_service`** — POST c `key=<API_KEY>`, проверка статуса, JSON и поля `error`.
- **`save_json`** — сохраняет JSON в `data/FROM_TO_YYYY-MM-DD.json`.
- **`run_one`** — валидирует входные, вызывает сервис и сохраняет результат.
- **`main`** — переключение между одиночным и пакетным режимом.

## 5) Примеры для презентации

Пять равных точек в диапазоне:
```bash
python lab02/currency_exchange_rate.py --from USD --to EUR --start-date 2025-01-01 --end-date 2025-09-15 --num-dates 5
```

Проверка обработки ошибок (неверная валюта):
```bash
python lab02/currency_exchange_rate.py --from US --to EUR --date 2025-06-01
```

## 6) Что загрузить на GitHub

- `lab02/currency_exchange_rate.py`
- `lab02/readme.md`
- `requirements.txt`
- `.gitignore` (по желанию)
- (опционально) содержимое `data/*.json` и `error.log` для демонстрации
