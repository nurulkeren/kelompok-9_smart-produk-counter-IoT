# SMART CONVEYOR CONTROL & TRACEABILITY SYSTEM

### PID-Based Conveyor Speed Control, Computer Vision Barcode/QR Scanning, and Real-Time IoT Production Monitoring

<p align="center">
  <strong>Kelompok 9 | Kelas A</strong><br>
  Program Studi Teknik Komputer<br>
  Fakultas Teknik<br>
  Universitas Jenderal Soedirman<br>
  2026
</p>

---

## 📌 1. Project Overview

**Smart Conveyor Control & Traceability System** merupakan sistem otomasi jalur konveyor industri skala purwarupa yang mengintegrasikan teknologi **Closed-Loop PID Control**, **Computer Vision**, dan **Internet of Things (IoT)** untuk mendukung proses pemindahan, identifikasi, serta pencatatan riwayat produksi secara *real-time*.

Sistem dirancang menggunakan arsitektur terdistribusi yang terdiri atas ESP8266 NodeMCU sebagai *Edge Controller*, Raspberry Pi sebagai *Vision Processing & MQTT Broker Node*, serta aplikasi web berbasis Laravel dan database MySQL sebagai pusat monitoring dan pengelolaan data produksi.

Integrasi ketiga subsistem memungkinkan konveyor melakukan pengaturan kecepatan secara otomatis, menghentikan pergerakan barang ketika proses pemindaian berlangsung, serta menyimpan informasi produk ke dalam sistem *Audit Traceability*.

### Key Features

| Fitur | Deskripsi |
|---|---|
| ⚙️ PID Speed Control | Pengaturan kecepatan motor DC menggunakan kendali PID lup tertutup. |
| 📡 Real-Time RPM Monitoring | Pemantauan kecepatan aktual motor berdasarkan sensor encoder FC-03. |
| 🔍 Computer Vision Scanning | Deteksi multi-objek dan pembacaan barcode/QR menggunakan OpenCV dan pyzbar. |
| ⏸️ Stop-and-Scan Automation | Penghentian konveyor otomatis selama proses pemindaian, maksimal 5 detik. |
| 🌐 Hybrid Control | Pengoperasian konveyor melalui dashboard web maupun saklar fisik. |
| 📊 Production Monitoring | Monitoring telemetri PID dan laju produksi secara real-time. |
| 🏷️ QR Code Generator | Pembuatan label QR Code berdasarkan batch dan identitas produk. |
| 🗂️ Audit Traceability | Pencatatan riwayat identifikasi dan proses produksi ke database MySQL. |
| 🎥 Live Camera Streaming | Streaming video kamera secara langsung melalui MJPEG. |
| 🛡️ Watchdog Fail-Safe | Pemulihan otomatis ketika komunikasi terputus saat proses scanning. |

---

## 👥 2. Team Members

| No. | Nama Lengkap | NIM | Peran |
|:---:|---|:---:|---|
| 1 | Nurul Maftuhah | H1H024002 | Anggota |
| 2 | Difa' Tamaya Maulidina Adz dzikro | H1H024019 | Anggota |
| 3 | Kaira Meilasya Nayada | H1H024020 | Ketua Kelompok |
| 4 | Nursyafika | H1H024023 | Anggota |

### Academic Information

| Keterangan | Informasi |
|---|---|
| Mata Kuliah | Internet of Things (IoT) |
| Program Studi | Teknik Komputer |
| Fakultas | Teknik |
| Universitas | Universitas Jenderal Soedirman |
| Kelompok | 9 |
| Kelas | A |
| Tahun | 2026 |

---

## 🏗️ 3. System Architecture

Sistem menggunakan arsitektur terdistribusi berbasis protokol **MQTT (Message Queuing Telemetry Transport)** untuk komunikasi antarperangkat dan **HTTP MJPEG Stream** untuk transmisi video kamera.

Arsitektur dibagi menjadi tiga lapisan utama:

1. **Edge Control Layer (ESP8266):** Pengendalian motor, pembacaan sensor, algoritma PID, dan antarmuka lokal.
2. **Vision & Broker Layer (Raspberry Pi):** Pemrosesan citra, pelacakan objek, pemindaian barcode/QR, dan komunikasi MQTT.
3. **Application & Database Layer (Laravel & MySQL):** Monitoring, kendali jarak jauh, pengelolaan produk, serta penyimpanan riwayat produksi.

### Architecture Diagram

```text
+-----------------------------------------------------------------------+
|                       EDGE CONTROL LAYER                              |
|                         ESP8266 NODEMCU                               |
|                                                                       |
|  [Encoder FC-03 D6] ---> [Digital PID] ---> [PWM Motor D5]             |
|  [20 Slots, 250ms]       [Kp=1.2]         [1000 Hz]                   |
|                          [Ki=0.8]         [8-bit]                     |
|                          [Kd=0.05]        [85-255]                    |
|                                                                       |
|  [Physical Switch D7] -----------------> [Relay D0]                   |
|                                               |                       |
|  [LCD 16x2 I2C] <----------------------- [ESP8266]                    |
|  [LED Red/Yellow/Green]                   [MQTT Client]               |
+-----------------------------------------------|-----------------------+
                                                |
                                           WiFi / MQTT
                                                |
                                                v
+-----------------------------------------------------------------------+
|                    VISION & BROKER LAYER                               |
|                         RASPBERRY PI                                  |
|                                                                       |
|  [USB Webcam] ---> [OpenCV Multi-Object Tracker]                      |
|                              |                                        |
|                              v                                        |
|                      [pyzbar Scanner]                                 |
|                              |                                        |
|              +---------------+----------------+                       |
|              |                                |                       |
|              v                                v                       |
|       [MJPEG Stream]                   [Mosquitto Broker]              |
|          Port 5050                         Port 1883                  |
+--------------|---------------------------------|----------------------+
               |                                 |
          HTTP Stream                        MQTT / JSON
               |                                 |
               v                                 v
+-----------------------------------------------------------------------+
|                 APPLICATION & DATABASE LAYER                          |
|                       LARAVEL + MYSQL                                 |
|                                                                       |
|  [MQTT Worker] ------> [MySQL Database]                               |
|                              |                                        |
|                              v                                        |
|                     [Web Dashboard]                                   |
|                                                                       |
|  - Hybrid ON/OFF Control                                               |
|  - PID Setpoint Tuning                                                 |
|  - Real-Time RPM Monitoring                                            |
|  - Live Vision Camera                                                  |
|  - QR Code Generator                                                   |
|  - Production Analytics                                                |
|  - Audit Traceability                                                  |
+-----------------------------------------------------------------------+
```

---

## ⚙️ 4. Hardware Components

| No. | Komponen | Spesifikasi / Tipe | Fungsi |
|:---:|---|---|---|
| 1 | Microcontroller | ESP8266 NodeMCU ESP-12E | Pengendali utama motor dan sensor berbasis PID. |
| 2 | Mini Computer | Raspberry Pi | Pemrosesan Computer Vision dan MQTT Broker. |
| 3 | Camera | USB Webcam | Akuisisi citra dan streaming video. |
| 4 | Actuator | DC Motor | Penggerak utama sabuk konveyor. |
| 5 | Motor Driver | PWM Motor Driver | Pengaturan kecepatan motor DC. |
| 6 | Relay Module | Relay | Pemutus dan penghubung daya utama motor. |
| 7 | Speed Sensor | Optocoupler FC-03 | Pengukuran kecepatan aktual motor. |
| 8 | Encoder Disc | 20 Slots | Menghasilkan pulsa untuk pengukuran RPM. |
| 9 | Display | LCD 16x2 I2C (0x27) | Menampilkan status, jumlah produk, dan RPM. |
| 10 | Input Switch | Physical Switch | Kendali lokal ON/OFF. |
| 11 | Indicators | 3x LED | Indikator Standby, Scanning, dan Running. |

### ESP8266 Pin Configuration

| NodeMCU Pin | Program Constant | Connected Component | Function |
|---|---|---|---|
| `D0` | `PIN_RELAY` | Relay Module | Active-Low Motor Power Control |
| `D1` | `PIN_LCD_SCL` | LCD I2C | I2C Clock |
| `D2` | `PIN_LCD_SDA` | LCD I2C | I2C Data |
| `D3` | `PIN_LED_MERAH` | Red LED | Standby / OFF |
| `D4` | `PIN_LED_HIJAU` | Green LED | Running |
| `D5` | `PIN_ENA` | Motor Driver | PWM Output |
| `D6` | `PIN_SENSOR` | FC-03 Encoder | Hardware Interrupt (FALLING) |
| `D7` | `PIN_SAKLAR` | Physical Switch | INPUT_PULLUP |
| `D8` | `PIN_LED_KUNING` | Yellow LED | Scanning |

> **Hardware Note:** ESP8266 menggunakan level logika 3,3 V. Perhatikan kompatibilitas tegangan sensor, driver, dan LCD. Pin D3, D4, serta D8 merupakan pin yang memiliki fungsi boot-strapping sehingga rangkaian eksternal tidak boleh mengganggu proses boot mikrokontroler.

---

## 💻 5. Software Stack

| Layer | Technology | Description |
|---|---|---|
| Firmware | Arduino IDE (C/C++) | Pemrograman ESP8266 |
| WiFi Communication | ESP8266WiFi | Koneksi jaringan nirkabel |
| MQTT Client | PubSubClient | Komunikasi MQTT ESP8266 |
| Local Display | LiquidCrystal_I2C | Pengendalian LCD |
| Computer Vision | Python 3, OpenCV | Pemrosesan citra dan deteksi objek |
| Barcode Scanner | pyzbar | Pembacaan barcode dan QR Code |
| Image Processing | NumPy | Pengolahan data citra |
| MQTT Service | Paho MQTT | Komunikasi MQTT Raspberry Pi |
| Message Broker | Eclipse Mosquitto | Distribusi pesan MQTT |
| Backend | PHP Laravel | Aplikasi web dan pengelolaan data |
| Database | MySQL | Penyimpanan data produksi |
| MQTT Background Service | Laravel MQTT Worker | Pemrosesan pesan MQTT |
| Video Streaming | HTTP MJPEG | Live camera stream |
| Process Management | systemd | Menjalankan service Raspberry Pi saat boot |

---

## 🎛️ 6. PID Control System

Sistem menggunakan metode **Closed-Loop PID Control** untuk menjaga kecepatan sabuk konveyor tetap stabil berdasarkan nilai setpoint yang diberikan operator.

Sensor optocoupler FC-03 membaca pulsa encoder dan mengirimkan data ke ESP8266 melalui mekanisme *hardware interrupt*.

Kecepatan aktual motor dihitung setiap 250 ms, kemudian diproses menggunakan filter Exponential Moving Average (EMA) sebelum digunakan sebagai umpan balik pengendali PID.

### PID Parameters

| Parameter | Value |
|---|---:|
| `Kp` | 1.2 |
| `Ki` | 0.8 |
| `Kd` | 0.05 |
| Sampling Period | 250 ms |
| `PWM_MIN` | 85 |
| `PWM_MAX` | 255 |
| PWM Frequency | 1000 Hz |
| PWM Resolution | 8-bit |
| Kick-Start PWM | 150 |
| Default Setpoint | 100 RPM |
| Setpoint Range | 20–500 RPM |
| Integral Limit | -150 to 150 |

### RPM Calculation

\[
RPM=\frac{N_p}{N_s\times dt}\times60
\]

Dengan jumlah celah encoder sebanyak 20 dan periode sampling 0,25 detik:

\[
RPM=N_p\times12
\]

### EMA Filter

\[
RPM_f(k)=0.6RPM_a(k)+0.4RPM_f(k-1)
\]

### Digital PID Equation

\[
e(k)=SP(k)-RPM_f(k)
\]

\[
I(k)=\operatorname{clamp}
(I(k-1)+K_i e(k)dt,-150,150)
\]

\[
D(k)=K_d\frac{e(k)-e(k-1)}{dt}
\]

\[
u(k)=K_pe(k)+I(k)+D(k)
\]

Keluaran PID digunakan untuk menyesuaikan nilai PWM motor pada rentang 85–255 ketika sistem berjalan. Ketika sistem OFF atau SCANNING, PWM diatur menjadi 0.

Sistem juga menerapkan *kick-start* PWM sebesar 150 untuk membantu mengatasi inersia awal ketika motor mulai beroperasi.

---

## 🔄 7. Stop-and-Scan Automation

Sistem mengimplementasikan mekanisme **Stop-and-Scan** untuk mengatur proses identifikasi produk secara otomatis.

Ketika kamera mendeteksi objek memasuki zona pemindaian, Raspberry Pi mengirimkan event `SCANNING` melalui MQTT. ESP8266 kemudian menghentikan motor dengan mengatur PWM menjadi 0 dan memutus relay.

### State Machine

| State | Trigger / Event | System Action |
|---|---|---|
| `MODE_OFF` | START / ON | Mengaktifkan konveyor |
| `MODE_RUNNING` | SCANNING | Menghentikan motor |
| `MODE_SCANNING` | SCAN_OK | Melanjutkan konveyor |
| `MODE_SCANNING` | SCAN_FAIL | Memberikan peringatan dan auto-resume |
| `MODE_SCANNING` | Watchdog Timeout | Memulihkan operasi konveyor |
| `MODE_RUNNING` | STOP / OFF | Menghentikan konveyor |

### Scanning Parameters

| Parameter | Value |
|---|---:|
| Maximum Scanning Duration | 5 Seconds |
| Watchdog Timeout | 6.5 Seconds |
| Scanning Indicator | Yellow LED (D8) |
| Running Indicator | Green LED (D4) |
| Standby Indicator | Red LED (D3) |

### Scanning Workflow

1. Kamera Raspberry Pi mendeteksi dan melacak objek secara individual.
2. Ketika titik tengah objek memasuki zona pemindaian, Raspberry Pi mengirimkan event `SCANNING`.
3. ESP8266 menghentikan motor dan mengaktifkan LED kuning.
4. Raspberry Pi menjalankan pembacaan barcode atau QR Code menggunakan pyzbar.
5. Sistem memvalidasi hasil pemindaian dan memeriksa kemungkinan duplikasi kode.
6. Jika kode valid, sistem mengirimkan `SCAN_OK`, menyimpan data produk, dan menjalankan kembali konveyor.
7. Jika kode tidak ditemukan dalam 5 detik, sistem menghasilkan `SCAN_FAIL`, memberikan peringatan LED, dan menjalankan kembali konveyor.
8. Jika komunikasi terputus selama lebih dari 6,5 detik saat SCANNING, watchdog ESP8266 menjalankan prosedur pemulihan.

---

## 📡 8. MQTT Communication

Komunikasi antarperangkat menggunakan protokol MQTT dengan broker Eclipse Mosquitto yang berjalan pada Raspberry Pi.

### Broker Configuration

| Parameter | Configuration |
|---|---|
| Broker | Eclipse Mosquitto |
| Host | `192.168.137.230` |
| Port | `1883` |
| Protocol | MQTT |
| Payload Format | JSON / String / Integer |

### MQTT Topics

| Topic | Direction | Payload | Function |
|---|---|---|---|
| `kel9_iot/conveyor/kontrol` | Web / Raspberry Pi → ESP8266 | `ON`, `OFF`, `SCANNING`, `SCAN_OK`, `SCAN_FAIL`, `RPM:<nilai>` | Kendali motor, scanning, dan setpoint RPM. |
| `kel9_iot/conveyor/status` | ESP8266 → Web / Raspberry Pi | JSON | Telemetri PID dan status perangkat keras setiap 500 ms. |
| `kel9_iot/conveyor/data` | Raspberry Pi → Worker / ESP8266 | JSON | Data hasil pemindaian dan informasi produk. |
| `kel9_iot/conveyor/kode` | Raspberry Pi → ESP8266 | String | Menampilkan kode produk yang berhasil dipindai pada LCD. |
| `kel9_iot/conveyor/jumlah` | Raspberry Pi → ESP8266 | Integer | Memperbarui jumlah barang valid pada LCD. |
| `kel9_iot/conveyor/reset` | Web → Raspberry Pi / ESP8266 | `RESET` | Mengatur ulang counter, memori anti-duplikat, dan kalibrasi kamera. |

### Telemetry Payload

Contoh pesan pada topik status:

```json
{
  "status": "RUNNING",
  "saklar": "ON",
  "sistem": "ACTIVE",
  "rpm": 98.5,
  "setpoint": 100,
  "pwm": 145
}
```

Data telemetri dikirimkan setiap 500 ms untuk mendukung pemantauan kondisi konveyor secara real-time.

Contoh data hasil pemindaian:

```json
{
  "uid_barcode": "BCH2611-PRD01-0001",
  "tipe_kode": "QR",
  "status_scan": "VALID",
  "jumlah": 1,
  "rpm_aktual": 98.5,
  "waktu_scan": "2026-11-22 20:00:00"
}
```

*Contoh payload di atas merupakan ilustrasi struktur data, bukan rekaman hasil pengujian aktual.*

---

## 🌐 9. Web Dashboard & Traceability

Aplikasi web berbasis Laravel digunakan sebagai antarmuka utama untuk monitoring, pengendalian, dan pencatatan data produksi.

Dashboard terintegrasi dengan MQTT Worker untuk menerima data telemetri dan mengirimkan perintah kepada ESP8266.

### Dashboard Features

| Feature | Description |
|---|---|
| Conveyor Control | Kendali ON/OFF melalui dashboard. |
| PID Setpoint Tuning | Pengaturan target RPM secara dinamis (20–500 RPM). |
| Real-Time Monitoring | Monitoring RPM, PWM, dan status sistem. |
| Device Connectivity | Monitoring konektivitas ESP8266 dan Raspberry Pi. |
| Live Camera | Menampilkan video langsung dari USB Webcam. |
| Multi-Object Tracking | Menampilkan kotak pelacakan objek dan status pemindaian. |
| QR Code Generator | Membuat label identitas produk berdasarkan batch dan SKU. |
| Production Analytics | Grafik barang valid dan tanpa barcode per jam. |
| Audit Traceability | Menyimpan riwayat pemindaian dan identitas produk. |
| Production Logs | Menampilkan catatan aktivitas produksi. |

### QR Code Label Format

Format identitas produk menggunakan struktur:

```text
BCHxxxx-PRDxx-xxxx
```

Contoh:

```text
BCH2611-PRD01-0001
```

Format tersebut digunakan untuk membedakan batch dan identitas produk dalam proses pencatatan produksi.

---

## 🚀 10. How to Run the System

### 10.1 Hardware & Raspberry Pi

1. Hubungkan ESP8266 dan Raspberry Pi ke sumber daya listrik.
2. Pastikan Raspberry Pi terhubung dengan jaringan lokal yang sama.
3. Pastikan service kamera dan MQTT pada Raspberry Pi berjalan.
4. Service `conveyor-cam.service` dikonfigurasi agar berjalan otomatis saat proses booting.

### 10.2 Local Server & Dashboard

1. Jalankan Laragon menggunakan opsi **Start All**.
2. Pastikan layanan MySQL aktif pada port `3307`.
3. Pastikan konfigurasi database `db_conveyor_kel9` telah sesuai.
4. Jalankan file peluncur:

```bash
MULAI_KONVEYOR.bat
```

File tersebut digunakan untuk mengaktifkan:

- Laravel Web Server.
- MQTT Database Worker (`php artisan mqtt:worker`).
- Dashboard web pada browser.

Alamat dashboard:

```text
http://127.0.0.1:8000
```

### 10.3 System Operation

1. Buka dashboard Smart Conveyor.
2. Pastikan ESP8266 dan Raspberry Pi terhubung.
3. Klik tombol **Jalankan (ON)**.
4. Atur target kecepatan sesuai kebutuhan.
5. Letakkan barang yang telah diberi label QR Code pada sabuk konveyor.
6. Sistem akan mendeteksi objek, menghentikan konveyor, dan melakukan pemindaian otomatis.
7. Hasil pemindaian ditampilkan dan dicatat ke database.

---

# 🧪 11. Hasil Pengujian dan Implementasi

Bagian ini menjelaskan fitur yang telah berhasil diimplementasikan, hasil pengujian fungsi utama, serta kendala yang masih perlu diperhatikan selama pengembangan sistem Smart Conveyor.

## 11.1 Hasil Implementasi Fitur

Berdasarkan implementasi proyek, fitur-fitur utama sistem telah dikembangkan dan diintegrasikan ke dalam tiga subsistem utama, yaitu ESP8266, Raspberry Pi, dan aplikasi web Laravel.

| No. | Fitur | Subsistem | Status | Keterangan |
|:---:|---|---|:---:|---|
| 1 | Closed-Loop PID Control | ESP8266 | ✅ Berhasil | Pengendalian kecepatan motor menggunakan umpan balik encoder FC-03. |
| 2 | RPM Measurement | ESP8266 | ✅ Berhasil | Pengukuran kecepatan menggunakan 20 celah encoder dan interrupt. |
| 3 | EMA Filtering | ESP8266 | ✅ Diimplementasikan | Penyaringan pembacaan RPM untuk mengurangi fluktuasi sensor. |
| 4 | PWM Motor Control | ESP8266 | ✅ Berhasil | Pengaturan kecepatan melalui PWM pada pin D5. |
| 5 | Hybrid Control | ESP8266 & Laravel | ✅ Berhasil | Kendali konveyor melalui dashboard dan saklar fisik. |
| 6 | Local HMI | ESP8266 | ✅ Berhasil | Tampilan status, RPM, jumlah barang, dan LED indikator. |
| 7 | Multi-Object Tracking | Raspberry Pi | ✅ Berhasil | Deteksi dan pelacakan beberapa objek pada sabuk konveyor. |
| 8 | Barcode/QR Scanning | Raspberry Pi | ✅ Berhasil | Pemindaian identitas produk menggunakan OpenCV dan pyzbar. |
| 9 | Stop-and-Scan | ESP8266 & Raspberry Pi | ✅ Berhasil | Penghentian konveyor ketika objek memasuki zona pemindaian. |
| 10 | Auto-Resume | ESP8266 & Raspberry Pi | ✅ Berhasil | Konveyor berjalan kembali setelah SCAN_OK atau SCAN_FAIL. |
| 11 | MQTT Communication | ESP8266 & Raspberry Pi | ✅ Berhasil | Integrasi komunikasi melalui broker Mosquitto lokal. |
| 12 | MJPEG Streaming | Raspberry Pi & Laravel | ✅ Berhasil | Pengiriman video kamera ke dashboard. |
| 13 | Laravel Dashboard | Laravel | ✅ Berhasil | Monitoring dan kendali sistem melalui aplikasi web. |
| 14 | QR Code Generator | Laravel | ✅ Berhasil | Pembuatan label QR berdasarkan batch dan produk. |
| 15 | Production Analytics | Laravel & MySQL | ✅ Berhasil | Visualisasi jumlah barang valid dan tanpa barcode. |
| 16 | Audit Traceability | Laravel & MySQL | ✅ Berhasil | Pencatatan riwayat pemindaian produk. |
| 17 | Watchdog Fail-Safe | ESP8266 | ✅ Diimplementasikan | Mekanisme pemulihan ketika komunikasi terputus saat scanning. |

## 11.2 Hasil Pengujian Fungsi Utama Sistem

Pengujian dilakukan untuk memastikan setiap subsistem dapat menjalankan fungsi sesuai dengan rancangan dan spesifikasi proyek.

Berdasarkan checklist implementasi, pengujian yang telah dilakukan mencakup kalibrasi PID, pengujian Stop-and-Scan multi-barang, serta pengujian mekanisme auto-resume ketika barcode tidak ditemukan.

### A. Pengujian Kendali Kecepatan PID

**Tujuan:** Memastikan motor DC dapat dikendalikan berdasarkan setpoint RPM menggunakan algoritma PID dan umpan balik sensor FC-03.

| Parameter | Konfigurasi |
|---|---|
| Setpoint Default | 100 RPM |
| Rentang Setpoint | 20–500 RPM |
| Kp | 1.2 |
| Ki | 0.8 |
| Kd | 0.05 |
| Sampling Time | 250 ms |
| Sensor | FC-03 (20 Slots) |
| Output | PWM 85–255 |

**Hasil pengujian:**

- Algoritma PID telah diimplementasikan pada ESP8266.
- Pembacaan kecepatan motor dilakukan melalui sensor encoder FC-03.
- Pengaturan keluaran motor dilakukan menggunakan sinyal PWM.
- Kalibrasi PID telah dilakukan sebagai bagian dari pengujian sistem kendali.

**Kesimpulan:** Fungsi kendali kecepatan berbasis PID telah diimplementasikan dan masuk dalam pengujian sistem. Pengukuran numerik seperti settling time, overshoot, dan error steady-state perlu dicatat tersendiri untuk mengevaluasi tingkat akurasi kendali.

### B. Pengujian Computer Vision dan Barcode/QR Scanning

**Tujuan:** Memastikan Raspberry Pi dapat mendeteksi objek dan membaca identitas produk menggunakan kamera.

| Skenario | Hasil yang Diharapkan | Status |
|---|---|:---:|
| Deteksi satu objek | Objek terdeteksi kamera | Berhasil |
| Deteksi multi-objek | Setiap objek dilacak secara individual | Berhasil |
| Pembacaan QR Code | Identitas produk terbaca | Berhasil |
| Pembacaan barcode | Identitas produk teridentifikasi | Berhasil |
| Validasi kode | Kode diperiksa sebelum disimpan | Berhasil |
| Filter anti-duplikat | Kode yang sama tidak dihitung berulang | Berhasil |

**Hasil pengujian:**

- Sistem Computer Vision telah diimplementasikan menggunakan OpenCV.
- Pelacakan objek dilakukan secara individual dengan identitas objek seperti `#1`, `#2`, dan seterusnya.
- Pembacaan barcode/QR dilakukan menggunakan library pyzbar.
- Sistem menggunakan filter anti-duplikat untuk menghindari pencatatan identitas yang sama secara berulang.

**Kesimpulan:** Subsistem Computer Vision dan pemindaian identitas produk telah berhasil diimplementasikan dan diuji pada skenario multi-objek.

### C. Pengujian Stop-and-Scan

**Tujuan:** Memastikan konveyor dapat berhenti secara otomatis ketika objek memasuki zona pemindaian dan berjalan kembali setelah proses selesai.

| Skenario | Respons Sistem | Status |
|---|---|:---:|
| Objek memasuki zona kamera | Raspberry Pi mengirim `SCANNING` | Berhasil |
| Event SCANNING diterima | Motor berhenti dan LED kuning menyala | Berhasil |
| Barcode valid | Mengirim `SCAN_OK` dan auto-resume | Berhasil |
| Barcode tidak ditemukan | Mengirim `SCAN_FAIL` dan auto-resume | Berhasil |
| Timeout pemindaian | Sistem memulihkan operasi konveyor | Berhasil diuji |
| Pemindaian multi-barang | Proses Stop-and-Scan pada beberapa objek | Berhasil diuji |

**Hasil pengujian:**

- Mekanisme penghentian konveyor berdasarkan deteksi objek telah diimplementasikan.
- Proses pemindaian berlangsung dengan batas maksimal 5 detik.
- Sistem dapat melanjutkan operasi setelah hasil pemindaian diproses.
- Pengujian Stop-and-Scan multi-barang dan mekanisme auto-resume telah dilakukan.

**Kesimpulan:** Mekanisme Stop-and-Scan telah berhasil diimplementasikan dan diuji untuk mendukung proses identifikasi produk secara otomatis.

### D. Pengujian Komunikasi MQTT

**Tujuan:** Memastikan komunikasi antara ESP8266, Raspberry Pi, dan aplikasi web berjalan sesuai kebutuhan sistem.

| Skenario | Hasil yang Diharapkan | Status |
|---|---|:---:|
| Koneksi ESP8266 ke broker | Perangkat terhubung ke Mosquitto | Berhasil |
| Pengiriman perintah ON/OFF | Status motor berubah sesuai perintah | Berhasil |
| Pengiriman SCANNING | Konveyor berhenti | Berhasil |
| Pengiriman SCAN_OK | Konveyor berjalan kembali | Berhasil |
| Pengiriman SCAN_FAIL | Sistem menjalankan auto-resume | Berhasil |
| Pengiriman telemetri | Data status dikirim setiap 500 ms | Berhasil diimplementasikan |
| Pengiriman data produk | Hasil scan diteruskan ke worker | Berhasil |

**Hasil pengujian:**

- Broker Mosquitto telah digunakan sebagai pusat komunikasi.
- ESP8266 dan Raspberry Pi telah diintegrasikan menggunakan MQTT.
- Dashboard menggunakan MQTT Worker untuk memproses pesan.
- Pengiriman data status dan hasil pemindaian telah diintegrasikan melalui topik yang telah ditentukan.

**Kesimpulan:** Komunikasi MQTT telah diimplementasikan sebagai penghubung antarperangkat dan aplikasi web.

### E. Pengujian Dashboard dan Database

**Tujuan:** Memastikan aplikasi web dapat digunakan untuk monitoring, kendali jarak jauh, dan pencatatan riwayat produksi.

| Fitur | Hasil yang Diharapkan | Status |
|---|---|:---:|
| Dashboard Monitoring | Menampilkan status perangkat dan konveyor | Berhasil |
| Remote ON/OFF | Mengendalikan motor melalui web | Berhasil |
| Setpoint Tuning | Mengubah target RPM | Berhasil |
| Live Camera | Menampilkan video kamera Raspberry Pi | Berhasil |
| QR Code Generator | Menghasilkan label QR produk | Berhasil |
| Production Analytics | Menampilkan grafik produksi | Berhasil |
| Audit Traceability | Menampilkan riwayat pemindaian | Berhasil |
| Reset Counter & Log | Mengatur ulang data penghitung dan log | Berhasil diimplementasikan |

**Hasil pengujian:**

- Aplikasi web Laravel telah terintegrasi dengan MQTT Worker.
- Database MySQL digunakan untuk menyimpan informasi produksi.
- Dashboard menyediakan fungsi kendali dan monitoring.
- Fitur QR Code Generator, grafik produksi, dan Audit Traceability telah dikembangkan.

**Kesimpulan:** Subsistem aplikasi web dan database telah berhasil diimplementasikan untuk mendukung monitoring dan pengelolaan data produksi.

## 11.3 Ringkasan Hasil Pengujian

| No. | Subsistem | Fokus Pengujian | Hasil |
|:---:|---|---|---|
| 1 | ESP8266 | PID dan pembacaan RPM | Berhasil diimplementasikan dan dikalibrasi |
| 2 | Motor DC | Pengaturan PWM | Berhasil |
| 3 | Computer Vision | Deteksi multi-objek | Berhasil |
| 4 | Scanner | Pembacaan QR/Barcode | Berhasil |
| 5 | Otomasi | Stop-and-Scan multi-barang | Berhasil diuji |
| 6 | Otomasi | Auto-Resume ketika barcode tidak ditemukan | Berhasil diuji |
| 7 | Komunikasi | Integrasi MQTT | Berhasil |
| 8 | Dashboard | Kendali dan monitoring | Berhasil |
| 9 | Database | Pencatatan traceability | Berhasil diimplementasikan |

**Catatan:** Status keberhasilan pada tabel merupakan ringkasan implementasi dan checklist pengujian proyek. Nilai pengukuran kuantitatif seperti RPM aktual setiap skenario, persentase error PID, waktu respons, dan tingkat keberhasilan pemindaian belum dicantumkan karena belum tersedia dalam dokumentasi pengujian yang digunakan.

## 11.4 Kendala dan Hal yang Perlu Disempurnakan

Dalam proses pengembangan sistem terintegrasi, terdapat beberapa aspek teknis yang perlu mendapatkan perhatian lebih lanjut.

| No. | Aspek | Hal yang Perlu Diperhatikan | Rencana Penyempurnaan |
|:---:|---|---|---|
| 1 | PID Tuning | Parameter PID perlu dievaluasi berdasarkan perubahan beban dan karakteristik motor. | Melakukan pengujian kuantitatif dan penyetelan ulang parameter PID. |
| 2 | Sensor Encoder | Pembacaan RPM berpotensi dipengaruhi noise dan kondisi optik encoder. | Melakukan evaluasi filter dan kestabilan pembacaan pulsa. |
| 3 | Computer Vision | Akurasi deteksi objek dan pembacaan barcode dapat dipengaruhi posisi serta kondisi pencahayaan. | Melakukan kalibrasi kamera dan pengujian pada variasi posisi objek. |
| 4 | MQTT Connection | Gangguan jaringan dapat memengaruhi pertukaran pesan antarperangkat. | Mengevaluasi mekanisme reconnect dan watchdog. |
| 5 | Stop-and-Scan | Perlu pengujian lebih lanjut terhadap objek yang berdekatan dan antrean pemindaian. | Mengoptimalkan koordinasi multi-objek dan urutan scanning. |
| 6 | Traceability | Konsistensi data produk perlu dijaga agar tidak terjadi pencatatan ganda. | Mempertahankan validasi UID dan filter anti-duplikat. |

**Keterangan:** Tabel tersebut merupakan aspek evaluasi dan pengembangan lanjutan, bukan pernyataan bahwa seluruh kendala telah ditemukan dalam pengujian. Belum terdapat laporan kendala aktual yang secara spesifik dinyatakan belum terselesaikan.

## 11.5 Evaluasi Akhir Implementasi

Berdasarkan implementasi dan pengujian yang telah dilakukan, Smart Conveyor Control & Traceability System telah mengintegrasikan tiga subsistem utama, yaitu kendali motor berbasis PID, pemindaian produk berbasis Computer Vision, dan monitoring produksi melalui aplikasi web berbasis IoT.

Pengujian menunjukkan bahwa fungsi utama seperti kendali PID, deteksi multi-objek, pemindaian barcode/QR, mekanisme Stop-and-Scan, auto-resume, serta komunikasi MQTT telah diimplementasikan dan diuji.

Integrasi dengan Laravel dan MySQL juga memungkinkan pengelolaan identitas produk serta pencatatan aktivitas produksi melalui dashboard.

Pengembangan selanjutnya difokuskan pada dokumentasi hasil pengukuran kuantitatif, evaluasi akurasi PID, dan pengujian keandalan sistem pada variasi beban serta kondisi komunikasi yang berbeda.

---

## 🔮 12. Future Development

Beberapa pengembangan yang dapat dilakukan untuk meningkatkan kemampuan sistem:

- Implementasi algoritma PID tuning otomatis.
- Penambahan sensor pendeteksi keberadaan barang.
- Pengembangan sistem multi-camera untuk area pemindaian yang lebih luas.
- Implementasi analisis performa produksi secara historis.
- Penambahan fitur notifikasi ketika terjadi kegagalan sistem.
- Pengembangan sistem prediksi gangguan motor berdasarkan data RPM dan PWM.
- Implementasi mekanisme emergency stop dan proteksi aktuator tambahan.
- Pengujian performa PID dengan pengukuran settling time, overshoot, dan steady-state error.
- Pengujian akurasi pembacaan barcode/QR pada berbagai kondisi pencahayaan.

---

## 📄 13. License & Academic Disclaimer

Proyek ini dikembangkan sebagai bagian dari tugas akademik Mata Kuliah **Internet of Things (IoT)** pada Program Studi Teknik Komputer, Fakultas Teknik, Universitas Jenderal Soedirman, Tahun 2026.

Seluruh rancangan dan implementasi ditujukan untuk kebutuhan pembelajaran, eksperimen, serta pengembangan purwarupa sistem otomasi berbasis IoT.

---

<p align="center">
  <strong>SMART CONVEYOR CONTROL & TRACEABILITY SYSTEM</strong><br>
  <em>Automating Motion. Identifying Products. Tracking Production.</em><br><br>
  Developed by <strong>Group 9 — Computer Engineering</strong><br>
  Universitas Jenderal Soedirman · 2026
</p>
