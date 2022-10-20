'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="geometry3d" data-geometry-3d="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-id="reportId"></div>
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
        <div data-ng-switch-when="SourcesOrTallies">
          <div data-sources-or-tallies-editor="" data-model-name="modelName"
            data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="TallyAspects" class="col-sm-12">
          <div data-tally-aspects="" data-model="model" data-field="model[field]"></div>
           <div class="sr-input-warning"></div>
        </div>
        <div data-ng-switch-when="TallyScoreWithGrouping" class="col-sm-10">
          <div data-tally-score-group="" data-model="model" data-field="field" data-enum="enum"></div>
        </div>
        <div data-ng-switch-when="SimpleListEditor" class="col-sm-7">
          <div data-simple-list-editor="" data-model="model" data-field="field" data-sub-model="info[4]"></div>
        </div>
        <div data-ng-switch-when="Filter">
          <div data-multi-level-editor="filter" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="MaterialValue" data-ng-class="fieldClass">
          <div data-material-list="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="TallyList" data-ng-class="fieldClass">
          <div class="input-group">
            <select class="form-control" data-ng-model="model[field]" data-ng-options="t.name as t.name for t in model.tallies"></select>
          </div>
        </div>
        <div data-ng-switch-when="ScoreList" data-ng-class="fieldClass">
          <div class="input-group">
            <select class="form-control" data-ng-model="model[field]" data-ng-options="s.score as s.score for s in (model.tallies | filter:{name:model.tally})[0].scores"></select>
          </div>
        </div>
    `;
    SIREPO.FILE_UPLOAD_TYPE = {
        'geometryInput-dagmcFile': '.h5m',
    };
});

SIREPO.app.factory('cloudmcService', function(appState) {
    const self = {};
    appState.setAppService(self);

    function findScore(tallies, tally, score) {
        return findTally(tallies, tally).scores.filter(v => v.score == score).length
            ? score
            : null;
    }

    function findTally(tallies, tally) {
        return tallies.filter(v => v.name == tally)[0];
    }

    self.computeModel = modelKey => modelKey;

    self.findTally = () => {
        return findTally(appState.models.openmcAnimation.tallies, appState.models.openmcAnimation.tally);
    };

    self.isGraveyard = volume => {
        return volume.name && volume.name.toLowerCase() == 'graveyard';
    };

    self.validateSelectedTally = () => {
        const a = appState.models.openmcAnimation;
        if (! a.tally || ! findTally(a.tallies, a.tally)) {
            a.tally = a.tallies[0].name;
        }
        if (! a.score || ! findScore(a.tallies, a.tally, a.score)) {
            a.score = findTally(a.tallies, a.tally).scores[0].score;
        }
        appState.saveQuietly('openmcAnimation');
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

SIREPO.app.controller('VisualizationController', function(appState, cloudmcService, frameCache, persistentSimulation, requestSender, $scope) {
    const self = this;
    self.frameCache = frameCache;
    self.simScope = $scope;
    self.simComputeModel = 'openmcAnimation';
    let errorMessage;

    function validateSelectedTally(tallies) {
        appState.models.openmcAnimation.tallies = tallies;
        appState.saveQuietly('openmcAnimation');
        cloudmcService.validateSelectedTally();
    }

    self.simHandleStatus = function (data) {
        errorMessage = data.error;
        if (data.frameCount) {
            frameCache.setFrameCount(data.frameCount);
        }
        if (data.tallies) {
            validateSelectedTally(data.tallies);
        }
    };
    self.simState = persistentSimulation.initSimulationState(self);
    self.simState.errorMessage = () => errorMessage;
    self.simState.runningMessage = () => {
        return `Completed batch: ${self.simState.getFrameCount()}`;
    };
    self.simCompletionState = () => {
        if (self.simState.isStateError) {
            return '';
        }
        return `${frameCache.getFrameCount()} batches`;
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
    self.tallyTitle = () => {
        const a = appState.models.openmcAnimation;
        return `Tally Results - ${a.tally} - ${a.score} - ${a.aspect}`;
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

SIREPO.app.directive('geometry3d', function(appState, cloudmcService, mathRendering, panelState, plotting, plotToPNG, requestSender, vtkPlotting, $rootScope) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            reportId: '<',
        },
        template: `
            <div data-vtk-display="" class="vtk-display col-sm-11"
              data-ng-style="sizeStyle()" data-show-border="true"
              data-report-id="reportId" data-model-name="{{ modelName }}"
              data-event-handlers="eventHandlers" data-reset-side="y"
              data-enable-axes="true" data-axis-cfg="axisCfg"
              data-axis-obj="axisObj" data-enable-selection="true"></div>
            <div class="col-sm-1" style="padding-left: 0;" data-ng-if="supportsColorbar()">
                <div class="colorbar"></div>
            </div>
        `,
        controller: function($scope, $element) {
            const isGeometryOnly = $scope.modelName === 'geometry3DReport';
            $scope.isClientOnly = isGeometryOnly;
            let axesBoxes = {};
            let basePolyData = null;
            let colorbar = null;
            let colorbarPtr = null;
            let fieldData = [];
            let picker = null;
            let minField, maxField;
            let selectedVolume = null;
            let tally = null;

            const bundleByVolume = {};
            const colorbarThickness = 30;
            let tallyBundle = null;
            let vtkScene = null;
            // volumes are measured in centimeters
            const scale = 0.01;
            const coordMapper = new SIREPO.VTK.CoordMapper(
                new SIREPO.GEOMETRY.Transform(
                    new SIREPO.GEOMETRY.SquareMatrix([[scale, 0, 0], [0, scale, 0], [0, 0, scale]])
                )
            );
            const watchFields = [`${$scope.modelName}.bgColor`, `${$scope.modelName}.showEdges`];
            const clientOnlyFields = ['voxels.colorMap'].concat(watchFields);
            const voxelPoly = [
                [0, 1, 2, 3],
                [4, 5, 6, 7],
                [4, 5, 1, 0],
                [3, 2, 6, 7],
                [4, 0, 3, 7],
                [1, 5, 6, 2],
            ];
            const _SCENE_BOX = '_scene';

            function addTally(data) {
                loadTally(data);
                $rootScope.$broadcast('vtk.hideLoader');
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
                    edgeVisibility: model().showEdges === '1',
                });
                bundleByVolume[volId] = b;
                vtkScene.addActor(b.actor);
                picker.addPickList(b.actor);
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
                    // always clear the scene box
                    name = _SCENE_BOX;
                    vtkScene.removeActor(axesBoxes[name]);
                    delete axesBoxes[name];
                    boundsBox = vtkScene.sceneBoundingBox();
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

            function buildVoxel(lowerLeft, wx, wy, wz, points, polys) {
                const pi = points.length / 3;
                points.push(...lowerLeft);
                points.push(...[lowerLeft[0] + wx, lowerLeft[1], lowerLeft[2]]);
                points.push(...[lowerLeft[0] + wx, lowerLeft[1] + wy, lowerLeft[2]]);
                points.push(...[lowerLeft[0], lowerLeft[1] + wy, lowerLeft[2]]);
                points.push(...[lowerLeft[0], lowerLeft[1], lowerLeft[2] + wz]);
                points.push(...[lowerLeft[0] + wx, lowerLeft[1], lowerLeft[2] + wz]);
                points.push(...[lowerLeft[0] + wx, lowerLeft[1] + wy, lowerLeft[2] + wz]);
                points.push(...[lowerLeft[0], lowerLeft[1] + wy, lowerLeft[2] + wz]);
                for (const r of voxelPoly) {
                    polys.push(4);
                    polys.push(...r.map(v => v + pi));
                }
            }

            function buildVoxels() {
                function getMeshFilter() {
                    const t = cloudmcService.findTally();
                    for (let k = 1; k <= SIREPO.APP_SCHEMA.constants.maxFilters; k++) {
                        const f = t[`filter${k}`];
                        if (f && f._type === 'meshFilter') {
                            return f;
                        }
                    }
                    return null;
                }

                if (tallyBundle) {
                    vtkScene.removeActor(tallyBundle.actor);
                    picker.deletePickList(tallyBundle.actor);
                    tallyBundle = null;
                }
                const mesh = getMeshFilter();
                if (! mesh) {
                    return;
                }
                const [nx, ny, nz] = mesh.dimension;
                const [wx, wy, wz] = [
                    (mesh.upper_right[0] - mesh.lower_left[0]) / mesh.dimension[0],
                    (mesh.upper_right[1] - mesh.lower_left[1]) / mesh.dimension[1],
                    (mesh.upper_right[2] - mesh.lower_left[2]) / mesh.dimension[2],
                ];
                const [sx, sy, sz] = mesh.upper_right.map(
                    (x, i) => (1.0 - appState.models.voxels.voxelInsetPct)
                        * Math.abs(x - mesh.lower_left[i]) / mesh.dimension[i]
                );
                const points = [];
                const polys = [];
                fieldData = [];
                const fd = basePolyData.getFieldData().getArrayByName(model().aspect).getData();
                minField = Number.MAX_VALUE;
                maxField = Number.MIN_VALUE;
                for (let zi = 0; zi < nz; zi++) {
                    for (let yi = 0; yi < ny; yi++) {
                        for (let xi = 0; xi < nx; xi++) {
                            const f = fd[zi * nx * ny + yi * nx + xi];
                            if (! isInFieldThreshold(f)) {
                                continue;
                            }
                            if (f < minField) {
                                minField = f;
                            }
                            else if (f > maxField) {
                                maxField = f;
                            }
                            fieldData.push(f);
                            const p = [
                                xi * wx + mesh.lower_left[0],
                                yi * wy + mesh.lower_left[1],
                                zi * wz + mesh.lower_left[2],
                            ];
                            buildVoxel(p, sx, sy, sz, points, polys);
                        }
                    }
                }
                basePolyData.getPoints().setData(new window.Float32Array(points), 3);
                basePolyData.getPolys().setData(new window.Uint32Array(polys));
                basePolyData.buildCells();

                tallyBundle = coordMapper.buildPolyData(
                    basePolyData,
                    {
                        lighting: false,
                    }
                );
                vtkScene.addActor(tallyBundle.actor);
                picker.addPickList(tallyBundle.actor);
                setTallyColors();
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
                if (vtkScene.renderer !== callData.pokedRenderer || isGeometryOnly) {
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

            function isInFieldThreshold(value) {
                //TODO(pjm): add a min threshold value to openmcAnimation model
                return value > 0;
            }

            function setTallyColors() {
                const cellsPerVoxel = voxelPoly.length;
                const s = SIREPO.PLOTTING.Utils.colorScale(
                    minField,
                    maxField,
                    SIREPO.PLOTTING.Utils.COLOR_MAP()[appState.models.voxels.colorMap],
                );
                colorbar.scale(s);
                colorbarPtr = d3.select('.colorbar').call(colorbar);
                const sc = [];
                const o = Math.floor(255 * appState.models.openmcAnimation.opacity);
                for (const f of basePolyData.getFieldData().getArrayByName(model().aspect).getData()) {
                    if (! isInFieldThreshold(f)) {
                        continue;
                    }
                    const c = SIREPO.VTK.VTKUtils.colorToFloat(s(f)).map(v => Math.floor(255 * v));
                    c.push(o);
                    for (let j = 0; j < cellsPerVoxel; j++) {
                        sc.push(...c);
                    }
                }
                tallyBundle.setColorScalarsForCells(sc, 4);
                basePolyData.modified();
                vtkScene.render();
            }

            function loadTally(data) {
                basePolyData = SIREPO.VTK.VTKUtils.parseLegacy(data);
                buildVoxels();
            }

            $scope.supportsColorbar = () => ! isGeometryOnly;

            function loadVolumes(volIds) {
                //TODO(pjm): update progress bar with each promise resolve?
                return Promise.all(volIds.map(i => addVolume(i)));
            }

            function model() {
                return appState.models[$scope.modelName];
            }

            function scoreUnits() {
                return SIREPO.APP_SCHEMA.constants.scoreUnits[appState.models.openmcAnimation.score] || '';
            }

            function setGlobalProperties() {
                if (! vtkScene.renderer) {
                    return;
                }
                vtkScene.setBgColor(model().bgColor);
                for (const volId in bundleByVolume) {
                    const b = bundleByVolume[volId];
                    const v = getVolumeById(volId);
                    b.setActorProperty(
                        'opacity',
                        v.isVisible ? v.opacity * model().opacity : 0
                    );
                    b.setActorProperty(
                        'edgeVisibility',
                        model().showEdges === '1'
                    );
                }
                vtkScene.render();
            }

            function setVolumeProperty(bundle, name, value) {
                bundle.setActorProperty(name, value);
                vtkScene.render();
            }

            function showFieldInfo(callData) {
                function info(field, pos) {
                    const p = pos.map(
                        x => SIREPO.UTILS.roundToPlaces(x, 4).toLocaleString(
                            undefined,
                            {
                                minimumFractionDigits: 3,
                            }
                        )
                    );
                    return {
                        info: `
                                ${SIREPO.UTILS.roundToPlaces(field, 3)}
                                ${scoreUnits()} at
                                (${p[0]}, ${p[1]}, ${p[2]})cm
                            `,
                    };
                }

                if (vtkScene.renderer !== callData.pokedRenderer) {
                    return;
                }
                const pos = callData.position;
                picker.pick([pos.x, pos.y, 0.0], vtkScene.renderer);
                const cid = picker.getCellId();
                if (cid < 0) {
                    $scope.$broadcast('vtk.selected', null);
                    return;
                }
                const f = fieldData[Math.floor(cid / 6)];
                $scope.$broadcast(
                    'vtk.selected',
                    info(f, picker.getMapperPosition())
                );
                colorbarPtr.pointTo(f);
            }

            function volumesError(reason) {
                srlog(new Error(`Volume load failed: ${reason}`));
                $rootScope.$broadcast('vtk.hideLoader');
            }

            function volumesLoaded() {
                if (! vtkScene) {
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

            $scope.onlyClientFieldsChanged = false;

            // the vtk teardown is handled in vtkPlotting
            $scope.destroy = () => {
                vtkScene = null;
            };

            $scope.init = () => {
                $scope.fieldDelegate = buildOpacityDelegate();
            };

            $scope.load = json => {
                if (vtkScene) {
                    $rootScope.$broadcast('vtk.showLoader');
                    addTally(json.content, model().aspect);
                }
                else {
                    tally = json.content;
                }
            };

            $scope.resize = () => {
                //TODO(pjm): reposition camera?
            };

            $scope.sizeStyle = () => {
                if (! isGeometryOnly) {
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

            $scope.$on('fieldsChanged', function(e, modelFields) {
                $scope.onlyClientFieldsChanged = modelFields && modelFields.every(x => clientOnlyFields.includes(x));
            });

            $scope.$on('vtk-init', (e, d) => {
                $rootScope.$broadcast('vtk.showLoader');
                colorbar = Colorbar()
                    .margin({top: 5, right: colorbarThickness + 10, bottom: 5, left: 0})
                    .thickness(colorbarThickness)
                    .orient('vertical')
                    .barlength($('.vtk-canvas-holder').height())
                    .origin([0, 0]);
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

                picker = vtk.Rendering.Core.vtkCellPicker.newInstance();
                picker.setPickFromList(true);
                vtkScene.renderWindow.getInteractor().onLeftButtonPress(handlePick);
                if (! isGeometryOnly) {
                    vtkScene.renderWindow.getInteractor().onMouseMove(showFieldInfo);
                }

                const vols = [];
                for (const n in appState.models.volumes) {
                    if (! cloudmcService.isGraveyard(appState.models.volumes[n])) {
                        vols.push(appState.models.volumes[n].volId);
                    }
                }
                vtkScene.render();
                if (isGeometryOnly) {
                    loadVolumes(Object.values(vols)).then(volumesLoaded, volumesError);
                }
                if (tally) {
                    addTally(tally, model().aspect);
                    tally = null;
                }
                vtkScene.resetView();

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

            appState.watchModelFields($scope, ['voxels.colorMap'], setTallyColors);

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
                        args: {
                            name: value,
                            component: scope.model.component,
                        }
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

SIREPO.app.directive('sourcesOrTalliesEditor', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            model: '=',
            field: '=',
        },
        template: `
            <div class="col-sm-7">
              <button class="btn btn-xs btn-info pull-right"
                data-ng-click="addItem()">
                <span class="glyphicon glyphicon-plus"></span> Add {{ itemName }}</button>
            </div>
            <div class="col-sm-12">
              <table data-ng-if="model[field].length"
                style="width: 100%; table-layout: fixed; margin-bottom: 10px"
                class="table table-hover">
                <colgroup>
                  <col>
                  <col style="width: 8em">
                </colgroup>
                <thead>
                  <tr>
                    <th>{{ itemHeading }}</th>
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
                        data-ng-click="editItem(m)">Edit</button>
                      <button data-ng-click="removeItem(m)"
                        class="btn btn-danger btn-xs"><span
                          class="glyphicon glyphicon-remove"></span></button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
        `,
        controller: function($scope) {
            const childModel = $scope.field == 'sources' ? 'source' : 'tally';
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

            $scope.itemName = childModel === 'source' ? 'Source' : 'Tally';
            $scope.itemHeading = childModel === 'source' ? 'Space' : 'Tally';

            function nextIndex() {
                return $scope.model[$scope.field].length;
            }

            function editChild(model) {
                appState.models[childModel] = model;
                panelState.showModalEditor(childModel);
            }

            $scope.addItem = () => {
                editChild(appState.setModelDefaults({
                    _index: nextIndex(),
                }, childModel));
            };

            $scope.description = m => {
                if (childModel == 'source')  {
                    return sourceInfo('SpatialDistribution', m.space);
                }
                return tallyInfo(m);
            };

            function tallyInfo(model) {
                return model.name + ': ' + model.scores.map(t => t.score).join(', ');
            }

            function sourceInfo(modelType, model) {
                let res = appState.enumDescription(modelType, model._type);
                if (infoFields[model._type]) {
                    res += '(';
                    for (const f of infoFields[model._type]) {
                        if (! model[f]) {
                            continue;
                        }
                        res += `${f}=`;
                        if (model[f]._type) {
                            res += sourceInfo('ProbabilityDistribution', model[f]);
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

            $scope.editItem = model => {
                editChild(model);
            };

            $scope.removeItem = model => {
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

// A special enum editor which groups items within optgroups
SIREPO.app.directive('tallyScoreGroup', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            enum: '=',
        },
        template: `
            <select class="form-control" data-ng-model="model[field]"
              data-ng-options="item.v as item.l group by item.g for item in items">
            </select>
        `,
        controller: function($scope) {
            // enums are in order by group
            const groups = {
                flux: 'Flux scores',
                absorption: 'Reaction scores',
                'delayed-nu-fission': 'Particle production scores',
                current: 'Miscellaneous scores',
            };
            $scope.items = [];
            let g = '';
            for (const t of $scope.enum.TallyScore) {
                const v = t[0];
                if (groups[v]) {
                    g = groups[v];
                }
                $scope.items.push({
                    v: v,
                    l: t[1],
                    g: g,
                });
            }
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
    $scope.whenSelected = processPlanes;
    $scope.watchFields = [
        ['reflectivePlanes.useReflectivePlanes'], processPlanes,
    ];
});

SIREPO.app.directive('simpleListEditor', function(panelState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            subModel: '=',
        },
        template: `
            <div data-ng-repeat="row in model[field] track by $index">
              <div class="form-group form-group-sm">
                <div data-field-editor="subField"
                  data-model-name="subModel" data-label-size="0"
                  data-field-size="10"
                  data-model="model[field][$index]"></div>
                <div class="col-sm-2" style="margin-top: 5px">
                  <button data-ng-click="removeIndex($index)"
                    class="btn btn-danger btn-xs"><span
                      class="glyphicon glyphicon-remove"></span></button>
                </div>
              </div>
            </div>
            <div class="form-group form-group-sm">
              <div data-field-editor="subField" data-model-name="subModel"
                data-field-size="10"
                data-label-size="0" data-model="newRowModel"></div>
            </div>
        `,
        controller: function($scope, $element) {
            $scope.subField = SIREPO.APP_SCHEMA.view[$scope.subModel].advanced[0];
            $scope.newRowModel = {};

            $scope.removeIndex = (idx) => {
                $scope.model[$scope.field].splice(idx, 1);
            };

            $scope.$watchCollection('newRowModel', (newValue, oldValue) => {
                if (newValue && newValue[$scope.subField]) {
                    $scope.model[$scope.field].push({
                        [$scope.subField]: newValue[$scope.subField],
                    });
                    $scope.newRowModel = {};
                    // the focus should now be set to the new field in the field array
                    panelState.waitForUI(() => {
                        $($element).find(
                            `.model-${$scope.subModel}-${$scope.subField} input`,
                        ).eq(-2).focus();
                });
                }
            });
        },
    };
});

SIREPO.app.directive('materialList', function(appState, cloudmcService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <select class="form-control" data-ng-model="model[field]" data-ng-options="v.key as v.name for v in volumes"></select>
        `,
        controller: function($scope) {
            function initVolumes() {
                const res = [];
                const volumes = appState.applicationState().volumes;
                for (const k in volumes) {
                    if (cloudmcService.isGraveyard(volumes[k])) {
                        continue;
                    }
                    res.push({
                        key: k,
                        name: volumes[k].name,
                    });
                }
                res.sort((a, b) => a.name.localeCompare(b.name));
                return res;
            }
            $scope.volumes = initVolumes();
        },
    };
});

SIREPO.viewLogic('openmcAnimationView', function(appState, cloudmcService, panelState, $scope) {
    $scope.watchFields = [
        ['openmcAnimation.tally'], cloudmcService.validateSelectedTally,
    ];
});
