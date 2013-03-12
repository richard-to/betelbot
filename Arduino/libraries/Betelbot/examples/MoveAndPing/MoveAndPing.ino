#include <Betelbot.h>
#include <Serial.h>
#include <Servo.h>

#define PING_SWEEP_DELAY 425

#define KEY_START 's'

int resolution = 24;
int radius = 3.2;
int boundB = 20;
int boundW = 125;

int irPin = 0;

int pingPin = 7;
int pingServoPin = 11;

int leftservoPin = 9;
int rightservoPin = 10;

Servo pingServo;
Servo rightservo;
Servo leftservo;

ServoDriver driver;
WheelEncoder encoder;
PingTurret pingTurret;

bool isRunning = false;
int revolutions = 0;

void setup() {
  Serial.begin(9600);

  pingServo.attach(pingServoPin);
  pingTurret.begin(pingServo, pingPin, PING_SWEEP_DELAY);
  pingTurret.scanRight();

  rightservo.attach(rightservoPin);
  leftservo.attach(leftservoPin);
  driver.begin(leftservo, rightservo);
  driver.stop();

  encoder.begin(radius, resolution, irPin, boundB, boundW);
}

void loop() {
  char c;
  if (Serial.available() && isRunning == false) {
    c = Serial.read();
    if (c == KEY_START) {
      isRunning = true;
      Serial.println(pingTurret.scan());
      encoder.run();
      driver.forward();
    }
  }
  
  if (isRunning == true) {
    if (encoder.status() == ENCODER_ENCODE) {
      encoder.encode();
    } else {
      isRunning = false;
      driver.stop();
      Serial.println(pingTurret.scan());
    }
  }
}