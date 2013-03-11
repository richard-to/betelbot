#include <Betelbot.h>
#include <Serial.h>
#include <Servo.h>

#define PING_SWEEP_DELAY 425
#define KEY_SCAN_LEFT 'l'
#define KEY_SCAN_FORWARD 'f'
#define KEY_SCAN_RIGHT 'r'
#define KEY_SCAN 's'

const int baseServoPin = 9;
const int pingPin = 7;

Servo base;
PingTurret pingTurret;

void setup() {
  Serial.begin(9600);
  base.attach(baseServoPin);
  pingTurret.begin(base, pingPin, PING_SWEEP_DELAY);
  pingTurret.scanForward();
}

void loop() {
  int pingStatus;
  long result;
  char c;

  if (Serial.available()) {
    c = Serial.read();
  }
  
  if (c == KEY_SCAN) {
    Serial.println(pingTurret.scan());
  }
   
  pingStatus = pingTurret.status(); 
  if (pingStatus == PING_SLEEP) {
    if (c == KEY_SCAN_LEFT) {
      pingTurret.scanLeft();
    } else if (c == KEY_SCAN_FORWARD) {
      pingTurret.scanForward();
    } else if (c == KEY_SCAN_RIGHT) {
      pingTurret.scanRight();
    }
  } else if (pingStatus == PING_READY) {
    Serial.println(pingTurret.scan());
    pingTurret.sleep();
  }
}