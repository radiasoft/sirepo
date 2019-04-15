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
      '<div data-equation="equation" data-model="model" data-field="field" data-form="form"></div>',
      '<div class="sr-input-warning" data-ng-show="showWarning">{{warningText}}</div>',
    '</div>',
    '<div data-ng-switch-when="EquationVariables" class="col-sm-7">',
      '<div data-equation-variables="" data-model="model" data-field="field" data-form="form" data-is-variable="true"></div>',
    '</div>',
    '<div data-ng-switch-when="EquationParameters" class="col-sm-7">',
      '<div data-equation-variables="" data-model="model" data-field="field" data-form="form" data-is-variable="false"></div>',
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
            field: '=',
            form: '=',
        },
        template: [
            '<div>',
                '<input type="text" data-ng-change="validateAll()" data-ng-model="model[field]" class="form-control" required>',
            '</div>',
        ].join(''),
        controller: function ($scope) {
            $scope.webconservice = webconService;

            //srdbg('eq', $scope.model[$scope.field], 'tokens', tokenizeEquation());

            // function tokenizeEquation() {
            //     var reserved = ['sin', 'cos', 'tan', 'csc', 'sec', 'cot', 'exp', 'abs'];
            //TODO(pjm): jshint doesn't like the regular expression for some reason
            //     var tokens = $scope.model[$scope.field].split(/[-+*/^|%().0-9\s+]/)
            //         .filter(function (t) {
            //             return t.length > 0 && reserved.indexOf(t.toLowerCase()) < 0;
            //     });
            //     //tokens = tokens.filter(function (t) {
            //     //    return tokens.indexOf(t) === tokens.lastIndexOf(t);
            //     //});
            //     return tokens;
            // }

            $scope.validateAll = function() {
                $scope.form.$$controls.forEach(function (c) {
                    c.$validate();
                });
            };
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
            $scope.equation = $scope.model.equation;
        },
    };
});

SIREPO.app.directive('validVariableOrParam', function(appState, webconService) {
    return {
        restrict: 'A',
        require: 'ngModel',
        link: function(scope, element, attrs, ngModel) {

            // set dirty on load to catch invalid variables that might have been saved
            if(! ngModel.$valid) {
                ngModel.$setDirty();
            }

            function tokens() {
                return (ngModel.$viewValue || '').split(/\s*,\s*/);
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
                return tokens()
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

SIREPO.app.directive('fftReport', function(appState, panelState, plotting) {
    return {
        scope: {
            controller: '=parentController',
        },
        template: [
            '<div data-report-panel="parameter" data-request-priority="1" data-model-name="fftReport">',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {

            $scope.$on('fftReport.summaryData', function (e, data) {
                var str = '';
                data.freqs.forEach(function (wi, i) {
                    if(str == '') {
                        str = 'Found frequncies: ';
                    }
                    var w = wi[1];
                    str = str + w + 's-1';
                    str = str + (i < data.freqs.length - 1 ? ', ' : '');
                });
                $($element).find('.focus-hint').text(str);
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
            '<div data-ng-if="controller.isFitterConfigured()" data-report-panel="parameter" data-request-priority="1" data-model-name="fitReport">',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {

            function roundTo3Places(f) {
                return Math.round(f * 1000) / 1000;
            }

            $scope.$on('fitter.changed', function() {
                appState.saveChanges('fitReport');
            });
            $scope.$on('fitReport.summaryData', function (e, data) {
                var str = '';
                var pNames = (appState.models.fitter.parameters || '').split(/\s*,\s*/);
                var pVals = data.p_vals.map(roundTo3Places);
                var pErrs = data.p_errs.map(roundTo3Places);
                pNames.forEach(function (p, i) {
                    str = str + p + ' = ' + pVals[i] + ' ± ' + pErrs[i];
                    str = str + (i < pNames.length - 1 ? '; ' : '');
                });
                $($element).find('.focus-hint').text(str);
            });


        },
    };
});
