; Octavium InnoSetup Installer Script
; Version 1.1.2
; https://github.com/owenpkent/Octavium

#define MyAppName "Octavium"
#define MyAppVersion "1.1.2"
#define MyAppPublisher "Owen Kent"
#define MyAppURL "https://github.com/owenpkent/Octavium"
#define MyAppExeName "Octavium.exe"
#define MyAppDescription "Making music accessible"

; Stable GUID — do NOT change between versions (enables upgrade detection)
#define MyAppId "{{B8F3A2E1-7C4D-4E9A-8B5F-1A2D3E4F5678}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
AppCopyright=Copyright (c) 2025-2026 {#MyAppPublisher}
AppComments={#MyAppDescription}

; Install to Program Files (admin required)
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=admin

; Output settings
OutputDir=..\dist
OutputBaseFilename=Octavium-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Visual settings
SetupIconFile=..\assets\Octavium.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
WizardStyle=modern
WizardResizable=no

; Wizard branding images (generate with: python installer/generate_wizard_images.py)
WizardImageFile=..\installer\wizard_large.bmp
WizardSmallImageFile=..\installer\wizard_small.bmp

; Versioning and upgrade behaviour
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoCopyright=Copyright (c) 2025-2026 {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}.0
MinVersion=10.0
ArchitecturesInstallIn64BitMode=x64compatible

; Allow user to choose install directory
AllowNoIcons=yes
DisableProgramGroupPage=yes

; Uninstall settings
Uninstallable=yes
CreateUninstallRegKey=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
english.WelcomeLabel2=This will install [name/ver] on your computer.%n%n{#MyAppDescription}%n%nIt is recommended that you close all other applications before continuing.
english.FinishedHeadingLabel=Completing {#MyAppName} Setup
english.FinishedLabel=Setup has finished installing {#MyAppName} on your computer.%n%n{#MyAppDescription}

; MIDI library directory names — passed by build script via /D flags
; e.g. ISCC /DMidiChordsDir=free-midi-chords-20251006 /DMidiProgressionsDir=free-midi-progressions-20251006
; If not provided, the MIDI component is excluded from the installer.
#ifndef MidiChordsDir
  #define MidiChordsDir ""
#endif
#ifndef MidiProgressionsDir
  #define MidiProgressionsDir ""
#endif

[Types]
Name: "full"; Description: "Full installation (recommended)"
Name: "compact"; Description: "Compact installation (no MIDI chord library)"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Components]
Name: "main"; Description: "{#MyAppName} application"; Types: full compact custom; Flags: fixed
Name: "midilibrary"; Description: "MIDI Chord Library (~30 MB) — enables chord autofill from real voicings"; Types: full

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startmenuicon"; Description: "Create a &Start Menu shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Files]
; Main executable (must be signed before running InnoSetup)
Source: "..\dist\Octavium.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: main

; MIDI chord library (optional, bundled when built with MidiChordsDir defined)
#if MidiChordsDir != ""
Source: "..\resources\{#MidiChordsDir}\*"; DestDir: "{app}\resources\{#MidiChordsDir}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: midilibrary
#endif
#if MidiProgressionsDir != ""
Source: "..\resources\{#MidiProgressionsDir}\*"; DestDir: "{app}\resources\{#MidiProgressionsDir}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: midilibrary
#endif

; Application icon (for shortcuts)
Source: "..\assets\Octavium.ico"; DestDir: "{app}"; Flags: ignoreversion; Components: main

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\Octavium.ico"; Comment: "{#MyAppDescription}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\Octavium.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\Octavium.ico"; Comment: "{#MyAppDescription}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up any runtime-generated files in the install directory
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\*.log"

[Registry]
; Store version info for upgrade detection
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

[Code]
// -----------------------------------------------------------------------
// Pascal Script: Previous version detection, removal, version checks,
// and optional MIDI chord library download.
// -----------------------------------------------------------------------

#if Defined(MidiChordsDir) && MidiChordsDir != ""
const MidiBundled = True;
#else
const MidiBundled = False;
#endif

var
  MidiDownloadPage: TWizardPage;
  MidiDownloadCheck: TNewCheckBox;

function GetInstalledVersion(): String;
var
  InstalledVersion: String;
begin
  Result := '';
  if RegQueryStringValue(HKLM, 'Software\{#MyAppPublisher}\{#MyAppName}', 'Version', InstalledVersion) then
    Result := InstalledVersion;
end;

function GetUninstallString(): String;
var
  UninstallString: String;
begin
  Result := '';
  if RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppId}_is1', 'UninstallString', UninstallString) then
    Result := UninstallString;
end;

function CompareVersionStrings(V1, V2: String): Integer;
// Returns: -1 if V1 < V2, 0 if equal, 1 if V1 > V2
var
  P1, P2: Integer;
  N1, N2: Integer;
  S1, S2: String;
begin
  Result := 0;
  S1 := V1;
  S2 := V2;
  while (Length(S1) > 0) or (Length(S2) > 0) do
  begin
    // Extract next numeric segment from S1
    P1 := Pos('.', S1);
    if P1 > 0 then
    begin
      N1 := StrToIntDef(Copy(S1, 1, P1 - 1), 0);
      S1 := Copy(S1, P1 + 1, Length(S1));
    end
    else
    begin
      N1 := StrToIntDef(S1, 0);
      S1 := '';
    end;

    // Extract next numeric segment from S2
    P2 := Pos('.', S2);
    if P2 > 0 then
    begin
      N2 := StrToIntDef(Copy(S2, 1, P2 - 1), 0);
      S2 := Copy(S2, P2 + 1, Length(S2));
    end
    else
    begin
      N2 := StrToIntDef(S2, 0);
      S2 := '';
    end;

    if N1 < N2 then
    begin
      Result := -1;
      Exit;
    end
    else if N1 > N2 then
    begin
      Result := 1;
      Exit;
    end;
  end;
end;

function UninstallPreviousVersion(): Boolean;
var
  UninstallString: String;
  ResultCode: Integer;
begin
  Result := True;
  UninstallString := GetUninstallString();
  if UninstallString <> '' then
  begin
    // Remove surrounding quotes if present
    if (Length(UninstallString) > 1) and (UninstallString[1] = '"') then
      UninstallString := RemoveQuotes(UninstallString);

    if not Exec(UninstallString, '/SILENT /NORESTART', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      MsgBox('Failed to uninstall the previous version. Please uninstall it manually from Add/Remove Programs and run this setup again.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function InitializeSetup(): Boolean;
var
  InstalledVersion: String;
  CompareResult: Integer;
begin
  Result := True;
  InstalledVersion := GetInstalledVersion();

  if InstalledVersion <> '' then
  begin
    CompareResult := CompareVersionStrings('{#MyAppVersion}', InstalledVersion);

    if CompareResult = 0 then
    begin
      // Same version already installed
      if MsgBox('{#MyAppName} ' + InstalledVersion + ' is already installed.' + #13#10 + #13#10 +
                'Would you like to reinstall it?',
                mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
        Exit;
      end;
    end
    else if CompareResult < 0 then
    begin
      // Trying to install an older version
      if MsgBox('A newer version of {#MyAppName} (' + InstalledVersion + ') is already installed.' + #13#10 + #13#10 +
                'You are trying to install version {#MyAppVersion}.' + #13#10 + #13#10 +
                'Are you sure you want to downgrade?',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDNO then
      begin
        Result := False;
        Exit;
      end;
    end
    else
    begin
      // Upgrading to newer version
      if MsgBox('{#MyAppName} ' + InstalledVersion + ' is currently installed.' + #13#10 + #13#10 +
                'This will upgrade it to version {#MyAppVersion}.' + #13#10 + #13#10 +
                'Continue?',
                mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
        Exit;
      end;
    end;

    // Uninstall the previous version before proceeding
    if not UninstallPreviousVersion() then
    begin
      Result := False;
      Exit;
    end;
  end;
end;

// -----------------------------------------------------------------------
// MIDI Library download page — shown only when library is NOT bundled
// and the user selected the midilibrary component.
// -----------------------------------------------------------------------

procedure CreateMidiDownloadPage;
var
  LabelDesc: TNewStaticText;
begin
  MidiDownloadPage := CreateCustomPage(
    wpSelectComponents,
    'MIDI Chord Library',
    'Optional: download real chord voicings from the internet'
  );

  LabelDesc := TNewStaticText.Create(MidiDownloadPage);
  LabelDesc.Parent := MidiDownloadPage.Surface;
  LabelDesc.Left   := 0;
  LabelDesc.Top    := 0;
  LabelDesc.Width  := MidiDownloadPage.SurfaceWidth;
  LabelDesc.AutoSize := True;
  LabelDesc.WordWrap := True;
  LabelDesc.Caption :=
    'The MIDI Chord Library provides real chord voicings for the Chord Monitor autofill feature.'  + #13#10 + #13#10 +
    'The library is free and open-source (~30 MB download from github.com/ldrolez/free-midi-chords).' + #13#10 + #13#10 +
    'An internet connection is required. You can also download it later by re-running setup.';

  MidiDownloadCheck := TNewCheckBox.Create(MidiDownloadPage);
  MidiDownloadCheck.Parent  := MidiDownloadPage.Surface;
  MidiDownloadCheck.Left    := 0;
  MidiDownloadCheck.Top     := LabelDesc.Top + LabelDesc.Height + 16;
  MidiDownloadCheck.Width   := MidiDownloadPage.SurfaceWidth;
  MidiDownloadCheck.Caption := 'Download and install the MIDI Chord Library now (recommended)';
  MidiDownloadCheck.Checked := True;
end;

procedure InitializeWizard;
begin
  // Only show the download page when the library was NOT bundled at build time
  if not MidiBundled then
    CreateMidiDownloadPage;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  // Skip the download page if library is bundled OR midilibrary component not selected
  if (MidiDownloadPage <> nil) and (PageID = MidiDownloadPage.ID) then
    Result := MidiBundled or not IsComponentSelected('midilibrary');
end;

procedure DownloadMidiLibrary;
var
  Script: String;
  TmpScript: String;
  ResultCode: Integer;
begin
  WizardForm.StatusLabel.Caption := 'Downloading MIDI Chord Library...';
  WizardForm.ProgressGauge.Style := npbstMarquee;

  TmpScript := ExpandConstant('{tmp}\fetch_midi.ps1');

  // Inline PowerShell: download latest free-midi-chords release from GitHub
  Script :=
    '$dest = ''' + ExpandConstant('{app}\resources') + ''';' + #13#10 +
    'New-Item -ItemType Directory -Force -Path $dest | Out-Null;' + #13#10 +
    '$api = ''https://api.github.com/repos/ldrolez/free-midi-chords/releases/latest'';' + #13#10 +
    '$rel = Invoke-RestMethod -Uri $api -Headers @{''User-Agent''=''Octavium-Setup''} -TimeoutSec 30;' + #13#10 +
    'foreach ($asset in $rel.assets) {' + #13#10 +
    '  if ($asset.name -match ''\\.zip$'') {' + #13#10 +
    '    $zip = Join-Path $env:TEMP $asset.name;' + #13#10 +
    '    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -TimeoutSec 300;' + #13#10 +
    '    Expand-Archive -Path $zip -DestinationPath $dest -Force;' + #13#10 +
    '    Remove-Item $zip -Force -ErrorAction SilentlyContinue;' + #13#10 +
    '  }' + #13#10 +
    '}';

  SaveStringToFile(TmpScript, Script, False);

  if not Exec('powershell.exe',
      '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + TmpScript + '"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
  begin
    MsgBox(
      'Could not download the MIDI Chord Library.' + #13#10 + #13#10 +
      'You can download it manually later from:' + #13#10 +
      'https://github.com/ldrolez/free-midi-chords/releases' + #13#10 + #13#10 +
      'Extract the zip files into: ' + ExpandConstant('{app}\resources'),
      mbInformation, MB_OK);
  end;

  DeleteFile(TmpScript);
  WizardForm.ProgressGauge.Style := npbstNormal;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Download library if: not bundled, component selected, and user checked the download box
    if (not MidiBundled) and
       IsComponentSelected('midilibrary') and
       (MidiDownloadCheck <> nil) and
       MidiDownloadCheck.Checked then
      DownloadMidiLibrary;
  end;
end;
