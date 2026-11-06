@echo off
powershell -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0firmware\esp32-arm\present.ps1"
