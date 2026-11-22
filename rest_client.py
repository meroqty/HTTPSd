#!/usr/bin/env python3
"""REST-клиент: получение списка, создание, изменение и удаление записи."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request(base, method, path, data=None):
    body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = Request(
        base.rstrip("/") + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    try:
        with urlopen(req, timeout=5) as response:
            status = response.status
            raw = response.read()
    except HTTPError as exc:
        status = exc.code
        raw = exc.read()
    result = json.loads(raw.decode("utf-8"))
    print(f"{method:6} {path:16} -> {status}  {json.dumps(result, ensure_ascii=False)}")
    return status, result


def main():
    parser = argparse.ArgumentParser(description="Проверка CRUD на учебном API")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    try:
        status, _ = request(args.base_url, "GET", "/api/items")
        assert status == 200

        status, created = request(args.base_url, "POST", "/api/items", {"name": "Учебная запись"})
        assert status == 201
        item_id = created["id"]

        status, _ = request(args.base_url, "PUT", f"/api/items/{item_id}", {"name": "Изменённая запись"})
        assert status == 200

        status, _ = request(args.base_url, "GET", f"/api/items/{item_id}")
        assert status == 200

        status, _ = request(args.base_url, "DELETE", f"/api/items/{item_id}")
        assert status == 200

        status, _ = request(args.base_url, "GET", f"/api/items/{item_id}")
        assert status == 404

        print("Все CRUD-операции выполнены успешно.")
    except (URLError, OSError, ValueError, KeyError, AssertionError) as exc:
        print(f"Ошибка проверки: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
