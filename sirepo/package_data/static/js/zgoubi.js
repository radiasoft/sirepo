'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.appHomeTab = 'lattice';
SIREPO.USER_MANUAL_URL = 'https://zgoubi.sourceforge.io/ZGOUBI_DOCS/Zgoubi.pdf';
SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="LatticeBeamlineList" data-ng-class="fieldClass">',
      '<div data-lattice-beamline-list="" data-model="model" data-field="field"></div>',
    '</div>',
].join('');

SIREPO.lattice = {
    elementColor: {
        CHANGREF: 'orange',
        QUADRUPO: 'tomato',
        SEXTUPOL: 'lightgreen',
    },
    elementPic: {
        aperture: [],
        bend: ['AUTOREF', 'BEND', 'CHANGREF', 'MULTIPOL'],
        drift: ['DRIFT'],
        magnet: ['QUADRUPO', 'SEXTUPOL'],
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'lattice\')}"><a href data-ng-click="nav.openSection(\'lattice\')"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>',
                  '<li class="sim-section" data-ng-if="latticeService.hasBeamlines()" data-ng-class="{active: nav.isActive(\'source\')}"><a data-ng-href="{{ nav.sectionURL(\'source\') }}"><span class="glyphicon glyphicon-flash"></span> Bunch</a></li>',
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
    self.basicNames = ['AUTOREF', 'BEND', 'CHANGREF', 'DRIFT', 'MARKER', 'MULTIPOL', 'QUADRUPO', 'SEXTUPOL', 'YMY'];

    function computeBendAngle(bend) {
    }

    function processChangrefFormat() {
        var model = appState.models.CHANGREF;
        ['XCE', 'YCE', 'ALE'].forEach(function(f) {
            panelState.showField('CHANGREF', f, model.format == 'old');
        });
        panelState.showField('CHANGREF', 'order', model.format == 'new');
    }

    function updateElementAttributes(item) {
        if (item.type == 'BEND') {
            item.angle = 0;
            delete item.travelLength;
            item.e1 = item.W_E;
            item.e2 = item.W_S;
            var computedAngle = 2 * Math.asin((item.B1 * item.l * 100)/(2 * appState.models.bunch.rigidity));
            item.travelLength = latticeService.arcLength(computedAngle, item.l);

            if (item.KPOS == '2') {
                // misaligned
                //TODO(pjm): support misalignment YCE, ALE
            }
            else if (item.KPOS == '3') {
                if (item.ALE) {
                    item.angle = - item.ALE * 2;
                }
                else {
                    // angle computed from field, length and magnetic rigidity
                    item.angle = computedAngle;
                }
            }
        }
        else if (item.type == 'CHANGREF') {
            item.angle = 0;
            if (item.format == 'old') {
                item.angle = - item.ALE;
            }
        }
        else if (item.type == 'MULTIPOL') {
            item.color = '';
            if (item.B_2) {
                item.color = SIREPO.lattice.elementColor.QUADRUPO;
            }
            else if (item.B_3) {
                item.color = SIREPO.lattice.elementColor.SEXTUPOL;
            }
        }
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

        if (! appState.models.simulation.isInitialized) {
            appState.models.elements.map(updateElementAttributes);
            appState.models.simulation.isInitialized = true;
            appState.saveChanges(['elements', 'simulation']);
        }

        $scope.$on('modelChanged', function(e, name) {
            var m = appState.models[name];
            if (m.type) {
                updateElementAttributes(m);
            }
        });
    });
});

SIREPO.app.controller('SourceController', function(appState, latticeService, panelState, $scope) {
    var self = this;
    var TWISS_FIELDS = ['alpha_Y', 'beta_Y', 'alpha_Z', 'beta_Z', 'DY', 'DT', 'DZ', 'DP'];

    function processBunchTwiss() {
        var bunch = appState.models.bunch;
        panelState.showField('simulation', 'visualizationBeamlineId', bunch.match_twiss_parameters == '1');
        TWISS_FIELDS.forEach(function(f) {
            panelState.enableField('bunch', f, bunch.match_twiss_parameters == '0');
        });
    }

    function processParticleType() {
        var particle = appState.models.particle;
        ['M', 'Q', 'G', 'Tau'].forEach(function(f) {
            panelState.showField('particle', f, particle.particleType == 'Other');
        });
    }

    self.handleModalShown = function(name) {
        if (name == 'bunch') {
            processBunchTwiss();
            processParticleType();
        }
    };

    appState.whenModelsLoaded($scope, function() {
        appState.watchModelFields($scope, ['bunch.match_twiss_parameters'], processBunchTwiss);
        appState.watchModelFields($scope, ['particle.particleType'], processParticleType);
        processParticleType();
    });

    $scope.$on('bunchReport1.summaryData', function(e, info) {
        if (appState.isLoaded() && info.bunch) {
            var bunch = appState.models.bunch;
            if (bunch.match_twiss_parameters == '1') {
                TWISS_FIELDS.forEach(function(f) {
                    bunch[f] = info.bunch[f];
                });
                appState.saveQuietly('bunch');
            }
        }
    });

    latticeService.initSourceController(self);
});

SIREPO.app.controller('VisualizationController', function (appState, frameCache, panelState, persistentSimulation, requestSender, $rootScope, $scope) {
    var self = this;
    self.settingsModel = 'simulationStatus';
    self.panelState = panelState;
    self.errorMessage = '';

    function handleStatus(data) {
        self.errorMessage = data.error;
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
