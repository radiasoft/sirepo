'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.factory('raydataService', function(appState) {
    const self = {};
    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('AnalysisController', function(appState, frameCache, persistentSimulation, $scope) {
    const self = this;
    self.appState = appState;
    self.simScope = $scope;
    self.simComputeModel = 'analysisAnimation';
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
        template: [
            '<div data-common-footer="nav"></div>'
        ].join(''),
    };
});

SIREPO.app.directive('appHeader', function(appState, panelState) {
    return {
	restrict: 'A',
	scope: {
            nav: '=appHeader',
	},
        template: [
            '<div data-app-header-brand="nav"></div>',
            '<div data-app-header-left="nav"></div>',
            '<div data-app-header-right="nav"></div>',
	].join(''),
    };
});
