#include "pantalla.h"

#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Wire.h>

#include "pines.h"

static Adafruit_SSD1306 oled(128, 64, &Wire, -1);
static bool ok = false;
static char linea1[22] = "", linea2[22] = "";
static float barra = -1;

static bool responde(uint8_t dir) {
  Wire.beginTransmission(dir);
  return Wire.endTransmission() == 0;
}

static void dibujar() {
  if (!ok) return;
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);
  oled.setTextSize(1);
  oled.setCursor(0, 0);
  oled.print("PIA RDP");
  oled.drawFastHLine(0, 10, 128, SSD1306_WHITE);
  oled.setCursor(0, 18);
  oled.print(linea1);
  oled.setCursor(0, 34);
  oled.print(linea2);
  if (barra >= 0) {
    oled.drawRect(0, 54, 128, 10, SSD1306_WHITE);
    oled.fillRect(2, 56, (int)(124 * (barra > 1 ? 1 : barra)), 6, SSD1306_WHITE);
  }
  oled.display();
}

uint8_t pantallaIniciar() {
  Wire.begin(PIN_SDA, PIN_SCL);
  uint8_t dir = responde(0x3C) ? 0x3C : responde(0x3D) ? 0x3D : 0;
  ok = dir && oled.begin(SSD1306_SWITCHCAPVCC, dir);
  dibujar();
  return ok ? dir : 0;
}

bool pantallaOk() { return ok; }

void pantallaMostrar(const char *l1, const char *l2) {
  strncpy(linea1, l1, sizeof linea1 - 1);
  strncpy(linea2, l2, sizeof linea2 - 1);
  linea1[sizeof linea1 - 1] = linea2[sizeof linea2 - 1] = 0;
  barra = -1;
  dibujar();
}

void pantallaBarra(float progreso) {
  barra = progreso;
  dibujar();
}
