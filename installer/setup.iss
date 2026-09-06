; installer/setup.iss — Legal Inno Setup Script for ANSH - Your Own AI Friend
; Created & Engineered by Anshu Dubey | https://getyoursoft.page.gd

#define MyAppName "ANSH - Your Own AI Friend"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Anshu Dubey"
#define MyAppURL "https://getyoursoft.page.gd"
#define MyAppExeName "ansh.exe"

[Setup]
AppId={{D1A8F932-5B4A-4831-92F6-B29A78229F81}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\ANSH AI
DefaultGroupName=ANSH AI
DisableProgramGroupPage=yes
LicenseFile=EULA.txt
OutputDir=release
OutputBaseFilename=ANSH_Setup_v1.0
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Automatically start ANSH when Windows boots"; GroupDescription: "Startup Options:"

[Files]
Source: "..\release_app\ansh\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "EULA.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ANSH_AI"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
