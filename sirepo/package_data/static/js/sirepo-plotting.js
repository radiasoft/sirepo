'use strict';

(function() {
    var INITIAL_HEIGHT = 400;

    function createAxis(scale, orient) {
        return d3.svg.axis()
            .scale(scale)
            .orient(orient);
    }

    function createExponentialAxis(scale, orient) {
        return createAxis(scale, orient)
        // this causes a 'number of fractional digits' error in MSIE
        //.tickFormat(d3.format('e'))
            .tickFormat(function (value) {
                return value.toExponential();
            });
    }

    // Returns a function, that, as long as it continues to be invoked, will not
    // be triggered. The function will be called after it stops being called for
    // N milliseconds. If `immediate` is passed, trigger the function on the
    // leading edge, instead of the trailing.
    // taken from http://davidwalsh.name/javascript-debounce-function
    function debounce(func, wait, immediate) {
        var timeout;
        return function() {
            var context = this, args = arguments;
            var later = function() {
                timeout = null;
                if (!immediate) func.apply(context, args);
            };
            var callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(context, args);
        };
    }

    function linkPlot(scope, element, d3Service, appState) {
        d3Service.d3().then(function(d3) {
            scope.element = element[0];

            function requestData() {
                if (! appState.isLoaded())
                    return;
                //console.log('requesting data: ', scope.modelName);
                appState.requestData(scope.modelName, function(data) {
                    //console.log('loading data: ', scope.modelName);
                    if (scope.element)
                        scope.load(data);
                });
            }
            scope.$on(scope.modelName + '.changed', requestData);
            scope.init();
            requestData();
        });
    }

    function ticks(axis, width, isHorizontalAxis) {
        var spacing = isHorizontalAxis ? 80 : 30;
        var n = Math.max(Math.round(width / spacing), 2);
        axis.ticks(n);
    };


    app.directive('plot2d', function(appState, d3Service) {
        return {
            restrict: 'A',
            scope: {
                modelName: '@',
            },
            templateUrl: '/static/html/plot2d.html?20150728',
            controller: function($scope) {

                var ASPECT_RATIO = 4.0 / 7;
                $scope.margin = {top: 50, right: 50, bottom: 80, left: 70};
                $scope.width = $scope.height = 0;
                var formatter, graphLine, points, xAxis, xAxisGrid, xAxisScale, xPeakValues, xUnits, yAxis, yAxisGrid, yAxisScale;

                function computePeaks(json, dimensions, xPoints) {
                    var peakSpacing = dimensions[0] / 20;
                    var minPixelHeight = dimensions[1] * .995;
                    var xPeakValues = [];
                    var sortedPoints = d3.zip(xPoints, json.points).sort(function(a, b) { return b[1] - a[1] });
                    for (var i = 0; i < sortedPoints.length / 2; i++) {
                        var p = sortedPoints[i]
                        var xPixel = xAxisScale(p[0]);
                        var yPixel = yAxisScale(p[1]);
                        if (yPixel >= minPixelHeight) {
                            break;
                        }
                        var found = false;
                        for (var j = 0; j < xPeakValues.length; j++) {
                            if (Math.abs(xPixel - xPeakValues[j][2]) < peakSpacing) {
                                found = true;
                                break;
                            }
                        }
                        if (! found)
                            xPeakValues.push([p[0], p[1], xPixel]);
                    }
                    //console.log('local maxes: ', xPeakValues.length);
                    return xPeakValues;
                }

                function linspace(start, stop, nsteps) {
                    var delta = (stop - start) / (nsteps - 1);
                    return d3.range(start, stop + delta, delta).slice(0, nsteps);
                }

                function mouseMove() {
                    if (! points)
                        return;
                    var x0 = xAxisScale.invert(d3.mouse(this)[0]);
                    var localMax = null;
                    for (var i = 0; i < xPeakValues.length; i++) {
                        var v = xPeakValues[i];
                        if (localMax === null || Math.abs(v[0] - x0) < Math.abs(localMax[0] - x0)) {
                            localMax = v;
                        }
                    }
                    if (localMax) {
                        var xPixel = xAxisScale(localMax[0]);
                        if (xPixel < 0 || xPixel >= select('.plot-viewport').attr('width'))
                            return;
                        var focus = select('.focus');
                        focus.attr('transform', 'translate(' + xPixel + ',' + yAxisScale(localMax[1]) + ')');
                        focus.select('text').text(formatter(localMax[0]) + ' ' + xUnits);
                    }
                };

                function resize() {
                    if (! points)
                        return;
                    $scope.width = parseInt(select().style('width')) - $scope.margin.left - $scope.margin.right;
                    $scope.height = ASPECT_RATIO * $scope.width;
                    select('svg')
                        .attr('width', $scope.width + $scope.margin.left + $scope.margin.right)
                        .attr('height', $scope.height + $scope.margin.top + $scope.margin.bottom);
                    ticks(xAxis, $scope.width, true);
                    ticks(xAxisGrid, $scope.width, true);
                    ticks(yAxis, $scope.height, false);
                    ticks(yAxisGrid, $scope.height, false);
                    xAxisScale.range([-0.5, $scope.width - 0.5]);
                    yAxisScale.range([$scope.height - 0.5, 0 - 0.5]).nice();
                    xAxisGrid.tickSize(-$scope.height);
                    yAxisGrid.tickSize(-$scope.width);
                    select('.x.axis').call(xAxis);
                    select('.x.axis.grid').call(xAxisGrid); // tickLine == gridline
                    select('.y.axis').call(yAxis);
                    select('.y.axis.grid').call(yAxisGrid);
                    select('.line').attr('d', graphLine);
                    return [$scope.width, $scope.height];
                }

                function select(selector) {
                    var e = d3.select($scope.element);
                    return selector ? e.select(selector) : e;
                }

                function sliderChanged(ev) {
                    if (! points)
                        return;
                    function computePoint(value) {
                        return Math.round($scope.xRange[0] + (value / 100) * ($scope.xRange[1] - $scope.xRange[0]));
                    }
                    var xStart = computePoint(ev.value[0]);
                    var xEnd = computePoint(ev.value[1]);
                    xAxisScale.domain([xStart, xEnd]);

                    var yMin, yMax;
                    for (var i = 0; i < points.length; i++) {
                        var p = points[i];
                        if (p[0] < xStart)
                            continue;
                        if (p[0] > xEnd)
                            break;
                        if (yMin === undefined || yMin > p[1])
                            yMin = p[1];
                        if (yMax === undefined || yMax < p[1])
                            yMax = p[1];
                    }
                    yAxisScale.domain([yMin, yMax]);
                    resize();
                }

                $scope.windowResize = debounce(function() {
                    resize();
                    $scope.$apply();
                }, 250);

                $scope.init = function() {
                    formatter = d3.format(',.0f');
                    select('svg').attr('height', INITIAL_HEIGHT);
                    $scope.slider = $(select('.srw-plot2d-slider').node()).slider();
                    $scope.slider.on('slide', sliderChanged);
                    $(window).resize($scope.windowResize);
                    xAxisScale = d3.scale.linear();
                    yAxisScale = d3.scale.linear();
                    xAxis = createAxis(xAxisScale, 'bottom');
                    xAxisGrid = createAxis(xAxisScale, 'bottom');
                    yAxis = createExponentialAxis(yAxisScale, 'left');
                    yAxisGrid = createAxis(yAxisScale, 'left');
                    graphLine = d3.svg.line()
                        .x(function(d) {return xAxisScale(d[0])})
                        .y(function(d) {return yAxisScale(d[1])});
                    var focus = select('.focus');
                    select('.overlay')
                        .on('mouseover', function() { focus.style('display', null); })
                        .on('mouseout', function() { focus.style('display', 'none'); })
                        .on('mousemove', mouseMove);
                };

                $scope.load = function(json) {
                    var xPoints = linspace(json.x_range[0], json.x_range[1], json.points.length);
                    points = d3.zip(xPoints, json.points);
                    $scope.xRange = json.x_range;
                    xUnits = json.x_units;
                    xAxisScale.domain([json.x_range[0], json.x_range[1]]);
                    yAxisScale.domain([d3.min(json.points), d3.max(json.points)]);
                    select('.y-axis-label').text(json.y_label);
                    select('.x-axis-label').text(json.x_label);
                    select('.main-title').text(json.title);
                    select('.line').datum(points);
                    var dimensions = resize();
                    xPeakValues = computePeaks(json, dimensions, xPoints);
                };
            },
            link: function link(scope, element) {
                linkPlot(scope, element, d3Service, appState);
                scope.$on('$destroy', function() {
                    scope.element = null;
                    $(window).off('resize', scope.windowResize);
                    $('.overlay').off();
                    scope.slider.off();
                    scope.slider.data('slider').picker.off();
                    scope.slider.remove();
                });
            },
        };
    });

    app.directive('plot3d', function(appState, d3Service) {
        return {
            restrict: 'A',
            scope: {
                modelName: '@',
            },
            templateUrl: '/static/html/plot3d.html?20150728',
            controller: function($scope) {

                $scope.margin = 50;
                $scope.bottomPanelMargin = {top: 10, bottom: 30};
                $scope.rightPanelMargin = {left: 10, right: 40};
                // will be set to the correct size in resize()
                $scope.canvasSize = 0;
                $scope.rightPanelWidth = $scope.bottomPanelHeight = 50;

                var bottomPanelCutLine, bottomPanelXAxis, bottomPanelYAxis, bottomPanelYScale, canvas, ctx, heatmap, mainXAxis, mainYAxis, mouseRect, rightPanelCutLine, rightPanelXAxis, rightPanelYAxis, rightPanelXScale, rightPanelXScale, xAxisScale, xIndexScale, xValueMax, xValueMin, xValueRange, yAxisScale, yIndexScale, yValueMax, yValueMin, yValueRange;

                function drawBottomPanelCut() {
                    var bBottom = yIndexScale(yAxisScale.domain()[0]);
                    var yTop = yIndexScale(yAxisScale.domain()[1]);
                    var yv = Math.floor(bBottom + (yTop - bBottom + 1)/2);
                    var row = heatmap[yv];
                    var xvMin = xIndexScale.domain()[0];
                    var xvMax = xIndexScale.domain()[1];
                    var xiMin = Math.ceil(xIndexScale(xvMin));
                    var xiMax = Math.floor(xIndexScale(xvMax));
                    var xvRange = xValueRange.slice(xiMin, xiMax + 1);
                    var zvRange = row.slice(xiMin, xiMax + 1);
                    select('.bottom-panel path')
                        .datum(d3.zip(xvRange, zvRange))
                        .attr('d', bottomPanelCutLine);
                }

                function drawRightPanelCut() {
                    var yvMin = yIndexScale.domain()[0];
                    var yvMax = yIndexScale.domain()[1];
                    var yiMin = Math.ceil(yIndexScale(yvMin));
                    var yiMax = Math.floor(yIndexScale(yvMax));
                    var xLeft = xIndexScale(xAxisScale.domain()[0]);
                    var xRight = xIndexScale(xAxisScale.domain()[1]);
                    var xv = Math.floor(xLeft + (xRight - xLeft + 1)/2);
                    var data = heatmap.slice(yiMin, yiMax + 1).map(function (v, i) {
                        return [yValueRange[i], v[xv]];
                    });
                    select('.right-panel path')
                        .datum(data)
                        .attr('d', rightPanelCutLine);
                }

                function initDraw(json, zmin, zmax) {
                    var color = d3.scale.linear()
                        .domain([zmin, zmax])
                        .range(['#333', '#fff']);
                    var xmax = json.x_range.length - 1;
                    var ymax = json.y_range.length - 1;
                    // Compute the pixel colors; scaled by CSS.
                    var img = ctx.createImageData(json.x_range.length, json.y_range.length);
                    for (var yi = 0, p = -1; yi <= ymax; ++yi) {
	                for (var xi = 0; xi <= xmax; ++xi) {
	                    var c = d3.rgb(color(heatmap[yi][xi]));
	                    img.data[++p] = c.r;
	                    img.data[++p] = c.g;
	                    img.data[++p] = c.b;
	                    img.data[++p] = 255;
	                }
                    }
                    // Keeping pixels as nearest neighbor (as anti-aliased as we can get
                    // without doing more programming) allows us to see how the marginals
                    // line up when zooming in a lot.
                    ctx.mozImageSmoothingEnabled = false;
                    ctx.imageSmoothingEnabled = false;
                    ctx.msImageSmoothingEnabled = false;
                    ctx.imageSmoothingEnabled = false;
                    ctx.putImageData(img, 0, 0);
                    $scope.imageObj.src = canvas.node().toDataURL();
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
                                //		tx = 0;
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

                    ctx.clearRect(0, 0, $scope.canvasSize, $scope.canvasSize);
                    if (s == 1) {
                        tx = 0;
                        ty = 0;
                        $scope.zoom.translate([tx, ty]);
                    }
                    ctx.drawImage(
                        $scope.imageObj,
                        tx*$scope.imageObj.width/$scope.canvasSize,
                        ty*$scope.imageObj.height/$scope.canvasSize,
                        $scope.imageObj.width*s,
                        $scope.imageObj.height*s
                    );
                    drawBottomPanelCut();
                    drawRightPanelCut();
                    select('.bottom-panel .x.axis').call(bottomPanelXAxis);
                    select('.bottom-panel .y.axis').call(bottomPanelYAxis);
                    select('.right-panel .x.axis').call(rightPanelXAxis);
                    select('.right-panel .y.axis').call(rightPanelYAxis);
                    select('.x.axis.grid').call(mainXAxis);
                    select('.y.axis.grid').call(mainYAxis);
                }

                function resize() {
                    if (! heatmap)
                        return;
                    var width = parseInt(select().style('width')) - 2 * $scope.margin;
                    var canvasSize = 2 * (width - $scope.rightPanelMargin.left - $scope.rightPanelMargin.right) / 3;
                    $scope.canvasSize = canvasSize;
                    $scope.bottomPanelHeight = 2 * canvasSize / 5 + $scope.bottomPanelMargin.top + $scope.bottomPanelMargin.bottom;
                    $scope.rightPanelWidth = canvasSize / 2 + $scope.rightPanelMargin.left + $scope.rightPanelMargin.right;
                    ticks(rightPanelXAxis, $scope.rightPanelWidth, true);
                    ticks(rightPanelYAxis, canvasSize, false);
                    ticks(bottomPanelXAxis, canvasSize, true);
                    ticks(bottomPanelYAxis, $scope.bottomPanelHeight, false);
                    ticks(mainXAxis, canvasSize, false);
                    ticks(mainYAxis, canvasSize, false);
                    xAxisScale.range([0, canvasSize - 1]);
                    yAxisScale.range([canvasSize - 1, 0]);
                    bottomPanelYScale.range([$scope.bottomPanelHeight - $scope.bottomPanelMargin.top - $scope.bottomPanelMargin.bottom - 1, 0]).nice();
                    rightPanelXScale.range([0, $scope.rightPanelWidth - $scope.rightPanelMargin.left - $scope.rightPanelMargin.right]).nice();
                    mainXAxis.tickSize(- canvasSize - $scope.bottomPanelHeight + $scope.bottomPanelMargin.bottom); // tickLine == gridline
                    mainYAxis.tickSize(- canvasSize - $scope.rightPanelWidth + $scope.rightPanelMargin.right); // tickLine == gridline
                    $scope.zoom.center([canvasSize / 2, canvasSize / 2])
                        .x(xAxisScale.domain([xValueMin, xValueMax]))
                        .y(yAxisScale.domain([yValueMin, yValueMax]));
                    select('.mouse-rect').call($scope.zoom);
                    refresh();
                };

                function select(selector) {
                    var e = d3.select($scope.element);
                    return selector ? e.select(selector) : e;
                }

                $scope.init = function() {
                    select('svg').attr('height', INITIAL_HEIGHT);
                    xAxisScale = d3.scale.linear();
                    xIndexScale = d3.scale.linear();
                    yAxisScale = d3.scale.linear();
                    yIndexScale = d3.scale.linear();
                    bottomPanelYScale = d3.scale.linear();
                    rightPanelXScale = d3.scale.linear();
                    mainXAxis = createAxis(xAxisScale, 'bottom');
                    mainYAxis = createAxis(yAxisScale, 'left');
                    bottomPanelXAxis = createAxis(xAxisScale, 'bottom');
                    bottomPanelYAxis = createExponentialAxis(bottomPanelYScale, 'left');
                    rightPanelXAxis = createExponentialAxis(rightPanelXScale, 'bottom');
                    rightPanelYAxis = createAxis(yAxisScale, 'right');
                    $scope.zoom = d3.behavior.zoom()
                        .scaleExtent([1, 10])
                        .on('zoom', refresh);
                    canvas = select('canvas');
                    mouseRect = select('.mouse-rect');
                    ctx = canvas.node().getContext('2d');
                    $scope.imageObj = new Image();
                    $scope.imageObj.onload = function() {
                        // important - the image may not be ready initially
                        refresh();
                    };
                    bottomPanelCutLine = d3.svg.line()
                        .x(function(d) {return xAxisScale(d[0])})
                        .y(function(d) {return bottomPanelYScale(d[1])});
                    rightPanelCutLine = d3.svg.line()
                        .y(function(d) { return yAxisScale(d[0])})
                        .x(function(d) { return rightPanelXScale(d[1])});
                    $(window).resize($scope.windowResize);
                };

                $scope.load = function(json) {
                    heatmap = [];
                    var xmax = json.x_range.length - 1;
                    var ymax = json.y_range.length - 1;
                    xValueMin = json.x_range[0];
                    xValueMax = json.x_range[xmax];
                    xValueRange = json.x_range.slice(0);
                    yValueMin = json.y_range[0];
                    yValueMax = json.y_range[ymax];
                    yValueRange = json.y_range.slice(0);
                    xIndexScale.range([0, xmax]);
                    yIndexScale.range([0, ymax]);
                    canvas.attr('width', json.x_range.length)
                        .attr('height', json.y_range.length);
                    select('.main-title').text(json.title);
                    select('.x-axis-label').text(json.x_label);
                    select('.y-axis-label').text(json.y_label);
                    select('.z-axis-label').text(json.z_label);
                    xAxisScale.domain([xValueMin, xValueMax]);
                    xIndexScale.domain([xValueMin, xValueMax]);
                    yAxisScale.domain([yValueMin, yValueMax]);
                    yIndexScale.domain([yValueMin, yValueMax]);

                    var zmin = json.z_matrix[0][0]
                    var zmax = json.z_matrix[0][0]
                    for (var yi = 0; yi <= ymax; ++yi) {
                        // flip to match the canvas coordinate system (origin: top left)
                        // matplotlib is bottom left
                        heatmap[ymax - yi] = [];
                        for (var xi = 0; xi <= xmax; ++xi) {
	                    var zi = json.z_matrix[yi][xi];
	                    heatmap[ymax - yi][xi] = zi;
	                    if (zmax < zi)
	                        zmax = zi;
	                    else if (zmin > zi)
	                        zmin = zi;
                        }
                    }
                    bottomPanelYScale.domain([zmin, zmax]);
                    rightPanelXScale.domain([zmax, zmin]);
                    initDraw(json, zmin, zmax);
                    resize();
                };

                $scope.windowResize = debounce(function() {
                    resize();
                    $scope.$apply();
                }, 250);
            },
            link: function link(scope, element) {
                linkPlot(scope, element, d3Service, appState);
                scope.$on('$destroy', function() {
                    scope.element = null;
                    $(window).off('resize', scope.windowResize);
                    scope.zoom.on('zoom', null);
                    scope.imageObj.onload = null;
                });
            },
        };
    });
})();
