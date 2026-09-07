from __future__ import annotations

import io
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from torrent_dashboard.dashboard import QBitClient, parse_multipart


def make_client():
    return QBitClient({
        "id": "test",
        "name": "qBitTorrent",
        "base_url": "http://127.0.0.1:8080",
        "auth_method": "api_key",
        "api_key": "qbt_" + ("x" * 28),
        "username": "",
        "password": "",
    })


class TorrentAddApiTests(unittest.TestCase):
    def test_multipart_filename_stops_at_content_disposition_line(self):
        boundary = "----TorrentDashboardTest"
        payload = b"ID3\x04\x00\x00audio"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="sound"; filename="alert.mp3"\r\n'
            "Content-Type: audio/mpeg\r\n\r\n"
        ).encode() + payload + f"\r\n--{boundary}--\r\n".encode()
        handler = SimpleNamespace(
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
            },
            rfile=io.BytesIO(body),
        )
        fields, files = parse_multipart(handler)
        self.assertEqual(fields, {})
        self.assertEqual(files[0][0], "sound")
        self.assertEqual(files[0][1], "alert.mp3")
        self.assertEqual(files[0][2], payload)

    def test_cached_add_serializes_file_priorities(self):
        client = make_client()
        client.post = Mock(return_value=(200, b""))
        client.action("add_torrent", {
            "source": "a" * 40,
            "file_priorities": [1, 0, 6, 7],
            "stopped": False,
        })
        path, form = client.post.call_args.args
        self.assertEqual(path, "/api/v2/torrents/add")
        self.assertEqual(form["urls"], "a" * 40)
        self.assertEqual(form["filePriorities"], "1,0,6,7")

    def test_cached_add_rejects_invalid_file_priority(self):
        client = make_client()
        client.post = Mock(return_value=(200, b""))
        with self.assertRaisesRegex(RuntimeError, "Unsupported torrent file priority"):
            client.action("add_torrent", {"source": "a" * 40, "file_priorities": [1, 2]})
        client.post.assert_not_called()

    def test_metadata_save_falls_back_to_existing_torrent_export(self):
        client = make_client()
        calls = []

        def request(method, path, **kwargs):
            calls.append(path)
            if "/saveMetadata?" in path:
                raise RuntimeError("qBittorrent HTTP 409: Metadata is not yet available")
            if "/export?" in path:
                return 200, b"d4:test4:datae"
            raise AssertionError(path)

        client._request = Mock(side_effect=request)
        status, body = client.save_torrent_metadata("magnet:?xt=urn:btih:test", "b" * 40)
        self.assertEqual(status, 200)
        self.assertTrue(body)
        self.assertTrue(any("/api/v2/torrents/export?" in path for path in calls))


if __name__ == "__main__":
    unittest.main()
