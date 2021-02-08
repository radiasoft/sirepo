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
        '<div data-ng-switch-when="DirectiveParameterField" data-ng-class="fieldClass">',
          '<div data-directive-parameter-field="" data-field="field" data-model="model"></div>',
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

    self.create = function(name) {
        if(! appState.models.setupConfigDirectives) {
            appState.models.setupConfigDirectives = [];
        }

        const m = {
            _id: appState.maxId(appState.models.setupConfigDirectives, '_id') + 1,
            _type: name,
        };
        const n = modelName(m);
        appState.setModelDefaults(m, n);
        appState.models[n] = m;
        panelState.showModalEditor(n);
    };

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

    self.editDirective = function(directive) {
        function directiveForId(directive) {
            const d = appState.models.setupConfigDirectives;
            for (let i = 0; i < d.length; i++) {
                if (d[i]._id == directive._id) {
                    return d[i];
                }
            }
            return null
        }
        const m = modelName(directive);
        appState.models[m] = directiveForId(directive);
        panelState.showModalEditor(m);
    };

    self.isDirectiveModelName = function(name) {
        return name.indexOf(DIRECTIVE_PREFIX) === 0;
    }

    self.typeFromModelName = function(name) {
        return name.split(DIRECTIVE_PREFIX)[1];
    }

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
    // Ordering matters - It is the order they appear in the config table
    self.directiveNames = [
        'REQUIRES',
        'REQUESTS',
        'PARAMETER',
        'PARTICLEPROP',
        'PARTICLEMAP',
        'VARIABLE',
    ];
    self.advancedNames = [];

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
        scope: {
            directiveNames: '=',
        },
        template: [
            '<div class="pull-right">',
                '<button class="btn btn-info btn-xs" data-ng-click="newDirective()" accesskey="c" ng-bind-html="newDirectiveText()"><span class="glyphicon glyphicon-plus"></span></button>',
              '</div>',
              '<p class="lead text-center"><small><em>Hover over a directive to see edit options</em></small></p>',
              '<table class="table table-hover" style="width: 100%">',
              '<tbody data-ng-repeat="(name, category) in tree">',
                '<tr>',
                  '<td style="cursor: pointer" colspan="4" data-ng-click="toggleCategory(name, category)" ><span class="glyphicon" data-ng-class="{\'glyphicon-collapse-up\': ! category.isCollapsed, \'glyphicon-collapse-down\': category.isCollapsed}"></span> <b>{{ name }}</b></td>',
                '</tr>',
                '<tr data-ng-show="! category.isCollapsed" data-ng-repeat="directive in category.directives track by $index">',
                  '<td>',
                    '<div class="sr-button-bar-parent pull-right"><div class="sr-button-bar"><button class="btn btn-info btn-xs"  data-ng-disabled="$index == 0" data-ng-click="moveDirective(-1, name, directive)"><span class="glyphicon glyphicon-arrow-up"></span></button> <button class="btn btn-info btn-xs" data-ng-disabled="$index == category.directives.length - 1" data-ng-click="moveDirective(1, name, directive)"><span class="glyphicon glyphicon-arrow-down"></span></button> <button class="btn btn-info btn-xs sr-hover-button" data-ng-click="editDirective(directive)">Edit</button><button data-ng-click="deleteDirective(directive)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div></div>',
                    '<div>',
                      '<div style="font-size: 14px" class="badge sr-badge-icon">{{ directive._type }}</div>',
                    '</div>',
                    '<div style="white-space: pre-wrap">{{ directive.description }}</div>',
                  '</td>',
                '</tr>',
              '</tbody>',
              '</table>',
              '<button class="btn btn-info btn-xs pull-right" data-ng-click="newDirective()" accesskey="c" ng-bind-html="newDirectiveText()"><span class="glyphicon glyphicon-plus"></span></button>',
            '</div>',
            '<div data-confirmation-modal="" data-id="sr-delete-directive-confirmation" data-title="Delete Directive?" data-ok-text="Delete" data-ok-clicked="deleteSelected()">Delete directive &quot;{{ selectedDirectiveType() }}&quot;?</div>',
        ].join(''),
        controller: function($injector, $scope) {
            var selectedDirective = null;
            const collapsedCategories = {};
            $scope.tree = {};

            function loadDirectives() {
                $scope.tree = {};
                const tree = {};
                $scope.directiveNames.forEach((n) => {
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

            function saveDirectives() {
                const directives = [];
                Object.values($scope.tree).forEach((c) => {
                    c.directives.forEach((d) => {
                        const e = {...d};
                        delete e.description;
                        directives.push(e)
                    })
                })
                appState.models.setupConfigDirectives = directives;
                appState.saveChanges('setupConfigDirectives');
            }

            $scope.deleteDirective = function(directive) {
                $scope.selectDirective(directive);
                $('#sr-delete-directive-confirmation').modal('show');
            };

            $scope.deleteSelected = function() {
                let index = null;
                const d = $scope.tree[selectedDirective._type].directives;
                for (let i = 0; i < d.length; i++) {
                    if (d[i]._id === selectedDirective._id) {
                        index = i;
                        break
                    }
                }
                if (index >= 0) {
                    selectedDirective = null;
                    d.splice(index, 1)
                    saveDirectives();
                }
            };

            // expects a negative number to move up, positive to move down
            $scope.moveDirective = function(direction, categoryName, directive) {
                function directiveIndex(directive) {
                    const d = $scope.tree[categoryName].directives;
                    for (let i = 0; i< d.length; i++) {
                        if (d[i]._id === directive._id)  {
                            return i
                        }
                    }
                    throw new Error(`directive=${d} not found in setupConfigDirectives`);
                }
                const idx = directiveIndex(directive);
                const d = $scope.tree[categoryName].directives;
                const n = Math.min(Math.max(idx + direction, 0), d.length - 1);
                if (idx === n) {
                    return;
                }
                const t = d[idx]
                d[idx] = d[n];
                d[n] = t;
                saveDirectives();
            };

            $scope.editDirective = function(directive) {
                directiveService.editDirective(directive);
            };

            $scope.newDirective = function() {
                $('#' + panelState.modalId('newDirective')).modal('show');
            };

            $scope.newDirectiveText = function() {
                return 'New <u>D</u>irective';
            }

            $scope.selectDirective = function(directive) {
                selectedDirective = directive;
            };

            $scope.selectedDirectiveType = function() {
                if (selectedDirective) {
                    return selectedDirective._type;
                }
                return '';
            };

            $scope.toggleCategory = function(name, category) {
                category.isCollapsed = ! category.isCollapsed;
                collapsedCategories[name] = category.isCollapsed;
            };

            appState.whenModelsLoaded($scope, function() {
                $scope.$on('modelChanged', function(e, name) {
                    function selectedDirectiveIndex() {
                        if (selectedDirective) {
                            const d = appState.models.setupConfigDirectives;
                            for (let i = 0; i < d.length; i++) {
                                if (d[i]._id == selectedDirective._id) {
                                    return i;
                                }
                            }
                        }
                        return -1;
                    }

                    if (name == 'setupConfigDirectives') {
                        loadDirectives();
                    }
                    if (directiveService.isDirectiveModelName(name)) {
                        let foundIt = false;
                        const d = ($scope.tree[directiveService.typeFromModelName(name)] || {}).directives || [];
                        for (var i = 0; i < d.length; i++) {
                            if (d[i]._id == appState.models[name]._id) {
                                foundIt = true;
                                break;
                            }
                        }
                        if (! foundIt) {
                            const index = selectedDirectiveIndex();
                            if (index >= 0) {
                                appState.models.setupConfigDirectives.splice(index + 1, 0, appState.models[name]);
                            }
                            else {
                                appState.models.setupConfigDirectives.push(appState.models[name]);
                            }
                            $scope.selectDirective(appState.models[name]);
                        }
                        appState.removeModel(name);
                        appState.saveChanges('setupConfigDirectives');
                    }
                });
                $scope.$on('cancelChanges', function(e, name) {
                    if (directiveService.isDirectiveModelName(name)) {
                        appState.removeModel(name);
                        appState.cancelChanges('setupConfigDirectives');
                    }
                });
                loadDirectives();
            });
        },
    };
});

SIREPO.app.directive('directiveParameterField', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: [
            // TODO(e-carlin): copied from sirepo-components.fieldEditor
            '<div data-ng-switch="type">',
              '<div data-ng-switch-when="Integer" data-ng-class="fieldClass">',
                '<input data-string-to-number="integer" data-ng-model="model[field]" class="form-control" style="text-align: right" data-lpignore="true" />',
              '</div>',
              '<div data-ng-switch-when="Float" data-ng-class="fieldClass">',
                '<input data-string-to-number="" data-ng-model="model[field]" class="form-control" style="text-align: right" data-lpignore="true" />',
              '</div>',
               '<div data-ng-switch-when="Boolean" class="col-sm-7">',
                 // angular has problems initializing checkboxes - ngOpen has no effect on them, but we can use it to change the state as the models load
                 '<input class="sr-bs-toggle" data-ng-open="fieldDelegate.refreshChecked()" data-ng-model="model[field]" data-bootstrap-toggle="" data-model="model" data-field="field" data-field-delegate="fieldDelegate" data-info="info" type="checkbox">',
              '</div>',
              '<div data-ng-switch-when="String" data-ng-class="fieldClass">',
                '<input data-ng-model="model[field]" class="form-control" data-lpignore="true" />',
              '</div>',
             '</div>',
        ].join(''),
        controller: function($scope, appState) {
            $scope.fieldDelegate = {};
            const d = {
                BOOLEAN: 'Boolean',
                INTEGER: 'Integer',
                REAL: 'Float',
                STRING: 'String'
            };

            function setType() {
                function info(type) {
                    const b = [...SIREPO.APP_SCHEMA.model.directive_PARAMETER.default];
                    b[1] = type;
                    $scope.info = b;
                }

                $scope.type = d[$scope.model.type];
                if ($scope.type === 'Boolean')  {
                    info('Boolean');
                } else {
                    info('DirectiveParameterField');
                }
                // TODO(e-carlin): fix
                // field needs to be reset whenever the type is changed.
                // If we go from REAL 2.45 to bool the 2.45 needs to be cleared.
                // This doesn't work because a change is raised whenever we
                // open a new directive which means the field will be cleared
                // as soon as a user opens a new directive even if they don't
                // change the type
                $scope.model[$scope.field] = '';
            }

            setType();
            appState.watchModelFields($scope, ['directive_PARAMETER.type'], () => {
                setType();
            })
        },
    };
});

SIREPO.app.directive('directivePicker', function(directiveService) {
    return {
        restrict: 'A',
        scope: {
            controller: '=',
            title: '@',
            id: '@',
            smallElementClass: '@',
        },
        template: [
            '<div class="modal fade" data-ng-attr-id="{{ id }}" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<span class="lead modal-title text-info">{{ title }}</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<div class="row">',
                        '<div data-ng-repeat="name in controller.directiveNames" class="col-sm-4">',
                          '<button style="width: 100%; margin-bottom: 1ex;" class="btn btn-default" type="button" data-ng-click="createDirective(name)">{{ name }}</button>',
                        '</div>',
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
        ].join(''),
        controller: function($scope) {
            $scope.createDirective = function(name) {
                // don't show the new editor until the picker panel is gone
                // the modal show/hide in bootstrap doesn't handle layered modals
                // and the browser scrollbar can be lost in some cases
                var picker = $('#' + $scope.id);
                picker.on('hidden.bs.modal', function() {
                    picker.off();
                    directiveService.create(name);
                    $scope.$applyAsync();
                });
                picker.modal('hide');
            };
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
                  '<td>',
                    '<div class="sr-button-bar-parent pull-right"><div class="sr-button-bar"><button class="btn btn-info btn-xs sr-hover-button" data-ng-click="editParam(param)">Edit</button></div></div>',
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

            $scope.editParam = function(param) {
                directiveService.editDirective(param);
            }

            appState.whenModelsLoaded($scope, function() {
                $scope.$on('modelChanged', function(e, name) {
                    if (name == 'setupConfigDirectives') {
                        loadParameters();
                    }
                    if (directiveService.isDirectiveModelName(name)) {
                        appState.removeModel(name);
                        appState.saveChanges('setupConfigDirectives');
                    }
                });
                $scope.$on('cancelChanges', function(e, name) {
                    if (directiveService.isDirectiveModelName(name)) {
                        appState.removeModel(name);
                        appState.cancelChanges('setupConfigDirectives');
                    }
                });
                loadParameters();
            });
        },
    };
});
