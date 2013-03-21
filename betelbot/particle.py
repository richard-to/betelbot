#!/usr/bin/env python

import ConfigParser
import logging
import random
import signal

from math import *

import numpy as np

from tornado.ioloop import IOLoop

from map import simple_world
from topic import histogramTopic, moveTopic, senseTopic
from util import PubSubClient, signalHandler, loadGridData


max_steering_angle = pi / 4.0 # You do not need to use this value, but keep in mind the limitations of a real car.
bearing_noise = 0.1 # Noise parameter: should be included in sense function.
steering_noise = 0.1 # Noise parameter: should be included in move function.
distance_noise = 5.0 # Noise parameter: should be included in move function.

tolerance_xy = 15.0 # Tolerance for localization in the x and y directions.
tolerance_orientation = 0.25 # Tolerance for orientation.

class Particle:

    def __init__(self, grid, lookupTable):
        self.grid = grid
        self.lookupTable = lookupTable
        while True;
            self.x = random.randint(0, len(grid[0]) - 1)
            self.y = random.randint(0, len(grid) - 1)
            if grid[x][y] > 0:
                break
        self.orientation = random.random() * 2.0 * pi
        self.length = length
        self.bearing_noise  = 0.0
        self.steering_noise = 0.0
        self.distance_noise = 0.0

    def set(self, new_x, new_y, new_orientation):
        if new_orientation < 0 or new_orientation >= 2 * pi:
            raise ValueError, 'Orientation must be in [0..2pi]'
        self.x = float(new_x)
        self.y = float(new_y)
        self.orientation = float(new_orientation)

    def set_noise(self, new_b_noise, new_s_noise, new_d_noise):
        self.bearing_noise  = float(new_b_noise)
        self.steering_noise = float(new_s_noise)
        self.distance_noise = float(new_d_noise)

    def measurement_prob(self, measurements):
        predicted_measurements = self.sense(0)
        error = 1.0
        for i in range(len(measurements)):
            error_bearing = abs(measurements[i] - predicted_measurements[i])
            error_bearing = (error_bearing + pi) % (2.0 * pi) - pi  
            error *= (exp(- (error_bearing ** 2) / (self.bearing_noise ** 2) / 2.0) /  
                      sqrt(2.0 * pi * (self.bearing_noise ** 2)))
        return error
    
    def __repr__(self):
        return '[x=%.6s y=%.6s orient=%.6s]' % (str(self.x), str(self.y), 
                                                str(self.orientation))
    
    def move(self, motion):
        theta, d = motion 
        if d < 0:
            raise ValueError, 'Robot cant move backwards'
        d = float(d) + random.gauss(0.0, self.distance_noise)
        theta = float(theta)   
        beta = (d/self.length) * tan(theta)
        if(abs(beta) < 0.001):
            orientation = (self.orientation + random.gauss(0.0, self.steering_noise)) % (2 * pi)            
            x = self.x + d * cos(orientation)
            y = self.y + d * sin(orientation)
        else:
            radius = d/beta        
            cx = self.x - sin(self.orientation) * radius
            cy = self.y + cos(self.orientation) * radius  
            x = cx + sin(self.orientation + beta) * radius
            y = cy - cos(self.orientation + beta) * radius
            orientation = (self.orientation + beta + random.gauss(0.0, self.steering_noise)) % (2 * pi)

        result = Particle(self.length)
        result.set(int(x), int(y), orientation)
        result.set_noise(self.bearing_noise, self.steering_noise, self.distance_noise)
        return result
    
    def sense(self, has_noise = 1):
        Z = []
        for i in range(len(landmarks)):
            dist = (atan2(landmarks[i][0] - self.y, landmarks[i][1] - self.x) - self.orientation)
            if has_noise:
                dist += random.gauss(0.0, self.bearing_noise)
            dist %= 2 * pi
            Z.append(dist)
        return Z


class ParticleFilter:

    def __init__(self, client):
        self.client = client

def loadGridData(filename):
    file = open(filename, 'r')
    data = file.readlines()
    return np.array(json.loads(data[0]))


def main():
    #signal.signal(signal.SIGINT, signal_handler)

    #config = ConfigParser.SafeConfigParser()
    #config.read('config/default.cfg')

    # client = PubSubClient('', config.getint('server', 'port'))
    # particleFilter = ParticleFilter(client)

    # IOLoop.instance().start()
    grid = loadGridData(''.join([config.get('map', 'dir'), config.get('map-data', 'grid')]))
    lookupTbl = [ 
        loadGridData(''.join([config.get('map', 'dir'), config.get('map-data', 'ldmap')])),
        loadGridData(''.join([config.get('map', 'dir'), config.get('map-data', 'rdmap')])),
        loadGridData(''.join([config.get('map', 'dir'), config.get('map-data', 'udmap')])),
        loadGridData(''.join([config.get('map', 'dir'), config.get('map-data', 'ddmap')]))
    ]

if __name__ == '__main__':
    main()
