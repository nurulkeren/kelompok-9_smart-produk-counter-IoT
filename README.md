# TUGAS BESAR 1 INTERNET OF THINGS (IoT)

**Smart Product Counter Berbasis ESP8266 dan Protokol MQTT**

## Identitas Kelompok

| Keterangan | Informasi | 
| ----- | ----- | 
| **Mata Kuliah** | Internet of Things (IoT) | 
| **Program Studi** | Teknik Komputer | 
| **Fakultas** | Teknik | 
| **Universitas** | Universitas Jenderal Soedirman | 
| **Kelompok** | 9 | 
| **Kelas** | A | 
| **Tahun** | 2026 | 

## Anggota Kelompok

| No. | Nama Lengkap | NIM | Peran | 
| ----- | ----- | ----- | ----- | 
| 1. | Nurul Maftuhah | H1H024002 | Ketua Kelompok | 
| 2. | Difa' Tamaya Maulidina Adz dzikro | H1H024019 | Anggota | 
| 3. | Kaira Meilasya Nayada | H1H024020 | Anggota | 
| 4. | Nursyafika | H1H024023 | Anggota | 

## Deskripsi Proyek

**Smart Product Counter** merupakan sistem penghitung dan pemantau jumlah stok barang berbasis Internet of Things (IoT). Sistem menggunakan mikrokontroler **ESP8266** sebagai pusat pengendali dan sensor ultrasonik **HC-SR04** untuk mendeteksi keberadaan objek/barang. Jumlah barang yang terdeteksi akan dihitung secara otomatis, ditampilkan melalui **LCD 16×2**, serta dikirimkan secara *real-time* melalui komunikasi **MQTT**.

Sistem dirancang dengan target penghitungan sebanyak **10 barang** dan batas jarak deteksi sensor sebesar $\le 15\text{ cm}$. Pengguna dapat mengaktifkan atau menghentikan proses melalui tombol **START/STOP** dan mengembalikan hitungan ke kondisi awal melalui tombol **RESET**. Ketika target tercapai, sistem menghentikan monitoring, menyalakan LED indikator target, menampilkan status pada LCD, dan membunyikan buzzer.

Komunikasi IoT menggunakan jaringan WiFi dan broker MQTT publik **HiveMQ**. ESP8266 mengirimkan data jumlah stok dan status sistem, serta dapat menerima perintah `START`, `STOP`, dan `RESET` melalui *topic* MQTT yang telah ditentukan.

## Komponen Sistem

### 1. Perangkat Keras (*Hardware*)

| No. | Komponen | Spesifikasi / Tipe | Fungsi dalam Sistem | 
| ----- | ----- | ----- | ----- | 
| 1. | **Mikrokontroler** | ESP8266 (NodeMCU ESP-12E) | Pusat pemrosesan logika penghitung, kontrol I/O, dan konektivitas WiFi/MQTT. | 
| 2. | **Sensor Jarak** | Ultrasonik HC-SR04 | Mendeteksi objek/barang yang melintas pada jarak $\le 15\text{ cm}$. | 
| 3. | **Layar Display** | LCD 16×2 + Modul I2C | Menampilkan jumlah stok terhitung dan status operasional sistem secara lokal. | 
| 4. | **Tombol Kontrol** | 2× Push Button Tactile | Input fisik untuk perintah **START/STOP** proses dan **RESET** hitungan. | 
| 5. | **Indikator Visual** | LED + Resistor $220\text{ }\Omega$ | Memberikan sinyal visual ketika target 10 barang telah tercapai. | 
| 6. | **Indikator Audio** | Buzzer Aktif 5V | Memberikan peringatan suara saat target penghitungan tercapai. | 
| 7. | **Pendukung** | Breadboard & Kabel Jumper | Media perakitan rangkaian prototipe dan distribusi jalur daya/sinyal. | 

### 2. Perangkat Lunak & Layanan (*Software & Cloud*)

* **Arduino IDE (C/C++):** Lingkungan pengembangan untuk pemrograman *firmware* ESP8266.

* **Library Pendukung:** `ESP8266WiFi`, `PubSubClient` (komunikasi MQTT), dan `LiquidCrystal_I2C`.

* **MQTT Broker:** HiveMQ Public Broker (`broker.hivemq.com`, Port `1883` / WebSocket `8000`).

* **IoT Dashboard:** Antarmuka berbasis web/aplikasi MQTT Client untuk pemantauan dan kendali jarak jauh.

## Arsitektur Sistem

Sistem menerapkan arsitektur IoT dua arah (*bi-directional*) berbasis pola *Publish-Subscribe* melalui protokol MQTT:

```
+-------------------------------------------------------------------+
|                        HARDWARE LAYER (EDGE)                      |
|                                                                   |
|  [Sensor HC-SR04] ----+                                           |
|  (Deteksi <= 15 cm)   |                                           |
|                       v                                           |
|  [Tombol START/STOP] ---> [   ESP8266    ] ---> [LCD 16x2 I2C]    |
|  [Tombol RESET]      ---> [ NodeMCU 12E  ] ---> [LED Indikator]   |
|                                  ^         ---> [Buzzer]          |
+----------------------------------|--------------------------------+
                                   |
                         WiFi (TCP/IP - MQTT)
                                   |
                                   v
+-------------------------------------------------------------------+
|                         BROKER LAYER (CLOUD)                      |
|                                                                   |
|                   [ HiveMQ Public MQTT Broker ]                   |
|                     (broker.hivemq.com:1883)                      |
+----------------------------------|--------------------------------+
                                   |
                       Publish & Subscribe Topics
                                   |
                                   v
+-------------------------------------------------------------------+
|                       APPLICATION LAYER (USER)                    |
|                                                                   |
|                        [  IoT Dashboard  ]                        |
|        * Monitoring: Jumlah Barang & Status Sistem                |
|        * Kontrol   : Tombol Virtual START, STOP, RESET            |
+-------------------------------------------------------------------+

```

### Pemetaan Topik MQTT (*MQTT Topics*)

| Arah Komunikasi | Nama Topik *(Contoh)* | Payload | Keterangan | 
| ----- | ----- | ----- | ----- | 
| **Publish** (ESP $\rightarrow$ Broker) | `unsoed/iot/kel9/jumlah` | `0` – `10` | Mengirimkan pembaruan jumlah barang setiap kali terdeteksi. | 
| **Publish** (ESP $\rightarrow$ Broker) | `unsoed/iot/kel9/status` | `READY`, `RUNNING`, `STOPPED`, `TARGET_REACHED` | Mengirimkan status kondisi sistem saat ini. | 
| **Subscribe** (Broker $\rightarrow$ ESP) | `unsoed/iot/kel9/kontrol` | `START`, `STOP`, `RESET` | Menerima instruksi kendali jarak jauh dari dashboard. | 

## Mekanisme Kerja Sistem

1. **Inisialisasi Sistem:**

   * Saat perangkat dinyalakan, ESP8266 melakukan koneksi ke jaringan WiFi dan terhubung ke broker MQTT HiveMQ.

   * LCD 16×2 menampilkan status awal `SYSTEM READY` dengan hitungan awal `0 / 10`.

2. **Aktivasi Proses (*Start*):**

   * Pengguna menekan tombol fisik **START/STOP** atau menekan tombol **START** pada dashboard IoT.

   * Status sistem berubah menjadi `RUNNING` dan sensor ultrasonik mulai memindai objek.

3. **Deteksi & Penghitungan Barang:**

   * Sensor HC-SR04 mengukur jarak objek di depannya secara berkala.

   * Apabila terbaca jarak $\le 15\text{ cm}$, sistem mencatat $+1$ barang. Sistem menerapkan logika *state-change detection* (menunggu objek menjauh $> 15\text{ cm}$ sebelum menghitung lagi) agar satu barang yang diam tidak terhitung berulang kali.

   * Nilai hitungan terbaru langsung ditampilkan di LCD 16×2 dan dikirim (*publish*) ke broker HiveMQ.

4. **Penanganan Target Tercapai (Limit 10 Barang):**

   * Ketika nilai hitungan mencapai $10$, sistem secara otomatis menghentikan proses pemantauan (`TARGET_REACHED`).

   * **LED indikator** menyala, **buzzer** berbunyi sebagai notifikasi, dan layar LCD menampilkan pesan `TARGET TERCAPAI!`.

5. **Penghentian Sementara & Reset:**

   * Pengguna dapat menjeda penghitungan kapan saja melalui tombol **START/STOP** atau perintah `STOP` dari dashboard.

   * Menekan tombol **RESET** (fisik maupun virtual) akan mengembalikan jumlah hitungan ke `0`, mematikan LED dan buzzer, serta mengembalikan sistem ke kondisi `READY`.

## Dashboard Monitoring & Kontrol

Dashboard berfungsi sebagai antarmuka pengguna (*User Interface*) berbasis web/MQTT client yang terhubung langsung ke broker HiveMQ untuk memantau proses penghitungan tanpa harus berada di dekat perangkat.

### Fitur Utama Dashboard:

* **Counter Display & Progress:** Menampilkan angka jumlah barang yang telah terhitung secara *real-time* beserta indikator pencapaian menuju target 10 barang.

* **Status Indicator:** Menampilkan status operasional terkini (`READY`, `RUNNING`, `STOPPED`, atau `TARGET REACHED`).

* **Remote Control Panel:**

  * Tombol **START:** Memulai proses penghitungan jarak jauh.

  * Tombol **STOP:** Menghentikan sementara proses monitoring.

  * Tombol **RESET:** Menghapus hitungan menjadi `0` dan mereset alarm target.

> *Catatan: Dokumentasi tangkapan layar (screenshot) tampilan dashboard dapat dilampirkan pada bagian ini setelah pengujian antarmuka selesai.*

## Status Pengembangan

Progres pengerjaan proyek **Smart Product Counter** hingga saat ini:

* \[x\] Perancangan spesifikasi sistem dan arsitektur komunikasi MQTT.

* \[x\] Perakitan rangkaian perangkat keras (ESP8266, HC-SR04, LCD I2C, Push Button, LED, Buzzer).

* \[x\] Implementasi logika pembacaan jarak sensor ultrasonik ($\le 15\text{ cm}$) dengan pencegahan *double counting*.

* \[x\] Integrasi output lokal pada LCD 16×2, LED indikator, dan Buzzer.

* \[x\] Konfigurasi koneksi WiFi dan komunikasi dua arah dengan broker publik HiveMQ.

* \[ \] Pengujian stabilitas sistem secara menyeluruh dan kalibrasi akurasi deteksi barang.

* \[ \] Penyusunan laporan akhir dan video demonstrasi proyek.

## Rencana Pengembangan Selanjutnya

Untuk meningkatkan kapabilitas sistem dari purwarupa dasar menuju standar otomasi industri skala kecil, berikut adalah rencana pengembangan selanjutnya:

1. **Otomatisasi Jalur Konveyor dengan Kontrol PID:**
   Menambahkan sistem mekanik sabuk konveyor menggunakan Motor DC, driver motor **L298N**, serta sensor kecepatan optocoupler (**FC-03**) dengan kendali **PID** agar kecepatan perpindahan barang tetap stabil dan dapat berhenti otomatis saat proses pemindaian.

2. **Identifikasi Jenis Produk Berbasis Computer Vision:**
   Mengintegrasikan **Raspberry Pi** dan modul kamera untuk memindai *barcode* atau klasifikasi visual barang secara otomatis sehingga sistem tidak hanya menghitung kuantitas, tetapi juga mencatat jenis SKU produk.

3. **Penyimpanan Data Historis (*Database Logging*):**
   Menyimpan setiap log transaksi barang masuk dan waktu pencapaian target ke dalam basis data (*MySQL / InfluxDB*) untuk kebutuhan rekapitulasi laporan harian dan analitik inventaris.

4. **Notifikasi Instan ke Perangkat Seluler:**
   Menambahkan integrasi bot **Telegram** atau **WhatsApp** agar operator gudang menerima pesan otomatis begitu target batch produksi tercapai.
