'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="Integer19StringArray" class="col-sm-7">',
          '<div data-number-list="" data-field="model[field]" data-info="info" data-type="Integer" data-count="19"></div>',
        '</div>',
    ].join('');
    SIREPO.SINGLE_FRAME_ANIMATION = ['parameterAnimation'];
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
        if (data.frameCount) {
            frameCache.setFrameCount(data.frameCount);
            frameCache.setFrameCount(data.particleFrameCount, 'particleAnimation');
            frameCache.setFrameCount(data.fieldFrameCount, 'fieldDistributionAnimation');
        }
    };
    self.simState = persistentSimulation.initSimulationState(self);
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
            <div data-import-dialog="" data-title="Import Genesis 1.3 File" data-description="Select an Genesis 1.3 (.in) or Sirepo Export (.zip)" data-file-formats=".in,.zip"></div>
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
