'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appDefaultSimulationValues.simulation.flashType = 'RTFlame';
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="NoDashInteger" data-ng-class="fieldClass">',
        // TODO(e-carlin): this is just copied from sirepo-components
          '<input data-string-to-number="integer" data-ng-model="model[field]" data-min="info[4]" data-max="info[5]" class="form-control" style="text-align: right" data-lpignore="true" required />',
        '</div>'
    ].join('');
    SIREPO.FILE_UPLOAD_TYPE = {
        'problemFiles-archive': '.zip',
    };
    SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL = true;
    SIREPO.SINGLE_FRAME_ANIMATION = ['gridEvolutionAnimation'];
});


SIREPO.app.factory('directiveService', function(appState, panelState, validationService) {
    const self = {};
    const DIRECTIVE_PREFIX = 'directive_';

    function modelName(item) {
        return DIRECTIVE_PREFIX + item._type;
    }

    self.description = function(directive) {
        return {
            PARAMETER: `${directive.name} ${directive.type} ${directive.default}`,
            PARTICLEPROP: `${directive.name} ${directive.type}`,
            PARTICLEMAP: `TO ${directive.partName} FROM ${directive.varType} ${directive.varName}`,
            REQUIRES: `${directive.unit}`,
            REQUESTS: `${directive.unit}`,
            VARIABLE: `${directive.name}`
        }[directive._type];
    };

    return self;
});

SIREPO.app.factory('flashService', function(appState, panelState) {
    var self = {};

    self.computeModel = function(analysisModel) {
        return 'animation';
    };

    self.isCapLaser = function() {
        return appState.isLoaded()
            &&  appState.models.simulation.flashType.indexOf('CapLaser') >= 0;
    };

    self.isFlashType = function(simType) {
        return appState.isLoaded()
            && simType == appState.models.simulation.flashType;
    };

    self.simulationModel = function() {
        return 'Simulation' + appState.models.simulation.flashType;
    };

    appState.setAppService(self);

    return self;
});

SIREPO.app.controller('ConfigController', function (directiveService, flashService) {
    var self = this;
    self.flashService = flashService;
});

SIREPO.app.controller('PhysicsController', function (flashService) {
    var self = this;
    self.flashService = flashService;
});

SIREPO.app.controller('RuntimeParamsController', function () {
    var self = this;
});

SIREPO.app.controller('PhysicsController', function (flashService) {
    var self = this;
    self.flashService = flashService;
});

SIREPO.app.controller('SourceController', function (appState, flashService, panelState, $scope) {
    var self = this;
    self.flashService = flashService;

    function setReadOnly(modelName) {
        [
            'sim_tionWall', 'sim_tionFill', 'sim_tradWall', 'sim_tradFill',
        ].forEach(function(f) {
            panelState.enableField(modelName, f, false);
        });
        // TODO(e-carlin): If we support more than alumina for wall species
        // then we should remove this readonly or keep it and update the Z and A
        // when the species changes.
        ['ms_wallA', 'ms_wallZ'].forEach(function(f) {
            panelState.enableField('Multispecies', f, false);
        });
    }

    function makeTempsEqual(modelField) {
        var t = modelField.indexOf('Fill') >= 0 ? 'Fill' : 'Wall';
        var s = appState.parseModelField(modelField);
        ['ion', 'rad'].forEach(function(f) {
            appState.models[flashService.simulationModel()]['sim_t' + f + t] = appState.models[s[0]][s[1]];
        });
    }

    function processCurrType() {
        var modelName = flashService.simulationModel();

        function showField(field, isShown) {
            panelState.showField(modelName, field, isShown);
        }

        var isFile = appState.models[modelName].sim_currType === '2';
        showField('sim_currFile', isFile);
        ['sim_peakCurr', 'sim_riseTime'].forEach(function(f) {
            showField(f, !isFile);
        });
    }

    appState.whenModelsLoaded($scope, function() {
        if (! flashService.isCapLaser()) {
            return;
        }
        $scope.$on('sr-tabSelected', function(event, modelName) {
            if (['SimulationCapLaser3D', 'SimulationCapLaserBELLA'].indexOf(modelName) >= 0) {
                // Must be done on sr-tabSelected because changing tabs clears the
                // readonly prop. This puts readonly back on.
                setReadOnly(modelName);
            }
            else if (modelName == 'Grid') {
                ['polar', 'spherical'].forEach(function(f) {
                    panelState.showEnum(
                        'Grid',
                        'geometry',
                        f,
                        ! flashService.isCapLaser()
                    );
                });
            }
        });
        appState.watchModelFields(
            $scope,
            ['Wall', 'Fill'].map(
                function(x) {
                    return flashService.simulationModel() + '.sim_tele' + x;
                }
            ),
            makeTempsEqual
        );
        processCurrType();
        appState.watchModelFields(
            $scope,
            [flashService.simulationModel() + '.sim_currType'],
            processCurrType
        );
    });
});

SIREPO.app.controller('VisualizationController', function (appState, flashService, frameCache, persistentSimulation, $scope, $window) {
    var self = this;
    self.simScope = $scope;
    self.flashService = flashService;
    self.plotClass = 'col-md-6 col-xl-4';
    self.gridEvolutionColumnsSet = false;

    self.simHandleStatus = function(data) {
        var i = 0;
        // moved function out of for loop to avoid jshint warning
        function addValue(e) {
            appState.models.gridEvolutionAnimation.valueList[e].push(
                data.gridEvolutionColumns[i]
            );
        }
        self.errorMessage = data.error;
        if ('frameCount' in data && ! data.error) {
            ['varAnimation', 'gridEvolutionAnimation'].forEach(function(m) {
                appState.saveQuietly(m);
                frameCache.setFrameCount(data.frameCount, m);
            });
        }
        if (! self.gridEvolutionColumnsSet && data.gridEvolutionColumns) {
            self.gridEvolutionColumnsSet = true;
            appState.models.gridEvolutionAnimation.valueList = {
                y1: [],
                y2: [],
                y3: []
            };
            for (i = 0; i < data.gridEvolutionColumns.length; i++) {
                ['y1', 'y2', 'y3'].forEach(addValue);
            }
            appState.saveChanges('gridEvolutionAnimation');
        }
        frameCache.setFrameCount(data.frameCount || 0);
    };

    self.simState = persistentSimulation.initSimulationState(self);

    appState.whenModelsLoaded($scope, function() {
        $scope.$on('varAnimation.summaryData', function(e, data) {
            var newPlotClass = self.plotClass;
            if (data.aspectRatio > 2) {
                newPlotClass = 'col-md-5 col-xl-4';
            }
            else if (data.aspectRatio < 1) {
                newPlotClass = 'col-md-12 col-xl-6';
            }
            else {
                newPlotClass = 'col-md-6 col-xl-4';
            }
            if (newPlotClass != self.plotClass) {
                self.plotClass = newPlotClass;
                $($window).trigger('resize');
            }
        });
    });
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
                '<div data-sim-sections="">',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-th"></span> Source</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'physics\')}"><a href data-ng-click="nav.openSection(\'physics\')"><span class="glyphicon glyphicon-fire"></span> Physics</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'config\')}"><a href data-ng-click="nav.openSection(\'config\')"><span class="glyphicon glyphicon-cog"></span> Config</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'runtimeParams\')}"><a href data-ng-click="nav.openSection(\'runtimeParams\')"><span class="glyphicon glyphicon-scale"></span> Runtime Params</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'visualization\')}"><a href data-ng-click="nav.openSection(\'visualization\')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
                '</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
              '</app-settings>',
              '<app-header-right-sim-list>',
              '</app-header-right-sim-list>',
            '</div>',
        ].join(''),
    };
});

SIREPO.app.directive('configTable', function(appState, directiveService, panelState) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div class="pull-right">',
              '</div>',
              '<table class="table table-hover" style="width: 100%">',
              '<tbody data-ng-repeat="(name, category) in tree">',
                '<tr>',
                  '<td style="cursor: pointer" colspan="4" data-ng-click="toggleCategory(name, category)" ><span class="glyphicon" data-ng-class="{\'glyphicon-collapse-up\': ! category.isCollapsed, \'glyphicon-collapse-down\': category.isCollapsed}"></span> <b>{{ name }}</b></td>',
                '</tr>',
                '<tr data-ng-show="! category.isCollapsed" data-ng-repeat="directive in category.directives track by $index">',
                  '<td>',
                    '<div>',
                      '<div style="font-size: 14px" class="badge sr-badge-icon">{{ directive._type }}</div>',
                    '</div>',
                    '<div style="white-space: pre-wrap">{{ directive.description }}</div>',
                  '</td>',
                '</tr>',
              '</tbody>',
              '</table>',
            '</div>',
        ].join(''),
        controller: function($injector, $scope) {
            var selectedDirective = null;
            const collapsedCategories = {};
            $scope.tree = {};

            function loadDirectives() {
                $scope.tree = {};
                const tree = {};
                [
                    'REQUIRES',
                    'REQUESTS',
                    'PARAMETER',
                    'PARTICLEPROP',
                    'PARTICLEMAP',
                    'VARIABLE',
                ].forEach((n) => {
                    tree[n] = {
                            directives: [],
                            isCollapsed: collapsedCategories[n],
                    };
                });
                const directives = appState.applicationState().setupConfigDirectives || [];
                directives.forEach((d) => {
                    const t = d._type;
                    tree[t].directives.push(Object.assign(
                        {description: directiveService.description(d),}, d
                    ));
                });
                for (const k in tree) {
                    if (tree[k].directives.length === 0) {
                        delete tree[k];
                    }
                }
                $scope.tree = tree;
            }

            $scope.toggleCategory = function(name, category) {
                category.isCollapsed = ! category.isCollapsed;
                collapsedCategories[name] = category.isCollapsed;
            };

            appState.whenModelsLoaded($scope, function() {
                $scope.$on('modelChanged', function(e, name) {
                    if (name == 'setupConfigDirectives') {
                        loadDirectives();
                    }
                });
                loadDirectives();
            });
        },
    };
});

SIREPO.app.directive('runtimeParametersTable', function() {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<table class="table table-hover" style="width: 100%">',
              '<thead>',
                '<tr>',
                  '<th scope="col">Name</th>',
                  '<th scope="col">Value</th>',
                '</tr>',
              '</thead>',
              '<tbody data-ng-repeat="param in parameters">',
                '<tr>',
                  '<td>',
                    '<div style="font-size: 14px" class="badge sr-badge-icon">{{ param.name }}</div>',
                  '</td>',
                  '<td>',
                    '<div>{{ param.value }}</div>',
                  '</td>',
                '</tr>',
              '</tbody>',
            '</table>',
        ].join(''),
        controller: function($scope, appState, directiveService) {
            $scope.parameters = [];
            function loadParameters() {
                const m = appState.models[`Simulation${appState.models.simulation.flashType}`];
                $scope.parameters =  Object.keys(m).map((k) => {
                    return {name: k, value: m[k]};
                });
            }

            appState.whenModelsLoaded($scope, function() {
                $scope.$on('modelChanged', function(e, name) {
                    if (name == 'setupConfigDirectives') {
                        loadParameters();
                    }
                });
                loadParameters();
            });
        },
    };
});
