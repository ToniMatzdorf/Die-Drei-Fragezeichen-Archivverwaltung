
from pathlib import Path
from datetime import datetime
import shutil

backend_path = Path(
    r"C:\DreiFragezeichenArchiv\Verwaltung\app\backend.py"
)

if not backend_path.exists():
    raise FileNotFoundError(f"Backend nicht gefunden: {backend_path}")

content = backend_path.read_text(encoding="utf-8")

if "def organizations_page():" in content:
    raise SystemExit(
        "Die Organisationsverwaltung ist bereits im Backend vorhanden."
    )

# Sicherungskopie erstellen
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = backend_path.with_name(
    f"backend_backup_{timestamp}.py"
)

shutil.copy2(backend_path, backup_path)

# ------------------------------------------------------------
# 1. Seitenauslieferung ergänzen
# ------------------------------------------------------------

page_anchor = '''@app.get("/creatures")
def creatures_page():
    return FileResponse(APP_DIR / "templates" / "creatures.html")
'''

page_addition = '''

@app.get("/organizations")
def organizations_page():
    return FileResponse(APP_DIR / "templates" / "organizations.html")
'''

if page_anchor not in content:
    raise SystemExit("Seitenroute für Kreaturen nicht gefunden.")

content = content.replace(
    page_anchor,
    page_anchor + page_addition,
    1
)

# ------------------------------------------------------------
# 2. Datenmodelle ergänzen
# ------------------------------------------------------------

model_anchor = '''class CreatureEpisodeAssignment(BaseModel):
    episode_id: int
    notes: Optional[str] = None
'''

model_addition = '''

class Organization(BaseModel):
    name: str
    description: Optional[str] = None


class OrganizationEpisodeAssignment(BaseModel):
    episode_id: int
    notes: Optional[str] = None
'''

if model_anchor not in content:
    raise SystemExit("Datenmodell für Kreaturen nicht gefunden.")

content = content.replace(
    model_anchor,
    model_anchor + model_addition,
    1
)

# ------------------------------------------------------------
# 3. Organisations-API ergänzen
# ------------------------------------------------------------

api_addition = '''

# ============================================================
# ORGANISATIONSVERWALTUNG – API
# ============================================================

@app.get("/api/organizations")
def list_organizations(search: str = ""):
    with get_connection() as conn:
        if search.strip():
            rows = conn.execute(
                """
                SELECT *
                FROM organizations
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
                FROM organizations
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()

        return [dict(row) for row in rows]


@app.post("/api/organizations")
def create_organization(organization: Organization):
    name = organization.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Der Organisationsname darf nicht leer sein."
        )

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO organizations (name, description)
            VALUES (?, ?)
            """,
            (name, organization.description)
        )

        return {
            "id": cursor.lastrowid,
            "message": "Organisation wurde angelegt."
        }


@app.get("/api/organizations/{organization_id}")
def get_organization(organization_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM organizations WHERE id = ?",
            (organization_id,)
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Organisation nicht gefunden."
            )

        return dict(row)


@app.put("/api/organizations/{organization_id}")
def update_organization(
    organization_id: int,
    organization: Organization
):
    name = organization.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Der Organisationsname darf nicht leer sein."
        )

    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE organizations
            SET name = ?, description = ?
            WHERE id = ?
            """,
            (name, organization.description, organization_id)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Organisation nicht gefunden."
            )

        return {
            "message": "Organisation wurde aktualisiert."
        }


@app.delete("/api/organizations/{organization_id}")
def delete_organization(organization_id: int):
    with get_connection() as conn:
        try:
            cursor = conn.execute(
                "DELETE FROM organizations WHERE id = ?",
                (organization_id,)
            )

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Organisation nicht gefunden."
                )

            return {
                "message": "Organisation wurde gelöscht."
            }

        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Die Organisation ist noch Hörspielfolgen zugeordnet. "
                    "Bitte entferne zuerst diese Zuordnungen."
                )
            )


# ============================================================
# ORGANISATIONEN – HÖRSPIELFOLGEN-ZUORDNUNGEN
# ============================================================

@app.get("/api/organizations/{organization_id}/episodes")
def get_organization_episodes(organization_id: int):
    with get_connection() as conn:
        if not conn.execute(
            "SELECT id FROM organizations WHERE id = ?",
            (organization_id,)
        ).fetchone():
            raise HTTPException(
                status_code=404,
                detail="Organisation nicht gefunden."
            )

        rows = conn.execute(
            """
            SELECT
                e.id AS episode_id,
                e.episode_number,
                e.title,
                eo.notes
            FROM episode_organizations eo
            JOIN episodes e ON e.id = eo.episode_id
            WHERE eo.organization_id = ?
            ORDER BY e.episode_number
            """,
            (organization_id,)
        ).fetchall()

        return [dict(row) for row in rows]


@app.post("/api/organizations/{organization_id}/episodes")
def assign_organization_to_episode(
    organization_id: int,
    assignment: OrganizationEpisodeAssignment
):
    with get_connection() as conn:
        if not conn.execute(
            "SELECT id FROM organizations WHERE id = ?",
            (organization_id,)
        ).fetchone():
            raise HTTPException(
                status_code=404,
                detail="Organisation nicht gefunden."
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
                INSERT INTO episode_organizations
                (episode_id, organization_id, notes)
                VALUES (?, ?, ?)
                """,
                (
                    assignment.episode_id,
                    organization_id,
                    assignment.notes
                )
            )

            return {
                "message": (
                    "Organisation wurde der Hörspielfolge zugeordnet."
                )
            }

        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Diese Organisation ist dieser Folge bereits zugeordnet."
                )
            )


@app.delete(
    "/api/organizations/{organization_id}/episodes/{episode_id}"
)
def remove_organization_episode(
    organization_id: int,
    episode_id: int
):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM episode_organizations
            WHERE organization_id = ? AND episode_id = ?
            """,
            (organization_id, episode_id)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Zuordnung nicht gefunden."
            )

        return {
            "message": "Organisations-Zuordnung wurde entfernt."
        }

'''

# ------------------------------------------------------------
# 4. API-Code ans Backend anhängen
# ------------------------------------------------------------

content = content.rstrip() + "\n\n" + api_addition

# ------------------------------------------------------------
# 5. Backend speichern
# ------------------------------------------------------------

backend_path.write_text(content, encoding="utf-8")

print("Organisationsverwaltung erfolgreich in backend.py ergänzt.")
print(f"Sicherungskopie: {backup_path}")
print(f"Backend-Datei: {backend_path}")
