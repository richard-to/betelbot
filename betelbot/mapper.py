#!/usr/bin/env python

import ConfigParser
import json

import cv2
import numpy as np


def loadMap(imageLocation, gridSize):
    image = cv2.imread(imageLocation, cv2.CV_LOAD_IMAGE_GRAYSCALE)
    rows, cols = image.shape
    mRows = rows + rows % gridSize
    mCols = cols + cols % gridSize  
    map = np.zeros([mRows, mCols], dtype=np.uint8)
    map[0:rows, 0:cols] = image
    return map


def buildGrid(map, gridSize, openByte, wallByte):
    mRows, mCols = map.shape
    gRows = mRows / gridSize
    gCols = mCols / gridSize
    lookupTable = [(i * gridSize, (i + 1) * gridSize - 1) 
        for i in xrange(gRows if gRows > gCols else gCols)]      
    grid = np.zeros([gRows, gCols], dtype=np.uint8)
    for i in xrange(gRows):
        iStart, iEnd = lookupTable[i]
        for g in xrange(gCols):
            gStart, gEnd = lookupTable[g]
            grid[i, g] = wallByte if np.any(map[iStart:iEnd, gStart:gEnd] != openByte) else openByte
    return grid 


def calcDistanceMap(map, dMap, wallByte):
    sIndex = 0
    cIndex = None
    ndMap = dMap.copy()
    walls = np.where(map == wallByte)
    for i in xrange(len(walls[0])):
        yIndex = walls[0][i]
        xIndex = walls[1][i]
        if yIndex != cIndex:
            cIndex = yIndex
            sIndex = 0
        if map[yIndex][xIndex] == wallByte:
            stop = xIndex - sIndex
            if stop == 0:
                ndMap[cIndex, sIndex] = 0
            else:
                ndMap[cIndex, sIndex:xIndex] = np.arange(stop - 1, -1, -1)
            sIndex = xIndex
    return ndMap


def calcDistanceMapRight(map, wallByte):
    rows, cols = map.shape
    dMap = np.tile(np.arange(cols)[::-1], (rows, 1))
    return calcDistanceMap(map, dMap, wallByte)


def calcDistanceMapLeft(map, wallByte):
    rows, cols = map.shape
    dMap = np.tile(np.arange(cols), (rows, 1))
    dMap = calcDistanceMap(np.fliplr(map), np.fliplr(dMap), wallByte)    
    return np.fliplr(dMap)


def calcDistanceMapDown(map, wallByte):
    rows, cols = map.shape
    dMap = np.tile(np.arange(rows)[::-1] , (cols, 1))
    return calcDistanceMap(map.transpose(), dMap, wallByte).transpose()


def calcDistanceMapUp(map, wallByte):
    rows, cols = map.shape
    dMap = np.tile(np.arange(rows) , (cols, 1))    
    dMap = calcDistanceMap(np.fliplr(map.transpose()), np.fliplr(dMap), wallByte)
    return np.fliplr(dMap).transpose()


def writeMapData(filename, data):
    file = open(filename, 'w')
    file.write(data)
    file.close()


def main():    
    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')
    wallByte = config.getint('map', 'wall')
    openByte = config.getint('map', 'open')
    gridSize = config.getint('map', 'gridSize')

    dir = config.get('map', 'dir')
    mapFile = ''.join([dir, config.get('map', 'map')])
    gridFile = ''.join([dir, config.get('map', 'gridData')])
    rdMapFile = ''.join([dir, config.get('map', 'rdmapData')])
    ldMapFile = ''.join([dir, config.get('map', 'ldmapData')])
    udMapFile = ''.join([dir, config.get('map', 'udmapData')])
    ddMapFile = ''.join([dir, config.get('map', 'ddmapData')])
    
    map = loadMap(mapFile, gridSize)

    grid = buildGrid(map, gridSize, openByte, wallByte)
    
    rdMap = calcDistanceMapRight(map, wallByte)
    ldMap = calcDistanceMapLeft(map, wallByte)
    udMap = calcDistanceMapUp(map, wallByte)
    ddMap = calcDistanceMapDown(map, wallByte)

    writeMapData(gridFile, json.dumps(grid.tolist()))
    writeMapData(rdMapFile, json.dumps(rdMap.tolist()))
    writeMapData(ldMapFile, json.dumps(ldMap.tolist()))
    writeMapData(udMapFile, json.dumps(udMap.tolist()))
    writeMapData(ddMapFile, json.dumps(ddMap.tolist()))

if __name__ == '__main__':
    main()