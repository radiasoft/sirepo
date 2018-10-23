'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.USER_MANUAL_URL = 'https://zgoubi.sourceforge.io/ZGOUBI_DOCS/Zgoubi.pdf';
SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="LatticeBeamlineList" data-ng-class="fieldClass">',
      '<div data-lattice-beamline-list="" data-model="model" data-field="field"></div>',
    '</div>',
].join('');

SIREPO.lattice = {
    reverseAngle: true,
    elementColor: {
        CHANGREF: 'orange',
        QUADRUPO: 'red',
    },
    elementPic: {
        aperture: [],
        bend: ['AUTOREF', 'BEND', 'CHANGREF', 'MULTIPOL'],
        drift: ['DRIFT'],
        magnet: ['QUADRUPO', ],
        rf: ['CAVITE'],
        solenoid: [],
        watch: ['MARKER'],
        zeroLength: ['YMY'],
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a data-ng-href="{{ nav.sectionURL(\'source\') }}"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'lattice\')}"><a href data-ng-click="nav.openSection(\'lattice\')"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>',
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

SIREPO.app.controller('LatticeController', function(appState, panelState, latticeService, $scope) {
    var self = this;
    self.latticeService = latticeService;
    self.advancedNames = [];
    self.basicNames = ['AUTOREF', 'BEND', 'CHANGREF', 'DRIFT', 'MARKER', 'MULTIPOL', 'QUADRUPO', 'YMY'];

    function processChangrefFormat() {
        var model = appState.models.CHANGREF;
        ['XCE', 'YCE', 'ALE'].forEach(function(f) {
            panelState.showField('CHANGREF', f, model.format == 'old');
        });
        panelState.showField('CHANGREF', 'order', model.format == 'new');
    }

    self.handleModalShown = function(name) {
        if (name == 'CHANGREF') {
            processChangrefFormat();
        }
    };

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[name].description;
    };

    appState.whenModelsLoaded($scope, function() {
        appState.watchModelFields($scope, ['CHANGREF.format'], processChangrefFormat);
    });
});

SIREPO.app.controller('SourceController', function() {
    var self = this;
});

SIREPO.app.controller('VisualizationController', function (appState, frameCache, panelState, persistentSimulation, requestSender, $rootScope, $scope) {
    var self = this;
    self.settingsModel = 'simulationStatus';
    self.panelState = panelState;
    self.errorMessage = '';

    function handleStatus(data) {
        if (data.startTime && ! data.error) {
            ['bunchAnimation', 'bunchAnimation2'].forEach(function(m) {
                appState.models[m].startTime = data.startTime;
                appState.saveQuietly(m);
            });
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
        bunchAnimation2: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'x', 'y', 'histogramBins', 'startTime'],
    });

    appState.whenModelsLoaded($scope, function() {
        //TODO(pjm): need to work this into sirepo-lattice.js
        $scope.$on('simulation.changed', function(e, name) {
            $rootScope.$broadcast('activeBeamlineChanged');
        });
    });
});
