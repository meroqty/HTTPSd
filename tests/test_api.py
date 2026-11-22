#!/usr/bin/env python3
"""Автоматическая проверка статусов, CRUD и Content-Type."""

import json
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Handler, ItemsStore  # noqa: E402


class QuietHandler(Handler):
    def log_message(self, fmt, *args):
        pass


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Handler.store = ItemsStore()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def call(self, method, path, data=None, raw_body=None, content_type="application/json"):
        body = raw_body if raw_body is not None else (json.dumps(data).encode() if data is not None else None)
        headers = {"Content-Type": content_type} if body is not None else {}
        req = Request(self.base + path, data=body, headers=headers, method=method)
        try:
            with urlopen(req, timeout=3) as response:
                return response.status, response.headers, response.read()
        except HTTPError as exc:
            return exc.code, exc.headers, exc.read()

    def test_crud(self):
        status, _, data = self.call("GET", "/api/items")
        self.assertEqual(status, 200)
        self.assertIn("items", json.loads(data))
        status, headers, data = self.call("POST", "/api/items", {"name": "Книга"})
        self.assertEqual(status, 201)
        item_id = json.loads(data)["id"]
        self.assertEqual(headers["Location"], f"/api/items/{item_id}")
        status, _, data = self.call("PUT", f"/api/items/{item_id}", {"name": "Новая книга"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["name"], "Новая книга")
        status, _, data = self.call("GET", f"/api/items/{item_id}")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["name"], "Новая книга")
        status, _, _ = self.call("DELETE", f"/api/items/{item_id}")
        self.assertEqual(status, 200)
        status, _, _ = self.call("GET", f"/api/items/{item_id}")
        self.assertEqual(status, 404)

    def test_bad_json_and_validation(self):
        status, _, _ = self.call("POST", "/api/items", raw_body=b"{broken")
        self.assertEqual(status, 400)
        status, _, _ = self.call("POST", "/api/items", {"name": ""})
        self.assertEqual(status, 400)
        status, _, _ = self.call("GET", "/api/items/abc")
        self.assertEqual(status, 400)

    def test_static_content_types(self):
        status, headers, data = self.call("GET", "/")
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("text/html"))
        self.assertIn(b"<!doctype html>", data)
        status, headers, _ = self.call("GET", "/style.css")
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("text/css"))
        status, _, _ = self.call("GET", "/missing.html")
        self.assertEqual(status, 404)

    def test_http_11_and_length(self):
        status, headers, data = self.call("GET", "/api/items")
        self.assertEqual(status, 200)
        self.assertEqual(int(headers["Content-Length"]), len(data))


if __name__ == "__main__":
    unittest.main(verbosity=2)
