'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;
SIREPO.PLOTTING_CSV_EVENT = 'plottingCSV';
SIREPO.PLOTTING_YMIN_ZERO = true;
SIREPO.DEFAULT_COLOR_MAP = 'viridis';
SIREPO.SCREEN_DIMS = ['x', 'y'];
SIREPO.SCREEN_INFO = {x: { direction: 1 },  y: { direction: -1 }};
SIREPO.ZERO_ARR = [0, 0, 0];

class PlottingUtils {
    static COLOR_MAP() {
        function colorsFromString(s) {
            return s.match(/.{6}/g).map(function(x) {
                return "#" + x;
            });
        }

        return {
            grayscale: ['#333', '#fff'],
            afmhot: colorsFromString('0000000200000400000600000800000a00000c00000e00001000001200001400001600001800001a00001c00001e00002000002200002400002600002800002a00002c00002e00003000003200003400003600003800003a00003c00003e00004000004200004400004600004800004a00004c00004e00005000005200005400005600005800005a00005c00005e00006000006200006400006600006800006a00006c00006e00007000007200007400007600007800007a00007c00007e00008000008202008404008607008808008a0a008c0d008e0f009010009212009414009617009818009a1a009c1d009e1f00a02000a22200a42400a62700a82800aa2a00ac2d00ae2f00b03000b23200b43400b63700b83800ba3a00bc3d00be3f00c04000c24200c44400c64600c84800ca4a00cc4d00ce4e00d05000d25200d45400d65600d85800da5a00dc5d00de5e00e06000e26200e46400e66600e86800ea6a00ec6d00ee6e00f07000f27200f47400f67600f87800fa7a00fc7d00fe7e00ff8001ff8203ff8405ff8607ff8809ff8b0bff8c0dff8e0fff9011ff9213ff9415ff9617ff9919ff9b1bff9c1dff9e1fffa021ffa223ffa425ffa627ffa829ffab2bffac2dffae2fffb031ffb233ffb435ffb637ffb939ffbb3bffbc3dffbe3fffc041ffc243ffc445ffc647ffc849ffcb4bffcc4dffce4fffd051ffd253ffd455ffd657ffd959ffdb5bffdc5dffde5fffe061ffe263ffe465ffe667ffe869ffeb6bffec6dffee6ffff071fff273fff475fff677fff979fffb7bfffc7dfffe7fffff81ffff83ffff85ffff87ffff89ffff8bffff8dffff8fffff91ffff93ffff95ffff97ffff99ffff9bffff9dffff9fffffa1ffffa3ffffa5ffffa7ffffa9ffffabffffadffffafffffb1ffffb3ffffb5ffffb7ffffb9ffffbbffffbdffffbfffffc1ffffc3ffffc5ffffc7ffffc9ffffcbffffcdffffcfffffd1ffffd3ffffd5ffffd7ffffd9ffffdbffffddffffdfffffe1ffffe3ffffe5ffffe7ffffe9ffffebffffedffffeffffff1fffff3fffff5fffff7fffff9fffffbfffffdffffff'),
            blues: colorsFromString('f7fbffdeebf7c6dbef9ecae16baed64292c62171b508519c08306b'),
            coolwarm: colorsFromString('3b4cc03c4ec23d50c33e51c53f53c64055c84257c94358cb445acc455cce465ecf485fd14961d24a63d34b64d54c66d64e68d84f69d9506bda516ddb536edd5470de5572df5673e05875e15977e35a78e45b7ae55d7ce65e7de75f7fe86180e96282ea6384eb6485ec6687ed6788ee688aef6a8bef6b8df06c8ff16e90f26f92f37093f37295f47396f57597f67699f6779af7799cf87a9df87b9ff97da0f97ea1fa80a3fa81a4fb82a6fb84a7fc85a8fc86a9fc88abfd89acfd8badfd8caffe8db0fe8fb1fe90b2fe92b4fe93b5fe94b6ff96b7ff97b8ff98b9ff9abbff9bbcff9dbdff9ebeff9fbfffa1c0ffa2c1ffa3c2fea5c3fea6c4fea7c5fea9c6fdaac7fdabc8fdadc9fdaec9fcafcafcb1cbfcb2ccfbb3cdfbb5cdfab6cefab7cff9b9d0f9bad0f8bbd1f8bcd2f7bed2f6bfd3f6c0d4f5c1d4f4c3d5f4c4d5f3c5d6f2c6d6f1c7d7f0c9d7f0cad8efcbd8eeccd9edcdd9eccedaebcfdaead1dae9d2dbe8d3dbe7d4dbe6d5dbe5d6dce4d7dce3d8dce2d9dce1dadce0dbdcdedcdddddddcdcdedcdbdfdbd9e0dbd8e1dad6e2dad5e3d9d3e4d9d2e5d8d1e6d7cfe7d7cee8d6cce9d5cbead5c9ead4c8ebd3c6ecd3c5edd2c3edd1c2eed0c0efcfbfefcebdf0cdbbf1cdbaf1ccb8f2cbb7f2cab5f2c9b4f3c8b2f3c7b1f4c6aff4c5adf5c4acf5c2aaf5c1a9f5c0a7f6bfa6f6bea4f6bda2f7bca1f7ba9ff7b99ef7b89cf7b79bf7b599f7b497f7b396f7b194f7b093f7af91f7ad90f7ac8ef7aa8cf7a98bf7a889f7a688f6a586f6a385f6a283f5a081f59f80f59d7ef59c7df49a7bf4987af39778f39577f39475f29274f29072f18f71f18d6ff08b6ef08a6cef886bee8669ee8468ed8366ec8165ec7f63eb7d62ea7b60e97a5fe9785de8765ce7745be67259e57058e46e56e36c55e36b54e26952e16751e0654fdf634ede614ddd5f4bdc5d4ada5a49d95847d85646d75445d65244d55042d44e41d24b40d1493fd0473dcf453ccd423bcc403acb3e38ca3b37c83836c73635c53334c43032c32e31c12b30c0282fbe242ebd1f2dbb1b2cba162bb8122ab70d28b50927b40426'),
            jet: colorsFromString('00008000008400008900008d00009200009600009b00009f0000a40000a80000ad0000b20000b60000bb0000bf0000c40000c80000cd0000d10000d60000da0000df0000e30000e80000ed0000f10000f60000fa0000ff0000ff0000ff0000ff0000ff0004ff0008ff000cff0010ff0014ff0018ff001cff0020ff0024ff0028ff002cff0030ff0034ff0038ff003cff0040ff0044ff0048ff004cff0050ff0054ff0058ff005cff0060ff0064ff0068ff006cff0070ff0074ff0078ff007cff0080ff0084ff0088ff008cff0090ff0094ff0098ff009cff00a0ff00a4ff00a8ff00acff00b0ff00b4ff00b8ff00bcff00c0ff00c4ff00c8ff00ccff00d0ff00d4ff00d8ff00dcfe00e0fb00e4f802e8f406ecf109f0ee0cf4eb0ff8e713fce416ffe119ffde1cffdb1fffd723ffd426ffd129ffce2cffca30ffc733ffc436ffc139ffbe3cffba40ffb743ffb446ffb149ffad4dffaa50ffa753ffa456ffa05aff9d5dff9a60ff9763ff9466ff906aff8d6dff8a70ff8773ff8377ff807aff7d7dff7a80ff7783ff7387ff708aff6d8dff6a90ff6694ff6397ff609aff5d9dff5aa0ff56a4ff53a7ff50aaff4dadff49b1ff46b4ff43b7ff40baff3cbeff39c1ff36c4ff33c7ff30caff2cceff29d1ff26d4ff23d7ff1fdbff1cdeff19e1ff16e4ff13e7ff0febff0ceeff09f1fc06f4f802f8f500fbf100feed00ffea00ffe600ffe200ffde00ffdb00ffd700ffd300ffd000ffcc00ffc800ffc400ffc100ffbd00ffb900ffb600ffb200ffae00ffab00ffa700ffa300ff9f00ff9c00ff9800ff9400ff9100ff8d00ff8900ff8600ff8200ff7e00ff7a00ff7700ff7300ff6f00ff6c00ff6800ff6400ff6000ff5d00ff5900ff5500ff5200ff4e00ff4a00ff4700ff4300ff3f00ff3b00ff3800ff3400ff3000ff2d00ff2900ff2500ff2200ff1e00ff1a00ff1600ff1300fa0f00f60b00f10800ed0400e80000e40000df0000da0000d60000d10000cd0000c80000c40000bf0000bb0000b60000b20000ad0000a80000a400009f00009b00009600009200008d0000890000840000800000'),
            viridis: colorsFromString('44015444025645045745055946075a46085c460a5d460b5e470d60470e6147106347116447136548146748166848176948186a481a6c481b6d481c6e481d6f481f70482071482173482374482475482576482677482878482979472a7a472c7a472d7b472e7c472f7d46307e46327e46337f463480453581453781453882443983443a83443b84433d84433e85423f854240864241864142874144874045884046883f47883f48893e49893e4a893e4c8a3d4d8a3d4e8a3c4f8a3c508b3b518b3b528b3a538b3a548c39558c39568c38588c38598c375a8c375b8d365c8d365d8d355e8d355f8d34608d34618d33628d33638d32648e32658e31668e31678e31688e30698e306a8e2f6b8e2f6c8e2e6d8e2e6e8e2e6f8e2d708e2d718e2c718e2c728e2c738e2b748e2b758e2a768e2a778e2a788e29798e297a8e297b8e287c8e287d8e277e8e277f8e27808e26818e26828e26828e25838e25848e25858e24868e24878e23888e23898e238a8d228b8d228c8d228d8d218e8d218f8d21908d21918c20928c20928c20938c1f948c1f958b1f968b1f978b1f988b1f998a1f9a8a1e9b8a1e9c891e9d891f9e891f9f881fa0881fa1881fa1871fa28720a38620a48621a58521a68522a78522a88423a98324aa8325ab8225ac8226ad8127ad8128ae8029af7f2ab07f2cb17e2db27d2eb37c2fb47c31b57b32b67a34b67935b77937b87838b9773aba763bbb753dbc743fbc7340bd7242be7144bf7046c06f48c16e4ac16d4cc26c4ec36b50c46a52c56954c56856c66758c7655ac8645cc8635ec96260ca6063cb5f65cb5e67cc5c69cd5b6ccd5a6ece5870cf5773d05675d05477d1537ad1517cd2507fd34e81d34d84d44b86d54989d5488bd6468ed64590d74393d74195d84098d83e9bd93c9dd93ba0da39a2da37a5db36a8db34aadc32addc30b0dd2fb2dd2db5de2bb8de29bade28bddf26c0df25c2df23c5e021c8e020cae11fcde11dd0e11cd2e21bd5e21ad8e219dae319dde318dfe318e2e418e5e419e7e419eae51aece51befe51cf1e51df4e61ef6e620f8e621fbe723fde725'),
            contrast: colorsFromString('000000' + 'ffffff'.repeat(255)),
        };
    }

    static colorScale(min, max, colorMap) {
        return d3.scale.linear()
            .domain(SIREPO.UTILS.linearlySpacedArray(min, max, colorMap.length))
            .range(colorMap)
            .clamp(true);
    }

}

class AbstractPlotShape {
    constructor(
        id=SIREPO.UTILS.randomString(),
        name='AbstractPlotShape',
        layoutShape=''
    ) {
        this.alpha = 1.0;
        this.color = null;
        this.dashes = null;
        this.fillStyle = 'solid';
        this.id = id;
        this.layoutShape = layoutShape;
        this.name = name;
        this.outlineOffset = 0.0;
        this.strokeStyle = 'solid';
        this.strokeWidth = 1.0;

        this.axes = ['x', 'y'];
        this.center = new SIREPO.GEOMETRY.Point(0, 0);
        this.draggable = true;
        this.elevation = null;
        this.links = [];
        this.size = {x: 0.0, y: 0.0};
        this.transform = new SIREPO.GEOMETRY.IdentityMatrix(2);

        // d3 events require x and y
        this.x = 0;
        this.y = 0;

        // used to sort
        this.z = 0;
    }

    addLink(otherShape, linkFunction) {
        this.links.push(this.plotShapeLink(otherShape, linkFunction));
    }

    bounds() {
        return {
            x: [0.0, 0.0],
            y: [0.0, 0.0],
        };
    }

    copy(exclude=[]) {
        const c = SIREPO.UTILS.copyInstance(this, exclude.concat(['center', 'id', 'transform']));
        c.center = new SIREPO.GEOMETRY.Point(...this.center.coords());
        c.transform = new SIREPO.GEOMETRY.SquareMatrix(this.transform.val);
        return c;
    }

    getCoords(obj) {
        const coords = [];
        for (const dim of this.axes) {
            coords.push(obj[dim]);
        }
        return coords;
    }

    // link this shape to another so that some aspect of the linked shape is tied to
    // this one via a provided function
    plotShapeLink(linkedShape, linkFunction) {
        return {
            shape: this,
            linkedShape: linkedShape,
            fn: linkFunction,
        };
    }

    runLinks() {
        const linkRes = [];
        this.links.forEach(function (l) {
            linkRes.push(l.fn(l.shape, l.linkedShape));
        });
        return linkRes;
    }

    selectionId(includeHash=true) {
        return `${(includeHash ? '#' : '')}shape-${this.id}`;
    }

    setCoords(obj, coords) {
        Object.keys(obj).forEach(function(dim, i) {
            obj[dim] = coords[i];
        });
    }

    setAlpha(alpha) {
        this.alpha = alpha;
    }

    setColor(color) {
        this.color = color;
    }

    setDashes(dashes) {
        this.dashes = dashes;
    }

    setDraggable(isDraggable) {
        this.draggable = isDraggable;
    }

    setFillStyle(style) {
        this.fillStyle = style;
    }

    setOutlineOffset(offset) {
        this.outlineOffset = offset;
    }

    setStrokeStyle(style) {
        this.strokeStyle = style;
    }

    setStrokeWidth(width) {
        this.strokeWidth = width;
    }
}

class AbstractPlotShape2D extends AbstractPlotShape {
    constructor(
        id,
        name,
        layoutShape,
        center=[0, 0]
    ) {
        super(
            id,
            name,
            layoutShape
        );
        this.center = new SIREPO.GEOMETRY.Point(...center);
    }

    getCenterCoords() {
        return this.getCoords(this.center);
    }

    setCenter(coords) {
        this.setCoords(this.center, coords);
    }
}

class PlotPolygon extends AbstractPlotShape2D {
    constructor(
        id,
        name,
        points=[[0,0],[0,1],[1,1]]
    ) {
        if (points.length < 3) {
            throw new Error('Polygons require at least 3 points: ' + points.length);
        }
        const p = points.map(x => new SIREPO.GEOMETRY.Point(...x));
        const sx = SIREPO.GEOMETRY.GeometryUtils.sortInDimension(p, 'x');
        const sy = SIREPO.GEOMETRY.GeometryUtils.sortInDimension(p, 'y');
        const ctr = [
            sx[0].x + (sx[sx.length - 1].x - sx[0].x) / 2,
            sy[0].y + (sy[sy.length - 1].y - sy[0].y) / 2,
        ];

        super(
            id,
            name,
            'polygon',
            ctr
        );

        this.size = {
            x: Math.abs(sx[sx.length - 1].x - sx[0].x),
            y: Math.abs(sy[sy.length - 1].y - sy[0].y),
        };

        this.center.x = ctr[0];
        this.center.y = ctr[1];

        this.setPoints(p);
    }

    bounds() {
        return SIREPO.GEOMETRY.GeometryUtils.bounds(this.points);
    }

    copy() {
        const c = super.copy(['points']);
        c.points = [];
        for (const p of this.points) {
            c.points.push(new SIREPO.GEOMETRY.Point(...p.coords()));
        }
        return c;
    }

    getSizeCoords() {
        return this.getCoords(this.size);
    }

    setPoints(arr) {
        this.points = arr;
    }
}

SIREPO.app.factory('plotting', function(appState, frameCache, panelState, utilities, simulationQueue, $interval, $rootScope, $window) {

    var INITIAL_HEIGHT = 400;
    var MAX_PLOTS = 11;
    const COLOR_MAP = PlottingUtils.COLOR_MAP();

    // polyfill for MSIE without Math.log2 and Math.log10
    Math.log2 = Math.log2 || function(x) {
        return Math.log(x) * Math.LOG2E;
    };
    Math.log10 = Math.log10 || function(x) {
        return Math.log(x) * Math.LOG10E;
    };

    var LOG_SCALE = {
        log: safeLog(Math.log, 'e'),
        log2: safeLog(Math.log2, '2'),
        log10: safeLog(Math.log10, '10'),
    };

    function broadcastSummaryData(name, summaryData) {
        // send info in two formats, similar to modelChanged
        $rootScope.$broadcast(name + '.summaryData', summaryData);
        $rootScope.$broadcast('summaryData', name, summaryData);
    }

    function initAnimation(scope) {
        scope.prevFrameIndex = SIREPO.nonDataFileFrame;
        scope.isPlaying = false;
        var requestData = scope.requestData || function() {
            if (! scope.hasFrames()) {
                return;
            }
            var index = frameCache.getCurrentFrame(scope.modelName);
            if (frameCache.getCurrentFrame(scope.modelName) == scope.prevFrameIndex) {
                return;
            }
            panelState.setError(scope.modelName, '');
            scope.prevFrameIndex = index;
            frameCache.getFrame(scope.modelName, index, scope.isPlaying, function(index, data) {
                if (scope.element) {
                    if (data.state == 'canceled') {
                        data.error = 'Request canceled due to timeout';
                    }
                    if (data.error) {
                        panelState.setError(scope.modelName, data.error);
                        return;
                    }
                    panelState.setError(scope.modelName, null);
                    scope.load(data);
                    if (data.summaryData) {
                        broadcastSummaryData(scope.modelName, data.summaryData);
                    }
                }
                if (scope.isPlaying) {
                    scope.advanceFrame(1);
                }
            });
        };

        scope.advanceFrame = function(increment, stopPlaying) {
            if (stopPlaying) {
                scope.isPlaying = false;
            }
            var next = frameCache.getCurrentFrame(scope.modelName) + increment;
            if (next < 0 || next > frameCache.getFrameCount(scope.modelName) - 1) {
                scope.isPlaying = false;
                return;
            }
            frameCache.setCurrentFrame(scope.modelName, next);
            requestData();
        };
        scope.defaultFrame = function() {
            if (scope.getDefaultFrame) {
                frameCache.setCurrentFrame(scope.modelName, scope.getDefaultFrame());
                requestData();
            }
            else {
                scope.lastFrame();
            }
        };
        scope.firstFrame = function() {
            scope.isPlaying = false;
            frameCache.setCurrentFrame(scope.modelName, 0);
            requestData();
        };
        scope.hasFrames = function() {
//rn scope.modelName is beamAnimation or particleAnimation but there would
// be no frames.
            return frameCache.isLoaded() && frameCache.getFrameCount(scope.modelName) > 0;
        };
        scope.hasManyFrames = function() {
            if (SIREPO.SINGLE_FRAME_ANIMATION && SIREPO.SINGLE_FRAME_ANIMATION.indexOf(scope.modelName) >= 0) {
                return false;
            }
            if (appState.isLoaded() && appState.models[scope.modelName].showAllFrames == '1') {
                return false;
            }
            return frameCache.isLoaded() && frameCache.getFrameCount(scope.modelName) > 1;
        };
        scope.isFirstFrame = function() {
            return frameCache.getCurrentFrame(scope.modelName) === 0;
        };
        scope.isLastFrame = function() {
            return frameCache.getCurrentFrame(scope.modelName) == frameCache.getFrameCount(scope.modelName) - 1;
        };
        scope.lastFrame = function() {
            scope.isPlaying = false;
            frameCache.setCurrentFrame(scope.modelName, frameCache.getFrameCount(scope.modelName) - 1);
            requestData();
        };
        scope.togglePlay = function() {
            scope.isPlaying = ! scope.isPlaying;
            if (scope.isPlaying) {
                if (scope.isLastFrame()) {
                    frameCache.setCurrentFrame(scope.modelName, 0);
                    requestData();
                }
                else {
                    scope.advanceFrame(1);
                }
            }
        };
        scope.$on('framesCleared', function() {
            scope.prevFrameIndex = SIREPO.nonDataFileFrame;
            if (scope.clearData) {
                scope.clearData();
            }
        });
        scope.$on('modelsLoaded', requestData);
        scope.$on('framesLoaded', function(event, oldFrameCount) {
            if (! frameCache.getSimulationStatus(scope.modelName).computeJobSerial) {
                // if there are multiple different sourced frame-based animations on the same page,
                // then one may be ready before the rest. Check that the serial job is available
                // before loading the data. Ex. SRW source page with fluxAnimation and coherentModesAnimation
                return;
            }
            if (scope.prevFrameIndex < 0 || oldFrameCount === 0) {
                scope.defaultFrame();
            }
            else if (scope.prevFrameIndex > frameCache.getFrameCount(scope.modelName)) {
                scope.firstFrame();
            }
            // go to the next last frame, if the current frame was the previous last frame
            else if (
                frameCache.getCurrentFrame(scope.modelName) >= oldFrameCount - 1
                || frameCache.getCurrentFrame(scope.modelName) == frameCache.getFrameCount(scope.modelName) - 2
            ) {
                scope.defaultFrame();
            }
        });
        return requestData;
    }

    function initPlot(scope) {
        var interval = null;
        var requestData = function() {
            var priority = getCurrentPriority();
            interval = $interval(function() {
                if (interval) {
                    $interval.cancel(interval);
                    interval = null;
                }
                if (! scope.element) {
                    return;
                }
                panelState.requestData(scope.modelName, function(data) {
                    if (! scope.element) {
                        return;
                    }
                    if (data.x_range) {
                        scope.clearData();
                        scope.load(data);
                        if (data.summaryData) {
                            broadcastSummaryData(scope.modelName, data.summaryData);
                        }
                    }
                    else {
                        panelState.setError(scope.modelName, 'Invalid results received from server');
                    }
                });
            }, 50 + priority * 10, 1);
        };

        function getCurrentPriority() {
            var current = scope.$parent;
            while (current) {
                if (current.requestPriority) {
                    return current.requestPriority;
                }
                current = current.$parent;
            }
            return 0;
        }

        return requestData;
    }

    function linearlySpacedArray(start, stop, nsteps) {
        if (nsteps < 1) {
            throw new Error("linearlySpacedArray: steps " + nsteps + " < 1");
        }
        var delta = (stop - start) / (nsteps - 1);
        var res = d3.range(nsteps).map(function(d) { return start + d * delta; });
        res[res.length - 1] = stop;

        if (res.length != nsteps) {
            throw new Error("linearlySpacedArray: steps " + nsteps + " != " + res.length);
        }
        return res;
    }

    function noOp() {}

    function normalizeValues(yValues, shift) {
        var yMin = utilities.arrayMin(yValues);
        var yMax = utilities.arrayMax(yValues);
        var yRange = yMax - yMin;
        for (var i = 0; i < yValues.length; i++) {
            yValues[i] = (yValues[i] - yMin) / yRange - shift;  // roots are at Y=0
        }
        return yValues;
    }

    function safeLog(logFunction, powerName) {
        var res = function(v) {
            if (v > 0) {
                return logFunction(v);
            }
            // small log value
            return -100;
        };
        res.powerName = powerName;
        return res;
    }

    function setupSelector(scope, element) {
        scope.element = element[0];
        scope.select = function(selector) {
            var e = d3.select(scope.element);
            return selector ? e.select(selector) : e;
        };
    }

    var self = {
        COLOR_MAP: COLOR_MAP,

        addConvergencePoints: function(select, parentClass, pointsList, points) {
            var i;
            if (points.length > 1 && SIREPO.PLOTTING_SUMMED_LINEOUTS) {
                var newPoints = [];
                var dist = (points[1][0] - points[0][0]) / 2.0;
                newPoints.push(points[0]);
                var prevY = points[0][1];
                for (i = 1; i < points.length; i++) {
                    var p = points[i];
                    if (prevY != p[1]) {
                        var x = p[0] - dist;
                        newPoints.push([x, prevY], [x, p[1]]);
                        prevY = p[1];
                    }
                }
                newPoints.push(points[points.length - 1]);
                points = newPoints;
            }
            pointsList.splice(0, 0, points);
            if (pointsList.length > MAX_PLOTS) {
                pointsList = pointsList.slice(0, MAX_PLOTS);
            }
            for (i = 0; i < MAX_PLOTS; i++) {
                select(parentClass + ' .line-' + i).datum(pointsList[i] || []);
            }
            return pointsList;
        },

        calculateFWHM: function(xValues, yValues) {
            yValues = normalizeValues(yValues, 0.5);
            var positive = yValues[0] > 0;
            var listOfRoots = [];
            for (var i = 0; i < yValues.length; i++) {
                var currentPositive = yValues[i] > 0;
                if (currentPositive !== positive) {
                    listOfRoots.push(xValues[i - 1] + (xValues[i] - xValues[i - 1]) / (Math.abs(yValues[i]) + Math.abs(yValues[i - 1])) * Math.abs(yValues[i - 1]));
                    positive = !positive;
                }
            }
            var fwhm = NaN;
            if (listOfRoots.length >= 2) {
                fwhm = Math.abs(listOfRoots[listOfRoots.length - 1] - listOfRoots[0]);
            }
            return fwhm;
        },

        colorMapFromModel: function(modelName, fieldName) {

            var model = appState.models[modelName];
            var modelMap = model ? (model[fieldName] || model.colorMap) : null;

            var modelDefaultMap;
            var info = SIREPO.APP_SCHEMA.model[modelName];
            if (info) {
                var mapInfo = info.colorMap;
                modelDefaultMap = mapInfo ? mapInfo[SIREPO.INFO_INDEX_DEFAULT_VALUE] : null;
            }

            return this.colorMapOrDefault(modelMap, modelDefaultMap);
        },

        colorMapNameOrDefault: function(mapName, defaultMapName) {
            return mapName || defaultMapName || SIREPO.PLOTTING_COLOR_MAP || SIREPO.DEFAULT_COLOR_MAP;
        },

        colorMapOrDefault: function(mapName, defaultMapName) {
            return COLOR_MAP[this.colorMapNameOrDefault(mapName, defaultMapName)];
        },

        colorScaleForPlot: function(plotRange, modelName, fieldName) {
            var m = appState.models[modelName];
            var zMin = plotRange.min;
            var zMax = plotRange.max;
            if (zMin == zMax) {
                // draw single value plot as lowest colormap value
                zMax += 1;
            }
            if (m.colorRangeType == 'fixed') {
                zMin = m.colorMin;
                zMax = m.colorMax;
            }
            var colorMap = this.colorMapFromModel(modelName, fieldName);
            return d3.scale.linear()
                .domain(linearlySpacedArray(zMin, zMax, colorMap.length))
                .range(colorMap)
                .clamp(true);
        },

        colorScale: PlottingUtils.colorScale,

        colorsFromHexString: function(color, range) {
            if (! (/^#([0-9a-f]{2}){3}$/i).test(color)) {
                throw new Error(color + ': Invalid color string');
            }
            return color.match((/[0-9a-f]{2}/ig)).map(function(h) {
                return parseInt(h, 16) / (range || 1.0);
            });
        },

        constrainFullscreenSize: function(scope, plotWidth, aspectRatio) {
            function heightMargins() {
                let panelTitleSizeEstimate = 50 + 2 * 15 + 2 * 4 + (scope.isAnimation && scope.hasFrames() ? 34 : 0);
                return scope.margin.top + scope.margin.bottom + panelTitleSizeEstimate;
            }

            function widthMargins() {
                return scope.margin.left + scope.margin.right + (scope.pad || 0)
                     + (utilities.isFullscreen() ? 35 : 0);
            }

            if (! utilities.isFullscreen()) {
                let w = plotWidth - widthMargins();
                return [aspectRatio * w, w];
            }
            var maxHeight = window.innerHeight - heightMargins();
            var maxWidth = window.innerWidth - widthMargins();
            var h = maxHeight;
            var w = h / aspectRatio;
            if (w > maxWidth) {
                w = maxWidth;
                h = w * aspectRatio;
            }
            return [h, w];
        },

        csvFilename: (fileName) => {
            return fileName.replace(/\[.*\]/, '')
                .replace(/\s+$/, '')
                .replace(/(\_|\W|\s)+/g, '-') + '.csv';
        },

        drawImage: function(xAxisScale, yAxisScale, width, height, xValues, yValues, canvas, cacheCanvas, alignOnPixel) {
            var xZoomDomain = xAxisScale.domain();
            var xDomain = xValues.srDomain || [xValues[0], xValues[xValues.length - 1]];
            var yZoomDomain = yAxisScale.domain();
            var yDomain = yValues.srDomain || [yValues[0], yValues[yValues.length - 1]];
            var zoomWidth = xZoomDomain[1] - xZoomDomain[0];
            var zoomHeight = yZoomDomain[1] - yZoomDomain[0];
            canvas.width = width;
            canvas.height = height;
            const sz =  this.pixelSize(xAxisScale, yAxisScale, width, height, xValues, yValues);
            var xPixelSize = alignOnPixel ? sz.x: 0;
            var yPixelSize = alignOnPixel ? sz.y : 0;
            var ctx = canvas.getContext('2d');
            ctx.imageSmoothingEnabled = false;
            ctx.msImageSmoothingEnabled = false;
            ctx.drawImage(
                cacheCanvas,
                -(xZoomDomain[0] - xDomain[0]) / zoomWidth * width - xPixelSize / 2,
                -(yDomain[1] - yZoomDomain[1]) / zoomHeight * height - yPixelSize / 2,
                (xDomain[1] - xDomain[0]) / zoomWidth * width + xPixelSize,
                (yDomain[1] - yDomain[0]) / zoomHeight * height + yPixelSize);
        },

        ensureDomain: function(domain, scaleFunction) {
            if (domain && scaleFunction) {
                domain = domain.map(scaleFunction);
            }
            if (domain && (domain[0] == domain[1])) {
                domain[0] -= (domain[0] || 1);
                domain[1] += (domain[1] || 1);
            }
            return domain;
        },

        exportCSV: function(fileName, heading, points) {
            var res = heading.map(function(v) {
                v = v.replace(/"/g, '');
                if (v.indexOf(',') >= 0) {
                    v = '"' + v + '"';
                }
                return v;
            }).join(',') + "\n";
            points.forEach(function(row) {
                res += row.map(function(v) {
                    return v.toExponential(9);
                }).join(',') + "\n";
            });
            saveAs(new Blob([res], {type: "text/csv;charset=utf-8"}), self.csvFilename(fileName));
        },

        formatValue: function(v, formatter, ordinateFormatter) {
            var fmt = formatter ? formatter : d3.format('.3f');
            var ordfmt = ordinateFormatter ? ordinateFormatter : d3.format('.3e');
            if (v < 1 || v > 1000000) {
                return ordfmt(v);
            }
            return fmt(v);
        },

        getAspectRatio: function(modelName, json, defaultRatio) {
            if (! json.aspectRatio && appState.isLoaded() && appState.applicationState()[modelName]) {
                var ratioEnum = appState.applicationState()[modelName].aspectRatio;
                if (ratioEnum) {
                    return parseFloat(ratioEnum);
                }
            }
            return json.aspectRatio || defaultRatio || 1.0;
        },

        initialHeight: function(scope) {
            return scope.isAnimation ? 1 : INITIAL_HEIGHT;
        },

        initImage: function(plotRange, heatmap, cacheCanvas, imageData, modelName, threshold=null) {
            var scaleFunction = this.scaleFunction(modelName);
            if (scaleFunction) {
                if (["e", "10", "2"].indexOf(scaleFunction.powerName) >= 0) {
                    plotRange.min = d3.min(heatmap, function(row) {
                        return d3.min(row, function(x) {
                            return x <= 0 ? Infinity : x;});
                    });
                }
                plotRange = {
                    min: scaleFunction(plotRange.min),
                    max: scaleFunction(plotRange.max),
                };
            }
            var colorScale = this.colorScaleForPlot(plotRange, modelName);
            var xSize = heatmap[0].length;
            var ySize = heatmap.length;
            var img = imageData;

            for (var yi = 0, p = -1; yi < ySize; ++yi) {
                for (var xi = 0; xi < xSize; ++xi) {
                    var v = heatmap[yi][xi];
                    if (scaleFunction) {
                        const old = v;
                        v = scaleFunction(v);
                        if (! v && plotRange.min === 0 && old) {
                            // special case for 0..n range with log scale
                            // scale log(1) to a nonzero value
                            v = 0.5;
                        }
                    }
                    var c = d3.rgb(colorScale(v));
                    img.data[++p] = c.r;
                    img.data[++p] = c.g;
                    img.data[++p] = c.b;
                    let a = 255;
                    if (threshold !== null) {
                        if (threshold[0] === 0 && v === 0) {
                            a = 0;
                        }
                        else {
                            a = v <= threshold[1] && v >= threshold[0] ? 255 : 0;
                        }
                    }
                    img.data[++p] = a;
                }
            }
            try {
                cacheCanvas.getContext('2d').putImageData(img, 0, 0);
            }
            catch (e) {
                throw new Error('Plot data size is not supported by the browser');
            }
            return colorScale;
        },

        linkPlot: function(scope, element) {
            setupSelector(scope, element);
            scope.isAnimation = appState.isAnimationModelName(scope.modelName);
            var requestData;

            if (scope.isClientOnly) {
                requestData = function() {};
            }
            else if (scope.isAnimation) {
                requestData = initAnimation(scope);
            }
            else {
                requestData = initPlot(scope);
            }

            // also emit so scopes in either direction can see
            scope.broadcastEvent = function(args) {
                scope.$broadcast('sr-plotEvent', args);
                scope.$emit('sr-plotEvent', args);
            };
            // work-around for #6230 Safari browser
            $(element, 'div.sr-plot').on('wheel', e => {});
            scope.$on('$destroy', function() {
                scope.destroy();
                $(d3.select(scope.element).select('svg.sr-plot').node()).off();
                $(scope.element, 'div.sr-plot').off();
                scope.element = null;
            });

            scope.$on(
                scope.modelName + '.changed',
                function() {
                    scope.prevFrameIndex = SIREPO.nonDataFileFrame;
                    panelState.clear(scope.modelName);
                    if (! scope.isClientOnly) {
                        requestData();
                    }
                });

            scope.isLoading = () => panelState.isLoading(scope.modelName);

            // scope.resize is not defined until later
            scope.$on('sr-window-resize', () => scope.resize());

            // #777 catch touchstart on outer svg nodes to prevent browser zoom on ipad
            $(d3.select(scope.element).select('svg.sr-plot').node()).on('touchstart touchmove', function(event) {
                event.preventDefault();
                event.stopPropagation();
            });
            scope.init();
            if (appState.isLoaded()) {
                if (scope.isAnimation && scope.defaultFrame) {
                    scope.defaultFrame();
                }
                else {
                    requestData();
                }
            }
            // let the parent and child scope know the plot is ready.
            // used by parameterWithLattice
            scope.$emit('sr-plotLinked');
            // used by interactiveOverlay, focusCircle, popupReport
            scope.$broadcast('sr-plotLinked');
        },

        linearlySpacedArray: linearlySpacedArray,

        min2d: function(data) {
            return d3.min(data, function(row) {
                return d3.min(row);
            });
        },

        min3d: function(data) {
            return d3.min(data, function(row) {
                return d3.min(row, function(col) {
                    return d3.min(col);
                });
            });
        },

        max2d: function(data) {
            return d3.max(data, function(row) {
                return d3.max(row);
            });
        },

        max3d: function(data) {
            return d3.max(data, function(row) {
                return d3.max(row, function(col) {
                    return d3.max(col);
                });
            });
        },

        pixelSize: function(xAxisScale, yAxisScale, width, height, xValues, yValues) {
            const xZoomDomain = xAxisScale.domain();
            const xDomain = xValues.srDomain || [xValues[0], xValues[xValues.length - 1]];
            const yZoomDomain = yAxisScale.domain();
            const yDomain = yValues.srDomain || [yValues[0], yValues[yValues.length - 1]];
            const zoomWidth = xZoomDomain[1] - xZoomDomain[0];
            const zoomHeight = yZoomDomain[1] - yZoomDomain[0];
            return {
                x: Math.round(((xDomain[1] - xDomain[0]) / zoomWidth * width / xValues.length)),
                y: Math.round(((yDomain[1] - yDomain[0]) / zoomHeight * height / yValues.length)),
            };
        },

        // create a 2d shape for d3 to plot - note that x, y are required because d3 looks for those
        // attributes
        plotShape: function(id, name, center, size, color, alpha, fillStyle, strokeStyle, dashes, layoutShape, points) {
            function getCoords(obj) {
                let coords = [];
                for (const dim in obj) {
                    coords.push(obj[dim]);
                }
                return coords;
            }

            function setCoords(obj, coords) {
                Object.keys(obj).forEach(function(dim, i) {
                    obj[dim] = coords[i];
                });
            }

            const shape = {
                addLink: function(otherShape, linkFunction) {
                    this.links.push(self.plotShapeLink(this, otherShape, linkFunction));
                },
                getCenterCoords: function() {
                    return getCoords(this.center);
                },
                getSizeCoords: function() {
                    return getCoords(this.size);
                },
                runLinks: function() {
                    var linkRes = [];
                    this.links.forEach(function (l) {
                        linkRes.push(l.fn(l.shape, l.linkedShape));
                    });
                    return linkRes;
                },
                setCenter: function(coords) {
                    setCoords(this.center, coords);
                },
                setSize: function(coords) {
                    setCoords(this.size, coords);
                },
                alpha: alpha,
                axes: ['x', 'y'],
                center: {
                    x: center[0], y: center[1]
                },
                color: color,
                dashes: dashes,
                draggable: true,
                fillStyle: fillStyle,
                id: id,
                layoutShape: layoutShape,
                links: [],
                name: name,
                points: points,
                size: {
                    x: size[0], y: size[1]
                },
                strokeStyle: strokeStyle,
                x: center[0] + SIREPO.SCREEN_INFO.x.direction * size[0] / 2,
                y: center[1] + SIREPO.SCREEN_INFO.y.direction * size[1] / 2,
            };
            return shape;
        },

        plotLine: function(id, name, line, color, alpha, strokeStyle, dashes) {
            var shape = this.plotShape(id, name, SIREPO.ZERO_ARR, SIREPO.ZERO_ARR, color, alpha, null, strokeStyle, dashes, 'line');
            shape.line = line;
            return shape;
        },

        // link on shape to another so that some aspect of the linked shape is tied to
        // the main shape via a provided function
        plotShapeLink: function(shape, linkedShape, linkFunction) {
            return {
                shape: shape,
                linkedShape: linkedShape,
                fn: linkFunction,
            };
        },

        plotTitle: (element) => {
            return $(element).closest('.panel').find('.sr-panel-heading').text();
        },

        recalculateDomainFromPoints: function(modelName, yScale, points, xDomain, invertAxis) {
            var ydom;
            var min_nonzero = Number.MAX_VALUE;
            var scaleFunction = this.scaleFunction(modelName);

            for (var i = 0; i < points.length; i++) {
                var d = points[i];
                if (d[0] > xDomain[1] || d[0] < xDomain[0]) {
                    continue;
                }
                if (ydom) {
                    if (d[1] < ydom[0]) {
                        ydom[0] = d[1];
                    }
                    else if (d[1] > ydom[1]) {
                        ydom[1] = d[1];
                    }
                }
                else {
                    ydom = [d[1], d[1]];
                }
                if (d[1] > 0 && d[1] < min_nonzero) { min_nonzero = d[1]; }
            }
            if (appState.models[modelName].useIntensityLimits == '1') {
                var m = appState.models[modelName];
                ydom = [
                    m.minIntensityLimit,
                    m.maxIntensityLimit,
                ];
            }
            if (ydom) {
                if (scaleFunction && ydom[0] <= 0 && ['e', '2', '10'].indexOf(scaleFunction.powerName) >= 0) {
                    ydom[0] = min_nonzero;
                }

                ydom = this.scaleYDomain(yScale, ydom, scaleFunction, ydom[0] > 0);
                if (invertAxis) {
                    var x = ydom[0];
                    ydom[0] = ydom[1];
                    ydom[1] = x;
                    yScale.domain(ydom).nice();
                }
            }
        },

        refreshConvergencePoints: function(select, parentClass, graphLine) {
            for (var i = 0; i < MAX_PLOTS; i++) {
                select(parentClass + ' .line-' + i).attr('d', graphLine);
            }
        },

        // takes a 24-bit color integer and returns an rgb array with values 0 -> <range>
        // (typically 256 or 1.0)
        //rgbFromInt: function(c, range=256.0)  {
        rgbFromInt: function(c, range)  {
            if (angular.isUndefined(range)) {
                range = 256.0;
            }
            var b = range * ((c % 256) / 256.0);
            var g = range * ((((c - b) / 256) % 256) / 256.0);
            var r = range * (((c - b - 256 * g) / (256 * 256)) / 256.0);
            return [r, g, b];
        },

        safeHeatmap: function(heatmap) {
            const FIREFOX_MAX_SIZE = 16384;
            // special case for Firefox which limits canvas dimensions
            // no sampling: just cut array size in half until proper size is reached
            if ($window.navigator.userAgent.indexOf('Firefox') >= 0) {
                while (heatmap[0].length > FIREFOX_MAX_SIZE) {
                    const rows = heatmap.length;
                    for (let i = 0; i < rows; i++) {
                        heatmap[i] = heatmap[i].filter((d, idx) => idx % 2 == 0);
                    }
                }
                while (heatmap.length > FIREFOX_MAX_SIZE) {
                    const rows = parseInt(heatmap.length / 2);
                    for (let i = 0; i < rows; i++) {
                        heatmap[i] = heatmap[i * 2];
                    }
                    heatmap.length = rows;
                }
            }
            return heatmap;
        },

        scaleFunction: function(modelName) {
            // returns the scaling function (ex. Math.log) or null
            var scale = null;
            if (appState.isLoaded() && appState.models[modelName]) {
                scale = appState.models[modelName].plotScale;
            }
            return scale ? LOG_SCALE[scale] : null;
        },

        scaleYDomain: function(yScale, yDomain, scaleFunction, isZeroMin) {
            if (yDomain && yDomain[0] != yDomain[1]) {
                if (scaleFunction) {
                    yDomain = yDomain.map(scaleFunction);
                }
                else if (isZeroMin && SIREPO.PLOTTING_YMIN_ZERO) {
                    yDomain[0] = 0;
                }
                yScale.domain(yDomain).nice();
            }
            return yDomain;
        },

        setTextOnlyReport: function(plotScope) {
            plotScope.clearData = noOp;
            plotScope.destroy = noOp;
            plotScope.init = noOp;
            plotScope.resize = noOp;
        },

        setupSelector: setupSelector,

        tickFontSize: function(node) {
            var defaultSize = 12;
            if (! node || ! node[0] || ! node[0][0]) {
                return defaultSize;
            }
            if (node.style) {
                return utilities.fontSizeFromString(node.style('font-size')) || defaultSize;
            }
            return defaultSize;
        },

        ticks: function(axis, width, isHorizontalAxis) {
            var spacing = isHorizontalAxis ? 80 : 50;
            var n = Math.max(Math.round(width / spacing), 2);
            axis.ticks(n);
        },

        // ensures the axis domain fits in the fullDomain
        // returns true if size is reset to full
        trimDomain: function(axisScale, fullDomain) {
            const dom = axisScale.domain();
            if (fullDomain[0] > fullDomain[1]) {
                const zoomSize = dom[0] - dom[1];

                if (zoomSize >= (fullDomain[0] - fullDomain[1])) {
                    axisScale.domain(fullDomain);
                    return true;
                }
                if (dom[1] < fullDomain[1]) {
                    axisScale.domain([zoomSize + fullDomain[1], fullDomain[1]]);
                }
                if (dom[0] > fullDomain[0]) {
                    axisScale.domain([fullDomain[0], fullDomain[0] - zoomSize]);
                }
                return false;
            }
            const zoomSize = dom[1] - dom[0];

            if (zoomSize >= (fullDomain[1] - fullDomain[0])) {
                axisScale.domain(fullDomain);
                return true;
            }
            if (dom[0] < fullDomain[0]) {
                axisScale.domain([fullDomain[0], zoomSize + fullDomain[0]]);
            }
            if (dom[1] > fullDomain[1]) {
                axisScale.domain([fullDomain[1] - zoomSize, fullDomain[1]]);
            }
            return false;
        },

        vtkPlot: function(scope, element) {

            scope.element = element[0];
            var requestData = initAnimation(scope);

            scope.$on('$destroy', function() {
                scope.destroy();
                scope.element = null;
            });

            scope.$on(
                scope.modelName + '.changed',
                function() {
                    scope.prevFrameIndex = SIREPO.nonDataFileFrame;
                    panelState.clear(scope.modelName);
                    requestData();
                });
            scope.isLoading = function() {
                return panelState.isLoading(scope.modelName);
            };
            scope.$on('sr-window-resize', function() {
                scope.resize();
            });

            scope.init();
            if (appState.isLoaded()) {
                requestData();
            }
        },

    };

    return self;
});

SIREPO.app.directive('animationButtons', function() {
    return {
        restrict: 'A',
        template: `
            <div data-ng-if="isAnimation && hasManyFrames()" style="width: 100%;" class="text-center">
              <button type="button" class="btn btn-default" data-ng-disabled="isFirstFrame()" data-ng-click="firstFrame()"><span class="glyphicon glyphicon-backward"></span></button>
              <button type="button" class="btn btn-default" data-ng-disabled="isFirstFrame()" data-ng-click="advanceFrame(-1, true)"><span class="glyphicon glyphicon-step-backward"></span></button>
              <button type="button" class="btn btn-default" data-ng-click="togglePlay()"><span class="glyphicon glyphicon-{{ isPlaying ? \'pause\' : \'play\' }}"></span></button>
              <button type="button" class="btn btn-default" data-ng-disabled="isLastFrame()" data-ng-click="advanceFrame(1, true)"><span class="glyphicon glyphicon-step-forward"></span></button>
              <button type="button" class="btn btn-default" data-ng-disabled="isLastFrame()" data-ng-click="lastFrame()"><span class="glyphicon glyphicon-forward"></span></button>
            </div>
        `,
    };
});

SIREPO.app.service('plot2dService', function(appState, layoutService, panelState, plotting, utilities) {

    this.init2dPlot = function($scope, attrs) {
        var colorbar, scaleFunction, zoom;
        // default scope values
        $.extend($scope, {
            aspectRatio: 4.0 / 7,
            zoomContainer: '.overlay',
        });
        $.extend($scope, attrs);
        $scope.width = $scope.height = 0;
        $scope.dataCleared = true;
        $scope.axes = {
            x: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh),
            y: layoutService.plotAxis($scope.margin, 'y', 'left', refresh),
            y2: layoutService.plotAxis($scope.margin, 'y2', 'right', refresh),
        };
        function init() {
            $scope.select('svg.sr-plot').attr('height', plotting.initialHeight($scope));
            $.each($scope.axes, function(dim, axis) {
                axis.init();
                axis.grid = axis.createAxis();
            });
            $scope.graphLine = d3.svg.line()
                .x(function(d) {
                    return $scope.axes.x.scale(d[0]);
                })
                .y(function(d) {
                    return $scope.axes.y.scale(scaleFunction ? scaleFunction(d[1]) : d[1]);
                });
            resetZoom();
        }

        function recalcAxes() {
            $.each($scope.axes, function(dim, axis) {
                axis.updateLabelAndTicks({
                    width: $scope.width,
                    height: $scope.height,
                    scaleFunction: dim == 'x' ? null: scaleFunction,
                }, $scope.select);
                axis.grid.ticks(axis.tickCount);
                $scope.select('.' + dim + '.axis.grid').call(axis.grid);
            });
        }

        function refresh() {
            if (! $scope.axes.x.domain) {
                return;
            }
            if (layoutService.plotAxis.allowUpdates) {
                recalcAxes();
                var elementWidth = parseInt($scope.select().style('width'));
                if (isNaN(elementWidth)) {
                    return;
                }
                [$scope.height, $scope.width] = plotting.constrainFullscreenSize($scope, elementWidth, $scope.aspectRatio);
                $scope.select('svg.sr-plot')
                    .attr('width', $scope.width + $scope.margin.left + $scope.margin.right)
                    .attr('height', $scope.height + $scope.margin.top + $scope.margin.bottom);
                $scope.axes.x.scale.range([0, $scope.width]);
                $scope.axes.y.scale.range([$scope.height, 0]);
                if ($scope.axes.y2) {
                    $scope.axes.y2.scale.range([$scope.height, 0]);
                }
                $scope.axes.x.grid.tickSize(-$scope.height);
                $scope.axes.y.grid.tickSize(-$scope.width);
                recalcAxes();
            }
            var isFullSize = plotting.trimDomain($scope.axes.x.scale, $scope.axes.x.domain);
            if ($scope.recalculateYDomain && ! $scope.isZoomXY) {
                $scope.recalculateYDomain();
            }
            else if (isFullSize) {
                $scope.axes.y.scale.domain($scope.axes.y.domain).nice();
            }
            $scope.select($scope.zoomContainer)
                .classed('mouse-zoom', isFullSize)
                .classed('mouse-move', ! isFullSize && $scope.isZoomXY)
                .classed('mouse-move-ns', ! isFullSize && $scope.isZoomY)
                .classed('mouse-move-ew', ! isFullSize && ! ($scope.isZoomXY || $scope.isZoomY));
            resetZoom();
            $scope.select($scope.zoomContainer).call(zoom);
            if ($scope.wantColorbar) {
                colorbar.barlength($scope.height)
                    .origin([0, 0]);
                $scope.pointer = $scope.select('.colorbar').call(colorbar);
            }
            $scope.refresh();
        }

        function resetZoom() {
            if ($scope.isZoomY) {
                zoom = $scope.axes.y.createZoom($scope);
                return;
            }
            zoom = $scope.axes.x.createZoom($scope);
            if ($scope.isZoomXY) {
                zoom.y($scope.axes.y.scale);
            }
        }

        $scope.clearData = function() {
            $scope.dataCleared = true;
            $scope.axes.x.domain = null;
        };

        $scope.destroy = function() {
            zoom.on('zoom', null);
            $($scope.element).find($scope.zoomContainer).off();
        };

        $scope.resize = function() {
            if ($scope.select().empty()) {
                return;
            }
            refresh();
        };

        $scope.updatePlot = function(json) {
            $scope.dataCleared = false;
            $.each($scope.axes, (dim, axis) => {
                axis.updateLabel(json[dim + '_label'] || '', $scope.select);
            });
            $scope.select('.main-title').text(json.title);
            $scope.select('.sub-title').text(json.subtitle);
            if ($scope.wantColorbar) {
                var colorMap = plotting.colorMapFromModel($scope.modelName);
                $scope.colorScale = d3.scale.linear()
                    .domain(plotting.linearlySpacedArray(json.v_min, json.v_max, colorMap.length))
                    .range(colorMap);
                colorbar = Colorbar()
                    .scale($scope.colorScale)
                    .thickness(30)
                    .margin({top: 10, right: 60, bottom: 20, left: 10})
                    .orient("vertical");
            }
            scaleFunction = plotting.scaleFunction($scope.modelName);
            panelState.waitForUI($scope.resize);
        };

        init();
    };
});

SIREPO.app.service('focusPointService', function(plotting) {
    var svc = this;

    svc.dataCoordsToMouseCoords = function(modelName, focusPoint) {
        var x = focusPoint.data.x;
        var scaleFunction = plotting.scaleFunction(modelName);
        var y = scaleFunction ? scaleFunction(focusPoint.data.y) : focusPoint.data.y;
        var mouseX, mouseY;
        if (focusPoint.config.invertAxis) {
            mouseX = focusPoint.config.yAxis.scale(y);
            mouseY = focusPoint.config.xAxis.scale(x);
        }
        else {
            mouseX = focusPoint.config.xAxis.scale(x);
            mouseY = focusPoint.config.yAxis.scale(y);
        }
        if (isNaN(mouseX) || isNaN(mouseY)) {
            return null;
        }
        return {
            x: mouseX,
            y: mouseY
        };
    };

    svc.formatFocusPointData = function(focusPoint, xLabel, yLabel, xUnits, yUnits) {
        var xl = xLabel || focusPoint.config.xLabel || 'X';
        var yl = yLabel || focusPoint.config.yLabel || 'Y';
        var xu = processUnit(xUnits || focusPoint.config.xAxis.units);
        var yu = processUnit(yUnits || focusPoint.config.yAxis.units);
        var fmt = {
            xText: formatDatum(xl, focusPoint.data.x, xu),
            yText: formatDatum(yl, focusPoint.data.y, yu),
        };
        if (SIREPO.PLOTTING_SHOW_FWHM) {
            fmt.fwhmText = formatFWHM(focusPoint.data.fwhm, focusPoint.config.xAxis.units);
        }
        return fmt;
    };

    svc.hideFocusPoint = function(plotScope, killFocus) {
        plotScope.broadcastEvent({
            name: 'hideFocusPointInfo',
            killFocus: killFocus,
        });
        if (plotScope.hideFocusPointText) {
            plotScope.hideFocusPointText();
        }
    };

    svc.loadFocusPoint = function(focusPoint, axisPoints, preservePoint, plotScope) {
        var hideAfterLoad = ! focusPoint.load(axisPoints, preservePoint);
        if (hideAfterLoad) {
            svc.hideFocusPoint(plotScope);
        }
    };

    svc.moveFocusPoint = function(plotScope, focusPoint) {
        plotScope.broadcastEvent({
            name: 'moveFocusPointInfo',
            focusPoint: focusPoint,
        });
        if (plotScope.showFocusPointText) {
            plotScope.showFocusPointText(focusPoint);
        }
    };

    svc.refreshFocusPoint = function(focusPoint, plotScope, isMainFocus, geometry) {
        plotScope.broadcastEvent({
            name: 'showFocusPointInfo',
            focusPoint: focusPoint,
            isMainFocus: isMainFocus,
            geometry: geometry,
        });
    };

    svc.setupFocusPoint = function(xAxis, yAxis, invertAxis, name) {
        return {
            config: {
                name: name,
                color: 'steelblue',
                invertAxis: invertAxis,
                xAxis: xAxis,
                yAxis: yAxis,
                xLabel: '',
                yLabel: '',
            },
            data: {
                focusIndex: -1,
                isActive: false,
            },
            load: function(axisPoints, preservePoint) {
                if (preservePoint && (axisPoints.length != (this.config.points || []).length)) {
                    preservePoint = false;
                }
                this.config.points = axisPoints;
                if (preservePoint) {
                    return true;
                }
                return false;
            },
            move: function(step) {
                if (! this.data.isActive) {
                    return false;
                }
                if (this.config.invertAxis) {
                    step = -step;
                }
                var newIndex = this.data.focusIndex + step;
                if (newIndex < 0 || newIndex >= this.config.points.length) {
                    return false;
                }
                this.data.focusIndex = newIndex;
                return true;
            },
            unset: function() {
                this.data.focusIndex = -1;
                this.data.isActive = false;
            },
        };
    };

    svc.updateFocus = function(focusPoint, mouseX, mouseY, strategy) {
        // lastClickX determines if the user is panning or clicking on a point
        if (! focusPoint.config.points || Math.abs(focusPoint.data.lastClickX - d3.event[focusPoint.config.invertAxis ? 'clientY' : 'clientX']) > 10) {
            return false;
        }
        var x = focusPoint.config.xAxis.scale.invert(mouseX);
        strategy = strategy || 'maximum';
        var spread = strategy == 'maximum' ? 10 : 100;
        var xMin = focusPoint.config.xAxis.scale.invert(mouseX - spread);
        var xMax = focusPoint.config.xAxis.scale.invert(mouseX + spread);
        if (xMin > xMax) {
            var swap = xMin;
            xMin = xMax;
            xMax = swap;
        }
        var domain = focusPoint.config.xAxis.scale.domain();
        if (xMin < domain[0]) {
            xMin = domain[0];
        }
        if (xMax > domain[1]) {
            xMax = domain[1];
        }

        focusPoint.data.focusIndex = -1;
        var selectedPoint;
        for (var i = 0; i < focusPoint.config.points.length; i++) {
            var p = focusPoint.config.points[i];
            if (p[0] > xMax || p[0] < xMin) {
                continue;
            }
            if (strategy == 'maximum') {
                if (! selectedPoint || p[1] > selectedPoint[1]) {
                    selectedPoint = p;
                    focusPoint.data.focusIndex = i;
                    focusPoint.data.isActive = true;
                }
            }
            else if (strategy == 'closest') {
                if (! selectedPoint || (Math.abs(p[0] - x) < Math.abs(selectedPoint[0] - x))) {
                    selectedPoint = p;
                    focusPoint.data.focusIndex = i;
                    focusPoint.data.isActive = true;
                }
            }
            else {
                throw new Error('invalid focus point strategy: ' + strategy);
            }
        }
        if (selectedPoint) {
            return svc.updateFocusData(focusPoint);
        }
        return false;
    };

    svc.updateFocusData = function(focusPoint) {
        if (! focusPoint.data.isActive) {
            return false;
        }

        var p = focusPoint.config.points[focusPoint.data.focusIndex];
        var domain = focusPoint.config.xAxis.scale.domain();
        if (!p || p[0] < domain[0] || p[0] > domain[1]) {
            return false;
        }

        focusPoint.data.x = p[0];
        focusPoint.data.y = p[1];
        focusPoint.data.fwhm = fwhmFromLocalVals(focusPoint);
        return true;
    };

    function formatDatum(label, val, units) {
        return val || val === 0
            ? label + ' = ' + plotting.formatValue(val) + ' ' + (units || '')
            : '';
    }

    function formatFWHM(fwhm, units) {
        return fwhm ? 'FWHM = ' + d3.format('.6s')(fwhm) + (units || '') : '';
    }

    function fwhmFromLocalVals(focusPoint) {

        var points = focusPoint.config.points;
        var focusIndex = focusPoint.data.focusIndex;

        var xValues = [];
        var yValues = [];
        for (var i = 0; i < points.length; i++) {
            xValues.push(points[i][0]);
            yValues.push(points[i][1]);
        }

        // Find the local maximum and the left and right minima:
        var peakIndex = null;
        var rightMinIndex = null;
        var leftMinIndex = null;
        if (focusIndex < xValues.length - 1 && focusIndex > 0) { // check if the index is within the range
            if (points[focusIndex][1] < points[focusIndex - 1][1] || points[focusIndex][1] < points[focusIndex + 1][1]) { // step on the left and on the right to see if it's a local maximum
                // It's not a local maximum!
                if (points[focusIndex][1] < points[focusIndex - 1][1]) { // we are on the right from the maximum
                    for (i = focusIndex; i > 0; i--) { // <<< go to the left to find the maximum
                        if (points[i-1][1] < points[i][1]) { // we crossed the maximum and started to descend
                            // ^ <<< - we reached the maximum:
                            peakIndex = i;
                            break;
                        }
                    }
                }
                else { // we are on the left from the maximum
                    for (i = focusIndex + 1; i < xValues.length; i++) { // >>> go to the right to find the maximum
                        if (points[i-1][1] > points[i][1]) { // we crossed the maximum and started to descend
                            // >>> ^ - we reached the maximum:
                            peakIndex = i - 1;
                            break;
                        }
                    }
                }
            }
            else {
                // ^ - we are at the local maximum.
                peakIndex = focusIndex;
            }

            // >>> go to the right from the peak to find the right minimum:
            for (i = peakIndex + 1; i < xValues.length; i++) {
                if (points[i-1][1] < points[i][1]) {
                    // >>> v - we reached the right minimum:
                    rightMinIndex = i - 1;
                    break;
                }
            }
            if (! rightMinIndex) {
                rightMinIndex = xValues.length - 1;
            }

            // <<< go to the left to find the left minimum:
            for (i = peakIndex; i > 0; i--) {
                if (points[i-1][1] > points[i][1]) {
                    // v <<< - we reached the left minimum:
                    leftMinIndex = i;
                    break;
                }
            }
            if (! leftMinIndex) {
                leftMinIndex = 0;
            }
        }
        // Calculate the FWHM for the selected peak (between the left and the right minima - v^v):
        if (peakIndex) {
            var localXValues = [];
            var localYValues = [];
            for (i = leftMinIndex; i <= rightMinIndex; i++) {
                localXValues.push(points[i][0]);
                localYValues.push(points[i][1]);
            }
            return plotting.calculateFWHM(localXValues, localYValues);
        }
        return NaN;
    }

    function processUnit(unit) {
        if (! unit) {
            return null;
        }
        // units that are "1/<unit>" become "<unit>-1" (otherwise the "1" looks like part of the value)
        // Once laTeX is handled we won't need this kind of thing
        var isInverse = /^1\/([a-zA-Z]+)$/;
        var m = unit.match(isInverse);
        if (m) {
            return m[1] + '-1';
        }
        return unit;
    }

});

SIREPO.app.service('layoutService', function(mathRendering, panelState, plotting, utilities) {
    var svc = this;

    svc.formatUnits = (units, isFixed) => {
        if (! units) {
            return '';
        }
        return isFixed
            ? `(${units})`
            : `[${units}]`;
    };

    svc.parseLabelAndUnits = function(label, isFixedUnits) {
        const re = isFixedUnits ? /\((.*?)\)/ : /\[(.*?)\]/;
        const match = label.match(re);
        if (match) {
            return {
                label: label.replace(re, '').trim(),
                units: match[1],
            };
        }
        return {
            label: label,
            units: '',
        };
    };

    svc.plotAxis = function(margin, dimension, orientation, refresh) {
        const MAX_TICKS = 10;
        const ZERO_REGEX = /^\-?0(\.0+)?(e\+0)?$/;

        // Using https://bl.ocks.org/mbostock/7621155 as a reference for log scales
        const superscript = "⁰¹²³⁴⁵⁶⁷⁸⁹";

        // global value, don't allow margin updates during zoom/pad handling
        svc.plotAxis.allowUpdates = true;

        const self = {};
        const debouncedRefresh = utilities.debounce(function() {
            const sum = margin.left + margin.right;
            refresh();
            if (sum != margin.left + margin.right) {
                refresh();
            }
        }, 500);


        ///////
        // these 3 methods are from a future version of d3, backported to this version of sirepo
        function d3_exponent(x) {
            x = d3_formatDecimalParts(Math.abs(x));
            return x ? x[1] : NaN;
        }

        function d3_formatDecimalParts(x, p) {
            if ((i = (x = p ? x.toExponential(p - 1) : x.toExponential()).indexOf("e")) < 0) {
                return null;
            }
            var i, coefficient = x.slice(0, i);
            return [
                coefficient.length > 1 ? coefficient[0] + coefficient.slice(2) : coefficient,
                +x.slice(i + 1)
            ];
        }

        function d3_precisionRound(step, max) {
            step = Math.abs(step);
            max = Math.abs(max) - step;
            return Math.max(0, d3_exponent(max) - d3_exponent(step)) + 1;
        }
        ///////

        function applyUnit(v, base, unit) {
            if (base) {
                v -= base;
            }
            return unit ? unit.scale(v) : v;
        }

        function baseLabel() {
            // remove any parenthesis first, ex. "p (mec)" --> "p"
            const label = (self.label || '').replace(/\s\(.*/, '');
            const res = label.length > 4 ? dimension : label;
            // padding is unicode thin-space
            return res ? ('< ' + res + ' >') : '';
        }

        function calcFormat(count, unit, base) {
            let code = 'e';
            let tickValues = self.scale.ticks(count);
            if (tickValues.length < 2) {
                tickValues = self.scale.ticks(count + 1);
            }
            const v0 = applyUnit(tickValues[0], base, unit);
            const v1 = applyUnit(tickValues[1], base, unit);
            const vn = applyUnit(tickValues[tickValues.length - 1], base, unit);
            const max = Math.abs(v0) > Math.abs(vn) ? Math.abs(v0) : vn;
            let decimals = d3_precisionRound(v1 - v0, max);
            if (useFloatFormat(v0) && useFloatFormat(vn)) {
                code = 'f';
                decimals -= valuePrecision(max);
                if (decimals < 0) {
                    decimals = 0;
                }
            }
            while (decimals > 0 && hasTrailingZeros(unit, base, code, decimals, tickValues)) {
                decimals -= 1;
            }
            return {
                base: base,
                tickCount: tickValues.length,
                decimals: decimals,
                code: code,
                unit: unit,
                tickValues: tickValues,
                format: d3.format('.' + decimals + code),
            };
        }

        function calcTickCount(formatInfo, canvasSize, fontSize) {
            let tickCount;
            if (dimension == 'x') {
                const width = Math.max(4, maxDomainWidth(formatInfo));
                tickCount = Math.min(MAX_TICKS, Math.round(canvasSize.width / (width * fontSize)));
            }
            else {
                tickCount = Math.min(MAX_TICKS, Math.round(canvasSize.height / (5 * fontSize)));
            }
            return Math.max(2, tickCount);
        }

        function calcTicks(formatInfo, canvasSize, fontSize) {
            formatInfo = calcFormat(
                calcTickCount(formatInfo, canvasSize, fontSize),
                formatInfo.unit,
            );

            if (formatInfo.decimals > 3 && ! canvasSize.scaleFunction && ! self.noBaseFormat) {
                const baseFormat = formatInfo.format;
                formatInfo = midPoint(formatInfo.tickValues, formatInfo.unit);
                formatInfo = midPoint(
                    calcFormat(
                        calcTickCount(formatInfo, canvasSize, fontSize),
                        formatInfo.unit,
                    ).tickValues,
                    formatInfo.unit,
                );
                formatInfo.baseFormat = baseFormat;
            }
            if ((orientation === 'left' || orientation === 'right') && ! canvasSize.isPlaying) {
                let w = maxDomainWidth(formatInfo) + 6;
                if (canvasSize.scaleFunction) {
                    w += 2;
                }
                margin[orientation] = w * (fontSize / 2);
            }
            self.svgAxis.ticks(formatInfo.tickCount);
            self.tickCount = formatInfo.tickCount;
            self.svgAxis.tickFormat(v => {
                if (canvasSize.scaleFunction) {
                    return formatScale(v, canvasSize.scaleFunction);
                }
                const res = formatInfo.format(applyUnit(v, formatInfo.base, formatInfo.unit));
                // format zero values as '0'
                if (ZERO_REGEX.test(res)) {
                    return '0';
                }
                return res.replace(/e\+0$/, '');
            });
            self.unitSymbol = formatInfo.unit ? formatInfo.unit.symbol : '';
            return formatInfo;
        }

        function formatBase(formatInfo, unit) {
            let v = '';
            if (formatInfo.base) {
                let label = baseLabel();
                if (label) {
                    label += ' = ';
                }
                else {
                    if (formatInfo.base > 0) {
                        label = '+';
                    }
                }
                v = label + formatInfo.baseFormat(applyUnit(formatInfo.base, 0, unit))
                                      .replace(/(\.\d+?)0+($|e)/, '$1$2')
                                      .replace(/\.0+($|e)/, '$1');
                if (unit) {
                    v += ' ' + unit.symbol + self.units;
                }
            }
            return v;
        }

        // If the axis is set to preserve units, use whatever prefix the plot started
        // with regardless of zoom.  Useful for non-linear units (1/sec, m^2, etc)
        function formatPrefix(base) {
            const d = self.scale.domain();
            if (! base) {
                base = 0;
            }
            return d3.formatPrefix(Math.max(Math.abs(d[0] - base), Math.abs(d[1] - base)), 0);
        }

        function formatScale(v, scaleFunction) {
            if (v == parseInt(v)) {
                return scaleFunction.powerName
                    + (v < 0 ? '⁻' : '')
                    + (v + "").split("").map(function(c) {
                        return superscript[c];
                    }).join("");
            }
            return '';
        }

        function hasTrailingZeros(unit, base, code, decimals, tickValues) {
            const f = d3.format('.' + decimals + code);
            return tickValues.every(v => {
                const vf = f(applyUnit(v, base, unit));
                return vf.search(/\.\d*0e/) >= 0 || vf.search(/\.\d*0$/) >= 0;
            });
        }

        function maxDomainWidth(formatInfo) {
            //const d = self.scale.domain();
            const d = [
                formatInfo.tickValues[0],
                formatInfo.tickValues[formatInfo.tickCount - 1],
            ];
            return Math.max(
                formatInfo.format(applyUnit(d[0], formatInfo.base, formatInfo.unit)).length,
                formatInfo.format(applyUnit(d[1], formatInfo.base, formatInfo.unit)).length,
            );
        }

        function midPoint(tickValues, unit) {
            // find the tickValue which is closest to the domain midpoint
            const d = self.scale.domain();
            const mid = d[0] + (d[1] - d[0]) / 2;
            const v = (tickValues.length - 1) / 2;
            const i1 = Math.floor(v);
            const i2 = Math.ceil(v);
            let base;
            if (Math.abs(tickValues[i1] - mid) > Math.abs(tickValues[i2] - mid)) {
                base = tickValues[i2];
            }
            else {
                base = tickValues[i1];
            }
            if (unit) {
                unit = formatPrefix(base);
            }
            return calcFormat(tickValues.length, unit, base);
        }

        function setLabel(label, select) {
            select(`.${dimension}-axis-label`).html(mathRendering.mathAsHTML(label));
        }

        function useFloatFormat(v) {
            v = valuePrecision(v);
            return v >= -2 && v <= 3;
        }

        function valuePrecision(v) {
            Math.log10 = Math.log10 || function(x) {
                return Math.log(x) * Math.LOG10E;
            };
            return Math.floor(Math.log10(Math.abs(v || 1)));
        }

        self.createAxis = function(orient) {
            return d3.svg.axis().scale(self.scale).orient(orient || orientation);
        };

        self.createZoom = function() {
            return d3.behavior.zoom()[dimension](self.scale)
                .on('zoom', function() {
                    // don't update the plot margins during zoom/pad
                    svc.plotAxis.allowUpdates = false;
                    refresh();
                    svc.plotAxis.allowUpdates = true;
                    // schedule a refresh to adjust margins later
                    debouncedRefresh();
                });
        };

        self.init = function() {
            self.scale = d3.scale.linear();
            self.svgAxis = self.createAxis();
        };

        self.parseLabelAndUnits = function(label) {
            const lu = svc.parseLabelAndUnits(label);
            self.units = lu.units;
            self.unitSymbol = '';
            self.label = lu.label;
        };

        self.updateLabel = (label, select) => {
            self.parseLabelAndUnits(label);
            setLabel(label, select);
        };

        self.updateLabelAndTicks = function(canvasSize, select, cssPrefix) {
            if (svc.plotAxis.allowUpdates) {
                // update the axis to get the tick font size from the css
                select((cssPrefix || '') + '.' + dimension + '.axis').call(self.svgAxis);
                const fontSize = plotting.tickFontSize(select('.sr-plot .axis text'));
                let formatInfo, unit;
                if (self.units) {
                    unit = formatPrefix(0);
                    formatInfo = calcTicks(calcFormat(MAX_TICKS, unit), canvasSize, fontSize);
                    setLabel(
                        self.label + (formatInfo.base ? (' - ' + baseLabel()) : '')
                        + ' ' + svc.formatUnits(formatInfo.unit.symbol + self.units),
                        select,
                    );
                }
                else {
                    formatInfo = calcTicks(calcFormat(MAX_TICKS), canvasSize, fontSize);
                    if (self.label) {
                        setLabel(
                            self.label + (formatInfo.base ? (' - ' + baseLabel()) : ''),
                            select,
                        );
                    }
                }
                if (! self.noBaseFormat) {
                    select('.' + dimension + '-base').text(formatBase(formatInfo, unit));
                }
            }
            select((cssPrefix || '') + '.' + dimension + '.axis').call(self.svgAxis);
        };

        return self;
    };
});

SIREPO.app.directive('columnForAspectRatio', function(appState) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@columnForAspectRatio',
        },
        transclude: true,
        template: `
            <div class="{{ columnClass() }}">
              <div data-ng-transclude=""></div>
            </div>
        `,
        controller: function($scope) {
            $scope.columnClass = function() {
                if (appState.isLoaded()) {
                    var ratio = parseFloat(appState.applicationState()[$scope.modelName].aspectRatio);
                    if (ratio <= 0.5) {
                        return 'col-md-12 col-xl-8 col-xxl-5';
                    }
                }
                return 'col-md-6 col-xl-4 col-xxl-2';
            };
        }
    };
});

SIREPO.app.directive('interactiveOverlay', function(focusPointService, keypressService, plotting, $timeout) {
    return {
        restrict: 'A',
        scope: {
            reportId: '<',
            focusPoints: '=',
            focusStrategy: '=',
        },
        controller: function($scope, $element) {
            if (! $scope.reportId || ! $scope.focusPoints) {
                // interactiveOverlay only applies if focusPoints are defined on the plot
                return;
            }
            plotting.setupSelector($scope, $element);

            var listenerId = SIREPO.UTILS.randomId();
            var geometries = [];
            var plotScope;

            function copyToClipboard() {
                if (! $scope.focusPoints || $scope.focusPoints.length === 0) {
                    return;
                }
                var focusHint = plotScope.select('.focus-hint');
                var focusText = plotScope.select('.focus-text');
                focusText.style('display', 'none');
                var inputField = $('<textarea>');
                $('body').append(inputField);

                var fmtText = '';
                $scope.focusPoints.forEach(function(fp, fpIndex) {
                    var fpt = plotScope.formatFocusPointData(fp);
                    if (fpIndex === 0) {
                        fmtText = fmtText + fpt.xText + '\n';
                    }
                    fmtText = fmtText + fpt.yText;
                    if (fpt.fwhmText) {
                        fmtText = fmtText + ', ' + fpt.fwhmText;
                    }
                    fmtText = fmtText + '\n';
                });
                inputField.val(fmtText).select();
                try {
                    document.execCommand('copy');
                    focusHint.style('display', null);
                    focusHint.text('Copied to clipboard');
                    $timeout(function() {
                        focusHint.style('display', 'none');
                        focusText.style('display', null);
                    }, 1000);
                }
                catch (e) {
                }
                inputField.remove();
            }

            function init() {
                if ($scope.focusPoints) {
                    $scope.focusPoints.forEach(function(fp) {
                        geometries.push(setupGeometry());
                    });
                }
                $scope.select()
                    .on('mousedown', onMouseDown)
                    .on('click', onClick)
                    .on('dblclick', copyToClipboard);
            }

            function onClick() {
                /*jshint validthis: true*/
                if (d3.event.defaultPrevented) {
                    // ignore event if drag is occurring
                    return;
                }
                if (plotScope.noOverlay) {
                    // if the data has multiple x datasets,
                    // the overlay will not work correctly
                    $scope.select()
                        .on('mousedown', null)
                        .on('click', null)
                        .on('dblclick', null);
                    return;
                }
                // start listening on clicks instead of mouseover
                keypressService.addListener(listenerId, onKeyDown, $scope.reportId);

                if ($scope.focusPoints) {
                    for (var fpIndex = 0; fpIndex < $scope.focusPoints.length; ++fpIndex) {
                        var fp = $scope.focusPoints[fpIndex];
                        var geometry = geometries[fpIndex];
                        if (! geometry) {
                            geometry = setupGeometry();
                            geometries[fpIndex] = geometry;
                        }
                        var axisIndex =  fp.config.invertAxis ? 1 : 0;
                        geometry.mouseX = d3.mouse(this)[axisIndex];
                        geometry.mouseY = d3.mouse(this)[1 - axisIndex];
                        if (focusPointService.updateFocus(fp, geometry.mouseX, geometry.mouseY, $scope.focusStrategy)) {
                            focusPointService.refreshFocusPoint(fp, plotScope, true, geometry);
                            if (plotScope.showFocusPointText) {
                                plotScope.showFocusPointText(fp);
                            }
                        }
                    }
                }
            }

            function onKeyDown() {
                var keyCode = d3.event.keyCode;
                var shiftFactor = d3.event.shiftKey ? 10 : 1;

                // do some focusPoint-independent work outside the loop
                if (keyCode == 27) { // escape
                    removeKeyListener();
                }
                if (keyCode == 9) {  // tab
                    keypressService.enableNextListener(d3.event.shiftKey ? -1 : 1);
                    d3.event.preventDefault();
                }
                for (var fpIndex = 0; fpIndex < $scope.focusPoints.length; ++fpIndex) {
                    if (!$scope.focusPoints[fpIndex].data.isActive) {
                        return;
                    }
                    var doUpdate = false;
                    var fp = $scope.focusPoints[fpIndex];
                    var geometry = geometries[fpIndex];
                    if (keyCode == 27) { // escape
                        fp.unset();
                        focusPointService.hideFocusPoint(plotScope);
                    }
                    if (keyCode == 37 || keyCode == 40) { // left & down
                        fp.move(-1 * shiftFactor);
                        doUpdate = true;
                        d3.event.preventDefault();
                    }
                    if (keyCode == 39 || keyCode == 38) { // right & up
                        fp.move(1 * shiftFactor);
                        doUpdate = true;
                        d3.event.preventDefault();
                    }
                    if (doUpdate) {
                        if (focusPointService.updateFocusData(fp)) {
                            focusPointService.moveFocusPoint(plotScope, fp);
                        }
                        else {
                            focusPointService.hideFocusPoint(plotScope);
                        }
                    }
                }
            }

            function onMouseDown() {
                if ($scope.focusPoints) {
                    $scope.focusPoints.forEach(function(fp) {
                        fp.data.lastClickX = d3.event[fp.config.invertAxis ? 'clientY' : 'clientX'];
                    });
                }
            }

            function removeKeyListener() {
                keypressService.removeListener(listenerId);
            }

            function setupGeometry() {
                return {
                    mouseX: 0,
                    mouseY: 0,
                };
            }

            init();

            $scope.$on('$destroy', function(event) {
                keypressService.removeReport($scope.reportId);
            });

            $scope.$on('sr-plotLinked', function(event) {
                plotScope = event.targetScope;
                //TODO(pjm): shouldn't put on plot scope, but needed by popupReport
                plotScope.copyToClipboard = copyToClipboard;
            });

            $scope.$on('sr-plotEvent', function(event, args) {
                if (args.name == 'hideFocusPointInfo') {
                    if (args.killFocus) {
                        removeKeyListener();
                    }
                }
            });
        },
    };
});

SIREPO.app.directive('focusCircle', function(focusPointService, plotting) {
    return {
        restrict: 'A',
        scope: {
            focusPoint: '=',
            isSoloPoint: '@',
        },
        // no "template", svg element outside a <svg> element don't work in MS Edge 38.14393
        controller: function($scope, $element) {
            plotting.setupSelector($scope, $element);
            var defaultCircleSize = $scope.select('circle').attr('r');

            function hideFocusCircle() {
                $scope.select().style('display', 'none');
            }

            function setInfoVisible(isVisible) {
                // don't invoke hideFocusCircle() - we want the data in place
                $scope.select('circle').style('opacity', isVisible ? 1.0 : 0.0);
            }

            function showFocusCircle(isMainFocus) {
                $scope.select().style('display', null);
                if (! focusPointService.updateFocusData($scope.focusPoint)) {
                    hideFocusCircle();
                    return;
                }
                var circle = $scope.select('circle');
                if (isMainFocus) {
                    circle.attr('r', defaultCircleSize);
                }
                else {
                    circle.attr('r', defaultCircleSize - 2);
                }
                circle.style('stroke', $scope.focusPoint.config.color);
                var mouseCoords = focusPointService.dataCoordsToMouseCoords(
                    $scope.$parent.$parent.modelKey || $scope.$parent.$parent.modelName,
                    $scope.focusPoint);
                if (mouseCoords) {
                    $scope.select().attr('transform', 'translate(' + mouseCoords.x + ',' + mouseCoords.y + ')');
                }
                else {
                    hideFocusCircle();
                }
            }

            $scope.$on('sr-plotEvent', function(event, args) {
                if (args.name == 'showFocusPointInfo') {
                    if ($scope.isSoloPoint) {
                        if (args.focusPoint == $scope.focusPoint) {
                            showFocusCircle(args.isMainFocus);
                        }
                        else if (args.isMainFocus) {
                            hideFocusCircle();
                            $scope.focusPoint.unset();
                        }
                    }
                    else {
                        showFocusCircle(args.isMainFocus);
                    }
                }
                else if (args.name == 'hideFocusPointInfo') {
                    hideFocusCircle();
                }
                else if (args.name == 'moveFocusPointInfo') {
                    if (args.focusPoint == $scope.focusPoint) {
                        showFocusCircle();
                    }
                }
                else if (args.name == 'setInfoVisible') {
                    if (args.focusPoint == $scope.focusPoint) {
                        setInfoVisible(args.isVisible);
                    }
                }
            });
        },
    };
});


SIREPO.app.directive('popupReport', function(focusPointService, plotting) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            focusPoints: '=',
            plots: '=',
        },
        template: `
            <div style="pointer-events: all; position: absolute" class="sr-popup-report"
              data-ng-drag="true" data-ng-drag-success="dragDone($data, $event)">
              <div class="panel panel-info">
                <div class="panel-heading" style="cursor: move; padding: 3px" ng-drag-handle="">
                  <a href><span style="margin-left: 3px" data-ng-click="copyToClipboard()"
                    class="glyphicon glyphicon-copy"></span></a>
                  <div class="pull-right"><button type="button" class="close"  data-ng-click="closePopup()"
                    style="margin-top: -2px; margin-right: 2px"><span>&times;</span></button></div>
                </div>
                <div style="padding: 4px; white-space: nowrap">
                <div style="height: 20px"><span data-text-with-math="focusPoints[0].config.xAxis.label"
                  data-is-dynamic="1"></span> = {{ pointText(0, true) }} {{ focusPoints[0].config.xAxis.units }}</div>
                <div data-ng-style="{ opacity: opacity($index) }" style="height: 20px"
                  data-ng-repeat="p in plots track by p._label + $index">
                  <div style="display:inline" data-color-circle="p"></div>
                  <span data-text-with-math="p._label"></span> = {{ pointText($index) }} {{ p._units }}
                </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope, $element) {
            let didDragToNewPositon = false;

            // prevent memory leak?
            $scope.focusPoints.allowClone = true;

            function adjustBounds(bound, dim) {
                if (bound < 1) {
                    return 1;
                }
                const p = popup();
                const v = p[dim]();
                const pv = p.parent()[dim]();
                if (bound > pv - v - 2) {
                    return pv - v - 2;
                }
                return bound;
            }

            function hidePopup() {
                didDragToNewPositon = false;
                popup().css({
                    display: 'none',
                });
            }

            function moveToFocusPoint() {
                if (didDragToNewPositon) {
                    return;
                }
                const m = focusPointService.dataCoordsToMouseCoords(
                    $scope.modelName, $scope.focusPoints[0]);
                if (m) {
                    const p = popup();
                    setPosition(m.x, p.offset().top - p.parent().offset().top);
                }
            }

            function plotScope() {
                let p = $scope.$parent;
                while (! p.broadcastEvent) {
                    p = p.$parent;
                }
                return p;
            }

            function popup() {
                return $($element).find('.sr-popup-report');
            }

            function setRelativePosition(left, top) {
                const p = popup();
                const po = p.parent().offset();
                setPosition(left - po.left, top - po.top);
            }

            function setPosition(left, top) {
                popup().css({
                    left: adjustBounds(left, 'width') + 'px',
                    top: adjustBounds(top, 'height') + 'px',
                    display: 'block',
                });
            }

            $scope.closePopup = () => {
                focusPointService.hideFocusPoint(plotScope(), true);
            };

            $scope.copyToClipboard = () => {
                plotScope().copyToClipboard();
            };

            $scope.dragDone = ($data, $event) => {
                didDragToNewPositon = true;
                const o = popup().offset();
                setRelativePosition(o.left, o.top);
            };

            $scope.opacity = (index) => {
                if (! $scope.plots[index]._isVisible) {
                    return 0.4;
                }
                return 1.0;
            };

            $scope.pointText = (index, xValue) => {
                if ($scope.focusPoints[index]) {
                    return plotting.formatValue($scope.focusPoints[index].data[xValue ? 'x' : 'y']);
                }
            };

            $scope.$on('sr-plotEvent', (event, args) => {
                if (args.name == 'showFocusPointInfo') {
                    if (args.geometry && ! didDragToNewPositon) {
                        setPosition(args.geometry.mouseX, args.geometry.mouseY);
                    }
                    $scope.$applyAsync();
                }
                else if (args.name == 'hideFocusPointInfo') {
                    hidePopup();
                }
                else if (args.name == 'moveFocusPointInfo') {
                    moveToFocusPoint();
                    $scope.$applyAsync();
                }
            });

        },
    };
});

SIREPO.app.service('keypressService', function() {
    const svc = this;
    const listeners = {};
    const reports = {};
    const activeListeners = [];
    let activeListenerId = null;

    function removeListenersForReport(reportId) {
        if (! reports[reportId]) {
            return;
        }
        const rlArr = reports[reportId];
        for(let rlIndex = 0; rlIndex < rlArr.length; ++rlIndex) {
            svc.removeListener(rlArr[rlIndex]);
        }
    }

    function reportForListener(listenerId) {
        if (! listenerId) {
            return null;
        }
        for(const reportId in reports) {
            const rlIndex = reports[reportId].indexOf(listenerId);
            if (rlIndex < 0) {
                continue;
            }
            return reportId;
        }
    }

    function showPanelActive(reportId, isActive) {
        if (isActive) {
            $('#' + reportId).parents('.panel').addClass('sr-panel-active');
            return;
        }
        $('#' + reportId).parents('.panel').removeClass('sr-panel-active');
    }

    svc.addListener = (listenerId, listener, reportId) => {
        listeners[listenerId] = listener;
        if (! reports[reportId]) {
                reports[reportId] = [];
        }
        reports[reportId].push(listenerId);
        if (activeListeners.indexOf(listenerId) < 0) {
            activeListeners.push(listenerId);
        }

        // turn off highlighting for active report panel, if any
        showPanelActive(reportForListener(activeListenerId), false);

        activeListenerId = listenerId;
        svc.enableListener(true);
    };

    // set the active listener, or
    // remove keydown listener from body element leaving the keys in place
    svc.enableListener = (doListen, listenerId) => {
        if (listenerId)  {
            activeListenerId = listenerId;
        }
        const reportId = reportForListener(activeListenerId);
        if (doListen && activeListenerId) {
            d3.select('body').on('keydown', listeners[activeListenerId]);
            showPanelActive(reportId, true);
            return;
        }
        d3.select('body').on('keydown', null);
        showPanelActive(reportId, false);
    };

    svc.enableNextListener = (direction) => {
        const lIndex = activeListeners.indexOf(activeListenerId);
        if (lIndex < 0) {
            return;
        }
        svc.enableListener(false);
        const d = direction < 0 ? -1 : 1;
        const newIndex = (lIndex + d + activeListeners.length) % activeListeners.length;
        svc.enableListener(true, activeListeners[newIndex]);
    };

    svc.removeListener = (listenerId) => {
        const lIndex = activeListeners.indexOf(listenerId);
        if (lIndex >= 0) {
            activeListeners.splice(lIndex, 1);
        }
        delete listeners[listenerId];

        const reportId = reportForListener(listenerId);
        showPanelActive(reportId, false);
        if (reportId) {
            reports[reportId].splice(reports[reportId].indexOf(listenerId), 1);
        }

        // activate the last one added, if any remain
        if (activeListeners.length > 0) {
            activeListenerId = activeListeners[activeListeners.length - 1];
            svc.enableListener(true);
        }
        else {
            activeListenerId = null;
            svc.enableListener(false);
        }
    };

    svc.removeReport = function(reportId) {
        removeListenersForReport(reportId);
        delete reports[reportId];
    };
});

SIREPO.app.directive('plot2d', function(focusPointService, plotting, plot2dService) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/plot2d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            var points;
            $scope.reportId = SIREPO.UTILS.randomId();
            $scope.focusPoints = [];

            $scope.formatFocusPointData = function(fp) {
                return focusPointService.formatFocusPointData(fp);
            };

            $scope.init = function() {
                plot2dService.init2dPlot($scope, {
                    margin: {top: 50, right: 10, bottom: 20, left: 75},
                });
                delete $scope.axes.y2;
                $scope.focusPoints.push(
                    focusPointService.setupFocusPoint($scope.axes.x, $scope.axes.y, false));
            };

            $scope.load = function(json) {
                var xPoints = json.x_points
                    ? json.x_points
                    : plotting.linearlySpacedArray(json.x_range[0], json.x_range[1], json.points.length);
                var xdom = [json.x_range[0], json.x_range[1]];
                if (!($scope.axes.x.domain && $scope.axes.x.domain[0] == xdom[0] && $scope.axes.x.domain[1] == xdom[1])) {
                    $scope.axes.x.domain = xdom;
                    points = [];
                    $scope.axes.x.scale.domain(xdom);
                }
                if (!SIREPO.PLOTTING_SHOW_CONVERGENCE_LINEOUTS) {
                    points = [];
                }
                var ymin = d3.min(json.points);
                var scaleFunction = plotting.scaleFunction($scope.modelName);
                if (ymin > 0 && ! scaleFunction) {
                    ymin = 0;
                }
                $scope.axes.y.domain = plotting.ensureDomain([ymin, d3.max(json.points)], scaleFunction);
                $scope.axes.y.scale.domain($scope.axes.y.domain).nice();
                var p = d3.zip(xPoints, json.points);
                plotting.addConvergencePoints($scope.select, '.plot-viewport', points, p);

                $scope.focusPoints.forEach(function(fp) {
                    focusPointService.loadFocusPoint(fp, p, true, $scope);
                    fp.config.xLabel = json.x_label;
                    fp.config.yLabel = json.y_label;
                });

                $scope.updatePlot(json);
                $scope.resize();
            };

            $scope.recalculateYDomain = function() {
                plotting.recalculateDomainFromPoints($scope.modelName, $scope.axes.y.scale, points[0], $scope.axes.x.scale.domain());
            };

            $scope.refresh = function() {
                plotting.refreshConvergencePoints($scope.select, '.plot-viewport', $scope.graphLine);
                for (var fpIndex = 0; fpIndex < $scope.focusPoints.length; ++fpIndex) {
                    focusPointService.refreshFocusPoint($scope.focusPoints[fpIndex], $scope);
                }
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('plot3d', function(appState, focusPointService, layoutService, plotting, utilities) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/plot3d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            var MIN_PIXEL_RESOLUTION = 10;
            $scope.reportId = SIREPO.UTILS.randomId();
            $scope.margin = {
                top: 50,
                left: 50,
                right: 45,
                bottom: 30,
            };
            $scope.pad = 10;
            $scope.noLabelPad = -18;
            // will be set to the correct size in resize()
            $scope.canvasSize = {
                width: 0,
                height: 0,
            };
            $scope.rightPanelWidth = $scope.bottomPanelHeight = 55;
            $scope.dataCleared = true;
            $scope.focusPoints = [];

            var canvas, ctx, fullDomain, heatmap, lineOuts, prevDomain, scaleFunction, xyZoom;
            var cacheCanvas, imageData;
            var aspectRatio = 1.0;
            var axes = {
                x: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh),
                y: layoutService.plotAxis($scope.margin, 'y', 'right', refresh),
                bottomY: layoutService.plotAxis($scope.margin, 'y', 'left', refresh),
                rightX: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh),
            };
            axes.rightX.noBaseFormat = true;
            axes.bottomY.noBaseFormat = true;

            var cursorShape = {
                '11': 'mouse-move-ew',
                '10': 'mouse-move-e',
                '01': 'mouse-move-w',
                '22': 'mouse-move-ns',
                '20': 'mouse-move-n',
                '02': 'mouse-move-s',
            };

            function adjustZoomToCenter(scale) {
                // if the domain is almost centered on 0.0 (within 10%) adjust zoom and offset to center
                var domain = scale.domain();
                if (SIREPO.PLOTTING_SUMMED_LINEOUTS) {
                    return;
                }
                if (domain[0] < 0 && domain[1] > 0) {
                    var width = domain[1] - domain[0];
                    var diff = (domain[0] + domain[1]) / width;
                    if (diff > 0 && diff < 0.1) {
                        domain[1] = -domain[0];
                    }
                    else if (diff > -0.1 && diff < 0) {
                        domain[0] = -domain[1];
                    }
                    else {
                        return;
                    }
                    scale.domain(domain);
                }
            }

            function clipDomain(scale, axisName) {
                var domain = fullDomain[axisName == 'x' ? 0 : 1];
                var domainSize = domain[1] - domain[0];
                var fudgeFactor = domainSize * 0.001;
                var d = scale.domain();
                var canMove = axisName == 'x' ? [1, 1] : [2, 2];

                if (d[0] - domain[0] <= fudgeFactor) {
                    canMove[0] = 0;
                    d[1] -= d[0] - domain[0];
                    d[0] = domain[0];
                }
                if (domain[1] - d[1] <= fudgeFactor) {
                    canMove[1] = 0;
                    d[0] -= d[1] - domain[1];
                    if (d[0] - domain[0] <= fudgeFactor) {
                        canMove[0] = 0;
                        d[0] = domain[0];
                    }
                    d[1] = domain[1];
                }
                scale.domain(d);
                var cursorKey = '' + canMove[0] + canMove[1];
                var className = 'mouse-rect-' + axisName;
                select('rect.' + className).attr('class', className + ' ' + (cursorShape[cursorKey] || 'mouse-zoom'));
                return canMove[0] + canMove[1];
            }

            function drawBottomPanelCut() {
                var row;
                var yBottom = axes.y.indexScale(axes.y.scale.domain()[0]);
                var yTop = axes.y.indexScale(axes.y.scale.domain()[1]);
                var yv = Math.round(yBottom + (yTop - yBottom) / 2);
                if (SIREPO.PLOTTING_SUMMED_LINEOUTS) {
                    row = sumRegion(
                        true,
                        Math.floor(yBottom + 0.5),
                        Math.ceil(yTop - 0.5),
                        Math.floor(axes.x.indexScale(axes.x.scale.domain()[0])),
                        Math.ceil(axes.x.indexScale(axes.x.scale.domain()[1])));
                }
                else {
                    row = heatmap[axes.y.values.length - 1 - yv];
                }
                var points = d3.zip(axes.x.values, row);
                plotting.recalculateDomainFromPoints($scope.modelName, axes.bottomY.scale, points, axes.x.scale.domain());
                drawLineout('x', yv, points, axes.x.cutLine);
                focusPointService.loadFocusPoint($scope.focusPointX, points, true, $scope);
            }

            function drawLineout(axis, key, points, cutLine) {
                if (! lineOuts[axis] || ! SIREPO.PLOTTING_SHOW_CONVERGENCE_LINEOUTS) {
                    lineOuts[axis] = {};
                }
                var axisClass = axis == 'x' ? '.bottom-panel' : '.right-panel';
                if (lineOuts[axis][key]) {
                    if (! appState.deepEquals(points, lineOuts[axis][key][0])) {
                        lineOuts[axis][key] = plotting.addConvergencePoints(select, axisClass, lineOuts[axis][key], points);
                    }
                }
                else {
                    lineOuts[axis] = {};
                    lineOuts[axis][key] = plotting.addConvergencePoints(select, axisClass, [], points);
                }
                plotting.refreshConvergencePoints(select, axisClass, cutLine);
            }

            function drawRightPanelCut() {
                var xLeft = axes.x.indexScale(axes.x.scale.domain()[0]);
                var xRight = axes.x.indexScale(axes.x.scale.domain()[1]);
                var xv = Math.round(xLeft + (xRight - xLeft) / 2);
                var points;

                if (SIREPO.PLOTTING_SUMMED_LINEOUTS) {
                    points = d3.zip(axes.y.values, sumRegion(
                        false,
                        Math.floor(axes.y.indexScale(axes.y.scale.domain()[0])),
                        Math.ceil(axes.y.indexScale(axes.y.scale.domain()[1])),
                        Math.floor(xLeft + 0.5),
                        Math.ceil(xRight - 0.5))).reverse();
                }
                else {
                    points = heatmap.map(function(v, i) {
                        return [axes.y.values[axes.y.values.length - 1 - i], v[xv]];
                    });
                }
                plotting.recalculateDomainFromPoints($scope.modelName, axes.rightX.scale, points, axes.y.scale.domain(), true);
                drawLineout('y', xv, points, axes.y.cutLine);
                focusPointService.loadFocusPoint($scope.focusPointY, points, true, $scope);
            }

            function exceededMaxZoom(scale, axisName) {
                var domain = fullDomain[axisName == 'x' ? 0 : 1];
                var domainSize = domain[1] - domain[0];
                var d = scale.domain();
                var pixels = (axisName == 'x' ? axes.x.values : axes.y.values).length * (d[1] - d[0]) / domainSize;
                return pixels < MIN_PIXEL_RESOLUTION;
            }

            function layoutFocusPointText() {
                select('.focus-text-close').node().setAttribute(
                    'x', select('.focus-text').node().getComputedTextLength() + 16,
                );
            }

            function refresh() {
                if (! fullDomain) {
                    return;
                }
                if (layoutService.plotAxis.allowUpdates && ! $scope.isPlaying) {
                    var elementWidth = parseInt(select().style('width'));
                    if (! heatmap || isNaN(elementWidth)){
                        return;
                    }
                    var canvasResize = 2 / 3;
                    var [totalHeight, totalWidth] = plotting.constrainFullscreenSize($scope, elementWidth, aspectRatio);
                    $scope.canvasSize.height = canvasResize * totalHeight;
                    $scope.canvasSize.width = canvasResize * totalWidth;
                    $scope.bottomPanelHeight = (1 - canvasResize) * totalHeight;
                    $scope.rightPanelWidth = (1 - canvasResize) * totalWidth + $scope.margin.right + $scope.pad;
                    axes.x.scale.range([0, $scope.canvasSize.width]);
                    axes.y.scale.range([$scope.canvasSize.height, 0]);
                    axes.bottomY.scale.range([$scope.bottomPanelHeight - $scope.pad - $scope.margin.bottom - 1, 0]);
                    axes.rightX.scale.range([0, $scope.rightPanelWidth - $scope.pad - $scope.margin.right]);
                }
                if (prevDomain && (exceededMaxZoom(axes.x.scale, 'x') || exceededMaxZoom(axes.y.scale, 'y'))) {
                    restoreDomain(axes.x.scale, prevDomain[0]);
                    restoreDomain(axes.y.scale, prevDomain[1]);
                }
                if (clipDomain(axes.x.scale, 'x') + clipDomain(axes.y.scale, 'y')) {
                    select('rect.mouse-rect-xy').attr('class', 'mouse-rect-xy mouse-move');
                }
                else {
                    select('rect.mouse-rect-xy').attr('class', 'mouse-rect-xy mouse-zoom');
                }
                plotting.drawImage(axes.x.scale, axes.y.scale, $scope.canvasSize.width, $scope.canvasSize.height, axes.x.values, axes.y.values, canvas, cacheCanvas, true);
                drawBottomPanelCut();
                drawRightPanelCut();

                axes.x.updateLabelAndTicks({
                    height: $scope.bottomPanelHeight,
                    width: $scope.canvasSize.width,
                }, select, '.bottom-panel ');
                axes.y.updateLabelAndTicks({
                    width: $scope.rightPanelWidth,
                    height: $scope.canvasSize.height,
                }, select, '.right-panel ');
                axes.bottomY.updateLabelAndTicks({
                    height: $scope.bottomPanelHeight,
                    width: $scope.canvasSize.width,
                    isPlaying: $scope.isPlaying,
                    scaleFunction: scaleFunction,
                }, select, '.bottom-panel ');
                axes.rightX.updateLabelAndTicks({
                    width: $scope.rightPanelWidth - $scope.margin.right,
                    height: $scope.canvasSize.height,
                    scaleFunction: scaleFunction,
                }, select, '.right-panel ');

                if (layoutService.plotAxis.allowUpdates) {
                    axes.x.grid.ticks(axes.x.tickCount);
                    axes.y.grid.ticks(axes.y.tickCount);
                    axes.x.grid.tickSize(- $scope.canvasSize.height - $scope.bottomPanelHeight + $scope.margin.bottom); // tickLine == gridline
                    axes.y.grid.tickSize(- $scope.canvasSize.width - $scope.rightPanelWidth + $scope.margin.right); // tickLine == gridline
                }
                resetZoom();
                select('.mouse-rect-xy').call(xyZoom);
                select('.mouse-rect-x').call(axes.x.zoom);
                select('.mouse-rect-y').call(axes.y.zoom);
                select('.right-panel .x.axis').call(axes.rightX.svgAxis);
                select('.x.axis.grid').call(axes.x.grid);
                select('.y.axis.grid').call(axes.y.grid);
                focusPointService.refreshFocusPoint($scope.focusPointX, $scope);
                focusPointService.refreshFocusPoint($scope.focusPointY, $scope);
                prevDomain = [
                    axes.x.scale.domain(),
                    axes.y.scale.domain(),
                ];
                if (appState.deepEquals(fullDomain, prevDomain)) {
                    adjustZoomToCenter(axes.x.scale);
                    adjustZoomToCenter(axes.y.scale);
                }
            }

            function resetZoom() {
                xyZoom = axes.x.createZoom($scope).y(axes.y.scale);
                axes.x.zoom = axes.x.createZoom($scope);
                axes.y.zoom = axes.y.createZoom($scope);
            }

            function restoreDomain(scale, oldValue) {
                var d = scale.domain();
                d[0] = oldValue[0];
                d[1] = oldValue[1];
            }

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            function sumRegion(isWidth, bottom, top, left, right) {
                var points = [];
                var max = isWidth ? right : top;
                for (var i = 0; i <= max; i++) {
                    points[i] = 0;
                }
                for (i = bottom; i <= top; i++) {
                    for (var j = left; j <= right; j++) {
                        var index = isWidth ? j : i;
                        points[index] += heatmap[axes.y.values.length - 1 - i][j];
                    }
                }
                return points;
            }

            $scope.clearData = function() {
                $scope.dataCleared = true;
                fullDomain = null;
                lineOuts = {};
            };

            $scope.destroy = function() {
                xyZoom.on('zoom', null);
                axes.x.zoom.on('zoom', null);
                axes.y.zoom.on('zoom', null);
            };

            $scope.formatFocusPointData = function(fp) {
                return focusPointService.formatFocusPointData(
                    fp,
                    fp.config.xAxis.label,
                    select('.z-axis-label').text()
                );
            };

            $scope.hideFocusPointText = function() {
                select('.focus-text').text('');
                select('.focus-text-close').style('display', 'none');
                select('.sub-title').style('display', 'block');
            };

            $scope.hideFocusPoints = function() {
                focusPointService.hideFocusPoint($scope, true);
                $scope.focusPointX.unset();
                $scope.focusPointY.unset();
            };

            $scope.init = function() {
                select('svg.sr-plot').attr('height', plotting.initialHeight($scope));
                axes.x.init();
                axes.y.init();
                axes.bottomY.init();
                axes.rightX.init();
                axes.x.indexScale = d3.scale.linear();
                axes.y.indexScale = d3.scale.linear();
                axes.x.grid = axes.x.createAxis();
                axes.y.grid = axes.y.createAxis('left');
                resetZoom();
                canvas = select('canvas').node();
                ctx = canvas.getContext('2d', { willReadFrequently: true });
                cacheCanvas = document.createElement('canvas');
                axes.x.cutLine = d3.svg.line()
                    .x(function(d) {return axes.x.scale(d[0]);})
                    .y(function(d) {
                        return axes.bottomY.scale(scaleFunction ? scaleFunction(d[1]) : d[1]);
                    });
                axes.y.cutLine = d3.svg.line()
                    .y(function(d) { return axes.y.scale(d[0]);})
                    .x(function(d) {
                        return axes.rightX.scale(scaleFunction ? scaleFunction(d[1]) : d[1]);
                    });

                $scope.focusPointX = focusPointService.setupFocusPoint(axes.x, axes.bottomY, false, $scope.modelName + '-fp-X');
                $scope.focusPointY = focusPointService.setupFocusPoint(axes.y, axes.rightX, true, $scope.modelName + '-fp-Y');
                select('.focus-text-close')
                    .on('click', $scope.hideFocusPoints);
           };

            $scope.load = function(json) {
                prevDomain = null;
                $scope.dataCleared = false;
                aspectRatio = plotting.getAspectRatio($scope.modelName, json);
                $scope.width = json.z_matrix[0].length;
                $scope.height = json.z_matrix.length;
                heatmap = plotting.safeHeatmap(appState.clone(json.z_matrix).reverse());
                var newFullDomain = [
                    [json.x_range[0], json.x_range[1]],
                    [json.y_range[0], json.y_range[1]],
                ];
                if ((axes.y.values && axes.y.values.length != heatmap.length)
                    || ! appState.deepEquals(fullDomain, newFullDomain)) {
                    fullDomain = newFullDomain;
                    lineOuts = {};
                    axes.x.values = plotting.linearlySpacedArray(fullDomain[0][0], fullDomain[0][1], heatmap[0].length);
                    axes.y.values = plotting.linearlySpacedArray(fullDomain[1][0], fullDomain[1][1], heatmap.length);
                    axes.x.scale.domain(fullDomain[0]);
                    axes.x.indexScale.domain(fullDomain[0]);
                    axes.y.scale.domain(fullDomain[1]);
                    axes.y.indexScale.domain(fullDomain[1]);
                    adjustZoomToCenter(axes.x.scale);
                    adjustZoomToCenter(axes.y.scale);
                }
                var xmax = axes.x.values.length - 1;
                var ymax = axes.y.values.length - 1;
                axes.x.indexScale.range([0, xmax]);
                axes.y.indexScale.range([0, ymax]);
                cacheCanvas.width = axes.x.values.length;
                cacheCanvas.height = axes.y.values.length;
                imageData = ctx.getImageData(0, 0, cacheCanvas.width, cacheCanvas.height);
                select('.main-title').text(json.title);
                select('.sub-title').text(json.subtitle);
                axes.x.updateLabel(json.x_label, select);
                axes.y.updateLabel(json.y_label, select);
                select('.z-axis-label').text(json.z_label);
                if (json.z_footer) {
                    select('.z-axis-footer').text(json.z_footer);
                }
                var zmin = plotting.min2d(heatmap);
                var zmax = plotting.max2d(heatmap);
                if ('z_range' in json) { zmin = json.z_range[0]; zmax = json.z_range[1]; }
                scaleFunction = plotting.scaleFunction($scope.modelName);
                if (zmin > 0 && SIREPO.PLOTTING_YMIN_ZERO && ! scaleFunction) {
                    zmin = 0;
                }
                var domain = plotting.ensureDomain([zmin, zmax], scaleFunction);
                axes.bottomY.scale.domain(domain).nice();
                axes.rightX.scale.domain([domain[1], domain[0]]).nice();
                plotting.initImage({ min: zmin, max: zmax }, heatmap, cacheCanvas, imageData, $scope.modelName, json.threshold);
                $scope.resize();
            };

            $scope.resize = function() {
                if (select().empty()) {
                    return;
                }
                //TODO(pjm): double refresh required to get correct axis in some cases
                // see https://github.com/radiasoft/sirepo/issues/7297
                refresh();
                refresh();
            };

            $scope.showFocusPointText = function(focusPoint) {
                select('.focus-text-close').style('display', 'block');

                var focusText = select('.focus-text');
                var fmtTxt = focusPointService.formatFocusPointData(focusPoint);
                var xyfText = fmtTxt.xText + ', ' + fmtTxt.yText;
                if (fmtTxt.fwhmText) {
                    xyfText = xyfText + ', ' + fmtTxt.fwhmText;
                }
                if (focusPoint == $scope.focusPointX) {
                    xyfText = xyfText + ' ↓';
                }
                if (focusPoint == $scope.focusPointY) {
                    xyfText = xyfText + ' →';
                }
                select('.sub-title').style('display', 'none');
                focusText.text(xyfText);
                layoutFocusPointText();
            };

            $scope.showPlotSize = () => {
                return appState.models[$scope.modelName].showPlotSize == '1';
            };

            $scope.$on(SIREPO.PLOTTING_CSV_EVENT, function(evt, axisName) {
                var title = plotting.plotTitle($scope.element);
                var heading, points;
                if (axisName == 'x' || axisName == 'y') {
                    var axisText = axes[axisName].label + ' ' + layoutService.formatUnits(axes[axisName].units);
                    heading = [axisText, select('.z-axis-label').text()];
                    title += ' - ' + axisText;
                    var keys = Object.keys(lineOuts[axisName]);
                    points = lineOuts[axisName][keys[0]][0];
                }
                else {
                    // full plot to csv
                    heading = [
                        title + ': ' + select('.z-axis-label').text()
                            + ' vs ' + axes.x.label + ' [' + axes.x.units
                            + '] and ' + axes.y.label + ' [' + axes.y.units
                            + ']. The ' + axes.x.label + 's are given in the first column, '
                            +  axes.y.label + 's in the first row.'
                    ];
                    axes.y.values.forEach(function(v) {
                        heading.push('' + v.toExponential(9));
                    });
                    var width = axes.x.values.length;
                    var height = axes.y.values.length;
                    points = [];
                    axes.x.values.forEach(function(v, idx) {
                        var row = [v];
                        for (var i = 0; i < height; i++) {
                            row.push(heatmap[height - i - 1][idx]);
                        }
                        points.push(row);
                    });
                }
                plotting.exportCSV(title, heading, points);
            });
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('heatmap', function(appState, layoutService, plotting, utilities) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            isClientOnly: '@',
        },
        templateUrl: '/static/html/heatplot.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            // will be set to the correct size in resize()
            $scope.canvasSize = {
                width: 0,
                height: 0,
            };
            $scope.dataCleared = true;
            $scope.margin = {top: 50, left: 70, right: 100, bottom: 50};

            const axes = {
                x: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh),
                y: layoutService.plotAxis($scope.margin, 'y', 'left', refresh),
            };
            const overlayDataClass = 'sr-overlay-data';

            let aspectRatio = 1.0;
            let amrLine, canvas, ctx, fullDomain, heatmap, mouseClickPoint, mouseMovePoint, pointer, zoom;
            let globalMin = 0.0;
            let globalMax = 1.0;
            let cacheCanvas, imageData;
            let colorbar, hideColorBar;
            const overlaySelector = 'svg.sr-plot g.sr-overlay-data-group';
            const cellHighlightClass = 'sr-cell-highlight';
            let selectedCell;
            let overlayData = null;

            function binnedCoords(point) {
                const [i, j] = heatmapIndices(point);
                const [bx, by] = coordBinSize();
                const [xd, yd] = [fullDomain.x, fullDomain.y];
                return [
                    xd[0] + (i * bx + bx / 2) * (xd[0] > xd[1] ? -1 : 1),
                    yd[0] + (j * by + by / 2) * (yd[0] > yd[1] ? -1 : 1),
                ];
            }

            function coordBinSize() {
                const n = SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL ? 0 : 1;
                return [
                    Math.abs((fullDomain.x[1] - fullDomain.x[0])) / (heatmap[0].length - n),
                    Math.abs((fullDomain.y[1] - fullDomain.y[0])) / (heatmap.length - n),
                ];
            }

            function colorbarSize() {
                var tickFormat = colorbar.tickFormat();
                if (! tickFormat) {
                    return 0;
                }
                var maxLength = colorbar.scale().ticks().reduce(function(size, v) {
                    return Math.max(size, tickFormat(v).length);
                }, 0);
                var textSize = Math.max(25, maxLength * plotting.tickFontSize(select('.sr-plot .axis text')));
                var res = textSize + colorbar.thickness() + colorbar.margin().left;
                colorbar.margin().right = res;
                return res;
            }

            function drawOverlay() {
                const ns = 'http://www.w3.org/2000/svg';
                const overlay = select(overlaySelector);
                overlay.selectAll(`rect.${cellHighlightClass}`).remove();
                if ($scope.enableSelection && selectedCell) {
                    const c = overlay
                        .selectAll(`rect.${cellHighlightClass}`)
                        .data([selectedCell]);
                    c.exit().remove();
                    c.enter()
                        .append((d) => document.createElementNS(ns, 'rect'))
                        .attr('class', cellHighlightClass);
                    c.call(updateCellHighlight);
                }
                if (! overlayData) {
                    return;
                }
                let ds = overlay
                    .selectAll(`path.${overlayDataClass}`)
                    .data(overlayData);
                ds.exit().remove();
                ds.enter()
                    .append((d) => document.createElementNS(ns, 'path'))
                    .append((d) => document.createElementNS(ns, 'title'));
                ds.call(updateOverlay);
            }

            function heatmapIndices(point) {
                const x = axes.x.scale.invert(point[0] - 1);
                const y = axes.y.scale.invert(point[1] - 1);
                const n = SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL ? 0 : 1;
                const dx = Math.abs((fullDomain.x[1] - fullDomain.x[0])) / (heatmap[0].length - n);
                const dy = Math.abs((fullDomain.y[1] - fullDomain.y[0])) / (heatmap.length - n);
                const i = Math.abs((x - fullDomain.x[0]) / dx);
                const j = Math.abs((y - fullDomain.y[0]) / dy);
                return [
                    n ? Math.round(i) : Math.max(0, Math.floor(i)),
                    n ? Math.round(j) : Math.max(0, Math.floor(j)),
                ];
            }

            function mouseClick() {
                if (! mouseClickPoint || ! d3.event.altKey || ! $scope.enableSelection) {
                    return;
                }
                const newSelected = binnedCoords(mouseClickPoint);
                selectedCell = appState.deepEquals(newSelected, selectedCell)
                             ? null : newSelected;
                drawOverlay();
                $scope.broadcastEvent({
                    name: SIREPO.PLOTTING.HeatmapSelectCellEvent,
                    cell: selectedCell,
                });
            }

            const mouseMove = utilities.debounce(() => {
                /*jshint validthis: true*/
                if (! heatmap || ! heatmap[0].length || ! mouseMovePoint) {
                    return;
                }
                const [i, j] = heatmapIndices(mouseMovePoint);
                try {
                    pointer.pointTo(heatmap[heatmap.length - 1 - j][i]);
                    if ($scope.enableSelection) {
                        updateReadout(mouseMovePoint, i, j);
                    }
                }
                catch (err) {
                    // ignore range errors due to mouse move after heatmap is reset
                }
            }, 100);

            function refresh() {
                if (layoutService.plotAxis.allowUpdates && ! $scope.isPlaying) {
                    var elementWidth = parseInt(select().style('width'));
                    if (! heatmap || isNaN(elementWidth)) {
                        return;
                    }
                    [$scope.canvasSize.height, $scope.canvasSize.width] = plotting.constrainFullscreenSize($scope, elementWidth, aspectRatio);
                    axes.x.scale.range([0, $scope.canvasSize.width]);
                    axes.y.scale.range([$scope.canvasSize.height, 0]);
                }
                if (plotting.trimDomain(axes.x.scale, fullDomain.x)
                    + plotting.trimDomain(axes.y.scale, fullDomain.y)) {
                    select('.mouse-rect').attr('class', 'mouse-rect mouse-zoom');
                }
                else {
                    select('.mouse-rect').attr('class', 'mouse-rect mouse-move');
                }
                plotting.drawImage(axes.x.scale, axes.y.scale, $scope.canvasSize.width, $scope.canvasSize.height, axes.x.values, axes.y.values, canvas, cacheCanvas, ! SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL);
                select('.line-amr-grid').attr('d', amrLine);
                resetZoom();
                select('.mouse-rect').call(zoom);
                $scope.canvasSize.isPlaying = $scope.isPlaying;
                $.each(axes, function(dim, axis) {
                    axis.updateLabelAndTicks($scope.canvasSize, select);
                });
                if (showColorBar()) {
                    if (layoutService.plotAxis.allowUpdates) {
                        colorbar.barlength($scope.canvasSize.height).origin([$scope.canvasSize.width + $scope.margin.right, 0]);
                        // must remove the element to reset the margins
                        select('svg.colorbar').remove();
                        pointer = select('.colorbar').call(colorbar);
                        $scope.margin.right = colorbarSize();
                    }
                }
                else {
                    select('svg.colorbar').remove();
                    $scope.margin.right = 20;
                }

                drawOverlay();
            }

            function resetZoom() {
                zoom = axes.x.createZoom($scope).y(axes.y.scale);
            }

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            function setColorScale(threshold) {
                var plotMin = globalMin != null ? globalMin : plotting.min2d(heatmap);
                var plotMax = globalMax != null ? globalMax : plotting.max2d(heatmap);
                if (plotMin == plotMax) {
                    if (plotMin <= 0) {
                        plotMax = plotMax ? 0 : 1;
                    }
                    else if (plotMin > 0) {
                        plotMin = 0;
                    }
                }
                var colorScale = plotting.initImage(
                    {
                        min: plotMin,
                        max: plotMax,
                    },
                    heatmap,
                    cacheCanvas,
                    imageData,
                    $scope.modelName,
                    threshold,
                );
                colorbar.scale(colorScale);
            }

            function showColorBar() {
                if (appState.isLoaded() && ! hideColorBar) {
                    return appState.models[$scope.modelName].colorMap != 'contrast';
                }
                return false;
            }

            function updateCellHighlight(selection) {
                const fp = SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL;
                const sz = plotting.pixelSize(
                    axes.x.scale,
                    axes.y.scale,
                    $scope.canvasSize.width,
                    $scope.canvasSize.height,
                    axes.x.values,
                    axes.y.values
                );
                selection
                    .attr('x', (d) => Math.round(axes.x.scale(d[0]) - (fp ? sz.x / 2 : 0)))
                    .attr('y', (d) => Math.round(axes.y.scale(d[1]) - (fp ? sz.y / 2 : 0)))
                    .attr('width', (d) => sz.x)
                    .attr('height', (d) =>  sz.y);
            }

            function updateOverlay(selection) {
                selection
                    .attr('class', overlayDataClass)
                    .attr('id', d => {
                        return `${overlayDataClass}-${d.name}`;
                    })
                    .attr('clip-path', 'url(#sr-plot-window)')
                    .attr('stroke', d => d.color)
                    .attr('stroke-dasharray', d => d.dashes)
                    .attr('stroke-width', 2.0)
                    .attr('fill', 'none')
                    .attr('marker-end', d => `url(#${d.marker})`)
                    .attr('d', d => {
                        // we don't use the SVGPath directly, but it is a convenient way to build
                        // a path string
                        return new SIREPO.DOM.SVGPath(
                            null,
                            d.data.map(c => [axes.x.scale(c[0]), axes.y.scale(c[1])])
                        ).pathString(d.doClose);
                    })
                    .select('title').text(d => d.name);
            }

            function updateReadout(point, i, j) {
                let text;
                if (point) {
                    const c = binnedCoords(point).map(v => SIREPO.UTILS.roundToPlaces(v, 4));
                    const labels = [axes.x.label, axes.y.label];
                    const val = SIREPO.UTILS.roundToPlaces(heatmap[heatmap.length - 1 - j][i], 4);
                    text = `(${axes.x.label}: ${c[0]}, ${axes.y.label}: ${c[1]}): ${val}`;
                }
                else {
                    text = '';
                }
                select().selectAll('text.sr-heatmap-readout').text(text);
            }

            $scope.clearData = function() {
                $scope.dataCleared = true;
                $scope.prevFrameIndex = SIREPO.nonDataFileFrame;
            };

            $scope.destroy = function() {
                select('.mouse-rect').on('mousemove', null);
                select('.mouse-rect').on('click', null);
                zoom.on('zoom', null);
            };

            $scope.init = function() {
                select('svg.sr-plot').attr('height', plotting.initialHeight($scope));
                $.each(axes, function(dim, axis) {
                    axis.init();
                });
                resetZoom();
                canvas = select('canvas').node();
                select('.mouse-rect')
                    .on('mousemove', function() {
                        // mouseMove is debounced, so save the point before calling
                        mouseMovePoint = d3.mouse(this);
                        mouseMove();
                    })
                    .on('click', function() {
                        mouseClickPoint = d3.mouse(this);
                        mouseClick();
                    })
                    .on('mouseout', () => {
                        mouseMovePoint = null;
                        updateReadout();
                    });
                ctx = canvas.getContext('2d', { willReadFrequently: true });
                cacheCanvas = document.createElement('canvas');
                colorbar = Colorbar()
                    .margin({top: 10, right: 100, bottom: 20, left: 10})
                    .thickness(30)
                    .orient('vertical');
                amrLine = d3.svg.line()
                    .defined(function(d) { return d !== null; })
                    .x(function(d) {
                        return axes.x.scale(d[0]);
                    })
                    .y(function(d) {
                        return axes.y.scale(d[1]);
                    });
            };

            $scope.load = function(json) {
                if (! json.z_matrix) {
                    //TODO(pjm): plot may be loaded with { state: 'canceled' }?
                    return;
                }
                overlayData = json.overlayData;
                selectedCell = json.selectedCoords;
                $scope.dataCleared = false;
                $scope.enableSelection = json.enableSelection;
                aspectRatio = plotting.getAspectRatio($scope.modelName, json);
                heatmap = plotting.safeHeatmap(appState.clone(json.z_matrix).reverse());
                globalMin = json.global_min;
                globalMax = json.global_max;
                select('.main-title').text(json.title);
                select('.sub-title').text(json.subtitle);
                const newFullDomain = {};
                $.each(axes, function(dim, axis) {
                    newFullDomain[dim] = json[dim + '_range'].slice(0, 2);
                    axis.values = plotting.linearlySpacedArray(...json[dim + '_range']);
                    axis.values.srDomain = newFullDomain[dim];
                    axis.updateLabel(json[dim + '_label'], select);
                    if (! appState.deepEquals(fullDomain && fullDomain[dim], newFullDomain[dim])) {
                        axis.scale.domain(newFullDomain[dim]);
                    }
                });
                fullDomain = newFullDomain;
                cacheCanvas.width = axes.x.values.length;
                cacheCanvas.height = axes.y.values.length;
                imageData = ctx.getImageData(0, 0, cacheCanvas.width, cacheCanvas.height);
                select('.z-axis-label').text(json.z_label);
                select('.frequency-label').text(json.frequency_title);
                setColorScale(json.threshold);
                hideColorBar = json.hideColorBar || false;

                var amrLines = [];
                if (json.amr_grid) {
                    for (var i = 0; i < json.amr_grid.length; i++) {
                        var p = json.amr_grid[i];
                        amrLines.push([p[0][0], p[1][0]]);
                        amrLines.push([p[0][1], p[1][0]]);
                        amrLines.push([p[0][1], p[1][1]]);
                        amrLines.push(null);
                    }
                }
                select('.line-amr-grid').datum(amrLines);
                $scope.resize();
            };

            $scope.resize = function() {
                if (select().empty()) {
                    return;
                }
                //TODO(pjm): double refresh required to get correct axis in some cases
                // see https://github.com/radiasoft/sirepo/issues/7297
                refresh();
                refresh();
            };

            $scope.$on(`${$scope.modelName}.reload`, (e, d) => {
                $scope.load(d);
            });

            $scope.$on(`${$scope.modelName}.updateSelection`, (e, d) => {
                selectedCell = d;
                drawOverlay();
            });

        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});


SIREPO.app.directive('colorCircle', function() {
    return {
        resize: 'A',
        scope: {
            plot: '<colorCircle',
        },
        template: `
              <svg width="30" height="10">
                <line x1="0" y1="5" x2="30" y2="5"
                  data-ng-attr-stroke-width="{{ plot.strokeWidth }}"
                  data-ng-attr-opacity="{{ plot.opacity || 1.0 }}"
                  data-ng-attr-stroke="{{ plot.color }}"
                  data-ng-attr-stroke-dasharray="{{ plot.dashes }}" />
              </svg>
        `,
    };
});

SIREPO.app.directive('plotLegend', function(mathRendering) {
    return {
        restrict: 'A',
        scope: {
            plots: '<',
            togglePlot: '&',
            dynamicYLabel: '<',
        },
        template: `
            <div data-ng-if="plots.length > 1">
              <div data-ng-repeat="p in plots" style="margin-left: 1em">
                <div data-ng-click="click($index)" style="cursor: pointer; display: inline">
                  <a href data-ng-style="{ opacity: opacity(p) }"><span class="glyphicon" data-ng-class="{'glyphicon-check': p._isVisible, 'glyphicon-unchecked': ! p._isVisible}"> </span></a>
                  <div style="display:inline" data-color-circle="p"></div>
                  <span data-text-with-math="label(p)" data-is-dynamic="1"></span>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
            function hasSameUnits(units) {
                for (const p of $scope.plots) {
                    if (p._units !== units) {
                        return false;
                    }
                }
                return true;
            }

            $scope.click = (index) => {
                $scope.togglePlot({ pIndex: index });
            };

            $scope.label = (p) => {
                if ($scope.dynamicYLabel && hasSameUnits(p._units)) {
                    return p._label;
                }
                return p.label;
            };

            $scope.opacity = (p) => {
                if (p._isVisible) {
                    for (const p2 of $scope.plots) {
                        if (p.label !== p2.label && p2._isVisible) {
                            return 1.0;
                        }
                    }
                    return 0.4;
                }
                return 1.0;
            };
        },
    };
});

SIREPO.app.directive('parameterPlot', function(appState, focusPointService, layoutService, mathRendering, plotting, plot2dService, utilities) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/plot2d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope, $element) {
            const yMargin = 23;
            let scaleFunction, y2_axis;

            $scope.dynamicYLabel = false;
            $scope.focusPoints = [];
            $scope.focusStrategy = 'closest';
            $scope.plots = null;
            $scope.reportId = SIREPO.UTILS.randomId();

            function build2dPointsForPlot(plotIndex) {
                var pts = [];
                var xPoints = $scope.axes.x.points;
                for (var ptIndex = 0; ptIndex < xPoints.length; ++ptIndex) {
                    pts.push([
                        xPoints[ptIndex],
                        $scope.plots[plotIndex].points[ptIndex]
                    ]);
                }
                return pts;
            }

            function canToggle(pIndex) {
                for (const [idx, p] of $scope.plots.entries()) {
                    if (idx != pIndex && p._isVisible) {
                        return true;
                    }
                }
                return false;
            }

            function getPlotLabels() {
                return $scope.plots.map(plot => plot.label);
            }

            function isFixedDomain() {
                var m = appState.models[$scope.modelName];
                return m && (m.plotRangeType == 'fixed' || m.plotRangeType == 'fit');
            }

            function isPlotVisible(pIndex) {
                return $scope.plots[pIndex]._isVisible;
            }

            function normalizeInput(json) {
                $scope.aspectRatio = plotting.getAspectRatio($scope.modelName, json, 4.0 / 7);
                $scope.dynamicYLabel = json.dynamicYLabel || false;
                // data may contain 2 plots (y1, y2) or multiple plots (plots)
                json.plots = json.plots || [
                    {
                        points: json.points[0],
                        label: json.y1_title,
                        color: '#1f77b4',
                    },
                    {
                        points: json.points[1],
                        label: json.y2_title,
                        color: '#ff7f0e',
                    },
                ];
                if (json.plots[0].x_points) {
                    $scope.noOverlay = true;
                }
                if (json.plots.length == 1 && ! json.y_label) {
                    json.y_label = json.plots[0].label;
                }
                $scope.axes.x.points = json.x_points
                    || plotting.linearlySpacedArray(json.x_range[0], json.x_range[1], json.x_range[2] || json.points.length);
                if (angular.isArray($scope.axes.x.points[0])) {
                    throw new Error('expecting a single array for x values: ' + $scope.modelName);
                }
                //TODO(pjm): onRefresh indicates a beamline overlay, needs improvement
                if ($scope.onRefresh && json.x_range[1] > 0) {
                    // beamline overlay always starts at position 0
                    json.x_range[0] = 0;
                }
                $scope.margin.top = json.title
                    ? 50
                    : $scope.onRefresh
                        ? 65
                        : 20;
                let hasY2Axis = false;
                json.plots.forEach(function(plot, ip) {
                    const lu = layoutService.parseLabelAndUnits(plot.label);
                    plot._units = lu.units;
                    plot._label = lu.label;
                    plot._yaxis = appState.applicationState()[$scope.modelName][plot.dim + 'Position'] || 'left';
                    if (plot._yaxis == 'right') {
                        hasY2Axis = true;
                        plot.dashes = '5 3';
                    }
                });
                if (hasY2Axis) {
                    const ydoms = calcYDomains(json.plots);
                    json.y_range = ydoms[0];
                    json.y2_range = ydoms[1];
                    $scope.axes.y2 = y2_axis;
                    $($element).find('.y2.axis').show();
                    $($element).find('.y2-axis-label').show();
                }
                else {
                    delete json.y2_range;
                    if ($scope.axes.y2) {
                        delete $scope.axes.y2;
                        $($element).find('.y2.axis').hide();
                        $($element).find('.y2-axis-label').hide();
                        $scope.margin.right = yMargin;
                    }
                }
            }

            function plotPath(pIndex) {
                var sel = '.plot-viewport .param-plot[data-sr-index=\'' + pIndex + '\']';
                return d3.selectAll(selectAll(sel)[0]);
            }

            function selectAll(selector) {
                var e = d3.select($scope.element);
                return selector ? e.selectAll(selector) : e;
            }

            function setPlotVisible(pIndex, isVisible) {
                // disable last toggle - meaningless to show no plots
                if (! isVisible && ! canToggle(pIndex)) {
                    return;
                }
                const p = $scope.plots[pIndex];
                p._isVisible = isVisible;
                plotPath(pIndex).style('opacity', isVisible ? (p.opacity || 1.0) : 0.0);
                $scope.recalculateYDomain();
                $scope.broadcastEvent({
                    name: 'setInfoVisible',
                    isVisible: isVisible,
                    focusPoint: $scope.focusPoints[pIndex],
                    index: pIndex,
                });
            }

            function setupPlots(json) {
                const viewport = $scope.select('.plot-viewport');
                viewport.selectAll('.line').remove();
                viewport.selectAll('g.param-plot').remove();
                json.plots.forEach(function(plot, ip) {
                    plot.strokeWidth = plot.strokeWidth || 2.0;
                    if (plot.style === 'scatter') {
                        let clusterInfo;
                        let circleRadius = plot.circleRadius || 2;
                        if (json.clusters) {
                            clusterInfo = json.clusters;
                            $scope.clusterInfo = clusterInfo;
                            clusterInfo.scale = clusterInfo.count > 10
                                ? d3.scale.category20()
                                : d3.scale.category10();
                            circleRadius = plot.circleRadius || 4;
                        }
                        viewport.append('g')
                        .attr('class', 'param-plot')
                        .attr('data-sr-index', ip)
                        .selectAll('.scatter-point')
                            .data(plot.points)
                            .enter()
                            .append('circle')
                            .attr('r', circleRadius)
                            .style('fill', function (d, j) {
                                return clusterInfo ? clusterInfo.scale(clusterInfo.group[j]) : plot.color;
                            })
                            .attr('class', 'scatter-point line-color');
                    }
                    else {
                        const p = viewport.append('path')
                            .attr('class', 'param-plot line line-color')
                            .attr('data-sr-index', ip)
                            .style('stroke', plot.color)
                            .style('stroke-width', plot.strokeWidth)
                            .datum(plot.points);
                        if (plot.dashes) {
                            p.style('stroke-dasharray', (plot.dashes));
                        }
                    }
                    // must create extra focus points here since we don't know how many to make
                    const name = $scope.modelName + '-fp-' + ip;
                    if (! $scope.focusPoints[ip]) {
                        $scope.focusPoints[ip] = focusPointService.setupFocusPoint(
                            $scope.axes.x,
                            // will be reset below
                            $scope.axes.y,
                            false,
                            name,
                        );
                    }
                    $scope.focusPoints[ip].config.yAxis = $scope.axes[plot._yaxis === 'left' ? 'y' : 'y2'];

                });
                return json.plots;
            }

            function togglePlot(pIndex) {
                setPlotVisible(pIndex, ! isPlotVisible(pIndex));
                updateYLabels();
                $scope.resize();
            }

            function updateAxes(json) {
                const xdom = [json.x_range[0], json.x_range[1]];
                if (! appState.deepEquals(xdom, $scope.axes.x.domain)) {
                    $scope.axes.x.domain = xdom;
                    $scope.axes.x.scale.domain(xdom);
                }

                function setDomain(dim, range) {
                    if (range) {
                        $scope.axes[dim].domain = plotting.ensureDomain([range[0], range[1]], plotting.scaleFunction($scope.modelName));
                        $scope.axes[dim].scale.domain($scope.axes[dim].domain).nice();
                    }
                }
                setDomain('y', json.y_range);
                setDomain('y2', json.y2_range);
            }

            function updateYLabels() {
                // combine labels from all selected plots, use common units if possible
                if (! $scope.dynamicYLabel) {
                    return;
                }
                updateYLabel($scope.axes.y, 'left');
                updateYLabel($scope.axes.y2, 'right');
            }

            function updateYLabel(yaxis, orientation) {
                if (! yaxis) {
                    return;
                }
                function addUnits(labels, units) {
                    let isFixedUnits = false;
                    let hasCommonUnits = true;
                    labels.forEach((label, idx) => {
                        let lu = layoutService.parseLabelAndUnits(label);
                        if (! lu.units) {
                            lu = layoutService.parseLabelAndUnits(label, true);
                            isFixedUnits = true;
                        }
                        labels[idx] = lu.label;
                        units.push(lu.units);
                        if (units[0] != units[idx]) {
                            hasCommonUnits = false;
                        }
                    });
                    return hasCommonUnits
                        ? layoutService.formatUnits(units[0], isFixedUnits)
                        : '';
                }
                const maxLabelSize = 45;
                const labels = getPlotLabels().filter((l, idx) => {
                    return isPlotVisible(idx) && $scope.plots[idx]._yaxis === orientation;
                });
                if (! labels.length) {
                    return;
                }
                const units = [];
                const yUnits = addUnits(labels, units);
                let yLabel = '';
                labels.forEach((l, idx) => {
                    if (yLabel) {
                        yLabel += ', ';
                    }
                    yLabel += l;
                    if (! yUnits && units[idx]) {
                        yLabel += ' ' + layoutService.formatUnits(units[idx], true);
                    }
                });
                // strip out any KaTeX formatting before computing label length
                if (yLabel.replace(/\$|\{|\s+/g, '').length > maxLabelSize) {
                    yLabel = yUnits;
                }
                else if (yUnits) {
                    yLabel += ' ' + yUnits;
                }
                yaxis.updateLabel(yLabel, $scope.select);
            }

            $scope.formatFocusPointData = function(fp) {
                const plotLabels = getPlotLabels();
                var yLabel = plotLabels[$scope.focusPoints.indexOf(fp)];
                var lu = {};
                if (yLabel) {
                    lu = layoutService.parseLabelAndUnits(yLabel);
                    yLabel = lu.label;
                }
                fp.config.yLabel = yLabel;
                return focusPointService.formatFocusPointData(fp, fp.config.xAxis.label, yLabel, null, lu.units);
            };

            // interface used by parameterWithLattice
            $scope.getXAxis = function() {
                return $scope.axes.x;
            };

            $scope.init = function() {
                plot2dService.init2dPlot($scope, {
                    margin: {top: 50, right: yMargin, bottom: 20, left: yMargin}
                });
                y2_axis = $scope.axes.y2;
                delete $scope.axes.y2;
                // override graphLine to work with multiple point sets
                $scope.plotGraphLine = function(plotIndex) {
                    const p = ($scope.plots || [])[plotIndex] || {};
                    const xPoints = p.x_points || $scope.axes.x.points;
                    const yaxis = p._yaxis == 'right' ? $scope.axes.y2 : $scope.axes.y;
                    return d3.svg.line()
                        .x(function(d, i) {
                            return $scope.axes.x.scale(xPoints[i]);
                        })
                        .y(function(d) {
                            return yaxis.scale(scaleFunction ? scaleFunction(d) : d);
                        });
                };
                $scope.graphLine = d3.svg.line()
                    .x(function(d, i) {
                        return $scope.axes.x.scale($scope.axes.x.points[i]);
                    })
                    .y(function(d) {
                        return $scope.axes.y.scale(scaleFunction ? scaleFunction(d) : d);
                    });
            };

            $scope.load = function(json) {
                if (! json.plots && ! json.points) {
                    //TODO(pjm): plot may be loaded with { state: 'canceled' }?
                    return;
                }
                normalizeInput(json);
                updateAxes(json);
                const oldPlots = $scope.plots;
                $scope.plots = setupPlots(json);
                $scope.updatePlot(json);
                $scope.plots.forEach((plot, ip) => setPlotVisible(ip, true));
                $scope.plots.forEach(function(plot, ip) {
                    if (oldPlots && oldPlots[ip] && oldPlots[ip].label === plot.label && ! oldPlots[ip]._isVisible) {
                        setPlotVisible(ip, false);
                    }
                });
                updateYLabels();
                if (! $scope.noOverlay) {
                    for (var fpIndex = 0; fpIndex < $scope.focusPoints.length; ++fpIndex) {
                        if (fpIndex < $scope.plots.length) {
                            $scope.focusPoints[fpIndex].config.color = $scope.plots[fpIndex].color;
                            focusPointService.loadFocusPoint($scope.focusPoints[fpIndex], build2dPointsForPlot(fpIndex), false, $scope);
                        }
                        else {
                            focusPointService.loadFocusPoint($scope.focusPoints[fpIndex], [], false, $scope);
                        }
                    }
                }
                $scope.resize();
            };

            function calcYDomains(plots, xdom) {
                // calculate left and right y axis domains for plots (assumed all visible)
                const ydom = [null, null];
                const xPoints = $scope.axes.x.points;

                for (let i = 0; i < xPoints.length; i++) {
                    const x = xPoints[i];
                    if (xdom && (x > xdom[1] || x < xdom[0])) {
                        continue;
                    }
                    for (const p of plots) {
                        const y = p.points[i];
                        const ia = p._yaxis == 'left' ? 0 : 1;
                        if (ydom[ia]) {
                            if (y < ydom[ia][0]) {
                                ydom[ia][0] = y;
                            }
                            else if (y > ydom[ia][1]) {
                                ydom[ia][1] = y;
                            }
                        }
                        else {
                            ydom[ia] = [y, y];
                        }
                    }
                }
                ['left', 'right'].forEach((v, i) => {
                    if (ydom[i]) {
                        const limit = appState.applicationState()[$scope.modelName][`${v}Limit`];
                        if (limit && ydom[i][1] > limit) {
                            ydom[i][1] = limit;
                            if (ydom[i][0] > ydom[i][1]) {
                                ydom[i][0] = ydom[i][1];
                            }
                        }
                    }
                });

                return ydom;
            }

            $scope.recalculateYDomain = function() {
                if (isFixedDomain()) {
                    //TODO(pjm): I don't think a fixed domain works in conjunction with scaleFunction
                    $scope.axes.y.scale.domain($scope.axes.y.domain).nice();
                    return;
                }
                const ydoms = calcYDomains($scope.plots.filter(p => p._isVisible), $scope.axes.x.scale.domain());
                if (ydoms[0]) {
                    plotting.scaleYDomain($scope.axes.y.scale, ydoms[0], scaleFunction, ydoms[0][0] > 0 && $scope.axes.y.domain[0] == 0);
                }
                if (ydoms[1]) {
                    plotting.scaleYDomain($scope.axes.y2.scale, ydoms[1], scaleFunction, ydoms[1][0] > 0 && $scope.axes.y2.domain[0] == 0);
                }
            };

            $scope.refresh = function() {
                $scope.select('.plot-viewport').selectAll('.line')
                    .each(function (d) {
                        var ip = parseInt(d3.select(this).attr('data-sr-index'));
                        d3.select(this).attr('d', $scope.plotGraphLine(ip));
                    });

                $scope.select('.plot-viewport').selectAll('g.param-plot')
                    .each(function (d, ip) {
                        var sp = d3.select(this).selectAll('.scatter-point');
                        var dp = d3.select(this).selectAll('.data-point');
                        [sp, dp].forEach(function (pt) {
                            if (! pt) {
                                return;
                            }
                            pt.attr('cx', $scope.plotGraphLine(ip).x())
                                .attr('cy', $scope.plotGraphLine(ip).y());
                        });
                });

                $scope.focusPoints.forEach(function(fp) {
                    focusPointService.refreshFocusPoint(fp, $scope);
                });
                if ($scope.onRefresh) {
                    $scope.onRefresh();
                }
            };

            $scope.togglePlot = (pIndex) => {
                togglePlot(pIndex);
            };

            $scope.$on(SIREPO.PLOTTING_CSV_EVENT, ()=> {
                const points = [
                    $scope.axes.x.points,
                ];
                $scope.plots.forEach((plot)=> {
                    points.push(plot.points);
                });
                let res = $scope.axes.x.label;
                for (const p of $scope.plots) {
                    res += ',' + p.label;
                }
                res += '\n';
                for (let i = 0; i < points[0].length; i++) {
                    let row = '';
                    for (const [idx, col] of points.entries()) {
                        row += (idx > 0 ? ',' : '') + col[i].toExponential(9);
                    }
                    res += row + '\n';
                }
                saveAs(new Blob([res], {
                    type: "text/csv;charset=utf-8"
                }), plotting.csvFilename(plotting.plotTitle($element)));
            });

            // Note that here we pad the axis domain, not the scale!  The scale is set by
            // user interaction
            $scope.padXDomain = function() {
                var xdom = $scope.axes.x.domain;
                $scope.axes.x.domain = [xdom[0], xdom[1]];
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('particle', function(plotting, plot2dService) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/plot2d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            var allPoints, scaleFunction;

            $scope.init = function() {
                plot2dService.init2dPlot($scope, {
                    margin: {top: 50, right: 23, bottom: 20, left: 75},
                });
            };

            $scope.load = function(json) {
                $scope.aspectRatio = plotting.getAspectRatio($scope.modelName, json, 4.0 / 7);
                allPoints = [];
                var xdom = [json.x_range[0], json.x_range[1]];
                $scope.axes.x.domain = xdom;
                $scope.axes.x.scale.domain(xdom);
                scaleFunction = plotting.scaleFunction($scope.modelName);
                $scope.axes.y.domain = plotting.ensureDomain([json.y_range[0], json.y_range[1]], scaleFunction);
                $scope.axes.y.scale.domain($scope.axes.y.domain).nice();
                var viewport = $scope.select('.plot-viewport');
                viewport.selectAll('.line').remove();
                var isFixedX = ! Array.isArray(json.x_points[0]);
                var i;
                var lineClass = json.points.length > 20 ? 'line line-7' : 'line line-0';
                var points;
                for (i = 0; i < json.points.length; i++) {
                    points = d3.zip(
                        isFixedX ? json.x_points : json.x_points[i],
                        json.points[i]);
                    viewport.append('path').attr('class', lineClass).datum(points);
                    allPoints.push(points);
                }
                if (json.lost_x && json.lost_x.length) {
                    for (i = 0; i < json.lost_x.length; i++) {
                        points = d3.zip(json.lost_x[i], json.lost_y[i]);
                        viewport.append('path').attr('class', 'line line-reflected').datum(points);
                        allPoints.push(points);
                    }
                    // absorbed/reflected legend
                    $scope.select('svg.sr-plot')
                        .append('circle').attr('class', 'line-absorbed').attr('r', 5).attr('cx', 8).attr('cy', 10);
                    $scope.select('svg.sr-plot')
                        .append('text').attr('class', 'focus-text').attr('x', 16).attr('y', 16)
                        .text('Absorbed');
                    $scope.select('svg.sr-plot')
                        .append('circle').attr('class', 'line-reflected').attr('r', 5).attr('cx', 8).attr('cy', 30);
                    $scope.select('svg.sr-plot')
                        .append('text').attr('class', 'focus-text').attr('x', 16).attr('y', 36)
                        .text('Lost');
                }
                $scope.updatePlot(json);
            };

            $scope.recalculateYDomain = function() {
                var ydom;
                var xdom = $scope.axes.x.scale.domain();
                allPoints.forEach(function(points) {
                    points.forEach(function(p) {
                        var x = p[0];
                        var y = p[1];
                        if (x >= xdom[0] && x <= xdom[1]) {
                            if (ydom) {
                                if (y < ydom[0]) {
                                    ydom[0] = y;
                                }
                                else if (y > ydom[1]) {
                                    ydom[1] = y;
                                }
                            }
                            else {
                                ydom = [y, y];
                            }
                        }
                    });
                });
                if (ydom) {
                    plotting.scaleYDomain($scope.axes.y.scale, ydom, scaleFunction, ydom[0] > 0 && $scope.axes.y.domain[0] == 0);
                }
            };

            $scope.refresh = function() {
                $scope.select('.plot-viewport').selectAll('.line').attr('d', $scope.graphLine);
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.PLOTTING = {
    HeatmapSelectCellEvent: 'heatmapSelectCell',
    PlotPolygon: PlotPolygon,
    Utils: PlottingUtils,
};
