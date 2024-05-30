'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appFieldEditors += ``;
    SIREPO.lattice = {
        elementColor: {
            MULTIPOLE: 'yellow',
            QUADRUPOLE: 'red',
            DIPOLE: 'lightgreen',
            SOLENOID: 'red',
            DRIFT: 'grey',
        },
        elementPic: {
            drift: ['DRIFT'],
            lens: ['ROTATIONALLY_SYMMETRIC_TO_3D'],
            magnet: ['MULTIPOLE', 'QUADRUPOLE', 'DIPOLE'],
            solenoid: ['SOLENOID', 'SOLENOIDRF'],
            watch: ['WRITE_BEAM'],
            zeroLength: [
                'CHANGE_TIMESTEP',
                'SPACECHARGE',
                'WAKEFIELD',
                'STOP',
            ],
        },
    };
});

SIREPO.app.factory('impacttService', function(appState) {
    const self = {};

    self.computeModel = () => 'impacttReport';

    appState.setAppService(self);
    return self;
});


SIREPO.app.controller('SourceController', function(appState, $scope) {
    var self = this;
});

SIREPO.app.controller('VisualizationController', function (appState, panelState, persistentSimulation, impacttService, $scope) {
    const self = this;
    self.simScope = $scope;

    self.simHandleStatus = data => {};
    self.simState = persistentSimulation.initSimulationState(self);
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('lattice')}"><a href data-ng-click="nav.openSection('lattice')"><span class="glyphicon glyphicon-flash"></span> Lattice</a></li>
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
