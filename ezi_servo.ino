// ================================================================
// THI NGHIEM EP CAM BIEN LUC
// Arduino Nano + EZI-Servo (che do Step/Dir)
// ================================================================
//
// QUY TRINH SU DUNG:
//   1. Mo Serial Monitor (9600 baud, line ending = Newline)
//   2. Dua dong co ve vi tri mong muon lam goc
//   3. NHAN NUT HOME (cong tac tren chan D2) -> Dat vi tri = 0 mm
//   4. Nhap quang duong (mm) vao Serial Monitor, Enter
//      -> Dong co di chuyen truc tiep den vi tri da nhap
//      -> Doc cam bien luc tai vi tri do
//   5. Nhap quang duong moi -> lap lai tu buoc 4
//
// ================================================================

// ===================== CHAN KET NOI =============================
const int stepPin    = 9;   // STEP  (day Do   -> chan 2 driver: Pulse-)
const int dirPin     = 8;   // DIR   (day Vang -> chan 4 driver: Dir-)
const int homeBtnPin = 2;   // Cong tac Home (noi giua D2 va GND)

// ===================== THONG SO CO KHI =========================
const long  pulsesPerRev = 10000;   // Xung/vong (Resolution tren driver)
const float mmPerRev     = 20.0;    // Buoc vitme (mm/vong)

// Tinh tu dong: so xung tren moi mm
const float pulsesPerMm  = (float)pulsesPerRev / mmPerRev; // = 500.0

// ===================== TOC DO ==================================
// Thoi gian tre moi nua xung (microseconds)
// Cang nho = cang nhanh. Thu tu 300 -> 1000 cho an toan.
unsigned int runSpeed  = 300;   // Toc do chay test (us)
unsigned int homeSpeed = 500;   // Toc do ve home (us) - cham hon, an toan

// ===================== CHIEU QUAY ==============================
const bool DIR_PRESS   = HIGH;  // Chieu tien (ep vao cam bien luc)
const bool DIR_RETRACT = LOW;   // Chieu lui (ve phia home)

// ===================== GIOI HAN AN TOAN ========================
const float MAX_TRAVEL_MM = 200.0;  // Quang duong toi da cho phep (mm)

// ===================== BIEN TRANG THAI =========================
long currentPos = 0;    // Vi tri hien tai (don vi: xung). Home = 0
bool isHomed   = false; // Da set Home chua?

// ================================================================
// HAM DI CHUYEN - quay motor so buoc nhat dinh
// ================================================================
void moveSteps(bool direction, long steps, unsigned int pulseDelayUs) {
  if (steps <= 0) return;

  digitalWrite(dirPin, direction);
  delayMicroseconds(10); // Cho driver nhan chieu quay on dinh

  for (long i = 0; i < steps; i++) {
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(pulseDelayUs);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(pulseDelayUs);

    // Cap nhat vi tri
    if (direction == DIR_PRESS) {
      currentPos++;
    } else {
      currentPos--;
    }
  }
}

// ================================================================
// HAM VE HOME (vi tri 0)
// ================================================================
void goHome() {
  if (currentPos == 0) {
    Serial.println(F("  Da o Home."));
    return;
  }

  Serial.print(F("  Ve Home tu "));
  Serial.print((float)currentPos / pulsesPerMm, 2);
  Serial.println(F(" mm..."));

  if (currentPos > 0) {
    // Dang o phia truoc home -> lui ve
    moveSteps(DIR_RETRACT, currentPos, homeSpeed);
  } else {
    // Dang o phia sau home -> tien len
    moveSteps(DIR_PRESS, -currentPos, homeSpeed);
  }

  currentPos = 0; // Dam bao chinh xac
  Serial.println(F("  >> Da ve Home (0 mm)."));
}

// ================================================================
// HAM SET HOME - goi khi nhan nut
// ================================================================
void setHome() {
  currentPos = 0;
  isHomed = true;
  Serial.println(F(""));
  Serial.println(F("========================================"));
  Serial.println(F(">> HOME DA DUOC DAT TAI VI TRI HIEN TAI"));
  Serial.println(F(">> Vi tri = 0.00 mm"));
  Serial.println(F("========================================"));
  Serial.println(F(""));
  Serial.println(F("Nhap quang duong (mm) vao Serial Monitor:"));
}

// ================================================================
// HAM CHAY TEST CASE
// ================================================================
void runTestCase(float distanceMm) {
  long targetPulses = (long)(distanceMm * pulsesPerMm);
  long delta = targetPulses - currentPos;

  Serial.println(F(""));
  Serial.println(F("========================================"));
  Serial.print(F("  TEST: Di chuyen den "));
  Serial.print(distanceMm, 2);
  Serial.print(F(" mm  ("));
  Serial.print(targetPulses);
  Serial.println(F(" xung)"));
  Serial.println(F("========================================"));

  // Di chuyen truc tiep den vi tri mong muon (khong ve Home)
  if (delta > 0) {
    Serial.print(F("  Tien "));
    Serial.print((float)delta / pulsesPerMm, 2);
    Serial.println(F(" mm..."));
    moveSteps(DIR_PRESS, delta, runSpeed);
  } else if (delta < 0) {
    Serial.print(F("  Lui "));
    Serial.print((float)(-delta) / pulsesPerMm, 2);
    Serial.println(F(" mm..."));
    moveSteps(DIR_RETRACT, -delta, runSpeed);
  } else {
    Serial.println(F("  Da o vi tri mong muon."));
  }

  // Hoan tat
  Serial.println(F(""));
  Serial.print(F(">> DA DEN VI TRI: "));
  Serial.print((float)currentPos / pulsesPerMm, 2);
  Serial.println(F(" mm"));
  Serial.println(F(">> Dong co giu luc. DOC CAM BIEN LUC bay gio."));
  Serial.println(F(""));
  Serial.println(F("Nhap quang duong moi (mm), '0' de ve Home,"));
  Serial.println(F("hoac nhan nut Home de dat lai goc:"));
}

// ================================================================
// SETUP
// ================================================================
void setup() {
  Serial.begin(9600);

  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
  pinMode(homeBtnPin, INPUT_PULLUP); // Cong tac: D2 <-> GND

  digitalWrite(stepPin, LOW);
  digitalWrite(dirPin, LOW);

  delay(500);
  Serial.println(F(""));
  Serial.println(F("================================================"));
  Serial.println(F("  THI NGHIEM EP CAM BIEN LUC"));
  Serial.println(F("  Arduino Nano + EZI-Servo (Step/Dir)"));
  Serial.println(F("================================================"));
  Serial.println(F(""));
  Serial.println(F("Thong so:"));
  Serial.print(F("  Vitme     : ")); Serial.print(mmPerRev, 1); Serial.println(F(" mm/vong"));
  Serial.print(F("  Resolution: ")); Serial.print(pulsesPerRev); Serial.println(F(" xung/vong"));
  Serial.print(F("  Do chinh xac: 1 xung = "));
  Serial.print(mmPerRev / pulsesPerRev, 4);
  Serial.println(F(" mm"));
  Serial.println(F(""));
  Serial.println(F("HUONG DAN:"));
  Serial.println(F("  1. Dua dong co ve vi tri goc bang tay (neu can)"));
  Serial.println(F("  2. NHAN NUT HOME (cong tac tren D2)"));
  Serial.println(F("  3. Nhap quang duong (mm) -> Enter"));
  Serial.println(F("  4. Dong co ve Home roi tien toi vi tri do"));
  Serial.println(F(""));
  Serial.println(F(">> NHAN NUT HOME de bat dau..."));
  Serial.println(F(""));
}

// ================================================================
// LOOP CHINH
// ================================================================
void loop() {

  // --- KIEM TRA NUT HOME ---
  // Cong tac noi D2 <-> GND, binh thuong HIGH (pullup), nhan = LOW
  if (digitalRead(homeBtnPin) == LOW) {
    delay(50); // Chong rung (debounce)
    if (digitalRead(homeBtnPin) == LOW) {
      setHome();
      // Cho tha nut
      while (digitalRead(homeBtnPin) == LOW) {
        delay(10);
      }
      delay(50);
    }
  }

  // --- DOC LENH TU SERIAL MONITOR ---
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input.length() == 0) return;

    // Kiem tra da Home chua
    if (!isHomed) {
      Serial.println(F("!! CHUA DAT HOME. Nhan nut Home truoc."));
      return;
    }

    // Chuyen sang so
    float distanceMm = input.toFloat();

    // Kiem tra gia tri hop le
    if (distanceMm < 0.0) {
      Serial.println(F("!! Quang duong phai >= 0."));
      return;
    }
    if (distanceMm > MAX_TRAVEL_MM) {
      Serial.print(F("!! Vuot qua gioi han (toi da "));
      Serial.print(MAX_TRAVEL_MM, 0);
      Serial.println(F(" mm)."));
      return;
    }

    // Truong hop nhap 0 -> chi ve Home
    if (distanceMm == 0.0) {
      Serial.println(F(">> Ve Home..."));
      goHome();
      Serial.println(F("Nhap quang duong moi (mm):"));
      return;
    }

    // Chay test case
    runTestCase(distanceMm);
  }
}