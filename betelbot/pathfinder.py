#!/usr/bin/env python

import ConfigParser
import json
import logging
import random
import signal

from tornado.ioloop import IOLoop

from map import simple_world
from topic import searchTopic, moveTopic, senseTopic
from util import PubSubClient, signal_handler


class PathFinder:

    def __init__(self, client, grid, heuristic):
        self.client = client
        self.grid = grid
        self.heuristic = heuristic
        self.delta = [[-1, 0 ], [ 0, -1], [ 1, 0 ], [ 0, 1 ]]
        self.cost = 1        

    def search(self, start, goal):
        grid = self.grid
        heuristic = self.heuristic
        delta = self.delta
        cost = self.cost
        openByte = 255
        wallByte = 0
 
        path = [[' ' for row in range(len(grid[0]))] for col in range(len(grid))]       
        closed = [[openByte for row in range(len(grid[0]))] for col in range(len(grid))]
        closed[start[0]][start[1]] = wallByte

        expand = [[-1 for row in range(len(grid[0]))] for col in range(len(grid))]

        x = start[0]
        y = start[1]
        g = 0
        f = g + heuristic(x, y, goal[0], goal[1])
        open = [[g, x, y, f]]

        found = False
        resign = False
        count = 0
        
        while not found and not resign:
            if len(open) == 0:
                resign = True
                return "Fail"
            else:
                open = sorted(open, key=lambda visit: visit[3], reverse=True) 
                next = open.pop()
                x = next[1]
                y = next[2]
                g = next[0]
                f = next[3]
                expand[x][y] = count
                count += 1
                
                if x == goal[0] and y == goal[1]:
                    found = True
                else:
                    for i in range(len(delta)):
                        x2 = x + delta[i][0]
                        y2 = y + delta[i][1]
                        if x2 >= 0 and x2 < len(grid) and y2 >= 0 and y2 < len(grid[0]):
                            if closed[x2][y2] == openByte and grid[x2][y2] == openByte:
                                g2 = g + cost
                                f = g2 + heuristic(x2, y2, goal[0], goal[1])
                                open.append([g2, x2, y2, f])
                                closed[x2][y2] = wallByte
        
        px = goal[0]
        py = goal[1]    
        path = [[py, px]] 
        pathFinished = False

        while pathFinished == False:
            prev = expand[px][py]
            if prev == 0:
                pathFinished = True
            else:
                for i in range(len(delta)):
                    dx = px + delta[i][0]
                    dy = py + delta[i][1]
                    if (dx >= 0 and dx < len(grid) and 
                            dy >= 0 and dy < len(grid[0]) and 
                            expand[dx][dy] >= 0 and expand[dx][dy] < prev):
                        path.append([dy, dx])
                        px = dx
                        py = dy
                        break
                count += 1

        return path


def euclideanDistance(x, y, goalX, goalY):
    return 0 #(x - goalX)**2 + (y - goalY)**2


def loadGridData(filename):
    file = open(filename, 'r')
    data = file.readlines()
    return json.loads(data[0])


def main():
    signal.signal(signal.SIGINT, signal_handler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')
    client = None
    grid = loadGridData(''.join([config.get('map', 'dir'), config.get('map-data', 'grid')]))
    init = [0, 14]
    goal = [15, 2]

    # client = PubSubClient('', config.getint('server', 'port'))
    pathfinder = PathFinder(client, grid, euclideanDistance)
    path = pathfinder.search(init, goal)
    print path
    # IOLoop.instance().start()


if __name__ == '__main__':
    main()
