from __future__ import annotations

import unittest

from torrent_dashboard.integrations import (
    delete_integration,
    integration_catalog,
    normalize_integration,
    save_integration,
)


class IntegrationModuleTests(unittest.TestCase):
    def test_normalize_preserves_existing_secret_when_blank(self):
        existing = {
            "id": "sonarr-1",
            "type": "sonarr",
            "name": "Sonarr",
            "enabled": True,
            "url": "http://sonarr:8989",
            "api_key": "stored-key",
        }
        item = normalize_integration(
            {"id": "sonarr-1", "type": "sonarr", "url": "http://sonarr:8989/", "api_key": ""},
            existing,
        )
        self.assertEqual(item["api_key"], "stored-key")
        self.assertEqual(item["url"], "http://sonarr:8989")

    def test_normalize_rejects_invalid_provider_url(self):
        with self.assertRaisesRegex(RuntimeError, "must start with http"):
            normalize_integration({"type": "sonarr", "url": "sonarr:8989", "api_key": "abc"})

    def test_save_and_delete_round_trip(self):
        cfg = {"integrations": []}
        updated, item = save_integration(
            cfg,
            {"type": "ntfy", "name": "Alerts", "topic_url": "https://ntfy.sh/example"},
        )
        self.assertEqual(len(updated["integrations"]), 1)
        removed = delete_integration(updated, item["id"])
        self.assertEqual(removed["integrations"], [])
        self.assertEqual(cfg["integrations"], [])

    def test_catalog_exposes_provider_form_metadata(self):
        catalog = {item["type"]: item for item in integration_catalog()}
        self.assertIn("sonarr", catalog)
        api_key = next(field for field in catalog["sonarr"]["fields"] if field["key"] == "api_key")
        self.assertTrue(api_key["secret"])
        self.assertTrue(api_key["required"])


if __name__ == "__main__":
    unittest.main()
