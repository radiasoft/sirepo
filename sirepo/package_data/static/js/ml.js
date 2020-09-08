'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.PLOTTING_COLOR_MAP = 'blues';
    SIREPO.SINGLE_FRAME_ANIMATION = ['epochAnimation'];
    SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL = true;
    SIREPO.appReportTypes = [
        '<div data-ng-switch-when="classificationMetrics" data-table-panel="" data-model-name="{{ modelKey }}" class="sr-plot"></div>',
        '<div data-ng-switch-when="confusionMatrix" data-table-panel="" data-model-name="{{ modelKey }}" class="sr-plot"></div>',
    ].join('');
});

SIREPO.app.factory('mlService', function(appState) {
    var self = {};

    self.appModeIn = function(modes) {
        if(! appState.isLoaded()) {
            return;
        }
        return modes.includes(appState.applicationState().dataFile.appMode);
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

    self.partitionReportName = function(idx) {
        return 'partitionColumnReport' + idx;
    };

    self.isAnalysis = function() {
        return appState.isLoaded() && appState.applicationState().dataFile.appMode == 'analysis';
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

SIREPO.app.controller('DataController', function (appState, requestSender, $scope) {
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
                var info = appState.models.columnInfo;
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

SIREPO.app.directive('columnSelector', function(appState, mlService, panelState) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<form name="form">',
              '<table style="width: 100%; table-layout: fixed; margin-bottom: 10px" class="table table-hover">',
                '<colgroup>',
                  '<col style="width: 100%">',
                  '<col style="width: 6em">',
                  '<col style="width: 6em">',
                  '<col style="width: 6em">',
                '</colgroup>',
                '<thead>',
                  '<tr>',
                    '<th>Column Name</th>',
                    '<th data-ng-if="! isAnalysis()" class="text-center">Input</th>',
                    '<th data-ng-if="! isAnalysis()" class="text-center">Output</th>',
                    '<th></th>',
                  '</tr>',
                '</thead>',
                '<tbody>',
                  '<tr data-ng-repeat="col in model.header track by $index">',
                    '<td class="form-group form-group-sm">',
                      '<input data-ng-model="model.header[$index]" class="form-control" data-lpignore="true" required />',
                    '</td>',
                    '<td data-ng-if="! isAnalysis()" class="text-center">',
                      '<input data-ng-model="model.inputOutput[$index]" class="sr-checkbox" data-ng-true-value="\'input\'" data-ng-false-value="\'none\'" type="checkbox" />',
                    '</td>',
                    '<td data-ng-if="! isAnalysis()" class="text-center">',
                      '<input data-ng-model="model.inputOutput[$index]" class="sr-checkbox" data-ng-true-value="\'output\'" data-ng-false-value="\'none\'" type="checkbox" />',
                    '</td>',
                    '<td>',
                      '<a class="media-middle" href data-ng-click="togglePlot($index)">{{ showOrHideText($index) }}</a>',
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

            function setModel() {
                $scope.model = appState.models.columnInfo;
                if (! $scope.model.header) {
                    return;
                }
                $scope.model.header.forEach(function(header, idx) {
                    var modelKey = mlService.columnReportName(idx);
                    appState.models[modelKey] = {
                        columnNumber: idx,
                    };
                    appState.saveQuietly(modelKey);
                });
            }

            $scope.isAnalysis = mlService.isAnalysis;

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
                $scope.$on('columnInfo.changed', setModel);
                $scope.$on('cancelChanges', function(evt, name) {
                    if (name == 'columnInfo') {
                        setModel();
                    }
                });
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
