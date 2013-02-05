(function(window, undefined) {

    var BetelBotAI = window.BetelBotAI || {};
    
    window.BetelBotAI = BetelBotAI;

    if (typeof define === "function" && define.amd && define.amd.BetelBotAI) {
        define( "BetelBotAI", [], function () { return BetelBotAI; } );
    }    

})(window);