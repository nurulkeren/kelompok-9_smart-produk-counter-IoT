
# SMART CONVEYOR CONTROL & TRACEABILITY SYSTEM

**Sistem Kendali Kecepatan Sabuk Berbasis PID, Pemindaian Barcode/QR *Computer Vision*, dan Monitoring Produksi *Real-Time* Berbasis IoT**

## Identitas Kelompok

| Keterangan | Informasi |
| :--- | :--- |
| **Mata Kuliah** | Internet of Things (IoT) |
| **Program Studi** | Teknik Komputer |
| **Fakultas** | Teknik |
| **Universitas** | Universitas Jenderal Soedirman |
| **Kelompok** | 9 |
| **Kelas** | A |
| **Tahun** | 2026 |

## Anggota Kelompok

| No. | Nama Lengkap | NIM | Peran |
| :--- | :--- | :--- | :--- |
| 1. | Nurul Maftuhah | H1H024002 | Ketua Kelompok |
| 2. | Difa' Tamaya Maulidina Adz dzikro | H1H024019 | Anggota |
| 3. | Kaira Meilasya Nayada | H1H024020 | Anggota |
| 4. | Nursyafika | H1H024023 | Anggota |

---

## Deskripsi Proyek

**Smart Conveyor Control & Traceability System** merupakan sistem otomasi jalur konveyor industri skala purwarupa yang menggabungkan **kendali kecepatan lup tertutup (*Closed-Loop PID*)**, **pemindaian identitas produk berbasis *Computer Vision***, dan **pencatatan riwayat produksi (*Audit Traceability*)** secara *real-time* melalui protokol **MQTT**.

Sistem bekerja secara terintegrasi antara tiga subsistem utama:
1. **ESP8266 NodeMCU (*Edge Controller*):** Mengatur kecepatan motor DC konveyor menggunakan algoritma **PID digital** berdasarkan umpan balik sensor optocoupler **FC-03** ($20$ celah), mengelola kendali hibrida (tombol web maupun saklar fisik), serta menampilkan status operasi pada **LCD 16×2** dan **3 LED indikator**.
2. **Raspberry Pi (*Vision & MQTT Broker Node*):** Menjalankan pemrosesan citra (**OpenCV** & **`pyzbar`**) untuk mendeteksi keberadaan multi-objek di atas sabuk, menghentikan konveyor secara otomatis selama maksimal **$5\text{ detik}$** (*stop-and-scan*) saat objek berada di tengah zona kamera, memindai kode QR/Barcode, serta mengalirkan *live video stream* ke dashboard.
3. **Aplikasi Web Laravel & MySQL:** Menyediakan antarmuka kendali jarak jauh (`ON`/`OFF` dan *tuning* target RPM), pemantauan telemetri PID secara *real-time*, *generator* label QR Code per batch/produk, grafik laju produksi harian, dan tabel log audit keterlacakan produk.

---

## Komponen Sistem

### 1. Perangkat Keras (*Hardware*)

| No. | Komponen | Spesifikasi / Tipe | Fungsi dalam Sistem |
| :--- | :--- | :--- | :--- |
| 1. | **Mikrokontroler Kendali** | ESP8266 (NodeMCU ESP-12E) | Eksekusi algoritma PID motor, pembacaan encoder FC-03, kontrol relay & HMI lokal. |
| 2. | **Komputer Mini & Broker** | Raspberry Pi + USB Webcam | Pemrosesan *computer vision* (OpenCV/pyzbar), *MJPEG streaming*, dan broker MQTT Mosquitto. |
| 3. | **Aktuator & Penggerak** | Motor DC + Driver PWM + Relay | Menggerakkan sabuk konveyor dengan pengaturan kecepatan PWM ($85\text{–}255$) dan pemutus daya utama. |
| 4. | **Sensor Kecepatan** | Optocoupler / Encoder FC-03 | Mengukur kecepatan putar aktual sabuk (RPM) menggunakan piringan $20$ celah berbasis *interrupt*. |
| 5. | **Layar Display Lokal** | LCD 16×2 + Modul I2C (`0x27`) | Menampilkan status konveyor (`JALAN`, `SCANNING`, `MATI`), jumlah barang valid, dan RPM aktual. |
| 6. | **Saklar & Indikator** | Saklar Manual + 3× LED (Merah, Kuning, Hijau) | Kontrol manual *edge-triggered* dan indikator visual status sistem (*Standby*, *Scanning*, *Running*). |

### Pemetaan Pin ESP8266 NodeMCU

| Pin NodeMCU | Konstanta Program | Komponen Terhubung | Keterangan Sinyal |
| :--- | :--- | :--- | :--- |
| `D0` | `PIN_RELAY` | Modul Relay Daya Motor | *Active-Low* (pemutus daya utama motor konveyor) |
| `D1` | `PIN_LCD_SCL` | LCD 16×2 I2C | Jalur clock komunikasi I2C |
| `D2` | `PIN_LCD_SDA` | LCD 16×2 I2C | Jalur data komunikasi I2C |
| `D3` | `PIN_LED_MERAH` | LED Indikator Merah | Nyala saat konveyor berhenti / *Standby* (`OFF`) |
| `D4` | `PIN_LED_HIJAU` | LED Indikator Hijau | Nyala saat konveyor berjalan normal (`RUNNING`) |
| `D5` | `PIN_ENA` | Input PWM Driver Motor | Sinyal PWM $1000\text{ Hz}$, resolusi 8-bit ($85\text{–}255$) |
| `D6` | `PIN_SENSOR` | Sensor Encoder FC-03 | *Hardware Interrupt* (`FALLING`) pembaca pulsa kecepatan |
| `D7` | `PIN_SAKLAR` | Saklar Manual Fisik | `INPUT_PULLUP` (deteksi perubahan posisi *edge-triggered*) |
| `D8` | `PIN_LED_KUNING` | LED Indikator Kuning | Nyala saat proses pemindaian barcode (`SCANNING`) |

### 2. Perangkat Lunak & Layanan (*Software Stack*)

- **Firmware Mikrokontroler:** Arduino IDE (C/C++) dengan pustaka `ESP8266WiFi`, `PubSubClient`, dan `LiquidCrystal_I2C`.
- **Computer Vision & Service (Raspberry Pi):** Python 3 (`opencv-python`, `pyzbar`, `numpy`, `paho-mqtt`) yang berjalan otomatis saat *booting* melalui layanan `systemd` (`conveyor-cam.service`).
- **Message Broker:** Eclipse Mosquitto MQTT Broker lokal (`192.168.137.230`, Port `1883`).
- **Backend, Frontend & Database:** PHP Laravel Framework, *MQTT Background Worker* (`php artisan mqtt:worker`), dan MySQL (`db_conveyor_kel9`, Port `3307` via Laragon).

---

## Arsitektur Sistem

Sistem menggunakan arsitektur terdistribusi berbasis protokol **MQTT** dan **HTTP MJPEG Stream**:

```text
+-------------------------------------------------------------------------+
|                     EDGE CONTROL LAYER (ESP8266)                        |
|                                                                         |
|  [Encoder FC-03 (D6)] ---> [  Algoritma PID  ] ---> [PWM Motor (D5)]    |
|  (20 Celah, dt=250ms)      [ Kp=1.2, Ki=0.8, ] ---> [Relay Daya (D0)]   |
|  [Saklar Fisik (D7)]  ---> [     Kd=0.05     ] ---> [LCD 16x2 I2C]      |
|                                     ^          ---> [LED M / K / H]     |
+-------------------------------------|-----------------------------------+
                                      | WiFi (MQTT Pub/Sub)
                                      v
+-------------------------------------------------------------------------+
|               VISION & BROKER LAYER (RASPBERRY PI)                      |
|                                                                         |
|  [USB Webcam] ---> [ OpenCV Multi-Object Tracker & pyzbar Scanner ]     |
|                             |                         |                 |
|             (MJPEG Stream :5050)        [ Mosquitto MQTT Broker :1883 ] |
+-----------------------------|-------------------------|-----------------+
                              |                         |
                    HTTP Live Video           MQTT Topics (JSON)
                              |                         |
                              v                         v
+-------------------------------------------------------------------------+
|               APPLICATION & DATABASE LAYER (LARAVEL + MYSQL)            |
|                                                                         |
|  [MQTT Worker] ---> [ MySQL: db_conveyor_kel9 (:3307) ]                 |
|                            |                                            |
|                            v                                            |
|  [ Smart Conveyor Web Dashboard ([http://127.0.0.1:8000](http://127.0.0.1:8000)) ]               |
|   * Kendali Hibrida ON/OFF & Tuning Setpoint RPM                        |
|   * Live Vision Camera, Generator Label QR & Audit Traceability         |
+-------------------------------------------------------------------------+

```

### Pemetaan Topik MQTT (*MQTT Topics*)

| Arah Komunikasi | Nama Topik | Format / Payload | Keterangan |
| --- | --- | --- | --- |
| **Bidirectional** (Web / Raspi $\rightarrow$ ESP) | `kel9_iot/conveyor/kontrol` | `ON`, `OFF`, `SCANNING`, `SCAN_OK`, `SCAN_FAIL`, `RPM:<nilai>` | Mengatur status operasi konveyor, jeda *scanning*, dan target kecepatan RPM. |
| **Publish** (ESP $\rightarrow$ Web / Raspi) | `kel9_iot/conveyor/status` | JSON (`status`, `saklar`, `sistem`, `rpm`, `setpoint`, `pwm`) | Mengirimkan telemetri performa PID dan status perangkat keras setiap $500\text{ ms}$. |
| **Publish** (Raspi $\rightarrow$ Worker / ESP) | `kel9_iot/conveyor/data` | JSON (`uid_barcode`, `tipe_kode`, `status_scan`, `jumlah`, `rpm_aktual`, `waktu_scan`) | Mengirimkan hasil pemindaian (`VALID` atau `FAILED`) untuk dicatat ke database MySQL. |
| **Publish** (Raspi $\rightarrow$ ESP) | `kel9_iot/conveyor/kode` | String (contoh: `BCH2611-PRD01-0001`) | Menampilkan notifikasi keberhasilan pemindaian pada LCD 16×2. |
| **Publish** (Raspi $\rightarrow$ ESP) | `kel9_iot/conveyor/jumlah` | Integer (`0`, `1`, `2`, ...) | Memperbarui penghitung barang valid pada LCD 16×2 secara *real-time*. |
| **Publish** (Web $\rightarrow$ Raspi / ESP) | `kel9_iot/conveyor/reset` | `RESET` | Mengatur ulang counter barang, memori anti-duplikat, dan kalibrasi kamera. |

---

## Formulasi Kendali & Mekanisme Kerja Sistem

### 1. Regulasi Kecepatan Lup Tertutup (*Closed-Loop PID*)

* **Pengukuran & Filter RPM:** Pulsa sensor FC-03 dihitung setiap periode sampling $\Delta t = 0,25\text{ s}$ dan dihaluskan menggunakan *Exponential Moving Average* (EMA):

$$\text{RPM}_{\text{filtered}}(k) = 0,6 \cdot \text{RPM}_{\text{aktual}}(k) + 0,4 \cdot \text{RPM}_{\text{filtered}}(k-1)$$

* **Kontroler PID Diskrit:** Menggunakan konstanta $K_p = 1,2$, $K_i = 0,8$, dan $K_d = 0,05$ dengan pembatasan integral (*anti-windup clamping* pada rentang $[-150, 150]$) serta penskalaan aktuator PWM pada rentang kerja efektif $85\text{–}255$ (diawali *kick-start* $\text{PWM} = 150$ untuk mengatasi inersia awal sabuk).

### 2. Alur Operasional (*Hybrid Control & Stop-and-Scan*)

1. **Kendali Hibrida Bebas (*Non-Locking*):** Operator dapat menyalakan (`Jalankan ON`) atau menghentikan (`Hentikan OFF`) konveyor langsung dari dashboard web tanpa harus menggeser saklar fisik terlebih dahulu; sebaliknya, pergeseran saklar fisik tetap dapat mengambil alih status operasi kapan saja.
2. **Deteksi Multi-Objek & *Stop-and-Scan*:** Kamera melacak setiap barang di atas sabuk secara individual (`#1`, `#2`, dst.). Saat titik tengah barang memasuki zona pemindaian di tengah lensa, Raspberry Pi mengirim perintah `SCANNING` sehingga ESP8266 langsung menghentikan motor (LED Kuning menyala) selama maksimal **$5\text{ detik}$**.
3. **Validasi QR/Barcode & *Auto-Resume*:**
* **Barcode Valid (`SCAN_OK`):** Sistem memvalidasi kode (dilengkapi filter anti-duplikat), mengirim data JSON ke MySQL, menambah jumlah barang valid, dan langsung menjalankan konveyor kembali.
* **Tanpa Barcode / Timeout 5 Detik (`SCAN_FAIL`):** ESP8266 mengedipkan ketiga LED sebanyak $2\times$ sebagai peringatan visual, mencatat status `FAILED` (`NO_BARCODE`) ke grafik produksi harian, dan **otomatis menjalankan konveyor kembali** (*auto-resume*) agar aliran produksi tidak tersumbat.
* **Pengaman *Watchdog Fail-Safe*:** Jika komunikasi dengan Raspberry Pi terputus saat mode `SCANNING` melebihi $6,5\text{ detik}$, ESP8266 memulihkan konveyor ke mode berjalan secara mandiri.



---

## Fitur Dashboard Web

* **Panel Telemetri & Status Real-Time:** Menampilkan status konektivitas ESP8266 & Raspberry Pi, status konveyor (`RUNNING`, `SCANNING`, `OFF`), kecepatan aktual sabuk (RPM), nilai PWM, jumlah barang valid, serta indikator peringatan tanpa barcode.
* **Kendali Operasi & Tuning PID:** Tombol jarak jauh **Jalankan (ON)**, **Hentikan (OFF)**, **Reset Counter & Log**, serta pengaturan target kecepatan sabuk ($20\text{–}500\text{ RPM}$).
* **Live Vision Camera:** Menampilkan umpan video langsung dari kamera Raspberry Pi lengkap dengan kotak pelacakan objek dan status pemindaian.
* **Generator Label Barcode & Master Batch:** Membuat dan mencetak label QR Code sesuai format Batch dan SKU produk (`BCHxxxx-PRDxx-xxxx`).
* **Visualisasi Laju Produksi & Audit Traceability:** Grafik perbandingan barang valid vs tanpa barcode per jam serta tabel riwayat lengkap setiap pemindaian yang tersimpan di MySQL.

---

## Cara Menjalankan Sistem

1. **Perangkat Keras (ESP8266 & Raspberry Pi):**
* Hubungkan ESP8266 dan Raspberry Pi ke sumber daya listrik. Layanan kamera & MQTT (`conveyor-cam.service`) pada Raspberry Pi akan berjalan otomatis saat *booting*.


2. **Server Lokal & Dashboard (Laptop/PC):**
* Jalankan **Laragon** (*Start All*) dan pastikan layanan **MySQL** aktif pada port **`3307`**.
* Jalankan file peluncur sekali klik **`MULAI_KONVEYOR.bat`** di folder utama proyek untuk mengaktifkan *Laravel Web Server*, *MQTT Database Worker* (`php artisan mqtt:worker`), dan membuka dashboard di browser (`http://127.0.0.1:8000`).


3. **Operasi:**
* Klik tombol **`Jalankan (ON)`** pada dashboard untuk memulai konveyor dan meletakkan barang berlabel QR Code di atas sabuk.



---

## Status Pengembangan

* [x] Perancangan sistem kendali kecepatan *closed-loop* PID pada ESP8266 dengan umpan balik encoder FC-03.
* [x] Implementasi algoritma *computer vision* multi-objek dan pemindaian QR/Barcode pada Raspberry Pi (`conveyor_cam.py`).
* [x] Integrasi komunikasi dua arah melalui broker MQTT Mosquitto lokal dan *auto-start service* `systemd`.
* [x] Pembangunan dashboard web Laravel, *MQTT worker*, database MySQL (`db_conveyor_kel9`), serta *launcher* otomatis.
* [x] Pengujian *stop-and-scan* multi-barang, kalibrasi PID, dan mekanisme *auto-resume* pada kondisi tanpa barcode.
* [ ] Penyusunan laporan akhir proyek rekayasa sistem kendali dan dokumentasi video demonstrasi.

```

