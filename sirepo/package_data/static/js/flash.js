'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="NoDashInteger" data-ng-class="fieldClass">
          <input data-string-to-number="integer" data-ng-model="model[field]"
            data-min="info[4]" data-max="info[5]" class="form-control"
            style="text-align: right" data-lpignore="true" required />
        </div>
        <div data-ng-switch-when="OptionalInteger" data-ng-class="fieldClass">
          <input data-string-to-number="integer" data-ng-model="model[field]"
            data-min="info[4]" data-max="info[5]" class="form-control"
            style="text-align: right" data-lpignore="true" />
        </div>
        <div data-ng-switch-when="PlotFileArray" class="col-sm-7">
          <div data-plot-file-selection-list="" data-field="model[field]"
            data-model-name="modelName"></div>
        </div>
        <div data-ng-switch-when="Constant" class="col-sm-3">
          <div data-constant-field="" data-model-name="modelName"
            data-field="field"></div>
        </div>
        <div data-ng-switch-when="ArchiveFileArray" class="col-sm-12">
          <div data-archive-file-list="" data-model="model" data-field="field"></div>
        </div>
    `;
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
        return requestSender.formatUrl('downloadRunFile', {
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

    self.isConfig = filename => filename == 'Config';

    self.isFlashPar = filename => filename == 'flash.par';

    // could be foo.f90 or foo.f90.special-case
    self.isFortran = filename => filename.search(/\.F90/i) >= 0;

    self.resetFlashSchema = (callback) => {
        appState.removeModel('flashSchema');
        appState.saveChanges('simulation', callback);
    };

    self.setParValues = (modelName, parValues) => {
        const m = appState.models[modelName];
        let hasChanged = false;
        for (const f in m) {
            if (f in parValues) {
                if (m[f] != parValues[f]) {
                    m[f] = parValues[f];
                    hasChanged = true;
                }
            }
        }
        return hasChanged;
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

    function updateSchema(flashSchema, parValues) {
        appState.models.flashSchema = flashSchema;
        flashService.updateSchema();
        let updateModels = ['flashSchema'];
        for (const name in flashSchema.model) {
            let saveName = false;
            if (! appState.models[name]) {
                appState.models[name] = appState.setModelDefaults({}, name);
                if (parValues) {
                    flashService.setParValues(name, parValues);
                }
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
                            m[f] = flashSchema.model[name][f][
                                SIREPO.INFO_INDEX_DEFAULT_VALUE];
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
        flashService.resetFlashSchema(self.simState.runSimulation);
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
            if (['cylindrical', 'spherical'].includes(
                appState.models.Grid_GridMain.geometry)) {
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
        updateValueList(
            'gridEvolutionAnimation', ['y1', 'y2', 'y3'], data.gridEvolutionColumns);
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

    self.simState.errorMessage = () => self.errorMessage;

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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('setup')}">
                    <a href data-ng-click="nav.openSection('setup')">
                      <span class="glyphicon glyphicon-tasks"></span> Setup</a>
                  </li>
                  <li data-ng-if="flashService.hasFlashSchema()" class="sim-section"
                    data-ng-class="{active: nav.isActive('source')}">
                    <a href data-ng-click="nav.openSection('source')">
                      <span class="glyphicon glyphicon-th"></span> Source</a>
                  </li>
                  <li data-ng-if="flashService.hasFlashSchema()" class="sim-section"
                    data-ng-class="{active: nav.isActive('physics')}">
                    <a href data-ng-click="nav.openSection('physics')">
                      <span class="glyphicon glyphicon-fire"></span> Physics</a>
                  </li>
                  <li data-ng-if="flashService.hasFlashSchema()" class="sim-section"
                    data-ng-class="{active: nav.isActive('params')}">
                    <a href data-ng-click="nav.openSection('params')">
                      <span class="glyphicon glyphicon-edit"></span> Parameters</a>
                  </li>
                  <li data-ng-if="flashService.hasFlashSchema()" class="sim-section"
                    data-ng-class="{active: nav.isActive('visualization')}">
                    <a href data-ng-click="nav.openSection('visualization')">
                      <span class="glyphicon glyphicon-picture"></span> Visualization</a>
                  </li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
              </app-settings>
              <app-header-right-sim-list>
                <ul class="nav navbar-nav sr-navbar-right">
                  <li><a href data-ng-click="nav.showImportModal()">
                    <span class="glyphicon glyphicon-cloud-upload"></span> Import</a>
                  </li>
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
            <div style="margin: 5px 0; min-height: 34px; max-height: 20em;
              overflow-y: auto; border: 1px solid #ccc; border-radius: 4px">
              <table class="table table-condensed table-hover" style="margin:0">
                <tbody>
                  <tr data-ng-repeat="file in plotFiles track by $index"
                    data-ng-click="toggleFile(file.filename)">
                    <td>{{ file.time }}</td>
                    <td><input type="checkbox"
                      data-ng-checked="isSelected(file.filename)"></td>
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

SIREPO.app.directive('constantField', function() {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            field: '=',
        },
        template: `
            <div class="form-control-static text-right">{{ ::schemaValue() }}</div>
        `,
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
                  <div data-ng-if="! setupCommand">
                    <span class="glyphicon glyphicon-hourglass"></span>
                    Computing setup command ...
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope, appState, flashService, requestSender) {
            function updateSetupCommand() {
                $scope.setupCommand = '';
                requestSender.sendStatelessCompute(
                    appState,
                    data => $scope.setupCommand = data.setupCommand,
                    {
                        method: 'setup_command',
                        args: {
                            setupArguments: appState.models.setupArguments,
                        }
                    });
            }

            $scope.$on('setupArguments.changed', () => {
                updateSetupCommand();
                flashService.resetFlashSchema();
                if (appState.models.setupArguments.geometry == '-none-'
                    || ! appState.models.Grid_GridMain) {
                    return;
                }
                if (appState.models.Grid_GridMain.geometry
                    != appState.models.setupArguments.geometry) {
                    appState.models.Grid_GridMain.geometry =
                        appState.models.setupArguments.geometry;
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
        setProcessing(true);
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
                    setProcessing(false);
                }
            },
            err => {
                setProcessing(false, err.error);
                appState.models.problemFiles.archive = null;
                appState.saveChanges('problemFiles');
                showArchiveFields();
            });
    }

    function setProcessing(value, error) {
        isProcessing = value;
        if (error) {
            flashService.zipFileStatusText = 'Error: ' + error;
        }
        else {
            flashService.zipFileStatusText = value
                ? 'Extracting Simulation Files'
                : '';
        }
    }

    function updateLibFile() {
        setProcessing(true);
        return requestSender.sendStatefulCompute(
            appState,
            (data) => {
                if (data.archiveLibId) {
                    appState.models.problemFiles.archiveLibId = data.archiveLibId;
                    flashService.resetFlashSchema();
                    appState.saveChanges('problemFiles');
                    setProcessing(false);
                    showArchiveFields();
                }
                else {
                    setProcessing(false, data.error);
                }
            },
            {
                method: 'update_lib_file',
                args: {
                    simulationId: appState.models.simulation.simulationId,
                    archiveLibId: appState.models.problemFiles.archiveLibId,
                }
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
            'archive', ! isProcessing && ! flashService.hasArchiveFiles(),
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
              <span data-ng-if="! hasError()" class="glyphicon glyphicon-hourglass">
              </span>
              {{ flashService.zipFileStatusText }}
              <span data-ng-if="! hasError()">...</span>
            </div>
        `,
        controller: function($scope, flashService) {
            $scope.flashService = flashService;
            $scope.hasError = () => flashService.zipFileStatusText.search(/^Error/i) >= 0;
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
                    <a href data-ng-click="viewFile(row.name)">{{ row.name }}</a>
                  </div>
                </td>
                <td>
                  <div class="text-center" data-ng-show="canView(row.name)">
                    <a href data-ng-click="viewFile(row.name)">view</a>
                  </div>
                </td>
                <td>
                  <div class="text-center">
                    <a href data-ng-click="downloadFile(row.name)">
                      <span class="glyphicon glyphicon-cloud-download"></span></a>
                  </div>
                </td>
                <td>
                  <div class="text-center" data-ng-show="canDelete(row.name)">
                    <a href data-ng-click="deleteFileConfirm(row.name)">
                      <span class="glyphicon glyphicon-remove"></span></a>
                  </div>
                </td>
              </tr>
            </table>

            <div class="row">
              <div class="col-sm-3 text-right">
                <label>Add/Replace File</label>
              </div>
              <div class="col-sm-9">
                <input id="sr-archive-file-upload" type="file"
                  data-file-model="inputFile" />
              </div>
            </div>

            <div class="modal fade" id="sr-flash-text-view" tabindex="-1" role="dialog">
              <div class="modal-dialog modal-lg">
                <div class="modal-content">
                  <div class="modal-header bg-warning">
                    <button type="button" class="close" data-dismiss="modal">
                      <span>&times;</span>
                    </button>
                    <span class="lead modal-title text-info">{{ selectedFileName }}</span>
                  </div>
                  <div class="modal-body" style="padding: 0">
                    <iframe id="sr-flash-text-iframe"
                      style="border: 0; width: 100%; height: 80vh" src=""></iframe>
                  </div>
                </div>
              </div>
            </div>

            <div data-confirmation-modal="" data-id="sr-flash-delete-file-dialog"
              data-title="Delete File" data-ok-text="Delete"
              data-ok-clicked="deleteFile()">Remove the "{{ selectedFileName }}" file?
            </div>

            <div data-confirmation-modal="" data-id="sr-flash-replace-file-dialog"
              data-title="Replace File" data-ok-text="Replace"
              data-ok-clicked="uploadFile()">Replace the "{{ selectedFileName }}" file?
            </div>

            <div data-confirmation-modal="" data-id="sr-flash-par-file-dialog"
              data-title="Replace flash.par" data-ok-text="Update"
              data-ok-clicked="uploadFile()">Update simulation settings from the
                "{{ selectedFileName }}" file?
            </div>

        `,
        controller: function(appState, fileUpload, flashService, panelState, requestSender, $element, $scope) {
            $scope.selectedFileName = '';

            function replaceFile() {
                statefulCompute('replace_file_in_zip', data => {
                    if (data.archiveFiles) {
                        appState.models.problemFiles.archiveFiles =
                            data.archiveFiles;
                        appState.saveChanges('problemFiles');
                    }
                    if (flashService.isConfig($scope.selectedFileName)
                        || flashService.isFortran($scope.selectedFileName)) {
                        flashService.resetFlashSchema();
                    }
                    else if (flashService.isFlashPar($scope.selectedFileName)) {
                        if (data.parValues) {
                            const names = [];
                            for (const name in appState.models.flashSchema.model) {
                                if (flashService.setParValues(name, data.parValues)) {
                                    names.push(name);
                                }
                            }
                            if (names.length) {
                                appState.saveChanges(names);
                            }
                        }
                    }
                    resetFile();
                });
            }

            function resetFile() {
                $scope.selectedFileName = '';
                $scope.inputFile = null;
                $($element).find("input[type='file']").val(null);
            }

            function setIFrameHTML(html) {
                $('#sr-flash-text-iframe').contents().find('html').html(html);
            }

            function statefulCompute(method, callback) {
                requestSender.sendStatefulCompute(
                    appState,
                    data => callback(data),
                    {
                        method: method,
                        args: {
                            simulationId: appState.models.simulation.simulationId,
                            filename: $scope.selectedFileName,
                            models: flashService.isFlashPar($scope.selectedFileName)
                                ? appState.applicationState()
                                : {},
                            archiveFiles: appState.models.problemFiles.archiveFiles,
                        }
                    });
            }

            $scope.canView = name => {
                return flashService.isConfig(name)
                    || flashService.isFlashPar(name)
                    || flashService.isFortran(name)
                    || name == 'Makefile'
                    || name == 'README'
                    || name.search(/\.txt$/) >= 0;
            };
            $scope.canDelete = name => {
                return ! flashService.isConfig(name)
                    && ! flashService.isFlashPar(name)
                    && name != 'Makefile';
            };
            $scope.deleteFile = () => {
                statefulCompute('delete_archive_file', data => {
                    if (data.error) {
                        return;
                    }
                    const f = appState.models.problemFiles.archiveFiles;
                    f.splice(
                        f.findIndex(e => e.name == $scope.selectedFileName),
                        1);
                    appState.saveChanges('problemFiles');
                });
            };
            $scope.deleteFileConfirm = name => {
                $scope.selectedFileName = name;
                $('#sr-flash-delete-file-dialog').modal('show');
            };
            $scope.downloadFile = name => {
                $scope.selectedFileName = name;
                statefulCompute('get_archive_file', data => {
                    if (! data.error) {
                        fetch(
                            `data:application/octet-stream;base64,${data.encoded}`
                        ).then(res => {
                            res.blob().then(b => {
                                saveAs(b, name);
                            });
                        });
                    }
                });
            };
            $scope.uploadFile = () => {
                fileUpload.uploadFileToUrl(
                    $scope.inputFile,
                    null,
                    requestSender.formatUrl(
                        'uploadLibFile',
                        {
                            '<simulation_id>': appState.models.simulation.simulationId,
                            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                            '<file_type>': 'problemFile',
                        }),
                    function(data) {
                        if (data.error) {
                            resetFile();
                        }
                        else {
                            replaceFile();
                        }
                    });
            };
            $scope.viewFile = name => {
                $scope.selectedFileName = name;
                setIFrameHTML(
                    '<div style="text-align: center; padding: 1em">Loading '
                        + name + '</div>');
                $('#sr-flash-text-view').modal('show');
                statefulCompute('format_text_file', data => setIFrameHTML(data.html));
            };
            $scope.$watch('inputFile', () => {
                if ($scope.inputFile) {
                    const n = $scope.inputFile.name;
                    $scope.selectedFileName = n;

                    if (flashService.isFlashPar(n)) {
                        $('#sr-flash-par-file-dialog').modal('show');
                        return;
                    }
                    if (appState.models.problemFiles.archiveFiles.some(
                        r => r.name == n)) {
                        $('#sr-flash-replace-file-dialog').modal('show');
                        return;
                    }
                    $scope.uploadFile();
                }
            });

            resetFile();
        },
    };
});

SIREPO.app.directive('moduleLink', function() {
    return {
        restrict: 'A',
        scope: {
            row: '=moduleLink',
        },
        template: `
            <div data-ng-attr-style="font-size: {{ fontSize(row) }}%" data-ng-if="! row.modelName">{{ row.name }}</div>
            <div data-ng-attr-style="font-size: {{ fontSize(row) }}%" data-ng-if="row.modelName">
              <a href data-ng-click="showModal(row)">{{ row.name }}
                <span class="badge">{{ row.fieldCount }}</span>
              </a>
            </div>
        `,
        controller: function(appState, panelState, $scope) {
            $scope.fontSize = (row) => {
                if (row.level == 0) {
                    return '130';
                }
                if (row.level == 1) {
                    return '115';
                }
                return '100';
            };
            $scope.showModal = row => panelState.showModalEditor(row.modelName);
        },
    };
});

SIREPO.app.directive('parametersPanel', function() {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <form class="form-inline">
              <div style="margin-bottom: 1ex" class="col-md-12 text-center">
                <label style="padding-right: 1em">Search:</label>
                <input type="text" class="form-control" data-ng-model="searchText" />
              </div>
            </form>

            <div class="col-sm-12 col-md-6 col-lg-4"
              data-ng-repeat="col in columns track by $index">
              <div data-ng-repeat="row in col track by row.name">
                <div data-ng-attr-style="margin-left: {{ 2 * row.level }}em"
                  data-module-link="row"></div>
              </div>
            </div>
        `,
        controller: function(appState, panelState, $scope) {
            let filter = '';
            $scope.searchText = '';

            function buildTreeColumn(search) {
                filter = search.toLowerCase();
                const rows = [];
                const tree = {};
                for (const name in appState.models.flashSchema.model) {
                    let title = appState.viewInfo(name).title;
                    if (title.search('/') < 0) {
                        title = name;
                        title = title.replaceAll('_', '/');
                    }
                    const parts = [];
                    for (const p of title.split('/')) {
                        if (parts.length < 3) {
                            parts.push(p);
                            continue;
                        }
                        parts[2] += '/' + p;
                    }
                    for (let i = 0; i < parts.length; i++) {
                        const p = parts[i];
                        if (tree[p]) {
                            continue;
                        }
                        tree[p] = {
                            name: p,
                            level: i,
                            fieldCount: fieldCount(name),
                        };
                        if (p == parts[parts.length - 1]) {
                            tree[p].modelName = name;
                        }
                        rows.push(tree[p]);
                    }
                }
                $scope.columns = splitRows(filterRows(rows, filter));
            }

            function fieldCount(modelName) {
                const s = Object.keys(appState.models.flashSchema.model[modelName]);
                if (! filter) {
                    return s.length;
                }
                let count = 0;
                for (const f of s) {
                    if (matchesFilter(f)) {
                        count ++;
                    }
                }
                return count;
            }

            function filterRows(rows, filter) {
                if (! filter) {
                    return rows;
                }
                const added = {};
                const levels = [null, null, null];
                const res = [];
                for (const r of rows) {
                    levels[r.level] = r;
                    if (matchesFilter(r.name) || r.fieldCount) {
                        for (let i = 0; i < r.level + 1; i++) {
                            if (added[levels[i].name]) {
                                continue;
                            }
                            added[levels[i].name] = true;
                            res.push(levels[i]);
                        }
                    }
                }
                return res;
            }

            function matchesFilter(value) {
                return value.toLowerCase().indexOf(filter) >= 0;
            }

            function splitRows(rows) {
                const res = [rows, [], []];
                for (let i = 0; i < rows.length; i++) {
                    if (rows[i].name == 'physics') {
                        res[2] = rows.splice(i, rows.length - i);
                        break;
                    }
                }
                let mid = parseInt(rows.length / 2);
                while (mid > 0 && rows[mid].level != 0) {
                    mid--;
                }
                if (mid > 0) {
                    res[1] = rows.splice(mid, rows.length - mid);
                }
                return res;
            }

            buildTreeColumn('');

            $scope.$watch('searchText', () => {
                if ($scope.searchText && $scope.searchText.length >= 3) {
                    if (filter != $scope.searchText) {
                        buildTreeColumn($scope.searchText);
                    }
                }
                else {
                    if (filter != '') {
                        buildTreeColumn('');
                    }
                }
            });
        },
    };
});
