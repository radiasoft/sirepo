'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.SINGLE_FRAME_ANIMATION = [
        'wavefrontSummaryAnimation',
        'laserPulse1Animation',
        'laserPulse2Animation',
        'laserPulse3Animation',
        'laserPulse4Animation',
        'plotAnimation',
        'plot2Animation',
        'crystal3dAnimation',
    ];
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="SelectElement" data-ng-class="fieldClass">',
          '<div data-select-element="" data-model="model" data-field="field"></div>',
        '</div>',
    ].join('');
    SIREPO.appDownloadLinks = [
        '<li data-export-python-link="" data-report-title="{{ reportTitle() }}"></li>',
    ].join('');
    SIREPO.appReportTypes = [
        '<div data-ng-switch-when="crystal3d" data-crystal-3d="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-id="reportId"></div>',
    ].join('');
});

SIREPO.app.factory('silasService', function(appState) {
    var self = {};
    self.computeModel = (analysisModel) => {
        if (['crystalAnimation', 'crystal3dAnimation', 'plotAnimation', 'plot2Animation'].indexOf(analysisModel) >= 0) {
            return 'crystalAnimation';
        }
        return 'animation';
    };
    self.getCrystal = () => {
        return appState.models.beamline[1];
    };
    self.getFirstMirror = () => {
        return appState.models.beamline[0];
    };
    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('BeamlineController', function (appState, beamlineService, frameCache, persistentSimulation, silasService, $scope) {
    var self = this;
    self.simScope = $scope;
    self.appState = appState;
    self.beamlineModels = ['beamline'];
    self.prepareToSave = () => {};
    self.toolbarItemNames = ['crystal', 'mirror'];

    function updateCavityDistance() {
        var pos = 0;
        appState.models.beamline.forEach((item) => {
            item.position = pos;
            pos += appState.models.simulationSettings.cavity_length / 2;
        });
        appState.saveChanges('beamline');
    }

    function updateWavefrontModels() {
        var names = [];
        self.wavefronts = [];
        appState.models.beamline.forEach((item) => names.push(wavefront(item)));
        appState.saveChanges(names);
    }

    function wavefront(item) {
        var modelKey = wavefrontAnimationName(item);
        if (! appState.models[modelKey]) {
            appState.models[modelKey] = {};
        }
        appState.models[modelKey].id = item.id;
        self.wavefronts.push({
            title: item.title,
            modelKey: modelKey,
            getData: () => appState.models[modelKey],
        });
        return modelKey;
    }

    function wavefrontAnimationName(item) {
        return 'wavefrontAnimation' + item.id;
    }

    self.hasFrames = frameCache.hasFrames;

    self.hasLaserProfile = function(isInitial) {
        if (! self.hasFrames()) {
            return false;
        }
        if (isInitial) {
            return true;
        }
        return self.simState.getPercentComplete() == 100;
    };

    self.simHandleStatus = (data) => {
        if (! appState.isLoaded()) {
            return;
        }
        if ((data.frameCount || 0) > 1) {
            appState.models.beamline.forEach((item, idx) => {
                frameCache.setFrameCount(
                    data.wavefrontsFrameCount[idx],
                    wavefrontAnimationName(item));
            });
            frameCache.setFrameCount(data.frameCount);
        }
    };

    self.simState = persistentSimulation.initSimulationState(self);
    beamlineService.setEditable(false);
    appState.whenModelsLoaded($scope, () => {
        var oldWidth = silasService.getCrystal().width;
        updateWavefrontModels();
        $scope.$on('modelChanged', (e, name) => {
            if (! appState.isReportModelName(name)) {
                updateWavefrontModels();
            }
            if (name == 'simulationSettings') {
                updateCavityDistance();
            }
            else if (name == 'beamline') {
                var width = silasService.getCrystal().width;
                if (oldWidth != width) {
                    oldWidth = width;
                    appState.models.crystalCylinder.crystalWidth = width;
                    appState.saveQuietly('crystalCylinder');
                    frameCache.setFrameCount(0);
                }
            }
        });
        $scope.$on('wavefrontSummaryAnimation.summaryData', function (e, data) {
            if (data.crystalWidth && data.crystalWidth != silasService.getCrystal().width) {
                frameCache.setFrameCount(0);
            }
        });
    });
});

SIREPO.app.controller('CrystalController', function (appState, frameCache, persistentSimulation, silasService, $scope) {
    var self = this;
    self.appState = appState;
    self.simScope = $scope;
    self.simAnalysisModel = 'crystalAnimation';

    self.hasCrystal3d = function() {
        return frameCache.hasFrames() && self.simState.getPercentComplete() == 100;
    };

    self.simHandleStatus = (data) => {
        if (! appState.isLoaded()) {
            return;
        }
        frameCache.setFrameCount(data.frameCount);
    };

    self.simState = persistentSimulation.initSimulationState(self);

    appState.whenModelsLoaded($scope, () => {
        $scope.$on('plotAnimation.summaryData', function (e, data) {
            if (data.crystalWidth && data.crystalWidth != silasService.getCrystal().width) {
                frameCache.setFrameCount(0);
            }
        });
    });
});

SIREPO.app.directive('appFooter', function(appState, silasService) {
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

SIREPO.app.directive('appHeader', function(appState) {
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'laser-cavity\')}"><a href data-ng-click="nav.openSection(\'laser-cavity\')"><span class="glyphicon glyphicon-option-horizontal"></span> Laser Cavity</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'crystal\')}"><a href data-ng-click="nav.openSection(\'crystal\')"><span class="glyphicon glyphicon-th"></span> Crystal</a></li>
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
    };
});

SIREPO.app.directive('selectElement', function(appState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <select class="form-control" data-ng-model="model[field]" data-ng-options="item.id as item.name for item in elementList()"></select>
        `,
        controller: function($scope) {
            var list;

            $scope.elementList = () => {
                if (! appState.isLoaded() || ! $scope.model) {
                    return null;
                }
                if (! list) {
                    list = [{
                        id: 'all',
                        name: 'All Elements',
                    }];
                    appState.models.beamline.forEach((item) => {
                        list.push({
                            id: item.id,
                            name: item.title,
                        });
                    });
                }
                return list;
            };

            $scope.$on('beamline.changed', () => {
                list = null;
            });
        },
    };
});

SIREPO.beamlineItemLogic('crystalView', function(appState, panelState, $scope) {
    $scope.whenSelected = () => panelState.enableField('crystal', 'position', false);
});

SIREPO.beamlineItemLogic('mirrorView', function(appState, panelState, $scope) {
    $scope.whenSelected = () => panelState.enableField('mirror', 'position', false);
});

SIREPO.viewLogic('simulationSettingsView', function(appState, panelState, requestSender, silasService, $scope) {

    function computeRMSSize(field, saveChanges) {
        var beamline = appState.applicationState().beamline;
        requestSender.sendStatelessCompute(
            appState,
            (data) => {
                if (data.rmsSize) {
                    appState.models.gaussianBeam.rmsSize = appState.formatFloat(data.rmsSize * 1e6, 4);
                    if (saveChanges) {
                        appState.saveQuietly('gaussianBeam');
                    }
                }
            },
            {
                method: 'compute_rms_size',
                gaussianBeam: appState.models.gaussianBeam,
                simulationSettings: appState.models.simulationSettings,
                mirror: silasService.getFirstMirror(),
                crystal: silasService.getCrystal(),
            }
        );
    }

    $scope.whenSelected = () => panelState.enableField('gaussianBeam', 'rmsSize', false);
    $scope.watchFields = [
        [
            'simulationSettings.cavity_length',
            'gaussianBeam.photonEnergy',
        ], computeRMSSize,
    ];

    $scope.$on('modelChanged', (e, name) => {
        if (name == 'beamline') {
            computeRMSSize(name, true);
        }
    });
});

SIREPO.viewLogic('crystalCylinderView', function(appState, panelState, silasService, $scope) {
    $scope.whenSelected = () => {
        appState.models.crystalCylinder.crystalWidth = silasService.getCrystal().width;
        panelState.enableFields('crystalCylinder', [
            'crystalWidth', false,
        ]);
    };
});

SIREPO.app.directive('crystal3d', function(appState, plotting, silasService, utilities) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            reportId: '<',
        },
        template: `
            <div data-ng-class="{\'sr-plot-loading\': isLoading(), \'sr-plot-cleared\': dataCleared}">
              <table><tr><td width="100%">
                <div class="sr-plot vtk-canvas-holder"></div>
              </td><td>
                <div style="margin-left: 1em"><svg width="80" ng-attr-height="{{canvasHeight}}">
                  <g class="colorbar"></g>
                </svg></div>
              </td></tr></table>
              <div style="margin-top: 1ex" class="row">
                <div class="col-sm-4">
                  <input data-ng-model="showEdges" data-ng-change="resize()" type="checkbox" id="showEdges" checked="checked" /> <label for="showEdges">Show Edges</label>
                </div>
                <div class="col-sm-7">
            <div class="row form-horizontal">
            <div class="col-sm-6 control-label"><label>Cutoff Axis</label></div>
            <div class="col-sm-6"><select class="form-control" data-ng-model="boundAxis" data-ng-change="resize()" data-ng-options="axis for axis in axes"></select></div>
            <div class="col-sm-12">
                  <div>Thickness cutoff</div>
                  <input data-ng-model="sliderValue" data-ng-change="resize()" class="s_range_slider" type="range" min="0" max="100" />
                  <span class="s_slider_label light left">{{ bound | number : 2 }} cm</span>
                </div>
              </div>
            </div>
            </div>
            </div>
        `,
        controller: function($scope, $element) {
            let colorbar, data, fsRenderer, orientationMarker;
            let mapName = 'Viridis (matplotlib)';
            $scope.bound = 0;
            $scope.showEdges = true;
            $scope.canvasHeight = 100;
            $scope.sliderValue = 100;
            $scope.axes = ['X', 'Y', 'Z'];
            $scope.boundAxis = 'Z';

            function checkBounds(vertexIdx, axisIdx) {
                let verts = data.vertices;
                let indices = data.indices;
                for (let i = 0; i < 3; i++) {
                    var v = verts[indices[vertexIdx + i] * 3 + axisIdx];
                    if (v > $scope.bound) {
                        return false;
                    }
                }
                return true;
            }

            // use function in vtk ScalarsToColors if it become public
            function floatColorToUChar(c) {
                return Math.floor(c * 255.0 + 0.5);
            }

            function getIntensityColors(polyData) {
                let cf = vtk.Rendering.Core.vtkColorTransferFunction.newInstance();
                cf.applyColorMap(
                    vtk.Rendering.Core.vtkColorTransferFunction.vtkColorMaps.getPresetByName(mapName));
                cf.setMappingRange(...data.intensity_range);
                let rgb = [];
                let colors = [];
                for (let i = 0; i < polyData.PointColor.length; i++) {
                    cf.getColor(polyData.PointColor[i], rgb);
                    colors.push(
                        floatColorToUChar(rgb[0]),
                        floatColorToUChar(rgb[1]),
                        floatColorToUChar(rgb[2]));
                }
                return colors;
            }

            function getPolys(polyData) {
                let polys = [];
                let polyIdx = 0;
                for (let i = 0; i < polyData.PolyLen.length; i++) {
                    let len = polyData.PolyLen[i];
                    polys.push(len);
                    for (let j = 0; j < len; j++) {
                        polys.push(polyData.PolyInd[polyIdx]);
                        polyIdx++;
                    }
                }
                return polys;
            }

            function getPolyData() {
                let len = [];
                let indices = [];
                let verts = data.vertices;
                let size = $scope.boundAxis == 'Z'
                    ? silasService.getCrystal().width
                    : appState.applicationState().crystalCylinder.diameter;
                let axisIdx = $scope.axes.indexOf($scope.boundAxis);
                $scope.bound = (size + 0.01) * ($scope.sliderValue - 50) / 100;
                for (let i = 0; i < data.indices.length; i += 3) {
                    if (checkBounds(i, axisIdx)) {
                        indices.push(data.indices[i], data.indices[i + 1], data.indices[i + 2]);
                        len.push(3);
                    }
                }
                return {
                    PolyVert: verts,
                    PolyInd: indices,
                    PolyLen: len,
                    PointColor: data.intensity,
                };
            }

            function getVtkElement() {
                return $($element).find('.vtk-canvas-holder');
            }

            function polyActor(polyData) {
                let mapper = vtk.Rendering.Core.vtkMapper.newInstance();
                let actor = vtk.Rendering.Core.vtkActor.newInstance();
                mapper.setInputData(polyData);
                actor.setMapper(mapper);
                actor.getProperty().setLighting(false);
                if ($scope.showEdges) {
                    actor.getProperty().setEdgeVisibility(true);
                    actor.getProperty().setEdgeColor(0.5, 0.5, 0.5);
                }
                return actor;
            }

            function refresh(resetCamera) {
                removeActors();
                let polyData = getPolyData();
                let pd = vtk.Common.DataModel.vtkPolyData.newInstance();
                pd.getPoints().setData(new window.Float32Array(polyData.PolyVert), 3);
                pd.getPolys().setData(new window.Uint32Array(getPolys(polyData)));
                pd.getPointData().setScalars(vtk.Common.Core.vtkDataArray.newInstance({
                    numberOfComponents: 3,
                    values: getIntensityColors(polyData),
                    dataType: vtk.Common.Core.vtkDataArray.VtkDataTypes.UNSIGNED_CHAR,
                }));
                fsRenderer.getRenderer().addActor(polyActor(pd));
                let renderer = fsRenderer.getRenderer();
                if (resetCamera) {
                    let camera = renderer.get().activeCamera;
                    camera.setPosition(0, 1, 0.5);
                    camera.setFocalPoint(0, 0, 0);
                    camera.setViewUp(0, -1, 0);
                    renderer.resetCamera();
                    camera.zoom(1.3);
                    orientationMarker.updateMarkerOrientation();
                }
                fsRenderer.getRenderWindow().render();
                $scope.canvasHeight = $($element[0]).find('.vtk-canvas-holder').height();
                colorbar.barlength($scope.canvasHeight - 20)
                        .origin([10, 10])
                        .margin({top: 10, right: 35, bottom: 20, left: 10});
                d3.select($element[0]).select('.colorbar').call(colorbar);
            }

            function removeActors() {
                let renderer = fsRenderer.getRenderer();
                renderer.getActors().forEach((actor) => renderer.removeActor(actor));
            }

            $scope.destroy = function() {
                getVtkElement().off();
                fsRenderer.getInteractor().unbindEvents();
                fsRenderer.delete();
                document.removeEventListener(utilities.fullscreenListenerEvent(), refresh);
            };

            $scope.init = function() {
                document.addEventListener(utilities.fullscreenListenerEvent(), refresh);
                let rw = getVtkElement();
                rw.on('dblclick', () => refresh(true));
                fsRenderer = vtk.Rendering.Misc.vtkFullScreenRenderWindow.newInstance({
                    background: [1, 0.97647, 0.929412],
                    container: rw[0],
                });
                orientationMarker = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
                    actor: vtk.Rendering.Core.vtkAxesActor.newInstance(),
                    interactor: fsRenderer.getInteractor()
                });
                orientationMarker.setEnabled(true);
                orientationMarker.setViewportCorner(
                    vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.TOP_RIGHT
                );
            };

            $scope.load = function(json) {
                data = json;
                //TODO(pjm): use vtk colormap, not sirepo colormap
                var colorMap = plotting.COLOR_MAP.viridis;
                var colorScale = d3.scale.linear()
                    .domain(plotting.linearlySpacedArray(...data.intensity_range, colorMap.length))
                    .range(colorMap);
                colorbar = Colorbar()
                    .scale(colorScale)
                    .orient("vertical");
                refresh(true);
            };

            $scope.resize = refresh;

            $scope.$on('$destroy', function() {
                if (orientationMarker) {
                    orientationMarker.setEnabled(false);
                }
            });
        },
        link: function link(scope, element) {
            plotting.vtkPlot(scope, element);
        },
    };
});
