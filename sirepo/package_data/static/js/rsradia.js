'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.SINGLE_FRAME_ANIMATION = ['solver'];
    //SIREPO.appReportTypes = [
    //    '<div data-ng-switch-when="linePath" data-conductor-grid="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-id="reportId"></div>',
    //].join('');
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="PtsFile" data-ng-class="fieldClass">',
          '<input id="radia-pts-file-import" type="file" data-file-model="ptsFile" accept=".dat,.txt" />',
        '</div>',
    ].join('');

});

SIREPO.app.factory('radiaService', function(appState, requestSender, $rootScope) {
    var self = {};

    var pathPts = {
        circle: circlePts,
        file: filePts,
        line: linePts,
        manual: manualPts,
    };

    // why is this here?
    self.computeModel = function(analysisModel) {
        return 'solver';
    };

    //self.pointFieldTypes = SIREPO.APP_SCHEMA.enum.FieldType.slice(1).map(function (tArr) {
    //    return tArr[0];
    //});

    self.pointFieldTypes = appState.enumVals('FieldType').slice(1);

    self.newPath = function() {
        srdbg('ADD PATH');
    };

    // to geometry?
    self.pointsForPath = function(path) {
        //srdbg('pt', path.type);
        if (! path.type || Object.keys(pathPts).indexOf(path.type) < 0) {
            throw new Error(path.type + ': Unknown path type');
        }
        return pathPts[path.type](path);
    };


    function circlePts(path) {
        srdbg('pts from circle', path);
        var pts = [];
        var ctr = [path.ctrX, path.ctrY, path.ctrZ].map(toFloat);
        var r = toFloat(path.radius);
        // theta is a rotation about the x-axis
        var th = toFloat(path.theta);
        // phi is a rotation about the z-axis
        var phi = toFloat(path.phi);
        var n = toInt(path.numPoints);
        var dpsi = 2.0 * Math.PI / n;
        // psi is the angle in the circle's plane
        for (var i = 0; i < n; ++i) {
            var psi = i * dpsi;
            pts.push(
                r * Math.sin(psi) * Math.cos(phi) - r * Math.cos(psi) * Math.cos(th) * Math.sin(phi) + ctr[0],
                r * Math.sin(psi) * Math.sin(phi) - r * Math.cos(psi) * Math.cos(th) * Math.cos(phi) + ctr[1],
                r * Math.cos(psi) * Math.sin(th) + ctr[2]
            );
        }
        return pts;
    }

    function filePts(path) {
        return [];
    }

    function linePts(path) {
        var pts = [];
        var p1 = [path.beginX, path.beginY, path.beginZ].map(toFloat);
        var p2 = [path.endX, path.endY, path.endZ].map(toFloat);
        var n = toInt(path.numPoints) - 1;
        pts.push(...p1);
        for (var i = 1; i < n ; ++i) {
            for (var j = 0; j < 3; ++j) {
                pts.push(p1[j] + i * (p2[j] - p1[j]) / n);
            }
        }
        pts.push(...p2);
        return pts;
    }

    function manualPts(path) {
        return [path.ptX, path.ptY, path.ptZ].map(toFloat);
    }

    function toFloat(v) {
        return parseFloat('' + v);
    }
    function toInt(v) {
        return parseInt('' + v);
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


SIREPO.app.directive('fieldPathTable', function(appState, radiaService) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<table data-ng-if="hasPaths()" style="width: 100%; table-layout: fixed; margin-bottom: 10px" class="table table-hover">',
              '<colgroup>',
                '<col style="width: 20ex">',
                '<col style="width: 100%">',
                '<col style="width: 12ex">',
              '</colgroup>',
              '<thead>',
                '<tr>',
                  '<th>Name</th>',
                  '<th>Type</th>',
                  '<th>Details</th>',
                '</tr>',
              '</thead>',
              '<tbody>',
                '<tr data-ng-repeat="path in paths track by $index">',
                  '<td><div class="badge sr-badge-icon sr-lattice-icon"><span>{{ path.name }}</span></div></td>',
                  '<td><span>{{ path.type }}</span></td>',
                  '<td style="text-align: right">',
                    '<span>STUFF</span>',
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
                srdbg('DEL', path);
                $scope.paths.splice(index, 1);
           };

           $scope.editPath = function(path) {
                srdbg('EDIT', path);
           };

           appState.whenModelsLoaded($scope, function() {
               $scope.paths = appState.models.fieldPaths.paths;
           });
        },
    };
});

SIREPO.app.directive('radiaFieldPaths', function(appState, radiaService) {

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
                        '<div data-field-editor="\'path\'", data-model-name="modelName", data-model="model"></div>',
                            '<div data-ng-if="modelsLoaded">',
                            '<div data-ng-repeat="type in pathTypes" data-ng-show="getPathType() == type" data-advanced-editor-pane="" data-view-name="type + \'Path\'" data-field-def="basic" data-want-buttons="false">',
                            '</div>',
                        '</div>',
                        '<button class="btn btn-default col-sm-2 col-sm-offset-5" data-ng-click="addPath()">+</button>',
                        '<button class="btn btn-default col-sm-2 col-sm-offset-5" data-ng-click="clearPaths()">Clear</button>',
                    '</div>',
                '</div>',
            '</div>',

        ].join(''),
        controller: function($scope, $element) {
            $scope.modelsLoaded = false;
            $scope.pathTypes = appState.enumVals('PathType');
            $scope.ptsFile = null;
            $scope.radiaService = radiaService;

            $scope.getPathType = function() {
                return ($scope.model || {}).path;
            };
            //$scope.pathField = $scope.model.path;

            //var POINT_FIELD_TYPES = SIREPO.APP_SCHEMA.enum.FieldType.slice(1).map(function (tArr) {
            //    return tArr[0];
            //});


            $scope.addPath = function() {
                var m = $scope.getPathView();
                var p = appState.models[m];
                var t = $scope.getPathType();
                srdbg('ADD PATH', appState.models[m], 'TO', $scope.model.paths);
                if (! $scope.model.paths) {
                    $scope.model.paths = [];
                }
                appState.saveChanges(m, function () {
                    p.name = t + numPathsOfType(t);
                    p.type = t;
                    if (p.type === 'file') {
                        srdbg('ptsf', $scope.ptsFile);
                        p.fileName = $scope.ptsFile;
                    }
                    $scope.model.paths.push(p);
                    appState.saveChanges($scope.modelName, function (d) {
                        srdbg('ADDED');
                    });
                });
            };

            $scope.getPathView = function() {
                return ($scope.getPathType() || '') + 'Path';
            };

            $scope.clearPaths = function() {
                // open confirm dialog
                srdbg('CLEAR?');
                //$scope.model.paths = [];
                //appState.saveChanges($scope.modelName, function (d) {
                //    srdbg('CLEARED');
                //});
            };

            $scope.$on('fieldPaths.changed', function () {

            });

            function numPathsOfType(type) {
                //srdbg('chk', $scope.model.paths);
                if (! $scope.model.paths) {
                    return 0;
                }
                return $scope.model.paths.filter(function (p) {
                    return p.type === type;
                }).length;
            }

            appState.whenModelsLoaded($scope, function () {
                $scope.model = appState.models[$scope.modelName];

                //$scope.model.paths = [];
                srdbg('loaded paths', $scope.model);
                $scope.modelsLoaded = true;
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
                    '<button class="btn btn-default" data-ng-click="solve()">Solve</button>',
                    '<button class="btn btn-default" data-ng-click="reset()">Reset</button>',
                    '</div>',
                '</div>',
            '</div>',

        ].join(''),
        controller: function($scope, $element) {

            $scope.model = appState.models[$scope.modelName];

            $scope.solve = function() {
                srdbg('SOLVE');
                appState.models.geometry.lastBuilt = Date.now();
                appState.saveQuietly('geometry');
                $scope.viz.startSimulation();
            };

            // not sure how to do this - want Radia to keep geom defs but forget the fields...???
            $scope.reset = function() {
                srdbg('RESET');
                appState.models.geometry.lastBuilt = Date.now();
                appState.saveQuietly('geometry');
                panelState.requestData('geometry', function (d) {
                    srdbg('RESET DONE', d);
                }, true);
            };

            appState.whenModelsLoaded($scope, function () {

            });


        },
    };
});

SIREPO.app.directive('radiaViewer', function(appState, errorService, frameCache, geometry, layoutService, panelState, plotting, plotToPNG, radiaService, requestSender, utilities, vtkPlotting, vtkUtils, $interval) {

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: [
            '<div class="col-md-6">',
                '<div data-basic-editor-panel="" data-view-name="{{ modelName }}">',
                    '<div data-vtk-display="" data-model-name="{{ modelName }}" data-event-handlers="eventHandlers"></div>',
                '</div>',
            '</div>',

        ].join(''),
        controller: function($scope, $element) {

            var LINEAR_SCALE_ARRAY = 'linear';
            var LOG_SCALE_ARRAY = 'log';
            var ORIENTATION_ARRAY = 'orientation';
            var FIELD_ATTR_ARRAYS = [LINEAR_SCALE_ARRAY, LOG_SCALE_ARRAY, ORIENTATION_ARRAY];

            var PICKABLE_TYPES = [vtkUtils.GEOM_TYPE_POLYS, vtkUtils.GEOM_TYPE_VECTS];

            var SCALAR_ARRAY = 'scalars';

            var actorInfo = {};
            var cm = vtkPlotting.coordMapper();
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
            var renderer = null;
            var renderWindow = null;
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
            }

            function buildScene() {
                var name = sceneData.name;
                var id = sceneData.id;
                //appState.saveQuietly('geometry');
                var data = sceneData.data;
                srdbg('got data', data, 'for', name, id);

                vtkPlotting.removeActors(renderer);
                for (var i = 0; i < data.length; ++i) {

                    var sceneDatum = data[i];
                    var bounds = vtkUtils.objBounds(sceneDatum);

                    // trying a separation into an actor for each data type, to better facilitate selection
                    vtkUtils.GEOM_TYPES.forEach(function (t) {
                        var d = sceneDatum[t];
                        if (!d || !d.vertices || !d.vertices.length) {
                            return;
                        }
                        var isPoly = t === vtkUtils.GEOM_TYPE_POLYS;
                        var pdti = vtkUtils.objToPolyData(sceneDatum, [t]);
                        var pData = pdti.data;
                        var bundle = null;
                        var actor = null;
                        if (vtkUtils.GEOM_OBJ_TYPES.indexOf(t) >= 0) {
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
                        var gname = name + '.' + i;
                        var aname = gname + '.' + t;
                        addActor(aname, gname, bundle.actor, t, PICKABLE_TYPES.indexOf(t) >= 0);
                    });

                    /*
                    for (let j = 0; j < 3; ++j) {
                        let k = 2 * j;
                        totalBounds[k] = Math.min(totalBounds[k], bounds[k]);
                        totalBounds[k + 1] = Math.max(totalBounds[k + 1], bounds[k + 1]);
                    }
                     */
                }
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

            function getInfoForActor(actor) {
                for (var n in actorInfo) {
                    if (getActor(n) === actor) {
                        return getActorInfo(n);
                    }
                }
            }

            // used to create array of arrows (or other objects) for vector fields
            // change to use magnitudes and color locally
            // to be set by parent widget
            function getVectFormula(vectors, colorMapName) {

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
                srdbg('No vector array named ' + name, vectArrays.output);
                throw new Error('No vector array named ' + name  + ': ' + vectArrays.output);
            }

            function hasPaths() {
                return appState.models.fieldPaths.paths && appState.models.fieldPaths.paths.length;
            }

            function init() {
                srdbg('init...');
                if (! renderer) {
                    throw new Error('No renderer!');
                }
                updateViewer();
                updateLayout();
            }

            function numColors(polyData, type) {
                if (vtkUtils.GEOM_OBJ_TYPES.indexOf(type) < 0) {
                    return 0;
                }
                if (type === 'lines') {
                    return numDataColors(polyData.getLines().getData());
                }
                if (type === 'polys') {
                    return numDataColors(polyData.getPolys().getData());
                }
            }

            // lines and poly data arrays look like:
            //    [<num vertices for obj 0>, <vertex 0, 0>, ...,]
            function numDataColors(data) {
                let i = 0;
                let j = 0;
                while (i < data.length) {
                    i += (data[i] + 1);
                    ++j;
                }
                return j;
            }

            function setColorMap() {
                getActorsOfType(vtkUtils.GEOM_TYPE_VECTS).forEach(function (actor) {
                    var mapName = appState.models.fieldDisplay.colorMap;
                    actor.getMapper().getInputConnection(0).filter
                        .setFormula(getVectFormula(sceneData.data[0].vectors, mapName));  // which data? all? at what index?
                });
                renderWindow.render();
            }

            function setScaling() {
                getActorsOfType(vtkUtils.GEOM_TYPE_VECTS).forEach(function (actor) {
                    var mapper = actor.getMapper();
                    mapper.setScaleFactor(8.0);
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
                    //vtkAPI.setCam();
                    initDone = true;
                }
            }

            function updateLayout() {
                //srdbg('updateLayout', appState.models.magnetDisplay.viewType);
                panelState.showField(
                    'magnetDisplay',
                    'fieldType',
                    appState.models.magnetDisplay.viewType === 'fields'
                );
                radiaService.pointFieldTypes.forEach(function (ft) {
                    panelState.showEnum('magnetDisplay', 'fieldType', ft, hasPaths());
                });
                fieldDisplayFields.forEach(function (f) {
                    var mf = appState.parseModelField(f);
                    panelState.showField(mf[0], mf[1], appState.models.magnetDisplay.viewType === 'fields');
                });
                setColorMap();
                setScaling();
            }

            function updateViewer(rebuild) {
                //srdbg('updateViewer');
                sceneData = {};
                actorInfo = {};
                enableWatchFields(! rebuild);
                if (rebuild) {
                    panelState.clear('geometry');
                    panelState.requestData('geometry', setupSceneData, true);
                    return;
                }
                requestSender.getApplicationData(
                    {
                        method: 'get_geom',
                        simulationId: appState.models.simulation.simulationId,
                    },
                    function(d) {
                        if (d) {
                            setupSceneData(d);
                            return;
                        }
                        panelState.clear('geometry');
                        panelState.requestData('geometry', setupSceneData, true);
                    });
                //panelState.clear('geometry');
                //panelState.requestData('geometry', function (d) {
                //    //srdbg('got geom data', d);
                //    sceneData = d;
                //    buildScene();
                //    if (! initDone) {
                //        initDone = true;
                //    }
                //}, true);
            }


            $scope.eventHandlers = {
                handleDblClick: function(e) {
                    vtkAPI.setCam();
                }
            };

            appState.whenModelsLoaded($scope, function () {
                $scope.model = appState.models[$scope.modelName];
                appState.watchModelFields($scope, watchFields, updateLayout);
                panelState.enableField('geometry', 'name', ! appState.models.simulation.isExample);
                appState.models.fieldPaths.paths.forEach(function (p) {
                    //srdbg('pts for', p, radiaService.pointsForPath(p));
                });
            });

            // or keep stuff on vtk viewer scope?
            // start using custom javascript events to break away from angular?
            $scope.$on('vtk-init', function (e, d) {
                //srdbg('VTK INIT', e, d);
                renderer = d.objects.renderer;
                renderWindow = d.objects.window;
                vtkAPI = d.api;
                init();
            });

            $scope.$on('fieldPaths.changed', function () {
                srdbg('MODIFY POINTS');
                if (! $scope.model.fieldPoints) {
                    $scope.model.fieldPoints = [];
                }
                if (! appState.models.fieldPaths.paths || ! appState.models.fieldPaths.paths.length) {
                    return;
                }
                appState.models.fieldPaths.paths.forEach(function (p) {
                    //srdbg('pts for', p, radiaService.pointsForPath(p));
                });
            });

            $scope.$on('fieldDisplay.changed', function () {
                updateViewer(false);
            });

            $scope.$on('magnetDisplay.changed', function (e, d) {
                srdbg('MDC', e, d);
                // does not seem the best way...
                var interval = null;
                interval = $interval(function() {
                    if (interval) {
                        $interval.cancel(interval);
                        interval = null;
                    }
                    updateViewer(true);
                }, 500, 1);
            });

            $scope.$on('framesLoaded', function (e, d) {
                //srdbg('F', e, d);
                if (! initDone) {
                    //srdbg('init in progress, ignore');
                    return;
                }
                updateViewer();
            });

            $scope.$on('solveStarted', function (e, d) {
                //srdbg('S', e, d);
            });

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

SIREPO.app.factory('vtkUtils', function(utilities) {

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

    self.objToPolyData = function(json, includeTypes) {

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
                //rsUtils.rsdbg('Ignoring data for type', type);
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
                colors.push(Math.floor(255 * c[i]));
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
            //for (var i = 0; i < t.vertices.length; i++) {
            //    points.push(t.vertices[i]);
            //}
            var tInd = 0;
            var tInds = utilities.indexArray(t.vertices.length / 3);
            t.lengths.forEach(function (len) {
                tArr.push(len);
                for (var j = 0; j < len; j++) {
                    tArr.push(tInds[tInd++] + tOffset);
                }
            });
            //for (var i = 0; i < t.lengths.length; i++) {
            //    var len = t.lengths[i];
            //    tArr.push(len);
            //    for (var j = 0; j < len; j++) {
            //        tArr.push(tInds[tInd++] + tOffset);
            //    }
            //}
            if (tArr.length) {
                tData[type] = new window.Uint32Array(tArr);
            }

        });

        points = new window.Float32Array(points);

        var pd = vtk.Common.DataModel.vtkPolyData.newInstance();
        pd.getPoints().setData(points, 3);

        //rsUtils.rsdbg('setting polydata from', tData);
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