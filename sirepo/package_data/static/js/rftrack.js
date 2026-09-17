'use strict';

SIREPO.app.config(function() {
    SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
    SIREPO.SINGLE_FRAME_ANIMATION = ['statAnimation', 'stat2Animation'];
    SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL = true;
    SIREPO.appFieldEditors += ``;
    SIREPO.lattice = {
        elementColor: {
        },
        elementPic: {
            bend: ['RBEND'],
            drift: ['DRIFT'],
            magnet: ['QUADRUPOLE', 'CORRECTOR'],
            rf: ['CAVITY'],
            solenoid: ['SOLENOID'],
            watch: ['SCREEN'],
        },
    };
});

SIREPO.app.factory('rftrackService', function(appState) {
    const self = {};

    self.computeModel = () => 'animation';

    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('SourceController', function(appState, latticeService, $scope) {
    const self = this;
    latticeService.initSourceController(self);
});

SIREPO.app.controller('VisualizationController', function(appState, frameCache, panelState, persistentSimulation, requestSender, $scope) {
    const self = this;
    self.simScope = $scope;
    self.errorMessage = '';

    const valueListFields = (modelName) => {
        const r = [];
        for (const [f, d] of Object.entries(SIREPO.APP_SCHEMA.model[modelName])) {
            if (d[1] === 'ValueList') {
                r.push(f);
            }
        }
        return r;
    };

    const initModel = (info, modelName) => {
        panelState.setError(info.modelKey, null);
        if (! appState.models[info.modelKey]) {
            appState.models[info.modelKey] = {};
        }
        const m = appState.setModelDefaults(appState.models[info.modelKey], modelName);
        m.valueList = {};
        for (const f of valueListFields(modelName)) {
            m[f] = m[f] || info[f];
            m.valueList[f] = info.columns;
        }
        appState.saveQuietly(info.modelKey);
    };

    const initSimState = () => {
        const s = persistentSimulation.initSimulationState(self);

        s.errorMessage = () => self.errorMessage;

        s.logFileURL = () => {
            return requestSender.formatUrl('downloadRunFile', {
                '<simulation_id>': appState.models.simulation.simulationId,
                '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                '<model>': self.simState.model,
                '<frame>': SIREPO.nonDataFileFrame,
            });
        };

        s.runningMessage = () => {
            return 'Simulation running';
        };
        return s;
    };

    const loadReports = (reports) => {
        self.outputFiles = [];
        reports.forEach((info) => {
            if (info.modelKey == 'statAnimation' || info.modelKey == 'stat2Animation') {
                initModel(info, info.modelKey);
                return;
            }
            initModel(info, 'elementAnimation');
            self.outputFiles.push({
                info: info,
                modelAccess: {
                    modelKey: info.modelKey,
                    getData: () => appState.models[info.modelKey],
                    getPlotType: () => appState.models[info.modelKey].plotType,
                },
                panelTitle: info.name,
            });
            frameCache.setFrameCount(info.frameCount, info.modelKey);
        });
    };

    self.simHandleStatus = (data) => {
        self.errorMessage = data.error;
        self.outputFiles = [];
        if (data.reports && data.reports.length) {
            loadReports(data.reports);
        }
        frameCache.setFrameCount(data.frameCount || 0);
    };

    self.simState = initSimState();
});

SIREPO.app.controller('LatticeController', function(latticeService, appState) {
    const self = this;
    self.advancedNames = SIREPO.APP_SCHEMA.constants.advancedElementNames;
    self.basicNames = SIREPO.APP_SCHEMA.constants.basicElementNames;
    self.latticeService = latticeService;

    self.titleForName = (name) => SIREPO.APP_SCHEMA.view[name].title;
});

SIREPO.app.directive('appFooter', function(rftrackService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
        `,
    };
});

SIREPO.app.directive('appHeader', function(appState, panelState) {
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('lattice')}"><a href data-ng-click="nav.openSection('lattice')"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('source')}"><a href data-ng-click="nav.openSection('source')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('visualization')}"><a href data-ng-click="nav.openSection('visualization')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
              </app-settings>
              <app-header-right-sim-list>
              </app-header-right-sim-list>
            </div>
        `,
    };
});

SIREPO.viewLogic('beamView', function(appState, panelState, $scope) {

    const updateFields = () => {
        const m = appState.models.beam;
        const isOther = m.particle === 'other';
        const isCathode = m.distributionType === 'cathode';
        panelState.showFields('beam', [
            ['mass', 'charge'], isOther,
            ['beta_x', 'alpha_x', 'emit_x', 'beta_y', 'alpha_y', 'emit_y', 'sigma_t', 'sigma_pt'], ! isCathode,
            ['sigX', 'riseTime', 'flatTopLength', 'cutoffX', 'cutoffY', 'cutoffT', 'ePhoton', 'phiEff', 'noiseReduc'], isCathode,
        ]);
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['beam.particle', 'beam.distributionType'], updateFields,
    ];
});

SIREPO.viewLogic('quadrupoleView', function(appState, panelState, $scope) {

    const updateFields = () => {
        const m = appState.models.QUADRUPOLE;
        if (! m) {
            return;
        }
        panelState.showFields('QUADRUPOLE', [
            ['gradient'], m.strengthType === 'gradient',
            ['k1'], m.strengthType === 'k1',
        ]);
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['QUADRUPOLE.strengthType'], updateFields,
    ];
});

SIREPO.viewLogic('solenoidView', function(appState, panelState, $scope) {

    const updateFields = () => {
        const m = appState.models.SOLENOID;
        if (! m) {
            return;
        }
        const isMap = m.fieldSource === 'fieldMap';
        panelState.showFields('SOLENOID', [
            ['b_field'], ! isMap,
            ['fieldMapFile', 'rescaleMode'], isMap,
            ['maxField'], isMap && m.rescaleMode === 'peak',
            ['scaleFactor'], isMap && m.rescaleMode === 'factor',
        ]);
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['SOLENOID.fieldSource', 'SOLENOID.rescaleMode'], updateFields,
    ];
});

SIREPO.viewLogic('cavityView', function(appState, panelState, $scope) {

    const updateFields = () => {
        const m = appState.models.CAVITY;
        if (! m) {
            return;
        }
        const isMap = m.fieldSource === 'fieldMap';
        panelState.showFields('CAVITY', [
            ['gradient'], ! isMap,
            ['fieldMapFile', 'rescaleMode'], isMap,
            ['maxField'], isMap && m.rescaleMode === 'peak',
            ['scaleFactor'], isMap && m.rescaleMode === 'factor',
        ]);
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['CAVITY.fieldSource', 'CAVITY.rescaleMode'], updateFields,
    ];
});

SIREPO.viewLogic('simulationSettingsView', function(appState, panelState, latticeService, $scope) {

    const beamlineHasCavity = (beamline, visited) => {
        visited = visited || {};
        if (! beamline || ! beamline.items || visited[beamline.id]) {
            return false;
        }
        visited[beamline.id] = true;
        for (const itemId of beamline.items) {
            const item = latticeService.elementForId(itemId);
            if (! item) {
                continue;
            }
            if (item._id !== undefined) {
                // element
                if (item.type === 'CAVITY') {
                    return true;
                }
            }
            else if (beamlineHasCavity(item, visited)) {
                // nested beamline
                return true;
            }
        }
        return false;
    };

    const updateFields = () => {
        const m = appState.models.simulationSettings;
        if (! m) {
            return;
        }
        panelState.showFields('simulationSettings', [
            ['scGridNx', 'scGridNy', 'scGridNz', 'scDtMm', 'scSmooth', 'scMirror'], m.spaceCharge === 'pic',
            ['autophase'], beamlineHasCavity(latticeService.getSimulationBeamline()),
            ['trackingS0', 'trackingS1'], m.autoTrackingRange === '0',
        ]);
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['simulationSettings.spaceCharge', 'simulationSettings.autoTrackingRange', 'simulation.visualizationBeamlineId'], updateFields,
    ];
});
