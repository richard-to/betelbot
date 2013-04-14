function drawMapImage(canvas, data, scale, opacity) {
    opacity = opacity || 255;
    scale = scale || 1;

    var originX = 0;
    var originY = 0;
    var rgbaBytes = 4;

    var context = canvas.getContext('2d');
    var imageData = context.getImageData(originX, originY, canvas.width, canvas.height);

    for (var y = 0; y < canvas.height; ++y) {
        var index = Math.floor(y / scale);
        var col = y * canvas.width * rgbaBytes;
        _.each(data[index], function(element) {
            _(scale).times(function(n) {
                var color = (element < 200) ? 240 : element;
                imageData.data[col++] = color;
                imageData.data[col++] = color;
                imageData.data[col++] = color;
                imageData.data[col++] = opacity;
            });
        });
    }
    context.putImageData(imageData, originX, originY);
}

function drawGrid(canvas, gridSize, scale) {
    scale = scale || 1;
    gridSize = gridSize || 20;

    var color = '#ccc';
    var originX = 0;
    var originY = 0;

    var scaledGridSize = gridSize * scale;
    var context = canvas.getContext('2d');

    context.strokeStyle = color;

    _(Math.floor(canvas.width / scaledGridSize) + 1).times(function(n) {
        context.beginPath();
        context.lineWidth = 1;
        context.moveTo(n * scaledGridSize, originY);
        context.lineTo(n * scaledGridSize, canvas.height);
        context.stroke();
    });

    _(Math.floor(canvas.height / scaledGridSize) + 1).times(function(n) {
        context.beginPath();
        context.lineWidth = 1;
        context.moveTo(originX, n * scaledGridSize);
        context.lineTo(canvas.width, n * scaledGridSize);
        context.stroke();
    });
}

function drawParticles(canvas, particles, scale, size) {
    scale = scale || 1;
    size = size || 1;

    var radius = size * scale;
    var scaledSize = size * scale;
    var context = canvas.getContext('2d');

    _.each(particles, function(element) {
        context.beginPath();
        context.arc(element[1] * scale, element[0] * scale, size, 0, 2 * Math.PI, false);
        context.fillStyle = 'rgba(0,0,0,0)';
        context.fill();
        context.lineWidth = 2;
        context.strokeStyle = 'rgba(20,20,20,.4)';
        context.stroke();
    });
}

function drawProbabilities(canvas, probabilities, gridSize, scale) {
    scale = scale || 1;
    gridSize = gridSize || 20;

    var textSettings = {
        font: '13px arial',
        fillStyle: '#333',
        textAlign: 'center',
        textBaseline: 'middle'
    };

    var scaledGridSize = gridSize * scale;
    var context = canvas.getContext('2d');

    context.font = textSettings.font;
    context.fillStyle = textSettings.fillStyle;
    context.textAlign = textSettings.textAlign;
    context.textBaseline = textSettings.textBaseline;

    for (var y = 0; y < probabilities.length; ++y) {
        for (var x = 0; x < probabilities[y].length; ++x) {
            if (probabilities[y][x] != null) {
                context.fillText(probabilities[y][x],
                    gridSize + (x * scaledGridSize),
                    gridSize + (y * scaledGridSize));
            }
        }
    }
}

function drawHeatmap(canvas, probabilities, gridSize, scale) {
    scale = scale || 1;
    gridSize = gridSize || 20;

    var textSettings = {
        font: '13px arial',
        fillStyle: '#333',
        textAlign: 'center',
        textBaseline: 'middle'
    };

    var scaledGridSize = gridSize * scale;
    var context = canvas.getContext('2d');

    context.font = textSettings.font;
    context.fillStyle = textSettings.fillStyle;
    context.textAlign = textSettings.textAlign;
    context.textBaseline = textSettings.textBaseline;

    for (var y = 0; y < probabilities.length; ++y) {
        for (var x = 0; x < probabilities[y].length; ++x) {
            if (probabilities[y][x] != null) {
                context.beginPath();
                color = Math.floor(255 * probabilities[y][x]);
                context.fillStyle = 'rgba(' + color + ', 0, 0, 1)';
                context.rect(x * scaledGridSize + 1,
                    y * scaledGridSize + 1,
                    scaledGridSize - scale, scaledGridSize - scale);
                context.fill();
            }
        }
    }
}

function drawLinePath(canvas, path, gridSize, scale) {
    scale = scale || 1;
    gridSize = gridSize || 20;

    var radius = 2 * scale;
    var scaledGridSize = gridSize * scale;
    var context = canvas.getContext('2d');
    var lineColor = 'rgba(40, 50, 40, 1)';
    context.strokeStyle = lineColor;
    for (i = 1; i < path.length; i++) {
        var x1 = path[i - 1][1];
        var y1 = path[i - 1][0];
        var x2 = path[i][1];
        var y2 = path[i][0];

        context.beginPath();
        context.moveTo(x1 * scaledGridSize + scaledGridSize/2, y1 * scaledGridSize + scaledGridSize/2);
        context.lineTo(x2 * scaledGridSize + scaledGridSize/2, y2 * scaledGridSize + scaledGridSize/2);
        context.stroke();
        context.fill();
    }

    context.beginPath();
    context.arc(
        path[0][1] * scaledGridSize + scaledGridSize/2,
        path[0][0] * scaledGridSize + scaledGridSize/2, radius, 0, 2 * Math.PI, false);
    context.fillStyle = lineColor;
    context.fill();

    context.beginPath();
    context.arc(
        path[path.length - 1][1] * scaledGridSize + scaledGridSize/2,
        path[path.length - 1][0] * scaledGridSize + scaledGridSize/2, radius, 0, 2 * Math.PI, false);
    context.fillStyle = lineColor;
    context.fill();
}

function drawPath(canvas, path, gridSize, scale) {
    scale = scale || 1;
    gridSize = gridSize || 20;

    var scaledGridSize = gridSize * scale;
    var context = canvas.getContext('2d');

    context.fillStyle = 'rgba(100, 100, 100, .4)';
    for (i = 0; i < path.length; i++) {
        context.beginPath();
        context.rect(path[i][1] * scaledGridSize + 1,
            path[i][0] * scaledGridSize + 1,
            scaledGridSize - scale, scaledGridSize - scale);
        context.fill();
    }
}

function refreshCanvas(context, canvas, map, path, particles) {
    var scale = 2;

    context.clearRect(0, 0, canvas.width, canvas.height);

    if (map) {
        drawMapImage(canvas, map, scale);
        drawGrid(canvas, 20, scale);
    }

    if (path) {
        drawLinePath(canvas, path, 20, scale);
    }

    if (particles) {
        drawParticles(canvas, particles, scale, 6);
    }
}

var canvas = document.getElementById('map');
var context = canvas.getContext('2d');

var ws = null;
var map = null;
var path = null;
var particles = null;

$.get('/static/data/map.json', function(data) {
    map = data;
    refreshCanvas(context, canvas, map, path, particles);
});

ws = new WebSocket("ws://localhost:8889/socket");

ws.onopen = function() {

};

ws.onclose = function() {

};

ws.onmessage = function(event) {
    var response = JSON.parse(event.data);
    switch(response.method) {
        case 'particle':
            particles = response.params[0];
            refreshCanvas(context, canvas, map, path, particles);
        break;
        case 'path':
            path = response.params[0];
            refreshCanvas(context, canvas, map, path, particles);
        break;
    };
};
