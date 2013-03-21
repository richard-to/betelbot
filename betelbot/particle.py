#!/usr/bin/env python

import ConfigParser
import json
import logging
import random
import signal

from math import atan2, cos, exp, pi, cos, sin, sqrt, tan

import cv2
import numpy as np

from tornado.ioloop import IOLoop

from map import simple_world
from topic import histogramTopic, moveTopic, senseTopic
from util import PubSubClient, signalHandler

class Particle:

    def __init__(self, length, grid, lookupTable):
        self.grid = grid
        self.lookupTable = lookupTable
        self.delta = [[1, 0], [0, 1], [1, 0], [0, 1]]
        self.length = length
        self.bearingNoise  = 0.0
        self.steeringNoise = 0.0
        self.distanceNoise = 0.0
        self.y = 0.0
        self.x = 0.0

    def randomizePosition(self):
        self.orientation = random.random() * 2.0 * pi
        gridY = self.grid.shape[0] - 1
        gridX = self.grid.shape[1] - 1
        while True:
            self.y = float(random.randint(0, gridY))            
            self.x = float(random.randint(0, gridX))
            if self.grid[self.y][self.x] > 0:
                break

    def set(self, y, x, orientation):
        if orientation < 0 or orientation >= 2.0 * pi:
            raise ValueError, 'Orientation must be in [0..2pi]'
        self.x = float(x)
        self.y = float(y)
        self.orientation = float(orientation)

    def setNoise(self, bNoise, sNoise, dNoise):
        self.bearingNoise  = float(bNoise)
        self.steeringNoise = float(sNoise)
        self.distanceNoise = float(dNoise)

    def measurementProb(self, measurements):
        predictedMeasurements = self.sense(0)
        error = 1.0
        for i in range(len(measurements)):
            error_bearing = abs(measurements[i] - predictedMeasurements[i])
            error_bearing = (error_bearing + pi) % (2.0 * pi) - pi

            error *= (exp(- (error_bearing ** 2) / (self.bearingNoise ** 2) / 2.0) /  
                      sqrt(2.0 * pi * (self.bearingNoise ** 2)))
        return error
    
    def move(self, motion):
        theta, d = motion 
        if d < 0:
            raise ValueError, 'Robot cant move backwards'
        d = float(d) + random.gauss(0.0, self.distanceNoise)
        theta = float(theta)   
        beta = (d/self.length) * tan(theta)
        if(abs(beta) < 0.001):
            orientation = (self.orientation + random.gauss(0.0, self.steeringNoise)) % 2.0 * pi            
            x = self.x + d * cos(orientation)
            y = self.y + d * sin(orientation)
        else:
            radius = d/beta        
            cx = float(self.x) - sin(self.orientation) * radius
            cy = float(self.y) + cos(self.orientation) * radius  
            x = cx + sin(self.orientation + beta) * radius
            y = cy - cos(self.orientation + beta) * radius
            orientation = (self.orientation + beta + random.gauss(0.0, self.steeringNoise)) % 2.0 * pi
        result = Particle(self.length, self.grid, self.lookupTable)
        result.set(round(x), round(y), orientation)
        result.setNoise(self.bearingNoise, self.steeringNoise, self.distanceNoise)
        return result
    
    def sense(self, hasNoise=False):
        Z = []
        count = len(self.delta) 
        index = self.y * self.grid.shape[1] * count + self.x * count
        for i in xrange(count):
            value = self.lookupTable[index]
            dy = value * self.delta[i][0]
            dx = value * self.delta[i][1]
            dist = (atan2(dy, dx) - self.orientation)
            if hasNoise:
                dist += random.gauss(0.0, self.bearingNoise)
            dist %= 2.0 * pi
            index += 1
            Z.append(dist)
        return Z

    def __repr__(self):
        return '[y=%.6s x=%.6s orient=%.6s]' % (str(self.y), str(self.x), 
                                                str(self.orientation))


class ParticleFilter:

    def __init__(self, length, grid, lookupTable, N=500):
        self.N = N
        self.length = length
        self.grid = grid
        self.lookupTable = lookupTable

    def makeParticles(self, bearingNoise, steeringNoise, distanceNoise, N=None):
        self.N = self.N if N is None else N
        self.particles = []
        for i in xrange(self.N):
            p = Particle(self.length, self.grid, self.lookupTable)
            p.randomizePosition()
            p.setNoise(bearingNoise, steeringNoise, steeringNoise)
            self.particles.append(p)        
    
    def getData(self):
        return [[p.y, p.x] for p in self.particles]

    def update(self, motion, measurements):
        updatedParticles = []
        for i in xrange(self.N):
            updatedParticles.append(self.particles[i].move(motion))
        self.particles = updatedParticles

        weight = []
        for i in range(self.N):
            weight.append(self.particles[i].measurementProb(measurements))

        self.particles = self.resample(self.particles, weight, self.N)  

    def resample(self, particles, weight, N):
        sampledParticles = []
        index = int(random.random() * N)
        beta = 0.0
        maxWeight = max(weight)
        for i in xrange(N):
            beta += random.random() * 2.0 * maxWeight
            while beta > weight[index]:
                beta -= weight[index]
                index = (index + 1) % N
            sampledParticles.append(particles[index])
        return sampledParticles       

def main():
    signal.signal(signal.SIGINT, signalHandler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')

    grid = cv2.imread(config.get('map-data', 'map'), cv2.CV_LOAD_IMAGE_GRAYSCALE)
    lookupTable = np.load(config.get('map-data', 'dmap'))

    length = config.getint('robot', 'length')

    bearingNoise = config.getfloat('particle', 'bearingNoise')
    steeringNoise = config.getfloat('particle', 'steeringNoise')
    distanceNoise = config.getfloat('particle', 'distanceNoise')

    particleFilter = ParticleFilter(length, grid, lookupTable)
    particleFilter.makeParticles(bearingNoise, steeringNoise, distanceNoise)

if __name__ == '__main__':
    main()
