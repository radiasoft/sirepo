'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="Integer19StringArray" class="col-sm-7">',
          '<div data-number-list="" data-field="model[field]" data-info="info" data-type="Integer" data-count="19"></div>',
        '</div>',
    ].join('');
    SIREPO.SINGLE_FRAME_ANIMATION = ['parameterAnimation', 'particleAnimation'];
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
    self.simScope = $scope;
    self.simComputeModel = 'animation';
    self.simHandleStatus = function (data) {
        if (data.frameCount) {
            frameCache.setFrameCount(data.frameCount);
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
            </div>
        `,
    };
});
