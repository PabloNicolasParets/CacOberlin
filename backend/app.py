from contextlib import closing, asynccontextmanager
from datetime import date
import json
import os
from pathlib import Path
import sqlite3
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field


DATABASE_PATH = Path(
    os.environ.get(
        "PRIMERA_ESCUCHA_DB",
        str(Path(__file__).parent / "data" / "CACOberlin.db"),
    )
)


class RecordInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    record_date: date
    consult_type: Literal["directa", "indirecta"]
    full_name: str = Field(min_length=2, max_length=160)
    address: str | None = Field(default=None, max_length=240)
    dni: str | None = Field(default=None, max_length=32)
    kinship: str | None = Field(default=None, max_length=80)
    consultation: str = Field(min_length=3, max_length=5000)
    referral: str | None = Field(default=None, max_length=2000)


class Record(RecordInput):
    id: int
    created_at: str


class ContactInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    date_and_place: str | None = Field(default=None, max_length=240)
    full_name: str = Field(min_length=2, max_length=160)
    birth_date: str | None = Field(default=None, max_length=40)
    self_perceived_gender: str | None = Field(default=None, max_length=240)
    dni: str | None = Field(default=None, max_length=32)
    housing_situation: str | None = Field(default=None, max_length=2000)
    residence_address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=80)
    contact_datetime: str | None = Field(default=None, max_length=80)
    access_mode: str | None = Field(default=None, max_length=2000)
    manifest_demand: str | None = Field(default=None, max_length=5000)
    latent_demand: str | None = Field(default=None, max_length=5000)
    affective_references: str | None = Field(default=None, max_length=5000)
    household_structure: str | None = Field(default=None, max_length=5000)
    literacy: str | None = Field(default=None, max_length=2000)
    education_level: str | None = Field(default=None, max_length=2000)
    employment_situation: str | None = Field(default=None, max_length=2000)
    disability: str | None = Field(default=None, max_length=80)
    disability_details: str | None = Field(default=None, max_length=2000)
    health: str | None = Field(default=None, max_length=5000)
    violence_present: str | None = Field(default=None, max_length=80)
    violence_details: str | None = Field(default=None, max_length=3000)
    legal_conflict: str | None = Field(default=None, max_length=2000)
    rights_accessibility: str | None = Field(default=None, max_length=3000)
    substance: str | None = Field(default=None, max_length=2000)
    frequency: str | None = Field(default=None, max_length=1000)
    medication_treatment: str | None = Field(default=None, max_length=3000)
    consumption_observations: str | None = Field(default=None, max_length=3000)
    previous_treatments: str | None = Field(default=None, max_length=5000)
    first_response: str | None = Field(default=None, max_length=5000)
    accompaniment_proposals: str | None = Field(default=None, max_length=3000)
    participation_activities: str | None = Field(default=None, max_length=3000)
    activity: str | None = Field(default=None, max_length=1000)
    activity_day_time: str | None = Field(default=None, max_length=500)
    activity_place: str | None = Field(default=None, max_length=500)
    activity_referent: str | None = Field(default=None, max_length=500)
    second_response: str | None = Field(default=None, max_length=5000)
    follow_up_observations: str | None = Field(default=None, max_length=5000)


class Contact(ContactInput):
    id: int
    created_at: str


class ResidenceInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nombre_querido: str = Field(min_length=2, max_length=160)
    direccion: str = Field(default="", max_length=500)
    ocupacion: int = Field(default=0, ge=0, le=100000)
    capacidad: int = Field(default=0, ge=0, le=100000)


class Residence(ResidenceInput):
    id: int
    created_at: str


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with closing(get_connection()) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if "records" in tables and "PrimeraConsulta" in tables:
            raise RuntimeError(
                "No se puede renombrar records: records y PrimeraConsulta existen."
            )
        if "records" in tables:
            connection.execute('ALTER TABLE records RENAME TO "PrimeraConsulta"')
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS "PrimeraConsulta" (
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
        if "contacts" in tables and "primerContacto" in tables:
            raise RuntimeError(
                "No se puede renombrar contacts: contacts y primerContacto existen."
            )
        if "contacts" in tables:
            connection.execute('ALTER TABLE contacts RENAME TO "primerContacto"')
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS "primerContacto" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS "Residencias" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_querido TEXT NOT NULL,
                direccion TEXT NOT NULL DEFAULT '',
                ocupacion INTEGER NOT NULL DEFAULT 0 CHECK (ocupacion >= 0),
                capacidad INTEGER NOT NULL DEFAULT 0 CHECK (capacidad >= 0),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        residence_columns = {
            row["name"]: row
            for row in connection.execute(
                'PRAGMA table_info("Residencias")'
            ).fetchall()
        }
        if (
            "ocupacion" in residence_columns
            and residence_columns["ocupacion"]["type"].upper() != "INTEGER"
        ):
            connection.execute('ALTER TABLE "Residencias" RENAME TO "Residencias_old"')
            connection.execute(
                """
                CREATE TABLE "Residencias" (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre_querido TEXT NOT NULL,
                    direccion TEXT NOT NULL DEFAULT '',
                    ocupacion INTEGER NOT NULL DEFAULT 0 CHECK (ocupacion >= 0),
                    capacidad INTEGER NOT NULL DEFAULT 0 CHECK (capacidad >= 0),
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            connection.execute(
                """
                INSERT INTO "Residencias"
                    (id, nombre_querido, direccion, ocupacion, capacidad, created_at, updated_at)
                SELECT
                    id,
                    nombre_querido,
                    COALESCE(direccion, ''),
                    CASE WHEN typeof(ocupacion) = 'integer' THEN ocupacion ELSE 0 END,
                    CASE WHEN typeof(capacidad) = 'integer' AND capacidad >= 0 THEN capacidad ELSE 0 END,
                    created_at,
                    updated_at
                FROM "Residencias_old"
                """
            )
            connection.execute('DROP TABLE "Residencias_old"')
        connection.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Primera escucha", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


def fetch_record(record_id: int) -> dict:
    with closing(get_connection()) as connection:
        row = connection.execute(
            'SELECT * FROM "PrimeraConsulta" WHERE id = ?', (record_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="No se encontró el registro.")
    return dict(row)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/records", response_model=list[Record])
def list_records(
    search: str | None = Query(default=None, max_length=160),
    consult_type: Literal["directa", "indirecta"] | None = None,
) -> list[dict]:
    conditions: list[str] = []
    parameters: list[str] = []

    if search:
        term = f"%{search.strip()}%"
        conditions.append(
            "(full_name LIKE ? OR dni LIKE ? OR consultation LIKE ? OR referral LIKE ?)"
        )
        parameters.extend([term, term, term, term])
    if consult_type:
        conditions.append("consult_type = ?")
        parameters.append(consult_type)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with closing(get_connection()) as connection:
        rows = connection.execute(
            f'SELECT * FROM "PrimeraConsulta" {where_clause} ORDER BY record_date DESC, id DESC',
            parameters,
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/records", response_model=Record, status_code=201)
def create_record(record: RecordInput) -> dict:
    values = record.model_dump(mode="json")
    with closing(get_connection()) as connection:
        cursor = connection.execute(
            """
            INSERT INTO "PrimeraConsulta"
                (record_date, consult_type, full_name, address, dni, kinship, consultation, referral)
            VALUES
                (:record_date, :consult_type, :full_name, :address, :dni, :kinship, :consultation, :referral)
            """,
            values,
        )
        connection.commit()
        record_id = cursor.lastrowid
    return fetch_record(record_id)


@app.get("/api/records/{record_id}", response_model=Record)
def get_record(record_id: int) -> dict:
    return fetch_record(record_id)


@app.put("/api/records/{record_id}", response_model=Record)
def update_record(record_id: int, record: RecordInput) -> dict:
    fetch_record(record_id)
    values = record.model_dump(mode="json")
    values["id"] = record_id
    with closing(get_connection()) as connection:
        connection.execute(
            """
            UPDATE "PrimeraConsulta"
            SET record_date = :record_date,
                consult_type = :consult_type,
                full_name = :full_name,
                address = :address,
                dni = :dni,
                kinship = :kinship,
                consultation = :consultation,
                referral = :referral
            WHERE id = :id
            """,
            values,
        )
        connection.commit()
    return fetch_record(record_id)


@app.delete("/api/records/{record_id}", status_code=204)
def delete_record(record_id: int) -> Response:
    fetch_record(record_id)
    with closing(get_connection()) as connection:
        connection.execute('DELETE FROM "PrimeraConsulta" WHERE id = ?', (record_id,))
        connection.commit()
    return Response(status_code=204)


def fetch_contact(contact_id: int) -> dict:
    with closing(get_connection()) as connection:
        row = connection.execute(
            'SELECT id, data_json, created_at FROM "primerContacto" WHERE id = ?',
            (contact_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="No se encontró el primer contacto.")
    return {**json.loads(row["data_json"]), "id": row["id"], "created_at": row["created_at"]}


@app.get("/api/contacts", response_model=list[Contact])
def list_contacts() -> list[dict]:
    with closing(get_connection()) as connection:
        rows = connection.execute(
            'SELECT id, data_json, created_at FROM "primerContacto" ORDER BY id DESC'
        ).fetchall()
    return [
        {**json.loads(row["data_json"]), "id": row["id"], "created_at": row["created_at"]}
        for row in rows
    ]


@app.post("/api/contacts", response_model=Contact, status_code=201)
def create_contact(contact: ContactInput) -> dict:
    values = contact.model_dump(mode="json")
    with closing(get_connection()) as connection:
        cursor = connection.execute(
            'INSERT INTO "primerContacto" (full_name, data_json) VALUES (?, ?)',
            (values["full_name"], json.dumps(values, ensure_ascii=False)),
        )
        connection.commit()
        contact_id = cursor.lastrowid
    return fetch_contact(contact_id)


@app.get("/api/contacts/{contact_id}", response_model=Contact)
def get_contact(contact_id: int) -> dict:
    return fetch_contact(contact_id)


@app.put("/api/contacts/{contact_id}", response_model=Contact)
def update_contact(contact_id: int, contact: ContactInput) -> dict:
    fetch_contact(contact_id)
    values = contact.model_dump(mode="json")
    with closing(get_connection()) as connection:
        connection.execute(
            """
            UPDATE "primerContacto"
            SET full_name = ?, data_json = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (values["full_name"], json.dumps(values, ensure_ascii=False), contact_id),
        )
        connection.commit()
    return fetch_contact(contact_id)


@app.delete("/api/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: int) -> Response:
    fetch_contact(contact_id)
    with closing(get_connection()) as connection:
        connection.execute(
            'DELETE FROM "primerContacto" WHERE id = ?', (contact_id,)
        )
        connection.commit()
    return Response(status_code=204)


def fetch_residence(residence_id: int) -> dict:
    with closing(get_connection()) as connection:
        row = connection.execute(
            'SELECT id, nombre_querido, direccion, ocupacion, capacidad, created_at '
            'FROM "Residencias" WHERE id = ?',
            (residence_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="No se encontró la residencia.")
    return dict(row)


@app.get("/api/residences", response_model=list[Residence])
def list_residences() -> list[dict]:
    with closing(get_connection()) as connection:
        rows = connection.execute(
            'SELECT id, nombre_querido, direccion, ocupacion, capacidad, created_at '
            'FROM "Residencias" ORDER BY nombre_querido COLLATE NOCASE, id'
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/residences", response_model=Residence, status_code=201)
def create_residence(residence: ResidenceInput) -> dict:
    values = residence.model_dump()
    with closing(get_connection()) as connection:
        cursor = connection.execute(
            """
            INSERT INTO "Residencias" (nombre_querido, direccion, ocupacion, capacidad)
            VALUES (:nombre_querido, :direccion, :ocupacion, :capacidad)
            """,
            values,
        )
        connection.commit()
        residence_id = cursor.lastrowid
    return fetch_residence(residence_id)


@app.put("/api/residences/{residence_id}", response_model=Residence)
def update_residence(residence_id: int, residence: ResidenceInput) -> dict:
    fetch_residence(residence_id)
    values = residence.model_dump()
    values["id"] = residence_id
    with closing(get_connection()) as connection:
        connection.execute(
            """
            UPDATE "Residencias"
            SET nombre_querido = :nombre_querido,
                direccion = :direccion,
                ocupacion = :ocupacion,
                capacidad = :capacidad,
                updated_at = datetime('now')
            WHERE id = :id
            """,
            values,
        )
        connection.commit()
    return fetch_residence(residence_id)
