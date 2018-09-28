'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="LatticeBeamlineList" data-ng-class="fieldClass">',
      '<div data-lattice-beamline-list="" data-model="model" data-field="field"></div>',
    '</div>',
].join('');

SIREPO.lattice = {
    reverseAngle: true,
    elementColor: {
        QUADRUPO: 'red',
    },
    elementPic: {
        aperture: [],
        bend: ['CHANGREF'],
        drift: ['DRIFT'],
        magnet: ['QUADRUPO'],
        rf: [],
        solenoid: [],
        watch: ['MARKER'],
        zeroLength: [],
    },
};

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-common-footer="nav"></div>',
        ].join(''),
    };
});

SIREPO.app.directive('appHeader', function(latticeService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: [
            '<div data-app-header-brand="nav"></div>',
            '<div data-app-header-left="nav"></div>',
            '<div data-app-header-right="nav">',
              '<app-header-right-sim-loaded>',
                '<div data-sim-sections="">',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
                  '<li class="sim-section" data-ng-if="latticeService.hasBeamlines()" data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
                '</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
                //  '<div>App-specific setting item</div>',
              '</app-settings>',
              '<app-header-right-sim-list>',
              '</app-header-right-sim-list>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.latticeService = latticeService;
        },
    };
});

SIREPO.app.controller('LatticeController', function(latticeService) {
    var self = this;
    self.latticeService = latticeService;

    self.advancedNames = [];

    self.basicNames = ['CHANGREF', 'DRIFT', 'MARKER', 'QUADRUPO'];

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[name].description;
    };
});

SIREPO.app.controller('VisualizationController', function (appState, frameCache, panelState, persistentSimulation, requestSender, $scope) {
    var self = this;
    self.settingsModel = 'simulationStatus';
    self.panelState = panelState;
    self.errorMessage = '';

    function handleStatus(data) {
        if (data.startTime && ! data.error) {
            appState.models.bunchAnimation.startTime = data.startTime;
            appState.saveQuietly('bunchAnimation');
        }
        frameCache.setFrameCount(data.frameCount || 0);
    }

    self.notRunningMessage = function() {
        return 'Simulation ' + self.simState.stateAsText();
    };

    self.startSimulation = function() {
        self.simState.saveAndRunSimulation('simulation');
    };

    self.simState = persistentSimulation.initSimulationState($scope, 'animation', handleStatus, {
        bunchAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'x', 'y', 'histogramBins', 'startTime'],
    });
});
