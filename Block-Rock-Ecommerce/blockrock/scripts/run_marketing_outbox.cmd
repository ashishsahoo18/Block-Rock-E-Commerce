@echo off
setlocal
cd /d "%~dp0.."
"C:\Users\ASHISH\AppData\Local\Programs\Python\Python313\python.exe" manage.py send_marketing_notifications
