import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from roboflex.server import make_server


@pytest.fixture
def api():
    server = make_server(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


def post(api, body, **headers):
    return urlopen(Request(api + "/api/command", data=json.dumps(body).encode(),
                           headers={"Content-Type": "application/json", **headers}))


def test_hmi_and_camera_endpoints(api):
    assert b"RoboFlex" in urlopen(api).read()
    assert urlopen(api + "/api/frame").headers["Content-Type"] == "image/jpeg"
    assert json.load(urlopen(api + "/api/status"))["state"] == "IDLE"
    assert json.load(post(api, {"command": "start"}))["accepted"]


@pytest.mark.parametrize("payload", [{"command": "unknown"}, {"command": "fault", "fault": "unknown"}, []])
def test_invalid_requests(api, payload):
    with pytest.raises(HTTPError) as error:
        post(api, payload)
    assert error.value.code == 400


def test_cross_origin_commands_rejected(api):
    with pytest.raises(HTTPError) as error:
        post(api, {"command": "start"}, Origin="https://example.com")
    assert error.value.code == 403
