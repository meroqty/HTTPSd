#!/usr/bin/env python3
"""Простой HTTP/1.1 сервер с REST API и статическими файлами."""

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_BODY = 16 * 1024


class ItemsStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.items = {}
        self.next_id = 1

    def list_items(self):
        with self.lock:
            return [dict(item) for item in self.items.values()]

    def get_item(self, item_id):
        with self.lock:
            item = self.items.get(item_id)
            return dict(item) if item is not None else None

    def create_item(self, name):
        with self.lock:
            item = {"id": self.next_id, "name": name}
            self.items[self.next_id] = item
            self.next_id += 1
            return dict(item)

    def update_item(self, item_id, name):
        with self.lock:
            if item_id not in self.items:
                return None
            self.items[item_id]["name"] = name
            return dict(self.items[item_id])

    def delete_item(self, item_id):
        with self.lock:
            return self.items.pop(item_id, None) is not None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    store = ItemsStore()

    def reply(self, status, payload, content_type="application/json; charset=utf-8", extra=None):
        if not isinstance(payload, bytes):
            payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)

    def error_json(self, status, message):
        self.reply(status, {"error": message})

    def item_id_from_path(self, path):
        prefix = "/api/items/"
        if not path.startswith(prefix):
            return None
        value = path[len(prefix):]
        if not value.isdecimal() or int(value) == 0:
            return 0
        return int(value)

    def read_item_name(self):
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValueError("Требуется Content-Type: application/json")
        length_text = self.headers.get("Content-Length")
        if length_text is None:
            raise ValueError("Отсутствует Content-Length")
        try:
            length = int(length_text)
        except ValueError as exc:
            raise ValueError("Некорректный Content-Length") from exc
        if not 0 < length <= MAX_BODY:
            raise ValueError("Недопустимый размер тела запроса")
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Некорректный JSON") from exc
        if not isinstance(data, dict) or not isinstance(data.get("name"), str):
            raise ValueError("Нужно передать строковое поле name")
        name = data["name"].strip()
        if not name or len(name) > 100:
            raise ValueError("name должен содержать от 1 до 100 символов")
        return name

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/items":
            self.reply(200, {"items": self.store.list_items()})
            return
        item_id = self.item_id_from_path(path)
        if item_id is not None:
            if not item_id:
                self.error_json(400, "Некорректный идентификатор")
                return
            item = self.store.get_item(item_id)
            if item is None:
                self.error_json(404, "Запись не найдена")
            else:
                self.reply(200, item)
            return
        self.serve_static(path)

    def serve_static(self, path):
        if path == "/":
            path = "/index.html"
        target = (STATIC_DIR / path.lstrip("/")).resolve()
        if not target.is_relative_to(STATIC_DIR) or not target.is_file():
            self.error_json(404, "Страница не найдена")
            return
        types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".txt": "text/plain; charset=utf-8",
        }
        self.reply(200, target.read_bytes(), types.get(target.suffix.lower(), "application/octet-stream"))

    def do_POST(self):
        path = urlsplit(self.path).path
        if path != "/api/items":
            self.error_json(404, "Маршрут не найден")
            return
        try:
            name = self.read_item_name()
        except ValueError as exc:
            self.close_connection = True
            self.error_json(400, str(exc))
            return
        item = self.store.create_item(name)
        self.reply(201, item, extra={"Location": f"/api/items/{item['id']}"})

    def do_PUT(self):
        path = urlsplit(self.path).path
        item_id = self.item_id_from_path(path)
        if item_id is None:
            self.error_json(404, "Маршрут не найден")
            return
        if not item_id:
            self.error_json(400, "Некорректный идентификатор")
            return
        try:
            name = self.read_item_name()
        except ValueError as exc:
            self.close_connection = True
            self.error_json(400, str(exc))
            return
        item = self.store.update_item(item_id, name)
        if item is None:
            self.error_json(404, "Запись не найдена")
        else:
            self.reply(200, item)

    def do_DELETE(self):
        path = urlsplit(self.path).path
        item_id = self.item_id_from_path(path)
        if item_id is None:
            self.error_json(404, "Маршрут не найден")
        elif not item_id:
            self.error_json(400, "Некорректный идентификатор")
        elif self.store.delete_item(item_id):
            self.reply(200, {"deleted": item_id})
        else:
            self.error_json(404, "Запись не найдена")


def main():
    parser = argparse.ArgumentParser(description="HTTP/1.1 REST сервер")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    with ThreadingHTTPServer((args.host, args.port), Handler) as server:
        print(f"Сервер запущен: http://{args.host}:{server.server_port}", flush=True)
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            print("\nСервер остановлен.", flush=True)


if __name__ == "__main__":
    main()
