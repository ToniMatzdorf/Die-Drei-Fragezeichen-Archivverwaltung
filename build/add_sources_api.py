
from pathlib import Path
from datetime import datetime
import shutil

backend_path = Path(
    r"C:\DreiFragezeichenArchiv\Verwaltung\app\backend.py"
)

if not backend_path.exists():
    raise FileNotFoundError(f"Backend nicht gefunden: {backend_path}")

content = backend_path.read_text(encoding="utf-8")

if "def sources_page():" in content or "/api/sources" in content:
    raise RuntimeError(
        "Eine Quellenverwaltung scheint bereits vorhanden zu sein. "
        "Es wurden keine Änderungen vorgenommen."
    )

# Sicherungskopie erstellen
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = backend_path.with_name(
    f"backend_backup_{timestamp}.py"
)
shutil.copy2(backend_path, backup_path)

# Seitenroute ergänzen
page_anchor = '''@app.get("/keywords")
def keywords_page():
    return FileResponse(APP_DIR / "templates" / "keywords.html")
'''

page_addition = '''

@app.get("/sources")
def sources_page():
    return FileResponse(APP_DIR / "templates" / "sources.html")
'''

if page_anchor not in content:
    raise RuntimeError("Die Schlagwort-Seitenroute wurde nicht gefunden.")

content = content.replace(
    page_anchor,
    page_anchor + page_addition,
    1
)

# Datenmodelle ergänzen
model_anchor = '''class KeywordEpisodeAssignment(BaseModel):
    episode_id: int
'''

model_addition = '''

class Source(BaseModel):
    title: str
    source_type: Optional[str] = None
    author: Optional[str] = None
    publication_date: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None


class SourceEpisodeAssignment(BaseModel):
    episode_id: int
    notes: Optional[str] = None
'''

if model_anchor not in content:
    raise RuntimeError("Das Schlagwort-Datenmodell wurde nicht gefunden.")

content = content.replace(
    model_anchor,
    model_anchor + model_addition,
    1
)

# API-Endpunkte ergänzen
api_addition = '''

# ---------------------------------------------------------
# QUELLEN
# ---------------------------------------------------------

@app.get("/api/sources")
def get_sources(search: str = ""):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, source_type, author,
                   publication_date, url, notes
            FROM sources
            WHERE title LIKE ?
               OR author LIKE ?
               OR source_type LIKE ?
            ORDER BY title COLLATE NOCASE
            """,
            (f"%{search}%", f"%{search}%", f"%{search}%")
        ).fetchall()

    return [dict(row) for row in rows]


@app.post("/api/sources")
def create_source(source: Source):
    title = source.title.strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Bitte einen Titel für die Quelle eingeben."
        )

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO sources
                (title, source_type, author, publication_date, url, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                source.source_type,
                source.author,
                source.publication_date,
                source.url,
                source.notes
            )
        )

        source_id = cursor.lastrowid

    return {"id": source_id, "title": title}


@app.get("/api/sources/{source_id}")
def get_source(source_id: int):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, title, source_type, author,
                   publication_date, url, notes
            FROM sources
            WHERE id = ?
            """,
            (source_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Quelle nicht gefunden."
        )

    return dict(row)


@app.put("/api/sources/{source_id}")
def update_source(source_id: int, source: Source):
    title = source.title.strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Bitte einen Titel für die Quelle eingeben."
        )

    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE sources
            SET title = ?,
                source_type = ?,
                author = ?,
                publication_date = ?,
                url = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                title,
                source.source_type,
                source.author,
                source.publication_date,
                source.url,
                source.notes,
                source_id
            )
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Quelle nicht gefunden."
            )

    return {"id": source_id, "title": title}


@app.delete("/api/sources/{source_id}")
def delete_source(source_id: int):
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM sources WHERE id = ?",
            (source_id,)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Quelle nicht gefunden."
            )

    return {"message": "Quelle gelöscht."}


@app.get("/api/sources/{source_id}/episodes")
def get_source_episodes(source_id: int):
    with get_connection() as conn:
        source = conn.execute(
            "SELECT id FROM sources WHERE id = ?",
            (source_id,)
        ).fetchone()

        if source is None:
            raise HTTPException(
                status_code=404,
                detail="Quelle nicht gefunden."
            )

        rows = conn.execute(
            """
            SELECT
                e.id AS episode_id,
                e.episode_number,
                e.title,
                es.notes
            FROM episode_sources es
            JOIN episodes e ON e.id = es.episode_id
            WHERE es.source_id = ?
            ORDER BY e.episode_number
            """,
            (source_id,)
        ).fetchall()

    return [dict(row) for row in rows]


@app.post("/api/sources/{source_id}/episodes")
def assign_source_episode(
    source_id: int,
    assignment: SourceEpisodeAssignment
):
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO episode_sources
                    (episode_id, source_id, notes)
                VALUES (?, ?, ?)
                """,
                (
                    assignment.episode_id,
                    source_id,
                    assignment.notes
                )
            )

        return {"message": "Quelle zugeordnet."}

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Die Zuordnung existiert bereits oder die Folge bzw. Quelle wurde nicht gefunden."
        )


@app.delete("/api/sources/{source_id}/episodes/{episode_id}")
def remove_source_episode(source_id: int, episode_id: int):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM episode_sources
            WHERE source_id = ? AND episode_id = ?
            """,
            (source_id, episode_id)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Zuordnung nicht gefunden."
            )

    return {"message": "Zuordnung entfernt."}

'''

content += api_addition

backend_path.write_text(content, encoding="utf-8")

print("Quellenverwaltung erfolgreich in backend.py ergänzt.")
print(f"Sicherungskopie: {backup_path}")
print(f"Backend-Datei: {backend_path}")
