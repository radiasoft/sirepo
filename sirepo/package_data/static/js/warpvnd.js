'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.appLocalRoutes.visualization = '/visualization/:simulationId';
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="XCell" data-ng-class="fieldClass">',
      '<div data-cell-selector=""></div>',
    '</div>',
    '<div data-ng-switch-when="ZCell" data-ng-class="fieldClass">',
      '<div data-cell-selector=""></div>',
    '</div>',
].join('');
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

SIREPO.app.factory('warpvndService', function(appState, panelState, plotting) {
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

    self.getXRange = function() {
        var grid = appState.models.simulationGrid;
        var channel = grid.channel_width;
        return plotting.linspace(-channel / 2, channel / 2, grid.num_x + 1);
    };

    self.getZRange = function() {
        var grid = appState.models.simulationGrid;
        var plateSpacing = grid.plate_spacing;
        return plotting.linspace(0, plateSpacing, grid.num_z + 1);
    };

    self.isEGunMode = function(isSavedValues) {
        if (appState.isLoaded()) {
            var models = isSavedValues ? appState.applicationState() : appState.models;
            return models.simulation.egun_mode == '1';
        }
        return false;
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

    function updateFieldComparison() {
        var isX = appState.models.fieldComparisonReport.dimension == 'x';
        ['1', '2', '3'].forEach(function(i) {
            panelState.showField('fieldComparisonReport', 'xCell' + i, ! isX);
            panelState.showField('fieldComparisonReport', 'zCell' + i, isX);
        });
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

    function updatePermittivity() {
        panelState.showField('box', 'permittivity', appState.models.box.isConductor == '0');
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

    self.editConductor = function(id) {
        var conductor = null;
        appState.models.conductors.forEach(function(m) {
            if (m.id == id) {
                conductor = m;
            }
        });
        appState.models.conductorPosition = conductor;
        panelState.showModalEditor('conductorPosition');
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
        else if (name == 'conductorPosition') {
            appState.removeModel(name);
            appState.cancelChanges('conductors');
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
        else if (name == 'conductorPosition') {
            appState.removeModel(name);
            appState.saveChanges('conductors');
        }
    });

    appState.watchModelFields($scope, ['simulationGrid.num_x'], updateParticlesPerStep);
    appState.watchModelFields($scope, ['simulationGrid.plate_spacing', 'simulationGrid.num_z'], updateParticleZMin);
    appState.watchModelFields($scope, ['simulationGrid.channel_width'], updateBeamRadius);
    appState.watchModelFields($scope, ['beam.currentMode'], updateBeamCurrent);
    appState.watchModelFields($scope, ['fieldComparisonReport.dimension'], updateFieldComparison);
    appState.watchModelFields($scope, ['box.isConductor'], updatePermittivity);
    appState.whenModelsLoaded($scope, updateAllFields);
});

SIREPO.app.controller('WarpVNDVisualizationController', function (appState, panelState, requestSender, warpvndService, $scope) {
    var self = this;
    self.warpvndService = warpvndService;

    function computeSimulationSteps() {
        requestSender.getApplicationData(
            {
                method: 'compute_simulation_steps',
                simulationId: appState.models.simulation.simulationId,
            },
            function(data) {
                if (data.timeOfFlight || data.electronFraction) {
                    self.estimates = {
                        timeOfFlight: data.timeOfFlight ? (+data.timeOfFlight).toExponential(4) : null,
                        steps: Math.round(data.steps),
                        electronFraction: Math.round(data.electronFraction),
                    };
                }
                else {
                    self.estimates = null;
                }
            });
    }

    self.handleModalShown = function(name) {
        panelState.enableField('simulationGrid', 'particles_per_step', false);
    };

    appState.whenModelsLoaded($scope, computeSimulationSteps);
});

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-common-footer="nav"></div>',
        ].join(''),
    };
});

SIREPO.app.directive('appHeader', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: [
            '<div data-app-header-brand="nav"></div>',
            '<div data-app-header-left="nav"></div>',
            '<div data-app-header-right="nav">',
              '<app-header-right-sim-loaded>',
                '<ul class="nav navbar-nav sr-navbar-right">',
                  '<li data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
                  '<li data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
                '</ul>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
                //  '<div>App-specific setting item</div>',
              '</app-settings>',
              '<app-header-right-sim-list>',
                //'<ul class="nav navbar-nav sr-navbar-right">',
                //  '<li>App-specific items</li>',
                //'</ul>',
              '</app-header-right-sim-list>',
            '</div>',
         ].join(''),
    };
});

SIREPO.app.directive('cellSelector', function(appState, plotting, warpvndService) {
    return {
        restrict: 'A',
        template: [
            '<select class="form-control" data-ng-model="model[field]" data-ng-options="item.id as item.name for item in cellList()"></select>',
        ].join(''),
        controller: function($scope) {
            var cells = null;
            $scope.cellList = function() {
                if (appState.isLoaded() && plotting.isPlottingReady()) {
                    if (cells) {
                        return cells;
                    }
                    cells = [];
                    if ($scope.info[1] == 'XCell') {
                        warpvndService.getXRange().forEach(function(v, index) {
                            cells.push({
                                id: index,
                                name: Math.round(v * 1000) + ' nm',
                            });
                        });
                    }
                    else if ($scope.info[1] == 'ZCell') {
                        warpvndService.getZRange().forEach(function(v, index) {
                            cells.push({
                                id: index,
                                name: v.toFixed(3) + ' µm',
                            });
                        });
                    }
                    else {
                        throw 'unknown cell type: ' + $scope.info[1];
                    }
                }
                return cells;
            };
            $scope.$on('simulationGrid.changed', function() {
                cells = null;
            });
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
            '<table data-ng-show="appState.models.conductorTypes.length" style="width: 100%;  table-layout: fixed" class="table table-hover">',
              '<colgroup>',
                '<col>',
                '<col style="width: 12ex">',
                '<col style="width: 12ex">',
              '</colgroup>',
              '<thead>',
                '<tr>',
                  '<th>Name</th>',
                '</tr>',
              '</thead>',
              '<tbody data-ng-repeat="conductorType in appState.models.conductorTypes track by conductorType.id">',
                '<tr>',
                  '<td style="padding-left: 1em; cursor: pointer; white-space: nowrap" data-ng-click="toggleConductorType(conductorType)"><div class="badge elegant-icon"><span data-ng-drag="true" data-ng-drag-data="conductorType">{{ conductorType.name }}</span></div> <span class="glyphicon" data-ng-show="hasConductors(conductorType)" data-ng-class="{\'glyphicon-collapse-down\': isCollapsed(conductorType), \'glyphicon-collapse-up\': ! isCollapsed(conductorType)}"> </span></td>',
                  '<td style="text-align: right">{{ conductorType.zLength }}µm</td>',
                  '<td style="text-align: right">{{ conductorType.voltage }}eV<div class="sr-button-bar-parent"><div class="sr-button-bar"><button data-ng-click="editConductorType(conductorType)" class="btn btn-info btn-xs sr-hover-button">Edit</button> <button data-ng-click="deleteConductorType(conductorType)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div><div></td>',
                '</tr>',
                '<tr class="warpvnd-conductor-th" data-ng-show="hasConductors(conductorType) && ! isCollapsed(conductorType)">',
                  '<td></td><th>Center Z</th><th>Center X</th>',
                '</tr>',
                '<tr data-ng-show="! isCollapsed(conductorType)" data-ng-repeat="conductor in conductors(conductorType) track by conductor.id">',
                  '<td></td>',
                  '<td style="text-align: right">{{ formatSize(conductor.zCenter) }}</td>',
                  '<td style="text-align: right">{{ formatSize(conductor.xCenter) }}<div class="sr-button-bar-parent"><div class="sr-button-bar"><button data-ng-click="editConductor(conductor)" class="btn btn-info btn-xs sr-hover-button">Edit</button> <button data-ng-click="deleteConductor(conductor)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div><div></td>',
                '</tr>',
              '</tbody>',
            '</table>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
            var collapsed = {};
            var conductorsByType = {};

            function updateConductors() {
                conductorsByType = {};
                if (! appState.isLoaded()) {
                    return;
                }
                appState.models.conductors.forEach(function(c) {
                    if (! conductorsByType[c.conductorTypeId]) {
                        conductorsByType[c.conductorTypeId] = [];
                    }
                    conductorsByType[c.conductorTypeId].push(c);
                });
                Object.keys(conductorsByType).forEach(function(id) {
                    conductorsByType[id].sort(function(a, b) {
                        var v = a.zCenter - b.zCenter;
                        if (v === 0) {
                            return a.xCenter - b.xCenter;
                        }
                        return v;
                    });
                });
            }

            $scope.conductors = function(conductorType) {
                return conductorsByType[conductorType.id];
            };
            $scope.deleteConductor = function(conductor) {
                $scope.source.deleteConductorPrompt(conductor);
            };
            $scope.deleteConductorType = function(conductorType) {
                $scope.source.deleteConductorTypePrompt(conductorType);
            };
            $scope.editConductor = function(conductor) {
                $scope.source.editConductor(conductor.id);
            };
            $scope.editConductorType = function(conductorType) {
                $scope.source.editConductorType('box', conductorType);
            };
            $scope.formatSize = function(v) {
                if (v) {
                    return (+v).toFixed(3);
                }
                return v;
            };
            $scope.hasConductors = function(conductorType) {
                var conductors = $scope.conductors(conductorType);
                return conductors ? conductors.length : false;
            };
            $scope.isCollapsed = function(conductorType) {
                return collapsed[conductorType.id];
            };
            $scope.toggleConductorType = function(conductorType) {
                collapsed[conductorType.id] = ! collapsed[conductorType.id];
            };
            appState.whenModelsLoaded($scope, updateConductors);
            $scope.$on('conductors.changed', updateConductors);
        },
        link: function link(scope, element) {
            //TODO(pjm): work-around for iOS 10, it would be better to add into ngDraggable
            // see discussion here: https://github.com/metafizzy/flickity/issues/457
            window.addEventListener('touchmove', function() {});
        },
    };
});

SIREPO.app.directive('conductorGrid', function(appState, panelState, plotting, warpvndService) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/conductor-grid.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            //TODO(pjm): keep in sync with pkcli/warpvnd.py color
            var CELL_COLORS = ['red', 'green', 'blue'];
            var ASPECT_RATIO = 6.0 / 14;
            $scope.margin = {top: 20, right: 20, bottom: 50, left: 70};
            $scope.width = $scope.height = 0;
            $scope.isClientOnly = true;
            $scope.source = panelState.findParentAttribute($scope, 'source');
            var dragCarat, dragShape, dragStart, xAxis, xAxisGrid, xAxisScale, xDomain, yAxis, yAxisGrid, yAxisScale, yDomain, zoom;
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
                var n = toMicron(appState.models.simulationGrid.channel_width / (numX * 2));
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
                var v = pn < n / 2
                    ? p - pn
                    : p + n - pn;
                if (Math.abs(v) < 1e-16) {
                    return 0;
                }
                return v;
            }

            function caratData() {
                var zRange = warpvndService.getZRange();
                var xRange = warpvndService.getXRange();
                var res = [];
                [1, 2, 3].forEach(function(i) {
                    res.push(caratField(i, 'x', zRange));
                    res.push(caratField(i, 'z', xRange));
                });
                return res;
            }

            function caratField(index, dimension, range) {
                var field = (dimension == 'x' ? 'z': 'x') + 'Cell' + index;
                return {
                    index: index,
                    field: field,
                    pos: appState.models.fieldComparisonReport[field],
                    dimension: dimension,
                    range: range,
                };
            }

            function caratText(d) {
                verifyCaratRange(d);
                return d.range[d.pos].toFixed(5);
            }

            function clearDragShadow() {
                d3.selectAll('.warpvnd-drag-shadow').remove();
            }

            function d3DragEndCarat(d) {
                if (d.pos != appState.models.fieldComparisonReport[d.field]) {
                    appState.models.fieldComparisonReport[d.field] = d.pos;
                    appState.models.fieldComparisonReport.dimension = d.dimension;
                    appState.saveChanges('fieldComparisonReport');
                }
            }

            function d3DragCarat(d) {
                /*jshint validthis: true*/
                var p = d.dimension == 'x'
                    ? xAxisScale.invert(d3.event.x) * 1e6
                    : yAxisScale.invert(d3.event.y) * 1e6;
                for (var i = 0; i < d.range.length; i++) {
                    if (d.range[i] >= p) {
                        d.pos = i;
                        break;
                    }
                }
                d3.select(this).call(updateCarat);
            }

            function d3DragEndShape(shape) {
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

            function d3DragShape(shape) {
                /*jshint validthis: true*/
                var xdomain = xAxisScale.domain();
                var xPixelSize = (xdomain[1] - xdomain[0]) / $scope.width;
                shape.x = dragStart.x + xPixelSize * d3.event.x;
                var ydomain = yAxisScale.domain();
                var yPixelSize = (ydomain[1] - ydomain[0]) / $scope.height;
                shape.y = dragStart.y - yPixelSize * d3.event.y;
                alignShapeOnGrid(shape);
                d3.select(this).call(updateShapeAttributes);
                showShapeLocation(shape);
            }

            function d3DragStartShape(shape) {
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
                    .on('dblclick', function() { editPlate('cathode'); })
                    .append('title').text('Cathode');
                viewport.append('rect')
                    .attr('class', 'warpvnd-plate warpvnd-plate-voltage')
                    .attr('x', xAxisScale(plateSpacing))
                    .attr('y', yAxisScale(channel))
                    .attr('width', w)
                    .attr('height', h)
                    .on('dblclick', function() { editPlate('anode'); })
                    .append('title').text('Anode');
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
                        conductorType: conductorType,
                    });
                });
                d3.select('.plot-viewport').selectAll('.warpvnd-shape').remove();
                d3.select('.plot-viewport').selectAll('.warpvnd-shape')
                    .data(shapes)
                    .enter().append('rect')
                    .on('dblclick', editPosition)
                    .call(updateShapeAttributes)
                    .call(dragShape);

                d3.select('.plot-viewport').selectAll('.warpvnd-cell-selector').remove();
                d3.select('.plot-viewport').selectAll('.warpvnd-cell-selector')
                    .data(caratData())
                    .enter().append('path')
                    .attr('class', 'warpvnd-cell-selector')
                    .attr('d', function(d) {
                        return d.dimension == 'x'
                            ? 'M0,-14L7,0 -7,0Z'
                            : 'M0,-7L0,7 14,0Z';
                    })
                    .style('cursor', function(d) {
                        return d.dimension == 'x' ? 'ew-resize' : 'ns-resize';
                    })
                    .style('fill', function(d) {
                        return CELL_COLORS[d.index - 1];
                    })
                    .call(updateCarat)
                    .call(dragCarat).append('title')
                    .text(caratText);
            }

            function doesShapeCrossGridLine(shape) {
                var numX = appState.models.simulationGrid.num_x;  // number of vertical cells
                var halfChannel = toMicron(appState.models.simulationGrid.channel_width/2.0);
                var cellHeight = toMicron(appState.models.simulationGrid.channel_width / numX);  // height of one cell
                var numZ = appState.models.simulationGrid.num_z;  // number of horizontal cells
                var cellWidth = toMicron(appState.models.simulationGrid.plate_spacing / numZ);  // width of one cell
                if( cellHeight === 0 || cellWidth === 0 ) {  // pathological?
                    return true;
                }
                if( shape.height >= cellHeight || shape.width >= cellWidth ) {  // shape always crosses grid line if big enough
                    return true;
                }
                var vOffset = numX % 2 === 0 ? 0.0 : cellHeight/2.0;  // translate coordinate system
                var topInCellUnits = (shape.y + vOffset)/cellHeight;
                var bottomInCellUnits = (shape.y - shape.height + vOffset)/cellHeight;
                var top = Math.floor(topInCellUnits);  // closest grid line below top
                var bottom =  Math.floor(bottomInCellUnits); // closest grid line below bottom

                // note that we do not need to translate coordinates here, since the 1st grid line is
                // always at 0 in the horizontal direction
                var leftInCellUnits = shape.x/cellWidth;
                var rightInCellUnits = (shape.x + shape.width)/cellWidth;
                var left = Math.floor(leftInCellUnits);  // closest grid line left of shape
                var right =  Math.floor(rightInCellUnits); // closest grid line right of shape

                // if the top of the shape extends above the top of the channel, it
                // is ignored.  If the bottom goes below, it is not
                return (shape.y < halfChannel && top != bottom) || left != right;
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
                    $scope.source.editConductor(shape.id);
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
                yAxisGrid.tickValues(plotting.linspace(-channel / 2, channel / 2, grid.num_x + 1));
                // var plate = toMicron(grid.plate_spacing);
                // xAxisGrid.tickValues(plotting.linspace(0, plate, grid.num_z + 1));
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

            function updateCarat(selection) {
                selection.attr('transform', function(d) {
                    verifyCaratRange(d);
                    if (d.dimension == 'x') {
                        return 'translate('
                            + xAxisScale(d.range[d.pos] * 1e-6)
                            + ',' + $scope.height + ')';
                    }
                    return 'translate(' + '0' + ',' + yAxisScale(d.range[d.pos] * 1e-6) + ')';
                });
                selection.select('title').text(caratText);
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

            function toMicron(v) {
                return v * 1e-6;
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

            function updateShapeAttributes(selection) {
                selection
                    .attr('class', 'warpvnd-shape')
                    .classed('warpvnd-shape-noncrossing', function(d) {
                        return !  doesShapeCrossGridLine(d);
                    })
                    .classed('warpvnd-shape-voltage', function(d) {
                        return d.conductorType.voltage > 0;
                    })
                    .attr('x', function(d) { return xAxisScale(d.x); })
                    .attr('y', function(d) { return yAxisScale(d.y); })
                    .attr('width', function(d) {
                        return xAxisScale(d.x + d.width) - xAxisScale(d.x);
                    })
                    .attr('height', function(d) { return yAxisScale(d.y) - yAxisScale(d.y + d.height); });
                var tooltip = selection.select('title');
                if (tooltip.empty()) {
                    tooltip = selection.append('title');
                }
                tooltip.text(function(d) {
                    return doesShapeCrossGridLine(d)
                        ? d.conductorType.name
                        : '⚠️ Conductor does not cross a warp grid line and will be ignored';
                });
            }

            function verifyCaratRange(d) {
                if (d.pos > d.range.length) {
                    d.pos = d.range.length - 1;
                }
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
                dragShape = d3.behavior.drag()
                    .origin(function(d) { return d; })
                    .on('drag', d3DragShape)
                    .on('dragstart', d3DragStartShape)
                    .on('dragend', d3DragEndShape);
                dragCarat = d3.behavior.drag()
                    .on('drag', d3DragCarat)
                    .on('dragstart', function() {
                        d3.event.sourceEvent.stopPropagation();
                    })
                    .on('dragend', d3DragEndCarat);
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
            });
            $scope.$on('modelChanged', function(e, name) {
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

SIREPO.app.directive('simulationStatusPanel', function(appState, frameCache, panelState, persistentSimulation) {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            modelName: '@simulationStatusPanel',
        },
        template: [
            '<div class="panel panel-info">',
              '<div class="panel-heading clearfix" data-panel-heading="Simulation Status" data-model-key="modelName"></div>',
              '<div class="panel-body" data-ng-hide="panelState.isHidden(modelName)">',
                '<form name="form" class="form-horizontal" autocomplete="off" novalidate data-ng-show="isStateProcessing()">',
                  '<div data-ng-show="isStatePending()">',
                    '<div class="col-sm-12">{{ stateAsText() }} {{ dots }}</div>',
                  '</div>',
                  '<div data-ng-show="isStateRunning()">',
                    '<div class="col-sm-12">',
                      '<div data-ng-show="isInitializing()">',
                        'Running Simulation {{ dots }}',
                      '</div>',
                      '<div data-ng-show="getFrameCount() > 0">',
                        'Completed frame: {{ getFrameCount() }}',
                      '</div>',
                      '<div class="progress">',
                        '<div class="progress-bar" data-ng-class="{ \'progress-bar-striped active\': isInitializing() }" role="progressbar" aria-valuenow="{{ displayPercentComplete() }}" aria-valuemin="0" aria-valuemax="100" data-ng-attr-style="width: {{ displayPercentComplete() }}%"></div>',
                      '</div>',
                    '</div>',
                  '</div>',
                  '<div class="col-sm-6 pull-right">',
                    '<button class="btn btn-default" data-ng-click="cancelSimulation()">End Simulation</button>',
                  '</div>',
                '</form>',
                '<form name="form" class="form-horizontal" autocomplete="off" novalidate data-ng-show="isStateStopped()">',
                  '<div data-ng-transclude=""></div>',
                '</form>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var SINGLE_PLOTS = ['particleAnimation', 'impactDensityAnimation'];
            $scope.panelState = panelState;
            $scope.model = 'animation';

            $scope.getFrameCount = function() {
                return frameCache.getFrameCount();
            };

            $scope.handleStatus = function(data) {
                SINGLE_PLOTS.forEach(function(name) {
                    frameCache.setFrameCount(0, name);
                });
                if (data.startTime && ! data.error) {
                    ['currentAnimation', 'fieldAnimation', 'particleAnimation', 'egunCurrentAnimation', 'impactDensityAnimation'].forEach(function(modelName) {
                        appState.models[modelName].startTime = data.startTime;
                        appState.saveQuietly(modelName);
                    });
                    if (data.percentComplete === 100 && ! data.isStateProcessing) {
                        SINGLE_PLOTS.forEach(function(name) {
                            frameCache.setFrameCount(1, name);
                        });
                    }
                }
                if (data.egunCurrentFrameCount) {
                    frameCache.setFrameCount(data.egunCurrentFrameCount, 'egunCurrentAnimation');
                }
                else {
                    frameCache.setFrameCount(0, 'egunCurrentAnimation');
                }
                frameCache.setFrameCount(data.frameCount);
            };

            $scope.startSimulation = function() {
                frameCache.setFrameCount(0);
                appState.saveChanges(['simulation', 'simulationGrid'], $scope.runSimulation);
            };

            persistentSimulation.initProperties($scope, $scope, {
                currentAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'startTime'],
                fieldAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'field', 'startTime'],
                particleAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '3', 'renderCount', 'startTime'],
                impactDensityAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'startTime'],
                egunCurrentAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'startTime'],
            });
        },
    };
});

SIREPO.app.directive('impactDensityPlot', function(appState, plotting) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/plot2d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            var ASPECT_RATIO = 4.0 / 7;
            $scope.margin = {top: 50, right: 80, bottom: 50, left: 70};
            $scope.width = $scope.height = 0;
            $scope.dataCleared = true;
            $scope.wantColorbar = true;
            var colorbar, graphLine, pointer, xAxis, xAxisGrid, xAxisScale, xDomain, yAxis, yAxisGrid, yAxisScale, yDomain, zoom;

            function mouseOver() {
                /*jshint validthis: true*/
                var path = d3.select(this);
                if (! path.empty()) {
                    var density = path.datum().srDensity;
                    pointer.pointTo(density);
                }
            }

            function refresh() {
                if (! xDomain) {
                    return;
                }
                var xdom = xAxisScale.domain();
                var zoomWidth = xdom[1] - xdom[0];

                if (zoomWidth >= (xDomain[1] - xDomain[0])) {
                    select('.plot-viewport').attr('class', 'plot-viewport mouse-zoom');
                    xAxisScale.domain(xDomain);
                    yAxisScale.domain(yDomain).nice();
                }
                else {
                    select('.plot-viewport').attr('class', 'plot-viewport mouse-move-ew');
                    if (xdom[0] < xDomain[0]) {
                        xAxisScale.domain([xDomain[0], zoomWidth + xDomain[0]]);
                    }
                    if (xdom[1] > xDomain[1]) {
                        xAxisScale.domain([xDomain[1] - zoomWidth, xDomain[1]]);
                    }
                }
                resetZoom();
                select('.plot-viewport').call(zoom);
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
                $('.plot-viewport').off();
            };

            $scope.init = function() {
                select('svg').attr('height', plotting.initialHeight($scope));
                select('svg').selectAll('.overlay').remove();
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
                $scope.xRange = json.x_range;
                var xdom = [json.x_range[0], json.x_range[1]];
                var smallDiff = (xdom[1] - xdom[0]) / 200.0;
                xdom[0] -= smallDiff;
                xdom[1] += smallDiff;
                xDomain = xdom;
                xAxisScale.domain(xdom);
                yDomain = [json.y_range[0], json.y_range[1]];
                yAxisScale.domain(yDomain).nice();
                var viewport = select('.plot-viewport');
                viewport.selectAll('.line').remove();
                select('.y-axis-label').text(plotting.extractUnits($scope, 'y', json.y_label));
                select('.x-axis-label').text(plotting.extractUnits($scope, 'x', json.x_label));
                select('.main-title').text(json.title);

                var colorRange = plotting.colorRangeFromModel($scope.modelName);
                var colorScale = d3.scale.linear()
                    .domain(plotting.linspace(json.v_min, json.v_max, colorRange.length))
                    .range(colorRange);
                colorbar = Colorbar()
                    .scale(colorScale)
                    .thickness(30)
                    .margin({top: 0, right: 60, bottom: 20, left: 10})
                    .orient("vertical");

                var i;
                for (i = 0; i < json.density_lines.length; i++) {
                    var lineInfo = json.density_lines[i];
                    var p = lineInfo.points;
                    if (! lineInfo.density.length) {
                        lineInfo.density = [0];
                    }
                    var lineSegments = plotting.linspace(p[0], p[1], lineInfo.density.length + 1);
                    var j;
                    for (j = 0; j < lineSegments.length - 1; j++) {
                        var v;
                        var density = lineInfo.density[j];
                        var p0 = lineSegments[j];
                        var p1 = lineSegments[j + 1];
                        if (lineInfo.align == 'horizontal') {
                            v = [[p0, p[2]], [p1, p[2]]];
                        }
                        else {
                            v = [[p[2], p0], [p[2], p1]];
                        }
                        v.srDensity = density;
                        var path = viewport.append('path')
                            .attr('class', 'line')
                            .attr('style', 'stroke-width: 6px; stroke-linecap: square; cursor: default; stroke: '
                                  + (density > 0 ? colorScale(density) : 'black'))
                            .datum(v);
                        path.on('mouseover', mouseOver);
                    }
                }
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
                colorbar.barlength($scope.height)
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
