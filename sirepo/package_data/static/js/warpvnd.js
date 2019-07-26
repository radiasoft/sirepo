'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.PLOT_3D_CONFIG = {
    'coordMatrix': [[0, 0, 1], [1, 0, 0], [0, 1, 0]]
};
SIREPO.SINGLE_FRAME_ANIMATION = ['optimizerAnimation', 'fieldCalcAnimation', 'fieldComparisonAnimation'];
SIREPO.appReportTypes = [
    '<div data-ng-switch-when="conductorGrid" data-conductor-grid="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-id="reportId"></div>',
    '<div data-ng-switch-when="impactDensity" data-impact-density-plot="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
    '<div data-ng-switch-when="optimizerPath" data-optimizer-path-plot="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
].join('');
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="XCell" data-ng-class="fieldClass">',
      '<div data-cell-selector=""></div>',
    '</div>',
    '<div data-ng-switch-when="YCell" data-ng-class="fieldClass">',
      '<div data-cell-selector=""></div>',
    '</div>',
    '<div data-ng-switch-when="ZCell" data-ng-class="fieldClass">',
      '<div data-cell-selector=""></div>',
    '</div>',
    '<div data-ng-switch-when="Color" data-ng-class="fieldClass">',
      '<div data-color-picker="" data-color="model.color" data-default-color="model.isConductor === \'0\' ? \'#f3d4c8\' : \'#6992ff\'"></div>',
    '</div>',
    '<div data-ng-switch-when="OptimizationField" data-ng-class="fieldClass">',
      '<div data-optimization-field-picker="" field="field" data-model="model"></div>',
    '</div>',
].join('');
SIREPO.appImportText = 'Import an stl file';
SIREPO.app.factory('warpvndService', function(appState, panelState, plotting, vtkPlotting, $rootScope) {
    var self = {};
    var plateSpacing = 0;
    var rootScopeListener = null;

    function addOptimizeContainerFields(optFields, containerName, modelName, optFloatFields) {
        var idx = {};
        appState.models[containerName].forEach(function(m) {
            var name;
            if (m.name) {
                name = m.name;
            }
            else {
                var conductorTypeName = self.findConductorType(m.conductorTypeId).name;
                idx[conductorTypeName] = (idx[conductorTypeName] || 0) + 1;
                name = conductorTypeName + ' #' + idx[conductorTypeName];
            }
            $.each(m, function(fieldName, value) {
                var field = appState.optFieldName(modelName, fieldName, m);
                if (appState.models.optimizer.enabledFields[field]) {
                    var label = optFloatFields[appState.optFieldName(modelName, fieldName)];
                    optFields.push({
                        field: appState.optFieldName(modelName, fieldName, m),
                        label: name + ' ' + label,
                        value: m[fieldName],
                    });
                }
            });
        });
    }

    function addOptimizeModelFields(optFields) {
        var optFloatFields = {};

        // look through schema for OptFloat types which have been enabled
        $.each(SIREPO.APP_SCHEMA.model, function(modelName, modelInfo) {
            $.each(modelInfo, function(fieldName, fieldInfo) {
                if (fieldInfo[1] == 'OptFloat') {
                    var m = appState.models[modelName];
                    var field = appState.optFieldName(modelName, fieldName);
                    optFloatFields[field] = fieldInfo[0];
                    if (appState.models.optimizer.enabledFields[field]) {
                        optFields.push({
                            field: field,
                            label: fieldInfo[0],
                            value: m[fieldName],
                        });
                    }
                }
            });
        });
        return optFloatFields;
    }

    function cleanNumber(v) {
        v = v.replace(/\.0+(\D+)/, '$1');
        v = v.replace(/(\.\d)0+(\D+)/, '$1$2');
        v = v.replace(/(\.0+)$/, '');
        return v;
    }

    function findModelById(name, id) {
        var model = null;
        appState.models[name].some(function(m) {
            if (m.id == id) {
                model = m;
                return true;
            }
        });
        if (! model) {
            throw 'model not found: ' + name + ' id: ' + id;
        }
        return model;
    }

    function formatNumber(value, decimals) {
        decimals = decimals || 3;
        if (value) {
            if (Math.abs(value) < 1e3 && Math.abs(value) > 1e-3) {
                return cleanNumber(value.toFixed(decimals));
            }
            else {
                return cleanNumber(value.toExponential(decimals));
            }
        }
        return '' + value;
    }

    function gridRange(sizeField, countField) {
        var grid = appState.models.simulationGrid;
        var channel = grid[sizeField];
        return plotting.linearlySpacedArray(-channel / 2, channel / 2, grid[countField] + 1);
    }

    function realignConductors() {
        var v = appState.models.simulationGrid.plate_spacing;
        // realign conductors in relation to the right border
        if (plateSpacing && plateSpacing != v) {
            var diff = v - plateSpacing;
            appState.models.conductors.forEach(function(m) {
                m.zCenter = formatNumber(parseFloat(m.zCenter) + diff);
            });
            appState.saveChanges('conductors');
            plateSpacing = v;
        }
    }

    self.stlUnits = [1000, 1, 1e-3, 1e-6, 1e-9];
    self.stlNanoUnits = self.stlUnits.map(function (unit) {
        return 1e-9 / unit;
    });

    self.activeComparisonReport = function() {
        //return self.is3D() ? 'fieldComparisonAnimation' : 'fieldComparisonReport';
        return 'fieldComparisonAnimation';
    };

    self.activeFieldReport = function() {
        //return warpvndService.is3D() ? 'fieldCalcAnimation' : 'fieldReport';
        return 'fieldCalcAnimation';
    };

    self.allow3D = function() {
        return SIREPO.APP_SCHEMA.feature_config.allow_3d_mode;
    };

    self.buildOptimizeFields = function() {
        var optFields = [];
        var optFloatFields = addOptimizeModelFields(optFields);
        addOptimizeContainerFields(optFields, 'conductorTypes', 'box', optFloatFields);
        addOptimizeContainerFields(optFields, 'conductors', 'conductorPosition', optFloatFields);
        return optFields;
    };

    self.conductorTypeMap = function() {
        var res = {};
        appState.models.conductorTypes.forEach(function(m) {
            if(! m) {
                return;
            }
            res[m.id] = m;
        });
        return res;
    };

    self.findConductor = function(id) {
        return findModelById('conductors', id);
    };

    self.findConductorType = function(id) {
        return findModelById('conductorTypes', id);
    };

    self.formatNumber = formatNumber;

    self.getConductorType = function(conductor) {
        return (self.conductorTypeMap()[conductor.conductorTypeId].type) || 'box';
    };

    self.getXRange = function() {
        return gridRange('channel_width', 'num_x');
    };

    self.getYRange = function() {
        return gridRange('channel_height', 'num_y');
    };

    self.getZRange = function() {
        var grid = appState.models.simulationGrid;
        return plotting.linearlySpacedArray(0, grid.plate_spacing, grid.num_z + 1);
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

    self.setOptimizingRow = function(row) {
        var v = row ? row.slice(4) : null;
        if (! appState.deepEquals(v, self.optimizingRow)) {
            // this triggers a watch in optimizerPathPlot
            self.optimizingRow = v;
        }
    };

    appState.whenModelsLoaded($rootScope, function() {
        if (rootScopeListener) {
            rootScopeListener();
        }
        plateSpacing = appState.models.simulationGrid.plate_spacing;
        rootScopeListener = $rootScope.$on('simulationGrid.changed', realignConductors);
    });

    return self;
});


SIREPO.app.controller('SourceController', function (appState, frameCache, panelState, persistentSimulation, vtkPlotting, warpvndService, $scope) {
    var self = this;
    var MAX_PARTICLES_PER_STEP = 1000;
    var condctorTypes = SIREPO.APP_SCHEMA.enum.ConductorType.map(function (t) {
        return t[SIREPO.ENUM_INDEX_VALUE];
    });

    function importedConductorTypes(f) {
        return appState.models.conductorTypes.filter(function (t) {
            return t.type === 'stl' && t.file === f;
        });
    }

    // If this simulation was created by importing an stl file, we'll
    // add the type here.  Details get filled in later
    function initImportedConductor() {
        var f = appState.models.simulation.conductorFile;
        if (f) {
            var iTypes = importedConductorTypes(f);
            if (iTypes.length) {
                return;
            }
            vtkPlotting.loadSTLFile(f).then(function (r) {
                vtkPlotting.addSTLReader(f, r);
                var t = self.createConductorType('stl', true);
                t.file = f;
                t.name = f.substring(0, f.indexOf('.'));
                t.voltage = 0;
                var bounds = r.getOutputData().getBounds();
                t.scale = initScale(bounds);
                t.zLength = normalizeToum(Math.abs(bounds[5] - bounds[4]), t.scale);
                t.xLength = normalizeToum(Math.abs(bounds[1] - bounds[0]), t.scale);
                t.yLength = normalizeToum(Math.abs(bounds[3] - bounds[2]), t.scale);
                appState.models.simulationGrid.plate_spacing = Math.max(appState.models.simulationGrid.plate_spacing, t.zLength);
                appState.models.simulationGrid.channel_width = Math.max(appState.models.simulationGrid.channel_width, t.xLength);
                appState.models.simulationGrid.channel_height = Math.max(appState.models.simulationGrid.channel_height, t.yLength);

                // recommended cell counts for complex conductors
                //TODO(mvk): calculate sizes
                appState.models.simulationGrid.num_x = 64;
                appState.models.simulationGrid.num_y = 64;
                appState.models.simulationGrid.num_z = 64;
                appState.models.stl = t;

                // force centering in x, y (but not z)
                appState.saveChanges(['stl', 'simulationGrid'], function() {
                    var c = {
                        id: appState.maxId(appState.models.conductors) + 1,
                        conductorTypeId: t.id,
                        zCenter: normalizeToum(bounds[4], t.scale) + t.zLength / 2.0,
                        xCenter: 0.0,
                        yCenter: 0.0,
                    };
                    appState.models.conductors.push(c);
                    appState.saveChanges('conductors');
                });
            });
        }
    }

    // stl files can have arbitrary scale - we are using our knowledge of the problem space
    // to set the scale to something reasonable.  For example, an object with linear dimension
    // in the hundreds is assumed to be in nanometers, etc.  The user can adjust if it is wrong
    function initScale(bounds) {
        var minGridBounds = [0, 0, 0];
        for(var i = 0; i < bounds.length; i += 2) {
            minGridBounds[i / 2] = Math.abs(bounds[i + 1] - bounds[i]);
        }
        // adjust to accomodate smallest dimension (??)
        var maxmin = Math.min.apply(null, minGridBounds);
        for(var j in warpvndService.stlUnits) {
            var unit = warpvndService.stlUnits[j];
            if (maxmin >= unit) {
                return warpvndService.stlNanoUnits[j];
            }
        }
        return 1;
    }

    function isModelConductorType(modelName) {
        return condctorTypes.indexOf(modelName) >= 0;
    }

    function normalizeToum(val, scale) {
        return Math.round(10000 * scale * val / 1e-6) / 10000;
    }

    //TODO(mvk): validate sizing
    function plateSpacingValidator() {
        return true;
    }

    function setFieldState() {
        panelState.enableField('stl', 'zLength', false);
        panelState.enableField('stl', 'xLength', false);
        panelState.enableField('stl', 'yLength', false);
    }

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
        //var dim = appState.models.fieldComparisonReport.dimension;
        var rpt = warpvndService.activeComparisonReport();
        var dim = appState.models[rpt].dimension;
        var dims = warpvndService.is3D() ? ['x', 'y', 'z'] : ['x', 'z'];
        ['1', '2', '3'].forEach(function(i) {
            dims.forEach(function (d) {
                panelState.showField(rpt, d + 'Cell' + i, dim != d);
            });
            if (! warpvndService.is3D()) {
                panelState.showField(rpt, 'yCell' + i, false);
            }
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

    function updatePermittivity(conductorType) {
        var type = conductorType || 'box';
        panelState.showField(type, 'permittivity', appState.models[type].isConductor == '0');
        $scope.defaultColor = appState.models[type].isConductor == '0' ? '#f3d4c8' : '#6992ff';
    }

    function updateSimulationMode() {
        var isNotStl = ! appState.models.simulation.conductorFile;
        panelState.showField('simulationGrid', 'simulation_mode', warpvndService.allow3D() && isNotStl);
        var is3d = appState.models.simulationGrid.simulation_mode == '3d';
        ['channel_height', 'num_y'].forEach(function(f) {
            panelState.showField('simulationGrid', f, is3d);
        });
        panelState.showField('box', 'yLength', is3d);
        panelState.showField('conductorPosition', 'yCenter', is3d);
        panelState.showField('fieldCalcAnimation', 'axes', is3d);
        panelState.showEnum(warpvndService.activeComparisonReport(), 'dimension', 'y', is3d);
    }

    self.isWaitingForSTL = false;

    self.createConductorType = function(type, silent) {
        var model = {
            id: appState.maxId(appState.models.conductorTypes) + 1,
        };
        var m = appState.setModelDefaults(model, type);
        if(! silent) {
            self.editConductorType(type, model);
        }
        return m;
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
            isConductor: model.isConductor,
            color: model.color,
            type: model.type || 'box',
        };

        self.editConductorType(model.type || 'box', modelCopy);
    };

    self.deleteConductor = function() {
        appState.models.conductors.splice(
            appState.models.conductors.indexOf(self.deleteWarning.conductor), 1);
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
        appState.models.conductorTypes.splice(
            appState.models.conductorTypes.indexOf(model), 1);
        appState.models.conductors = appState.models.conductors.filter(function(m) {
            return m.conductorTypeId != model.id;
        });
        appState.saveChanges(['conductorTypes', 'conductors']);
    };

    self.deleteConductorTypePrompt = function(model) {
        var count = appState.models.conductors.reduce(function(accumulator, m) {
            return accumulator + (m.conductorTypeId == model.id ? 1 : 0);
        }, 0);
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
        appState.models.conductorPosition = warpvndService.findConductor(id);
        panelState.showModalEditor('conductorPosition');
    };

    self.editConductorType = function(type, model) {
        appState.models[type] = model;
        panelState.showModalEditor(type);
    };

    self.fieldReport = function() {
        return appState.models[warpvndService.activeFieldReport()];
    };

    self.handleModalShown = function(name) {
        updateAllFields();
        if (name == warpvndService.activeComparisonReport()) {
            updateFieldComparison();
        }
    };

    self.hasFrames = function(modelName) {
        return frameCache.hasFrames(modelName);
    };

    self.is3D = function() {
        return warpvndService.is3D();
    };

    self.usesSTL = function() {
        return ! ! (appState.models.simulation || {}).conductorFile;
    };

    self.updateFieldComparison = function() {
        updateSimulationMode();
        updateFieldComparison();
    };

    $scope.$on('cancelChanges', function(e, name) {
        if (isModelConductorType(name)) {
            appState.removeModel(name);
            appState.cancelChanges('conductorTypes');
        }
        else if (name == 'conductorPosition') {
            appState.removeModel(name);
            appState.cancelChanges('conductors');
        }
    });

    $scope.$on('modelChanged', function(e, name) {
       if (isModelConductorType(name)) {
            var model = appState.models[name];
            var foundIt = appState.models.conductorTypes.some(function(m) {
                if (m.id == model.id) {
                    return true;
                }
            });
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
        setFieldState();
        updateAllFields();
        initImportedConductor();
        appState.watchModelFields($scope, ['simulationGrid.num_x'], updateParticlesPerStep);
        appState.watchModelFields($scope, ['simulationGrid.plate_spacing', 'simulationGrid.num_z'], updateParticleZMin);
        appState.watchModelFields($scope, ['simulationGrid.channel_width'], updateBeamRadius);
        appState.watchModelFields($scope, ['beam.currentMode'], updateBeamCurrent);
        appState.watchModelFields($scope, [warpvndService.activeComparisonReport() + '.dimension'], updateFieldComparison);
        SIREPO.APP_SCHEMA.enum.ConductorType.forEach(function (i) {
            var t = i[SIREPO.INFO_INDEX_TYPE];
            appState.watchModelFields($scope, [t + '.isConductor'], function () {
                updatePermittivity(t);
            });
        });
        appState.watchModelFields($scope, ['simulationGrid.simulation_mode'], updateSimulationMode);
    });
});

SIREPO.app.controller('OptimizationController', function (appState, frameCache, persistentSimulation, $scope) {
    var self = this;

    function handleStatus(data) {
        if (data.startTime && ! data.error) {
            appState.models.optimizerAnimation.startTime = data.startTime;
            appState.saveQuietly('optimizerAnimation');
            frameCache.setFrameCount(data.frameCount > 1 ? data.frameCount : 0);
            self.simState.summaryData = data.summary;
        }
    }

    self.hasOptFields = function() {
        if (appState.isLoaded()) {
            var optimizer = appState.applicationState().optimizer;
            if (optimizer.fields) {
                return optimizer.fields.length > 0;
            }
        }
        return false;
    };

    self.simState = persistentSimulation.initSimulationState($scope, 'optimizerAnimation', handleStatus, {
        optimizerAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'x', 'y', 'startTime'],
    });

    self.simState.notRunningMessage = function() {
        return 'Optimization ' + self.simState.stateAsText() + ': ' + self.simState.getFrameCount() + ' runs';
    };

    self.simState.runningMessage = function() {
        return 'Completed run: ' + self.simState.getFrameCount();
    };

});

SIREPO.app.controller('VisualizationController', function (appState, frameCache, panelState, requestSender, warpvndService, $scope) {
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

    self.handleModalShown = function() {
        panelState.enableField('simulationGrid', 'particles_per_step', false);
    };

    self.hasFrames = function(modelName) {
        if (modelName) {
            return frameCache.getFrameCount(modelName) > 0;
        }
        return frameCache.getFrameCount() > 0;
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
            '<div data-stl-import-dialog="" data-title="STL" data-description="Use conductors from STL file"></div>',
        ].join(''),
    };
});

SIREPO.app.directive('appHeader', function(appState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: [
            '<div data-app-header-brand="nav"></div>',
            '<div data-app-header-left="nav"></div>',
            '<div data-app-header-right="nav" data-new-template="newTemplate" data-new-callback="newCallback">',
              '<app-header-right-sim-loaded>',
                '<div data-sim-sections="">',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'visualization\')}"><a href data-ng-click="nav.openSection(\'visualization\')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
                  '<li class="sim-section" data-ng-show="showOptimization()" data-ng-class="{active: nav.isActive(\'optimization\')}"><a href data-ng-click="nav.openSection(\'optimization\')"><span class="glyphicon glyphicon-time"></span> Optimization</a></li>',
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
        controller: function($scope) {
            $scope.showOptimization = function() {
                if (appState.isLoaded()) {
                    return ! $.isEmptyObject(appState.applicationState().optimizer.enabledFields);
                }
                return false;
            };
        },
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
                if (appState.isLoaded()) {
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
                    else if ($scope.info[1] == 'YCell') {
                        warpvndService.getYRange().forEach(function(v, index) {
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
            '<table data-ng-show="conductorTypes().length" style="width: 100%;  table-layout: fixed" class="table table-hover">',
              '<colgroup>',
                '<col>',
                '<col style="width: 12ex">',
              '</colgroup>',
              '<thead>',
                '<tr>',
                  '<th>Name</th>',
                '</tr>',
              '</thead>',
              '<tbody data-ng-repeat="conductorType in conductorTypes() track by conductorType.id">',
                '<tr>',
                  '<td colspan="2" style="padding-left: 1em; cursor: pointer; white-space: nowrap" data-ng-click="toggleConductorType(conductorType)"><div class="badge sr-badge-icon"><span data-ng-drag="true" data-ng-drag-data="conductorType">{{ conductorType.name }}</span></div> <span class="glyphicon" data-ng-show="hasConductors(conductorType)" data-ng-class="{\'glyphicon-collapse-down\': isCollapsed(conductorType), \'glyphicon-collapse-up\': ! isCollapsed(conductorType)}"> </span></td>',
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
                if(! conductorType) {
                    return null;
                }
                return conductorsByType[conductorType.id];
            };
            $scope.conductorTypes = function() {
                return appState.models.conductorTypes;
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
                $scope.source.editConductorType(conductorType.type || 'box', conductorType);
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
                if(! conductorType) {
                    return true;
                }
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
            reportId: '<',
        },
        templateUrl: '/static/html/conductor-grid.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            var ASPECT_RATIO = 6.0 / 14;
            var CELL_COLORS = SIREPO.APP_SCHEMA.constants.cellColors;
            var ELEVATIONS = {
                front: 'front',
                side: 'side',
                top: 'top'
            };

            var insetWidthPct = 0.07;
            var insetMargin = 16.0;

            $scope.warpvndService = warpvndService;
            $scope.margin = {top: 20, right: 20, bottom: 45, left: 70};
            $scope.width = $scope.height = 0;
            $scope.zHeight = 150;
            $scope.isClientOnly = true;
            $scope.source = panelState.findParentAttribute($scope, 'source');
            $scope.is3dPreview = false;
            $scope.tileOpacity = 0.6;
            $scope.tileBoundaryThresholdPct = 0.05;
            $scope.conductorNearBoundary = false;

            $scope.zMargin = function () {
                var xl = select('.x-axis-label');
                var xaxis = select('.x.axis');
                if(xl.empty() || xaxis.empty()) {
                    return 0;
                }
                try {
                    // firefox throws on getBBox() if the node is not visible
                    return xl.attr('height') + xaxis.node().getBBox().height + 16;
                }
                catch (e) {
                    return 0;
                }
            };

            var dragCarat, dragShape, dragStart, yRange, zoom;
            var planeLine = 0.0;
            var plateSize = 0;
            var plateSpacing = 0;
            var axes = {
                x: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh),
                y: layoutService.plotAxis($scope.margin, 'y', 'left', refresh),
                z: layoutService.plotAxis($scope.margin, 'z', 'left', refresh),
            };
            var insetAxes = {
                x: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh),
                y: layoutService.plotAxis($scope.margin, 'y', 'left', refresh),
            };

            function alignShapeOnGrid(shape) {
                var grid = appState.models.simulationGrid;
                var numX = grid.num_x;
                var n = toMicron(grid.channel_width / (numX * 2));
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
                var typeMap = warpvndService.conductorTypeMap();
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
                var v = pn < n
                    ? p - pn
                    : p + n - pn;
                if (Math.abs(v) < 1e-16) {
                    return 0;
                }
                return v;
            }

            function caratData(elev) {
                var zRange = warpvndService.getZRange();
                var xRange = warpvndService.getXRange();
                var yRange = warpvndService.getYRange();
                var res = [];
                [1, 2, 3].forEach(function(i) {
                    if (elev === ELEVATIONS.front) {
                        res.push(caratField(elev, i, 'x', zRange));
                        res.push(caratField(elev, i, 'z', xRange));
                    }
                    else {
                        res.push(caratField(elev, i, 'y', zRange));
                        res.push(caratField(elev, i, 'z', yRange));
                    }
                });
                return res;
            }

            function caratField(elev, index, dimension, range) {
                var rpt = warpvndService.activeComparisonReport();
                var cell = 'Cell' + index;
                var field = (elev === ELEVATIONS.front ?
                    (dimension == 'x' ? 'z': 'x') :
                    (dimension == 'y' ? 'z': 'y')) + cell;
                if (appState.models[rpt][field] >= range.length) {
                    appState.models[rpt][field] = range.length - 1;
                }
                return {
                    elev: elev,
                    index: index,
                    field: field,
                    pos: appState.models[rpt][field],
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
                var vertAxis = d.elev === ELEVATIONS.front ? axes.y : axes.z;
                var p = d.dimension === 'x' || d.dimension === 'y'
                    ? axes.x.scale.invert(d3.event.x) * 1e6
                    : vertAxis.scale.invert(d3.event.y) * 1e6;
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
                var rpt = warpvndService.activeComparisonReport();
                if (d.pos != appState.models[rpt][d.field]) {
                    appState.models[rpt][d.field] = d.pos;
                    appState.models[rpt].dimension = d.dimension;
                    appState.saveChanges(rpt);
                }
            }

            function d3DragEndShape(shape) {
                var conductorPosition = warpvndService.findConductor(shape.id);
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
                var grid = appState.models.simulationGrid;
                var oldPlaneLine = planeLine;
                planeLine = axes.z.scale.invert(d3.event.y);
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
                if (shape.elev == ELEVATIONS.top) {
                    return true;
                }
                var grid = appState.models.simulationGrid;
                var numX = grid.num_x;  // number of vertical cells
                var halfChannel = toMicron(grid.channel_width/2.0);
                var cellHeight = toMicron(grid.channel_width / numX);  // height of one cell
                var numZ = grid.num_z;  // number of horizontal cells
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

            function drawCathodeAndAnode(elev) {
                var grid = appState.models.simulationGrid;
                var info = plotInfoForElevation(elev);
                var viewport = select(info.viewportClass);
                viewport.selectAll('.warpvnd-plate').remove();
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
                drawCathodeAndAnode('front');
                if (warpvndService.is3D()) {
                    drawCathodeAndAnode('top');
                }
            }

            function drawCarats(elev) {
                var info = plotInfoForElevation(elev);
                d3.select(info.viewportClass).selectAll('.warpvnd-cell-selector').remove();
                d3.select(info.viewportClass).selectAll('.warpvnd-cell-selector')
                    .data(caratData(elev))
                    .enter().append('path')
                    .attr('class', 'warpvnd-cell-selector')
                    .attr('d', function(d) {
                        return d.dimension === 'x' || d.dimension === 'y'
                            ? 'M0,-14L7,0 -7,0Z'
                            : 'M0,-7L0,7 14,0Z';
                    })
                    .style('cursor', function(d) {
                        return d.dimension === 'x' || d.dimension === 'y' ? 'ew-resize' : 'ns-resize';
                    })
                    .style('fill', function(d) {
                        return CELL_COLORS[d.index - 1];
                    })
                    .call(updateCarat)
                    .call(dragCarat).append('title')
                    .text(caratText);
            }

            function drawConductors(typeMap, elev) {
                var grid = appState.models.simulationGrid;
                var info = plotInfoForElevation(elev);
                var shapes = [];
                appState.models.conductors
                    .forEach(function(conductorPosition) {
                        var conductorType = typeMap[conductorPosition.conductorTypeId];
                        var w = toMicron(conductorType.zLength);
                        var h = toMicron(conductorType[info.lengthField]);
                        var d = toMicron(conductorType.yLength);
                        var x = toMicron(conductorPosition.zCenter) - w / 2;
                        var y = toMicron(conductorPosition[info.centerField]) + h / 2;
                        shapes.push({
                            x: x,
                            y: y,
                            plane: toMicron(conductorPosition.yCenter),
                            width: w,
                            height: h,
                            depth: d,
                            id: conductorPosition.id,
                            conductorType: conductorType,
                            elev: elev,
                        });
                        var dy = toMicron(grid[info.heightField]);
                        var y0 = -dy / 2;
                        var y1 = dy / 2;
                        var dy1 = y1 - y;
                        var dy2 = (y - h) - y0;
                        var t = 0.05 * dy;
                        $scope.conductorNearBoundary = $scope.conductorNearBoundary || dy1 < t || dy2 < t;
                    });
                var ds = d3.select(info.viewportClass).selectAll('.warpvnd-shape')
                    .data(shapes);
                ds.exit().remove();
                ds.enter().append('rect')
                    .on('dblclick', editPosition);
                ds.call(updateShapeAttributes);
                if (elev === ELEVATIONS.front) {
                    ds.call(dragShape);
                }
                if(! $scope.isDomainTiled || elev !== ELEVATIONS.front) {
                    return;
                }
                // just once per set of conductors
                drawTiledConductors(shapes);
            }

            function drawTiledConductors(shapes) {
                var dr = d3.select('#tile-master').selectAll('.warpvnd-shape').data(shapes);
                dr.exit().remove();
                dr.enter().append('rect');
                dr.call(updateTiles);
            }

            function drawShapes() {
                $scope.conductorNearBoundary = false;
                var typeMap = warpvndService.conductorTypeMap();
                drawConductors(typeMap, ELEVATIONS.front);
                drawCarats(ELEVATIONS.front);
                if (warpvndService.is3D()) {
                    drawConductors(typeMap, ELEVATIONS.top);
                    drawCarats(ELEVATIONS.top);
                }
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

            function plotInfoForElevation(elev) {
                if (elev === ELEVATIONS.front) {
                    return {
                        viewportClass: '.plot-viewport',
                        axis: axes.y,
                        heightField: 'channel_width',
                        centerField: 'xCenter',
                        lengthField: 'xLength',
                    };
                }
                else if (elev === ELEVATIONS.top) {
                    return {
                        viewportClass: '.z-plot-viewport',
                        axis: axes.z,
                        heightField: 'channel_height',
                        centerField: 'yCenter',
                        lengthField: 'yLength',
                    };
                }
                throw 'invalid elev: ' + elev;
            }

            function zPanelHeight() {
                return warpvndService.is3D() ? $scope.zHeight + $scope.zMargin() : 0;
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
                        .attr('height', $scope.plotHeight());
                    select('.z-plot')
                        .attr('width', $scope.width + $scope.margin.left + $scope.margin.right)
                        .attr('height', $scope.zHeight + $scope.margin.bottom);
                    axes.x.scale.range([0, $scope.width]);
                    axes.y.scale.range([$scope.height, 0]);
                    axes.z.scale.range([$scope.zHeight, 0]);
                    axes.x.grid.tickSize(-$scope.height);
                    axes.y.grid.tickSize(-$scope.width);
                    axes.z.grid.tickSize(-$scope.width);

                    insetAxes.x.scale.range([0, $scope.tileInsetSize().width]);
                    insetAxes.y.scale.range([$scope.tileInsetSize().height, 0]);
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
                axes.y.grid.tickValues(plotting.linearlySpacedArray(-channel / 2, channel / 2, grid.num_x + 1));
                var depth = toMicron(grid.channel_height);
                axes.z.grid.tickValues(plotting.linearlySpacedArray(-depth / 2, depth / 2, grid.num_y + 1));
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
                    insetAxes.y.domain = newYDomain;
                    insetAxes.y.scale.domain(insetAxes.y.domain);
                }
                if (warpvndService.is3D()) {
                    yRange = warpvndService.getYRange();
                    var depth = toMicron(grid.channel_height / 2.0);
                    var newZDomain = [- depth, depth];
                    if (! axes.z.domain || ! appState.deepEquals(axes.z.domain, newZDomain)) {
                        axes.z.domain = newZDomain;
                        axes.z.scale.domain(axes.z.domain);
                        insetAxes.x.domain = newZDomain;
                        insetAxes.x.scale.domain(insetAxes.x.domain);
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
                var grid = appState.models.simulationGrid;
                selection.attr('transform', function(d) {
                    var vertAxis = d.elev === ELEVATIONS.front ? axes.y : axes.z;
                    if (d.dimension === 'x' || d.dimension === 'y') {
                        var info = plotInfoForElevation(d.elev);
                        var h = -grid[info.heightField] / 2.0;
                        return 'translate(' +
                            axes.x.scale(toMicron(d.range[d.pos])) + ',' +
                            vertAxis.scale(toMicron(h)) + ')';
                    }
                    return 'translate(' + '0' + ',' + vertAxis.scale(toMicron(d.range[d.pos])) + ')';
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

            function shapeColor(hexColor, alpha) {
                var comp = plotting.colorsFromHexString(hexColor);
                return 'rgb(' + comp[0] + ', ' + comp[1] + ', ' + comp[2] + ', ' + (alpha || 1.0) + ')';
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
                    .attr('id', function (d) {
                        return 'shape-' + d.elev + '-' + d.id;
                    })
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
                        var axis = d.elev === ELEVATIONS.front
                            ? axes.y
                            : axes.z;
                        return axis.scale(d.y);
                    })
                    .attr('width', function(d) {
                        return axes.x.scale(d.x + d.width) - axes.x.scale(d.x);
                    })
                    .attr('height', function(d) {
                        var axis = d.elev === ELEVATIONS.front
                            ? axes.y
                            : axes.z;
                        return axis.scale(d.y) - axis.scale(d.y + d.height);
                    })
                    .attr('style', function(d) {
                        if(d.conductorType.color && doesShapeCrossGridLine(d)) {
                            return 'fill:' + shapeColor(d.conductorType.color, 0.3) + '; ' +
                                'stroke: ' + shapeColor(d.conductorType.color);
                        }
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

            function updateTiles(selection) {
                selection
                    .attr('id', function (d) {
                        return 'shape-inset-' + d.id;
                    })
                    .attr('class', 'warpvnd-shape')
                    .classed('warpvnd-shape-voltage', function(d) {
                        return d.conductorType.voltage > 0;
                    })
                    .attr('x', function(d) {
                        return warpvndService.is3D() ? insetAxes.x.scale(d.plane - d.depth / 2.0) : 0;
                    })
                    .attr('y', function(d) {
                        return insetAxes.y.scale(d.y);
                    })
                    .attr('width', function(d) {
                        return warpvndService.is3D() ? Math.abs(insetAxes.x.scale(d.plane + d.depth) - insetAxes.x.scale(d.plane)) : $scope.tileInsetSize().width;
                    })
                    .attr('height', function(d) {
                        return Math.abs(insetAxes.y.scale(d.y + d.height) - insetAxes.y.scale(d.y));
                    })
                    .attr('style', function(d) {
                        var fstyle = d.conductorType.color ? 'fill:' + shapeColor(d.conductorType.color, 1.0) + '; ' : '';
                        return fstyle + 'stroke: none';
                    });
            }

            $scope.allInsetSize = function() {
                return {
                    width: 3 * $scope.tileInsetSize().width,
                    height: 3 * $scope.tileInsetSize().height,
                };
            };

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
                var grid = appState.models.simulationGrid;
                plateSpacing = grid.plate_spacing;
                select('svg').attr('height', plotting.initialHeight($scope));
                $.each(axes, function(dim, axis) {
                    axis.init();
                    axis.grid = axis.createAxis();
                });
                $.each(insetAxes, function(dim, axis) {
                    axis.init();
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
                replot();
            };

           $scope.plotHeight = function() {
                var ph = $scope.plotOffset() + $scope.margin.top + $scope.margin.bottom + zPanelHeight();
                return ph;
            };

            $scope.plotOffset = function() {
                return $scope.height + $scope.tileOffset();
            };


            $scope.resize = function() {
                if (select().empty()) {
                    return;
                }
                refresh();
            };

            $scope.tileInsetSize = function() {
                var w = 0;
                var h = 0;
                var grid = appState.models.simulationGrid;
                if($scope.isDomainTiled) {
                    w = insetWidthPct * $scope.width;
                    h = warpvndService.is3D() ? w *  (grid.channel_width / grid.channel_height) : insetWidthPct * $scope.height;
                }
                return {
                    width: w,
                    height: h
                };
            };

            $scope.tileInsetOffset = function() {
                return {
                    x: warpvndService.is3D() ? $scope.tileInsetSize().width : 0,
                    y: 0
                };
            };

            $scope.tileOffset = function() {
                return $scope.isDomainTiled ? insetMargin + $scope.allInsetSize().height : 0;
            };

            $scope.toggle3dPreview = function() {
                //if(! $scope.source.usesSTL()) {
                    $scope.is3dPreview = !$scope.is3dPreview;
                //}
            };

            $scope.toggleTiledDomain = function() {
                $scope.isDomainTiled = ! $scope.isDomainTiled;
                refresh();
            };

            appState.whenModelsLoaded($scope, function() {
                $scope.is3dPreview = $scope.source.usesSTL();
                var grid = appState.models.simulationGrid;
                $scope.$on('cancelChanges', function(e, name) {
                    if (name == 'conductors') {
                        replot();
                    }
                });
                $scope.$on('conductorGridReport.changed', replot);
                $scope.$on('simulationGrid.changed', function() {
                    plateSpacing = grid.plate_spacing;
                    replot();
                });
                $scope.$on(warpvndService.activeComparisonReport() + '.changed', replot);
            });
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('fieldCalculationAnimation', function(appState, frameCache, panelState, persistentSimulation) {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            modelName: '@fieldCalculationAnimation',
        },
        template: [
            '<div data-simple-panel="{{ modelName }}">',
                '<div data-sim-status-panel="simState""></div>',
            '</div>',
        ].join(''),
        controller: function($scope) {

            var SINGLE_PLOTS = ['fieldCalcAnimation', 'fieldComparisonAnimation'];
            $scope.panelState = panelState;

            function buildAnimArgs(name, version) {
                var args = [SIREPO.ANIMATION_ARGS_VERSION + version]
                    .concat(SIREPO.APP_SCHEMA.animationArgs[name]);
                args.push('startTime');
                return args;
            }

            function handleStatus(data) {
                SINGLE_PLOTS.forEach(function(name) {
                    frameCache.setFrameCount(0, name);
                });
                if (data.startTime && ! data.error) {
                    SINGLE_PLOTS.forEach(function(modelName) {
                        appState.models[modelName].startTime = data.startTime;
                        appState.saveQuietly(modelName);
                    });
                    if (data.percentComplete === 100 && ! $scope.simState.isProcessing()) {
                        SINGLE_PLOTS.forEach(function(name) {
                            frameCache.setFrameCount(1, name);
                        });
                    }
                }
                frameCache.setFrameCount(data.frameCount);
            }

            $scope.startSimulation = function() {
                $scope.simState.saveAndRunSimulation(['simulation', 'simulationGrid']);
            };


            $scope.simState = persistentSimulation.initSimulationState($scope, 'fieldCalculationAnimation', handleStatus, {
                fieldCalcAnimation: buildAnimArgs('fieldCalcAnimation', '1'),
                fieldComparisonAnimation: buildAnimArgs('fieldComparisonAnimation', '1'),
            });
        },
    };
});


SIREPO.app.directive('optimizationForm', function(appState, panelState, warpvndService) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div class="well" data-ng-show="! optFields.length">',
            'Select fields for optimization on the <i>Source</i> tab.',
            '</div>',
            '<form name="form" class="form-horizontal" data-ng-show="::optFields.length">',
            '<div class="form-group form-group-sm">',
              '<h4>Bounds</h4>',
              '<table class="table table-striped table-condensed">',
                '<thead>',
                  '<tr>',
                    '<th>Field</th>',
                    '<th>Minimum</th>',
                    '<th>Maximum</th>',
                    '<th> </th>',
                  '</tr>',
                '</thead>',
                '<tbody>',
                  '<tr data-ng-repeat="optimizerField in appState.models.optimizer.fields track by $index">',
                    '<td>',
                      '<div class="form-control-static">{{ labelForField(optimizerField.field) }}</div>',
                    '</td><td>',
                      '<div class="row" data-field-editor="\'minimum\'" data-field-size="12" data-model-name="\'optimizerField\'" data-model="optimizerField"></div>',
                    '</td><td>',
                      '<div class="row" data-field-editor="\'maximum\'" data-field-size="12" data-model-name="\'optimizerField\'" data-model="optimizerField"></div>',
                    '</td>',
                    '<td style="vertical-align: middle">',
                      '<button class="btn btn-danger btn-xs" data-ng-click="deleteField($index)" title="Delete Row"><span class="glyphicon glyphicon-remove"></span></button>',
                    '</td>',
                  '</tr>',
                  '<tr>',
                    '<td>',
                      '<select class="input-sm form-control" data-ng-model="selectedField" data-ng-options="f.field as f.label for f in unboundedOptFields" data-ng-change="addField()"></select>',
                    '</td>',
                    '<td></td>',
                    '<td></td>',
                    '<td></td>',
                  '</tr>',
                '</tbody>',
              '</table>',
            '</div>',
            '<div class="form-group form-group-sm" data-ng-show="appState.models.optimizer.fields.length">',
              '<h4>Constraints</h4>',
              '<table class="table table-striped table-condensed">',
                '<thead>',
                  '<tr>',
                    '<th>Bounded Field</th>',
                    '<th> </th>',
                    '<th>Field</th>',
                    '<th> </th>',
                  '</tr>',
                '</thead>',
                '<tbody>',
                  '<tr data-ng-repeat="constraint in appState.models.optimizer.constraints track by $index">',
                    '<td>',
                      '<div class="form-control-static">{{ labelForField(constraint[0]) }}</div>',
                    '</td>',
                    '<td style="vertical-align: middle">{{ constraint[1] }}</td>',
                    '<td>',
                      '<div class="form-control-static">{{ labelForField(constraint[2]) }}</div>',
                    '</td>',
                    '<td style="vertical-align: middle">',
                      '<button class="btn btn-danger btn-xs" data-ng-click="deleteConstraint($index)" title="Delete Row"><span class="glyphicon glyphicon-remove"></span></button>',
                    '</td>',
                  '</tr>',
                  '<tr>',
                    '<td>',
                      '<select class="input-sm form-control" data-ng-model="selectedConstraint" data-ng-options="f.field as labelForField(f.field) for f in appState.models.optimizer.fields"></select>',
                    '</td>',
                    '<td>=</td>',
                    '<td>',
                      '<select data-ng-show="selectedConstraint" class="input-sm form-control" data-ng-model="selectedConstraint2" data-ng-options="f.field as f.label for f in ::optFields" data-ng-change="addConstraint()"></select>',
                    '</td>',
                    '<td style="vertical-align: middle">',
                      '<button  data-ng-show="selectedConstraint" class="btn btn-danger btn-xs" data-ng-click="deleteSelectedConstraint()" title="Delete Row"><span class="glyphicon glyphicon-remove"></span></button>',
                    '</td>',
                  '</tr>',
                '</tbody>',
              '</table>',
            '</div>',
            '<div class="form-group form-group-sm">',
              '<div data-model-field="\'objective\'" data-model-name="\'optimizer\'"></div>',
            '</div>',
            '<div class="col-sm-6 pull-right" data-ng-show="hasChanges()">',
              '<button data-ng-click="saveChanges()" class="btn btn-primary" data-ng-disabled="! form.$valid">Save Changes</button> ',
              '<button data-ng-click="cancelChanges()" class="btn btn-default">Cancel</button>',
            '</div>',
            '</form>',
        ].join(''),
        controller: function($scope, $element) {
            $scope.form = angular.element($($element).find('form').eq(0));
            $scope.appState = appState;
            $scope.selectedField = null;
            $scope.selectedConstraint = null;
            $scope.selectedConstraint2 = null;

            function buildOptimizeFields() {
                $scope.optFields = warpvndService.buildOptimizeFields();
            }

            function setDefaults(model) {
                $scope.optFields.some(function(f) {
                    if (f.field == model.field) {
                        model.minimum = model.maximum = f.value;
                        return true;
                    }
                });
            }

            function verifyBounds() {
                var isField = {};
                $scope.optFields.forEach(function(f) {
                    isField[f.field] = true;
                });
                var list = [];
                var isBoundedField = {};
                appState.models.optimizer.fields.forEach(function(f) {
                    if (isField[f.field]) {
                        list.push(f);
                        isBoundedField[f.field] = true;
                    }
                });
                if (appState.models.optimizer.fields.length != list.length) {
                    appState.models.optimizer.fields = list;
                }
                return isBoundedField;
            }

            function verifyBoundsAndConstraints() {
                if ($scope.optFields) {
                    verifyConstraints(verifyBounds());
                }
            }

            function verifyConstraints(isBoundedField) {
                $scope.unboundedOptFields = [];
                $scope.optFields.forEach(function(f) {
                    if (! isBoundedField[f.field]) {
                        $scope.unboundedOptFields.push(f);
                    }
                });

                var list = [];
                appState.models.optimizer.constraints.forEach(function(c) {
                    if (isBoundedField[c[0]] && ! isBoundedField[c[2]]) {
                        list.push(c);
                    }
                });
                if (appState.models.optimizer.constraints.length != list.length) {
                    appState.models.optimizer.constraints = list;
                }
            }

            $scope.addConstraint = function() {
                if ($scope.selectedConstraint == $scope.selectedConstraint2) {
                    return;
                }
                appState.models.optimizer.constraints.push(
                    [$scope.selectedConstraint, '=', $scope.selectedConstraint2]);
                $scope.selectedConstraint = null;
                $scope.selectedConstraint2 = null;
            };

            $scope.addField = function() {
                var m = {
                    field: $scope.selectedField,
                };
                appState.models.optimizer.fields.push(m);
                setDefaults(m);
                $scope.selectedField = null;
                verifyBoundsAndConstraints();
            };

            $scope.cancelChanges = function() {
                appState.cancelChanges('optimizer');
                verifyBoundsAndConstraints();
                $scope.form.$setPristine();
            };

            $scope.deleteConstraint = function(idx) {
                appState.models.optimizer.constraints.splice(idx, 1);
                $scope.form.$setDirty();
            };

            $scope.deleteField = function(idx) {
                var field = appState.models.optimizer.fields[idx].field;
                appState.models.optimizer.fields.splice(idx, 1);
                verifyBoundsAndConstraints();
                $scope.form.$setDirty();
            };

            $scope.deleteSelectedConstraint = function() {
                $scope.selectedConstraint = null;
                $scope.selectedConstraint2 = null;
            };

            $scope.getBoundsFieldList = function() {
                if (! $scope.optFields) {
                    return null;
                }
                var existingFieldBounds = {};
                appState.models.optimizer.fields.forEach(function(f) {
                    existingFieldBounds[f.field] = true;
                });
                var list = [];
                $scope.optFields.forEach(function(f) {
                    if (! existingFieldBounds[f.field]) {
                        list.push(f);
                    }
                });
                return list;
            };

            $scope.hasChanges = function() {
                if ($scope.form.$dirty) {
                    return true;
                }
                return appState.areFieldsDirty('optimizer.fields') || appState.areFieldsDirty('optimizer.constraints');
            };

            $scope.labelForField = function(field) {
                var res = '';
                if ($scope.optFields) {
                    $scope.optFields.some(function(f) {
                        if (f.field == field) {
                            res = f.label;
                            return true;
                        }
                    });
                }
                return res;
            };

            $scope.saveChanges = function() {
                appState.saveChanges('optimizer');
                $scope.form.$setPristine();
            };

            appState.whenModelsLoaded($scope, function() {
                buildOptimizeFields();
                verifyBoundsAndConstraints();
            });
        },
    };
});

SIREPO.app.directive('optimizationResults', function(appState, warpvndService) {
    return {
        restrict: 'A',
        scope: {
            simState: '=optimizationResults',
        },
        template: [
            '<div data-ng-show="results && simState.getFrameCount() > 0" class="well warpvnd-well">',
              '{{ results }}',
            '</div>',
            '<div data-ng-show="showCurrentStatus()"  class="well warpvnd-well">',
              '{{ currentSimStatus }}',
              '<div style="height: 124px; overflow-y: scroll; margin-top: 10px;">',
                '<table class="table table-striped table-condensed" style="margin-bottom: 0;">',
                  '<tr style="position: sticky; top: 0"><th class="text-right">Steps</th><th class="text-right">Time [s]</th><th class="text-right">Tolerance</th><th class="text-right">Result</th></tr>',
                  '<tr data-ng-repeat="row in statusRows track by $index">',
                    '<td class="text-right">{{ row[0] }}</td><td class="text-right">{{ row[1] }}</td><td class="text-right">{{ row[2] }}</td><td class="text-right">{{ row[3] }}</td>',
                  '</tr>',
                '</table>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            function labelAndValue(optFields, fields, value, idx) {
                var field = fields[idx].field;
                var label = field;
                optFields.some(function(opt) {
                    if (opt.field == field) {
                        label = opt.label;
                        if (label.indexOf('µ') >= 0) {
                            value *= 1e6;
                        }
                        return true;
                    }
                });
                return label + ': ' + warpvndService.formatNumber(value, 4) + '\n';
            }

            function updateStats(info) {
                $scope.results = '';
                if (! $scope.simState.isStateRunning()) {
                    $scope.currentSimStatus = '';
                }
                if (! info || ! appState.isLoaded()) {
                    return;
                }
                var optFields = warpvndService.buildOptimizeFields();
                $scope.statusRows = info.statusRows;
                if ($scope.statusRows) {
                    $scope.statusRows.reverse();
                    var currentStep = $scope.statusRows[0][0];
                    var targetStep = currentStep + ($scope.statusRows.length > 1 ? info.optimizerSteps : info.initialSteps);
                    $scope.currentSimStatus = 'Running Simulation #' + (info.frameCount + 1)
                        + ', Steps ' + (currentStep + 1) + ' - ' + targetStep + '\n';
                    $scope.statusRows[0].forEach(function(v, idx) {
                        if (idx > 3) {
                            $scope.currentSimStatus += labelAndValue(optFields, info.fields, v, idx - 4);
                        }
                    });
                    warpvndService.setOptimizingRow($scope.statusRows[0]);
                }
                else {
                    warpvndService.setOptimizingRow(null);
                }
                if (info.x) {
                    if ($scope.simState.isStopped()) {
                        if (info.success) {
                            $scope.results += 'Optimization successful\n';
                        }
                        else if (! $scope.simState.isStateCanceled()) {
                            $scope.results += 'Optimization failed to converge\n';
                        }
                    }
                    $scope.results += 'Best Result: ' + warpvndService.formatNumber(info.fun, 4) + '\n';
                    info.x.forEach(function(v, idx) {
                        $scope.results += labelAndValue(optFields, info.fields, v, idx);
                    });
                }
            }

            $scope.showCurrentStatus = function() {
                if ($scope.simState.isStateRunning()) {
                    return $scope.currentSimStatus;
                }
                warpvndService.setOptimizingRow(null);
                return false;
            };

            appState.whenModelsLoaded($scope, function() {
                $scope.$watch('simState.summaryData', updateStats);
            });
        },
    };
});

SIREPO.app.directive('fieldComparison', function(appState, warpvndService) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            parentController: '<',
        },
        template: [
            '<div data-report-panel="parameter" data-request-priority="0" data-model-name="fieldComparisonAnimation">',
            '</div>',
       ].join(''),
        controller: function($scope) {
            $scope.svc = warpvndService;
            appState.whenModelsLoaded($scope, function () {
                $scope.$on($scope.modelName + '.editor.show', function () {
                    $scope.parentController.updateFieldComparison();
                });
            });
       },
    };
});

SIREPO.app.directive('potentialReport', function(appState, panelState, plotting, warpvndService, utilities) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            modelName: '@',
        },
        template: [
            '<div data-report-panel="heatmap" data-request-priority="2" data-model-name="fieldCalcAnimation">',
                '<div data-ng-class="utilities.modelFieldID(modelName, \'slice\')">',
                    '<div data-label-with-tooltip="" class="control-label col-sm-5" data-ng-class="labelClass" data-label="Slice" data-tooltip=""></div>',
                '</div>',
                '<div class="col-sm-8" data-range-slider="" data-field="\'slice\'" data-model-name="modelName" data-model="model" data-update="changeSlice"></div>',
                //'<div class="col-sm-8">',
                //    '<input type="checkbox" checked data-ng-click="toggleConductors()"> Show Conductors',
                //'</div>',
                //'<div data-3d-slice-widget="" data-axis-info="axisInfo" data-slice-axis="sliceAxis" data-model="model" data-field="\'slice\'"></div>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {

            var lastAxes = 'xz';
            var slider;

            $scope.axisInfo = {
                height: 100,
                width: 100,
                map: {
                    x: 'y',
                    y: 'z',
                    z: 'x'
                },
            };
            $scope.showConductors = true;
            $scope.sliceAxis = '-';
            $scope.sliceRange = [0, 1];
            $scope.step = 1;
            $scope.utilities = utilities;

            $scope.changeSlice = function () {
                utilities.debounce(loadSlice, 500)();
            };

            $scope.toggleConductors = function () {
                $scope.showConductors = ! $scope.showConductors;
                drawConductors();
            };

            function drawConductors() {
                var plotRect = $($element).find('svg.sr-plot rect.mouse-rect');
                var d3pr = d3.select('svg.sr-plot rect.mouse-rect');
                //srdbg('found plot', plotRect, 'd3', d3pr, d3pr.attr('width'), 'x', d3pr.attr('height'));
                appState.models.conductors.forEach(function (c) {
                    var ct = warpvndService.findConductorType(c.conductorTypeId);
                    //srdbg('c', c, 't', ct);
                });
            }

            function loadSlice() {
                appState.saveChanges($scope.modelName);
            }

            function sliceAxis(axes) {
                return 'xyz'.replace(new RegExp('[' + axes + ']', 'g'), '');
            }

            function rangeForAxes(axes) {
                var grid = appState.models.simulationGrid;
                if (axes == 'yz') {
                    return [-grid.channel_width / 2.0, grid.channel_width / 2.0];
                }
                else if (axes === 'xy') {
                    return [0, grid.plate_spacing];
                }
                else {
                    return [-grid.channel_height / 2.0, grid.channel_height / 2.0];
                }
            }

            function updateSliceRange() {

                var axes = $scope.model.axes || 'xz';
                var grid = appState.models.simulationGrid;
                $scope.sliceAxis = sliceAxis(axes);

                var lastRange = rangeForAxes(lastAxes);

                $scope.sliceRange = rangeForAxes(axes);
                $scope.step = ($scope.sliceRange[1] - $scope.sliceRange[0]) / grid['num_' + $scope.sliceAxis];

                panelState.setFieldLabel($scope.modelName, 'slice', 'Slice ' + $scope.sliceAxis.toUpperCase());

                if (! slider) {
                    return;
                }

                slider.attr('min', $scope.sliceRange[0]);
                slider.attr('max', $scope.sliceRange[1]);
                slider.attr('step', $scope.step);

                if (lastAxes != axes) {
                    var pct = $scope.model.slice / ((lastRange[1] - lastRange[0]));
                    var newVal = slider.attr('min') + pct * (slider.attr('max') - slider.attr('min'));
                    //slider[0].value = Math.max(Math.min(newVal, $scope.sliceRange[1]), $scope.sliceRange[0]);
                    lastAxes = axes;
                }
           }

            appState.whenModelsLoaded($scope, function () {
                $scope.model = appState.models[$scope.modelName];
                $scope.model.units = 'µm';
                //panelState.showField('fieldCalcAnimation', 'slice', warpvndService.is3D());
                slider = $('#fieldCalcAnimation-slice-range');
                updateSliceRange();
            });

            appState.watchModelFields($scope, ['fieldCalcAnimation.axes'], updateSliceRange);
            appState.watchModelFields($scope, ['simulationGrid.simulation_mode'], updateSliceRange);

            // the DOM for editors does not exist until they appear, so we must show/hide fields this way
            $scope.$on('fieldCalcAnimation.editor.show', function () {
                if (! slider) {
                    slider = $('#fieldCalcAnimation-slice-range');
                }
                panelState.showField('fieldCalcAnimation', 'axes', warpvndService.is3D());
                panelState.showField('fieldCalcAnimation', 'slice', warpvndService.is3D());

                updateSliceRange();
            });
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
            '<div data-simple-panel="{{ modelName }}">',
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

SIREPO.app.directive('impactDensityPlot', function(plotting, plot2dService, geometry) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/plot2d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {

            function mouseOver() {
                /*jshint validthis: true*/
                var path = d3.select(this);
                if (! path.empty()) {
                    var density = path.datum().srDensity;
                    $scope.pointer.pointTo(density);
                }
            }

            function toMicron(v) {
                return v * 1e-6;
            }

            function toNano(v) {
                return v * 1e-9;
            }

            $scope.has3dData = false;

            $scope.init = function() {
                plot2dService.init2dPlot($scope, {
                    aspectRatio: 4.0 / 7,
                    margin: {top: 50, right: 80, bottom: 50, left: 70},
                    zoomContainer: '.plot-viewport',
                    wantColorbar: true,
                });
                // can't remove the overlay or it causes a memory leak
                $scope.select('svg').selectAll('.overlay').classed('disabled-overlay', true);
            };
            $scope.load = function(json) {
                $scope.xRange = json.x_range;
                var xdom = [json.x_range[0], json.x_range[1]];
                var smallDiff = (xdom[1] - xdom[0]) / 200.0;
                xdom[0] -= smallDiff;
                xdom[1] += smallDiff;
                $scope.axes.x.domain = xdom;
                $scope.axes.x.scale.domain(xdom);
                $scope.axes.y.domain = [json.y_range[0], json.y_range[1]];
                $scope.axes.y.scale.domain($scope.axes.y.domain).nice();
                var viewport = $scope.select('.plot-viewport');
                viewport.selectAll('.line').remove();
                $scope.updatePlot(json);

                var i;
                for (i = 0; i < json.density_lines.length; i++) {
                    var lineInfo = json.density_lines[i];
                    var p = lineInfo.points;
                    if (! lineInfo.density.length) {
                        lineInfo.density = [0];
                    }
                    var lineSegments = plotting.linearlySpacedArray(p[0], p[1], lineInfo.density.length + 1);
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
                                  + (density > 0 ? $scope.colorScale(density) : 'black'))
                            .datum(v);
                        path.on('mouseover', mouseOver);
                    }
                }

                // loop over conductors
                // arr[0] + k * sk for 2d
                // arr[0][0] + k * sk + l * sl for 3d (later)
                (json.density || []).forEach(function (c, ci) {
                    var pg = viewport.append('g')
                        .attr('class', 'density-plot');
                    // loop over "faces"
                    c.forEach(function (f, fi) {
                        var o = [f.x.startVal, f.z.startVal].map(toNano);
                        var sk = [f.x.slopek, f.z.slopek].map(toNano);
                        var den = f.dArr;
                        var nk = den.length;
                        var nl = den[0].length;
                        if(nl) {
                            // for now don't display 2d impact density if the data is 3d
                            $scope.has3dData = true;
                            return;
                        }
                        /*** aves ***/
                        var nPts = f.n;
                        var binWidth = Math.floor(nPts / nk);
                        var indices = [];
                        for(var j = 0; j < nk; ++j) {
                            indices.push(j * binWidth);
                        }
                        indices.push(nPts - 1);

                        /*** raw densities ***/
                        /*
                        var indices = [];
                        for(var j = 0; j < nk; ++j) {indices.push(j);}
                        */
                        /******/

                        var xc = indices.map(function (i) {
                            return o[0] + sk[0] * i;
                        });
                        var zc = indices.map(function (i) {
                            return o[1] + sk[1] * i;
                        });
                        var coords = geometry.transpose([zc, xc]);
                        var smin = 0;  //Math.min.apply(null, den);  // always 0?  otherwise plotting a false floor
                        var smax = Math.max.apply(null, den);
                        var fcs = plotting.colorScaleForPlot({ min: smin, max: smax }, $scope.modelName);

                        coords.forEach(function (c, i) {
                            if(i === coords.length - 1) {
                                return;
                            }
                            var p0 = c;
                            var p1 = coords[i+1];
                            var v = [[p0[0], p0[1]], [p1[0], p1[1]]];
                            v.srDensity = den[i];
                            var path = pg.append('path')
                                .attr('class', 'line')
                                .attr('style', 'stroke-width: 6px; stroke-linecap: square; cursor: default; stroke: ' +
                                        (den[i] > 0 ? fcs(den[i]) : 'black')
                                )
                                .datum(v);
                            path.on('mouseover', mouseOver);
                        });
                    });
                });
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

SIREPO.app.directive('optimizationFieldPicker', function(appState, warpvndService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: [
            '<div class="input-group">',
              '<select class="form-control" data-ng-model="model[field]" data-ng-options="item.index as item.name for item in optimizationFields()"></select>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var list = null;

            function buildList() {
                var labelMap = {};
                warpvndService.buildOptimizeFields().forEach(function(f) {
                    labelMap[f.field] = f.label;
                });
                list = [];
                appState.models.optimizer.fields.forEach(function(f, idx) {
                    list.push({
                        index: idx,
                        name: labelMap[f.field] ? labelMap[f.field] : '',
                    });
                });
            }

            $scope.optimizationFields = function() {
                return list;
            };

            appState.whenModelsLoaded($scope, buildList);
            $scope.$on('optimizer.changed', buildList);
        },
    };
});

SIREPO.app.directive('optimizerPathPlot', function(appState, plotting, plot2dService, warpvndService) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/plot2d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            var maxValue, optimizerFields, optimizerInfo, optimizerPoints, pointInfo, points, sortedPoints;

            function drawOptPoint(viewport) {
                viewport.selectAll('.warpvnd-opt-point').remove();
                viewport.selectAll('.line-2').remove();
                var row = warpvndService.optimizingRow;
                if (row) {
                    var p = [row[pointInfo.x_index], row[pointInfo.y_index]];
                    if (pointInfo.x_index == pointInfo.y_index) {
                        p[1] = 0;
                    }
                    viewport.append('path').attr('class', 'line line-2').datum(
                        [points[points.length - 1], p]);
                    viewport.selectAll('.line.line-2').attr('d', $scope.graphLine);
                    viewport.selectAll('.warpvnd-opt-point')
                        .data([p])
                        .enter().append('circle')
                        .attr('class', 'warpvnd-opt-point')
                        .attr('r', 8);
                    viewport.selectAll('.warpvnd-opt-point')
                        .attr('cx', $scope.graphLine.x())
                        .attr('cy', $scope.graphLine.y());
                }
            }

            function fieldLabel(field, optFields) {
                var res = name;
                optFields.some(function(f) {
                    if (field == f.field) {
                        res = f.label.replace('µ', '');
                        return true;
                    }
                });
                return res;
            }

            function tableRowHTML(label, value) {
                return '<tr>'
                    + '<td class="text-right" style="padding-right: 1ex"><b>' + label + '</b></td>'
                    + '<td class="text-right">' + value + '</td>'
                    + '</tr>';
            }

            function popupHTML(point) {
                var info = optimizerInfo[point[2]];
                var fields = optimizerPoints[point[2]];
                var optFields = warpvndService.buildOptimizeFields();
                return '<table>'
                    + optimizerFields.map(function(f, idx) {
                        return tableRowHTML(fieldLabel(f, optFields), fields[idx]);
                    }).join('')
                    + tableRowHTML('Steps', info[0])
                    + tableRowHTML('Time [s]', parseInt(info[1]))
                    + tableRowHTML('Tolerance', info[2].toExponential(3))
                    + tableRowHTML('Result', info[3])
                    + '</table>';
            }

            function resultForPoint(point) {
                return optimizerInfo[point[2]][3];
            }

            function updateOptimizingRow() {
                if (points) {
                    $scope.refresh();
                }
            }

            $scope.destroy = function() {
                $('.warpvnd-scatter-point').popover('hide');
                $('.warpvnd-scatter-point').off();
            };

            $scope.init = function() {
                plot2dService.init2dPlot($scope, {
                    aspectRatio: 4.0 / 7,
                    margin: {top: 20, right: 80, bottom: 50, left: 70},
                    zoomContainer: '.plot-viewport',
                    wantColorbar: true,
                    isZoomXY: true,
                });
                //TODO(pjm): move to plot2dService
                // can't remove the overlay or it causes a memory leak
                $scope.select('svg').selectAll('.overlay').classed('disabled-overlay', true);

                $scope.warpvndService = warpvndService;
                $scope.$watch('warpvndService.optimizingRow', updateOptimizingRow);
            };

            $scope.load = function(json) {
                optimizerFields = json.fields;
                optimizerInfo = json.optimizerInfo;
                optimizerPoints = json.optimizerPoints;
                var isOneVariable = json.x_field == json.y_field;
                // points is an array of [x, y, index]
                points = d3.zip(
                    optimizerPoints.map(function(v) {
                        return v[json.x_index];
                    }),
                    optimizerPoints.map(function(v) {
                        return isOneVariable ? 0 : v[json.y_index];
                    }),
                    optimizerPoints.map(function(v, idx) {
                        return idx;
                    }));
                pointInfo = {
                    x_index: json.x_index,
                    y_index: json.y_index,
                };
                sortedPoints = appState.clone(points).sort(function(v1, v2) {
                    return resultForPoint(v1) - resultForPoint(v2);
                });
                maxValue = json.v_max;
                var xdom = [json.x_range[0], json.x_range[1]];
                var ydom = [json.y_range[0], json.y_range[1]];
                if (appState.deepEquals(xdom, $scope.axes.x.domain)
                    && appState.deepEquals(ydom, $scope.axes.y.domain)) {
                    // domain is unchanged, don't change current zoom
                }
                else {
                    // reset scaling
                    $scope.axes.x.domain = xdom;
                    $scope.axes.x.scale.domain(xdom);
                    $scope.axes.y.domain = ydom;
                    $scope.axes.y.scale.domain($scope.axes.y.domain).nice();
                }
                var viewport = $scope.select('.plot-viewport');
                viewport.selectAll('.line').remove();
                viewport.append('path').attr('class', 'line line-1').datum(points);
                var optFields = warpvndService.buildOptimizeFields();
                json.x_label = fieldLabel(json.x_field, optFields);
                $scope.isZoomXY = ! isOneVariable;
                if (isOneVariable) {
                    json.y_label = '';
                }
                else {
                    json.y_label = fieldLabel(json.y_field, optFields);
                }
                $scope.updatePlot(json);
            };

            $scope.refresh = function() {
                var viewport = $scope.select('.plot-viewport');
                drawOptPoint(viewport);
                viewport.selectAll('.line').attr('d', $scope.graphLine);
                $('.warpvnd-scatter-point').popover('hide');
                viewport.selectAll('.warpvnd-scatter-point')
                    .data(sortedPoints)
                    .enter().append('circle')
                    .attr('class', 'warpvnd-scatter-point')
                    .attr('r', 8)
                    .on('mouseover', function() {
                        var obj = d3.select(this);
                        if (! obj.empty()) {
                            $scope.pointer.pointTo(resultForPoint(obj.datum()));
                        }
                    })
                    .on('click', function() {
                        var obj = d3.select(this);
                        $(this).popover({
                            trigger: 'manual',
                            html: true,
                            placement: 'bottom',
                            container: 'div.panel-body',
                            content: function() {
                                return popupHTML(obj.datum());
                            },
                        });
                        $('.warpvnd-scatter-point').not($(this)).popover('hide');
                        $(this).popover('toggle');
                    });
                viewport.selectAll('.warpvnd-scatter-point')
                    .attr('cx', $scope.graphLine.x())
                    .attr('cy', $scope.graphLine.y())
                    .attr('style', function(d) {
                        var result = resultForPoint(d);
                        var res = 'fill: ' + $scope.colorScale(result);
                        if (result == maxValue) {
                            res += '; stroke-width: 2; stroke: black';
                        }
                        return res;
                    })
                    // position circles on top of all other svg elements
                    .each(function() {
                        this.parentNode.appendChild(this);
                    });
                viewport.selectAll('.warpvnd-opt-point').each(function() {
                    this.parentNode.appendChild(this);
                });
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('conductors3d', function(appState, errorService, geometry, plotToPNG, utilities, vtkPlotting, warpvndService) {
    return {
        restrict: 'A',
        scope: {
            parentController: '=',
            reportId: '<',
        },
        template: [
            '', //'<div></div>',
        ].join(''),
        controller: function($scope, $element) {

            var rpt = warpvndService.activeComparisonReport();
            var fcr =  appState.models[rpt];

            var CELL_COLORS = SIREPO.APP_SCHEMA.constants.cellColors;
            $scope.defaultColor = SIREPO.APP_SCHEMA.constants.nonZeroVoltsColor;

            var zeroVoltsColor = vtk.Common.Core.vtkMath.hex2float(SIREPO.APP_SCHEMA.constants.zeroVoltsColor);
            var voltsColor = vtk.Common.Core.vtkMath.hex2float(SIREPO.APP_SCHEMA.constants.nonZeroVoltsColor);
            var fsRenderer = null;

            // this canvas is the one created by vtk
            var canvas3d;

            // we keep this one updated with a copy of the vtk canvas
            var snapshotCanvas;
            var snapshotCtx;

            var stlActors = {};
            var stlReaders = {};

            // if we have stl-type conductors, we might need to rescale the grid for drawing
            // (easier and faster than scaling the data)
            var toMetersFactor = Math.min.apply(null, warpvndService.stlNanoUnits);
            var toMicronFactor = 1.0;
            var gridOffsets = [0, 0, 0];
            var domain = {
                width: 1,
                height: 1,
                depth: 1,
            };
            var xfactor = 1;

            /*
            function addCarats() {

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
                if (fcr[field] > range.length) {
                    fcr[field] = range.length - 1;
                }
                return {
                    index: index,
                    field: field,
                    pos: fcr[field],
                    dimension: dimension,
                    range: range,
                };
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
            */

            function addConductors() {
                var typeMap = warpvndService.conductorTypeMap();

                // do stl conductors first so we have a proper scale
                appState.models.conductors.filter(function (c) {
                    return warpvndService.getConductorType(c) === 'stl';
                }).forEach(function (c) {
                    var cModel = typeMap[c.conductorTypeId];
                    toMetersFactor = Math.max(toMetersFactor, cModel.scale);
                    toMicronFactor = 1e-6 / toMetersFactor;
                    setScaling();
                    // no need to reload data
                    var r = vtkPlotting.getSTLReader(cModel.file);
                    if (! r) {
                        loadConductor(c, cModel);
                    }
                    else {
                        setupConductor(r, c, cModel);
                    }
                });

                setScaling();
                appState.models.conductors.filter(function (c) {
                    return warpvndService.getConductorType(c) === 'box';
                }).forEach(function(c) {
                    var cModel = typeMap[c.conductorTypeId];
                    var vColor = vtk.Common.Core.vtkMath.hex2float(cModel.color || '#6992ff');
                    var zColor = vtk.Common.Core.vtkMath.hex2float(cModel.color || '#f3d4c8');
                    // model (z, x, y) --> (x, y, z)
                    addSource(
                        vtk.Filters.Sources.vtkCubeSource.newInstance({
                            xLength: toMicronFactor * xfactor * cModel.zLength,
                            yLength: toMicronFactor * cModel.xLength,
                            zLength: toMicronFactor * cModel.yLength,
                            center: [
                                toMicronFactor * xfactor * c.zCenter,
                                toMicronFactor * c.xCenter,
                                toMicronFactor * c.yCenter,
                            ],
                        }),
                        {
                            color: cModel.voltage == 0 ? zColor : vColor,
                            edgeVisibility: true,
                        });
                });
                return {
                    x: [0, xfactor * domain.width],
                    y: [-domain.height / 2.0, domain.height / 2.0],
                    z: [-domain.depth / 2.0, domain.depth / 2.0],
                };
            }

            function addPlane(pointRanges, index, color) {
                addSource(
                    vtk.Filters.Sources.vtkPlaneSource.newInstance({
                        origin: [pointRanges.x[index], pointRanges.y[0], pointRanges.z[0]],
                        point1: [pointRanges.x[index], pointRanges.y[0], pointRanges.z[1]],
                        point2: [pointRanges.x[index], pointRanges.y[1], pointRanges.z[0]],
                    }),
                    {
                        color: color,
                    });
            }

            function addSource(source, actorProperties) {
                if (! fsRenderer) {
                    return;
                }
                var actor = vtk.Rendering.Core.vtkActor.newInstance();
                actorProperties.lighting = false;
                actor.getProperty().set(actorProperties);
                var mapper = vtk.Rendering.Core.vtkMapper.newInstance();
                mapper.setInputConnection(source.getOutputPort());
                actor.setMapper(mapper);
                fsRenderer.getRenderer().addActor(actor);
                return;
            }

            var isAdjustingSize = false;
            function adjustSize(rect) {
                if (isAdjustingSize) {
                    isAdjustingSize = false;
                    return;
                }
                var cnt = $($element);
                var fitThreshold = 0.01;
                var cntAspectRatio = 1.3;
                isAdjustingSize = vtkPlotting.adjustContainerSize(cnt, rect, cntAspectRatio, fitThreshold);
                if (isAdjustingSize) {
                    fsRenderer.resize();
                }
            }

            function init() {
                var rw = $($element);
                rw.on('dblclick', reset);

                // removed listenWindowResize: false - turns out we need it for fullscreen to work.
                // Instead we remove the event listener ourselves on destroy
                fsRenderer = vtk.Rendering.Misc.vtkFullScreenRenderWindow.newInstance(
                    {
                        background: [1, 1, 1, 1],
                        container: rw[0],
                    });
                fsRenderer.getRenderer().getLights()[0].setLightTypeToSceneLight();
                fsRenderer.setResizeCallback(adjustSize);

                rw.on('pointerup', cacheCanvas);
                rw.on('wheel', function () {
                    utilities.debounce(cacheCanvas, 100)();
                });

                canvas3d = $($element).find('canvas')[0];

                // this canvas is used to store snapshots of the 3d canvas
                snapshotCanvas = document.createElement('canvas');
                snapshotCtx = snapshotCanvas.getContext('2d');
                plotToPNG.addCanvas(snapshotCanvas, $scope.reportId);

                refresh();
            }

            var labMatrix = [
                0, 1, 0, 0,
                0, 0, -1, 0,
                1, 0, 0, 0,
                0, 0, 0, 1
            ];  //stl
            //var labMatrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];  //unit

            function loadConductor(conductor, type) {
                $scope.parentController.isWaitoingForSTL = true;
                vtkPlotting.loadSTLFile(type.file).then(function (r) {
                    vtkPlotting.addSTLReader(type.file, r);
                    loadConductorData(r, conductor, type);
                });
            }

            function loadConductorData(reader, conductor, type) {
                if (! reader) {
                    return;
                }
                reader.loadData()
                    .then(function (res) {
                        setupConductor(reader, conductor, type);
                    }, function (reason) {
                        throw type.file + ': Error loading data from .stl file: ' + reason;
                    },
                        showLoadProgress
                ).catch(function (e) {
                    $scope.parentController.isWaitingForSTL = false;
                    errorService.alertText(e);
                });

            }

            function setScaling() {
                var grid = appState.models.simulationGrid;
                var ASPECT_RATIO = 4.0 / 7;
                domain = {
                    width: toMicronFactor * grid.plate_spacing,
                    height: toMicronFactor * grid.channel_width,
                    depth: toMicronFactor * grid.channel_height,
                };
                xfactor = domain.height / domain.width / ASPECT_RATIO;
            }

            function setupConductor(reader, conductor, type) {
                if (! fsRenderer) {
                    return;
                }
                var bounds = reader.getOutputData().getBounds();
                var xOffset = bounds[0] + (bounds[1] - bounds[0]) / 2;
                var yOffset = bounds[2] + (bounds[3] - bounds[2]) / 2;
                var zOffset = bounds[4] + (bounds[5] - bounds[4]) / 2;
                var cColor = vtk.Common.Core.vtkMath.hex2float(type.color || SIREPO.APP_SCHEMA.constants.nonZeroVoltsColor);
                var a = vtk.Rendering.Core.vtkActor.newInstance();
                var smapper = vtk.Rendering.Core.vtkMapper.newInstance();
                a.setMapper(smapper);
                smapper.setInputConnection(reader.getOutputPort());
                a.setUserMatrix(labMatrix);  // rotates from lab to "vtk world" coords
                var offsetPos = [
                    toMicronFactor * conductor.xCenter - xOffset,
                    toMicronFactor * conductor.yCenter - yOffset,
                    toMicronFactor * xfactor * conductor.zCenter - zOffset
                ];
                a.addPosition(offsetPos);
                a.getProperty().setColor(cColor[0], cColor[1], cColor[2]);
                //a.getProperty().setEdgeVisibility(true);
                a.getProperty().setLighting(false);
                fsRenderer.getRenderer().addActor(a);
                stlActors[conductor.id] = a;
                $scope.parentController.isWaitingForSTL = false;
                reset();
            }

            function showLoadProgress() {
                //srdbg('...still loading...');
            }

            function refresh() {
                if (! fsRenderer) {
                    return;
                }
                removeActors();
                var pointRanges = addConductors();

                addPlane(pointRanges, 0, zeroVoltsColor);
                addPlane(pointRanges, 1, voltsColor);
                var padding = (pointRanges.x[1] - pointRanges.x[0]) / 1000.0;
                addSource(
                    vtk.Filters.Sources.vtkCubeSource.newInstance({
                        xLength: pointRanges.x[1] - pointRanges.x[0] + padding,
                        yLength: pointRanges.y[1] - pointRanges.y[0] + padding,
                        zLength: pointRanges.z[1] - pointRanges.z[0] + padding,
                        center: [(pointRanges.x[1] - pointRanges.x[0]) / 2.0, 0, 0],
                    }),
                    {
                        edgeVisibility: true,
                        frontfaceCulling: true,
                    });
                reset();
            }

            function removeActors() {
                var renderer = fsRenderer.getRenderer();
                renderer.getActors().forEach(function(actor) {
                    renderer.removeActor(actor);
                });
            }

            function reset() {
                var renderer = fsRenderer.getRenderer();
                var cam = renderer.get().activeCamera;
                cam.setPosition(0, 0, 1);
                cam.setFocalPoint(0, 0, 0);
                cam.setViewUp(0, 1, 0);
                renderer.resetCamera();
                cam.zoom(1.3);
                fsRenderer.getRenderWindow().render();
                cacheCanvas();
            }
            function cacheCanvas() {
                if (! snapshotCtx) {
                    return;
                }
                var w = parseInt(canvas3d.getAttribute('width'));
                var h = parseInt(canvas3d.getAttribute('height'));
                snapshotCanvas.width = w;
                snapshotCanvas.height = h;
                // this call makes sure the buffer is fresh (it appears)
                fsRenderer.getOpenGLRenderWindow().traverseAllPasses();
                snapshotCtx.drawImage(canvas3d, 0, 0, w, h);
            }

            $scope.$on('conductors.changed', refresh);
            $scope.$on('$destroy', function() {
                $element.off();
                window.removeEventListener('resize', fsRenderer.resize);
                fsRenderer.getInteractor().unbindEvents();
                fsRenderer.delete();
                plotToPNG.removeCanvas($scope.reportId);
            });

            appState.whenModelsLoaded($scope, function() {
                init();
                $scope.$on('simulationGrid.changed', refresh);
                $scope.$on('box.changed', refresh);
                $scope.$on('stl.changed', refresh);
            });
        },
    };
});


SIREPO.app.service('warpVTKService', function(vtkPlotting, geometry) {

    var svc = this;

    var startPlaneBundle;
    var endPlaneBundle;
    var conductorBundles = [];
    var outlineBundle;
    var orientationMarker;

    // colors - vtk uses a range of 0-1 for RGB components
    //TODO(mvk): set colors on the model, keeping these as defaults
    var zeroVoltsColor = [243.0/255.0, 212.0/255.0, 200.0/255.0];
    var voltsColor = [105.0/255.0, 146.0/255.0, 255.0/255.0];

    this.initScene = function (coordMapper, renderer) {

        // the emitter plane
        startPlaneBundle = coordMapper.buildPlane();
        startPlaneBundle.actor.getProperty().setColor(zeroVoltsColor[0], zeroVoltsColor[1], zeroVoltsColor[2]);
        startPlaneBundle.actor.getProperty().setLighting(false);
        renderer.addActor(startPlaneBundle.actor);

        // the collector plane
        endPlaneBundle = coordMapper.buildPlane();
        endPlaneBundle.actor.getProperty().setColor(voltsColor[0], voltsColor[1], voltsColor[2]);
        endPlaneBundle.actor.getProperty().setLighting(false);
        renderer.addActor(endPlaneBundle.actor);

        // a box around the elements, for visual clarity
        outlineBundle = coordMapper.buildBox();
        outlineBundle.actor.getProperty().setColor(1, 1, 1);
        outlineBundle.actor.getProperty().setEdgeVisibility(true);
        outlineBundle.actor.getProperty().setEdgeColor(0, 0, 0);
        outlineBundle.actor.getProperty().setFrontfaceCulling(true);
        outlineBundle.actor.getProperty().setLighting(false);
        renderer.addActor(outlineBundle.actor);

        /*
        orientationMarker = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
            actor: vtk.Rendering.Core.vtkAxesActor.newInstance(),
            interactor: renderWindow.getInteractor()
        });
        orientationMarker.setEnabled(true);
        orientationMarker.setViewportCorner(
            vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.TOP_RIGHT
        );
        orientationMarker.setViewportSize(0.08);
        orientationMarker.setMinPixelSize(100);
        orientationMarker.setMaxPixelSize(300);
        */
   };

    this.updateScene = function (coordMapper, axisInfo) {

        coordMapper.setPlane(startPlaneBundle.source,
            [axisInfo.x.min, axisInfo.y.min, axisInfo.z.min],
            [axisInfo.x.min, axisInfo.y.max, axisInfo.z.min],
            [axisInfo.x.max, axisInfo.y.min, axisInfo.z.min]
        );
        coordMapper.setPlane(endPlaneBundle.source,
            [axisInfo.x.min, axisInfo.y.min, axisInfo.z.max],
            [axisInfo.x.min, axisInfo.y.max, axisInfo.z.max],
            [axisInfo.x.max, axisInfo.y.min, axisInfo.z.max]
        );

        var padding = 0.01;
        var spsOrigin = startPlaneBundle.source.getOrigin();
        var epsOrigin = endPlaneBundle.source.getOrigin();
        var epsP1 = endPlaneBundle.source.getPoint1();
        var epsP2 = endPlaneBundle.source.getPoint2();

        var osXLen = Math.abs(epsOrigin[0] - spsOrigin[0]) + padding;
        var osYLen = Math.abs(epsP2[1] - epsP1[1]) + padding;
        var osZLen = Math.abs(epsP2[2] - epsP1[2]) + padding;
        var osCtr = [];
        for(var i = 0; i < 3; ++i) {
            osCtr.push((epsOrigin[i] - spsOrigin[i]) / 2.0);
        }
        outlineBundle.setLength([
            Math.abs(epsOrigin[0] - spsOrigin[0]) + padding,
            Math.abs(epsP2[1] - epsP1[1]) + padding,
            Math.abs(epsP2[2] - epsP1[2]) + padding
        ]);
        outlineBundle.setCenter(osCtr);

    };

    this.getStartPlane = function () {
        return startPlaneBundle;
    };
    this.getEndPlane = function () {
        return endPlaneBundle;
    };
    this.getOutline = function () {
        return outlineBundle;
    };

});

// NOTE: the vtk and warp coordinate systems are related the following way:
//    vtk X (left to right) = warp Z
//    vtk Y (bottom to top) = warp X
//    vtk Z (out to in) = warp Y
SIREPO.app.directive('particle3d', function(appState, errorService, frameCache, geometry, layoutService, panelState, plotting, plotToPNG, requestSender, utilities, vtkPlotting, warpvndService, $timeout) {

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            reportId: '<',
        },
        templateUrl: '/static/html/particle3d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope, $element) {

            var d3self;
            var xzAspectRatio = 4.0 / 7.0;
            $scope.margin = {top: 50, right: 23, bottom: 50, left: 75};
            $scope.width = $scope.height = 0;
            $scope.axesMargins = {
                x: { width: 16.0, height: 0.0 },
                y: { width: 0.0, height: 16.0 }
            };

            // little test boxes are useful for translating vtk space to screen space
            $scope.testBoxes = [];

            // The side of the plot facing the user
            $scope.side = 'y';
            $scope.xdir = 1;
            $scope.ydir = 1;
            $scope.zdir = 1;

            $scope.canInteract = true;
            $scope.interactionStyle = function() {
                if (! $scope.canInteract) {
                    return {
                        'cursor': 'not-allowed'
                    };
                }
                return {
                    'cursor': 'pointer'
                };
            };

            $scope.dataCleared = true;

            $scope.hasAbsorbed = false;
            $scope.hasConductors = false;
            $scope.hasReflected = false;
            $scope.showAbsorbed = true;
            $scope.showReflected = true;
            $scope.showImpact = true;
            $scope.enableImpactDensity = true;
            $scope.showImpactDensity = false;
            $scope.showConductors = true;

            // these are in screen/vtk coords, not lab coords
            //TODO(mvk): should refer only to lab coords outside of plotting-vtk (?)
            var axes = {
                x: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh, utilities),
                y: layoutService.plotAxis($scope.margin, 'y', 'left', refresh, utilities),
                z: layoutService.plotAxis($scope.margin, 'z', 'bottom', refresh, utilities)
            };
            var axisCfg = {};
            var boundAxes = {};

            // rendering
            var fsRenderer = null;
            var renderWindow = null;
            var mainView = null;
            var renderer = null;
            var cam = null;
            var camPos = [0, 0, 1];
            var camViewUp = [0, 1, 0];
            var camFP = [0, 0, 0];
            var camZoom = 1.3;
            var lastCamPos = camPos;
            var lastCamViewUp = camViewUp;
            var lastCamFP = camFP;
            var lastCamZoom = camZoom;
            var interactor;

            // planes
            var gridPlaneBundles = [];

            var startPlaneBundle = null;
            var endPlaneBundle = null;
            var densityPlaneBundles = [];

            // conductors (boxes)
            var conductorBundles = [];
            var conductorActors = [];

            var stlActors = {};
            var stlReaders = {};

            var toMetersFactor = Math.min.apply(null, warpvndService.stlNanoUnits);
            var toMicronFactor = 1e-6;
            var gridOffsets = [0, 0, 0];
            var xfactor = 1;

            // lines
            var absorbedLineBundle;
            var reflectedLineBundle;

            // spheres
            var impactSphereActors = [];

            // other
            var densityBundles = [];

            // outline
            var outlineSource = null;
            var outlineBundle = null;
            var vpOutline = null;

            // orientation cube/axis
            var orientationMarker = null;

            // geometry
            var coordMapper = vtkPlotting.coordMapper();
            var scaleTransform = coordMapper.xform;
            var scaleTransformNorm = coordMapper.xform;

            // data
            var numPoints = 0;
            var pointData = {};
            var fieldData = {};
            var impactData = [];
            var xmin = 0.0;  var xmax = 1.0;
            var ymin = 0.0;  var ymax = 1.0;
            var zmin = 0.0;  var zmax = 1.0;

            var heatmap = [];
            var fieldXFactor = 1.0;
            var fieldZFactor = 1.0;
            var fieldYFactor = 1.0;
            var fieldColorScale = null;
            var indexMaps = [];

            var minZSpacing = Number.MAX_VALUE;

            var impactSphereSize = 0.0125 * xzAspectRatio;
            var zoomUnits = 0;
            var didPan = false;
            var sceneRect;
            var sceneArea;
            var screenRect;
            var malSized = false;
            var offscreen = false;
            var picker = vtk.Rendering.Core.vtkPicker.newInstance();

            // colors - vtk uses a range of 0-1 for RGB components
            var zeroVoltsColor = vtk.Common.Core.vtkMath.hex2float(SIREPO.APP_SCHEMA.constants.zeroVoltsColor);
            var voltsColor = vtk.Common.Core.vtkMath.hex2float(SIREPO.APP_SCHEMA.constants.nonZeroVoltsColor);
            var particleTrackColor = vtk.Common.Core.vtkMath.hex2float(SIREPO.APP_SCHEMA.constants.particleTrackColor);
            var reflectedParticleTrackColor = vtk.Common.Core.vtkMath.hex2float(SIREPO.APP_SCHEMA.constants.reflectedParticleTrackColor);

            // this canvas is the one created by vtk
            var canvas3d;

            // we keep this one updated with a copy of the vtk canvas
            var snapshotCanvas;
            var snapshotCtx;

            document.addEventListener(utilities.fullscreenListenerEvent(), refresh);

            function addSTLConductors() {
                var typeMap = warpvndService.conductorTypeMap();

                appState.models.conductors.filter(function (c) {
                    return warpvndService.getConductorType(c) === 'stl';
                }).forEach(function (c) {
                    var cModel = typeMap[c.conductorTypeId];
                    toMetersFactor = Math.max(toMetersFactor, cModel.scale);
                    toMicronFactor = 1e-6 / toMetersFactor;
                    loadConductor(c, cModel);
                });
            }

            var stl_cm = vtkPlotting.coordMapper();
            function loadConductor(conductor, type) {
                $scope.isWaitingForSTL = true;
                // put stl coordinates to meters.  This is independent of the
                // scaling of warp data (which is already in meters)
                stl_cm = buildSTLCoordMapper(toMetersFactor);
                stl_cm.buildSTL(type.file, conductorLoader(conductor, type));
            }

            function conductorLoader(conductor, type) {
                return function (bundle) {
                    setupConductor(bundle, conductor, type);
                };
            }

            function buildSTLCoordMapper(scale) {
                var t1 = geometry.transform([
                    [0, 1, 0],
                    [0, 0, -1],
                    [1, 0, 0]
                ]);
                var t2 = geometry.transform(
                     [
                        [scale, 0, 0],
                        [0, scale, 0],
                        [0, 0, scale]
                    ]
                );
                return vtkPlotting.coordMapper(t2.compose(t1).compose(scaleTransform));
            }

            function setupConductor(bundle, conductor, type) {
                var reader = bundle.source;
                var actor = bundle.actor;
                var bounds = reader.getOutputData().getBounds();
                var xOffset = bounds[0] + (bounds[1] - bounds[0]) / 2;
                var yOffset = bounds[2] + (bounds[3] - bounds[2]) / 2;
                var zOffset = bounds[4] + (bounds[5] - bounds[4]) / 2;
                // the conductor centers are in microns
                var offsetPos = [
                    toMicronFactor * conductor.yCenter - yOffset,
                    toMicronFactor * conductor.xCenter - xOffset,
                    toMicronFactor * conductor.zCenter - zOffset
                ];
                var cColor = vtk.Common.Core.vtkMath.hex2float(type.color || SIREPO.APP_SCHEMA.constants.nonZeroVoltsColor);
                actor.addPosition(offsetPos);
                actor.getProperty().setColor(cColor[0], cColor[1], cColor[2]);
                actor.getProperty().setLighting(false);
                fsRenderer.getRenderer().addActor(actor);
                stlActors[conductor.id] = actor;
            }

            function getSTLActors() {
                var arr = [];
                for (var id in stlActors) {
                    arr.push(stlActors[id]);
                }
                return arr;
            }

            var cFactor = 1000000.0;
            function scaleWithShave(a) {
                var shave = 0.01;
                return (1.0 - shave) * a / cFactor;
            }

            function scaleConductor(a) {
                return a / cFactor;
            }

            $scope.requestData = function() {
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
                                frameCache.getFrame('impactDensityAnimation', 0, false, function(index, data) {
                                    if ($scope.element) {
                                        if (data.error) {
                                            panelState.setError($scope.modelName, data.error);
                                            return;
                                        }
                                        panelState.setError($scope.modelName, null);
                                        impactData = data;
                                        $scope.load();
                                    }
                                });
                             }
                        });
                    }
                });
            };

            $scope.init = function() {

                d3self = d3.selectAll($element);

                var rw = angular.element($($element).find('.sr-plot-particle-3d .vtk-canvas-holder'))[0];
                fsRenderer = vtk.Rendering.Misc.vtkFullScreenRenderWindow.newInstance({
                    background: [1, 1, 1, 1],
                    container: rw,
                    listenWindowResize: false,
                });
                renderer = fsRenderer.getRenderer();
                renderer.getLights()[0].setLightTypeToSceneLight();
                renderWindow = fsRenderer.getRenderWindow();
                interactor = renderWindow.getInteractor();
                mainView = renderWindow.getViews()[0];

                cam = renderer.get().activeCamera;

                rw.addEventListener('dblclick', resetAndDigest);

                var worldCoord = vtk.Rendering.Core.vtkCoordinate.newInstance({
                    renderer: renderer
                });
                worldCoord.setCoordinateSystemToWorld();

                var isDragging = false;
                var isPointerUp = true;
                rw.onpointerdown = function(evt) {
                    isDragging = false;
                    isPointerUp = false;
                };
                rw.onpointermove = function(evt) {
                    if (isPointerUp) {
                        return;
                    }
                    isDragging = true;
                    didPan = didPan || evt.shiftKey;
                    $scope.side = null;
                    utilities.debounce(refresh, 100)();
                };
                rw.onpointerup = function(evt) {
                    if (! isDragging) {
                        // use picker to display info on objects
                    }
                    isDragging = false;
                    isPointerUp = true;
                    refresh(true);
                };
                rw.onwheel = function(evt) {
                    var camPos = cam.getPosition();

                    // If zoom needs to be halted or limited, it can be done here.  For now track the "zoom units"
                    // for managing refreshing and resetting
                    if (! malSized) {
                        zoomUnits += evt.deltaY;
                    }
                    utilities.debounce(
                        function() {
                            refresh(true);
                        },
                        100)();
                };

                //warpVTKService.initScene(coordMapper, renderer);

                // the emitter plane
                startPlaneBundle = coordMapper.buildPlane();
                startPlaneBundle.actor.getProperty().setColor(zeroVoltsColor[0], zeroVoltsColor[1], zeroVoltsColor[2]);
                //startPlaneBundle.actor.getProperty().setOpacity(0.5);
                startPlaneBundle.actor.getProperty().setLighting(false);
                renderer.addActor(startPlaneBundle.actor);

                // the collector plane
                endPlaneBundle = coordMapper.buildPlane();
                endPlaneBundle.actor.getProperty().setColor(voltsColor[0], voltsColor[1], voltsColor[2]);
                //endPlaneBundle.actor.getProperty().setOpacity(0.5);
                endPlaneBundle.actor.getProperty().setLighting(false);
                renderer.addActor(endPlaneBundle.actor);

                // a box around the elements, for visual clarity
                outlineBundle = coordMapper.buildBox();
                outlineSource =  outlineBundle.source;

                outlineBundle.actor.getProperty().setColor(1, 1, 1);
                outlineBundle.actor.getProperty().setEdgeVisibility(true);
                outlineBundle.actor.getProperty().setEdgeColor(0, 0, 0);
                outlineBundle.actor.getProperty().setFrontfaceCulling(true);
                outlineBundle.actor.getProperty().setLighting(false);
                renderer.addActor(outlineBundle.actor);

                vpOutline = vtkPlotting.vpBox(outlineBundle.source, renderer);

                // a little widget that mirrors the orientation (not the scale) of the scence
                var axesActor = vtk.Rendering.Core.vtkAxesActor.newInstance();
                orientationMarker = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
                    actor: axesActor,
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
                for (var d = 0; d < 3; ++d) {
                    var dpb = [];
                    for (var s = 0; s < 1; ++s) {
                        var pb = coordMapper.buildPlane();
                        pb.actor.getProperty().setColor(0, 0, 0);
                        pb.actor.getProperty().setLighting(false);
                        pb.actor.getProperty().setRepresentationToWireframe();
                        renderer.addActor(pb.actor);
                        dpb.push(pb);
                    }
                    gridPlaneBundles.push(dpb);
                }

                absorbedLineBundle = coordMapper.buildActorBundle();
                reflectedLineBundle = coordMapper.buildActorBundle();

                canvas3d = $($element).find('canvas')[0];

                // this canvas is used to store snapshots of the 3d canvas
                snapshotCanvas = document.createElement('canvas');
                snapshotCtx = snapshotCanvas.getContext('2d');
                plotToPNG.addCanvas(snapshotCanvas, $scope.reportId);
            };

            $scope.load = function() {
                $scope.dataCleared = false;

                vtkPlotting.removeActors(renderer, impactSphereActors);
                vtkPlotting.removeActors(renderer, conductorActors);

                densityPlaneBundles = [];
                densityBundles = [];

                conductorActors = [];
                conductorBundles = [];
                impactSphereActors = [];

                if (!pointData) {
                    return;
                }

                var grid = appState.models.simulationGrid;

                // particle min/max
                var xpoints = pointData.points;
                xmin = pointData.y_range[0];
                xmax = pointData.y_range[1];

                var zpoints = pointData.x_points;
                zmin = pointData.x_range[0];
                zmax = pointData.x_range[1];

                var ypoints = pointData.z_points;
                ymin = pointData.z_range[0];
                ymax = pointData.z_range[1];

                // grid min/max
                var gXMin = 1e-6 * (-grid.channel_width / 2.0);
                var gXMax = 1e-6 * (grid.channel_width / 2.0);
                var gYMin = 1e-6 * (-grid.channel_height / 2.0);
                var gYMax = 1e-6 * (grid.channel_height / 2.0);
                var gZMin = 0;
                var gZMax = 1e-6 * grid.plate_spacing;

                var lcoords = [];
                var lostCoords = [];
                zpoints.forEach(function(z, i) {
                    lcoords.push(geometry.transpose([xpoints[i], ypoints[i], zpoints[i]]));
                });
                pointData.lost_z.forEach(function(z, i) {
                    lostCoords.push(geometry.transpose([pointData.lost_y[i], pointData.lost_z[i], pointData.lost_x[i]]));
                });

                $scope.hasAbsorbed = lcoords.length > 0;
                $scope.hasConductors = appState.models.conductors.length > 0;

                axisCfg = {
                    x: {
                        dimLabel: 'z',
                        label: pointData.x_label,
                        min: gZMin,
                        max: gZMax,
                        numPoints: zpoints.length,
                        screenDim: 'x',
                    },
                    y: {
                        dimLabel: 'x',
                        label: pointData.y_label,
                        min: gXMin,
                        max: gXMax,
                        numPoints: xpoints.length,
                        screenDim: 'y',
                    },
                    z: {
                        dimLabel: 'y',
                        label: pointData.z_label,
                        min: gYMin,
                        max: gYMax,
                        numPoints: ypoints.length,
                        screenDim: 'x',
                    },
                };


                var yzAspectRatio =  grid.channel_height / grid.channel_width;

                // vtk makes things fit so it does not particularly care about the
                // absolute sizes of things - except that really small values (e.g. 10^-7) don't scale
                // up properly.  We use these scaling factors to overcome that problem

                // This defines how axes are mapped...
                var t1 = geometry.transform(SIREPO.PLOT_3D_CONFIG.coordMatrix);

                // ...this scales the new axes (also used for stl conductors)
                scaleTransform = geometry.transform(
                     [
                        [1.0 / Math.abs(gZMax - gZMin), 0, 0],
                        [0, xzAspectRatio / Math.abs(gXMax - gXMin), 0],
                        [0, 0, yzAspectRatio * xzAspectRatio / Math.abs(gYMax - gYMin)]
                     ]
                );
                coordMapper = vtkPlotting.coordMapper(scaleTransform.compose(t1));

                coordMapper.setPlane(startPlaneBundle,
                    [gXMin, gYMin, gZMin],
                    [gXMin, gYMax, gZMin],
                    [gXMax, gYMin, gZMin]
                );
                coordMapper.setPlane(endPlaneBundle,
                    [gXMin, gYMin, gZMax],
                    [gXMin, gYMax, gZMax],
                    [gXMax, gYMin, gZMax]
                );


                var padding = 0.01;
                var spsOrigin = startPlaneBundle.source.getOrigin();
                var epsOrigin = endPlaneBundle.source.getOrigin();
                var epsP1 = endPlaneBundle.source.getPoint1();
                var epsP2 = endPlaneBundle.source.getPoint2();

                var osXLen = Math.abs(epsOrigin[0] - spsOrigin[0]) + padding;
                var osYLen = Math.abs(epsP2[1] - epsP1[1]) + padding;
                var osZLen = Math.abs(epsP2[2] - epsP1[2]) + padding;
                var osCtr = [];
                epsOrigin.forEach(function(o, i) {
                    osCtr.push((o - spsOrigin[i]) / 2.0);
                });

                outlineBundle.setLength([
                    Math.abs(epsOrigin[0] - spsOrigin[0]) + padding,
                    Math.abs(epsP2[1] - epsP1[1]) + padding,
                    Math.abs(epsP2[2] - epsP1[2]) + padding
                ]);
                outlineBundle.setCenter(osCtr);


                for (var d = 0; d < 3; ++d) {
                    for (var s = 0; s < 1; ++s) {
                        var pb = gridPlaneBundles[d][s];
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
                        vtkPlotting.coordMapper().setPlane(pb, gpOrigin, gpP1, gpP2);
                    }
                }

                // evenly spaced points to be linearly interpolated between the data, for
                // purposes of coloring lines with the field colors
                var numInterPoints = 50;

                for (var dim in axes) {
                    var cfg = axisCfg[dim];
                    axes[dim].init();
                    axes[dim].svgAxis.tickSize(0);
                    axes[dim].values = plotting.linearlySpacedArray(cfg.min, cfg.max, cfg.numPoints);
                    axes[dim].scale.domain([cfg.min, cfg.max]);
                    axes[dim].parseLabelAndUnits(cfg.label);
                }

                minZSpacing = Math.abs((zmax - zmin)) / numInterPoints;
                var nearestIndex = 0;
                indexMaps = [];

                // linearly interpolate the data
                for (var i = 0; i < lcoords.length; ++i) {
                    var ptsArr = lcoords[i];

                    var newIndexMap = {0:0};
                    var lastNearestIndex = 0;
                    nearestIndex = 1;
                    var newZ = ptsArr[0][2];
                    var finalZ = ptsArr[ptsArr.length-1][2];
                    var j = 1;

                    // ASSUMES MONOTONICALLY INCREASING Z
                    while (newZ <= finalZ) {
                        newZ = ptsArr[0][2] + j * minZSpacing;
                        nearestIndex = 1;  // start at the beginning
                        lastNearestIndex = 1;
                        var checkZ = ptsArr[nearestIndex][2];
                        while (nearestIndex < ptsArr.length && checkZ < newZ) {
                            if (! newIndexMap[nearestIndex]) {
                                // ensures we don't skip any indices, mapping them to the nearest previously mapped value
                                newIndexMap[nearestIndex] = indexValPriorTo(newIndexMap, nearestIndex, 1) || 0;
                            }
                            ++nearestIndex;
                            checkZ = (ptsArr[nearestIndex] || [])[2];
                        }
                        if (nearestIndex != lastNearestIndex) {
                            lastNearestIndex = nearestIndex;
                        }

                        var lo = Math.max(0, nearestIndex - 1);
                        var hi = Math.min(ptsArr.length-1, nearestIndex);
                        var p = ptsArr[lo];
                        var nextP = ptsArr[hi];
                        var dzz = nextP[2] - p[2];
                        var newP = [0, 0, newZ];
                        for (var ci = 0; ci < 2; ++ci) {
                            newP[ci] = dzz ? p[ci] + (newP[2] - p[2]) * (nextP[ci] - p[ci]) / dzz : p[ci];
                        }
                        ptsArr.splice(lo + 1, 0, newP);

                        newIndexMap[hi] = j;
                        ++j;
                    }
                    newIndexMap[ptsArr.length-1] = indexValPriorTo(newIndexMap, nearestIndex, 1);
                    indexMaps.push(newIndexMap);
                }

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
                fieldColorScale = plotting.colorScaleForPlot({ min: hm_zmin, max: hm_zmax }, 'particle3d');

                setLinesFromPoints(absorbedLineBundle, lcoords, null, true);

                if (pointData.lost_x) {
                    $scope.hasReflected = pointData.lost_x.length > 0;
                    setLinesFromPoints(reflectedLineBundle, lostCoords, reflectedParticleTrackColor, false);
                }

                mapImpactDensity();

                function coordAtIndex(startVal, sk, sl, k, l) {
                    return startVal + k * sk + l * sl;
                }

                function scaleWithShave(a) {
                    var shave = 0.01;
                    return (1.0 - shave) * a / cFactor;
                }

                function scaleConductor(a) {
                    return a / cFactor;
                }

                function toMicron(v) {
                    return v * 1e-6;
                }

                addSTLConductors();

                // build box conductors -- make them a tiny bit small so the edges do not bleed into each other
                for (var cIndex = 0; cIndex < appState.models.conductors.length; ++cIndex) {
                    var conductor = appState.models.conductors[cIndex];

                    // lengths and centers are in µm
                    var cFactor = 1000000.0;
                    var cModel = null;
                    var cColor = [0, 0, 0];
                    var cEdgeColor = [0, 0, 0];
                    for (var ctIndex = 0; ctIndex < appState.models.conductorTypes.length; ++ctIndex) {
                        if (appState.models.conductorTypes[ctIndex].id == conductor.conductorTypeId) {
                            cModel = appState.models.conductorTypes[ctIndex];
                            var vColor = vtk.Common.Core.vtkMath.hex2float(cModel.color || SIREPO.APP_SCHEMA.constants.nonZeroVoltsColor);
                            var zColor = vtk.Common.Core.vtkMath.hex2float(cModel.color || SIREPO.APP_SCHEMA.constants.zeroVoltsColor);
                            cColor = cModel.voltage == 0 ? zColor : vColor;
                            break;
                        }
                    }
                    if (cModel && cModel.type !== 'stl') {
                        var bl = [cModel.xLength, cModel.yLength, cModel.zLength].map(scaleWithShave);
                        var bc = [conductor.xCenter, conductor.yCenter, conductor.zCenter].map(scaleConductor);

                        var bb = coordMapper.buildBox(bl, bc);
                        conductorBundles.push(bb);
                        bb.actor.getProperty().setColor(cColor[0], cColor[1], cColor[2]);
                        bb.actor.getProperty().setEdgeVisibility(true);
                        bb.actor.getProperty().setEdgeColor(cEdgeColor[0], cEdgeColor[1], cEdgeColor[2]);
                        bb.actor.getProperty().setLighting(false);
                        bb.actor.getProperty().setOpacity(0.80);
                        conductorActors.push(bb.actor);
                    }
                }

                // do an initial render
                renderWindow.render();

                // wait to initialize after the render so the world to viewport transforms are ready
                vpOutline.initializeWorld();

                refresh(true);

                // allow the sizing to take hold and initialize the camera position
                $timeout(resetCam, 0);
            };

            function mapImpactDensity() {
                // loop over conductors
                // arr[0][0] + k * sk + l * sl
                (impactData.density || []).forEach(function (c) {
                    if (! $scope.enableImpactDensity) {
                        return;
                    }
                    // loop over faces
                    c.forEach(function (f) {
                        if (! f.y) {
                            $scope.enableImpactDensity = false;
                            return;
                        }

                        if (f.type === 'unstructured') {
                            mapUnstructuredDensity(f);
                            return;
                        }

                        var o = [f.x.startVal, f.y.startVal, f.z.startVal].map(toNano);
                        var sk = [f.x.slopek, f.y.slopek, f.z.slopek].map(toNano);
                        var sl = [f.x.slopel, f.y.slopel, f.z.slopel].map(toNano);
                        var d = f.dArr;
                        var nk = d.length;
                        var nl = d[0].length;
                        var smin = plotting.min2d(d);
                        var smax = plotting.max2d(d);
                        var fcs = plotting.colorScaleForPlot({ min: smin, max: smax }, $scope.modelName,  'impactColorMap');

                        var p1 = [
                            o[0] + (nk - 1) * sk[0],
                            o[1] + (nk - 1) * sk[1],
                            o[2] + (nk - 1) * sk[2]
                        ];
                        var p2 = [
                            o[0] + (nl - 1) * sl[0],
                            o[1] + (nl - 1) * sl[1],
                            o[2] + (nl - 1) * sl[2]
                        ];
                        var p = coordMapper.buildPlane(o, p1, p2);
                        p.source.setXResolution(nl - 1);
                        p.source.setYResolution(nk - 1);
                        p.actor.getProperty().setLighting(false);

                        var dataColors = [];
                        for(var k = 0; k < nk - 1; ++k) {
                            for(var l = 0; l < nl - 1; ++l) {
                                var color = vtk.Common.Core.vtkMath.hex2float(fcs(d[k][l])).map(function (cc) {
                                    return Math.floor(255*cc);
                                });
                                dataColors.push(color[0], color[1], color[2]);
                           }
                        }
                        var carr = vtk.Common.Core.vtkDataArray.newInstance({
                            numberOfComponents: 3,
                            values: dataColors,
                            dataType: vtk.Common.Core.vtkDataArray.VtkDataTypes.UNSIGNED_CHAR
                        });
                        p.source.getOutputData().getCellData().setScalars(carr);

                        densityPlaneBundles.push(p);
                    });
                });

                function toNano(v) {
                    return v * 1e-9;
                }
            }

            function mapUnstructuredDensity(faceData) {
                var d = faceData.dArr;
                var nk = d.length;
                var x = faceData.x.map(toNano);
                var y = faceData.y.map(toNano);
                var z = faceData.z.map(toNano);
                var dx = Math.max.apply(null, x) - Math.min.apply(null, x);
                var dy = Math.max.apply(null, y) - Math.min.apply(null, y);
                var dz = Math.max.apply(null, z) - Math.min.apply(null, z);
                var size = [Math.abs(dx), Math.abs(dy), Math.abs(dz)];
                var ctr = [
                    Math.min.apply(null, x) + dx / 2.0,
                    Math.min.apply(null, y) + dy / 2.0,
                    Math.min.apply(null, z) + dz / 2.0
                ];

                var smin = Math.min.apply(null, d);
                var smax = Math.max.apply(null, d);

                var fcs = plotting.colorScaleForPlot({ min: smin, max: smax }, $scope.modelName,  'impactColorMap');
                var dataColors = [];
                var dataPoints = [];
                var dataVertices = [];
                for (var k = 0; k < nk - 1; ++k) {
                    var color = vtk.Common.Core.vtkMath.hex2float(fcs(d[k]))
                        .map(function (cc) {
                            return Math.floor(255*cc);
                        });
                    dataColors.push(color[0], color[1], color[2]);
                    dataVertices.push(1);
                    dataVertices.push(dataPoints.length / 3);
                    var vtkPts = coordMapper.xform.doTransform([x[k], y[k], z[k]]);
                    for (var cx = 0; cx < vtkPts.length; ++cx) {
                        dataPoints.push(vtkPts[cx]);
                    }
                }
                var p32 = window.Float32Array.from(dataPoints);
                var v32 = window.Uint32Array.from(dataVertices);
                var carr = vtk.Common.Core.vtkDataArray.newInstance({
                    numberOfComponents: 3,
                    values: dataColors,
                    dataType: vtk.Common.Core.vtkDataArray.VtkDataTypes.UNSIGNED_CHAR
                });
                var b = coordMapper.buildActorBundle();
                var pd = vtk.Common.DataModel.vtkPolyData.newInstance();
                pd.getPoints().setData(p32, 3);
                pd.getVerts().setData(v32);
                b.mapper.setScalarVisibility(true);
                pd.getCellData().setScalars(carr);
                b.mapper.setInputData(pd);
                densityBundles.push(b);

                function toNano(v) {
                    return v * 1e-9;
                }
            }

            function setLinesFromPoints(bundle, points, color, includeImpact) {
                if (! bundle) {
                    return;
                }

                var k = 0;
                var dataPoints = [];
                var dataLines = [];
                var dataColors = [];
                for (var i = 0; i < points.length; ++i) {
                    var l = points[i].length;
                    for (var j = 0; j < l; ++j) {
                        ++numPoints;
                        if (j < l - 1) {
                            k = j + 1;
                            pushLineData(points[i][j], points[i][k], color || colorAtIndex(indexMaps[i][j]));
                        }
                    }
                    if (l > j) {
                        k = j - 1;
                        ++numPoints;
                        pushLineData(points[i][k], points[i][l - 1], color || colorAtIndex(indexMaps[i][k]));
                    }
                    if (includeImpact) {
                        k = points[i].length - 1;
                        impactSphereActors.push(coordMapper.buildSphere(points[i][k], impactSphereSize, color || colorAtIndex(indexMaps[i][k])).actor);
                    }
                }
                var p32 = window.Float32Array.from(dataPoints);
                var l32 = window.Uint32Array.from(dataLines);
                var pd = vtk.Common.DataModel.vtkPolyData.newInstance();
                pd.getPoints().setData(p32, 3);
                pd.getLines().setData(l32);
                bundle.mapper.setInputData(pd);

                if (color) {
                    bundle.mapper.setScalarVisibility(false);
                    bundle.actor.getProperty().setColor(color[0], color[1], color[2]);
                }
                else {
                    bundle.mapper.setScalarVisibility(true);
                    var carr = vtk.Common.Core.vtkDataArray.newInstance({
                        numberOfComponents: 3,
                        values: dataColors,
                        dataType: vtk.Common.Core.vtkDataArray.VtkDataTypes.UNSIGNED_CHAR
                    });

                    // lines live in "cells"
                    pd.getCellData().setScalars(carr);
                }

                function pushLineData(p1, p2, c) {
                    // we always have two points per line
                    dataLines.push(2);
                    dataLines.push(dataPoints.length / 3, 1 + dataPoints.length / 3);
                    [p1, p2].forEach(function(p) {
                        coordMapper.xform.doTransform(p).forEach(function(a) {
                            dataPoints.push(a);
                        });
                    });

                    // scalar colors are unsigned chars, not floats like for every other part of vtk
                    c.forEach(function(comp) {
                        dataColors.push(Math.floor(255*comp));
                    });
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
                return plotting.colorsFromHexString(fieldColorScale(heatmap[fieldzIndex][fieldxIndex]), 255.0);
            }

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

            function refresh(doCacheCanvas) {

                var width = parseInt($($element).css('width')) - $scope.margin.left - $scope.margin.right;
                $scope.width = plotting.constrainFullscreenSize($scope, width, xzAspectRatio);
                $scope.height = xzAspectRatio * $scope.width;

                var vtkCanvasHolderSize = {
                    width: $('.vtk-canvas-holder').width(),
                    height: $('.vtk-canvas-holder').height()
                };

                screenRect = geometry.rect(
                    geometry.point(
                        $scope.axesMargins.x.width,
                        $scope.axesMargins.y.height
                    ),
                    geometry.point(
                        vtkCanvasHolderSize.width - $scope.axesMargins.x.width,
                        vtkCanvasHolderSize.height - $scope.axesMargins.y.height
                    )
                );

                var vtkCanvasSize = {
                    width: $scope.width + $scope.margin.left + $scope.margin.right,
                    height: $scope.height + $scope.margin.top + $scope.margin.bottom
                };

                select('.vtk-canvas-holder svg')
                    .attr('width', vtkCanvasSize.width)
                    .attr('height', vtkCanvasSize.height);

                // Note that vtk does not re-add actors to the renderer if they already exist
                vtkPlotting.addActor(renderer, absorbedLineBundle.actor);
                vtkPlotting.addActor(renderer, reflectedLineBundle.actor);
                vtkPlotting.addActors(renderer, conductorActors);
                vtkPlotting.addActors(renderer, impactSphereActors);
                vtkPlotting.addActors(renderer, densityPlaneBundles.map(function (b) {
                    return b.actor;
                }));
                vtkPlotting.addActors(renderer, densityBundles.map(function (b) {
                    return b.actor;
                }));

                vtkPlotting.showActor(renderWindow, startPlaneBundle.actor, ! $scope.showImpactDensity);
                vtkPlotting.showActor(renderWindow, endPlaneBundle.actor, ! $scope.showImpactDensity);
                vtkPlotting.showActor(renderWindow, absorbedLineBundle.actor, $scope.showAbsorbed);
                vtkPlotting.showActors(renderWindow, impactSphereActors, $scope.showAbsorbed && $scope.showImpact);
                vtkPlotting.showActor(renderWindow, reflectedLineBundle.actor, $scope.showReflected);
                vtkPlotting.showActors(renderWindow, conductorActors, $scope.showConductors, 0.80);
                vtkPlotting.showActors(renderWindow, densityPlaneBundles.map(function (b) {
                    return b.actor;
                }), $scope.showImpactDensity, 1.0);
                vtkPlotting.showActors(renderWindow, densityBundles.map(function (b) {
                    return b.actor;
                }), $scope.showImpactDensity, 1.0);

                // reset camera will negate zoom and pan but *not* rotation
                if (zoomUnits == 0 && ! didPan) {
                    renderer.resetCamera();
                }
                renderWindow.render();

                sceneRect =  vpOutline.boundingRect();

                // initial area of scene
                if (! sceneArea) {
                    sceneArea = sceneRect.area();
                }

                offscreen = ! (
                    sceneRect.intersectsRect(screenRect) ||
                    screenRect.containsRect(sceneRect) ||
                    sceneRect.containsRect(screenRect)
                );
                var a = sceneRect.area() / sceneArea;
                malSized = a < 0.1 || a > 7.5;
                $scope.canInteract = ! offscreen && ! malSized;
                if ($scope.canInteract) {
                    lastCamPos = cam.getPosition();
                    lastCamViewUp = cam.getViewUp();
                    lastCamFP = cam.getFocalPoint();
                }
                else {
                    setCam(lastCamPos, lastCamFP ,lastCamViewUp);
                }

                refreshAxes();

                // do this after the axes are set so the number of sections in the grids
                // match the new number of ticks
                refreshGridPlanes();

                if (SIREPO.APP_SCHEMA.feature_config.display_test_boxes) {
                    $scope.testBoxes = [

                        /*
                        {
                            x: xAxisLeft, //clippedXEnds[0][0],
                            y: xAxisTop, //clippedXEnds[0][1],
                            color: "red"
                        },
                        {
                            x: xAxisRight, //clippedXEnds[1][0],
                            y: xAxisBottom, //clippedXEnds[1][1],
                            color: "blue"
                        },
                        */
                        /*
                        {
                            x: yAxisLeft, //clippedYEnds[0][0],
                            y: yAxisTop, //clippedYEnds[0][1],
                            color: "red"
                        },
                        {
                            x: yAxisRight, //clippedYEnds[1][0],
                            y: yAxisBottom, //clippedYEnds[1][1],
                            color: "blue"
                        },
                        */
                        /*
                        {
                            x: clippedYEnds[0][0],
                            y: clippedYEnds[0][1],
                            color: "red"
                        },
                        {
                            x: clippedYEnds[1][0],
                            y: clippedYEnds[1][1],
                            color: "blue"
                        },
                        */
                        /*
                        {
                            x: screenYEnds.left[0],
                            y: screenYEnds.left[1],
                            color: "red"
                        },
                        {
                            x: screenYEnds.right[0],
                            y: screenYEnds.right[1],
                            color: "blue"
                        },
                        */
                        /*
                         {
                            x: clippedZEnds[0][0],
                            y: clippedZEnds[0][1],
                            color: "red"
                        },
                        {
                            x: clippedZEnds[1][0],
                            y: clippedZEnds[1][1],
                            color: "blue"
                        },
                        */
                        /*
                        {
                            x: zAxisLeft,
                            y: zAxisTop,
                            color: "red"
                        },
                        {
                            x: zAxisRight,
                            y: zAxisBottom,
                            color: "blue"
                        }
                        */
                    ];

                }

                if (doCacheCanvas) {
                    cacheCanvas();
                }
            }

            function refreshAxes() {

                // If an axis is shorter than this, don't display it -- the ticks will
                // be cramped and unreadable
                var minAxisDisplayLen = 50;

                //var b = ['z'];
                //for (var i in b) {  // use to test inidividual axes
                for (var i in geometry.basis) {

                    //var dim = b[i];
                    var dim = geometry.basis[i];

                    var screenDim = axisCfg[dim].screenDim;
                    var isHorizontal = screenDim === 'x';
                    var axisEnds = isHorizontal ? ['◄', '►'] : ['▼', '▲'];
                    var perpScreenDim = isHorizontal ? 'y' : 'x';

                    var showAxisEnds = false;
                    var axisSelector = '.' + dim + '.axis';
                    var axisLabelSelector = '.' + dim + '-axis-label';

                    // sort the external edges so we'll preferentially pick the left and bottom
                    var externalEdges = vpOutline.externalVpEdgesForDimension(dim)
                        .sort(edgeSorter(perpScreenDim, ! isHorizontal));
                    var seg = geometry.bestEdgeAndSectionInBounds(externalEdges, screenRect, dim, false);

                    if (! seg) {
                        // all possible axis ends offscreen, so try a centerline
                        var cl = vpOutline.vpCenterLineForDimension(dim);
                        seg = geometry.bestEdgeAndSectionInBounds([cl], screenRect, dim, false);
                        if (! seg) {
                            // don't draw axes
                            select(axisSelector).style('opacity', 0.0);
                            select(axisLabelSelector).style('opacity', 0.0);
                            continue;
                        }
                        showAxisEnds = true;
                    }
                    select(axisSelector).style('opacity', 1.0);

                    var fullSeg = seg.full;
                    var clippedSeg = seg.clipped;
                    var reverseOnScreen = shouldReverseOnScreen(dim, seg.index, screenDim);
                    var sortedPts = geometry.sortInDimension(clippedSeg.points(), screenDim, false);
                    var axisLeft = sortedPts[0].x;
                    var axisTop = sortedPts[0].y;
                    var axisRight = sortedPts[1].x;
                    var axisBottom = sortedPts[1].y;

                    var newRange = Math.min(fullSeg.length(), clippedSeg.length());
                    var radAngle = Math.atan(clippedSeg.slope());
                    if (! isHorizontal) {
                        radAngle -= Math.PI / 2;
                        if (radAngle < -Math.PI / 2) {
                            radAngle += Math.PI;
                        }
                    }
                    var angle = (180 * radAngle / Math.PI);

                    var allPts = geometry.sortInDimension(fullSeg.points().concat(clippedSeg.points()), screenDim, false);

                    var limits = reverseOnScreen ? [axisCfg[dim].max, axisCfg[dim].min] : [axisCfg[dim].min, axisCfg[dim].max];
                    var newDom = [axisCfg[dim].min, axisCfg[dim].max];
                    // 1st 2, last 2 points
                    for (var m = 0; m < allPts.length; m += 2) {
                        // a point may coincide with its successor
                        var d = allPts[m].dist(allPts[m+1]);
                        if (d != 0) {
                            var j = Math.floor(m / 2);
                            var k = reverseOnScreen ? 1 - j : j;
                            var l1 = limits[j];
                            var l2 = limits[1 - j];
                            var part = (l1 - l2) * d / fullSeg.length();
                            var newLimit = l1 - part;
                            newDom[k] = newLimit;
                        }
                    }
                    var xform = 'translate(' + axisLeft + ',' + axisTop + ') ' +
                        'rotate(' + angle + ')';

                    axes[dim].scale.domain(newDom).nice();
                    axes[dim].scale.range([reverseOnScreen ? newRange : 0, reverseOnScreen ? 0 : newRange]);

                    // this places the axis tick labels on the appropriate side of the axis
                    var outsideCorner = geometry.sortInDimension(vpOutline.vpCorners(), perpScreenDim, isHorizontal)[0];
                    var bottomOrLeft = outsideCorner.equals(sortedPts[0]) || outsideCorner.equals(sortedPts[1]);
                    if (isHorizontal) {
                        axes[dim].svgAxis.orient(bottomOrLeft ? 'bottom' : 'top');
                    }
                    else {
                        axes[dim].svgAxis.orient(bottomOrLeft ? 'left' : 'right');
                    }


                    if (showAxisEnds) {
                        axes[dim].svgAxis.ticks(0);
                        select(axisSelector).call(axes[dim].svgAxis);
                    }
                    else {
                        axes[dim].updateLabelAndTicks({
                            width: newRange,
                            height: newRange
                        }, select);
                    }

                    select(axisSelector).attr('transform', xform);

                    var dimLabel = axisCfg[dim].dimLabel;
                    d3self.selectAll(axisSelector + '-end')
                        .style('opacity', showAxisEnds ? 1 : 0);

                    var tf = axes[dim].svgAxis.tickFormat();
                    if (tf) {
                        select(axisSelector + '-end.low')
                            .text(axisEnds[0] + ' ' + dimLabel + ' ' + tf(reverseOnScreen ? newDom[1] : newDom[0]) + axes[dim].unitSymbol + axes[dim].units)
                            .attr('x', axisLeft)
                            .attr('y', axisTop)
                            .attr('transform', 'rotate(' + (angle) + ', ' + axisLeft + ', ' + axisTop + ')');

                        select(axisSelector + '-end.high')
                            .attr('text-anchor', 'end')
                            .text(tf(reverseOnScreen ? newDom[0] : newDom[1]) + axes[dim].unitSymbol + axes[dim].units + ' ' + dimLabel + ' ' + axisEnds[1])
                            .attr('x', axisRight)
                            .attr('y', axisBottom)
                            .attr('transform', 'rotate(' + (angle) + ', ' + axisRight + ', ' + axisBottom + ')');
                    }

                    // counter-rotate the tick labels
                    var labels = d3self.selectAll(axisSelector + ' text');
                    labels.attr('transform', 'rotate(' + (-angle) + ')');
                    select(axisSelector + ' .domain').style({'stroke': 'none'});
                    select(axisSelector).style('opacity', newRange < minAxisDisplayLen ? 0 : 1);

                    var labelSpace = 2 * plotting.tickFontSize(select(axisSelector + '-label'));
                    var labelSpaceX = (isHorizontal ? Math.sin(radAngle) : Math.cos(radAngle)) * labelSpace;
                    var labelSpaceY = (isHorizontal ? Math.cos(radAngle) : Math.sin(radAngle)) * labelSpace;
                    var labelX = axisLeft + (bottomOrLeft ? -1 : 1) * labelSpaceX + (axisRight - axisLeft) / 2.0;
                    var labelY = axisTop + (bottomOrLeft ? 1 : -1) * labelSpaceY + (axisBottom - axisTop) / 2.0;
                    var labelXform = 'rotate(' + (isHorizontal ? 0 : -90) + ' ' + labelX + ' ' + labelY + ')';

                    select('.' + dim + '-axis-label')
                        .attr('x', labelX)
                        .attr('y', labelY)
                        .attr('transform', labelXform)
                        .style('opacity', (showAxisEnds || newRange < minAxisDisplayLen) ? 0 : 1);
                }
            }

            function edgeSorter(dim, shouldReverse) {
                return function(e1, e2) {
                    if (! e1) {
                        if (! e2) {
                            return 0;
                        }
                        return 1;
                    }
                    if (! e2) {
                        return -1;
                    }
                    var pt1 = geometry.sortInDimension(e1.points(), dim, shouldReverse)[0];
                    var pt2 = geometry.sortInDimension(e2.points(), dim, shouldReverse)[0];
                    return (shouldReverse ? -1 : 1) * (pt2[dim] - pt1[dim]);
                };
            }

            function shouldReverseOnScreen(dim, index, screenDim) {
                var currentEdge = vpOutline.vpEdgesForDimension(dim)[index];
                var currDiff = currentEdge.points()[1][screenDim] - currentEdge.points()[0][screenDim];
                return currDiff < 0;
            }

            // Redraw the grid planes to match the number of tick marks
            // on the axes
            function refreshGridPlanes() {

                var numX = Math.max($($element).find('.x.axis .tick').length - 1, 1);
                var numY = Math.max($($element).find('.y.axis .tick').length - 1, 1);
                var numZ = Math.max($($element).find('.z.axis .tick').length - 1, 1);
                for (var d = 0; d < 3; ++d) {
                    for (var s = 0; s < 1; ++s) {
                        var ps = gridPlaneBundles[d][s].source;
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

            function resetAndDigest() {
                $scope.$apply(reset);
            }
            function reset() {
                camPos = [0, 0, 1];
                camViewUp = [0, 1, 0];
                $scope.side = 'y';
                $scope.xdir = 1;  $scope.ydir = 1;  $scope.zdir = 1;
                resetCam();
            }
            function resetCam() {
                setCam(camPos, [0,0,0], camViewUp);
                cam.zoom(1.3);
                renderer.resetCamera();
                zoomUnits = 0;
                didPan = false;
                orientationMarker.updateMarkerOrientation();
                refresh(true);
            }
            function setCam(pos, fp, vu) {
                cam.setPosition(pos[0], pos[1], pos[2]);
                cam.setFocalPoint(fp[0], fp[1], fp[2]);
                cam.setViewUp(vu[0], vu[1], vu[2]);
            }
            function cacheCanvas() {
                if (! snapshotCtx) {
                    return;
                }
                var w = parseInt(canvas3d.getAttribute('width'));
                var h = parseInt(canvas3d.getAttribute('height'));
                snapshotCanvas.width = w;
                snapshotCanvas.height = h;
                // this call makes sure the buffer is fresh (it appears)
                fsRenderer.getOpenGLRenderWindow().traverseAllPasses();
                snapshotCtx.drawImage(canvas3d, 0, 0, w, h);
            }

            function resetZoom() {
            }

            $scope.clearData = function() {
            };

            $scope.destroy = function() {
                document.removeEventListener(utilities.fullscreenListenerEvent(), refresh);
                var rw = angular.element($($element).find('.sr-plot-particle-3d .vtk-canvas-holder'))[0];
                rw.removeEventListener('dblclick', resetAndDigest);
                $($element).off();
                fsRenderer.getInteractor().unbindEvents();
                fsRenderer.delete();
                plotToPNG.removeCanvas($scope.reportId);
            };

            $scope.resize = function() {
                refresh(false);
            };

            $scope.toggleAbsorbed = function() {
                $scope.showAbsorbed = ! $scope.showAbsorbed;
                vtkPlotting.showActor(renderWindow, absorbedLineBundle.actor, $scope.showAbsorbed);
                vtkPlotting.showActors(renderWindow, impactSphereActors, $scope.showAbsorbed && $scope.showImpact);
            };
            $scope.toggleImpact = function() {
                $scope.showImpact = ! $scope.showImpact;
                vtkPlotting.showActors(renderWindow, impactSphereActors, $scope.showAbsorbed && $scope.showImpact);
            };
            $scope.toggleReflected = function() {
                $scope.showReflected = ! $scope.showReflected;
                vtkPlotting.showActor(renderWindow, reflectedLineBundle.actor, $scope.showReflected);
            };
            $scope.toggleConductors = function() {
                $scope.showConductors = ! $scope.showConductors;
                vtkPlotting.showActors(renderWindow, conductorActors, $scope.showConductors, 0.80);
                vtkPlotting.showActors(renderWindow, getSTLActors(), $scope.showConductors, 0.80);
            };
            $scope.toggleImpactDensity = function() {
                $scope.showImpactDensity = ! $scope.showImpactDensity;
                $scope.showConductors = ! $scope.showImpactDensity;
                vtkPlotting.showActors(renderWindow, getSTLActors(), $scope.showConductors, 0.80);
                refresh();
            };


            $scope.xdir = 1;  $scope.ydir = 1;  $scope.zdir = 1;
            $scope.side = 'y';
            $scope.showSide = function(side) {
                var dir = side === 'x' ? $scope.xdir : (side === 'y' ? $scope.ydir : $scope.zdir);
                if ( side == $scope.side ) {
                    dir *= -1;
                    if (side === 'x') {
                        $scope.xdir = dir;
                    }
                    if (side === 'y') {
                        $scope.ydir = dir;
                    }
                    if (side === 'z') {
                        $scope.zdir = dir;
                    }
                }
                $scope.side = side;

                camPos = side === 'x' ? [0, dir, 0] : (side === 'y' ? [0, 0, dir] : [dir, 0, 0] );
                camViewUp = side === 'x' ? [0, 0, 1] : [0, 1, 0];
                resetCam();
            };

            $scope.mode = 'move';
            $scope.selectMode = function(mode) {
                $scope.mode = mode;
                // turn off interactor?
            };

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }


        },

        link: function link(scope, element) {
            plotting.vtkPlot(scope, element);
        },
    };
});
