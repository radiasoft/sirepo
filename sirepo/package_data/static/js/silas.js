'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.INITIAL_INTENSITY_REPORT_TITLE = 'Initial Laser Pulse';
    SIREPO.SINGLE_FRAME_ANIMATION = [];
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="FloatArray" class="col-sm-7">
            <div data-num-array="" data-model="model" data-field-name="field" data-field="model[field]" data-info="info" data-num-type="Float"></div>
        </div>
        <div data-ng-switch-when="EquationText">
            <div data-equation-text="model[field]"></div>
        </div>
        <div data-ng-switch-when="IntArray" class="col-sm-7">
            <div data-num-array="" data-model="model" data-field-name="field" data-field="model[field]" data-info="info" data-num-type="Int"></div>
        </div>
        <div data-ng-switch-when="SelectCrystal" class="col-sm-7">
          <div data-select-crystal="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="SelectThermalTransportCrystal" class="col-sm-7">
          <div data-select-crystal="" data-model="model" data-field="field" data-update-crystal="true"></div>
        </div>
        <div data-ng-switch-when="N0n2Plot">
          <div data-n0n2-plot="" data-model="model" data-image-class="images-sample"></div>
        </div>
        <div data-ng-switch-when="Float6">
          <div data-float-6="" data-model-name="modelName" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="PumpRepRate">
          <div data-pump-rep-rate="" data-model-name="modelName" data-model="model" data-field="field"></div>
        </div>
    `;
    SIREPO.appDownloadLinks = [
        `<li data-export-python-link="" data-report-title="{{ reportTitle().replace('/', ' ') }}"></li>`,
    ].join('');
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="crystal3d" data-crystal-3d="" class="sr-plot" data-model-name="{{ modelKey }}"></div>
    `;
    SIREPO.BEAMLINE_WATCHPOINT_MODEL_PREFIX = 'beamlineAnimation';
    SIREPO.BEAMLINE_WATCHPOINT_REPORT_ELEMENTS = ['watch', 'crystal'];
});

SIREPO.app.factory('silasService', function(appState) {
    const self = {};

    self.computeModel = (analysisModel) => {
        if (['crystalAnimation', 'crystal3dAnimation', 'tempHeatMapAnimation', 'tempProfileAnimation'].indexOf(analysisModel) >= 0) {
            return 'crystalAnimation';
        }
        if (['laserPulseAnimation', 'laserPulse2Animation'].includes(analysisModel)) {
            return 'laserPulseAnimation';
        }
        return 'beamlineAnimation';
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
        const cc = appState.models.thermalTransportCrystal;
        for (const e of appState.applicationState().beamline) {
            if (cc.crystal_id == e.id) {
                return e;
            }
        }
        const c = self.getCrystals()[0];
        cc.crystal_id = c.id;
        return c;
    };

    self.hasCrystal = () => (appState.models.beamline || []).some(e => e.type === 'crystal');

    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('SourceController', function (appState, frameCache, persistentSimulation, silasService, $scope) {
    const self = this;
    let errorMessage;
    self.simScope = $scope;
    self.simAnalysisModel = 'laserPulseAnimation';

    self.simHandleStatus = (data) => {
        if (! appState.isLoaded()) {
            return;
        }
        errorMessage = data.error;
        if (data.outputInfo) {
            for (const m of data.outputInfo) {
                frameCache.setFrameCount(m.frameCount, m.modelKey);
            }
        }
        frameCache.setFrameCount(data.frameCount || 0);
    };

    self.laserPulsePlotType = (modelName) => {
        return appState.applicationState()[modelName].watchpointPlot.includes('longitudinal')
             ? 'parameter' : '3d';
    };

    self.simState = persistentSimulation.initSimulationState(self);
    self.simState.errorMessage = () => errorMessage;

    $scope.$on('laserPulse.changed', () => {
        self.simState.runSimulation();
    });
});

SIREPO.app.controller('BeamlineController', function (appState, beamlineService, $scope) {
    var self = this;
    self.appState = appState;
    self.beamlineModels = ['beamline'];
    self.beamlineService = beamlineService;
    self.prepareToSave = () => {};
    self.toolbarItemNames = [
        ['Optics', ['crystal', 'lens', 'mirror2', 'splitter', 'telescope']],
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
        beamlineService.createWatchModel(0);
        appState.saveQuietly('beamline');
    });
});

SIREPO.app.controller('CrystalController', function (appState, frameCache, persistentSimulation, silasService, $scope) {
    var self = this;
    let errorMessage;
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
        errorMessage = data.error;
        frameCache.setFrameCount(data.frameCount);
    };

    self.simState = persistentSimulation.initSimulationState(self);
    self.simState.errorMessage = () => errorMessage;
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('beamline')}"><a href data-ng-click="nav.openSection('beamline')"><span class="glyphicon glyphicon-option-horizontal"></span> {{ beamlineName }} </a></li>
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
            $scope.beamlineName = SIREPO.APP_SCHEMA.strings.beamlineTabName;
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
            updateCrystal: '@',
        },
        template: `
            <select class="form-control pull-left"
              style="display: inline-block; width: 60%; height: 34px; margin-right: 5px"
              data-ng-model="model[field]"
               data-ng-options="item.id as name(item) for item in crystals()"></select>
            <button data-ng-if="updateCrystal" data-ng-click="revertCrystal()" class="pull-left btn btn-default"
              style="margin-right: 5px" title="Revert to beamline crystal values"
            ><span class="glyphicon glyphicon-refresh"></button>
            <button data-ng-if="updateCrystal" data-ng-click="saveCrystal()" class="pull-left btn btn-default"
              title="Save values to beamline crystal"
            ><span class="glyphicon glyphicon-floppy-disk"></button>
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

            $scope.revertCrystal = () => {
                appState.models.crystal = appState.clone(silasService.getCrystal($scope.model[$scope.field]));
                appState.models.thermalTransportCrystal.crystal = appState.models.crystal;
            };

            $scope.saveCrystal = () => {
                const c = silasService.getCrystal($scope.model[$scope.field]);
                $.extend(c, appState.models.crystal);
                appState.saveChanges(['thermalTransportCrystal', 'crystal', 'beamline']);
            };

            $scope.name = item => `${item.title} (${item.position}m)`;
        },
    };
});

SIREPO.app.directive('n0n2Plot', function(appState, panelState, requestSender) {
    return {
        restrict: 'A',
        scope: {
            imageClass: '@',
            model: "=",
        },
        template: `
            <div class="col-sm-12">
              <div class="lead text-center">
                <span data-ng-if="errorMessage">{{ errorMessage }}</span>
                <span data ng-if="isLoading && ! errorMessage">Loading N0 N2 Plot ...</span>
                </div>
              <img class="img-responsive {{ imageClass }}" />
            </div>
          `,
        controller: function($scope) {
            $scope.isLoading = true;
            $scope.imageClass = null;
            $scope.errorMessage = null;
            const abcd = ['A', 'B', 'C', 'D'];

            const showABCD = () => {
                abcd.forEach(e => {
                    panelState.showField('crystal', e, $scope.model.propagationType === 'abcd_lct');
                    panelState.enableField('crystal', e, false);
                });
            };

            const crystalById = (id) => {
                for (let e of appState.models.beamline){
                    if (e.id == id) {
                        return e;
                    }
                }
                throw new Error(`Could Not Find Crystal with id=${id}`);
            };

            const loadImageFile = () => {
                requestSender.sendStatefulCompute(
                    appState,
                    response => {
                        if (! $scope.model) {
                            return;
                        }
                        if (response.error) {
                            $scope.errorMessage = response.error;
                            return;
                        }
                        if (response.state == 'canceled') {
                            $scope.errorMessage = 'Request canceled';
                            return;
                        }
                        if ($('.' + $scope.imageClass).length) {
                            $('.' + $scope.imageClass)[0].src = response.uri;
                        }
                        $scope.isLoading = false;
                        const c = crystalById($scope.model.id);
                        abcd.forEach(e => {
                            c[e] = response[e];
                        });
                        showABCD();
                    },
                    {
                        method: 'n0n2_plot',
                        sigx_waist: appState.applicationState().laserPulse.sigx_waist,
                        model: $scope.model,
                    }
                );
            };

            loadImageFile();
        },
    };
});

SIREPO.app.directive('pumpRepRate', function(appState, validationService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            modelName: '=',
        },
        template: `
            <div class="col-sm-3">
              <input data-string-to-number="" data-ng-model="model[field]" class="form-control" style="text-align: right" required />
              <div class="{{ validRange() }}"></div>
            </div>
        `,
        controller: function($scope) {
            const info = appState.modelInfo($scope.modelName)[$scope.field];
            const low = info[4];
            const high = info[5];
            $scope.validRange = () => {
                if (! $scope.model) {
                    return;
                }
                const v = ($scope.model[$scope.field] <= low || $scope.model[$scope.field] >= high) && $scope.model[$scope.field] >= 0;
                validationService.validateField(
                    $scope.modelName,
                    $scope.field,
                    'input',
                    v,
                    `Rate must be between 0 and ${low} or greater than ${high}`,
                );
                return 'sr-input-warning';
            };
        }
    };
});

SIREPO.beamlineItemLogic('crystalView', function(panelState, silasService, $scope) {
    function updateAll(item) {
        updateCrystalFields(item);
        updateCalculationType(item);
    }

    function updateCalculationType(item) {
        panelState.showField('crystal', 'calc_type', item.pump_rep_rate >= 100);
    }

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
        panelState.showFields(item.type, [
            ['l_scale'], item.propagationType === 'n0n2_lct' || item.propagationType === 'abcd_lct',
            ['origin'], hasCrystals,
            ['reuseCrystal'], item.origin === 'reuse',
            ['title', 'length', 'nslice', 'inversion_mesh_extent', 'crystal_alpha'], item.origin === 'new',
            ['A', 'B', 'C', 'D'], false,
        ]);
        panelState.enableField(item.type, 'pump_wavelength', false);
        panelState.showTab(item.type, 2, item.origin === 'new');
        panelState.showTab(item.type, 3, item.origin === 'new');
        panelState.showTab(item.type, 4, item.origin === 'new');
    }

    $scope.whenSelected = updateAll;
    $scope.watchFields = [
        ['propagationType', 'origin', 'reuseCrystal'], updateCrystalFields,
        ['pump_rep_rate'], updateCalculationType,
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

    function computeChirp() {
        const m = appState.models[$scope.modelName];
        requestSender.sendStatelessCompute(
            appState,
            data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                m.chirp = data.chirp;
            },
            {
                method: 'calc_chirp',
                model: {
                    tau_0: m.tau_0,
                    tau_fwhm: m.tau_fwhm,
                },
            },
        );
    }

    $scope.whenSelected = () => {
        $scope.model = appState.models[$scope.modelName];
        panelState.enableField($scope.modelName, 'chirp', false);
        computeChirp();
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
        ['laserPulse.tau_0', 'laserPulse.tau_fwhm'], computeChirp
    ];
});

SIREPO.viewLogic('thermalTransportCrystalView', function(appState, panelState, silasService, $scope) {

    function checkAll() {
        checkThermalTransportCrystal();
        updateCalculationType();
    }

    function checkThermalTransportCrystal() {
        if (! appState.applicationState().thermalTransportCrystal.crystal_id) {
            updateThermalTransportCrystal();
            appState.saveChanges(['crystal', 'thermalTransportCrystal']);
        }
    }

    function updateCalculationType() {
        const c = appState.models.crystal;
        panelState.showField('crystal', 'calc_type', c.pump_rep_rate >= 100);
    }

    function updateThermalTransportCrystal() {
        const c = appState.clone(silasService.getThermalCrystal());
        appState.models.crystal = c;
        appState.models.thermalTransportCrystal.crystal = c;
    }

    $scope.whenSelected = checkAll;
    $scope.watchFields = [
        ['thermalTransportCrystal.crystal_id'], updateThermalTransportCrystal,
        ['crystal.pump_rep_rate'], updateCalculationType,
    ];

    $scope.$on('crystal.changed', () => {
        appState.models.thermalTransportCrystal.crystal = appState.models.crystal;
        appState.saveQuietly('thermalTransportCrystal');
    });
});

SIREPO.app.directive('crystal3d', function(appState, plotting, silasService, plotToPNG, utilities) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
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
                const c = appState.applicationState().thermalTransportCrystal.crystal;
                let size = $scope.boundAxis == 'Z'
                    ? c.length
                    : c.inversion_mesh_extent * 2 * 100;
                let axisIdx = $scope.axes.indexOf($scope.boundAxis);
                $scope.bound = (size + 0.01) * $scope.sliderValue / 100 - size / 2;
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
            };

            $scope.init = function() {
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

SIREPO.app.directive('equationText', function() {
    return {
        restrict: 'A',
        scope: {
            selectedPumpProfile: '=equationText',
        },
        template: `
          <div class="col-sm-12">
            <div class="lead text-center">Initial Temperature Due to Pump Laser:</div>
            <div class="lead text-center"><span data-text-with-math="equation()" data-is-dynamic="1"></span></div>
          </div>
        `,
        controller: function($scope) {
            $scope.equation = () => {
                return SIREPO.APP_SCHEMA.strings.pumpPulseProfileEquation[$scope.selectedPumpProfile] || '';
            };
        },
    };
});

const intensityViewHandler = function(appState, beamlineService, panelState, $scope) {

    function model() {
        return $scope.modelData
             ? $scope.modelData.getData()
             : appState.models[modelKey()];
    }

    function modelKey() {
        return $scope.modelData
             ? $scope.modelData.modelKey
             : $scope.modelName;
    }

    function element() {
        return $scope.modelData
             ? beamlineService.getItemById($scope.modelData.modelKey.match(/(\d+)/)[1])
             : null;
    }

    function isCrystal(element) {
        return element && element.type == 'crystal';
    }

    function updateIntensityReport() {
        //TODO(pjm): maybe keep the id on the model
        //const e = beamlineService.getItemById($scope.modelData.modelKey.match(/(\d+)/)[1]);
        const e = element();
        const m = model();
        panelState.showFields('watchpointReport', [
            ['watchpointPlot'], ! isCrystal(e),
            ['crystalPlot'], isCrystal(e),
        ]);

        const getAndSavePlot = (model, element) => {
            let p = isCrystal(element) ? model.crystalPlot : model.watchpointPlot;
            model.reportType = p.includes('longitudinal')
                        ? 'parameter'
                        : '3d';
            appState.saveQuietly(modelKey());
        };

        getAndSavePlot(m, e);
        const idx = SIREPO.SINGLE_FRAME_ANIMATION.indexOf(modelKey());
        if (m.reportType == 'parameter'
            || (! isCrystal(e) && ['total_intensity', 'total_phase'].includes(m.watchpointPlot))
            || (isCrystal(e) && (m.crystalPlot === 'excited_states_longitudinal' || m.crystalPlot === 'total_excited_states'))
        ) {
            if (idx < 0) {
                SIREPO.SINGLE_FRAME_ANIMATION.push(modelKey());
            }
        }
        else if (idx >= 0) {
            SIREPO.SINGLE_FRAME_ANIMATION.splice(idx, 1);
        }
    }

    $scope.whenSelected = updateIntensityReport;
    $scope.$on('modelChanged', (e, name) => {
        if (name == modelKey()) {
            updateIntensityReport();
        }
    });
};

SIREPO.viewLogic('watchpointReportView', intensityViewHandler);
SIREPO.viewLogic('laserPulseAnimationView', intensityViewHandler);
SIREPO.viewLogic('laserPulse2AnimationView', intensityViewHandler);
SIREPO.viewLogic('initialIntensityReportView', intensityViewHandler);
