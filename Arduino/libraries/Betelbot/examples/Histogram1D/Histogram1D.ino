#include <Serial.h>
#include <Servo.h>
#include <SPI.h>

#include <WiFly.h>

#include <Betelbot.h>
#include "settings.h"

#define PING_SWEEP_DELAY 450
#define KEY_FORWARD 'k'

#define SEND_MOVE "m "
#define SEND_SENSE "s "

const char *ssid = SSID;
const char *pass = PASS;
 
const char *serverAddress = SERVER; 
const int serverPort = PORT;

int resolution = 24;
float radius = 3.2;
int boundB = 20;
int boundW = 40;

int irPin = 0;

int pingPin = 6;
int pingServoPin = 5;

int leftservoPin = 2;
int rightservoPin = 3;

Servo pingServo;
Servo rightservo;
Servo leftservo;

ServoDriver driver;
WheelEncoder encoder;
PingTurret pingTurret;

WiFlyClient client;

bool isRunning = false;

void setup() {
  WiFly.begin();
  WiFly.join(ssid, pass, true);
  client.connect(serverAddress, serverPort);

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
  if (client.available()) {
    c = client.read();
  }
  
  if (c == KEY_FORWARD && isRunning == false) {
    isRunning = true;
     encoder.run();
     driver.forward();
  }
  
  if (isRunning == true) {
    if (encoder.status() == ENCODER_ENCODE) {
      encoder.encode();
    } else {
      isRunning = false;
      driver.stop();
      client.print(SEND_MOVE);
      client.println(KEY_FORWARD);
      client.print(SEND_SENSE);
      client.println(pingTurret.scan());
    }
  }
}