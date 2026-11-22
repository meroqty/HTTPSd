# Домашнее задание. Пара 05 — HTTP/1.1 и REST API

## Состав

- `server.py` — HTTP/1.1-сервер со статическими файлами и REST API.
- `rest_client.py` — REST-клиент: список, создание, изменение и удаление записи.
- `static/index.html`, `static/style.css` — статические файлы с корректными `Content-Type`.
- `Схема_вызовов.docx` — таблица «метод → URL → тело → статус».
- `вывод_проверки.txt` — результат запуска клиента и тестов.
- `tests/test_api.py` — автоматические тесты.

## Запуск

Нужен Python 3.9 или новее. Дополнительные библиотеки не требуются.

В первом терминале из папки проекта:

```bash
python3 server.py
```

Во втором терминале:

```bash
python3 rest_client.py
```

Проверить работу сервера: `http://127.0.0.1:8000/`.

Остановить сервер: `Ctrl+C`.

Другой порт:

```bash
python3 server.py --port 8080
python3 rest_client.py --base-url http://127.0.0.1:8080
```

## Эндпоинты API

| Метод | URL | JSON-тело | Статус |
|---|---|---|---|
| GET | `/api/items` | — | 200 |
| GET | `/api/items/1` | — | 200 (есть) / 404 (нет) |
| POST | `/api/items` | `{"name":"Книга"}` | 201 |
| PUT | `/api/items/1` | `{"name":"Новая книга"}` | 200 (есть) / 404 (нет) |
| DELETE | `/api/items/1` | — | 200 (есть) / 404 (нет) |
| POST | `/api/items` | некорректный JSON или пустое `name` | 400 |
| GET | `/` | — | 200, `text/html` |
| GET | `/style.css` | — | 200, `text/css` |
| GET | `/missing.html` | — | 404 |

При создании сервер возвращает JSON с `id` и заголовок `Location`. В `POST` и `PUT` надо передавать `Content-Type: application/json`. Данные хранятся в памяти и после остановки сервера исчезают.

## Проверка

```bash
python3 -m unittest discover -s tests -v
```

Проверяются статусы 200/201/400/404, CRUD-операции, `Content-Type` и `Content-Length`.
