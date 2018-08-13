'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.appReportTypes = [
    '<div data-ng-switch-when="conductorGrid" data-conductor-grid="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
    '<div data-ng-switch-when="impactDensity" data-impact-density-plot="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
].join('');
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="XCell" data-ng-class="fieldClass">',
      '<div data-cell-selector=""></div>',
    '</div>',
    '<div data-ng-switch-when="ZCell" data-ng-class="fieldClass">',
      '<div data-cell-selector=""></div>',
    '</div>',
].join('');
SIREPO.app.config(function() {
    if (SIREPO.IS_LOGGED_OUT) {
        return;
    }
    SIREPO.addRoutes(SIREPO.APP_SCHEMA.localRoutes);
});

SIREPO.app.factory('warpvndService', function(appState, panelState, plotting) {
    var self = {};

    function cleanNumber(v) {
        v = v.replace(/\.0+(\D+)/, '$1');
        v = v.replace(/(\.\d)0+(\D+)/, '$1$2');
        v = v.replace(/(\.0+)$/, '');
        return v;
    }

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

    function formatNumber(value) {
        if (value) {
            if (Math.abs(value) < 1e3 && Math.abs(value) > 1e-3) {
                return cleanNumber(value.toFixed(3));
            }
            else {
                return cleanNumber(value.toExponential(2));
            }
        }
        return '' + value;
    }

    self.allow3D = function() {
        return SIREPO.APP_SCHEMA.feature_config.allow_3d_mode;
    };

    self.findConductor = function(id) {
        return findModelById('conductors', id);
    };

    self.findConductorType = function(id) {
        return findModelById('conductorTypes', id);
    };

    function gridRange(sizeField, countField) {
        var grid = appState.models.simulationGrid;
        var channel = grid[sizeField];
        return plotting.linspace(-channel / 2, channel / 2, grid[countField] + 1);
    }

    self.getXRange = function() {
        return gridRange('channel_width', 'num_x');
    };

    self.getYRange = function() {
        return gridRange('channel_height', 'num_y');
    };

    self.getZRange = function() {
        var grid = appState.models.simulationGrid;
        return plotting.linspace(0, grid.plate_spacing, grid.num_z + 1);
    };

    self.is3D = function() {
        return self.allow3D() && appState.isLoaded() && appState.applicationState().simulationGrid.simulation_mode == '3d';
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

SIREPO.app.controller('WarpVNDSourceController', function (appState, warpvndService, panelState, $scope) {
    var self = this;
    var MAX_PARTICLES_PER_STEP = 1000;

    function updateAllFields() {
        updateSimulationMode();
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
        grid.particles_per_step = Math.min(MAX_PARTICLES_PER_STEP, grid.num_x * 10);
    }

    function updatePermittivity() {
        panelState.showField('box', 'permittivity', appState.models.box.isConductor == '0');
    }

    function updateSimulationMode() {
        panelState.showField('simulationGrid', 'simulation_mode', warpvndService.allow3D());
        var is3d = appState.models.simulationGrid.simulation_mode == '3d';
        ['channel_height', 'num_y'].forEach(function(f) {
            panelState.showField('simulationGrid', f, is3d);
        });
        panelState.showField('box', 'yLength', is3d);
        panelState.showField('conductorPosition', 'yCenter', is3d);
    }

    self.createConductorType = function(type) {
        var model = {
            id: appState.maxId(appState.models.conductorTypes) + 1,
        };
        appState.setModelDefaults(model, type);
        srdbg('conductor model', model);
        self.editConductorType(type, model);
    };

    self.copyConductor = function(model) {
        var modelCopy = {
            name: model.name + " Copy",
            id: appState.maxId(appState.models.conductorTypes) + 1,
            voltage: model.voltage,
            xLength: model.xLength,
            zLength: model.zLength,
            yLength: model.yLength,
            permittivity: model.permittivity,
            isConductor: model.isConductor
        };

        self.editConductorType('box', modelCopy);
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

    self.handleModalShown = function() {
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

    appState.whenModelsLoaded($scope, function() {
        updateAllFields();
        appState.watchModelFields($scope, ['simulationGrid.num_x'], updateParticlesPerStep);
        appState.watchModelFields($scope, ['simulationGrid.plate_spacing', 'simulationGrid.num_z'], updateParticleZMin);
        appState.watchModelFields($scope, ['simulationGrid.channel_width'], updateBeamRadius);
        appState.watchModelFields($scope, ['beam.currentMode'], updateBeamCurrent);
        appState.watchModelFields($scope, ['fieldComparisonReport.dimension'], updateFieldComparison);
        appState.watchModelFields($scope, ['box.isConductor'], updatePermittivity);
        appState.watchModelFields($scope, ['simulationGrid.simulation_mode'], updateSimulationMode);
    });
});

SIREPO.app.controller('WarpVNDVisualizationController', function (appState, frameCache, panelState, requestSender, warpvndService, $scope) {
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

    self.hasFrames = function() {
        return frameCache.getFrameCount() > 0;
    };

    self.handleModalShown = function() {
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
            '<div data-import-dialog=""></div>',
        ].join(''),
    };
});

SIREPO.app.directive('appHeader', function() {
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
                '<div data-sim-sections="">',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
                '</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
                //  '<div>App-specific setting item</div>',
              '</app-settings>',
              '<app-header-right-sim-list>',
                '<ul class="nav navbar-nav sr-navbar-right">',
                  '<li><a href data-ng-click="nav.showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>',
                '</ul>',
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
SIREPO.app.directive('conductorTable', function(appState, warpvndService) {
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
              '</colgroup>',
              '<thead>',
                '<tr>',
                  '<th>Name</th>',
                '</tr>',
              '</thead>',
              '<tbody data-ng-repeat="conductorType in appState.models.conductorTypes track by conductorType.id">',
                '<tr>',
                  '<td colspan="2" style="padding-left: 1em; cursor: pointer; white-space: nowrap" data-ng-click="toggleConductorType(conductorType)"><div class="badge elegant-icon"><span data-ng-drag="true" data-ng-drag-data="conductorType">{{ conductorType.name }}</span></div> <span class="glyphicon" data-ng-show="hasConductors(conductorType)" data-ng-class="{\'glyphicon-collapse-down\': isCollapsed(conductorType), \'glyphicon-collapse-up\': ! isCollapsed(conductorType)}"> </span></td>',
                  '<td style="text-align: right">{{ conductorType.zLength }}µm</td>',
                  '<td style="text-align: right">{{ conductorType.voltage }}eV<div class="sr-button-bar-parent"><div class="sr-button-bar"><button data-ng-click="source.copyConductor(conductorType)" class="btn btn-info btn-xs sr-hover-button">Copy</button> <button data-ng-click="editConductorType(conductorType)" class="btn btn-info btn-xs sr-hover-button">Edit</button> <button data-ng-click="deleteConductorType(conductorType)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div><div></td>',
                '</tr>',
                '<tr class="warpvnd-conductor-th" data-ng-show="hasConductors(conductorType) && ! isCollapsed(conductorType)">',
                  '<td></td><td data-ng-if="! warpvndService.is3D()"></td><th data-ng-if="warpvndService.is3D()">Center Y</th><th>Center Z</th><th>Center X</th>',
                '</tr>',
                '<tr data-ng-show="! isCollapsed(conductorType)" data-ng-repeat="conductor in conductors(conductorType) track by conductor.id">',
                  '<td></td>',
                  '<td data-ng-if="! warpvndService.is3D()"></td>',
                  '<td data-ng-if="warpvndService.is3D()" style="text-align: right">{{ formatSize(conductor.yCenter) }}</td>',
                  '<td style="text-align: right">{{ formatSize(conductor.zCenter) }}</td>',
                  '<td style="text-align: right">{{ formatSize(conductor.xCenter) }}<div class="sr-button-bar-parent"><div class="sr-button-bar"><button data-ng-click="editConductor(conductor)" class="btn btn-info btn-xs sr-hover-button">Edit</button> <button data-ng-click="deleteConductor(conductor)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div><div></td>',
                '</tr>',
              '</tbody>',
            '</table>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
            $scope.warpvndService = warpvndService;
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
    };
});

SIREPO.app.directive('conductorGrid', function(appState, layoutService, panelState, plotting, warpvndService) {
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
            $scope.warpvndService = warpvndService;
            $scope.margin = {top: 20, right: 20, bottom: 45, left: 70};
            $scope.width = $scope.height = 0;
            $scope.zHeight = 150;
            $scope.isClientOnly = true;
            $scope.source = panelState.findParentAttribute($scope, 'source');
            $scope.is3dPreview = false;
            var dragCarat, dragShape, dragStart, yRange, zoom;
            var planeLine = 0.0;
            var plateSize = 0;
            var plateSpacing = 0;
            var isInitialized = false;
            var axes = {
                x: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh),
                y: layoutService.plotAxis($scope.margin, 'y', 'left', refresh),
                z: layoutService.plotAxis($scope.margin, 'z', 'left', refresh),
            };

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
                shape.y = alignValue(yCenter, n) + shape.height / 2;
                // iterate shapes (and anode)
                //   if drag-shape right edge overlaps, but is less than the drag-shape midpoint:
                //      set drag-shape right edge to shape left edge
                var anodeLeft = toMicron(plateSpacing);
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

            function alignValue(p, n) {
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
                if (appState.models.fieldComparisonReport[field] > range.length) {
                    appState.models.fieldComparisonReport[field] = range.length - 1;
                }
                return {
                    index: index,
                    field: field,
                    pos: appState.models.fieldComparisonReport[field],
                    dimension: dimension,
                    range: range,
                };
            }

            function caratText(d) {
                return d.range[d.pos].toFixed(5);
            }

            function clearDragShadow() {
                d3.selectAll('.warpvnd-drag-shadow').remove();
            }

            function d3DragCarat(d) {
                /*jshint validthis: true*/
                var p = d.dimension == 'x'
                    ? axes.x.scale.invert(d3.event.x) * 1e6
                    : axes.y.scale.invert(d3.event.y) * 1e6;
                var halfWidth = (d.range[1] - d.range[0]) / 2.0;
                for (var i = 0; i < d.range.length; i++) {
                    if (d.range[i] + halfWidth >= p) {
                        d.pos = i;
                        break;
                    }
                }
                d3.select(this).call(updateCarat);
            }

            function d3DragEndCarat(d) {
                if (d.pos != appState.models.fieldComparisonReport[d.field]) {
                    appState.models.fieldComparisonReport[d.field] = d.pos;
                    appState.models.fieldComparisonReport.dimension = d.dimension;
                    appState.saveChanges('fieldComparisonReport');
                }
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

            function d3DragLine() {
                var oldPlaneLine = planeLine;
                planeLine = axes.z.scale.invert(d3.event.y);
                var grid = appState.models.simulationGrid;
                var depth = toMicron(grid.channel_height / 2.0);
                if (planeLine < -depth) {
                    planeLine = -depth;
                }
                else if (planeLine > depth) {
                    planeLine = depth;
                }
                var halfWidth = (yRange[1] - yRange[0]) / 2.0;
                for (var i = 0; i < yRange.length; i++) {
                    if (yRange[i] + halfWidth >= planeLine * 1e6) {
                        planeLine = yRange[i] / 1e6;
                        break;
                    }
                }
                if (oldPlaneLine != planeLine) {
                    drawShapes();
                }
                updateDragLine();
            }

            function d3DragShape(shape) {
                /*jshint validthis: true*/
                var xdomain = axes.x.scale.domain();
                var xPixelSize = (xdomain[1] - xdomain[0]) / $scope.width;
                shape.x = dragStart.x + xPixelSize * d3.event.x;
                var ydomain = axes.y.scale.domain();
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

            function doesShapeCrossGridLine(shape) {
                if (shape.dim == 'y') {
                    return true;
                }
                var numX = appState.models.simulationGrid.num_x;  // number of vertical cells
                var halfChannel = toMicron(appState.models.simulationGrid.channel_width/2.0);
                var cellHeight = toMicron(appState.models.simulationGrid.channel_width / numX);  // height of one cell
                var numZ = appState.models.simulationGrid.num_z;  // number of horizontal cells
                var cellWidth = toMicron(plateSpacing / numZ);  // width of one cell
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

            function drawCathodeAndAnode(dim) {
                var info = plotInfoForDimension(dim);
                var viewport = select(info.viewportClass);
                viewport.selectAll('.warpvnd-plate').remove();
                var grid = appState.models.simulationGrid;
                var channel = toMicron(grid[info.heightField] / 2.0);
                var h = info.axis.scale(-channel) - info.axis.scale(channel);
                var w = axes.x.scale(0) - axes.x.scale(-plateSize);
                viewport.append('rect')
                    .attr('class', 'warpvnd-plate')
                    .attr('x', axes.x.scale(-plateSize))
                    .attr('y', info.axis.scale(channel))
                    .attr('width', w)
                    .attr('height', h)
                    .on('dblclick', function() { editPlate('cathode'); })
                    .append('title').text('Cathode');
                viewport.append('rect')
                    .attr('class', 'warpvnd-plate warpvnd-plate-voltage')
                    .attr('x', axes.x.scale(toMicron(plateSpacing)))
                    .attr('y', info.axis.scale(channel))
                    .attr('width', w)
                    .attr('height', h)
                    .on('dblclick', function() { editPlate('anode'); })
                    .append('title').text('Anode');
            }

            function drawCathodeAndAnodes() {
                drawCathodeAndAnode('x');
                if (warpvndService.is3D()) {
                    drawCathodeAndAnode('y');
                }
            }

            function drawCarats() {
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

            function drawConductors(typeMap, dim) {
                var info = plotInfoForDimension(dim);
                var shapes = [];
                appState.models.conductors.forEach(function(conductorPosition) {
                    var conductorType = typeMap[conductorPosition.conductorTypeId];
                    var w = toMicron(conductorType.zLength);
                    var h = toMicron(conductorType[info.lengthField]);
                    shapes.push({
                        x: toMicron(conductorPosition.zCenter) - w / 2,
                        y: toMicron(conductorPosition[info.centerField]) + h / 2,
                        plane: toMicron(conductorPosition.yCenter),
                        width: w,
                        height: h,
                        depth: toMicron(conductorType.yLength),
                        id: conductorPosition.id,
                        conductorType: conductorType,
                        dim: dim,
                    });
                });
                d3.select(info.viewportClass).selectAll('.warpvnd-shape').remove();
                d3.select(info.viewportClass).selectAll('.warpvnd-shape')
                    .data(shapes)
                    .enter().append('rect')
                    .on('dblclick', editPosition)
                    .call(updateShapeAttributes);
                if (dim == 'x') {
                    d3.select(info.viewportClass).selectAll('.warpvnd-shape').call(dragShape);
                }
            }

            function drawShapes() {
                var typeMap = {};
                appState.models.conductorTypes.forEach(function(conductorType) {
                    typeMap[conductorType.id] = conductorType;
                });
                drawConductors(typeMap, 'x');
                if (warpvndService.is3D()) {
                    drawConductors(typeMap, 'y');
                }
                drawCarats();
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
                if (bounds.right < axes.x.domain[0] || bounds.left > axes.x.domain[1]
                    || bounds.top < axes.y.domain[0] || bounds.bottom > axes.y.domain[1]) {
                    return false;
                }
                return true;
            }

            function plotInfoForDimension(dim) {
                if (dim === 'x') {
                    return {
                        viewportClass: '.plot-viewport',
                        axis: axes.y,
                        heightField: 'channel_width',
                        centerField: 'xCenter',
                        lengthField: 'xLength',
                    };
                }
                else if (dim === 'y') {
                    return {
                        viewportClass: '.z-plot-viewport',
                        axis: axes.z,
                        heightField: 'channel_height',
                        centerField: 'yCenter',
                        lengthField: 'yLength',
                    };
                }
                throw 'invalid dim: ' + dim;
            }

            function refresh() {
                if (! axes.x.domain) {
                    return;
                }
                if (layoutService.plotAxis.allowUpdates) {
                    var width = parseInt(select().style('width')) - $scope.margin.left - $scope.margin.right;
                    if (isNaN(width)) {
                        return;
                    }
                    width = plotting.constrainFullscreenSize($scope, width, ASPECT_RATIO);
                    $scope.width = width;
                    $scope.height = ASPECT_RATIO * $scope.width;
                    select('svg')
                        .attr('width', $scope.width + $scope.margin.left + $scope.margin.right)
                        .attr('height', $scope.height + $scope.margin.top + $scope.margin.bottom);
                    select('.z-plot')
                        .attr('width', $scope.width + $scope.margin.left + $scope.margin.right)
                        .attr('height', $scope.zHeight + $scope.margin.bottom);
                    axes.x.scale.range([0, $scope.width]);
                    axes.y.scale.range([$scope.height, 0]);
                    axes.z.scale.range([$scope.zHeight, 0]);
                    axes.x.grid.tickSize(-$scope.height);
                    axes.y.grid.tickSize(-$scope.width);
                    axes.z.grid.tickSize(-$scope.width);
                }
                if (plotting.trimDomain(axes.x.scale, axes.x.domain)) {
                    select('.overlay').attr('class', 'overlay mouse-zoom');
                    select('.z-plot-viewport .overlay').attr('class', 'overlay mouse-zoom');
                    axes.y.scale.domain(axes.y.domain);
                }
                else {
                    select('.overlay').attr('class', 'overlay mouse-move-ew');
                    select('.z-plot-viewport .overlay').attr('class', 'overlay mouse-move-ew');
                }

                var grid = appState.models.simulationGrid;
                var channel = toMicron(grid.channel_width);
                axes.y.grid.tickValues(plotting.linspace(-channel / 2, channel / 2, grid.num_x + 1));
                var depth = toMicron(grid.channel_height);
                axes.z.grid.tickValues(plotting.linspace(-depth / 2, depth / 2, grid.num_y + 1));
                resetZoom();
                select('.plot-viewport').call(zoom);
                select('.z-plot-viewport').call(zoom);
                $.each(axes, function(dim, axis) {
                    axis.updateLabelAndTicks({
                        width: $scope.width,
                        height: $scope.height,
                    }, select);
                    axis.grid.ticks(axis.tickCount);
                    select('.' + dim + '.axis.grid').call(axis.grid);
                });
                select('.zx.axis.grid').call(axes.x.grid);
                drawCathodeAndAnodes();
                drawShapes();
                updateDragLine();
            }

            function replot() {
                var grid = appState.models.simulationGrid;
                plateSize = toMicron(plateSpacing) / 15;
                var newXDomain = [-plateSize, toMicron(plateSpacing) + plateSize];
                if (! axes.x.domain || ! appState.deepEquals(axes.x.domain, newXDomain)) {
                    axes.x.domain = newXDomain;
                    axes.x.scale.domain(axes.x.domain);
                    $scope.xRange = appState.clone(axes.x.domain);
                }
                var channel = toMicron(grid.channel_width / 2.0);
                var newYDomain = [- channel, channel];
                if (! axes.y.domain || ! appState.deepEquals(axes.y.domain, newYDomain)) {
                    axes.y.domain = newYDomain;
                    axes.y.scale.domain(axes.y.domain);
                }
                if (warpvndService.is3D()) {
                    yRange = warpvndService.getYRange();
                    var depth = toMicron(grid.channel_height / 2.0);
                    var newZDomain = [- depth, depth];
                    if (! axes.z.domain || ! appState.deepEquals(axes.z.domain, newZDomain)) {
                        axes.z.domain = newZDomain;
                        axes.z.scale.domain(axes.z.domain);
                    }
                    if (select('.z-plot-viewport line.cross-hair').empty()) {
                        select('.z-plot-viewport')
                            .append('line')
                            .attr('class', 'cross-hair')
                            .attr('x1', 0);
                    }
                    if (select('.z-plot-viewport line.plane-dragline').empty()) {
                        var dragLine = d3.behavior.drag()
                            .on('drag', d3DragLine)
                            .on('dragstart', function() {
                                d3.event.sourceEvent.stopPropagation();
                            });
                        select('.z-plot-viewport')
                            .append('line')
                            .attr('class', 'plane-dragline plane-dragline-y selectable-path')
                            .attr('x1', 0)
                            .call(dragLine);
                    }
                }
                $scope.resize();
            }

            function resetZoom() {
                zoom = axes.x.createZoom($scope);
            }

            function updateCarat(selection) {
                selection.attr('transform', function(d) {
                    if (d.dimension == 'x') {
                        return 'translate('
                            + axes.x.scale(toMicron(d.range[d.pos]))
                            + ',' + $scope.height + ')';
                    }
                    return 'translate(' + '0' + ',' + axes.y.scale(toMicron(d.range[d.pos])) + ')';
                });
                selection.select('title').text(caratText);
            }

            function updateDragLine() {
                var l1 = select('.z-plot-viewport line.cross-hair');
                var l2 = select('.z-plot-viewport line.plane-dragline');
                var y = axes.z.scale(planeLine);
                [l1, l2].forEach(function(line) {
                    line.attr('x1', 0)
                        .attr('x2', $scope.width)
                        .attr('y1', y)
                        .attr('y2', y);
                });
                select('.z-plot .focus-text').text('Y=' + formatNumber(planeLine * 1e6, 4) + 'µm');
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
                    x: axes.x.scale.invert(p[0]) - w / 2,
                    y: axes.y.scale.invert(p[1]) + h / 2,
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
                    .attr('x', function() { return axes.x.scale(shape.x); })
                    .attr('y', function() { return axes.y.scale(shape.y); })
                    .attr('width', function() {
                        return axes.x.scale(shape.x + shape.width) - axes.x.scale(shape.x);
                    })
                    .attr('height', function() { return axes.y.scale(shape.y) - axes.y.scale(shape.y + shape.height); });
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
                    .classed('warpvnd-shape-inactive', function(d) {
                        if (! warpvndService.is3D()) {
                            return false;
                        }
                        var halfDepth = d.depth / 2;
                        if (planeLine >= d.plane - halfDepth && planeLine <= d.plane + halfDepth) {
                            return false;
                        }
                        return true;
                    })
                    .attr('x', function(d) { return axes.x.scale(d.x); })
                    .attr('y', function(d) {
                        var axis = d.dim === 'x'
                            ? axes.y
                            : axes.z;
                        return axis.scale(d.y);
                    })
                    .attr('width', function(d) {
                        return axes.x.scale(d.x + d.width) - axes.x.scale(d.x);
                    })
                    .attr('height', function(d) {
                        var axis = d.dim === 'x'
                            ? axes.y
                            : axes.z;
                        return axis.scale(d.y) - axis.scale(d.y + d.height);
                    });
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
                        yCenter: formatMicron(planeLine),
                    });
                    appState.saveChanges('conductors');
                }
            };

            $scope.init = function() {
                if (! appState.isLoaded()) {
                    appState.whenModelsLoaded($scope, $scope.init);
                    return;
                }
                plateSpacing = appState.models.simulationGrid.plate_spacing;
                select('svg').attr('height', plotting.initialHeight($scope));
                $.each(axes, function(dim, axis) {
                    axis.init();
                    axis.grid = axis.createAxis();
                });
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
                axes.x.parseLabelAndUnits('z [m]');
                axes.y.parseLabelAndUnits('x [m]');
                axes.z.parseLabelAndUnits('y [m]');
                isInitialized = true;
                replot();
            };

            $scope.resize = function() {
                if (select().empty()) {
                    return;
                }
                refresh();
            };

            $scope.toggle3dPreview = function() {
                $scope.is3dPreview = ! $scope.is3dPreview;
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
                    if (isInitialized) {
                        replot();
                    }
                }
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
                '<form name="form" class="form-horizontal" autocomplete="off" novalidate data-ng-show="simState.isProcessing()">',
                  '<div data-ng-show="simState.isStatePending()">',
                    '<div class="col-sm-12">{{ simState.stateAsText() }} {{ simState.dots }}</div>',
                  '</div>',
                  '<div data-ng-show="simState.isStateRunning()">',
                    '<div class="col-sm-12">',
                      '<div data-ng-show="simState.isInitializing()">',
                        'Running Simulation {{ simState.dots }}',
                      '</div>',
                      '<div data-ng-show="simState.getFrameCount() > 0">',
                        'Completed frame: {{ simState.getFrameCount() }}',
                      '</div>',
                      '<div class="progress">',
                        '<div class="progress-bar" data-ng-class="{ \'progress-bar-striped active\': simState.isInitializing() }" role="progressbar" aria-valuenow="{{ simState.getPercentComplete() }}" aria-valuemin="0" aria-valuemax="100" data-ng-attr-style="width: {{ simState.getPercentComplete() }}%"></div>',
                      '</div>',
                    '</div>',
                  '</div>',
                  '<div class="col-sm-6 pull-right">',
                    '<button class="btn btn-default" data-ng-click="simState.cancelSimulation()">End Simulation</button>',
                  '</div>',
                '</form>',
                '<form name="form" class="form-horizontal" autocomplete="off" novalidate data-ng-show="simState.isStopped()">',
                  '<div data-ng-transclude=""></div>',
                '</form>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var SINGLE_PLOTS = ['particleAnimation', 'impactDensityAnimation', 'particle3d'];
            $scope.panelState = panelState;

            function handleStatus(data) {
                SINGLE_PLOTS.forEach(function(name) {
                    frameCache.setFrameCount(0, name);
                });
                if (data.startTime && ! data.error) {
                    ['currentAnimation', 'fieldAnimation', 'particleAnimation', 'particle3d', 'egunCurrentAnimation', 'impactDensityAnimation'].forEach(function(modelName) {
                        appState.models[modelName].startTime = data.startTime;
                        appState.saveQuietly(modelName);
                    });
                    if (data.percentComplete === 100 && ! $scope.simState.isProcessing()) {
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
            }

            $scope.startSimulation = function() {
                $scope.simState.saveAndRunSimulation(['simulation', 'simulationGrid']);
            };

            $scope.simState = persistentSimulation.initSimulationState($scope, 'animation', handleStatus, {
                currentAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'startTime'],
                fieldAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'field', 'startTime'],
                particleAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '3', 'renderCount', 'startTime'],
                particle3d: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'renderCount', 'startTime'],
                impactDensityAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'startTime'],
                egunCurrentAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'startTime'],
            });
        },
    };
});

SIREPO.app.directive('impactDensityPlot', function(appState, layoutService, plotting) {
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
            var colorbar, graphLine, pointer, zoom;
            var axes = {
                x: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh),
                y: layoutService.plotAxis($scope.margin, 'y', 'left', refresh),
            };

            function mouseOver() {
                /*jshint validthis: true*/
                var path = d3.select(this);
                if (! path.empty()) {
                    var density = path.datum().srDensity;
                    pointer.pointTo(density);
                }
            }

            function refresh() {
                if (! axes.x.domain) {
                    return;
                }
                if (layoutService.plotAxis.allowUpdates) {
                    var width = parseInt(select().style('width')) - $scope.margin.left - $scope.margin.right;
                    if (isNaN(width)) {
                        return;
                    }
                    width = plotting.constrainFullscreenSize($scope, width, ASPECT_RATIO);
                    $scope.width = width;
                    $scope.height = ASPECT_RATIO * $scope.width;
                    select('svg')
                        .attr('width', $scope.width + $scope.margin.left + $scope.margin.right)
                        .attr('height', $scope.height + $scope.margin.top + $scope.margin.bottom);
                    axes.x.scale.range([0, $scope.width]);
                    axes.y.scale.range([$scope.height, 0]);
                    axes.x.grid.tickSize(-$scope.height);
                    axes.y.grid.tickSize(-$scope.width);
                    colorbar.barlength($scope.height)
                        .origin([0, 0]);
                    pointer = select('.colorbar').call(colorbar);
                }
                if (plotting.trimDomain(axes.x.scale, axes.x.domain)) {
                    select('.plot-viewport').attr('class', 'plot-viewport mouse-zoom');
                    axes.y.scale.domain(axes.y.domain);
                }
                else {
                    select('.plot-viewport').attr('class', 'plot-viewport mouse-move-ew');
                }
                resetZoom();
                select('.plot-viewport').call(zoom);
                $.each(axes, function(dim, axis) {
                    axis.updateLabelAndTicks({
                        width: $scope.width,
                        height: $scope.height,
                    }, select);
                    axis.grid.ticks(axis.tickCount);
                    select('.' + dim + '.axis.grid').call(axis.grid);
                });
                select('.plot-viewport').selectAll('.line').attr('d', graphLine);
            }

            function resetZoom() {
                zoom = axes.x.createZoom($scope);
            }

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            $scope.clearData = function() {
                $scope.dataCleared = true;
                axes.x.domain = null;
            };

            $scope.destroy = function() {
                zoom.on('zoom', null);
                $('.plot-viewport').off();
            };

            $scope.init = function() {
                select('svg').attr('height', plotting.initialHeight($scope));
                // can't remove the overlay or it causes a memory leak
                select('svg').selectAll('.overlay').classed('disabled-overlay', true);
                $.each(axes, function(dim, axis) {
                    axis.init();
                    axis.grid = axis.createAxis();
                });
                graphLine = d3.svg.line()
                    .x(function(d) {
                        return axes.x.scale(d[0]);
                    })
                    .y(function(d) {
                        return axes.y.scale(d[1]);
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
                axes.x.domain = xdom;
                axes.x.scale.domain(xdom);
                axes.y.domain = [json.y_range[0], json.y_range[1]];
                axes.y.scale.domain(axes.y.domain).nice();
                var viewport = select('.plot-viewport');
                viewport.selectAll('.line').remove();
                $.each(axes, function (dim, axis) {
                    axis.parseLabelAndUnits(json[dim + '_label']);
                    select('.' + dim + '-axis-label').text(json[dim + '_label']);
                });
                select('.main-title').text(json.title);

                var colorMap = plotting.colorMapFromModel($scope.modelName);
                var colorScale = d3.scale.linear()
                    .domain(plotting.linspace(json.v_min, json.v_max, colorMap.length))
                    .range(colorMap);
                colorbar = Colorbar()
                    .scale(colorScale)
                    .thickness(30)
                    .margin({top: 10, right: 60, bottom: 20, left: 10})
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
                refresh();
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('conductors3d', function(appState, vtkService, vtkPlotting, warpVTKService) {
    return {
        restrict: 'A',
        template: [
            '<div class="sr-plot-particle-3d">',
              '<div class="vtk-canvas-holder"></div>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {
            var X_Z_ASPECT_RATIO = 4.0 / 7.0;

            // rendering
            var renderWindow = null;
            var renderer = null;
            var cam = null;
            var startPlaneSource = null;
            var endPlaneSource = null;
            var boxActors = [];
            var outlineSource = null;
            var pointRanges = {};

            // geometry
            var coordMapper = vtkPlotting.coordMapper();

            // colors - vtk uses a range of 0-1 for RGB components
            var zeroVoltsColor = [243.0/255.0, 212.0/255.0, 200.0/255.0];
            var voltsColor = [105.0/255.0, 146.0/255.0, 255.0/255.0];

            function addActors(actorArr) {
                actorArr.forEach(function(actor) {
                    renderer.addActor(actor);
                });
            }

            function init() {
                var rw = $($element).find('.sr-plot-particle-3d .vtk-canvas-holder');
                rw.on('dblclick', reset);
                rw.height(rw.width() / 1.3);
                var fsRenderer = vtk.Rendering.Misc.vtkFullScreenRenderWindow.newInstance(
                    {
                        background: [1, 1, 1, 1],
                        container: rw[0],
                    });
                renderer = fsRenderer.getRenderer();
                renderer.getLights()[0].setLightTypeToSceneLight();
                renderWindow = fsRenderer.getRenderWindow();
                cam = renderer.get().activeCamera;
                var rwInteractor = renderWindow.getInteractor();
                var zoomObserver = vtk.Rendering.Core.vtkInteractorObserver.newInstance({
                    interactor: rwInteractor,
                    subscribedEvents: ['StartPinch']
                });
                zoomObserver.setInteractor(rwInteractor);
                var startPlaneMapper = vtk.Rendering.Core.vtkMapper.newInstance();
                var startPlaneActor = vtk.Rendering.Core.vtkActor.newInstance();
                startPlaneActor.getProperty().setColor(zeroVoltsColor[0], zeroVoltsColor[1], zeroVoltsColor[2]);
                startPlaneActor.getProperty().setLighting(false);
                startPlaneSource = vtk.Filters.Sources.vtkPlaneSource.newInstance({ xResolution: 8, yResolution: 8 });
                startPlaneMapper.setInputConnection(startPlaneSource.getOutputPort());
                startPlaneActor.setMapper(startPlaneMapper);
                renderer.addActor(startPlaneActor);

                var endPlaneMapper = vtk.Rendering.Core.vtkMapper.newInstance();
                var endPlaneActor = vtk.Rendering.Core.vtkActor.newInstance();
                endPlaneActor.getProperty().setColor(voltsColor[0], voltsColor[1], voltsColor[2]);
                endPlaneActor.getProperty().setLighting(false);
                endPlaneSource = vtk.Filters.Sources.vtkPlaneSource.newInstance({ xResolution: 8, yResolution: 8 });
                endPlaneMapper.setInputConnection(endPlaneSource.getOutputPort());
                endPlaneActor.setMapper(endPlaneMapper);
                renderer.addActor(endPlaneActor);

                var outlineMapper = vtk.Rendering.Core.vtkMapper.newInstance();
                var outlineActor = vtk.Rendering.Core.vtkActor.newInstance();
                outlineSource = vtk.Filters.Sources.vtkCubeSource.newInstance();
                outlineActor.getProperty().setColor(1, 1, 1);
                outlineActor.getProperty().setEdgeVisibility(true);
                outlineActor.getProperty().setEdgeColor(0, 0, 0);
                outlineActor.getProperty().setFrontfaceCulling(true);
                outlineActor.getProperty().setLighting(false);

                outlineMapper.setInputConnection(outlineSource.getOutputPort());
                outlineActor.setMapper(outlineMapper);
                renderer.addActor(outlineActor);
            }

            function load() {
                removeActors(boxActors);

                var grid = appState.models.simulationGrid;
                var ymax = grid.channel_height / 2.0 * 1e-6;
                var ymin = -ymax;
                var zmin = 0;
                var zmax = grid.plate_spacing * 1e-6;
                var xmax = grid.channel_width / 2.0 * 1e-6;
                var xmin = -xmax;

                var yzAspectRatio =  grid.channel_height / grid.channel_width;
                var pointScales = {
                    z: 1 / Math.abs((zmax - zmin)),
                    x: X_Z_ASPECT_RATIO / Math.abs((xmax - xmin)),
                    y: X_Z_ASPECT_RATIO * yzAspectRatio / Math.abs((ymax - ymin))
                };
                pointRanges = {
                    z: [pointScales.z * zmin, pointScales.z * zmax],
                    x: [pointScales.x * xmin, pointScales.x * xmax],
                    y: [pointScales.y * ymin, pointScales.y * ymax]
                };
                //var zfactor = pointScales.z;
                //var xfactor = pointScales.x;
                //var yfactor = pointScales.y;
                coordMapper = warpVTKService.warpCoordMapper([pointScales.x, pointScales.y, pointScales.z]);

                coordMapper.setPlane(startPlaneSource,
                    [xmin, ymin, zmin],
                    [xmin, ymax, zmin],
                    [xmax, ymin, zmin]
                );
                coordMapper.setPlane(endPlaneSource,
                    [xmin, ymin, zmax],
                    [xmin, ymax, zmax],
                    [xmax, ymin, zmax]
                );
                var padding = 0.01;
                outlineSource.setXLength(Math.abs(endPlaneSource.getOrigin()[0] - startPlaneSource.getOrigin()[0]) + padding);
                outlineSource.setYLength(Math.abs(endPlaneSource.getPoint2()[1] - endPlaneSource.getPoint1()[1]) + padding);
                outlineSource.setZLength(Math.abs(endPlaneSource.getPoint2()[2] - endPlaneSource.getPoint1()[2]) + padding);
                outlineSource.setCenter([
                    (endPlaneSource.getOrigin()[0] - startPlaneSource.getOrigin()[0]) / 2.0,
                    (endPlaneSource.getOrigin()[1] - startPlaneSource.getOrigin()[1]) / 2.0,
                    (endPlaneSource.getOrigin()[2] - startPlaneSource.getOrigin()[2]) / 2.0
                ]);


                var typeMap = {};
                appState.models.conductorTypes.forEach(function(conductorType) {
                    typeMap[conductorType.id] = conductorType;
                });
                appState.models.conductors.forEach(function(conductor) {
                    // lengths and centers are in µm
                    var cFactor = 1e6;
                    var cModel = typeMap[conductor.conductorTypeId];
                    var bs = coordMapper.buildBox(
                        [cModel.xLength / cFactor, cModel.yLength / cFactor, cModel.zLength / cFactor],
                        [conductor.xCenter / cFactor, conductor.yCenter / cFactor, conductor.zCenter / cFactor]
                    );
                    var bm = vtk.Rendering.Core.vtkMapper.newInstance();
                    bm.setInputConnection(bs.getOutputPort());

                    var cColor = cModel.voltage == 0 ? zeroVoltsColor : voltsColor;
                    var cEdgeColor = [0, 0, 0];
                    var ba = vtk.Rendering.Core.vtkActor.newInstance();
                    ba.getProperty().setColor(cColor[0], cColor[1], cColor[2]);
                    ba.getProperty().setEdgeVisibility(true);
                    ba.getProperty().setEdgeColor(cEdgeColor[0], cEdgeColor[1], cEdgeColor[2]);
                    ba.getProperty().setLighting(false);
                    ba.setMapper(bm);
                    boxActors.push(ba);
                });

                refresh();
            }

            function refresh() {
                addActors(boxActors);
                reset();
            }

            function removeActors(actorArr) {
                actorArr.forEach(function(actor) {
                    renderer.removeActor(actor);
                });
                actorArr.length = 0;
            }

            function reset() {
                cam.setPosition(0, 0, 1);
                cam.setFocalPoint(0, 0, 0);
                cam.setViewUp(0, 1, 0);
                renderer.resetCamera();
                cam.zoom(1.3);
                renderWindow.render();
            }

            $scope.$on('$destroy', function() {
                $($element).find('.sr-plot-particle-3d .vtk-canvas-holder').off();
                //TODO(pjm): fix memory leaks
            });

            appState.whenModelsLoaded($scope, function() {
                vtkService.vtk().then(function() {
                    init();
                    load();
                });
            });

        },
    };
});

// NOTE: the vtk and warp coordinate systems are related the following way:
//    vtk X (left to right) = warp Z
//    vtk Y (bottom to top) = warp X
//    vtk Z (out to in) = warp Y
SIREPO.app.directive('particle3d', function(appState, panelState, requestSender, frameCache, plotting, vtkPlotting, layoutService, utilities, vtkService, warpVTKService) {

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/particle3d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope, $element) {

            var d3self;
            //srdbg(appState.models.fieldReport, appState.models.simulationGrid, appState.models.particle3d);
            var X_Z_ASPECT_RATIO = 4.0 / 7.0;
            //var Y_Z_ASPECT_RATIO = 4.0 / 7.0;
            $scope.margin = {top: 50, right: 23, bottom: 50, left: 75};
            $scope.xAxisAngle = 0;
            $scope.yAxisAngle = 0;
            $scope.zAxisAngle = -35;
            $scope.width = $scope.height = 0;
            $scope.axesMargins = {
                x: { width: 16.0, height: 0.0 },
                y: { width: 0.0, height: 16.0 }
            };

            // little test boxes are useful for translating vtk space to screen space
            $scope.testBoxes = [];

            $scope.side = 'y';
            $scope.xdir = 1;  $scope.ydir = 1;  $scope.zdir = 1;

            $scope.dataCleared = true;

            $scope.hasReflected = false;
            $scope.showAbsorbed = true;
            $scope.showReflected = true;
            $scope.showImpact = true;
            $scope.showConductors = true;

            // to speed renders, only draw lines between every <joinEvery> data points
            function getJoinEvery() {
                return appState.models.particle3d.joinEvery || 1;
            }

            // these are in screen/vtk coords, not lab coords
            var axes = {
                x: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh, utilities),
                y: layoutService.plotAxis($scope.margin, 'y', 'left', refresh, utilities),
                z: layoutService.plotAxis($scope.margin, 'z', 'bottom', refresh, utilities)
            };

            // rendering
            var fsRenderer = null;
            var renderWindow = null;
            var mainView = null;
            var renderer = null;
            var cam = null;
            var camPos = [0, 0, 1];
            var camViewUp = [0, 1, 0];

            // planes
            var startPlaneActor = null;
            var startPlaneMapper = null;
            var startPlaneSource = null;
            var endPlaneActor = null;
            var endPlaneMapper = null;
            var endPlaneSource = null;
            var gridPlaneSources = [];
            var gridPlaneActors = [];

            // conductors (boxes)
            var conductorActors = [];

            // lines
            var lineActors = [];
            var reflectedLineActors = [];

            // spheres
            var impactSphereActors = [];
            var fieldSphereActors = [];

            // outline
            var outlineSource = null;
            var outlineMapper = null;
            var outlineActor = null;

            // orientation cube
            var orientationMarker = null;

            // geometry
            var coordMapper = vtkPlotting.coordMapper();

            // data
            var numPoints = 0;
            var pointRanges = {};
            var pointData = {};
            var fieldData = {};
            var xmin = 0.0;  var xmax = 1.0;
            var ymin = 0.0;  var ymax = 1.0;
            var zmin = 0.0;  var zmax = 1.0;

            // these are randomly generated in python for now
            var ypoints = pointData.z_points;

            var heatmap = [];
            var fieldXFactor = 1.0;
            var fieldZFactor = 1.0;
            var fieldYFactor = 1.0;
            var fieldColorScale = null;
            var indexMaps = [];
            //var pts;

            //var xfactor = 1;  var zfactor = 1;  var yfactor = 1;

            var minZSpacing = Number.MAX_VALUE;

            // normFactor scales all data to a reasonable viewing size
            //var normFactor = 1.0;
            //var impactSphereSize = 0.0125 * normFactor * X_Z_ASPECT_RATIO;
            var impactSphereSize = 0.0125 * X_Z_ASPECT_RATIO;
            var zoomUnits = 0;
            var didPan = false;
            var minZoomUnits = -256;
            var maxZoomUnits = 256;

            // colors - vtk uses a range of 0-1 for RGB components
            var zeroVoltsColor = [243.0/255.0, 212.0/255.0, 200.0/255.0];
            var voltsColor = [105.0/255.0, 146.0/255.0, 255.0/255.0];
            var particleTrackColor = [70.0/255.0, 130.0/255.0, 180.0/255.0];
            var reflectedParticleTrackColor = [224.0/255.0, 72.0/255.0, 54.0/255.0];

            document.addEventListener(utilities.fullscreenListenerEvent(), refresh);

            $scope.requestData = function() {
                //srdbg('p3d requestData');
                if (! $scope.hasFrames()) {
                    return;
                }
                frameCache.getFrame($scope.modelName, 0, false, function(index, data) {
                    if ($scope.element) {
                        if (data.error) {
                            panelState.setError($scope.modelName, data.error);
                            return;
                        }
                        panelState.setError($scope.modelName, null);
                        pointData = data;
                        frameCache.getFrame('fieldAnimation', 0, false, function(index, data) {
                            if ($scope.element) {
                                if (data.error) {
                                    panelState.setError($scope.modelName, data.error);
                                    return;
                                }
                                panelState.setError($scope.modelName, null);
                                fieldData = data;
                                $scope.load();
                            }
                        });
                    }
                });
            };

            $scope.init = function() {
                //srdbg('p3d init', $scope);
                d3self = d3.selectAll($element);

                var rw = angular.element($($element).find('.sr-plot-particle-3d .vtk-canvas-holder'))[0];
                fsRenderer = vtk.Rendering.Misc.vtkFullScreenRenderWindow.newInstance({ background: [1, 1, 1, 1], container: rw });
                renderer = fsRenderer.getRenderer();
                renderer.getLights()[0].setLightTypeToSceneLight();
                renderWindow = fsRenderer.getRenderWindow();
                mainView = renderWindow.getViews()[0];

                cam = renderer.get().activeCamera;

                var rwInteractor = renderWindow.getInteractor();
                var zoomObserver = vtk.Rendering.Core.vtkInteractorObserver.newInstance({
                    interactor: rwInteractor,
                    subscribedEvents: ['StartPinch']
                });
                zoomObserver.setInteractor(rwInteractor);

                rw.addEventListener('dblclick', reset);

                var minDist = 4.0;
                var minDistSq = minDist * minDist;
                var maxDist = 14.0;
                var maxDistSq = maxDist * maxDist;
                var lastVU = [];
                var lastFP = [];
                var lastPos = [0,0,0];
                var newPos = [0,0,0];

                var worldCoord = vtk.Rendering.Core.vtkCoordinate.newInstance({
                    renderer: renderer
                });
                worldCoord.setCoordinateSystemToWorld();

                var isDragging = false;
                rw.onpointerdown = function(evt) {
                    isDragging = true;
                };
                rw.onpointermove = function(evt) {
                    if(! isDragging) {
                        return;
                    }
                    didPan = didPan || evt.shiftKey;
                    $scope.side = null;
                    utilities.debounce(refresh, 100)();
                };
                rw.onpointerup = function(evt) {
                    lastPos = cam.getPosition();
                    isDragging = false;
                    refresh();
                };
                rw.onwheel = function (evt) {
                    var camPos = cam.getPosition();
                    var absPos = [Math.abs(camPos[0]), Math.abs(camPos[1]), Math.abs(camPos[2])];
                    var camDistSq = camPos[0] * camPos[0] + camPos[1] * camPos[1] + camPos[2] * camPos[2];
                    var camVU = cam.getViewUp();
                    var camFP = cam.getFocalPoint();
                    var adjZ = 0.0;
                    var adjCoord = 0.0;

                    /*
                    if(evt.deltaY < 0) {
                        //if(camDistSq < minDistSq) {
                        if(zoomUnits < minZoomUnits) {
                            //srdbg('TOO BIG!', camDistSq);
                            newPos = [lastPos[0], lastPos[1], lastPos[2]];
                            //srdbg('old dist', camDistSq, 'will set pos to', newPos);
                            cam.setPosition(newPos[0], newPos[1], newPos[2]);
                        }
                        else {
                            zoomUnits += evt.deltaY;
                        }
                    }
                    else {
                        //if(camDistSq > maxDistSq) {
                            //srdbg('TOO SMALL!', camDistSq);
                            var maxComponent = Math.max.apply(null, absPos);
                            var maxCIndex = absPos.indexOf(maxComponent);
                            var maxCSign = camPos[maxCIndex] / absPos[maxCIndex];
                            //srdbg('biggest component', maxCIndex, maxComponent, maxCSign);
                            //if(Math.abs(maxComponent) > maxDist) {
                            if(zoomUnits > maxZoomUnits) {
                                //srdbg('TOO SMALL!', camDistSq);
                                newPos = [lastPos[0], lastPos[1], lastPos[2]];
                                newPos[maxCIndex] = maxCSign * maxDist;
                                //srdbg('old dist', camDistSq, 'will set pos to', newPos);
                                cam.setPosition(newPos[0], newPos[1], newPos[2]);
                            }
                            else {
                                zoomUnits += evt.deltaY;
                            }
                        //}
                    }
                    */
                    zoomUnits += evt.deltaY;
                    //srdbg('cam pos now:', cam.getPosition(), 'fp:', camFP, 'vu:', camVU);
                    //srdbg('cam dist now:', camDistSq);
                    //srdbg('zoom units now:', zoomUnits);
                    //srdbg('dist to viewplane now', viewPlane.distanceToPlane(cam.getPosition()));
                    lastVU = camVU;
                    lastFP = camFP;
                    lastPos = cam.getPosition();

                    utilities.debounce(refresh, 100)();
                };

                // the emitter plane
                startPlaneMapper = vtk.Rendering.Core.vtkMapper.newInstance();
                startPlaneActor = vtk.Rendering.Core.vtkActor.newInstance();
                //startPlaneActor.getProperty().setEdgeVisibility(true);
                startPlaneActor.getProperty().setColor(zeroVoltsColor[0], zeroVoltsColor[1], zeroVoltsColor[2]);
                startPlaneActor.getProperty().setLighting(false);
                startPlaneSource = vtk.Filters.Sources.vtkPlaneSource.newInstance({ xResolution: 8, yResolution: 8 });
                startPlaneMapper.setInputConnection(startPlaneSource.getOutputPort());
                startPlaneActor.setMapper(startPlaneMapper);
                renderer.addActor(startPlaneActor);

                // the collector plane
                endPlaneMapper = vtk.Rendering.Core.vtkMapper.newInstance();
                endPlaneActor = vtk.Rendering.Core.vtkActor.newInstance();
                //endPlaneActor.getProperty().setEdgeVisibility(true);
                endPlaneActor.getProperty().setColor(voltsColor[0], voltsColor[1], voltsColor[2]);
                endPlaneActor.getProperty().setLighting(false);
                endPlaneSource = vtk.Filters.Sources.vtkPlaneSource.newInstance({ xResolution: 8, yResolution: 8 });
                endPlaneMapper.setInputConnection(endPlaneSource.getOutputPort());
                endPlaneActor.setMapper(endPlaneMapper);
                renderer.addActor(endPlaneActor);

                // a box around the elements, for visual clarity
                outlineMapper = vtk.Rendering.Core.vtkMapper.newInstance();
                outlineActor = vtk.Rendering.Core.vtkActor.newInstance();
                outlineSource = vtk.Filters.Sources.vtkCubeSource.newInstance();
                outlineActor.getProperty().setColor(1, 1, 1);
                outlineActor.getProperty().setEdgeVisibility(true);
                outlineActor.getProperty().setEdgeColor(0, 0, 0);
                //outlineActor.getProperty().setRepresentationToWireframe();
                outlineActor.getProperty().setFrontfaceCulling(true);
                outlineActor.getProperty().setLighting(false);

                outlineMapper.setInputConnection(outlineSource.getOutputPort());
                outlineActor.setMapper(outlineMapper);
                renderer.addActor(outlineActor);

                // a little widget that mirrors the orientation (not the scale) of the scence
                var oCubeActor = vtk.Rendering.Core.vtkAnnotatedCubeActor.newInstance();
                var axesActor = vtk.Rendering.Core.vtkAxesActor.newInstance();
                oCubeActor.setDefaultStyle({
                    text: '+Z',
                    fontStyle: 'bold',
                    fontFamily: 'Arial',
                    fontColor: 'black',
                    //fontSizeScale: function(res) { return res/2; },
                    faceColor: 'rgba(192, 192, 192, 0.5)',  //'#eeeeee',
                    faceRotation: 0,
                    edgeThickness: 0.05,
                    edgeColor: 'black',
                    resolution: 400,
                });
                oCubeActor.setXMinusFaceProperty({
                  text: '-Z',
                  //faceColor: '#ffff00',
                  //faceRotation: 90,
                  //fontStyle: 'italic',
                });
                oCubeActor.setYPlusFaceProperty({
                  text: '+X',
                  //faceColor: '#00ff00',
                  //fontSizeScale: function(res) { return res/4; },
                });
                oCubeActor.setYMinusFaceProperty({
                  text: '-X',
                  //faceColor: '#00ffff',
                  //fontColor: 'white',
                });
                oCubeActor.setZPlusFaceProperty({
                  text: '+Y',
                  //edgeColor: 'yellow',
                });
                oCubeActor.setZMinusFaceProperty({
                    text: '-Y',
                    //faceRotation: 45,
                    //edgeThickness: 0
                });

                orientationMarker = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
                    actor: axesActor, //oCubeActor,  // axesActor
                    interactor: renderWindow.getInteractor()
                });
                orientationMarker.setEnabled(true);
                orientationMarker.setViewportCorner(
                    vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.TOP_RIGHT
                );
                orientationMarker.setViewportSize(0.08);
                orientationMarker.setMinPixelSize(100);
                orientationMarker.setMaxPixelSize(300);

                // 6 grid planes indexed by dimension then side
                for(var d = 0; d < 3; ++d) {
                    var dps = [];
                    var dpa = [];
                    for(var s = 0; s < 1; ++s) {
                        var pm = vtk.Rendering.Core.vtkMapper.newInstance();
                        var pa  = vtk.Rendering.Core.vtkActor.newInstance();
                        //pa.getProperty().setColor(0.7, 0.7, 0.7);
                        pa.getProperty().setColor(0, 0, 0);
                        pa.getProperty().setLighting(false);
                        pa.getProperty().setRepresentationToWireframe();
                        var ps = vtk.Filters.Sources.vtkPlaneSource.newInstance();
                        dps.push(ps);
                        pm.setInputConnection(ps.getOutputPort());
                        pa.setMapper(pm);
                        renderer.addActor(pa);
                        dpa.push(pa);
                    }
                    gridPlaneSources.push(dps);
                    gridPlaneActors.push(dpa);
                }
            };

            $scope.load = function() {
                //srdbg('p3d load', pointData, fieldData);
                $scope.dataCleared = false;

                vtkPlotting.removeActors(renderer, lineActors);
                vtkPlotting.removeActors(renderer, reflectedLineActors);
                vtkPlotting.removeActors(renderer, impactSphereActors);
                vtkPlotting.removeActors(renderer, conductorActors);

                lineActors = [];
                reflectedLineActors = [];
                impactSphereActors = [];
                fieldSphereActors = [];
                conductorActors = [];

                if(!pointData) {
                    return;
                }

                var xpoints = pointData.points;
                xmin = pointData.y_range[0];
                xmax = pointData.y_range[1];

                var zpoints = pointData.x_points;
                zmin = pointData.x_range[0];
                zmax = pointData.x_range[1];

                // these are randomly generated in python for now
                var ypoints = pointData.z_points;
                ymin = pointData.z_range[0];
                ymax = pointData.z_range[1];

                var grid = appState.models.simulationGrid;
                var yzAspectRatio =  grid.channel_height / grid.channel_width;
                var pointScales = {
                    //z: normFactor / Math.abs((zmax - zmin)),
                    //x: normFactor * X_Z_ASPECT_RATIO / Math.abs((xmax - xmin)),
                    //y: normFactor * yzAspectRatio * X_Z_ASPECT_RATIO / Math.abs((ymax - ymin))
                    z: 1.0 / Math.abs((zmax - zmin)),
                    x: 1.0 * X_Z_ASPECT_RATIO / Math.abs((xmax - xmin)),
                    y: 1.0 * yzAspectRatio * X_Z_ASPECT_RATIO / Math.abs((ymax - ymin))
                };
                pointRanges = {
                    z: {min: zmin, max: zmax},
                    x: {min: xmin, max: xmax},
                    y: {min: ymin, max: ymax}
                };

                // vtk makes things fit so it does not particularly care about the
                // absolute sizes of things - except that really small values (e.g. 10^-7) don't scale
                // up properly.  We use these scaling factors to overcome that problem
                coordMapper = warpVTKService.warpCoordMapper([pointScales.x, pointScales.y, pointScales.z]);

                coordMapper.setPlane(startPlaneSource,
                    [xmin, ymin, zmin],
                    [xmin, ymax, zmin],
                    [xmax, ymin, zmin]
                );
                coordMapper.setPlane(endPlaneSource,
                    [xmin, ymin, zmax],
                    [xmin, ymax, zmax],
                    [xmax, ymin, zmax]
                );

                var padding = 0.01;  // * normFactor;
                var spsOrigin = startPlaneSource.getOrigin();
                var epsOrigin = endPlaneSource.getOrigin();
                var epsP1 = endPlaneSource.getPoint1();
                var epsP2 = endPlaneSource.getPoint2();

                var osXLen = Math.abs(epsOrigin[0] - spsOrigin[0]) + padding;
                var osYLen = Math.abs(epsP2[1] - epsP1[1]) + padding;
                var osZLen = Math.abs(epsP2[2] - epsP1[2]) + padding;
                var osCtr = [
                    (epsOrigin[0] - spsOrigin[0]) / 2.0,
                    (epsOrigin[1] - spsOrigin[1]) / 2.0,
                    (epsOrigin[2] - spsOrigin[2]) / 2.0
                ];
                outlineSource.setXLength(osXLen);
                outlineSource.setYLength(osYLen);
                outlineSource.setZLength(osZLen);
                outlineSource.setCenter(osCtr);

                //var oaBounds = outlineActor.getBounds();
                //var ospd = outlineSource.getOutputData().getPolys().getTuple();
                //srdbg('outlinesource', osCtr, osXLen, osYLen, osZLen, oaBounds);


                for(var d = 0; d < 3; ++d) {
                    for(var s = 0; s < 1; ++s) {
                        var ps = gridPlaneSources[d][s];
                        var pa = gridPlaneActors[d][s];
                        var gpOrigin = s == 0 ?
                            [osCtr[0] - osXLen/2.0, osCtr[1] - osYLen/2.0, osCtr[2] - osZLen/2.0] :
                            [osCtr[0] + osXLen/2.0, osCtr[1] + osYLen/2.0, osCtr[2] + osZLen/2.0];
                        var gpP1 = [0,0,1];
                        var gpP2 = [0,1,0];
                        switch (2*d + s) {
                            // bottom
                            case 0:
                                gpP1 = [osCtr[0] + osXLen/2.0, osCtr[1] - osYLen/2.0, osCtr[2] - osZLen/2.0];
                                gpP2 = [osCtr[0] - osXLen/2.0, osCtr[1] - osYLen/2.0, osCtr[2] + osZLen/2.0];
                                break;
                            // top
                            case 1:
                                gpP1 = [osCtr[0] - osXLen/2.0, osCtr[1] + osYLen/2.0, osCtr[2] + osZLen/2.0];
                                gpP2 = [osCtr[0] + osXLen/2.0, osCtr[1] + osYLen/2.0, osCtr[2] - osZLen/2.0];
                                break;
                            // left
                            case 2:
                                gpP1 = [osCtr[0] - osXLen/2.0, osCtr[1] - osYLen/2.0, osCtr[2] + osZLen/2.0];
                                gpP2 = [osCtr[0] - osXLen/2.0, osCtr[1] + osYLen/2.0, osCtr[2] - osZLen/2.0];
                                break;
                            // right
                            case 3:
                                gpP1 = [osCtr[0] + osXLen/2.0, osCtr[1] + osYLen/2.0, osCtr[2] - osZLen/2.0];
                                gpP2 = [osCtr[0] + osXLen/2.0, osCtr[1] - osYLen/2.0, osCtr[2] + osZLen/2.0];
                                break;
                            // back
                            case 4:
                                gpP1 = [osCtr[0] + osXLen/2.0, osCtr[1] - osYLen/2.0, osCtr[2] - osZLen/2.0];
                                gpP2 = [osCtr[0] - osXLen/2.0, osCtr[1] + osYLen/2.0, osCtr[2] - osZLen/2.0];
                                break;
                            // front
                            case 5:
                                gpP1 = [osCtr[0] - osXLen/2.0, osCtr[1] + osYLen/2.0, osCtr[2] + osZLen/2.0];
                                gpP2 = [osCtr[0] + osXLen/2.0, osCtr[1] - osYLen/2.0, osCtr[2] + osZLen/2.0];
                                break;
                            default:
                                break;
                        }
                        // all coords are within vtk, so use the default (identity) coordMapper
                        vtkPlotting.coordMapper().setPlane(ps, gpOrigin, gpP1, gpP2);
                    }
                }

                var joinEvery =  getJoinEvery();

                // evenly spaced points to be linearly interpolated between the data, for
                // purposes of coloring lines with the field colors
                var numInterPoints = 50;

                axes.x.init();
                axes.x.svgAxis.tickSize(0);
                axes.x.values = plotting.linspace(zmin, zmax, zpoints.length);
                axes.x.scale.domain([zmin, zmax]);
                axes.x.parseLabelAndUnits(pointData.x_label);

                axes.y.init();
                axes.y.svgAxis.tickSize(0);
                axes.y.values = plotting.linspace(xmin, xmax, xpoints.length);
                axes.y.scale.domain([xmin, xmax]);
                axes.y.parseLabelAndUnits(pointData.y_label);

                axes.z.init();
                axes.z.svgAxis.tickSize(0);
                axes.z.values = plotting.linspace(ymin, ymax, ypoints.length);
                axes.z.scale.domain([ymin, ymax]);
                axes.z.parseLabelAndUnits(pointData.z_label);

                minZSpacing = Math.abs((zmax - zmin)) / numInterPoints;
                var nearestIndex = 0;
                indexMaps = [];
                for(var i = 0; i < zpoints.length; ++i) {
                    var zArr = zpoints[i];  var yArr = ypoints[i];  var xArr = xpoints[i];
                    var l = zArr.length;

                    var newIndexMap = {0:0};
                    var lastNearestIndex = 0;
                    nearestIndex = joinEvery;
                    var newZ = zArr[0];
                    var finalZ = zArr[zArr.length-1];
                    var j = 1;
                    while (newZ <= finalZ) {  // ASSUMES MONOTONICALLY INCREASING
                        newZ = zArr[0] + j * minZSpacing;
                        nearestIndex = joinEvery;  // start at the beginning
                        lastNearestIndex = joinEvery;
                        var checkZ = zArr[nearestIndex];
                        while (nearestIndex < zArr.length && checkZ < newZ) {
                            if(! newIndexMap[nearestIndex]) {
                                // ensures we don't skip any indices, mapping them to the nearest previously mapped value
                                newIndexMap[nearestIndex] = indexValPriorTo(newIndexMap, nearestIndex, joinEvery) || 0;
                            }
                            nearestIndex += joinEvery;
                            checkZ = zArr[nearestIndex];
                        }
                        if(nearestIndex != lastNearestIndex) {
                            lastNearestIndex = nearestIndex;
                        }
                        var lowIndex = Math.max(0, nearestIndex - joinEvery);
                        var highIndex = Math.min(zArr.length-1, nearestIndex);
                        var z = zArr[lowIndex];
                        var nextZ = zArr[highIndex];
                        var y = yArr[lowIndex];
                        var nextY = yArr[highIndex];
                        var x = xArr[lowIndex];
                        var nextX = xArr[highIndex];

                        // linear interpolation
                        var dx = nextX - x;
                        var dy = nextY - y;
                        var dz = nextZ - z;
                        var newX = dz ? x + (newZ - z) * dx / dz : x;
                        var newY = dz ? y + (newZ - z) * dy / dz : y;

                        zArr.splice(lowIndex+1, 0, newZ);
                        yArr.splice(lowIndex+1, 0, newY);
                        xArr.splice(lowIndex+1, 0, newX);

                        newIndexMap[highIndex] = j;
                        ++j;
                    }  // END WHILE
                    newIndexMap[zArr.length-1] = indexValPriorTo(newIndexMap, nearestIndex, joinEvery);
                    indexMaps.push(newIndexMap);
                }  // end loop over partcles

                // distribute the heat map evenly over the interpolated points
                heatmap = appState.clone(fieldData.z_matrix).reverse();
                var hm_zlen = heatmap.length;
                var hm_xlen = heatmap[0].length;
                var hm_ylen = numInterPoints;
                fieldXFactor = hm_xlen / numInterPoints;
                fieldZFactor = hm_zlen / numInterPoints;
                fieldYFactor = hm_ylen / numInterPoints;

                var hm_zmin = Math.max(0, plotting.min2d(heatmap));
                var hm_zmax = plotting.max2d(heatmap);
                fieldColorScale = plotting.colorScaleForPlot({ min: hm_zmin, max: hm_zmax }, 'fieldAnimation');

                buildLineActorsFromPoints(xpoints, ypoints, zpoints, null, true);
                if (pointData.lost_x) {
                    $scope.hasReflected = pointData.lost_x.length > 0;
                    buildLineActorsFromPoints(pointData.lost_y, pointData.lost_z, pointData.lost_x, reflectedParticleTrackColor, false);
                }

                // build conductors -- make them a tiny bit small so the edges do not bleed into each other
                var shave = 0.001;
                for(var cIndex = 0; cIndex < appState.models.conductors.length; ++cIndex) {
                    var conductor = appState.models.conductors[cIndex];

                    // lengths and centers are in µm
                    var cFactor = 1000000.0;
                    var cModel = null;
                    var cColor = [0, 0, 0];  var cEdgeColor = [0, 0, 0];
                    for(var ctIndex = 0; ctIndex < appState.models.conductorTypes.length; ++ctIndex) {
                        if(appState.models.conductorTypes[ctIndex].id == conductor.conductorTypeId) {
                            cModel = appState.models.conductorTypes[ctIndex];
                            cColor = cModel.voltage == 0 ? zeroVoltsColor : voltsColor;
                            break;
                        }
                    }
                    if(cModel) {

                        var zl = (1.0 - shave) * cModel.zLength / cFactor;
                        var xl = (1.0 - shave) * cModel.xLength / cFactor;
                        var zc = (1.0 - shave) * conductor.zCenter / cFactor;
                        var xc = conductor.xCenter / cFactor;
                        var yl = Math.abs(ymax - ymin);
                        var yc = ymin + (ymax - ymin) / 2.0;

                        var bs = coordMapper.buildBox([xl, yl, zl], [xc, yc, zc]);
                        var bm = vtk.Rendering.Core.vtkMapper.newInstance();
                        bm.setInputConnection(bs.getOutputPort());

                        var ba = vtk.Rendering.Core.vtkActor.newInstance();
                        ba.getProperty().setColor(cColor[0], cColor[1], cColor[2]);
                        ba.getProperty().setEdgeVisibility(true);
                        ba.getProperty().setEdgeColor(cEdgeColor[0], cEdgeColor[1], cEdgeColor[2]);
                        ba.getProperty().setLighting(false);
                        ba.getProperty().setOpacity(0.80);
                        ba.setMapper(bm);
                        conductorActors.push(ba);
                    }
                }

                refresh();
            };

            /*
            function addActors(actorArr) {
                for(var aIndex = 0; aIndex < actorArr.length; ++aIndex) {
                    renderer.addActor(actorArr[aIndex]);
                }
            }
            function removeActors(actorArr) {
                for(var aIndex = 0; aIndex < actorArr.length; ++aIndex) {
                    renderer.removeActor(actorArr[aIndex]);
                }
            }
            */
            function buildLineActorsFromPoints(xpoints, ypoints, zpoints, color, includeImpact) {
                var joinEvery = getJoinEvery();
                var x = 0.0;  var y = 0.0;  var z = 0.0;
                var nextX = 0.0;  var nextY = 0.0;  var nextZ = 0.0;
                var k = 0;
                for (var i = 0; i < zpoints.length; ++i) {
                    var l = zpoints[i].length;
                    for (var j = 0; j < l; j += joinEvery) {
                        z = zpoints[i][j];
                        x = xpoints[i][j];
                        y = ypoints[i][j];
                        ++numPoints;
                        if (j < l - joinEvery) {
                            k = j + joinEvery;
                            nextZ = zpoints[i][k];
                            nextX = xpoints[i][k];
                            nextY = ypoints[i][k];
                            lineActors.push(coordMapper.buildLine([x, y, z], [nextX, nextY, nextZ], color || colorAtIndex(indexMaps[i][j])));
                        }
                    }
                    if(l - 1 > j - joinEvery) {
                        k = j - joinEvery;
                        z = zpoints[i][k];
                        x = xpoints[i][k];
                        y = ypoints[i][k];
                        nextZ = zpoints[i][l - 1];
                        nextX = xpoints[i][l - 1];
                        nextY = ypoints[i][l - 1];
                        ++numPoints;
                        lineActors.push(coordMapper.buildLine([x, y, z], [nextX, nextY, nextZ], color || colorAtIndex(indexMaps[i][j - joinEvery])));
                    }
                    if(includeImpact) {
                        k = xpoints[i].length - 1;
                        var lastZ = zpoints[i][k];
                        var lastX = xpoints[i][k];
                        var lastY = ypoints[i][k];
                        impactSphereActors.push(coordMapper.buildSphere([lastX, lastY, lastZ], impactSphereSize, color || colorAtIndex(indexMaps[i][k])));
                    }
                }
            }
            function indexValPriorTo(map, startIndex, spacing) {
                var k = startIndex - spacing;
                var prevVal = map[k];
                while(k >= 0 && (prevVal == null || prevVal === 'undefined')) {
                    k -= spacing;
                    prevVal = map[k];
                }
                return prevVal;
            }
            function colorAtIndex(index) {
                var fieldxIndex = Math.min(heatmap[0].length-1, Math.floor(fieldXFactor * index));
                var fieldzIndex = Math.min(heatmap.length-1, Math.floor(fieldZFactor * index));
                var fieldyIndex = Math.floor(fieldYFactor * index);
                //return colorsFromHexString(fieldColorScale(heatmap[fieldzIndex][fieldxIndex]));
                return plotting.colorsFromHexString(fieldColorScale(heatmap[fieldzIndex][fieldxIndex]), 255.0);
            }
            // accepts a string of the form '#abcdef' and returns an array of rgb values ranging from 0-1
            //function colorsFromHexString(color) {
                //var hexColor = color.substring(1, color.length);
                //return [parseInt(hexColor.substring(0,2), 16) / 255.0, parseInt(hexColor.substring(2,4), 16) / 255.0, parseInt(hexColor.substring(4,6), 16) / 255.0];
            //    return plotting.colorsFromHexString(color, 255.0);
            //}

            $scope.vtkCanvasGeometry = function() {
                var vtkCanvasHolder = $($element).find('.vtk-canvas-holder')[0];
                return {
                    pos: $(vtkCanvasHolder).position(),
                    size: {
                        width: $(vtkCanvasHolder).width(),
                        height: $(vtkCanvasHolder).height()
                    }
                };
            };
            $scope.axisGeometry = function() {
                var xaxis = $($element).find('.vtk-info-overlay .x.axis')[0];
                var yaxis = $($element).find('.vtk-info-overlay .y.axis')[0];
                var zaxis = $($element).find('.vtk-info-overlay .z.axis')[0];
                var g = {
                    x: {
                        pos: $(xaxis).position(),
                        size: {
                            width: $(xaxis).width(),
                            height: $(xaxis).height()
                        }
                    },
                    y: {
                        pos: $(yaxis).position(),
                        size: {
                            width: $(yaxis).width(),
                            height: $(yaxis).height()
                        }
                    },
                    z: {
                        pos: $(zaxis).position(),
                        size: {
                            width: $(zaxis).width(),
                            height: $(zaxis).height()
                        }
                    }
                };
                return g;
            };

            // the values below take rotation into account
            $scope.labelGeometry = function() {
                var xlabel = d3.select('.vtk-info-overlay .x-axis-label');
                var ylabel = d3.select('.vtk-info-overlay .y-axis-label');
                var zlabel = d3.select('.vtk-info-overlay .z-axis-label');
                var xfs = utilities.fontSizeFromString(xlabel.style('font-size'));
                var yfs = utilities.fontSizeFromString(ylabel.style('font-size'));
                var zfs = utilities.fontSizeFromString(zlabel.style('font-size'));
                var g = {
                    x: {
                        pos: {
                            top: parseInt(xlabel.attr('y') || '0'),
                            left: parseInt(xlabel.attr('x') || '0')
                        },
                        size: {
                            width: xlabel.text().length * xfs,
                            height: xfs
                        }
                    },
                    y: {
                        pos: {
                            top: parseInt(ylabel.attr('x') || '0'),
                            left: parseInt(ylabel.attr('y') || '0')
                        },
                        size: {
                            width: yfs,
                            height: ylabel.text().length * yfs
                        }
                    },
                    z: {
                        pos: {
                            top: parseInt(zlabel.attr('x')),
                            left: parseInt(zlabel.attr('y'))
                        },
                        size: {
                            width: zfs,
                            height: zlabel.text().length * zfs
                        }
                    }
                };
                return g;
            };


            function refresh() {
                //srdbg('p3d refresh');
                var width = parseInt($($element).css('width')) - $scope.margin.left - $scope.margin.right;
                $scope.width = plotting.constrainFullscreenSize($scope, width, X_Z_ASPECT_RATIO);
                $scope.height = X_Z_ASPECT_RATIO * $scope.width;

                var vtkCanvasHolderSize = {
                    width: $('.vtk-canvas-holder').width(),
                    height: $('.vtk-canvas-holder').height()
                };
                var vtkCanvasHolderBounds = {
                    left: $scope.axesMargins.x.width,
                    top: $scope.axesMargins.y.height,
                    right: vtkCanvasHolderSize.width - $scope.axesMargins.x.width,
                    bottom: vtkCanvasHolderSize.height - $scope.axesMargins.y.height
                };
                var vtkCanvasSize = {
                    width: $scope.width + $scope.margin.left + $scope.margin.right,
                    height: $scope.height + $scope.margin.top + $scope.margin.bottom
                };
                var axisMax = {
                    x: vtkCanvasHolderSize.width - 2 * $scope.axesMargins.x.width,
                    y: vtkCanvasHolderSize.height - 2 * $scope.axesMargins.y.height,
                    z: 200,
                };

                // Note that vtk does not re-add actors to the renderer if they already exist
                vtkPlotting.addActors(renderer, lineActors);
                vtkPlotting.addActors(renderer, reflectedLineActors);
                vtkPlotting.addActors(renderer, conductorActors);
                vtkPlotting.addActors(renderer, impactSphereActors);

                vtkPlotting.showActors(renderWindow, lineActors, $scope.showAbsorbed);
                vtkPlotting.showActors(renderWindow, impactSphereActors, $scope.showAbsorbed && $scope.showImpact);
                vtkPlotting.showActors(renderWindow, reflectedLineActors, $scope.showReflected);
                vtkPlotting.showActors(renderWindow, conductorActors, $scope.showConductors, 0.80);

                // reset camera will negate zoom and pan but *not* rotation
                if(zoomUnits == 0 && ! didPan) {
                    renderer.resetCamera();
                }
                renderWindow.render();

                var osCenter = outlineSource.getCenter();
                var osLeftCenterOut = [osCenter[0] - 0.5 * outlineSource.getXLength(), osCenter[1], osCenter[2] + 0.5 * outlineSource.getZLength()];
                var osRightCenterOut = [osCenter[0] + 0.5 * outlineSource.getXLength(), osCenter[1], osCenter[2] + 0.5 * outlineSource.getZLength()];

                // outline corners - axes will adhere to the proper sides
                var osLeftBottomOut = [osCenter[0] - 0.5 * outlineSource.getXLength(), osCenter[1] - 0.5 * outlineSource.getYLength(), osCenter[2] + 0.5 * outlineSource.getZLength()];
                var osLeftTopOut = [osCenter[0] - 0.5 * outlineSource.getXLength(), osCenter[1] + 0.5 * outlineSource.getYLength(), osCenter[2] + 0.5 * outlineSource.getZLength()];
                var osRightTopOut = [osCenter[0] + 0.5 * outlineSource.getXLength(), osCenter[1] + 0.5 * outlineSource.getYLength(), osCenter[2] + 0.5 * outlineSource.getZLength()];
                var osRightBottomOut = [osCenter[0] + 0.5 * outlineSource.getXLength(), osCenter[1] - 0.5 * outlineSource.getYLength(), osCenter[2] + 0.5 * outlineSource.getZLength()];
                var osLeftBottomIn = [osCenter[0] - 0.5 * outlineSource.getXLength(), osCenter[1] - 0.5 * outlineSource.getYLength(), osCenter[2] - 0.5 * outlineSource.getZLength()];
                var osLeftTopIn = [osCenter[0] - 0.5 * outlineSource.getXLength(), osCenter[1] + 0.5 * outlineSource.getYLength(), osCenter[2] - 0.5 * outlineSource.getZLength()];
                var osRightTopIn = [osCenter[0] + 0.5 * outlineSource.getXLength(), osCenter[1] + 0.5 * outlineSource.getYLength(), osCenter[2] - 0.5 * outlineSource.getZLength()];
                var osRightBottomIn = [osCenter[0] + 0.5 * outlineSource.getXLength(), osCenter[1] - 0.5 * outlineSource.getYLength(), osCenter[2] - 0.5 * outlineSource.getZLength()];

                // put in array for ease of transformation
                var osCorners = [
                    osLeftBottomOut, osLeftTopOut, osRightTopOut, osRightBottomOut,
                    osLeftBottomIn, osLeftTopIn, osRightTopIn, osRightBottomIn
                ];

                var worldCoord = vtk.Rendering.Core.vtkCoordinate.newInstance({
                    renderer: renderer
                });
                worldCoord.setCoordinateSystemToWorld();

                // "vp" for "viewPort"
                var vpCorners = osCorners.map(function (corner) {
                    return localCoordFromWorld(worldCoord, corner);
                });

                // names are easier to think about
                var vpLeftBottomOut = vpCorners[0];
                var vpLeftBottomIn = vpCorners[4];
                var vpLeftTopOut = vpCorners[1];
                var vpLeftTopIn = vpCorners[5];

                var vpRightBottomOut = vpCorners[3];
                var vpRightBottomIn = vpCorners[7];
                var vpRightTopOut = vpCorners[2];
                var vpRightTopIn = vpCorners[6];

                // edges
                var vpBottomOut = [vpLeftBottomOut, vpRightBottomOut];
                var vpBottomIn = [vpLeftBottomIn, vpRightBottomIn];
                var vpTopOut = [vpLeftTopOut, vpRightTopOut];
                var vpTopIn = [vpLeftTopIn, vpRightTopIn];

                var vpLeftBottom = [vpLeftBottomOut, vpLeftBottomIn];
                var vpRightBottom = [vpRightBottomOut, vpRightBottomIn];
                var vpLeftTop = [vpLeftTopOut, vpLeftTopIn];
                var vpRightTop = [vpRightTopOut, vpRightTopIn];

                var vpLeftOut = [vpLeftBottomOut, vpLeftTopOut];
                var vpLeftIn = [vpLeftBottomIn, vpLeftTopIn];
                var vpRightOut = [vpRightBottomOut, vpRightTopOut];
                var vpRightIn = [vpRightBottomIn, vpRightTopIn];

                // arrays for axis handling
                var vpXEdges = [
                    vpBottomOut, vpBottomIn, vpTopOut, vpTopIn
                ];
                var vpYEdges = [
                    vpLeftOut, vpLeftIn, vpRightOut, vpRightIn
                ];
                var vpZEdges = [
                    vpBottomOut, vpBottomIn, vpTopOut, vpTopIn
                ];

                var vpLeftCenterOut = localCoordFromWorld(worldCoord, osLeftCenterOut);
                var vpRightCenterOut = localCoordFromWorld(worldCoord, osRightCenterOut);

                var lowestCorners = extrema(vpCorners, 1, 1);
                var leftmostCorners = extrema(vpCorners, 0, 0);
                var highestCorners = extrema(vpCorners, 1, 0);
                var rightmostCorners = extrema(vpCorners, 0, 1);

                //srdbg('low corners', lowestCorners, 'left corners', leftmostCorners);

                var edges = edgesWithCorners(vpXEdges, lowestCorners)[0];
                var isXReversed = edges[0][0] > edges[1][0];
                // x-direction limits, sorted left to right
                var sceneXEnds = sortInDimension(edges, 0);
                // points where the x limits intersect the screen boundaries
                var screenXEnds = boundsIntersections(vtkCanvasHolderBounds, sceneXEnds[0], sceneXEnds[1]);
                var sceneXLen = dist(sceneXEnds[0], sceneXEnds[1]);
                srdbg('edges', edges, 'scene', sceneXEnds, 'screen x ends', screenXEnds);
                /*
                if(lowestCorners.includes(vpLeftBottomOut) || lowestCorners.includes(vpRightBottomOut) ) {
                    //sceneXEnds = sortInDimension([vpLeftBottomOut, vpRightBottomOut], 0, 0);
                    srdbg('bottom out');
                }
                if(lowestCorners.includes(vpLeftBottomIn) || lowestCorners.includes(vpRightBottomIn) ) {
                    //sceneXEnds = [vpLeftBottomIn, vpRightBottomIn];
                    srdbg('bottom in');
                }
                if(lowestCorners.includes(vpLeftTopOut) || lowestCorners.includes(vpRightTopOut) ) {
                    //sceneXEnds = [vpLeftTopOut, vpRightTopOut];
                    srdbg('top out');
                }
                if(lowestCorners.includes(vpLeftTopIn) || lowestCorners.includes(vpRightTopIn) ) {
                    //sceneXEnds = [vpLeftTopIn, vpRightTopIn];
                    srdbg('top in');
                }
                */
                /*
                var bottomOutLen = Math.sqrt(
                    (vpLeftBottomOut[0] - vpRightBottomOut[0]) * (vpLeftBottomOut[0] - vpRightBottomOut[0]) +
                    (vpLeftBottomOut[1] - vpRightBottomOut[1]) * (vpLeftBottomOut[1] - vpRightBottomOut[1])
                );
                var bottomInLen = Math.sqrt(
                    (vpLeftBottomIn[0] - vpRightBottomIn[0]) * (vpLeftBottomIn[0] - vpRightBottomIn[0]) +
                    (vpLeftBottomIn[1] - vpRightBottomIn[1]) * (vpLeftBottomIn[1] - vpRightBottomIn[1])
                );
*/
                var leftOutLen = Math.sqrt(
                    (vpLeftTopOut[0] - vpLeftBottomOut[0]) * (vpLeftTopOut[0] - vpLeftBottomOut[0]) +
                    (vpLeftTopOut[1] - vpLeftBottomOut[1]) * (vpLeftTopOut[1] - vpLeftBottomOut[1])
                );
                var leftInLen = Math.sqrt(
                    (vpLeftTopIn[0] - vpLeftBottomIn[0]) * (vpLeftTopIn[0] - vpLeftBottomIn[0]) +
                    (vpLeftTopIn[1] - vpLeftBottomIn[1]) * (vpLeftTopIn[1] - vpLeftBottomIn[1])
                );

                //var vpWidth = bottomOutLen;  //Math.abs(vpRightCenterOut[0] - vpLeftCenterOut[0]);  // axisMax.x;  //
                //var vpHeight = Math.abs(vpLeftTopOut[1] - vpLeftBottomOut[1]); // axisMax.y;  //
                var dx = (vpLeftBottomIn[0] - vpLeftBottomOut[0]);
                var dy = (vpLeftBottomIn[1] - vpLeftBottomOut[1]);

                //var tanPsi = (vpLeftBottomOut[1] - vpRightBottomOut[1]) / (vpLeftBottomOut[0] - vpRightBottomOut[0]);
                var tanPsi = (sceneXEnds[0][1] - sceneXEnds[1][1]) / (sceneXEnds[0][0] - sceneXEnds[1][0]);
                var psi = 180 * Math.atan(tanPsi) / Math.PI;
                var psiMod = Math.abs(psi) % 180;
                $scope.xAxisAngle = psi;

                var tanPhi = (vpLeftBottomIn[1] - vpLeftTopIn[1]) / (vpLeftBottomIn[0] - vpLeftTopIn[0]);
                var phi = 180 * Math.atan(tanPhi) / Math.PI - 90;
                if(phi < -90 ) {
                    phi += 180;
                }
                var tanPhiComp = Math.tan(Math.PI * phi / 180);
                $scope.yAxisAngle = phi;

                var vpDepth = Math.sqrt(dx * dx + dy * dy);  //200;
                var tanTheta = (vpLeftBottomOut[1] - vpLeftBottomIn[1]) / (vpLeftBottomOut[0] - vpLeftBottomIn[0]);
                var theta = 180 * Math.atan(tanTheta) / Math.PI;
                $scope.zAxisAngle = theta;

                //srdbg('psi phi theta', $scope.xAxisAngle, $scope.yAxisAngle, $scope.zAxisAngle);

                // vpWidth is the length of the x-direction of the scene
                //var vpWidth = theta <= 0 ? bottomOutLen : bottomInLen;  //Math.abs(vpRightCenterOut[0] - vpLeftCenterOut[0]);  // axisMax.x;  //
                var vpHeight = phi <= 0 ? leftOutLen : leftInLen;  //Math.abs(vpLeftTopOut[1] - vpLeftBottomOut[1]); // axisMax.y;  //

                var yAxisStartX = Math.min(
                    vtkCanvasHolderSize.width - $scope.axesMargins.x.width,
                    Math.max(Math.min(vpLeftTopOut[0], vpLeftTopIn[0]), $scope.axesMargins.x.width)
                );
                var yAxisStartY = Math.max(Math.min(vpLeftTopOut[1], vpLeftTopIn[1]), $scope.axesMargins.y.height);
                var yAxisProjXMax = yAxisStartX - tanPhiComp * (vtkCanvasHolderSize.height - $scope.axesMargins.y.height - yAxisStartY);
                var yAxisProjXMin = yAxisStartX + tanPhiComp * (yAxisStartY - $scope.axesMargins.y.height);
                var yAxisProjLen = Math.sqrt(
                    (yAxisProjXMax -  yAxisProjXMin) * (yAxisProjXMax -  yAxisProjXMin) +
                    (vtkCanvasHolderSize.height - 2.0 * $scope.axesMargins.y.height) * (vtkCanvasHolderSize.height - 2.0 * $scope.axesMargins.y.height)
                );
                //srdbg('y proj min', yAxisProjXMin, 'tan phi', tanPhi, 'phi', phi, 'proj max', yAxisProjXMax);

                $scope.yAxisTop = Math.max(Math.min(vpLeftTopOut[1], vpLeftTopIn[1]), $scope.axesMargins.y.height); // $scope.axesMargins.y.height;  //
                $scope.yAxisLeft = Math.min(
                    vtkCanvasHolderSize.width - $scope.axesMargins.x.width,
                    Math.max(Math.min(vpLeftTopOut[0], vpLeftTopIn[0]), $scope.axesMargins.x.width)
                );

                // These are the coordinates of each end of the scene, which may be off screen
                //var sceneXEnds1 = theta <= 0 ?
                //    (vpLeftBottomIn[0] < vpLeftBottomOut[0] ? vpLeftBottomIn : vpLeftBottomOut) :
                //    (vpLeftBottomIn[0] > vpLeftBottomOut[0] ? vpLeftBottomIn : vpLeftBottomOut);
                //var sceneXEnds2 = theta <= 0 ?
                //    (vpLeftBottomIn[0] < vpLeftBottomOut[0] ? vpRightBottomIn : vpRightBottomOut) :
                //    (vpLeftBottomIn[0] > vpLeftBottomOut[0] ? vpRightBottomIn : vpRightBottomOut);
                //var sceneXEnds = [sceneXEnds1, sceneXEnds2];
                //var screenXEnds = boundsIntersections(vtkCanvasHolderBounds, sceneXEnds1, sceneXEnds2);

                var clippedXEnds = [];
                for(var edge in screenXEnds) {
                    var p = screenXEnds[edge];
                    //srdbg(p, 'in', vtkCanvasHolderBounds, isPointWithinBounds(p,vtkCanvasHolderBounds));
                    //if(p[0] < vtkCanvasHolderBounds.left ||
                    //    p[0] > vtkCanvasHolderBounds.right ||
                    //    p[1] < vtkCanvasHolderBounds.top ||
                    //    p[1] > vtkCanvasHolderBounds.bottom
                    //) {
                    //    // point is outside the screen
                    //    continue;
                    //}
                    if(! isPointWithinBounds(p, vtkCanvasHolderBounds)) {
                        continue;
                    }

                    //if(p[0] == Infinity || p[1] == Infinity) {
                    //    continue;
                    //}

                    clippedXEnds.push(p);
                }
                srdbg('clipped', clippedXEnds);
                clippedXEnds = sortInDimension(clippedXEnds, 0, 0);
                srdbg('xaxis screen intersections', sceneXEnds, clippedXEnds);
                var xAxisProjLen = 0;
                if(clippedXEnds.length == 2) {
                    $scope.xAxisLeft = Math.max(sceneXEnds[0][0], clippedXEnds[0][0]);
                    $scope.xAxisTop = $scope.xAxisLeft == sceneXEnds[0][0] ? sceneXEnds[0][1] : clippedXEnds[0][1]; // Math.max(sceneXEnds[0][1], visibleXEnds[0][1]);
                    $scope.xAxisRight = Math.min(sceneXEnds[1][0], clippedXEnds[1][0]);
                    $scope.xAxisBottom = $scope.xAxisLeft == sceneXEnds[1][0] ? sceneXEnds[1][1] : clippedXEnds[1][1]; // Math.min(sceneXEnds[1][0], visibleXEnds[1][1]);
                    xAxisProjLen = Math.sqrt(
                        ($scope.xAxisRight - $scope.xAxisLeft) * ($scope.xAxisRight - $scope.xAxisLeft) +
                        ($scope.xAxisBottom - $scope.xAxisTop) * ($scope.xAxisBottom - $scope.xAxisTop)
                    );
                }

                //var xAxisStartX = theta <= 0 ? Math.min(vpLeftBottomIn[0], vpLeftBottomOut[0]) : Math.max(vpLeftBottomIn[0], vpLeftBottomOut[0]);
                var sceneXStartX = sceneXEnds[0][0];  var sceneXEndX = sceneXEnds[1][0];
                //var xAxisStartY = Math.max(vpLeftBottomIn[1], vpLeftBottomOut[1]);
                var sceneXStartY = sceneXEnds[0][1];  var sceneXEndY = sceneXEnds[1][1];

                // intersection of scene and screen boundaries
                var  sceneXScreenBottomY = vtkCanvasHolderSize.height - $scope.axesMargins.y.height;
               // var  sceneXScreenBottomX = sceneXStartX + (sceneXScreenBottomY - sceneXStartY) / tanPsi;
                var  sceneXScreenTopY = $scope.axesMargins.y.height;
                //var  sceneXScreenTopX = sceneXStartX + (sceneXScreenTopY - sceneXStartY) / tanPsi;

                var  sceneXScreenLeftX = $scope.axesMargins.x.width;
                var  sceneXScreenLeftY = sceneXStartY + tanPsi * (sceneXScreenLeftX - sceneXStartX);
                var  sceneXScreenRightX = vtkCanvasHolderSize.width - $scope.axesMargins.x.width;
                var  sceneXScreenRightY = sceneXStartY + tanPsi * (sceneXScreenRightX - sceneXStartX);



                // projection of the x-axis to the margins of the viewport
                var xAxisProjYMax = sceneXStartY + tanPsi * (vtkCanvasHolderSize.width - $scope.axesMargins.x.width - sceneXStartX);
                if(xAxisProjYMax > vtkCanvasHolderSize.width - $scope.axesMargins.y.height) {
                    if(tanPsi < 0) {  // low end of x axis intersects bottom of scene
                        //xAxisStartX = xAxisStartX + (xAxisProjYMax - xAxisStartY) / tanPsi;
                    }
                    //xAxisStartX = tanPsi != 0 ? $scope.axesMargins.x.width + (xAxisProjYMax - xAxisStartY) / tanPsi : $scope.axesMargins.x.width;
                    xAxisProjYMax = vtkCanvasHolderSize.width - $scope.axesMargins.y.height;
                }
                var xAxisProjYMin = sceneXStartY - tanPsi * (sceneXStartX - $scope.axesMargins.x.width);
                xAxisProjYMin = Math.max(xAxisProjYMin, $scope.axesMargins.y.height);
                //var xAxisProjLen = Math.sqrt(
                //    (xAxisProjYMax -  xAxisProjYMin) * (xAxisProjYMax -  xAxisProjYMin) +
                //    (vtkCanvasHolderSize.width - 2.0 * $scope.axesMargins.x.width) * (vtkCanvasHolderSize.width - 2.0 * $scope.axesMargins.x.width)
                //);
                //srdbg('x proj min', xAxisProjYMin, 'tan psi', tanPsi, 'psi', psi, 'proj max', xAxisProjYMax);
/*
                $scope.xAxisTop = Math.min(
                    Math.max(vpLeftBottomIn[1], vpLeftBottomOut[1]),
                    vtkCanvasHolderSize.height - $scope.axesMargins.y.height
                );
                $scope.xAxisLeft = Math.max(
                    $scope.axesMargins.x.width,
                    theta <= 0 ? Math.min(vpLeftBottomIn[0], vpLeftBottomOut[0]) : Math.max(vpLeftBottomIn[0], vpLeftBottomOut[0])
                );
*/
                var zAxisStartX = theta <= 0 ? Math.min(vpLeftBottomIn[0], vpLeftBottomOut[0]) : Math.max(vpLeftBottomIn[0], vpLeftBottomOut[0]);
                var zAxisStartY = Math.max(vpLeftBottomIn[1], vpLeftBottomOut[1]);
                var zAxisProjYMax = zAxisStartY + tanPsi * (vtkCanvasHolderSize.width - $scope.axesMargins.x.width - zAxisStartX);
                var zAxisProjYMin = zAxisStartY - tanPsi * (zAxisStartX - $scope.axesMargins.x.width);
                var zAxisProjLen = Math.sqrt(
                    (zAxisProjYMax -  zAxisProjYMin) * (zAxisProjYMax -  zAxisProjYMin) +
                    (vtkCanvasHolderSize.width - 2.0 * $scope.axesMargins.x.width) * (vtkCanvasHolderSize.width - 2.0 * $scope.axesMargins.x.width)
                );
                //srdbg('x proj min', xAxisProjYMin, 'tan psi', tanPsi, 'psi', psi, 'proj max', xAxisProjYMax);

                $scope.zAxisTop = Math.min(
                    Math.max(vpLeftBottomIn[1], vpLeftBottomOut[1]),
                    vtkCanvasHolderSize.height - $scope.axesMargins.y.height
                );
                $scope.zAxisLeft = Math.max(
                    $scope.axesMargins.x.width,
                    theta <= 0 ? Math.min(vpLeftBottomIn[0], vpLeftBottomOut[0]) : Math.max(vpLeftBottomIn[0], vpLeftBottomOut[0])
                );

                select('.vtk-canvas-holder svg')
                    .attr('width', vtkCanvasSize.width)
                    .attr('height', vtkCanvasSize.height);

                // domain is the value of the data points
                // range is the position on the screen
                // TODO (mvk): plotAxis should handle arbitrary rotated axes instead of doing it here
                //plotting.recalculateDomainFromPoints(axes.y.scale, points[0], axes.x.scale.domain());
                //var xrange = Math.min(vpWidth, axisMax.x);
                var xrange = Math.min(xAxisProjLen, sceneXLen);
                var newMin = zmin;  var newMax = zmax;  var domainPct = 0.0;
                var domainChanged = false;
                if(sceneXEnds[0][0] < vtkCanvasHolderBounds.left ) {
                    domainPct = (vtkCanvasHolderBounds.left - sceneXEnds[0][0]) / xrange;
                    newMin = zmin + (zmax - zmin) * domainPct;
                    domainChanged = true;
                }
                if(sceneXEnds[1][0] > vtkCanvasHolderBounds.right) {
                    domainPct = (sceneXEnds[1][0] - vtkCanvasHolderBounds.right ) / xrange;
                    newMax = zmax - (zmax - zmin) * domainPct;
                    domainChanged = true;
                }
                //srdbg('new min/max', newMin, newMax);
                if(domainChanged) {
                    axes.x.scale.domain([newMin, newMax]).nice();
                }
                //var isReversed = $scope.xAxisLeft > $scope.xAxisRight;
                //srdbg('xaxis reveresed?', isReversed);
                axes.x.scale.range([isXReversed ? xrange : 0, isXReversed ? 0 :xrange]);
                axes.x.updateLabelAndTicks({
                    width: xrange,
                    height: $scope.vtkCanvasGeometry().size.height
                }, select);
                var xl = 'translate(' +
                    Math.min($scope.xAxisLeft, $scope.xAxisRight) + ',' +
                    $scope.xAxisTop +') ' +
                    //($scope.labelGeometry().x.pos.top - $scope.labelGeometry().x.size.height - 24) +') ' +
                    'rotate(' + $scope.xAxisAngle + ')';
                select('.x.axis').attr('transform', xl);
                // counter-rotate the tick labels
                var xlabels = d3self.selectAll('.x.axis text');
                var maxXLabelLen = maxLabelLen(xlabels);

                xlabels.attr('transform', 'rotate(' +  (-$scope.xAxisAngle) + ')');
                select('.x.axis .domain').style({'stroke': 'none'});
                select('.x.axis').style('opacity', xrange < 50 ? 0.0 : 1.0);
                select('.x-axis-label').style('opacity', xrange < 50 ? 0.0 : 1.0);


                //var yrange = Math.min(vpHeight, axisMax.y);
                var yrange = Math.min(vpHeight, yAxisProjLen);
                axes.y.scale.range([yrange, 0]);
                axes.y.updateLabelAndTicks({
                    width: $scope.vtkCanvasGeometry().size.width,
                    height: yrange
                }, select);
                var yl = 'translate(' +
                    //($scope.labelGeometry().y.pos.left + $scope.labelGeometry().y.size.width + 32) + ',' +
                    $scope.yAxisLeft + ',' +
                    $scope.yAxisTop +') ' +
                    'rotate(' + $scope.yAxisAngle + ')';
                select('.y.axis').attr('transform', yl);
                d3self.selectAll('.y.axis text')
                    .attr('transform', 'rotate(' +  (-$scope.yAxisAngle) + ')');
                select('.y.axis .domain').style({'stroke': 'none'});
                select('.y.axis').style('opacity', yrange < 50 ? 0.0 : 1.0);

                axes.z.scale.range([0, vpDepth]);
                axes.z.updateLabelAndTicks({
                    width: vpDepth,
                    height: vpDepth
                }, select);
                select('.z.axis .domain').style({'stroke': 'none'});
                var zl = 'translate(' +
                    $scope.xAxisLeft + ',' +
                    //($scope.vtkCanvasGeometry().size.height - 64) +') ' +
                    ($scope.yAxisTop + vpHeight) + ') ' +
                    'rotate(' + $scope.zAxisAngle + ')';
                d3self.selectAll('.z.axis')
                    .attr('transform', zl);
                // counter-rotate the tick labels
                d3self.selectAll('.z.axis text')
                    .attr('transform', 'translate(24, -12) rotate(' +  (-$scope.zAxisAngle) + ') translate(8,0)');
                //select('.z.axis').style('opacity', vpDepth < 50 ? 0.0 : 1.0);

                //d3.selectAll('.z.axis line')
                //    .attr('transform', 'rotate(' +  (-(90 + $scope.zAxisAngle)) + ')');


                //refreshAxes();
                refreshGridPlanes();

                //var minPointRaw = [pointRanges.z.min, pointRanges.x.min, pointRanges.y.min];
                //var minPointRaw = [minPoint[0]/warpVTKService.zscale, minPoint[1]/warpVTKService.xscale, minPoint[2]/warpVTKService.yscale];
                //var minPointRaw = [zmin, xmin, ymin];
                //var axisLeftBottomOut = [axes.x.scale(minPointRaw[0]), axes.y.scale(minPointRaw[1]), axes.z.scale(minPointRaw[2])];
                //srdbg('minpt -> minpt raw -> osLeftBottomOut -> axisLeftBottomOut: ', minPoint, minPointRaw, osLeftBottomOut, axisLeftBottomOut);

                $scope.testBoxes = [

                    {
                        x: clippedXEnds[0][0],
                        y: clippedXEnds[0][1],
                        color: "red"
                    },
                    {
                        x: clippedXEnds[1][0],
                        y: clippedXEnds[1][1],
                        color: "blue"
                    },

/*
                    {
                        x: yAxisProjXMin,
                        y: $scope.axesMargins.y.height,
                        color: "red"
                    },
                    {
                        x: yAxisProjXMax,
                        y: vtkCanvasHolderSize.height - $scope.axesMargins.y.height,
                        color: "blue"
                    }
                    */
                ];
            }

            // TODO (mvk): most of this geometry should be moved to various plotting services

            // Finds the intersections of the line defined by the given points [x,y]
            // with the rectangle defined by the bounds {left, top, right, bottom}.
            // Any of the intersections could be outside the rectangle
            function boundsIntersections(bounds, startPoint, endPoint) {
                //srdbg('x of', startPoint, endPoint, 'with bounds', bounds);
                var startX = startPoint[0];  var startY = startPoint[1];
                var endX = endPoint[0];  var endY = endPoint[1];
                var infFactor = 1;

                // horizontal line
                if(startY == endY) {
                    //infFactor = startY < bounds.top || startY > bounds.bottom ? -1 : 1;
                    return {
                        left: [bounds.left, startY],
                        top: [infFactor * Infinity, bounds.top],
                        right: [bounds.right, endY],
                        bottom: [infFactor * Infinity, bounds.bottom]
                    };
                }
                // vertical line
                if(startX == endX) {
                    //infFactor = startX < bounds.left || startX > bounds.right ? -1 : 1;
                    return {
                        left: [bounds.left, infFactor * Infinity],
                        top: [startX, bounds.top],
                        right: [bounds.right, infFactor * Infinity],
                        bottom: [endX, bounds.bottom]
                    };
                }

                var m = (endY - startY) / (endX - startX);
                return {
                    left: [bounds.left, startY + m * (bounds.left - startX)],
                    top: [startX + (bounds.top - startY) / m, bounds.top],
                    right: [bounds.right, startY + m * (bounds.right - startX)],
                    bottom: [startX + (bounds.bottom - startY) / m, bounds.bottom]
                };
            }

            function isPointWithinBounds(p, b) {
                return p[0] >= b.left && p[0] <= b.right && p[1] >= b.top && p[1] <= b.bottom;
            }

            // Returns the point(s) that have the smallest (minMax == 0) or largest value in the given dimension
            function extrema(pArr, dim, loHi) {
                var sPArr = sortInDimension(pArr, dim, loHi);
                if(! sPArr) {
                    return null;
                }
                return sPArr.filter(function (point) {
                    return point[dim] == sPArr[0][dim];
                });
            }

            // Returns the members of an array of edges (point pairs) that
            // contain any of the points in another array
            function edgesWithCorners(edgeArr, pArr) {
                var edges = edgeArr.filter(function (edge) {
                    return edge.some(function (corner) {
                        return pArr.includes(corner);
                    });
                });
                return edges;
            }

            // Sort the point array by the values in the given dimension; reversed if loHi is
            // Array is cloned first so the original is unchanged
            function sortInDimension(pArr, dim, loHi) {
                if(!pArr || !pArr.length || dim >= pArr[0].length ) {
                    return null;
                }
                var pArrClone = pArr.slice(0);
                return pArrClone.sort(function (p1, p2) {
                    return loHi ? (p1[dim] < p2[dim]) : (p1[dim] >= p2[dim]);
                });
            }

            // returns the distance bewteen two (2d) points
            function dist(p1, p2) {
                return Math.sqrt(
                    (p2[0] - p1[0]) * (p2[0] - p1[0]) +
                    (p2[1] - p1[1]) * (p2[1] - p1[1])
                );
            }

            // display values seem to be double, not sure why
            function localCoordFromWorld(coord, point) {
                coord.setCoordinateSystemToWorld();
                coord.setValue(point);
                var lCoord = coord.getComputedLocalDisplayValue();
                return [lCoord[0] / 2.0, lCoord[1] / 2.0];
            }
            function worldCoordFromLocal(coord, point) {
                var newPoint = [2.0 * point[0], 2.0 * point[1]];
                // must first convert from "localDisplay" to "display"  - this is the inverse of
                // what is done by vtk to get from display to localDisplay
                var newPointView = [newPoint[0], mainView.getFramebufferSize()[1] - newPoint[1] - 1];
                //srdbg('localDisplay (y = size[1] - y\'- 1) -> display?:', newPoint, fbSize[1], newPointView);
                coord.setCoordinateSystemToDisplay();
                coord.setValue(newPointView);
                //srdbg('localDisplay -> world:', newPointView, wCoord);
                return coord.getComputedWorldValue();
            }

            function refreshAxes() {
            }

            // takes the result of a d3.selectAll
            function maxLabelLen(lSelect) {
                return Math.max.apply(null, lSelect[0].map(function (item) {
                    return item.textContent.length;
                }));
            }

            // Redraw the grid planes to match the number of tick marks
            // on the axes
            function refreshGridPlanes() {

                var numX = $($element).find('.x.axis .tick').length - 1;
                var numY = $($element).find('.y.axis .tick').length - 1;
                var numZ = $($element).find('.z.axis .tick').length - 1;
                for(var d = 0; d < 3; ++d) {
                    for(var s = 0; s < 1; ++s) {
                        var ps = gridPlaneSources[d][s];
                        var xres = 2;
                        var yres = 2;
                        switch (2*d + s) {
                            // bottom, top
                            case 0: case 1:
                                xres = numX;
                                yres = numZ;
                                break;
                            // left, right
                            case 2: case 3:
                                xres = numZ;
                                yres = numY;
                                break;
                            // back, front
                            case 4: case 5:
                                xres = numX;
                                yres = numY;
                                break;
                            default:
                                break;
                        }
                        ps.setXResolution(xres);
                        ps.setYResolution(yres);
                    }
                }
            }

            function reset() {
                //srdbg('reset');
                camPos = [0, 0, 1];
                camViewUp = [0, 1, 0];
                $scope.side = 'y';
                $scope.xdir = 1;  $scope.ydir = 1;  $scope.zdir = 1;
                resetCam();
            }
            function resetCam() {
                //srdbg('reset cam');
                cam.setPosition(camPos[0], camPos[1], camPos[2]);
                cam.setFocalPoint(0, 0, 0);
                cam.setViewUp(camViewUp[0], camViewUp[1], camViewUp[2]);
                cam.zoom(1.3);
                renderer.resetCamera();
                zoomUnits = 0;
                didPan = false;
                orientationMarker.updateMarkerOrientation();
                refresh();
            }

            function resetZoom() {
                //srdbg('p3d resetZoom');
            }

            $scope.clearData = function() {
            };

            $scope.destroy = function() {
                document.removeEventListener(utilities.fullscreenListenerEvent(), refresh);
                var rw = angular.element($($element).find('.sr-plot-particle-3d .vtk-canvas-holder'))[0];
                rw.removeEventListener('dblclick', reset);
            };


            $scope.resize = function() {
                //srdbg('resize');
                refresh();
            };

            $scope.toggleAbsorbed = function() {
                $scope.showAbsorbed = ! $scope.showAbsorbed;
                vtkPlotting.showActors(lineActors, $scope.showAbsorbed);
                vtkPlotting.showActors(impactSphereActors, $scope.showAbsorbed && $scope.showImpact);
            };
            $scope.toggleImpact = function() {
                $scope.showImpact = ! $scope.showImpact;
                vtkPlotting.showActors(impactSphereActors, $scope.showAbsorbed && $scope.showImpact);
            };
            $scope.toggleReflected = function() {
                $scope.showReflected = ! $scope.showReflected;
                vtkPlotting.showActors(reflectedLineActors, $scope.showReflected);
            };
            $scope.toggleConductors = function() {
                $scope.showConductors = ! $scope.showConductors;
                vtkPlotting.showActors(conductorActors, $scope.showConductors, 0.80);
            };


            $scope.xdir = 1;  $scope.ydir = 1;  $scope.zdir = 1;
            $scope.side = 'y';
            $scope.showSide = function(side) {
                var dir = side === 'x' ? $scope.xdir : (side === 'y' ? $scope.ydir : $scope.zdir);
                if( side == $scope.side ) {
                    dir *= -1;
                    if(side === 'x') {
                        $scope.xdir = dir;
                    }
                    if(side === 'y') {
                        $scope.ydir = dir;
                    }
                    if(side === 'z') {
                        $scope.zdir = dir;
                    }
                }
                $scope.side = side;

                camPos = side === 'x' ? [0, dir, 0] : (side === 'y' ? [0, 0, dir] : [dir, 0, 0] );
                camViewUp = side === 'x' ? [0, 0, 1] : [0, 1, 0];
                resetCam();
            };

            /*
            function showActors(actorArray, doShow, visibleOpacity, hiddenOpacity) {
                for(var aIndex = 0; aIndex < actorArray.length; ++aIndex) {
                    actorArray[aIndex].getProperty().setOpacity(doShow ? visibleOpacity || 1.0 : hiddenOpacity || 0.0);
                }
                renderWindow.render();
            }
            */

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }


        },

        link: function link(scope, element) {
            if (vtkService.vtk) {
                vtkService.vtk().then(function(vtk) {
                    plotting.vtkPlot(scope, element);
                });
            }
        },
    };
});

SIREPO.app.service('warpVTKService', function(vtkPlotting) {

    var svc = this;

    this.warpCoordMapper = function(scale) {
        return vtkPlotting.coordMapper(labToVTK(scale || [1.0, 1.0, 1.0]));
    };

    function labToVTK(scale) {
        return function (lpoint) {
            return [scale[2] * lpoint[2], scale[0] * lpoint[0], scale[1] * lpoint[1]];
        };
    }

    // TODO (mvk): this inverse transform should really be calculated not supplied
    function vtkToLab(scale) {
        return function (vpoint) {
            return [vpoint[1] / scale[0], vpoint[2] / scale[1], vpoint[0] / scale[2]];
        };
    }


});
