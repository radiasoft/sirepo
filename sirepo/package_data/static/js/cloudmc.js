'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.controller('SourceController', function (appState, persistentSimulation, $scope) {
    const self = this;
    self.simScope = $scope;
    self.simComputeModel = 'paramakAnimation';
    self.isGeometrySelected = () => self.isParamak() || self.isDagMC();
    self.isDagMC = () => {
        const g = appState.applicationState().geometryInput;
        return g.method == 'dagmc' && g.dagmcFile;
    };
    self.isParamak = () => appState.applicationState().geometryInput.method == 'paramak';
    self.simHandleStatus = function (data) {

    };
    self.simState = persistentSimulation.initSimulationState(self);
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('source')}"><a href data-ng-click="nav.openSection('source')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>
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


SIREPO.viewLogic('geometryInputView', function(appState, panelState, $scope) {

    function processMethod() {
        panelState.showField(
            'geometryInput',
            'dagmcFile',
            appState.models.geometryInput.method == 'dagmc');
    }

    $scope.whenSelected = processMethod;
    $scope.watchFields = [
        ['geometryInput.method'], processMethod,
    ];
});
