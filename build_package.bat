@echo off
setlocal

cd /d "%~dp0"

echo Installing/upgrading Python build backend...
python -m pip install --upgrade build
if errorlevel 1 exit /b %errorlevel%

echo Cleaning previous package artifacts...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
for /d %%D in (*.egg-info src\*.egg-info) do rmdir /s /q "%%D"

echo Building wheel and source distribution...
python -m build
if errorlevel 1 exit /b %errorlevel%

echo.
echo Package artifacts created in dist:
dir /b dist
echo.
echo Install with:
for %%F in (dist\*.whl) do echo python -m pip install "%%F"

endlocal
