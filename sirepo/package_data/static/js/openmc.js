'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.SINGLE_FRAME_ANIMATION = [
        'energyAnimation',
    ];
    SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL = true;
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="geometry3d" data-geometry-3d="" class="sr-plot" data-model-name="{{ modelKey }}"></div>
        <div data-ng-switch-when="tallyViewer" data-tally-viewer="" class="sr-plot" data-model-name="{{ modelKey }}"></div>
    `;
    //TODO(pjm): OptionalFloat should be standard
    SIREPO.appFieldEditors = `
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
        <div data-ng-switch-when="PlotTallyList" data-ng-class="fieldClass">
          <div class="input-group">
            <div data-tally-list="model.tallies" data-model="model" data-field="field"></div>
          </div>
        </div>
        <div data-ng-switch-when="SettingsTallyList" data-ng-class="fieldClass">
          <div class="input-group">
            <div data-tally-list="appState.models.settings.tallies" data-model="model" data-field="field"></div>
          </div>
        </div>
        <div data-ng-switch-when="PlotScoreList" data-ng-class="fieldClass">
          <div class="input-group">
            <select class="form-control" data-ng-model="model[field]" data-ng-options="s.score as s.score for s in (model.tallies | filter:{name:model.tally})[0].scores"></select>
          </div>
        </div>
        <div data-ng-switch-when="FloatArray" class="col-sm-7">
            <div data-num-array="" data-model="model" data-field-name="field" data-field="model[field]" data-info="info" data-num-type="Float"></div>
        </div>
        <div data-ng-switch-when="Threshold" class="col-sm-7">
            <div data-threshold="" data-model-name="modelName" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="Opacity" class="col-sm-5">
          <div data-slider="" data-model="model" data-field="field" data-min="0" data-max="1" data-steps="101"  data-is-range="1"></div>
        </div>
        <div data-ng-switch-when="EnergyRange" class="col-sm-5">
          <div data-energy-range-slider="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="PlanePosition" class="col-sm-5">
          <div data-plane-position-slider="" data-model="model" data-field="field" data-dim="model.axis"></div>
        </div>
        <div data-ng-switch-when="XPlanePosition" class="col-sm-5">
          <div data-plane-position-slider="" data-model="model" data-field="field" data-dim="'x'"></div>
        </div>
        <div data-ng-switch-when="YPlanePosition" class="col-sm-5">
          <div data-plane-position-slider="" data-model="model" data-field="field" data-dim="'y'"></div>
        </div>
        <div data-ng-switch-when="ZPlanePosition" class="col-sm-5">
          <div data-plane-position-slider="" data-model="model" data-field="field" data-dim="'z'"></div>
        </div>
        <div data-ng-switch-when="PlanesList">
          <div data-plane-list="" data-model="model" data-field="field" data-sub-model-name="plane"></div>
        </div>
    `;
    SIREPO.FILE_UPLOAD_TYPE = {
        'geometryInput-dagmcFile': '.h5m,.stp',
        'geometryInput-materialsFile': '.xml',
    };
});

SIREPO.app.factory('openmcService', function(appState, panelState, $rootScope) {
    const self = {};
    appState.setAppService(self);

    function findFilter(tallies, tally, type) {
        const t = findTally(tallies, tally);
        return self.FILTER_INDICES
            .map(i => t[`filter${i}`])
            .filter(x => x._type === type)[0];
    }

    function findScore(tallies, tally, score) {
        return findTally(tallies, tally).scores.filter(v => v.score == score).length
            ? score
            : null;
    }

    function findTally() {
        const a = appState.models.openmcAnimation;
        return a.tallies.filter(v => v.name === a.tally)[0];
    }

    self.findScore = (score) => findScore(
        appState.models.openmcAnimation.tallies,
        appState.models.openmcAnimation.tally,
        score,
    );

    // volumes are measured in centimeters
    self.GEOMETRY_SCALE = SIREPO.APP_SCHEMA.constants.geometryScale;

    self.FILTER_INDICES = SIREPO.UTILS.indexArray(SIREPO.APP_SCHEMA.constants.maxFilters, 1);

    self.boxDimensions = space => {
        const size = space.upper_right.map((x, i) => Math.abs(x - space.lower_left[i]));
        return {
            center: size.map((x, i) => space.lower_left[i] + 0.5 * x),
            size: size,
        };
    };

    self.canNormalizeScore = score => ! SIREPO.APP_SCHEMA.constants.unnormalizableScores.includes(score);

    self.computeModel = (modelKey) => {
        if (modelKey == "energyAnimation") {
            return "openmcAnimation";
        }
        return modelKey;
    };

    self.findFilter = type => {
        return findFilter(
            appState.models.openmcAnimation.tallies,
            appState.models.openmcAnimation.tally,
            type
        );
    };

    self.findTally = () => {
        return findTally(
            appState.models.openmcAnimation.tallies,
            appState.models.openmcAnimation.tally,
        );
    };

    self.getNonGraveyardVolumes = () => {
        const vols = [];
        for (const n in appState.models.volumes) {
            if (! self.isGraveyard(appState.models.volumes[n])) {
                vols.push(appState.models.volumes[n].volId);
            }
        }
        return vols;
    };

    self.getSourceVisualizations = builders => {
        const sources = [];
        const noop = () => {};
        for (const s of appState.models.settings.sources.filter(x => x.space && x.space.only_fissionable !== '1')) {
            let b = null;
            const space = s.space;
            b = (builders[space._type] || noop)(space);
            if (b) {
                sources.push(b);
            }
        }
        return sources;
    };

    self.getVolumeById = volId => {
        for (const n in appState.models.volumes) {
            const v = appState.models.volumes[n];
            if (v.volId === volId) {
                return v;
            }
        }
        return null;
    };

    self.invalidateRange = (field) => {
        appState.models.openmcAnimation[field] = [0, 0];
    };

    self.isGraveyard = volume => {
        return volume.name && volume.name.toLowerCase() === 'graveyard';
    };

    self.isRangeValid = (field) => {
        const m = appState.models.openmcAnimation;
        return m[field] && (m[field][0] || m[field][1]);
    };

    self.toggleAllVolumes = (isVisible, visibleKey) => {
        for (const vId of self.getNonGraveyardVolumes()) {
            const v = self.getVolumeById(vId);
            if (v[visibleKey] !== isVisible) {
                self.toggleVolume(v, visibleKey, false);
            }
        }
        $rootScope.$broadcast('sr-volume-visibility-toggle-all', isVisible);
        appState.saveQuietly('volumes');
    };

    self.toggleVolume = (volume, visibleKey, doUpdate) => {
        volume[visibleKey] = ! volume[visibleKey];
        $rootScope.$broadcast('sr-volume-visibility-toggle', volume, volume[visibleKey], doUpdate);
        if (doUpdate) {
            appState.saveQuietly('volumes');
        }
    };

    self.validateSelectedTally = () => {
        const a = appState.models.openmcAnimation;
        if (! a.tally || ! findTally()) {
            a.tally = a.tallies[0].name;
        }
        if (! a.score || ! self.findScore(a.score)) {
            a.score = findTally().scores[0].score;
        }
        appState.saveQuietly('openmcAnimation');
    };
    return self;
});

SIREPO.app.controller('GeometryController', function (appState, openmcService, panelState, persistentSimulation, requestSender, $scope) {
    const self = this;
    let hasVolumes = false;
    let hasGeometry = false;
    self.simScope = $scope;
    self.simComputeModel = 'dagmcAnimation';

    function downloadRemoteGeometryFile() {
        requestSender.sendStatefulCompute(
            appState,
            data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                appState.models.geometryInput.exampleURL = "";
                appState.saveQuietly('geometryInput');
                processGeometry();
            },
            {
                method: 'download_remote_lib_file',
                args: {
                    exampleURL: appState.models.geometryInput.exampleURL,
                },
            }
        );
    }

    function processGeometry() {
        panelState.showFields('geometryInput', [
            ['dagmcFile', 'materialsFile'], false,
        ]);
        if (appState.models.geometryInput.exampleURL) {
            downloadRemoteGeometryFile();
            return;
        }
        hasGeometry = true;
        self.simState.runSimulation();
    }

    function verifyGeometry() {
        requestSender.sendStatefulCompute(
            appState,
            (data) => {
                // don't initialize simulation until geometry is known
                hasGeometry = data.animationDirExists;
                self.simState = persistentSimulation.initSimulationState(self);
                self.simState.errorMessage = () => self.errorMessage;
            },
            {
                method: 'check_animation_dir',
                args: {
                    modelName: 'dagmcAnimation',
                },
            },
        );
    }

    self.isGeometrySelected = () => {
        return appState.applicationState().geometryInput.dagmcFile;
    };

    self.isGeometryProcessed = () => hasVolumes;

    self.simHandleStatus = (data) => {
        self.errorMessage = data.error;
        self.hasServerStatus = true;
        if (hasGeometry && data.volumes) {
            hasVolumes = true;
            if (! Object.keys(appState.applicationState().volumes).length) {
                appState.models.volumes = data.volumes;
                for (const n in data.volumes) {
                    if (data.volumes[n].material) {
                        appState.setModelDefaults(data.volumes[n].material, 'material');
                    }
                }
                appState.saveChanges('volumes');
            }
        }
        else if (['canceled', 'completed', 'missing'].includes(data.state)) {
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

    verifyGeometry();
});

SIREPO.app.controller('VisualizationController', function(appState, openmcService, frameCache, panelState, persistentSimulation, requestSender, tallyService, $scope) {
    const self = this;
    self.eigenvalue = null;
    self.results = null;
    self.simScope = $scope;
    self.simComputeModel = 'openmcAnimation';
    let errorMessage, isRunning, statusMessage;

    function validateSelectedTally(tallies) {
        appState.models.openmcAnimation.tallies = tallies;
        appState.saveQuietly('openmcAnimation');
        openmcService.validateSelectedTally();
    }

    self.eigenvalueHistory = () => appState.models.settings.eigenvalueHistory;

    $scope.showEnergyPlot = () => {
        return openmcService.findFilter('energyFilter')
            && appState.applicationState().openmcAnimation.isEnergySelected === "1";
    };

    self.simHandleStatus = function(data) {
        statusMessage = '';
        tallyService.isRunning = self.simState.isProcessing();
        if (isRunning || self.simState.isProcessing()) {
            if (data.frameCount != frameCache.getFrameCount()) {
                openmcService.invalidateRange('thresholds');
            }
            isRunning = self.simState.isProcessing();
        }
        errorMessage = data.error;
        self.eigenvalue = data.eigenvalue;
        self.results = data.results;
        if (data.iteration > 0) {
            statusMessage = ': ' + (data.iteration > 1 ? ( data.iteration + ' iterations, ') : '') + data.batch + ' batches';
        }
        if (data.frameCount) {
            frameCache.setFrameCount(data.frameCount);
        }
        if (data.tallies) {
            validateSelectedTally(data.tallies);
        }
    };
    self.simState = persistentSimulation.initSimulationState(self);
    self.simState.errorMessage = () => errorMessage;
    self.simCompletionState = () => {
        return statusMessage;
    };
    self.simState.runningMessage = () => {
        return 'Completed' + statusMessage;
    };
    self.startSimulation = function() {
        tallyService.clearMesh();
        const r = appState.models.openmcAnimation;
        delete r.tallies;
        delete r.tally;
        openmcService.invalidateRange('energyRangeSum');
        openmcService.invalidateRange('thresholds');
        r.isEnergySelected = "0";
        panelState.clear('tallyReport');
        self.simState.saveAndRunSimulation('openmcAnimation');
    };
    self.simState.logFileURL = function() {
        return requestSender.downloadRunFileUrl(
            appState,
            {
                model: self.simState.model,
                suffix: 'log',
            },
        );
    };
    self.tallyTitle = () => {
        const a = appState.models.openmcAnimation;
        return `Tally Results - ${a.tally} - ${a.score} - ${a.aspect}`;
    };

    const sortTallies = () => {
        for (const t of appState.models.settings.tallies) {
            // sort and unique scores
            const v = {};
            const r = [];
            for (const s of t.scores) {
                if (! v[s.score]) {
                    r.push(s);
                    v[s.score] = true;
                }
            }
            t.scores = r.sort((a, b) => a.score.localeCompare(b.score));
            appState.saveQuietly('settings');
        }
    };

    $scope.$on('settings.changed', sortTallies);

    sortTallies();
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

SIREPO.app.directive('appHeader', function(appState, openmcService, panelState) {
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

SIREPO.app.factory('tallyService', function(appState, openmcService, utilities, $rootScope) {
    const self = {
        mesh: null,
        fieldData: null,
        minField: 0,
        maxField: 0,
        outlines: null,
        sourceParticles: [],
    };

    function normalizer(score, numParticles) {
        if (numParticles === undefined || ! openmcService.canNormalizeScore(score)) {
            return x => x;
        }
        return x => (appState.models.openmcAnimation.sourceNormalization / numParticles) * x;
    }

    self.clearMesh = () => {
        self.mesh = null;
        self.fieldData = null;
        self.outlines = null;
    };

    self.colorScale = modelName => {
        return SIREPO.PLOTTING.Utils.colorScale(
            ...appState.models.openmcAnimation.thresholds,
            SIREPO.PLOTTING.Utils.COLOR_MAP()[appState.applicationState()[modelName].colorMap],
        );
    };

    self.getEnergyReportCoords = () => {
        const [x, y] = SIREPO.GEOMETRY.GeometryUtils.nextAxes(appState.models.tallyReport.axis).reverse();
        if (appState.applicationState().openmcAnimation.isEnergySelected === "0") {
            return null;
        }
        const r = appState.models.energyAnimation;
        return [
            r[x],
            r[y],
        ];
    };

    self.getMaxMeshExtent = () => {
        let e = 0;
        for (const r of self.getMeshRanges()) {
            e = Math.max(e, Math.abs(r[1] - r[0]));
        }
        return e;
    };

    self.getMeshRanges = () => {
        return SIREPO.GEOMETRY.GeometryUtils.BASIS().map(
            dim => SIREPO.GEOMETRY.GeometryUtils.axisIndex(dim),
        ).map(i => [
            openmcService.GEOMETRY_SCALE * self.mesh.lower_left[i],
            openmcService.GEOMETRY_SCALE * self.mesh.upper_right[i],
            self.mesh.dimension[i],
        ]);
    };

    self.getOutlines = (volId, dim, index) => {
        if (! self.outlines) {
            return [];
        }
        const t = self.outlines[appState.applicationState().openmcAnimation.tally];
        if (t && t[`${volId}`]) {
            const o = t[`${volId}`][dim];
            if (o.length) {
                return o[index];
            }
        }
        return [];
    };

    self.getSourceParticles = () => self.sourceParticles;

    self.initMesh = () => {
        const t = openmcService.findTally();
        for (let k = 1; k <= SIREPO.APP_SCHEMA.constants.maxFilters; k++) {
            const f = t[`filter${k}`];
            if (f && f._type === 'meshFilter') {
                self.mesh = f;
                return true;
            }
        }
        self.mesh = null;
        return false;
    };

    self.setFieldData = (fieldData, min, max, numParticles) => {
        const n = normalizer(appState.models.openmcAnimation.score, numParticles);
        self.fieldData = fieldData.map(n);
        self.minField = n(min);
        self.maxField = n(max);
        if (! openmcService.isRangeValid('thresholds')) {
            appState.models.openmcAnimation.thresholds = [self.minField, self.maxField];
            appState.saveQuietly('openmcAnimation');
        }
        const f = openmcService.findFilter('energyFilter');
        if (f && ! openmcService.isRangeValid('energyRangeSum')) {
            appState.models.openmcAnimation.energyRangeSum = [
                f.start,
                f.stop,
            ];
        }
    };

    self.setOutlines = (tally, outlines) => {
        if (appState.applicationState().openmcAnimation.tally === tally) {
            self.outlines = {
                [tally]: outlines,
            };
        }
    };

    self.setSourceParticles = particles => {
        self.sourceParticles = particles;
    };

    self.sourceParticleColorScale = colorMapName => {
        const r = self.sourceParticleEnergyRange();
        return SIREPO.PLOTTING.Utils.colorScale(
            r[0],
            r[1],
            SIREPO.PLOTTING.Utils.COLOR_MAP()[colorMapName],
        );
    };

    self.sourceParticleEnergyRange = () => {
        const e = self.getSourceParticles().map(x => x.energy);
        return [utilities.arrayMin(e), utilities.arrayMax(e)];
    };

    self.sourceParticleMeanEnergy = () => {
        let e = 0;
        const p = self.getSourceParticles();
        const n = p.length;
        if (! n) {
            return e;
        }
        for (const s of p) {
            e += s.energy;
        }
        return e / n;
    };

    self.tallyRange = (dim, useBinCenter=false) => {
        if (! self.mesh) {
            return {};
        }
        const r = self.getMeshRanges()[SIREPO.GEOMETRY.GeometryUtils.BASIS().indexOf(dim)];
        const s = Math.abs((r[1] - r[0])) / r[2];
        const f = useBinCenter ? 0.5 : 0;
        return {
            min: r[0] + f * s,
            max: r[1] - f * s,
            steps: r[2],
        };
    };

    self.updateTallyDisplay = () => {
        appState.models.tallyReport.colorMap = appState.models.openmcAnimation.colorMap;
        // save quietly but immediately
        appState.saveQuietly('openmcAnimation');
        appState.saveQuietly('tallyReport');
        appState.autoSave();
    };

    $rootScope.$on('modelsUnloaded', self.clearMesh);

    return self;
});

SIREPO.app.factory('volumeLoadingService', function(appState, requestSender, $rootScope) {
    const self = {};
    let cacheReadersByVol = {};

    function addVolume(volId, initCallback) {
        let reader = cacheReadersByVol[volId];
        let res;
        if (reader) {
            res = Promise.resolve();
        }
        else {
            reader = vtk.IO.Core.vtkHttpDataSetReader.newInstance();
            cacheReadersByVol[volId] = reader;
            res = reader.setUrl(volumeURL(volId), {
                compression: 'zip',
                fullpath: true,
                loadData: true,
            });
        }
        initCallback(volId, reader);
        return res;
    }

    function volumesError(reason) {
        srlog(new Error(`Volume load failed: ${reason}`));
        $rootScope.$broadcast('vtk.hideLoader');
    }

    function volumeURL(volId) {
        return requestSender.downloadRunFileUrl(
            appState,
            {
                model: 'dagmcAnimation',
                frame: volId,
            }
        );
    }

    self.loadVolumes = (volIds, initCallback, loadedCallback) => {
        //TODO(pjm): update progress bar with each promise resolve?
        Promise.all(
            volIds.map(i => addVolume(i, initCallback))
        ).then(loadedCallback, volumesError);
    };

    $rootScope.$on('modelsUnloaded', () => {
        cacheReadersByVol = {};
    });

    return self;
});

SIREPO.app.directive('planeList', function(appState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            subModelName: '@',
        },
        template: `
            <div style="position: relative; top: -25px">
              <div class="col-sm-12">
                <div class="row">
                  <div class="col-sm-2" data-ng-repeat="(key, value) in model[field][0]">
                    <div class="text-center" data-label-with-tooltip=""
                      data-label="{{ label(key) }}" data-tooltip="{{ tooltip(key) }}"></div>
                  </div>
                </div>
                <div data-ng-repeat="plane in model[field] track by $index">
                  <div class="row" style="margin-bottom: 15px">
                    <div data-ng-repeat="(key, value) in plane">
                      <div data-model-field="key" data-model-name="subModelName"
                        data-model-data="modelData($parent.$index)" data-label-size="0"
                        data-field-size="2"></div>
                      </div>
                    <div class="col-sm-2">
                      <button data-ng-click="deletePlane($index)"
                        class="row btn btn-danger btn-xs">
                        <span class="glyphicon glyphicon-remove"></span>
                      </button>
                    </div>
                  </div>
                </div>
                <div class="col-md-5">
                  <button type="button" data-ng-click="addPlane()"
                    class="btn btn-primary">Add New Plane</button>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
            const modelData = {};

            $scope.addPlane = () => {
                appState.models.reflectivePlanes.planesList.push(
                    appState.setModelDefaults({}, 'plane'),
                );
            };

            $scope.deletePlane = (index) => {
                appState.models.reflectivePlanes.planesList.splice(index, 1);
            };

            $scope.label = (field) => appState.modelInfo($scope.subModelName)[field][0];

            $scope.modelData = (index) => {
                if (! $scope.model) {
                    return;
                }
                if (! modelData[index]) {
                    modelData[index] = {
                        getData: () => $scope.model[$scope.field][index],
                    };
                }
                return modelData[index];
            };

            $scope.tooltip = (field) => appState.modelInfo($scope.subModelName)[field][3];
        }
    };
});

SIREPO.app.directive('tallyVolumePicker', function(openmcService, volumeLoadingService) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div data-ng-if="volumeList" style="padding-top: 8px; padding-bottom: 8px;"><div data-ng-click="toggleVolumeList()" title="{{ isVolumeListExpanded ? 'hide' : 'show' }}" style="cursor: pointer; display: inline-block">Select Volumes <span class="glyphicon" data-ng-class="isVolumeListExpanded ? 'glyphicon-chevron-up' : 'glyphicon-chevron-down'"></span></div></div>
            <div data-ng-if="! buildVolumeList()" style="padding-top: 8px; padding-bottom: 8px;">Loading Volumes<span data-header-tooltip="'loading'"></span></div>
            <table data-ng-show="isVolumeListExpanded" class="table-condensed">
                <thead>
                <th style="border-bottom: solid lightgray;" colspan="{{ numVolumeCols }}">
                    <div
                        title="{{ allVolumesVisible ? 'Deselect' : 'Select' }} all volumes"
                        style="display: inline-block; cursor: pointer; white-space: nowrap; min-height: 25px;"
                        data-ng-click="toggleAllVolumes(v)">
                            <span class="glyphicon"
                                data-ng-class="allVolumesVisible ? 'glyphicon-check' : 'glyphicon-unchecked'">
                            </span>
                    </div>
                </th>
                </thead>
                <tbody>
                    <tr data-ng-repeat="r in volumeList track by $index">
                        <td data-ng-repeat="v in r track by v.volId">
                            <div
                                title="{{ v.isVisibleWithTallies ? 'Deselect' : 'Select' }} volume"
                                style="display: inline-block; cursor: pointer; white-space: nowrap; min-height: 25px;"
                                data-ng-click="toggleVolume(v)">
                                    <span class="glyphicon"
                                        data-ng-class="v.isVisibleWithTallies ? 'glyphicon-check' : 'glyphicon-unchecked'"></span>
                                <span style="font-weight: 500;">{{ v.name }}</span>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        `,
        controller: function($scope) {
            $scope.allVolumesVisible = false;
            $scope.numVolumeCols = 2;
            $scope.isVolumeListExpanded = false;
            $scope.volumeList = null;
            const volumeIds = openmcService.getNonGraveyardVolumes();

            function getVolumes() {
                return volumeIds.map(x => openmcService.getVolumeById(x));
            }

            $scope.buildVolumeList = () => {
                if (! $scope.volumeList) {
                    const vols = getVolumes();
                    if (! $scope.numVolumeCols) {
                        return vols;
                    }
                    const v = [];
                    for (let i = 0; i < vols.length; i += $scope.numVolumeCols) {
                        v.push(vols.slice(i, i + $scope.numVolumeCols));
                    }
                    $scope.volumeList = v;
                }
                return true;
            };

            $scope.toggleAllVolumes = () => {
                $scope.allVolumesVisible = ! $scope.allVolumesVisible;
                openmcService.toggleAllVolumes($scope.allVolumesVisible, 'isVisibleWithTallies');
            };

            $scope.toggleVolume = volume => {
                openmcService.toggleVolume(volume, 'isVisibleWithTallies', true);
            };

            $scope.toggleVolumeList = () => {
                $scope.isVolumeListExpanded = ! $scope.isVolumeListExpanded;
            };
        },
    };
});

SIREPO.app.directive('tallyViewer', function(appState, openmcService, plotting, tallyService) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: `
            <div style="height: 90%">
                <ul class="nav nav-tabs">
                    <li role="presentation" data-ng-class="{active: is2D()}">
                        <a href data-ng-click="setSelectedGeometry('2D')">2D</a>
                    </li>
                    <li role="presentation" data-ng-class="{active: is3D()}">
                        <a href data-ng-click="setSelectedGeometry('3D')">3D</a>
                    </li>
                </ul>
                <div data-ng-if="is3D()">
                    <div data-report-content="geometry3d" data-model-key="{{ modelName }}"></div>
                </div>
                <div data-ng-if="is2D()">
                    <div data-geometry-2d="" data-energy-filter="energyFilter()"></div>
                </div>
            </div>
        `,
        controller: function($scope) {
            plotting.setTextOnlyReport($scope);

            $scope.appState = appState;

            $scope.energyFilter = () => openmcService.findFilter('energyFilter');

            $scope.load = json => {
                if (json.content) {
                    // old format, ignore
                    return;
                }
                tallyService.setFieldData(json.field_data, json.min_field, json.max_field, json.num_particles);
                tallyService.setOutlines(json.summaryData.tally, json.summaryData.outlines || {});
                tallyService.setSourceParticles(json.summaryData.sourceParticles || []);
            };

            $scope.setSelectedGeometry = d => {
                appState.models.tallyReport.selectedGeometry = d;
                appState.saveQuietly('tallyReport');
            };
            $scope.is2D = () => appState.applicationState().tallyReport.selectedGeometry === '2D';
            $scope.is3D = () => ! $scope.is2D();
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('geometry2d', function(appState, openmcService, panelState, tallyService) {
    return {
        restrict: 'A',
        scope: {
            energyFilter: '=',
        },
        template: `
            <div data-heatmap="" class="sr-plot sr-screenshot" data-model-name="tallyReport" data-is-client-only="1"></div>
        `,
        controller: function($scope) {
            $scope.tallyService = tallyService;
            const displayRanges = {};
            const sources = openmcService.getSourceVisualizations(
                {
                    box: space => {
                        const d = openmcService.boxDimensions(space);
                        return new SIREPO.VTK.CuboidViews(
                            null,
                            'box',
                            d.center,
                            d.size,
                            openmcService.GEOMETRY_SCALE
                        );
                    },
                    point: space => {
                        return new SIREPO.VTK.SphereViews(
                            null,
                            'point',
                            space.xyz,
                            0.5,
                            24,
                            openmcService.GEOMETRY_SCALE,
                        );
                    },
                }
            );

            function setBins(hVal, vVal) {
                const [z, x, y] = tallyReportAxes();
                const r = appState.models.energyAnimation;
                r[x] = hVal;
                r[y] = vVal;
                r[z] = appState.models.tallyReport.planePos;
                appState.models.openmcAnimation.isEnergySelected = "1";
            }

            function buildTallyReport() {
                if (! tallyService.mesh) {
                    return;
                }
                const [z, x, y] = tallyReportAxes();
                const [n, m, l] = tallyReportAxisIndices();
                const ranges = tallyService.getMeshRanges();
                const pos = appState.models.tallyReport.planePos;

                // for now set the aspect ratio to something reasonable even if it distorts the shape
                const arRange = [0.50, 1.25];
                let ar = Math.max(
                    arRange[0],
                    Math.min(
                        arRange[1],
                        Math.abs(ranges[m][1] - ranges[m][0]) / Math.abs(ranges[l][1] - ranges[l][0])
                    )
                );
                const r =  {
                    enableSelection: ! ! $scope.energyFilter,
                    aspectRatio: ar,
                    global_min: appState.models.openmcAnimation.thresholds[0],
                    global_max: appState.models.openmcAnimation.thresholds[1],
                    threshold: appState.models.openmcAnimation.thresholds,
                    title: `Score at ${z} = ${SIREPO.UTILS.roundToPlaces(pos, 6)}m${energySumLabel()}`,
                    x_label: `${x} [m]`,
                    x_range: ranges[l],
                    y_label: `${y} [m]`,
                    y_range: ranges[m],
                    z_matrix: reorderFieldData(tallyService.mesh.dimension)[fieldIndex(pos, ranges[n], n)],
                    z_range: ranges[n],
                    overlayData: getOutlines(pos, ranges[n], n),
                    selectedCoords: $scope.energyFilter ? tallyService.getEnergyReportCoords() : null,
                };
                panelState.setData('tallyReport', r);
                $scope.$broadcast('tallyReport.reload', r);
            }

            function displayRangeIndices() {
                const r = tallyService.getMeshRanges();
                return [
                    displayRanges.x,
                    displayRanges.y,
                    displayRanges.z,
                ]
                    .map((x, i) => [fieldIndex(x.min, r[i], i), fieldIndex(x.max, r[i], i)]);
            }

            function energySumLabel() {
                const sumRange = appState.models.openmcAnimation.energyRangeSum;
                return $scope.energyFilter ? ` / Energy ∑ ${sumDisplay(sumRange[0])}-${sumDisplay(sumRange[1])} MeV` : '';
            }

            function fieldIndex(pos, range, dimIndex) {
                const d = tallyService.mesh.dimension[dimIndex];
                return Math.min(
                    d - 1,
                    Math.max(0, Math.floor(d * (pos - range[0]) / (range[1] - range[0])))
                );
            }

            function getOutlines(pos, range, dimIndex) {

                const particleColors = SIREPO.UTILS.unique(
                    tallyService.getSourceParticles().map(p => particleColor(p))
                );

                function isPosOutsideMesh(pos, j, k) {
                    const r = tallyService.getMeshRanges();
                    return pos[j] < r[j][0] || pos[j] > r[j][1] || pos[k] < r[k][0] || pos[k]  > r[k][1];
                }

                function particleColor(p) {
                    return tallyService.sourceParticleColorScale(
                        appState.models.openmcAnimation.sourceColorMap
                    )(p.energy);
                }

                function particleId(p) {
                    return particleIdFromColor(particleColor(p));
                }

                function particleIdFromColor(c) {
                    return `arrow-${c.slice(1)}`;
                }

                // we cannot set the color of an instance of a marker ref, so we will
                // have to create them on the fly
                function placeMarkers() {
                    const ns = 'http://www.w3.org/2000/svg';
                    let ds = d3.select('svg.sr-plot defs')
                        .selectAll('marker')
                        .data(particleColors);
                    ds.exit().remove();
                    ds.enter()
                        .append(d => document.createElementNS(ns, 'marker'))
                        .append('path')
                        .attr('d', 'M0,0 L0,4 L9,2 z');
                    ds.call(updateMarkers);
                }

                function updateMarkers(selection) {
                    selection
                        .attr('id', d => particleIdFromColor(d))
                        .attr('markerHeight', 8)
                        .attr('markerWidth', 8)
                        .attr('refX', 4)
                        .attr('refY', 2)
                        .attr('orient', 'auto')
                        .attr('markerUnits', 'strokeWidth')
                        .select('path')
                        .attr('fill', d => sourceColor(d));
                }

                const outlines = [];
                const dim = SIREPO.GEOMETRY.GeometryUtils.BASIS()[dimIndex];
                for (const volId of openmcService.getNonGraveyardVolumes()) {
                    const v = openmcService.getVolumeById(volId);
                    if (! v.isVisibleWithTallies) {
                        continue;
                    }
                    const o = tallyService.getOutlines(volId, dim, fieldIndex(pos, range, dimIndex));
                    o.forEach((arr, i) => {
                        outlines.push({
                            name: `${v.name}-${i}`,
                            color: v.color,
                            data: arr,
                        });
                    });
                }
                sources.forEach((view, i) => {
                    const s = appState.models.settings.sources[i];
                    if (view instanceof SIREPO.VTK.SphereViews) {
                        view.setRadius(25 * vectorScaleFactor());
                    }
                    outlines.push({
                        name: `source-${s.particle}-${s.space._type}-${i}`,
                        color: sourceColor('#ff0000'),
                        data: view.shapePoints(dim).map(p => p.toReversed()),
                        doClose: true,
                    });
                });
                placeMarkers();
                const r = vectorScaleFactor();
                const [j, k] = SIREPO.GEOMETRY.GeometryUtils.nextAxisIndices(dim);
                tallyService.getSourceParticles().forEach((p, n) => {
                    const p1 = [p.position[j], p.position[k]].map(x => x * openmcService.GEOMETRY_SCALE);
                    // ignore sources outside the plotting range
                    if (isPosOutsideMesh(p1, j, k)) {
                        return;
                    }
                    // normalize in the plane and check if perpendicular
                    const d = Math.hypot(p.direction[j], p.direction[k]);
                    const p2 = d ? [p1[0] + r * p.direction[j] / d, p1[1] + r * p.direction[k] / d] : p1;
                    outlines.push({
                        name: `${p.type}-${p.energy}eV-${n}`,
                        color: sourceColor(particleColor(p)),
                        dashes: p.type === 'PHOTON' ? '6 2' : '',
                        data: [p1, p2].map(p => p.toReversed()),
                        marker: particleId(p),
                    });
                });
                return outlines;
            }

            function reorderFieldData(dims) {
                const [n, m, l] = tallyReportAxisIndices();
                const fd = tallyService.fieldData;
                const d = SIREPO.UTILS.reshape(fd, dims.slice().reverse());
                const inds = displayRangeIndices();
                let N = 1;
                for (const idx of inds) {
                    N *= (idx[1] - idx[0] + 1);
                }
                const ff = SIREPO.UTILS.reshape(
                    new Array(N),
                    [(inds[n][1] - inds[n][0] + 1), (inds[m][1] - inds[m][0] + 1), (inds[l][1] - inds[l][0] + 1)]
                );

                for (let k = 0; k <= (inds[n][1] - inds[n][0]); ++k) {
                    for (let j = 0; j <= (inds[m][1] - inds[m][0]); ++j) {
                        for (let i = 0; i <= (inds[l][1] - inds[l][0]); ++i) {
                            const v = [0, 0, 0];
                            v[l] = inds[l][0] + i;
                            v[m] = inds[m][0] + j;
                            v[n] = inds[n][0] + k;
                            ff[k][j][i] = d[v[2]][v[1]][v[0]];
                        }
                    }
                }
                return ff;
            }

            function sourceColor(color) {
                return appState.models.openmcAnimation.showSources === '1' ? color : 'none';
            }

            function sumDisplay(val) {
                const sumRange = appState.models.openmcAnimation.energyRangeSum;
                if ($scope.energyFilter.space === 'log' && $scope.energyFilter.start > 0) {
                    return SIREPO.UTILS.formatFloat(
                        SIREPO.UTILS.linearToLog(val, $scope.energyFilter.start, $scope.energyFilter.stop, $scope.energyFilter.num - 1),
                        4
                    );
                }
                return val;
            }

            function tallyReportAxes() {
                return [
                    appState.models.tallyReport.axis,
                    ...SIREPO.GEOMETRY.GeometryUtils.nextAxes(appState.models.tallyReport.axis).reverse()
                ];
            }

            function tallyReportAxisIndices() {
                return SIREPO.GEOMETRY.GeometryUtils.axisIndices(appState.models.tallyReport.axis);
            }

            function updateDisplay() {
                tallyService.updateTallyDisplay();
                updateSlice();
            }

            function updateDisplayRange() {
                if (! tallyService.initMesh()) {
                    return;
                }
                SIREPO.GEOMETRY.GeometryUtils.BASIS().forEach(dim => {
                    displayRanges[dim] = tallyService.tallyRange(dim);
                });
                updateVisibleAxes();
                updateSliceAxis();
            }

            function updateSlice() {
                buildTallyReport();
                // save quietly but immediately
                appState.saveQuietly('tallyReport');
                appState.saveQuietly('openmcAnimation');
                appState.autoSave();
            }

            function updateSliceAxis() {
                if (! tallyService.fieldData) {
                    return;
                }
                if (! tallyService.initMesh()) {
                    return ;
                }
                updateSlice();
            }

            function updateVisibleAxes() {
                const v = {};
                SIREPO.GEOMETRY.GeometryUtils.BASIS().forEach(dim => {
                    v[dim] = true;
                    SIREPO.GEOMETRY.GeometryUtils.BASIS_VECTORS()[dim].forEach((bv, bi) => {
                        if (! bv && tallyService.mesh.dimension[bi] < SIREPO.APP_SCHEMA.constants.minTallyResolution) {
                            delete v[dim];
                        }
                    });
                });
                SIREPO.GEOMETRY.GeometryUtils.BASIS().forEach(dim => {
                    const s = ! Object.keys(v).length || dim in v;
                    panelState.showEnum('tallyReport', 'axis', dim, s);
                    if (! s && appState.models.tallyReport.axis === dim) {
                        appState.models.tallyReport.axis = Object.keys(v)[0];
                    }
                });
            }

            function vectorScaleFactor() {
                return 0.05 * tallyService.getMaxMeshExtent();
            }

            $scope.$on('sr-plotEvent', (e, d) => {
                if (d.name !== SIREPO.PLOTTING.HeatmapSelectCellEvent) {
                    return;
                }
                if (d.cell) {
                    setBins(...d.cell);
                }
                else {
                    appState.models.openmcAnimation.isEnergySelected = '0';
                }
                appState.saveChanges(['energyAnimation', 'openmcAnimation']);
            });

            $scope.$on('sr-volume-visibility-toggle', (event, volume, isVisible, doUpdate) => {
                if (doUpdate) {
                    buildTallyReport();
                }
            });

            $scope.$on('sr-volume-visibility-toggle-all', buildTallyReport);
            appState.watchModelFields($scope, ['tallyReport.axis'], updateSliceAxis);
            appState.watchModelFields($scope, ['openmcAnimation.colorMap', 'openmcAnimation.sourceColorMap'], updateDisplay);
            appState.watchModelFields($scope, ['tallyReport.planePos', 'openmcAnimation.showSources'], updateSlice, true);
            $scope.$watch('tallyService.fieldData', (newValue, oldValue) => {
                if (newValue && newValue !== oldValue) {
                    updateDisplayRange();
                }
            });

            $scope.$on('sr-plotLinked', () => {
                if (tallyService.fieldData) {
                    updateDisplayRange();
                }
            });
        },
    };
});

SIREPO.app.directive('geometry3d', function(appState, openmcService, plotting, plotToPNG, tallyService, utilities, volumeLoadingService, $rootScope) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: `
            <div data-vtk-display="" class="vtk-display col-sm-11"
                  data-ng-style="sizeStyle()" data-show-border="true"
                  data-model-name="{{ modelName }}"
                  data-event-handlers="eventHandlers" data-reset-side="y" data-reset-direction="-1"
                  data-enable-axes="true" data-axis-cfg="axisCfg"
                  data-axis-obj="axisObj" data-enable-selection="true"></div>
            <div class="col-sm-1" style="padding-left: 0;" data-ng-show="supportsColorbar()">
                <div class="colorbar"></div>
            </div>
        `,
        controller: function($scope, $element) {
            const hasTallies = $scope.modelName === 'openmcAnimation';
            $scope.isClientOnly = true;
            $scope.tallyService = tallyService;

            // 3d geometry state
            const axes = {
                boxes: {},
                SCENE_BOX: '_scene',
            };
            const bundleByVolume = {};
            const coordMapper = new SIREPO.VTK.CoordMapper(
                new SIREPO.GEOMETRY.Transform(
                    new SIREPO.GEOMETRY.SquareMatrix([
                        [openmcService.GEOMETRY_SCALE, 0, 0],
                        [0, openmcService.GEOMETRY_SCALE, 0],
                        [0, 0, openmcService.GEOMETRY_SCALE],
                    ])
                )
            );
            let picker = null;
            let renderedFieldData = [];
            let selectedVolume = null;
            const sourceProps = {
                color: [255, 0, 0],
                edgeVisibility: true,
                lighting: false,
            };
            const sourceBundles = openmcService.getSourceVisualizations(
                {
                    box: space => {
                        const d = openmcService.boxDimensions(space);
                        const b = coordMapper.buildBox(
                            d.size,
                            d.center,
                            sourceProps
                        );
                        b.actorProperties.setRepresentationToWireframe();
                        return b;
                    },
                    point: space => {
                        const b = coordMapper.buildSphere(
                            space.xyz,
                            0.5,
                            sourceProps
                        );
                        b.setRes(8, 8);
                        b.actorProperties.setRepresentationToWireframe();
                        return b;
                    },
                }
            );
            let particleBundle = null;

            let vtkScene = null;

            // ********* 3d tally state and functions
            //TODO(pjm): these should be moved to a subdirective

            const colorbar = {
                element: null,
                pointer: null,
                THICKNESS: 30,
            };
            let tallyBundle = null;
            let tallyPolyData = null;
            const voxelPoly = [
                [0, 1, 2, 3],
                [4, 5, 6, 7],
                [4, 5, 1, 0],
                [3, 2, 6, 7],
                [4, 0, 3, 7],
                [1, 5, 6, 2],
            ];

            function addTally(data) {
                tallyPolyData = vtk.Common.DataModel.vtkPolyData.newInstance();
                buildVoxels();
                addSources();
                $rootScope.$broadcast('vtk.hideLoader');
                initAxes();
                buildAxes();
                vtkScene.renderer.resetCamera();
                vtkScene.render();
            }

            function addSources() {
                sourceBundles.forEach(b => {
                    vtkScene.removeActor(b.actor);
                    if (appState.models.openmcAnimation.showSources !== '1') {
                        return;
                    }
                    if (b.source.setRadius) {
                        b.source.setRadius(0.25 * vectorScaleFactor());
                    }
                    vtkScene.addActor(b.actor);
                });

                if (particleBundle) {
                    vtkScene.removeActor(particleBundle.actor);
                }
                if (appState.models.openmcAnimation.showSources === '1') {
                    const particles = tallyService.getSourceParticles();
                    if (particles.length) {
                        particleBundle = coordMapper.buildVectorField(
                            particles.map(p => p.direction.map(x => p.energy * x)),
                            particles.map(p => p.position),
                            vectorScaleFactor(),
                            true,
                            appState.models.openmcAnimation.sourceColorMap,
                            {edgeVisibility: false, lighting: false}
                        );
                        vtkScene.addActor(particleBundle.actor);
                    }
                }
                vtkScene.render();
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
                if (tallyBundle) {
                    vtkScene.removeActor(tallyBundle.actor);
                    picker.deletePickList(tallyBundle.actor);
                    tallyBundle = null;
                }
                if (! tallyService.initMesh()) {
                    return;
                }
                const [nx, ny, nz] = tallyService.mesh.dimension;
                const [wx, wy, wz] = [
                    (tallyService.mesh.upper_right[0] - tallyService.mesh.lower_left[0]) / tallyService.mesh.dimension[0],
                    (tallyService.mesh.upper_right[1] - tallyService.mesh.lower_left[1]) / tallyService.mesh.dimension[1],
                    (tallyService.mesh.upper_right[2] - tallyService.mesh.lower_left[2]) / tallyService.mesh.dimension[2],
                ];
                const [sx, sy, sz] = tallyService.mesh.upper_right.map(
                    (x, i) => Math.abs(x - tallyService.mesh.lower_left[i]) / tallyService.mesh.dimension[i]
                );
                const points = [];
                const polys = [];
                renderedFieldData = [];
                const fd = tallyService.fieldData;
                if (! fd) {
                    return;
                }
                for (let zi = 0; zi < nz; zi++) {
                    for (let yi = 0; yi < ny; yi++) {
                        for (let xi = 0; xi < nx; xi++) {
                            const f = fd[zi * nx * ny + yi * nx + xi];
                            if (! isInFieldThreshold(f)) {
                                continue;
                            }
                            renderedFieldData.push(f);
                            const p = [
                                xi * wx + tallyService.mesh.lower_left[0],
                                yi * wy + tallyService.mesh.lower_left[1],
                                zi * wz + tallyService.mesh.lower_left[2],
                            ];
                            buildVoxel(p, sx, sy, sz, points, polys);
                        }
                    }
                }
                tallyPolyData.getPoints().setData(new window.Float32Array(points), 3);
                tallyPolyData.getPolys().setData(new window.Uint32Array(polys));
                tallyPolyData.buildCells();

                tallyBundle = coordMapper.buildPolyData(
                    tallyPolyData,
                    {
                        lighting: false,
                    }
                );
                vtkScene.addActor(tallyBundle.actor);
                picker.addPickList(tallyBundle.actor);
                setTallyColors();
            }

            function isInFieldThreshold(value) {
                const t = appState.models.openmcAnimation.thresholds;
                if (t[0] === 0 && value === 0) {
                    return false;
                }
                return value <= t[1] && value >= t[0];
            }

            function scoreUnits() {
                return SIREPO.APP_SCHEMA.constants.scoreUnits[appState.models.openmcAnimation.score] || '';
            }

            function setTallyColors() {
                const cellsPerVoxel = voxelPoly.length;
                $scope.colorScale = tallyService.colorScale($scope.modelName);
                colorbar.element.scale($scope.colorScale);
                colorbar.element.pointer = d3.select('.colorbar').call(colorbar.element);
                const sc = [];
                const o = Math.floor(255 * appState.models.openmcAnimation.opacity);
                for (const f of tallyService.fieldData) {
                    if (! isInFieldThreshold(f)) {
                        continue;
                    }
                    const c = SIREPO.VTK.VTKUtils.colorToFloat($scope.colorScale(f)).map(v => Math.floor(255 * v));
                    c.push(o);
                    for (let j = 0; j < cellsPerVoxel; j++) {
                        sc.push(...c);
                    }
                }
                tallyBundle.setColorScalarsForCells(sc, 4);
                tallyPolyData.modified();
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
                const f = renderedFieldData[Math.floor(cid / 6)];
                $scope.$broadcast(
                    'vtk.selected',
                    info(f, picker.getMapperPosition())
                );
                colorbar.element.pointer.pointTo(f);
            }

            // ********* 3d geometry functions

            function buildAxes(actor) {
                let boundsBox = null;
                let name = null;
                if (selectedVolume) {
                    vtkScene.removeActor(axes.boxes[selectedVolume.name]);
                    delete axes.boxes[selectedVolume.name];
                    selectedVolume = null;
                }
                if (actor) {
                    const v = getVolumeByActor(actor);
                    name = v.name;
                    boundsBox = SIREPO.VTK.VTKUtils.buildBoundingBox(actor.getBounds());
                }
                else {
                    // always clear the scene box
                    name = axes.SCENE_BOX;
                    vtkScene.removeActor(axes.boxes[name]);
                    delete axes.boxes[name];
                    boundsBox = vtkScene.sceneBoundingBox();
                }
                if (! axes.boxes[name]) {
                    vtkScene.addActor(boundsBox.actor);
                }
                const bounds = boundsBox.actor.getBounds();
                axes.boxes[name] = boundsBox.actor;
                $scope.axisObj = new SIREPO.VTK.ViewPortBox(boundsBox.source, vtkScene.renderer);

                SIREPO.GEOMETRY.GeometryUtils.BASIS().forEach((dim, i) => {
                    $scope.axisCfg[dim].max = bounds[2 * i + 1];
                    $scope.axisCfg[dim].min = bounds[2 * i];
                });
            }

            function getVolumeByActor(a) {
                for (const volId in bundleByVolume) {
                    if (bundleByVolume[volId].actor === a) {
                        return openmcService.getVolumeById(volId);
                    }
                }
                return null;
            }

            function handlePick(callData) {
                function getClosestActor(pickedActors) {
                    for (const a of pickedActors) {
                        const v = getVolumeByActor(a);
                        if (v) {
                            return [a, v];
                        }
                    }
                    return [null, null];
                }

                if (vtkScene.renderer !== callData.pokedRenderer || hasTallies) {
                    return;
                }

                // regular clicks are generated when spinning the scene - we'll select/deselect with ctrl-click
                if (! callData.controlKey) {
                    return;
                }

                const pos = callData.position;
                picker.pick([pos.x, pos.y, 0.0], vtkScene.renderer);
                const [actor, v] = getClosestActor(picker.getActors());

                if (v === selectedVolume) {
                    buildAxes();
                }
                else {
                    axes.boxes[axes.SCENE_BOX].getProperty().setOpacity(0);
                    buildAxes(actor);
                    selectedVolume = v;
                }
                $scope.$apply(vtkScene.fsRenderer.resize());
            }

            function initAxes() {
                $scope.axisCfg = {};
                SIREPO.GEOMETRY.GeometryUtils.BASIS().forEach((dim, i) => {
                    $scope.axisCfg[dim] = {
                        dimLabel: dim,
                        label: dim + ' [m]',
                        numPoints: 2,
                        screenDim: dim === 'z' ? 'y' : 'x',
                        showCentral: false,
                    };
                });
            }

            function initVolume(volId, reader) {
                const v = openmcService.getVolumeById(volId);
                const a = volumeAppearance(v);
                const b = coordMapper.buildActorBundle(reader, a.actorProperties);
                bundleByVolume[volId] = b;
                vtkScene.addActor(b.actor);
                setVolumeVisible(volId, v[a.visibilityKey]);
                if (! hasTallies) {
                    picker.addPickList(b.actor);
                }
            }

            function model() {
                return appState.models[$scope.modelName];
            }

            function setGlobalProperties() {
                if (! vtkScene || ! vtkScene.renderer) {
                    return;
                }
                vtkScene.setBgColor(model().bgColor);
                updateMarker();
                for (const volId in bundleByVolume) {
                    const b = bundleByVolume[volId];
                    const a = volumeAppearance(openmcService.getVolumeById(volId));
                    b.setActorProperty(
                        'opacity',
                        a.actorProperties.opacity * model().opacity,
                    );
                    b.setActorProperty(
                        'edgeVisibility',
                        a.actorProperties.edgeVisibility
                    );
                }
                vtkScene.render();
            }

            function setVolumeVisible(volId, isVisible) {
                bundleByVolume[volId].actor.setVisibility(isVisible);
            }

            function updateMarker() {
                vtkScene.isMarkerEnabled = model().showMarker === '1';
                vtkScene.refreshMarker();
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

            function volumeAppearance(v) {
                if (hasTallies) {
                    return {
                        actorProperties: {
                            color: [0.75, 0.75, 0.75],
                            opacity: 0.1,
                            edgeVisibility: false,
                        },
                        visibilityKey: 'isVisibleWithTallies',
                    };
                }
                return {
                    actorProperties: {
                        color: v.color,
                        opacity: v.opacity,
                        edgeVisibility: model().showEdges === '1',
                    },
                    visibilityKey: 'isVisible',
                };
            }

            // the vtk teardown is handled in vtkPlotting
            $scope.destroy = () => {
                vtkScene = null;
                plotToPNG.destroyVTK($element);
            };

            $scope.init = () => {};

            $scope.resize = () => {
                //TODO(pjm): reposition camera?
            };

            $scope.sizeStyle = () => {
                if (hasTallies) {
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

            $scope.supportsColorbar = () => hasTallies;

            $scope.$on('vtk-init', (e, d) => {
                $rootScope.$broadcast('vtk.showLoader');
                colorbar.element = Colorbar()
                    .margin({top: 5, right: colorbar.THICKNESS + 20, bottom: 5, left: 0})
                    .thickness(colorbar.THICKNESS)
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
                updateMarker();

                picker = vtk.Rendering.Core.vtkCellPicker.newInstance();
                picker.setPickFromList(true);
                vtkScene.renderWindow.getInteractor().onLeftButtonPress(handlePick);
                if (hasTallies) {
                    //TODO(pjm): this should only be enabled for hover, see #6039
                    // vtkScene.renderWindow.getInteractor().onMouseMove(showFieldInfo);
                }

                const vols = openmcService.getNonGraveyardVolumes();
                vtkScene.render();
                volumeLoadingService.loadVolumes(vols, initVolume, volumesLoaded);
                if (hasTallies && tallyService.fieldData) {
                    addTally(tallyService.fieldData);
                }
                vtkScene.resetView();

                plotToPNG.initVTK($element, vtkScene.renderer);
            });

            function renderAxes() {
                buildAxes();
                vtkScene.render();
            }

            function showSources() {
                addSources();
                appState.saveQuietly($scope.modelName);
                appState.autoSave();
            }

            const updateDisplay = utilities.debounce(() => {
                // values can change before we're ready
                if (! tallyService.fieldData || ! vtkScene) {
                    return;
                }
                tallyService.updateTallyDisplay();
                setTallyColors();
                addSources();
            });

            function vectorScaleFactor() {
                return 3.5 * tallyService.getMaxMeshExtent();
            }

            $scope.$on('sr-volume-visibility-toggle', (event, volume, isVisible, doUpdate) => {
                setVolumeVisible(volume.volId, isVisible);
                if (doUpdate) {
                    renderAxes();
                }
            });

            $scope.$on('sr-volume-visibility-toggle-all', renderAxes);
            $scope.$on($scope.modelName + '.changed', setGlobalProperties);

            if (hasTallies) {
                appState.watchModelFields($scope, [
                    `${$scope.modelName}.colorMap`,
                    `${$scope.modelName}.opacity`,
                    `${$scope.modelName}.sourceColorMap`,
                ], updateDisplay, true);
                appState.watchModelFields($scope, [`${$scope.modelName}.showSources`], showSources, true);
                $scope.$watch('tallyService.fieldData', (newValue, oldValue) => {
                    if (vtkScene && newValue && newValue !== oldValue) {
                        $rootScope.$broadcast('vtk.showLoader');
                        addTally(tallyService.fieldData);
                    }
                });
            }
            else {
                $scope.$on('sr-volume-property.changed', (event, volId, prop, val) => {
                    bundleByVolume[volId].setActorProperty(prop, val);
                    vtkScene.render();
                });
            }
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

SIREPO.app.directive('volumeSelector', function(appState, openmcService, panelState, utilities, $rootScope) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div style="padding: 0.5ex 1ex; border-bottom: 1px solid #ddd;">
              <div style="display: inline-block; cursor: pointer"
                data-ng-click="toggleAllVolumes()">
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
                    data-ng-click="toggleVolume(row)">
                    <span class="glyphicon"
                      data-ng-class="row.isVisible ? 'glyphicon-check' : 'glyphicon-unchecked'"></span>
                    <b>{{ row.name }}</b>
                  </div>
                  <div style="position: absolute; top: 0px; right: 5px">
                    <button type="button" data-ng-click="editMaterial(row)"
                      class="btn btn-info btn-xs sr-hover-button">Edit</button>
                  </div>
                  <div data-ng-show="row.isVisible">
                    <div class="col-sm-3">
                      <input
                        id="volume-{{ row.name }}-color" type="color"
                        class="sr-color-button" data-ng-model="row.color" />
                    </div>
                    <div class="col-sm-9">
                      <div
                        id="volume-{{ row.name }}-opacity-range" data-slider=""
                        data-model="row" data-field="'opacity'" data-min="0" data-max="1"
                        data-steps="101" data-is-range="1"
                      </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
            $scope.allVisible = true;
            let editRowKey = null;
            let prevOffset = 0;

            const broadcastVolumePropertyChanged = utilities.debounce((idx, prop) => {
                if ($scope.rows && $scope.rows[idx]) {
                    const row = $scope.rows[idx];
                    appState.saveQuietly('volumes');
                    $rootScope.$broadcast(
                        'sr-volume-property.changed',
                        row.volId,
                        prop,
                        row[prop],
                    );
                }
            });

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
                        row.isVisibleWithTallies = false;
                    }
                    if (openmcService.isGraveyard(row)) {
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

            $scope.toggleAllVolumes = () => {
                $scope.allVisible = ! $scope.allVisible;
                openmcService.toggleAllVolumes($scope.allVisible, 'isVisible');
            };

            $scope.toggleVolume = (row) => {
                openmcService.toggleVolume(row, 'isVisible', true);
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
                if (editRowKey && name === 'material') {
                    appState.cancelChanges('volumes');
                    unloadMaterial();
                }
            });

            loadRows();

            for (const i in $scope.rows) {
                for (const p of ['color', 'opacity']) {
                    $scope.$watch(`rows[${i}].${p}`, () => broadcastVolumePropertyChanged(i, p));
                }
            }
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
                      <div style="font-size: 13px" data-label-with-tooltip="" data-label="{{ fieldInfo.label }}"
                        data-tooltip="{{ fieldInfo.tooltip }}"></div>
                      <div class="row" data-field-editor="fieldInfo.field"
                        data-field-size="12" data-model-name="'materialComponent'"
                        data-model="c" data-label-size="0"></div>
                    </div>
                  </td>
                  <td>
                    <div class="sr-button-bar-parent pull-right">
                      <div class="sr-button-bar">
                        <button type="button" data-ng-click="deleteComponent($index)"
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

            ngModel.$parsers.push(value => {
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
            ngModel.$formatters.push(value => {
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
            const TYPE_NONE = 'None';

            function setView() {
                if (type() && type() !== TYPE_NONE) {
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
                        if (newValue !== TYPE_NONE) {
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

SIREPO.app.directive('threshold', function(tallyService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            modelName: '<',
            field: '<',
        },
        template: `
            <div data-min-max="" data-model-name="modelName" data-model="model" data-field="field" data-ng-model="model[field]" data-min="tallyService.minField" data-max="tallyService.maxField"></div>
        `,
        controller: function($scope) {
            $scope.tallyService = tallyService;
        },
    };
});

SIREPO.app.directive('minMax', function(validationService) {
    return {
        require: 'ngModel',
        restrict: 'A',
        scope: {
            model: '=',
            modelName: '<',
            field: '<',
            min: '<',
            max: '<',
        },
        template: `
            <div data-ng-repeat="v in model[field] track by $index" style="display: inline-block;">
                <label style="margin-right: 1ex">{{ globalButton[$index].label }}</label>
                <button type="button" class="btn sr-button-action btn-xs" title="{{ globalButton[$index].title }}" data-ng-click="toGlobal($index)"><span class="{{ globalButton[$index].class }}"></span></button>
                <input class="form-control sr-number-list" data-string-to-number="Float" data-ng-model="model[field][$index]" style="text-align: right" required />
                <div data-ng-if="$last" class="sr-input-warning"></div>
            </div>
        `,
        controller: function($scope) {
            $scope.toGlobal = (index) => {
                $scope.model[$scope.field][index] = index ? $scope.max : $scope.min;
            };

            $scope.globalButton = [
                {
                    label: "Lower",
                    title: "Set to global minimum",
                    class: 'glyphicon glyphicon-step-backward',
                },
                {
                    label: "Upper",
                    title: "Set to global maximum",
                    class: 'glyphicon glyphicon-step-forward',
                },
            ];
        },
        link: function(scope, element, attr, ngModel) {
            function validate() {
                const t = scope.model[scope.field];
                if (! t) {
                    return;
                }
                const err = t.some(x => x === null || x === undefined)
                          ? 'Enter values'
                          : (t[0] === 0 && t[1] === 0)
                          ? ''
                          : t[0] >= t[1]
                          ? 'Lower limit must be less than upper limit'
                          : '';
                ngModel.$setValidity('', validationService.validateField(
                    scope.modelName,
                    scope.field,
                    'input',
                    !err,
                    err,
                ));
            }
            scope.$watch('model[field]', validate, true);
        }
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
              <button type="button" class="btn btn-xs btn-info pull-right"
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
                      <button type="button" class="btn btn-xs btn-info" style="width: 5em"
                        data-ng-click="editItem(m)">Edit</button>
                      <button type="button" data-ng-click="removeItem(m)"
                        class="btn btn-danger btn-xs"><span
                          class="glyphicon glyphicon-remove"></span></button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
        `,
        controller: function($scope) {
            const childModel = $scope.field === 'sources' ? 'source' : 'tally';
            const infoFields = {
                box: ['lower_left', 'upper_right'],
                cartesianIndependent: SIREPO.GEOMETRY.GeometryUtils.BASIS(),
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
                if (childModel === 'source')  {
                    return m.type === 'file' && m.file
                         ? `File(filename=${m.file })`
                         : sourceInfo('SpatialDistribution', m.space);
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
                if (name === childModel) {
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

SIREPO.viewLogic('energyAnimationView', function(appState, panelState, tallyService, utilities, $rootScope, $scope) {

    const autoUpdate = utilities.debounce(() => {
        if ($scope.form.$valid) {
            appState.saveChanges(['energyAnimation']);
        }
    });

    function updateEditor() {
        SIREPO.GEOMETRY.GeometryUtils.BASIS().forEach(dim => {
            panelState.showField(
                $scope.modelName,
                dim,
                appState.models.tallyReport.selectedGeometry == '3D'
                    || (
                        appState.models.tallyReport.axis != dim
                            && tallyService.tallyRange(dim, true).steps > 1
                    ),
            );
        });
    }

    $scope.whenSelected = updateEditor;

    $scope.watchFields = [
        [
            'energyAnimation.x',
            'energyAnimation.y',
            'energyAnimation.z',
        ], autoUpdate,
        ['tallyReport.selectedGeometry'], updateEditor,
    ];

    $scope.$on('modelChanged', (e, name) => {
        if (name === $scope.modelName) {
            // update the 2d heatmap plot
            $rootScope.$broadcast('tallyReport.updateSelection', tallyService.getEnergyReportCoords());
        }
    });

});

SIREPO.viewLogic('settingsView', function(appState, panelState, validationService, $scope) {

    function updateEditor() {
        const m = appState.models[$scope.modelName];
        const isRunModeEigenvalue = m.run_mode === 'eigenvalue';

        function activeBatches() {
            return m.batches - (isRunModeEigenvalue ? m.inactive : 0);
        }

        panelState.showFields('reflectivePlanes', [
            ['planesList'],
            appState.models.reflectivePlanes.useReflectivePlanes === '1',
        ]);

        //TODO(pjm): consider adding panelState.showLeadText()
        if (appState.models.reflectivePlanes.useReflectivePlanes === '1') {
            $('#sr-settings-basicEditor').find('.lead').show();
        }
        else {
            $('#sr-settings-basicEditor').find('.lead').hide();
        }

        panelState.showFields(
            $scope.modelName,
            [
                ['inactive'], isRunModeEigenvalue,
            ],
        );
        panelState.showFields('survivalBiasing', [
            ['weight', 'weight_avg'], m.varianceReduction == 'survival_biasing',
        ]);
        panelState.showFields('weightWindows', [
            ['tally', 'iterations', 'particles'], m.varianceReduction == 'weight_windows_tally',
            ['particle'], ['weight_windows_tally', 'weight_windows_mesh'].includes(m.varianceReduction),
        ]);
        panelState.showFields('weightWindowsMesh', [
            ['dimension', 'lower_left', 'upper_right'], m.varianceReduction == 'weight_windows_mesh',
        ]);
        panelState.showFields('settings', [
            ['max_splits'], ['weight_windows_tally', 'weight_windows_mesh'].includes(m.varianceReduction),
        ]);
        validationService.validateField(
            $scope.modelName,
            'batches',
            'input',
            activeBatches() > 0,
            `Must have at least one active batch (currently ${activeBatches()})`
        );
    }

    $scope.whenSelected = updateEditor;

    $scope.watchFields = [
        [
            `${$scope.modelName}.run_mode`,
            `${$scope.modelName}.batches`,
            `${$scope.modelName}.inactive`,
            `${$scope.modelName}.varianceReduction`,
            'reflectivePlanes.useReflectivePlanes'
        ], updateEditor,
    ];

});

SIREPO.viewLogic('sourceView', function(appState, panelState, $scope) {
    function updateEditor() {
        const isFile = appState.models[$scope.modelName].type === 'file';
        panelState.showField($scope.modelName, 'file', isFile);
        $scope.$parent.advancedFields.forEach((x, i) => {
            panelState.showTab($scope.modelName, i + 1, ! isFile || x[0] === 'Type');
        });
    }

    $scope.whenSelected = updateEditor;

    $scope.watchFields = [
        ['source.type'], updateEditor,
    ];
});

SIREPO.viewLogic('tallyView', function(appState, openmcService, panelState, validationService, $scope) {

    const ALL_TYPES = SIREPO.APP_SCHEMA.enum.TallyFilter
        .map(x => x[SIREPO.ENUM_INDEX_VALUE]);
    const inds = openmcService.FILTER_INDICES;

    const TYPE_NONE = 'None';

    function filterField(index) {
        return `${$scope.modelName}.filter${index}`;
    }

    function type(index) {
        return appState.models[$scope.modelName][`filter${index}`]._type;
    }

    function updateEditor() {
        updateAvailableFilters();
    }

    function updateAvailableFilters() {
        // can always select 'None'
        const assignedTypes = inds.map(i => type(i)).filter(x => x !== TYPE_NONE);
        // remove assigned types
        ALL_TYPES.forEach(x => {
            panelState.showEnum('filter', '_type', x, ! assignedTypes.includes(x));
        });
        // replace the type for this "instance"
        inds.forEach(i => {
            panelState.showEnum('filter', '_type', type(i), true, i - 1);
        });

    }

    function validateEnergyFilter(filter) {
        if (! filter) {
            return;
        }
        const rangeFields = ['start', 'stop'];
        if (rangeFields.map(x => filter[x]).some(x => x == null)) {
            return;
        }
        const isValid = filter.start < filter.stop;
        rangeFields.forEach(x => {
            validationService.validateField(
                'energyFilter',
                x,
                'input',
                isValid,
                'Start must be less than stop',
            );
        });
        if (isValid && filter.space === 'log' && filter.start <= 0) {
            validationService.validateField(
                'energyFilter',
                'start',
                'input',
                false,
                'Log EnergyFilters must start after zero',
            );
        }
    }

    function validateFilter(field) {
        const f = appState.models[$scope.modelName][field.split('.')[1]];
        if (f._type === 'None') {
            return;
        }
        if (f._type === 'energyFilter' || f._type === 'energyoutFilter') {
            validateEnergyFilter(f);
        }
    }

    $scope.whenSelected = updateEditor;

    $scope.watchFields = [
        inds.map(i => `${filterField(i)}._type`), updateEditor,
        inds.map(i => `${filterField(i)}`), validateFilter,
    ];
});

SIREPO.viewLogic('materialView', function(appState, panelState, $scope) {

    let name = null;

    $scope.whenSelected = () => {
        $scope.appState = appState;
        name = model().name;
    };

    function isStd() {
        return model() && model().standardType !== 'None';
    }

    function model() {
        return appState.models[$scope.modelName];
    }

    function updateMaterial() {
        if (! model()) {
            return;
        }
        if (isStd()) {
            // don't change the name as it came from the loaded volume
            appState.models[$scope.modelName] = appState.setModelDefaults({name: name}, model().standardType);
        }
    }

    // only update when the user makes a change, not on the initial model load
    $scope.$watch(`appState.models['${$scope.modelName}']['standardType']`, (newVal, oldVal) => {
        if (oldVal === undefined || oldVal === newVal) {
            return;
        }
        updateMaterial();
    });

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
                  <button type="button" data-ng-click="removeIndex($index)"
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

SIREPO.app.directive('materialList', function(appState, openmcService) {
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
                    if (openmcService.isGraveyard(volumes[k])) {
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

SIREPO.app.directive('slider', function(appState, panelState) {
    const sliderClass = 'sr-slider';
    return {
        restrict: 'A',
        scope: {
            field: '<',
            model: '=',
            min: '<',
            max: '<',
            steps: '<',
            space: '<',
            isRange: '@',
            isMulti: '@',
        },
        template: `
            <div class="${ sliderClass }" style="margin-top: 10px"></div>
            <div data-ng-show="showLabels" style="display:flex; justify-content:space-between;">
                <span>{{ formatFloat(min) }}</span>
                <span style="font-weight: bold;">{{ display(model[field]) }}</span>
                <span>{{ formatFloat(max) }}</span>
            </div>
        `,
        controller: function($scope, $element) {
            let slider = null;
            // don't show labels for simple cases, ex. opacity
            $scope.showLabels = !($scope.min === 0 && $scope.max === 1);
            function buildSlider() {
                const s = $($element).find('.' + sliderClass);
                if (! s.length) {
                    return null;
                }
                s.slider({
                    classes: {
                        'ui-slider': 'ui-widget-header',
                        'ui-slider-range': $scope.isRange ? 'sr-range-slider' : '',
                        'ui-slider-handle': $scope.isRange ? '' : 'sr-range-slider',
                    },
                    min: $scope.min,
                    max: $scope.max,
                    range: $scope.isMulti ? true : 'min',
                    slide: (e, ui) => {
                        // prevent handles from having the same value
                        if ($scope.isMulti && ui.values[0] === ui.values[1]) {
                            return false;
                        }
                        $scope.$apply(() => {
                            if ($scope.isMulti) {
                                $scope.model[$scope.field][ui.handleIndex] = ui.value;
                            }
                            else {
                                $scope.model[$scope.field] = ui.value;
                            }
                        });
                    },
                    step: ($scope.max - $scope.min) / ($scope.steps - 1),
                });
                // ensure the max is constant
                s.slider('instance').max = $scope.max;
                s.slider('option', $scope.isMulti ? 'values' : 'value', $scope.model[$scope.field]);
                slider = s;
            }

            function didChange(newValues, oldValues) {
                if (Array.isArray(newValues)) {
                    return newValues.some((x, i) => x !== oldValues[i]) && ! newValues.some(x => x == null);
                }
                return newValues != null && newValues !== oldValues;
            }

            $scope.display = (val) => {
                if (Array.isArray(val)) {
                    if ($scope.space === 'log' && $scope.min > 0) {
                        val = val.map(v =>
                            SIREPO.UTILS.linearToLog(v, $scope.min, $scope.max, $scope.steps - 1));
                    }
                    return val.map(v => $scope.formatFloat(v));
                }
                return $scope.formatFloat(val);
            };

            $scope.formatFloat = (val) => SIREPO.UTILS.formatFloat(val, 4);

            panelState.waitForUI(buildSlider);

            $scope.$watch(
                'model[field]',
                (newValue, oldValue) => {
                    if (didChange(newValue, oldValue)) {
                        slider.slider('option', $scope.isMulti ? 'values' : 'value', newValue);
                    }
                }
            );

            $scope.$on('$destroy', () => {
                if (slider) {
                    slider.slider('destroy');
                    slider = null;
                }
            });
        },
    };
});

SIREPO.app.directive('tallySettings', function(appState, openmcService) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div data-tally-volume-picker=""></div>
            <div data-advanced-editor-pane="" data-view-name="'tallySettings'" data-want-buttons="" data-field-def="basic"></div>
        `,
        controller: function($scope) {
            $scope.is2D = () => {
                return appState.models.tallyReport.selectedGeometry === '2D';
            };
        },
    };
});

SIREPO.app.directive('tallyList', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            tallyList: '=',
        },
        template: `
            <select class="form-control" data-ng-model="model[field]"
              data-ng-options="t as t for t in tallyNames"></select>
        `,
        controller: function($scope) {
            function updateNames() {
                $scope.tallyNames = $scope.tallyList.map(t => t.name, $scope.tallyList);
                if ($scope.tallyNames.length && ! $scope.tallyNames.includes($scope.model[$scope.field])) {
                    // default to first tally if the current values is invalid
                    $scope.model[$scope.field] = $scope.tallyNames[0];
                }
            }
            $scope.$watch('tallyList', updateNames);
            updateNames();
        },
    };
});

SIREPO.viewLogic('tallySettingsView', function(appState, openmcService, panelState, tallyService, utilities, $scope) {
    $scope.tallyService = tallyService;

    const autoUpdate = utilities.debounce((field) => {
        if ($scope.form.$valid) {
            //TODO(pjm): thresholds is an array and === doesn't check values
            if (field === 'openmcAnimation.thresholds') {
                if (appState.deepEquals(
                    appState.models.openmcAnimation.thresholds,
                    appState.applicationState().openmcAnimation.thresholds,
                )) {
                    return;
                }
            }
            appState.models.energyAnimation.tally = appState.models.openmcAnimation.tally;
            appState.models.energyAnimation.score = appState.models.openmcAnimation.score;
            appState.saveChanges(['openmcAnimation', 'energyAnimation']);
        }
    }, 500);

    function invalidateThreshold() {
        openmcService.invalidateRange('thresholds');
    }

    function showFields() {
        if (! appState.isLoaded()) {
            return;
        }
        const is2D = appState.models.tallyReport.selectedGeometry === '2D';
        const showSources = appState.models.openmcAnimation.showSources === '1';
        panelState.showFields('openmcAnimation', [
            'opacity', ! is2D,
        ]);

        panelState.showFields('tallyReport', [
            'axis', is2D,
            'planePos', is2D && tallyService.tallyRange(appState.models.tallyReport.axis, true).steps > 1,
        ]);

        panelState.showField('openmcAnimation', 'energyRangeSum', ! ! openmcService.findFilter('energyFilter'));
        panelState.showField('openmcAnimation', 'sourceNormalization', openmcService.canNormalizeScore(appState.models.openmcAnimation.score));
        panelState.showField('openmcAnimation', 'numSampleSourceParticles', showSources);
        panelState.showField('openmcAnimation', 'sourceColorMap', showSources && appState.models.openmcAnimation.numSampleSourceParticles);
    }

    function updateEnergyPlot() {
        appState.models.energyAnimation[appState.models.tallyReport.axis] = appState.models.tallyReport.planePos;
        appState.saveChanges('energyAnimation');
    }

    function validateTally() {
        openmcService.validateSelectedTally();
        autoUpdate();
    }

    $scope.whenSelected = showFields;

    $scope.watchFields = [
        [
            'openmcAnimation.aspect',
            'openmcAnimation.energyRangeSum',
            'openmcAnimation.numSampleSourceParticles',
            'openmcAnimation.score',
            'openmcAnimation.sourceNormalization',
            'openmcAnimation.thresholds',
        ], autoUpdate,
        ['tallyReport.planePos'], updateEnergyPlot,
        ['openmcAnimation.tally'], validateTally,
        [
            'tallyReport.selectedGeometry',
            'openmcAnimation.score',
            'openmcAnimation.showSources',
            'openmcAnimation.numSampleSourceParticles',
        ], showFields,
        [
            'openmcAnimation.tally',
            'openmcAnimation.score',
            'openmcAnimation.aspect',
            'openmcAnimation.sourceNormalization',
            'openmcAnimation.energyRangeSum',
        ], invalidateThreshold,
    ];
    $scope.$watch('tallyService.fieldData', showFields);
});

SIREPO.app.directive('energyRangeSlider', function(appState, openmcService, panelState, tallyService) {
    return {
        restrict: 'A',
        scope: {
            field: '<',
            model: '=',
        },
        template: `
          <div data-ng-if="steps">
            <div data-slider="" data-model="model" data-field="field" data-min="min" data-max="max" data-steps="steps" data-is-multi="1" data-is-range="1" data-space="space"></div>
          </div>
        `,
        controller: function($scope) {
            $scope.tallyService = tallyService;

            function updateRange() {
                const f = openmcService.findFilter('energyFilter');
                if (f) {
                    $scope.min = f.start;
                    $scope.max = f.stop;
                    $scope.steps = f.num;
                    $scope.space = f.space;
                }
            }
            updateRange();
            $scope.$watch('tallyService.fieldData', (newValue, oldValue) => {
                if (newValue !== oldValue) {
                    updateRange();
                }
            });
        },
    };
});

SIREPO.app.directive('planePositionSlider', function(appState, panelState, tallyService) {
    return {
        restrict: 'A',
        scope: {
            field: '<',
            model: '=',
            dim: '<',
        },
        template: `
          <div data-ng-if="steps">
            <div data-slider="" data-model="model" data-field="field" data-min="min" data-max="max" data-steps="steps"></div>
          </div>
        `,
        controller: function($scope) {
            $scope.tallyService = tallyService;

            function updateRange() {
                if ($scope.dim) {
                    const r = tallyService.tallyRange($scope.dim, true);
                    $scope.min = r.min;
                    $scope.max = r.max;
                    $scope.steps = r.steps;
                }
            }
            updateRange();
            $scope.$watch('tallyService.fieldData', updateRange);
        },
    };
});
