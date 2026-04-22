// STM32 Bluepill - Read ADC A0, A1 and send via USB Serial

// Pin mapping:
// A0 -> PA0
// A1 -> PA1

const int adcPin1 = PA0;  // A0
const int adcPin2 = PA1;  // A1

void setup() {
  analogReadResolution(12);
  // Khởi tạo Serial USB
  Serial.begin(115200);


  // Đợi USB sẵn sàng (quan trọng với STM32)
  while (!Serial);

  Serial.println("STM32 ADC Dual Channel Start");
}

void loop() {
  // Đọc ADC (12-bit: 0–4095)
  int value1 = analogRead(adcPin1);
  int value2 = analogRead(adcPin2);

  // Chuyển sang điện áp (3.3V reference)
  float voltage1 = value1 * (3.3 / 4095.0);
  float voltage2 = value2 * (3.3 / 4095.0);

  // Gửi dữ liệu qua USB Serial
  //Serial.print("A0: ");
  //Serial.print(value1);
 // Serial.print(" (");
  Serial.print(voltage1, 3);
  Serial.print(" ");

 // Serial.print(" | A1: ");
  //Serial.print(value2);
  //Serial.print(" (");
  Serial.println(voltage2-2.3, 3);
  //Serial.println(" V)");

  delay(50);  // 0.5s
}