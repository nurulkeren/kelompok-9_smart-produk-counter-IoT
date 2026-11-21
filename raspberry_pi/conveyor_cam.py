import cv2
import time
import json
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

WAKTU_BERHENTI_SCAN = 5.0   # Berhenti 5 detik untuk proses scanning
AMBANG_AREA_MIN     = 3500  # Batas ukuran objek di frame

jumlah_barang = 0
kode_terscan_set = set()    # Menyimpan riwayat barcode agar tidak ter-scan ulang
frame_kosong = 0
barang_sudah_diproses = False
sedang_scanning = False
waktu_mulai_scan = 0.0
siklus_scan = 0

data_pid = {"status": "OFF", "rpm": 0.0, "setpoint": 100.0, "pwm": 0}
latest_jpeg = None
frame_lock = threading.Lock()

# =====================================================
# SERVER LIVE PREVIEW KAMERA (MJPEG STREAM)
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
                "<html><body style='background:#0f172a;color:#fff;text-align:center;font-family:sans-serif'>"
                "<h3>Live Kamera Conveyor (Kel 9 IoT)</h3>"
                "<img src='/stream' style='max-width:95%;border:2px solid #22c55e;border-radius:8px'/>"
                "</body></html>"
            )
            self.wfile.write(html.encode())
        elif self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                while True:
                    with frame_lock:
                        jpg = latest_jpeg
                    if jpg is not None:
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n")
                    time.sleep(0.06)
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
        client.publish(TOPIC_JUMLAH, str(jumlah_barang))
        client.publish(TOPIC_KONTROL, "ON")
    else:
        print(f"[MQTT] Gagal terhubung, kode: {reason_code}")

def on_message(client, userdata, msg):
    global jumlah_barang, kode_terscan_set, data_pid
    pesan = msg.payload.decode().strip()

    if msg.topic == TOPIC_RESET and pesan == "RESET":
        jumlah_barang = 0
        kode_terscan_set.clear()  # Reset daftar barcode yang sudah pernah di-scan
        client.publish(TOPIC_JUMLAH, "0")
        print("[SISTEM] Hitungan barang & memori anti-duplikat di-reset!")

    elif msg.topic == TOPIC_STATUS:
        try:
            data_pid = json.loads(pesan)
        except json.JSONDecodeError:
            pass

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_start()

# =====================================================
# INISIALISASI WEBCAM
# =====================================================
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
if not cap.isOpened():
    cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print("[ERROR] USB Webcam tidak dapat dibuka!")
    exit(1)

bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=120, varThreshold=45, detectShadows=False)

print("[KALIBRASI] Menstabilkan kamera & sabuk selama 2 detik...")
for _ in range(25):
    ret, frame_awal = cap.read()
    if ret:
        h, w = frame_awal.shape[:2]
        y1, y2 = int(h * 0.12), int(h * 0.88)
        x1, x2 = int(w * 0.12), int(w * 0.88)
        roi_init = cv2.GaussianBlur(frame_awal[y1:y2, x1:x2], (15, 15), 0)
        bg_subtractor.apply(roi_init, learningRate=0.1)
    time.sleep(0.05)

luas_roi_maks = (y2 - y1) * (x2 - x1) * 0.85
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
kernel_sharpen = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
qr_fallback = cv2.QRCodeDetector()

def scan_multi_mode(gray_full, roi_gray, mode):
    hasil = decode(gray_full)
    if hasil:
        return hasil[0].data.decode("utf-8").strip(), hasil[0].type, hasil[0].rect

    if mode == 0:
        tajam = cv2.filter2D(clahe.apply(roi_gray), -1, kernel_sharpen)
        hasil = decode(tajam)
    elif mode == 1:
        adap = cv2.adaptiveThreshold(roi_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 12)
        hasil = decode(adap)
    elif mode == 2:
        rot = cv2.rotate(roi_gray, cv2.ROTATE_90_CLOCKWISE)
        hasil = decode(rot)
    else:
        teks_qr, _, _ = qr_fallback.detectAndDecode(gray_full)
        if teks_qr:
            return teks_qr.strip(), "QRCODE", None

    if hasil:
        return hasil[0].data.decode("utf-8").strip(), hasil[0].type, hasil[0].rect
    return None, None, None

print(f"[SISTEM] Siap! Live kamera: http://192.168.137.230:{STREAM_PORT}")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.03)
            continue

        gray_full = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        roi_gray = gray_full[y1:y2, x1:x2]

        roi_blur = cv2.GaussianBlur(frame[y1:y2, x1:x2], (15, 15), 0)
        lr = 0.0 if sedang_scanning else 0.01
        fg_mask = bg_subtractor.apply(roi_blur, learningRate=lr)

        fg_mask = cv2.erode(fg_mask, None, iterations=1)
        fg_mask = cv2.dilate(fg_mask, None, iterations=2)
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        area_terbesar = max((cv2.contourArea(c) for c in contours), default=0)
        ada_barang = (AMBANG_AREA_MIN < area_terbesar < luas_roi_maks)

        siklus_scan = (siklus_scan + 1) % 4
        isi_kode, tipe_kode, rect_kode = scan_multi_mode(gray_full, roi_gray, siklus_scan)

        preview = frame.copy()
        warna_roi = (0, 255, 255) if sedang_scanning else ((0, 255, 0) if isi_kode else (255, 255, 255))
        cv2.rectangle(preview, (x1, y1), (x2, y2), warna_roi, 2)

        if isi_kode:
            frame_kosong = 0
            if rect_kode:
                rx, ry, rw, rh = rect_kode
                cv2.rectangle(preview, (rx, ry), (rx + rw, ry + rh), (255, 0, 0), 3)

            # Cek apakah barcode sudah pernah di-scan sebelumnya
            if isi_kode in kode_terscan_set:
                cv2.putText(preview, f"DUPLIKAT: {isi_kode}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 165, 255), 2)
                if not barang_sudah_diproses:
                    print(f"[DUPLIKAT] Barcode '{isi_kode}' sudah pernah di-scan -> Tidak dihitung ulang.")
                    barang_sudah_diproses = True
                if sedang_scanning:
                    client.publish(TOPIC_KONTROL, "SCAN_OK")
                    sedang_scanning = False
            else:
                # Barcode baru & valid
                kode_terscan_set.add(isi_kode)
                barang_sudah_diproses = True
                jumlah_barang += 1
                waktu_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                client.publish(TOPIC_KONTROL, "SCAN_OK")
                client.publish(TOPIC_KODE, isi_kode)
                client.publish(TOPIC_JUMLAH, str(jumlah_barang))
                sedang_scanning = False

                payload_json = json.dumps({
                    "uid_barcode": isi_kode,
                    "tipe_kode": tipe_kode,
                    "status_scan": "VALID",
                    "jumlah": jumlah_barang,
                    "rpm_aktual": data_pid.get("rpm", 0.0),
                    "waktu_scan": waktu_str
                })
                client.publish(TOPIC_DATA, payload_json)
                cv2.putText(preview, f"SCAN BERHASIL: {isi_kode}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 0), 2)
                print(f"[{waktu_str}] SCAN BERHASIL ({tipe_kode}): {isi_kode} | Total: {jumlah_barang}")

        else:
            status_txt = f"SCANNING 5s (Area:{int(area_terbesar)})" if sedang_scanning else f"STANDBY (Area:{int(area_terbesar)})"
            cv2.putText(preview, status_txt, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, warna_roi, 2)

            if ada_barang:
                frame_kosong = 0
                if not barang_sudah_diproses and not sedang_scanning:
                    client.publish(TOPIC_KONTROL, "SCANNING")
                    sedang_scanning = True
                    waktu_mulai_scan = time.time()
                    print(f"[DETEKSI] Barang terdeteksi (Area: {int(area_terbesar)}) -> Berhenti 5 detik & LED Kuning ON")

                elif sedang_scanning:
                    if time.time() - waktu_mulai_scan >= WAKTU_BERHENTI_SCAN:
                        print("[ALERT] 5 detik selesai, barcode tidak terdeteksi -> Kirim SCAN_FAIL!")
                        client.publish(TOPIC_KONTROL, "SCAN_FAIL")

                        # Kirim log gagal scan ke backend Laravel untuk audit traceability
                        payload_fail = json.dumps({
                            "uid_barcode": "NO_BARCODE",
                            "tipe_kode": "NONE",
                            "status_scan": "FAILED",
                            "jumlah": jumlah_barang,
                            "rpm_aktual": data_pid.get("rpm", 0.0),
                            "waktu_scan": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        client.publish(TOPIC_DATA, payload_fail)

                        sedang_scanning = False
                        barang_sudah_diproses = True
            else:
                frame_kosong += 1
                if frame_kosong >= 8:
                    barang_sudah_diproses = False
                    if sedang_scanning:
                        client.publish(TOPIC_KONTROL, "SCAN_OK")
                        sedang_scanning = False

        ok_jpg, buf_jpg = cv2.imencode(".jpg", preview, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if ok_jpg:
            with frame_lock:
                latest_jpeg = buf_jpg.tobytes()

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\n[SISTEM] Program dihentikan.")
finally:
    client.publish(TOPIC_KONTROL, "OFF")
    cap.release()
    client.loop_stop()
    client.disconnect()