'use strict';

SIREPO.app.config(function() {
    SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
    SIREPO.SINGLE_FRAME_ANIMATION = ['statAnimation'];
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
    var self = this;
});

SIREPO.app.controller('VisualizationController', function (appState, frameCache, impacttService, panelState, persistentSimulation, $scope) {
    const self = this;
    self.simScope = $scope;
    self.errorMessage = '';

    function cleanFilename(fn) {
        return fn.replace(/\_/g, ' ').replace(/\.(?:h5|outfn)/g, '');
    }

    function loadReports(reports) {
        self.outputFiles = [];
        reports.forEach((info) => {
            var outputFile = {
                info: info,
                reportType: 'heatmap',
                viewName: 'elementAnimation',
                filename: info.filename,
                modelAccess: {
                    modelKey: info.modelKey,
                    getData: function() {
                        return appState.models[info.modelKey];
                    },
                },
                panelTitle: cleanFilename(info.filename),
            };
            self.outputFiles.push(outputFile);
            panelState.setError(info.modelKey, null);
            if (! appState.models[info.modelKey]) {
                appState.models[info.modelKey] = {};
            }
            var m = appState.models[info.modelKey];
            appState.setModelDefaults(m, 'elementAnimation');
            appState.saveQuietly(info.modelKey);
            frameCache.setFrameCount(1, info.modelKey);
        });
    }

    self.simHandleStatus = data => {
        self.errorMessage = data.error;
        frameCache.setFrameCount(data.frameCount || 0);
        self.outputFiles = [];
        if (data.reports && data.reports.length) {
            loadReports(data.reports);
        }
    };
    self.simState = persistentSimulation.initSimulationState(self);
    self.simState.runningMessage = () => {
        if (appState.isLoaded() && self.simState.getFrameCount()) {
            return 'Completed time step: ' + self.simState.getFrameCount();
        }
        return 'Simulation running';
    };
});

SIREPO.app.controller('LatticeController', function(latticeService, appState) {
    var self = this;
    self.latticeService = latticeService;

    self.advancedNames = SIREPO.APP_SCHEMA.constants.advancedElementNames;
    self.basicNames = SIREPO.APP_SCHEMA.constants.basicElementNames;

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[name].description;
    };

});

SIREPO.app.directive('appFooter', function() {
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('visualization')}"><a href data-ng-click="nav.openSection('visualization')"><span class="glyphicon glyphicon-flash"></span> Visualization</a></li>
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

SIREPO.viewLogic('wakefieldView', function(appState, panelState, $scope) {

    function updateFields() {
        const m = appState.models.WAKEFIELD;
        if (! m) {
            return;
        }
        panelState.showFields('WAKEFIELD', [
            ['gap', 'period', 'iris_radius'], m.method === 'analytical',
            ['filename'], m.method === 'from_file',
        ]);
    }

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['WAKEFIELD.method'], updateFields,
    ];
});

SIREPO.viewLogic('beamView', function(appState, panelState, $scope) {

    function updateFields() {
        panelState.showFields('beam', [
            ['Bmass', 'Bcharge'], appState.models.beam.particle === 'other',
        ]);
    }

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['beam.particle'], updateFields,
    ];

});

SIREPO.viewLogic('distributionView', function(appState, panelState, $scope) {

    function updateFields() {
        panelState.showField('distribution', 'filename', appState.models.distribution.Flagdist === "16");
        // the other distribution fields may also apply even when "from file" is selected
    }

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['distribution.Flagdist'], updateFields,
    ];

});
