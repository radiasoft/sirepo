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
        <div data-ng-switch-when="Float6">
          <div data-float-6="" data-model-name="modelName" data-model="model" data-field="field"></div>
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

    self.getCrystal = itemId =>  appState.models.beamline.filter(e => e.id === itemId)[0];

    self.getCrystals = () => appState.models.beamline.filter(
        e => e.type === 'crystal' && e.origin === 'new',
    );

    self.getPriorCrystals = itemId => {
        const res = [];
        for (const c of appState.models.beamline.filter(e => e.type == 'crystal')) {
            if (c.id === itemId) {
                break;
            }
            if (c.origin === 'new') {
                res.push(c);
            }
        }
        return res;
    };

    self.getThermalCrystal = () => {
        const cc = appState.models.crystalCylinder;
        for (const e of appState.applicationState().beamline) {
            if (cc.crystal == e.id) {
                return e;
            }
        }
        const c = self.getCrystals()[0];
        cc.crystal = c.id;
        return c;
    };

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
        ['Optics', ['crystal', 'lens', 'mirror']],
        'watch',
    ];

    function updateCrystals() {
        let c = 0;
        const byId = {};
        for (const e of appState.models.beamline) {
            if (e.type === 'crystal') {
                if (e.origin === 'new') {
                    byId[e.id] = e;
                    c += 1;
                    const t = e.title.replace(/\s+#\d+$/, '');
                    if (t === 'Crystal') {
                        e.title = `${t} #${c}`;
                    }
                }
                else {
                    e.title = byId[e.reuseCrystal]?.title || '';
                }
            }
        }
    }

    // uniquely name all the crystals in beamline order
    $scope.$watchCollection('appState.models.beamline', updateCrystals);
    $scope.$on('beamline.changed', () => {
        updateCrystals();
        appState.saveQuietly('beamline');
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
            if (data.crystalLength && data.crystalLength != silasService.getThermalCrystal().length) {
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
                  <li data-ng-show="hasCrystal()" class="sim-section" data-ng-class="{active: nav.isActive('thermal-transport')}"><a href data-ng-click="nav.openSection('thermal-transport')"><span class="glyphicon glyphicon-th"></span> Thermal Transport</a></li>
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
              data-ng-options="item.id as name(item) for item in crystals()"></select>
        `,
        controller: function($scope) {
            let crystals;

            $scope.crystals = () => {
                const c = $scope.model && $scope.model.type === 'crystal'
                        ? silasService.getPriorCrystals($scope.model.id)
                        : silasService.getCrystals();
                if (! crystals || (crystals.length != c.length)) {
                    crystals = appState.clone(c);
                }
                return crystals;
            };

            $scope.name = item => `${item.title} (${item.position}m)`;
        },
    };
});

SIREPO.beamlineItemLogic('crystalView', function(panelState, silasService, $scope) {
    function updateCrystalFields(item) {
        const crystals = silasService.getPriorCrystals(item.id);
        const hasCrystals = crystals.length > 0;
        if (hasCrystals) {
            if (! item.reuseCrystal) {
                item.reuseCrystal = crystals[crystals.length - 1].id;
            }
        }
        else {
            item.origin = 'new';
        }
        if (item.origin === 'reuse') {
            item.title = silasService.getCrystal(item.reuseCrystal)?.title || '';
        }
        if (item.radial_n2 === '1' && item.propagationType !== 'n0n2_srw') {
            item.radial_n2 = '0';
        }
        panelState.showFields(item.type, [
            ['l_scale'], item.propagationType === 'n0n2_lct' || item.propagationType === 'abcd_lct',
            ['pump_waist'], item.propagationType === 'gain_calc'
                || item.radial_n2 === '1' || item.calc_gain == '1',
            [
                'inversion_n_cells', 'inversion_mesh_extent', 'crystal_alpha',
                'pump_wavelength', 'pump_energy', 'pump_type',
            ], item.calc_gain === '1' || item.propagationType === 'gain_calc',
            ['calc_gain'], item.propagationType !== 'gain_calc',
            ['radial_n2'], item.propagationType == 'n0n2_srw',
            ['origin'], hasCrystals,
            ['reuseCrystal'], item.origin === 'reuse',
            ['title', 'length', 'nslice'], item.origin === 'new',
            ['A', 'B', 'C', 'D'], item.propagationType == 'abcd_lct',
        ]);
        panelState.showTab(item.type, 2, item.origin === 'new');
        panelState.showTab(item.type, 3, item.origin === 'new');
    }

    $scope.whenSelected = updateCrystalFields;
    $scope.watchFields = [
        ['propagationType', 'radial_n2', 'calc_gain', 'origin', 'reuseCrystal'], updateCrystalFields,
    ];
});

SIREPO.viewLogic('laserPulseView', function(appState, panelState, requestSender, silasService, $scope) {
    const _FILES = ['ccd', 'meta', 'wfs'];

    function hasFiles() {
        return _FILES.every(f => $scope.model[f]);
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
        const m = appState.models[$scope.modelName];
        const useFiles = m.distribution === 'file';
        panelState.showFields($scope.modelName, [
            _FILES, useFiles,
            ['poltype', 'sigx_waist', 'sigy_waist'], ! useFiles,
        ]);
        if (useFiles && hasFiles()) {
            updateMesh();
        }
        updateMeshPoints();
    }

    function updateMeshPoints() {
        const m = appState.models[$scope.modelName];
        const useFiles = m.distribution === 'file';
        if (m.nx_slice && ! useFiles) {
            m.ny_slice = m.nx_slice;
        }
        panelState.enableFields($scope.modelName, [
            ['nx_slice'], ! useFiles,
            ['ny_slice'], false,
        ]);
    }

    $scope.whenSelected = () => {
        $scope.model = appState.models[$scope.modelName];
        updateEditor();
    };

    $scope.watchFields = [
        [
            'laserPulse.ccd',
            'laserPulse.meta',
            'laserPulse.wfs',
            'laserPulse.distribution',
        ], updateEditor,
        ['laserPulse.nx_slice'], updateMeshPoints,
    ];
});

SIREPO.viewLogic('crystalCylinderView', function(appState, panelState, silasService, $scope) {

    const parent = $scope.$parent;
    parent.silasService = silasService;

    function updateCylinder(saveChanges)  {
        const cc = appState.models.crystalCylinder;
        const c = silasService.getThermalCrystal();
        cc.crystalLength = c.length;
        panelState.enableFields('crystalCylinder', [
            ['crystalLength'], false,
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
                    ? silasService.getThermalCrystal().length
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

SIREPO.app.directive('float6', function(appState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            modelName: '=',
            field: '=',
        },
        template: `
            <div class="clearfix" data-ng-if="model.nslice > 3"></div>
            <div class="col-sm-2" data-ng-repeat="idx in indices() track by $index">
              <input data-string-to-number="" data-ng-model="model[field][$index]" class="form-control" style="text-align: right" data-lpignore="true" required />
            </div>
        `,
        controller: function($scope) {
            const max = 6;
            const indices = [];
            $scope.indices = () => {
                let size = max;
                if ($scope.model && $scope.model[$scope.field]) {
                    if ($scope.model.nslice && $scope.model.nslice < max) {
                        size = $scope.model.nslice;
                    }
                }
                indices.length = size;
                return indices;
            };
        },
    };
});
