(function() {
    var CANVAS_ID = 'map';
    var EL = 'body';
    var canvas = document.getElementById(CANVAS_ID);
    var renderer = new Betelbot.Visualizer.Renderer(canvas);
    var app = new Betelbot.Visualizer.App(EL, renderer);
    app.run();
})();
