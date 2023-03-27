'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.INITIAL_INTENSITY_REPORT_TITLE = 'Initial Intensity';
    SIREPO.SINGLE_FRAME_ANIMATION = [
        'plotAnimation',
        'plot2Animation',
        'crystal3dAnimation',
    ];
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="FloatArray" class="col-sm-7">
            <div data-num-array="" data-model="model" data-field-name="field" data-field="model[field]" data-info="info" data-num-type="Float"></div>
        </div>
        <div data-ng-switch-when="IntArray" class="col-sm-7">
            <div data-num-array="" data-model="model" data-field-name="field" data-field="model[field]" data-info="info" data-num-type="Int"></div>
        </div>
        <div data-ng-switch-when="SelectCrystal" data-ng-class="fieldClass">
          <div data-select-crystal="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="SliceNumber" data-ng-class="fieldClass">
          <div data-slice-number="" data-model="model" data-field="field"></div>
        </div>
    `;
    SIREPO.appDownloadLinks = [
        '<li data-export-python-link="" data-report-title="{{ reportTitle() }}"></li>',
    ].join('');
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="crystal3d" data-crystal-3d="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-id="reportId"></div>
    `;
});

SIREPO.app.factory('silasService', function(appState) {
    const self = {};

    self.computeModel = (analysisModel) => {
        if (['crystalAnimation', 'crystal3dAnimation', 'plotAnimation', 'plot2Animation'].indexOf(analysisModel) >= 0) {
            return 'crystalAnimation';
        }
        return 'animation';
    };

    self.getCrystal = () => {
        const cc = appState.models.crystalCylinder;
        let c = self.getCrystals()[cc.crystal];
        if (c === undefined) {
            cc.crystal = "0";
            c = self.getCrystals()[0];
        }
        return c;
    };

    self.getCrystals = () => appState.models.beamline.filter(e => e.type === 'crystal');

    self.hasCrystal = () => (appState.models.beamline || []).some(e => e.type === 'crystal');

    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('SourceController', function (appState, silasService, $scope) {
});

SIREPO.app.controller('BeamlineController', function (appState, beamlineService, frameCache, persistentSimulation, silasService, $scope) {
    var self = this;
    self.appState = appState;
    self.beamlineModels = ['beamline'];
    self.beamlineService = beamlineService;
    self.prepareToSave = () => {};
    self.toolbarItemNames = [
        ['Optics', ['crystal', 'lens']],
        'watch',
    ];
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

SIREPO.app.directive('appHeader', function(appState, silasService) {
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('source')}"><a href data-ng-click="nav.openSection('source')"><span class="glyphicon glyphicon-flash"></span> Laser Pulse</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('beamline')}"><a href data-ng-click="nav.openSection('beamline')"><span class="glyphicon glyphicon-option-horizontal"></span> Beamline</a></li>
                  <li data-ng-show="hasCrystal()" class="sim-section" data-ng-class="{active: nav.isActive('crystal')}"><a href data-ng-click="nav.openSection('crystal')"><span class="glyphicon glyphicon-th"></span> Crystal</a></li>
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
        controller:  function($scope) {
            $scope.hasCrystal = () => silasService.hasCrystal();
        },
    };
});

SIREPO.app.directive('selectCrystal', function(appState, silasService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <select class="form-control" data-ng-model="model[field]"
              data-ng-options="idx as name(item) for (idx, item) in crystals"></select>
        `,
        controller: function($scope) {
            $scope.crystals = appState.clone(silasService.getCrystals());
            $scope.name = item => `${item.title} (${item.position}m)`;
        },
    };
});

SIREPO.viewLogic('laserPulseView', function(appState, panelState, requestSender, silasService, $scope) {
    const _FILES = ['ccd', 'meta', 'wfs'];

    $scope.watchFields = [
        [
            'laserPulse.distribution',
        ], updateEditor,
    ];

    function hasFiles() {
        return _FILES.every(f => (! ! $scope.model[f]) && $scope.model[f] !== "");
    }

    function updateMesh() {
        requestSender.sendStatefulCompute(
            appState,
            data => {
                $scope.model.nx_slice = data.numSliceMeshPoints[0];
                $scope.model.ny_slice = data.numSliceMeshPoints[1];
            },
            {
                method: 'mesh_dimensions',
                args: {
                    ccd: $scope.model.ccd,
                    meta: $scope.model.meta,
                    wfs: $scope.model.wfs,
                }
            },
            err => {
                throw new Error(err);
            }
        );
    }

    function updateEditor() {
        const useFiles = appState.models[$scope.modelName].distribution === 'file';
        panelState.showFields($scope.modelName, [
            _FILES, useFiles,
            ['pad_factor'], useFiles,
            ['poltype'], ! useFiles,
        ]);
        panelState.enableFields($scope.modelName, [
            ['nx_slice', 'ny_slice'], ! useFiles,
        ]);
        panelState.showRow($scope.modelName, 'sigx_waist', ! useFiles);
        if (useFiles) {
            if (hasFiles()) {
                updateMesh();
            }
        }
    }

    $scope.whenSelected = () => {
        $scope.model = appState.models[$scope.modelName];
        updateEditor();
    };

    $scope.$on('cancelChanges', (e, model) => {
        if (model === $scope.modelName) {
            updateEditor();
        }
    });
});

SIREPO.viewLogic('crystalCylinderView', function(appState, panelState, silasService, $scope) {

    const parent = $scope.$parent;
    parent.silasService = silasService;

    function updateCylinder(saveChanges)  {
        const cc = appState.models.crystalCylinder;
        const c = silasService.getCrystal();
        cc.crystalWidth = c.width;
        cc.diameter = c.diameter;
        cc.diffusionConstant = c.diffusionConstant;
        panelState.enableFields('crystalCylinder', [
            ['crystalWidth', 'diameter', 'diffusionConstant'], false,
        ]);
        if (saveChanges) {
            appState.saveChanges('crystalCylinder');
        }
    }

    $scope.whenSelected = () => updateCylinder(true);
    $scope.watchFields = [
        [
            'crystalCylinder.crystal',
        ], () => updateCylinder(false),
    ];
});

SIREPO.app.directive('crystal3d', function(appState, plotting, silasService, plotToPNG, utilities) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            reportId: '<',
        },
        template: `
            <div data-ng-class="{\'sr-plot-loading\': isLoading(), \'sr-plot-cleared\': dataCleared}">
              <div class="sr-screenshot">
                <table><tr><td width="100%">
                  <div class="sr-plot vtk-canvas-holder"></div>
                </td><td>
                  <div style="margin-left: 1em"><svg width="80" ng-attr-height="{{canvasHeight}}">
                    <g class="colorbar"></g>
                  </svg></div>
                </td></tr></table>
              </div>
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
                plotToPNG.initVTK($element, fsRenderer);
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

SIREPO.app.directive('sliceNumber', function(appState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <select class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in sliceNumbers()"></select>
        `,
        controller: function($scope) {
            let numbers = [];
            $scope.sliceNumbers = () => {
                const count = appState.applicationState().laserPulse.nslice;
                if (numbers.length != count) {
                    numbers = [];
                    for (let i = 0; i < count; i++) {
                        numbers.push([i, i + 1]);
                    }
                }
                return numbers;
            };
        },
    };
});
