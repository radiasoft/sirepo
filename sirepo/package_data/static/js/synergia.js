'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.appLocalRoutes.lattice = '/lattice/:simulationId';
SIREPO.appLocalRoutes.visualization = '/visualization/:simulationId';
SIREPO.SINGLE_FRAME_ANIMATION = ['beamEvolutionAnimation'];

SIREPO.app.config(function($routeProvider, localRoutesProvider) {
    if (SIREPO.IS_LOGGED_OUT) {
        return;
    }
    var localRoutes = localRoutesProvider.$get();
    $routeProvider
        .when(localRoutes.source, {
            controller: 'SynergiaSourceController as source',
            templateUrl: '/static/html/synergia-source.html' + SIREPO.SOURCE_CACHE_KEY,
        })
        .when(localRoutes.lattice, {
            controller: 'LatticeController as lattice',
            templateUrl: '/static/html/synergia-lattice.html' + SIREPO.SOURCE_CACHE_KEY,
        })
        .when(localRoutes.visualization, {
            controller: 'VisualizationController as visualization',
            templateUrl: '/static/html/synergia-visualization.html' + SIREPO.SOURCE_CACHE_KEY,
        });
});

SIREPO.app.controller('LatticeController', function(latticeService) {
    var self = this;
    self.latticeService = latticeService;

    self.advancedNames = [];

    self.basicNames = [
        'DRIFT', 'MONITOR', 'QUADRUPOLE', 'RFCAVITY', 'SBEND',
    ];

    self.elementColor = {
        QUADRUPOLE: 'red',
    };

    self.elementPic = {
        bend: ['SBEND'],
        drift: ['DRIFT'],
        magnet: ['QUADRUPOLE'],
        rf: ['RFCAVITY'],
        watch: ['MONITOR'],
    };

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[name].description;
    };
});

SIREPO.app.controller('SynergiaSourceController', function () {
    var self = this;
});

SIREPO.app.controller('VisualizationController', function (appState, frameCache, panelState, persistentSimulation, $scope) {
    var self = this;
    self.settingsModel = 'simulationStatus';
    self.panelState = panelState;

    function handleStatus(data) {
        if (data.startTime && ! data.error) {
            ['beamEvolutionAnimation'].forEach(function(m) {
                appState.models[m].startTime = data.startTime;
                appState.saveQuietly(m);
                frameCache.setFrameCount(data.frameCount, m);
            });
        }
        frameCache.setFrameCount(data.frameCount || 0);
    }

    self.simState = persistentSimulation.initSimulationState($scope, 'animation', handleStatus, {
        beamEvolutionAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'y1', 'y2', 'y3', 'startTime'],
    });
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
            '<div data-app-header-right="nav">',
              '<app-header-right-sim-loaded>',
		'<div data-sim-sections="">',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'lattice\')}"><a data-ng-href="{{ nav.sectionURL(\'lattice\') }}"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>',
                  '<li class="sim-section" data-ng-if="hasBeamlines()" data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
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
            $scope.hasBeamlines = function() {
                if (! $scope.nav.isLoaded()) {
                    return false;
                }
                for (var i = 0; i < appState.models.beamlines.length; i++) {
                    var beamline = appState.models.beamlines[i];
                    if (beamline.items.length > 0) {
                        return true;
                    }
                }
                return false;
            };
        },
    };
});
