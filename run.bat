@echo off
title SmartStudy - Running Web Server
cd /d "%~dp0"
echo ==============================================
echo    Starting SmartStudy Web Application...
echo ==============================================
echo.
python -m streamlit run app.py
pause
