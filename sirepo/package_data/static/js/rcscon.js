'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.SINGLE_FRAME_ANIMATION = ['epochAnimation'];
});

SIREPO.app.factory('rcsconService', function(appState, panelState, frameCache) {
    var self = {};

    self.addAnimations = function(modelName, titlePrefix, countField, countOffset) {
        countOffset = countOffset || 0;
        var res = [];
        var files = appState.applicationState().files;
        for (var i = 0; i < files[countField]; i++) {
            var modelKey = modelName + (i + countOffset);
            if (! appState.models[modelKey]) {
                appState.models[modelKey] = {
                    columnNumber: i + countOffset,
                };
                if (modelName == 'partitionAnimation' && i >= 4) {
                    panelState.toggleHidden(modelKey);
                }
                appState.saveQuietly(modelKey);
            }
            res.push(self.reportInfo(modelKey, titlePrefix + ' ' + (i + 1)));
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
    };

    self.computeModel = function(analysisModel) {
        if (analysisModel.indexOf('partitionAnimation') >= 0) {
            return 'partitionAnimation';
        }
        return 'animation';
    };
    self.reportInfo = function(modelKey, title) {
        return {
            title: title,
            modelKey: modelKey,
            getData: function() {
                return appState.models[modelKey];
            },
        };
    };
    appState.setAppService(self);
    return self;
});

SIREPO.app.directive('appFooter', function() {
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

SIREPO.app.directive('appHeader', function(appState) {
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'visualization\')}"><a href data-ng-click="nav.openSection(\'visualization\')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
                  '<li class="sim-section" data-ng-if="hasFiles()" data-ng-class="{active: nav.isActive(\'partition\')}"><a href data-ng-click="nav.openSection(\'partition\')"><span class="glyphicon glyphicon-scissors"></span> Partition</a></li>',
                  '<li class="sim-section" data-ng-if="hasFilesAndPartition()" data-ng-class="{active: nav.isActive(\'machine-learning\')}"><a href data-ng-click="nav.openSection(\'machine-learning\')"><span class="glyphicon glyphicon-qrcode"></span> Machine Learning</a></li>',
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
            $scope.hasFiles = function() {
                if (appState.isLoaded()) {
                    var files = appState.applicationState().files;
                    return files.inputs && files.outputs;
                }
                return false;
            };

            $scope.hasFilesAndPartition = function() {
                if (! $scope.hasFiles()) {
                    return false;
                }
                return appState.applicationState().partition.method;
            };

            $scope.showImportModal = function() {
                $('#srw-simulation-import').modal('show');
            };
        },
    };
});

SIREPO.app.controller('MLController', function (appState, frameCache, persistentSimulation, rcsconService, utilities, $scope) {
    var self = this;

    function handleStatus(data) {
        self.reports = null;
        if ('percentComplete' in data && ! data.error) {
            if (data.percentComplete === 100 && ! self.simState.isProcessing()) {
                self.reports = rcsconService.addAnimations('fitAnimation', 'Fit', 'outputsCount');
            }
        }
        frameCache.setFrameCount(data.frameCount || 0);
    }

    self.display = function() {
        if (utilities.isFullscreen()) {
            utilities.exitFullscreenFn().call(document);
        }
        const el = $('#sr-ml-model-plot');
        el.modal('show');
        el.on('shown.bs.modal', function() {
            $scope.mlModelShown = true;
            $scope.$digest();
        });
        el.on('hidden.bs.modal', function() {
            $scope.mlModelShown = false;
            el.off();
        });
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

    self.hasFrames = function() {
        return frameCache.hasFrames();
    };

    self.hasLayers = function() {
        return ((appState.models.neuralNet || {}).layers || []).length > 0;
    };

    self.simState = persistentSimulation.initSimulationState(
        $scope,
        rcsconService.computeModel('fitAnimation'),
        handleStatus
    );
});

SIREPO.app.directive('mlModelGraph', function(appState, utilities) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            reportId: '<',
        },
        template: [
            '<div data-report-content="rawSVG" data-model-key="mlModelGraph" data-report-cfg="reportCfg">',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {

            const scale = 0.75;
            $scope.reportCfg = {
                reload: function () {
                    return true;
                },
                process: function(str) {

                    // for some reason the viewbox and size do not always match
                    const svg = $(str);
                    const width = $($element).width();
                    let w = utilities.fontSizeFromString(svg.attr('width'));
                    let h = utilities.fontSizeFromString(svg.attr('height'));

                    // jquery considers viewBox a property, not an attribute
                    let vb = svg.prop('viewBox').baseVal;

                    // fix the viewBox or the plot will be cut off
                    vb.width = w;
                    vb.height = h;

                    // resize
                    svg.attr('width', scale * w);
                    svg.attr('height', scale * h);

                    // re-center
                    const pd = utilities.fontSizeFromString(
                        $($element).find('div.panel-body').css('padding')
                    );

                    svg.attr('transform', 'translate(' + ((width - scale * w) / 2 - pd) + ', 0)');

                    // apply colors
                    const baseClass = 'rcscon-layer';

                    // keras adds text to the node boxes formatted as:
                    //     <layer_type>_<index>: <Layer Type>
                    const layers = appState.models.neuralNet.layers;
                    svg.find('g.node').each(function (idx) {
                        let node = $(this);

                        let txtEl = node.find('text').eq(0);
                        let txt = txtEl.text();

                        let cName = txt.substring(0, txt.indexOf(':'));
                        let p = node.find('polygon');
                        p.addClass(baseClass);
                        // input is named differently
                        if (cName.indexOf('_input') >= 0) {
                            p.addClass(baseClass + '-input');
                            return;
                        }
                        cName = cName.substring(0, cName.lastIndexOf('_')).replace('_', '-');
                        p.addClass(baseClass + '-' + cName);


                        // the input box is added by keras, and does not correspond to a layer
                        let layer = layers[idx - 1];
                        let lType = txt.substring(txt.indexOf(':') + 1).trim();
                        let pName = SIREPO.APP_SCHEMA.constants.layerGraphParams[lType];
                        if (! layer || ! pName) {
                            return;
                        }

                        // add other params
                        // regroup text into tspans
                        txtEl.text('');
                        let ts = '<tspan>' + txt + '</tspan>';
                        ts +=  ('<tspan x="' + txtEl.attr('x') + '" dy="16" class="rcscon-activation-txt">');
                        if (pName.toLowerCase().indexOf('activation') >= 0) {
                             ts += layer[pName];
                        }
                        if (pName.toLowerCase().indexOf('dropout') >= 0) {
                             ts += ('Rate = ' + layer[pName]);
                        }
                        if (pName.toLowerCase().indexOf('gaussiannoise') >= 0) {
                             ts += ('𝞼 = ' + layer[pName]);
                        }
                        ts += '</tspan>';

                        txtEl.html(ts);
                    });
                    return svg;
                },
            };

       },
    };
});

SIREPO.app.directive('partitionSelection', function(appState) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<form name="form" class="form-horizontal" data-ng-style="formStyle">',
              '<div class="form-group">',
                '<div data-ng-repeat="field in fields track by $index" data-model-field="field" data-model-name="modelName" data-label-size="0" data-field-size="4"></div>',
                '<div data-ng-repeat="field in fields track by $index" class="col-sm-4">',
                  '<p class="form-control-static text-center">{{ selectedRange(field) }}</p>',
                '</div>',
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

            function setDefaultCutoff(partition) {
                var axis = plotScope.axes.x;
                partition.cutoff0 = 0.125 * axis.domain[1];
                partition.cutoff1 = (1 - 0.125) * axis.domain[1];
            }

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
                var partition = appState.models.partition;
                if (! partition.cutoff0 || ! partition.cutoff1) {
                    setDefaultCutoff(partition);
                }
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
                        }
                    });
                }
            }

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

SIREPO.app.directive('partitionSimState', function(appState, frameCache, panelState, persistentSimulation, rcsconService) {
    return {
        restrict: 'A',
        scope: {
            controller: '=',
        },
        template: [
            '{{ statusText }}',
            '<div class="progress" data-ng-if="simState.isProcessing()" >',
              '<div class="progress-bar progress-bar-striped active" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" data-ng-attr-style="width: 100%"></div>',
            '</div>',
        ].join(''),
        controller: function($scope) {

            function handleStatus(data) {
                if (! appState.isLoaded()) {
                    return;
                }
                if (! appState.models.partition.method) {
                    // first time visiting this page, the form should appear dirty
                    appState.models.partition.method = 'random';
                }
                $scope.statusText = '';
                var reports = null;
                if (data.error) {
                    $scope.statusText = 'Error partitioning data: ' + data.error;
                }
                else {
                    if (data.percentComplete == 100) {
                        reports = rcsconService.addAnimations('partitionAnimation', 'Input', 'inputsCount');
                        reports = reports.concat(rcsconService.addAnimations(
                            'partitionAnimation', 'Output', 'outputsCount',
                            appState.models.files.inputsCount));
                    }
                    else {
                        if ($scope.simState.isProcessing()) {
                            $scope.statusText = 'Partitioning data ...';
                        }
                    }
                }
                $scope.controller.reports = reports;
                frameCache.setFrameCount(data.frameCount || 0);
            }

            $scope.simState = persistentSimulation.initSimulationState(
                $scope,
                rcsconService.computeModel('partitionAnimation'),
                handleStatus
            );

            appState.whenModelsLoaded($scope, function() {
                $scope.$on('partition.changed', $scope.simState.runSimulation);
            });
        },
    };
});

SIREPO.app.controller('PartitionController', function (appState, panelState, $scope) {
    var self = this;

    function updatePartitionMethod() {
        var partition = appState.models.partition;
        ['training', 'testing', 'validation'].forEach(function(f) {
            panelState.showField('partition', f, partition.method == 'random');
        });
    }

    function updatePercents() {
        var partition = appState.models.partition;
        if (partition.training && partition.testing) {
            var validation = 100 - (partition.training + partition.testing);
            if (validation > 0) {
                partition.validation = validation.toFixed(2);
            }
        }
        panelState.enableField('partition', 'validation', false);
    }

    $scope.showPartitionSelection = function() {
        if (appState.isLoaded()) {
            return appState.models.partition.method == 'selection';
        }
        return false;
    };

    appState.whenModelsLoaded($scope, function() {
        appState.watchModelFields($scope, ['partition.training', 'partition.testing'], updatePercents);
        appState.watchModelFields($scope, ['partition.method'], updatePartitionMethod);
        updatePercents();
        updatePartitionMethod();
    });
});

SIREPO.app.controller('VisualizationController', function (appState, requestSender, rcsconService, $scope) {
    var self = this;

    function createReports() {
        self.reports = [];
        var files = appState.applicationState().files;
        for (var i = 0; i < files.columnCount; i++) {
            var modelKey = 'fileColumnReport' + i;
            if (! appState.models[modelKey]) {
                appState.models[modelKey] = {
                    columnNumber: i,
                };
                appState.saveQuietly(modelKey);
            }
            var title = 'Input ' + (i + 1);
            var wantBreak = (i == files.inputsCount - 1) || i % 4 == 3;
            if (i >= files.inputsCount) {
                title = 'Output ' + (i - files.inputsCount + 1);
                wantBreak = (i - files.inputsCount) % 4 == 3;
            }
            var report = rcsconService.reportInfo(modelKey, title);
            report.break = wantBreak;
            self.reports.push(report);
        }
    }

    function processColumnCount() {
        var files = appState.models.files;
        if (! files.inputs || ! files.outputs) {
            return;
        }
        requestSender.getApplicationData(
            {
                method: 'compute_column_count',
                files: files,
            },
            function(data) {
                if (appState.isLoaded()) {
                    var files = appState.models.files;
                    ['columnCount', 'inputsCount', 'outputsCount'].forEach(function(f) {
                        files[f] = data[f];
                    });
                }
            });
    }

    appState.whenModelsLoaded($scope, function() {
        $scope.$on('files.changed', createReports);
        appState.watchModelFields($scope, ['files.inputs', 'files.outputs'], processColumnCount);
        createReports();
    });
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
