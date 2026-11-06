import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as records_app


class RecordApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "test.db"
        self.database_patch = patch.object(records_app, "DATABASE_PATH", self.database_path)
        self.database_patch.start()
        self.client_context = TestClient(records_app.app)
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.database_patch.stop()
        self.temporary_directory.cleanup()

    def create_record(self, **overrides: str) -> dict:
        payload = {
            "record_date": "2026-11-04",
            "consult_type": "directa",
            "full_name": "Ana Pérez",
            "address": "Calle 123",
            "dni": "12345678",
            "kinship": "Madre",
            "consultation": "Solicita orientación para su familia.",
            "referral": "Derivación al área social.",
        }
        payload.update(overrides)
        response = self.client.post("/api/records", json=payload)
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_create_search_update_and_delete_record(self) -> None:
        record = self.create_record()
        self.assertEqual(record["full_name"], "Ana Pérez")
        self.assertEqual(record["consult_type"], "directa")

        search_response = self.client.get("/api/records", params={"search": "12345678"})
        self.assertEqual([item["id"] for item in search_response.json()], [record["id"]])

        updated_response = self.client.put(
            f"/api/records/{record['id']}",
            json={
                "record_date": "2026-11-05",
                "consult_type": "indirecta",
                "full_name": "Ana Pérez",
                "consultation": "Un familiar solicita orientación.",
            },
        )
        self.assertEqual(updated_response.status_code, 200)
        self.assertEqual(updated_response.json()["consult_type"], "indirecta")
        self.assertIsNone(updated_response.json()["dni"])

        delete_response = self.client.delete(f"/api/records/{record['id']}")
        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(self.client.get("/api/records").json(), [])

    def test_rejects_invalid_consultation_type(self) -> None:
        response = self.client.post(
            "/api/records",
            json={
                "record_date": "2026-11-04",
                "consult_type": "otra",
                "full_name": "Ana Pérez",
                "consultation": "Solicita orientación.",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_missing_record_returns_not_found(self) -> None:
        response = self.client.get("/api/records/999")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
