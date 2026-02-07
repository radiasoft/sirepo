'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.factory('myappService', function(appState) {
    const self = {};
    self.computeModel = (analysisModel) => analysisModel || 'activityAnimation';
    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('MyAppSourceController', function (appState, frameCache, myappService, panelState, persistentSimulation, $scope) {
    const self = this;
    self.simScope = $scope;

    const dogDispositionChanged = () => {
        panelState.showField('dog', 'favoriteTreat', appState.models.dog.disposition == 'friendly');
    };

    self.simHandleStatus = (data) => {
        frameCache.setFrameCount(data.frameCount);
    };

    appState.whenModelsLoaded($scope, () => {
        // after the model data is available, hide/show the
        // favoriteTreat field depending on the disposition
        dogDispositionChanged();
        appState.watchModelFields($scope, ['dog.disposition'], function() {
            // respond to changes in the disposition field value
            dogDispositionChanged();
        });
    });

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
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>
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
