#ifndef _BETELBOT_H_
#define _BETELBOT_H_

#include <Arduino.h>
#include <Servo.h>

#define SCAN_LEFT 180
#define SCAN_FORWARD 90
#define SCAN_RIGHT 0

#define PING_SLEEP 0
#define PING_SWEEP 1
#define PING_READY 2

#define ENCODER_BLACK false
#define ENCODER_WHITE true

#define ENCODER_SLEEP 0
#define ENCODER_ENCODE 1

class PingTurret {
public:
    PingTurret();
    void begin(Servo &base, const int sensorPin, int sweepDelay);
    void sweep(int pos);
    int status();
    void sleep();
    long scan();
    void scanForward();
    void scanLeft();
    void scanRight();  
private:
    Servo _base;
    int _status;
    int _sensorPin;
    int _sweepDelayOneStep;
    int _sweepDelayTwoStep;
    int _sweepDelay;
    unsigned long _startMillis;  
};

class ServoDriver {
public:
    ServoDriver();
    void begin(Servo &left, Servo &right);
    void forward();
    void reverse();
    void left();
    void right();
    void stop();
private:
    Servo _left;
    Servo _right;
};

class WheelEncoder {
public:
    WheelEncoder();
    void begin(float radius, int resolution, int sensorPin, int boundB, int boundW);
    void run();
    void encode();
    void sleep();
    int status();
private:
    int _status;    
    int _sensorPin;
    float _radius;
    int _resolution;
    float _distance;    
    int _ticks;
    bool _color;
    int _boundB;
    int _boundW;
};

#endif