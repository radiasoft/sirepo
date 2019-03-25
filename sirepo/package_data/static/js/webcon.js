'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="AnalysisParameter" class="col-sm-5">',
      '<div data-analysis-parameter="" data-model="model" data-field="field"></div>',
    '</div>',
    '<div data-ng-switch-when="AnalysisOptionalParameter" class="col-sm-5">',
      '<div data-analysis-parameter="" data-model="model" data-field="field" data-is-optional="true"></div>',
    '</div>',
    '<div data-ng-switch-when="Equation" class="col-sm-7">',
      '<div data-equation="equation" data-model="model" data-field="field"></div>',
      '<div class="sr-input-warning" data-ng-show="showWarning">{{warningText}}</div>',
    '</div>',
    '<div data-ng-switch-when="EquationVariables" class="col-sm-7">',
      '<div data-equation-variables="" data-model="model" data-field="field" data-form="form" data-is-variable="true"></div>',
    '</div>',
    '<div data-ng-switch-when="EquationParameters" class="col-sm-7">',
      '<div data-equation-variables="" data-model="model" data-field="field" data-form="form" data-is-variable="false"></div>',
    '</div>',
].join('');


SIREPO.app.factory('webconService', function(appState, validationService) {
    var self = {};
    validationService.setFieldValidator('equation', self.validateEquation);
    self.analysisParameters = null;

    self.setAnalysisParameters = function(columnInfo) {
        self.analysisParameters = columnInfo;
    };

    self.validateEquation = function (fitModel) {
        srdbg('validate', fitModel);
    };

    return self;
});

SIREPO.app.controller('AnalysisController', function (appState, frameCache, panelState, persistentSimulation, webconService, $scope, $timeout) {
    var self = this;

    function handleStatus(data) {
        if (appState.models.analysisData.file) {
            frameCache.setFrameCount(data.frameCount);
            if (data.columnInfo) {
                webconService.setAnalysisParameters(data.columnInfo);
            }
        }
    }

    self.hasFile = function() {
        return appState.isLoaded() && appState.applicationState().analysisData.file;
    };

    self.isFitterConfigured = function() {
        return appState.models.fitter.equation && appState.models.fitter.variable && appState.models.fitter.parameters;
    };

    appState.whenModelsLoaded($scope, function() {
        $scope.$on('analysisData.changed', function() {
            frameCache.setFrameCount(0);
            if (appState.models.analysisData.file) {
                self.simState.saveAndRunSimulation('analysisData');
            }
        });
    });

    self.simState = persistentSimulation.initSimulationState($scope, 'animation', handleStatus, {
        analysisAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'x', 'y1', 'y2', 'y3', 'startTime'],
    });
});

SIREPO.app.directive('analysisParameter', function(webconService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            isOptional: '@',
        },
        template: [
            '<select class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in parameterValues()"></select>',
        ].join(''),
        controller: function($scope) {
            var analysisParameters, parameterValues;
            $scope.parameterValues = function() {
                if (analysisParameters == webconService.analysisParameters) {
                    return parameterValues;
                }
                analysisParameters = webconService.analysisParameters;
                parameterValues = [];
                var visited = {};
                analysisParameters.names.forEach(function(name, idx) {
                    // skip duplicate columns
                    if (! visited[name]) {
                        parameterValues.push(['' + idx, name]);
                        visited[name] = true;
                    }
                });
                parameterValues.sort(function(a, b) {
                    return a[1].localeCompare(b[1]);
                });
                if ($scope.isOptional) {
                    parameterValues.unshift(['none', 'None']);
                }
                return parameterValues;
            };
        },
    };
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'analysis\')}"><a href data-ng-click="nav.openSection(\'analysis\')"><span class="glyphicon glyphicon-tasks"></span> Analysis</a></li>',
		'</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
		//  '<div>App-specific setting item</div>',
              '</app-settings>',
              '<app-header-right-sim-list>',
              '</app-header-right-sim-list>',
            '</div>',
        ].join(''),
    };
});

SIREPO.app.directive('equation', function(appState, webconService) {
    return {
        scope: {
            model: '=',
            field: '='
        },
        template: [
            '<div>',
                '<input type="text" data-ng-model="model[field]" class="form-control" required>',
            '</div>',
        ].join(''),
        controller: function ($scope) {
            $scope.webconservice = webconService;

            this.tmp = $scope.model;
            //$scope.validate = function () {
            //    srdbg('val eq', $scope.model);
                //$scope.controller.validateEquation($scope.model.equation);
            //};

        },
    };
});

SIREPO.app.directive('equationVariables', function() {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            form: '=',
            isVariable: '<',
            model: '=',
        },
        template: [
            '<div>',
                '<input type="text" data-ng-model="model[field]" data-valid-variable-or-param="" class="form-control" required />',
            '</div>',
            '<div class="sr-input-warning" data-ng-show="warningText.length > 0">{{warningText}}</div>',
        ].join(''),
        controller: function($scope, $element) {
            var opsRegEx = /[\+\-\*/\^\(\)\%]/;
            var reserved = ['sin', 'cos', 'tan', 'abs'];

            $scope.equation = $scope.model.equation;
        },
    };
});

SIREPO.app.directive('validVariableOrParam', function(utilities) {
    return {
        restrict: 'A',
        require: 'ngModel',
         link: function(scope, element, attrs, ngModel) {

            function tokens(unique) {
                var t = (ngModel.$viewValue || '').split(/\s*,\s*/);
                if(unique) {
                    return utilities.unique(t);
                }
                return t;
            }

            function isUnique (val, arr) {
                var i = arr.indexOf(val);
                if(i < 0) {
                    throw val + ': Value not in array';
                }
                return i === arr.lastIndexOf(val);
            }

            function validateParam(p) {
                scope.warningText = '';
                if(! /^[a-zA-Z]+$/.test(p)) {
                    scope.warningText = (scope.isVariable ? 'Variables' : 'Parameters') + ' must be alphabetic';
                    return false;
                }
                if(! scope.isVariable && p === scope.model.variable) {
                    scope.warningText = p + ' is an independent variable';
                    return false;
                }
                if(scope.model.equation.indexOf(p) < 0) {
                    scope.warningText = p + ' does not appear in the equation';
                    return false;
                }
                if(! isUnique(p, tokens())) {
                    scope.warningText = p + ' is duplicated';
                    return false;
                }

                return true;
            }

            ngModel.$validators.validTokens = (function (v) {
                return (ngModel.$viewValue || '').split(/\s*,\s*/)
                    .filter(function (p) {
                        return p.length > 0;
                    })
                    .reduce(function (valid, p) {
                        return valid && validateParam(p);
                    }, true);
            });
        },
    };
});

SIREPO.app.directive('fitReport', function(appState) {
    return {
        scope: {
            controller: '=parentController',
        },
        template: [
            '<div data-basic-editor-panel="" data-view-name="fitter" data-parent-controller="controller"></div>',
            '<div data-ng-if="controller.isFitterConfigured()" data-report-panel="parameter" data-request-priority="1" data-model-name="fitReport"></div>',
        ].join(''),
        controller: function($scope) {

            $scope.$on('fitter.changed', function() {
                appState.saveChanges('fitReport', function () {
                });
            });
            $scope.$on('fitReport.changed', function() {
                srdbg('FR', appState.models);
            });

        },
    };
});
