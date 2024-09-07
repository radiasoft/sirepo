'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.lattice = {
        canReverseBeamline: true,
        elementColor: {
            OCTUPOLE: 'yellow',
            QUADRUPOLE: 'red',
            SEXTUPOLE: 'lightgreen',
        },
        elementPic: {
            aperture: ['APERTURE'],
            bend: ['SBEND'],
            drift: ['DRIFT'],
            magnet: ['KICKER', 'MULTIPOLE', 'QUADRUPOLE', 'SEXTUPOLE'],
            rf: ['RFCAVITY'],
            solenoid: ['SOLENOID'],
            watch: ['MONITOR'],
            zeroLength: [],
        },
    };
    SIREPO.FILE_UPLOAD_TYPE = {
        'distribution.distributionFile': '.h5',
    };
});

SIREPO.app.factory('canvasService', function(appState) {
    const self = {};
    appState.setAppService(self);
    self.computeModel = analysisModel => 'animation';
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

SIREPO.app.directive('appHeader', function(canvasService) {
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('lattice')}"><a href data-ng-click="nav.openSection('lattice')"><span class="glyphicon glyphicon-option-horizontal"></span>  Lattice</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('source')}"><a href data-ng-click="nav.openSection('source')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('comparison')}"><a href data-ng-click="nav.openSection('comparison')">Comparison</a></li>
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

SIREPO.app.controller('LatticeController', function(latticeService) {
    var self = this;
    self.latticeService = latticeService;
    self.advancedNames = [];
    self.basicNames = [
        "APERTURE",
        "DRIFT",
        "KICKER",
        "MONITOR",
        "MULTIPOLE",
        "QUADRUPOLE",
        "RFCAVITY",
        "SBEND",
        "SEXTUPOLE",
        "SOLENOID"
    ];
});

SIREPO.app.controller('SourceController', function(latticeService) {
    const self = this;
    latticeService.initSourceController(self);
});

SIREPO.app.controller('ComparisonController', function(frameCache, persistentSimulation, $scope) {
    var self = this;
    self.simScope = $scope;
    self.errorMessage = '';

    self.simHandleStatus = (data) => {
        self.errorMessage = data.error;
        frameCache.setFrameCount(data.frameCount || 0);
    };

    self.simState = persistentSimulation.initSimulationState(self);
    self.simState.errorMessage = () => self.errorMessage;
});
