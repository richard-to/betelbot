(function(window, undefined)) {

    var Betelbot = window.Betelbot || {};
    var Visualizer = {};

    var Renderer = function(canvas, settings) {
        this.CONTEXT_2D = '2d';
        this.RGBA_BYTES = 4;
        this.OPAQUE_BYTE = 255;
        this.ANGLE_0_RAD = 0;
        this.ANGLE_2PI_RAD = 2 * Math.PI;

        var defaults = {
            scale: 2,
            gridsize: 20,
            map: {
                openColor: 255,
                wallColor: 240,
                wallThreshold: 200
            },
            grid: {
                color: '#ccc',
                lineWidth: 1
            },
            particles: {
                radius: 6,
                lineWidth: 2,
                fillStyle: 'rgba(0,0,0,0)',
                strokeStyle: 'rgba(20,20,20,.4)'
            },
            histogram: {
                font: '13px arial',
                fillStyle: '#333',
                textAlign: 'center',
                textBaseline: 'middle'
            },
            linePath: {
                radius: 2,
                color: 'rgba(40, 50, 40, 1)'
            }
        };

        this.settings = $.extend(true, defaults, settings);

        this.canvas = canvas;
        this.context = canvas.getContext(this.CONTEXT_2D);
    };

    Renderer.prototype.map = function(data) {
        var rgbaBytes = this.RGBA_BYTES;
        var alphaOpaque = this.OPAQUE_BYTE;

        var scale = this.settings.scale;

        var wallThreshold = this.settings.map.wallThreshold;
        var openColorByte = this.settings.map.openColorByte;
        var wallColorByte = this.settings.map.wallColorByte;

        var canvas = this.settings.canvas;
        var context = this.settings.context;

        var originX = 0;
        var originY = 0;

        var imageData = context.getImageData(originX, originY, canvas.width, canvas.height);

        for (var y = 0; y < canvas.height; ++y) {
            var index = Math.floor(y / scale);
            var col = y * canvas.width * rgbaBytes;
            _.each(data[index], function(element) {
                _(scale).times(function(n) {
                    var color = (element < wallThreshold) ? wallColorByte : openColorByte;
                    imageData.data[col++] = color;
                    imageData.data[col++] = color;
                    imageData.data[col++] = color;
                    imageData.data[col++] = alphaOpaque;
                });
            });
        }
        context.putImageData(imageData, originX, originY);
    };

    Renderer.prototype.grid = function() {
        var scale = this.settings.scale;
        var gridsize = this.settings.gridsize;

        var color = this.settings.grid.color;
        var lineWidth = this.settings.grid.lineWidth;

        var canvas = this.settings.canvas;
        var context = this.settings.context;

        var originX = 0;
        var originY = 0;

        context.strokeStyle = color;
        context.lineWidth = lineWidth;

        _(Math.floor(canvas.width / scaledGridSize) + 1).times(function(n) {
            context.beginPath();
            context.moveTo(n * scaledGridSize, originY);
            context.lineTo(n * scaledGridSize, canvas.height);
            context.stroke();
        });

        _(Math.floor(canvas.height / scaledGridSize) + 1).times(function(n) {
            context.beginPath();
            context.lineWidth = lineWidth;
            context.moveTo(originX, n * scaledGridSize);
            context.lineTo(canvas.width, n * scaledGridSize);
            context.stroke();
        });
    };

    Renderer.prototype.particles = function(particles) {
        var startAngle = this.ANGLE_0_RAD;
        var endAngle = this.ANGLE_2PI_RAD;

        var scale = this.settings.scale;
        var radius = this.settings.particles.radius;
        var scaledRadius = scale * radius;
        var lineWidth = this.settings.particles.lineWidth;
        var strokeStyle = this.settings.particles.strokeStyle;
        var fillStyle = this.settings.particles.fillStyle;

        context.fillStyle = fillStyle;
        context.lineWidth = lineWidth;
        context.strokeStyle = strokeStyle;

        _.each(particles, function(element) {
            context.beginPath();
            context.arc(element[1] * scale, element[0] * scale, scaledRadius, startAngle, endAngle, false);
            context.fill();
            context.stroke();
        });
    }

    Renderer.prototype.linePath = function(path) {
        var startAngle = this.ANGLE_0_RAD;
        var endAngle = this.ANGLE_2PI_RAD;

        var scale = this.settings.scale;
        var radius = this.settings.linePath.radius;
        var scaledRadius = scale * radius;
        var gridsize = this.settings.gridsize;
        var scaledGridsize = scale * gridsize;
        var gridMidpoint = scaledGridsize/2;

        var context = this.context;
        var lineColor = this.settings.linePath.color;
        context.strokeStyle = lineColor;

        for (i = 1; i < path.length; i++) {
            var x1 = path[i - 1][1];
            var y1 = path[i - 1][0];
            var x2 = path[i][1];
            var y2 = path[i][0];

            context.beginPath();
            context.moveTo(x1 * scaledGridsize + gridMidpoint, y1 * scaledGridsize + gridMidpoint);
            context.lineTo(x2 * scaledGridsize + gridMidpoint, y2 * scaledGridsize + gridMidpoint);
            context.stroke();
            context.fill();
        }

        context.beginPath();
        context.arc(
            path[0][1] * scaledGridsize + gridMidpoint,
            path[0][0] * scaledGridsize + gridMidpoint,
            radius, startAngle, endAngle, false);
        context.fillStyle = lineColor;
        context.fill();

        context.beginPath();
        context.arc(
            path[path.length - 1][1] * scaledGridsize + gridMidpoint,
            path[path.length - 1][0] * scaledGridsize + gridMidpoint,
            radius, startAngle, endAngle, false);
        context.fillStyle = lineColor;
        context.fill();
    };

    Renderer.prototype.histogram = function(probabilities) {
        var scale = this.settings.scale;
        var gridsize = this.settings.gridsize;

        var textSettings = this.settings.histogram;

        var scaledGridsize = scale * gridsize;
        var context = this.canvas;

        context.font = textSettings.font;
        context.fillStyle = textSettings.fillStyle;
        context.textAlign = textSettings.textAlign;
        context.textBaseline = textSettings.textBaseline;

        for (var y = 0; y < probabilities.length; ++y) {
            for (var x = 0; x < probabilities[y].length; ++x) {
                if (probabilities[y][x] != null) {
                    context.fillText(probabilities[y][x],
                        gridsize + (x * scaledGridsize),
                        gridsize + (y * scaledGridsize));
                }
            }
        }
    };

    Renderer.prototype.redraw = function(map, path, particles)
        var scale = this.settings.scale;
        var canvas = this.canvas;
        var context = this.context;

        context.clearRect(0, 0, canvas.width, canvas.height);

        if (map) {
            this.map(map);
            this.grid();
        }

        if (path) {
            this.linePath(path);
        }

        if (particles) {
            this.particles(particles);
        }
    };
    Visualizer.Renderer = Renderer;


    var App = function(renderer, settings) {
        var defaults = {
            dataUri: '/static/data/map.json',
            socketUri: 'ws://localhost:8889/socket'
        };
        this.settings = $.extend(defaults, settings);

        this.renderer = renderer;
        this.methods = {
            particle: this.responseParticle,
            path: this.responsePath
        };
        this.map = null;
        this.path = null;
        this.particles = null;

        var self = this;
        var ws = null;

        this.connect = function() {
            ws = new WebSocket(self.settings.socketUri);
            ws.onmessage = function(event) {
                var response = JSON.parse(event.data);
                if (self.methods.hasOwnProperty(response.method)) {
                    self.methods[response.method](response.params);
                }
            };
        };
    };

    App.prototype.run = function() {
        this.loadmap();
        this.connect();
    };

    App.prototype.loadmap = function() {
        var self = this;
        $.get(self.settings.dataUri, function(data) {
            self.map = data;
            self.redraw();
        });
    };

    App.prototype.responseParticle = function(params) {
        this.particles = params[0];
        this.redraw();
    };

    App.prototype.responsePath = function(params) {
        this.path = params[0];
        this.redraw();
    };

    App.prototype.redraw = function() {
        this.renderer.redraw(this.map, this.path, this.particles);
    };
    Visualizer.App = App;

    Betelbot.Visualizer = Visualizer;
    window.Betelbot = Betelbot;
})(window);