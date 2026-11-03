; Inno Setup script (https://jrsoftware.org/isinfo.php): iscc packaging\drevo-light.iss
[Setup]
AppName=Drevo Light
AppVersion=1.1
AppPublisher=candion
DefaultDirName={autopf}\Drevo Light
DefaultGroupName=Drevo Light
OutputDir=..\dist
OutputBaseFilename=drevo-light-setup
SetupIconFile=..\assets\icon.ico
LicenseFile=..\LICENSE
Compression=lzma
SolidCompression=yes

[Files]
Source: "..\dist\drevo-light\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Drevo Light"; Filename: "{app}\drevo-light.exe"
Name: "{autodesktop}\Drevo Light"; Filename: "{app}\drevo-light.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"
