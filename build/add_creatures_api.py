
from pathlib import Path
from datetime import datetime
import shutil

backend_path = (
    Path(r"C:\DreiFragezeichenArchiv")
    / "Verwaltung"
    / "app"
    / "backend.py"
)

if not backend_path.exists():
    raise FileNotFoundError(f"Backend nicht gefunden: {backend_path}")

content = backend_path.read_text(encoding="utf-8")

# Prüfen, ob die Erweiterung bereits vorhanden ist
if 'def creatures_page():' in content:
    raise RuntimeError("Die Kreaturenverwaltung ist bereits im Backend vorhanden.")

# Sicherungskopie erstellen
backup_path = backend_path.with_name(
    f"backend_backup_{datetime.now():%Y%m%d_%H%M%S}.py"
)
shutil.copy2(backend_path, backup_path)

# 1. Neue Seitenroute ergänzen
page_anchor = '''@app.get("/objects")
def objects_page():
    return FileResponse(APP_DIR / "templates" / "objects.html")
'''

page_addition = '''

@app.get("/creatures")
def creatures_page():
    return FileResponse(APP_DIR / "templates" / "creatures.html")
'''

if page_anchor not in content:
    raise RuntimeError("Einfügepunkt für die Seitenroute nicht gefunden.")

content = content.replace(
    page_anchor,
    page_anchor + page_addition,
    1
)

# 2. Datenmodelle ergänzen
model_anchor = '''class ObjectEpisodeAssignment(BaseModel):
    episode_id: int
    notes: Optional[str] = None
'''

model_addition = '''

class Creature(BaseModel):
    name: str
    description: Optional[str] = None


class CreatureEpisodeAssignment(BaseModel):
    episode_id: int
    notes: Optional[str] = None
'''

if model_anchor not in content:
    raise RuntimeError("Einfügepunkt für die Datenmodelle nicht gefunden.")

content = content.replace(
    model_anchor,
    model_anchor + model_addition,
    1
)

# 3. API-Endpunkte ergänzen
api_addition = '''

# ============================================================
# KREATUREN UND MONSTER – API
# ============================================================

@app.get("/api/creatures")
def list_creatures(search: str = ""):
    with get_connection() as conn:
        if search.strip():
            rows = conn.execute(
                """
                SELECT *
                FROM creatures
                WHERE name LIKE ? OR description LIKE ?
                ORDER BY name COLLATE NOCASE
                """,
                (
                    f"%{search.strip()}%",
                    f"%{search.strip()}%"
                )
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT *
                FROM creatures
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()

        return [dict(row) for row in rows]


@app.post("/api/creatures")
def create_creature(creature: Creature):
    name = creature.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Der Name der Kreatur darf nicht leer sein."
        )

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO creatures (name, description)
            VALUES (?, ?)
            """,
            (name, creature.description)
        )

        return {
            "id": cursor.lastrowid,
            "message": "Kreatur wurde angelegt."
        }


@app.get("/api/creatures/{creature_id}")
def get_creature(creature_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM creatures WHERE id = ?",
            (creature_id,)
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Kreatur nicht gefunden."
            )

        return dict(row)


@app.put("/api/creatures/{creature_id}")
def update_creature(creature_id: int, creature: Creature):
    name = creature.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Der Name der Kreatur darf nicht leer sein."
        )

    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE creatures
            SET name = ?, description = ?
            WHERE id = ?
            """,
            (name, creature.description, creature_id)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Kreatur nicht gefunden."
            )

        return {
            "message": "Kreatur wurde aktualisiert."
        }


@app.delete("/api/creatures/{creature_id}")
def delete_creature(creature_id: int):
    with get_connection() as conn:
        try:
            cursor = conn.execute(
                "DELETE FROM creatures WHERE id = ?",
                (creature_id,)
            )

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Kreatur nicht gefunden."
                )

            return {
                "message": "Kreatur wurde gelöscht."
            }

        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Die Kreatur ist noch Hörspielfolgen zugeordnet. "
                    "Bitte entferne zuerst diese Zuordnungen."
                )
            )


# ============================================================
# KREATUREN – HÖRSPIELFOLGEN-ZUORDNUNGEN
# ============================================================

@app.get("/api/creatures/{creature_id}/episodes")
def get_creature_episodes(creature_id: int):
    with get_connection() as conn:
        if not conn.execute(
            "SELECT id FROM creatures WHERE id = ?",
            (creature_id,)
        ).fetchone():
            raise HTTPException(
                status_code=404,
                detail="Kreatur nicht gefunden."
            )

        rows = conn.execute(
            """
            SELECT
                e.id AS episode_id,
                e.episode_number,
                e.title,
                ec.notes
            FROM episode_creatures ec
            JOIN episodes e ON e.id = ec.episode_id
            WHERE ec.creature_id = ?
            ORDER BY e.episode_number
            """,
            (creature_id,)
        ).fetchall()

        return [dict(row) for row in rows]


@app.post("/api/creatures/{creature_id}/episodes")
def assign_creature_to_episode(
    creature_id: int,
    assignment: CreatureEpisodeAssignment
):
    with get_connection() as conn:
        if not conn.execute(
            "SELECT id FROM creatures WHERE id = ?",
            (creature_id,)
        ).fetchone():
            raise HTTPException(
                status_code=404,
                detail="Kreatur nicht gefunden."
            )

        if not conn.execute(
            "SELECT id FROM episodes WHERE id = ?",
            (assignment.episode_id,)
        ).fetchone():
            raise HTTPException(
                status_code=404,
                detail="Hörspielfolge nicht gefunden."
            )

        try:
            conn.execute(
                """
                INSERT INTO episode_creatures
                (episode_id, creature_id, notes)
                VALUES (?, ?, ?)
                """,
                (
                    assignment.episode_id,
                    creature_id,
                    assignment.notes
                )
            )

            return {
                "message": "Kreatur wurde der Hörspielfolge zugeordnet."
            }

        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=409,
                detail="Diese Kreatur ist dieser Folge bereits zugeordnet."
            )


@app.delete("/api/creatures/{creature_id}/episodes/{episode_id}")
def remove_creature_episode(creature_id: int, episode_id: int):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM episode_creatures
            WHERE creature_id = ? AND episode_id = ?
            """,
            (creature_id, episode_id)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Zuordnung nicht gefunden."
            )

        return {
            "message": "Kreatur-Zuordnung wurde entfernt."
        }
'''

# Ergänzung am Ende der Backend-Datei
content = content.rstrip() + "\n\n" + api_addition.lstrip()

# Neue Backend-Datei speichern
backend_path.write_text(content + "\n", encoding="utf-8")

print("Kreaturenverwaltung erfolgreich in backend.py ergänzt.")
print(f"Sicherungskopie: {backup_path}")
print(f"Backend-Datei: {backend_path}")
