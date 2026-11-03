from pathlib import Path
import os
import sys
import shutil
import socket
import threading
import time
from urllib.request import urlopen
from urllib.error import URLError


# ============================================================
# GRUNDEINSTELLUNGEN
# ============================================================

APP_TITLE = "Die Drei ??? – Archivverwaltung"

HOST = "127.0.0.1"
PORT = 8765
URL = f"http://{HOST}:{PORT}"

# Programmordner ermitteln (normaler Python-Start oder .exe)
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys._MEIPASS) / "app"
else:
    APP_DIR = Path(__file__).resolve().parent.parent / "app"

# Ordner für Archivdaten und Fehlerprotokoll (wie im Backend)
DATA_DIR = Path(
    os.environ.get("LOCALAPPDATA")
    or (Path.home() / "AppData" / "Local")
) / "DreiFragezeichenArchiv"

# Als .exe ohne Konsole gibt es keine Standardausgabe –
# ohne Ersatz würden manche Bibliotheken beim Start abstürzen.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")


# ============================================================
# MELDUNGEN
# Funktioniert auch beim Start mit pythonw.exe (ohne Konsole).
# ============================================================

def show_message(text, error=True):
    try:
        import ctypes

        icon = 0x10 if error else 0x40  # Fehler- bzw. Info-Symbol
        ctypes.windll.user32.MessageBoxW(None, text, APP_TITLE, icon)
    except Exception:
        print(text)


def write_error_log(text):
    """Schreibt Startfehler in eine Textdatei im Datenordner."""
    try:
        import traceback

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        log_file = DATA_DIR / "fehlerprotokoll.txt"

        with open(log_file, "a", encoding="utf-8") as log:
            log.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
            log.write(text + "\n")
            log.write(traceback.format_exc() + "\n")

        return log_file
    except Exception:
        return None


def port_is_free():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test_socket:
        try:
            test_socket.bind((HOST, PORT))
            return True
        except OSError:
            return False


# ============================================================
# VORAUSSETZUNGEN PRÜFEN
# ============================================================

if not port_is_free():
    show_message(
        "Die Archivverwaltung kann nicht gestartet werden.\n\n"
        f"Der Anschluss (Port) {PORT} ist bereits belegt.\n\n"
        "Wahrscheinlich ist das Archiv bereits geöffnet.\n\n"
        "Bitte das vorhandene Archivfenster verwenden. Falls kein "
        "Fenster sichtbar ist, den Computer neu starten oder im "
        "Task-Manager die Archivverwaltung beenden."
    )
    sys.exit(1)

try:
    import uvicorn
    import webview

    # Backend für Python importierbar machen
    sys.path.insert(0, str(APP_DIR))

    import backend

except Exception as error:
    log_file = write_error_log(f"Laden fehlgeschlagen: {error}")
    show_message(
        "Die Archivverwaltung konnte nicht geladen werden.\n\n"
        f"Fehler: {error}\n\n"
        f"Details: {log_file or 'kein Protokoll möglich'}"
    )
    sys.exit(1)


# ============================================================
# LOKALEN WEBSERVER STARTEN
# ============================================================

server = uvicorn.Server(
    uvicorn.Config(
        backend.app,
        host=HOST,
        port=PORT,
        log_level="warning"
    )
)

server_thread = threading.Thread(
    target=server.run,
    daemon=True
)
server_thread.start()


# Warten, bis das Backend erreichbar ist
backend_ready = False

for attempt in range(30):
    if not server_thread.is_alive():
        break

    try:
        with urlopen(URL + "/api/status", timeout=1):
            backend_ready = True
            break
    except (URLError, OSError):
        time.sleep(0.5)

if not backend_ready:
    log_file = write_error_log("Backend nicht erreichbar.")
    show_message(
        "Das Archiv konnte nicht gestartet werden.\n\n"
        "Bitte das Programm erneut starten. Tritt der Fehler "
        "wiederholt auf, hilft das Fehlerprotokoll weiter:\n\n"
        f"{log_file or DATA_DIR}"
    )
    os._exit(1)


# ============================================================
# SCHNITTSTELLE FÜR DAS FENSTER (PDF-EXPORT)
# Attribute mit Unterstrich werden von pywebview nicht
# durchsucht – verhindert das Einfrieren beim Start.
# ============================================================

class ArchiveApi:
    def __init__(self):
        self._window = None

    def export_casefile(self, episode_id=None):
        return self.export_casefiles(episode_id)

    def export_casefiles(self, episode_id=None):
        import tempfile

        try:
            if self._window is None:
                return {"ok": False, "message": "Archivfenster nicht bereit."}

            if episode_id is not None:
                episode_id = int(episode_id)
                filename = f"Fallakte_Folge_{episode_id}.pdf"
            else:
                filename = "Die_Drei_Fragezeichen_Fallakten.pdf"

            documents = Path.home() / "Documents"
            if not documents.exists():
                documents = Path.home()

            selected = self._window.create_file_dialog(
                webview.FileDialog.SAVE,
                directory=str(documents),
                save_filename=filename,
                file_types=("PDF Dateien (*.pdf)",)
            )

            if not selected:
                return {
                    "ok": False,
                    "cancelled": True,
                    "message": "Export abgebrochen."
                }

            destination = Path(selected[0])

            if destination.suffix.lower() != ".pdf":
                destination = destination.with_suffix(".pdf")

            with tempfile.TemporaryDirectory(
                prefix="drei_fragezeichen_pdf_"
            ) as temp_dir:
                temporary_pdf = Path(temp_dir) / "export.pdf"

                backend.generate_casefiles_pdf(
                    temporary_pdf,
                    episode_id=episode_id
                )

                shutil.copy2(temporary_pdf, destination)

            return {
                "ok": True,
                "message": f"PDF wurde gespeichert:\n{destination}"
            }

        except Exception as error:
            return {"ok": False, "message": str(error)}


# ============================================================
# DESKTOP-FENSTER ÖFFNEN
# ============================================================

archive_api = ArchiveApi()

window = webview.create_window(
    APP_TITLE,
    URL,
    width=1200,
    height=800,
    min_size=(900, 650),
    background_color="#080808",
    js_api=archive_api
)

archive_api._window = window

try:
    webview.start()
finally:
    # ========================================================
    # SAUBER BEENDEN
    # Fenster wurde geschlossen: Server stoppen und Prozess
    # sicher beenden, damit Port 8765 wieder frei wird.
    # ========================================================
    server.should_exit = True
    server_thread.join(timeout=5)

    os._exit(0)
