#!/usr/bin/env python

import json
import logging
import random
import signal

from math import atan2, cos, exp, pi, cos, sin, sqrt, tan

import cv2
import numpy as np

from numpy import inf
from tornado.ioloop import IOLoop

import jsonrpc

from client import BetelbotClientConnection
from config import JsonConfig
from jsonrpc import JsonRpcServer, JsonRpcConnection
from topic.default import ParticleTopic
from util import Client, signalHandler


def convertToMotion(start, dest, gridSize):
    rotationDist = {
        'l': 0,
        'j': 1,
        'h': 2,
        'k': 3
    }
    rotation = 0
    dist = rotationDist[dest] - rotationDist[start]

    if dist == 0:
        rotation = 0
    elif dist == 1 or dist == -3:
        rotation = pi/2
    elif dist == 2 or dist == -2:
        rotation = pi
    elif dist == 3 or dist == -1:
        rotation = -pi/2

    return [rotation, gridSize]


class Particle:

    def __init__(self, length, grid, lookupTable):
        self.grid = grid
        self.lookupTable = lookupTable
        self.delta = [[1, 0], [0, 1], [1, 0], [0, 1]]
        self.length = length
        self.forwardNoise  = 0.0
        self.turnNoise = 0.0
        self.senseNoise = 0.0
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

    def setNoise(self, fNoise, tNoise, sNoise):
        self.forwardNoise  = float(fNoise)
        self.turnNoise = float(tNoise)
        self.senseNoise = float(sNoise)

    def move(self, motion):
        turn, forward = motion

        if forward < 0:
            raise ValueError, 'Robot cant move backwards'

        orientation = self.orientation + float(turn) + random.gauss(0.0, self.turnNoise)
        orientation %= 2 * pi

        dist = float(forward) + random.gauss(0.0, self.forwardNoise)
        x = self.x + (round(cos(orientation), 15) * dist)
        y = self.y + (round(sin(orientation), 15) * dist)
        y %= self.grid.shape[0]
        x %= self.grid.shape[1]
        particle = Particle(self.length, self.grid, self.lookupTable)
        particle.set(round(y), round(x), orientation)
        particle.setNoise(self.forwardNoise, self.turnNoise, self.senseNoise)
        return particle

    def sense(self, hasNoise=False):
        Z = []
        if (self.y >= 0 and self.y < self.grid.shape[0] and
            self.x >= 0 and self.x < self.grid.shape[1] and
            self.grid[self.y][self.x] > 0):
            count = len(self.delta)
            index = self.y * self.grid.shape[1] * count + self.x * count
            for i in xrange(count):
                value = self.lookupTable[index]
                dy = value * self.delta[i][0]
                dx = value * self.delta[i][1]
                index += 1
                dist = dy or dx
                if hasNoise:
                    dist += random.gauss(0.0, self.senseNoise)
                Z.append(dist)
        else:
            Z = [inf, inf, inf, inf]
        return Z

    def measurementProb(self, measurements):
        prob = 1.0
        Z = self.sense()
        for i in xrange(len(Z)):
            if measurements[i] is not None:
                prob *= self.gaussian(float(Z[i]), self.senseNoise, float(measurements[i]))
        return prob

    def gaussian(self, mu, sigma, x):
        return exp(- ((mu - x) ** 2) / (sigma ** 2) / 2.0) / sqrt(2.0 * pi * (sigma ** 2))

    def __repr__(self):
        return '[y=%.6s x=%.6s orient=%.6s]' % (str(self.y), str(self.x),
                                                str(self.orientation))


class ParticleFilter:

    def __init__(self, length, grid, lookupTable, N=500):
        self.N = N
        self.length = length
        self.grid = grid
        self.lookupTable = lookupTable

    def makeParticles(self, forwardNoise, turnNoise, senseNoise, N=None):
        self.N = self.N if N is None else N
        self.particles = []
        for i in xrange(self.N):
            p = Particle(self.length, self.grid, self.lookupTable)
            p.randomizePosition()
            p.setNoise(forwardNoise, turnNoise, senseNoise)
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

    def getPosition(self, p):
        x = 0.0
        y = 0.0
        orientation = 0.0
        for i in range(len(p)):
            x += p[i].x
            y += p[i].y
            orientation += (((p[i].orientation - p[0].orientation + pi) % (2.0 * pi))
                            + p[0].orientation - pi)
        return [y / len(p), x / len(p), orientation / len(p)]


class ParticleFilterMethod(object):
    UPDATEPARTICLES = 'updateparticles'


class ParticleFilterServer(JsonRpcServer):

    def onInit(self, **kwargs):
        logging.info('ParticleFilter Server is running')
        self.data['masterConn'] = kwargs['masterConn']
        self.data['particleFilter'] = kwargs['particleFilter']
        self.data['particleTopic'] = kwargs['particleTopic']


class ParticleFilterConnection(JsonRpcConnection):

    def onInit(self, **kwargs):

        self.logInfo('Received a new connection')

        self.masterConn = kwargs['masterConn']
        self.particleFilter = kwargs['particleFilter']
        self.particleTopic = kwargs['particleTopic']

        self.methodHandlers = {
            ParticleFilterMethod.UPDATEPARTICLES: self.handleUpdateParticles
        }

        self.read()

    def handleUpdateParticles(self, msg):

        id = msg.get(jsonrpc.Key.ID, None)
        method = msg.get(jsonrpc.Key.METHOD, None)
        params = msg.get(jsonrpc.Key.PARAMS, None)

        if id and len(params) == 2:
            motion, measurements = params

            self.logInfo('Updating particle filter')

            self.particleFilter.update(motion, measurements)
            particles = self.particleFilter.getData()

            self.masterConn.publish(self.particleTopic.id, particles)
            self.write(self.encoder.response(id, particles))


def main():
    signal.signal(signal.SIGINT, signalHandler)

    cfg =JsonConfig()

    logger = logging.getLogger('')
    logger.setLevel(cfg.general.logLevel)

    map = cv2.imread(cfg.mapData.map, cv2.CV_LOAD_IMAGE_GRAYSCALE)
    lookupTable = np.load(cfg.mapData.dmap)

    length = cfg.robot.length

    forwardNoise = cfg.particle.forwardnoise
    turnNoise = cfg.particle.turnnoise
    senseNoise = cfg.particle.sensenoise

    particleTopic = ParticleTopic()

    particleFilter = ParticleFilter(length, map, lookupTable)
    particleFilter.makeParticles(forwardNoise, turnNoise, senseNoise)
    particles = particleFilter.getData()

    serverPort = cfg.particle.port

    client = Client('', cfg.server.port, BetelbotClientConnection)
    conn = client.connect()
    conn.register(ParticleFilterMethod.UPDATEPARTICLES, serverPort)
    conn.publish(particleTopic.id, particles)

    server = ParticleFilterServer(connection=ParticleFilterConnection,
        masterConn=conn, particleFilter=particleFilter, particleTopic=particleTopic)
    server.listen(serverPort)

    IOLoop.instance().start()


if __name__ == '__main__':
    main()
