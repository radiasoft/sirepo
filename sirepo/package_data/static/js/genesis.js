'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="Integer19StringArray" class="col-sm-7">
          <div data-number-list="" data-field="model[field]" data-info="info" data-type="Integer" data-count="19"></div>
        </div>
        <div data-ng-switch-when="MaginPlot">
            <div data-magin-file-plot="" data-model-name="maginPlotReport"></div>
        </div>
    `;
});

SIREPO.app.factory('genesisService', function(appState) {
    const self = {};
    appState.setAppService(self);
    self.computeModel = () => 'animation';
    return self;
});

SIREPO.app.controller('SourceController', function(appState, panelState, $scope) {
    const self = this;
});

SIREPO.app.controller('VisualizationController', function(appState, frameCache, genesisService, persistentSimulation, $scope) {
    const self = this;
    self.frameCache = frameCache;
    self.simScope = $scope;
    self.simComputeModel = 'animation';
    self.simHandleStatus = function (data) {
        self.errorMessage = data.error;
        if (data.reports) {
            frameCache.setFrameCount(1);
            for (const r of data.reports) {
                frameCache.setFrameCount(r.frameCount, r.modelName);
            }
        }
    };
    self.simState = persistentSimulation.initSimulationState(self);
    self.simState.errorMessage = () => self.errorMessage;
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
            <div data-import-dialog="" data-title="Import Genesis 1.3 File" data-description="Select an Genesis 1.3 (.in) or Sirepo Export (.zip)" data-file-formats=".in,.zip">
                <div data-import-options=""></div>
            </div>
        `,
    };
});

SIREPO.app.directive('maginFilePlot', function(appState, utilities) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: `
            <div data-ng-if="hasMaginfile()">
              <div data-show-loading-and-error="" data-model-key="{{ modelName }}">
                <div data-parameter-plot="parameter" data-model-name="{{ modelName }}"></div>
              </div>
            </div>
        `,
        controller: function($scope) {
            $scope.hasMaginfile = () => appState.applicationState().io.maginfile;
        }
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
                <div data-ng-if="nav.isLoaded()" data-sim-sections="">
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a data-ng-href="{{ nav.sectionURL(\'source\') }}"><span class="glyphicon glyphicon-flash"></span> Source</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-header-right-sim-list>
                <ul class="nav navbar-nav sr-navbar-right">
                  <li><a href data-ng-click="nav.showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>
                </ul>
              </app-header-right-sim-list>
            </div>
        `,
    };
});

SIREPO.viewLogic('electronBeamView', function(appState, panelState, $scope) {

    function updateOtherTab() {
        panelState.showTab('electronBeam', 5, ! appState.models.io.beamfile);
    }

    $scope.whenSelected = updateOtherTab;
    $scope.watchFields = [
        ['io.distfile'], updateOtherTab,
    ];
});

SIREPO.viewLogic('meshView', function(appState, panelState, $scope) {

    function updateSpaceCharge() {
        panelState.showFields('mesh', [
            ['nscr', 'nptr', 'rmax0sc', 'iscrkup'],
            appState.models.mesh.nscz,
        ]);
    }

    $scope.whenSelected = updateSpaceCharge;
    $scope.watchFields = [
        ['mesh.nscz'], updateSpaceCharge,
    ];
});

SIREPO.viewLogic('timeDependenceView', function(appState, panelState, $scope) {

    function updateFieldVisibility() {
        panelState.showFields('timeDependence', [
            ['curlen', 'zsep', 'nslice', 'ntail', 'shotnoise', 'isntyp'],
            appState.models.timeDependence.itdp == '1',
        ]);
    }

    $scope.whenSelected = updateFieldVisibility;
    $scope.watchFields = [
        ['timeDependence.itdp'], updateFieldVisibility,
    ];
});

SIREPO.viewLogic('simulationControlView', function(appState, panelState, $scope) {
    $scope.whenSelected = () => {
        // hide output frequency tab for time-dependence simulations
        panelState.showTab(
            'simulationControl', 2,
            appState.applicationState().timeDependence.itdp == '0',
        );
    };
});
