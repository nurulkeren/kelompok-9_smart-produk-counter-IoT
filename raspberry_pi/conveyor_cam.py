import os
import cv2
import time
import json
import math
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
TOPIC_STATUS  = "kel9_iot/conveyor/status"
TOPIC_KODE    = "kel9_iot/conveyor/kode"
TOPIC_JUMLAH  = "kel9_iot/conveyor/jumlah"
TOPIC_DATA    = "kel9_iot/conveyor/data"
TOPIC_RESET   = "kel9_iot/conveyor/reset"

WAKTU_BERHENTI_SCAN = 5.0   # Berhenti maksimal 5 detik untuk scan, lalu otomatis lanjut
AMBANG_AREA_MIN     = 3500  # Minimal luas tiap objek fisik (piksel)

jumlah_barang = 0
kode_terscan_set = set()
minta_kalibrasi_ulang = False

konveyor_aktif = False
sedang_scanning = False
scanning_obj_id = None
waktu_mulai_scan = 0.0
siklus_scan = 0

tracked_objects = {}
next_obj_id = 1

data_pid = {"status": "OFF", "rpm": 0.0, "setpoint": 100.0, "pwm": 0}
latest_jpeg = None
frame_lock = threading.Lock()

# =====================================================
# SERVER LIVE PREVIEW KAMERA (MJPEG STREAM KE DASHBOARD)
# =====================================================
class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

class StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = (
                "<html><body style='margin:0;background:#090d16;display:flex;justify-content:center;align-items:center;height:100vh'>"
                "<img src='/stream' style='width:100%;height:100%;object-fit:contain'/>"
                "</body></html>"
            )
            self.wfile.write(html.encode())
        elif self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            try:
                while True:
                    with frame_lock:
                        jpg = latest_jpeg
                    if jpg is not None:
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n")
                    time.sleep(0.05)
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass

threading.Thread(
    target=lambda: ReusableThreadingHTTPServer(("0.0.0.0", STREAM_PORT), StreamHandler).serve_forever(),
    daemon=True
).start()

# =====================================================
# KONEKSI MQTT (PAHO-MQTT V2)
# =====================================================
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"[MQTT] Terhubung ke broker ({BROKER})")
        client.subscribe(TOPIC_RESET)
        client.subscribe(TOPIC_STATUS)
        client.subscribe(TOPIC_KONTROL)
        client.publish(TOPIC_JUMLAH, str(jumlah_barang), qos=1)
    else:
        print(f"[MQTT] Gagal terhubung, kode: {reason_code}")

def on_message(client, userdata, msg):
    global jumlah_barang, kode_terscan_set, data_pid, konveyor_aktif
    global sedang_scanning, scanning_obj_id, tracked_objects, minta_kalibrasi_ulang

    pesan = msg.payload.decode().strip()

    if msg.topic == TOPIC_RESET and pesan == "RESET":
        jumlah_barang = 0
        kode_terscan_set.clear()
        tracked_objects.clear()
        sedang_scanning = False
        scanning_obj_id = None
        minta_kalibrasi_ulang = True
        client.publish(TOPIC_JUMLAH, "0", qos=1)
        print("[SISTEM] Hitungan barang, memori anti-duplikat & kalibrasi kamera di-reset!")

    elif msg.topic == TOPIC_KONTROL:
        if pesan == "ON":
            konveyor_aktif = True
            print("[KONTROL] Konveyor dijalankan (ON).")
        elif pesan == "OFF":
            konveyor_aktif = False
            sedang_scanning = False
            scanning_obj_id = None
            print("[KONTROL] Konveyor dihentikan (OFF).")

    elif msg.topic == TOPIC_STATUS:
        try:
            data_pid = json.loads(pesan)
            if data_pid.get("sistem") == "ON":
                konveyor_aktif = True
            elif data_pid.get("sistem") == "OFF" and not sedang_scanning:
                konveyor_aktif = False
        except json.JSONDecodeError:
            pass

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
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
    exit(1)

# =====================================================
# KALIBRASI REFERENSI SABUK KOSONG & ZONA TENGAH
# =====================================================
h, w = frame_contoh.shape[:2]

y1, y2 = int(h * 0.05), int(h * 0.95)
x1, x2 = int(w * 0.14), int(w * 0.86)  # Fokus di area sabuk hitam (hindari rel logam kiri/kanan)
roi_h, roi_w = y2 - y1, x2 - x1
luas_maks_objek = roi_h * roi_w * 0.78   # Tolak perubahan cahaya global seukuran seluruh sabuk

# Zona berhenti di tengah kamera
cx1, cy1 = int(w * 0.20), int(h * 0.28)
cx2, cy2 = int(w * 0.80), int(h * 0.72)

def ambil_referensi_sabuk():
    kumpulan = []
    for _ in range(25):
        ret_b, frm_b = cap.read()
        if ret_b and frm_b is not None:
            g = cv2.cvtColor(frm_b[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
            kumpulan.append(cv2.GaussianBlur(g, (15, 15), 0).astype(np.float32))
        time.sleep(0.04)
    if kumpulan:
        return np.median(kumpulan, axis=0).astype(np.uint8)
    return np.zeros((roi_h, roi_w), dtype=np.uint8)

print("[KALIBRASI] Mengambil referensi sabuk kosong...")
bg_ref = ambil_referensi_sabuk()

qr_fallback = cv2.QRCodeDetector()
clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
kernel_open = np.ones((7, 7), np.uint8)
kernel_debloom = np.ones((3, 3), np.uint8)

def coba_decode(img_gray):
    hasil = decode(img_gray)
    if hasil:
        return hasil[0].data.decode("utf-8").strip(), hasil[0].type
    return None, None

def kontras_persentil(img_gray):
    p5, p95 = np.percentile(img_gray, (5, 95))
    if p95 - p5 < 15:
        return img_gray
    stretched = np.clip((img_gray.astype(np.float32) - p5) * (255.0 / (p95 - p5)), 0, 255)
    return stretched.astype(np.uint8)

def scan_multi_mode(gray_full, obj_box, mode):
    kandidat = []

    # 1. Potongan area objek yang sedang berhenti
    if obj_box is not None:
        bx, by, bw, bh = obj_box
        pad = 30
        ox1, oy1 = max(0, bx - pad), max(0, by - pad)
        ox2, oy2 = min(w, bx + bw + pad), min(h, by + bh + pad)
        crop_obj = gray_full[oy1:oy2, ox1:ox2]
        if crop_obj.size > 0:
            kandidat.append(crop_obj)

    # 2. Potongan zona tengah sabuk (bebas pantulan rel pinggir)
    kandidat.append(gray_full[cy1:cy2, cx1:cx2])

    for crop in kandidat:
        # Regangkan kontras khusus isi objek (mengubah layar HP redup menjadi hitam-putih tajam)
        tajam_kontras = kontras_persentil(crop)
        padded = cv2.copyMakeBorder(tajam_kontras, 35, 35, 35, 35, cv2.BORDER_CONSTANT, value=255)

        kode, tipe = coba_decode(padded)
        if kode:
            return kode, tipe

        # Ukuran 0.55x menghilangkan blur fokus dekat & grid piksel layar HP
        kecil = cv2.resize(padded, None, fx=0.55, fy=0.55, interpolation=cv2.INTER_AREA)
        kode, tipe = coba_decode(kecil)
        if kode:
            return kode, tipe

        if mode == 0:
            _, otsu = cv2.threshold(kecil, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            kode, tipe = coba_decode(otsu)
        elif mode == 1:
            tebal = cv2.erode(padded, kernel_debloom, iterations=1)
            tebal_kecil = cv2.resize(tebal, None, fx=0.55, fy=0.55, interpolation=cv2.INTER_AREA)
            kode, tipe = coba_decode(tebal_kecil)
        elif mode == 2:
            adap = cv2.adaptiveThreshold(clahe.apply(padded), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 10)
            kode, tipe = coba_decode(adap)
        else:
            teks_qr, _, _ = qr_fallback.detectAndDecode(kecil)
            if teks_qr:
                return teks_qr.strip(), "QRCODE"

        if kode:
            return kode, tipe

    return None, None

print("[SISTEM] Siap! Klik Jalankan (ON) di dashboard untuk memulai.")

# =====================================================
# LOOP UTAMA DETEKSI & PELACAKAN MULTI-OBJEK
# =====================================================
try:
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.03)
            continue

        sekarang = time.time()
        gray_full = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        roi_gray = gray_full[y1:y2, x1:x2]
        roi_blur = cv2.GaussianBlur(roi_gray, (15, 15), 0)

        if minta_kalibrasi_ulang:
            bg_ref = roi_blur.copy()
            minta_kalibrasi_ulang = False

        # Deteksi perbedaan objek fisik dari sabuk hitam
        diff = cv2.absdiff(roi_blur, bg_ref)
        _, fg_mask = cv2.threshold(diff, 45, 255, cv2.THRESH_BINARY)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel_open)
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        deteksi_saat_ini = []
        for c in contours:
            area = cv2.contourArea(c)
            if AMBANG_AREA_MIN <= area <= luas_maks_objek:
                bx, by, bw, bh = cv2.boundingRect(c)
                fx, fy = x1 + bx, y1 + by
                ocx, ocy = fx + bw // 2, fy + bh // 2
                deteksi_saat_ini.append({
                    "box": (fx, fy, bw, bh),
                    "center": (ocx, ocy)
                })

        # Cocokkan deteksi frame ini dengan objek yang sedang dilacak
        matched_ids = set()
        for det in deteksi_saat_ini:
            dcx, dcy = det["center"]
            best_id = None
            best_dist = 115.0

            for oid, obj in tracked_objects.items():
                if oid in matched_ids:
                    continue
                ocx, ocy = obj["center"]
                dist = math.hypot(dcx - ocx, dcy - ocy)
                if dist < best_dist:
                    best_dist = dist
                    best_id = oid

            if best_id is not None:
                tracked_objects[best_id]["box"] = det["box"]
                tracked_objects[best_id]["center"] = det["center"]
                tracked_objects[best_id]["last_seen"] = sekarang
                matched_ids.add(best_id)
            else:
                tracked_objects[next_obj_id] = {
                    "box": det["box"],
                    "center": det["center"],
                    "spawn_center": det["center"],
                    "spawn_time": sekarang,
                    "status": "NEW",
                    "label": "BARU",
                    "last_seen": sekarang,
                    "done_time": None
                }
                matched_ids.add(next_obj_id)
                next_obj_id += 1

        # Hapus objek yang keluar layar (> 0.35s), selesai diproses (> 1.8s),
        # ATAU bayangan palsu yang tidak berpindah tempat sama sekali selama > 1.2s saat motor jalan
        expired_ids = []
        ada_ghost_diam = False
        for oid, obj in tracked_objects.items():
            hilang_lama = (sekarang - obj["last_seen"]) > 0.35
            selesai_lama = (obj["done_time"] is not None) and ((sekarang - obj["done_time"]) > 1.8)

            jarak_geser = math.hypot(
                obj["center"][0] - obj["spawn_center"][0],
                obj["center"][1] - obj["spawn_center"][1]
            )
            ghost_diam = (
                konveyor_aktif
                and not sedang_scanning
                and obj["status"] == "NEW"
                and (sekarang - obj["spawn_time"]) > 1.2
                and jarak_geser < 10.0
            )
            if ghost_diam:
                ada_ghost_diam = True

            if hilang_lama or selesai_lama or ghost_diam:
                expired_ids.append(oid)

        for oid in expired_ids:
            if oid == scanning_obj_id:
                sedang_scanning = False
                scanning_obj_id = None
                if konveyor_aktif:
                    client.publish(TOPIC_KONTROL, "ON", qos=1)
            del tracked_objects[oid]

        if ada_ghost_diam:
            bg_ref = cv2.addWeighted(bg_ref, 0.70, roi_blur, 0.30, 0)

        # Self-healing background pada area sabuk di luar objek aktif
        if konveyor_aktif and not sedang_scanning:
            mask_sabuk = np.full((roi_h, roi_w), 255, dtype=np.uint8)
            for oid, obj in tracked_objects.items():
                fx, fy, bw, bh = obj["box"]
                ux1 = max(0, fx - x1 - 15)
                uy1 = max(0, fy - y1 - 15)
                ux2 = min(roi_w, fx - x1 + bw + 15)
                uy2 = min(roi_h, fy - y1 + bh + 15)
                if ux2 > ux1 and uy2 > uy1:
                    mask_sabuk[uy1:uy2, ux1:ux2] = 0

            blended = cv2.addWeighted(bg_ref, 0.92, roi_blur, 0.08, 0)
            bg_ref = np.where(mask_sabuk == 255, blended, bg_ref)

        preview = frame.copy()

        cv2.rectangle(preview, (x1, y1), (x2, y2), (100, 116, 139), 1)
        if not konveyor_aktif:
            warna_zona = (148, 163, 184)
        elif sedang_scanning:
            warna_zona = (0, 255, 255)
        else:
            warna_zona = (56, 189, 248)
        cv2.rectangle(preview, (cx1, cy1), (cx2, cy2), warna_zona, 3)

        for oid, obj in tracked_objects.items():
            fx, fy, bw, bh = obj["box"]
            ocx, ocy = obj["center"]
            st = obj["status"]

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
            cv2.putText(preview, f"#{oid} {obj['label']}", (fx, max(20, fy - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.52, warna_obj, 2)

        if not konveyor_aktif:
            cv2.putText(preview, "KONVEYOR OFF - KLIK JALANKAN (ON) DI WEB", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (248, 113, 113), 2)

        else:
            if not sedang_scanning:
                for oid, obj in tracked_objects.items():
                    if obj["status"] == "NEW":
                        ocx, ocy = obj["center"]
                        if cx1 <= ocx <= cx2 and cy1 <= ocy <= cy2:
                            obj["status"] = "SCANNING"
                            obj["label"] = "SCANNING"
                            sedang_scanning = True
                            scanning_obj_id = oid
                            waktu_mulai_scan = sekarang
                            client.publish(TOPIC_KONTROL, "SCANNING", qos=1)
                            print(f"[DETEKSI] Objek #{oid} tiba di tengah lensa -> Berhenti maksimal 5 detik...")
                            break

            if sedang_scanning and scanning_obj_id in tracked_objects:
                obj_aktif = tracked_objects[scanning_obj_id]
                sisa_waktu = max(0.0, WAKTU_BERHENTI_SCAN - (sekarang - waktu_mulai_scan))
                cv2.putText(preview, f"SCAN OBJEK #{scanning_obj_id} ({sisa_waktu:.1f}s)...", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (0, 255, 255), 2)

                siklus_scan = (siklus_scan + 1) % 4
                isi_kode, tipe_kode = scan_multi_mode(gray_full, obj_aktif["box"], siklus_scan)

                if isi_kode:
                    obj_aktif["status"] = "DONE_OK"
                    obj_aktif["label"] = f"OK: {isi_kode}"
                    obj_aktif["done_time"] = sekarang
                    sedang_scanning = False
                    scanning_obj_id = None

                    client.publish(TOPIC_KONTROL, "SCAN_OK", qos=1)
                    client.publish(TOPIC_KONTROL, "ON", qos=1)

                    if isi_kode in kode_terscan_set:
                        print(f"[DUPLIKAT] '{isi_kode}' sudah pernah di-scan -> Lanjut jalan.")
                    else:
                        kode_terscan_set.add(isi_kode)
                        jumlah_barang += 1
                        waktu_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        client.publish(TOPIC_KODE, isi_kode, qos=1)
                        client.publish(TOPIC_JUMLAH, str(jumlah_barang), qos=1)

                        payload_json = json.dumps({
                            "uid_barcode": isi_kode,
                            "tipe_kode": tipe_kode,
                            "status_scan": "VALID",
                            "jumlah": jumlah_barang,
                            "rpm_aktual": data_pid.get("rpm", 0.0),
                            "waktu_scan": waktu_str
                        })
                        client.publish(TOPIC_DATA, payload_json, qos=1)
                        print(f"[{waktu_str}] SCAN VALID: {isi_kode} | Total: {jumlah_barang} -> Lanjut jalan!")

                elif sekarang - waktu_mulai_scan >= WAKTU_BERHENTI_SCAN:
                    obj_aktif["status"] = "DONE_FAIL"
                    obj_aktif["label"] = "NO BARCODE"
                    obj_aktif["done_time"] = sekarang
                    sedang_scanning = False
                    scanning_obj_id = None

                    client.publish(TOPIC_KONTROL, "SCAN_FAIL", qos=1)
                    client.publish(TOPIC_KONTROL, "ON", qos=1)

                    payload_fail = json.dumps({
                        "uid_barcode": "NO_BARCODE",
                        "tipe_kode": "NONE",
                        "status_scan": "FAILED",
                        "jumlah": jumlah_barang,
                        "rpm_aktual": data_pid.get("rpm", 0.0),
                        "waktu_scan": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    client.publish(TOPIC_DATA, payload_fail, qos=1)
                    print("[TIMEOUT 5s] Tidak ada barcode -> Alert dikirim & konveyor otomatis lanjut!")

            elif len(tracked_objects) > 0:
                cv2.putText(preview, f"KONVEYOR JALAN ({len(tracked_objects)} OBJEK)", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
            else:
                cv2.putText(preview, "KONVEYOR JALAN - MENUNGGU BARANG", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (203, 213, 225), 2)

        ok_jpg, buf_jpg = cv2.imencode(".jpg", preview, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ok_jpg:
            with frame_lock:
                latest_jpeg = buf_jpg.tobytes()

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\n[SISTEM] Program dihentikan.")
finally:
    client.publish(TOPIC_KONTROL, "OFF", qos=1)
    cap.release()
    client.loop_stop()
    client.disconnect()