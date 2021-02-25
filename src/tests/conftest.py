import threading
import pytest

from flask import Flask
from werkzeug.serving import make_server
from contextlib import contextmanager


class WebServer:
    HOST = "0.0.0.0"
    PORT = 1337

    def __init__(self, app):
        self.app = app

    @contextmanager
    def run(self):
        webserver = make_server(self.HOST, self.PORT, self.app, threaded=True)
        thread = threading.Thread(target=webserver.serve_forever, daemon=True)
        thread.start()
        try:
            yield self
        finally:
            webserver.shutdown()
            thread.join()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.PORT}"


@pytest.fixture(scope="function")
def server():
    app = Flask("test")
    return WebServer(app)