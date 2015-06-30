/*
 * Computation of tickValues. Seems to be worse alg than d3, but guarantees inside.
 */
var tickValues = function(vMin, vMax, isShorterAxis) {
    var niceFraction = function(fraction, wantRound) {
        if (wantRound) {
            if (fraction < 1.5)
                return 1;
            else if (fraction < 3)
                return 2;
            else if (fraction < 7)
                return 5;
            return 10;
        }
        if (fraction <= 1)
            return 1;
        else if (fraction <= 2)
            return 2;
        else if (fraction <= 5)
            return 5;
        return 10;
    };
    var niceNum = function(value, wantRound) {
        var exponent = Math.floor(Math.log10(value));
        var fraction = value / Math.pow(10, exponent);
        return niceFraction(fraction, wantRound) * Math.pow(10, exponent);
    };
    var pixelSpacing = isShorterAxis ? 100 : 50;
    var count = Math.max(Math.round($scope.canvas_size / pixelSpacing), 3);
    var vRange = niceNum(vMax - vMin, false)
    var spacing = niceNum(vRange / (count - 1), true)
    var tickMin = Math.ceil(vMin / spacing) * spacing;
    var tickMax = Math.floor(vMax / spacing) * spacing;
    var ticks = [];
    var tick = tickMin;
    while (tick <= tickMax) {
        ticks.push(tick);
        tick += spacing;
    }
    if (ticks.length == 1)
        ticks = [vMin, ticks[0], vMax];
    console.log(ticks);
    return ticks;
};
