'use strict';

SIREPO.app.factory('plotting', function(appState, d3Service, frameCache, panelState, $timeout, $window) {

    var INITIAL_HEIGHT = 400;

    function cleanNumber(v) {
        v = v.replace(/\.0+(\D+)/, '$1');
        v = v.replace(/(\.\d)0+(\D+)/, '$1$2');
        return v;
    }

    // Returns a function, that, as long as it continues to be invoked, will not
    // be triggered. The function will be called after it stops being called for
    // N milliseconds. If `immediate` is passed, trigger the function on the
    // leading edge, instead of the trailing.
    // taken from http://davidwalsh.name/javascript-debounce-function
    function debounce(func, wait) {
        var timeout;
        return function() {
            var context = this, args = arguments;
            var later = function() {
                timeout = null;
                func.apply(context, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function initAnimation(scope) {
        scope.prevFrameIndex = -1;
        scope.isPlaying = false;
        var requestData = function() {
            if (! scope.hasFrames())
                return;
            var index = frameCache.getCurrentFrame(scope.modelName);
            if (frameCache.getCurrentFrame(scope.modelName) == scope.prevFrameIndex)
                return;
            scope.prevFrameIndex = index;
            frameCache.getFrame(scope.modelName, index, scope.isPlaying, function(index, data) {
                if (scope.element) {
                    if (data.error) {
                        panelState.setError(scope.modelName, data.error);
                        return;
                    }
                    scope.load(data);
                }
                if (scope.isPlaying)
                    scope.advanceFrame(1);
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
            if (scope.modelChanged)
                scope.modelChanged();
            requestData();
        };
        scope.hasFrames = function() {
            return frameCache.isLoaded() && frameCache.getFrameCount(scope.modelName) > 0;
        };
        scope.hasManyFrames = function() {
            if (SIREPO.APP_NAME == 'srw')
                return false;
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
            if (scope.isPlaying)
                scope.advanceFrame(1);
        };
        if (scope.clearData)
            scope.$on('framesCleared', scope.clearData);
        scope.$on('modelsLoaded', requestData);
        scope.$on('framesLoaded', function(event, oldFrameCount) {
            if (scope.prevFrameIndex < 0)
                scope.firstFrame();
            else if (oldFrameCount === 0)
                scope.lastFrame();
            else if (scope.prevFrameIndex > frameCache.getFrameCount(scope.modelName))
                scope.firstFrame();
            // go to the next last frame, if the current frame was the previous last frame
            else if (frameCache.getCurrentFrame(scope.modelName) == oldFrameCount - 1)
                scope.lastFrame();
        });
        return requestData;
    }

    return {

        createAxis: createAxis,

        createExponentialAxis: function(scale, orient) {
            return createAxis(scale, orient)
            // this causes a 'number of fractional digits' error in MSIE
            //.tickFormat(d3.format('e'))
                .tickFormat(function (value) {
                    if (value)
                        return cleanNumber(value.toExponential(2));
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

        fixFormat: function(scope, axis) {
            var format = d3.format('.3s');
            // amounts near zero may appear as NNNz, change them to 0
            return function(n) {
                var v = format(n);
                if ((v && v.indexOf('z') > 0) || v == '0.00')
                    return '0';
                v = cleanNumber(v);
                var units = scope[axis + 'units'] || '';
                return v + units;
            };
        },

        initialHeight: function(scope) {
            return scope.isAnimation ? 1 : INITIAL_HEIGHT;
        },

        linkPlot: function(scope, element) {
            d3Service.d3().then(function(d3) {
                scope.element = element[0];
                scope.isAnimation = scope.modelName.indexOf('Animation') >= 0;
                var requestData;

                if (scope.isAnimation)
                    requestData = initAnimation(scope);
                else if (scope.isClientOnly)
                    requestData = function() {};
                else {
                    requestData = function() {
                        //TODO(pjm): timeout is a hack to give time for invalid reports to be destroyed
                        $timeout(function() {
                            if (! scope.element)
                                return;
                            panelState.requestData(scope.modelName, function(data) {
                                if (scope.element)
                                    scope.load(data);
                            });
                        }, 50);
                    };
                }

                scope.windowResize = debounce(function() {
                    scope.resize();
                    scope.$apply();
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
                        if (scope.modelChanged)
                            scope.modelChanged();
                        panelState.clear(scope.modelName);
                        requestData();
                    });
                scope.isLoading = function() {
                    if (scope.isAnimation)
                        return false;
                    return panelState.isLoading(scope.modelName);
                };
                $($window).resize(scope.windowResize);
                scope.init();
                if (appState.isLoaded())
                    requestData();
            });
        },

        linspace: function(start, stop, nsteps) {
            var delta = (stop - start) / (nsteps - 1);
            return d3.range(start, stop, delta).slice(0, nsteps);
        },

        ticks: function(axis, width, isHorizontalAxis) {
            var spacing = isHorizontalAxis ? 60 : 40;
            var n = Math.max(Math.round(width / spacing), 2);
            axis.ticks(n);
        },
    };

    function createAxis(scale, orient) {
        return d3.svg.axis()
            .scale(scale)
            .orient(orient);
    }
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

SIREPO.app.directive('plot2d', function(plotting) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/plot2d.html?' + SIREPO.APP_VERSION,
        controller: function($scope) {

            var ASPECT_RATIO = 4.0 / 7;
            $scope.margin = {top: 50, right: 20, bottom: 50, left: 70};
            $scope.width = $scope.height = 0;
            $scope.dataCleared = true;
            var focusIndex, formatter, ordinate_formatter, graphLine, points, xAxis, xAxisGrid, xAxisScale, xDomain, yAxis, yAxisGrid, yAxisScale, yDomain, zoom;
            var keyListener = false;
            var defaultCircleSize = null;

            function onClick() {
                /*jshint validthis: true*/
                if (! points)
                    return;
                var mouseX = d3.mouse(this)[0];
                var xMin = xAxisScale.invert(mouseX - 10);
                var xMax = xAxisScale.invert(mouseX + 10);
                var domain = xAxisScale.domain();
                if (xMin < domain[0])
                    xMin = domain[0];
                if (xMax > domain[1])
                    xMax = domain[1];

                focusIndex = -1;
                var maxPoint;
                for (var i = 0; i < points.length; i++) {
                    var p = points[i];
                    if (p[0] > xMax)
                        break;
                    if (p[0] < xMin)
                        continue;
                    if (! maxPoint || p[1] > maxPoint[1]) {
                        maxPoint = p;
                        focusIndex = i;
                    }
                }
                if (maxPoint)
                    showFocusPoint(true);
            }

            function onKeyDown() {
                if (! points || focusIndex < 0)
                    return;
                var keyCode = d3.event.keyCode;
                if (keyCode == 37) // left
                    moveFocus(-1);
                else if (keyCode == 39) // right
                    moveFocus(1);
            }

            function formatValue(v) {
                if (v < 1 || v > 1000000)
                    return ordinate_formatter(v);
                return formatter(v);
            }

            function showFocusPoint(isMainFocus) {
                var p = points[focusIndex];
                var domain = xAxisScale.domain();
                if (p[0] < domain[0] || p[0] > domain[1]) {
                    select('.focus').style('display', 'none');
                    select('.focus-text').text('');
                    return;
                }
                var focus = select('.focus');
                focus.style('display', null);
                var circle = select('circle');
                if (isMainFocus) {
                    if (! defaultCircleSize)
                        defaultCircleSize = circle.attr('r');
                    circle.attr('r', defaultCircleSize);
                }
                else {
                    circle.attr('r', defaultCircleSize - 2);
                }
                focus.attr('transform', 'translate(' + xAxisScale(p[0]) + ',' + yAxisScale(p[1]) + ')');
                select('.focus-text').text('[' + formatValue(p[0]) + ', ' + formatValue(p[1]) + ']');
            }

            function moveFocus(step) {
                var newIndex = focusIndex + step;
                if (newIndex < 0 || newIndex >= points.length)
                    return;
                focusIndex = newIndex;
                showFocusPoint(false);
            }

            function refresh() {
                if (d3.event && d3.event.translate) {
                    var tx = zoom.translate()[0];
                    var ty = zoom.translate()[1];
                    var xdom = xAxisScale.domain();

                    if ((xdom[1] - xdom[0]) >= (xDomain[1] - xDomain[0])) {
                        select('.overlay').attr('class', 'overlay mouse-zoom');
                        xAxisScale.domain(xDomain);
                        yAxisScale.domain(yDomain);
                        xdom = xAxisScale.domain();
                        zoom.scale(1);
                        tx = 0;
                        ty = 0;
                    }
                    else {
                        select('.overlay').attr('class', 'overlay mouse-move');
                        if (xdom[0] < xDomain[0]) {
                            xAxisScale.domain([xDomain[0], xdom[1] - xdom[0] + xDomain[0]]);
                            xdom = xAxisScale.domain();
                            tx = 0;
                        }
                        if (xdom[1] > xDomain[1]) {
                            xdom[0] -= xdom[1] - xDomain[1];
                            xAxisScale.domain([xdom[0], xDomain[1]]);
                            xdom = xAxisScale.domain();
                            tx = (xDomain[0] - xdom[0]) * $scope.width / (xDomain[1] - xDomain[0]) * zoom.scale();
                        }

                        var ydom;
                        for (var i = 0; i < points.length; i++) {
                            var d = points[i];
                            if (d[0] > xdom[1])
                                break;
                            if (d[0] > xdom[0]) {
                                if (ydom) {
                                    if (d[1] < ydom[0])
                                        ydom[0] = d[1];
                                    else if (d[1] > ydom[1])
                                        ydom[1] = d[1];
                                }
                                else {
                                    ydom = [d[1], d[1]];
                                }
                            }
                        }
                        if (ydom && ydom[0] != ydom[1])
                            yAxisScale.domain(ydom).nice();
                    }
                    zoom.translate([tx, ty]);
                }
                select('.x.axis').call(xAxis);
                select('.x.axis.grid').call(xAxisGrid); // tickLine == gridline
                select('.y.axis').call(yAxis);
                select('.y.axis.grid').call(yAxisGrid);
                select('.line').attr('d', graphLine);
                if (focusIndex >= 0)
                    showFocusPoint(true);
            }

            $scope.resize = function() {
                var width = parseInt(select().style('width')) - $scope.margin.left - $scope.margin.right;
                if (! points || isNaN(width))
                    return;
                $scope.width = width;
                $scope.height = ASPECT_RATIO * $scope.width;
                select('svg')
                    .attr('width', $scope.width + $scope.margin.left + $scope.margin.right)
                    .attr('height', $scope.height + $scope.margin.top + $scope.margin.bottom);
                plotting.ticks(xAxis, $scope.width, true);
                plotting.ticks(xAxisGrid, $scope.width, true);
                plotting.ticks(yAxis, $scope.height, false);
                plotting.ticks(yAxisGrid, $scope.height, false);
                xAxisScale.range([-0.5, $scope.width - 0.5]);
                yAxisScale.range([$scope.height - 0.5, 0 - 0.5]).nice();
                xAxisGrid.tickSize(-$scope.height);
                yAxisGrid.tickSize(-$scope.width);
                zoom.x(xAxisScale);
                select('.overlay').call(zoom).on('dblclick.zoom', null);
                refresh();
            };

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            $scope.clearData = function() {
                $scope.dataCleared = true;
            };

            $scope.init = function() {
                formatter = d3.format('.2f');
                ordinate_formatter = d3.format('.3e');
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
                select('.overlay')
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
                    .on('click', onClick)
                    .on('dblclick', function copyToClipboard() {
                        var focus_text = select('.focus-text');
                        var focus_hint = select('.focus-hint');
                        var $temp = $('<input>');
                        $('body').append($temp);
                        $temp.val(focus_text.text()).select();
                        try {
                            document.execCommand('copy');
                            focus_hint.style('display', null);
                            focus_hint.text('Copied to clipboard');
                            setTimeout(function () {
                                focus_hint.style('display', 'none');
                            }, 1000);
                        } catch(e) {}
                        $temp.remove();
                    });
                zoom = d3.behavior.zoom().on('zoom', refresh);
            };

            $scope.load = function(json) {
                focusIndex = -1;
                select('.focus').style('display', 'none');
                select('.focus-text').text('');
                $scope.dataCleared = false;
                var xPoints = json.x_points
                    ? json.x_points
                    : plotting.linspace(json.x_range[0], json.x_range[1], json.points.length);
                points = d3.zip(xPoints, json.points);
                $scope.xRange = json.x_range;
                xAxisScale.domain([json.x_range[0], json.x_range[1]]);
                xDomain = xAxisScale.domain();
                yAxisScale.domain([d3.min(json.points), d3.max(json.points)]);
                yDomain = yAxisScale.domain();
                select('.y-axis-label').text(json.y_label);
                select('.x-axis-label').text(json.x_label);
                select('.main-title').text(json.title);
                select('.line').datum(points);
                $scope.resize();
            };

            $scope.destroy = function() {
                zoom.on('zoom', null);
                $('.overlay').off();
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('plot3d', function(plotting) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/plot3d.html?' + SIREPO.APP_VERSION,
        controller: function($scope) {

            $scope.margin = 50;
            $scope.bottomPanelMargin = {top: 10, bottom: 30};
            $scope.rightPanelMargin = {left: 10, right: 40};
            // will be set to the correct size in resize()
            $scope.canvasSize = 0;
            $scope.rightPanelWidth = $scope.bottomPanelHeight = 50;
            $scope.dataCleared = true;

            var bottomPanelCutLine, bottomPanelXAxis, bottomPanelYAxis, bottomPanelYScale, canvas, ctx, heatmap, mainXAxis, mainYAxis, mouseRect, rightPanelCutLine, rightPanelXAxis, rightPanelYAxis, rightPanelXScale, xAxisScale, xIndexScale, xValueMax, xValueMin, xValueRange, yAxisScale, yIndexScale, yValueMax, yValueMin, yValueRange;
            function drawBottomPanelCut() {
                var bBottom = yIndexScale(yAxisScale.domain()[0]);
                var yTop = yIndexScale(yAxisScale.domain()[1]);
                var yv = Math.floor(bBottom + (yTop - bBottom + 1)/2) + 1;
                var row = heatmap[yValueRange.length - yv];
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
                    return [yValueRange[yiMax - i], v[xv]];
                });
                select('.right-panel path')
                    .datum(data)
                    .attr('d', rightPanelCutLine);
            }

            function initDraw(zmin, zmax) {
                var color = d3.scale.linear()
                    .domain([zmin, zmax])
                    .range(['#333', '#fff']);
                var xmax = xValueRange.length - 1;
                var ymax = yValueRange.length - 1;

                // Compute the pixel colors; scaled by CSS.
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

            $scope.resize = function() {
                var width = parseInt(select().style('width')) - 2 * $scope.margin;
                if (! heatmap || isNaN(width))
                    return;
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
                bottomPanelYScale.range([$scope.bottomPanelHeight - $scope.bottomPanelMargin.top - $scope.bottomPanelMargin.bottom - 1, 0]).nice();
                rightPanelXScale.range([0, $scope.rightPanelWidth - $scope.rightPanelMargin.left - $scope.rightPanelMargin.right]).nice();
                mainXAxis.tickSize(- canvasSize - $scope.bottomPanelHeight + $scope.bottomPanelMargin.bottom); // tickLine == gridline
                mainYAxis.tickSize(- canvasSize - $scope.rightPanelWidth + $scope.rightPanelMargin.right); // tickLine == gridline
                $scope.zoom.x(xAxisScale.domain([xValueMin, xValueMax]))
                    .y(yAxisScale.domain([yValueMin, yValueMax]));
                select('.mouse-rect').call($scope.zoom);
                refresh();
            };

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            $scope.clearData = function() {
                $scope.dataCleared = true;
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
                    .x(function(d) {return xAxisScale(d[0]);})
                    .y(function(d) {return bottomPanelYScale(d[1]);});
                rightPanelCutLine = d3.svg.line()
                    .y(function(d) { return yAxisScale(d[0]);})
                    .x(function(d) { return rightPanelXScale(d[1]);});
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
                xIndexScale.range([0, xmax]);
                yIndexScale.range([0, ymax]);
                canvas.attr('width', xValueRange.length)
                    .attr('height', yValueRange.length);
                select('.main-title').text(json.title);
                select('.x-axis-label').text(plotting.extractUnits($scope, 'x', json.x_label));
                select('.y-axis-label').text(plotting.extractUnits($scope, 'y', json.y_label));
                select('.z-axis-label').text(json.z_label);
                xAxisScale.domain([xValueMin, xValueMax]);
                xIndexScale.domain([xValueMin, xValueMax]);
                yAxisScale.domain([yValueMin, yValueMax]);
                yIndexScale.domain([yValueMin, yValueMax]);
                var zmin = json.z_matrix[0][0];
                var zmax = json.z_matrix[0][0];

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
                //TODO(pjm): for now, we always want the lower range to be 0
                if (zmin > 0)
                    zmin = 0;
                bottomPanelYScale.domain([zmin, zmax]);
                rightPanelXScale.domain([zmax, zmin]);
                initDraw(zmin, zmax);
                $scope.resize();
            };

            $scope.destroy = function() {
                $scope.zoom.on('zoom', null);
                $scope.imageObj.onload = null;
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
        templateUrl: '/static/html/heatmap.html?' + SIREPO.APP_VERSION,
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
                    if (v > 1)
                        v = 1;
                    else if (v < 0)
                        v = 0;
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
                // Keeping pixels as nearest neighbor (as anti-aliased as we can get
                // without doing more programming) allows us to see how the marginals
                // line up when zooming in a lot.
                ctx.mozImageSmoothingEnabled = false;
                ctx.imageSmoothingEnabled = false;
                ctx.msImageSmoothingEnabled = false;
                ctx.imageSmoothingEnabled = false;
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
                if (! heatmap || heatmap[0].length <= 2)
                    return;
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
                select('.x.axis').call(xAxis);
                select('.y.axis').call(yAxis);
            }

            $scope.resize = function() {
                var canvasSize = parseInt(select().style('width')) - $scope.margin.left - $scope.margin.right;
                if (! heatmap || isNaN(canvasSize))
                    return;
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
                xAxis.tickFormat(plotting.fixFormat($scope, 'x'));
                yAxis = plotting.createAxis(yAxisScale, 'left');
                yAxis.tickFormat(plotting.fixFormat($scope, 'y'));
                $scope.zoom = d3.behavior.zoom()
                    .scaleExtent([1, 10])
                    .on('zoom', refresh);
                canvas = select('canvas');
                mouseRect = select('.mouse-rect');
                mouseRect.on('mousemove', mouseMove);
                ctx = canvas.node().getContext('2d');
                $scope.imageObj = new Image();
                $scope.imageObj.onload = function() {
                    // important - the image may not be ready initially
                    refresh();
                };
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
                        if (zmax < zi)
                            zmax = zi;
                        else if (zmin > zi)
                            zmin = zi;
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
                if ($scope.zoom)
                    $scope.zoom.on('zoom', null);
                if ($scope.imageObj)
                    $scope.imageObj.onload = null;
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('lattice', function(plotting, appState, $timeout, $window) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/lattice.html?' + SIREPO.APP_VERSION,
        controller: function($scope) {
            //TODO(pjm): need a way to get at the controller for info, or provide in a common service.
            var p = $scope;
            while (p.$parent) {
                p = p.$parent;
                if (p.lattice) {
                    $scope.latticeController = p.lattice;
                    break;
                }
            }
            $scope.isClientOnly = true;
            $scope.margin = 3;
            $scope.width = 1;
            $scope.height = 1;
            $scope.scale = 1;
            $scope.xOffset = 0;
            $scope.yOffset = 0;
            $scope.zoomScale = 1;
            $scope.panTranslate = [0, 0];
            $scope.markerWidth = 1;
            $scope.markerUnits = '';

            var emptyList = [];
            $scope.items = [];
            $scope.svgGroups = [];
            $scope.svgBounds = null;
            var picTypeCache = null;

            function applyGroup(items, pos) {
                var group = {
                    rotate: pos.angle,
                    rotateX: pos.x,
                    rotateY: pos.y,
                    items: [],
                };
                $scope.svgGroups.push(group);
                var x = 0;
                var oldRadius = pos.radius;
                var newAngle = 0;
                var maxHeight = 0;

                for (var i = 0; i < items.length; i++) {
                    var item = items[i];
                    var picType = $scope.getPicType(item.type);
                    var length = parseFloat(item.l || item.xmax || 0);
                    if (picType == 'zeroLength')
                        length = 0;
                    var elRadius = parseFloat(item.rx || item.x_max || 0);
                    pos.length += length;
                    if (length < 0) {
                        // negative length, back up
                        x += length;
                        length = 0;
                    }
                    //TODO(pjm): need to refactor picType processing
                    if (picType == 'bend') {
                        var radius = length / 2;
                        var angle = parseFloat(item.angle || item.kick || item.hkick || 0);
                        maxHeight = Math.max(maxHeight, length);
                        var height = 0.75;
                        var enter = [pos.radius + pos.x + x, pos.y];
                        //TODO(pjm): if angle is arc length, need to convert it to a rendered length
                        // if (length > 0 && angle != 0) {
                        //     var noArcLength = Math.abs(2 * Math.sin(angle / 2) * length / angle);
                        //     length = noArcLength;
                        // }
                        if (length === 0) {
                            length = 0.1;
                            enter[0] -= 0.05;
                        }
                        var enterEdge = parseFloat(item.e1 || 0);
                        var exitEdge = parseFloat(item.e2 || 0);
                        if (item.type == 'RBEN') {
                            enterEdge = 0;
                            exitEdge = 0;
                        }
                        var exit = [enter[0] + length / 2 + Math.cos(angle) * length / 2,
                                    pos.y + Math.sin(angle) * length / 2];
                        var exitAngle = exitEdge - angle;
                        group.items.push({
                            picType: picType,
                            element: item,
                            color: $scope.getPicColor(item.type, 'blue'),
                            points: [
                                [enter[0] - Math.sin(-enterEdge) * height / 2,
                                 enter[1] - Math.cos(-enterEdge) * height / 2],
                                [enter[0] + Math.sin(-enterEdge) * height / 2,
                                 enter[1] + Math.cos(-enterEdge) * height / 2],
                                [exit[0] + Math.sin(exitAngle) * height / 2,
                                 exit[1] + Math.cos(exitAngle) * height / 2],
                                [exit[0] - Math.sin(exitAngle) * height / 2,
                                 exit[1] - Math.cos(exitAngle) * height / 2],
                            ],
                        });
                        x += radius;
                        newAngle = angle * 180 / Math.PI;
                        pos.radius = radius;
                    }
                    else {
                        var groupItem = {
                            picType: picType,
                            element: item,
                            x: pos.radius + pos.x + x,
                            height: 0,
                            width: length,
                        };
                        if (picType == 'watch') {
                            groupItem.height = 1;
                            groupItem.y = pos.y;
                            groupItem.color = $scope.getPicColor(item.type, 'lightgreen');
                        }
                        else if (picType == 'drift') {
                            groupItem.color = $scope.getPicColor(item.type, 'lightgrey');
                            groupItem.height = 0.1;
                            groupItem.y = pos.y - groupItem.height / 2;
                        }
                        else if (picType == 'aperture') {
                            groupItem.color = 'lightgrey';
                            groupItem.apertureColor = $scope.getPicColor(item.type, 'black');
                            groupItem.height = 0.1;
                            groupItem.y = pos.y - groupItem.height / 2;
                            if (groupItem.width === 0) {
                                groupItem.x -= 0.01;
                                groupItem.width = 0.02;
                            }
                            groupItem.opening = elRadius || 0.1;
                        }
                        else if (picType == 'alpha') {
                            var alphaAngle = 40.71;
                            newAngle = 180 - 2 * alphaAngle;
                            if (length < 0.3)
                                groupItem.width = 0.3;
                            groupItem.angle = alphaAngle;
                            groupItem.height = groupItem.width;
                            groupItem.y = pos.y - groupItem.height / 2;
                            length = 0;
                        }
                        else if (picType == 'magnet') {
                            groupItem.height = 0.5;
                            groupItem.y = pos.y - groupItem.height / 2;
                            groupItem.color = $scope.getPicColor(item.type, 'red');
                        }
                        else if (picType == 'undulator') {
                            groupItem.height = 0.25;
                            groupItem.y = pos.y - groupItem.height / 2;
                            groupItem.color = $scope.getPicColor(item.type, 'gray');
                            var periods = Math.round(parseFloat(item.periods || item.poles || 0));
                            if (periods <= 0)
                                periods = Math.round(5 * length);
                            groupItem.blockWidth = groupItem.width / (2 * periods);
                            groupItem.blocks = [];
                            groupItem.blockHeight = 0.03;
                            for (var j = 0; j < 2 * periods; j++) {
                                groupItem.blocks.push([
                                    groupItem.x + j * groupItem.blockWidth,
                                    j % 2
                                        ? groupItem.y + groupItem.height / 4
                                        : groupItem.y + groupItem.height * 3 / 4 - groupItem.blockHeight,
                                ]);
                            }
                        }
                        else if (picType == 'zeroLength' || picType == 'mirror' || (picType == 'rf' && length < 0.005)) {
                            groupItem.color = $scope.getPicColor(item.type, 'black');
                            groupItem.picType = 'zeroLength';
                            groupItem.height = 0.5;
                            groupItem.y = pos.y;
                        }
                        else if (picType == 'rf') {
                            groupItem.height = 0.3;
                            groupItem.y = pos.y;
                            var ovalCount = Math.round(length / (groupItem.height / 2)) || 1;
                            groupItem.ovalWidth = length / ovalCount;
                            groupItem.ovals = [];
                            for (var k = 0; k < ovalCount; k++) {
                                groupItem.ovals.push(groupItem.x + k * groupItem.ovalWidth + groupItem.ovalWidth / 2);
                            }
                            groupItem.color = $scope.getPicColor(item.type, 'gold');
                        }
                        else if (picType == 'recirc') {
                            groupItem.radius = 0.3;
                            groupItem.y = pos.y;
                            groupItem.leftEdge = groupItem.x - groupItem.radius;
                            groupItem.rightEdge = groupItem.x + groupItem.radius;
                            groupItem.color = $scope.getPicColor(item.type, 'lightgreen');
                        }
                        else if (picType == 'lens') {
                            groupItem.height = 0.2;
                            groupItem.width = 0.02;
                            groupItem.x -= 0.01;
                            groupItem.y = pos.y - groupItem.height / 2;
                            groupItem.color = $scope.getPicColor(item.type, 'lightblue');
                        }
                        else if (picType == 'solenoid') {
                            if (length === 0) {
                                groupItem.width = 0.3;
                                groupItem.x -= 0.15;
                            }
                            groupItem.height = groupItem.width;
                            groupItem.y = pos.y - groupItem.height / 2;
                            groupItem.color = $scope.getPicColor(item.type, 'lightblue');
                        }
                        else {
                            groupItem.color = $scope.getPicColor(item.type, 'green');
                            groupItem.height = 0.2;
                            groupItem.y = pos.y - groupItem.height / 2;
                        }
                        maxHeight = Math.max(maxHeight, groupItem.height);
                        //groupItem.x = pos.radius + pos.x + x;
                        group.items.push(groupItem);
                        //console.log(item.type, ' ', [pos.radius + pos.x + x, pos.y - height / 2]);
                        x += length;
                    }
                }
                if (pos.angle === 0) {
                    pos.x += x + oldRadius;
                }
                else {
                    pos.x += Math.sin((90 - pos.angle) * Math.PI / 180) * (x + oldRadius);
                    pos.y += Math.sin(pos.angle * Math.PI / 180) * (x + oldRadius);
                }
                updateBounds(pos.bounds, pos.x, pos.y, Math.max(maxHeight, pos.radius));
                //console.log('bounds: ', pos.bounds);
                pos.angle += newAngle;
            }

            function computePositions() {
                var pos = {
                    x: 0,
                    y: 0,
                    angle: 0,
                    radius: 0,
                    bounds: [0, 0, 0, 0],
                    count: 0,
                    length: 0,
                };
                var explodedItems = explodeItems($scope.items);
                var group = [];
                var groupDone = false;
                for (var i = 0; i < explodedItems.length; i++) {
                    if (groupDone) {
                        applyGroup(group, pos);
                        group = [];
                        groupDone = false;
                    }
                    //var item = $scope.latticeController.elementForId($scope.items[i]);
                    var item = explodedItems[i];
                    var picType = $scope.getPicType(item.type);
                    if (picType != 'drift')
                        pos.count++;
                    if (picType == 'bend' || picType == 'alpha')
                        groupDone = true;
                    group.push(item);
                }
                if (group.length)
                    applyGroup(group, pos);
                $scope.svgBounds = pos.bounds;
                if (explodedItems.length > 0 && 'angle' in explodedItems[explodedItems.length - 1])
                    pos.x += pos.radius;
                return pos;
            }

            //TODO(pjm): will infinitely recurse if beamlines are self-referential
            function explodeItems(items, res, reversed) {
                if (! res)
                    res = [];
                if (reversed)
                    items = items.slice().reverse();
                for (var i = 0; i < items.length; i++) {
                    var id = items[i];
                    var item = $scope.latticeController.elementForId(id);
                    if (item.type)
                        res.push(item);
                    else {
                        explodeItems(item.items, res, id < 0);
                    }
                }
                return res;
            }

            function loadItemsFromBeamline(forceUpdate) {
                var id = $scope.latticeController.activeBeamlineId;
                if (! id) {
                    $scope.items = emptyList;
                    return;
                }
                var beamline = $scope.latticeController.getActiveBeamline();
                if (! forceUpdate && appState.deepEquals(beamline.items, $scope.items)) {
                    return;
                }
                $scope.items = appState.clone(beamline.items);
                $scope.svgGroups = [];
                var pos = computePositions();
                beamline.distance = Math.sqrt(Math.pow(pos.x, 2) + Math.pow(pos.y, 2));
                beamline.length = pos.length;
                beamline.angle = pos.angle * Math.PI / 180;
                beamline.count = pos.count;
                $scope.resize();
            }

            function recalcScaleMarker() {
                //TODO(pjm): use library for this
                $scope.markerUnits = '1 m';
                $scope.markerWidth = $scope.scale * $scope.zoomScale;
                if ($scope.markerWidth < 20) {
                    $scope.markerUnits = '10 m';
                    $scope.markerWidth *= 10;
                    if ($scope.markerWidth < 20) {
                        $scope.markerUnits = '100 m';
                        $scope.markerWidth *= 10;
                    }
                }
                else if ($scope.markerWidth > 200) {
                    $scope.markerUnits = '10 cm';
                    $scope.markerWidth /= 10;
                    if ($scope.markerWidth > 200) {
                        $scope.markerUnits = '1 cm';
                        $scope.markerWidth /= 10;
                    }
                }
            }

            function resetZoomAndPan() {
                $scope.zoomScale = 1;
                $scope.zoom.scale($scope.zoomScale);
                $scope.panTranslate = [0, 0];
                $scope.zoom.translate($scope.panTranslate);
                updateZoomAndPan();
            }

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            function updateBounds(bounds, x, y, buffer) {
                if (x - buffer < bounds[0])
                    bounds[0] = x - buffer;
                if (y - buffer < bounds[1])
                    bounds[1] = y - buffer;
                if (x + buffer > bounds[2])
                    bounds[2] = x + buffer;
                if (y + buffer > bounds[3])
                    bounds[3] = y + buffer;
            }

            function updateZoomAndPan() {
                recalcScaleMarker();
                $scope.container.attr("transform", "translate(" + $scope.panTranslate + ")scale(" + $scope.zoomScale + ")");
            }

            function zoomed() {
                $scope.zoomScale = d3.event.scale;

                if ($scope.zoomScale == 1) {
                    $scope.panTranslate = [0, 0];
                    $scope.zoom.translate($scope.panTranslate);
                }
                else {
                    //TODO(pjm): don't allow translation outside of image boundaries
                    $scope.panTranslate = d3.event.translate;
                }
                updateZoomAndPan();
                $scope.$apply();
            }

            $scope.getPicColor = function(type, defaultColor) {
                return $scope.latticeController.elementColor[type] || defaultColor;
            };

            $scope.getPicType = function(type) {
                if (! picTypeCache) {
                    picTypeCache = {};
                    var elementPic = $scope.latticeController.elementPic;
                    for (var picType in elementPic) {
                        var types = elementPic[picType];
                        for (var i = 0; i < types.length; i++)
                            picTypeCache[types[i]] = picType;
                    }
                }
                return picTypeCache[type];
            };

            $scope.itemClicked = function(item) {
                $scope.latticeController.editElement(item.type, item);
            };

            $scope.resize = function() {
                var width = parseInt(select().style('width'));
                if (isNaN(width))
                    return;
                $scope.width = width;
                $scope.height = $scope.width;
                var windowHeight = $($window).height();
                if ($scope.height > windowHeight / 2.5)
                    $scope.height = windowHeight / 2.5;

                if ($scope.svgBounds) {
                    var w = $scope.svgBounds[2] - $scope.svgBounds[0];
                    var h = $scope.svgBounds[3] - $scope.svgBounds[1];
                    if (w === 0 || h === 0)
                        return;
                    var scaleWidth = $scope.width / w;
                    var scaleHeight = $scope.height / h;
                    var scale = 1;
                    var xOffset = 0;
                    var yOffset = 0;
                    if (scaleWidth < scaleHeight) {
                        scale = scaleWidth;
                        yOffset = ($scope.height - h * scale) / 2;
                    }
                    else {
                        scale = scaleHeight;
                        xOffset = ($scope.width - w * scale) / 2;
                    }
                    $scope.scale = scale;
                    $scope.xOffset = - $scope.svgBounds[0] * scale + xOffset;
                    $scope.yOffset = - $scope.svgBounds[1] * scale + yOffset;
                    recalcScaleMarker();
                }
            };

            $scope.init = function() {
                $scope.zoom = d3.behavior.zoom()
                    .scaleExtent([1, 50])
                    .on('zoom', zoomed);
                select('svg').call($scope.zoom)
                    .on('dblclick.zoom', null);
                $scope.container = select('.s-zoom-plot');
                loadItemsFromBeamline();
            };

            $scope.destroy = function() {
                if ($scope.zoom)
                    $scope.zoom.on('zoom', null);
            };

            $scope.$on('modelChanged', function(e, name) {
                if (name == 'beamlines')
                    loadItemsFromBeamline();
                if (appState.models[name] && appState.models[name]._id) {
                    if ($scope.items.indexOf(appState.models[name]._id) >= 0)
                        loadItemsFromBeamline(true);
                }
            });

            $scope.$on('cancelChanges', function(e, name) {
                if (name == 'elements')
                    loadItemsFromBeamline(true);
            });

            $scope.$on('activeBeamlineChanged', function() {
                loadItemsFromBeamline();
                resetZoomAndPan();
            });
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});
