'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.controller('RadiaSourceController', function (appState, panelState, $scope) {
    const self = this;

    appState.whenModelsLoaded($scope, function() {
        // initial setup
        //appState.watchModelFields($scope, ['model.field'], function() {
        //});
        //srdbg('RadiaSourceController');
    });
});

SIREPO.app.controller('RadiaVisualizationController', function (appState, panelState, $scope) {
    const self = this;

    appState.whenModelsLoaded($scope, function() {
        // initial setup
       // appState.watchModelFields($scope, ['model.field'], function() {
        //});
        //srdbg('RadiaVisualizationController', appState.models);
    });
});

SIREPO.app.directive('radiaViewer', function(appState, errorService, frameCache, geometry, layoutService, panelState, plotting, plotToPNG, requestSender, utilities, vtkPlotting, vtkUtils) {

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: [
            '<div class="col-md-6">',
                '<div data-basic-editor-panel="" data-view-name="{{modelName}}">',
                    '<button class="btn btn-default col-sm-2 col-sm-offset-5" data-ng-click="solve()">Solve</button>',
                    '<div data-vtk-display="" data-model-name="" data-event-handlers="eventHandlers"></div>',
                '</div>',
            '</div>',

        ].join(''),
        controller: function($scope, $element) {

            $scope.model = appState.models[$scope.modelName];

            var cm = vtkPlotting.coordMapper();
            var renderer = null;
            var renderWindow = null;
            var vtkAPI = {};
            var watchFields = [
                 'magnetDisplay.pathType',
                 'magnetDisplay.viewType',
                 'solver.fieldType',
            ];


            function buildScene(sceneData) {
                var name = sceneData.name;
                var id = sceneData.id;
                var data = sceneData.data;
                //rsUtils.rsdbg('got data', data, 'for', name, id);

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
                            srdbg('VECTORS LATER');
                            /*
                            let vectorCalc = vtk.Filters.General.vtkCalculator.newInstance();
                            vectorCalc.setFormula(getVectFormula(d, view.model.get('vector_color_map_name')));
                            vectorCalc.setInputData(pData);

                            mapper = vtk.Rendering.Core.vtkGlyph3DMapper.newInstance();
                            mapper.setInputConnection(vectorCalc.getOutputPort(), 0);

                            let s = vtk.Filters.Sources.vtkArrowSource.newInstance();
                            mapper.setInputConnection(s.getOutputPort(), 1);
                            mapper.setOrientationArray(ORIENTATION_ARRAY);

                            // this scales by a constant - the default is to use scalar data
                            //TODO(mvk): set based on bounds size
                            mapper.setScaleFactor(8.0);
                            mapper.setScaleModeToScaleByConstant();
                            mapper.setColorModeToDefault();
                             */
                        }
                        //actor.setMapper(mapper);
                        bundle.actor.getProperty().setEdgeVisibility(isPoly);
                        bundle.actor.getProperty().setLighting(isPoly);
                        const gname = name + '.' + i;
                        const aname = gname + '.' + t;
                        vtkPlotting.addActor(renderer, bundle.actor);
                        //view.addActor(aname, gname, actor, t, PICKABLE_TYPES.indexOf(t) >= 0);
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
            }

            function init() {
                srdbg('init...');
                appState.watchModelFields($scope, watchFields, updateViewer);
                if (! renderer) {
                    throw new Error('No renderer!');
                }
                //srdbg(appState.models.simulation);
                //renderer.getLights()[0].setLightTypeToSceneLight();
                //var b = cm.buildSphere(null, null, [1, 0, 0]);
                //b.actor.getProperty().setEdgeVisibility(true);
                //vtkPlotting.addActor(renderer, b.actor);
                updateViewer();
            }

            function updateViewer() {
                srdbg('updateViewer');
                panelState.requestData('geometry', function (d) {
                    //srdbg('got display', d);
                    buildScene(d);
                }, true);
                //panelState.requestData('geometry');
                //vtkAPI.setCam();
            }

            $scope.eventHandlers = {
                handleDblClick: function(e) {
                    vtkAPI.setCam();
                }
            };

            $scope.solve = function() {
                srdbg('SOLVE');
               // panelState.requestData('');
            };

            //appState.watchModelFields($scope, watchFields, updateViewer);

            appState.whenModelsLoaded($scope, function () {
                srdbg('radia models loaded');
                //appState.watchModelFields($scope, watchFields, updateViewer);
                //updateViewer();
            });

            // or keep stuff on vtk viewer scope?
            // start using custom javascript events to break away from angular?
            $scope.$on('vtk-init', function (e, d) {
                srdbg('VTK INIT', e, d);
                renderer = d.objects.renderer;
                renderWindow = d.objects.window;
                vtkAPI = d.api;
                init();
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