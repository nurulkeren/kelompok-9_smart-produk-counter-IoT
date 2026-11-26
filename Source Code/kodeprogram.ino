#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ================= KONFIGURASI WIFI & MQTT =================
const char* WIFI_SSID   = "naye";
const char* WIFI_PASS   = "tolonglahya";
const char* MQTT_SERVER = "192.168.137.230";
const int   MQTT_PORT   = 1883;

const char* TOPIC_KONTROL = "kel9_iot/conveyor/kontrol";
const char* TOPIC_STATUS  = "kel9_iot/conveyor/status";
const char* TOPIC_KODE    = "kel9_iot/conveyor/kode";
const char* TOPIC_JUMLAH  = "kel9_iot/conveyor/jumlah";
const char* TOPIC_RESET   = "kel9_iot/conveyor/reset";

// ================= PIN ESP8266 =================
#define PIN_RELAY       D0
#define PIN_LCD_SDA     D2
#define PIN_LCD_SCL     D1
#define PIN_ENA         D5
#define PIN_SENSOR      D6
#define PIN_SAKLAR      D7
#define PIN_LED_MERAH   D3
#define PIN_LED_HIJAU   D4
#define PIN_LED_KUNING  D8

// Polaritas LED
#define LED_ON          LOW
#define LED_OFF         HIGH
#define LED_KUNING_ON   HIGH
#define LED_KUNING_OFF  LOW

// ================= KONFIGURASI KONVEYOR & PID =================
const int JUMLAH_CELAH = 20;

float setpointRPM = 100.0;
float Kp = 1.2;
float Ki = 0.8;
float Kd = 0.05;

const int PWM_MIN = 85;
const int PWM_MAX = 255;

// ================= STATUS OPERASI & DATA LCD =================
enum ModeKonveyor {
  MODE_RUNNING,
  MODE_SCANNING
};

ModeKonveyor modeSekarang = MODE_RUNNING;
bool konveyorAktif = false;      // Bisa langsung di-ON/OFF dari web tanpa saklar fisik
bool saklarSebelumnya = false;
bool inisialisasiSaklar = false;

int jumlahBarangLCD = 0;
String kodeTerakhirLCD = "-";
unsigned long waktuNotifStatus = 0;
String teksNotifStatus = "";

// ================= OBJEK & VARIABEL =================
WiFiClient espClient;
PubSubClient mqtt(espClient);
LiquidCrystal_I2C lcd(0x27, 16, 2);

volatile unsigned long jumlahPulsa = 0;
volatile unsigned long waktuPulsaTerakhir = 0;

unsigned long waktuPIDSebelumnya = 0;
unsigned long waktuKirimSebelumnya = 0;
unsigned long waktuReconnectMQTT = 0;
unsigned long waktuMulaiScan = 0;

float rpmAktual = 0.0;
float rpmFiltered = 0.0;
float integralPID = 0.0;
float errorSebelumnya = 0.0;
int   pwmOutput = 0;
bool  motorSedangJalan = false;

// ================= HELPER LCD & KEDIP ALERT =================
void cetakBarisLCD(int baris, String teks) {
  while (teks.length() < 16) teks += " ";
  if (teks.length() > 16) teks = teks.substring(0, 16);
  lcd.setCursor(0, baris);
  lcd.print(teks);
}

void setSemuaLED(bool merah, bool kuning, bool hijau) {
  digitalWrite(PIN_LED_MERAH, merah ? LED_ON : LED_OFF);
  digitalWrite(PIN_LED_KUNING, kuning ? LED_KUNING_ON : LED_KUNING_OFF);
  digitalWrite(PIN_LED_HIJAU, hijau ? LED_ON : LED_OFF);
}

// Alert 5 detik tanpa barcode: LED kedip 2x + LCD tampil "NO BARCODE!" & hitungan tetap muncul
void jalankanAlertGagalScan() {
  cetakBarisLCD(0, "NO BARCODE!     ");
  cetakBarisLCD(1, "BRG:" + String(jumlahBarangLCD) + " RPM:0");

  for (int i = 0; i < 2; i++) {
    setSemuaLED(true, true, true);
    delay(200);
    setSemuaLED(false, false, false);
    delay(200);
  }

  teksNotifStatus = "NO BARCODE!     ";
  waktuNotifStatus = millis();
  modeSekarang = MODE_RUNNING;
}

// ================= INTERRUPT SENSOR FC-03 =================
void IRAM_ATTR hitungPulsa() {
  unsigned long sekarang = micros();
  if (sekarang - waktuPulsaTerakhir > 1000) {
    jumlahPulsa++;
    waktuPulsaTerakhir = sekarang;
  }
}

// ================= KONTROL INDIKATOR 3 LED =================
void updateIndikatorLED() {
  if (!konveyorAktif) {
    setSemuaLED(true, false, false);
  } 
  else if (modeSekarang == MODE_SCANNING) {
    setSemuaLED(false, true, false);
  } 
  else {
    setSemuaLED(false, false, true);
  }
}

// ================= PROSES PERINTAH MQTT & SERIAL =================
void prosesPerintah(String pesan) {
  pesan.trim();
  String cmd = pesan;
  cmd.toUpperCase();

  if (cmd == "ON" || cmd == "START") {
    konveyorAktif = true;
    modeSekarang = MODE_RUNNING;
  }
  else if (cmd == "OFF" || cmd == "STOP") {
    konveyorAktif = false;
    modeSekarang = MODE_RUNNING;
  }
  else if (cmd == "SCANNING" || cmd == "PAUSE") {
    if (konveyorAktif) {
      modeSekarang = MODE_SCANNING;
      waktuMulaiScan = millis();
      teksNotifStatus = "";
    }
  }
  else if (cmd == "SCAN_OK" || cmd == "RESUME" || cmd == "RUN") {
    if (konveyorAktif) {
      modeSekarang = MODE_RUNNING;
    }
  }
  else if (cmd == "SCAN_FAIL") {
    jalankanAlertGagalScan();
  }
  else if (cmd.startsWith("RPM:")) {
    float targetBaru = cmd.substring(4).toFloat();
    if (targetBaru >= 20 && targetBaru <= 500) {
      setpointRPM = targetBaru;
    }
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String topikStr = String(topic);
  String pesan = "";
  for (unsigned int i = 0; i < length; i++) {
    pesan += (char)payload[i];
  }
  pesan.trim();

  if (topikStr == TOPIC_KONTROL) {
    prosesPerintah(pesan);
  }
  else if (topikStr == TOPIC_JUMLAH) {
    jumlahBarangLCD = pesan.toInt();
  }
  else if (topikStr == TOPIC_KODE) {
    kodeTerakhirLCD = pesan;
    teksNotifStatus = "SCAN BERHASIL!  ";
    waktuNotifStatus = millis();
  }
  else if (topikStr == TOPIC_RESET && pesan == "RESET") {
    jumlahBarangLCD = 0;
    kodeTerakhirLCD = "-";
    teksNotifStatus = "";
  }
}

// ================= KONTROL MOTOR & RELAY =================
void mulaiMotor() {
  if (!motorSedangJalan) {
    pinMode(PIN_RELAY, OUTPUT);
    digitalWrite(PIN_RELAY, LOW);
    delay(40);

    integralPID = 0.0;
    errorSebelumnya = 0.0;
    pwmOutput = 150;
    analogWrite(PIN_ENA, pwmOutput);
    motorSedangJalan = true;
  }
}

void hentikanMotor() {
  if (motorSedangJalan) {
    analogWrite(PIN_ENA, 0);
    digitalWrite(PIN_ENA, LOW);
    delay(40);
    pinMode(PIN_RELAY, INPUT);

    pwmOutput = 0;
    rpmAktual = 0.0;
    rpmFiltered = 0.0;
    integralPID = 0.0;
    errorSebelumnya = 0.0;
    motorSedangJalan = false;
  }
}

// ================= KONEKSI WIFI & MQTT =================
void setupWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  int percobaan = 0;
  while (WiFi.status() != WL_CONNECTED && percobaan < 20) {
    delay(500);
    percobaan++;
  }
}

void cekKoneksiMQTT() {
  if (WiFi.status() != WL_CONNECTED) return;
  if (!mqtt.connected()) {
    if (millis() - waktuReconnectMQTT >= 5000) {
      waktuReconnectMQTT = millis();
      String clientId = "ESP8266-Conveyor-" + String(random(0xffff), HEX);
      if (mqtt.connect(clientId.c_str())) {
        mqtt.subscribe(TOPIC_KONTROL);
        mqtt.subscribe(TOPIC_JUMLAH);
        mqtt.subscribe(TOPIC_KODE);
        mqtt.subscribe(TOPIC_RESET);
      }
    }
  } else {
    mqtt.loop();
  }
}

// ================= SETUP =================
void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(PIN_RELAY, INPUT);
  pinMode(PIN_ENA, OUTPUT);
  digitalWrite(PIN_ENA, LOW);

  pinMode(PIN_SENSOR, INPUT);
  pinMode(PIN_SAKLAR, INPUT_PULLUP);

  pinMode(PIN_LED_MERAH, OUTPUT);
  pinMode(PIN_LED_HIJAU, OUTPUT);
  pinMode(PIN_LED_KUNING, OUTPUT);

  analogWriteRange(255);
  analogWriteFreq(1000);

  Wire.begin(PIN_LCD_SDA, PIN_LCD_SCL);
  delay(250);
  lcd.init();
  lcd.backlight();
  lcd.clear();

  setSemuaLED(true, true, true);
  cetakBarisLCD(0, "PERSIAPAN SISTEM");
  cetakBarisLCD(1, "SEMUA LED ON 2s ");
  delay(2000);

  setSemuaLED(true, false, false);
  cetakBarisLCD(0, "MENGHUBUNGKAN...");
  cetakBarisLCD(1, "WIFI & MQTT     ");
  setupWiFi();

  mqtt.setServer(MQTT_SERVER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);

  attachInterrupt(digitalPinToInterrupt(PIN_SENSOR), hitungPulsa, FALLING);
}

// ================= LOOP =================
void loop() {
  cekKoneksiMQTT();

  if (Serial.available() > 0) {
    String cmdSerial = Serial.readStringUntil('\n');
    prosesPerintah(cmdSerial);
  }

  // 1. Cek perubahan saklar fisik (tidak mengunci tombol web)
  bool saklarFisikON = (digitalRead(PIN_SAKLAR) == LOW);
  if (!inisialisasiSaklar) {
    saklarSebelumnya = saklarFisikON;
    inisialisasiSaklar = true;
    konveyorAktif = false;
  } else if (saklarFisikON != saklarSebelumnya) {
    saklarSebelumnya = saklarFisikON;
    konveyorAktif = saklarFisikON;
    modeSekarang = MODE_RUNNING;
  }

  // 2. Eksekusi Motor
  if (!konveyorAktif) {
    hentikanMotor();
  } else {
    // Pengaman jika Raspi terputus saat scanning lebih dari 6.5 detik -> otomatis lanjut
    if (modeSekarang == MODE_SCANNING && (millis() - waktuMulaiScan >= 6500)) {
      jalankanAlertGagalScan();
    }

    if (modeSekarang == MODE_RUNNING) {
      mulaiMotor();
    } else {
      hentikanMotor();
    }
  }

  updateIndikatorLED();

  // 3. Perhitungan Sensor FC-03 & PID setiap 250 ms
  unsigned long sekarang = millis();
  if (sekarang - waktuPIDSebelumnya >= 250) {
    float dt = (sekarang - waktuPIDSebelumnya) / 1000.0;
    waktuPIDSebelumnya = sekarang;

    noInterrupts();
    unsigned long pulsa = jumlahPulsa;
    jumlahPulsa = 0;
    interrupts();

    if (motorSedangJalan) {
      rpmAktual = ((float)pulsa / JUMLAH_CELAH) * (60.0 / dt);
      rpmFiltered = (0.6 * rpmAktual) + (0.4 * rpmFiltered);

      float error = setpointRPM - rpmFiltered;
      integralPID += error * dt;
      integralPID = constrain(integralPID, -150.0, 150.0);
      float derivative = (error - errorSebelumnya) / dt;
      errorSebelumnya = error;

      float pidOut = (Kp * error) + (Ki * integralPID) + (Kd * derivative);
      pwmOutput = constrain((int)(pwmOutput + pidOut * 0.25), PWM_MIN, PWM_MAX);

      analogWrite(PIN_ENA, pwmOutput);
    } else {
      rpmAktual = 0.0;
      rpmFiltered = 0.0;
      pwmOutput = 0;
    }
  }

  // 4. Update LCD & Kirim Telemetry setiap 500 ms
  if (sekarang - waktuKirimSebelumnya >= 500) {
    waktuKirimSebelumnya = sekarang;

    if (teksNotifStatus != "" && (sekarang - waktuNotifStatus >= 3000)) {
      teksNotifStatus = "";
    }

    const char* statusTeks = "OFF";
    if (!konveyorAktif) {
      statusTeks = "OFF";
      cetakBarisLCD(0, "KONVEYOR: MATI  ");
    } 
    else if (teksNotifStatus != "") {
      statusTeks = "RUNNING";
      cetakBarisLCD(0, teksNotifStatus);
    }
    else if (modeSekarang == MODE_SCANNING) {
      statusTeks = "SCANNING";
      cetakBarisLCD(0, "SCANNING (5s)...");
    } 
    else {
      statusTeks = "RUNNING";
      cetakBarisLCD(0, "KONVEYOR: JALAN ");
    }

    String barisInfo = "BRG:" + String(jumlahBarangLCD) + " RPM:" + String((int)rpmFiltered);
    cetakBarisLCD(1, barisInfo);

    char jsonPayload[160];
    snprintf(jsonPayload, sizeof(jsonPayload),
             "{\"status\":\"%s\",\"saklar\":\"%s\",\"sistem\":\"%s\",\"rpm\":%.1f,\"setpoint\":%.1f,\"pwm\":%d}",
             statusTeks,
             saklarFisikON ? "ON" : "OFF",
             konveyorAktif ? "ON" : "OFF",
             rpmFiltered, setpointRPM, pwmOutput);

    if (mqtt.connected()) {
      mqtt.publish(TOPIC_STATUS, jsonPayload);
    }
  }
}
