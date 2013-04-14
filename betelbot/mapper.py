#!/usr/bin/env python

import json

import cv2
import numpy as np

from config import JsonConfig

def loadMap(imageLocation, gridSize):
    # Converts image file to numpy matrix

    image = cv2.imread(imageLocation, cv2.CV_LOAD_IMAGE_GRAYSCALE)
    rows, cols = image.shape
    mRows = rows + rows % gridSize
    mCols = cols + cols % gridSize
    map = np.zeros([mRows, mCols], dtype=np.uint8)
    map[0:rows, 0:cols] = image
    return map


def buildGrid(map, gridSize, openByte, wallByte):
    # Scales map matrix down to discrete blocks specified by gridSize.
    # If area has all open bytes, then it will be marked as an open byte.
    # If area has all at least one wall byte, then it will be marked as a wall byte.

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
    # Calculates the distance from a pixel to a wall bytes for all pixels in map.

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
    # Calculates distance to the right wall of map

    rows, cols = map.shape
    dMap = np.tile(np.arange(cols, dtype=np.uint16)[::-1], (rows, 1))
    return calcDistanceMap(map, dMap, wallByte)


def calcDistanceMapLeft(map, wallByte):
    # Calculates distance to the left wall of map

    rows, cols = map.shape
    dMap = np.tile(np.arange(cols, dtype=np.uint16), (rows, 1))
    dMap = calcDistanceMap(np.fliplr(map), np.fliplr(dMap), wallByte)
    return np.fliplr(dMap)


def calcDistanceMapDown(map, wallByte):
    # Calculates distance to the south wall of map

    rows, cols = map.shape
    dMap = np.tile(np.arange(rows, dtype=np.uint16)[::-1] , (cols, 1))
    return calcDistanceMap(map.transpose(), dMap, wallByte).transpose()


def calcDistanceMapUp(map, wallByte):
    # Calculates distance to the north wall of map

    rows, cols = map.shape
    dMap = np.tile(np.arange(rows, dtype=np.uint16) , (cols, 1))
    dMap = calcDistanceMap(np.fliplr(map.transpose()), np.fliplr(dMap), wallByte)
    return np.fliplr(dMap).transpose()


def mergeDistanceMaps(dmaps):
    # Merges all distance maps into one large array (left, down, up, right)

    mapY, mapX = dmaps[0].shape
    count = len(dmaps)
    size = dmaps[0].size * count * count
    data = np.empty([size], np.uint16)
    cols = 0
    for y in xrange(mapY):
        for x in xrange(mapX):
            for m in dmaps:
                data[cols] = m[y, x]
                cols += 1
    return data


def main():
    cfg = JsonConfig()
    wallByte = cfg.map.wall
    openByte = cfg.map.open
    gridSize = cfg.map.gridsize
    mapImage = cfg.map.image
    mapFile = cfg.mapData.map
    gridFile= cfg.mapData.grid
    dmapFile = cfg.mapData.dmap

    map = loadMap(mapImage, gridSize)
    cv2.imwrite(mapFile, map)

    grid = buildGrid(map, gridSize, openByte, wallByte)
    cv2.imwrite(gridFile, grid)

    dmaps = [
        calcDistanceMapLeft(map, wallByte),
        calcDistanceMapDown(map, wallByte),
        calcDistanceMapUp(map, wallByte),
        calcDistanceMapRight(map, wallByte)
    ]
    dmap = mergeDistanceMaps(dmaps)
    np.save(dmapFile, dmap)


if __name__ == '__main__':
    main()