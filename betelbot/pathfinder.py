#!/usr/bin/env python

import ConfigParser
import json
import logging
import random
import signal

import cv2
import numpy as np

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado.netutil import TCPServer

import jsonrpc

from client import BetelbotClientConnection
from jsonrpc import JsonRpcServer, JsonRpcConnection
from topic.default import PathTopic, DirectionsTopic
from util import Client, signalHandler


def convertPathToDirections(path, cmds, delta):
    # Converts an array of xy coordinates to Betelbot 
    # commands (hjkl).
    
    directions = []
    current = path[0]
    moves = path[1:]
    for move in moves:
        nextDelta = [move[0] - current[0], move[1] - current[1]]
        for i in range(len(delta)):
            if delta[i] == nextDelta:
                directions.append(cmds[i])
                break
        current = move
    return directions 


def euclideanDistance(x, y, goalX, goalY):
    # Heuristic function for A*.
    #
    # Calculates euclidean distance to measure
    # distance from goal.

    xDist = (x - goalX)
    yDist = (y - goalY)
    return xDist * xDist + yDist * yDist


class Pathfinder:
    # Searches for the shortest path given a discrete map.
    #
    # The map is a 2-d numpy array with x-cols and y-rows.
    #
    # For Betelbot, a grayscale map image is first converted to an array 
    # with 255(white) being an open cell and 0(black) representing walls.
    #
    # Using no heuristic function will fallback to using djikstra.
    #
    # The result of the search method will return an array of x,y coordinates that 
    # lead to the goal.
    #
    # For now, the cost parameter has no effect and will always be set to 1.

    def __init__(self, grid, openCell, heuristic=None, cost=1):
        # Initializes the pathfinder with a map and heuristic function.
        # 
        # The open cell is a byte in decimal between 0-255. This represents 
        # cells that can be visited. Everything is else is considered a wall or
        # obstacle.
        #
        # The grid is a numpy array that represents a map that is broken up into
        # discrete cells. For instance, each 20x20 block in the regular map 
        # would be equal to a 1x1 pixel in the grid.

        self.grid = grid
        self.openCell = openCell
        self.heuristic = heuristic or self.noHeuristic
        self.delta = [[0, -1],[1, 0],[-1, 0],[0, 1]]
        self.cost = 1     

    def search(self, start, goal):
        # Search for a path from start to goal.
        # Start and goal are valid x,y coordinates on the given map.
        #
        # The map and heuristic are given at initialization.
        #
        # If no path is found, this method will return False. If one is found, 
        # then array of x,y coordinates will be returned.

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
        path.reverse()                        
        return path

    def noHeuristic(self, x, y, goalX, goalY):
        # Dummy heuristic function for the case 
        # where no heuristic is given.
        
        return 0


class PathfinderSearchType:
    PATH = 1
    DIRECTIONS = 2
    BOTH = 3

class PathfinderMethod:
    # Methods supported by Pathfinder server

    # - Type: Request
    # - Method: search
    # - Params: start[x,y], goal[x,y], PathfinderSearchType
    # - Response: Depends on type   
    SEARCH = 'search'


class PathfinderServer(JsonRpcServer):
    # Pathfinder server is a service that finds a path from two points.
    #
    # Currently a specific map cannot be chosen, only what is loaded by the 
    # server on start up.
    #
    # Supported operations:
    #
    # - search([xStart, yStart], [xGoal, yGoal]): array of (x,y) coordinates
    # - directions([xStart, yStart], [xGoal, yGoal]): array of commands

    def onInit(self, **kwargs):
        logging.info('Pathfinder Server is running')
        self.data['masterConn'] = kwargs['masterConn']
        self.data['pathfinder'] = kwargs['pathfinder']
        self.data['cmds'] = kwargs['cmds']


class PathfinderConnection(JsonRpcConnection):

    def onInit(self, **kwargs):
        # Initializes pathfinder connection
        #
        # Need to have a pathfinder and a cmds array to
        # map to pathfinder deltas.

        self.logInfo('Received a new connection')

        self.masterConn = kwargs['masterConn']        
        self.pathfinder = kwargs['pathfinder']
        self.cmds = kwargs['cmds']
        self.pathTopic = kwargs.get('pathTopics', PathTopic())
        self.directionsTopic = kwargs.get('directionsTopic', DirectionsTopic())
        
        self.methodHandlers = {
            PathfinderMethod.SEARCH: self.handleSearch,
        }
        self.read()

    def handleSearch(self, msg):
        # Handles "search" and "getdirections" operation.
        #
        # Will send response back to caller, but will also
        # publish path and directions to any subscribers.

        id = msg.get(jsonrpc.Key.ID, None)
        method = msg.get(jsonrpc.Key.METHOD, None)
        params = msg.get(jsonrpc.Key.PARAMS, None)

        if id and len(params) == 3:
            start, goal, type = params
            placeholders = start + goal            
            
            self.logInfo('Searching for path from ({0},{1}) to ({2},{3})..'.format(*placeholders))
            
            path = self.pathfinder.search(start, goal)
            directions = convertPathToDirections(path, self.cmds, self.pathfinder.delta)
                       
            self.masterConn.publish(self.pathTopic.id, path)
            self.masterConn.publish(self.directionsTopic.id, directions)            
            
            result = []
            
            if type != PathfinderSearchType.DIRECTIONS:
                result.append(path)

            if type != PathfinderSearchType.PATH:
                result.append(directions)
            
            self.write(self.encoder.response(id, *result))

      
def main():

    signal.signal(signal.SIGINT, signalHandler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')
    openByte = config.getint('map', 'open')
    grid = cv2.imread(config.get('map-data', 'grid'), cv2.CV_LOAD_IMAGE_GRAYSCALE)
    cmds = list(config.get('general', 'cmds'))

    logger = logging.getLogger('')
    logger.setLevel(config.get('general', 'log_level'))
 
    pathfinder = Pathfinder(grid, openByte, euclideanDistance)

    serverPort = config.getint('pathfinder', 'port')

    client = Client('', config.getint('server', 'port'), BetelbotClientConnection)
    conn = client.connect()
    conn.register(PathfinderMethod.SEARCH, serverPort)

    server = PathfinderServer(connection=PathfinderConnection, 
        masterConn=conn, cmds=cmds, pathfinder=pathfinder)
    server.listen(serverPort)

    IOLoop.instance().start()


if __name__ == '__main__':
    main()
