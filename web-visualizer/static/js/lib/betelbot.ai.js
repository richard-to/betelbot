(function() {

    // Initial Setup
    // -------------
    var root = this;
    var BetelBotAI = root.BetelBotAI || {};

    // Current BetelBotAI version.
    BetelBotAI.VERSION = '0.1';


    // 1D HistogramFilter
    // ------------------

    // This 1D histogram filter is based off code from the 
    // Udacity: AI for Robotics course.
    var HistogramFilter1D = function(settings) {       
        this.settings = {
            world: [],
            pHit: 6.0,
            pMiss: 2.0,
            pExact: 1.0,
            pUndershoot: 0.0,
            pOvershoot: 0.0
        };
        this.settings = _.extend(this.settings, _.pick(_.keys(this.settings), settings));
    };

    HistogramFilter1D.prototype.sense = function(probability, measurement) {
        var settings = this.settings;       
        var newProbability = newProbability = _.map(probability, function(num, i, probability){ 
            var hit = (measurement == settings.world[i]);
            return num * (hit * settings.pHit + (1 - hit) * settings.pMiss));
        });
        var sum = _.reduce(newProbability, function(memo, num){ return memo + num; }, 0);
        return _.map(newProbability, function(num){ return num / sum; });
    };

    HistogramFilter1D.prototype.move = function(probability, motion) {

    };

    root.BetelBotAI = BetelBotAI;

    if (typeof define === "function" && define.amd && define.amd.BetelBotAI) {
        define( "BetelBotAI", [], function () { return BetelBotAI; } );
    }    

}).call(this);