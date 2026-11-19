from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as records_app


class ApiTestCase(unittest.TestCase):
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

class RecordApiTests(ApiTestCase):
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

    def test_migrates_records_table_without_losing_records(self) -> None:
        with closing(records_app.get_connection()) as connection:
            connection.execute('DROP TABLE "PrimeraConsulta"')
            connection.execute(
                """
                CREATE TABLE records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_date TEXT NOT NULL,
                    consult_type TEXT NOT NULL CHECK (consult_type IN ('directa', 'indirecta')),
                    full_name TEXT NOT NULL,
                    address TEXT,
                    dni TEXT,
                    kinship TEXT,
                    consultation TEXT NOT NULL,
                    referral TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            connection.execute(
                """
                INSERT INTO records
                    (record_date, consult_type, full_name, consultation)
                VALUES ('2026-11-04', 'directa', 'Ana Pérez', 'Solicita orientación.')
                """,
            )
            connection.commit()

        records_app.initialize_database()

        with closing(records_app.get_connection()) as connection:
            table_names = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        self.assertIn("PrimeraConsulta", table_names)
        self.assertNotIn("records", table_names)

        response = self.client.get("/api/records")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["full_name"], "Ana Pérez")

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


class ContactApiTests(ApiTestCase):
    def create_contact(self, **overrides: str) -> dict:
        payload = {
            "full_name": "Ana Pérez",
            "date_and_place": "2026-11-04, Oberá",
            "manifest_demand": "Solicita orientación para su familia.",
            "activity": "Taller comunitario",
        }
        payload.update(overrides)
        response = self.client.post("/api/contacts", json=payload)
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_migrates_contacts_table_without_losing_records(self) -> None:
        with closing(records_app.get_connection()) as connection:
            connection.execute('DROP TABLE "primerContacto"')
            connection.execute(
                """
                CREATE TABLE contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            connection.execute(
                "INSERT INTO contacts (full_name, data_json) VALUES (?, ?)",
                ("Ana Pérez", '{"full_name":"Ana Pérez"}'),
            )
            connection.commit()

        records_app.initialize_database()

        with closing(records_app.get_connection()) as connection:
            table_names = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        self.assertIn("primerContacto", table_names)
        self.assertNotIn("contacts", table_names)

        response = self.client.get("/api/contacts")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["full_name"], "Ana Pérez")

    def test_create_list_update_and_delete_contact(self) -> None:
        contact = self.create_contact()
        self.assertEqual(contact["full_name"], "Ana Pérez")
        self.assertEqual(contact["manifest_demand"], "Solicita orientación para su familia.")

        list_response = self.client.get("/api/contacts")
        self.assertEqual([item["id"] for item in list_response.json()], [contact["id"]])

        updated_response = self.client.put(
            f"/api/contacts/{contact['id']}",
            json={
                "full_name": "Ana Pérez",
                "phone": "3755-123456",
                "manifest_demand": "Consulta actualizada.",
            },
        )
        self.assertEqual(updated_response.status_code, 200)
        self.assertEqual(updated_response.json()["phone"], "3755-123456")
        self.assertEqual(updated_response.json()["activity"], None)

        delete_response = self.client.delete(f"/api/contacts/{contact['id']}")
        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(self.client.get("/api/contacts").json(), [])

    def test_rejects_contact_without_valid_name(self) -> None:
        response = self.client.post("/api/contacts", json={"full_name": "A"})
        self.assertEqual(response.status_code, 422)

    def test_missing_contact_returns_not_found(self) -> None:
        response = self.client.get("/api/contacts/999")
        self.assertEqual(response.status_code, 404)


class ResidenceApiTests(ApiTestCase):
    def test_create_list_and_update_residence(self) -> None:
        payload = {
            "nombre_querido": "Casa Esperanza",
            "direccion": "Calle 123, Oberá",
            "ocupacion": 8,
            "capacidad": 12,
        }
        created_response = self.client.post("/api/residences", json=payload)
        self.assertEqual(created_response.status_code, 201)
        residence = created_response.json()
        self.assertEqual(residence["nombre_querido"], "Casa Esperanza")
        self.assertEqual(residence["ocupacion"], 8)

        list_response = self.client.get("/api/residences")
        self.assertEqual([item["id"] for item in list_response.json()], [residence["id"]])

        payload["capacidad"] = 15
        updated_response = self.client.put(
            f"/api/residences/{residence['id']}",
            json=payload,
        )
        self.assertEqual(updated_response.status_code, 200)
        self.assertEqual(updated_response.json()["capacidad"], 15)

    def test_rejects_residence_with_invalid_capacity(self) -> None:
        response = self.client.post(
            "/api/residences",
            json={
                "nombre_querido": "Casa Esperanza",
                "direccion": "Calle 123",
                "ocupacion": 1,
                "capacidad": -1,
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_name_is_the_only_required_residence_field(self) -> None:
        response = self.client.post(
            "/api/residences",
            json={"nombre_querido": "Residencia mínima"},
        )
        self.assertEqual(response.status_code, 201)
        residence = response.json()
        self.assertEqual(residence["direccion"], "")
        self.assertEqual(residence["ocupacion"], 0)
        self.assertEqual(residence["capacidad"], 0)


if __name__ == "__main__":
    unittest.main()
