from contextlib import closing, asynccontextmanager
from datetime import date
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


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with closing(get_connection()) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
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
            "SELECT * FROM records WHERE id = ?", (record_id,)
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
            f"SELECT * FROM records {where_clause} ORDER BY record_date DESC, id DESC",
            parameters,
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/records", response_model=Record, status_code=201)
def create_record(record: RecordInput) -> dict:
    values = record.model_dump(mode="json")
    with closing(get_connection()) as connection:
        cursor = connection.execute(
            """
            INSERT INTO records
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
            UPDATE records
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
        connection.execute("DELETE FROM records WHERE id = ?", (record_id,))
        connection.commit()
    return Response(status_code=204)
