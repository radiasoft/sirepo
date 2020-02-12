'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.SINGLE_FRAME_ANIMATION = ['epochAnimation'];

SIREPO.app.factory('rcsconService', function(appState) {
    var self = {};
    self.computeModel = function(analysisModel) {
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

SIREPO.app.directive('appHeader', function() {
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'machine-learning\')}"><a href data-ng-click="nav.openSection(\'machine-learning\')"><span class="glyphicon glyphicon-qrcode"></span> Machine Learning</a></li>',
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
            //TODO(pjm): hide machine learning tab if no files selected.

            $scope.showImportModal = function() {
                $('#srw-simulation-import').modal('show');
            };

        },
    };
});

SIREPO.app.controller('MLController', function (appState, frameCache, persistentSimulation, rcsconService, utilities, $scope) {
    var self = this;

    function addFitAnimations() {
        self.reports = [];
        var files = appState.applicationState().files;
        for (var i = 0; i < files.outputsCount; i++) {
            var modelKey = 'fitAnimation' + i;
            if (! appState.models[modelKey]) {
                appState.models[modelKey] = {
                    columnNumber: i,
                };
                appState.saveQuietly(modelKey);
            }
            self.reports.push(rcsconService.reportInfo(modelKey, 'Fit ' + (i + 1)));
            if (SIREPO.SINGLE_FRAME_ANIMATION.indexOf(modelKey) < 0) {
                SIREPO.SINGLE_FRAME_ANIMATION.push(modelKey);
            }
            frameCache.setFrameCount(1, modelKey);
        }
    }

    function handleStatus(data) {
        self.reports = null;
        if ('percentComplete' in data && ! data.error) {
            if (data.percentComplete === 100 && ! self.simState.isProcessing()) {
                addFitAnimations();
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
        rcsconService.computeModel(),
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
                    //svg.attr('transform', 'translate(' + (scale * w / 2) + ', 0)');

                    // apply colors
                    const baseClass = 'rcscon-layer';
                    const nodes = svg.find('g.node');

                    // keras adds text to the node boxes formatted as:
                    //     <layer)_type>_<index>: <Layer Type>
                    nodes.each(function (idx) {
                        let txt = $(this).find('text').text();
                        let cName = txt.substring(0, txt.indexOf(':'));
                        let p = $(this).find('polygon');
                        p.addClass(baseClass);
                        // input is named differently
                        if (cName.indexOf('_input') >= 0) {
                            p.addClass(baseClass + '-input');
                            return;
                        }
                        cName = cName.substring(0, cName.lastIndexOf('_')).replace('_', '-');
                        p.addClass(baseClass + '-' + cName);
                    });
                    return svg;
                },
            };

       },
    };
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
            if (i >= files.inputsCount) {
                title = 'Output ' + (i - files.inputsCount + 1);
            }
            self.reports.push(rcsconService.reportInfo(modelKey, title));
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
