@echo off
title US Immigration Group - Billing System
echo ============================================
echo   US Immigration Group - Legal Billing
echo   Starting Streamlit Server...
echo ============================================
echo.
cd /d "%~dp0"
python run_server.py
pause
