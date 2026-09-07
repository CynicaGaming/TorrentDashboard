"""Exercise hostile framing and byte-preserving browser uploads."""

from email.message import Message
import io
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from torrent_dashboard.http_input import parse_json_body, parse_multipart


def handler(body=b"", **headers):
    values = Message()
    values["Content-Length"] = str(len(body))
    for name, value in headers.items():
        if name in values:
            del values[name]
        values[name] = value
    return SimpleNamespace(headers=values, rfile=io.BytesIO(body))


class HttpInputTests(unittest.TestCase):
    def test_invalid_lengths_never_read_the_stream(self):
        for value in ("-1", "+2", "1, 1", "invalid", "", "９"):
            with self.subTest(value=value):
                request = handler(**{"Content-Length": value})
                request.rfile = Mock()
                with self.assertRaisesRegex(RuntimeError, "Content-Length"):
                    parse_json_body(request)
                request.rfile.read.assert_not_called()

    def test_ambiguous_framing_is_rejected(self):
        request = handler(b"{}")
        request.headers["Content-Length"] = "2"
        with self.assertRaisesRegex(RuntimeError, "Multiple"):
            parse_json_body(request)
        request = handler(b"{}", **{"Transfer-Encoding": "chunked"})
        with self.assertRaisesRegex(RuntimeError, "Transfer-Encoding"):
            parse_json_body(request)

    def test_truncation_and_size_limit_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Incomplete"):
            parse_json_body(handler(b"{}", **{"Content-Length": "5"}))
        with self.assertRaisesRegex(RuntimeError, "too large"):
            parse_json_body(handler(b"{}"), max_bytes=1)

    def test_json_requires_an_object(self):
        for body in (b"[]", b"null", b"true", b"1", b'"text"', b"\xff", b"{"):
            with self.subTest(body=body), self.assertRaises(RuntimeError):
                parse_json_body(handler(body))
        self.assertEqual(parse_json_body(handler(b'{"value": 1}')), {"value": 1})
        self.assertEqual(parse_json_body(handler()), {})

    def test_upload_preserves_embedded_boundary_text_and_binary_bytes(self):
        boundary = "BoundaryForTest"
        content = b"\x00\xffprefix--BoundaryForTestinside\r\ntrailing\r\n"
        body = (
            b'--BoundaryForTest\r\nContent-Disposition: form-data; name="file"; filename="sample.tdbackup"\r\n'
            b'Content-Type: application/octet-stream\r\n\r\n' + content + b"\r\n--BoundaryForTest--\r\n"
        )
        request = handler(body, **{"Content-Type": f'multipart/form-data; boundary="{boundary}"; charset=utf-8'})
        fields, files = parse_multipart(request)
        self.assertEqual(fields, {})
        self.assertEqual(files, [("file", "sample.tdbackup", content)])

    def test_missing_closing_boundary_is_rejected(self):
        body = b'--test\r\nContent-Disposition: form-data; name="field"\r\n\r\nvalue'
        with self.assertRaisesRegex(RuntimeError, "multipart"):
            parse_multipart(handler(body, **{"Content-Type": "multipart/form-data; boundary=test"}))
