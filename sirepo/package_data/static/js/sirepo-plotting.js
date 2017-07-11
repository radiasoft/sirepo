'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.factory('plotting', function(appState, d3Service, frameCache, panelState, $interval, $rootScope, $window) {

    var INITIAL_HEIGHT = 400;
    var MAX_PLOTS = 11;
    var COLOR_MAP = {
        grayscale: ['#333', '#fff'],
        afmhot: colorsFromString('0000000200000400000600000800000a00000c00000e00001000001200001400001600001800001a00001c00001e00002000002200002400002600002800002a00002c00002e00003000003200003400003600003800003a00003c00003e00004000004200004400004600004800004a00004c00004e00005000005200005400005600005800005a00005c00005e00006000006200006400006600006800006a00006c00006e00007000007200007400007600007800007a00007c00007e00008000008202008404008607008808008a0a008c0d008e0f009010009212009414009617009818009a1a009c1d009e1f00a02000a22200a42400a62700a82800aa2a00ac2d00ae2f00b03000b23200b43400b63700b83800ba3a00bc3d00be3f00c04000c24200c44400c64600c84800ca4a00cc4d00ce4e00d05000d25200d45400d65600d85800da5a00dc5d00de5e00e06000e26200e46400e66600e86800ea6a00ec6d00ee6e00f07000f27200f47400f67600f87800fa7a00fc7d00fe7e00ff8001ff8203ff8405ff8607ff8809ff8b0bff8c0dff8e0fff9011ff9213ff9415ff9617ff9919ff9b1bff9c1dff9e1fffa021ffa223ffa425ffa627ffa829ffab2bffac2dffae2fffb031ffb233ffb435ffb637ffb939ffbb3bffbc3dffbe3fffc041ffc243ffc445ffc647ffc849ffcb4bffcc4dffce4fffd051ffd253ffd455ffd657ffd959ffdb5bffdc5dffde5fffe061ffe263ffe465ffe667ffe869ffeb6bffec6dffee6ffff071fff273fff475fff677fff979fffb7bfffc7dfffe7fffff81ffff83ffff85ffff87ffff89ffff8bffff8dffff8fffff91ffff93ffff95ffff97ffff99ffff9bffff9dffff9fffffa1ffffa3ffffa5ffffa7ffffa9ffffabffffadffffafffffb1ffffb3ffffb5ffffb7ffffb9ffffbbffffbdffffbfffffc1ffffc3ffffc5ffffc7ffffc9ffffcbffffcdffffcfffffd1ffffd3ffffd5ffffd7ffffd9ffffdbffffddffffdfffffe1ffffe3ffffe5ffffe7ffffe9ffffebffffedffffeffffff1fffff3fffff5fffff7fffff9fffffbfffffdffffff'),
        jet: colorsFromString('00008000008400008900008d00009200009600009b00009f0000a40000a80000ad0000b20000b60000bb0000bf0000c40000c80000cd0000d10000d60000da0000df0000e30000e80000ed0000f10000f60000fa0000ff0000ff0000ff0000ff0000ff0004ff0008ff000cff0010ff0014ff0018ff001cff0020ff0024ff0028ff002cff0030ff0034ff0038ff003cff0040ff0044ff0048ff004cff0050ff0054ff0058ff005cff0060ff0064ff0068ff006cff0070ff0074ff0078ff007cff0080ff0084ff0088ff008cff0090ff0094ff0098ff009cff00a0ff00a4ff00a8ff00acff00b0ff00b4ff00b8ff00bcff00c0ff00c4ff00c8ff00ccff00d0ff00d4ff00d8ff00dcfe00e0fb00e4f802e8f406ecf109f0ee0cf4eb0ff8e713fce416ffe119ffde1cffdb1fffd723ffd426ffd129ffce2cffca30ffc733ffc436ffc139ffbe3cffba40ffb743ffb446ffb149ffad4dffaa50ffa753ffa456ffa05aff9d5dff9a60ff9763ff9466ff906aff8d6dff8a70ff8773ff8377ff807aff7d7dff7a80ff7783ff7387ff708aff6d8dff6a90ff6694ff6397ff609aff5d9dff5aa0ff56a4ff53a7ff50aaff4dadff49b1ff46b4ff43b7ff40baff3cbeff39c1ff36c4ff33c7ff30caff2cceff29d1ff26d4ff23d7ff1fdbff1cdeff19e1ff16e4ff13e7ff0febff0ceeff09f1fc06f4f802f8f500fbf100feed00ffea00ffe600ffe200ffde00ffdb00ffd700ffd300ffd000ffcc00ffc800ffc400ffc100ffbd00ffb900ffb600ffb200ffae00ffab00ffa700ffa300ff9f00ff9c00ff9800ff9400ff9100ff8d00ff8900ff8600ff8200ff7e00ff7a00ff7700ff7300ff6f00ff6c00ff6800ff6400ff6000ff5d00ff5900ff5500ff5200ff4e00ff4a00ff4700ff4300ff3f00ff3b00ff3800ff3400ff3000ff2d00ff2900ff2500ff2200ff1e00ff1a00ff1600ff1300fa0f00f60b00f10800ed0400e80000e40000df0000da0000d60000d10000cd0000c80000c40000bf0000bb0000b60000b20000ad0000a80000a400009f00009b00009600009200008d0000890000840000800000'),
        viridis: colorsFromString('44015444025645045745055946075a46085c460a5d460b5e470d60470e6147106347116447136548146748166848176948186a481a6c481b6d481c6e481d6f481f70482071482173482374482475482576482677482878482979472a7a472c7a472d7b472e7c472f7d46307e46327e46337f463480453581453781453882443983443a83443b84433d84433e85423f854240864241864142874144874045884046883f47883f48893e49893e4a893e4c8a3d4d8a3d4e8a3c4f8a3c508b3b518b3b528b3a538b3a548c39558c39568c38588c38598c375a8c375b8d365c8d365d8d355e8d355f8d34608d34618d33628d33638d32648e32658e31668e31678e31688e30698e306a8e2f6b8e2f6c8e2e6d8e2e6e8e2e6f8e2d708e2d718e2c718e2c728e2c738e2b748e2b758e2a768e2a778e2a788e29798e297a8e297b8e287c8e287d8e277e8e277f8e27808e26818e26828e26828e25838e25848e25858e24868e24878e23888e23898e238a8d228b8d228c8d228d8d218e8d218f8d21908d21918c20928c20928c20938c1f948c1f958b1f968b1f978b1f988b1f998a1f9a8a1e9b8a1e9c891e9d891f9e891f9f881fa0881fa1881fa1871fa28720a38620a48621a58521a68522a78522a88423a98324aa8325ab8225ac8226ad8127ad8128ae8029af7f2ab07f2cb17e2db27d2eb37c2fb47c31b57b32b67a34b67935b77937b87838b9773aba763bbb753dbc743fbc7340bd7242be7144bf7046c06f48c16e4ac16d4cc26c4ec36b50c46a52c56954c56856c66758c7655ac8645cc8635ec96260ca6063cb5f65cb5e67cc5c69cd5b6ccd5a6ece5870cf5773d05675d05477d1537ad1517cd2507fd34e81d34d84d44b86d54989d5488bd6468ed64590d74393d74195d84098d83e9bd93c9dd93ba0da39a2da37a5db36a8db34aadc32addc30b0dd2fb2dd2db5de2bb8de29bade28bddf26c0df25c2df23c5e021c8e020cae11fcde11dd0e11cd2e21bd5e21ad8e219dae319dde318dfe318e2e418e5e419e7e419eae51aece51befe51cf1e51df4e61ef6e620f8e621fbe723fde725'),
    };

    function cleanNumber(v) {
        v = v.replace(/\.0+(\D+)/, '$1');
        v = v.replace(/(\.\d)0+(\D+)/, '$1$2');
        return v;
    }

    function colorsFromString(s) {
        return s.match(/.{6}/g).map(function(x) {
            return "#" + x;
        });
    }

    function createAxis(scale, orient) {
        return d3.svg.axis()
            .scale(scale)
            .orient(orient);
    }

    // Returns a function, that, as long as it continues to be invoked, will not
    // be triggered. The function will be called after it stops being called for
    // N milliseconds.
    // taken from http://davidwalsh.name/javascript-debounce-function
    function debounce(delayedFunc, milliseconds) {
        var debounceInterval = null;
        return function() {
            var context = this, args = arguments;
            var later = function() {
                if (debounceInterval) {
                    $interval.cancel(debounceInterval);
                    debounceInterval = null;
                }
                delayedFunc.apply(context, args);
            };
            if (debounceInterval) {
                $interval.cancel(debounceInterval);
            }
            debounceInterval = $interval(later, milliseconds, 1);
        };
    }

    function initAnimation(scope) {
        scope.prevFrameIndex = -1;
        scope.isPlaying = false;
        var requestData = function() {
            if (! scope.hasFrames()) {
                return;
            }
            var index = frameCache.getCurrentFrame(scope.modelName);
            if (frameCache.getCurrentFrame(scope.modelName) == scope.prevFrameIndex) {
                return;
            }
            scope.prevFrameIndex = index;
            frameCache.getFrame(scope.modelName, index, scope.isPlaying, function(index, data) {
                if (scope.element) {
                    if (data.error) {
                        panelState.setError(scope.modelName, data.error);
                        return;
                    }
                    scope.load(data);
                }
                if (scope.isPlaying) {
                    scope.advanceFrame(1);
                }
            });
        };
        scope.advanceFrame = function(increment) {
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
            if (scope.modelChanged) {
                scope.modelChanged();
            }
            requestData();
        };
        scope.hasFrames = function() {
            return frameCache.isLoaded() && frameCache.getFrameCount(scope.modelName) > 0;
        };
        scope.hasManyFrames = function() {
            if (SIREPO.APP_NAME == 'srw') {
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
                scope.advanceFrame(1);
            }
        };
        scope.$on('framesCleared', function() {
            scope.prevFrameIndex = -1;
            if (scope.clearData) {
                scope.clearData();
            }
        });
        scope.$on('modelsLoaded', requestData);
        scope.$on('framesLoaded', function(event, oldFrameCount) {
            if (scope.prevFrameIndex < 0 || oldFrameCount === 0) {
                scope.defaultFrame();
            }
            else if (scope.prevFrameIndex > frameCache.getFrameCount(scope.modelName)) {
                scope.firstFrame();
            }
            // go to the next last frame, if the current frame was the previous last frame
            else if (frameCache.getCurrentFrame(scope.modelName) >= oldFrameCount - 1) {
                scope.defaultFrame();
            }
        });
        return requestData;
    }

    function initPlot(scope) {
        var priority = 0;
        var current = scope.$parent;
        while (current) {
            if (current.requestPriority) {
                priority = current.requestPriority;
                break;
            }
            current = current.$parent;
        }
        var interval = null;
        var requestData = function(forceRunCount) {
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
                    forceRunCount = forceRunCount || 0;
                    if (data.x_range) {
                        scope.clearData();
                        scope.load(data);
                        if (data.summaryData) {
                            $rootScope.$broadcast(scope.modelName + '.summaryData', data.summaryData);
                        }
                    }
                    else if (forceRunCount++ <= 2) {
                        // try again, probably bad data
                        panelState.clear(scope.modelName);
                        requestData(forceRunCount);
                    }
                    else {
                        panelState.setError(scope.modelName, 'server error: incomplete result');
                        srlog('incomplete response: ', data);
                    }
                }, forceRunCount ? true : false);
            }, 50 + priority * 10, 1);
        };
        return requestData;
    }

    function linspace(start, stop, nsteps) {
        var delta = (stop - start) / (nsteps - 1);
        var res = d3.range(nsteps).map(function(d) { return start + d * delta; });
        res[res.length - 1] = stop;

        if (res.length != nsteps) {
            throw "invalid linspace steps: " + nsteps + " != " + res.length;
        }
        return res;
    }

    return {

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

        createAxis: createAxis,

        createExponentialAxis: function(scale, orient) {
            return createAxis(scale, orient)
            // this causes a 'number of fractional digits' error in MSIE
            //.tickFormat(d3.format('e'))
                .tickFormat(function (value) {
                    if (value) {
                        if (Math.abs(value) < 1e3 & Math.abs(value) > 1e-3) {
                            return cleanNumber(value.toString());
                        } else {
                            return cleanNumber(value.toExponential(2));
                        }
                    }
                    return value;
                });
        },

        drawImage: function(xAxisScale, yAxisScale, width, height, xValues, yValues, canvas, cacheCanvas, alignOnPixel) {
            var xZoomDomain = xAxisScale.domain();
            var xDomain = [xValues[0], xValues[xValues.length - 1]];
            var yZoomDomain = yAxisScale.domain();
            var yDomain = [yValues[0], yValues[yValues.length - 1]];
            var zoomWidth = xZoomDomain[1] - xZoomDomain[0];
            var zoomHeight = yZoomDomain[1] - yZoomDomain[0];
            canvas.width = width;
            canvas.height = height;
            var xPixelSize = alignOnPixel ? ((xDomain[1] - xDomain[0]) / zoomWidth * width / xValues.length) : 0;
            var yPixelSize = alignOnPixel ? ((yDomain[1] - yDomain[0]) / zoomHeight * height / yValues.length) : 0;
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

        extractUnits: function(scope, axis, label) {
            scope[axis + 'units'] = '';
            var match = label.match(/\[(.*?)\]/);
            if (match) {
                scope[axis + 'units'] = match[1];
                label = label.replace(/\[.*?\]/, '');
            }
            return label;
        },

        fixFormat: function(scope, axis, precision) {
            var format = d3.format('.' + (precision || '3') + 's');
            var format2 = d3.format('.2f');
            // amounts near zero may appear as NNNz, change them to 0
            return function(n) {
                var units = scope[axis + 'units'];
                if (! units) {
                    return format2(n);
                }
                var v = format(n);
                //TODO(pjm): use a regexp
                if ((v && (v.indexOf('z') > 0 || v.indexOf('y') > 0)) || v == '0.00' || v == '0.0000') {
                    return '0';
                }
                v = cleanNumber(v);
                return v + units;
            };
        },

        initialHeight: function(scope) {
            return scope.isAnimation ? 1 : INITIAL_HEIGHT;
        },

        initImage: function(zMin, zMax, heatmap, cacheCanvas, imageData) {
            var colorRange = COLOR_MAP[SIREPO.PLOTTING_COLOR_MAP || 'viridis'];
            var colorScale = d3.scale.linear()
                .domain(linspace(zMin, zMax, colorRange.length))
                .range(colorRange);
            var xSize = heatmap[0].length;
            var ySize = heatmap.length;
            var img = imageData;

            for (var yi = 0, p = -1; yi < ySize; ++yi) {
                for (var xi = 0; xi < xSize; ++xi) {
                    var c = d3.rgb(colorScale(heatmap[yi][xi]));
                    img.data[++p] = c.r;
                    img.data[++p] = c.g;
                    img.data[++p] = c.b;
                    img.data[++p] = 255;
                }
            }
            cacheCanvas.getContext('2d').putImageData(img, 0, 0);
            return colorScale;
        },

        linkPlot: function(scope, element) {
            d3Service.d3().then(function(d3) {
                scope.element = element[0];
                scope.isAnimation = scope.modelName.indexOf('Animation') >= 0;
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

                scope.windowResize = debounce(function() {
                    scope.resize();
                }, 250);

                scope.$on('$destroy', function() {
                    scope.destroy();
                    $(d3.select(scope.element).select('svg').node()).off();
                    scope.element = null;
                    $($window).off('resize', scope.windowResize);
                });

                scope.$on(
                    scope.modelName + '.changed',
                    function() {
                        scope.prevFrameIndex = -1;
                        if (scope.modelChanged) {
                            scope.modelChanged();
                        }
                        panelState.clear(scope.modelName);
                        requestData();
                    });
                scope.isLoading = function() {
                    if (scope.isAnimation) {
                        return false;
                    }
                    return panelState.isLoading(scope.modelName);
                };
                $($window).resize(scope.windowResize);
                // #777 catch touchstart on outer svg nodes to prevent browser zoom on ipad
                $(d3.select(scope.element).select('svg').node()).on('touchstart touchmove', function(event) {
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
            });
        },

        linspace: linspace,

        min2d: function(data) {
            return d3.min(data, function(row) {
                return d3.min(row);
            });
        },

        max2d: function(data) {
            return d3.max(data, function(row) {
                return d3.max(row);
            });
        },

        recalculateDomainFromPoints: function(yScale, points, xDomain, invertAxis) {
            var ydom;

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
            }
            if (ydom && ydom[0] != ydom[1]) {
                if (ydom[0] > 0) {
                    ydom[0] = 0;
                }
                if (invertAxis) {
                    var x = ydom[0];
                    ydom[0] = ydom[1];
                    ydom[1] = x;
                }
                yScale.domain(ydom).nice();
            }
        },

        refreshConvergencePoints: function(select, parentClass, graphLine) {
            for (var i = 0; i < MAX_PLOTS; i++) {
                select(parentClass + ' .line-' + i).attr('d', graphLine);
            }
        },

        ticks: function(axis, width, isHorizontalAxis) {
            var spacing = isHorizontalAxis ? 60 : 40;
            var n = Math.max(Math.round(width / spacing), 2);
            axis.ticks(n);
        },

        // ensures the axis domain fits in the fullDomain
        // returns true if size is reset to full
        trimDomain: function(axisScale, fullDomain) {
            var dom = axisScale.domain();
            var zoomSize = dom[1] - dom[0];

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
    };
});

SIREPO.app.directive('animationButtons', function() {
    return {
        restrict: 'A',
        template: [
            '<div data-ng-if="isAnimation && hasManyFrames()" style="width: 100%;" class="text-center">',
              '<button type="button" class="btn btn-default" data-ng-disabled="isFirstFrame()" data-ng-click="firstFrame()"><span class="glyphicon glyphicon-backward"></span></button>',
              '<button type="button" class="btn btn-default" data-ng-disabled="isFirstFrame()" data-ng-click="advanceFrame(-1)"><span class="glyphicon glyphicon-step-backward"></span></button>',
              '<button type="button" class="btn btn-default" data-ng-disabled="isLastFrame()" data-ng-click="togglePlay()"><span class="glyphicon glyphicon-{{ isPlaying ? \'pause\' : \'play\' }}"></span></button>',
              '<button type="button" class="btn btn-default" data-ng-disabled="isLastFrame()" data-ng-click="advanceFrame(1)"><span class="glyphicon glyphicon-step-forward"></span></button>',
              '<button type="button" class="btn btn-default" data-ng-disabled="isLastFrame()" data-ng-click="lastFrame()"><span class="glyphicon glyphicon-forward"></span></button>',
            '</div>',
        ].join(''),
    };
});

//TODO(pjm): remove global function, change into a service
function setupFocusPoint(overlay, circleClass, xAxisScale, yAxisScale, invertAxis, scope) {

    var defaultCircleSize, focusIndex, formatter, keyListener, lastClickX, ordinateFormatter, points;

    function isPositive(num) {
        return true ? num > 0 : false;
    }

    function normalizeValues(yValues, shift) {
        var yMin = Math.min.apply(Math, yValues);
        var yMax = Math.max.apply(Math, yValues);
        var yRange = yMax - yMin;
        for (var i = 0; i < yValues.length; i++) {
            yValues[i] = (yValues[i] - yMin) / yRange - shift;  // roots are at Y=0
        }
        return yValues;
    }

    function calculateFWHM(xValues, yValues) {
        yValues = normalizeValues(yValues, 0.5);
        var positive = isPositive(yValues[0]);
        var listOfRoots = [];
        for (var i = 0; i < yValues.length; i++) {
            var currentPositive = isPositive(yValues[i]);
            if (currentPositive !== positive) {
                listOfRoots.push(xValues[i - 1] + (xValues[i] - xValues[i - 1]) / (Math.abs(yValues[i]) + Math.abs(yValues[i - 1])) * Math.abs(yValues[i - 1]));
                positive = !positive;
            }
        }
        var fwhm = null;
        if (listOfRoots.length >= 2) {
            fwhm = Math.abs(listOfRoots[listOfRoots.length - 1] - listOfRoots[0]);
        }
        return fwhm;
    }

    function formatValue(v) {
        if (v < 1 || v > 1000000) {
            return ordinateFormatter(v);
        }
        return formatter(v);
    }

    function hasFocusPoint() {
        return points && focusIndex >= 0 && focusIndex < points.length;
    }

    function hideFocusPoint() {
        select(circleClass).style('display', 'none');
        select('.focus-text').text('');
    }

    function init() {
        focusIndex = -1;
        formatter = d3.format('.3f');
        ordinateFormatter = d3.format('.3e');
        overlay
            .on('mouseover', function() {
                if (! keyListener) {
                    keyListener = true;
                    d3.select('body').on('keydown', onKeyDown);
                }
            })
            .on('mouseout', function() {
                d3.select('body').on('keydown', null);
                keyListener = false;
            })
            .on('mousedown', function(e) {
                lastClickX = d3.event[invertAxis ? 'clientY' : 'clientX'];
            })
            .on('click', onClick)
            .on('dblclick', function copyToClipboard() {
                var focusText = select('.focus-text');
                var focusHint = select('.focus-hint');
                var inputField = $('<input>');
                $('body').append(inputField);
                inputField.val(focusText.text()).select();
                try {
                    document.execCommand('copy');
                    focusHint.style('display', null);
                    focusHint.text('Copied to clipboard');
                    setTimeout(function () {
                        focusHint.style('display', 'none');
                    }, 1000);
                } catch(e) {}
                inputField.remove();
            });

        return {
            load: function(axisPoints, preservePoint) {
                if (preservePoint && (axisPoints.length != (points || []).length)) {
                    preservePoint = false;
                }
                points = axisPoints;
                if (preservePoint) {
                    var focus = select(circleClass);
                    if (focus.style('display') != 'none') {
                        return;
                    }
                }
                focusIndex = -1;
                hideFocusPoint();
            },
            refresh: function() {
                if (hasFocusPoint()) {
                    showFocusPoint(true);
                }
            },
        };
    }

    function moveFocus(step) {
        if (! hasFocusPoint()) {
            return;
        }
        if (invertAxis) {
            step = -step;
        }
        var newIndex = focusIndex + step;
        if (newIndex < 0 || newIndex >= points.length) {
            return;
        }
        focusIndex = newIndex;
        showFocusPoint(false);
    }

    function onClick() {
        /*jshint validthis: true*/
        // lastClickX determines if the user is panning or clicking on a point
        if (! points || Math.abs(lastClickX - d3.event[invertAxis ? 'clientY' : 'clientX']) > 10) {
            return;
        }
        var axisIndex = invertAxis ? 1 : 0;
        var mouseX = d3.mouse(this)[axisIndex];
        var xMin = xAxisScale.invert(mouseX - 10);
        var xMax = xAxisScale.invert(mouseX + 10);
        if (xMin > xMax) {
            var swap = xMin;
            xMin = xMax;
            xMax = swap;
        }
        var domain = xAxisScale.domain();
        if (xMin < domain[0]) {
            xMin = domain[0];
        }
        if (xMax > domain[1]) {
            xMax = domain[1];
        }

        focusIndex = -1;
        var maxPoint;
        for (var i = 0; i < points.length; i++) {
            var p = points[i];
            if (p[0] > xMax || p[0] < xMin) {
                continue;
            }
            if (! maxPoint || p[1] > maxPoint[1]) {
                maxPoint = p;
                focusIndex = i;
            }
        }
        if (maxPoint) {
            showFocusPoint(true);
        }
    }

    function onKeyDown() {
        if (! hasFocusPoint()) {
            return;
        }
        var keyCode = d3.event.keyCode;
        if (keyCode == 27) { // escape
            hideFocusPoint();
        }
        if (keyCode == 37 || keyCode == 40) { // left & down
            moveFocus(-1);
            d3.event.preventDefault();
        }
        if (keyCode == 39 || keyCode == 38) { // right & up
            moveFocus(1);
            d3.event.preventDefault();
        }
    }

    function select(selector) {
        var e = d3.select(overlay.node().parentNode);
        return e.select(selector);
    }

    function showFocusPoint(isMainFocus) {
        if (! hasFocusPoint()) {
            return;
        }
        var p = points[focusIndex];
        var domain = xAxisScale.domain();
        $(overlay.node()).parent().find('[class=focus]').hide();

        if (p[0] < domain[0] || p[0] > domain[1]) {
            hideFocusPoint();
            return;
        }
        var focus = select(circleClass);
        focus.style('display', null);
        var circle = select(circleClass + ' circle');
        if (isMainFocus) {
            if (! defaultCircleSize) {
                defaultCircleSize = circle.attr('r');
            }
            circle.attr('r', defaultCircleSize);
        }
        else {
            circle.attr('r', defaultCircleSize - 2);
        }

        var xValues = [];
        var yValues = [];
        for (var i = 0; i < points.length; i++) {
            xValues.push(points[i][0]);
            yValues.push(points[i][1]);
        }

        // Find the local maximum and the left and righ minima:
        var peakIndex = null;
        var rightMinIndex = null;
        var leftMinIndex = null;
        var fwhm = null;
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
                } else { // we are on the left from the maximum
                    for (i = focusIndex + 1; i < xValues.length; i++) { // >>> go to the right to find the maximum
                        if (points[i-1][1] > points[i][1]) { // we crossed the maximum and started to descend
                            // >>> ^ - we reached the maximum:
                            peakIndex = i - 1;
                            break;
                        }
                    }
                }
            } else {
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
            fwhm = calculateFWHM(localXValues, localYValues);
        }

        var fwhmText = '';
        if (fwhm !== null && typeof(fwhm) !== 'undefined') {
            var fwhmConverted = fwhm;
            var units = invertAxis ? scope.yunits : scope.xunits;
            if (fwhm >= 1e9 && fwhm < 1e12) {
                fwhmConverted = fwhm * 1e-9;
                units = 'G' + units;
            } else if (fwhm >= 1e6 && fwhm < 1e9) {
                fwhmConverted = fwhm * 1e-6;
                units = 'M' + units;
            } else if (fwhm >= 1e3 && fwhm < 1e6) {
                fwhmConverted = fwhm * 1e-3;
                units = 'k' + units;
            } else if (fwhm >= 1e-3 && fwhm < 1e0) {
                fwhmConverted = fwhm * 1e3;
                units = 'm' + units;
            } else if (fwhm >= 1e-6 && fwhm < 1e-3) {
                fwhmConverted = fwhm * 1e6;
                units = 'µ' + units;
            } else if (fwhm >= 1e-9 && fwhm < 1e-6) {
                fwhmConverted = fwhm * 1e9;
                units = 'n' + units;
            } else if (fwhm >= 1e-12 && fwhm < 1e-9) {
                fwhmConverted = fwhm * 1e12;
                units = 'p' + units;
            }
            fwhmText = ', FWHM=' + fwhmConverted.toFixed(3) + ' ' + units;
        }
        if (invertAxis) {
            focus.attr('transform', 'translate(' + yAxisScale(p[1]) + ',' + xAxisScale(p[0]) + ')');
        } else {
            focus.attr('transform', 'translate(' + xAxisScale(p[0]) + ',' + yAxisScale(p[1]) + ')');
        }
        select('.focus-text').text('X=' + formatValue(p[0]) + ', Y=' + formatValue(p[1]) + '' + fwhmText);
    }

    return init();
}

SIREPO.app.directive('plot2d', function(plotting) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/plot2d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            var ASPECT_RATIO = 4.0 / 7;
            $scope.margin = {top: 50, right: 20, bottom: 50, left: 70};
            $scope.width = $scope.height = 0;
            $scope.dataCleared = true;
            var focusPoint, graphLine, points, xAxis, xAxisGrid, xAxisScale, xDomain, yAxis, yAxisGrid, yAxisScale, yDomain, zoom;

            function refresh() {
                if (! xDomain) {
                    return;
                }

                if (plotting.trimDomain(xAxisScale, xDomain)) {
                    select('.overlay').attr('class', 'overlay mouse-zoom');
                    yAxisScale.domain(yDomain).nice();
                }
                else {
                    select('.overlay').attr('class', 'overlay mouse-move-ew');
                    plotting.recalculateDomainFromPoints(yAxisScale, points[0], xAxisScale.domain());
                }
                resetZoom();
                select('.overlay').call(zoom);
                select('.x.axis').call(xAxis);
                select('.x.axis.grid').call(xAxisGrid); // tickLine == gridline
                select('.y.axis').call(yAxis);
                select('.y.axis.grid').call(yAxisGrid);
                plotting.refreshConvergencePoints(select, '.plot-viewport', graphLine);
                focusPoint.refresh();
            }

            function resetZoom() {
                zoom = d3.behavior.zoom()
                    .x(xAxisScale)
                    .on('zoom', refresh);
            }

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            $scope.clearData = function() {
                $scope.dataCleared = true;
                xDomain = null;
            };

            $scope.destroy = function() {
                zoom.on('zoom', null);
                $('.overlay').off();
            };

            $scope.init = function() {
                select('svg').attr('height', plotting.initialHeight($scope));
                xAxisScale = d3.scale.linear();
                yAxisScale = d3.scale.linear();
                xAxis = plotting.createAxis(xAxisScale, 'bottom');
                xAxis.tickFormat(plotting.fixFormat($scope, 'x'));
                xAxisGrid = plotting.createAxis(xAxisScale, 'bottom');
                yAxis = plotting.createExponentialAxis(yAxisScale, 'left');
                yAxisGrid = plotting.createAxis(yAxisScale, 'left');
                graphLine = d3.svg.line()
                    .x(function(d) {return xAxisScale(d[0]);})
                    .y(function(d) {return yAxisScale(d[1]);});
                focusPoint = setupFocusPoint(select('.overlay'), '.focus', xAxisScale, yAxisScale, false, $scope);
                resetZoom();
            };

            $scope.load = function(json) {
                $scope.dataCleared = false;
                var xPoints = json.x_points
                    ? json.x_points
                    : plotting.linspace(json.x_range[0], json.x_range[1], json.points.length);
                $scope.xRange = json.x_range;
                var xdom = [json.x_range[0], json.x_range[1]];
                if (! (xDomain && xDomain[0] == xdom[0] && xDomain[1] == xdom[1])) {
                    xDomain = xdom;
                    points = [];
                    xAxisScale.domain(xdom);
                }
                if (! SIREPO.PLOTTING_SHOW_CONVERGENCE_LINEOUTS) {
                    points = [];
                }
                var ymin = d3.min(json.points);
                if (ymin > 0) {
                    ymin = 0;
                }
                yDomain = [ymin, d3.max(json.points)];
                yAxisScale.domain(yDomain).nice();
                var p = d3.zip(xPoints, json.points);
                plotting.addConvergencePoints(select, '.plot-viewport', points, p);
                focusPoint.load(p, true);
                select('.y-axis-label').text(json.y_label);
                select('.x-axis-label').text(plotting.extractUnits($scope, 'x', json.x_label));
                select('.main-title').text(json.title);
                $scope.resize();
            };

            $scope.resize = function() {
                if (select().empty()) {
                    return;
                }
                var width = parseInt(select().style('width')) - $scope.margin.left - $scope.margin.right;
                if (! points || isNaN(width)) {
                    return;
                }
                $scope.width = width;
                $scope.height = ASPECT_RATIO * $scope.width;
                select('svg')
                    .attr('width', $scope.width + $scope.margin.left + $scope.margin.right)
                    .attr('height', $scope.height + $scope.margin.top + $scope.margin.bottom);
                plotting.ticks(xAxis, $scope.width, true);
                plotting.ticks(xAxisGrid, $scope.width, true);
                plotting.ticks(yAxis, $scope.height, false);
                plotting.ticks(yAxisGrid, $scope.height, false);
                xAxisScale.range([0, $scope.width]);
                yAxisScale.range([$scope.height, 0]);
                xAxisGrid.tickSize(-$scope.height);
                yAxisGrid.tickSize(-$scope.width);
                refresh();
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('plot3d', function(appState, plotting) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/plot3d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {

            var MIN_PIXEL_RESOLUTION = 10;
            $scope.margin = 50;
            $scope.bottomPanelMargin = {top: 10, bottom: 30};
            $scope.rightPanelMargin = {left: 10, right: 40};
            // will be set to the correct size in resize()
            $scope.canvasSize = 0;
            $scope.titleCenter = 0;
            $scope.rightPanelWidth = $scope.bottomPanelHeight = 50;
            $scope.dataCleared = true;
            $scope.wantCrossHairs = ! SIREPO.PLOTTING_SUMMED_LINEOUTS;

            var bottomPanelCutLine, bottomPanelXAxis, bottomPanelYAxis, bottomPanelYScale, canvas, ctx, focusPointX, focusPointY, fullDomain, heatmap, lineOuts, mainXAxis, mainYAxis, prevDomain, rightPanelCutLine, rightPanelXAxis, rightPanelYAxis, rightPanelXScale, xAxisScale, xIndexScale, xValues, xyZoom, xZoom, yAxisScale, yIndexScale, yValues, yZoom;
            var cacheCanvas, imageData;

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

            function centerTitle() {
                // center the title over the image, if text is too large, center it over whole plot
                var titleNode = select('text.main-title').node();
                if (titleNode) {
                    var width = titleNode.getBBox().width;
                    $scope.titleCenter = $scope.canvasSize / 2;
                    if (width > $scope.canvasSize) {
                        $scope.titleCenter += $scope.rightPanelWidth / 2;
                    }
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

            function sumRegion(isWidth, bottom, top, left, right) {
                var points = [];
                var max = isWidth ? right : top;
                for (var i = 0; i <= max; i++) {
                    points[i] = 0;
                }
                for (i = bottom; i <= top; i++) {
                    for (var j = left; j <= right; j++) {
                        var index = isWidth ? j : i;
                        points[index] += heatmap[yValues.length - 1 - i][j];
                    }
                }
                return points;
            }

            function drawBottomPanelCut() {
                var row;
                var yBottom = yIndexScale(yAxisScale.domain()[0]);
                var yTop = yIndexScale(yAxisScale.domain()[1]);
                var yv = Math.round(yBottom + (yTop - yBottom) / 2);
                if (SIREPO.PLOTTING_SUMMED_LINEOUTS) {
                    row = sumRegion(
                        true,
                        Math.floor(yBottom + 0.5),
                        Math.ceil(yTop - 0.5),
                        Math.floor(xIndexScale(xAxisScale.domain()[0])),
                        Math.ceil(xIndexScale(xAxisScale.domain()[1])));
                }
                else {
                    row = heatmap[yValues.length - 1 - yv];
                }
                var points = d3.zip(xValues, row);
                plotting.recalculateDomainFromPoints(bottomPanelYScale, points, xAxisScale.domain());
                drawLineout('x', yv, points, bottomPanelCutLine);
                focusPointX.load(points, true);
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
                var xLeft = xIndexScale(xAxisScale.domain()[0]);
                var xRight = xIndexScale(xAxisScale.domain()[1]);
                var xv = Math.round(xLeft + (xRight - xLeft) / 2);
                var points;

                if (SIREPO.PLOTTING_SUMMED_LINEOUTS) {
                    points = d3.zip(yValues, sumRegion(
                        false,
                        Math.floor(yIndexScale(yAxisScale.domain()[0])),
                        Math.ceil(yIndexScale(yAxisScale.domain()[1])),
                        Math.floor(xLeft + 0.5),
                        Math.ceil(xRight - 0.5)));
                }
                else {
                    points = heatmap.map(function (v, i) {
                        return [yValues[yValues.length - 1 - i], v[xv]];
                    });
                }
                plotting.recalculateDomainFromPoints(rightPanelXScale, points, yAxisScale.domain(), true);
                drawLineout('y', xv, points, rightPanelCutLine);
                focusPointY.load(points, true);
            }

            function exceededMaxZoom(scale, axisName) {
                var domain = fullDomain[axisName == 'x' ? 0 : 1];
                var domainSize = domain[1] - domain[0];
                var d = scale.domain();
                var pixels = (axisName == 'x' ? xValues : yValues).length * (d[1] - d[0]) / domainSize;
                return pixels < MIN_PIXEL_RESOLUTION;
            }

            function refresh() {
                if (! fullDomain) {
                    return;
                }
                if (prevDomain && (exceededMaxZoom(xAxisScale, 'x') || exceededMaxZoom(yAxisScale, 'y'))) {
                    restoreDomain(xAxisScale, prevDomain[0]);
                    restoreDomain(yAxisScale, prevDomain[1]);
                }
                if (clipDomain(xAxisScale, 'x') + clipDomain(yAxisScale, 'y')) {
                    select('rect.mouse-rect-xy').attr('class', 'mouse-rect-xy mouse-move');
                }
                else {
                    select('rect.mouse-rect-xy').attr('class', 'mouse-rect-xy mouse-zoom');
                }
                plotting.drawImage(xAxisScale, yAxisScale, $scope.canvasSize, $scope.canvasSize, xValues, yValues, canvas, cacheCanvas, true);
                drawBottomPanelCut();
                drawRightPanelCut();
                resetZoom();
                select('.mouse-rect-xy').call(xyZoom);
                select('.mouse-rect-x').call(xZoom);
                select('.mouse-rect-y').call(yZoom);
                select('.bottom-panel .x.axis').call(bottomPanelXAxis);
                select('.bottom-panel .y.axis').call(bottomPanelYAxis);
                select('.right-panel .x.axis').call(rightPanelXAxis);
                select('.right-panel .y.axis').call(rightPanelYAxis);
                select('.x.axis.grid').call(mainXAxis);
                select('.y.axis.grid').call(mainYAxis);
                focusPointX.refresh();
                focusPointY.refresh();
                prevDomain = [
                    xAxisScale.domain(),
                    yAxisScale.domain(),
                ];
                centerTitle();
            }

            function resetZoom() {
                xyZoom = d3.behavior.zoom()
                    .x(xAxisScale)
                    .y(yAxisScale)
                    .on('zoom', refresh);
                xZoom = d3.behavior.zoom()
                    .x(xAxisScale)
                    .on('zoom', refresh);
                yZoom = d3.behavior.zoom()
                    .y(yAxisScale)
                    .on('zoom', refresh);
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

            $scope.clearData = function() {
                $scope.dataCleared = true;
                fullDomain = null;
                lineOuts = {};
            };

            $scope.destroy = function() {
                xyZoom.on('zoom', null);
                xZoom.on('zoom', null);
                yZoom.on('zoom', null);
            };

            $scope.init = function() {
                select('svg').attr('height', plotting.initialHeight($scope));
                xAxisScale = d3.scale.linear();
                xIndexScale = d3.scale.linear();
                yAxisScale = d3.scale.linear();
                yIndexScale = d3.scale.linear();
                bottomPanelYScale = d3.scale.linear();
                rightPanelXScale = d3.scale.linear();
                mainXAxis = plotting.createAxis(xAxisScale, 'bottom');
                mainYAxis = plotting.createAxis(yAxisScale, 'left');
                bottomPanelXAxis = plotting.createAxis(xAxisScale, 'bottom');
                bottomPanelXAxis.tickFormat(plotting.fixFormat($scope, 'x'));
                bottomPanelYAxis = plotting.createExponentialAxis(bottomPanelYScale, 'left');
                rightPanelXAxis = plotting.createExponentialAxis(rightPanelXScale, 'bottom');
                rightPanelYAxis = plotting.createAxis(yAxisScale, 'right');
                rightPanelYAxis.tickFormat(plotting.fixFormat($scope, 'y'));
                resetZoom();
                canvas = select('canvas').node();
                ctx = canvas.getContext('2d');
                cacheCanvas = document.createElement('canvas');
                bottomPanelCutLine = d3.svg.line()
                    .x(function(d) {return xAxisScale(d[0]);})
                    .y(function(d) {return bottomPanelYScale(d[1]);});
                rightPanelCutLine = d3.svg.line()
                    .y(function(d) { return yAxisScale(d[0]);})
                    .x(function(d) { return rightPanelXScale(d[1]);});
                focusPointX = setupFocusPoint(select('.mouse-rect-x'), '.bottom-panel .focus', xAxisScale, bottomPanelYScale, false, $scope);
                focusPointY = setupFocusPoint(select('.mouse-rect-y'), '.right-panel .focus', yAxisScale, rightPanelXScale, true, $scope);
            };

            $scope.load = function(json) {
                prevDomain = null;
                $scope.dataCleared = false;
                heatmap = appState.clone(json.z_matrix).reverse();
                var newFullDomain = [
                    [json.x_range[0], json.x_range[1]],
                    [json.y_range[0], json.y_range[1]],
                ];
                if ((yValues && yValues.length != json.z_matrix.length)
                    || ! appState.deepEquals(fullDomain, newFullDomain)) {
                    fullDomain = newFullDomain;
                    lineOuts = {};
                    xValues = plotting.linspace(fullDomain[0][0], fullDomain[0][1], json.x_range[2]);
                    yValues = plotting.linspace(fullDomain[1][0], fullDomain[1][1], json.y_range[2]);
                    xAxisScale.domain(fullDomain[0]);
                    xIndexScale.domain(fullDomain[0]);
                    yAxisScale.domain(fullDomain[1]);
                    yIndexScale.domain(fullDomain[1]);
                    adjustZoomToCenter(xAxisScale);
                    adjustZoomToCenter(yAxisScale);
                }
                var xmax = xValues.length - 1;
                var ymax = yValues.length - 1;
                xIndexScale.range([0, xmax]);
                yIndexScale.range([0, ymax]);
                cacheCanvas.width = xValues.length;
                cacheCanvas.height = yValues.length;
                imageData = ctx.getImageData(0, 0, cacheCanvas.width, cacheCanvas.height);
                select('.main-title').text(json.title);
                select('.x-axis-label').text(plotting.extractUnits($scope, 'x', json.x_label));
                select('.y-axis-label').text(plotting.extractUnits($scope, 'y', json.y_label));
                select('.z-axis-label').text(json.z_label);
                var zmin = plotting.min2d(heatmap);
                var zmax = plotting.max2d(heatmap);

                //TODO(pjm): for now, we always want the lower range to be 0
                if (zmin > 0) {
                    zmin = 0;
                }
                bottomPanelYScale.domain([zmin, zmax]).nice();
                rightPanelXScale.domain([zmax, zmin]).nice();
                plotting.initImage(zmin, zmax, heatmap, cacheCanvas, imageData);
                $scope.resize();
            };

            $scope.resize = function() {
                if (select().empty()) {
                    return;
                }
                var width = parseInt(select().style('width')) - 2 * $scope.margin;
                if (! heatmap || isNaN(width)){
                    return;
                }
                var canvasSize = 2 * (width - $scope.rightPanelMargin.left - $scope.rightPanelMargin.right) / 3;
                $scope.canvasSize = canvasSize;
                $scope.bottomPanelHeight = 2 * canvasSize / 5 + $scope.bottomPanelMargin.top + $scope.bottomPanelMargin.bottom;
                $scope.rightPanelWidth = canvasSize / 2 + $scope.rightPanelMargin.left + $scope.rightPanelMargin.right;
                plotting.ticks(rightPanelXAxis, $scope.rightPanelWidth - $scope.rightPanelMargin.left - $scope.rightPanelMargin.right, true);
                plotting.ticks(rightPanelYAxis, canvasSize, false);
                plotting.ticks(bottomPanelXAxis, canvasSize, true);
                plotting.ticks(bottomPanelYAxis, $scope.bottomPanelHeight, false);
                plotting.ticks(mainXAxis, canvasSize, true);
                plotting.ticks(mainYAxis, canvasSize, false);
                xAxisScale.range([0, canvasSize]);
                yAxisScale.range([canvasSize, 0]);
                bottomPanelYScale.range([$scope.bottomPanelHeight - $scope.bottomPanelMargin.top - $scope.bottomPanelMargin.bottom - 1, 0]);
                rightPanelXScale.range([0, $scope.rightPanelWidth - $scope.rightPanelMargin.left - $scope.rightPanelMargin.right]);
                mainXAxis.tickSize(- canvasSize - $scope.bottomPanelHeight + $scope.bottomPanelMargin.bottom); // tickLine == gridline
                mainYAxis.tickSize(- canvasSize - $scope.rightPanelWidth + $scope.rightPanelMargin.right); // tickLine == gridline
                refresh();
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('heatmap', function(appState, plotting) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/heatplot.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {

            $scope.margin = {top: 40, left: 60, right: 100, bottom: 50};
            // will be set to the correct size in resize()
            $scope.canvasSize = {
                width: 0,
                height: 0,
            };
            $scope.dataCleared = true;

            var aspectRatio = 1.0;
            var canvas, colorbar, ctx, heatmap, pointer, xAxis, xAxisScale, xValues, yAxis, yAxisScale, yValues, zoom;
            var cacheCanvas, imageData;

            var EMA = function() {
                var avg = null;
                var length = 3;
                var alpha = 2.0 / (length + 1.0);
                this.compute = function(value) {
                    return avg += avg !== null
                    ? alpha * (value - avg)
                    : value;
                };
            };

            var allFrameMin = new EMA();
            var allFrameMax = new EMA();

            function getRange(values) {
                return [values[0], values[values.length - 1]];
            }

            function initDraw(zmin, zmax) {
                var colorScale = plotting.initImage(zmin, zmax, heatmap, cacheCanvas, imageData);
                colorbar = Colorbar()
                    .scale(colorScale)
                    .thickness(30)
                    .margin({top: 0, right: 60, bottom: 20, left: 10})
                    .orient("vertical");
            }

            function mouseMove() {
                /*jshint validthis: true*/
                if (! heatmap || heatmap[0].length <= 2) {
                    return;
                }
                var point = d3.mouse(this);
                var xRange = getRange(xValues);
                var yRange = getRange(yValues);
                var x0 = xAxisScale.invert(point[0] - 1);
                var y0 = yAxisScale.invert(point[1] - 1);
                var x = Math.round((heatmap[0].length - 1) * (x0 - xRange[0]) / (xRange[1] - xRange[0]));
                var y = Math.round((heatmap.length - 1) * (y0 - yRange[0]) / (yRange[1] - yRange[0]));
                var value = heatmap[heatmap.length - 1 - y][x];
                pointer.pointTo(value);
            }

            function refresh() {
                if (plotting.trimDomain(xAxisScale, getRange(xValues))
                    + plotting.trimDomain(yAxisScale, getRange(yValues))) {
                    select('.mouse-rect').attr('class', 'mouse-rect mouse-zoom');
                }
                else {
                    select('.mouse-rect').attr('class', 'mouse-rect mouse-move');
                }
                plotting.drawImage(xAxisScale, yAxisScale, $scope.canvasSize.width, $scope.canvasSize.height, xValues, yValues, canvas, cacheCanvas, false);
                resetZoom();
                select('.mouse-rect').call(zoom);
                select('.x.axis').call(xAxis);
                select('.y.axis').call(yAxis);
            }

            function resetZoom() {
                zoom = d3.behavior.zoom()
                    .x(xAxisScale)
                    .y(yAxisScale)
                    .on('zoom', refresh);
            }

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            $scope.clearData = function() {
                $scope.dataCleared = true;
                $scope.prevFrameIndex = -1;
            };

            $scope.destroy = function() {
                $('.mouse-rect').off();
                zoom.on('zoom', null);
            };

            $scope.init = function() {
                select('svg').attr('height', plotting.initialHeight($scope));
                xAxisScale = d3.scale.linear();
                yAxisScale = d3.scale.linear();
                xAxis = plotting.createAxis(xAxisScale, 'bottom');
                xAxis.tickFormat(plotting.fixFormat($scope, 'x', 5));
                yAxis = plotting.createAxis(yAxisScale, 'left');
                yAxis.tickFormat(plotting.fixFormat($scope, 'y', 5));
                resetZoom();
                canvas = select('canvas').node();
                select('.mouse-rect').on('mousemove', mouseMove);
                ctx = canvas.getContext('2d');
                cacheCanvas = document.createElement('canvas');
            };

            $scope.load = function(json) {
                $scope.dataCleared = false;
                aspectRatio = json.aspect_ratio || 1.0;
                heatmap = appState.clone(json.z_matrix).reverse();
                xValues = plotting.linspace(json.x_range[0], json.x_range[1], json.x_range[2]);
                yValues = plotting.linspace(json.y_range[0], json.y_range[1], json.y_range[2]);
                cacheCanvas.width = xValues.length;
                cacheCanvas.height = yValues.length;
                imageData = ctx.getImageData(0, 0, cacheCanvas.width, cacheCanvas.height);
                select('.main-title').text(json.title);
                select('.x-axis-label').text(plotting.extractUnits($scope, 'x', json.x_label));
                select('.y-axis-label').text(plotting.extractUnits($scope, 'y', json.y_label));
                select('.z-axis-label').text(json.z_label);
                select('.frequency-label').text(json.frequency_title);
                xAxisScale.domain(getRange(xValues));
                yAxisScale.domain(getRange(yValues));
                initDraw(
                    allFrameMin.compute(plotting.min2d(heatmap)),
                    allFrameMax.compute(plotting.max2d(heatmap)));
                $scope.resize();
            };

            $scope.modelChanged = function() {
                allFrameMin = new EMA();
                allFrameMax = new EMA();
            };

            $scope.resize = function() {
                if (select().empty()) {
                    return;
                }
                var width = parseInt(select().style('width')) - $scope.margin.left - $scope.margin.right;
                if (! heatmap || isNaN(width)) {
                    return;
                }
                $scope.canvasSize.width = width;
                $scope.canvasSize.height = width * aspectRatio;
                plotting.ticks(yAxis, $scope.canvasSize.height, false);
                plotting.ticks(xAxis, $scope.canvasSize.width, true);
                xAxisScale.range([0, $scope.canvasSize.width]);
                yAxisScale.range([$scope.canvasSize.height, 0]);
                colorbar.barlength($scope.canvasSize.height)
                    .origin([0, 0]);
                pointer = select('.colorbar').call(colorbar);
                refresh();
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

//TODO(pjm): consolidate plot code with plotting service
SIREPO.app.directive('parameterPlot', function(plotting) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/plot2d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            var ASPECT_RATIO = 4.0 / 7;
            $scope.margin = {top: 50, right: 20, bottom: 50, left: 70};
            $scope.width = $scope.height = 0;
            $scope.dataCleared = true;
            var graphLine, xAxis, xAxisGrid, xAxisScale, xDomain, yAxis, yAxisGrid, yAxisScale, yDomain, y1Label, y2Label, zoom, xPoints;

            function refresh() {
                if (! xDomain) {
                    return;
                }
                var xdom = xAxisScale.domain();
                var zoomWidth = xdom[1] - xdom[0];

                if (zoomWidth >= (xDomain[1] - xDomain[0])) {
                    select('.overlay').attr('class', 'overlay mouse-zoom');
                    xAxisScale.domain(xDomain);
                    yAxisScale.domain(yDomain).nice();
                }
                else {
                    select('.overlay').attr('class', 'overlay mouse-move-ew');
                    if (xdom[0] < xDomain[0]) {
                        xAxisScale.domain([xDomain[0], zoomWidth + xDomain[0]]);
                    }
                    if (xdom[1] > xDomain[1]) {
                        xAxisScale.domain([xDomain[1] - zoomWidth, xDomain[1]]);
                    }
                }
                resetZoom();
                select('.overlay').call(zoom);
                select('.x.axis').call(xAxis);
                select('.x.axis.grid').call(xAxisGrid); // tickLine == gridline
                select('.y.axis').call(yAxis);
                select('.y.axis.grid').call(yAxisGrid);
                select('.plot-viewport').selectAll('.line').attr('d', graphLine);
            }

            function resetZoom() {
                zoom = d3.behavior.zoom()
                    .x(xAxisScale)
                    .on('zoom', refresh);
            }

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            $scope.clearData = function() {
                $scope.dataCleared = true;
                xDomain = null;
            };

            $scope.destroy = function() {
                zoom.on('zoom', null);
                $('.overlay').off();
            };

            $scope.init = function() {
                select('svg').attr('height', plotting.initialHeight($scope));
                xAxisScale = d3.scale.linear();
                yAxisScale = d3.scale.linear();
                xAxis = plotting.createAxis(xAxisScale, 'bottom');
                xAxis.tickFormat(plotting.fixFormat($scope, 'x'));
                xAxisGrid = plotting.createAxis(xAxisScale, 'bottom');
                yAxis = plotting.createAxis(yAxisScale, 'left');
                yAxis.tickFormat(plotting.fixFormat($scope, 'y'));
                yAxisGrid = plotting.createAxis(yAxisScale, 'left');
                graphLine = d3.svg.line()
                    .x(function(d, i) {
                        return xAxisScale(xPoints[i]);
                    })
                    .y(function(d) {
                        return yAxisScale(d);
                    });
                resetZoom();
                // y1/y2 legend
                select('svg')
                    .append('circle').attr('class', 'line-y1').attr('r', 5).attr('cx', 8).attr('cy', 10);
                y1Label = select('svg')
                    .append('text').attr('class', 'focus-text').attr('x', 16).attr('y', 16);
                select('svg')
                    .append('circle').attr('class', 'line-y2').attr('r', 5).attr('cx', 8).attr('cy', 30);
                y2Label = select('svg')
                    .append('text').attr('class', 'focus-text').attr('x', 16).attr('y', 36);
            };

            $scope.load = function(json) {
                $scope.dataCleared = false;
                xPoints = json.x_points
                    ? json.x_points
                    : plotting.linspace(json.x_range[0], json.x_range[1], json.points.length);
                $scope.xRange = json.x_range;
                var xdom = [json.x_range[0], json.x_range[1]];
                xDomain = xdom;
                xAxisScale.domain(xdom);
                yDomain = [json.y_range[0], json.y_range[1]];
                yAxisScale.domain(yDomain).nice();
                var viewport = select('.plot-viewport');
                viewport.selectAll('.line').remove();
                viewport.append('path').attr('class', 'line line-y1').datum(json.points[0]);
                viewport.append('path').attr('class', 'line line-y2').datum(json.points[1]);
                select('.y-axis-label').text(plotting.extractUnits($scope, 'y', json.y_label));
                select('.x-axis-label').text(plotting.extractUnits($scope, 'x', json.x_label));
                select('.main-title').text(json.title);
                $scope.resize();
                y1Label.text(json.y1_title);
                y2Label.text(json.y2_title);
            };

            $scope.resize = function() {
                if (select().empty()) {
                    return;
                }
                var width = parseInt(select().style('width')) - $scope.margin.left - $scope.margin.right;
                if (! xPoints || isNaN(width)) {
                    return;
                }
                $scope.width = width;
                $scope.height = ASPECT_RATIO * $scope.width;
                select('svg')
                    .attr('width', $scope.width + $scope.margin.left + $scope.margin.right)
                    .attr('height', $scope.height + $scope.margin.top + $scope.margin.bottom);
                plotting.ticks(xAxis, $scope.width, true);
                plotting.ticks(xAxisGrid, $scope.width, true);
                plotting.ticks(yAxis, $scope.height, false);
                plotting.ticks(yAxisGrid, $scope.height, false);
                xAxisScale.range([0, $scope.width]);
                yAxisScale.range([$scope.height, 0]);
                xAxisGrid.tickSize(-$scope.height);
                yAxisGrid.tickSize(-$scope.width);
                refresh();
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

//TODO(pjm): consolidate plot code with plotting service
SIREPO.app.directive('particle', function(plotting) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/plot2d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            var ASPECT_RATIO = 4.0 / 7;
            $scope.margin = {top: 50, right: 20, bottom: 50, left: 70};
            $scope.width = $scope.height = 0;
            $scope.dataCleared = true;
            var graphLine, xAxis, xAxisGrid, xAxisScale, xDomain, yAxis, yAxisGrid, yAxisScale, yDomain, zoom;

            function refresh() {
                if (! xDomain) {
                    return;
                }
                var xdom = xAxisScale.domain();
                var zoomWidth = xdom[1] - xdom[0];

                if (zoomWidth >= (xDomain[1] - xDomain[0])) {
                    select('.overlay').attr('class', 'overlay mouse-zoom');
                    xAxisScale.domain(xDomain);
                    yAxisScale.domain(yDomain).nice();
                }
                else {
                    select('.overlay').attr('class', 'overlay mouse-move-ew');
                    if (xdom[0] < xDomain[0]) {
                        xAxisScale.domain([xDomain[0], zoomWidth + xDomain[0]]);
                    }
                    if (xdom[1] > xDomain[1]) {
                        xAxisScale.domain([xDomain[1] - zoomWidth, xDomain[1]]);
                    }
                }
                resetZoom();
                select('.overlay').call(zoom);
                select('.x.axis').call(xAxis);
                select('.x.axis.grid').call(xAxisGrid); // tickLine == gridline
                select('.y.axis').call(yAxis);
                select('.y.axis.grid').call(yAxisGrid);
                select('.plot-viewport').selectAll('.line').attr('d', graphLine);
            }

            function resetZoom() {
                zoom = d3.behavior.zoom()
                    .x(xAxisScale)
                    .on('zoom', refresh);
            }

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            $scope.clearData = function() {
                $scope.dataCleared = true;
                xDomain = null;
            };

            $scope.destroy = function() {
                zoom.on('zoom', null);
                $('.overlay').off();
            };

            $scope.init = function() {
                select('svg').attr('height', plotting.initialHeight($scope));
                xAxisScale = d3.scale.linear();
                yAxisScale = d3.scale.linear();
                xAxis = plotting.createAxis(xAxisScale, 'bottom');
                xAxis.tickFormat(plotting.fixFormat($scope, 'x'));
                xAxisGrid = plotting.createAxis(xAxisScale, 'bottom');
                yAxis = plotting.createAxis(yAxisScale, 'left');
                yAxis.tickFormat(plotting.fixFormat($scope, 'y'));
                yAxisGrid = plotting.createAxis(yAxisScale, 'left');
                graphLine = d3.svg.line()
                    .x(function(d) {
                        return xAxisScale(d[0]);
                    })
                    .y(function(d) {
                        return yAxisScale(d[1]);
                    });
                resetZoom();
            };

            $scope.load = function(json) {
                $scope.dataCleared = false;
                // xPoints = json.x_points
                //     ? json.x_points
                //     : plotting.linspace(json.x_range[0], json.x_range[1], json.points.length);
                $scope.xRange = json.x_range;
                var xdom = [json.x_range[0], json.x_range[1]];
                xDomain = xdom;
                xAxisScale.domain(xdom);
                yDomain = [json.y_range[0], json.y_range[1]];
                yAxisScale.domain(yDomain).nice();
                var viewport = select('.plot-viewport');
                viewport.selectAll('.line').remove();
                var isFixedX = ! Array.isArray(json.x_points[0]);
                for (var i = 0; i < json.points.length; i++) {
                    var p = d3.zip(
                        isFixedX ? json.x_points : json.x_points[i],
                        json.points[i]);
                    viewport.append('path').attr('class', 'line line-7').datum(p);
                }
                // json.points.forEach(function(p) {
                //     viewport.append('path').attr('class', 'line line-7').datum(p);
                // });
                select('.y-axis-label').text(plotting.extractUnits($scope, 'y', json.y_label));
                select('.x-axis-label').text(plotting.extractUnits($scope, 'x', json.x_label));
                select('.main-title').text(json.title);
                $scope.resize();
            };

            $scope.resize = function() {
                if (select().empty()) {
                    return;
                }
                var width = parseInt(select().style('width')) - $scope.margin.left - $scope.margin.right;
                if (! xDomain || isNaN(width)) {
                    return;
                }
                $scope.width = width;
                $scope.height = ASPECT_RATIO * $scope.width;
                select('svg')
                    .attr('width', $scope.width + $scope.margin.left + $scope.margin.right)
                    .attr('height', $scope.height + $scope.margin.top + $scope.margin.bottom);
                plotting.ticks(xAxis, $scope.width, true);
                plotting.ticks(xAxisGrid, $scope.width, true);
                plotting.ticks(yAxis, $scope.height, false);
                plotting.ticks(yAxisGrid, $scope.height, false);
                xAxisScale.range([0, $scope.width]);
                yAxisScale.range([$scope.height, 0]);
                xAxisGrid.tickSize(-$scope.height);
                yAxisGrid.tickSize(-$scope.width);
                refresh();
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});
