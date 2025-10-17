'use strict';

SIREPO.app.config(function() {
    SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
    SIREPO.SINGLE_FRAME_ANIMATION = ['statAnimation'];
    SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL = true;
    SIREPO.appFieldEditors += ``;
    SIREPO.lattice = {
        elementColor: {
        },
        elementPic: {
            drift: ['DRIFT', 'EMFIELD_CARTESIAN', 'EMFIELD_CYLINDRICAL', 'WAKEFIELD'],
            lens: ['ROTATIONALLY_SYMMETRIC_TO_3D'],
            magnet: ['QUADRUPOLE', 'DIPOLE'],
            solenoid: ['SOLENOID', 'SOLRF'],
            watch: ['WRITE_BEAM', 'WRITE_SLICE_INFO'],
            zeroLength: [
                'CHANGE_TIMESTEP',
                'OFFSET_BEAM',
                'SPACECHARGE',
                'STOP',
            ],
        },
    };
});

SIREPO.app.factory('impacttService', function(appState) {
    const self = {};

    self.computeModel = () => 'animation';

    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('SourceController', function(appState, $scope) {
    const self = this;
});

SIREPO.app.controller('VisualizationController', function(appState, frameCache, panelState, persistentSimulation, requestSender, $scope) {
    const self = this;
    self.simScope = $scope;
    self.errorMessage = '';

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
            if (appState.isLoaded() && self.simState.getFrameCount()) {
                return 'Completed time step: ' + self.simState.getFrameCount();
            }
            return 'Simulation running';
        };
        return s;
    };

    const loadReports = (reports) => {
        self.outputFiles = [];
        reports.forEach((info) => {
            if (info.modelKey == 'statAnimation') {
                initModel(info, 'statAnimation');
                return;
            }
            initModel(info, 'elementAnimation');
            self.outputFiles.push({
                info: info,
                modelAccess: {
                    modelKey: info.modelKey,
                    getData: () => appState.models[info.modelKey],
                    //getPlotType: () => appState.applicationState()[info.modelKey].plotType,
                    getPlotType: () => appState.models[info.modelKey].plotType,
                },
                panelTitle: info.name.replace('_', ' '),
            });
            frameCache.setFrameCount(info.frameCount, info.modelKey);
        });
    };

    const valueListFields = (modelName) => {
        const r = [];
        for (const [f, d] of Object.entries(SIREPO.APP_SCHEMA.model[modelName])) {
            if (d[1] === 'ValueList') {
                r.push(f);
            }
        }
        return r;
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

    self.titleForName = (name) => SIREPO.APP_SCHEMA.view[name].description;
});

SIREPO.app.directive('appFooter', function(impacttService) {
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('visualization')}"><a href data-ng-click="nav.openSection('visualization')"><span class="glyphicon glyphicon-flash"></span> Visualization</a></li>
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

SIREPO.viewLogic('wakefieldView', function(appState, panelState, $scope) {

    const updateFields = () => {
        const m = appState.models.WAKEFIELD;
        if (! m) {
            return;
        }
        panelState.showFields('WAKEFIELD', [
            ['gap', 'period', 'iris_radius'], m.method === 'analytical',
            ['filename'], m.method === 'from_file',
        ]);
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['WAKEFIELD.method'], updateFields,
    ];
});

SIREPO.viewLogic('beamView', function(appState, panelState, $scope) {

    const updateFields = () => {
        const d = appState.models.distribution.Flagdist === 'distgen_xyfile';
        panelState.showFields('beam', [
            ['Bmass', 'Bcharge'], appState.models.beam.particle === 'other',
            ['Np'], appState.models.distribution.Flagdist !== '16',
            ['particle'], ! d,
        ]);
        panelState.showFields('distgen', [
            ['xy_dist_file', 'total_charge', 'species', 'cathode_mte'], d,
        ]);
        panelState.showRow('distribution', 'sigx', ! d);
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['beam.particle', 'distribution.Flagdist'], updateFields,
    ];
});

SIREPO.viewLogic('distributionView', function(appState, panelState, $scope) {

    const updateFields = () => {
        panelState.showField('distribution', 'filename', appState.models.distribution.Flagdist === "16");
        // the other distribution fields may also apply even when "from file" is selected
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['distribution.Flagdist'], updateFields,
    ];
});
