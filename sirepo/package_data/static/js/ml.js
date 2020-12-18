'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.PLOTTING_COLOR_MAP = 'blues';
    SIREPO.SINGLE_FRAME_ANIMATION = ['epochAnimation'];
    SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL = true;
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="AnalysisParameter" class="col-sm-5">',
          '<div data-analysis-parameter="" data-model="model" data-field="field"></div>',
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
        '<div data-ng-switch-when="XColumn" data-field-class="fieldClass">',
          '<div data-x-column="" data-model-name="modelName" data-model="model" data-field="field"></div>',
        '</div>',
    ].join('');
    SIREPO.appReportTypes = [
        '<div data-ng-switch-when="classificationMetrics" data-table-panel="" data-model-name="{{ modelKey }}" class="sr-plot"></div>',
        '<div data-ng-switch-when="confusionMatrix" data-table-panel="" data-model-name="{{ modelKey }}" class="sr-plot"></div>',
    ].join('');
});

SIREPO.app.factory('mlService', function(appState, panelState) {
    var self = {};
    var parameterCache = {
        analysisParameters: null,
        parameterValues: null,
        optionalParameterValues: null,
    };

    self.addSubreport = function(parent, action) {
        let report = appState.clone(parent);
        let subreports = self.getSubreports();
        report.id = subreports.length
            ? (Math.max.apply(null, subreports) + 1)
            : 1;
        report.action = null;
        report.history.push(action);
        let name = 'analysisReport' + report.id;
        let fftName = 'fftReport' + report.id;
        appState.models[name] = report;
        appState.models[fftName] = {
            'analysisReport': name,
        };
        subreports.push(report.id);
        appState.saveChanges([name, fftName, 'hiddenReport']);
    };

    self.appModeIn = function(modes) {
        if(! appState.isLoaded()) {
            return;
        }
        return modes.includes(appState.applicationState().dataFile.appMode);
    };

    self.buildParameterList = function(includeOptional) {
        if (! appState.isLoaded()) {
            return null;
        }
        var name = includeOptional ? 'optionalParameterValues' : 'parameterValues';
        // use cached list unless the columnInfo changes
        if (parameterCache.analysisParameters == appState.models.columnInfo) {
            if (parameterCache[name]) {
                return parameterCache[name];
            }
        }
        parameterCache.analysisParameters = appState.models.columnInfo;
        if (! parameterCache.analysisParameters) {
            return null;
        }
        var parameterValues = [];
        var visited = {};
        (parameterCache.analysisParameters.header || []).forEach(function(name, idx) {
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

    self.columnReportName = function(idx) {
        return 'fileColumnReport' + idx;
    };

    self.computeModel = function(analysisModel) {
        if ([
            'dtClassifierClassificationMetricsAnimation',
            'dtClassifierConfusionMatrixAnimation',
            'knnClassificationMetricsAnimation',
            'knnConfusionMatrixAnimation',
            'knnErrorRateAnimation',
            'linearSvcErrorRateAnimation',
            'linearSvcConfusionMatrixAnimation',
            'logisticRegressionClassificationMetricsAnimation',
            'logisticRegressionConfusionMatrixAnimation',
            'logisticRegressionErrorRateAnimation'
        ].includes(analysisModel)) {
            return 'classificationAnimation';
        }
        return 'animation';
    };

    self.getSubreports = function() {
        // subreports are kept on a report which is never shown.
        // This avoids refreshing all reports when a subreport is added or removed.
        return appState.models.hiddenReport.subreports;
    };

    self.isAnalysis = function() {
        return appState.isLoaded() && appState.applicationState().dataFile.appMode == 'analysis';
    };

    self.partitionReportName = function(idx) {
        return 'partitionColumnReport' + idx;
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

    self.reportInfo = function(modelKey, title, idx) {
        return {
            columnNumber: idx,
            title: title,
            data: {
                modelKey: modelKey,
                getData: function() {
                    return appState.models[modelKey];
                },
            },
        };
    };

    self.tokenizeEquation = function(eq) {
        return (eq || '').split(/[-+*/^|%().0-9\s]/)
            .filter(function (t) {
                return t.length > 0 &&
                    SIREPO.APP_SCHEMA.constants.allowedEquationOps.indexOf(t) < 0;
        });
    };

    self.tokenizeParams = function(val) {
        return (val || '').split(/\s*,\s*/).filter(function (t) {
            return t.length > 0;
        });
    };

    appState.setAppService(self);
    return self;
});

SIREPO.app.directive('appFooter', function(mlService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-common-footer="nav"></div>',
            '<div data-import-dialog=""></div>',
        ].join(''),
    };
});

SIREPO.app.directive('appHeader', function(appState, mlService) {
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'data\')}"><a href data-ng-click="nav.openSection(\'data\')"><span class="glyphicon glyphicon-picture"></span> Data Source</a></li>',
                  '<li class="sim-section" data-ng-if="hasFile() && isAnalysis()" data-ng-class="{active: nav.isActive(\'analysis\')}"><a href data-ng-click="nav.openSection(\'analysis\')"><span class="glyphicon glyphicon-tasks"></span> Analysis</a></li>',
                  '<li class="sim-section" data-ng-if="hasInputsAndOutputs() && ! isAnalysis()" data-ng-class="{active: nav.isActive(\'partition\')}"><a href data-ng-click="nav.openSection(\'partition\')"><span class="glyphicon glyphicon-scissors"></span> Partition</a></li>',
                  '<li class="sim-section" data-ng-if="hasInputsAndOutputs() && appModeIn([\'regression\'])" data-ng-class="{active: nav.isActive(\'regression\')}"><a href data-ng-click="nav.openSection(\'regression\')"><span class="glyphicon glyphicon-qrcode"></span> Regression</a></li>',
                  '<li class="sim-section" data-ng-if="hasInputsAndOutputs() && appModeIn([\'classification\'])" data-ng-class="{active: nav.isActive(\'classification\')}"><a href data-ng-click="nav.openSection(\'classification\')"><span class="glyphicon glyphicon-tag"></span> Classification</a></li>',
                '</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
               //  '<div>App-specific setting item</div>',
              '</app-settings>',
              '<app-header-right-sim-list>',
                '<ul class="nav navbar-nav sr-navbar-right">',
                  '<li><a href data-ng-click="nav.showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>',
                '</ul>',
              '</app-header-right-sim-list>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.appModeIn = mlService.appModeIn;
            $scope.hasFile = function() {
                return appState.isLoaded() && appState.applicationState().dataFile.file;
            };
            $scope.hasInputsAndOutputs = function() {
                if ($scope.hasFile() && appState.applicationState().columnInfo) {
                    var inputOutput = appState.applicationState().columnInfo.inputOutput;
                    return inputOutput && inputOutput.indexOf('input') >= 0
                        && inputOutput.indexOf('output') >= 0;
                }
                return false;
            };
            $scope.isAnalysis = mlService.isAnalysis;
        },
    };
});

SIREPO.app.controller('AnalysisController', function (appState, mlService, panelState, requestSender, $scope) {
    var self = this;
    var currentFile = null;
    self.subplots = null;

    function buildSubplots() {
        if (! currentFile) {
            self.subplots = null;
            return;
        }
        self.subplots = [];
        (mlService.getSubreports() || []).forEach(function(id, idx) {
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
                dataFile: appState.models.dataFile,
            },
            function(data) {
                if (appState.isLoaded() && data.columnInfo) {
                    appState.models.columnInfo = data.columnInfo;
                    appState.saveChanges('columnInfo');
                }
            });
    }

    self.hasFile = function() {
        return appState.isLoaded() && appState.applicationState().dataFile.file;
    };

    appState.whenModelsLoaded($scope, function() {
        currentFile = appState.models.dataFile.file;
        if (currentFile && ! appState.models.columnInfo) {
            updateAnalysisParameters();
        }
        $scope.$on('dataFile.changed', function() {
            let dataFile = appState.models.dataFile;
            if (currentFile != dataFile.file) {
                currentFile = dataFile.file;
                if (currentFile) {
                    updateAnalysisParameters();
                    mlService.removeAllSubreports();
                    appState.models.analysisReport.action = null;
                    appState.saveChanges(['analysisReport', 'hiddenReport']);
                }
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

SIREPO.app.controller('DataController', function (appState, panelState, requestSender, $scope) {
    var self = this;

    function computeColumnInfo() {
        var dataFile = appState.models.dataFile;
        if (! dataFile.file) {
            appState.models.columnReports = [];
            appState.saveChanges('columnReports');
            return;
        }
        if (dataFile.file == dataFile.oldFile) {
            return;
        }
        dataFile.oldFile = dataFile.file;
        appState.saveQuietly('dataFile');
        requestSender.getApplicationData({
            method: 'compute_column_info',
            dataFile: dataFile,
        }, function(data) {
            appState.models.columnInfo = data;
            computeDefaultPartition();
            appState.models.columnReports = [];
            appState.saveChanges(['columnInfo', 'columnReports', 'partition']);
        });
    }

    function computeDefaultPartition() {
        var size = appState.models.columnInfo.rowCount;
        var partition = appState.models.partition;
        if (! partition.cutoff0 || ! partition.cutoff1
            || partition.cutoff0 > size
            || partition.cutoff1 > size) {
            partition.cutoff0 = parseInt(0.125 * size);
            partition.cutoff1 = parseInt((1 - 0.125) * size);
        }
    }

    function dataFileChanged() {
        computeColumnInfo();
        const dataFile = appState.models.dataFile;
        const partition = appState.models.partition;
        if (dataFile.appMode == 'regression'
            && partition.training + partition.testing >= 100) {
            ['training', 'testing', 'validation'].forEach(function(f) {
                delete partition[f];
            });
            appState.setModelDefaults(partition, 'partition');
        }
        else if (dataFile.appMode == 'classification') {
            if (partition.training + partition.testing < 100) {
                partition.testing = 100 - partition.training;
            }
        }
        appState.saveQuietly('partition');
    }

    self.hasDataFile = function() {
        return appState.isLoaded() && appState.applicationState().dataFile.file;
    };

    appState.whenModelsLoaded($scope, function() {
        $scope.$on('dataFile.changed', dataFileChanged);
        //TODO(pjm): enable when analysis tab is completed
        //panelState.showEnum('dataFile', 'appMode', 'analysis', false);
    });
});

SIREPO.app.controller('ClassificationController', function(appState, frameCache, panelState, persistentSimulation, $scope) {
    let self = this;
    let errorMessage = '';
    self.framesForClassifier = null;
    self.simComputeModel = 'classificationAnimation'; // TODO(e-carlin): try ending in compute and see what happens
    self.simScope = $scope;

    function showClassifierSettings() {
        ['min', 'max'].forEach((f) => panelState.showField(
            'knnClassification',
            `k${f}`,
            appState.models.classificationAnimation.classifier === 'knn'
        ));
        ['linearSvc', 'logisticRegression'].forEach((c) => {
            [
                'toleranceMax',
                'toleranceMin',
                'totalNumValues'
            ].forEach((f) => panelState.showField(
                `${c}Classification`,
                f,
                appState.models.classificationAnimation.classifier === c
            ));
        });
    }

    self.hasFrames = function() {
        if (appState.isLoaded()
            && self.framesForClassifier == appState.applicationState().classificationAnimation.classifier) {
            return frameCache.hasFrames();
        }
        return false;
    };

    self.simHandleStatus = function (data) {
        errorMessage = data.error;
        self.framesForClassifier = data.framesForClassifier;
        if (data.frameCount) {
            frameCache.setFrameCount(data.frameCount);
        }
    };

    self.simCompletionState = function(statusText) {
        return '';
    };

    self.simState = persistentSimulation.initSimulationState(self);

    self.simState.errorMessage = function() {
        return errorMessage;
    };

    appState.whenModelsLoaded($scope, function() {
        showClassifierSettings();
        appState.watchModelFields(
            $scope,
            ['classificationAnimation.classifier'],
            showClassifierSettings
        );
    });
});

SIREPO.app.controller('RegressionController', function (appState, frameCache, mlService, panelState, persistentSimulation, $scope) {
    var self = this;
    self.simScope = $scope;
    self.simAnalysisModel = 'fitAnimation';
    var errorMessage = '';

    function columnTypeCount(type) {
        var res = 0;
        appState.models.columnInfo.inputOutput.forEach(function(col) {
            if (col == type) {
                res++;
            }
        });
        return res;
    }

    function addFitReports() {
        var res = [];
        for (var i = 0; i < columnTypeCount('output'); i++) {
            var modelKey = 'fitAnimation' + i;
            if (! appState.models[modelKey]) {
                appState.models[modelKey] = {
                    columnNumber: i,
                };
                appState.saveQuietly(modelKey);
            }
            res.push(mlService.reportInfo(modelKey, 'Fit ' + (i + 1), i));
            if (SIREPO.SINGLE_FRAME_ANIMATION.indexOf(modelKey) < 0) {
                SIREPO.SINGLE_FRAME_ANIMATION.push(modelKey);
            }
            frameCache.setFrameCount(1, modelKey);
            if (i % 4 == 3) {
                res[res.length - 1].break = true;
            }
        }
        res[res.length - 1].break = true;
        return res;
    }

    self.simHandleStatus = function (data) {
        errorMessage = data.error;
        self.reports = null;
        if ('percentComplete' in data && ! data.error) {
            if (data.percentComplete === 100 && ! self.simState.isProcessing()) {
                self.reports = addFitReports();
            }
        }
        frameCache.setFrameCount(data.frameCount || 0);
    };

    self.hasModel = function() {
        if (appState.isLoaded()) {
            return appState.applicationState().neuralNet.layers.length;
        }
        return false;
    };

    self.startSimulation = function() {
        self.simState.saveAndRunSimulation('simulation');
    };

    self.hasFrames = frameCache.hasFrames;

    self.simState = persistentSimulation.initSimulationState(self);

    self.simState.errorMessage = function() {
        return errorMessage;
    };

    self.simState.runningMessage = function() {
        if (appState.isLoaded() && self.simState.getFrameCount()) {
            return 'Completed epoch: ' + self.simState.getFrameCount();
        }
        return 'Simulation running';
    };
});

SIREPO.app.directive('analysisActions', function(appState, panelState, mlService) {
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
                mlService.addSubreport(parent, action);
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
                mlService.removeSubreport($scope.model().id);
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

SIREPO.app.directive('analysisParameter', function(appState, mlService) {
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
                return mlService.buildParameterList($scope.isOptional);
            };
        },
    };
});

SIREPO.app.directive('columnReports', function(appState, mlService) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div data-ng-repeat="report in reports track by report.columnNumber">',
              '<div class="col-sm-3 col-xl-2">',
                '<div class="sr-height-panel" data-report-panel="parameter" data-model-name="fileColumnReport" data-model-data="report.data" data-panel-title="{{ report.title }}" data-ng-style="reportStyle">',
                  '<button data-ng-click="closeReport(report.columnNumber)" title="close" type="button" class="close" style="position: absolute; top: 55px; right: 25px">',
                    '<span>&times;</span>',
                  '</button>',
                  '<div>{{ computeHeight() }}</div>',
                  '<form class="form-horizontal">',
                    '<div class="form-group form-group-sm" data-model-field="\'x\'" data-model-name="\'fileColumnReport\'" data-model-data="report.data" data-label-size="4" data-field-size="8"></div>',
                  '</form>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {
            $scope.reportStyle = {
                'min-height': 0,
            };

            $scope.computeHeight = function() {
                var maxHeight = 0;
                $($element).find('.sr-height-panel').each(function(f, el) {
                    var h = $(el).children().first().height();
                    if (h > maxHeight) {
                        maxHeight = h;
                    }
                });
                //TODO(pjm): 20 is the margin bottom. needs improvements
                $scope.reportStyle['min-height'] = (maxHeight + 20) + 'px';
            };

            function setReports() {
                $scope.reports = [];
                appState.models.columnReports.forEach(function(idx) {
                    var modelKey = mlService.columnReportName(idx);
                    $scope.reports.push(mlService.reportInfo(modelKey, 'Column ' + (idx + 1), idx));
                });
            }

            $scope.closeReport = function(closeIdx) {
                var reports = [];
                appState.models.columnReports.forEach(function(idx) {
                    if (idx != closeIdx) {
                        reports.push(idx);
                    }
                });
                appState.models.columnReports = reports;
                appState.saveChanges('columnReports');
            };

            appState.whenModelsLoaded($scope, function() {
                setReports();
                $scope.$on('columnReports.changed', setReports);
            });
        },
    };
});

SIREPO.app.directive('xColumn', function(appState, mlService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: [
            '<div class="col-sm-8">',
            '<select class="form-control" data-ng-model="model[field]" data-ng-change="columnChanged()" data-ng-options="item as header(item) for item in getItems()"></select>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
            $scope.columnChanged = function() {
                appState.saveChanges(mlService.columnReportName($scope.model.columnNumber));
            };
            $scope.header = function(item) {
                if (appState.isLoaded()) {
                    if (item == -1) {
                        return 'occurrence';
                    }
                    return appState.models.columnInfo.header[item];
                }
            };
            $scope.getItems = function() {
                if (appState.isLoaded()) {
                    if (! $scope.items) {
                        $scope.items = [-1];
                        var info = appState.models.columnInfo;
                        info.header.forEach(function(h, idx) {
                            if (! info.colsWithNonUniqueValues[h]) {
                                $scope.items.push(idx);
                            }
                        });
                    }
                }
                return $scope.items;
            };
            $scope.$on('modelChanged', function() {
                $scope.items = null;
            });
        },
    };
});

SIREPO.app.directive('columnSelector', function(appState, mlService, panelState) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<form name="form">',
              '<table style="width: 100%; table-layout: fixed; margin-bottom: 10px" class="table table-hover">',
                '<colgroup>',
                  '<col style="width: 3em">',
                  '<col style="width: 100%">',
                  '<col style="width: 6em">',
                  '<col style="width: 6em">',
                  '<col style="width: 6em">',
                '</colgroup>',
                '<thead>',
                  '<tr>',
                    '<th> </th>',
                    '<th>Column Name</th>',
                    '<th data-ng-show="! isAnalysis" class="text-center">Input</th>',
                    '<th data-ng-show="! isAnalysis" class="text-center">Output</th>',
                    '<th></th>',
                  '</tr>',
                '</thead>',
                '<tbody>',
                  '<tr data-ng-repeat="col in cols track by col">',
                    '<td class="form-group form-group-sm"><p class="form-control-static">{{ col + 1 }}</p></td>',
                    '<td class="form-group form-group-sm">',
                      '<input data-ng-model="model.header[col]" class="form-control" data-lpignore="true" required />',
                    '</td>',

                    '<td data-ng-show="! isAnalysis" class="text-center">',
                      '<input data-ng-model="model.inputOutput[col]" class="sr-checkbox" data-ng-true-value="\'input\'" data-ng-false-value="\'none\'" type="checkbox" />',
                    '</td>',
                    '<td data-ng-show="! isAnalysis" class="text-center">',
                      '<input data-ng-model="model.inputOutput[col]" class="sr-checkbox" data-ng-true-value="\'output\'" data-ng-false-value="\'none\'" type="checkbox" />',
                    '</td>',
                    '<td data-ng-if="! isAnalysis">',
                      '<a class="media-middle" href data-ng-click="togglePlot(col)">{{ showOrHideText(col) }}</a>',
                    '</td>',
                  '</tr>',
                '</tbody>',
              '</table>',
              '<div class="col-sm-12 text-center" data-buttons="" data-model-name="modelName" data-fields="fields"></div>',
            '</form>',
        ].join(''),
        controller: function($scope) {
            $scope.modelName = 'columnInfo';
            $scope.fields = ['header', 'inputOutput'];
            $scope.isAnalysis = false;

            function setModel() {
                $scope.model = appState.models.columnInfo;
                $scope.cols = [];
                const c = appState.models.columnInfo;
                if (! c.header) {
                    return;
                }
                for (let i = 0; i < c.header.length; i++) {
                    if (c.colsWithNonUniqueValues.hasOwnProperty(c.header[i])) {
                        continue;
                    }
                    $scope.cols.push(i);
                    const m = mlService.columnReportName(i);
                    if (! appState.models[m]) {
                        appState.models[m] = appState.setModelDefaults({
                            columnNumber: i,
                        }, 'fileColumnReport');
                        appState.saveQuietly(m);
                    }
                }
            }

            function updateIsAnalysis() {
                $scope.isAnalysis = mlService.isAnalysis();
            }

            $scope.showOrHideText = function(idx) {
                return appState.models.columnReports.indexOf(idx) >= 0
                    ? 'hide' : 'show';
            };

            $scope.togglePlot = function(idx) {
                var pos = appState.models.columnReports.indexOf(idx);
                if (pos < 0) {
                    appState.models.columnReports.unshift(idx);
                    // show the report if it was previously hidden
                    var modelKey = mlService.columnReportName(idx);
                    if (panelState.isHidden(modelKey)) {
                        panelState.toggleHidden(modelKey);
                    }
                }
                else {
                    appState.models.columnReports.splice(pos, 1);
                }
                appState.saveChanges('columnReports');
            };

            appState.whenModelsLoaded($scope, function() {
                setModel();
                updateIsAnalysis();
                $scope.$on('columnInfo.changed', setModel);
                $scope.$on('cancelChanges', function(evt, name) {
                    if (name == 'columnInfo') {
                        setModel();
                    }
                });
                $scope.$on('dataFile.changed', updateIsAnalysis);
            });

        },
    };
});

SIREPO.app.directive('equation', function(appState, mlService, $timeout) {
    return {
        scope: {
            model: '=',
            field: '=',
            form: '=',
        },
        template: [
            '<div>',
                '<input type="text" data-ng-change="validateAll()" data-ng-model="model[field]" class="form-control" required>',
                '<input type="checkbox" data-ng-model="model.autoFill" data-ng-change="validateAll()"> Auto-fill variables',
            '</div>',
        ].join(''),
        controller: function ($scope) {

            var defaultFitVars = ['x', 'y', 'z', 't'];

            function tokenizeEquation() {
                return mlService.tokenizeEquation($scope.model[$scope.field]);
            }

            function extractParams() {

                var params = mlService.tokenizeParams($scope.model.fitParameters).sort();
                var tokens = tokenizeEquation().filter(function (t) {
                    return t !== $scope.model.fitVariable;
                });

                // remove parameters no longer in the equation
                params.reverse().forEach(function (p, i) {
                    if (tokens.indexOf(p) < 0) {
                        params.splice(i, 1);
                    }
                });

                // add tokens not represented
                tokens.forEach(function (t) {
                    if (params.indexOf(t) < 0) {
                        params.push(t);
                    }
                });
                params.sort();

                return params;
            }

            function extractVar() {
                var tokens = tokenizeEquation();
                var indVar = $scope.model.fitVariable;

                if (! indVar|| tokens.indexOf(indVar) < 0) {
                    indVar = null;
                    tokens.forEach(function (t) {
                        if (indVar) {
                            return;
                        }
                        if (defaultFitVars.indexOf(t) >= 0) {
                            indVar = t;
                        }
                    });
                }
                return indVar;
            }

            $scope.validateAll = function() {
                if ($scope.model.autoFill) {
                    // allow time for models to be set before validating
                    $timeout(function () {
                        $scope.model.fitVariable = extractVar();
                        $scope.model.fitParameters = extractParams().join(',');
                    });
                }

                $scope.form.$$controls.forEach(function (c) {
                    c.$setDirty();
                    c.$validate();
                });
            };

            if ($scope.model.autoFill === null) {
                $scope.model.autoFill = true;
            }
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
                    if (str == '') {
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

SIREPO.app.directive('heatmapModifications', function() {
    return {
        restrict: 'A',
        scope: {},
        controller: function($scope, plotting, layoutService) {
            const CLASS_LABEL = 'sr-svg-label';
            const CLASS_RESULT = 'sr-svg-result';
            let analysisReport, data, svg;

            function addTicks() {
                data.labels.forEach((l, i) => {
                    commonAttributes('.x', l, CLASS_LABEL)
                        .attr('x', elementPosition(i, 'width'))
                        .attr('y',  20);
                });
                [...data.labels].reverse().forEach((l, i) => {
                    commonAttributes('.y', l, CLASS_LABEL)
                        .attr('x', elementPosition(i, 'height'))
                        .attr('y',  -10)
                        .attr('transform', 'rotate(270)');
                });
            }

            function addResultNumbers() {
                for (let i = 0 ; i < data.z_matrix.length; i++) {
                    for (let j = 0; j < data.z_matrix[i].length; j++) {
                        commonAttributes('.x', data.z_matrix[i][j], CLASS_RESULT)
                            .attr('x', elementPosition(j, 'width'))
                            .attr('y', elementPosition(i, 'height'));

                    }
                }
            }

            function commonAttributes(element, label, cssClass) {
                return svg.select(element)
                    .append('text')
                    .text(label)
                    .attr('class', cssClass)
                    .attr('text-anchor', 'middle');
            }

            function elementPosition(index, heightOrWidth) {
                const d = analysisReport.canvasSize[heightOrWidth];
                const l = data.labels.length;
                return (
                        (heightOrWidth == 'height' ? -1 : 1) *
                        ((d * index / l) + (d / (l * 2))
                        )
                    );
            }

            function removeUnusedElements() {
                [
                    '.mouse-rect',
                    '.x .tick',
                    '.y .tick',
                    `.${CLASS_LABEL}`,
                    `.${CLASS_RESULT}`,
                ].forEach((e) => {
                    svg.selectAll(e).remove();
                });
            }

            $scope.$parent.$parent.$parent.$on('sr-plotLinked', function(event) {
                analysisReport = event.targetScope;
                svg = analysisReport.select("svg");
                const oldResize = analysisReport.resize;
                analysisReport.resize = function() {
                    oldResize();
                    removeUnusedElements();
                    addTicks();
                    addResultNumbers();
                };

                const oldLoad = analysisReport.load;
                analysisReport.load = function(json) {
                    data = json;
                    oldLoad(data);
                };
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

SIREPO.app.controller('PartitionController', function (appState, mlService, $scope) {
    var self = this;
    self.reports = [];

    function loadReports() {
        appState.models.columnInfo.inputOutput.forEach(function(type, idx) {
            if (type == 'none') {
                return;
            }
            var modelKey = mlService.partitionReportName(idx);
            appState.models[modelKey] = {
                columnNumber: idx,
            };
            appState.saveQuietly(modelKey);
            self.reports.push(mlService.reportInfo(modelKey, type.charAt(0).toUpperCase() + type.slice(1) + ' ' + (idx + 1), idx));
        });
    }

    $scope.showPartitionSelection = function() {
        if (appState.isLoaded()) {
            if (appState.applicationState().dataFile.appMode == 'regression') {
                return appState.applicationState().partition.method == 'selection';
            }
        }
        return false;
    };

    appState.whenModelsLoaded($scope, loadReports);
});

SIREPO.app.directive('neuralNetLayersForm', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<form name="form" class="form-horizontal">',
              '<div class="form-group form-group-sm">',
                '<table class="table table-striped table-condensed">',
                  '<tr data-ng-repeat="layer in appState.models.neuralNet.layers track by $index" data-ng-init="layerIndex = $index">',
                    '<td data-ng-repeat="fieldInfo in layerInfo(layerIndex) track by fieldTrack(layerIndex, $index)">',
                      '<div data-ng-if="fieldInfo.field">',
                        '<b>{{ fieldInfo.label }}</b>',
                        '<div class="row" data-field-editor="fieldInfo.field" data-field-size="12" data-model-name="\'neuralNetLayer\'" data-model="layer"></div>',
                      '</div>',
                    '</td>',
                    '<td style="padding-top: 2em;">',
                      '<button class="btn btn-danger btn-xs" data-ng-click="deleteLayer($index)" title="Delete Row"><span class="glyphicon glyphicon-remove"></span></button>',
                    '</td>',
                  '<tr>',
                    '<td>',
                      '<b>Add Layer</b>',
                        '<select class="form-control" data-ng-model="selectedLayer" data-ng-options="item[0] as item[1] for item in layerEnum" data-ng-change="addLayer()"></select>',
                    '</td>',
                    '<td></td>',
                    '<td></td>',
                    '<td></td>',
                  '</tr>',
                '</table>',
              '</div>',
              '<div class="col-sm-6 pull-right" data-ng-show="hasChanges()">',
                '<button data-ng-click="saveChanges()" class="btn btn-primary" data-ng-disabled="! form.$valid">Save Changes</button> ',
                '<button data-ng-click="cancelChanges()" class="btn btn-default">Cancel</button>',
              '</div>',
            '</form>',
        ].join(''),
        controller: function($scope, $element) {
            var layerFields = {};
            var layerInfo = [];
            $scope.appState = appState;
            $scope.form = angular.element($($element).find('form').eq(0));
            $scope.selectedLayer = '';
            $scope.layerEnum = SIREPO.APP_SCHEMA.enum.NeuralNetLayer;

            $scope.addLayer = function() {
                if (! $scope.selectedLayer) {
                    return;
                }
                var neuralNet = appState.models.neuralNet;
                if (! neuralNet.layers) {
                    neuralNet.layers = [];
                }
                var m = appState.setModelDefaults({}, 'neuralNetLayer');
                m.layer = $scope.selectedLayer;
                neuralNet.layers.push(m);
                $scope.selectedLayer = '';
            };

            $scope.cancelChanges = function() {
                appState.cancelChanges('neuralNet');
                $scope.form.$setPristine();
            };

            $scope.deleteLayer = function(idx) {
                appState.models.neuralNet.layers.splice(idx, 1);
                $scope.form.$setDirty();
            };

            $scope.layerInfo = function(idx) {
                if (! appState.isLoaded()) {
                    return layerInfo;
                }
                var layer = appState.models.neuralNet.layers[idx];
                layerInfo[idx] = layerFields[layer.layer];
                return layerInfo[idx];
            };

            $scope.hasChanges = function() {
                if ($scope.form.$dirty) {
                    return true;
                }
                return appState.areFieldsDirty('neuralNet.layers');
            };

            $scope.fieldTrack = function(layerIdx, idx) {
                // changes the fields editor if the layer type changes
                var layer = appState.models.neuralNet.layers[layerIdx];
                return layer.layer + idx;
            };

            $scope.saveChanges = function() {
                appState.saveChanges('neuralNet');
                $scope.form.$setPristine();
            };

            function buildLayerFields() {
                var MAX_FIELDS = 3;
                var layerSchema = SIREPO.APP_SCHEMA.model.neuralNetLayer;
                $scope.layerEnum.forEach(function(row) {
                    var name = row[0];
                    var cols = [
                        {
                            field: 'layer',
                            label: 'Layer',
                        },
                    ];
                    Object.keys(layerSchema).sort().reverse().forEach(function(field) {
                        if (field.toLowerCase().indexOf(name.toLowerCase()) == 0) {
                            cols.push({
                                field: field,
                                label: layerSchema[field][0],
                            });
                        }
                    });
                    while (cols.length < MAX_FIELDS) {
                        cols.push({});
                    }
                    layerFields[name] = cols;
                });
            }

            buildLayerFields();
        },
    };
});

SIREPO.app.directive('partitionSelection', function(appState) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<form name="form" class="form-horizontal" data-ng-style="formStyle">',
              '<div class="form-group form-group-sm">',
                '<div data-ng-repeat="field in fields track by $index" data-model-field="field" data-model-name="modelName" data-label-size="0" data-field-size="4"></div>',
                '<div data-ng-repeat="field in fields track by $index" class="col-sm-4">',
                  '<p class="form-control-static text-center">{{ selectedRange(field) }}</p>',
                '</div>',
                '<div data-ng-if="hasTrainingAndTesting()" data-model-field="\'trainTestPercent\'" data-model-name="\'partition\'"></div>',
              '</div>',
              '<div class="col-sm-12 text-center" data-buttons="" data-model-name="modelName" data-fields="allFields"></div>',
            '</form>',
        ].join(''),
        controller: function($scope) {
            var dragCarat, plotRefresh, plotScope;
            $scope.modelName = 'partition';
            $scope.fields = ['section0', 'section1', 'section2'];
            $scope.allFields = $scope.fields.concat(['cutoff0', 'cutoff1']);
            $scope.formStyle = {};

            function validateCutoff(p) {
                var axis = plotScope.axes.x;
                if (p <= axis.domain[0]) {
                    p = axis.domain[0] + 2;
                }
                if (p >= axis.domain[1]) {
                    p = axis.domain[1] - 2;
                }
                return parseInt(p);
            }

            function d3DragCarat(d) {
                /*jshint validthis: true*/
                var axis = plotScope.axes.x;
                var p = axis.scale.invert(d3.event.x);
                appState.models.partition[d] = validateCutoff(p);
                d3.select(this).call(updateCarat);
                $scope.$applyAsync();
            }

            function d3DragEndCarat(d) {
                var partition = appState.models.partition;
                if (partition.cutoff0 > partition.cutoff1) {
                    var c = partition.cutoff0;
                    partition.cutoff0 = partition.cutoff1;
                    partition.cutoff1 = c;
                }
                $scope.$applyAsync();
            }

            function drawCarats(parts) {
                var viewport = plotScope.select('.plot-viewport');
                viewport.selectAll('.rcscon-cell-selector').remove();
                viewport.selectAll('.rcscon-cell-selector')
                    .data(parts)
                    .enter().append('path')
                    .attr('class', 'rcscon-cell-selector')
                    .attr('d', 'M-2,-28L-2,-3000 2,-3000 2,-28 14,0 -14,0Z')
                    .style('cursor', 'ew-resize')
                    .style('fill-opacity', 0.8)
                    .style('stroke', '#000')
                    .style('stroke-width', '1.5px')
                    .style('fill', '#666')
                    .call(updateCarat)
                    .call(dragCarat);
            }

            function init(targetScope) {
                plotScope = targetScope;
                plotRefresh = plotScope.refresh;
                plotScope.refresh = refresh;
                dragCarat = d3.behavior.drag()
                    .on('drag', d3DragCarat)
                    .on('dragstart', function() {
                        d3.event.sourceEvent.stopPropagation();
                    })
                    .on('dragend', d3DragEndCarat);
            }

            function refresh() {
                $scope.formStyle['margin-left'] = plotScope.margin.left + 'px';
                $scope.formStyle['margin-right'] = plotScope.margin.right + 'px';
                plotScope.select('svg').selectAll('.overlay').classed('disabled-overlay', true);
                plotRefresh();
                drawCarats(['cutoff0', 'cutoff1']);
            }

            function updateCarat(selection) {
                var axes = plotScope.axes;
                selection.attr('transform', function(d) {
                    var x = appState.models.partition[d];
                    return 'translate('
                        + axes.x.scale(x) + ',' + axes.y.scale(axes.y.scale.domain()[0])
                        + ')';
                });
            }

            function processSection(field) {
                // ensure all three values are selected
                var partition = appState.models.partition;
                if ($scope.hasTrainingAndTesting()) {
                    var count = 0;
                    $scope.fields.forEach(function(f) {
                        if (partition[f] == 'train_and_test') {
                            count++;
                        }
                        else {
                            partition[f] = 'validate';
                        }
                    });
                    if (count == 3) {
                        partition.section2 = 'validate';
                    }
                }
                else {
                    setMissingSection(field, partition);
                }
            }

            function setMissingSection(field, partition) {
                var currentValue, missingValue;
                ['train', 'test', 'validate'].some(function(v) {
                    var hasValue = false;
                    $scope.fields.forEach(function(f) {
                        if (field == 'partition.' + f) {
                            currentValue = partition[f];
                        }
                        if (partition[f] == v) {
                            hasValue = true;
                        }
                    });
                    if (! hasValue) {
                        missingValue = v;
                    }
                });
                if (missingValue) {
                    $scope.fields.forEach(function(f) {
                        if (field != 'partition.' + f
                            && partition[f] == currentValue) {
                            partition[f] = missingValue;
                            missingValue = '';
                        }
                    });
                    if (missingValue) {
                        partition.section2 = missingValue;
                    }
                }
            }

            $scope.hasTrainingAndTesting = function() {
                if (! appState.isLoaded()) {
                    return;
                }
                var partition = appState.models.partition;
                return $scope.fields.some(function(f) {
                    return partition[f] == 'train_and_test';
                });
            };

            $scope.selectedRange = function(field) {
                if (! appState.isLoaded() || ! plotScope || ! plotScope.axes.x.domain) {
                    return;
                }
                var partition = appState.models.partition;
                if (field == 'section0') {
                    return '0 - ' + (partition.cutoff0 - 1);
                }
                if (field == 'section1') {
                    return partition.cutoff0 + ' - ' + (partition.cutoff1 - 1);
                }
                return partition.cutoff1 + ' - ' + (plotScope.axes.x.domain[1] - 1);
            };

            $scope.$parent.$parent.$parent.$on('sr-plotLinked', function(event) {
                init(event.targetScope);
            });

            $scope.$on('cancelChanges', refresh);

            appState.watchModelFields(
                $scope, ['partition.section0', 'partition.section1', 'partition.section2'],
                processSection);
        },
    };
});

SIREPO.app.directive('tablePanel', function(plotting) {
    return {
        restrict: 'A',
        scope: {
            modelName: "@"
        },
        template: [
            '<div data-ng-if="! tableHeaders">',
              '<div class="lead">&nbsp;</div>',
            '</div>',
            '<div data-ng-if="tableHeaders">',
              '<div class="col-sm-12" style="margin-top: 1ex;">',
                '<table class="table">',
                  '<caption>{{ title }}</caption>',
                  '<thead>',
                    '<tr>',
                      '<th data-ng-repeat="h in tableHeaders">{{h}}</th>',
                    '</tr>',
                  '</thead>',
                  '<tr data-ng-repeat="r in tableRows" data-ng-bind-html=row(r)></tr>',
                '</table>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope, $sce) {
            plotting.setTextOnlyReport($scope);
            $scope.row = (row) => {
                const r = [...row];
                let x = '<th>' + r.shift() + '</th>' + r.map(function (e) {
                    return '<td>' + e + '</td>';
                }).join('');
                return $sce.trustAsHtml(x);
            };

            $scope.load = (json) => {
                $scope.tableHeaders = ['', ...json.labels];
                $scope.tableRows = [];
                for (let i = 0; i < json.matrix.length; i++) {
                    const r = [];
                    for (let j = 0; j < json.matrix[i].length; j++) {
                        let v = json.matrix[i][j];
                        if (! Number.isNaN(Number(v)) && ! Number.isInteger(Number(v))) {
                            v = Number(v).toFixed(4);
                        }
                        r.push(v);
                    }
                    $scope.tableRows.push(r);
                }
                $scope.title = json.title;
            };
            $scope.$on('framesCleared', function() {
                $scope.tableHeaders = null;
            });
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.viewLogic('partitionView', function(appState, panelState, $scope) {

    function updatePartitionMethod() {
        var appMode = appState.models.dataFile.appMode;
        panelState.showField('partition', 'method', appMode == 'regression');
        var partition = appState.models.partition;
        ['training', 'testing'].forEach(function(f) {
            panelState.showField(
                'partition',
                f,
                appMode == 'classification' || partition.method == 'random');
        });
        panelState.showField(
            'partition',
            'validation',
            appMode == 'regression' && partition.method == 'random');
    }

    function updatePercents() {
        var appMode = appState.models.dataFile.appMode;
        var partition = appState.models.partition;
        if (appMode == 'classification') {
            if (partition.training) {
                partition.testing = 100 - partition.training;
            }
            panelState.enableField('partition', 'testing', false);
        }
        else if (partition.training && partition.testing) {
            var validation = 100 - (partition.training + partition.testing);
            if (validation > 0) {
                partition.validation = parseFloat(validation.toFixed(2));
            }
        }
        panelState.enableField('partition', 'validation', false);
    }

    $scope.whenSelected = function() {
        updatePercents();
        updatePartitionMethod();
    };
    $scope.watchFields = [
        ['partition.training', 'partition.testing'], updatePercents,
        ['partition.method'], updatePartitionMethod,
    ];
});

SIREPO.viewLogic('dataFileView', function(appState, panelState, $scope) {

    function processAppMode() {
        const appMode = appState.models.dataFile.appMode;
        panelState.showField(
            'dataFile', 'inputsScaler',
            ['regression', 'classification'].includes(appMode));
        panelState.showField(
            'dataFile', 'outputsScaler',
            appMode == 'regression');
    }

    $scope.whenSelected = processAppMode;
    $scope.watchFields = [
        ['dataFile.appMode'], processAppMode,
    ];
});
