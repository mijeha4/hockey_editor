@echo off
chcp 65001 >nul
echo ╔══════════════════════════════════════════════╗
echo ║     Hockey Editor Pro — Сборка проекта      ║
echo ╚══════════════════════════════════════════════╝
echo.

:: ── Шаг 1: Генерация ассетов ──
echo [1/3] Генерация иконок...
python scripts\generate_assets.py
if %ERRORLEVEL% NEQ 0 (
    echo ОШИБКА: Не удалось сгенерировать ассеты!
    pause
    exit /b 1
)
echo.

:: ── Шаг 2: Сборка EXE ──
echo [2/3] Сборка EXE через PyInstaller...
pyinstaller hockey_editor.spec --clean --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo ОШИБКА: Сборка PyInstaller не удалась!
    pause
    exit /b 1
)
echo.

:: ── Шаг 3: Проверка ──
echo [3/3] Проверка...
if exist "dist\HockeyEditor\HockeyEditor.exe" (
    echo.
    echo ╔══════════════════════════════════════════════╗
    echo ║            СБОРКА ЗАВЕРШЕНА!                 ║
    echo ║                                              ║
    echo ║  EXE: dist\HockeyEditor\HockeyEditor.exe    ║
    echo ║                                              ║
    echo ║  Для установщика запустите Inno Setup        ║
    echo ║  с файлом installer.iss                      ║
    echo ╚══════════════════════════════════════════════╝
) else (
    echo ОШИБКА: EXE файл не найден!
)

echo.
pause