; ============================================================
; Inno-Setup-Skript – Die Drei ??? – Archivverwaltung
;
; Voraussetzung: vorher die .exe mit PyInstaller bauen
;   (dist\DreiFragezeichenArchiv\ muss existieren)
;
; Aufruf (im Ordner C:\DreiFragezeichenArchiv_Programm):
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\DreiFragezeichenArchiv.iss
;
; Ergebnis:
;   installer\Ausgabe\DreiFragezeichenArchiv_Setup_1.0.0.exe
; ============================================================

#define AppName        "Die Drei ??? – Archivverwaltung"
#define AppShortName   "Die Drei Fragezeichen Archiv"
#define AppVersion     "1.0.0"
#define AppPublisher   "Toni Matzdorf"
#define AppExeName     "DreiFragezeichenArchiv.exe"
#define SourceDir      "..\dist\DreiFragezeichenArchiv"

[Setup]
; Feste ID – NIE ändern, sonst erkennt Windows Updates nicht als
; dasselbe Programm.
AppId={{CECB8992-01AA-4CA9-9FC0-0E05D4827656}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}

; Installation ohne Administratorrechte möglich
; (dann unter %LOCALAPPDATA%\Programs), mit Adminrechten
; wahlweise für alle Benutzer unter "C:\Program Files".
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\DreiFragezeichenArchiv
DefaultGroupName={#AppShortName}
DisableProgramGroupPage=yes

; Nur 64-Bit-Windows (Windows 10 / 11)
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

SetupIconFile=..\app\static\images\blacky_archiv.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}

OutputDir=Ausgabe
OutputBaseFilename=DreiFragezeichenArchiv_Setup_{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

; Laufendes Archiv vor Update/Deinstallation schließen
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Verknüpfung auf dem Desktop anlegen"; GroupDescription: "Zusätzliche Verknüpfungen:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppShortName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{#AppShortName} deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppShortName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Archivverwaltung jetzt starten"; Flags: nowait postinstall skipifsilent

; Hinweis: Die Archivdaten liegen unter %LOCALAPPDATA%\DreiFragezeichenArchiv
; und werden bei Updates und bei der Deinstallation bewusst NICHT gelöscht.

[Code]
// ------------------------------------------------------------
// Prüfung: Microsoft Edge WebView2 Runtime
// (wird für das Programmfenster benötigt; unter Windows 11
// immer vorhanden, unter Windows 10 fast immer)
// ------------------------------------------------------------
const
  WebView2ClientKey = 'Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function WebView2Installed(): Boolean;
var
  Version: String;
begin
  Result :=
    (RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\' + WebView2ClientKey, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0')) or
    (RegQueryStringValue(HKLM, 'SOFTWARE\' + WebView2ClientKey, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0')) or
    (RegQueryStringValue(HKCU, 'Software\' + WebView2ClientKey, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0'));
end;

function InitializeSetup(): Boolean;
var
  ErrorCode: Integer;
begin
  Result := True;

  if not WebView2Installed() then
  begin
    if MsgBox(
      'Für die Archivverwaltung wird die "Microsoft Edge WebView2 Runtime" benötigt.' + #13#10 + #13#10 +
      'Sie scheint auf diesem Computer nicht installiert zu sein.' + #13#10 + #13#10 +
      'Soll die Download-Seite von Microsoft jetzt geöffnet werden?' + #13#10 +
      '(Die Installation der Archivverwaltung wird danach fortgesetzt.)',
      mbConfirmation, MB_YESNO) = IDYES then
    begin
      ShellExec('open', 'https://developer.microsoft.com/microsoft-edge/webview2/',
        '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
    end;
  end;
end;
