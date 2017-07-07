'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.appLocalRoutes.visualization = '/visualization/:simulationId';
SIREPO.app.config(function($routeProvider, localRoutesProvider) {
    if (SIREPO.IS_LOGGED_OUT) {
        return;
    }
    var localRoutes = localRoutesProvider.$get();
    $routeProvider
        .when(localRoutes.source, {
            controller: 'WarpVNDSourceController as source',
            templateUrl: '/static/html/warpvnd-source.html' + SIREPO.SOURCE_CACHE_KEY,
        })
        .when(localRoutes.visualization, {
            controller: 'WarpVNDVisualizationController as visualization',
            templateUrl: '/static/html/warpvnd-visualization.html' + SIREPO.SOURCE_CACHE_KEY,
        });
});

SIREPO.app.factory('warpvndService', function(appState, panelState) {
    var self = {};

    function findModelById(name, id) {
        var model = null;
        appState.models[name].forEach(function(m) {
            if (m.id == id) {
                model = m;
            }
        });
        if (! model) {
            throw 'model not found: ' + name + ' id: ' + id;
        }
        return model;
    }

    self.findConductorType = function(id) {
        return findModelById('conductorTypes', id);
    };

    self.findConductor = function(id) {
        return findModelById('conductors', id);
    };

    return self;
});

SIREPO.app.controller('WarpVNDSourceController', function (appState, warpvndService, frameCache, panelState, $scope) {
    var self = this;

    function updateAllFields() {
        updateBeamCurrent();
        updateBeamRadius();
        updateParticleZMin();
        updateParticlesPerStep();
    }

    function updateBeamCurrent() {
        panelState.showField('beam', 'beam_current', appState.models.beam.currentMode == '1');
    }

    function updateBeamRadius() {
        panelState.enableField('beam', 'x_radius', false);
        appState.models.beam.x_radius = appState.models.simulationGrid.channel_width / 2.0;
    }

    function updateParticleZMin() {
        var grid = appState.models.simulationGrid;
        panelState.enableField('simulationGrid', 'z_particle_min', false);
        grid.z_particle_min = grid.plate_spacing / grid.num_z / 8.0;
    }

    function updateParticlesPerStep() {
        var grid = appState.models.simulationGrid;
        grid.particles_per_step = grid.num_x * 10;
    }

    self.createConductorType = function(type) {
        var model = {
            id: appState.maxId(appState.models.conductorTypes) + 1,
        };
        appState.setModelDefaults(model, type);
        self.editConductorType(type, model);
    };

    self.deleteConductor = function() {
        var conductors = [];
        appState.models.conductors.forEach(function(m) {
            if (m.id != self.deleteWarning.conductor.id) {
                conductors.push(m);
            }
        });
        appState.models.conductors = conductors;
        appState.saveChanges(['conductors']);
    };

    self.deleteConductorType = function() {
        var model = self.deleteWarning.conductorType;
        var conductorTypes = [];
        appState.models.conductorTypes.forEach(function(m) {
            if (m.id != model.id) {
                conductorTypes.push(m);
            }
        });
        appState.models.conductorTypes = conductorTypes;
        var conductors = [];
        appState.models.conductors.forEach(function(m) {
            if (m.conductorTypeId != model.id) {
                conductors.push(m);
            }
        });
        appState.models.conductors = conductors;
        appState.saveChanges(['conductorTypes', 'conductors']);
    };

    self.deleteConductorPrompt = function(model) {
        var conductor = warpvndService.findConductor(model.id);
        var conductorType = warpvndService.findConductorType(conductor.conductorTypeId);
        self.deleteWarning = {
            conductor: conductor,
            name: conductorType.name + ' Conductor',
            message: '',
        };
        $('#sr-delete-conductor-dialog').modal('show');
    };

    self.deleteConductorTypePrompt = function(model) {
        var count = 0;
        appState.models.conductors.forEach(function(m) {
            if (m.conductorTypeId == model.id) {
                count++;
            }
        });
        var message = count === 0
            ? ''
            : ('There ' + (
                count == 1
                    ? 'is 1 conductor which uses'
                    : ('are ' + count + ' conductors which use')
            ) + '  this type and will be removed from the grid.');
        self.deleteWarning = {
            conductorType: model,
            name: model.name,
            message: message,
        };
        $('#sr-delete-conductorType-dialog').modal('show');
    };

    self.editConductorType = function(type, model) {
        appState.models[type] = model;
        panelState.showModalEditor(type);
    };

    self.handleModalShown = function(name) {
        updateAllFields();
    };

    $scope.$on('cancelChanges', function(e, name) {
        if (name == 'box') {
            appState.removeModel(name);
            appState.cancelChanges('conductorTypes');
        }
    });

    $scope.$on('modelChanged', function(e, name) {
        if (name == 'box') {
            var model = appState.models[name];
            var foundIt = false;
            for (var i = 0; i < appState.models.conductorTypes.length; i++) {
                var m = appState.models.conductorTypes[i];
                if (m.id == model.id) {
                    foundIt = true;
                    break;
                }
            }
            if (! foundIt) {
                appState.models.conductorTypes.push(model);
            }
            appState.removeModel(name);
            appState.models.conductorTypes.sort(function(a, b) {
                return a.name.localeCompare(b.name);
            });
            appState.saveChanges('conductorTypes');
        }
    });

    appState.watchModelFields($scope, ['simulationGrid.num_x'], updateParticlesPerStep);
    appState.watchModelFields($scope, ['simulationGrid.plate_spacing', 'simulationGrid.num_z'], updateParticleZMin);
    appState.watchModelFields($scope, ['simulationGrid.channel_width'], updateBeamRadius);
    appState.watchModelFields($scope, ['beam.currentMode'], updateBeamCurrent);
    appState.whenModelsLoaded($scope, updateAllFields);
});

SIREPO.app.controller('WarpVNDVisualizationController', function (appState, frameCache, panelState, persistentSimulation, $scope) {
    var self = this;
    self.model = 'animation';
    self.simulationErrors = '';

    function updateAllFields() {
        panelState.enableField('simulationGrid', 'particles_per_step', false);
    }

    self.handleModalShown = function(name) {
        updateAllFields();
    };

    self.handleStatus = function(data) {
        self.simulationErrors = data.errors || '';
        frameCache.setFrameCount(0, 'particleAnimation');
        if (data.startTime && ! data.error) {
            ['currentAnimation', 'fieldAnimation', 'particleAnimation'].forEach(function(modelName) {
                appState.models[modelName].startTime = data.startTime;
                appState.saveQuietly(modelName);
            });
            if (data.percentComplete === 100 && ! data.isStateProcessing) {
                frameCache.setFrameCount(1, 'particleAnimation');
            }
        }
        frameCache.setFrameCount(data.frameCount);
    };

    self.getFrameCount = function() {
        return frameCache.getFrameCount();
    };

    persistentSimulation.initProperties(self, $scope, {
        currentAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'startTime'],
        fieldAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'field', 'startTime'],
        particleAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'renderCount', 'startTime'],
    });
    appState.whenModelsLoaded($scope, updateAllFields);
});

SIREPO.app.directive('appHeader', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: [
            '<div class="navbar-header">',
              '<a class="navbar-brand" href="/#about"><img style="width: 40px; margin-top: -10px;" src="/static/img/radtrack.gif" alt="radiasoft"></a>',
              '<div class="navbar-brand"><a href data-ng-click="nav.openSection(\'simulations\')">Warp VND</a></div>',
            '</div>',
            '<div data-app-header-left="nav"></div>',
            '<ul class="nav navbar-nav navbar-right" data-login-menu=""></ul>',
            '<ul class="nav navbar-nav navbar-right" data-ng-show="isLoaded()">',
              '<li data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
              '<li data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
            '</ul>',
            '<ul class="nav navbar-nav navbar-right" data-ng-show="nav.isActive(\'simulations\')">',
              '<li><a href data-ng-click="showSimulationModal()"><span class="glyphicon glyphicon-plus sr-small-icon"></span><span class="glyphicon glyphicon-file"></span> New Simulation</a></li>',
              '<li><a href data-ng-click="showNewFolderModal()"><span class="glyphicon glyphicon-plus sr-small-icon"></span><span class="glyphicon glyphicon-folder-close"></span> New Folder</a></li>',
            '</ul>',
        ].join(''),
        controller: function($scope) {
            $scope.hasLattice = function() {
                return appState.isLoaded();
            };
            $scope.isLoaded = function() {
                if ($scope.nav.isActive('simulations')) {
                    return false;
                }
                return appState.isLoaded();
            };
            $scope.showNewFolderModal = function() {
                panelState.showModalEditor('simulationFolder');
            };
            $scope.showSimulationModal = function() {
                panelState.showModalEditor('simulation');
            };
        },
    };
});

SIREPO.app.directive('conductorTable', function(appState) {
    return {
        restrict: 'A',
        scope: {
            source: '=controller',
        },
        template: [
            '<table style="width: 100%;  table-layout: fixed" class="table table-hover">',
              '<colgroup>',
                '<col>',
                '<col style="width: 12ex">',
                '<col style="width: 12ex">',
              '</colgroup>',
              '<thead>',
                '<tr>',
                  '<th>Name</th>',
                  '<th style="white-space: nowrap">Length [µm]</th>',
                  '<th style="white-space: nowrap">Voltage [eV]</th>',
                '</tr>',
              '</thead>',
              '<tbody>',
                '<tr data-ng-repeat="conductorType in appState.models.conductorTypes track by conductorType.id">',
                  '<td style="padding-left: 1em"><div class="badge elegant-icon"><span data-ng-drag="true" data-ng-drag-data="conductorType">{{ conductorType.name }}</span></div></td>',
                  '<td style="text-align: right">{{ conductorType.zLength }}</td>',
                  '<td style="text-align: right">{{ conductorType.voltage }}<div class="sr-button-bar-parent"><div class="sr-button-bar"><button data-ng-click="editConductorType(conductorType)" class="btn btn-info btn-xs sr-hover-button">Edit</button> <button data-ng-click="deleteConductorType(conductorType)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div><div></td>',
                '</tr>',
              '</tbody>',
            '</table>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;

            $scope.editConductorType = function(conductorType) {
                $scope.source.editConductorType('box', conductorType);
            };
            $scope.deleteConductorType = function(conductorType) {
                $scope.source.deleteConductorTypePrompt(conductorType);
            };
        },
        link: function link(scope, element) {
            //TODO(pjm): work-around for iOS 10, it would be better to add into ngDraggable
            // see discussion here: https://github.com/metafizzy/flickity/issues/457
            window.addEventListener('touchmove', function() {});
        },
    };
});

SIREPO.app.directive('conductorGrid', function(appState, panelState, plotting) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/conductor-grid.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            var ASPECT_RATIO = 6.0 / 14;
            $scope.margin = {top: 20, right: 20, bottom: 50, left: 70};
            $scope.width = $scope.height = 0;
            $scope.isClientOnly = true;
            $scope.source = panelState.findParentAttribute($scope, 'source');
            var drag, dragStart, xAxis, xAxisGrid, xAxisScale, xDomain, yAxis, yAxisGrid, yAxisScale, yDomain, zoom;
            var plateSize = 0;
            var plateSpacing = 0;
            var isInitialized = false;

            function adjustConductorLocation(diff) {
                appState.models.conductors.forEach(function(m) {
                    m.zCenter = formatNumber(parseFloat(m.zCenter) + diff);
                });
                appState.saveChanges('conductors');
            }

            function alignShapeOnGrid(shape) {
                var numX = appState.models.simulationGrid.num_x;
                var n = toMicron(appState.models.simulationGrid.channel_width / (numX + 1));
                var yCenter = shape.y - shape.height / 2;
                shape.y = alignValue(yCenter, n, numX) + shape.height / 2;
                // iterate shapes (and anode)
                //   if drag-shape right edge overlaps, but is less than the drag-shape midpoint:
                //      set drag-shape right edge to shape left edge
                var anodeLeft = toMicron(appState.models.simulationGrid.plate_spacing);
                var shapeCenter = shape.x + shape.width / 2;
                var shapeRight = shape.x + shape.width;
                if (shapeRight > anodeLeft && shapeCenter < anodeLeft) {
                    shape.x = anodeLeft - shape.width;
                    return;
                }
                var typeMap = {};
                appState.models.conductorTypes.forEach(function(conductorType) {
                    typeMap[conductorType.id] = conductorType;
                });
                appState.models.conductors.forEach(function(m) {
                    if (m.id != shape.id) {
                        var conductorLeft = toMicron(m.zCenter - typeMap[m.conductorTypeId].zLength / 2);
                        if (shapeRight > conductorLeft && shapeCenter < conductorLeft) {
                            shape.x = conductorLeft - shape.width;
                            return;
                        }
                        var conductorRight = toMicron(+m.zCenter + typeMap[m.conductorTypeId].zLength / 2);
                        if (shapeRight > conductorRight && shapeCenter < conductorRight) {
                            shape.x = conductorRight - shape.width;
                            return;
                        }
                    }
                });
            }

            function alignValue(p, n, numX) {
                var pn = fmod(p, n);
                var v;
                if (numX % 2) {
                    v = pn < 0
                        ? p - pn - n /2
                        : p + n / 2 - pn;
                }
                else {
                    v = pn < n / 2
                        ? p - pn
                        : p + n - pn;
                }
                if (Math.abs(v) < 1e-16) {
                    return 0;
                }
                return v;
            }

            function clearDragShadow() {
                d3.selectAll('.warpvnd-drag-shadow').remove();
            }

            function d3DragEnd(shape) {
                var conductorPosition = null;
                appState.models.conductors.forEach(function(m) {
                    if (shape.id == m.id) {
                        conductorPosition = m;
                    }
                });
                $scope.$applyAsync(function() {
                    if (isShapeInBounds(shape)) {
                        conductorPosition.zCenter = formatMicron(shape.x + shape.width / 2);
                        conductorPosition.xCenter = formatMicron(shape.y - shape.height / 2);
                        appState.saveChanges('conductors');
                    }
                    else {
                        appState.cancelChanges('conductors');
                        $scope.source.deleteConductorPrompt(shape);
                    }
                });
                hideShapeLocation();
            }

            function d3Dragged(shape) {
                /*jshint validthis: true*/
                var xdomain = xAxisScale.domain();
                var xPixelSize = (xdomain[1] - xdomain[0]) / $scope.width;
                shape.x = dragStart.x + xPixelSize * d3.event.x;
                var ydomain = yAxisScale.domain();
                var yPixelSize = (ydomain[1] - ydomain[0]) / $scope.height;
                shape.y = dragStart.y - yPixelSize * d3.event.y;
                alignShapeOnGrid(shape);
                d3.select(this).attr('x', xAxisScale(shape.x)).attr('y', yAxisScale(shape.y));
                showShapeLocation(shape);
            }

            function d3DragStart(shape) {
                d3.event.sourceEvent.stopPropagation();
                dragStart = appState.clone(shape);
                showShapeLocation(shape);
            }

            function drawCathodeAndAnode() {
                var viewport = select('.plot-viewport');
                viewport.selectAll('.warpvnd-plate').remove();
                var grid = appState.models.simulationGrid;
                var channel = toMicron(grid.channel_width / 2.0);
                var plateSpacing = toMicron(grid.plate_spacing);
                var h = yAxisScale(-channel) - yAxisScale(channel);
                var w = xAxisScale(0) - xAxisScale(-plateSize);
                viewport.append('rect')
                    .attr('class', 'warpvnd-plate')
                    .attr('x', xAxisScale(-plateSize))
                    .attr('y', yAxisScale(channel))
                    .attr('width', w)
                    .attr('height', h)
                    .on('dblclick', function() { editPlate('cathode'); });
                viewport.append('rect')
                    .attr('class', 'warpvnd-plate warpvnd-plate-voltage')
                    .attr('x', xAxisScale(plateSpacing))
                    .attr('y', yAxisScale(channel))
                    .attr('width', w)
                    .attr('height', h)
                    .on('dblclick', function() { editPlate('anode'); });
            }

            function drawShapes() {
                var typeMap = {};
                appState.models.conductorTypes.forEach(function(conductorType) {
                    typeMap[conductorType.id] = conductorType;
                });
                var shapes = [];
                appState.models.conductors.forEach(function(conductorPosition) {
                    var conductorType = typeMap[conductorPosition.conductorTypeId];
                    var w = toMicron(conductorType.zLength);
                    var h = toMicron(conductorType.xLength);
                    shapes.push({
                        x: toMicron(conductorPosition.zCenter) - w / 2,
                        y: toMicron(conductorPosition.xCenter) + h / 2,
                        width: w,
                        height: h,
                        id: conductorPosition.id,
                        voltage: conductorType.voltage,
                    });
                });
                d3.select('.plot-viewport').selectAll('.warpvnd-shape').remove();
                d3.select('.plot-viewport').selectAll('.warpvnd-shape')
                    .data(shapes)
                    .enter().append('rect')
                    .on('dblclick', editPosition)
                    .attr('class', function(d) {
                        return d.voltage > 0 ? 'warpvnd-shape warpvnd-shape-voltage' : 'warpvnd-shape';
                    })
                    .attr('x', function(d) { return xAxisScale(d.x); })
                    .attr('y', function(d) { return yAxisScale(d.y); })
                    .attr('width', function(d) {
                        return xAxisScale(d.x + d.width) - xAxisScale(d.x);
                    })
                    .attr('height', function(d) { return yAxisScale(d.y) - yAxisScale(d.y + d.height); })
                    .call(drag);
            }

            function editPlate(name) {
                d3.event.stopPropagation();
                $scope.$applyAsync(function() {
                    panelState.showModalEditor(name);
                });
            }

            function editPosition(shape) {
                d3.event.stopPropagation();
                $scope.$applyAsync(function() {
                    var conductor = null;
                    appState.models.conductors.forEach(function(m) {
                        if (m.id == shape.id) {
                            conductor = m;
                        }
                    });
                    appState.models.conductorPosition = conductor;
                    panelState.showModalEditor('conductorPosition');
                });
            }

            function fmod(a,b) {
                return formatNumber(Number((a - (Math.floor(a / b) * b))));
            }

            function formatMicron(v, decimals) {
                return formatNumber(v * 1e6, decimals);
            }

            function formatNumber(v, decimals) {
                return v.toPrecision(decimals || 8);
            }

            function toMicron(v) {
                return v * 1e-6;
            }

            function hideShapeLocation() {
                select('.focus-text').text('');
            }

            function isMouseInBounds(evt) {
                d3.event = evt.event;
                var p = d3.mouse(d3.select('.plot-viewport').node());
                d3.event = null;
                return p[0] >= 0 && p[0] < $scope.width && p[1] >= 0 && p[1] < $scope.height
                     ? p
                     : null;
            }

            function isShapeInBounds(shape) {
                var bounds = {
                    top: shape.y,
                    bottom: shape.y - shape.height,
                    left: shape.x,
                    right: shape.x + shape.width,
                };
                if (bounds.right < xDomain[0] || bounds.left > xDomain[1]
                    || bounds.top < yDomain[0] || bounds.bottom > yDomain[1]) {
                    return false;
                }
                return true;
            }

            function refresh() {
                if (! xDomain) {
                    return;
                }
                var xdom = xAxisScale.domain();
                var zoomWidth = xdom[1] - xdom[0];

                if (zoomWidth >= (xDomain[1] - xDomain[0])) {
                    select('.overlay').attr('class', 'overlay mouse-zoom');
                    xAxisScale.domain(xDomain);
                    yAxisScale.domain(yDomain);
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

                var grid = appState.models.simulationGrid;
                var channel = toMicron(grid.channel_width);
                var half_cell_height = channel / (grid.num_x + 1) / 2;
                yAxisGrid.tickValues(plotting.linspace(
                        -channel / 2 + half_cell_height, channel / 2 - half_cell_height, grid.num_x + 1));
                resetZoom();
                select('.plot-viewport').call(zoom);
                select('.x.axis').call(xAxis);
                select('.x.axis.grid').call(xAxisGrid); // tickLine == gridline
                select('.y.axis').call(yAxis);
                select('.y.axis.grid').call(yAxisGrid);
                drawCathodeAndAnode();
                drawShapes();
            }

            function replot() {
                var grid = appState.models.simulationGrid;
                var plateSpacing = toMicron(grid.plate_spacing);
                plateSize = plateSpacing / 15;
                var newXDomain = [-plateSize, plateSpacing + plateSize];
                if (! xDomain || ! appState.deepEquals(xDomain, newXDomain)) {
                    xDomain = newXDomain;
                    xAxisScale.domain(xDomain);
                    $scope.xRange = appState.clone(xDomain);
                }
                var channel = toMicron(grid.channel_width / 2.0);
                var newYDomain = [- channel, channel];
                if (! yDomain || ! appState.deepEquals(yDomain, newYDomain)) {
                    yDomain = newYDomain;
                    yAxisScale.domain(yDomain);
                }
                $scope.resize();
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

            function shapeFromConductorTypeAndPoint(conductorType, p) {
                var w = toMicron(conductorType.zLength);
                var h = toMicron(conductorType.xLength);
                return {
                    width: w,
                    height: h,
                    x: xAxisScale.invert(p[0]) - w / 2,
                    y: yAxisScale.invert(p[1]) + h / 2,
                };
            }

            function showShapeLocation(shape) {
                select('.focus-text').text(
                    'Center: Z=' + formatMicron(shape.x + shape.width / 2, 4)
                        + 'µm, X=' + formatMicron(shape.y - shape.height / 2, 4) + 'µm');
            }

            function updateDragShadow(conductorType, p) {
                clearDragShadow();
                var shape = shapeFromConductorTypeAndPoint(conductorType, p);
                alignShapeOnGrid(shape);
                showShapeLocation(shape);
                d3.select('.plot-viewport')
                    .append('rect').attr('class', 'warpvnd-shape warpvnd-drag-shadow')
                    .attr('x', function(d) { return xAxisScale(shape.x); })
                    .attr('y', function(d) { return yAxisScale(shape.y); })
                    .attr('width', function(d) {
                        return xAxisScale(shape.x + shape.width) - xAxisScale(shape.x);
                    })
                    .attr('height', function(d) { return yAxisScale(shape.y) - yAxisScale(shape.y + shape.height); });
            }

            $scope.destroy = function() {
                if (zoom) {
                    zoom.on('zoom', null);
                }
                $('.plot-viewport').off();
            };

            $scope.dragMove = function(conductorType, evt) {
                var p = isMouseInBounds(evt);
                if (p) {
                    d3.select('.sr-drag-clone').attr('class', 'sr-drag-clone sr-drag-clone-hidden');
                    updateDragShadow(conductorType, p);
                }
                else {
                    clearDragShadow();
                    d3.select('.sr-drag-clone').attr('class', 'sr-drag-clone');
                    hideShapeLocation();
                }
            };

            $scope.dropSuccess = function(conductorType, evt) {
                var p = isMouseInBounds(evt);
                if (p) {
                    var shape = shapeFromConductorTypeAndPoint(conductorType, p);
                    alignShapeOnGrid(shape);
                    appState.models.conductors.push({
                        id: appState.maxId(appState.models.conductors) + 1,
                        conductorTypeId: conductorType.id,
                        zCenter: formatMicron(shape.x + shape.width / 2),
                        xCenter: formatMicron(shape.y - shape.height / 2),
                    });
                    appState.saveChanges('conductors');
                }
            };

            $scope.init = function() {
                if (! appState.isLoaded()) {
                    appState.whenModelsLoaded($scope, $scope.init);
                    return;
                }
                select('svg').attr('height', plotting.initialHeight($scope));
                xAxisScale = d3.scale.linear();
                yAxisScale = d3.scale.linear();
                xAxis = plotting.createAxis(xAxisScale, 'bottom');
                xAxis.tickFormat(plotting.fixFormat($scope, 'x', 4));
                xAxisGrid = plotting.createAxis(xAxisScale, 'bottom');
                yAxis = plotting.createAxis(yAxisScale, 'left');
                yAxis.tickFormat(plotting.fixFormat($scope, 'y'));
                yAxisGrid = plotting.createAxis(yAxisScale, 'left');
                resetZoom();
                drag = d3.behavior.drag()
                    .origin(function(d) { return d; })
                    .on('drag', d3Dragged)
                    .on('dragstart', d3DragStart)
                    .on('dragend', d3DragEnd);
                select('.y-axis-label').text(plotting.extractUnits($scope, 'y', 'x [m]'));
                select('.x-axis-label').text(plotting.extractUnits($scope, 'x', 'z [m]'));
                isInitialized = true;
                replot();
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
                xAxisScale.range([0, $scope.width]);
                yAxisScale.range([$scope.height, 0]);
                xAxisGrid.tickSize(-$scope.height);
                yAxisGrid.tickSize(-$scope.width);
                refresh();
            };

            $scope.$on('cancelChanges', function(e, name) {
                if (name == 'conductors') {
                    replot();
                }
                if (name == 'conductorPosition') {
                    appState.removeModel(name);
                    appState.cancelChanges('conductors');
                }
            });
            $scope.$on('modelChanged', function(e, name) {
                if (name == 'conductorPosition') {
                    appState.removeModel(name);
                    appState.saveChanges('conductors');
                }
                if (name == 'conductorGridReport') {
                    if (isInitialized) {
                        replot();
                    }
                }
                if (name == 'simulationGrid') {
                    var v = appState.models.simulationGrid.plate_spacing;
                    if (plateSpacing && plateSpacing != v) {
                        adjustConductorLocation(v - plateSpacing);
                        plateSpacing = v;
                    }
                }
            });
            appState.whenModelsLoaded($scope, function() {
                plateSpacing = appState.models.simulationGrid.plate_spacing;
            });
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});
