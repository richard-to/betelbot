(function(window, undefined) {

    // Betelbot is the main namespace;
    var Betelbot = window.Betelbot || {};

    // Visualizer is a child namespace of Betelbot module.
    var Visualizer = {};

    // The renderer renders data from Betelbot to an HTML5 canvas.
    //
    // Currently can render data from:
    //
    // - map images
    // - particle filter
    // - path
    var Renderer = function(canvas, settings) {
        this.CONTEXT_2D = '2d';
        this.RGBA_BYTES = 4;
        this.OPAQUE_BYTE = 255;
        this.ANGLE_0_RAD = 0;
        this.ANGLE_2PI_RAD = 2 * Math.PI;

        var defaults = {
            scale: 2,
            gridsize: 20,
            display: {
                gridlines: true,
                route: true,
                particles: true,
            },
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
                radius: 3,
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

    // Renders map data to canvas
    Renderer.prototype.map = function(data) {
        var rgbaBytes = this.RGBA_BYTES;
        var alphaOpaque = this.OPAQUE_BYTE;

        var scale = this.settings.scale;

        var wallThreshold = this.settings.map.wallThreshold;
        var openColor = this.settings.map.openColor;
        var wallColor = this.settings.map.wallColor;

        var canvas = this.canvas;
        var context = this.context;

        var originX = 0;
        var originY = 0;
        var width = canvas.width;
        var height = canvas.height;
        var imageData = context.getImageData(originX, originY, width, height);

        var rgbaWidth = width * rgbaBytes;
        for (var y = 0; y < height; ++y) {
            var index = Math.floor(y / scale);
            var col = y * rgbaWidth;
            _.each(data[index], function(element) {
                _(scale).times(function(n) {
                    var color = (element < wallThreshold) ? wallColor : openColor;
                    imageData.data[col++] = color;
                    imageData.data[col++] = color;
                    imageData.data[col++] = color;
                    imageData.data[col++] = alphaOpaque;
                });
            });
        }
        context.putImageData(imageData, originX, originY);
    };

    // Renders gridlines on map
    Renderer.prototype.grid = function() {
        var scale = this.settings.scale;
        var gridsize = this.settings.gridsize;
        var scaledGridsize = scale * gridsize;
        var color = this.settings.grid.color;
        var lineWidth = this.settings.grid.lineWidth;

        var canvas = this.canvas;
        var context = this.context;

        var originX = 0;
        var originY = 0;
        var height = canvas.height;
        var width = canvas.width;
        context.strokeStyle = color;
        context.lineWidth = lineWidth;

        _(Math.floor(width / scaledGridsize) + 1).times(function(n) {
            context.beginPath();
            var pointX = n * scaledGridsize;
            context.moveTo(pointX, originY);
            context.lineTo(pointX, height);
            context.stroke();
        });

        _(Math.floor(height / scaledGridsize) + 1).times(function(n) {
            context.beginPath();
            var pointY = n * scaledGridsize;
            context.moveTo(originX, pointY);
            context.lineTo(width, pointY);
            context.stroke();
        });
    };

    // Renders particles from particles filter on map
    Renderer.prototype.particles = function(particles) {
        var startAngle = this.ANGLE_0_RAD;
        var endAngle = this.ANGLE_2PI_RAD;

        var scale = this.settings.scale;
        var radius = this.settings.particles.radius;
        var scaledRadius = scale * radius;
        var lineWidth = this.settings.particles.lineWidth;
        var strokeStyle = this.settings.particles.strokeStyle;
        var fillStyle = this.settings.particles.fillStyle;

        var context = this.context;
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

    // Renders Betelbot path on map
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
            scaledRadius, startAngle, endAngle, false);
        context.fillStyle = lineColor;
        context.fill();

        context.beginPath();
        context.arc(
            path[path.length - 1][1] * scaledGridsize + gridMidpoint,
            path[path.length - 1][0] * scaledGridsize + gridMidpoint,
            scaledRadius, startAngle, endAngle, false);
        context.fillStyle = lineColor;
        context.fill();
    };

    // Renders histogram data on map.
    // Histogram not implemented yet in Betelbot.
    Renderer.prototype.histogram = function(probabilities) {
        var scale = this.settings.scale;
        var gridsize = this.settings.gridsize;
        var scaledGridsize = scale * gridsize;
        var textSettings = this.settings.histogram;

        var context = this.context;
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

    Renderer.prototype.showGridlines = function(show) {
        this.settings.display.gridlines = (show === true);
    };

    Renderer.prototype.showRoute = function(show) {
        this.settings.display.route = (show === true);
    };

    Renderer.prototype.showParticles = function(show) {
        this.settings.display.particles = (show === true);
    };

    // Redraws the map data. Used when new data is received from Betelbot server.
    Renderer.prototype.redraw = function(map, path, particles) {
        var scale = this.settings.scale;
        var canvas = this.canvas;
        var context = this.context;
        var display = this.settings.display;

        context.clearRect(0, 0, canvas.width, canvas.height);

        if (map) {
            this.map(map);
            if (display.gridlines) {
                this.grid();
            }
        }

        if (path && display.route) {
            this.linePath(path);
        }

        if (particles && display.particles) {
            this.particles(particles);
        }
    };
    Visualizer.Renderer = Renderer;


    // Controller for Betelbot app.
    // Main job is to send new data to renderer.
    var App = function(el, renderer, settings) {
        var defaults = {
            dataUri: '/static/data/map.json',
            socketUri: 'ws://localhost:8889/socket',
            selectors: {
                showParticle: ".btn-group-particle button",
                showRoute: ".btn-group-route button",
                showGridlines: ".btn-group-gridlines button",
                alertConnect: ".alert-connect-server"
            },
            dataAttr: {
                value: {
                    name: "data-value",
                    vals: {on: "1", off: "0"}
                }
            }
        };
        this.settings = $.extend(true, defaults, settings);

        this.$el = el instanceof $ ? el : $(el);
        this.el = this.$el[0];

        this.renderer = renderer;
        this.methods = {
            particle: _.bind(this.responseParticle, this),
            path: _.bind(this.responsePath, this)
        };
        this.map = null;
        this.path = null;
        this.particles = null;

        var selectors = this.settings.selectors;
        var self = this;
        var ws = null;

        this.connect = function() {
            ws = new WebSocket(self.settings.socketUri);

            ws.onopen = function() {
                $(selectors.alertConnect, self.el).hide();
            };

            ws.onmessage = function(event) {
                var response = JSON.parse(event.data);
                if (self.methods.hasOwnProperty(response.method)) {
                    self.methods[response.method](response.params);
                }
            };

            ws.onclose = function() {
                $(selectors.alertConnect, self.el).show();
                self.connect();
            };
        };

        var dataValue = this.settings.dataAttr.value;
        $(selectors.showParticle, self.el).click(function(event) {
            self.renderer.showParticles(($(this).attr(dataValue.name) === dataValue.vals.on));
            self.redraw();
        });

        $(selectors.showGridlines, self.el).click(function(event) {
            self.renderer.showGridlines(($(this).attr(dataValue.name) === dataValue.vals.on));
            self.redraw();
        });

        $(selectors.showRoute, self.el).click(function(event) {
            self.renderer.showRoute(($(this).attr(dataValue.name) === dataValue.vals.on));
            self.redraw();
        });
    };

    // Runs the app. Will load map and automatically connect to server.
    App.prototype.run = function() {
        this.loadmap();
        this.connect();
    };

    // Loads the specified map data.
    // Currently map data is a json file, but it
    // would be more efficient to use a grayscale bitmap image.
    App.prototype.loadmap = function() {
        var self = this;
        $.get(self.settings.dataUri, function(data) {
            self.map = data;
            self.redraw();
        });
    };

    // Handles the case when Betelbot server sends particle filter data.
    App.prototype.responseParticle = function(params) {
        this.particles = params[0];
        this.redraw();
    };

    // Handles the case when server sends path data.
    App.prototype.responsePath = function(params) {
        this.path = params[0];
        this.redraw();
    };

    // Redraw is called any time data is updated.
    App.prototype.redraw = function() {
        this.renderer.redraw(this.map, this.path, this.particles);
    };
    Visualizer.App = App;

    Betelbot.Visualizer = Visualizer;
    window.Betelbot = Betelbot;
})(window);