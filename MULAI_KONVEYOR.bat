@echo off
title Smart Conveyor Launcher - Kelompok 9
cd /d C:\laragon\www\proyek_konveyor

echo [1/3] Menjalankan Server Web Laravel...
start "Laravel Web Server" cmd /k "php artisan serve"

echo [2/3] Menjalankan MQTT Database Worker...
start "Laravel MQTT Worker" cmd /k "php artisan mqtt:worker"

timeout /t 2 /nobreak > nul
echo [3/3] Membuka Dashboard di Browser...
start http://127.0.0.1:8000
exit