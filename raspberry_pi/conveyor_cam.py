#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conveyor_cam.py - Smart Conveyor Control & Traceability System (Raspberry Pi)

Perbaikan utama dibanding versi sebelumnya:
  1. Anti false-positive sabuk kosong
     - ROI dipersempit sehingga dinding/rel logam perak (x > 65%) tidak ikut terbaca.
     - Referensi sabuk kosong = median 25 frame + peta noise per-piksel (std) -> ambang adaptif.
     - Kompensasi kecerahan global (auto-exposure) dihitung dari piksel latar saja.
     - Pemrosesan di resolusi 50% + blur kuat + morfologi OPEN/CLOSE.
     - Kontur disaring: luas, sisi minimum, fill ratio, dan kontras rata-rata.
     - Objek baru baru boleh memicu scan jika: stabil >= N frame, >= durasi minimum,
       dan benar-benar BERGERAK (bukan artefak statis). Artefak statis diserap ke background.
     - Cooldown setelah motor menyala/lanjut (getaran start tidak memicu deteksi).
     - Background di-update pelan secara terus-menerus (kecuali area objek).
  2. Garansi 1 barang = 1x scan
     - Pelacakan objek dengan prediksi posisi; fragmen kontur milik barang yang sudah
       selesai (DONE_OK / DONE_FAIL) diserap ke barang itu, bukan jadi barang baru.
     - Exit-zone lock: scan berikutnya diblokir sampai barang selesai benar-benar
       meninggalkan zona tengah. Barang selesai TIDAK pernah kedaluwarsa selama masih terlihat.

Topik & payload MQTT sama persis dengan spesifikasi proyek.
"""

import os
import sys
import argparse
import cv2
import time
import json
import math
import queue
import threading
import numpy as np
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pyzbar.pyzbar import decode
import paho.mqtt.client as mqtt

# =====================================================
# KONFIGURASI MQTT, KAMERA & STREAM PREVIEW
# =====================================================
BROKER = "localhost"
PORT = 1883
STREAM_PORT = 5050

TOPIC_KONTROL = "kel9_iot/conveyor/kontrol"
TOPIC_STATUS = "kel9_iot/conveyor/status"
TOPIC_KODE = "kel9_iot/conveyor/kode"
TOPIC_JUMLAH = "kel9_iot/conveyor/jumlah"
TOPIC_DATA = "kel9_iot/conveyor/data"
TOPIC_RESET = "kel9_iot/conveyor/reset"

# --- Logika scan ---
WAKTU_BERHENTI_SCAN = 5.0     # Berhenti maksimal 5 detik untuk scan, lalu otomatis lanjut
SCAN_HILANG_MAX = 1.0         # Objek yang sedang di-scan hilang > 1 dtk = alarm palsu (tidak dihitung)
GRACE_RESTART = 1.0           # Cooldown deteksi setelah motor start/lanjut (getaran awal)

# --- Filter objek (koordinat frame penuh 640x480) ---
AMBANG_AREA_MIN = 3000        # Luas minimum objek (px^2)
MIN_SISI_OBJEK = 28           # Sisi terpendek bounding box minimum (px)
MIN_FILL_RATIO = 0.25         # Luas kontur / luas bounding box minimum
MIN_FRAME_STABIL = 3          # Frame berturut-turut minimum sebelum objek dianggap nyata
MIN_DURASI_STABIL = 0.12      # Umur minimum objek (detik) sebelum boleh memicu scan
MIN_JARAK_GERAK = 12          # Objek harus bergeser minimal sekian px (bukan artefak statis)
ARTEFAK_STATIS_DETIK = 6.0    # Objek NEW diam > ini saat motor jalan = artefak, diserap ke background

# --- Pengurangan background ---
SKALA = 0.5                   # Pemrosesan di 50% resolusi ROI (lebih cepat & lebih halus)
BASE_THR = 28.0               # Ambang dasar selisih intensitas
K_STD = 3.0                   # Pengali std per-piksel hasil kalibrasi
THR_MAX = 70.0                # Batas atas ambang adaptif
KONTRAS_MIN = 36.0            # Rata-rata selisih di dalam kontur minimum
DELTA_LUM_MAX = 60.0          # Batas kompensasi auto-exposure
ALPHA_JALAN = 0.04            # Kecepatan adaptasi background saat sabuk jalan
ALPHA_DIAM = 0.01             # Kecepatan adaptasi background saat sabuk diam
RASIO_PERUBAHAN_GLOBAL = 0.55 # Rasio piksel berubah yang dianggap perubahan cahaya global
FRAME_REBASELINE = 8          # Berapa frame berturut-turut sebelum re-baseline paksa

# --- Pelacakan & exit-zone lock ---
JARAK_MATCH_NEW = 135.0
JARAK_MATCH_DONE = 100.0
JARAK_ABAIKAN = 75            # Deteksi baru sedekat ini dari barang selesai/scanning diabaikan (fragmen)
NEW_HILANG_MAX = 0.5          # Objek NEW tak terlihat > ini dihapus
DONE_KELUAR_TEPI = 0.7        # Barang selesai hilang di tepi ROI -> dianggap keluar setelah ini
DONE_HILANG_TENGAH = 3.0      # Barang selesai hilang di tengah (flicker) -> ditahan selama ini
LOCK_KOSONG_MIN = 0.8         # Zona harus bebas barang selesai selama ini agar lock lepas
LOCK_MAKS = 60.0              # Pengaman: lock dilepas paksa setelah ini

PAD_STATUS = {"NEW": 25, "SCANNING": 50, "DONE_OK": 55, "DONE_FAIL": 55}
PRIORITAS = {"SCANNING": 0, "DONE_OK": 1, "DONE_FAIL": 1, "NEW": 2}
STATUS_SELESAI = ("DONE_OK", "DONE_FAIL")
JUMLAH_MODE_DECODE = 5

# =====================================================
# STATE BERSAMA ANTAR THREAD
# =====================================================
shared = {"jumlah": 0}
cmd_queue = queue.Queue()          # Perintah dari callback MQTT -> loop utama (thread-safe)
tracked_objects = {}

latest_jpeg = None
latest_id = 0
frame_lock = threading.Lock()


def kirim_ke_stream(img):
    global latest_jpeg, latest_id
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if ok:
        with frame_lock:
            latest_jpeg = buf.tobytes()
            latest_id += 1


# =====================================================
# SERVER LIVE PREVIEW KAMERA (MJPEG STREAM KE DASHBOARD)
# =====================================================
class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = (
                "<html><body style='margin:0;background:#090d16;display:flex;"
                "justify-content:center;align-items:center;height:100vh'>"
                "<img src='/stream' style='width:100%;height:100%;object-fit:contain'/>"
                "</body></html>"
            )
            self.wfile.write(html.encode())
        elif self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            last_id = -1
            try:
                while True:
                    with frame_lock:
                        jpg = latest_jpeg
                        fid = latest_id
                    if jpg is not None and fid != last_id:
                        self.wfile.write(
                            b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                            + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n"
                        )
                        self.wfile.flush()
                        last_id = fid
                    time.sleep(0.03)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                pass
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass


def jalankan_server_stream():
    try:
        server = ReusableThreadingHTTPServer(("0.0.0.0", STREAM_PORT), StreamHandler)
        server.serve_forever()
    except OSError as e:
        print(f"[STREAM] Gagal menjalankan server di port {STREAM_PORT}: {e}")


threading.Thread(target=jalankan_server_stream, daemon=True).start()

# =====================================================
# KONEKSI MQTT (PAHO-MQTT V2)
# =====================================================
def on_connect(client, userdata, flags, reason_code, properties):
    gagal = reason_code.is_failure if hasattr(reason_code, "is_failure") else (reason_code != 0)
    if not gagal:
        print(f"[MQTT] Terhubung ke broker ({BROKER})")
        client.subscribe([(TOPIC_RESET, 1), (TOPIC_STATUS, 1), (TOPIC_KONTROL, 1)])
        client.publish(TOPIC_JUMLAH, str(shared["jumlah"]), qos=1)
    else:
        print(f"[MQTT] Gagal terhubung, kode: {reason_code}")


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    print(f"[MQTT] Terputus dari broker ({reason_code}), mencoba menyambung ulang...")


def on_message(client, userdata, msg):
    # Callback hanya menaruh perintah ke antrean; semua perubahan state dilakukan di loop utama
    pesan = msg.payload.decode("utf-8", errors="ignore").strip()

    if msg.topic == TOPIC_RESET:
        if pesan == "RESET":
            cmd_queue.put(("RESET", None))
    elif msg.topic == TOPIC_KONTROL:
        if pesan in ("ON", "OFF"):
            cmd_queue.put(("KONTROL", pesan))
    elif msg.topic == TOPIC_STATUS:
        try:
            data = json.loads(pesan)
            if isinstance(data, dict):
                cmd_queue.put(("STATUS", data))
        except json.JSONDecodeError:
            pass


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.reconnect_delay_set(min_delay=1, max_delay=10)
client.connect_async(BROKER, PORT, 60)
client.loop_start()

# =====================================================
# DETEKSI OTOMATIS USB WEBCAM
# =====================================================
cap = None
frame_contoh = None

for idx in range(10):
    dev_path = f"/dev/video{idx}"
    if not os.path.exists(dev_path):
        continue

    temp_cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
    if not temp_cap.isOpened():
        temp_cap = cv2.VideoCapture(idx)

    if temp_cap.isOpened():
        temp_cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
        temp_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        temp_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        temp_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        ret_test, frm_test = temp_cap.read()
        if ret_test and frm_test is not None and frm_test.size > 0:
            cap = temp_cap
            frame_contoh = frm_test
            print(f"[KAMERA] Aktif di {dev_path} ({frm_test.shape[1]}x{frm_test.shape[0]})")
            break

    temp_cap.release()

if cap is None or not cap.isOpened():
    print("[ERROR] USB Webcam tidak dapat dibuka di /dev/video0..9!")
    sys.exit(1)

# =====================================================
# GEOMETRI ROI, ZONA TENGAH & SKALA PEMROSESAN
# =====================================================
h, w = frame_contoh.shape[:2]

# ROI murni di atas sabuk hitam. Sisi kanan (x > 65%) adalah dinding/rel logam perak -> dikeluarkan.
# Atur di sini (fraksi lebar/tinggi frame) ATAU lewat argumen tanpa edit kode:
#   python3 conveyor_cam.py --grid                       (penggaris 0.1-0.9 di preview)
#   python3 conveyor_cam.py --roi 0.19,0.62,0.04,0.96 --zona 0.20,0.61,0.10,0.90
# Format: x1,x2,y1,y2. ROI = batas sabuk hitam (tanpa dinding/rel). Zona HARUS di dalam ROI.
ROI_X1, ROI_X2, ROI_Y1, ROI_Y2 = 0.19, 0.62, 0.04, 0.96
ZONA_X1, ZONA_X2, ZONA_Y1, ZONA_Y2 = 0.20, 0.61, 0.10, 0.90

_parser = argparse.ArgumentParser(description="Smart Conveyor - kamera & scanner")
_parser.add_argument("--roi", default=None, help="x1,x2,y1,y2 (fraksi 0-1)")
_parser.add_argument("--zona", default=None, help="x1,x2,y1,y2 (fraksi 0-1)")
_parser.add_argument("--grid", action="store_true", help="tampilkan penggaris di preview")
_parser.add_argument("--uji", action="store_true",
                     help="mode uji: barang diam/dipegang tangan tetap bisa memicu scan (tanpa syarat gerak)")
_parser.add_argument("--tes-decode", dest="tes_decode", action="store_true",
                     help="hanya tes baca barcode dari kamera (tanpa logika konveyor)")
ARGS, _ = _parser.parse_known_args()


def _baca_empat(teks, default):
    try:
        v = [float(s) for s in teks.split(",")]
        if len(v) == 4 and min(v) >= 0.0 and max(v) <= 1.0 and v[0] < v[1] and v[2] < v[3]:
            return tuple(v)
    except ValueError:
        pass
    print(f"[GEOMETRI] Argumen '{teks}' tidak valid, memakai nilai bawaan.")
    return default


if ARGS.roi:
    ROI_X1, ROI_X2, ROI_Y1, ROI_Y2 = _baca_empat(ARGS.roi, (ROI_X1, ROI_X2, ROI_Y1, ROI_Y2))
if ARGS.zona:
    ZONA_X1, ZONA_X2, ZONA_Y1, ZONA_Y2 = _baca_empat(ARGS.zona, (ZONA_X1, ZONA_X2, ZONA_Y1, ZONA_Y2))

# Zona dipaksa berada di dalam ROI
ZONA_X1, ZONA_X2 = max(ZONA_X1, ROI_X1), min(ZONA_X2, ROI_X2)
ZONA_Y1, ZONA_Y2 = max(ZONA_Y1, ROI_Y1), min(ZONA_Y2, ROI_Y2)
print(f"[GEOMETRI] ROI x={ROI_X1:.2f}-{ROI_X2:.2f} y={ROI_Y1:.2f}-{ROI_Y2:.2f} | "
      f"ZONA x={ZONA_X1:.2f}-{ZONA_X2:.2f} y={ZONA_Y1:.2f}-{ZONA_Y2:.2f}")

y1, y2 = int(h * ROI_Y1), int(h * ROI_Y2)
x1, x2 = int(w * ROI_X1), int(w * ROI_X2)
roi_h, roi_w = y2 - y1, x2 - x1

# Zona berhenti di tengah kamera (seluruhnya berada di dalam ROI)
cx1, cy1 = int(w * ZONA_X1), int(h * ZONA_Y1)
cx2, cy2 = int(w * ZONA_X2), int(h * ZONA_Y2)
ZONA_BOX = (cx1, cy1, cx2 - cx1, cy2 - cy1)
ZONA_PUSAT = ((cx1 + cx2) / 2.0, (cy1 + cy2) / 2.0)

# Resolusi kerja (diperkecil)
sw = max(16, int(roi_w * SKALA))
sh = max(16, int(roi_h * SKALA))
skala_x = roi_w / float(sw)
skala_y = roi_h / float(sh)
px_total = float(sw * sh)
area_min_kecil = AMBANG_AREA_MIN / (skala_x * skala_y)
sisi_min_kecil = MIN_SISI_OBJEK / max(skala_x, skala_y)

kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
kernel_debloom = np.ones((3, 3), np.uint8)

qr_fallback = cv2.QRCodeDetector()
clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))


def preproses_roi(gray_full):
    roi = gray_full[y1:y2, x1:x2]
    kecil = cv2.resize(roi, (sw, sh), interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(kecil, (9, 9), 0).astype(np.float32)


def tampilkan_info(frame, teks):
    img = frame.copy()
    cv2.rectangle(img, (x1, y1), (x2, y2), (100, 116, 139), 1)
    cv2.putText(img, teks, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 255, 255), 2)
    kirim_ke_stream(img)


def kalibrasi_sabuk(jumlah_frame=25):
    """Referensi sabuk kosong = median N frame. Peta std per-piksel -> ambang adaptif."""
    kumpulan = []
    for i in range(jumlah_frame):
        ok, frm = cap.read()
        if ok and frm is not None:
            kumpulan.append(preproses_roi(cv2.cvtColor(frm, cv2.COLOR_BGR2GRAY)))
            tampilkan_info(frm, f"KALIBRASI SABUK KOSONG {i + 1}/{jumlah_frame}")
        time.sleep(0.04)

    if len(kumpulan) >= 5:
        stack = np.stack(kumpulan, axis=0)
        bg = np.median(stack, axis=0).astype(np.float32)
        std = np.std(stack, axis=0).astype(np.float32)
    else:
        bg = preproses_roi(cv2.cvtColor(frame_contoh, cv2.COLOR_BGR2GRAY))
        std = np.zeros_like(bg)

    thr = np.clip(BASE_THR + K_STD * std, BASE_THR, THR_MAX).astype(np.float32)
    return bg, thr


# =====================================================
# DECODE QR / BARCODE MULTI-MODE
# =====================================================
def coba_decode(img_gray):
    try:
        hasil = decode(img_gray)
    except Exception:
        return None, None
    if hasil:
        return hasil[0].data.decode("utf-8", errors="ignore").strip(), hasil[0].type
    return None, None


def kontras_persentil(img_gray):
    p5, p95 = np.percentile(img_gray, (5, 95))
    if p95 - p5 < 15:
        return img_gray
    stretched = np.clip((img_gray.astype(np.float32) - p5) * (255.0 / (p95 - p5)), 0, 255)
    return stretched.astype(np.uint8)


def scan_multi_mode(gray_full, obj_box, mode):
    kandidat = []

    if obj_box is not None:
        bx, by, bw, bh = obj_box
        # Padding longgar: barcode sering lebih besar dari kotak objek yang terpotong ROI
        pad = 90
        ox1, oy1 = max(0, bx - pad), max(0, by - pad)
        ox2, oy2 = min(w, bx + bw + pad), min(h, by + bh + pad)
        crop_obj = gray_full[oy1:oy2, ox1:ox2]
        if crop_obj.size > 0:
            kandidat.append(crop_obj)

    kandidat.append(gray_full[cy1:cy2, cx1:cx2])
    # Cadangan terakhir: seluruh frame (barcode yang menjulur keluar ROI/zona tetap terbaca)
    kandidat.append(gray_full)

    for crop in kandidat:
        if crop is None or crop.size == 0:
            continue

        tajam_kontras = kontras_persentil(crop)
        padded = cv2.copyMakeBorder(tajam_kontras, 35, 35, 35, 35, cv2.BORDER_CONSTANT, value=255)

        # 1) Kontras persentil apa adanya
        kode, tipe = coba_decode(padded)
        if kode:
            return kode, tipe

        # 2) Resize kecil
        kecil = cv2.resize(padded, None, fx=0.55, fy=0.55, interpolation=cv2.INTER_AREA)
        kode, tipe = coba_decode(kecil)
        if kode:
            return kode, tipe

        # 3) Mode bergilir per frame
        kode, tipe = None, None
        if mode == 0:
            _, otsu = cv2.threshold(kecil, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            kode, tipe = coba_decode(otsu)
        elif mode == 1:
            tebal = cv2.erode(padded, kernel_debloom, iterations=1)
            tebal_kecil = cv2.resize(tebal, None, fx=0.55, fy=0.55, interpolation=cv2.INTER_AREA)
            kode, tipe = coba_decode(tebal_kecil)
        elif mode == 2:
            adap = cv2.adaptiveThreshold(
                clahe.apply(padded), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 41, 10
            )
            kode, tipe = coba_decode(adap)
        elif mode == 3:
            try:
                teks_qr, _, _ = qr_fallback.detectAndDecode(kecil)
            except cv2.error:
                teks_qr = ""
            if teks_qr:
                return teks_qr.strip(), "QRCODE"
        else:
            besar = cv2.resize(padded, None, fx=1.6, fy=1.6, interpolation=cv2.INTER_CUBIC)
            kode, tipe = coba_decode(besar)

        if kode:
            return kode, tipe

    return None, None


# =====================================================
# FUNGSI BANTU GEOMETRI & PELACAKAN
# =====================================================
def kotak_beririsan(a, b, pad=0):
    """Apakah kotak a beririsan dengan kotak b yang diperluas sebesar pad."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw < bx - pad or bx + bw + pad < ax or
                ay + ah < by - pad or by + bh + pad < ay)


def titik_dalam_zona(pt, margin=0):
    return (cx1 - margin) <= pt[0] <= (cx2 + margin) and (cy1 - margin) <= pt[1] <= (cy2 + margin)


def titik_dalam_zona_inti(pt):
    """Inti zona = zona yang dikecilkan 30% di tiap sisi (untuk barang besar yang selalu menyentuh tepi ROI)."""
    mx = int((cx2 - cx1) * 0.30)
    my = int((cy2 - cy1) * 0.30)
    return (cx1 + mx) <= pt[0] <= (cx2 - mx) and (cy1 + my) <= pt[1] <= (cy2 - my)


def box_utuh_di_roi(box, margin=6):
    """True jika kotak objek tidak menyentuh tepi ROI -> barang sudah masuk utuh, barcode tidak terpotong."""
    bx, by, bw, bh = box
    return (bx > x1 + margin and by > y1 + margin and
            bx + bw < x2 - margin and by + bh < y2 - margin)


def dekat_tepi_roi(box, margin=22):
    bx, by, bw, bh = box
    return (bx <= x1 + margin or by <= y1 + margin or
            bx + bw >= x2 - margin or by + bh >= y2 - margin)


def prediksi_tengah(obj, sekarang):
    dt = min(max(sekarang - obj["last_seen"], 0.0), 0.5)
    vx, vy = obj["vel"]
    cxo, cyo = obj["center"]
    return (cxo + vx * dt, cyo + vy * dt)


def kotak_prediksi(obj, sekarang):
    pcx, pcy = prediksi_tengah(obj, sekarang)
    ocx, ocy = obj["center"]
    bx, by, bw, bh = obj["box"]
    return (int(bx + pcx - ocx), int(by + pcy - ocy), bw, bh)


def terapkan_deteksi(obj, daftar_box, sekarang):
    ux0 = min(b[0] for b in daftar_box)
    uy0 = min(b[1] for b in daftar_box)
    ux1 = max(b[0] + b[2] for b in daftar_box)
    uy1 = max(b[1] + b[3] for b in daftar_box)
    box_baru = (ux0, uy0, ux1 - ux0, uy1 - uy0)
    c_baru = (ux0 + (ux1 - ux0) // 2, uy0 + (uy1 - uy0) // 2)

    dt = sekarang - obj["last_seen"]
    if dt > 0.001:
        vx = max(-300.0, min(300.0, (c_baru[0] - obj["center"][0]) / dt))
        vy = max(-300.0, min(300.0, (c_baru[1] - obj["center"][1]) / dt))
        obj["vel"] = (0.7 * obj["vel"][0] + 0.3 * vx, 0.7 * obj["vel"][1] + 0.3 * vy)

    obj["box"] = box_baru
    obj["center"] = c_baru
    obj["last_seen"] = sekarang
    obj["frames_seen"] += 1
    sx, sy = obj["spawn_center"]
    obj["jarak_maks"] = max(obj["jarak_maks"], math.hypot(c_baru[0] - sx, c_baru[1] - sy))


def perbarui_tracking(deteksi, sekarang, next_id, kunci_zona):
    """
    Pass A : serap deteksi yang beririsan dengan kotak prediksi objek (fragmen -> objek yang sama).
    Pass B : objek yang belum dapat deteksi dicocokkan ke deteksi terdekat.
    Pass C : sisa deteksi menjadi objek baru, kecuali berada dekat barang selesai/scanning
             atau berada di zona saat exit-zone lock aktif (itu fragmen, bukan barang baru).
    """
    terpakai = set()
    cocok = {}
    urutan = sorted(tracked_objects.items(), key=lambda kv: PRIORITAS[kv[1]["status"]])

    # Pass A
    for oid, obj in urutan:
        kb = kotak_prediksi(obj, sekarang)
        pad = PAD_STATUS[obj["status"]]
        for i, det in enumerate(deteksi):
            if i in terpakai:
                continue
            if kotak_beririsan(det["box"], kb, pad):
                cocok.setdefault(oid, []).append(i)
                terpakai.add(i)

    # Pass B
    for oid, obj in urutan:
        if oid in cocok:
            continue
        batas = JARAK_MATCH_NEW if obj["status"] == "NEW" else JARAK_MATCH_DONE
        pcx, pcy = prediksi_tengah(obj, sekarang)
        terbaik, jarak_terbaik = None, batas
        for i, det in enumerate(deteksi):
            if i in terpakai:
                continue
            d = math.hypot(det["center"][0] - pcx, det["center"][1] - pcy)
            if d < jarak_terbaik:
                jarak_terbaik, terbaik = d, i
        if terbaik is not None:
            cocok[oid] = [terbaik]
            terpakai.add(terbaik)

    for oid, idxs in cocok.items():
        terapkan_deteksi(tracked_objects[oid], [deteksi[i]["box"] for i in idxs], sekarang)

    # Pass C
    for i, det in enumerate(deteksi):
        if i in terpakai:
            continue

        fragmen = False
        for obj in tracked_objects.values():
            if obj["status"] in STATUS_SELESAI or obj["status"] == "SCANNING":
                if kotak_beririsan(det["box"], kotak_prediksi(obj, sekarang), JARAK_ABAIKAN):
                    fragmen = True
                    break
        if fragmen:
            continue
        if kunci_zona and titik_dalam_zona(det["center"], margin=30):
            continue

        tracked_objects[next_id] = {
            "box": det["box"],
            "center": det["center"],
            "spawn_center": det["center"],
            "spawn_time": sekarang,
            "last_seen": sekarang,
            "frames_seen": 1,
            "status": "NEW",
            "label": "BARU",
            "done_time": None,
            "vel": (0.0, 0.0),
            "jarak_maks": 0.0,
        }
        next_id += 1

    return next_id


def ambil_rpm(data_pid):
    try:
        return float(data_pid.get("rpm", 0.0))
    except (TypeError, ValueError):
        return 0.0


def publish_valid(kode, tipe, jumlah, rpm):
    waktu_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    client.publish(TOPIC_KODE, kode, qos=1)
    client.publish(TOPIC_JUMLAH, str(jumlah), qos=1)
    client.publish(TOPIC_KONTROL, "SCAN_OK", qos=1)
    client.publish(TOPIC_KONTROL, "ON", qos=1)
    payload = json.dumps({
        "uid_barcode": kode,
        "tipe_kode": tipe,
        "status_scan": "VALID",
        "jumlah": jumlah,
        "rpm_aktual": rpm,
        "waktu_scan": waktu_str
    })
    client.publish(TOPIC_DATA, payload, qos=1)
    print(f"[{waktu_str}] SCAN VALID: {kode} | Total LCD: {jumlah} -> Lanjut jalan!")


def publish_gagal(jumlah, rpm):
    waktu_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    client.publish(TOPIC_JUMLAH, str(jumlah), qos=1)
    client.publish(TOPIC_KONTROL, "SCAN_FAIL", qos=1)
    client.publish(TOPIC_KONTROL, "ON", qos=1)
    payload = json.dumps({
        "uid_barcode": "NO_BARCODE",
        "tipe_kode": "NONE",
        "status_scan": "FAILED",
        "jumlah": jumlah,
        "rpm_aktual": rpm,
        "waktu_scan": waktu_str
    })
    client.publish(TOPIC_DATA, payload, qos=1)
    print(f"[{waktu_str}] NO BARCODE (5s) | Total LCD: {jumlah} -> Konveyor otomatis lanjut!")


def alasan_belum_scan(obj, sekarang, konveyor_aktif, sedang_scanning, menunggu_keluar_zona, blok_hingga):
    """Teks singkat: kenapa objek NEW ini belum memicu scan (ditampilkan di preview)."""
    if not konveyor_aktif:
        return "KONVEYOR OFF"
    if sedang_scanning:
        return "SCAN LAIN BERJALAN"
    if menunggu_keluar_zona:
        return "KUNCI ZONA"
    if sekarang < blok_hingga:
        return "COOLDOWN"
    if obj["frames_seen"] < MIN_FRAME_STABIL:
        return f"STABIL {obj['frames_seen']}/{MIN_FRAME_STABIL}"
    if (sekarang - obj["spawn_time"]) < MIN_DURASI_STABIL:
        return "STABIL (waktu)"
    if not ARGS.uji and obj["jarak_maks"] < MIN_JARAK_GERAK:
        return f"DIAM {obj['jarak_maks']:.0f}/{MIN_JARAK_GERAK}px"
    if not titik_dalam_zona(obj["center"]):
        return "DI LUAR ZONA"
    if not box_utuh_di_roi(obj["box"]) and not titik_dalam_zona_inti(obj["center"]):
        return "MENYENTUH TEPI ROI"
    return "SIAP SCAN"


def mode_tes_decode():
    """Tes baca barcode saja: seluruh frame, semua mode decode, tanpa logika konveyor/MQTT."""
    print("[TES-DECODE] Arahkan barcode/QR ke kamera. Lihat preview di http://<ip-pi>:5050 . Ctrl+C untuk keluar.")
    modus = 0
    terakhir_teks, terakhir_waktu = "", 0.0
    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(0.03)
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            modus = (modus + 1) % JUMLAH_MODE_DECODE
            kode, tipe = scan_multi_mode(gray, None, modus)

            ketajaman = cv2.Laplacian(gray, cv2.CV_64F).var()
            terang = float(np.mean(gray))
            silau = 100.0 * float(np.count_nonzero(gray >= 250)) / gray.size

            if kode:
                terakhir_teks, terakhir_waktu = f"{tipe}: {kode}", time.time()
                print(f"[TES-DECODE] TERBACA -> {terakhir_teks}")

            preview = frame.copy()
            cv2.putText(preview, f"Tajam:{ketajaman:.0f} (>100 bagus)  Terang:{terang:.0f}  Silau:{silau:.1f}%",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            if terakhir_teks and (time.time() - terakhir_waktu) < 3.0:
                cv2.putText(preview, "TERBACA: " + terakhir_teks[:40], (10, 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            else:
                cv2.putText(preview, "BELUM TERBACA", (10, 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            kirim_ke_stream(preview)
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n[TES-DECODE] Selesai.")
    finally:
        cap.release()
        client.loop_stop()
        client.disconnect()


# =====================================================
# LOOP UTAMA DETEKSI & PELACAKAN MULTI-OBJEK
# =====================================================
def main():
    if ARGS.tes_decode:
        mode_tes_decode()
        return

    print("[KALIBRASI] Mengambil referensi sabuk kosong (median 25 frame)...")
    bg_ref, thr_map = kalibrasi_sabuk()
    print("[SISTEM] Siap! Klik Jalankan (ON) di dashboard untuk memulai.")

    next_obj_id = 1
    data_pid = {"status": "OFF", "rpm": 0.0, "setpoint": 100.0, "pwm": 0}

    konveyor_aktif = False
    sedang_scanning = False
    scanning_obj_id = None
    waktu_mulai_scan = 0.0
    menunggu_keluar_zona = False
    waktu_zona_kosong = None
    waktu_selesai_scan = 0.0
    waktu_jalan_sejak = 0.0
    blok_trigger_hingga = 0.0
    siklus_scan = 0

    bg_mask_prev = None
    hitung_global = 0
    gagal_baca = 0
    fps = 10.0
    waktu_frame_prev = 0.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                gagal_baca += 1
                if gagal_baca == 100:
                    print("[KAMERA] Peringatan: frame gagal dibaca berulang kali, cek koneksi webcam!")
                time.sleep(0.03)
                continue
            gagal_baca = 0

            sekarang = time.time()
            if waktu_frame_prev > 0:
                dt_frame = sekarang - waktu_frame_prev
                if dt_frame > 0:
                    fps = 0.9 * fps + 0.1 * (1.0 / dt_frame)
            waktu_frame_prev = sekarang

            # ---------- Proses perintah dari MQTT ----------
            reset_diminta = False
            while True:
                try:
                    perintah, isi = cmd_queue.get_nowait()
                except queue.Empty:
                    break

                if perintah == "RESET":
                    reset_diminta = True

                elif perintah == "KONTROL":
                    if isi == "ON":
                        if not konveyor_aktif:
                            konveyor_aktif = True
                            waktu_jalan_sejak = sekarang
                            blok_trigger_hingga = sekarang + GRACE_RESTART
                            print("[KONTROL] Konveyor dijalankan (ON).")
                    elif isi == "OFF":
                        konveyor_aktif = False
                        if sedang_scanning:
                            # Scan dibatalkan manual: objek kembali NEW (belum dihitung)
                            obj_batal = tracked_objects.get(scanning_obj_id)
                            if obj_batal is not None:
                                obj_batal["status"] = "NEW"
                                obj_batal["label"] = "BARU"
                        sedang_scanning = False
                        scanning_obj_id = None
                        print("[KONTROL] Konveyor dihentikan (OFF).")

                elif perintah == "STATUS":
                    data_pid = isi
                    sistem = str(data_pid.get("sistem", "")).upper()
                    if sistem == "ON":
                        if not konveyor_aktif:
                            konveyor_aktif = True
                            waktu_jalan_sejak = sekarang
                            blok_trigger_hingga = sekarang + GRACE_RESTART
                    elif sistem == "OFF" and not sedang_scanning:
                        konveyor_aktif = False

            if reset_diminta:
                sedang_scanning_sebelum = sedang_scanning
                shared["jumlah"] = 0
                tracked_objects.clear()
                next_obj_id = 1
                sedang_scanning = False
                scanning_obj_id = None
                menunggu_keluar_zona = False
                waktu_zona_kosong = None
                bg_mask_prev = None
                hitung_global = 0
                client.publish(TOPIC_JUMLAH, "0", qos=1)
                if sedang_scanning_sebelum and konveyor_aktif:
                    client.publish(TOPIC_KONTROL, "ON", qos=1)
                print("[SISTEM] Hitungan barang di-reset! Kalibrasi ulang sabuk kosong...")
                bg_ref, thr_map = kalibrasi_sabuk()
                blok_trigger_hingga = time.time() + GRACE_RESTART
                waktu_jalan_sejak = time.time()
                print("[SISTEM] Kalibrasi ulang selesai.")
                continue

            gray_full = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            roi_blur = preproses_roi(gray_full)

            # ---------- Kompensasi kecerahan global (auto-exposure) ----------
            if bg_mask_prev is not None and cv2.countNonZero(bg_mask_prev) >= 0.30 * px_total:
                sel_latar = bg_mask_prev > 0
            else:
                sel_latar = np.ones((sh, sw), dtype=bool)

            # Gain (perkalian): area terang bergeser lebih besar daripada area gelap saat exposure berubah
            sel_gain = sel_latar & (bg_ref > 12.0)
            if np.count_nonzero(sel_gain) > 50:
                gain = float(np.median(roi_blur[sel_gain] / bg_ref[sel_gain]))
            else:
                gain = 1.0
            gain = max(0.6, min(1.6, gain))

            # Offset (penjumlahan) sisa setelah gain
            bg_komp = bg_ref * gain
            delta_lum = float(np.median((roi_blur - bg_komp)[sel_latar]))
            delta_lum = max(-DELTA_LUM_MAX, min(DELTA_LUM_MAX, delta_lum))
            bg_komp = bg_komp + delta_lum

            selisih = np.abs(roi_blur - bg_komp)
            sumber_norm = (roi_blur - delta_lum) / gain   # frame saat ini dinormalkan ke exposure referensi
            fg_mask = (selisih > thr_map).astype(np.uint8) * 255
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel_open)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel_close)
            rasio_perubahan = cv2.countNonZero(fg_mask) / px_total

            # ---------- Ekstraksi kontur kandidat objek ----------
            deteksi_saat_ini = []
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in contours:
                area = cv2.contourArea(c)
                if area < area_min_kecil:
                    continue
                bx, by, bw, bh = cv2.boundingRect(c)
                if min(bw, bh) < sisi_min_kecil:
                    continue
                # Tolak kotak raksasa seukuran seluruh sabuk (perubahan cahaya global)
                if bw > (sw * 0.85) and bh > (sh * 0.82) and not ARGS.uji:
                    continue
                if area / float(bw * bh) < MIN_FILL_RATIO:
                    continue
                mask_kontur = np.zeros((sh, sw), dtype=np.uint8)
                cv2.drawContours(mask_kontur, [c], -1, 255, -1)
                if cv2.mean(selisih, mask=mask_kontur)[0] < KONTRAS_MIN:
                    continue

                fx = x1 + int(bx * skala_x)
                fy = y1 + int(by * skala_y)
                fw = int(bw * skala_x)
                fh = int(bh * skala_y)
                deteksi_saat_ini.append({
                    "box": (fx, fy, fw, fh),
                    "center": (fx + fw // 2, fy + fh // 2)
                })

            # ---------- Pelacakan ----------
            next_obj_id = perbarui_tracking(deteksi_saat_ini, sekarang, next_obj_id, menunggu_keluar_zona)

            # ---------- Log pelacakan (untuk diagnosa) ----------
            for oid, obj in tracked_objects.items():
                if obj["status"] == "NEW" and obj["frames_seen"] >= MIN_FRAME_STABIL:
                    obj["alasan_terakhir"] = alasan_belum_scan(
                        obj, sekarang, konveyor_aktif, sedang_scanning, menunggu_keluar_zona, blok_trigger_hingga)
                    if not obj.get("dilog"):
                        obj["dilog"] = True
                        print(f"[TRACK] #{oid} terkonfirmasi box={obj['box']} pusat={obj['center']} "
                              f"fps={fps:.0f} | {obj['alasan_terakhir']}")

            # ---------- Kedaluwarsa objek ----------
            for oid in list(tracked_objects.keys()):
                obj = tracked_objects[oid]
                if obj["status"] == "SCANNING":
                    continue
                tak_terlihat = sekarang - obj["last_seen"]
                if obj["status"] in STATUS_SELESAI:
                    batas = DONE_KELUAR_TEPI if dekat_tepi_roi(obj["box"]) else DONE_HILANG_TENGAH
                else:
                    batas = NEW_HILANG_MAX
                if tak_terlihat > batas:
                    if obj["status"] == "NEW" and obj.get("dilog"):
                        print(f"[TRACK] #{oid} HILANG tanpa di-scan | alasan terakhir: {obj.get('alasan_terakhir')} "
                              f"| gerak maks={obj['jarak_maks']:.0f}px | umur={sekarang - obj['spawn_time']:.2f}s "
                              f"| posisi terakhir={obj['center']}")
                    del tracked_objects[oid]

            # ---------- Serap artefak statis (bukan barang) ke background ----------
            if (not ARGS.uji and konveyor_aktif and not sedang_scanning
                    and (sekarang - waktu_jalan_sejak) > ARTEFAK_STATIS_DETIK):
                for oid in list(tracked_objects.keys()):
                    obj = tracked_objects[oid]
                    if (obj["status"] == "NEW"
                            and (sekarang - obj["spawn_time"]) > ARTEFAK_STATIS_DETIK
                            and obj["jarak_maks"] < MIN_JARAK_GERAK):
                        bx, by, bw, bh = obj["box"]
                        sx0 = max(0, int((bx - x1) / skala_x) - 4)
                        sy0 = max(0, int((by - y1) / skala_y) - 4)
                        sx1 = min(sw, int((bx + bw - x1) / skala_x) + 5)
                        sy1 = min(sh, int((by + bh - y1) / skala_y) + 5)
                        if sx1 > sx0 and sy1 > sy0:
                            bg_ref[sy0:sy1, sx0:sx1] = sumber_norm[sy0:sy1, sx0:sx1]
                        del tracked_objects[oid]

            # ---------- Update background (self-healing) ----------
            ada_objek_nyata = any(o["frames_seen"] >= MIN_FRAME_STABIL for o in tracked_objects.values())
            if (rasio_perubahan > RASIO_PERUBAHAN_GLOBAL and not sedang_scanning
                    and not ada_objek_nyata and not ARGS.uji):
                hitung_global += 1
            else:
                hitung_global = 0

            mask_bg = cv2.bitwise_not(cv2.dilate(fg_mask, kernel_dilate))
            for obj in tracked_objects.values():
                bx, by, bw, bh = obj["box"]
                sx0 = max(0, int((bx - x1) / skala_x) - 6)
                sy0 = max(0, int((by - y1) / skala_y) - 6)
                sx1 = min(sw, int((bx + bw - x1) / skala_x) + 7)
                sy1 = min(sh, int((by + bh - y1) / skala_y) + 7)
                if sx1 > sx0 and sy1 > sy0:
                    mask_bg[sy0:sy1, sx0:sx1] = 0
            bg_mask_prev = mask_bg

            if hitung_global >= FRAME_REBASELINE:
                # Perubahan cahaya global besar -> adaptasi cepat ke seluruh ROI
                cv2.accumulateWeighted(roi_blur, bg_ref, 0.30)
            elif not sedang_scanning:
                alpha = ALPHA_JALAN if konveyor_aktif else ALPHA_DIAM
                cv2.accumulateWeighted(sumber_norm, bg_ref, alpha, mask_bg)

            # ---------- Exit-zone lock ----------
            if menunggu_keluar_zona:
                ada_selesai_di_zona = any(
                    o["status"] in STATUS_SELESAI and kotak_beririsan(o["box"], ZONA_BOX, 10)
                    for o in tracked_objects.values()
                )
                if ada_selesai_di_zona:
                    waktu_zona_kosong = None
                else:
                    if waktu_zona_kosong is None:
                        waktu_zona_kosong = sekarang
                    elif (sekarang - waktu_zona_kosong) >= LOCK_KOSONG_MIN:
                        menunggu_keluar_zona = False
                        waktu_zona_kosong = None
                if menunggu_keluar_zona and (sekarang - waktu_selesai_scan) > LOCK_MAKS:
                    menunggu_keluar_zona = False
                    waktu_zona_kosong = None

            # ---------- Pemicu scan: barang NEW yang nyata tiba di zona tengah ----------
            if (konveyor_aktif and not sedang_scanning and not menunggu_keluar_zona
                    and sekarang >= blok_trigger_hingga):
                kandidat_id, jarak_terbaik = None, 1e9
                for oid, obj in tracked_objects.items():
                    if obj["status"] != "NEW":
                        continue
                    if obj["frames_seen"] < MIN_FRAME_STABIL:
                        continue
                    if (sekarang - obj["spawn_time"]) < MIN_DURASI_STABIL:
                        continue
                    if not ARGS.uji and obj["jarak_maks"] < MIN_JARAK_GERAK:
                        continue
                    if not titik_dalam_zona(obj["center"]):
                        continue
                    # Berhenti hanya saat barang sudah masuk UTUH ke ROI (barcode tidak terpotong tepi).
                    # Barang besar yang selalu menyentuh tepi ROI berhenti saat pusatnya di inti zona.
                    if not box_utuh_di_roi(obj["box"]) and not titik_dalam_zona_inti(obj["center"]):
                        continue
                    jarak = math.hypot(obj["center"][0] - ZONA_PUSAT[0], obj["center"][1] - ZONA_PUSAT[1])
                    if jarak < jarak_terbaik:
                        jarak_terbaik, kandidat_id = jarak, oid

                if kandidat_id is not None:
                    obj = tracked_objects[kandidat_id]
                    obj["status"] = "SCANNING"
                    obj["label"] = "SCANNING"
                    sedang_scanning = True
                    scanning_obj_id = kandidat_id
                    waktu_mulai_scan = sekarang
                    siklus_scan = 0
                    client.publish(TOPIC_KONTROL, "SCANNING", qos=1)
                    print(f"[DETEKSI] Objek #{kandidat_id} tiba di tengah lensa -> Berhenti maksimal 5 detik...")

            # ---------- Proses scan aktif ----------
            teks_status = None
            warna_status = (203, 213, 225)

            if sedang_scanning:
                obj_aktif = tracked_objects.get(scanning_obj_id)

                if obj_aktif is None or (sekarang - obj_aktif["last_seen"]) > SCAN_HILANG_MAX:
                    # Objek lenyap saat scanning -> alarm palsu: lanjut jalan, TIDAK dihitung
                    print(f"[DETEKSI] Objek #{scanning_obj_id} hilang saat scanning "
                          f"({sekarang - waktu_mulai_scan:.1f}s setelah berhenti) -> alarm palsu, konveyor lanjut tanpa hitung.")
                    if obj_aktif is not None:
                        del tracked_objects[scanning_obj_id]
                    sedang_scanning = False
                    scanning_obj_id = None
                    blok_trigger_hingga = sekarang + GRACE_RESTART
                    waktu_jalan_sejak = sekarang
                    if konveyor_aktif:
                        client.publish(TOPIC_KONTROL, "ON", qos=1)
                else:
                    sisa_waktu = max(0.0, WAKTU_BERHENTI_SCAN - (sekarang - waktu_mulai_scan))
                    teks_status = f"SCAN OBJEK #{scanning_obj_id} ({sisa_waktu:.1f}s)..."
                    warna_status = (0, 255, 255)

                    siklus_scan = (siklus_scan + 1) % JUMLAH_MODE_DECODE
                    isi_kode, tipe_kode = scan_multi_mode(gray_full, obj_aktif["box"], siklus_scan)

                    if isi_kode:
                        obj_aktif["status"] = "DONE_OK"
                        obj_aktif["label"] = f"OK: {isi_kode}"
                        obj_aktif["done_time"] = sekarang
                        sedang_scanning = False
                        scanning_obj_id = None
                        waktu_selesai_scan = sekarang
                        menunggu_keluar_zona = True
                        waktu_zona_kosong = None
                        blok_trigger_hingga = sekarang + GRACE_RESTART
                        waktu_jalan_sejak = sekarang

                        shared["jumlah"] += 1
                        publish_valid(isi_kode, tipe_kode, shared["jumlah"], ambil_rpm(data_pid))

                    elif (sekarang - waktu_mulai_scan) >= WAKTU_BERHENTI_SCAN:
                        obj_aktif["status"] = "DONE_FAIL"
                        obj_aktif["label"] = "NO BARCODE"
                        obj_aktif["done_time"] = sekarang
                        sedang_scanning = False
                        scanning_obj_id = None
                        waktu_selesai_scan = sekarang
                        menunggu_keluar_zona = True
                        waktu_zona_kosong = None
                        blok_trigger_hingga = sekarang + GRACE_RESTART
                        waktu_jalan_sejak = sekarang

                        shared["jumlah"] += 1
                        publish_gagal(shared["jumlah"], ambil_rpm(data_pid))

            # ---------- Visualisasi preview ----------
            preview = frame.copy()
            cv2.rectangle(preview, (x1, y1), (x2, y2), (100, 116, 139), 1)

            if ARGS.grid:
                for k in range(1, 10):
                    gx, gy = int(w * k / 10.0), int(h * k / 10.0)
                    cv2.line(preview, (gx, 0), (gx, h), (90, 90, 90), 1)
                    cv2.line(preview, (0, gy), (w, gy), (90, 90, 90), 1)
                    cv2.putText(preview, f"{k / 10.0:.1f}", (gx + 2, h - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (230, 230, 230), 1)
                    cv2.putText(preview, f"{k / 10.0:.1f}", (2, gy - 3),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (230, 230, 230), 1)

            if not konveyor_aktif:
                warna_zona = (148, 163, 184)
            elif sedang_scanning:
                warna_zona = (0, 255, 255)
            elif menunggu_keluar_zona:
                warna_zona = (0, 255, 0)
            else:
                warna_zona = (56, 189, 248)
            cv2.rectangle(preview, (cx1, cy1), (cx2, cy2), warna_zona, 3)

            objek_terkonfirmasi = 0
            for oid, obj in tracked_objects.items():
                fx, fy, bw, bh = obj["box"]
                ocx, ocy = obj["center"]
                st = obj["status"]

                if st == "NEW" and obj["frames_seen"] < MIN_FRAME_STABIL:
                    # Kandidat belum stabil: gambar tipis abu-abu
                    cv2.rectangle(preview, (fx, fy), (fx + bw, fy + bh), (120, 120, 120), 1)
                    cv2.putText(preview, alasan_belum_scan(obj, sekarang, konveyor_aktif, sedang_scanning,
                                                           menunggu_keluar_zona, blok_trigger_hingga),
                                (fx, min(h - 6, fy + bh + 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
                    continue

                objek_terkonfirmasi += 1
                if st == "SCANNING":
                    warna_obj = (0, 255, 255)
                elif st == "DONE_OK":
                    warna_obj = (0, 255, 0)
                elif st == "DONE_FAIL":
                    warna_obj = (0, 165, 255)
                else:
                    warna_obj = (255, 165, 0)

                cv2.rectangle(preview, (fx, fy), (fx + bw, fy + bh), warna_obj, 2)
                cv2.circle(preview, (ocx, ocy), 6, (0, 0, 255), -1)
                cv2.putText(preview, f"#{oid} {obj['label']}", (fx, max(20, fy - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.52, warna_obj, 2)
                if st == "NEW":
                    cv2.putText(preview, alasan_belum_scan(obj, sekarang, konveyor_aktif, sedang_scanning,
                                                           menunggu_keluar_zona, blok_trigger_hingga),
                                (fx, min(h - 6, fy + bh + 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

            if teks_status is None:
                if not konveyor_aktif:
                    teks_status = "KONVEYOR OFF - KLIK JALANKAN (ON) DI WEB"
                    warna_status = (248, 113, 113)
                elif menunggu_keluar_zona:
                    teks_status = "BARANG SELESAI -> KELUAR ZONA SCAN"
                    warna_status = (0, 255, 0)
                elif objek_terkonfirmasi > 0:
                    teks_status = f"KONVEYOR JALAN ({objek_terkonfirmasi} OBJEK)"
                    warna_status = (0, 255, 0)
                else:
                    teks_status = "KONVEYOR JALAN - MENUNGGU BARANG"
                    warna_status = (203, 213, 225)

            cv2.putText(preview, teks_status, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.62, warna_status, 2)
            cv2.putText(preview, f"TOTAL: {shared['jumlah']}   RPM: {ambil_rpm(data_pid):.0f}   FPS: {fps:.0f}",
                        (15, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            kirim_ke_stream(preview)
            time.sleep(0.005)

    except KeyboardInterrupt:
        print("\n[SISTEM] Program dihentikan.")
    finally:
        client.publish(TOPIC_KONTROL, "OFF", qos=1)
        cap.release()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()