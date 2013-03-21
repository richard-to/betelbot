#!/usr/bin/env python

import ConfigParser
import json
import logging
import random
import signal

import cv2
import numpy as np

from tornado.ioloop import IOLoop

from map import simple_world
from topic import searchTopic, moveTopic, senseTopic
from util import PubSubClient, signalHandler


class PathFinder:

    def __init__(self, grid, openCell, heuristic=None, cost=1):
        self.grid = grid
        self.openCell = openCell
        self.heuristic = heuristic if heuristic is not None else self.noHeuristic
        self.delta = [[-1, 0 ], [ 0, -1], [ 1, 0 ], [ 0, 1 ]]
        self.cost = cost     

    def search(self, start, goal):
        gridY, gridX = self.grid.shape        
        closed = np.zeros(self.grid.shape, bool)
        expand = np.empty(self.grid.shape)
        expand.fill(-1)     

        y, x = start
        goalY, goalX = goal
        g = 0
        f = g + self.heuristic(x, y, goalY, goalX)
        open = [[g, y, x, f]]
        closed[y][x] = True
        
        found = False
        resign = False
        count = 0
        
        while not found and not resign:
            if len(open) == 0:
                resign = True
                return False
            else:
                open = sorted(open, key=lambda visit: visit[3], reverse=True) 
                next = open.pop()
                g, y, x, f = next
                expand[y][x] = count
                count += 1
                
                if y == goalY and x == goalX:
                    found = True
                else:
                    for pos in self.delta:
                        x2 = x + pos[1]
                        y2 = y + pos[0]
                        if (x2 >= 0 and x2 < gridX and y2 >= 0 and y2 < gridY and
                                closed[y2][x2] == False and self.grid[y2][x2] == self.openCell):
                            g2 = g + self.cost
                            f = g2 + self.heuristic(x2, y2, goal[1], goal[0])
                            open.append([g2, y2, x2, f])
                            closed[y2][x2] = True

        py, px = goal  
        path = [[py, px]] 
        pathFinished = False

        while pathFinished == False:
            count = expand[py][px]
            if count == 0:
                pathFinished = True
            else:
                for pos in self.delta:
                    dx = px + pos[1]
                    dy = py + pos[0]
                    if (dx >= 0 and dx < gridX and 
                            dy >= 0 and dy < gridY and 
                            expand[dy][dx] >= 0 and expand[dy][dx] < count):
                        path.append([dy, dx])
                        px = dx
                        py = dy
                        break

        return path

    def noHeuristic(self, x, y, goalX, goalY):
        return 0


def euclideanDistance(x, y, goalX, goalY):
    xDist = (x - goalX)
    yDist = (y - goalY)
    return xDist * xDist + yDist * yDist


def main():
    signal.signal(signal.SIGINT, signalHandler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')
    openByte = config.getint('map', 'open')
    gridFile = ''.join([config.get('map', 'dir'), config.get('map-data', 'grid')])
    grid = cv2.imread(gridFile, cv2.CV_LOAD_IMAGE_GRAYSCALE)
    
    start = [int(num) for num in config.get('map', 'start').split(',')]
    goal = [int(num) for num in config.get('map', 'goal').split(',')]

    # client = PubSubClient('', config.getint('server', 'port'))
    pathfinder = PathFinder(grid, openByte, euclideanDistance)
    path = pathfinder.search(start, goal)
    print path
    # IOLoop.instance().start()


if __name__ == '__main__':
    main()
