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
    '<div data-ng-switch-when="ClusterFields" class="col-sm-7">',
      '<div data-cluster-fields="" data-model="model" data-field="field"></div>',
    '</div>',
    '<div data-ng-switch-when="PlotActionButtons" class="col-sm-12">',
      '<div data-plot-action-buttons="" data-model="model" data-field="field"></div>',
    '</div>',
].join('');

SIREPO.app.factory('webconService', function(appState) {
    var self = {};
    var parameterCache = {
        analysisParameter: null,
        parameterValues: null,
        optionalParameterValues: null,
    };

    self.buildParameterList = function(includeOptional) {
        if (! appState.isLoaded()) {
            return null;
        }
        var name = includeOptional ? 'optionalParameterValues' : 'parameterValues';
        // use cached list unless the columnInfo changes
        if (parameterCache.analysisParameters == appState.models.analysisData.columnInfo) {
            if (parameterCache[name]) {
                return parameterCache[name];
            }
        }
        parameterCache.analysisParameters = appState.models.analysisData.columnInfo;
        var parameterValues = [];
        var visited = {};
        parameterCache.analysisParameters.names.forEach(function(name, idx) {
            // skip duplicate columns
            if (! visited[name]) {
                parameterValues.push(['' + idx, name]);
                visited[name] = true;
            }
        });
        parameterValues.sort(function(a, b) {
            return a[1].localeCompare(b[1]);
        });
        if (includeOptional) {
            parameterValues.unshift(['none', 'None']);
        }
        parameterCache[name] = parameterValues;
        return parameterValues;
    };
    return self;
});

SIREPO.app.controller('AnalysisController', function (appState, panelState, requestSender, $scope) {
    var self = this;
    var currentFile = null;

    function updateAnalysisParameters() {
        requestSender.getApplicationData(
            {
                method: 'column_info',
                analysisData: appState.models.analysisData,
            },
            function(data) {
                if (appState.isLoaded() && data.columnInfo) {
                    appState.models.analysisData.columnInfo = data.columnInfo;
                    appState.saveChanges('analysisData');
                }
            });
    }

    self.hasFile = function() {
        return appState.isLoaded() && appState.applicationState().analysisData.file;
    };

    appState.whenModelsLoaded($scope, function() {
        currentFile = appState.models.analysisData.file;
        if (currentFile && ! appState.models.analysisData.columnInfo) {
            updateAnalysisParameters();
        }
        $scope.$on('analysisData.changed', function() {
            var analysisData = appState.models.analysisData;
            if (currentFile != analysisData.file) {
                currentFile = analysisData.file;
                updateAnalysisParameters();
            }
        });
    });
});

SIREPO.app.directive('analysisActions', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: [
            '<div data-ng-show="! isLoading()" style="background: white; padding: 1ex; border-radius: 4px; margin-top: -40px">',
              '<div class="clearfix"></div>',
              '<div data-ng-repeat="view in viewNames track by $index">',
                '<div data-ng-if="showView(view)" style="margin-top:3ex;">',
                  '<div data-advanced-editor-pane="" data-view-name="view" data-field-def="basic" data-want-buttons="{{ wantButtons() }}"></div>',
                '</div>',
              '</div>',
              '<div class="clearfix"></div>',
              '<div data-ng-if="showFFT()">',
                '<div data-fft-report=""></div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {
            var viewForEnum = {
                '': 'analysisNone',
                'cluster': 'analysisCluster',
                'fft': 'analysisFFT',
                'fit': 'analysisFit',
                'trim': 'analysisTrim',
            };

            $scope.viewNames = [
                'analysisNone', 'analysisCluster', 'analysisFFT', 'analysisFit', 'analysisTrim',
            ];

            function roundTo3Places(f) {
                return Math.round(f * 1000) / 1000;
            }

            $scope.isLoading = function() {
                return panelState.isLoading($scope.modelName);
            };

            $scope.model = function() {
                if (appState.isLoaded()) {
                    return appState.models[$scope.modelName];
                }
                return null;
            };

            $scope.showFFT = function() {
                if (appState.isLoaded()) {
                    return $scope.model().action == 'fft';
                }
                return false;
            };

            $scope.showView = function(view) {
                var model = $scope.model();
                if (model) {
                    return viewForEnum[model.action || ''] == view;
                }
                return false;
            };

            $scope.wantButtons = function() {
                if (appState.isLoaded() && $scope.model().action != 'fft') {
                    return  '1';
                }
                return '';
            };

            appState.whenModelsLoaded($scope, function() {
                $scope.$on('analysisReport.summaryData', function (e, data) {
                    var str = '';
                    if (data.p_vals) {
                        var pNames = ($scope.model().fitParameters || '').split(/\s*,\s*/);
                        var pVals = data.p_vals.map(roundTo3Places);
                        var pErrs = data.p_errs.map(roundTo3Places);
                        pNames.forEach(function (p, i) {
                            str = str + p + ' = ' + pVals[i] + ' ± ' + pErrs[i];
                            str = str + (i < pNames.length - 1 ? '; ' : '');
                        });
                    }
                    $($element).closest('.panel-body').find('.focus-hint').text(str);
                });
            });
        },
    };
});

SIREPO.app.directive('plotActionButtons', function(appState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: [
            '<div class="text-center">',
            '<div class="btn-group">',
              '<button class="btn sr-enum-button" data-ng-repeat="item in enumValues" data-ng-click="model[field] = item[0]" data-ng-class="{\'active btn-primary\': isSelectedValue(item[0]), \'btn-default\': ! isSelectedValue(item[0])}">{{ item[1] }}</button>',
            '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.enumValues = SIREPO.APP_SCHEMA.enum.PlotAction;

            $scope.isSelectedValue = function(value) {
                if ($scope.model && $scope.field) {
                    return $scope.model[$scope.field] == value;
                }
                return false;
            };
        },
    };
});

SIREPO.app.directive('clusterFields', function(appState, webconService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: [
            '<div style="margin: 5px 0; min-height: 34px; max-height: 20em; overflow-y: auto; border: 1px solid #ccc; border-radius: 4px">',
              '<table class="table table-condensed table-hover" style="margin:0">',
                '<tbody>',
                  '<tr data-ng-repeat="item in itemList() track by item.index" data-ng-click="toggleItem(item)">',
                    '<td>{{ item.name }}</td>',
                    '<td><input type="checkbox" data-ng-checked="isSelected(item)"></td>',
                  '</tr>',
                '</tbody>',
              '</table>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var itemList, paramList;

            $scope.isSelected = function(item) {
                var v = $scope.model[$scope.field] || [];
                return v[item.index];
            };

            $scope.itemList = function() {
                var params = webconService.buildParameterList();
                if (paramList != params) {
                    paramList = params;
                    itemList = [];
                    paramList.forEach(function(param) {
                        itemList.push({
                            name: param[1],
                            index: parseInt(param[0]),
                        });
                    });
                }
                return itemList;
            };

            $scope.toggleItem = function(item) {
                var v = $scope.model[$scope.field] || [];
                v[item.index] = ! v[item.index];
                $scope.model[$scope.field] = v;
            };
        },
    };
});

SIREPO.app.directive('analysisParameter', function(appState, webconService) {
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
            $scope.parameterValues = function() {
                return webconService.buildParameterList($scope.isOptional);
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
            $scope.equation = $scope.model.fitEquation;
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
                if(! scope.isVariable && p === scope.model.fitVariable) {
                    scope.warningText = p + ' is an independent variable';
                    return false;
                }
                if(scope.model.fitEquation.indexOf(p) < 0) {
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

SIREPO.app.directive('fftReport', function() {
    return {
        scope: {
        },
        template: [
            '<div data-report-content="parameter" data-model-key="fftReport"></div>',
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
