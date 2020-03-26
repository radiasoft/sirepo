'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.SINGLE_FRAME_ANIMATION = ['solver'];
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="Color" data-ng-class="fieldClass">',
          '<div data-color-picker="" data-color="model.color" data-model="model" data-field="field" data-default-color="defaultColor"></div>',
        '</div>',
        '<div data-ng-switch-when="PtsFile" data-ng-class="fieldClass">',
          '<input id="radia-pts-file-import" type="file" data-file-model="model[field]" accept=".dat,.txt"/>',
        '</div>',
    ].join('');

});

SIREPO.app.factory('radiaService', function(appState, fileUpload, panelState, requestSender) {
    var self = {};

    // why is this here?
    self.computeModel = function(analysisModel) {
        return 'solver';
    };

    self.isEditing = false;
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
                min: appState.modelInfo(m)[f][SIREPO.INFO_INDEX_MIN],
                max: appState.modelInfo(m)[f][SIREPO.INFO_INDEX_MAX],
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
        srdbg('create', t);
        var model = {
            id: numPathsOfType(t),
        };
        appState.models[t] = appState.setModelDefaults(model, t);
    };

    self.getPathType = function() {
        srdbg('getPathType', appState.models.fieldTypes.path);
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

    self.showPathPicker = function(doShow, isNew) {
        //srdbg('showPathPicker show?', doShow, 'new?', isNew);
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
    const self = this;

    appState.whenModelsLoaded($scope, function() {
        // initial setup
        //appState.watchModelFields($scope, ['model.field'], function() {
        //});
        //srdbg('RadiaSourceController');
    });
});

SIREPO.app.controller('RadiaVisualizationController', function (appState, errorService, frameCache, panelState, persistentSimulation, radiaService, $scope) {

    const self = this;

    var SINGLE_PLOTS = ['magnetViewer'];
    $scope.mpiCores = 0;
    $scope.panelState = panelState;
    $scope.svc = radiaService;

    function handleStatus(data) {
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
                SINGLE_PLOTS.forEach(function(name) {
                    frameCache.setFrameCount(1, name);
                });
            }
        }
        frameCache.setFrameCount(data.frameCount);
    }

    self.startSimulation = function() {
        $scope.$broadcast('solveStarted', self.simState);
        self.simState.saveAndRunSimulation('simulation');
    };

    self.simState = persistentSimulation.initSimulationState(
        $scope,
        radiaService.computeModel(),
        handleStatus
    );

    appState.whenModelsLoaded($scope, function() {
        // initial setup
       // appState.watchModelFields($scope, ['model.field'], function() {
        //});
        //srdbg('RadiaVisualizationController', appState.models);
    });
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
            $scope.pathTypes = appState.enumVals('PathType');
            $scope.pathTypeModels = $scope.pathTypes.map(radiaService.pathTypeModel);
            $scope.radiaService = radiaService;

           $scope.getPathType = function() {
                return ($scope.model || {}).path;
           };

           function numPathsOfType(type) {
                if (! $scope.model.paths) {
                    return 0;
                }
                return $scope.model.paths.filter(function (p) {
                    return p.type === type;
                }).length;
           }

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

                $scope.modelsLoaded = true;
            });
        },
    };
});

SIREPO.app.directive('fieldPathTable', function(appState, radiaService) {
    return {
        restrict: 'A',
        scope: {},
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
                            ' <button data-ng-click="deletePath(path, $index)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button>',
                        '</div>',
                    '<div>',
                  '</td>',
                '</tr>',
              '</tbody>',
            '</table>',
        ].join(''),
        controller: function($scope) {

            $scope.hasPaths = function() {
                return $scope.paths && $scope.paths.length;
            };

            $scope.isActivePath = function(path) {
                return false;
            };

            $scope.copyPath = function(path) {
                srdbg('CPY', path);
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
               var excludeFields = ['_super', 'fileModel', 'id', 'name', 'type', 'numPoints'];
               var res = '';
               var pt = radiaService.pathTypeModel(path.type);
               var vf = appState.viewInfo(pt).basic;
               var info = appState.modelInfo(pt);
               Object.keys(info).filter(function (f) {
                    return excludeFields.indexOf(f) < 0;
               })
                   .forEach(function (f, i) {
                       var fi = info[f];
                       res += (fi[0] + ': ' + path[f] + '; ');
               });
               return res;
           };

           appState.whenModelsLoaded($scope, function() {
               $scope.paths = appState.models.fieldPaths.paths;
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
                        '<div data-field-path-table=""></div>',
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
            srdbg('m', $scope.model);
            appState.whenModelsLoaded($scope, function () {
            });
        },
    };
});

// does not need to be its own directive?  everything in viz and service? (and move template to html)
SIREPO.app.directive('radiaSolver', function(appState, errorService, frameCache, geometry, layoutService, panelState) {

    return {
        restrict: 'A',
        scope: {
            viz: '<',
            modelName: '@',
        },
        template: [
            '<div class="col-md-6">',
                '<div data-basic-editor-panel="" data-view-name="solver">',
                    '<div class="col-sm-6 col-sm-offset-5">',
                    '<button class="btn btn-default" data-ng-click="solve()">Solve</button> ',
                    '<button class="btn btn-default" data-ng-click="reset()">Reset</button>',
                    '</div>',
                '</div>',
            '</div>',

        ].join(''),
        controller: function($scope, $element) {

            $scope.model = appState.models[$scope.modelName];

            $scope.solve = function() {
                $scope.viz.startSimulation();
            };

            // not sure how to do this - want Radia to keep geom defs but forget the fields...???
            $scope.reset = function() {
                panelState.clear('geometry');
                panelState.requestData('reset', function (d) {
                    frameCache.setFrameCount(0);
                }, true);
            };

            appState.whenModelsLoaded($scope, function () {

            });


        },
    };
});

SIREPO.app.directive('radiaViewer', function(appState, errorService, frameCache, geometry, layoutService, panelState, plotting, plotToPNG, radiaService, radiaVtkUtils, requestSender, utilities, vtkPlotting, vtkUtils, $interval) {

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: [
            '<div class="col-md-6">',
                '<div data-basic-editor-panel="" data-view-name="{{ modelName }}">',
                    '<div data-vtk-display="" class="vtk-display" data-show-border="true" data-model-name="{{ modelName }}" data-event-handlers="eventHandlers" data-enable-axes="true" data-enable-selection="true" data-selected-info="selectedInfo()" data-selected-model="selectedModel()"></div>',
                '</div>',
            '</div>',

        ].join(''),
        controller: function($scope, $element) {

            $scope.defaultColor = "#ff0000";
            $scope.gModel = null;
            //$scope.selectedObj = null;

            $scope.selectedInfo = function () {
                if (selectedObj) {
                    return selectedObj.name;
                }
                return '--';
            };

            $scope.selectedModel = function () {
                if (! selectedObj) {
                    return null;
                }
                return {
                    name: 'geomObject',
                    model: {
                        getData: function () {
                            return selectedObj;
                        }
                    }
                };
            };

            var LINEAR_SCALE_ARRAY = 'linear';
            var LOG_SCALE_ARRAY = 'log';
            var ORIENTATION_ARRAY = 'orientation';
            var FIELD_ATTR_ARRAYS = [LINEAR_SCALE_ARRAY, LOG_SCALE_ARRAY, ORIENTATION_ARRAY];

            var PICKABLE_TYPES = [radiaVtkUtils.GEOM_TYPE_POLYS, radiaVtkUtils.GEOM_TYPE_VECTS];

            var SCALAR_ARRAY = 'scalars';

            var VIEW_TYPE_FIELDS = 'fields';
            var VIEW_TYPE_OBJECTS = 'objects';
            var VIEW_TYPES = appState.enumVals('ViewType');

            var actorInfo = {};
            var alphaDelegate = null;
            var cm = vtkPlotting.coordMapper();
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
            var selectedObj = null;
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
            function addActor(name, group, actor, type, pickable) {

                const pData = actor.getMapper().getInputData();
                const info = {
                    actor: actor,
                    colorIndices: [],
                    group: group || 0,
                    name: name,
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
                actorInfo[name] = info;

                vtkPlotting.addActor(renderer, actor);
                if (pickable) {
                    //this.ptPicker.addPickList(actor);
                    //this.cPicker.addPickList(actor);
                }
                return info;
            }

            function buildScene() {
                //srdbg('buildScene');
                var name = sceneData.name;
                var id = sceneData.id;
                var data = sceneData.data;
                srdbg('got data', data, 'for', name, id);

                vtkPlotting.removeActors(renderer);
                var didModifyGeom = false;
                for (var i = 0; i < data.length; ++i) {

                    var gname = name + '.' + i;
                    var sceneDatum = data[i];
                    var bounds = radiaVtkUtils.objBounds(sceneDatum);

                    // trying a separation into an actor for each data type, to better facilitate selection
                    radiaVtkUtils.GEOM_TYPES.forEach(function (t) {
                        var aname = gname + '.' + t;
                        var d = sceneDatum[t];
                        if (! d || ! d.vertices || ! d.vertices.length) {
                            return;
                        }
                        var isPoly = t === radiaVtkUtils.GEOM_TYPE_POLYS;
                        var gObj = getGeomObj(aname) || {};
                        var gColor = gObj.color ? vtk.Common.Core.vtkMath.hex2float(gObj.color) : null;
                        var pdti = radiaVtkUtils.objToPolyData(sceneDatum, [t], gColor);
                        var pData = pdti.data;
                        var bundle = null;
                        var actor = null;
                        if (radiaVtkUtils.GEOM_OBJ_TYPES.indexOf(t) >= 0) {
                            bundle = cm.buildActorBundle();
                            bundle.mapper.setInputData(pData);
                        }
                        else {
                            var vectorCalc = vtk.Filters.General.vtkCalculator.newInstance();
                            vectorCalc.setFormula(getVectFormula(d, ''));
                            vectorCalc.setInputData(pData);

                            var mapper = vtk.Rendering.Core.vtkGlyph3DMapper.newInstance();
                            mapper.setInputConnection(vectorCalc.getOutputPort(), 0);

                            var s = vtk.Filters.Sources.vtkArrowSource.newInstance();
                            mapper.setInputConnection(s.getOutputPort(), 1);
                            mapper.setOrientationArray(ORIENTATION_ARRAY);

                            // this scales by a constant - the default is to use scalar data
                            //TODO(mvk): set based on bounds size?
                            mapper.setScaleFactor(8.0);
                            mapper.setScaleModeToScaleByConstant();
                            mapper.setColorModeToDefault();
                            bundle = cm.buildActorBundle();
                            bundle.setMapper(mapper);
                        }
                        bundle.actor.getProperty().setEdgeVisibility(isPoly);
                        bundle.actor.getProperty().setLighting(isPoly);
                        var info = addActor(aname, gname, bundle.actor, t, PICKABLE_TYPES.indexOf(t) >= 0);
                        gColor = getColor(info);
                        //srdbg('add obj', gObj, isPoly);
                        if (isPoly && $.isEmptyObject(gObj)) {
                            gObj = appState.setModelDefaults(gObj, 'geomObject');
                            gObj.name = aname;
                            if (gColor) {
                                srdbg('storing color');
                                gObj.color = vtk.Common.Core.vtkMath.floatRGB2HexCode(vtkUtils.rgbToFloat(gColor));
                            }
                            if (! appState.models.geometry.objects) {
                                appState.models.geometry.objects = [];
                            }
                            appState.models.geometry.objects.push(gObj);
                            didModifyGeom = true;
                        }
                    });
                }

                if (didModifyGeom) {
                    srdbg('MOD GEOM SAVE');
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

            function getActor(name) {
                return (getActorInfo(name) || {}).actor;
            }

            function getActorInfo(name) {
                return actorInfo[name];
            }

            function getActorInfoOfType(typeName) {
                return Object.keys(actorInfo)
                    .filter(function (name) {
                        return getActorInfo(name).type === typeName;
                    })
                    .map(function (name) {
                        return getActorInfo(name);
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

            function getGeomObj(name) {
                var gObjs = appState.models.geometry.objects || [];
                for (var i = 0; i < gObjs.length; ++i) {
                    if (gObjs[i].name === name) {
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

                //srdbg('getVectFormula', colorMapName, '!');
                var cmap = plotting.colorMapOrDefault(
                    colorMapName,
                    appState.modelInfo('fieldDisplay').colorMap[SIREPO.INFO_INDEX_DEFAULT_VALUE]
                );
                //srdbg('v', vectors, 'cm', cmap);
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
                                var cIdx = Math.floor(norms[i] * (cmap.length - 1));
                                var h = parseInt(cmap[cIdx].substring(1), 16);
                                c = plotting.rgbFromInt(h);
                            }
                            // scale arrow length (object-local x-direction) only
                            // this can stretch/squish the arrowhead though so the actor may have to adjust the ratio
                            linScale[3 * i] = vectors.magnitudes[i];
                            logScale[3 * i] = logMags[i];
                            for (var j = 0; j < 3; ++j) {
                                const k = 3 * i + j;
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
                for (let vIdx in vectArrays.output) {
                    if (vectArrays.output[vIdx].name === name) {
                        return vIdx;
                    }
                }
                throw new Error('No vector array named ' + name  + ': ' + vectArrays.output);
            }

            function handlePick(callData) {
                //srdbg('handle', callData);
                if (renderer !== callData.pokedRenderer) {
                    return;
                }

                //srdbg('mode?', vtkAPI.getMode());
                // regular clicks happen when spinning the scene - we'll select/deselect with ctrl-click.
                // Though one also rotates in that case, it's less common
                //if (! callData.controlKey) {
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
                srdbg('Picked pt', point);
                srdbg('Picked pid', pid);
                srdbg('Picked cid', cid);

                // treat pickers separately rather than select one?
                var picker = cid >= 0 ? cPicker : (pid >= 0 ? ptPicker : null);
                if (cid < 0 && pid < 0) {
                    srdbg('Pick failed');
                    return;
                }


                var pas = picker.getActors();
                //let posArr = view.cPicker.getPickedPositions();
                //srdbg('pas', pas, 'positions', posArr);
                //TODO(mvk): need to get actor closest to the "screen" based on the selected points

                var selectedColor = [];
                var selectedInfo = null;
                var selectedValue = Number.NaN;
                var eligibleActors = [];
                var highlightVectColor = [255, 0, 0];
                for (var aIdx in pas) {
                    var actor = pas[aIdx];
                    //let pos = posArr[aIdx];
                    var info = getInfoForActor(actor);
                    //srdbg('actor', actor, 'info', info);
                    if (! info || ! info.pData) {
                        continue;
                    }

                    var pts = info.pData.getPoints();

                    // TODO(mvk): attach pick functions to actor info?
                    if (info.type === radiaVtkUtils.GEOM_TYPE_VECTS) {
                        var n = pts.getNumberOfComponents();
                        var coords = pts.getData().slice(n * pid, n * (pid + 1));
                        var f = actor.getMapper().getInputConnection(0).filter;
                        var linArr = f.getOutputData().getPointData().getArrayByName(LINEAR_SCALE_ARRAY);
                        if (! linArr) {
                            continue;
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

                        // toggle color?
                        if (view.selectedColor.length) {
                            const ssid = view.selectedPoint * ns;
                            view.selectedColor.forEach(function (c, i) {
                                sArr.getData()[ssid + i] = c;
                            });
                        }
                        if (pid === view.selectedPoint) {
                            view.selectedPoint = -1;
                            view.selectedColor = [];
                            selectedValue = Math.min.apply(null, linArr.getData());
                            v = [];
                        }
                        else {
                            highlightVectColor.forEach(function (c, i) {
                                sArr.getData()[sid + i] = c;
                            });
                            view.selectedPoint = pid;
                            view.selectedColor = sc;
                        }
                        info.pData.modified();

                        //srdbg(info.name, 'coords', coords, 'mag', selectedValue, 'orientation', o, 'color', sc);
                        view.processPickedVector(coords, v);
                        continue;
                    }

                    var colors = info.scalars.getData();
                    var j = info.colorIndices[cid];
                    selectedColor = colors.slice(j, j + 3);  // 4 to get alpha
                    selectedInfo = info;
                    srdbg(info.name, 'poly tup', cid, selectedColor);

                    //if (selectedColor.length > 0) {
                    //    if (actor === view.selectedObject) {
                    ///        view.selectedObject = null;
                    //    }
                    //    else {
                    //        eligibleActors.push(actor);
                    //        view.selectedObject = actor;
                    //    }
                    //    break;
                    //}
                }

                //if (selectedColor.length === 0) {
                //    view.selectedObject = null;
                //    return;
                //}

                if (! selectedInfo) {
                    return;
                }
                //$scope.selectedObj = getGeomObj(selectedInfo.name);
                //$scope.$apply(function () {
                    selectedObj = getGeomObj(selectedInfo.name);
                    //$scope.selectedObj = getGeomObj(selectedInfo.name);
                //});
                $scope.$broadcast('vtkModel.selected', $scope.selectedModel());
                radiaService.setSelectedObj(selectedObj);
                //srdbg('sel o', $scope.selectedObj);
                //appState.models.geomObject = g;
                //panelState.showModalEditor('geomObject');
                //$('#radia-edit-geom-obj').modal('show');
                editSelectedObj(point);

                var sc = vtkUtils.rgbToFloat(selectedColor);  //[];
                //for (var cIdx = 0; cIdx < selectedColor.length; ++cIdx) {
                //    sc.push(selectedColor[cIdx] / 255.0);
                //}

                var highlight = selectedColor.map(function (c) {
                    return 255 - c;
                });

                //var sch = vtk.Common.Core.vtkMath.floatRGB2HexCode(sc);
                //view.model.set('selected_obj_color', view.selectedObject ? sch : '#ffffff');
                //for (var name in view.actorInfo) {
                //    var a = view.getActor(name);
                //    view.setEdgeColor(a, view.sharesGroup(a, view.selectedObject) ? highlight : [0, 0, 0]);
                //}
                //view.processPickedObject(view.getInfoForActor(view.selectedObject));
            }

            function editSelectedObj(point) {
                //srdbg('edit', radiaService.selectedObj);
                //$('#radia-edit-geom-obj').modal('show');
                /*
                var modal = $('<div data-id="radia-edit-geom-obj" data-model="selectedObj"></div>');
                var cp = $($element).find('canvas').position();
                var co = $($element).find('canvas').offset();
                modal.css('position', 'relative');
                modal.width(200);
                modal.height(200);
                //modal.css('left', point[0] - cp.left);
                //modal.css('top', point[1] - cp.top);
                var pixels = window.devicePixelRatio;
                modal.css('left', point[0] / pixels);
                modal.css('top', point[1] / pixels);
                //modal.css('left', 100);
                //modal.css('top', 100);
                srdbg('modal', modal, 'cp', cp, 'co', co, 'pt', point);
                //srdbg(point[0] - cp.left, point[1] - cp.top, pixels);
                //$($element).append(modal);
                $('.vtk-canvas-holder').append(modal);
                 */
            }

            function hasPaths() {
                return appState.models.fieldPaths.paths && appState.models.fieldPaths.paths.length;
            }

            function init() {
                srdbg('init...');
                $scope.$broadcast('sliderParent.ready', appState.models.geometry);
                if (! renderer) {
                    throw new Error('No renderer!');
                }
                const ca = vtk.Rendering.Core.vtkAnnotatedCubeActor.newInstance();
                vtk.Rendering.Core.vtkAnnotatedCubeActor.Presets.applyPreset('default', ca);
                let df = ca.getDefaultStyle();
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
                //srdbg('SETA alpha GMODEL', alpha, 'APPST', appState.models.geometry.alpha);
                for (var name in actorInfo) {
                    var info = actorInfo[name];
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

            function setColor(info, type, color, alpha=255) {
               // srdbg(info, 'setColor', type, color, alpha);
                const s = info.scalars;
                if (! s) {
                    return;
                }
                if (type !== info.type) {
                    return;
                }
                const colors = s.getData();
                const nc = s.getNumberOfComponents();
                let i = 0;
                const inds = info.colorIndices || [];
                for (let j = 0; j < inds.length && i < s.getNumberOfValues(); ++j) {
                    if (color) {
                        for (let k = 0; k < nc - 1; ++k) {
                            colors[inds[j] + k] = color[k];
                        }
                    }
                    colors[inds[j] + nc - 1] = alpha;
                    i += nc;
                }
                info.pData.modified();
            }

            function setColorMap() {
                var mapName = appState.models.fieldDisplay.colorMap;
                getActorsOfType(radiaVtkUtils.GEOM_TYPE_VECTS).forEach(function (actor) {
                    actor.getMapper().getInputConnection(0).filter
                        .setFormula(getVectFormula(sceneData.data[0].vectors, mapName));  // which data? all? at what index?
                });
                renderWindow.render();
            }

            function setScaling() {
                var b = renderer.computeVisiblePropBounds();
                var s = [Math.abs(b[1] - b[0]), Math.abs(b[3] - b[2]), Math.abs(b[5] - b[4])];
                var mx = Math.max(...s);
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
                sceneData = data;
                buildScene();
                if (! initDone) {
                    initDone = true;
                }
            }

            function updateLayout() {
                //srdbg('updateLayout', appState.models.magnetDisplay.viewType);
                panelState.showField(
                    'magnetDisplay',
                    'fieldType',
                    appState.models.magnetDisplay.viewType === VIEW_TYPE_FIELDS
                );
                panelState.showField(
                    'geometry',
                    'alpha',
                    appState.models.magnetDisplay.viewType === VIEW_TYPE_OBJECTS
                );
                radiaService.pointFieldTypes.forEach(function (ft) {
                    panelState.showEnum('magnetDisplay', 'fieldType', ft, hasPaths());
                });
                fieldDisplayFields.forEach(function (f) {
                    var mf = appState.parseModelField(f);
                    panelState.showField(mf[0], mf[1], appState.models.magnetDisplay.viewType === VIEW_TYPE_FIELDS);
                });
                setColorMap();
                setScaling();
            }

            function updateObjects() {
                srdbg('UPDATE OBJ');
            }

            function updateViewer() {
                sceneData = {};
                actorInfo = {};
                enableWatchFields(false);
                var inData = {
                    method: 'get_geom',
                    name: appState.models.geometry.name,
                    viewType: appState.models.magnetDisplay.viewType,
                    simulationId: appState.models.simulation.simulationId,
                };
                if (appState.models.magnetDisplay.viewType === VIEW_TYPE_FIELDS) {
                    inData.fieldType = appState.models.magnetDisplay.fieldType;
                }
                if (radiaService.pointFieldTypes.indexOf(appState.models.magnetDisplay.fieldType) >= 0 ) {
                    inData.fieldPaths = appState.models.fieldPaths.paths;
                }

                srdbg('getting app data...');
                requestSender.getApplicationData(
                    inData,
                    function(d) {
                        srdbg('got app data', d);
                        if (d && d.data) {
                            setupSceneData(d);
                            return;
                        }
                        srdbg('no app data, requesting');
                        panelState.clear('geometry');
                        panelState.requestData('geometry', setupSceneData, true);
                    });
            }


            $scope.eventHandlers = {
                handleDblClick: function(e) {
                    vtkAPI.setCam();
                }
            };

            appState.whenModelsLoaded($scope, function () {
                //srdbg('whenModelsLoaded g', appState.models.geometry);
                $scope.model = appState.models[$scope.modelName];
                $scope.gModel = appState.models.geometry;
                appState.watchModelFields($scope, watchFields, updateLayout);
                appState.watchModelFields($scope, ['magnetDisplay.bgColor'], setBGColor);
                appState.watchModelFields($scope, ['geometry.objects'], updateObjects);
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

            $scope.$on('cancelChanges', function(e, name) {
                //srdbg('cancel', name);
            //    if ($scope.modelName === name) {
            //        //srdbg('cancel', name, $scope.model, appState.models[name]);
            //    }
            });

           $scope.$on('fieldPaths.changed', function () {
                if (! $scope.model.fieldPoints) {
                    $scope.model.fieldPoints = [];
                }
                if (! appState.models.fieldPaths.paths || ! appState.models.fieldPaths.paths.length) {
                    return;
                }
                updateViewer();
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
                    //srdbg('UV from magnetDisplay.changed');
                    //updateViewer(true);
                    updateViewer();
                }, 500, 1);
            });

            $scope.$on('framesCleared', function () {
                srdbg('FC');
                updateViewer();
            });
            $scope.$on('framesLoaded', function (e, d) {
                //srdbg('F', e, d);
                if (! initDone) {
                    //srdbg('init in progress, ignore');
                    return;
                }
                //srdbg('UV from framesLoaded');
                updateViewer();
            });

            $scope.$on('solveStarted', function (e, d) {
                //srdbg('S', e, d);
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
            for (var j = 0; j < 3; ++j) {
                var c = pts.filter(function (p, i) {
                    return i % 3 === j;
                });
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
                srdbg('No data for requested type', type);
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