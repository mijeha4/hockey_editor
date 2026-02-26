; ══════════════════════════════════════════════════════════
; Hockey Editor Pro — Inno Setup Installer Script
;
; Требования:
;   1. Собрать EXE: build.bat
;   2. Установить Inno Setup: https://jrsoftware.org/isinfo.php
;   3. Открыть этот файл в Inno Setup Compiler → Compile
; ══════════════════════════════════════════════════════════

#define MyAppName "Hockey Editor Pro"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Hockey Editor Team"
#define MyAppURL "https://github.com/hockey-editor"
#define MyAppExeName "HockeyEditor.exe"

[Setup]
; ID приложения (уникальный GUID — сгенерируйте свой!)
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Пути установки
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Выходной файл
OutputDir=installer_output
OutputBaseFilename=HockeyEditorSetup_{#MyAppVersion}

; Иконка установщика
SetupIconFile=assets\icons\app_icon.ico

; Сжатие
Compression=lzma2/ultra64
SolidCompression=yes

; Визуальный стиль
WizardStyle=modern
WizardSizePercent=110

; Права
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Минимальная версия Windows
MinVersion=10.0

; Лицензия (опционально — закомментируйте если нет файла)
; LicenseFile=LICENSE.txt

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные ярлыки:"; Flags: checkedonce
Name: "quicklaunchicon"; Description: "Создать ярлык в панели быстрого запуска"; GroupDescription: "Дополнительные ярлыки:"; Flags: unchecked

[Files]
; Все файлы из dist/HockeyEditor
Source: "dist\HockeyEditor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Ярлык в меню Пуск
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Удалить {#MyAppName}"; Filename: "{uninstallexe}"

; Ярлык на рабочем столе
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; Панель быстрого запуска
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Запустить приложение после установки
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Удалить пользовательские данные при деинсталляции (опционально)
Type: filesandirs; Name: "{localappdata}\HockeyEditor"