# -*- coding: utf-8 -*-
"""Unit tests for the WLAN access service (openspec/changes/add-wlan-access)."""
import json
import os
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'net'))
from moonboard_net_service import (DEFAULT_ORIGINS, InvalidProblem, TLSServer, allowed_origin,
                                   make_handler, validate_problem, validate_show)


class TestValidateProblem(unittest.TestCase):

    def test_valid_problem(self):
        msg = {"START": ["A1"], "MOVES": ["F9"], "TOP": ["K18"]}
        self.assertEqual(validate_problem(msg), msg)

    def test_optional_roles_kept(self):
        msg = {"START": ["A1"], "MOVES": [], "TOP": ["K18"], "FOOT": ["C2"], "LEFT": ["D5"]}
        self.assertEqual(validate_problem(msg)["FOOT"], ["C2"])

    def test_invalid_column(self):
        with self.assertRaisesRegex(InvalidProblem, "L5"):
            validate_problem({"START": ["L5"], "MOVES": [], "TOP": []})

    def test_invalid_row(self):
        with self.assertRaisesRegex(InvalidProblem, "A19"):
            validate_problem({"START": [], "MOVES": ["A19"], "TOP": []})

    def test_row_zero(self):
        with self.assertRaises(InvalidProblem):
            validate_problem({"START": ["A0"], "MOVES": [], "TOP": []})

    def test_missing_key(self):
        with self.assertRaisesRegex(InvalidProblem, "TOP"):
            validate_problem({"START": [], "MOVES": []})

    def test_unknown_key(self):
        with self.assertRaises(InvalidProblem):
            validate_problem({"START": [], "MOVES": [], "TOP": [], "X": []})

    def test_not_a_list(self):
        with self.assertRaises(InvalidProblem):
            validate_problem({"START": "A1", "MOVES": [], "TOP": []})


class TestShow(unittest.TestCase):

    def test_valid_mode(self):
        self.assertEqual(validate_show({"mode": "feuerreifen"}), "feuerreifen")

    def test_invalid_mode(self):
        for bad in ({"mode": "Zelt; rm"}, {"mode": ""}, {"mode": 3}, {}, []):
            with self.assertRaises(InvalidProblem):
                validate_show(bad)


class TestCors(unittest.TestCase):

    def test_manege_app_origin(self):
        self.assertEqual(allowed_origin("manege://app", DEFAULT_ORIGINS), "manege://app")


    def test_app_origin(self):
        self.assertEqual(allowed_origin("https://10.101.2.71:8443", DEFAULT_ORIGINS),
                         "https://10.101.2.71:8443")

    def test_foreign_origin(self):
        self.assertIsNone(allowed_origin("https://example.com", DEFAULT_ORIGINS))

    def test_no_origin(self):
        self.assertIsNone(allowed_origin(None, DEFAULT_ORIGINS))


class TestWallShowState(unittest.TestCase):
    """The show-mode state must not shadow Wall.show(), or no route reaches the wall."""

    def test_show_stays_callable_after_state_message(self):
        import moonboard_net_service as svc

        class Msg:
            topic = svc.SHOW_STATE
            payload = b"zirkus"

        wall = svc.Wall.__new__(svc.Wall)
        wall.show_mode = None
        self.assertTrue(callable(wall.show))
        wall._on_message(None, None, Msg())
        self.assertTrue(callable(wall.show))
        self.assertEqual(wall.show_mode, "zirkus")


class StubWall:
    connected = True
    show_mode = None

    def status(self):
        return {"ok": True}


@unittest.skipUnless(shutil.which("openssl"), "openssl needed for a test certificate")
class TestTlsServer(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        cert, key = os.path.join(self.dir, "c.pem"), os.path.join(self.dir, "k.pem")
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                        "-subj", "/CN=localhost", "-keyout", key, "-out", cert],
                       check=True, capture_output=True)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        self.server = TLSServer(("127.0.0.1", 0), make_handler(StubWall(), DEFAULT_ORIGINS), context)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.dir)

    def status(self):
        client = ssl.create_default_context()
        client.check_hostname = False
        client.verify_mode = ssl.CERT_NONE
        with socket.create_connection(self.server.server_address, timeout=3) as raw:
            with client.wrap_socket(raw) as tls:
                tls.sendall(b"GET /status HTTP/1.0\r\n\r\n")
                data = b""
                while True:
                    chunk = tls.recv(4096)
                    if not chunk:
                        break
                    data += chunk
        return json.loads(data.split(b"\r\n\r\n", 1)[1])

    def test_idle_connection_does_not_block_others(self):
        idle = socket.create_connection(self.server.server_address)
        try:
            self.assertEqual(self.status(), {"ok": True})
        finally:
            idle.close()


if __name__ == '__main__':
    unittest.main()
