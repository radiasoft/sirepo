'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.appLocalRoutes.lattice = '/lattice/:simulationId';
SIREPO.appLocalRoutes.visualization = '/visualization/:simulationId';
SIREPO.appReportTypes = [
    '<div data-ng-switch-when="lattice" data-lattice="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
].join('');
SIREPO.appHomeTab = 'lattice';
SIREPO.SINGLE_FRAME_ANIMATION = ['beamEvolutionAnimation'];
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="LatticeBeamlineList" data-ng-class="fieldClass">',
      '<div data-lattice-beamline-list="" data-model="model" data-field="field"></div>',
    '</div>',
].join('');
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

SIREPO.app.controller('SynergiaSourceController', function (appState, panelState, requestSender, $scope) {
    var self = this;

    function processBunchFields() {
        var bunch = appState.models.bunch;
        panelState.enableField('bunch', 'beta', false);
        var def = bunch.beam_definition;
        panelState.enableField('bunch', 'energy', def == 'energy');
        panelState.enableField('bunch', 'momentum', def == 'momentum');
        panelState.enableField('bunch', 'gamma', def == 'gamma');
        ['mass', 'charge'].forEach(function(f) {
            panelState.enableField('bunch', f, bunch.particle == 'other');
        });
    }

    function processBeamDefinition() {
        processBunchFields();
        processBeamParameter();
    }

    function processBeamParameter() {
        requestSender.getApplicationData(
            {
                method: 'calculate_bunch_parameters',
                bunch: appState.clone(appState.models.bunch),
            },
            function(data) {
                if (data.bunch && appState.isLoaded()) {
                    appState.models.bunch = data.bunch;
                }
            });
    }

    function processParticle() {
        var bunch = appState.models.bunch;
        processBunchFields();
        if (bunch.particle != 'other') {
            requestSender.getApplicationData(
                {
                    method: 'get_particle_info',
                    particle: bunch.particle,
                },
                function(data) {
                    if (appState.isLoaded()) {
                        bunch.mass = data.mass;
                        bunch.charge = data.charge;
                    }
                });
        }
    }

    self.handleModalShown = function(name) {
        if (name == 'bunch') {
            processBeamDefinition();
        }
    };

    appState.whenModelsLoaded($scope, function() {
        processBeamDefinition();
        processParticle();
        appState.watchModelFields($scope, ['bunch.beam_definition'], processBeamDefinition);
        appState.watchModelFields($scope, ['bunch.particle'], processParticle);
        appState.watchModelFields($scope, ['bunch.mass', 'bunch.energy', 'bunch.momentum', 'bunch.gamma'], processBeamParameter);
    });
});

SIREPO.app.controller('VisualizationController', function (appState, frameCache, panelState, persistentSimulation, $scope) {
    var self = this;
    self.settingsModel = 'simulationStatus';
    self.panelState = panelState;
    self.errorMessage = '';

    function handleStatus(data) {
        self.errorMessage = data.error;
        if (data.startTime && ! data.error) {
            ['beamEvolutionAnimation'].forEach(function(m) {
                appState.models[m].startTime = data.startTime;
                appState.saveQuietly(m);
                frameCache.setFrameCount(data.frameCount, m);
            });
        }
        frameCache.setFrameCount(data.frameCount || 0);
    }

    self.notRunningMessage = function() {
        return 'Simulation ' + self.simState.stateAsText();
    };

    self.runningMessage = function() {
        return 'Simulation running';
    };


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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'lattice\')}"><a data-ng-href="{{ nav.sectionURL(\'lattice\') }}"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>',
                  '<li class="sim-section" data-ng-if="hasBeamlines()" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Bunch</a></li>',
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
