#ifndef AppVersion
  #define AppVersion "1.0"
#endif
#ifndef AppFileVersion
  #define AppFileVersion "1.0.0.0"
#endif
#ifndef AppVersionMS
  #define AppVersionMS 65536
#endif
#ifndef AppVersionLS
  #define AppVersionLS 0
#endif
#ifndef DistDir
  #define DistDir "..\dist\YouTubeSync"
#endif
#ifndef OutputDir
  #define OutputDir "..\releases"
#endif

[Setup]
AppId={{82B9F3E3-6550-49FC-B744-A718EA4FC9C0}
AppName=YouTubeSync
AppVersion={#AppVersion}
AppPublisher=Pokidj
AppPublisherURL=https://github.com/Pokidj/YouTubeSync
AppSupportURL=https://github.com/Pokidj/YouTubeSync/issues
AppUpdatesURL=https://github.com/Pokidj/YouTubeSync/releases/latest
DefaultDirName={localappdata}\Programs\YouTubeSync
DefaultGroupName=YouTubeSync
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
UninstallDisplayName=YouTubeSync
UninstallDisplayIcon={app}\YouTubeSync.exe
SetupIconFile=..\assets\youtube-sync.ico
VersionInfoVersion={#AppFileVersion}
VersionInfoProductName=YouTubeSync
VersionInfoProductVersion={#AppVersion}
VersionInfoDescription=YouTubeSync Installer
OutputDir={#OutputDir}
OutputBaseFilename=YouTubeSync-{#AppVersion}-windows-x64-setup
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern dynamic
DisableProgramGroupPage=yes
CloseApplications=no
RestartApplications=no
SetupMutex=YouTubeSync.Setup
UsePreviousAppDir=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
spanish.CloseApp=Cierra YouTubeSync desde la bandeja antes de continuar.
english.CloseApp=Exit YouTubeSync from the system tray before continuing.
spanish.WaitFailed=YouTubeSync no se ha cerrado. No se ha instalado la actualización.
english.WaitFailed=YouTubeSync did not exit. The update has not been installed.
spanish.NewerInstalled=Ya hay una versión posterior instalada. No se permite volver a una anterior.
english.NewerInstalled=A newer version is installed. Downgrading is not allowed.
spanish.DesktopIcon=Crear un acceso directo en el escritorio
english.DesktopIcon=Create a desktop shortcut
spanish.OpenApp=Abrir YouTubeSync
english.OpenApp=Open YouTubeSync

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; Flags: unchecked

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\YouTubeSync"; Filename: "{app}\YouTubeSync.exe"
Name: "{autodesktop}\YouTubeSync"; Filename: "{app}\YouTubeSync.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\YouTubeSync.exe"; Description: "{cm:OpenApp}"; Flags: nowait postinstall skipifsilent; Check: not RelaunchRequested
Filename: "{app}\YouTubeSync.exe"; Flags: nowait; Check: RelaunchRequested

[Code]
function OpenProcess(Access: LongWord; Inherit: Boolean; ProcessId: LongWord): THandle;
  external 'OpenProcess@kernel32.dll stdcall';
function WaitForSingleObject(Handle: THandle; Milliseconds: LongWord): LongWord;
  external 'WaitForSingleObject@kernel32.dll stdcall';
function CloseHandle(Handle: THandle): Boolean;
  external 'CloseHandle@kernel32.dll stdcall';

function RelaunchRequested: Boolean;
begin
  Result := ExpandConstant('{param:RELAUNCH|0}') = '1';
end;

function InitializeSetup: Boolean;
var
  Pid: Integer;
  Process: THandle;
begin
  Result := True;
  Pid := StrToIntDef(ExpandConstant('{param:UPDATEPID|0}'), 0);
  if Pid > 0 then begin
    Process := OpenProcess($00100000, False, Pid);
    if Process <> 0 then begin
      Result := WaitForSingleObject(Process, 90000) = 0;
      CloseHandle(Process);
      if not Result then
        SuppressibleMsgBox(CustomMessage('WaitFailed'), mbError, MB_OK, IDOK);
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  MS, LS: Cardinal;
begin
  Result := '';
  if GetVersionNumbers(ExpandConstant('{app}\YouTubeSync.exe'), MS, LS) then
    if (MS > {#AppVersionMS}) or ((MS = {#AppVersionMS}) and (LS > {#AppVersionLS})) then
      Result := CustomMessage('NewerInstalled');
end;

procedure DeinitializeUninstall;
var
  StartupFile: String;
  Content: AnsiString;
begin
  StartupFile := ExpandConstant('{userstartup}\YouTubeSync.cmd');
  if LoadStringFromFile(StartupFile, Content) then
    if Pos(Lowercase(ExpandConstant('{app}\YouTubeSync.exe')), Lowercase(Utf8Decode(Content))) > 0 then
      DeleteFile(StartupFile);
end;

// No AppData deletion: authorization, upload records and playback profiles stay.
