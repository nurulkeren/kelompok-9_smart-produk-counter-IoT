# TUGAS BESAR 1 INTERNET OF THINGS (IoT)

## Identitas Kelompok

| Keterangan | Informasi |
|---|---|
| Mata Kuliah | Internet of Things (IoT) |
| Program Studi | Teknik Komputer |
| Fakultas | Teknik |
| Universitas | Universitas Jenderal Soedirman |
| Kelompok | 9 |
| Kelas | A |
| Tahun | 2026 |

## Anggota Kelompok

| No. | Nama Lengkap | NIM | Peran |
|---|---|---|---|
| 1. | Nurul Maftuhah | H1H024002 | Ketua Kelompok |
| 2. | Difa' Tamaya Maulidina Adz dzikro | H1H024019 | Anggota |
| 3. | Kaira Meilasya Nayada | H1H024020 | Anggota |
| 4. | Nursyafika | H1H024023 | Anggota |


## Deskripsi Proyek

Smart Product Counter merupakan sistem penghitung dan pemantau jumlah stok barang berbasis Internet of Things (IoT). Sistem menggunakan mikrokontroler ESP8266 sebagai pusat pengendali dan sensor ultrasonik HC-SR04 untuk mendeteksi keberadaan objek/barang. Jumlah barang yang terdeteksi akan dihitung secara otomatis, ditampilkan melalui LCD 16×2, serta dikirimkan melalui komunikasi MQTT.

Sistem dirancang dengan target penghitungan sebanyak 10 barang dan batas deteksi sensor sebesar 15 cm. Pengguna dapat mengaktifkan atau menghentikan proses melalui tombol START/STOP dan mengembalikan hitungan ke kondisi awal melalui tombol RESET. Ketika target tercapai, sistem menghentikan monitoring, menyalakan LED indikator target, menampilkan status pada LCD, dan membunyikan buzzer.

Komunikasi IoT menggunakan jaringan WiFi dan broker MQTT publik HiveMQ. ESP8266 mengirimkan data jumlah stok dan status sistem, serta dapat menerima perintah START, STOP, dan RESET melalui topic MQTT yang telah ditentukan.

