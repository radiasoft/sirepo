'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="geometry3d" data-geometry-3d="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-cfg="reportCfg" data-report-id="reportId"></div>
    `;
    //TODO(pjm): OptionalFloat should be standard
    SIREPO.appFieldEditors = `
        <div data-ng-switch-when="Color" data-ng-class="fieldClass">
          <input type="color" data-ng-model="model[field]" class="sr-color-button">
        </div>
        <div data-ng-switch-when="Point3D" class="col-sm-7">
          <div data-point3d="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="OptionalFloat" data-ng-class="fieldClass">
          <input data-string-to-number="" data-ng-model="model[field]"
            data-min="info[4]" data-max="info[5]" class="form-control"
            style="text-align: right" data-lpignore="true" />
        </div>
        <div data-ng-switch-when="MaterialComponents" class="col-sm-12">
          <div data-material-components=""></div>
        </div>
        <div data-ng-switch-when="ComponentName" data-ng-class="fieldClass">
          <input data-component-name="" data-ng-model="model[field]"
            class="form-control" data-lpignore="true" data-ng-required="isRequired()"
            autocomplete="chrome-off" />
        </div>
        <div data-ng-switch-when="PercentWithType" data-ng-class="fieldClass">
          <div data-compound-field="" data-field1="percent"
            data-field2="percent_type" data-field2-size="8em"
            data-model-name="modelName" data-model="model"></div>
        </div>
        <div data-ng-switch-when="EnrichmentWithType" data-ng-class="fieldClass">
          <div data-compound-field="" data-field1="enrichment"
            data-field2="enrichment_type" data-field2-size="8em"
            data-model-name="modelName" data-model="model"></div>
        </div>
        <div data-ng-switch-when="DensityWithUnits" data-ng-class="fieldClass">
          <div data-compound-field="" data-field1="density"
            data-field2="density_units" data-field2-size="10em"
            data-model-name="modelName" data-model="model"></div>
        </div>
        <div data-ng-switch-when="Spatial">
          <div data-multi-level-editor="spatial" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="Univariate">
          <div data-multi-level-editor="univariate" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="UnitSphere">
          <div data-multi-level-editor="unitSphere" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="Sources">
          <div data-sources-editor="" data-model-name="modelName"
            data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="TallyAspects" class="col-sm-12">
          <div data-tally-aspects="" data-model="model" data-field="model[field]"></div>
           <div class="sr-input-warning"></div>
        </div>
    `;
    SIREPO.FILE_UPLOAD_TYPE = {
        'geometryInput-dagmcFile': '.h5m',
    };
});

SIREPO.app.factory('cloudmcService', function(appState) {
    const self = {};
    appState.setAppService(self);
    self.computeModel = modelKey => modelKey;
    self.isGraveyard = volume => {
        return volume.name && volume.name.toLowerCase() == 'graveyard';
    };
    return self;
});

SIREPO.app.controller('GeometryController', function (appState, cloudmcService, panelState, persistentSimulation, $scope) {
    const self = this;
    let hasVolumes = false;

    function processGeometry() {
        panelState.showField('geometryInput', 'dagmcFile', false);
        self.simState.runSimulation();
    }

    self.geom3dReportCfg = {
        fitToWindow: true,
        objectsToLoad: ['volumes'],
    };
    self.isGeometrySelected = () => {
        return appState.applicationState().geometryInput.dagmcFile;
    };
    self.isGeometryProcessed = () => hasVolumes;
    self.simHandleStatus = data => {
        self.hasServerStatus = true;
        if (data.volumes) {
            hasVolumes = true;
            if (! Object.keys(appState.applicationState().volumes).length) {
                appState.models.volumes = data.volumes;
                appState.saveChanges('volumes');
            }
        }
        else if (data.state == 'missing' || data.state == 'canceled') {
            if (self.isGeometrySelected()) {
                processGeometry();
            }
        }
    };

    $scope.$on('geometryInput.changed', () => {
        if (! hasVolumes) {
            processGeometry();
        }
    });

    self.simScope = $scope;
    self.simComputeModel = 'dagmcAnimation';
    self.simState = persistentSimulation.initSimulationState(self);
});

SIREPO.app.controller('VisualizationController', function(appState, frameCache, persistentSimulation, requestSender, $scope) {
    const self = this;
    self.geom3dReportCfg = {
        fitToWindow: false,
        objectsToLoad: ['tallies'],
    };
    self.frameCache = frameCache;
    self.simScope = $scope;
    self.simComputeModel = 'openmcAnimation';
    self.simHandleStatus = function (data) {
        if (data.frameCount) {
            frameCache.setFrameCount(data.frameCount);
        }
    };
    self.simState = persistentSimulation.initSimulationState(self);
    self.simState.runningMessage = () => {
        return `Completed batch: ${self.simState.getFrameCount()}`;
    };
    self.simState.logFileURL = function() {
        return requestSender.formatUrl('downloadDataFile', {
            '<simulation_id>': appState.models.simulation.simulationId,
            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
            '<model>': self.simState.model,
            '<frame>': SIREPO.nonDataFileFrame,
            '<suffix>': 'log',
        });
    };
    return self;
});

SIREPO.app.directive('appFooter', function() {
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

SIREPO.app.directive('appHeader', function(appState, cloudmcService, panelState) {
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('geometry')}"><a href data-ng-click="nav.openSection('geometry')"><span class="glyphicon glyphicon-globe"></span> Geometry</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('visualization')}"><a href data-ng-click="nav.openSection('visualization')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>
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

SIREPO.app.directive('geometry3d', function(appState, cloudmcService, panelState, plotting, plotToPNG, requestSender, vtkPlotting, $rootScope) {
    return {
        restrict: 'A',
        scope: {
            fitToWindow: '=',
            modelName: '@',
            reportCfg: '<',
            reportId: '<',
        },
        template: `
            <div data-vtk-display="" class="vtk-display"
              data-ng-style="sizeStyle()" data-show-border="true"
              data-report-id="reportId" data-model-name="{{ modelName }}"
              data-event-handlers="eventHandlers" data-reset-side="z"
              data-enable-axes="true" data-axis-cfg="axisCfg"
              data-axis-obj="axisObj" data-enable-selection="true"></div>
        `,
        controller: function($scope, $element) {
            $scope.isClientOnly = true;
            $scope.model = appState.models[$scope.modelName];
            let axesBoxes = {};
            let picker = null;
            let vtkScene = null;
            let selectedVolume = null;

            const bundleByVolume = {};
            // volumes are measured in centimeters
            const scale = 0.01;
            const coordMapper = new SIREPO.VTK.CoordMapper(
                new SIREPO.GEOMETRY.Transform(
                    new SIREPO.GEOMETRY.SquareMatrix([[scale, 0, 0], [0, scale, 0], [0, 0, scale]])
                )
            );
            const geom3dCfg = $scope.reportCfg || {};
            const watchFields = ['geometry3DReport.bgColor', 'geometry3DReport.showEdges'];

            const _SCENE_BOX = '_scene';

            function addTally(str, name) {
                const pd = SIREPO.VTK.VTKUtils.parseLegacy(str);
                $rootScope.$broadcast('vtk.hideLoader');
                const b = coordMapper.buildActorBundle();
                b.mapper.setInputData(pd);
                setColorsFromFieldData(pd, name, SIREPO.PLOTTING.Utils.COLOR_MAP().jet);
                b.setActorProperty('lighting', false);
                vtkScene.addActor(b.actor);
                initAxes();
                buildAxes();
                vtkScene.renderer.resetCamera();
                vtkScene.render();
            }

            function addVolume(volId) {
                const reader = vtk.IO.Core.vtkHttpDataSetReader.newInstance();
                const res = reader.setUrl(volumeURL(volId), {
                    compression: 'zip',
                    fullpath: true,
                    loadData: true,
                });
                const v = getVolumeById(volId);
                const b = coordMapper.buildActorBundle(reader, {
                    color: v.color,
                    opacity: v.opacity,
                    edgeVisibility: $scope.model.showEdges === '1',
                });
                bundleByVolume[volId] = b;
                vtkScene.addActor(b.actor);
                return res;
            }

            function buildAxes(actor) {
                let boundsBox = null;
                let name = null;
                if (actor) {
                    const v = getVolumeByActor(actor);
                    name = v.name;
                    boundsBox = SIREPO.VTK.VTKUtils.buildBoundingBox(actor.getBounds());
                }
                else {
                    name = _SCENE_BOX;
                    boundsBox = vtkScene.sceneBoundingBox(0.02);
                }
                if (! axesBoxes[name]) {
                    vtkScene.addActor(boundsBox.actor);
                }
                const bounds = boundsBox.actor.getBounds();
                axesBoxes[name] = boundsBox.actor;
                $scope.axisObj = new SIREPO.VTK.ViewPortBox(boundsBox.source, vtkScene.renderer);

                SIREPO.GEOMETRY.GeometryUtils.BASIS().forEach((dim, i) => {
                    $scope.axisCfg[dim].max = bounds[2 * i + 1];
                    $scope.axisCfg[dim].min = bounds[2 * i];
                });
            }

            function buildOpacityDelegate() {
                const m = $scope.modelName;
                const f = 'opacity';
                const d = panelState.getFieldDelegate(m, f);
                d.range = () => {
                    return {
                        min: appState.fieldProperties(m, f).min,
                        max: appState.fieldProperties(m, f).max,
                        step: 0.01
                    };
                };
                d.readout = () => {
                    return appState.modelInfo(m)[f][SIREPO.INFO_INDEX_LABEL];
                };
                d.update = setGlobalProperties;
                return d;
            }

            function getVolumeById(volId) {
                for (const n in appState.models.volumes) {
                    const v = appState.models.volumes[n];
                    if (v.volId === volId) {
                        return v;
                    }
                }
                return null;
            }

            function getVolumeByActor(a) {
                for (const volId in bundleByVolume) {
                    if (bundleByVolume[volId].actor === a) {
                        return getVolumeById(volId);
                    }
                }
                return null;
            }

            function handlePick(callData) {
                if (vtkScene.renderer !== callData.pokedRenderer) {
                    return;
                }

                // regular clicks are generated when spinning the scene - we'll select/deselect with ctrl-click
                if (vtkScene.interactionMode === SIREPO.VTK.VTKUtils.interactionMode().INTERACTION_MODE_MOVE ||
                    (vtkScene.interactionMode === SIREPO.VTK.VTKUtils.interactionMode().INTERACTION_MODE_SELECT && ! callData.controlKey)
                ) {
                    return;
                }

                const pos = callData.position;
                picker.pick([pos.x, pos.y, 0.0], vtkScene.renderer);

                const actor = picker.getActors()[0];
                const v = getVolumeByActor(actor);
                if (selectedVolume) {
                    vtkScene.removeActor(axesBoxes[selectedVolume.name]);
                    delete axesBoxes[selectedVolume.name];
                }
                if (v === selectedVolume) {
                    selectedVolume = null;
                    axesBoxes[_SCENE_BOX].getProperty().setOpacity(1);
                    buildAxes();
                }
                else {
                    axesBoxes[_SCENE_BOX].getProperty().setOpacity(0);
                    selectedVolume = v;
                    buildAxes(actor);
                }
                $scope.$apply(vtkScene.fsRenderer.resize());
            }

            function initAxes() {
                $scope.axisCfg = {};
                SIREPO.GEOMETRY.GeometryUtils.BASIS().forEach((dim, i) => {
                    $scope.axisCfg[dim] = {};
                    $scope.axisCfg[dim].dimLabel = dim;
                    $scope.axisCfg[dim].label = dim + ' [m]';
                    $scope.axisCfg[dim].numPoints = 2;
                    $scope.axisCfg[dim].screenDim = dim === 'z' ? 'y' : 'x';
                    $scope.axisCfg[dim].showCentral = false;
                });
            }

            function setColorsFromFieldData(polyData, name, colorMap) {
                const dataColors = [];
                const d = Array.from(polyData.getFieldData().getArrayByName(name).getData());
                const s = SIREPO.PLOTTING.Utils.colorScale(
                    SIREPO.UTILS.largeMin(d),
                    SIREPO.UTILS.largeMax(d),
                    colorMap
                );
                d.map(x => SIREPO.VTK.VTKUtils.colorToFloat(s(x)).map(x => Math.floor(255 * x)))
                    .forEach((c, i) => {
                        // when the field value is 0, don't draw the element at all
                        dataColors.push(...c, d[i] === 0 ? 0 : 255);
                    });
                polyData.getCellData().setScalars(
                    vtk.Common.Core.vtkDataArray.newInstance({
                        numberOfComponents: 4,
                        values: dataColors,
                        dataType: vtk.Common.Core.vtkDataArray.VtkDataTypes.UNSIGNED_CHAR
                    })
                );
                polyData.buildCells();
            }

            function loadTally(name) {
                const u = requestSender.formatUrl(
                    'downloadDataFile',
                    {
                        '<simulation_id>': appState.models.simulation.simulationId,
                        '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        '<model>': 'openmcAnimation',
                        '<frame>': -1,
                        '<suffix>': 'vtk',
                    });
                requestSender.sendRequest(u, d => addTally(d.content, name));
            }

            function loadVolumes(volIds) {
                //TODO(pjm): update progress bar with each promise resolve?
                return Promise.all(volIds.map(i => addVolume(i)));
            }

            function setGlobalProperties() {
                if (! vtkScene.renderer) {
                    return;
                }
                vtkScene.setBgColor(appState.models.geometry3DReport.bgColor);
                for (const volId in bundleByVolume) {
                    const b = bundleByVolume[volId];
                    const v = getVolumeById(volId);
                    b.setActorProperty(
                        'opacity',
                        v.isVisible ? v.opacity * appState.models.geometry3DReport.opacity : 0
                    );
                    b.setActorProperty(
                        'edgeVisibility',
                        appState.models.geometry3DReport.showEdges === '1'
                    );
                }
                vtkScene.render();
            }

            function setVolumeProperty(bundle, name, value) {
                bundle.setActorProperty(name, value);
                vtkScene.render();
            }

            function volumesError(reason) {
                srlog(new Error(`Volume load failed: ${reason}`));
                $rootScope.$broadcast('vtk.hideLoader');
            }

            function volumesLoaded() {
                if (! $scope.model) {
                    // volumesLoaded may be called after the component was destroyed
                    return;
                }
                setGlobalProperties();
                $rootScope.$broadcast('vtk.hideLoader');
                initAxes();
                buildAxes();
                $scope.$apply(vtkScene.fsRenderer.resize());
            }

            function volumeURL(volId) {
                return requestSender.formatUrl(
                    'downloadDataFile',
                    {
                        '<simulation_id>': appState.models.simulation.simulationId,
                        '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        '<model>': 'dagmcAnimation',
                        '<frame>': volId,
                    });
            }

            // the vtk teardown is handled in vtkPlotting
            $scope.destroy = () => {
                $scope.model = null;
            };

            $scope.init = () => {
                $scope.fieldDelegate = buildOpacityDelegate();
            };

            $scope.resize = () => {
                //TODO(pjm): reposition camera?
            };

            $scope.sizeStyle = () => {
                if (! geom3dCfg.fitToWindow) {
                    return {};
                }
                // 53 legend size + 35 bottom panel padding
                const ph = Math.ceil(
                    $(window).height() - ($($element).offset().top + 53 + 35));
                const pw = Math.ceil($($element).width() - 1);
                return {
                    width: `${Math.min(ph, pw)}px`,
                    margin: '0 auto',
                };
            };

            $scope.$on('vtk-init', (e, d) => {
                $rootScope.$broadcast('vtk.showLoader');
                vtkScene = d;
                const ca = vtk.Rendering.Core.vtkAnnotatedCubeActor.newInstance();
                vtk.Rendering.Core.vtkAnnotatedCubeActor.Presets.applyPreset('default', ca);
                const df = ca.getDefaultStyle();
                df.fontFamily = 'Arial';
                df.faceRotation = 45;
                ca.setDefaultStyle(df);

                vtkScene.setMarker(
                    SIREPO.VTK.VTKUtils.buildOrientationMarker(
                        ca,
                        vtkScene.renderWindow.getInteractor(),
                        vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.TOP_RIGHT
                    )
                );

                const vols = [];
                for (const n in appState.models.volumes) {
                    if (! cloudmcService.isGraveyard(appState.models.volumes[n])) {
                        vols.push(appState.models.volumes[n].volId);
                    }
                }
                vtkScene.render();
                if (geom3dCfg.objectsToLoad.includes('volumes')) {
                    loadVolumes(Object.values(vols)).then(volumesLoaded, volumesError);
                }
                if (geom3dCfg.objectsToLoad.includes('tallies')) {
                    loadTally(appState.models.tally.aspect);
                }

                picker = vtk.Rendering.Core.vtkCellPicker.newInstance();
                picker.setPickFromList(false);
                vtkScene.renderWindow.getInteractor().onLeftButtonPress(handlePick);
                plotToPNG.initVTK($element, vtkScene.renderer);
            });

            $scope.$on('sr-volume-visibility-toggled', (event, volId, isVisible) => {
                setVolumeProperty(
                    bundleByVolume[volId], 'opacity', isVisible ? getVolumeById(volId).opacity : 0
                );
            });

            $scope.$on('sr-volume-property.changed', (event, volId, prop, val) => {
                setVolumeProperty(bundleByVolume[volId], prop, val);
            });

            appState.watchModelFields($scope, watchFields, setGlobalProperties);
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('compoundField', function() {
    return {
        restrict: 'A',
        scope: {
            field1: '@',
            field2: '@',
            field2Size: '@',
            modelName: '=',
            model: '=',
        },
        //TODO(pjm): couldn't find a good way to layout fields together without table
        template: `
          <div class="row">
            <table><tr><td>
              <div data-field-editor="field1" data-label-size="0"
                data-field-size="12" data-model-name="modelName" data-model="model"></div>
            </td><td>
              <div data-ng-attr-style="margin-left: -27px; width: {{ field2Size }}">
                <div data-field-editor="field2" data-label-size="0"
                  data-field-size="12" data-model-name="modelName"
                  data-model="model"></div>
              </div>
            </td></tr></table>
          </div>
        `,
    };
});

SIREPO.app.directive('volumeSelector', function(appState, cloudmcService, panelState, $rootScope) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div style="padding: 0.5ex 1ex; border-bottom: 1px solid #ddd;">
              <div style="display: inline-block; cursor: pointer"
                data-ng-click="toggleAll()">
                <span class="glyphicon"
                  data-ng-class="allVisible ? 'glyphicon-check' : 'glyphicon-unchecked'"></span>
              </div>
            </div>
            <div id="sr-volume-list" data-ng-style="heightStyle()">
              <div class="sr-hover-row" data-ng-repeat="row in rows track by $index"
                style="padding: 0.5ex 0 0.5ex 1ex; white-space: nowrap; overflow: hidden"
                data-ng-class="{'bg-warning': ! row.material.density}">
                <div style="position: relative">
                  <div
                    style="display: inline-block; cursor: pointer; white-space: nowrap; min-height: 25px;"
                    data-ng-click="toggleSelected(row)">
                    <span class="glyphicon"
                      data-ng-class="row.isVisible ? 'glyphicon-check' : 'glyphicon-unchecked'"></span>
                    <b>{{ row.name }}</b>
                  </div>
                  <div style="position: absolute; top: 0px; right: 5px">
                    <button data-ng-click="editMaterial(row)"
                      class="btn btn-info btn-xs sr-hover-button">Edit</button>
                  </div>
                  <div data-ng-show="row.isVisible">
                    <div class="col-sm-3">
                      <input
                        id="volume-{{ row.name }}-color" type="color"
                        class="sr-color-button" data-ng-model="row.color"
                        data-ng-change="broadcastVolumePropertyChanged(row, 'color')" />
                    </div>
                    <div class="col-sm-9" style="margin-top: 10px">
                      <input
                        id="volume-{{ row.name }}-opacity-range" type="range"
                        min="0" max="1.0" step="0.01" data-ng-model="row.opacity"
                        data-ng-change="broadcastVolumePropertyChanged(row, 'opacity')" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope, $window) {
            $scope.allVisible = true;
            let editRowKey = null;
            let prevOffset = 0;

            function loadRows() {
                $scope.rows = [];
                for (const n in appState.models.volumes) {
                    const row = appState.models.volumes[n];
                    row.key = n;
                    if (! row.color) {
                        row.name = n;
                        row.color = randomColor();
                        row.opacity = 0.3;
                        row.isVisible = true;
                    }
                    if (cloudmcService.isGraveyard(row)) {
                        continue;
                    }
                    $scope.rows.push(row);
                }
                $scope.rows.sort((a, b) => a.name.localeCompare(b.name));
            }

            function randomColor() {
                return SIREPO.VTK.VTKUtils.colorToHex(
                    Array(3).fill(0).map(() => Math.random()));
            }

            function unloadMaterial() {
                appState.removeModel('material');
                editRowKey = null;
            }

            $scope.broadcastVolumePropertyChanged = (row, prop) => {
                appState.saveQuietly('volumes');
                $rootScope.$broadcast(
                    'sr-volume-property.changed',
                    row.volId,
                    prop,
                    row[prop]);
            };

            $scope.editMaterial = (row) => {
                if (! row.material) {
                    row.material = appState.setModelDefaults(
                        {
                            name: row.name,
                        },
                        'material');
                }
                editRowKey = row.key;
                appState.models.material = appState.clone(row.material);
                panelState.showModalEditor('material');
            };

            $scope.heightStyle = () => {
                const el = $('#sr-volume-list:visible');
                const offset = el.length ? el.offset().top : prevOffset;
                // keep previous offset in case the element is hidden and then restored
                prevOffset = offset;
                return {
                    // bottom padding is 35px
                    //   .panel margin-bottom: 20px
                    //   .panel-body padding: 15px
                    height: `calc(100vh - ${Math.ceil(offset) + 35}px)`,
                    overflow: 'auto',
                };
            };

            $scope.toggleAll = () => {
                $scope.allVisible = ! $scope.allVisible;
                Object.values(appState.models.volumes).forEach(v => {
                    if (cloudmcService.isGraveyard(v)) {
                        return;
                    }
                    if (v.isVisible != $scope.allVisible) {
                        $scope.toggleSelected(v, true);
                    }
                });
                appState.saveChanges('volumes');
            };

            $scope.toggleSelected = (row, noSave) => {
                row.isVisible = ! row.isVisible;
                if (! noSave) {
                    appState.saveChanges('volumes');
                }
                $rootScope.$broadcast(
                    'sr-volume-visibility-toggled',
                    row.volId,
                    row.isVisible);
            };

            $scope.$on('material.changed', () => {
                if (editRowKey) {
                    const r = appState.models.volumes[editRowKey];
                    r.material = appState.models.material;
                    r.name = r.material.name;
                    appState.saveChanges('volumes', loadRows);
                    unloadMaterial();
                }
            });

            $scope.$on('cancelChanges', (event, name) => {
                if (editRowKey && name == 'material') {
                    appState.cancelChanges('volumes');
                    unloadMaterial();
                }
            });

            loadRows();
        },
    };
});

SIREPO.app.directive('materialComponents', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {},
        template: `
              <table class="table table-hover table-condensed">
                <tr data-ng-init="ci = $index"
                    data-ng-repeat="c in appState.models.material.components track by $index">
                  <td data-ng-repeat="fieldInfo in componentInfo(ci) track by fieldTrack(ci, $index)">
                    <div data-ng-if="fieldInfo.field">
                      <div data-label-with-tooltip="" data-label="{{ fieldInfo.label }}"
                        data-tooltip="{{ fieldInfo.tooltip }}"></div>
                      <div class="row" data-field-editor="fieldInfo.field"
                        data-field-size="12" data-model-name="'materialComponent'"
                        data-model="c" data-label-size="0"></div>
                    </div>
                  </td>
                  <td>
                    <div class="sr-button-bar-parent pull-right">
                      <div class="sr-button-bar">
                        <button data-ng-click="deleteComponent($index)"
                          class="btn btn-danger btn-xs">
                          <span class="glyphicon glyphicon-remove"></span>
                        </button>
                      </div>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td style="width: 15em">
                    <b>Add Component</b>
                      <select class="form-control" data-ng-model="selectedComponent"
                        data-ng-options="item[0] as item[1] for item in componentEnum"
                        data-ng-change="addComponent()"></select>
                  </td>
                  <td></td>
                  <td></td>
                  <td></td>
                  <td></td>
                  <td></td>
                </tr>
              </table>
        `,
        controller: function($scope, $element) {
            const componentInfo = [];
            $scope.appState = appState;
            $scope.selectedComponent = '';
            $scope.componentEnum = SIREPO.APP_SCHEMA.enum.MaterialComponent;
            const fieldsByComponent = {
                add_element: [
                    'percent_with_type',
                    'enrichment_with_type',
                    'enrichment_target',
                ],
                add_elements_from_formula: [
                    'percent_type',
                    'enrichment_with_type',
                    'enrichment_target',
                ],
                add_macroscopic: [],
                add_nuclide: ['percent_with_type'],
                add_s_alpha_beta: ['fraction'],
            };
            const fieldInfo = {};

            function buildFieldInfo() {
                const mi = appState.modelInfo('materialComponent');
                for (const p in fieldsByComponent) {
                    fieldsByComponent[p].unshift('component', 'name');
                    fieldInfo[p] = [];
                    for (const f of fieldsByComponent[p]) {
                        fieldInfo[p].push({
                            field: f,
                            label: mi[f][0],
                            tooltip: mi[f][3],
                        });
                    }
                    while (fieldInfo[p].length < 5) {
                        fieldInfo[p].push({
                            field: '',
                        });
                    }
                }
            }

            $scope.addComponent = () => {
                if (! $scope.selectedComponent) {
                    return;
                }
                var c = appState.models.material;
                if (! c.components) {
                    c.components = [];
                }
                var m = appState.setModelDefaults({}, 'materialComponent');
                // use the previous percent_type
                if (c.components.length) {
                    m.percent_type = c.components[c.components.length - 1].percent_type;
                }
                m.component = $scope.selectedComponent;
                c.components.push(m);
                $scope.selectedComponent = '';
                panelState.waitForUI(() => {
                    $($element).find('.model-materialComponent-name input').last().focus();
                });
            };

            $scope.componentInfo = idx => {
                const c = appState.models.material.components[idx];
                componentInfo[idx] = fieldInfo[c.component];
                return componentInfo[idx];
            };

            $scope.deleteComponent = idx => {
                appState.models.material.components.splice(idx, 1);
            };

            $scope.fieldTrack = (componentIndex, idx) => {
                var c = appState.models.material.components[componentIndex];
                return c.component + idx;
            };

            buildFieldInfo();
        },
    };
});

SIREPO.app.directive('componentName', function(appState, requestSender) {
    var requestIndex = 0;
    return {
        restrict: 'A',
        require: 'ngModel',
        link: function(scope, element, attrs, ngModel) {

            scope.isRequired = () => true;

            ngModel.$parsers.push(function(value) {
                if (ngModel.$isEmpty(value)) {
                    return null;
                }
                requestIndex++;
                const currentRequestIndex = requestIndex;
                requestSender.sendStatelessCompute(
                    appState,
                    data => {
                        // check for a stale request
                        if (requestIndex != currentRequestIndex) {
                            return;
                        }
                        ngModel.$setValidity('', data.error ? false : true);
                    },
                    {
                        method: 'validate_material_name',
                        name: value,
                        component: scope.model.component,
                    }
                );


                return value;
            });
            ngModel.$formatters.push(function(value) {
                if (ngModel.$isEmpty(value)) {
                    return value;
                }
                return value.toString();
            });
        }
    };
});

SIREPO.app.directive('multiLevelEditor', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@multiLevelEditor',
            model: '=',
            field: '=',
        },
        template: `
          <div style="position: relative; top: -5px; background: rgba(0, 0, 0, 0.05);
            border: 1px solid lightgray; border-radius: 3px; padding-top: 5px;
            margin: 0 15px">
            <div class="form-group">
              <div data-field-editor="'_type'" data-model-name="modelName"
                data-model="model[field]" data-label-size="0"></div>
            </div>
            <div data-ng-repeat="v in viewFields track by v.track">
              <div class="form-group">
                <div class="col-sm-11 col-sm-offset-1">
                  <div data-field-editor="v.field" data-model-name="model[field]._type"
                    data-label-size="5"
                    data-model="model[field]"></div>
                </div>
              </div>
            </div>
          </div>
        `,
        controller: function($scope) {

            function setView() {
                if (type() && type() !== 'None') {
                    $scope.viewFields = SIREPO.APP_SCHEMA.view[type()].advanced
                        .map(f => {
                            return {
                                field: f,
                                track: type() + f,
                            };
                        });
                }
                else {
                    $scope.viewFields = null;
                }
            }

            function type() {
                return $scope.model[$scope.field]._type;
            }

            $scope.$watch('model[field]._type', (newValue, oldValue) => {
                if (! $scope.model) {
                    return;
                }
                if (panelState.isActiveField($scope.modelName, '_type')) {
                    if (newValue !== oldValue && newValue) {
                        $scope.model[$scope.field] = {
                            _type: type(),
                        };
                        if (newValue !== 'None') {
                            appState.setModelDefaults(
                                $scope.model[$scope.field],
                                type(),
                            );
                        }
                    }
                }
                setView();
            });
        },
    };
});

SIREPO.app.directive('point3d', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <div data-ng-repeat="v in model[field] track by $index"
              style="display: inline-block; width: 7em; margin-right: 5px;" >
              <input class="form-control" data-string-to-number="Float"
                data-ng-model="model[field][$index]"
                style="text-align: right" required />
            </div>
        `,
    };
});

SIREPO.app.directive('sourcesEditor', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            model: '=',
            field: '=',
        },
        template: `
            <div style="position: relative; top: -25px">
              <div class="col-sm-12">
                <button class="btn btn-xs btn-info pull-right"
                  data-ng-click="addSource()">
                  <span class="glyphicon glyphicon-plus"></span> Add Source</button>
                <table data-ng-if="model[field].length"
                  style="width: 100%; table-layout: fixed; margin-bottom: 10px"
                  class="table table-hover">
                  <colgroup>
                    <col>
                    <col style="width: 8em">
                  </colgroup>
                  <thead>
                    <tr>
                      <th>Space</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr data-ng-repeat="m in model[field] track by $index">
                      <td>
                        <div style="text-overflow: ellipsis; overflow: hidden; white-space: nowrap">
                          {{ description(m) }}
                        </div>
                      </td>
                      <td>
                        <button class="btn btn-xs btn-info" style="width: 5em"
                          data-ng-click="editSource(m)">Edit</button>
                        <button data-ng-click="removeSource(m)"
                          class="btn btn-danger btn-xs"><span
                            class="glyphicon glyphicon-remove"></span></button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
        `,
        controller: function($scope) {
            const childModel = 'source';
            const infoFields = {
                box: ['lower_left', 'upper_right'],
                cartesianIndependent: ['x', 'y', 'z'],
                cylindricalIndependent: ['r', 'phi', 'z'],
                point: ['xyz'],
                sphericalIndependent: ['r', 'theta', 'phi'],
                maxwell: ['theta'],
                muir: ['e0', 'm_rat', 'kt'],
                normal: ['mean_value', 'std_dev'],
                powerLaw: ['a', 'b'],
                uniform: ['a', 'b'],
                watt: ['a', 'b'],
            };

            function nextIndex() {
                return $scope.model[$scope.field].length;
            }

            function editChild(model) {
                appState.models[childModel] = model;
                panelState.showModalEditor(childModel);
            }

            $scope.addSource = () => {
                editChild(appState.setModelDefaults({
                    _index: nextIndex(),
                }, childModel));
            };

            $scope.description = m => {
                return typeInfo('SpatialDistribution', m.space);
            };

            function typeInfo(modelType, model) {
                let res = appState.enumDescription(modelType, model._type);
                if (infoFields[model._type]) {
                    res += '(';
                    for (const f of infoFields[model._type]) {
                        if (! model[f]) {
                            continue;
                        }
                        res += `${f}=`;
                        if (model[f]._type) {
                            res += typeInfo('ProbabilityDistribution', model[f]);
                        }
                        else {
                            res += model[f];
                        }
                        res += ' ';
                    }
                    res = res.trim() + ')';
                }
                else if (model.probabilityValue) {
                    const MAX_VALUES = 3;
                    res += '(';
                    for (let i = 0; i < MAX_VALUES; i++) {
                        if (model.probabilityValue[i]
                            && model.probabilityValue[i].p) {
                            res += `(${model.probabilityValue[i].x},${model.probabilityValue[i].p}) `;
                        }
                    }
                    if (model.probabilityValue[MAX_VALUES]
                        && model.probabilityValue[MAX_VALUES].p) {
                        res += '...';
                    }
                    res = res.trim() + ')';
                }
                return res + ' ';
            }

            $scope.editSource = model => {
                editChild(model);
            };

            $scope.removeSource = model => {
                const c = [];
                for (const m of $scope.model[$scope.field]) {
                    if (m._index != model._index) {
                        m._index = c.length;
                        c.push(m);
                    }
                }
                $scope.model[$scope.field] = c;
            };

            $scope.$on('modelChanged', function(event, name) {
                if (name == childModel) {
                    const m = appState.models[childModel];
                    $scope.model[$scope.field][m._index] = m;
                    appState.removeModel(childModel);
                    appState.saveChanges($scope.modelName);
                }
            });
        },
    };
});

SIREPO.app.directive('tallyAspects', function() {

    const aspects = SIREPO.APP_SCHEMA.enum.TallyAspect;

    function template() {
        const numCols = 4;
        const numRows = Math.ceil(aspects.length / numCols);
        let t = '';
        for (let i = 0; i < numRows; ++i) {
            t += '<div class="row">';
            for (let j = 0; j < numCols; ++j) {
                const n = i * numRows + j;
                const label = aspects[n][1];
                const val = aspects[n][0];
                t += `
                  <div style="position: relative; top: -25px">
                    <div class="col-sm-offset-5 col-sm-6">
                        <label><input type="checkbox" data-ng-model="selectedAspects['${val}']" data-ng-change="toggleAspect('${val}')"> ${label}</label>
                    </div>
                  </div>
                `;
            }
            t += '</div>';
        }
        return t;
    }

    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: template(),
        controller: function($scope) {
            $scope.selectedAspects = {};
            for (const a of aspects) {
                $scope.selectedAspects[a[0]] = $scope.field.includes(a[0]);
            }

            $scope.toggleAspect = val => {
                if ($scope.selectedAspects[val]) {
                    $scope.field.push(val);
                }
                else {
                    $scope.field.splice($scope.field.indexOf(val), 1);
                }
            };
        },
    };
});


SIREPO.viewLogic('settingsView', function(appState, panelState, $scope) {
    function processPlanes() {
        panelState.showFields('reflectivePlanes', [
            ['plane1a', 'plane1b', 'plane2a', 'plane2b'],
            appState.models.reflectivePlanes.useReflectivePlanes == '1',
        ]);
    }
    function updateEditor() {
        for (const a of SIREPO.APP_SCHEMA.enum.TallyAspect) {
            panelState.showEnum(
                'tally',
                'aspect',
                a[0],
                appState.models.tally.aspects.includes(a[0])
            );
        }
    }
    $scope.whenSelected = () => {
        updateEditor();
        processPlanes();
    };
    $scope.watchFields = [
        ['reflectivePlanes.useReflectivePlanes'], processPlanes,
    ];
    $scope.$watchCollection('appState.models.tally.aspects', updateEditor);


    $scope.$on('tally.changed', updateEditor);
});
