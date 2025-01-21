'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.PLOTTING_COLOR_MAP = 'blues';
    SIREPO.SINGLE_FRAME_ANIMATION = [
        'epochAnimation',
        'epochComparisonAnimation',
        'dicePlotAnimation',
        'dicePlotComparisonAnimation',
        'bestLossesAnimation',
        'bestLossesComparisonAnimation',
        'worstLossesAnimation',
        'worstLosssComparisonAnimation',
    ];
    SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL = true;
    SIREPO.FILE_UPLOAD_TYPE = {
        'dataFile-file': '.h5,.csv',
    };
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="AnalysisParameter" class="col-sm-5">
          <div data-analysis-parameter="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="OptionalInteger" data-ng-class="fieldClass">
          <input data-string-to-number="integer" data-ng-model="model[field]"
            data-min="info[4]" data-max="info[5]" class="form-control"
            style="text-align: right" data-lpignore="true" />
        </div>
        <div data-ng-switch-when="Equation" class="col-sm-7">
          <div data-equation="equation" data-model="model" data-field="field" data-form="form"></div>
          <div class="sr-input-warning" data-ng-show="showWarning">{{warningText}}</div>
        </div>
        <div data-ng-switch-when="EquationVariables" class="col-sm-7">
          <div data-equation-variables="" data-model="model" data-field="field" data-form="form" data-is-variable="true"></div>
        </div>
        <div data-ng-switch-when="EquationParameters" class="col-sm-7">
          <div data-equation-variables="" data-model="model" data-field="field" data-form="form" data-is-variable="false"></div>
        </div>
        <div data-ng-switch-when="ClusterFields" class="col-sm-7">
          <div data-cluster-fields="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="PlotActionButtons" class="col-sm-12">
          <div data-plot-action-buttons="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="TrimButton" class="col-sm-5">
          <div data-trim-button="" data-model-name="modelName" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="URL" class="col-sm-7" data-field-class="fieldClass">
          <input type="text" data-ng-model="model[field]" class="form-control" data-lpignore="true" />
          <span data-ng-show="model.dataOrigin === 'url'" style="font-style: italic; font-size: 80%;">{{ UTILS.formatToThousands(model.bytesLoaded, 1, true) || 0 }} of {{ UTILS.formatToThousands(model.contentLength, 1, true) || 0 }} {{ UTILS.orderOfMagnitude(model.contentLength, true).suffix }}B</span>
          <div class="sr-input-warning"></div>
          <div data-ng-show="model.contentLength && ! model.bytesLoaded" data-sim-state-progress-bar=""></div>
        </div>
        <div data-ng-switch-when="XColumn" data-field-class="fieldClass">
          <div data-x-column="" data-model-name="modelName" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="SimList" data-ng-class="fieldClass">
          <div data-activait-sim-list="" data-model="model" data-field="field"></div>
        </div>
    `;
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="classificationMetrics" data-table-panel="" data-model-name="{{ modelKey }}" class="sr-plot sr-screenshot"></div>
        <div data-ng-switch-when="confusionMatrix" data-table-panel="" data-model-name="{{ modelKey }}" class="sr-plot sr-screenshot"></div>
        <div data-ng-switch-when="imageViewer" data-image-viewer="" data-model-name="{{ modelKey }}" class="sr-plot sr-screenshot"></div>
    `;
});

SIREPO.app.factory('activaitService', function(appState, panelState, utilities) {
    const self = {};
    const parameterCache = {
        analysisParameters: null,
        parameterValues: null,
        optionalParameterValues: null,
    };

    self.addSubreport = (parent, action) => {
        const report = appState.clone(parent);
        const subreports = self.getSubreports();
        report.id = subreports.length
            ? (utilities.arrayMax(subreports) + 1)
            : 1;
        report.action = null;
        report.history.push(action);
        const name = 'analysisReport' + report.id;
        const fftName = 'fftReport' + report.id;
        appState.models[name] = report;
        appState.models[fftName] = {
            'analysisReport': name,
        };
        subreports.push(report.id);
        appState.saveChanges([name, fftName, 'hiddenReport']);
    };

    self.buildParameterList = (includeOptional) => {
        if (! appState.isLoaded()) {
            return null;
        }
        const name = includeOptional ? 'optionalParameterValues' : 'parameterValues';
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
        const parameterValues = [];
        const visited = {};
        (parameterCache.analysisParameters.header || []).forEach((name, idx) => {
            // skip duplicate columns
            if (! visited[name]) {
                parameterValues.push(['' + idx, name]);
                visited[name] = true;
            }
        });
        parameterValues.sort((a, b) => {
            return a[1].localeCompare(b[1]);
        });
        if (includeOptional) {
            parameterValues.unshift(['none', 'None']);
        }
        parameterCache[name] = parameterValues;
        return parameterValues;
    };

    self.columnReportName = idx => 'fileColumnReport' + idx;

    self.computeModel = analysisModel => {
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

    // subreports are kept on a report which is never shown.
    // This avoids refreshing all reports when a subreport is added or removed.
    self.getSubreports = () => appState.models.hiddenReport.subreports;

    self.hasDataFile = () => appState.isLoaded()
        && appState.applicationState().dataFile.file;

    self.isAnalysis = () => self.isAppMode('analysis');

    self.isAppMode = mode => appState.isLoaded()
        && appState.applicationState().dataFile.appMode === mode;

    self.isImageData = () => self.hasDataFile()
        && appState.applicationState().dataFile.file.toLowerCase().endsWith('.h5');

    self.isTextData = () => self.hasDataFile()
        && appState.applicationState().dataFile.file.toLowerCase().endsWith('.csv');

    self.partitionReportName = idx => 'partitionColumnReport' + idx;

    self.removeAllSubreports = ()  => {
        const subreports = self.getSubreports();
        while (subreports.length) {
            self.removeSubreport(subreports[0]);
        }
    };

    self.removeSubreport = id => {
        const subreports = self.getSubreports();
        subreports.splice(subreports.indexOf(id), 1);
        appState.removeModel('analysisReport' + id);
        appState.removeModel('fftReport' + id);
        panelState.clear('analysisReport' + id);
    };

    self.reportInfo = (modelKey, title, idx) => {
        return {
            columnNumber: idx,
            title: title,
            data: {
                modelKey: modelKey,
                getData: () => appState.models[modelKey],
            },
        };
    };

    self.tokenizeEquation = eq => {
        return (eq || '').split(/[-+*/^|%().0-9\s]/)
            .filter(t => {
                return t.length > 0 &&
                    SIREPO.APP_SCHEMA.constants.allowedEquationOps.indexOf(t) < 0;
        });
    };

    self.tokenizeParams = val => {
        return (val || '').split(/\s*,\s*/).filter(t => {
            return t.length > 0;
        });
    };

    appState.setAppService(self);
    return self;
});

SIREPO.app.directive('appFooter', function(activaitService) {
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

SIREPO.app.directive('appHeader', function(appState, activaitService) {
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('data')}"><a href data-ng-click="nav.openSection('data')"><span class="glyphicon glyphicon-picture"></span> Data Source</a></li>
                  <li class="sim-section" data-ng-if="appState.isLoaded() && activaitService.hasDataFile() && activaitService.isAnalysis()" data-ng-class="{active: nav.isActive('analysis')}"><a href data-ng-click="nav.openSection('analysis')"><span class="glyphicon glyphicon-tasks"></span> Analysis</a></li>
                  <li class="sim-section" data-ng-if="hasInputsAndOutputs() && ! activaitService.isAnalysis()" data-ng-class="{active: nav.isActive('partition')}"><a href data-ng-click="nav.openSection('partition')"><span class="glyphicon glyphicon-scissors"></span> Partition</a></li>
                  <li class="sim-section" data-ng-if="hasInputsAndOutputs() && activaitService.isAppMode('regression')" data-ng-class="{active: nav.isActive('regression')}"><a href data-ng-click="nav.openSection('regression')"><span class="glyphicon glyphicon-qrcode"></span> Regression</a></li>
                  <li class="sim-section" data-ng-if="hasInputsAndOutputs() && activaitService.isAppMode('classification')" data-ng-class="{active: nav.isActive('classification')}"><a href data-ng-click="nav.openSection('classification')"><span class="glyphicon glyphicon-tag"></span> Classification</a></li>
                  <li class="sim-section" data-ng-if="isImageToImage()" data-ng-class="{active: nav.isActive('comparison')}"><a href data-ng-click="nav.openSection('comparison')"><span class="glyphicon glyphicon-tasks"></span> Model Comparison</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
              </app-settings>
              <app-header-right-sim-list>
                <ul class="nav navbar-nav sr-navbar-right">
                  <li><a href data-ng-click="nav.showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>
                </ul>
              </app-header-right-sim-list>
            </div>
        `,
        controller: function($scope) {
            $scope.appState = appState;
            $scope.activaitService = activaitService;
            $scope.hasInputsAndOutputs = () => {
                if (appState.isLoaded() && activaitService.hasDataFile()
                    && appState.applicationState().columnInfo) {
                    const inputOutput = appState.applicationState().columnInfo.inputOutput;
                    return inputOutput && inputOutput.indexOf('input') >= 0
                        && inputOutput.indexOf('output') >= 0;
                }
                return false;
            };
            $scope.isImageToImage = () => {
                var info = appState.models.columnInfo;
                if (info && info.inputOutput.indexOf('output') >= 0) {
                    if (info.shape) {
                        var idx = info.inputOutput.indexOf('output');
                        return info.shape[idx].slice(1, info.shape[idx].length).length > 1;
                    }
                }
                return false;
            };
        },
    };
});

SIREPO.app.controller('AnalysisController', function (appState, activaitService, panelState, requestSender, $scope, $window) {
    const self = this;
    self.subplots = null;

    function buildSubplots() {
        self.subplots = [];
        (activaitService.getSubreports() || []).forEach((id, idx) => {
            const modelKey = 'analysisReport' + id;
            self.subplots.push({
                id: id,
                modelKey: modelKey,
                title: 'Analysis Subplot #' + (idx + 1),
                getData: () => appState.models[modelKey],
            });
        });
    }

    $scope.$on('modelChanged', (e, name) => {
        if (name.indexOf('analysisReport') >= 0) {
            // invalidate the corresponding fftReport
            appState.saveChanges('fftReport' + (appState.models[name].id || ''));
        }
    });
    $scope.$on('hiddenReport.changed', buildSubplots);
    buildSubplots();
});

SIREPO.app.controller('DataController', function (activaitService, appState, requestSender, $scope) {
    const self = this;
    self.dataFileReady = false;
    self.activaitService = activaitService;

    const hasInOut = inputOutput => ['input', 'output'].map(x => inputOutput.includes(x)).reduce((p, c) => p && c);

    function downloadRemoteLibFile() {
        requestSender.sendStatefulCompute(
            appState,
            data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                self.dataFileReady = true;
                appState.models.dataFile.exampleDir = "";
                appState.saveChanges('dataFile');
            },
            {
                method: 'download_remote_lib_file',
                args: {
                    exampleDir: appState.models.dataFile.exampleDir,
                    exampleFileCnt: appState.models.dataFile.exampleFileCnt,
                    file: appState.models.dataFile.file
                },
            }
        );
    }

    $scope.$on('columnInfo.changed', () => {
        const c = appState.models.columnInfo;
        if (c.inputOutput && hasInOut(c.inputOutput) && c.header) {
            appState.models.imageViewerShow = true;
            appState.saveChanges('imageViewerShow');
            return;
        }
        appState.models.imageViewerShow = false;
        appState.saveChanges('imageViewerShow');
    });

    self.showImageViewer = () => activaitService.isImageData() && appState.models.imageViewerShow;

    if (appState.models.dataFile.exampleDir) {
        downloadRemoteLibFile();
    }
    else {
        self.dataFileReady = true;
    }
});

SIREPO.app.controller('ComparisonController', function (activaitService, appState, frameCache, persistentSimulation, $scope) {
    const self = this;
    self.simScope = $scope;
    self.simAnalysisModel = 'fitAnimation';
    self.activaitService = activaitService;
    var compare = false;
    var otherSimId = null;

    self.showComparisons = () => compare;

    self.comparisonId = () => otherSimId;

    const setComparisonSim = () => {
        if (appState.models.comparisonSims.compareSim.length) {
            compare = true;
            otherSimId = appState.models.comparisonSims.compareSim;
            appState.models.dicePlotComparisonAnimation.otherSimId = otherSimId;
            appState.models.epochComparisonAnimation.otherSimId = otherSimId;
            appState.models.bestLossesComparisonAnimation.otherSimId = otherSimId;
            appState.models.worstLossesComparisonAnimation.otherSimId = otherSimId;
            appState.saveChanges('bestLossesComparisonAnimation');
            appState.saveChanges('worstLossesComparisonAnimation');
            appState.saveChanges('dicePlotComparisonAnimation');
            appState.saveChanges('epochComparisonAnimation');
            return;
        }
        otherSimId = null;
        compare = false;
    };

    self.simHandleStatus = data => {
        self.reports = null;
        frameCache.setFrameCount(data.frameCount || 0);
    };

    self.simState = persistentSimulation.initSimulationState(self);

    setComparisonSim();

    $scope.$on('comparisonSims.changed', setComparisonSim);
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

    self.hasFrames = () => {
        if (appState.isLoaded()
            && self.framesForClassifier == appState.applicationState().classificationAnimation.classifier) {
            return frameCache.hasFrames();
        }
        return false;
    };

    self.simHandleStatus = data => {
        errorMessage = data.error;
        self.framesForClassifier = data.framesForClassifier;
        if (data.frameCount) {
            frameCache.setFrameCount(data.frameCount);
        }
    };

    self.simCompletionState = () => '';

    self.simState = persistentSimulation.initSimulationState(self);

    self.simState.errorMessage = () => errorMessage;

    showClassifierSettings();
    appState.watchModelFields(
        $scope,
        ['classificationAnimation.classifier'],
        showClassifierSettings
    );
});

SIREPO.app.controller('RegressionController', function (appState, frameCache, activaitService, persistentSimulation, $scope) {
    const self = this;
    self.simScope = $scope;
    self.simAnalysisModel = 'fitAnimation';
    var errorMessage = '';

    function outputColumnCount() {
        let res = 0;
        const info = appState.models.columnInfo;
        for (let i = 0; i < info.inputOutput.length; i++) {
            if (info.inputOutput[i] == 'output') {
                if (info.outputShape && info.dtypeKind[i] != 'u') {
                    res += info.outputShape[i];
                }
                else {
                    res++;
                }
            }
        }
        return res;
    }

    function addFitReports() {
        const res = [];
        for (let i = 0; i < outputColumnCount(); i++) {
            const modelKey = 'fitAnimation' + i;
            if (! appState.models[modelKey]) {
                appState.models[modelKey] = {
                    columnNumber: i,
                };
                appState.saveQuietly(modelKey);
            }
            res.push(activaitService.reportInfo(modelKey, 'Fit ' + (i + 1), i));
            if (SIREPO.SINGLE_FRAME_ANIMATION.indexOf(modelKey) < 0) {
                SIREPO.SINGLE_FRAME_ANIMATION.push(modelKey);
            }
            frameCache.setFrameCount(1, modelKey);
            if (i % 4 == 3) {
                res[res.length - 1].break = true;
            }
        }
        if (! res.length){
            return res;
        }
        res[res.length - 1].break = true;
        return res;
    }

    self.simHandleStatus = data => {
        errorMessage = data.error;
        self.reports = null;
        if ('percentComplete' in data && ! data.error) {
            if (data.percentComplete === 100 && ! self.simState.isProcessing()) {
                self.reports = addFitReports();
            }
        }
        frameCache.setFrameCount(data.frameCount || 0);
    };

    self.hasModel = () => {
        if (appState.isLoaded()) {
            return appState.applicationState().neuralNet.layers.length;
        }
        return false;
    };

    self.imageToImage = () => {
        if (! self.reports) {
            return false;
        }
        var info = appState.models.columnInfo;
        var idx = info.inputOutput.indexOf('output');
        if (! info.shape) {
            return false;
        }
        return info.shape[idx].slice(1, info.shape[idx].length).length > 1;
    };

    self.startSimulation = () => {
        self.simState.saveAndRunSimulation('simulation');
    };

    self.hasFrames = frameCache.hasFrames;

    self.simState = persistentSimulation.initSimulationState(self);

    self.simState.errorMessage = () => errorMessage;

    self.simState.runningMessage = () => {
        if (appState.isLoaded() && self.simState.getFrameCount()) {
            return 'Completed epoch: ' + self.simState.getFrameCount();
        }
        return 'Simulation running';
    };
});

SIREPO.app.directive('analysisActions', function(appState, panelState, activaitService) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            modelData: '=',
        },
        template: `
            <button data-ng-if="isSubreport()" data-ng-click="closeSubreport()" title="close" type="button" class="close" style="position: absolute; top: 55px; right: 25px">
              <span>&times;</span>
            </button>
            <div data-ng-show="! isLoading()" style="background: white; padding: 1ex; border-radius: 4px;">
              <div class="clearfix"></div>
              <div data-ng-repeat="view in viewNames track by $index">
                <div data-ng-if="isActiveView(view)" style="margin-top:3ex;">
                  <div data-advanced-editor-pane="" data-model-data="modelData" data-view-name="view" data-field-def="basic" data-want-buttons="{{ wantButtons() }}"></div>
                </div>
              </div>
              <div class="clearfix"></div>
              <div data-ng-if="showFFT()">
                <div data-fft-report="" data-model-data="modelData" style="margin-top: 5px;"></div>
              </div>
            </div>
        `,
        controller: function($scope, $element) {
            let analysisReport;
            let isFirstRefresh = true;
            const modelKey = $scope.modelData
                ? $scope.modelData.modelKey
                : $scope.modelName;
            const viewForEnum = {
                '': 'analysisNone',
                'cluster': 'analysisCluster',
                'fft': 'analysisFFT',
                'fit': 'analysisFit',
                'trim': 'analysisTrim',
            };
            $scope.viewNames = Object.keys(viewForEnum).map(k =>viewForEnum[k]);

            function addSubreport(clusterIndex) {
                const action = {
                    clusterIndex: clusterIndex,
                };
                const parent = $scope.model();
                ['action', 'clusterMethod', 'clusterCount', 'clusterFields', 'clusterScaleMin', 'clusterScaleMax', 'clusterRandomSeed', 'clusterKmeansInit', 'clusterDbscanEps'].forEach(f => {
                    action[f] = parent[f];
                });
                activaitService.addSubreport(parent, action);
            }

            function initAnalysisReport(reportScope) {
                analysisReport = reportScope;
                const oldLoad = analysisReport.load;
                analysisReport.load = json => {
                    isFirstRefresh = true;
                    $('.scatter-point').popover('hide');
                    oldLoad(json);
                };
                const oldRefresh = analysisReport.refresh;
                analysisReport.refresh = () => {
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
                const model = $scope.model();
                if (model && model.action == 'trim') {
                    model.trimField = model.x;
                    const xDomain = analysisReport.axes.x.scale.domain();
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
                    const viewport = analysisReport.select('.plot-viewport');
                    // click handler needs to be an explicit function for "this"
                    viewport.selectAll('.scatter-point').on('click', function(d, idx) {
                        const clusterIndex = analysisReport.clusterInfo.group[idx];

                        function buttonHandler() {
                            $('.scatter-point').popover('hide');
                            $scope.$apply(() => {
                                addSubreport(clusterIndex);
                            });
                        }
                        $(this).popover({
                            trigger: 'manual',
                            html: true,
                            placement: 'bottom',
                            container: 'body',
                            title: 'Cluster: ' + (clusterIndex + 1),
                            content: '<div><button class="btn btn-default activait-popover">Open in New Plot</button></div>',
                        }).on('hide.bs.popover', () => {
                            $(document).off('click', buttonHandler);
                        });
                        $('.scatter-point').not($(this)).popover('hide');
                        $(this).popover('toggle');
                        $(document).on('click', '.activait-popover', buttonHandler);
                    });
                }
            }

            $scope.closeSubreport = () => {
                activaitService.removeSubreport($scope.model().id);
                appState.saveChanges('hiddenReport');
            };

            $scope.isActiveView = view => {
                const model = $scope.model();
                if (model) {
                    return viewForEnum[model.action || ''] == view;
                }
                return false;
            };

            $scope.isLoading = () => panelState.isLoading(modelKey);

            $scope.isSubreport = () => modelKey != $scope.modelName;

            $scope.model = () => {
                if (appState.isLoaded()) {
                    return appState.models[modelKey];
                }
                return null;
            };

            $scope.showFFT = () => {
                if (appState.isLoaded()) {
                    return $scope.model().action == 'fft'
                        && appState.applicationState()[modelKey].action == 'fft';
                }
                return false;
            };

            $scope.wantButtons = () => {
                if (appState.isLoaded()) {
                    const action = $scope.model().action;
                    if (action == 'trim') {
                        return '';
                    }
                    return '1';
                }
                return '';
            };

            // hook up listener on report content to get the plot events
            $scope.$parent.$parent.$parent.$on('sr-plotLinked', event => {
                const reportScope = event.targetScope;
                if (reportScope.modelName.indexOf('analysisReport') >= 0) {
                    initAnalysisReport(reportScope);
                }
                else if (reportScope.modelName.indexOf('fftReport') >= 0) {
                    // it may be useful to have the fftReport scope available
                    //fftReport = reportScope;
                }
            });

            $scope.$on('$destroy', () => {
                $('.scatter-point').popover('destroy');
            });

            $scope.$on(modelKey + '.summaryData', (e, data) => {
                let str = '';
                if (data.p_vals) {
                    const pNames = ($scope.model().fitParameters || '').split(/\s*,\s*/);
                    const pVals = data.p_vals.map(roundTo3Places);
                    const pErrs = data.p_errs.map(roundTo3Places);
                    pNames.forEach((p, i) => {
                        str = str + p + ' = ' + pVals[i] + ' ± ' + pErrs[i];
                        str = str + (i < pNames.length - 1 ? '; ' : '');
                    });
                }
                $($element).closest('.panel-body').find('.focus-hint').text(str);
            });

            appState.watchModelFields($scope, [modelKey + '.action'], processTrimRange);
            appState.watchModelFields($scope, [modelKey + '.clusterMethod', modelKey + '.action'], processClusterMethod);
            processClusterMethod();
        },
    };
});

SIREPO.app.directive('analysisParameter', function(appState, activaitService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            isOptional: '@',
        },
        template: `
            <select class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in parameterValues()"></select>
        `,
        controller: function($scope) {
            $scope.parameterValues = () => {
                return activaitService.buildParameterList($scope.isOptional)
                    .filter(v => {
                        return (appState.models.columnInfo.selected || [])[v[0]];
                    });
            };
        },
    };
});

SIREPO.app.directive('columnReports', function(appState, activaitService) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div data-ng-repeat="report in reports track by report.columnNumber">
              <div class="col-sm-3 col-xl-2">
                <div class="sr-height-panel" data-report-panel="parameter" data-model-name="fileColumnReport" data-model-data="report.data" data-panel-title="{{ report.title }}" data-ng-style="reportStyle">
                  <button data-ng-click="closeReport(report.columnNumber)" title="close" type="button" class="close" style="position: absolute; top: 55px; right: 25px">
                    <span>&times;</span>
                  </button>
                  <div>{{ computeHeight() }}</div>
                  <form class="form-horizontal">
                    <div class="form-group form-group-sm" data-model-field="\'x\'" data-model-name="\'fileColumnReport\'" data-model-data="report.data" data-label-size="4" data-field-size="8"></div>
                  </form>
                </div>
              </div>
            </div>
        `,
        controller: function($scope, $element) {
            $scope.reportStyle = {
                'min-height': 0,
            };

            $scope.computeHeight = () => {
                let maxHeight = 0;
                $($element).find('.sr-height-panel').each((f, el) => {
                    const h = $(el).children().first().height();
                    if (h > maxHeight) {
                        maxHeight = h;
                    }
                });
                //TODO(pjm): 20 is the margin bottom. needs improvements
                $scope.reportStyle['min-height'] = (maxHeight + 20) + 'px';
            };

            function setReports() {
                $scope.reports = [];
                appState.models.columnReports.forEach(idx => {
                    const modelKey = activaitService.columnReportName(idx);
                    $scope.reports.push(activaitService.reportInfo(modelKey, 'Column ' + (idx + 1), idx));
                });
            }

            $scope.closeReport = function(closeIdx) {
                const reports = [];
                appState.models.columnReports.forEach(idx => {
                    if (idx != closeIdx) {
                        reports.push(idx);
                    }
                });
                appState.models.columnReports = reports;
                appState.saveChanges('columnReports');
            };

            $scope.$on('columnReports.changed', setReports);
            setReports();
        },
    };
});

SIREPO.app.directive('xColumn', function(appState, activaitService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <div class="col-sm-8">
            <select class="form-control" data-ng-model="model[field]" data-ng-change="columnChanged()" data-ng-options="item as header(item) for item in getItems()"></select>
            </div>
        `,
        controller: function($scope) {
            $scope.appState = appState;
            $scope.columnChanged = () => {
                appState.saveChanges(activaitService.columnReportName($scope.model.columnNumber));
            };
            $scope.header = item => {
                if (appState.isLoaded()) {
                    if (item == -1) {
                        return 'occurrence';
                    }
                    return appState.models.columnInfo.header[item];
                }
            };
            $scope.getItems = () => {
                if (appState.isLoaded()) {
                    if (! $scope.items) {
                        $scope.items = [-1];
                        const info = appState.models.columnInfo;
                        if (! info.header) {
                            return $scope.items;
                        }
                        info.header.forEach((h, idx) => {
                            if (! info.colsWithNonUniqueValues[h]) {
                                $scope.items.push(idx);
                            }
                        });
                    }
                }
                return $scope.items;
            };
            $scope.$on('modelChanged', () => {
                $scope.items = null;
            });
        },
    };
});

SIREPO.app.directive('clusterFields', function(appState, activaitService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <div style="margin: -3px 0 5px 0; min-height: 34px; max-height: 13.4em; overflow-y: auto; border: 1px solid #ccc; border-radius: 4px">
              <table class="table table-condensed table-hover" style="margin:0">
                <tbody>
                  <tr data-ng-repeat="item in itemList() track by item.index" data-ng-click="toggleItem(item)">
                    <td>{{ item.name }}</td>
                    <td><input type="checkbox" data-ng-checked="isSelected(item)"></td>
                  </tr>
                </tbody>
              </table>
            </div>
        `,
        controller: function($scope) {
            let itemList, paramList;

            $scope.isSelected = item => {
                const v = $scope.model[$scope.field] || [];
                return v[item.index];
            };

            $scope.itemList = () => {
                const params = activaitService.buildParameterList();
                if (paramList != params) {
                    paramList = params;
                    itemList = [];
                    paramList.forEach(param => {
                        itemList.push({
                            name: param[1],
                            index: parseInt(param[0]),
                        });
                    });
                }
                return itemList;
            };

            $scope.toggleItem = item => {
                const v = $scope.model[$scope.field] || [];
                v[item.index] = ! v[item.index];
                $scope.model[$scope.field] = v;
            };
        },
    };
});

SIREPO.app.directive('columnSelector', function(appState, activaitService, panelState) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <form name="form">
              <table style="width: 100%; table-layout: fixed; margin-bottom: 10px" class="table table-hover">
                <colgroup>
                  <col style="width: 3em">
                  <col style="width: 100%">
                  <col style="width: 6em">
                  <col style="width: 6em">
                  <col style="width: 6em">
                  <col style="width: 6em">
                </colgroup>
                <thead>
                  <tr>
                    <th> </th>
                    <th data-ng-if="! isImageData">Column Name</th>
                    <th data-ng-if="isImageData">Data Path</th>
                    <th data-ng-show="isImageData">Shape</th>
                    <th data-ng-show="! isAnalysis" class="text-center">Input</th>
                    <th data-ng-show="! isAnalysis" class="text-center">Output</th>
                    <th data-ng-show="isAnalysis" class="text-center"><span class="glyphicon glyphicon-filter"></span></th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr data-ng-show="! isImageData">
                    <td> </td><td> </td>
                    <td data-ng-repeat="(k, g) in selectionGroups" data-ng-show="groupVisible(g)" class="text-center"><input data-ng-model="g.val" type="checkbox" class="sr-checkbox" data-ng-click="toggleGroup(k)"/></td>
                    <td> </td>
                  </tr>
                  <tr data-ng-repeat="col in getPage() track by col">
                    <td class="form-group form-group-sm"><p class="form-control-static">{{ col + 1 }}</p></td>
                    <td data-ng-if="! isImageData" class="form-group form-group-sm">
                      <input data-ng-model="model.header[col]" class="form-control" data-lpignore="true" required />
                    </td>
                    <td data-ng-if="isImageData" class="form-group">
                      <p class="form-control-static">{{ model.header[col] }}</p>
                    </td>
                    <td data-ng-show="isImageData" style="white-space: nowrap">
                      <p class="form-control-static">{{ model.shape[col].join(', ') }}</p>
                    </td>
                    <td data-ng-show="! isAnalysis" class="text-center">
                      <input data-ng-model="model.inputOutput[col]" class="sr-checkbox" data-ng-true-value="\'input\'" data-ng-false-value="\'none\'" type="checkbox" />
                    </td>
                    <td data-ng-show="! isAnalysis" class="text-center">
                      <input data-ng-model="model.inputOutput[col]" class="sr-checkbox" data-ng-true-value="\'output\'" data-ng-false-value="\'none\'" type="checkbox" />
                    </td>
                    <td data-ng-show="isAnalysis" class="text-center">
                      <input data-ng-model="model.selected[col]" class="sr-checkbox" type="checkbox" data-ng-click="validateNumSelected(col)"/>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div class="sr-input-warning"></div>
              <div class="col-sm-12 text-center" data-buttons="" data-model-name="modelName" data-fields="fields"></div>
            </form>
            <nav class="pull-right">
              <span>{{ pageText() }}&nbsp;&nbsp;</span>
              <ul data-ng-if="pageText()" class="pagination">
                <li class="page-item"><button type="button" class="btn btn-outline-info" data-ng-disabled="pageIdx < 1" data-ng-click="changePage(-1)"><<</button></li>
                <li class="page-item"><button type="button" class="btn btn-outline-info" data-ng-disabled="pageIdx > pages.length - 2" data-ng-click="changePage(1)">>></button></li>
              </ul>
            </nav>
        `,
        controller: function($scope, $sce) {
            $scope.modelName = 'columnInfo';
            $scope.fields = ['header', 'inputOutput'];
            $scope.isAnalysis = false;
            $scope.isImageData = false;
            $scope.pages= [];
            $scope.pageIdx = 0;
            $scope.selectionGroups = {
                input: {
                    falseVal: 'none',
                    modelKey: 'inputOutput',
                    trueVal: 'input',
                    val: false,
                },
                output: {
                    falseVal: 'none',
                    modelKey: 'inputOutput',
                    trueVal: 'output',
                    val: false,
                },
                selected: {
                    falseVal: false,
                    modelKey: 'selected',
                    trueVal: true,
                    val: false,
                },
            };

            const pageSize = 10;
            const radioGroups = {
                inputOutput: ['input', 'output'],
            };

            function changeReports() {
                $scope.pages.map((page, i) => {
                    page.map((idx) => {
                        const pos = appState.models.columnReports.indexOf(idx);
                        if (i === $scope.pageIdx && pos < 0) {
                            appState.models.columnReports.push(idx);
                            const m = activaitService.columnReportName(idx);
                            if (panelState.isHidden(m)) {
                                panelState.toggleHidden(m);
                            }
                        }
                        else if (i !== $scope.pageIdx && pos >= 0) {
                            appState.models.columnReports.splice(pos, 1);
                        }
                    });
                });
                appState.saveChanges('columnReports');
            }

            // if all members of a group are true, set the group true.
            // Otherwise false
            function resetGroups() {
                for (let gName in $scope.selectionGroups) {
                    let g = $scope.selectionGroups[gName];
                    const t = g.trueVal;
                    const m = g.modelKey;
                    g.val = appState.models.columnInfo[m].every(v => v === t);
                }
            }

            function setModel() {
                $scope.model = appState.models.columnInfo;
                const c = appState.models.columnInfo;
                if (! c.header) {
                    return;
                }
                if (! appState.models.columnInfo.selected) {
                    appState.models.columnInfo.selected = [];
                }
                let p = 0;
                $scope.pages = [[]];
                for (let i = 0; i < c.header.length; i++) {
                    if (c.colsWithNonUniqueValues.hasOwnProperty(c.header[i])) {
                        continue;
                    }
                    if ($scope.pages[p].length === pageSize) {
                        $scope.pages[++p] = [];
                    }
                    $scope.pages[p].push(i);
                    const m = activaitService.columnReportName(i);
                    if (! appState.models[m]) {
                        appState.models[m] = appState.setModelDefaults({
                            columnNumber: i,
                        }, 'fileColumnReport');
                        appState.saveQuietly(m);
                    }
                    if (angular.isUndefined(appState.models.columnInfo.selected[i])) {
                        appState.models.columnInfo.selected[i] = true;
                    }
                }
                changeReports();
                resetGroups();
                $scope.validateNumSelected();
            }

            function updateIsAnalysis() {
                $scope.isAnalysis = activaitService.isAnalysis();
                $scope.isImageData = activaitService.isImageData();
                $scope.validateNumSelected();
            }

            $scope.changePage = change => {
                $scope.pageIdx += change;
                changeReports();
            };

            $scope.getPage = () => {
                if ($scope.pages.length === 0) {
                    return [];
                }
                return $scope.pages[$scope.pageIdx];
            };

            $scope.groupVisible = g => {
                return g.modelKey === 'inputOutput' ? ! $scope.isAnalysis : $scope.isAnalysis;
            };

            $scope.pageText = () => {
                const p = $scope.pages[$scope.pageIdx];
                if (! p) {
                    return '';
                }
                const l = $scope.pages[$scope.pages.length - 1];
                if (p[0] == 0 && p.length == l.length) {
                    return '';
                }
                return `Columns ${p[0] + 1} - ${p[p.length - 1] + 1} of ${l[l.length - 1] + 1 }`;
            };

            $scope.toggleGroup = gName => {
                let g = $scope.selectionGroups[gName];
                let p = $scope.model[g.modelKey];
                for (let c in p) {
                    p[c] = g.val ? g.falseVal : g.trueVal;
                }
                for (let rg of radioGroups[g.modelKey] || []) {
                    if (rg === gName) {
                        continue;
                    }
                    if (! g.val) {
                        $scope.selectionGroups[rg].val = false;
                    }
                }
                $scope.validateNumSelected();
            };

            $scope.validateNumSelected = c => {
                const b = $('div[data-column-selector] button.btn-primary')[0];
                const w = $('div[data-column-selector] .sr-input-warning').text('').hide();
                const msg = 'Select at least 2 columns';
                b.setCustomValidity('');
                if (! $scope.isAnalysis || ! $scope.model.selected) {
                    return;
                }
                let nv =  $scope.model.selected.filter((s, sIdx) => {
                    return ! angular.isUndefined(c) && c === sIdx ? ! s  : s;
                }).length;
                if (nv < 2) {
                    b.setCustomValidity(msg);
                    w.text(msg).show();
                }
            };

            setModel();
            updateIsAnalysis();
            $scope.$on('columnInfo.changed', setModel);
            $scope.$on('cancelChanges', (evt, name) => {
                if (name == 'columnInfo') {
                    setModel();
                }
            });
            $scope.$on('dataFile.changed', updateIsAnalysis);
        },
    };
});

SIREPO.app.directive('imageViewer', function(appState, plotting) {
    return {
        scope: {
            modelName: "@"
        },
        template: `
          <div data-ng-if="imageInfo">
              <div data-image-preview="imageInfo"></div>
          </div>
        `,
        controller: function($scope) {
            plotting.setTextOnlyReport($scope);
            $scope.load = function(json) {
                $scope.imageInfo = json.images;
                $scope.imageInfo.method = "imagePreview";
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('imagePreviewPanel', function(appState, requestSender) {
    return {
        restrict: 'A',
        scope: {
            method: '@',
            comparisonId: '=',
        },
        template: `
        <div class="container-fluid">
          <div data-ng-if="isLoading" data-sim-state-progress-bar="" data-sim-state="simState"></div>
          <div data-ng-if="imageInfo">
              <div data-image-preview="imageInfo"></div>
          </div>
        </div>
        `,
        controller: function($scope, $element) {
            $scope.isLoading = true;
            const f = $scope.method == 'imagePreview' ? requestSender.sendStatefulCompute : requestSender.sendAnalysisJob;
            f(
                appState,
                response => {
                    $scope.isLoading = false;
                    response.method = $scope.method;
                    $scope.imageInfo = response;
                },
                {
                    method: 'sample_images',
                    modelName: 'animation',
                    args: {
                        method: $scope.method,
                        imageFilename: 'sample',
                        dataFile: appState.applicationState().dataFile,
                        columnInfo: appState.applicationState().columnInfo,
                        otherSimId: $scope.comparisonId ? $scope.comparisonId : null,
                    }
                }
            );
        }
    };
});

SIREPO.app.directive('imagePreview', function(appState, requestSender, panelState) {
    return {
        restrict: 'A',
        scope: {
            imageInfo: '=imagePreview',
        },
        template: `
          <div data-ng-if="dataFileMissing">Data file {{ fileName }} is missing</div>
          <div data-ng-if="colA" class="row">
            <div class="{{ colClass() }}">
              <div class="lead text-center">{{ colAName }}</div>
            </div>
            <div class="{{ colClass() }}">
              <div class="lead text-center">{{ colBName }}</div>
            </div>
            <div data-ng-if="hasThirdColumn" class="col-md-4">
              <div class="lead text-center">{{ predColName }}</div>
            </div>
          </div>
          <div data-ng-repeat="image in pageImages">
            <div class="row">
              <div class="{{ colClass() }}">
                <img class="img-responsive colA{{ method + ($index + 1) }}" />
                <div data-ng-if="xIsParams"> <br/> <b>{{ parameters[$index] }}</b> </div>
              </div>
              <div class="{{ colClass() }}">
                <img class="img-responsive colB{{ method + ($index + 1) }}" />
                <div data-ng-if="imageToLabels" class="text-center"> <br/> <b>{{ labels[$index] }}</b> </div>
              </div>
              <div data-ng-if="hasThirdColumn" class="col-md-4">
                <img class="img-responsive pred{{ method + ($index + 1) }}" />
              </div>
            </div>
          </div>
          <div data-ng-if="multiPage">
            <div data-ng-if="numPages > 1" class="pull-left">
              <button class="btn btn-primary" title="first" data-ng-disabled="! canUpdateUri(-1)" data-ng-click="first()">|<</button>
              <button class="btn btn-primary" title="previous" data-ng-disabled="! canUpdateUri(-1)" data-ng-click="prev()"><</button>
            </div>
            <div data-ng-if="numPages > 1" class="pull-right">
                page {{ page() }} of {{ numPages }}
              <button class="btn btn-primary" title="next" data-ng-disabled="! canUpdateUri(1)" data-ng-click="next()">></button>
              <button class="btn btn-primary" title="last" data-ng-disabled="! canUpdateUri(1)" data-ng-click="last()">>|</button>
            </div>
          </div>
        `,
        controller: function($scope, $element) {
            $scope.numPages = 0;
            $scope.imagesPerPage = 3;
            $scope.pageImages = SIREPO.UTILS.indexArray($scope.imagesPerPage);
            $scope.colA = null;
            $scope.colB = null;
            $scope.pred = null;
            $scope.colAName = 'Image';
            $scope.colBName = 'Contour';
            $scope.predColName = 'Predicted';
            $scope.imageIdx = 0;
            $scope.dataFileMissing = false;
            $scope.hasThirdColumn = true;

            const pageIndex = () => $scope.imageIdx / $scope.imagesPerPage;

            $scope.page = () => Math.floor($scope.imageIdx / $scope.imagesPerPage) + 1;

            $scope.canUpdateUri = (increment) => {
                return $scope.imageIdx + increment >= 0 && pageIndex() + increment < $scope.numPages;
            };

            $scope.first = () => {
                setIndex($scope.imageIdx = 0);
            };

            $scope.last = () => {
                setIndex($scope.imageIdx = $scope.numPages * $scope.imagesPerPage - $scope.imagesPerPage);
            };

            $scope.next = () => {
                setIndex($scope.imageIdx += $scope.imagesPerPage);
            };

            $scope.prev = () => {
                setIndex($scope.imageIdx -= $scope.imagesPerPage);
            };

            $scope.colClass = () => `col-md-${$scope.hasThirdColumn ? '4' : '6'}`;

            function imageInRange(firstImageIndex, rowIndex) {
                return firstImageIndex + rowIndex + 1 <= $scope.colA.length;
            }

            function setColumnImage(firstImageIndex, rowIndex, column) {
                let isTextCol = column == 'A' ? $scope.xIsParams : $scope.imageToLabels;
                let textCol = column == 'A' ? $scope.parameters : $scope.labels;
                if (isTextCol) {
                    if (imageInRange(firstImageIndex, rowIndex)) {
                        const value = column == 'A' ? `${$scope.colA[firstImageIndex + rowIndex].replace(/[\[\]]/g, '')}` : $scope.colB[firstImageIndex + rowIndex];
                        textCol.splice(rowIndex, 0, value);
                        return;
                    }
                    textCol.splice(rowIndex, 0, '');
                    return;
                }
                const colSelector = $($element).find(`.col${column}${$scope.method}${rowIndex + 1}`)[0];
                if (imageInRange(firstImageIndex, rowIndex)) {
                    const value = column == 'A' ? $scope.colA[firstImageIndex + rowIndex] : $scope.colB[firstImageIndex + rowIndex];
                    colSelector.src = value;
                    return;
                }
                colSelector.src = '';
            }

            function setThirdColumnImage(firstImageIndex, rowIndex) {
                $scope.hasThirdColumn = $scope.pred != null;
                if ($(`.pred${$scope.method}1`).length && $scope.hasThirdColumn) {
                    const colSelector = $($element).find(`.pred${$scope.method}${rowIndex + 1}`)[0];
                    if (imageInRange(firstImageIndex, rowIndex)) {
                        colSelector.src = $scope.pred[firstImageIndex + rowIndex];
                        return;
                    }
                    colSelector.src = '';
                }
            }

            function setIndex(firstImageIndex) {
                if ($(`.colA${$scope.method}1`).length && $scope.colA) {
                    $scope.pageImages.forEach( (rowIndex) => {
                        setColumnImage(firstImageIndex, rowIndex, 'A');
                        setColumnImage(firstImageIndex, rowIndex, 'B');
                        setThirdColumnImage(firstImageIndex, rowIndex);

                    });
                }
                if (! $scope.colA) {
                    $scope.dataFileMissing = true;
                    $scope.fileName = appState.models.dataFile.file;
                }
            }

            // .colAimagePreview1
            function initFromResponse(response) {
                $scope.method = response.method;
                $scope.numPages = Math.ceil(response.colA.length / $scope.imagesPerPage);
                $scope.colA = response.colA;
                $scope.colB = response.colB;
                $scope.xIsParams = response.xIsParameters;
                $scope.imageToLabels = response.imageToLabels;
                $scope.pred = response.pred || null;
                if ($scope.xIsParams) {
                    $scope.parameters = [];
                }
                if ($scope.imageToLabels) {
                    $scope.labels = [];
                    $scope.colBName = 'Labels';
                }
                if ($scope.colA) {
                    $scope.multiPage = $scope.colA.length > 1;
                    panelState.waitForUI(() => setIndex(0));
                }
                if (response.paramToImage) {
                    if (! response.xIsParameters) {
                        $scope.colBName = 'Prediction';
                        return;
                    }
                    $scope.colAName = 'Parameters';
                    $scope.colBName = 'Images';
                }
            }
            initFromResponse($scope.imageInfo);
        }
    };
});

SIREPO.app.directive('equation', function(appState, activaitService, $timeout) {
    return {
        scope: {
            model: '=',
            field: '=',
            form: '=',
        },
        template: `
            <div>
                <input type="text" data-ng-change="validateAll()" data-ng-model="model[field]" class="form-control" required>
                <input type="checkbox" data-ng-model="model.autoFill" data-ng-change="validateAll()"> Auto-fill variables
            </div>
        `,
        controller: function ($scope) {

            const defaultFitVars = ['x', 'y', 'z', 't'];

            function tokenizeEquation() {
                return activaitService.tokenizeEquation($scope.model[$scope.field]);
            }

            function extractParams() {

                const params = activaitService.tokenizeParams($scope.model.fitParameters).sort();
                const tokens = tokenizeEquation().filter(t => t !== $scope.model.fitVariable);

                // remove parameters no longer in the equation
                params.reverse().forEach( (p, i) => {
                    if (tokens.indexOf(p) < 0) {
                        params.splice(i, 1);
                    }
                });

                // add tokens not represented
                tokens.forEach(t => {
                    if (params.indexOf(t) < 0) {
                        params.push(t);
                    }
                });
                params.sort();

                return params;
            }

            function extractVar() {
                const tokens = tokenizeEquation();
                let indVar = $scope.model.fitVariable;

                if (! indVar|| tokens.indexOf(indVar) < 0) {
                    indVar = null;
                    tokens.forEach(t => {
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

            $scope.validateAll = () => {
                if ($scope.model.autoFill) {
                    // allow time for models to be set before validating
                    $timeout(() => {
                        $scope.model.fitVariable = extractVar();
                        $scope.model.fitParameters = extractParams().join(',');
                    });
                }

                $scope.form.$$controls.forEach(c => {
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
        template: `
            <div>
                <input type="text" data-ng-model="model[field]" data-valid-variable-or-param="" class="form-control" required />
            </div>
            <div class="sr-input-warning" data-ng-show="warningText.length > 0">{{warningText}}</div>
        `,
    };
});

SIREPO.app.directive('fftReport', function(appState) {
    return {
        scope: {
            modelData: '=',
        },
        template: `
            <div data-advanced-editor-pane data-model-data="modelData" data-view-name="modelKey" data-want-buttons="1"></div>
            <div data-report-content="parameter" data-model-key="{{ modelKey }}"></div>
        `,
        controller: function($scope, $element) {
            $scope.modelKey = 'fftReport';
            if ($scope.modelData) {
                $scope.modelKey += appState.models[$scope.modelData.modelKey].id;
            }

            $scope.$on($scope.modelKey + '.summaryData', (e, data) => {
                let str = '';
                data.freqs.forEach((wi, i) => {
                    if (str == '') {
                        str = 'Found frequncies: ';
                    }
                    const w = wi[1];
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

            $scope.$parent.$parent.$parent.$on('sr-plotLinked', event => {
                analysisReport = event.targetScope;
                svg = analysisReport.select("svg");
                const oldResize = analysisReport.resize;
                analysisReport.resize = () => {
                    oldResize();
                    removeUnusedElements();
                    addTicks();
                    addResultNumbers();
                };

                const oldLoad = analysisReport.load;
                analysisReport.load = json => {
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
        template: `
            <div class="text-center">
            <div class="btn-group">
              <button class="btn sr-enum-button" data-ng-repeat="item in enumValues" data-ng-click="model[field] = item[0]" data-ng-class="{\'active btn-primary\': isSelectedValue(item[0]), \'btn-default\': ! isSelectedValue(item[0])}">{{ item[1] }}</button>
            </div>
            </div>
        `,
        controller: function($scope) {
            $scope.enumValues = SIREPO.APP_SCHEMA.enum.PlotAction;

            $scope.isSelectedValue = value => {
                if ($scope.model && $scope.field) {
                    return $scope.model[$scope.field] == value;
                }
                return false;
            };
        },
    };
});

SIREPO.app.directive('activaitSimList', function(appState, requestSender) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
          <div data-sim-list="" data-model="model" data-field="field" data-code="activait"></div>
        `,
        controller: function($scope) {
            const requestSimListByType = (simType) => {
                requestSender.sendRequest(
                    'listSimulations',
                    () => {},
                    {
                        simulationType: simType,
                    }
                );
            };
            requestSimListByType('activait');
        },
    };
});

SIREPO.app.controller('PartitionController', function (appState, activaitService, $scope) {
    const self = this;
    self.reports = [];

    function loadReports() {
        if (! activaitService.isTextData()) {
            return;
        }
        appState.models.columnInfo.inputOutput.forEach((type, idx) => {
            if (type == 'none') {
                return;
            }
            const modelKey = activaitService.partitionReportName(idx);
            appState.models[modelKey] = {
                columnNumber: idx,
            };
            appState.saveQuietly(modelKey);
            self.reports.push(activaitService.reportInfo(modelKey, type.charAt(0).toUpperCase() + type.slice(1) + ' ' + (idx + 1), idx));
        });
    }

    $scope.showPartitionSelection = () => {
        if (appState.isLoaded()) {
            if (! activaitService.isTextData()) {
                return false;
            }
            if (activaitService.isAppMode('regression')) {
                return appState.applicationState().partition.method == 'selection';
            }
        }
        return false;
    };

    loadReports();
});

SIREPO.app.directive('modelDownloadLink', function(appState, frameCache, requestSender) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: `
            <div class="container-fluid">
              <a data-ng-if="frameCache.hasFrames('epochAnimation')" style="position: relative; text-align: center;" href="{{ logFileURL() }}" target="_blank">  Download {{ modelType }} model</a>
            </div>
        `,
        controller: function($scope) {
            $scope.frameCache = frameCache;
            $scope.modelType = $scope.modelName == "neuralNetLayer" ? "unweighted" : "weighted";

            $scope.logFileURL = () => {
                return logFileRequest();
            };

            function logFileRequest() {
                return  requestSender.formatUrl('downloadRunFile', {
                    '<simulation_id>': appState.models.simulation.simulationId,
                    '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                    '<model>': 'animation',
                    '<frame>': SIREPO.nonDataFileFrame,
                    '<suffix>': $scope.modelName,
                });
            }
        },
    };
});

SIREPO.app.directive('neuralNetLayersForm', function(appState, stringsService) {
    return {
        restrict: 'A',
        scope: {
            layerTarget: '=',
            childIndex: '=',
            parentLayer: '=',
        },
        template: `
            <form name="form" class="form-horizontal">
              <div class="form-group form-group-sm">
              <button class="add-remove-child-btn" data-ng-if="removableChild()" data-ng-click="removeChild(childIndex)"> Remove this child </button>
                <table class="table table-striped table-condensed" style="border: 2px solid #8c8b8b; position: relative;">
                  <tr data-ng-repeat="layer in layerLevel track by $index + layerId" data-ng-init="layerIndex = $index">
                    <td data-ng-repeat="fieldInfo in layerInfo(layerIndex) track by fieldTrack(layerIndex, $index) + layerId">
                      <div data-ng-if="fieldInfo.field">
                        <b>{{ fieldInfo.label }} </b>
                        <div class="row" data-field-editor="fieldInfo.field" data-field-size="12" data-model-name="layerName(layer)" data-model="layer"></div>
                        <div data-ng-if="branching(layer)">
                         <button class="add-remove-child-btn" data-ng-click="addChild(layer)">Add another child</button>
                        </div>
                      </div>
                    </td>
                    <td colspan="100%">
                      <div data-ng-if="checkBranch(layer)">
                        <div data-ng-repeat="l in layer.children track by $index + layerId" class="ml-sub-table" data-parent-layer="layer" data-neural-net-layers-form="" data-child-index="$index" data-layer-target="l"></div>
                      </div>
                    </td>
                    <td colspan="100%">
                      <div class="sr-nn-button-bar-parent pull-right">
                        <div class="ml-button-bar">
                          <button class="btn btn-info btn-xs" data-ng-disabled="$index == 0" data-ng-click="moveLayer(-1, $index)">
                            <span class="glyphicon glyphicon-arrow-up"></span>
                          </button>
                          <button class="btn btn-info btn-xs" data-ng-disabled="$index == layerLevel.layers.length - 1" data-ng-click="moveLayer(1, $index)">
                            <span class="glyphicon glyphicon-arrow-down"></span>
                          </button>
                          <button data-ng-click="deleteLayer($index)" class="btn btn-danger btn-xs">
                            <span class="glyphicon glyphicon-remove"></span>
                          </button>
                        </div>
                      </div>
                    </td>
                  <tr>
                    <td>
                      <b>Add Layer</b>
                        <select class="form-control" data-ng-model="selectedLayer" data-ng-options="item[0] as item[1] for item in layerEnum" data-ng-change="addLayer()"></select>
                    </td>
                    <td colspan="100%"></td>
                    <td colspan="100%"></td>
                  </tr>
                </table>
                <div data-ng-if="root()">
                    <table class="table table-striped table-condensed" style="border: 2px solid #8c8b8b;">
                        <tr style="display: flex;">
                        <td>
                            <b>Output Layer</b>
                            <p class="form-control-static">Densely Connected NN</p>
                        </td>
                        <td>
                            <b>Dimensionality</b>
                            <p class="form-control-static text-right">{{ outputColCount()  }}</p>
                        </td>
                        <td>
                            <b>Activation</b>
                            <p class="form-control-static">Linear (identity)</p>
                        </td>
                        </tr>
                    </table>
                   <div data-model-download-link="" data-model-name="neuralNetLayer"></div>
                </div>
              </div>
              <div class="col-sm-6 pull-right" data-ng-show="hasChanges()">
                <button data-ng-click="saveChanges()" class="btn btn-primary sr-button-save-cancel" data-ng-disabled="! form.$valid">Save</button>
                <button data-ng-click="cancelChanges()" class="btn btn-default sr-button-save-cancel">Cancel</button>
              </div>
            </form>
        `,
        controller: function($scope, $element) {
            const layerFields = {};
            const layerInfo = [];
            $scope.form = angular.element($($element).find('form').eq(0));
            $scope.selectedLayer = '';
            $scope.layerEnum = SIREPO.APP_SCHEMA.enum.NeuralNetLayer;
            $scope.layerLevel = getLayerLevel();
            $scope.layerId = 0;
            $scope.root = () => {
                return ! Boolean($scope.layerTarget);
            };
            $scope.addLayer = () => {
                if (! $scope.selectedLayer) {
                    return;
                }
                if (branchingLayer($scope.selectedLayer)) {
                    nest();
                    $scope.selectedLayer = '';
                    return;
                }
                const neuralNet = $scope.layerLevel;
                if (! neuralNet.layers) {
                    neuralNet.layers = [];
                }
                const m = appState.setModelDefaults({}, stringsService.lcfirst($scope.selectedLayer));
                m.layer = $scope.selectedLayer;
                neuralNet.push(m);
                $scope.selectedLayer = '';
            };

            $scope.checkBranch = layer => {
                const b = branchingLayer(layer.layer);
                if (b && layer.children !== null) {
                    return b;
                }
                layer.children = newChildren();
                return b;
            };

            $scope.removeChild = childIndex => {
                $scope.parentLayer.children.splice(childIndex, 1);
                $scope.form.$setDirty();
            };

            $scope.branching = layer =>  {
                return branchingLayer(layer.layer);
            };

            function branchingLayer(layer) {
                return (layer == 'Add') || (layer == 'Concatenate');
            }

            $scope.addChild = layer => {
                layer.children.push(newChild());
                $scope.form.$setDirty();
            };

            $scope.layerName = layer => {
                return stringsService.lcfirst(layer.layer);
            };

            $scope.cancelChanges = () => {
                appState.cancelChanges('neuralNet');
                $scope.form.$setPristine();
            };

            $scope.deleteLayer = idx => {
                $scope.layerLevel.splice(idx, 1);
                $scope.form.$setDirty();
            };

            $scope.fieldTrack = (layerIdx, idx) => {
                // changes the fields editor if the layer type changes
                const layer = $scope.layerLevel[layerIdx];
                return layer.layer + idx;
            };

            $scope.hasChanges = () => {
                if (! $scope.root()) {
                    return false;
                }
                if ($scope.form.$dirty) {
                    return true;
                }
                return appState.areFieldsDirty('neuralNet.layers');
            };

            $scope.layerInfo = idx => {
                if (! appState.isLoaded()) {
                    return layerInfo;
                }
                const layer = $scope.layerLevel[idx];
                layerInfo[idx] = layerFields[layer.layer];
                return layerInfo[idx];
            };

            $scope.moveLayer = (direction, currIdx) => {
                const n = $scope.layerLevel;
                n.splice(
                    currIdx + direction,
                    0,
                    n.splice(currIdx, 1)[0]
                );
                $scope.form.$setDirty();
            };

            $scope.outputColCount = () => {
                if (! appState.isLoaded()) {
                    return '';
                }
                return appState.applicationState().columnInfo.inputOutput.filter(
                    col => col === 'output'
                ).length;
            };

            $scope.saveChanges = () => {
                appState.saveChanges('neuralNet');
                $scope.form.$setPristine();
            };

            $scope.removableChild = () => {
                return ! $scope.root() && $scope.childIndex >= 2;
            };

            function buildLayerFields() {
                $scope.layerEnum.forEach(row => {
                    const name = row[0];
                    const cols = [
                        {
                            field: 'layer',
                            label: 'Layer',
                        },
                    ];
                    const layerSchema = SIREPO.APP_SCHEMA.model[stringsService.lcfirst(name)];
                    if (layerSchema) {
                        for (const f of SIREPO.APP_SCHEMA.view[stringsService.lcfirst(name)].columns) {
                            cols.push({
                                field: f,
                                label: layerSchema[f][0],
                            });
                        }
                    }
                    layerFields[name] = cols;
                });
            }

            function getLayerLevel() {
                if ($scope.layerTarget){
                    return $scope.layerTarget.layers;
                }
                return appState.models.neuralNet.layers;
            }

            function newChild() {
                return {layers: []};
            }

            function newChildren() {
                return [
                    newChild(),
                    newChild(),
                ];
            }

            function nest() {
                const n = {
                    layer: $scope.selectedLayer,
                    children: newChildren(),
                };
                $scope.layerLevel.push(n);
            }

            $scope.rebuildLayers = () => {
                if ($scope.$parent.rebuildLayers) {
                    // parent layer must be rebuilt so the new neuralNet model is referenced
                    $scope.$parent.rebuildLayers();
                }
                $scope.layerLevel = getLayerLevel();
                // layerId is a unique value used by angular "track by"
                $scope.layerId = Math.random();
            };

            $scope.$on('cancelChanges', (e, name) => {
                if (name == 'neuralNet') {
                    $scope.rebuildLayers();
                }
            });

            $scope.$on('neuralNet.changed', $scope.rebuildLayers);

            buildLayerFields();
        },
    };
});

SIREPO.app.directive('partitionSelection', function(appState) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <form name="form" class="form-horizontal" data-ng-style="formStyle">
              <div class="form-group form-group-sm">
                <div data-ng-repeat="field in fields track by $index" data-model-field="field" data-model-name="modelName" data-label-size="0" data-field-size="4"></div>
                <div data-ng-repeat="field in fields track by $index" class="col-sm-4">
                  <p class="form-control-static text-center">{{ selectedRange(field) }}</p>
                </div>
                <div data-ng-if="hasTrainingAndTesting()" data-model-field="\'trainTestPercent\'" data-model-name="\'partition\'"></div>
              </div>
              <div class="col-sm-12 text-center" data-buttons="" data-model-name="modelName" data-fields="allFields"></div>
            </form>
        `,
        controller: function($scope) {
            let dragCarat, plotRefresh, plotScope;
            $scope.modelName = 'partition';
            $scope.fields = ['section0', 'section1', 'section2'];
            $scope.allFields = $scope.fields.concat(['cutoff0', 'cutoff1']);
            $scope.formStyle = {};

            function validateCutoff(p) {
                const axis = plotScope.axes.x;
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
                const axis = plotScope.axes.x;
                const p = axis.scale.invert(d3.event.x);
                appState.models.partition[d] = validateCutoff(p);
                d3.select(this).call(updateCarat);
                $scope.$applyAsync();
            }

            function d3DragEndCarat(d) {
                const partition = appState.models.partition;
                if (partition.cutoff0 > partition.cutoff1) {
                    const c = partition.cutoff0;
                    partition.cutoff0 = partition.cutoff1;
                    partition.cutoff1 = c;
                }
                $scope.$applyAsync();
            }

            function drawCarats(parts) {
                const viewport = plotScope.select('.plot-viewport');
                viewport.selectAll('.activait-cell-selector').remove();
                viewport.selectAll('.activait-cell-selector')
                    .data(parts)
                    .enter().append('path')
                    .attr('class', 'activait-cell-selector')
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
                    .on('dragstart', () => {
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
                const axes = plotScope.axes;
                selection.attr('transform', d => {
                    const x = appState.models.partition[d];
                    return 'translate('
                        + axes.x.scale(x) + ',' + axes.y.scale(axes.y.scale.domain()[0])
                        + ')';
                });
            }

            function processSection(field) {
                // ensure all three values are selected
                const partition = appState.models.partition;
                if ($scope.hasTrainingAndTesting()) {
                    let count = 0;
                    $scope.fields.forEach(f => {
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
                let currentValue, missingValue;
                ['train', 'test', 'validate'].some(v => {
                    let hasValue = false;
                    $scope.fields.forEach(f => {
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
                    $scope.fields.forEach(f => {
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

            $scope.hasTrainingAndTesting = () => {
                if (! appState.isLoaded()) {
                    return;
                }
                const partition = appState.models.partition;
                return $scope.fields.some(f => partition[f] == 'train_and_test');
            };

            $scope.selectedRange = field => {
                if (! appState.isLoaded() || ! plotScope || ! plotScope.axes.x.domain) {
                    return;
                }
                const partition = appState.models.partition;
                if (field == 'section0') {
                    return '0 - ' + (partition.cutoff0 - 1);
                }
                if (field == 'section1') {
                    return partition.cutoff0 + ' - ' + (partition.cutoff1 - 1);
                }
                return partition.cutoff1 + ' - ' + (plotScope.axes.x.domain[1] - 1);
            };

            $scope.$parent.$parent.$parent.$on('sr-plotLinked', event => {
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
        template: `
            <div data-ng-if="! tableHeaders">
              <div class="lead">&nbsp;</div>
            </div>
            <div data-ng-if="tableHeaders">
              <div class="col-sm-12" style="margin-top: 1ex;">
                <table class="table">
                  <caption>{{ title }}</caption>
                  <thead>
                    <tr>
                      <th data-ng-repeat="h in tableHeaders">{{h}}</th>
                    </tr>
                  </thead>
                  <tr data-ng-repeat="r in tableRows" data-ng-bind-html=row(r)></tr>
                </table>
              </div>
            </div>
        `,
        controller: function($scope, $sce) {
            plotting.setTextOnlyReport($scope);
            $scope.row = (row) => {
                const r = [...row];
                let x = '<th>' + r.shift() + '</th>' + r.map(e => '<td>' + e + '</td>').join('');
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
            $scope.$on('framesCleared', () => {
                $scope.tableHeaders = null;
            });
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('trimButton', function(appState, activaitService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            modelName: '=',
        },
        template: `
            <div class="text-center">
              <button class="btn btn-default" data-ng-click="trimPlot()">Open in New Plot</button>
            </div>
        `,
        controller: function($scope) {
            $scope.trimPlot = () => {
                const action = {};
                ['action', 'trimField', 'trimMin', 'trimMax'].forEach(f => {
                    action[f] = $scope.model[f];
                });
                activaitService.addSubreport($scope.model, action);
                appState.cancelChanges($scope.modelName + ($scope.model.id || ''));
            };
        },
    };
});

SIREPO.viewLogic('mlModelView', function(appState, panelState, requestSender, $scope) {
    appState.models.mlModel.mlModule = 'neuralnet';
    panelState.showField('mlModel', 'modelFile', appState.models.mlModel.mlModule == 'modelFile');
    function displayFileInput() {
        if (appState.models.mlModel.mlModule == 'modelFile') {
            panelState.showField('mlModel', 'modelFile', true);
            return;
        }
        panelState.showField('mlModel', 'modelFile', false);
    }

    $scope.watchFields = [
        ['mlModel.mlModule'],
        displayFileInput
    ];

    $scope.$on('mlModel.changed', () => {
        if (appState.models.mlModel.mlModule == 'modelFile') {
            requestSender.sendStatelessCompute(
                appState,
                (data) => {
                    appState.models.neuralNet.layers = data.layers.slice(0, -1);
                    appState.models.mlModel.mlModule = 'neuralnet';
                    appState.saveChanges(['mlModel', 'neuralNet']);
                },
                {
                    method: 'load_keras_model',
                    args: {
                        file: appState.models.mlModel.modelFile
                    }
                },
                {
                    onError: data => {
                        throw new Error(data.error);
                    }
                }
            );
        }
    });
});

SIREPO.viewLogic('partitionView', function(activaitService, appState, panelState, $scope) {

    function updatePartitionMethod() {
        panelState.showField(
            'partition',
            'method',
            activaitService.isAppMode('regression') && !activaitService.isImageData()
        );
        const partition = appState.models.partition;
        ['training', 'testing'].forEach(f => {
            panelState.showField(
                'partition',
                f,
                activaitService.isAppMode('classification') || partition.method == 'random');
        });
        panelState.showField(
            'partition',
            'validation',
            activaitService.isAppMode('regression') && partition.method == 'random');
    }

    function updatePercents() {
        const partition = appState.models.partition;
        if (activaitService.isAppMode('classification')) {
            if (partition.training) {
                partition.testing = 100 - partition.training;
            }
            panelState.enableField('partition', 'testing', false);
        }
        else if (partition.training && partition.testing) {
            const validation = 100 - (partition.training + partition.testing);
            if (validation > 0) {
                partition.validation = parseFloat(validation.toFixed(2));
            }
        }
        panelState.enableField('partition', 'validation', false);
    }

    $scope.whenSelected = () => {
        updatePercents();
        updatePartitionMethod();
    };
    $scope.watchFields = [
        ['partition.training', 'partition.testing'], updatePercents,
        ['partition.method'], updatePartitionMethod,
    ];
});

SIREPO.viewLogic('dataFileView', function(activaitService, appState, panelState, requestSender, validationService, $scope) {

    const modelName = $scope.modelName;
    const self = this;

    showOrHideFieldRange();
    function showOrHideFieldRange() {
        const d = appState.models.dataFile;
        if (d.inputsScaler == 'MinMaxScaler' || d.outputsScaler == 'MinMaxScaler') {
            featureRangesOn(true);
            return;
        }
        featureRangesOn(false);
    }

    function featureRangesOn(display) {
        ['featureRangeMin', 'featureRangeMax'].forEach(f => {
            panelState.showField('dataFile', f, display);
        });
    }

    function computeColumnInfo() {
        const dataFile = appState.models.dataFile;
        if (! dataFile.file) {
            appState.models.columnReports = [];
            appState.saveChanges('columnReports');
            return;
        }
        if (dataFile.file === dataFile.oldFile) {
            return;
        }
        dataFile.oldFile = dataFile.file;
        appState.saveQuietly('dataFile');
        appState.models.columnInfo = {};
        appState.saveQuietly('columnInfo');
        requestSender.sendStatefulCompute(
            appState,
            data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                appState.models.columnInfo = data;
                computeDefaultPartition();
                appState.models.columnReports = [];
                appState.saveChanges(['columnInfo', 'columnReports', 'partition']);
            },
            {
                method: 'column_info',
                args: {
                    dataFile: dataFile,
                }
            }
        );
    }

    function computeDefaultPartition() {
        const size = appState.models.columnInfo.rowCount;
        const partition = appState.models.partition;
        if (! partition.cutoff0 || ! partition.cutoff1
            || partition.cutoff0 > size
            || partition.cutoff1 > size
        ) {
            partition.cutoff0 = parseInt(0.125 * size);
            partition.cutoff1 = parseInt((1 - 0.125) * size);
        }
    }

    function dataFileChanged() {
        const dataFile = appState.models.dataFile;
        updateEditor();
        computeColumnInfo();
        const partition = appState.models.partition;
        if (activaitService.isAppMode('regression')
            && partition.training + partition.testing >= 100) {
            ['training', 'testing', 'validation'].forEach(f => {
                delete partition[f];
            });
            appState.setModelDefaults(partition, 'partition');
        }
        else if (activaitService.isAppMode('classification')) {
            if (partition.training + partition.testing < 100) {
                partition.testing = 100 - partition.training;
            }
        }
        appState.saveQuietly('partition');
    }

    function processAppMode() {
        const m = appState.models.dataFile.appMode;
        panelState.showField(
            modelName, 'inputsScaler', m === 'regression' || m === 'classification');
        panelState.showField(
            modelName, 'outputsScaler', m === 'regression');
    }

    function updateEditor() {
        const dataFile = appState.models[modelName];
        const o = dataFile.dataOrigin;
        panelState.showField(modelName, 'file', o === 'file');
        panelState.showField(modelName, 'url', o === 'url');
        panelState.showField(modelName, 'dataOrigin', ! activaitService.hasDataFile());
        validateURL();
    }

    function validateURL() {
        const dataFile = appState.models[modelName];
        validationService.validateField(
            modelName,
            'url',
            'input',
            dataFile.dataOrigin === 'file' || ! ! dataFile.url,
            'Enter a url'
        );
    }

    function getRemoteData(callback) {
        requestSender.sendStatefulCompute(
            appState,
            result => {
                if (result.error) {
                    throw new Error(`Failed to retrieve remote data: ${result.error}`);
                }
                callback(result);
            },
            {
                method: 'get_remote_data',
                args: {
                    url: appState.models[modelName].url,
                }
            },
            //TODO(robnagler) what is supposed to be canceled?
            {
                onError: data => {
                    //TODO(mvkeilman): cancel
                }
            }
        );
    }

    function hasCachedDataList(cache) {
        return cache && cache.dataList && cache.dataList.length;
    }

    function updateData() {
        const dataFile = appState.models[modelName];
        const urlCache = appState.models.urlCache;

        //TODO(mvk): button to force reload; handle deletion of file; share files across users;
        // store urls; share urls across apps
        if (dataFile.dataOrigin === 'url') {
            dataFile.oldURL = dataFile.url;
            const f = urlCache[dataFile.url];
            if (f) {
                dataFile.file = f.file;
                dataFile.dataList = f.dataList;
                dataFile.bytesLoaded = f.size;
                dataFile.contentLength = f.size;
                appState.saveQuietly(modelName);
                dataFileChanged();
                return;
            }
            dataFile.bytesLoaded = 0;
            dataFile.contentLength = 0;
            dataFile.file = '';
            dataFile.dataList = [];
            appState.saveQuietly(modelName);
            getRemoteData(result => {
                urlCache[dataFile.url] = {
                    file: (dataFile.file = new URL(dataFile.url).pathname.split('/').pop()),
                    size: (dataFile.contentLength = result.size),
                };
                appState.saveChanges('urlCache');
                appState.saveQuietly(modelName);
                dataFileChanged();
            });
        }
        else {
            dataFileChanged();
        }
    }

    $scope.watchFields = [
        [`${modelName}.appMode`], processAppMode,
        [`${modelName}.dataOrigin`, `${modelName}.file`, `${modelName}.dataFormat`], updateEditor,
        [`${modelName}.url`], validateURL,
        [`${modelName}.inputsScaler`], showOrHideFieldRange,
        [`${modelName}.outputsScaler`], showOrHideFieldRange,
    ];

    $scope.whenSelected = () => {
        processAppMode();
        dataFileChanged();
        updateEditor();
    };

    $scope.$on( `${modelName}.changed`, updateData);
});
