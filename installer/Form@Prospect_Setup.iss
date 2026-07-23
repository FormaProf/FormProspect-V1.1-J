#define MyAppName "Form@Prospect"
#define MyAppVersion "1.1.0-e"
#define MyAppPublisher "NM FORMATION"
#define MyAppExeName "Form@Prospect.exe"

[Setup]
AppId={{B3D2B6E3-4C88-4D0A-82E2-FA4B51F1226A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=Form@Prospect_Setup_v{#MyAppVersion}
SetupIconFile=..\assets\icons\formaprospect.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Creer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"; Flags: unchecked

[Files]
Source: "..\release\Form@Prospect\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\Manuel_utilisateur_FormProspect_1.0.0.pdf"; DestDir: "{app}\Documentation"; Flags: ignoreversion
Source: "..\docs\NOTES_DE_VERSION_V1.1-E.md"; DestDir: "{app}\Documentation"; Flags: ignoreversion
Source: "..\docs\NOTICE.md"; DestDir: "{app}\Documentation"; Flags: ignoreversion
Source: "..\Documentation\CHANGELOG.md"; DestDir: "{app}\Documentation"; Flags: ignoreversion

[Icons]
; Ne pas forcer IconFilename : Windows utilise l'icone embarquee dans l'EXE.
; Cela evite l'icone blanche provoquee par l'ancien chemin assets inexistant.
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
; Name: "{group}\Manuel utilisateur"; Filename: "{app}\Documentation\Manuel_utilisateur_FormProspect_1.0.0.pdf"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
