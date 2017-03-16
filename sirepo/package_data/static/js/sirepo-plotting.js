'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.factory('plotting', function(appState, d3Service, frameCache, panelState, $interval, $window) {

    var INITIAL_HEIGHT = 400;
    var MAX_PLOTS = 11;

    function cleanNumber(v) {
        v = v.replace(/\.0+(\D+)/, '$1');
        v = v.replace(/(\.\d)0+(\D+)/, '$1$2');
        return v;
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
        if (scope.clearData) {
            scope.$on('framesCleared', scope.clearData);
        }
        scope.$on('modelsLoaded', requestData);
        scope.$on('framesLoaded', function(event, oldFrameCount) {
            if (scope.prevFrameIndex < 0 || oldFrameCount === 0) {
                scope.lastFrame();
            }
            else if (scope.prevFrameIndex > frameCache.getFrameCount(scope.modelName)) {
                scope.firstFrame();
            }
            // go to the next last frame, if the current frame was the previous last frame
            else if (frameCache.getCurrentFrame(scope.modelName) >= oldFrameCount - 1) {
                scope.lastFrame();
            }
        });
        return requestData;
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
                if ((v && v.indexOf('z') > 0) || v == '0.00' || v == '0.0000') {
                    return '0';
                }
                v = cleanNumber(v);
                return v + units;
            };
        },

        initialHeight: function(scope) {
            return scope.isAnimation ? 1 : INITIAL_HEIGHT;
        },

        linkPlot: function(scope, element) {
            var priority = 0;
            var current = scope.$parent;
            while (current) {
                if (current.requestPriority) {
                    priority = current.requestPriority;
                    break;
                }
                current = current.$parent;
            }
            d3Service.d3().then(function(d3) {
                scope.element = element[0];
                scope.isAnimation = scope.modelName.indexOf('Animation') >= 0;
                var requestData;

                if (scope.isAnimation) {
                    requestData = initAnimation(scope);
                }
                else if (scope.isClientOnly) {
                    requestData = function() {};
                }
                else {
                    var interval = null;
                    requestData = function(forceRunCount) {
                        //TODO(pjm): timeout is a hack to give time for invalid reports to be destroyed
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
                }

                scope.windowResize = debounce(function() {
                    scope.resize();
                }, 250);

                scope.$on('$destroy', function() {
                    scope.destroy();
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
                scope.init();
                if (appState.isLoaded()) {
                    requestData();
                }
            });
        },

        linspace: function(start, stop, nsteps) {
            var delta = (stop - start) / (nsteps - 1);
            var res = d3.range(nsteps).map(function(d) { return start + d * delta; });

            if (res.length != nsteps) {
                throw "invalid linspace steps: " + nsteps + " != " + res.length;
            }
            return res;
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

    function calculateFWHM(xValues, yValues, yHalfMax) {
        function isPositive(num) {
            return true ? num > 0 : false;
        }
        var positive = isPositive(yValues[0] - yHalfMax);
        var listOfRoots = [];
        for (var i = 0; i < yValues.length; i++) {
            var currentPositive = isPositive(yValues[i] - yHalfMax);
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
            var localYHalfMax = points[peakIndex][1] / 2.0;
            for (i = leftMinIndex; i <= rightMinIndex; i++) {
                localXValues.push(points[i][0]);
                localYValues.push(points[i][1]);
            }
            fwhm = calculateFWHM(localXValues, localYValues, localYHalfMax);
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
            fwhmText = ', FWHM=' + fwhmConverted.toFixed(2) + ' ' + units;
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
            $scope.rightPanelWidth = $scope.bottomPanelHeight = 50;
            $scope.dataCleared = true;
            $scope.wantCrossHairs = ! SIREPO.PLOTTING_SUMMED_LINEOUTS;

            var bottomPanelCutLine, bottomPanelXAxis, bottomPanelYAxis, bottomPanelYScale, canvas, ctx, focusPointX, focusPointY, fullDomain, heatmap, imageObj, lineOuts, mainXAxis, mainYAxis, prevDomain, rightPanelCutLine, rightPanelXAxis, rightPanelYAxis, rightPanelXScale, xAxisScale, xIndexScale, xValues, xyZoom, xZoom, yAxisScale, yIndexScale, yValues, yZoom;

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

            function drawImage() {
                var xZoomDomain = xAxisScale.domain();
                var xDomain = fullDomain[0];
                var yZoomDomain = yAxisScale.domain();
                var yDomain = fullDomain[1];
                var zoomWidth = xZoomDomain[1] - xZoomDomain[0];
                var zoomHeight = yZoomDomain[1] - yZoomDomain[0];
                canvas.attr('width', $scope.canvasSize)
                    .attr('height', $scope.canvasSize);
                ctx.imageSmoothingEnabled = false;
                ctx.msImageSmoothingEnabled = false;
                var xPixelSize = (xDomain[1] - xDomain[0]) / zoomWidth * $scope.canvasSize / xValues.length;
                var yPixelSize = (yDomain[1] - yDomain[0]) / zoomHeight * $scope.canvasSize / yValues.length;
                ctx.drawImage(
                    imageObj,
                    -(xZoomDomain[0] - xDomain[0]) / zoomWidth * $scope.canvasSize - xPixelSize / 2,
                    -(yDomain[1] - yZoomDomain[1]) / zoomHeight * $scope.canvasSize - yPixelSize / 2,
                    (xDomain[1] - xDomain[0]) / zoomWidth * $scope.canvasSize + xPixelSize,
                    (yDomain[1] - yDomain[0]) / zoomHeight * $scope.canvasSize + yPixelSize);
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

            function initDraw(zmin, zmax) {
                var color = d3.scale.linear()
                    .domain([zmin, zmax])
                    .range(['#333', '#fff']);
                var xmax = xValues.length - 1;
                var ymax = yValues.length - 1;

                // Compute the pixel colors; scaled by CSS.
                var img = ctx.createImageData(xValues.length, yValues.length);
                for (var yi = 0, p = -1; yi <= ymax; ++yi) {
                    for (var xi = 0; xi <= xmax; ++xi) {
                        var c = d3.rgb(color(heatmap[yi][xi]));
                        img.data[++p] = c.r;
                        img.data[++p] = c.g;
                        img.data[++p] = c.b;
                        img.data[++p] = 255;
                    }
                }
                ctx.putImageData(img, 0, 0);
                imageObj.src = canvas.node().toDataURL();
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
                drawImage();
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
                imageObj.onload = null;
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
                canvas = select('canvas');
                ctx = canvas.node().getContext('2d');
                imageObj = new Image();
                // important - the image may not be ready initially
                imageObj.onload = refresh;
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
                heatmap = [];
                var newFullDomain = [
                    [json.x_range[0], json.x_range[1]],
                    [json.y_range[0], json.y_range[1]],
                ];
                if (! appState.deepEquals(fullDomain, newFullDomain)) {
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
                canvas.attr('width', xValues.length)
                    .attr('height', yValues.length);
                select('.main-title').text(json.title);
                select('.x-axis-label').text(plotting.extractUnits($scope, 'x', json.x_label));
                select('.y-axis-label').text(plotting.extractUnits($scope, 'y', json.y_label));
                select('.z-axis-label').text(json.z_label);
                var zmin = json.z_matrix[0][0];
                var zmax = json.z_matrix[0][0];

                for (var yi = 0; yi <= ymax; ++yi) {
                    // flip to match the canvas coordinate system (origin: top left)
                    // matplotlib is bottom left
                    heatmap[ymax - yi] = [];
                    for (var xi = 0; xi <= xmax; ++xi) {
                        var zi = json.z_matrix[yi][xi];
                        heatmap[ymax - yi][xi] = zi;
                        if (zmax < zi) {
                            zmax = zi;
                        }
                        else if (zmin > zi) {
                            zmin = zi;
                        }
                    }
                }
                //TODO(pjm): for now, we always want the lower range to be 0
                if (zmin > 0) {
                    zmin = 0;
                }
                bottomPanelYScale.domain([zmin, zmax]).nice();
                rightPanelXScale.domain([zmax, zmin]).nice();
                initDraw(zmin, zmax);
                $scope.resize();
            };

            $scope.resize = function() {
                //TODO(pjm): occasionally dies here in d3 when switching tabs
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

SIREPO.app.directive('heatmap', function(plotting) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/heatplot.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {

            $scope.margin = {top: 40, left: 60, right: 100, bottom: 50};
            // will be set to the correct size in resize()
            $scope.canvasSize = 0;
            $scope.dataCleared = true;

            var xAxis, canvas, colorbar, ctx, heatmap, mouseRect, yAxis, xAxisScale, xValueMax, xValueMin, xValueRange, yAxisScale, yValueMax, yValueMin, yValueRange, pointer;

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

            function colorMap(levels) {
                var colorMap = [];
                var mapGen = {
                    afmhot: function(x) {
                        return hex(2 * x) + hex(2 * x - 0.5) + hex(2 * x - 1);
                    },
                    grayscale: function(x) {
                        return hex(x) + hex(x) + hex(x);
                    }
                };

                function hex(v) {
                    if (v > 1) {
                        v = 1;
                    }
                    else if (v < 0) {
                        v = 0;
                    }
                    return ('0' + Math.round(v * 255).toString(16)).slice(-2);
                }

                var gen = mapGen.afmhot;

                for (var i = 0; i < levels; i++) {
                    var x = i / (levels - 1);
                    colorMap.push('#' + gen(x));
                }
                return colorMap;
            }

            function initDraw(zmin, zmax) {
                var levels = 50;
                var colorRange = d3.range(zmin, zmax, (zmax - zmin) / levels);
                colorRange.push(zmax);
                var color = d3.scale.linear()
                    .domain(colorRange)
                    .range(colorMap(levels));
                var xmax = xValueRange.length - 1;
                var ymax = yValueRange.length - 1;
                var img = ctx.createImageData(xValueRange.length, yValueRange.length);

                for (var yi = 0, p = -1; yi <= ymax; ++yi) {
                for (var xi = 0; xi <= xmax; ++xi) {
                    var c = d3.rgb(color(heatmap[yi][xi]));
                    img.data[++p] = c.r;
                    img.data[++p] = c.g;
                    img.data[++p] = c.b;
                    img.data[++p] = 255;
                }
                }
                ctx.putImageData(img, 0, 0);
                $scope.imageObj.src = canvas.node().toDataURL();

                colorbar = Colorbar()
                    .scale(color)
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
                var x0 = xAxisScale.invert(point[0] - 1);
                var y0 = yAxisScale.invert(point[1] - 1);
                var x = Math.round((heatmap[0].length - 1) * (x0 - xValueMin) / (xValueMax - xValueMin));
                var y = Math.round((heatmap.length - 1) * (y0 - yValueMin) / (yValueMax - yValueMin));
                var value = heatmap[heatmap.length - 1 - y][x];
                pointer.pointTo(value);
            }

            function refresh() {
                var tx = 0, ty = 0, s = 1;
                if (d3.event && d3.event.translate) {
                    var t = d3.event.translate;
                    s = d3.event.scale;
                    tx = t[0];
                    ty = t[1];
                    tx = Math.min(
                        0,
                        Math.max(
                            tx,
                            $scope.canvasSize - (s * $scope.imageObj.width) / ($scope.imageObj.width / $scope.canvasSize)));
                    ty = Math.min(
                        0,
                        Math.max(
                            ty,
                            $scope.canvasSize - (s * $scope.imageObj.height) / ($scope.imageObj.height / $scope.canvasSize)));

                    var xdom = xAxisScale.domain();
                    var ydom = yAxisScale.domain();
                    var resetS = 0;
                    if ((xdom[1] - xdom[0]) >= (xValueMax - xValueMin) * 0.9999) {
                        $scope.zoom.x(xAxisScale.domain([xValueMin, xValueMax]));
                        xdom = xAxisScale.domain();
                        resetS += 1;
                    }
                    if ((ydom[1] - ydom[0]) >= (yValueMax - yValueMin) * 0.9999) {
                        $scope.zoom.y(yAxisScale.domain([yValueMin, yValueMax]));
                        ydom = yAxisScale.domain();
                        resetS += 1;
                    }
                    if (resetS == 2) {
                        mouseRect.attr('class', 'mouse-zoom');
                        // Both axes are full resolution. Reset.
                        tx = 0;
                        ty = 0;
                    }
                    else {
                        mouseRect.attr('class', 'mouse-move');
                        if (xdom[0] < xValueMin) {
                            xAxisScale.domain([xValueMin, xdom[1] - xdom[0] + xValueMin]);
                            xdom = xAxisScale.domain();
                        }
                        if (xdom[1] > xValueMax) {
                            xdom[0] -= xdom[1] - xValueMax;
                            xAxisScale.domain([xdom[0], xValueMax]);
                        }
                        if (ydom[0] < yValueMin) {
                            yAxisScale.domain([yValueMin, ydom[1] - ydom[0] + yValueMin]);
                            ydom = yAxisScale.domain();
                        }
                        if (ydom[1] > yValueMax) {
                            ydom[0] -= ydom[1] - yValueMax;
                            yAxisScale.domain([ydom[0], yValueMax]);
                        }
                    }
                }

                canvas.attr('width', $scope.canvasSize)
                    .attr('height', $scope.canvasSize);
                ctx.clearRect(0, 0, $scope.canvasSize, $scope.canvasSize);
                if (s == 1) {
                    tx = 0;
                    ty = 0;
                    $scope.zoom.translate([tx, ty]);
                }
                ctx.imageSmoothingEnabled = false;
                ctx.msImageSmoothingEnabled = false;
                ctx.drawImage(
                    $scope.imageObj,
                    tx,
                    ty,
                    $scope.canvasSize * s,
                    $scope.canvasSize * s
                );
                select('.x.axis').call(xAxis);
                select('.y.axis').call(yAxis);
            }

            $scope.resize = function() {
                var canvasSize = parseInt(select().style('width')) - $scope.margin.left - $scope.margin.right;
                if (! heatmap || isNaN(canvasSize)) {
                    return;
                }
                $scope.canvasSize = canvasSize;
                plotting.ticks(yAxis, canvasSize, false);
                plotting.ticks(xAxis, canvasSize, true);
                xAxisScale.range([0, canvasSize]);
                yAxisScale.range([canvasSize, 0]);
                $scope.zoom.x(xAxisScale.domain([xValueMin, xValueMax]))
                    .y(yAxisScale.domain([yValueMin, yValueMax]));
                select('.mouse-rect').call($scope.zoom);
                colorbar.barlength(canvasSize)
                    .origin([0, 0]);
                pointer = select('.colorbar').call(colorbar);
                refresh();
            };

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            $scope.clearData = function() {
                $scope.dataCleared = true;
                $scope.prevFrameIndex = -1;
            };

            $scope.init = function() {
                select('svg').attr('height', plotting.initialHeight($scope));
                xAxisScale = d3.scale.linear();
                yAxisScale = d3.scale.linear();
                xAxis = plotting.createAxis(xAxisScale, 'bottom');
                xAxis.tickFormat(plotting.fixFormat($scope, 'x', 5));
                yAxis = plotting.createAxis(yAxisScale, 'left');
                yAxis.tickFormat(plotting.fixFormat($scope, 'y', 5));
                $scope.zoom = d3.behavior.zoom()
                    .scaleExtent([1, 10])
                    .on('zoom', refresh);
                canvas = select('canvas');
                mouseRect = select('.mouse-rect');
                mouseRect.on('mousemove', mouseMove);
                ctx = canvas.node().getContext('2d');
                $scope.imageObj = new Image();
                $scope.imageObj.onload = refresh;
            };

            $scope.load = function(json) {
                $scope.dataCleared = false;
                heatmap = [];
                xValueMin = json.x_range[0];
                xValueMax = json.x_range[1];
                xValueRange = plotting.linspace(xValueMin, xValueMax, json.x_range[2]);
                yValueMin = json.y_range[0];
                yValueMax = json.y_range[1];
                yValueRange = plotting.linspace(yValueMin, yValueMax, json.y_range[2]);
                var xmax = xValueRange.length - 1;
                var ymax = yValueRange.length - 1;
                canvas.attr('width', xValueRange.length)
                    .attr('height', yValueRange.length);
                select('.main-title').text(json.title);
                select('.x-axis-label').text(plotting.extractUnits($scope, 'x', json.x_label));
                select('.y-axis-label').text(plotting.extractUnits($scope, 'y', json.y_label));
                select('.z-axis-label').text(json.z_label);
                xAxisScale.domain([xValueMin, xValueMax]);
                yAxisScale.domain([yValueMin, yValueMax]);
                var zmin = json.z_matrix[0][0];
                var zmax = json.z_matrix[0][0];

                for (var yi = 0; yi <= ymax; ++yi) {
                    // flip to match the canvas coordinate system (origin: top left)
                    // matplotlib is bottom left
                    heatmap[ymax - yi] = [];
                    for (var xi = 0; xi <= xmax; ++xi) {
                        var zi = json.z_matrix[yi][xi];
                        heatmap[ymax - yi][xi] = zi;
                        if (zmax < zi) {
                            zmax = zi;
                        }
                        else if (zmin > zi) {
                            zmin = zi;
                        }
                    }
                }
                initDraw(allFrameMin.compute(zmin), allFrameMax.compute(zmax));
                $scope.resize();
            };

            $scope.modelChanged = function() {
                allFrameMin = new EMA();
                allFrameMax = new EMA();
            };

            $scope.destroy = function() {
                $('.mouse-rect').off();
                if ($scope.zoom) {
                    $scope.zoom.on('zoom', null);
                }
                if ($scope.imageObj) {
                    $scope.imageObj.onload = null;
                }
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});
