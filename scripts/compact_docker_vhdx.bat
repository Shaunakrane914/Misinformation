@echo off
title Docker VHDX Compactor
echo ======================================================================
echo           Docker Desktop Virtual Disk (VHDX) Compactor
echo ======================================================================
echo.
echo Step 1: Stopping Docker processes and shutting down WSL distros...
taskkill /F /IM "Docker Desktop.exe" >nul 2>&1
taskkill /F /IM "com.docker.backend.exe" >nul 2>&1
taskkill /F /IM "com.docker.build.exe" >nul 2>&1
taskkill /F /IM "docker-sandbox.exe" >nul 2>&1
wsl --shutdown
timeout /t 3 /nobreak >nul

set VHDX_PATH=%LOCALAPPDATA%\Docker\wsl\disk\docker_data.vhdx
if not exist "%VHDX_PATH%" (
    echo Error: Could not locate docker_data.vhdx at:
    echo %VHDX_PATH%
    pause
    exit /b 1
)

echo.
echo Step 2: Preparing diskpart compaction commands...
set SCRIPT_PATH=%TEMP%\compact_docker_diskpart.txt
(
    echo select vdisk file="%VHDX_PATH%"
    echo attach vdisk readonly
    echo compact vdisk
    echo detach vdisk
    echo exit
) > "%SCRIPT_PATH%"

echo.
echo Step 3: Compacting VHDX... (this takes 30-60 seconds)
diskpart /s "%SCRIPT_PATH%"
del "%SCRIPT_PATH%" >nul 2>&1

echo.
echo ======================================================================
echo  COMPACT COMPLETED! Free space has been returned to your C: drive.
echo ======================================================================
echo.
pause

