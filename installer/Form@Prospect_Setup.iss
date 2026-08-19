#define MyAppName "Form@Prospect"
#include "version.iss"
#define MyAppPublisher "NM FORMATION"
#define MyAppExeName "Form@Prospect.exe"

#ifndef SourceDir
  #define SourceDir "..\release\Form@Prospect"
#endif

[Setup]
AppId={{B3D2B6E3-4C88-4D0A-82E2-FA4B51F1226A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

OutputDir=output
OutputBaseFilename=Form@Prospect_Setup_v{#MyAppVersion}
SetupIconFile=..\assets\icons\formaprospect.ico

Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

CloseApplications=yes
RestartApplications=yes
AppMutex=FormProspect_NMFORMATION_2026

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
