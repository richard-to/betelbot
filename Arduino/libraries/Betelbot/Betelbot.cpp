#include "Betelbot.h"

static long microSecondsToCentimeters(long ms) {
    return ms / 29 / 2;
}

PingTurret::PingTurret() {
    _status = PING_SLEEP;
}

void PingTurret::begin(Servo &base, const int sensorPin, int sweepDelay) {
    _base = base;
    _sensorPin = sensorPin;
    _sweepDelayOneStep = sweepDelay;
    _sweepDelayTwoStep = sweepDelay * 2;
}

void PingTurret::sweep(int pos) {
    int currentPos = _base.read();
    if ((pos > SCAN_FORWARD && currentPos < SCAN_FORWARD) ||
            pos < SCAN_FORWARD && currentPos > SCAN_FORWARD ) {
        _sweepDelay = _sweepDelayTwoStep;
    } else {
        _sweepDelay = _sweepDelayOneStep;
    }
    _base.write(pos);
    _startMillis = millis();
    _status = PING_SWEEP;
}

void PingTurret::sleep() {
    _status = PING_SLEEP;
}

int PingTurret::status() {
    unsigned long elapsed = millis() - _startMillis;
    if (_status == PING_SWEEP && (millis() - _startMillis) >= _sweepDelay) {
        _status = PING_READY;
    }
    return _status;
}

long PingTurret::scan() {
    long duration;
    long cm;
    pinMode(_sensorPin, OUTPUT);
    digitalWrite(_sensorPin, LOW);
    delayMicroseconds(2);
    digitalWrite(_sensorPin, HIGH);
    delayMicroseconds(5);
    digitalWrite(_sensorPin, LOW);
    pinMode(_sensorPin, INPUT);
    duration = pulseIn(_sensorPin, HIGH);
    _status = PING_SLEEP;
    return microSecondsToCentimeters(duration);
}

void PingTurret::scanForward() {
    sweep(SCAN_FORWARD);
}

void PingTurret::scanLeft() {
    sweep(SCAN_LEFT);
}

void PingTurret::scanRight() {
    sweep(SCAN_RIGHT);
}


ServoDriver::ServoDriver() {

}

void ServoDriver::begin(Servo &left, Servo &right) {
    _left = left;
    _right = right;
}

void ServoDriver::forward() {
    _right.write(180);
    _left.write(65);
}

void ServoDriver::reverse() {
    _right.write(0);
    _left.write(180);
}

void ServoDriver::left() {
    _right.write(180);
    _left.write(180);
}

void ServoDriver::right() {
    _right.write(0);
    _left.write(0);
}

void ServoDriver::stop() {
    _right.write(90);
    _left.write(90);
}


WheelEncoder::WheelEncoder() {
    _ticks = 0;
    _status = ENCODER_SLEEP;
    _color = ENCODER_BLACK;
}

void WheelEncoder::begin(float radius, int resolution, int sensorPin, int boundB, int boundW) {
    _sensorPin = sensorPin;
    _radius = radius;
    _resolution = resolution;
    _distance = PI * 2 * _radius;
    _boundB = boundB;
    _boundW = boundW;
}

void WheelEncoder::run() {
    if (_status == ENCODER_ENCODE) {
        return;
    }
    _ticks = 0;
    _status = ENCODER_ENCODE;
    if (analogRead(_sensorPin) < _boundB) {
        _color = ENCODER_BLACK;
    } else {
        _color = ENCODER_WHITE;
    }
}

void WheelEncoder::encode() {
    if (_status == ENCODER_SLEEP) {
        return;
    }
    int value = analogRead(_sensorPin);
    if (value < _boundB && _color == ENCODER_BLACK) {
        _color = ENCODER_WHITE;
        _ticks++;
    } else if (value >= _boundW && _color == ENCODER_WHITE) {
        _color = ENCODER_BLACK;
        _ticks++;
    }
}

void WheelEncoder::sleep() {
    _status = ENCODER_SLEEP;
    _ticks = 0;
}

int WheelEncoder::status() {
    if (_status == ENCODER_ENCODE && _ticks == _resolution) {
        _status = ENCODER_SLEEP;
        _ticks = 0;
    }
    return _status;
}