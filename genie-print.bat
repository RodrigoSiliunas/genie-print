@echo off
REM Genie Print launcher (Windows).
REM Da pra dar duplo-clique. Configura o venv na primeira execucao e
REM em seguida abre o wizard. Qualquer argumento passado e repassado
REM pro image_watcher.py (ex: genie.bat --sync --dry-run).

setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "VENV_PY=.venv\Scripts\python.exe"

if exist "%VENV_PY%" goto :run

echo.
echo === Configurando ambiente pela primeira vez ===
echo.

where uv >nul 2>&1
if %errorlevel%==0 (
    uv venv --python 3.13 .venv || goto :setup_fail
    uv pip install -r requirements.txt || goto :setup_fail
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo Erro: nem 'uv' nem 'python' encontrados no PATH.
        echo Instale o uv ^(recomendado^) ou Python 3.11+ e tente de novo.
        pause
        exit /b 1
    )
    python -m venv .venv || goto :setup_fail
    "%VENV_PY%" -m pip install --upgrade pip >nul || goto :setup_fail
    "%VENV_PY%" -m pip install -r requirements.txt || goto :setup_fail
)

:run
"%VENV_PY%" image_watcher.py %*
goto :end

:setup_fail
echo.
echo === Falha na configuracao do ambiente ===
pause
exit /b 1

:end
endlocal
