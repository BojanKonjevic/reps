#!/usr/bin/env python3
"""pytest suite for sync concurrency (pull-first ETag, 412 abort, force)."""

import io
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SyncStubState:
    def __init__(self):
        self.stored = None
        self.requests = []
        self.always_conflict = False


def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send_json(self, status, obj, etag=None):
            body = json.dumps(obj).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            if etag:
                self.send_header("ETag", etag)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            state.requests.append({"method": "GET", "path": self.path,
                                   "if_match": self.headers.get("If-Match")})
            if self.headers.get("Authorization") != "Bearer test-secret":
                self._send_json(401, {"error": "unauthorized"})
                return
            if state.stored is None:
                self._send_json(200, {"note": "blank", "workouts": [], "sets": [],
                                      "bodyweight": []})
                return
            try:
                tag = '"' + json.loads(state.stored)["exported"] + '"'
            except (ValueError, KeyError, TypeError):
                tag = None
            body = state.stored.encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            if tag:
                self.send_header("ETag", tag)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_PUT(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode()
            state.requests.append({"method": "PUT", "path": self.path,
                                   "if_match": self.headers.get("If-Match"),
                                   "force": self.headers.get("X-Sync-Force")})
            if self.headers.get("Authorization") != "Bearer test-secret":
                self._send_json(401, {"error": "unauthorized"})
                return
            if state.stored is not None and self.headers.get("X-Sync-Force") != "1":
                try:
                    current_tag = '"' + json.loads(state.stored)["exported"] + '"'
                except (ValueError, KeyError, TypeError):
                    current_tag = None
                stale = state.always_conflict or (
                    current_tag is not None and self.headers.get("If-Match") != current_tag)
                if stale:
                    self._send_json(412, {"error": "stale snapshot", "etag": current_tag},
                                    etag=current_tag)
                    return
            try:
                tag = '"' + json.loads(raw)["exported"] + '"'
            except (ValueError, KeyError, TypeError):
                tag = None
            state.stored = raw
            if tag:
                self._send_json(200, {"ok": True, "etag": tag}, etag=tag)
            else:
                self._send_json(200, {"ok": True})

    return Handler


def start_stub(state):
    server = HTTPServer(("127.0.0.1", 0), make_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def write_cfg(tmp_path, monkeypatch, log_module, port):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"url": f"http://127.0.0.1:{port}", "secret": "test-secret"}))
    monkeypatch.setattr("reps.db.CFG", str(cfg))


def capture(fn, *args):
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        fn(*args)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old


def test_sync_sends_if_match_from_pull(log_module, tmp_path, monkeypatch):
    """Normal sync GETs first and pushes with the pulled If-Match."""
    import urllib.request
    state = SyncStubState()
    server = start_stub(state)
    try:
        write_cfg(tmp_path, monkeypatch, log_module, server.server_port)
        seed = json.dumps({"exported": "2026-09-17T12:00:00", "workouts": [],
                           "sets": [], "bodyweight": []}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/sync", data=seed, method="PUT",
            headers={"Authorization": "Bearer test-secret"})
        urllib.request.urlopen(req, timeout=5).read()
        state.requests.clear()

        out = capture(log_module.cmd_sync)
        assert json.loads(out.strip().splitlines()[0])["synced"] is True
        puts = [r for r in state.requests if r["method"] == "PUT"]
        assert any(r["method"] == "GET" for r in state.requests)
        assert len(puts) == 1
        assert puts[0]["if_match"] == '"2026-09-17T12:00:00"'
        assert json.loads(state.stored)["exported"] != "2026-09-17T12:00:00"
    finally:
        server.shutdown()


def test_sync_aborts_on_stale_base(log_module, tmp_path, monkeypatch, capsys):
    """A 412 from the server aborts loudly instead of overwriting."""
    state = SyncStubState()
    state.stored = json.dumps({"exported": "2026-09-17T12:05:00", "workouts": [],
                               "sets": [], "bodyweight": []})
    state.always_conflict = True
    server = start_stub(state)
    try:
        write_cfg(tmp_path, monkeypatch, log_module, server.server_port)
        try:
            log_module.cmd_sync()
            assert False, "should have exited"
        except SystemExit as e:
            assert "sync rejected" in str(e).lower()
            assert "force" in str(e).lower()
    finally:
        server.shutdown()


def test_sync_force_skips_pull_and_overwrites(log_module, tmp_path, monkeypatch):
    """sync force pushes with X-Sync-Force and no pull-first GET."""
    state = SyncStubState()
    state.stored = json.dumps({"exported": "2026-09-17T12:05:00", "workouts": [],
                               "sets": [], "bodyweight": []})
    state.always_conflict = True
    server = start_stub(state)
    try:
        write_cfg(tmp_path, monkeypatch, log_module, server.server_port)
        out = capture(log_module.cmd_sync, True)
        assert json.loads(out.strip().splitlines()[0])["synced"] is True
        puts = [r for r in state.requests if r["method"] == "PUT"]
        assert not [r for r in state.requests if r["method"] == "GET"]
        assert len(puts) == 1 and puts[0]["force"] == "1"
        assert json.loads(state.stored)["exported"] != "2026-09-17T12:05:00"
    finally:
        server.shutdown()
