
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ===============================
// KONFIGURASI LCD
// ===============================
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ===============================
// PIN ESP8266 NODEMCU
// ===============================
#define LED_MERAH  D0
#define LED_HIJAU  D4

#define IN1 D5
#define IN2 D6
#define ENA D7

// ===============================
// KONFIGURASI SISTEM
// ===============================
const int TARGET_STOK = 10;
const int KECEPATAN_MOTOR = 700; // Rentang PWM 0-1023

int jumlahStok = 0;
bool sistemAktif = false;
bool targetTercapai = false;

// ===============================
// FUNGSI MENAMPILKAN TEKS LCD
// ===============================
void tampilkanBaris(byte baris, String teks) {
  lcd.setCursor(0, baris);

  // Maksimal 16 karakter
  if (teks.length() > 16) {
    teks = teks.substring(0, 16);
  }

  lcd.print(teks);

  // Hapus sisa karakter sebelumnya
  for (int i = teks.length(); i < 16; i++) {
    lcd.print(" ");
  }
}

// ===============================
// TAMPILAN AWAL
// ===============================
void tampilkanAwal() {
  tampilkanBaris(0, "SMART COUNTER");
  tampilkanBaris(1, "CLICK START...");
}

// ===============================
// TAMPILAN SAAT BERJALAN
// ===============================
void tampilkanMonitoring() {
  String stok = "STOK ";

  if (jumlahStok < 10) {
    stok += "0";
  }

  stok += String(jumlahStok);
  stok += "/10";

  tampilkanBaris(0, stok);
  tampilkanBaris(1, "SCANNING ITEM");
}

// ===============================
// TAMPILAN TARGET TERCAPAI
// ===============================
void tampilkanTarget() {
  tampilkanBaris(0, "STOK 10/10");
  tampilkanBaris(1, "TARGET REACHED!");
}

// ===============================
// KONTROL MOTOR BERJALAN
// ===============================
void motorJalan() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  analogWrite(ENA, KECEPATAN_MOTOR);
}

// ===============================
// KONTROL MOTOR BERHENTI
// ===============================
void motorBerhenti() {
  analogWrite(ENA, 0);

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
}

// ===============================
// LED INDIKATOR
// ===============================
void ledBerjalan() {
  digitalWrite(LED_HIJAU, HIGH);
  digitalWrite(LED_MERAH, LOW);
}

void ledBerhenti() {
  digitalWrite(LED_HIJAU, LOW);
  digitalWrite(LED_MERAH, HIGH);
}

// ===============================
// MEMULAI SISTEM
// ===============================
void mulaiSistem() {
  if (targetTercapai) {
    Serial.println("TARGET_ALREADY_REACHED");
    return;
  }

  jumlahStok = 0;
  sistemAktif = true;

  motorJalan();
  ledBerjalan();
  tampilkanMonitoring();

  Serial.println("SYSTEM_STARTED");
}

// ===============================
// MENGHITUNG PRODUK
// ===============================
void hitungProduk() {
  if (!sistemAktif || targetTercapai) {
    Serial.println("COUNT_REJECTED");
    return;
  }

  jumlahStok++;

  Serial.print("STOK:");
  Serial.println(jumlahStok);

  if (jumlahStok >= TARGET_STOK) {
    jumlahStok = TARGET_STOK;

    sistemAktif = false;
    targetTercapai = true;

    motorBerhenti();
    ledBerhenti();

    tampilkanTarget();

    Serial.println("TARGET_REACHED");
  } else {
    tampilkanMonitoring();
  }
}

// ===============================
// RESET SISTEM
// ===============================
void resetSistem() {
  motorBerhenti();
  ledBerhenti();

  jumlahStok = 0;
  sistemAktif = false;
  targetTercapai = false;

  tampilkanAwal();

  Serial.println("SYSTEM_RESET");
}

// ===============================
// MEMBACA PERINTAH DARI RASPBERRY PI
// ===============================
void bacaPerintahSerial() {
  if (Serial.available()) {
    String perintah = Serial.readStringUntil('\n');
    perintah.trim();
    perintah.toUpperCase();

    if (perintah == "START") {
      mulaiSistem();
    }
    else if (perintah == "COUNT") {
      hitungProduk();
    }
    else if (perintah == "STOP") {
      sistemAktif = false;

      motorBerhenti();
      ledBerhenti();

      tampilkanBaris(0, "SYSTEM STOPPED");
      tampilkanBaris(1, "STOK: " + String(jumlahStok));

      Serial.println("SYSTEM_STOPPED");
    }
    else if (perintah == "RESET") {
      resetSistem();
    }
  }
}

// ===============================
// SETUP
// ===============================
void setup() {
  Serial.begin(115200);
  Serial.setTimeout(50);

  Wire.begin(D2, D1); // SDA, SCL

  lcd.init();
  lcd.backlight();

  pinMode(LED_MERAH, OUTPUT);
  pinMode(LED_HIJAU, OUTPUT);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(ENA, OUTPUT);

  analogWriteRange(1023);
  analogWriteFreq(1000);

  motorBerhenti();
  ledBerhenti();

  tampilkanAwal();

  Serial.println("SMART_PRODUCT_COUNTER_READY");
}

// ===============================
// LOOP
// ===============================
void loop() {
  bacaPerintahSerial();
}
