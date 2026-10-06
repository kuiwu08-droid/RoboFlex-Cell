"""Local HMI/API over HTTP; all state mutations occur under one lock."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

import cv2
import numpy as np

from .controller import Cell, FAULTS


def make_server(port=8080, seed=42):
    cell = Cell(seed)
    lock = threading.Lock()
    stop_event = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def reply(self, data, status=200, content_type="application/json"):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/":
                self.reply(Path(__file__).with_name("web").joinpath("index.html").read_bytes(),
                           content_type="text/html; charset=utf-8")
            elif path == "/api/status":
                with lock:
                    status = cell.snapshot()
                status["faults"] = {key: value[1] for key, value in FAULTS.items()}
                self.reply(status)
            elif path == "/api/frame":
                with lock:
                    frame = cell.image.copy() if cell.image is not None else np.full((480, 640, 3), 24, np.uint8)
                    target = cell.target.copy() if cell.target else None
                if target:
                    point = tuple(int(round(v)) for v in target["pixel"])
                    cv2.drawMarker(frame, point, (60, 220, 80), cv2.MARKER_CROSS, 30, 2)
                    cv2.putText(frame, target["kind"], (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (60, 220, 80), 2)
                _, encoded = cv2.imencode(".jpg", frame)
                self.reply(encoded.tobytes(), content_type="image/jpeg")
            else:
                self.reply({"error": "Not found"}, 404)

        def do_POST(self):
            # Only same-origin JSON calls. This simulator never exposes robot I/O.
            origin = self.headers.get("Origin")
            if origin and origin != f"http://{self.headers.get('Host')}":
                self.reply({"error": "Origin rejected"}, 403)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024 or self.headers.get("Content-Type") != "application/json":
                    raise ValueError("Expected a small JSON request")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("Expected JSON object")
                with lock:
                    if self.path != "/api/command":
                        self.reply({"error": "Not found"}, 404)
                        return
                    command = payload.get("command")
                    accepted = True
                    if command == "start":
                        accepted = cell.start()
                    elif command == "stop":
                        cell.stop()
                    elif command == "reset":
                        accepted = cell.reset(clear_part=payload.get("clear_part") is True)
                    elif command == "fault":
                        cell.inject(payload.get("fault"))
                    elif command == "clear_fault":
                        cell.fault = None
                    else:
                        raise ValueError("Unknown command")
                    self.reply({"accepted": accepted, "status": cell.snapshot()}, 200 if accepted else 409)
            except (ValueError, TypeError) as exc:
                self.reply({"error": str(exc)}, 400)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)

    def scan():
        while not stop_event.wait(0.01):
            with lock:
                cell.tick(0.01)

    server.cell, server.cell_lock, server.stop_event = cell, lock, stop_event
    server.scan_thread = threading.Thread(target=scan, daemon=True)
    return server


def serve(port=8080, seed=42):
    server = make_server(port, seed)
    server.scan_thread.start()
    print(f"RoboFlex Cell HMI: http://127.0.0.1:{server.server_port}", flush=True)
    print("Software-in-the-loop simulation. Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop_event.set()
        server.server_close()
