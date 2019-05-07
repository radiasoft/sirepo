'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="MiniFloat" class="col-sm-7">',
      '<input data-string-to-number="" data-ng-model="model[field]" data-min="info[4]" data-max="info[5]" class="form-control" style="text-align: right" data-lpignore="true" required />',
    '</div>',
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
    '<div data-ng-switch-when="TrimButton" class="col-sm-5">',
      '<div data-trim-button="" data-model-name="modelName" data-model="model" data-field="field"></div>',
    '</div>',
].join('');
SIREPO.lattice = {
    elementColor: {},
    elementPic: {
        drift: ['DRIF'],
        magnet: ['KICKER', 'QUAD'],
        watch: ['WATCH'],
    },
};

SIREPO.app.factory('webconService', function(appState, panelState) {
    var self = {};
    var parameterCache = {
        analysisParameter: null,
        parameterValues: null,
        optionalParameterValues: null,
    };

    self.addSubreport = function(parent, action) {
        var report = appState.clone(parent);
        var subreports = self.getSubreports();
        report.id = subreports.length
            ? (Math.max.apply(null, subreports) + 1)
            : 1;
        report.action = null;
        report.history.push(action);
        var name = 'analysisReport' + report.id;
        var fftName = 'fftReport' + report.id;
        appState.models[name] = report;
        appState.models[fftName] = {
            'analysisReport': name,
        };
        subreports.push(report.id);
        appState.saveChanges([name, fftName, 'hiddenReport']);
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
        if (! parameterCache.analysisParameters) {
            return null;
        }
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

    self.getSubreports = function() {
        // subreports are kept on a report which is never shown.
        // This avoids refreshing all reports when a subreport is added or removed.
        return appState.models.hiddenReport.subreports;
    };

    self.removeAllSubreports = function() {
        var subreports = self.getSubreports();
        while (subreports.length) {
            self.removeSubreport(subreports[0]);
        }
    };

    self.removeSubreport = function(id) {
        var subreports = self.getSubreports();
        subreports.splice(subreports.indexOf(id), 1);
        appState.removeModel('analysisReport' + id);
        appState.removeModel('fftReport' + id);
        panelState.clear('analysisReport' + id);
    };

    return self;
});

SIREPO.app.controller('AnalysisController', function (appState, panelState, requestSender, webconService, $scope) {
    var self = this;
    var currentFile = null;
    self.subplots = null;

    function buildSubplots() {
        if (! currentFile) {
            self.subplots = null;
            return;
        }
        self.subplots = [];
        webconService.getSubreports().forEach(function(id, idx) {
            var modelKey = 'analysisReport' + id;
            self.subplots.push({
                id: id,
                modelKey: modelKey,
                title: 'Analysis Subplot #' + (idx + 1),
                getData: function() {
                    return appState.models[modelKey];
                },
            });
        });
    }

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
                webconService.removeAllSubreports();
                appState.models.analysisReport.action = null;
                appState.saveChanges(['analysisReport', 'hiddenReport']);
            }
        });
        $scope.$on('modelChanged', function(e, name) {
            if (name.indexOf('analysisReport') >= 0) {
                // invalidate the corresponding fftReport
                appState.saveChanges('fftReport' + (appState.models[name].id || ''));
            }
        });
        $scope.$on('hiddenReport.changed', buildSubplots);
        buildSubplots();
    });
});

SIREPO.app.controller('ControlsController', function (appState, panelState, requestSender, webconService, $scope) {
    var self = this;

    //TODO(pjm): hard-coded beamline for now, using elegant format
    var elements = [
            {
                "_id": 8,
                "l": 0.1,
                "name": "drift",
                "type": "DRIF"
            },
            {
                "_id": 10,
                "hkick": 0,
                "name": "HV KICKER 1",
                "type": "KICKER",
                "vkick": 0
            },
            {
                "_id": 12,
                "hkick": 0,
                "name": "HV KICKER 2",
                "type": "KICKER",
                "vkick": 0
            },
            {
                "_id": 13,
                "hkick": 0,
                "name": "HV KICKER 3",
                "type": "KICKER",
                "vkick": 0
            },
            {
                "_id": 14,
                "hkick": 0,
                "name": "HV KICKER 4",
                "type": "KICKER",
                "vkick": 0
            },
            {
                "_id": 24,
                "k1": 5,
                "l": 0.05,
                "name": "F QUAD 1",
                "type": "QUAD",
            },
            {
                "_id": 25,
                "k1": -5,
                "l": 0.05,
                "name": "D QUAD 1",
                "type": "QUAD",
            },
            {
                "_id": 30,
                "k1": 5,
                "l": 0.05,
                "name": "F QUAD 2",
                "type": "QUAD",
            },
            {
                "_id": 31,
                "k1": -5,
                "l": 0.05,
                "name": "D QUAD 2",
                "type": "QUAD",
            },
            {
                "_id": 9,
                "name": "BPM 1",
                "type": "WATCH",
            },
            {
                "_id": 27,
                "name": "BPM 2",
                "type": "WATCH",
            },
            {
                "_id": 28,
                "name": "BPM 3",
                "type": "WATCH",
            },
            {
                "_id": 29,
                "name": "BPM 4",
                "type": "WATCH",
            }
    ];
    var beamline = [
        8, 8, 10, 8, 8, 9, 8, 8,
        8, 8, 12, 8, 8, 27, 8, 8,
        8, 24, 8, 8, 25, 8,
        8, 8, 13, 8, 8, 28, 8, 8,
        8, 8, 14, 8, 8, 29, 8, 8,
        8, 30, 8, 8, 31, 8,
    ];
    var layout = [
        [10, 24],
        [12, 25],
        [13, 30],
        [14, 31],
    ];

    function elementForId(id) {
        var model = null;
        elements.some(function(m) {
            if (m._id == id) {
                model = m;
                return true;
            }
        });
        if (! model) {
            throw 'model not found for id: ' + id;
        }
        return model;
    }

    function modelForElement(element, id) {
        var modelKey = element.type + id;
        if (! appState.models[modelKey]) {
            appState.models[modelKey] = element;
            appState.saveQuietly(modelKey);
        }
        return {
            id: id,
            modelKey: modelKey,
            title: element.name,
            viewName: element.type,
            getData: function() {
                return appState.models[modelKey];
            },
        };
    }

    appState.whenModelsLoaded($scope, function() {
        if (! appState.models.beamline) {
            appState.models.beamlines = [
                {
                    id: 1,
                    items: beamline,
                    name: 'beamline',
                },
            ];
            appState.models.elements = elements;
            appState.saveChanges(['beamlines', 'elements']);
        }
        self.watches = [];
        beamline.forEach(function(id) {
            var element = elementForId(id);
            if (element.type == 'WATCH') {
                self.watches.push(modelForElement(element, id));
            }
        });
        self.editorColumns = [];
        layout.forEach(function(col) {
            var res = [];
            col.forEach(function(id) {
                res.push(modelForElement(elementForId(id), id));
            });
            self.editorColumns.push(res);
        });
    });

    return self;
});

SIREPO.app.directive('analysisActions', function(appState, panelState, webconService) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            modelData: '=',
        },
        template: [
            //TODO(pjm): improve close button position, want it positioned relative to panel body, not full panel
            '<button data-ng-if="isSubreport()" data-ng-click="closeSubreport()" title="close" type="button" class="close" style="position: absolute; top: 55px; right: 25px">',
              '<span>&times;</span>',
            '</button>',
            '<div data-ng-show="! isLoading()" style="background: white; padding: 1ex; border-radius: 4px;">',
              '<div class="clearfix"></div>',
              '<div data-ng-repeat="view in viewNames track by $index" style="margin-top: -40px;">',
                '<div data-ng-if="isActiveView(view)" style="margin-top:3ex;">',
                  '<div data-advanced-editor-pane="" data-model-data="modelData" data-view-name="view" data-field-def="basic" data-want-buttons="{{ wantButtons() }}"></div>',
                '</div>',
              '</div>',
              '<div class="clearfix"></div>',
              '<div data-ng-show="showFFT()">',
                '<div data-fft-report="" data-model-data="modelData" style="margin-top: 5px;"></div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {
            var analysisReport;
            var isFirstRefresh = true;
            var modelKey = $scope.modelData
                ? $scope.modelData.modelKey
                : $scope.modelName;
            var viewForEnum = {
                '': 'analysisNone',
                'cluster': 'analysisCluster',
                'fft': 'analysisFFT',
                'fit': 'analysisFit',
                'trim': 'analysisTrim',
            };
            $scope.viewNames = Object.keys(viewForEnum).map(function(k) {
                return viewForEnum[k];
            });

            function addSubreport(clusterIndex) {
                var action = {
                    clusterIndex: clusterIndex,
                };
                var parent = $scope.model();
                ['action', 'clusterMethod', 'clusterCount', 'clusterFields', 'clusterScaleMin', 'clusterScaleMax', 'clusterRandomSeed', 'clusterKmeansInit', 'clusterDbscanEps'].forEach(function(f) {
                    action[f] = parent[f];
                });
                webconService.addSubreport(parent, action);
            }

            function initAnalysisReport(reportScope) {
                analysisReport = reportScope;
                var oldLoad = analysisReport.load;
                analysisReport.load = function(json) {
                    isFirstRefresh = true;
                    $('.scatter-point').popover('hide');
                    oldLoad(json);
                };
                var oldRefresh = analysisReport.refresh;
                analysisReport.refresh = function() {
                    if (isFirstRefresh) {
                        isFirstRefresh = false;
                        setupAnalysisReport();
                        // resize will call refresh again
                        analysisReport.resize();
                        return;
                    }
                    oldRefresh();
                    processTrimRange();
                };
            }

            function processClusterMethod() {
                //TODO(pjm): this does not work correctly for subreports
                panelState.showField($scope.modelName, 'clusterCount', $scope.model().clusterMethod != 'dbscan');
            }

            function processTrimRange() {
                var model = $scope.model();
                if (model && model.action == 'trim') {
                    model.trimField = model.x;
                    var xDomain = analysisReport.axes.x.scale.domain();
                    model.trimMin = xDomain[0];
                    model.trimMax = xDomain[1];
                }
            }

            function roundTo3Places(f) {
                return Math.round(f * 1000) / 1000;
            }

            function setupAnalysisReport() {
                analysisReport.select('svg').selectAll('.overlay').classed('disabled-overlay', true);
                analysisReport.zoomContainer = '.plot-viewport';
                if ($scope.model().action == 'cluster'
                    && appState.applicationState()[modelKey].action == 'cluster') {
                    var viewport = analysisReport.select('.plot-viewport');
                    viewport.selectAll('.scatter-point').on('click', function(d, idx) {
                        var clusterIndex = analysisReport.clusterInfo.group[idx];

                        function buttonHandler() {
                            $('.scatter-point').popover('hide');
                            $scope.$apply(function() {
                                addSubreport(clusterIndex);
                            });
                        }

                        $(this).popover({
                            trigger: 'manual',
                            html: true,
                            placement: 'bottom',
                            container: 'body',
                            title: 'Cluster: ' + (clusterIndex + 1),
                            content: '<div><button class="btn btn-default webcon-popover">Open in New Plot</button></div>',
                        }).on('hide.bs.popover', function() {
                            $(document).off('click', buttonHandler);
                        });
                        $('.scatter-point').not($(this)).popover('hide');
                        $(this).popover('toggle');
                        $(document).on('click', '.webcon-popover', buttonHandler);
                    });
                }
            }

            $scope.closeSubreport = function() {
                webconService.removeSubreport($scope.model().id);
                appState.saveChanges('hiddenReport');
            };

            $scope.isActiveView = function(view) {
                var model = $scope.model();
                if (model) {
                    return viewForEnum[model.action || ''] == view;
                }
                return false;
            };

            $scope.isLoading = function() {
                return panelState.isLoading(modelKey);
            };

            $scope.isSubreport = function() {
                return modelKey != $scope.modelName;
            };

            $scope.model = function() {
                if (appState.isLoaded()) {
                    return appState.models[modelKey];
                }
                return null;
            };

            $scope.showFFT = function() {
                if (appState.isLoaded()) {
                    return $scope.model().action == 'fft'
                        && appState.applicationState()[modelKey].action == 'fft';
                }
                return false;
            };

            $scope.wantButtons = function() {
                if (appState.isLoaded()) {
                    var action = $scope.model().action;
                    if (action == 'trim') {
                        return '';
                    }
                    return '1';
                }
                return '';
            };

            appState.whenModelsLoaded($scope, function() {
                $scope.$on(modelKey + '.summaryData', function (e, data) {
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
                appState.watchModelFields($scope, [modelKey + '.action'], processTrimRange);
                appState.watchModelFields($scope, [modelKey + '.clusterMethod', modelKey + '.action'], processClusterMethod);
                processClusterMethod();
            });

            // hook up listener on report content to get the plot events
            $scope.$parent.$parent.$parent.$on('sr-plotLinked', function(event) {
                var reportScope = event.targetScope;
                if (reportScope.modelName.indexOf('analysisReport') >= 0) {
                    initAnalysisReport(reportScope);
                }
                else if (reportScope.modelName.indexOf('fftReport') >= 0) {
                    // it may be useful to have the fftReport scope available
                    //fftReport = reportScope;
                }
            });

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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'controls\')}"><a href data-ng-click="nav.openSection(\'controls\')"><span class="glyphicon glyphicon-dashboard"></span> Controls</a></li>',
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


SIREPO.app.directive('clusterFields', function(appState, webconService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: [
            '<div style="margin: -3px 0 5px 0; min-height: 34px; max-height: 13.4em; overflow-y: auto; border: 1px solid #ccc; border-radius: 4px">',
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

SIREPO.app.directive('fftReport', function(appState) {
    return {
        scope: {
            modelData: '=',
        },
        template: [
            '<div data-report-content="parameter" data-model-key="{{ modelKey }}"></div>',
        ].join(''),
        controller: function($scope, $element) {
            $scope.modelKey = 'fftReport';
            if ($scope.modelData) {
                $scope.modelKey += appState.models[$scope.modelData.modelKey].id;
            }

            $scope.$on($scope.modelKey + '.summaryData', function (e, data) {
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

SIREPO.app.directive('trimButton', function(appState, webconService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            modelName: '=',
        },
        template: [
            '<div class="text-center">',
              '<button class="btn btn-default" data-ng-click="trimPlot()">Open in New Plot</button>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.trimPlot = function() {
                var action = {};
                ['action', 'trimField', 'trimMin', 'trimMax'].forEach(function(f) {
                    action[f] = $scope.model[f];
                });
                webconService.addSubreport($scope.model, action);
                appState.cancelChanges($scope.modelName + ($scope.model.id || ''));
            };
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
                if(scope.model.fitEquation && scope.model.fitEquation.indexOf(p) < 0) {
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

SIREPO.app.directive('webconLattice', function(utilities, $window) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div class="col-sm-10 col-sm-offset-1 col-md-8 col-md-offset-2 col-xl-6 col-xl-offset-3">',
              '<div class="webcon-lattice">',
                '<div id="sr-lattice" data-lattice="" class="sr-plot" data-model-name="beamlines" data-flatten="1"></div>',
                '<div style="margin-bottom: 1em">TODO: beamline labels will go in these rows, aligned under elements</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var axis, latticeScope;

            $scope.windowResize = utilities.debounce(function() {
                if (axis) {
                    axis.scale.range([0, $('.webcon-lattice').parent().width()]);
                    latticeScope.updateFixedAxis(axis, 0);
                    $scope.$applyAsync();
                }
            }, 250);

            $scope.$on('$destroy', function() {
                $($window).off('resize', $scope.windowResize);
            });

            $scope.$on('sr-latticeLinked', function(event) {
                latticeScope = event.targetScope;
                event.stopPropagation();
                axis = {
                    scale: d3.scale.linear(),
                    //TODO(pjm): 3.4 is the hard-code example beamline length
                    domain: [0, 3.4],
                };
                axis.scale.domain(axis.domain);
                $scope.windowResize();
            });

            $($window).resize($scope.windowResize);
        },
    };
});
