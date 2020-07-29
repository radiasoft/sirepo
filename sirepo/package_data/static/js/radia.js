'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.SINGLE_FRAME_ANIMATION = ['solver'];
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="Color" data-ng-class="fieldClass">',
          '<div data-color-picker="" data-form="form" data-color="model.color" data-model-name="modelName" data-model="model" data-field="field" data-default-color="defaultColor"></div>',
        '</div>',
        '<div data-ng-switch-when="PtsFile" data-ng-class="fieldClass">',
          '<input id="radia-pts-file-import" type="file" data-file-model="model[field]" accept=".dat,.txt"/>',
        '</div>',
    ].join('');
    SIREPO.appPanelHeadingButtons = [
        '<div style="display: inline-block">',
        '<a data-ng-click="download()" title="Download"> <span class="sr-panel-heading glyphicon glyphicon-cloud-download" style="margin-bottom: 0"></span></a> ',
        //'<ul class="dropdown-menu dropdown-menu-right">',
        //'<li data-export-python-link="" data-report-title="{{ reportTitle() }}"></li>',
        //'</ul>',
        '</div>',
    ].join('');
});

SIREPO.app.factory('radiaService', function(appState, fileUpload, panelState, requestSender) {
    var self = {};


    // why is this here? - answer: for getting frames
    self.computeModel = function(analysisModel) {
        return 'solver';
    };

    appState.setAppService(self);

    self.isEditing = false;
    self.objBounds = null;
    self.pointFieldTypes = appState.enumVals('FieldType').slice(1);
    self.selectedObj = null;

    self.addOrModifyPath = function(type) {
        var p = appState.models[self.pathTypeModel(type)];
        if (! appState.models.fieldPaths.paths) {
            appState.models.fieldPaths.paths = [];
        }
        if (! findPath(p)) {
            if (type === 'file') {
                p.fileName = p.fileModel.name;
                upload((p.fileModel));
            }
            appState.models.fieldPaths.paths.push(p);
        }
        appState.saveChanges('fieldPaths', function (d) {
            self.showPathPicker(false);
        });
    };

    self.alphaDelegate = function() {
        var m = 'geometry';
        var f = 'alpha';
        var d = panelState.getFieldDelegate(m, f);
        d.range = function() {
            return {
                min: appState.fieldProperties(m, f).min,
                max: appState.fieldProperties(m, f).max,
                step: 0.01
            };
        };
        d.readout = function() {
            return appState.modelInfo(m)[f][SIREPO.INFO_INDEX_LABEL];
        };
        d.update = function() {};
        d.watchFields = [];
        return d;
    };

    self.createPathModel = function(type) {
        var t = type || self.pathTypeModel(appState.models.fieldPaths.path);
        var model = {
            id: numPathsOfType(appState.models.fieldPaths.path),
        };
        appState.models[t] = appState.setModelDefaults(model, t);

        // set to fill bounds if any actors exist
        //TODO: must use OBJECT bounds, not the bounds of a vector field!
        if (t === 'fieldMapPath' && self.objBounds) {
            appState.models[t].lenX = Math.abs(self.objBounds[1] - self.objBounds[0]);
            appState.models[t].lenY = Math.abs(self.objBounds[3] - self.objBounds[2]);
            appState.models[t].lenZ = Math.abs(self.objBounds[5] - self.objBounds[4]);
            appState.models[t].ctrX = (self.objBounds[1] + self.objBounds[0]) / 2.0;
            appState.models[t].ctrY = (self.objBounds[3] + self.objBounds[2]) / 2.0;
            appState.models[t].ctrZ = (self.objBounds[5] + self.objBounds[4]) / 2.0;
        }
    };

    /*
    self.downloadPath = function(path, field) {
        //srdbg('dl', path);
        requestSender.getApplicationData(
            {
                fieldPaths: $scope.paths,
                method: 'get_field_integrals',
                simulationId: appState.models.simulation.simulationId,
            },
            function(d) {
                $scope.integrals = d;
            });

        var CSV_HEADING = ['x', 'y', 'z', field + 'x', field + 'y', field + 'z'];
        var fileName = panelState.fileNameFromText(path.name + ' ' + field, 'csv');
        var points = [CSV_HEADING];
        $scope.paths.forEach(function (p) {
            var row = [];
            row.push(
                p.name,
                p.beginX, p.beginY, p.beginZ, p.endX, p.endY, p.endZ
            );
            $scope.INTEGRABLE_FIELD_TYPES.forEach(function (t) {
                row = row.concat($scope.integrals[p.name][t]);
            });
            points.push(row);
        });
        saveAs(new Blob([d3.csv.format(points)], {type: "text/csv;charset=utf-8"}), fileName);
    };
*/
    self.getPathType = function() {
        return (appState.models.fieldTypes || {}).path;
    };

    self.getSelectedObj = function() {
        return self.selectedObj;
    };

    self.newPath = function() {
        self.showPathPicker(true, true);
    };

    self.pathEditorTitle = function() {
        if (! appState.models.fieldPaths) {
            return '';
        }
        return (self.isEditing ? 'Edit ' : 'New ') + appState.models.fieldPaths.path;
    };

    self.pathTypeModel = function(type) {
        return type + 'Path';
    };

    self.setSelectedObj = function(o) {
        self.selectedObj = o;
    };

    self.showFieldDownload = function(doShow, path) {
        self.selectedPath = path;
        $('#sr-field-download').modal(doShow ? 'show' : 'hide');
    };

    self.showPathPicker = function(doShow, isNew) {
        self.isEditing = doShow && ! isNew;
        if (doShow) {
            if (isNew) {
                self.createPathModel();
            }
        }
        $('#' + panelState.modalId('fieldpaths')).modal(doShow ? 'show' : 'hide');
    };

    function findPath(path) {
        for(var i = 0; i < (appState.models.fieldPaths.paths || []).length; ++i) {
            var p = appState.models.fieldPaths.paths[i];
            if (p.type === path.type && p.id === path.id) {
                return path;
            }
        }
        return null;
    }

    function numPathsOfType(type) {
        return (appState.models.fieldPaths.paths || []).filter(function (p) {
            return p.type === type;
        }).length;
    }

    function toFloat(v) {
        return parseFloat('' + v);
    }
    function toInt(v) {
        return parseInt('' + v);
    }

    function upload(inputFile) {
        fileUpload.uploadFileToUrl(
            inputFile,
            {},
            requestSender.formatUrl(
                'uploadFile',
                {
                    '<simulation_id>': appState.models.simulation.simulationId,
                    '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                    '<file_type>': SIREPO.APP_SCHEMA.constants.pathPtsFileType,
                }),
            function(d) {
                //srdbg('UPLOAD DONE', d);
            }, function (err) {
                throw new Error(inputFile + ': Error during upload ' + err);
            });
    }

    return self;
});

SIREPO.app.controller('RadiaSourceController', function (appState, panelState, $scope) {
    var self = this;

    appState.whenModelsLoaded($scope, function() {
        // initial setup
        //appState.watchModelFields($scope, ['model.field'], function() {
        //});
        //srdbg('RadiaSourceController');
    });
});

SIREPO.app.controller('RadiaVisualizationController', function (appState, errorService, frameCache, panelState, persistentSimulation, radiaService, utilities, $scope) {
    var SINGLE_PLOTS = ['magnetViewer'];
    var self = this;
    self.scope = $scope;
    $scope.mpiCores = 0;
    $scope.panelState = panelState;
    $scope.svc = radiaService;

    self.solution = [];

    self.simHandleStatus = function (data) {
        //srdbg('SIM STATUS', data);
        if (data.error) {
            throw new Error('Solver failed: ' + data.error);
        }
        //$scope.mpiCores = data.mpiCores > 1 ? data.mpiCores : 0;
        SINGLE_PLOTS.forEach(function(name) {
            frameCache.setFrameCount(0, name);
        });
        if ('percentComplete' in data && ! data.error) {
            if (data.percentComplete === 100 && ! self.simState.isProcessing()) {
                self.solution = data.outputInfo[0];
                SINGLE_PLOTS.forEach(function(name) {
                    frameCache.setFrameCount(1, name);
                });
            }
        }
        frameCache.setFrameCount(data.frameCount);
    };

    self.startSimulation = function() {
        self.solution = [];
        $scope.$broadcast('solveStarted', self.simState);
        self.simState.saveAndRunSimulation('simulation');
    };

    self.simState = persistentSimulation.initSimulationState(self);

    self.showCompletionState = function() {
        return self.solution && self.solution.length;
    };

    self.completionStateArgs = function() {
        return {
            stepCount: self.solution[3],
            maxM: utilities.roundToPlaces(self.solution[1], 4),
            maxH: utilities.roundToPlaces(self.solution[2], 4),
        };
    };

    self.simState.startButtonLabel = function() {
        return 'Solve';
    };

    self.simState.stopButtonLabel = function() {
        return 'Cancel';
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'visualization\')}"><a href data-ng-click="nav.openSection(\'visualization\')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
                '</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
                //  '<div>App-specific setting item</div>',
              '</app-settings>',
              '<app-header-right-sim-list>',
                '<ul class="nav navbar-nav sr-navbar-right">',
                  '<li><a href data-ng-click=""><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>',
                '</ul>',
              '</app-header-right-sim-list>',
            '</div>',
        ].join(''),
    };
});

SIREPO.app.directive('fieldDownload', function(appState, geometry, panelState, radiaService, requestSender) {

    return {
        restrict: 'A',
        scope: {
        },
        template: [
            '<div class="modal fade" tabindex="-1" role="dialog" id="sr-field-download" data-small-element-class="col-sm-2">',
                '<div class="modal-dialog modal-lg">',
                    '<div class="modal-content">',
                        '<div class="modal-header bg-info">',
                            '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                            '<span class="lead modal-title text-info">{{ svc.selectedPath.name }}</span>',
                        '</div>',
                        '<div class="modal-body">',
                            '<div class="form-horizontal">',
                                '<div class="form-group form-group-sm" data-ng-show="! isFieldMap()">',
                                    '<div class="control-label col-sm-5">',
                                        '<label><span>Field</span></label>',
                                    '</div>',
                                    '<div class="col-sm-5">',
                                        '<select data-ng-model="tModel.type" data-ng-change="ch()" class="form-control">',
                                            '<option ng-repeat="t in svc.pointFieldTypes">{{ t }}</option>',
                                        '</select>',
                                    '</div>',
                                '</div>',
                                '<div class="row">',
                                    '<button data-ng-click="download()" class="btn btn-default col-sm-offset-6">Download</button>',
                                '</div>',
                            '</div>',
                        '</div>',
                    '</div>',
                '</div>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {
            $scope.svc = radiaService;

            $scope.tModel = {
                type: radiaService.pointFieldTypes[0],
            };

            $scope.download = function() {
                //srdbg('download', $scope.tModel.type, radiaService.selectedPath);
                var p = radiaService.selectedPath;
                var f = p.name + ' ' + $scope.fieldType();
                var ext = $scope.isFieldMap() ? 'sdds' : 'csv';
                var fn = panelState.fileNameFromText(f, ext);
                var ct = $scope.isFieldMap() ? 'application/octet-stream' : 'text/csv;charset=utf-8';
                requestSender.getApplicationData(
                    {
                        beamAxis: appState.models.geometry.beamAxis,
                        contentType: ct,
                        fieldPaths: [radiaService.selectedPath],
                        fieldType: $scope.fieldType(),
                        fileType: $scope.isFieldMap() ? 'sdds' : 'csv',
                        method: 'save_field',
                        name: radiaService.selectedPath.name,
                        simulationId: appState.models.simulation.simulationId,
                        viewType: 'fields',
                    },
                    function(d) {
                        saveAs(new Blob([d], {type: ct}), fn);
                        radiaService.showFieldDownload(false);
                    },
                    fn
                );
            };

            $scope.fieldType = function() {
                return $scope.isFieldMap() ? 'B' : $scope.tModel.type;
            };

            $scope.isFieldMap = function() {
                return (radiaService.selectedPath || {}).type === 'fieldMap';
            };

            appState.whenModelsLoaded($scope, function () {
            });
        },
    };
});

SIREPO.app.directive('fieldPathPicker', function(appState, panelState, radiaService) {

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            controller: '=',
            title: '@',
            id: '@',
            smallElementClass: '@',
        },
        template: [
            '<div class="modal fade" data-ng-attr-id="{{ id }}" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<span class="lead modal-title text-info">{{ title }}</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<div class="row">',
                        '<div data-field-editor="\'path\'" data-label-size="" data-field-size="3" style="text-align: right" data-model-name="modelName" data-model="model"></div>',
                      '</div>',
                      '<br />',
                      '<div class="row">',
                        '<div data-ng-repeat="type in pathTypes" data-ng-show="getPathType() == type" data-advanced-editor-pane="" data-view-name="radiaService.pathTypeModel(type)" data-field-def="basic" data-want-buttons="false">',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {
            $scope.modelsLoaded = false;
            $scope.pathType = null;
            $scope.pathTypes = appState.enumVals('PathType');
            $scope.pathTypeModels = $scope.pathTypes.map(radiaService.pathTypeModel);
            $scope.radiaService = radiaService;

            $scope.getPathType = function() {
               return ($scope.model || {}).path;
            };

            appState.whenModelsLoaded($scope, function () {
                $scope.model = appState.models[$scope.modelName];
                $scope.pathTypes.forEach(function (t) {
                    var pt = radiaService.pathTypeModel(t);
                    $scope.$on(pt + '.changed', function () {
                        radiaService.addOrModifyPath(t);
                    });
                });
                $scope.$on('cancelChanges', function(e, name) {
                    if ($scope.pathTypeModels.indexOf(name) >= 0) {
                        radiaService.showPathPicker(false);
                    }
                });
                $scope.$watch('model.path', function (m) {
                    var o = $($element).find('.modal').css('opacity');
                    if (o == 1 && ! radiaService.isEditing) {
                        // displaying editor but not editing, must be new
                        radiaService.createPathModel();
                    }
                });
                $scope.modelsLoaded = true;
            });
        },
    };
});

SIREPO.app.directive('fieldIntegralTable', function(appState, panelState, plotting, radiaService, requestSender, utilities) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: [
            '<div class="col-md-6">',
                '<div class="panel panel-info">',
                    '<div class="panel-heading">',
                        '<span class="sr-panel-heading">Field Integrals (T &#x00B7; mm)</span>',
                        '<div class="sr-panel-options pull-right">',
                        '<a data-ng-show="hasPaths()" data-ng-click="download()" target="_blank" title="Download"> <span class="sr-panel-heading glyphicon glyphicon-cloud-download" style="margin-bottom: 0"></span></a> ',
                        '</div>',
                    '</div>',
                    '<div class="panel-body">',
                        '<table data-ng-if="hasPaths()" style="width: 100%; table-layout: fixed; margin-bottom: 10px" class="table table-hover">',
                          '<colgroup>',
                            '<col style="width: 20ex">',
                            '<col>',
                            '<col>',
                          '</colgroup>',
                          '<thead>',
                            '<tr>',
                              '<th data-ng-repeat="h in HEADING">{{ h }}</th>',
                            '</tr>',
                          '</thead>',
                          '<tbody>',
                            '<tr data-ng-repeat="path in linePaths()">',
                              '<td>{{ path.name }}</td>',
                              '<td>[{{ path.beginX }}, {{ path.beginY }}, {{ path.beginZ }}] &#x2192; [{{ path.endX }}, {{ path.endY }}, {{ path.endZ }}]</td>',
                              '<td>',
                                '<div data-ng-repeat="t in INTEGRABLE_FIELD_TYPES"><span style="font-weight: bold">{{ t }}:</span> </span><span>{{ format(integrals[path.name][t]) }}</span></div>',
                              '</td>',
                            '</tr>',
                          '</tbody>',
                        '</table>',
                    '</div>',
                '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {

            $scope.CSV_HEADING = ['Line', 'x0', 'y0', 'z0', 'x1', 'y1', 'z1', 'Bx', 'By', 'Bz', 'Hx', 'Hy', 'Hz'];
            $scope.HEADING = ['Line', 'Endpoints', 'Fields'];
            $scope.INTEGRABLE_FIELD_TYPES = ['B', 'H'];
            $scope.integrals = {};

            $scope.download = function() {
                var fileName = panelState.fileNameFromText('Field Integrals', 'csv');
                var data = [$scope.CSV_HEADING];
                $scope.linePaths().forEach(function (p) {
                    var row = [];
                    row.push(
                        p.name,
                        p.beginX, p.beginY, p.beginZ, p.endX, p.endY, p.endZ
                    );
                    $scope.INTEGRABLE_FIELD_TYPES.forEach(function (t) {
                        row = row.concat(
                            $scope.integrals[p.name][t]
                        );
                    });
                    data.push(row);
                });
                //srdbg('save to', fileName, heading, data);
                saveAs(new Blob([d3.csv.format(data)], {type: "text/csv;charset=utf-8"}), fileName);
            };

            $scope.hasPaths = function() {
                return $scope.linePaths().length;
            };

            $scope.format = function(vals) {
                if (! vals) {
                    return [];
                }
                return vals.map(function (v, i) {
                    return utilities.roundToPlaces(v, 4);
                });
            };

            $scope.isLine = function(p) {
                return p.type === 'line';
            };

            $scope.linePaths = function () {
                return (($scope.model || {}).paths || []).filter($scope.isLine);
            };

            function updateTable() {
                requestSender.getApplicationData(
                    {
                        fieldPaths: $scope.linePaths(),
                        method: 'get_field_integrals',
                        simulationId: appState.models.simulation.simulationId,
                    },
                    function(d) {
                        $scope.integrals = d;
                    });
            }

            $scope.$on('fieldPaths.changed', function () {
                updateTable();
            });

           appState.whenModelsLoaded($scope, function() {
               $scope.model = appState.models[$scope.modelName];
               // wait until we have some data to update
               $scope.$on('radiaViewer.loaded', function () {
                    updateTable();
               });
            });

        },
    };
});

SIREPO.app.directive('fieldPathTable', function(appState, panelState, radiaService, utilities) {
    return {
        restrict: 'A',
        scope: {
            paths: '='
        },
        template: [
            '<table data-ng-if="hasPaths()" style="width: 100%; table-layout: fixed; margin-bottom: 10px" class="table table-hover">',
              '<colgroup>',
                '<col style="width: 20ex">',
                '<col style="width: 10ex">',
                '<col style="width: 10ex">',
                '<col style="width: 100%">',
                '<col style="width: 10ex">',
              '</colgroup>',
              '<thead>',
                '<tr>',
                  '<th>Name</th>',
                  '<th>Type</th>',
                  '<th>Num. points</th>',
                  '<th>Details</th>',
                  '<th></th>',
                '</tr>',
              '</thead>',
              '<tbody>',
                '<tr data-ng-repeat="path in paths track by $index">',
                  '<td><div class="badge sr-badge-icon sr-lattice-icon"><span>{{ path.name }}</span></div></td>',
                  '<td><span>{{ path.type }}</span></td>',
                  '<td><span>{{ path.numPoints }}</span></td>',
                  '<td><span>{{ pathDetails(path) }}</span></td>',
                  '<td style="text-align: right">',
                    '<div class="sr-button-bar-parent">',
                        '<div class="sr-button-bar" data-ng-class="sr-button-bar-active" >',
                            '<button class="btn btn-info btn-xs sr-hover-button" data-ng-click="copyPath(path)">Copy</button>',
                            ' <button data-ng-click="editPath(path)" class="btn btn-info btn-xs sr-hover-button">Edit</button>',
                            ' <button data-ng-click="svc.showFieldDownload(true, path)" class="btn btn-info btn-xs"><span class="glyphicon glyphicon-cloud-download"></span></button>',
                            ' <button data-ng-click="deletePath(path, $index)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button>',
                        '</div>',
                    '<div>',
                  '</td>',
                '</tr>',
              '</tbody>',
            '</table>',
        ].join(''),
        controller: function($scope) {
            $scope.svc = radiaService;

            $scope.hasPaths = function() {
                return $scope.paths && $scope.paths.length;
            };

            $scope.copyPath = function(path) {
                //srdbg('CPY', path);
            };

           $scope.deletePath = function(path, index) {
                $scope.paths.splice(index, 1);
                appState.saveChanges('fieldPaths');
           };

           $scope.editPath = function(path) {
               appState.models[radiaService.pathTypeModel(path.type)] = path;
               appState.models.fieldPaths.path = path.type;
               radiaService.showPathPicker(true, false);
           };

           $scope.pathDetails = function(path) {
               var res = '';
               var pt = radiaService.pathTypeModel(path.type);
               var info = appState.modelInfo(pt);
               var d = SIREPO.APP_SCHEMA.constants.pathDetailFields[pt];
               d.forEach(function (f, i) {
                   var fi = info[f];
                   res += (fi[0] + ': ' + path[f] + (i < d.length - 1 ? '; ' : ''));
               });
               return res;
           };

           appState.whenModelsLoaded($scope, function() {
           });
        },
    };
});

SIREPO.app.directive('radiaFieldPaths', function(appState, panelState, radiaService) {

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: [
            '<div class="col-md-6">',
                '<div class="panel panel-info">',
                    '<div class="panel-heading"><span class="sr-panel-heading">Field Paths</span></div>',
                    '<div class="panel-body">',
                        '<button class="btn btn-info btn-xs pull-right" accesskey="p" data-ng-click="radiaService.newPath()"><span class="glyphicon glyphicon-plus"></span> New <u>P</u>ath</button>',
                        '<div data-field-path-table="" data-paths="model.paths"></div>',
                        '<button class="btn btn-default col-sm-2 col-sm-offset-5" data-ng-show="hasPaths()" data-ng-click="confirmClear()">Clear</button>',
                    '</div>',
                '</div>',
            '</div>',
            //'<div data-confirmation-modal="" data-id="sr-delete-path-confirmation" data-title="Delete Path?" data-ok-text="Delete" data-ok-clicked="deleteSelected()">Delete command &quot;{{ selectedItemName() }}&quot;?</div>',
            '<div data-confirmation-modal="" data-id="sr-clear-paths-confirmation" data-title="Clear All Paths?" data-ok-text="OK" data-ok-clicked="clearPaths()">Clear All Paths?</div>',

        ].join(''),
        controller: function($scope, $element) {
            $scope.modelsLoaded = false;
            $scope.pathTypes = appState.enumVals('PathType');
            $scope.radiaService = radiaService;

            $scope.getPathType = function() {
                return ($scope.model || {}).path;
            };

            $scope.clearPaths = function() {
                $scope.model.paths = [];
                appState.saveChanges($scope.modelName);
            };

            $scope.confirmClear = function() {
                $('#sr-clear-paths-confirmation').modal('show');
            };

            $scope.hasPaths = function() {
                if (! $scope.modelsLoaded) {
                    return false;
                }
                return $scope.model.paths && $scope.model.paths.length;
            };

            appState.whenModelsLoaded($scope, function () {
                $scope.model = appState.models[$scope.modelName];
                $scope.modelsLoaded = true;
            });
        },
    };
});

SIREPO.app.directive('radiaGeomObjInfo', function(appState, panelState, radiaService) {

    return {
        restrict: 'A',
        scope: {
            model: '=',
        },
        template: [
            '<div class="col-md-6">',
                '<div data-label-with-tooltip="" class="control-label" data-ng-class="labelClass" data-label="{{ model.name }}" data-tooltip=""></div>',
                '<div data-field-editor="\'color\'" data-model-name="geomObject" data-model="model"></div>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {
            $scope.radiaService = radiaService;
            appState.whenModelsLoaded($scope, function () {
            });
        },
    };
});

// does not need to be its own directive?  everything in viz and service? (and move template to html)
SIREPO.app.directive('radiaSolver', function(appState, errorService, frameCache, geometry, layoutService, panelState, radiaService) {

    return {
        restrict: 'A',
        scope: {
            viz: '<',
            modelName: '@',
        },
        template: [
            '<div class="col-md-6">',
                '<div data-basic-editor-panel="" data-view-name="solver">',
                        '<div data-sim-status-panel="viz.simState"></div>',
              //'<div>',
              //  '<div data-simulation-status-timer="viz.simState"></div>',
              //'</div>',
                        '<div class="col-sm-6 pull-right" style="padding-top: 8px;">',
                            '<button class="btn btn-default" data-ng-click="reset()">Reset</button>',
                        '</div>',
                    '</div>',
                '</div>',
            '</div>',

        ].join(''),
        controller: function($scope, $element) {

            $scope.model = appState.models[$scope.modelName];

            $scope.reset = function() {
                $scope.viz.solution = [];
                panelState.clear('geometry');
                panelState.requestData('reset', function (d) {
                    frameCache.setFrameCount(0);
                }, true);
            };

            appState.whenModelsLoaded($scope, function () {
                //srdbg('frms', frameCache.hasFrames(), frameCache.getFrameCount());
                //var cf = $scope.viz.simState.cancelSimulation;
                //$scope.viz.simState.cancelSimulation = cf(function () {
                //    $scope.reset();
                //});
            });


        },
    };
});

SIREPO.app.directive('radiaViewer', function(appState, errorService, frameCache, geometry, layoutService, panelState, plotting, plotToPNG, radiaService, radiaVtkUtils, requestSender, utilities, vtkPlotting, vtkUtils, $document, $interval, $rootScope) {

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: [
            '<div class="col-md-6">',
                '<div class="row" data-basic-editor-panel="" data-view-name="{{ modelName }}">',
                    '<div data-vtk-display="" class="vtk-display" data-ng-class="{\'col-sm-11\': isViewTypeFields()}" style="padding-right: 0" data-show-border="true" data-model-name="{{ modelName }}" data-event-handlers="eventHandlers" data-enable-axes="true" data-axis-cfg="axisCfg" data-axis-obj="axisObj" data-enable-selection="true"></div>',
                    //'<div data-vtk-axes="" data-width="canvasGeometry().size.width" data-height="canvasGeometry().size.height" data-bound-obj="beamAxisObj" data-axis-cfg="beamAxisCfg"></div>',
                    '<div class="col-sm-1" style="padding-left: 0" data-ng-if="isViewTypeFields()">',
                        '<div class="colorbar"></div>',
                    '</div>',
                '</div>',
            '</div>',

        ].join(''),
        controller: function($scope, $element) {

            $scope.axisObj = null;
            $scope.defaultColor = "#ff0000";
            $scope.gModel = null;
            $scope.mode = null;

            $scope.isViewTypeFields = function () {
                return (appState.models.magnetDisplay || {}).viewType === VIEW_TYPE_FIELDS;
            };

            $scope.isViewTypeObjects = function () {
                return (appState.models.magnetDisplay || {}).viewType === VIEW_TYPE_OBJECTS;
            };

            var LINEAR_SCALE_ARRAY = 'linear';
            var LOG_SCALE_ARRAY = 'log';
            var ORIENTATION_ARRAY = 'orientation';
            var FIELD_ATTR_ARRAYS = [LINEAR_SCALE_ARRAY, LOG_SCALE_ARRAY, ORIENTATION_ARRAY];

            var PICKABLE_TYPES = [radiaVtkUtils.GEOM_TYPE_POLYS, radiaVtkUtils.GEOM_TYPE_VECTS];

            var SCALAR_ARRAY = 'scalars';

            var VIEW_TYPE_FIELDS = 'fields';
            var VIEW_TYPE_OBJECTS = 'objects';

            var actorInfo = {};
            var alphaDelegate = null;
            var beamAxis = [[-1, 0, 0], [1, 0, 0]];
            var cm = vtkPlotting.coordMapper();
            var colorbar = null;
            var colorbarPtr = null;
            var colorScale = null;
            var cPicker = null;
            var displayFields = [
                 'magnetDisplay.pathType',
                 'magnetDisplay.viewType',
                 'magnetDisplay.fieldType',
            ];
            var fieldDisplayModelFields = {
                'fieldDisplay': ['colorMap', 'scaling'],
            };
            var fieldDisplayFields = fieldDisplayModelFields.fieldDisplay.map(function (f) {
                return 'fieldDisplay.' + f;
            });

            var initDone = false;
            var ptPicker = null;
            var renderer = null;
            var renderWindow = null;
            var selectedColor = [];
            var selectedInfo = null;
            var selectedObj = null;
            var selectedOutline = null;
            var selectedPointId = -1;
            var sceneData = {};

            // these objects are used to set various vector properties
            var vectInArrays = [{
                location: vtk.Common.DataModel.vtkDataSet.FieldDataTypes.COORDINATE,
            }];

            var vectOutArrays = [{
                    location: vtk.Common.DataModel.vtkDataSet.FieldDataTypes.POINT,
                    name: SCALAR_ARRAY,
                    dataType: 'Uint8Array',
                    attribute: vtk.Common.DataModel.vtkDataSetAttributes.AttributeTypes.SCALARS,
                    numberOfComponents: 3,
                },
            ];
            var vectArrays = {
                input: vectInArrays,
                output: vectOutArrays,
            };

            var vtkAPI = {};
            var vtkSelection = {};

            var watchFields = displayFields.concat(fieldDisplayFields);

            FIELD_ATTR_ARRAYS.forEach(function (n) {
                vectOutArrays.push({
                    location: vtk.Common.DataModel.vtkDataSet.FieldDataTypes.POINT,
                    name: n,
                    dataType: 'Float32Array',
                    numberOfComponents: 3,
                });
            });

            // stash the actor and associated info to avoid recalculation
            function addActor(id, group, actor, type, pickable) {
                //srdbg('addActor', 'id', id, 'grp', group, 'type', type, 'pcik', pickable);
                var pData = actor.getMapper().getInputData();
                var info = {
                    actor: actor,
                    colorIndices: [],
                    group: group || 0,
                    id: id,
                    pData: pData,
                    scalars: pData.getCellData().getScalars(),
                    type: type,
                };

                if (info.scalars) {
                    info.colorIndices = utilities.indexArray(numColors(pData, type))
                        .map(function (i) {
                            return 4 * i;
                        });
                }
                actorInfo[id] = info;

                vtkPlotting.addActor(renderer, actor);
                if (pickable) {
                    ptPicker.addPickList(actor);
                    //cPicker.addPickList(actor);
                }
                return info;
            }

            function buildScene() {
                //srdbg('buildScene', sceneData.data);
                var name = sceneData.name;
                var data = sceneData.data;

                vtkPlotting.removeActors(renderer);
                var didModifyGeom = false;
                for (var i = 0; i < data.length; ++i) {

                    var gname = name + '.' + i;
                    var sceneDatum = data[i];

                    // trying a separation into an actor for each data type, to better facilitate selection
                    for (var j = 0; j < radiaVtkUtils.GEOM_TYPES.length; ++j) {
                        var t = radiaVtkUtils.GEOM_TYPES[j];
                        var id = gname + '.' + t;
                        var d = sceneDatum[t];
                        if (! d || ! d.vertices || ! d.vertices.length) {
                            continue;
                        }
                        var isPoly = t === radiaVtkUtils.GEOM_TYPE_POLYS;
                        var gObj = getGeomObj(id) || {};
                        //srdbg('got obj', gObj);
                        var gColor = gObj.color ? vtk.Common.Core.vtkMath.hex2float(gObj.color) : null;
                        var pdti = radiaVtkUtils.objToPolyData(sceneDatum, [t], gColor);
                        var pData = pdti.data;
                        var bundle;
                        if (radiaVtkUtils.GEOM_OBJ_TYPES.indexOf(t) >= 0) {
                            bundle = cm.buildActorBundle();
                            bundle.mapper.setInputData(pData);
                        }
                        else {
                            var vectorCalc = vtk.Filters.General.vtkCalculator.newInstance();
                            vectorCalc.setFormula(getVectFormula(d, appState.models.fieldDisplay.colorMap));
                            vectorCalc.setInputData(pData);

                            var mapper = vtk.Rendering.Core.vtkGlyph3DMapper.newInstance();
                            mapper.setInputConnection(vectorCalc.getOutputPort(), 0);

                            var s = vtk.Filters.Sources.vtkArrowSource.newInstance();
                            mapper.setInputConnection(s.getOutputPort(), 1);
                            mapper.setOrientationArray(ORIENTATION_ARRAY);

                            // this scales by a constant - the default is to use scalar data
                            mapper.setScaleFactor(8.0);
                            mapper.setScaleModeToScaleByConstant();
                            mapper.setColorModeToDefault();
                            bundle = cm.buildActorBundle();
                            bundle.setMapper(mapper);
                        }
                        bundle.actor.getProperty().setEdgeVisibility(isPoly);
                        bundle.actor.getProperty().setLighting(isPoly);
                        var info = addActor(id, gname, bundle.actor, t, PICKABLE_TYPES.indexOf(t) >= 0);
                        gColor = getColor(info);
                        //srdbg('add obj', gObj, isPoly);
                        if (isPoly && $.isEmptyObject(gObj)) {
                            gObj = appState.setModelDefaults(gObj, 'geomObject');
                            gObj.name = id;
                            gObj.id = id;
                            if (gColor) {
                                gObj.color = vtk.Common.Core.vtkMath.floatRGB2HexCode(vtkUtils.rgbToFloat(gColor));
                            }
                            if (! appState.models.geometry.objects) {
                                appState.models.geometry.objects = [];
                            }
                            appState.models.geometry.objects.push(gObj);
                            didModifyGeom = true;
                        }
                        if (
                            t === radiaVtkUtils.GEOM_TYPE_LINES &&
                            appState.models.magnetDisplay.viewType == VIEW_TYPE_FIELDS
                        ) {
                            setEdgeColor(info, [216, 216, 216]);
                        }
                    }
                }

                var b = renderer.computeVisiblePropBounds();
                radiaService.objBounds = b;
                //srdbg('bnds', b);
                //srdbg('l', [Math.abs(b[1] - b[0]), Math.abs(b[3] - b[2]), Math.abs(b[5] - b[4])]);
                //srdbg('ctr', [(b[1] + b[0]) / 2, (b[3] + b[2]) / 2, (b[5] + b[4]) / 2]);

                var padPct = 0.1;
                var l = [
                    Math.abs(b[1] - b[0]),
                    Math.abs(b[3] - b[2]),
                    Math.abs(b[5] - b[4])
                ].map(function (c) {
                    return (1 + padPct) * c;
                });

                var bndBox = cm.buildBox(l, [(b[1] + b[0]) / 2, (b[3] + b[2]) / 2, (b[5] + b[4]) / 2]);
                bndBox.actor.getProperty().setRepresentationToWireframe();
                // NOTE: vtkLineFilter exists but is not included in the default vtk build
                //var lf = vtk.Filters.General.vtkLineFilter.newInstance();

                renderer.addActor(bndBox.actor);
                var vpb = vtkPlotting.vpBox(bndBox.source, renderer);
                renderWindow.render();
                vpb.defaultCfg.edgeCfg.z.sense = -1;
                vpb.initializeWorld(
                    {
                        edgeCfg: {
                            x: {sense: 1},
                            y: {sense: 1},
                            z: {sense: -1},
                        }
                    });
                $scope.axisObj = vpb;

                var acfg = {};
                geometry.basis.forEach(function (dim, i) {
                    acfg[dim] = {};
                    acfg[dim].dimLabel = dim;
                    acfg[dim].label = dim + ' [mm]';
                    acfg[dim].max = b[2 * i + 1];
                    acfg[dim].min = b[2 * i];
                    acfg[dim].numPoints = 2;
                    acfg[dim].screenDim = dim === 'z' ? 'y' : 'x';
                    acfg[dim].showCentral = dim === appState.models.geometry.beamAxis;
                });
                $scope.axisCfg = acfg;

                // visual rep of paths?
                /*
                appState.models.fieldPaths.paths.forEach(function (p) {
                    if (p.type == 'line') {
                        var s = vtk.Filters.Sources.vtkLineSource.newInstance({
                            point1: [p.beginX, p.beginY, p.beginZ],
                            point2: [p.endX, p.endY, p.endZ],
                            resolution: 2,
                        });
                        var b = cm.buildFromSource(s);
                        b.actor.getProperty().setColor(255, 0, 0);
                        renderer.addActor(b.actor);
                    }
                });
                */

                if (didModifyGeom) {
                    appState.saveQuietly('geometry');
                }
                updateLayout();
                setAlpha();
                setBGColor();
                vtkAPI.setCam();
                enableWatchFields(true);
            }

            function enableWatchFields(doEnable) {
                watchFields.forEach(function (wf) {
                    var mf = appState.parseModelField(wf);
                    panelState.enableField(mf[0], mf[1], doEnable);
                });
            }

            function getActor(id) {
                return (getActorInfo(id) || {}).actor;
            }

            function getActorInfo(id) {
                return actorInfo[id];
            }

            function getActorInfoOfType(typeName) {
                return Object.keys(actorInfo)
                    .filter(function (id) {
                        return getActorInfo(id).type === typeName;
                    })
                    .map(function (id) {
                        return getActorInfo(id);
                    });
            }

            function getActorsOfType(typeName) {
                return getActorInfoOfType(typeName).map(function (info) {
                    return info.actor;
                });
            }

            function getColor(info) {
                var s = info.scalars;
                if (! s) {
                    return null;
                }
                var inds = info.colorIndices;
                if (! inds) {
                    return null;
                }
                return s.getData().slice(inds[0], inds[0] + 3);
            }

            function getGeomObj(id) {
                var gObjs = appState.models.geometry.objects || [];
                for (var i = 0; i < gObjs.length; ++i) {
                    if (gObjs[i].id === id) {
                        return gObjs[i];
                    }
                }
                return null;
            }

            function getInfoForActor(actor) {
                for (var n in actorInfo) {
                    if (getActor(n) === actor) {
                        return getActorInfo(n);
                    }
                }
            }

            // used to create array of arrows (or other objects) for vector fields
            // change to use magnitudes and color locally
            function getVectFormula(vectors, colorMapName) {

                //srdbg('getVectFormula', colorMapName);
                var cmap = plotting.colorMapOrDefault(
                    colorMapName,
                    appState.fieldProperties('fieldDisplay', 'colorMap').default
                );
                //srdbg('v', vectors);
                //srdbg('cm', cmap);
                var norms = utilities.normalize(vectors.magnitudes);
                var logMags = vectors.magnitudes.map(function (n) {
                    return Math.log(n);
                });

                // get log values back into the original range, so that the extremes have the same
                // size as a linear scale
                var minLogMag = Math.min.apply(null, logMags);
                var maxLogMag = Math.max.apply(null, logMags);
                var minMag = Math.min.apply(null, vectors.magnitudes);
                var maxMag = Math.max.apply(null, vectors.magnitudes);
                colorScale = plotting.colorScale(minMag, maxMag, cmap);

                logMags = logMags.map(function (n) {
                    return minMag + (n - minLogMag) * (maxMag - minMag) / (maxLogMag - minLogMag);
                });

                return {
                    getArrays: function(inputDataSets) {
                        return vectArrays;
                    },
                    evaluate: function (arraysIn, arraysOut) {
                        var coords = arraysIn.map(function (d) {
                            return d.getData();
                        })[0];
                        var o = arraysOut.map(function (d) {
                            return d.getData();
                        });
                        // note these arrays already have the correct length, so we need to set elements, not append
                        var orientation = o[getVectOutIndex(ORIENTATION_ARRAY)];
                        var linScale = o[getVectOutIndex(LINEAR_SCALE_ARRAY)].fill(1.0);
                        var logScale = o[getVectOutIndex(LOG_SCALE_ARRAY)].fill(1.0);
                        var scalars = o[getVectOutIndex(SCALAR_ARRAY)];

                        for (var i = 0; i < coords.length / 3; i += 1) {
                            var c = [0, 0, 0];
                            if (cmap.length) {
                                var rgb = d3.rgb(colorScale(norms[i]));
                                c = [rgb.r, rgb.g, rgb.b];
                            }
                            // scale arrow length (object-local x-direction) only
                            // this can stretch/squish the arrowhead though so the actor may have to adjust the ratio
                            linScale[3 * i] = vectors.magnitudes[i];
                            logScale[3 * i] = logMags[i];
                            for (var j = 0; j < 3; ++j) {
                                var k = 3 * i + j;
                                orientation[k] = vectors.directions[k];
                                scalars[k] = c[j];
                            }
                        }

                        // Mark the output vtkDataArray as modified
                        arraysOut.forEach(function (x) {
                            x.modified();
                        });
                    },
                };
            }

            function getVectOutIndex(name) {
                for (var vIdx in vectArrays.output) {
                    if (vectArrays.output[vIdx].name === name) {
                        return vIdx;
                    }
                }
                throw new Error('No vector array named ' + name  + ': ' + vectArrays.output);
            }

            function getVectorInfo(point, vect, units) {
                var pt = [];
                point.forEach(function (c) {
                    pt.push(utilities.roundToPlaces(c, 2));
                });
                var val = Math.hypot(vect[0], vect[1], vect[2]);
                var theta = 180 * Math.acos(vect[2] / (val || 1)) / Math.PI;
                var phi = 180 * Math.atan2(vect[1], vect[0]) / Math.PI;
                return isNaN(val) ?
                    '--' :
                    utilities.roundToPlaces(val, 4) + units +
                    '  θ ' + utilities.roundToPlaces(theta, 2) +
                    '°  φ ' + utilities.roundToPlaces(phi, 2) +
                    '°  at (' + pt + ')';
            }

            function handlePick(callData) {
                //srdbg('handle', callData);
                if (renderer !== callData.pokedRenderer) {
                    return;
                }

                // regular clicks are generated when spinning the scene - we'll select/deselect with ctrl-click
                var iMode = vtkAPI.getMode();
                if (iMode === vtkUtils.INTERACTION_MODE_MOVE ||
                    (iMode === vtkUtils.INTERACTION_MODE_SELECT && ! callData.controlKey)
                ) {
                    return;
                }

                var pos = callData.position;
                var point = [pos.x, pos.y, 0.0];
                ptPicker.pick(point, renderer);
                cPicker.pick(point, renderer);
                var pid = ptPicker.getPointId();

                // cell id is "closest cell within tolerance", meaning a single value, though
                // we may get multiple actors
                var cid = cPicker.getCellId();
                //srdbg('Picked pt', point);
                //srdbg('Picked pid', pid);
                //srdbg('Picked cid', cid);

                var picker;
                if (appState.models.magnetDisplay.viewType === VIEW_TYPE_OBJECTS && cid >= 0) {
                    picker = cPicker;
                }
                else if (appState.models.magnetDisplay.viewType === VIEW_TYPE_FIELDS && pid >= 0) {
                    picker = ptPicker;
                }
                if (! picker) {
                    //srdbg('Pick failed');
                    return;
                }

                var pas = picker.getActors();
                //var posArr = view.cPicker.getPickedPositions();
                //srdbg('pas', pas, 'positions', posArr);

                var selectedValue = Number.NaN;
                var highlightVectColor = [255, 0, 0];
                // it seems the 1st actor in the array is the closest to the viewer
                var actor = pas[0];
                vtkSelection = {};
                //var pos = posArr[aIdx];
                var info = getInfoForActor(actor);
                selectedInfo = info;
                //srdbg('actor', actor, 'info', info);
                if (! info || ! info.pData) {
                    return;
                }

                var pts = info.pData.getPoints();

                // TODO(mvk): attach pick functions to actor info?
                // vectors
                if (info.type === radiaVtkUtils.GEOM_TYPE_VECTS) {
                    var n = pts.getNumberOfComponents();
                    var coords = pts.getData().slice(n * pid, n * (pid + 1));
                    var f = actor.getMapper().getInputConnection(0).filter;
                    var linArr = f.getOutputData().getPointData().getArrayByName(LINEAR_SCALE_ARRAY);
                    if (! linArr) {
                        return;
                    }
                    selectedValue = linArr.getData()[pid * linArr.getNumberOfComponents()];

                    var oArr = f.getOutputData().getPointData().getArrayByName(ORIENTATION_ARRAY);
                    var oid = pid * oArr.getNumberOfComponents();
                    var o = oArr.getData().slice(oid, oid + oArr.getNumberOfComponents());
                    var v = o.map(function (dir) {
                        return selectedValue * dir;
                    });

                    var sArr = f.getOutputData().getPointData().getArrayByName(SCALAR_ARRAY);
                    var ns = sArr.getNumberOfComponents();
                    var sid = pid * ns;
                    var sc = sArr.getData().slice(sid, sid + ns);

                    //srdbg('SEL C', sc, selectedColor, 'AT', sid);
                    //srdbg('SET OLD V COLOR');
                    selectedColor.forEach(function (c, i) {
                        sArr.getData()[selectedPointId * ns + i] = c;
                    });
                    if (pid === selectedPointId) {
                        selectedPointId = -1;
                        selectedColor = [];
                        selectedValue = Math.min.apply(null, linArr.getData());
                        v = [];
                    }
                    else {
                        //srdbg('SET NEW V COLOR', pid);
                        //srdbg(sArr.getData().slice(sid, sid + 3), '->', highlightVectColor);
                        highlightVectColor.forEach(function (c, i) {
                            sArr.getData()[sid + i] = c;
                        });
                        selectedPointId = pid;
                        selectedColor = sc;
                    }
                    info.pData.modified();

                    //srdbg(info.id, 'coords', coords, 'mag', selectedValue, 'orientation', o, 'color', sc);
                    vtkSelection = {
                        info: getVectorInfo(point, v, sceneData.data[0].vectors.units),
                    };
                    colorbarPtr.pointTo(selectedValue);
                }

                // objects
                else if (info.type === radiaVtkUtils.GEOM_TYPE_POLYS) {
                    var j = info.colorIndices[cid];
                    selectedColor = info.scalars.getData().slice(j, j + 3);  // 4 to get alpha
                   //srdbg(info.name, 'poly tup', cid, selectedColor);

                    var g = getGeomObj(info.id);
                    if (selectedObj === g) {
                        selectedObj = null;
                    }
                    else {
                        selectedObj = g;
                        selectedOutline = vtk.Filters.General.vtkOutlineFilter.newInstance();
                    }
                    var highlight = selectedColor.map(function (c) {
                        return 255 - c;
                    });

                    for (var id in actorInfo) {
                        setEdgeColor(
                            getActorInfo(id),
                            selectedObj && sharesGroup(getActor(id), actor) ? highlight : [0, 0, 0]
                        );
                    }

                    vtkSelection = {
                        info: selectedObj ? selectedObj.name : '--',
                        model: selectedObj ? {
                            getData: function () {
                                return selectedObj;
                            },
                            modelKey: 'geomObject',
                        } : null,
                    };
                }

                // for some reason scope changes are not immediately propagating, so we'll force the issue -
                // apply() or digest() cause infinite digest loops
                $scope.$broadcast('vtk.selected', vtkSelection);
            }

            function hasPaths() {
                return appState.models.fieldPaths.paths && appState.models.fieldPaths.paths.length;
            }

            function init() {
                //srdbg('init...');
                $scope.$broadcast('sliderParent.ready', appState.models.geometry);
                if (! renderer) {
                    throw new Error('No renderer!');
                }

                var t = 30;
                colorbar = Colorbar()
                    .margin({top: 5, right: t + 10, bottom: 0, left: 0})
                    .thickness(t)
                    .orient('vertical')
                    .barlength($('.vtk-canvas-holder').height())
                    .origin([0, 0]);

                var ca = vtk.Rendering.Core.vtkAnnotatedCubeActor.newInstance();
                vtk.Rendering.Core.vtkAnnotatedCubeActor.Presets.applyPreset('default', ca);
                var df = ca.getDefaultStyle();
                df.fontFamily = 'Arial';
                df.faceRotation = 45;
                ca.setDefaultStyle(df);

                var m = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
                    actor: ca,
                    interactor: renderWindow.getInteractor()
                });
                m.setViewportCorner(
                    vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.TOP_RIGHT
                );
                m.setViewportSize(0.07);
                m.computeViewport();
                m.setMinPixelSize(50);
                m.setMaxPixelSize(100);
                vtkAPI.setMarker(m);
                updateViewer();
            }

            function numColors(polyData, type) {
                if (radiaVtkUtils.GEOM_OBJ_TYPES.indexOf(type) < 0) {
                    return 0;
                }
                if (type === radiaVtkUtils.GEOM_TYPE_LINES) {
                    return numDataColors(polyData.getLines().getData());
                }
                if (type === radiaVtkUtils.GEOM_TYPE_POLYS) {
                    return numDataColors(polyData.getPolys().getData());
                }
            }

            // lines and poly data arrays look like:
            //    [<num vertices for obj 0>, <vertex 0, 0>, ...,]
            function numDataColors(data) {
                var i = 0;
                var j = 0;
                while (i < data.length) {
                    i += (data[i] + 1);
                    ++j;
                }
                return j;
            }

            // some weird disconnect between the model and the slider when cancelling...???
            function setAlpha() {
                if (! renderer) {
                    return;
                }
                var alpha = $scope.gModel.alpha;
                for (var id in actorInfo) {
                    var info = actorInfo[id];
                    var s = info.scalars;
                    if (! s) {
                        info.actor.getProperty().setOpacity(alpha);
                        continue;
                    }
                    setColor(info, radiaVtkUtils.GEOM_TYPE_POLYS, null, Math.floor(255 * alpha));
                }
                renderWindow.render();
            }

            function setBGColor(a, b) {
                renderer.setBackground(vtk.Common.Core.vtkMath.hex2float(appState.models.magnetDisplay.bgColor));
                renderWindow.render();
            }

            //function setColor(info, type, color, alpha=255) {
            function setColor(info, type, color, alpha) {
                //srdbg('setColor', 'info', info, 'type', type, 'color', color, 'alpha', alpha);
                if (angular.isUndefined(alpha)) {
                    alpha = 255;
                }
                var s = info.scalars;
                if (! s) {
                    return;
                }
                if (type !== info.type) {
                    return;
                }
                var colors = s.getData();
                var nc = s.getNumberOfComponents();
                var i = 0;
                var inds = info.colorIndices || [];
                for (var j = 0; j < inds.length && i < s.getNumberOfValues(); ++j) {
                    if (color) {
                        for (var k = 0; k < nc - 1; ++k) {
                            colors[inds[j] + k] = color[k];
                        }
                    }
                    colors[inds[j] + nc - 1] = alpha;
                    i += nc;
                }
                info.pData.modified();
            }

            function setColorMap() {
                getActorsOfType(radiaVtkUtils.GEOM_TYPE_VECTS).forEach(function (actor) {
                    actor.getMapper().getInputConnection(0).filter
                        .setFormula(getVectFormula(
                            sceneData.data[0].vectors,
                            appState.models.fieldDisplay.colorMap
                        ));  // which data? all? at what index?
                });
                if (colorScale) {
                    colorbar.scale(colorScale);
                    colorbarPtr = d3.select('.colorbar').call(colorbar);
                }
                renderWindow.render();
            }

            function setEdgeColor(info, color) {
                if (! info ) {
                    return;
                }
                if (! renderer) {
                    return;
                }
                //info.actor.getProperty().setEdgeColor(...color);
                info.actor.getProperty().setEdgeColor(color[0], color[1], color[2]);
                setColor(info, radiaVtkUtils.GEOM_TYPE_LINES, color);
            }

            function setScaling() {
                var b = renderer.computeVisiblePropBounds();
                var s = [Math.abs(b[1] - b[0]), Math.abs(b[3] - b[2]), Math.abs(b[5] - b[4])];
                //var mx = Math.max(...s);
                var mx = Math.max(s[0], s[1], s[2]);
                //srdbg('prop bnds', b, mx, mx / 8.0, 0.035 * mx);
                getActorsOfType(radiaVtkUtils.GEOM_TYPE_VECTS).forEach(function (actor) {
                    var mapper = actor.getMapper();
                    mapper.setScaleFactor(0.035 * mx);
                    var vs = appState.models.fieldDisplay.scaling;
                    if (vs === 'uniform') {
                        mapper.setScaleModeToScaleByConstant();
                    }
                    if (vs === 'linear') {
                        mapper.setScaleArray(LINEAR_SCALE_ARRAY);
                        mapper.setScaleModeToScaleByComponents();
                    }
                    if (vs === 'log') {
                        mapper.setScaleArray(LOG_SCALE_ARRAY);
                        mapper.setScaleModeToScaleByComponents();
                    }
                });
                renderWindow.render();
            }

            function setupSceneData(data) {
                $rootScope.$broadcast('radiaViewer.loaded');
                sceneData = data;
                buildScene();
                if (! initDone) {
                    initDone = true;
                }
            }

            function sharesGroup(actor1, actor2) {
                if (! actor1 || ! actor2) {
                    return false;
                }
                return getInfoForActor(actor1).group === getInfoForActor(actor2).group;
            }

            function updateLayout() {
                //srdbg('updateLayout', appState.models.magnetDisplay.viewType);
                if ($scope.isViewTypeObjects())  {
                    d3.select('svg.colorbar').remove();
                }
                panelState.showField(
                    'magnetDisplay',
                    'fieldType',
                    $scope.isViewTypeFields()
                );
                panelState.showField(
                    'geometry',
                    'alpha',
                    $scope.isViewTypeObjects()
                );
                radiaService.pointFieldTypes.forEach(function (ft) {
                    panelState.showEnum('magnetDisplay', 'fieldType', ft, hasPaths());
                });
                fieldDisplayFields.forEach(function (f) {
                    var mf = appState.parseModelField(f);
                    panelState.showField(mf[0], mf[1], $scope.isViewTypeFields());
                });
                setColorMap();
                setScaling();
            }

            function updateViewer() {
                //srdbg('update v');
                sceneData = {};
                actorInfo = {};
                radiaService.objBounds = null;
                //enableWatchFields(false);
                var inData = {
                    method: 'get_geom',
                    name: appState.models.geometry.name,
                    viewType: appState.models.magnetDisplay.viewType,
                    simulationId: appState.models.simulation.simulationId,
                };
                if ($scope.isViewTypeFields()) {
                    inData.fieldType = appState.models.magnetDisplay.fieldType;
                    inData.method = 'get_field';
                }
                if (radiaService.pointFieldTypes.indexOf(appState.models.magnetDisplay.fieldType) >= 0 ) {
                    inData.fieldPaths = appState.models.fieldPaths.paths;
                }

                //srdbg('getting app data...');
                requestSender.getApplicationData(
                    inData,
                    function(d) {
                        //srdbg('got app data', d);
                        if (d && d.data && d.data.length) {
                            if ($scope.isViewTypeFields()) {
                                // get the lines in a separate call - downside is longer wait
                                delete inData.fieldType;
                                inData.geomTypes = ['lines'];
                                inData.method = 'get_geom';
                                inData.viewType = VIEW_TYPE_OBJECTS;
                                requestSender.getApplicationData(
                                    inData,
                                    function(g) {
                                        if (g && g.data) {
                                            d.data = d.data.concat(g.data);
                                        }
                                        setupSceneData(d);
                                    }
                                );
                                return;
                            }
                            setupSceneData(d);
                            return;
                        }
                        if (d.error) {
                            throw new Error(d.error);
                        }
                        //srdbg('no app data, requesting');
                        panelState.clear('geometry');
                        panelState.requestData('geometry', setupSceneData, true);
                    });
            }

            $scope.eventHandlers = {
                keypress: function (evt) {
                    // do nothing?  Stops vtk from changing render based on key presses
                },
                //ondblclick: function(evt) {
                //    vtkAPI.setCam();
                //}
            };

            appState.whenModelsLoaded($scope, function () {
                $scope.model = appState.models[$scope.modelName];
                $scope.gModel = appState.models.geometry;
                appState.watchModelFields($scope, watchFields, updateLayout);
                appState.watchModelFields($scope, ['magnetDisplay.bgColor'], setBGColor);
                alphaDelegate = radiaService.alphaDelegate();
                alphaDelegate.update = setAlpha;
                panelState.enableField('geometry', 'name', ! appState.models.simulation.isExample);
            });

            // or keep stuff on vtk viewer scope?
            // start using custom javascript events to break away from angular?
            $scope.$on('vtk-init', function (e, d) {
                //srdbg('VTK INIT', e, d);
                renderer = d.objects.renderer;
                renderWindow = d.objects.window;
                vtkAPI = d.api;
                // move pickers to vtkdisplay?
                cPicker = vtk.Rendering.Core.vtkCellPicker.newInstance();
                cPicker.setPickFromList(false);
                ptPicker = vtk.Rendering.Core.vtkPointPicker.newInstance();
                ptPicker.setPickFromList(true);
                ptPicker.initializePickList();
                renderWindow.getInteractor().onLeftButtonPress(handlePick);
                init();
            });

            $scope.$on('modelChanged', function(e, name) {
                //srdbg('modelChanged', name);
            });

            $scope.$on('geomObject.changed', function(e) {
                appState.saveChanges('geometry', function (d) {
                    //srdbg('geom save', d);
                });
            });

            $scope.$on('fieldPaths.changed', function () {
                if (! $scope.model.fieldPoints) {
                    $scope.model.fieldPoints = [];
                }
                updateViewer();
            });

            $scope.$on('geomObject.color', function (e, h) {
                var c = vtk.Common.Core.vtkMath.hex2float(h);
                setColor(
                    selectedInfo,
                    radiaVtkUtils.GEOM_TYPE_POLYS,
                    vtkUtils.floatToRGB(c)
                );
                setAlpha();
            });

            $scope.$on('magnetDisplay.changed', function (e, d) {
                //srdbg('MDC', e, d);
                // does not seem the best way...
                var interval = null;
                interval = $interval(function() {
                    if (interval) {
                        $interval.cancel(interval);
                        interval = null;
                    }
                    updateViewer();
                }, 500, 1);
            });

            $scope.$on('framesCleared', function () {
                updateViewer();
            });
            $scope.$on('framesLoaded', function (e, d) {
                if (! initDone) {
                    return;
                }
                updateViewer();
            });

            $scope.$on('solveStarted', function (e, d) {
            });

        },
    };
});

SIREPO.app.factory('radiaVtkUtils', function(utilities) {

    var self = {};

    self.GEOM_TYPE_LINES = 'lines';
    self.GEOM_TYPE_POLYS = 'polygons';
    self.GEOM_TYPE_VECTS = 'vectors';
    self.GEOM_OBJ_TYPES = [self.GEOM_TYPE_LINES, self.GEOM_TYPE_POLYS];
    self.GEOM_TYPES = [self.GEOM_TYPE_LINES, self.GEOM_TYPE_POLYS, self.GEOM_TYPE_VECTS];

    self.objBounds = function(json) {
        var mins = [Number.MAX_VALUE, Number.MAX_VALUE, Number.MAX_VALUE];
        var maxs = [-Number.MAX_VALUE, -Number.MAX_VALUE, -Number.MAX_VALUE];

        self.GEOM_TYPES.forEach(function (type) {
            if (! json[type]) {
                return;
            }
            var pts = json[type].vertices;
            function modf(j) {
                return function(p, i) {
                    return i % 3 === j;
                };
            }
            for (var j = 0; j < 3; ++j) {
                //var c = pts.filter(function (p, i) {
                //    return i % 3 === j;
                //});
                var c = pts.filter(modf(j));
                mins[j] =  Math.min(mins[j], Math.min.apply(null, c));
                maxs[j] =  Math.max(maxs[j], Math.max.apply(null, c));
            }
        });

        return [mins[0], maxs[0], mins[1], maxs[1], mins[2], maxs[2]];
    };

    self.objToPolyData = function(json, includeTypes, color) {

        var colors = [];
        var points = [];
        var tData = {};

        if (! includeTypes || includeTypes.length === 0) {
            includeTypes = self.GEOM_TYPES;
        }

        var typeInfo = {};
        self.GEOM_TYPES.forEach(function (type, tIdx) {
            typeInfo[type] = {};
            if (includeTypes.indexOf(type) < 0) {
                //srdbg('Ignoring data for type', type);
                return;
            }

            var t = json[type];
            if (! t || json[type].vertices.length === 0) {
                //srdbg('No data for requested type', type);
                return;
            }

            // may not always be colors in the data
            var c = t.colors || [];
            for (var i = 0; i < c.length; i++) {
                var cc = (color || [])[i % 3] || c[i];
                colors.push(Math.floor(255 * cc));
                if (i % 3 === 2) {
                    colors.push(255);
                }
            }

            var tArr = [];
            var tOffset = points.length / 3;
            typeInfo[type].offset = tOffset;
            t.vertices.forEach(function (v) {
                points.push(v);
            });
            var tInd = 0;
            var tInds = utilities.indexArray(t.vertices.length / 3);
            t.lengths.forEach(function (len) {
                tArr.push(len);
                for (var j = 0; j < len; j++) {
                    tArr.push(tInds[tInd++] + tOffset);
                }
            });
            if (tArr.length) {
                tData[type] = new window.Uint32Array(tArr);
            }

        });

        points = new window.Float32Array(points);

        var pd = vtk.Common.DataModel.vtkPolyData.newInstance();
        pd.getPoints().setData(points, 3);

        //srdbg('setting polydata from', tData);
        if (tData.lines) {
            pd.getLines().setData(tData.lines);
        }
        if (tData.polygons) {
            pd.getPolys().setData(tData.polygons, 1);
        }

        pd.getCellData().setScalars(vtk.Common.Core.vtkDataArray.newInstance({
            numberOfComponents: 4,
            values: colors,
            dataType: vtk.Common.Core.vtkDataArray.VtkDataTypes.UNSIGNED_CHAR
        }));

        pd.buildCells();

        return {data: pd, typeInfo: typeInfo};
    };

    self.vectorsToPolyData = function(json) {
        var points = new window.Float32Array(json.vectors.vertices);
        var pd = vtk.Common.DataModel.vtkPolyData.newInstance();
        pd.getPoints().setData(points, 3);
        return pd;
    };

    return self;
});
