
from pathlib import Path
from datetime import datetime
import shutil

backend_path = Path(
    r"C:\DreiFragezeichenArchiv\Verwaltung\app\backend.py"
)

if not backend_path.exists():
    raise FileNotFoundError(f"Backend nicht gefunden: {backend_path}")

content = backend_path.read_text(encoding="utf-8")

if "def keywords_page():" in content or "/api/keywords" in content:
    raise RuntimeError(
        "Eine Schlagwortverwaltung scheint bereits vorhanden zu sein. "
        "Es wurden keine Änderungen vorgenommen."
    )

# Sicherungskopie erstellen
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = backend_path.with_name(
    f"backend_backup_{timestamp}.py"
)
shutil.copy2(backend_path, backup_path)

# Seitenroute ergänzen
page_anchor = '''@app.get("/organizations")
def organizations_page():
    return FileResponse(APP_DIR / "templates" / "organizations.html")
'''

page_addition = '''

@app.get("/keywords")
def keywords_page():
    return FileResponse(APP_DIR / "templates" / "keywords.html")
'''

if page_anchor not in content:
    raise RuntimeError("Die Organisations-Seitenroute wurde nicht gefunden.")

content = content.replace(
    page_anchor,
    page_anchor + page_addition,
    1
)

# Datenmodelle ergänzen
model_anchor = '''class OrganizationEpisodeAssignment(BaseModel):
    episode_id: int
    notes: Optional[str] = None
'''

model_addition = '''

class Keyword(BaseModel):
    name: str


class KeywordEpisodeAssignment(BaseModel):
    episode_id: int
'''

if model_anchor not in content:
    raise RuntimeError("Das Organisations-Datenmodell wurde nicht gefunden.")

content = content.replace(
    model_anchor,
    model_anchor + model_addition,
    1
)

# API-Endpunkte ergänzen
api_addition = '''

# ---------------------------------------------------------
# SCHLAGWÖRTER
# ---------------------------------------------------------

@app.get("/api/keywords")
def get_keywords(search: str = ""):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name
            FROM keywords
            WHERE name LIKE ?
            ORDER BY name COLLATE NOCASE
            """,
            (f"%{search}%",)
        ).fetchall()

    return [dict(row) for row in rows]


@app.post("/api/keywords")
def create_keyword(keyword: Keyword):
    name = keyword.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Bitte einen Namen für das Schlagwort eingeben."
        )

    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO keywords (name) VALUES (?)",
                (name,)
            )
            keyword_id = cursor.lastrowid

        return {"id": keyword_id, "name": name}

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Dieses Schlagwort existiert bereits."
        )


@app.get("/api/keywords/{keyword_id}")
def get_keyword(keyword_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name FROM keywords WHERE id = ?",
            (keyword_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Schlagwort nicht gefunden."
        )

    return dict(row)


@app.put("/api/keywords/{keyword_id}")
def update_keyword(keyword_id: int, keyword: Keyword):
    name = keyword.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Bitte einen Namen für das Schlagwort eingeben."
        )

    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "UPDATE keywords SET name = ? WHERE id = ?",
                (name, keyword_id)
            )

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Schlagwort nicht gefunden."
                )

        return {"id": keyword_id, "name": name}

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Dieses Schlagwort existiert bereits."
        )


@app.delete("/api/keywords/{keyword_id}")
def delete_keyword(keyword_id: int):
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM keywords WHERE id = ?",
            (keyword_id,)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Schlagwort nicht gefunden."
            )

    return {"message": "Schlagwort gelöscht."}


@app.get("/api/keywords/{keyword_id}/episodes")
def get_keyword_episodes(keyword_id: int):
    with get_connection() as conn:
        keyword = conn.execute(
            "SELECT id FROM keywords WHERE id = ?",
            (keyword_id,)
        ).fetchone()

        if keyword is None:
            raise HTTPException(
                status_code=404,
                detail="Schlagwort nicht gefunden."
            )

        rows = conn.execute(
            """
            SELECT
                e.id AS episode_id,
                e.episode_number,
                e.title
            FROM episode_keywords ek
            JOIN episodes e ON e.id = ek.episode_id
            WHERE ek.keyword_id = ?
            ORDER BY e.episode_number
            """,
            (keyword_id,)
        ).fetchall()

    return [dict(row) for row in rows]


@app.post("/api/keywords/{keyword_id}/episodes")
def assign_keyword_episode(
    keyword_id: int,
    assignment: KeywordEpisodeAssignment
):
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO episode_keywords (episode_id, keyword_id)
                VALUES (?, ?)
                """,
                (assignment.episode_id, keyword_id)
            )

        return {"message": "Schlagwort zugeordnet."}

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Die Zuordnung existiert bereits oder die Folge bzw. das Schlagwort wurde nicht gefunden."
        )


@app.delete("/api/keywords/{keyword_id}/episodes/{episode_id}")
def remove_keyword_episode(keyword_id: int, episode_id: int):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM episode_keywords
            WHERE keyword_id = ? AND episode_id = ?
            """,
            (keyword_id, episode_id)
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

print("Schlagwortverwaltung erfolgreich in backend.py ergänzt.")
print(f"Sicherungskopie: {backup_path}")
print(f"Backend-Datei: {backend_path}")
