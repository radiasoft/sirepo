'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="NoDashInteger" data-ng-class="fieldClass">',
        // TODO(e-carlin): this is just copied from sirepo-components
          '<input data-string-to-number="integer" data-ng-model="model[field]" data-min="info[4]" data-max="info[5]" class="form-control" style="text-align: right" data-lpignore="true" required />',
        '</div>',
        '<div data-ng-switch-when="OptionalInteger" data-ng-class="fieldClass">',
          '<input data-string-to-number="integer" data-ng-model="model[field]" data-min="info[4]" data-max="info[5]" class="form-control" style="text-align: right" data-lpignore="true" />',
        '</div>',
        '<div data-ng-switch-when="OptionalFloat" data-ng-class="fieldClass">',
          '<input data-string-to-number="" data-ng-model="model[field]" data-min="info[4]" data-max="info[5]" class="form-control" style="text-align: right" data-lpignore="true" />',
        '</div>',
        '<div data-ng-switch-when="PlotFileArray" class="col-sm-7">',
          '<div data-plot-file-selection-list="" data-field="model[field]" data-model-name="modelName"></div>',
        '</div>',
        '<div data-ng-switch-when="Constant" class="col-sm-3">',
          '<div data-constant-field="" data-model-name="modelName" data-field="field"></div>',
        '</div>',
        '<div data-ng-switch-when="ArchiveFileArray" class="col-sm-12">',
          '<div data-archive-file-list="" data-model="model" data-field="field"></div>',
        '</div>',
    ].join('');
    SIREPO.FILE_UPLOAD_TYPE = {
        'problemFiles-archive': '.zip',
    };
    SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL = true;
    SIREPO.PLOTTING_YMIN_ZERO = false;
    SIREPO.SINGLE_FRAME_ANIMATION = [
        'gridEvolutionAnimation',
        'oneDimensionProfileAnimation'
    ];
});

SIREPO.app.factory('flashService', function(appState, panelState, requestSender, $rootScope) {
    var self = {};
    const ORIGINAL_SCHEMA = appState.clone(SIREPO.APP_SCHEMA);

    self.computeModel = analysisModel => {
        if (analysisModel == 'setupAnimation') {
            return analysisModel;
        }
        return 'animation';
    };

    //TODO(pjm): share with elegant
    self.dataFileURL = function(model, index) {
        if (! appState.isLoaded()) {
            return '';
        }
        return requestSender.formatUrl('downloadDataFile', {
            '<simulation_id>': appState.models.simulation.simulationId,
            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
            '<model>': model,
            '<frame>': index,
        });

    };

    self.hasArchiveFiles = () => {
        const s = appState.applicationState();
        return s.problemFiles.archiveFiles
            && s.problemFiles.archiveLibId == s.simulation.simulationId;
    };

    self.hasFlashSchema = () => {
        return appState.applicationState().flashSchema;
    };

    self.updateSchema = () => {
        const schema = appState.clone(ORIGINAL_SCHEMA);
        const flashSchema = appState.models.flashSchema;
        for (const section in flashSchema) {
            for (const name in flashSchema[section]) {
                schema[section][name] = flashSchema[section][name];
            }
        }
        SIREPO.APP_SCHEMA = schema;
    };

    appState.setAppService(self);

    appState.whenModelsLoaded($rootScope, self.updateSchema);

    $rootScope.$on('modelsUnloaded', () => {
        SIREPO.APP_SCHEMA = ORIGINAL_SCHEMA;
        self.zipFileStatusText = '';
    });

    return self;
});

SIREPO.app.controller('ParamsController', function() {
    var self = this;
});

SIREPO.app.controller('PhysicsController', function(appState) {
    var self = this;
    self.panels = [];
    [
        'physics_sourceTerms_EnergyDeposition_EnergyDepositionMain_Laser',
        'physics_RadTrans_RadTransMain_MGD',
        'physics_Hydro_HydroMain',
        'physics_Diffuse_DiffuseMain',
        'physics_materialProperties_Opacity_OpacityMain_Multispecies',
        'physics_Gravity_GravityMain',
        'physics_sourceTerms_Flame_FlameMain',
    ].forEach(m => {
        if (m in appState.models) {
            self.panels.push(m);
        }
    });
});

SIREPO.app.controller('SetupController', function(appState, flashService, persistentSimulation, $scope) {
    var self = this;
    self.errorMessage = '';
    self.flashService = flashService;
    self.simAnalysisModel = 'setupAnimation';
    self.simScope = $scope;

    function setParValues(modelName, parValues) {
        if (parValues) {
            const m = appState.models[modelName];
            for (const f in m) {
                if (f in parValues) {
                    m[f] = parValues[f];
                }
            }
        }
    }

    function updateSchema(flashSchema, parValues) {
        appState.models.flashSchema = flashSchema;
        flashService.updateSchema();
        let updateModels = ['flashSchema'];
        for (const name in flashSchema.model) {
            let saveName = false;
            if (! appState.models[name]) {
                appState.models[name] = appState.setModelDefaults({}, name);
                setParValues(name, parValues);
                saveName = true;
            }
            else {
                const m = appState.models[name];
                // add any new missing fields
                for (const f in flashSchema.model[name]) {
                    if (!(f in m)) {
                        if (parValues && f in parValues) {
                            m[f] = parValues[f];
                        }
                        else {
                            m[f] = flashSchema.model[name][f][SIREPO.INFO_INDEX_DEFAULT_VALUE];
                        }
                        saveName = true;
                    }
                }
            }
            if (saveName) {
                updateModels.push(name);
            }
        }
        appState.saveChanges(updateModels);
    }

    self.hasLogFiles = () => self.errorMessage || self.successMessage;

    self.logURL = (frameIdName) => {
        return flashService.dataFileURL(
            self.simState.model,
            SIREPO.APP_SCHEMA.constants[frameIdName]);
    };

    self.startSimulation = () => {
        self.successMessage = '';
        appState.removeModel('flashSchema');
        self.simState.saveAndRunSimulation('simulation');
    };

    self.simHandleStatus = data => {
        self.errorMessage = data.error;
        if (data.flashSchema) {
            if (! appState.models.flashSchema) {
                updateSchema(data.flashSchema, data.parValues);
            }
            self.successMessage = 'Setup and Compile completed successfully';
        }
    };

    self.simState = persistentSimulation.initSimulationState(self);

    self.simState.errorMessage = () => self.errorMessage;
});

SIREPO.app.controller('SourceController', function(appState) {
    var self = this;
    self.appState = appState;
});

SIREPO.app.controller('VisualizationController', function(appState, flashService, frameCache, persistentSimulation, $scope, $window) {
    var self = this;
    self.simScope = $scope;
    self.plotClass = 'col-md-6';

    self.startSimulation = function() {
        appState.models.oneDimensionProfileAnimation.selectedPlotFiles = [];
        self.simState.saveAndRunSimulation(
            ['animation', 'simulation', 'oneDimensionProfileAnimation']
        );
    };

    function setAxis() {
        if (! appState.models.Grid_GridMain) {
            return;
        }
        SIREPO.APP_SCHEMA.enum.Axis = {
            'cartesian': [
                ['x', 'x'],
                ['y', 'y'],
                ['z', 'z'],
            ],
            'cylindrical': [
                ['r', 'r'],
                ['z', 'z']
            ],
            'spherical': [
                ['r', 'r'],
                ['theta', 'theta']
            ],
            'polar': [
                ['r', 'r'],
                ['phi', 'phi']
            ]
        }[appState.models.Grid_GridMain.geometry];
        if (appState.models.setupArguments.d === 3) {
            let a = 'z';
            if (['cylindrical', 'spherical'].includes(appState.models.Grid_GridMain.geometry)) {
                a = 'phi';
            }
            SIREPO.APP_SCHEMA.enum.Axis.push([a, a]);
        }
        const d = SIREPO.APP_SCHEMA.enum.Axis[0][0];
        SIREPO.APP_SCHEMA.model.oneDimensionProfileAnimation.axis[2]= d;
        // Set the axis to be the default if it is currently set to an
        // axis that is invalid for the selected geometry
        ['oneDimensionProfileAnimation', 'varAnimation'].forEach(m => {
            if (! SIREPO.APP_SCHEMA.enum.Axis.map(a => a[0]).includes(
                appState.models[m].axis
            )) {
                appState.models[m].axis = d;
                appState.saveChanges(m);
            }
        });
    }

    function updateValueList(modelName, fields, values) {
        if (! values || ! values.length) {
            return;
        }
        const m = appState.models[modelName];
        if (! m.valueList) {
            m.valueList = {};
        }
        fields.forEach(f => {
            m.valueList[f] = values;
            if (f == 'y2' || f == 'y3') {
                m.valueList[f] = appState.clone(values);
                m.valueList[f].unshift('None');
            }
            if (! m[f]) {
                m[f] = values[0];
            }
        });
        appState.saveQuietly(modelName);
    }

    self.reportType = () => appState.applicationState().varAnimation.plotType;

    self.simHandleStatus = function(data) {
        self.errorMessage = data.error;
        if ('frameCount' in data && ! data.error) {
            [
                'gridEvolutionAnimation',
                'oneDimensionProfileAnimation',
                'varAnimation'
            ].forEach(function(m) {
                appState.saveQuietly(m);
                frameCache.setFrameCount(data.frameCount, m);
            });
        }
        updateValueList('gridEvolutionAnimation', ['y1', 'y2', 'y3'], data.gridEvolutionColumns);
        updateValueList('oneDimensionProfileAnimation', ['var'], data.plotVars);
        updateValueList('varAnimation', ['var'], data.plotVars);
        self.hasPlotVars = data.plotVars && data.plotVars.length > 0;
        if (data.plotFiles) {
            appState.models.oneDimensionProfileAnimation.plotFiles = data.plotFiles;
            appState.saveQuietly('oneDimensionProfileAnimation');
        }
        frameCache.setFrameCount(data.frameCount || 0);
    };

    self.simState = persistentSimulation.initSimulationState(self);

    self.simState.logFileURL = function() {
        return flashService.dataFileURL(
            self.simState.model,
            SIREPO.APP_SCHEMA.constants.flashLogFrameId);
    };

    appState.whenModelsLoaded($scope, function() {
        setAxis();
        $scope.$on('varAnimation.summaryData', function(e, data) {
            var newPlotClass = self.plotClass;
            if (data.aspectRatio > 2) {
                newPlotClass = 'col-md-5';
            }
            else if (data.aspectRatio < 1) {
                newPlotClass = 'col-md-12 col-xl-8';
            }
            else {
                newPlotClass = 'col-md-6';
            }
            if (newPlotClass != self.plotClass) {
                self.plotClass = newPlotClass;
                $($window).trigger('resize');
            }
        });
    });
});

//TODO(pjm): flashService import is important to be sure the service is loaded initially
SIREPO.app.directive('appFooter', function(flashService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
            <div data-import-dialog=""></div>
        `,
    };
});

SIREPO.app.directive('appHeader', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: `
            <div data-app-header-brand="nav"></div>
            <div data-app-header-left="nav"></div>
            <div data-app-header-right="nav">
              <app-header-right-sim-loaded>
                <div data-sim-sections="">
                  <li class="sim-section" data-ng-class="{active: nav.isActive('setup')}"><a href data-ng-click="nav.openSection('setup')"><span class="glyphicon glyphicon-tasks"></span> Setup</a></li>
                  <li data-ng-if="flashService.hasFlashSchema()" class="sim-section" data-ng-class="{active: nav.isActive('source')}"><a href data-ng-click="nav.openSection('source')"><span class="glyphicon glyphicon-th"></span> Source</a></li>
                  <li data-ng-if="flashService.hasFlashSchema()" class="sim-section" data-ng-class="{active: nav.isActive('physics')}"><a href data-ng-click="nav.openSection('physics')"><span class="glyphicon glyphicon-fire"></span> Physics</a></li>
                  <li data-ng-if="flashService.hasFlashSchema()" class="sim-section" data-ng-class="{active: nav.isActive('params')}"><a href data-ng-click="nav.openSection('params')"><span class="glyphicon glyphicon-edit"></span> Parameters</a></li>
                  <li data-ng-if="flashService.hasFlashSchema()" class="sim-section" data-ng-class="{active: nav.isActive('visualization')}"><a href data-ng-click="nav.openSection('visualization')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
              </app-settings>
              <app-header-right-sim-list>
                <ul class="nav navbar-nav sr-navbar-right">
                  <li><a href data-ng-click="nav.showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>
                </ul>
              </app-header-right-sim-list>
            </div>
        `,
        controller: function(flashService, $scope) {
            $scope.flashService = flashService;
        },
    };
});

SIREPO.app.directive('plotFileSelectionList', function() {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            modelName: '=',
        },
        template: `
            <div style="margin: 5px 0; min-height: 34px; max-height: 20em; overflow-y: auto; border: 1px solid #ccc; border-radius: 4px">
              <table class="table table-condensed table-hover" style="margin:0">
                <tbody>
                  <tr data-ng-repeat="file in plotFiles track by $index" data-ng-click="toggleFile(file.filename)">
                    <td>{{ file.time }}</td>
                    <td><input type="checkbox" data-ng-checked="isSelected(file.filename)"></td>
                  </tr>
                </tbody>
              </table>
            </div>
        `,
        controller: function($scope, appState) {
            function loadPlotFiles() {
                $scope.plotFiles = appState.models.oneDimensionProfileAnimation.plotFiles;
            }

            $scope.isSelected = function(file) {
                if ($scope.field) {
                    return $scope.field.indexOf(file) >= 0;
                }
                return false;
            };

            $scope.toggleFile = function(file) {
                if ($scope.field) {
                    if ($scope.isSelected(file)) {
                        $scope.field.splice($scope.field.indexOf(file), 1);
                    }
                    else {
                        $scope.field.push(file);
                    }
                }
            };

            appState.whenModelsLoaded($scope, loadPlotFiles);
            appState.watchModelFields(
                $scope,
                ['oneDimensionProfileAnimation.plotFiles'],
                loadPlotFiles
            );
        },
    };
});

SIREPO.app.directive('parametersPanel', function() {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div style="margin-bottom: 1ex" data-ng-repeat="name in modelNames track by name">
            <button class="btn btn-default" data-ng-click="showModal(name)">{{ name }}</button>
            </div>
        `,
        controller: function(appState, panelState, $scope) {
            $scope.showModal = name => panelState.showModalEditor(name);

            appState.whenModelsLoaded($scope, () => {
                $scope.modelNames = [];
                for (const name in appState.models.flashSchema.model) {
                    $scope.modelNames.push(name);
                }
            });
        },
    };
});

SIREPO.app.directive('constantField', function() {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            field: '=',
        },
        template: '<div class="form-control-static text-right">{{ ::schemaValue() }}</div>',
        controller: function($scope) {
            $scope.schemaValue = () => {
                return SIREPO.APP_SCHEMA.model[$scope.modelName][$scope.field][2];
            };
        },
    };
});

SIREPO.app.directive('setupArgumentsPanel', function() {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div>
              <div data-basic-editor-panel="" data-view-name="setupArguments">
                <div class="well" style="margin-top: 1ex">
                  <div data-ng-if="setupCommand">{{ setupCommand }}</div>
                  <div data-ng-if="! setupCommand"><span class="glyphicon glyphicon-hourglass"></span> Computing setup command ...</div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope, appState, requestSender) {
            function updateSetupCommand() {
                $scope.setupCommand = '';
                requestSender.sendStatelessCompute(
                    appState,
                    data => $scope.setupCommand = data.setupCommand,
                    {
                        method: 'setup_command',
                        setupArguments: appState.models.setupArguments,
                    });
            }

            $scope.$on('setupArguments.changed', () => {
                updateSetupCommand();
                if (appState.models.setupArguments.geometry == '-none-' || ! appState.models.Grid_GridMain) {
                    return;
                }
                if (appState.models.Grid_GridMain.geometry != appState.models.setupArguments.geometry) {
                    appState.models.Grid_GridMain.geometry = appState.models.setupArguments.geometry;
                    appState.saveChanges('Grid_GridMain');
                }
            });
            updateSetupCommand();
        },
    };
});

SIREPO.viewLogic('varAnimationView', function(appState, panelState, $scope) {

    function getNdim() {
        if (appState.models.Grid_GridMain_paramesh_paramesh4_Paramesh4dev) {
            return appState.models.Grid_GridMain_paramesh_paramesh4_Paramesh4dev.gr_pmrpNdim;
        }
        return 0;
    }

    function updateHeatmapFields() {
        let isHeatmap = appState.models.varAnimation.plotType == 'heatmap';
        panelState.showFields('varAnimation', [
            'vmax', isHeatmap,
            'vmin', isHeatmap,
            'amrGrid', isHeatmap,
        ]);
    }

    $scope.whenSelected = () => {
        panelState.showField(
            'varAnimation',
            'axis',
            getNdim() > 2);
        updateHeatmapFields();
    };

    $scope.watchFields = [
        ['varAnimation.plotType'], updateHeatmapFields,
    ];
});

SIREPO.viewLogic('problemFilesView', function(appState, flashService, panelState, requestSender, $scope) {
    let isProcessing = false;

    function initZipfile() {
        panelState.clear('initZipReport');
        flashService.zipFileStatusText = 'Extracting Simulation Files';
        isProcessing = true;
        showArchiveFields();
        panelState.requestData(
            'initZipReport',
            data => {
                if (data.files) {
                    appState.models.problemFiles.archiveFiles = data.files;
                    appState.models.problemFiles.filesHash = data.filesHash;
                    showArchiveFields();
                }
                else {
                    flashService.zipFileStatusText = '';
                    isProcessing = false;
                }
            },
            false,
            err => {
                flashService.zipFileStatusText = 'Error processing zip archive: ' + err.error;
                isProcessing = false;
            });
    }

    function updateLibFile() {
        return requestSender.sendStatefulCompute(
            appState,
            (data) => {
                if (data.archiveLibId) {
                    appState.models.problemFiles.archiveLibId = data.archiveLibId;
                    appState.saveChanges('problemFiles');
                    flashService.zipFileStatusText = '';
                    isProcessing = false;
                    showArchiveFields();
                }
                else {
                    flashService.zipFileStatusText = data.error;
                    isProcessing = false;
                }
            },
            {
                method: 'update_lib_file',
                simulationId: appState.models.simulation.simulationId,
                archiveLibId: appState.models.problemFiles.archiveLibId,
            }
        );
    }

    function showArchiveFields() {
        if (appState.models.problemFiles.flashExampleName) {
            appState.models.problemFiles.flashExampleName = '';
            initZipfile();
        }
        else if (appState.models.problemFiles.archiveFiles
                 && ! flashService.hasArchiveFiles()) {
            updateLibFile();
        }
        panelState.showFields('problemFiles', [
            'archive', ! (isProcessing || (flashService.hasArchiveFiles() && ! flashService.zipFileStatusText)),
            'archiveFiles', flashService.hasArchiveFiles(),
        ]);
    }

    $scope.whenSelected = showArchiveFields;

    $scope.$on('initZipReport.changed', () => {
        if (appState.applicationState().problemFiles.archive
            && ! appState.applicationState().problemFiles.archiveFiles) {
            initZipfile();
        }
    });
});

SIREPO.app.directive('zipFileStatus', () => {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div class="text-center" data-ng-if="flashService.zipFileStatusText">
            <span class="glyphicon glyphicon-hourglass"></span> {{ flashService.zipFileStatusText }} ...
            </div>
        `,
        controller: function($scope, flashService) {
            $scope.flashService = flashService;
        },
    };
});

SIREPO.app.directive('archiveFileList', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <table style="margin-top: -1em" class="table table-hover table-condensed">
              <tr>
                <th>File name</th>
                <th width="5%"></th>
                <th width="5%"></th>
                <th width="5%"></th>
              </tr>
              <tr data-ng-repeat="row in model[field] track by row.name">
                <td style="padding-left: 1em">
                  <div data-ng-show="! canView(row.name)">{{ row.name }}</div>
                  <div data-ng-show="canView(row.name)">
                    <a href>{{ row.name }}</a>
                  </div>
                </td>
                <td>
                  <div class="text-center" data-ng-show="canView(row.name)">
                    <a href>view</a>
                  </div>
                </td>
                <td><div class="text-center"><a href><span class="glyphicon glyphicon-cloud-download"></span></a></div></td>
                <td><div class="text-center" data-ng-show="canDelete(row.name)">
                  <a href><span class="glyphicon glyphicon-remove"></span></a>
                </div></td>
              </tr>
            </table>
            <div class="row">
              <div class="col-sm-3 text-right">
                <label>Add/Replace File</label>
              </div>
              <div class="col-sm-9">
                <input id="sr-archive-file-import" type="file" data-file-model="inputFile" />
              </div>
            </div>
        `,
        controller: function(appState, panelState, $scope) {
            $scope.canView = name => {
                return name == 'Config'
                    || name == 'flash.par'
                    || name == 'Makefile'
                    || name == 'README'
                    || name.search(/\.(F90|txt)$/) >= 0;
            };
            $scope.canDelete = name => {
                return name != 'Config'
                    && name != 'flash.par'
                    && name != 'Makefile';
            };
        },
    };
});
