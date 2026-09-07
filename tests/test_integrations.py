from __future__ import annotations

import unittest
from unittest import mock
import urllib.error

from torrent_dashboard.integrations import (
    delete_integration,
    integration_catalog,
    normalize_integration,
    probe_integration_health,
    save_integration,
    save_jellyfin_task_favorites,
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

    def test_jellyfin_favorite_task_ids_persist_and_deduplicate(self):
        cfg = {"integrations": [{
            "id": "jellyfin-1",
            "type": "jellyfin",
            "name": "Jellyfin",
            "enabled": True,
            "url": "http://jellyfin:8096",
            "api_key": "stored-key",
        }]}
        updated, item = save_jellyfin_task_favorites(cfg, "jellyfin-1", ["task-a", "task-a", "task-b", ""])
        self.assertEqual(item["favorite_task_ids"], ["task-a", "task-b"])
        normalized = normalize_integration(
            {"id": "jellyfin-1", "type": "jellyfin", "url": "http://jellyfin:8096", "api_key": ""},
            item,
        )
        self.assertEqual(normalized["favorite_task_ids"], ["task-a", "task-b"])
        reordered, reordered_item = save_jellyfin_task_favorites(updated, "jellyfin-1", ["task-b", "task-a"])
        self.assertEqual(reordered_item["favorite_task_ids"], ["task-b", "task-a"])
        renormalized = normalize_integration(
            {"id": "jellyfin-1", "type": "jellyfin", "url": "http://jellyfin:8096", "api_key": ""},
            reordered_item,
        )
        self.assertEqual(renormalized["favorite_task_ids"], ["task-b", "task-a"])
        self.assertNotIn("favorite_task_ids", cfg["integrations"][0])

    def test_catalog_exposes_provider_form_metadata(self):
        catalog = {item["type"]: item for item in integration_catalog()}
        self.assertIn("sonarr", catalog)
        api_key = next(field for field in catalog["sonarr"]["fields"] if field["key"] == "api_key")
        self.assertTrue(api_key["secret"])
        self.assertTrue(api_key["required"])


    def test_health_marks_disabled_integration_disconnected(self):
        health = probe_integration_health({
            "type": "sonarr",
            "name": "Sonarr",
            "enabled": False,
            "url": "http://sonarr:8989",
            "api_key": "abc",
        })
        self.assertEqual(health["state"], "disconnected")

    def test_health_marks_reachable_auth_failure_as_issue(self):
        error = urllib.error.HTTPError("http://sonarr:8989", 401, "Unauthorized", {}, None)
        with mock.patch("torrent_dashboard.integrations.urllib.request.urlopen", side_effect=error):
            health = probe_integration_health({
                "type": "sonarr",
                "name": "Sonarr",
                "enabled": True,
                "url": "http://sonarr:8989",
                "api_key": "bad",
            })
        self.assertEqual(health["state"], "issue")


if __name__ == "__main__":
    unittest.main()
