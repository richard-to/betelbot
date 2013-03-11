#include <Betelbot.h>
#include <Servo.h>

int resolution = 24;
int radius = 3.2;
int boundB = 20;
int boundW = 125;

int irPin = 0;

int rightservoPin = 10;
int leftservoPin = 9;

Servo rightservo;
Servo leftservo;

ServoDriver driver;
WheelEncoder encoder;

void setup() {
  rightservo.attach(rightservoPin);
  leftservo.attach(leftservoPin);
  driver.begin(leftservo, rightservo);
  driver.stop();
  encoder.begin(radius, resolution, irPin, boundB, boundW);
  encoder.run();
  driver.forward();
}

void loop() {
  if (encoder.status() == ENCODER_ENCODE) {
    encoder.encode();
  } else {
    driver.stop();
  }
}