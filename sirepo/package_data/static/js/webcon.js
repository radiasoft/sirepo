'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.INCLUDE_EXAMPLE_FOLDERS = true;
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="AnalysisParameter" class="col-sm-5">',
      '<div data-analysis-parameter="" data-model="model" data-field="field"></div>',
    '</div>',
    '<div data-ng-switch-when="AnalysisOptionalParameter" class="col-sm-5">',
      '<div data-analysis-parameter="" data-model="model" data-field="field" data-is-optional="true"></div>',
    '</div>',
    '<div data-ng-switch-when="Equation" class="col-sm-7">',
      '<div data-equation="equation" data-model="model" data-field="field" data-parent-controller="source"></div>',
    '</div>',
    '<div data-ng-switch-when="EquationVariables" class="col-sm-7">',
      '<div data-equation-variables="" data-model="model" data-field="field"></div>',
    '</div>',
].join('');


SIREPO.app.factory('webconService', function(appState) {
    var self = {};
    self.analysisParameters = null;

    self.setAnalysisParameters = function(columnInfo) {
        self.analysisParameters = columnInfo;
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

    self.validateEquation = function(eq) {
        srdbg('VALIDATING', eq);
    };


    appState.whenModelsLoaded($scope, function() {
        appState.watchModelFields($scope, ['fitter.equation', 'fitter.variables'], function() {
            self.validateEquation(appState.models.fitter.equation);
        });
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

SIREPO.app.directive('equation', function(appState) {
    return {
        scope: {
            controller: '=parentController',
            model: '=',
            field: '='
        },
        template: [
            '<div>',
                '<input type="text" data-ng-model="model[field]" data-ng-change="validate()" class="form-control" required>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.validate = function () {
                //$scope.controller.validateEquation($scope.model.equation);
            };

        },
    };
});

SIREPO.app.directive('equationVariables', function() {
    return {
        restrict: 'A',
        scope: {
            equation: '<',
            field: '=',
            model: '=',
        },
        template: [
            '<div>',
                '<input type="text" data-ng-model="model[field]" class="form-control" required />',
            '</div>'
        ].join(''),
        controller: function($scope) {
            var opsRegEx = /[\+\-\*/\^\(\)]/;
            var reserved = ['sin', 'cos', 'tan', 'abs'];
            $scope.values = null;
            $scope.didChange = function() {
                $scope.field = $scope.values.join(', ');
            };
            $scope.parseValues = function() {
                if ($scope.field && ! $scope.values) {
                    $scope.values = $scope.field.split(/\s*,\s*/);
                }
                return $scope.values;
            };
        },
    };
});


SIREPO.app.directive('fitReport', function(appState) {
    return {
        //scope: {
        //    controller: '=parentController',
        //    model: '=',
        //},
        template: [
            '<div class="col-md-6 col-xl-4">',
                '<div data-report-panel="parameter" data-request-priority="1" data-model-name="fitterReport"></div>',
                //'<div data-equation="" data-model="model" data-field="field"></div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            srdbg('scope', $scope);
            //srdbg('model/field', $scope.model, $scope.field);
        },
    };
});
