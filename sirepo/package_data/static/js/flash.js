'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appDefaultSimulationValues.simulation.flashType = 'RTFlame';
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="NoDashInteger" data-ng-class="fieldClass">',
        // TODO(e-carlin): this is just copied from sirepo-components
          '<input data-string-to-number="integer" data-ng-model="model[field]" data-min="info[4]" data-max="info[5]" class="form-control" style="text-align: right" data-lpignore="true" required />',
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

SIREPO.app.factory('flashService', function(appState, panelState, $rootScope) {
    var self = {};
    const ORIGINAL_SCHEMA = appState.clone(SIREPO.APP_SCHEMA);

    self.computeModel = (analysisModel) => {
        if (analysisModel == 'setupAnimation') {
            return analysisModel;
        }
        return 'animation';
    };

    self.getNdim = function() {
        if (appState.models.Grid_paramesh_paramesh4_Paramesh4dev) {
            return appState.models.Grid_paramesh_paramesh4_Paramesh4dev.gr_pmrpNdim;
        }
        return 0;
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

    $rootScope.$on('modelsUnloaded', () => SIREPO.APP_SCHEMA = ORIGINAL_SCHEMA);

    return self;
});

SIREPO.app.controller('ConfigController', function(appState, flashService) {
    var self = this;
    self.appState = appState;
    self.flashService = flashService;
});

SIREPO.app.controller('ParamsController', function(appState) {
    var self = this;
    self.appState = appState;
});

SIREPO.app.controller('PhysicsController', function(flashService) {
    var self = this;
    self.flashService = flashService;
    self.panels = ['physics_Hydro', 'physics_sourceTerms_Flame', 'physics_Gravity'];
});

SIREPO.app.controller('RuntimeParamsController', function() {
    var self = this;
});

SIREPO.app.controller('SetupController', function(appState, flashService, persistentSimulation, $scope) {
    var self = this;
    self.appState = appState;
    self.errorMessage = '';
    self.simScope = $scope;
    self.simAnalysisModel = 'setupAnimation';

    function updateSchema(data) {
        appState.models.flashSchema = data.flashSchema;
        flashService.updateSchema();
        let updateModels = ['flashSchema'];
        for (const name in data.flashSchema.model) {
            //TODO(pjm): need to check for new fields as well
            if (! appState.models[name]) {
                appState.models[name] = appState.setModelDefaults({}, name);
                updateModels.push(name);
            }
        }
        appState.saveChanges(updateModels);
    }

    self.startSimulation = () => {
        self.successMessage = '';
        self.simState.runSimulation();
    };


    self.simHandleStatus = function(data) {
        self.errorMessage = data.error;
        if (data.flashSchema) {
            updateSchema(data.flashSchema);
            self.successMessage = 'Setup and Compile completed successfully';
        }
    };

    self.simState = persistentSimulation.initSimulationState(self);

    self.simState.errorMessage = function() {
        return self.errorMessage;
    };
});

SIREPO.app.controller('SourceController', function(appState, flashService, panelState, $scope) {
    var self = this;
    self.flashService = flashService;

    // function setReadOnly(modelName) {
    //     [
    //         'sim_tionWall', 'sim_tionFill', 'sim_tradWall', 'sim_tradFill',
    //     ].forEach(function(f) {
    //         panelState.enableField(modelName, f, false);
    //     });
    //     // TODO(e-carlin): If we support more than alumina for wall species
    //     // then we should remove this readonly or keep it and update the Z and A
    //     // when the species changes.
    //     ['ms_wallA', 'ms_wallZ'].forEach(function(f) {
    //         panelState.enableField('Multispecies', f, false);
    //     });
    // }

    // function makeTempsEqual(modelField) {
    //     var t = modelField.indexOf('Fill') >= 0 ? 'Fill' : 'Wall';
    //     var s = appState.parseModelField(modelField);
    //     ['ion', 'rad'].forEach(function(f) {
    //         appState.models[flashService.simulationModel()]['sim_t' + f + t] = appState.models[s[0]][s[1]];
    //     });
    // }

    // function processCurrType() {
    //     var modelName = flashService.simulationModel();

    //     function showField(field, isShown) {
    //         panelState.showField(modelName, field, isShown);
    //     }

    //     var isFile = appState.models[modelName].sim_currType === '2';
    //     showField('sim_currFile', isFile);
    //     ['sim_peakCurr', 'sim_riseTime'].forEach(function(f) {
    //         showField(f, !isFile);
    //     });
    // }

    appState.whenModelsLoaded($scope, function() {
        // if (! flashService.isCapLaser()) {
        //     return;
        // }
        // $scope.$on('sr-tabSelected', function(event, modelName) {
        //     if (['SimulationCapLaser3D', 'SimulationCapLaserBELLA'].indexOf(modelName) >= 0) {
        //         // Must be done on sr-tabSelected because changing tabs clears the
        //         // readonly prop. This puts readonly back on.
        //         setReadOnly(modelName);
        //     }
        //     else if (modelName == 'Grid') {
        //         // TODO(e-carlin): need to also constrain setupArguments geometry options
        //         ['polar', 'spherical'].forEach(function(f) {
        //             panelState.showEnum(
        //                 'Grid',
        //                 'geometry',
        //                 f,
        //                 ! flashService.isCapLaser()
        //             );
        //         });
        //     }
        // });
        // appState.watchModelFields(
        //     $scope,
        //     ['Wall', 'Fill'].map(
        //         function(x) {
        //             return flashService.simulationModel() + '.sim_tele' + x;
        //         }
        //     ),
        //     makeTempsEqual
        // );
        // processCurrType();
        // appState.watchModelFields(
        //     $scope,
        //     [flashService.simulationModel() + '.sim_currType'],
        //     processCurrType
        // );
    });
});

SIREPO.app.controller('VisualizationController', function(appState, flashService, frameCache, persistentSimulation, $scope, $window) {
    var self = this;
    self.simScope = $scope;
    self.flashService = flashService;
    self.plotClass = 'col-md-6';

    self.startSimulation = function() {
        appState.models.oneDimensionProfileAnimation.selectedPlotFiles = [];
        self.simState.saveAndRunSimulation(['simulation', 'oneDimensionProfileAnimation']);
    };

    function setAxis() {
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
        }[appState.models.Grid.geometry];
        if (appState.models.setupArguments.d === 3) {
            let a = 'z';
            if (['cylindrical', 'spherical'].includes(appState.models.Grid.geometry)) {
                a = 'phi';
            }
            SIREPO.APP_SCHEMA.enum.Axis.push([a, a]);
        }
        const d = SIREPO.APP_SCHEMA.enum.Axis[0][0];
        SIREPO.APP_SCHEMA.model.oneDimensionProfileAnimation.axis[2]= d;
        // Set the axis to be the default if it is currently set to an
        // axis that is invalid for the selected geometry
        ['oneDimensionProfileAnimation', 'varAnimation'].forEach((m) => {
            if (! SIREPO.APP_SCHEMA.enum.Axis.map((a) => a[0]).includes(
                appState.models[m].axis
            )) {
                appState.models[m].axis = d;
                appState.saveChanges(m);
            }
        });
    }

    function updateValueList(modelName, fields, values) {
        if (! values) {
            return;
        }
        const m = appState.models[modelName];
        if (! m.valueList) {
            m.valueList = {};
        }
        fields.forEach((f) => {
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
                '<div data-sim-sections="">',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'config\')}"><a href data-ng-click="nav.openSection(\'config\')"><span class="glyphicon glyphicon-list"></span> Config</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'setup\')}"><a href data-ng-click="nav.openSection(\'setup\')"><span class="glyphicon glyphicon-tasks"></span> Setup</a></li>',
                  '<li data-ng-if="appState.models.flashSchema" class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-th"></span> Source</a></li>',
                  '<li data-ng-if="appState.models.flashSchema" class="sim-section" data-ng-class="{active: nav.isActive(\'physics\')}"><a href data-ng-click="nav.openSection(\'physics\')"><span class="glyphicon glyphicon-fire"></span> Physics</a></li>',
                  '<li data-ng-if="appState.models.flashSchema" class="sim-section" data-ng-class="{active: nav.isActive(\'params\')}"><a href data-ng-click="nav.openSection(\'params\')"><span class="glyphicon glyphicon-edit"></span> Parameters</a></li>',
                  // '<li class="sim-section" data-ng-class="{active: nav.isActive(\'runtimeParams\')}"><a href data-ng-click="nav.openSection(\'runtimeParams\')"><span class="glyphicon glyphicon-scale"></span> Runtime Params</a></li>',
                  '<li data-ng-if="appState.models.flashSchema" class="sim-section" data-ng-class="{active: nav.isActive(\'visualization\')}"><a href data-ng-click="nav.openSection(\'visualization\')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
                '</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
              '</app-settings>',
              '<app-header-right-sim-list>',
              '</app-header-right-sim-list>',
            '</div>',
        ].join(''),
        controller: function(appState, $scope) {
            $scope.appState = appState;
        },
    };
});

SIREPO.app.directive('configTable', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<table class="table table-hover" style="width: 100%">',
              '<tr data-ng-repeat="item in configList track by item._id">',
                '<td>',
                  '<span style="white-space: pre">{{ item.pad }}</span>',
                  '<span style="font-size: 14px" class="badge sr-badge-icon">{{ item._type }}</span>',
                  ' <strong>{{ item.first }}</strong> <span> {{ item.description }}</span>',
                  '<div style="margin-left: 4em" data-ng-if="item.comment">{{ item.comment }}</div>',
                '</td>',
              '</tr>',
            '</table>',
        ].join(''),
        controller: function($scope) {
            const fieldOrder = SIREPO.APP_SCHEMA.constants.flashDirectives.fieldOrder;
            const labels = SIREPO.APP_SCHEMA.constants.flashDirectives.labels;

            function createItem(item, level) {
                const v = appState.clone(item);
                v.pad = '  '.repeat(level * 4);
                let desc = '';
                v.first = item[fieldOrder[item._type][0]];
                fieldOrder[item._type].forEach((f, idx) => {
                    if (idx > 0 && angular.isDefined(item[f])) {
                        let v = item[f];
                        if (f == 'isConstant') {
                            if (v == '1') {
                                desc += ' CONSTANT';
                            }
                            return;
                        }
                        if (f == 'default' && item.type == 'STRING') {
                            v = '"' + v + '"';
                        }
                        if (! v.length) {
                            return;
                        }
                        if (f == 'range') {
                            v = '[' + v + ']';
                        }
                        else if (labels[f]) {
                            v = labels[f] + ' ' + v;
                        }
                        desc += ' ' + v;
                    }
                });
                v.description = desc;
                return v;
            }

            function addConfigItem(item, level) {
                level = level || 0;
                $scope.configList.push(createItem(item, level));
                if (item.statements) {
                    item.statements.forEach((subitem) => addConfigItem(subitem, level + 1));
                }
            }

            function loadDirectives() {
                $scope.configList = [];
                appState.applicationState().setupConfigDirectives.forEach((item) => addConfigItem(item));
            }

            appState.whenModelsLoaded($scope, () => {
                $scope.$on('setupConfigDirectives.changed', loadDirectives);
                loadDirectives();
            });
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
        template: [
            '<div style="margin: 5px 0; min-height: 34px; max-height: 20em; overflow-y: auto; border: 1px solid #ccc; border-radius: 4px">',
              '<table class="table table-condensed table-hover" style="margin:0">',
                '<tbody>',
                  '<tr data-ng-repeat="file in plotFiles track by $index" data-ng-click="toggleFile(file.filename)">',
                    '<td>{{ file.time }}</td>',
                    '<td><input type="checkbox" data-ng-checked="isSelected(file.filename)"></td>',
                  '</tr>',
                '</tbody>',
              '</table>',
            '</div>',
        ].join(''),
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
        template: [
            '<div style="margin-bottom: 1ex" data-ng-repeat="name in modelNames track by name">',
            '<button class="btn btn-default" data-ng-click="showModal(name)">{{ name }}</button>',
            '</div>',
        ].join(''),
        controller: function(appState, panelState, $scope) {
            $scope.showModal = (name) => panelState.showModalEditor(name);

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
        template: [
            '<div>',
            '<div class="modal fade" id="sr-setup-command" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-warning">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<span class="lead modal-title text-info">Setup Command</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<div class="row">',
                        '<pre><code>{{ setupCommand }}</code></pre>',
                      '</div>',
                      '<br />',
                      '<div class="row">',
                        '<div class="col-sm-offset-6 col-sm-3">',
                          '<button data-dismiss="modal" class="btn btn-primary" style="width:100%">Close</button>',
                        '</div>',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
              '<div data-basic-editor-panel="" data-view-name="setupArguments">',
                '<button type="button" class="btn btn-secondary" data-ng-click="showSetupCommand()">',
                  '<span aria-hidden="true">Show setup command</span>',
                '</button>',
              '</div>',
            '</div>'
        ].join(''),
        controller: function($scope, appState, requestSender) {
            $scope.setupCommand = '';
            $scope.showSetupCommand= function() {
                var el = $('#sr-setup-command');
                el.modal('show');
                el.on('shown.bs.modal', function() {
                requestSender.getApplicationData(
                    {
                        method: 'setup_command',
                        models: appState.models,
                    },
                    function(data) {
                        $scope.setupCommand = data.setupCommand;
                    });
                });
                el.on('hidden.bs.modal', function() {
                    $scope.setupCommand = '';
                    el.off();
                });
            };
        },
    };
});

// SIREPO.app.directive('runtimeParametersTable', function() {
//     return {
//         restrict: 'A',
//         scope: {},
//         template: [
//             '<table class="table table-hover" style="width: 100%">',
//               '<thead>',
//                 '<tr>',
//                   '<th scope="col">Name</th>',
//                   '<th scope="col">Value</th>',
//                 '</tr>',
//               '</thead>',
//               '<tbody data-ng-repeat="param in parameters">',
//                 '<tr>',
//                   '<td>',
//                     '<div style="font-size: 14px" class="badge sr-badge-icon">{{ param.name }}</div>',
//                   '</td>',
//                   '<td>',
//                     '<div>{{ param.value }}</div>',
//                   '</td>',
//                 '</tr>',
//               '</tbody>',
//             '</table>',
//         ].join(''),
//         controller: function($scope, appState, directiveService) {
//             $scope.parameters = [];
//             function loadParameters() {
//                 const m = appState.models[`Simulation${appState.models.simulation.flashType}`];
//                 $scope.parameters =  Object.keys(m).map((k) => {
//                     return {name: k, value: m[k]};
//                 });
//             }

//             appState.whenModelsLoaded($scope, function() {
//                 $scope.$on('modelChanged', function(e, name) {
//                     if (name == 'setupConfigDirectives') {
//                         loadParameters();
//                     }
//                 });
//                 loadParameters();
//             });
//         },
//     };
// });

SIREPO.viewLogic('varAnimationView', function(appState, flashService, panelState, $scope) {

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
            flashService.getNdim() > 2);
        updateHeatmapFields();
    };

    $scope.watchFields = [
        ['varAnimation.plotType'], updateHeatmapFields,
    ];
});
