'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.SINGLE_FRAME_ANIMATION = ['beamEvolutionAnimation'];
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="LatticeBeamlineList" data-ng-class="fieldClass">',
      '<div data-lattice-beamline-list="" data-model="model" data-field="field"></div>',
    '</div>',
    '<div data-ng-switch-when="TurnCount" data-ng-class="fieldClass">',
      '<div data-turn-count-field="" field="field" data-model="model"></div>',
    '</div>',
].join('');
SIREPO.appImportText = 'Import a MAD-X or elegant Lattice';
SIREPO.FILE_UPLOAD_TYPE = {
    'bunch-particleFile': '.h5,.hdf5',
};
SIREPO.lattice = {
    elementColor: {
        QUADRUPOLE: 'red',
        SEXTUPOLE: 'lightgreen',
        VKICKER: 'blue',
        NLINSERT: 'green',
    },
    elementPic: {
        aperture: ['ECOLLIMATOR', 'RCOLLIMATOR'],
        bend: ['HKICKER', 'KICKER', 'RBEND', 'SBEND'],
        drift: ['DRIFT'],
        magnet: ['NLINSERT', 'QUADRUPOLE', 'SEXTUPOLE', 'VKICKER'],
        rf: ['RFCAVITY'],
        solenoid: ['SOLENOID'],
        watch: ['HMONITOR', 'MARKER', 'MONITOR', 'VMONITOR'],
        zeroLength: ['DIPEDGE', 'MULTIPOLE', 'NLLENS', 'SROTATION'],
    },
};

SIREPO.app.controller('LatticeController', function(latticeService) {
    var self = this;
    self.latticeService = latticeService;

    self.advancedNames = ['DIPEDGE', 'ECOLLIMATOR', 'HKICKER', 'HMONITOR', 'MARKER', 'MULTIPOLE', 'NLINSERT', 'NLLENS', 'RCOLLIMATOR', 'SEXTUPOLE', 'SOLENOID', 'SROTATION', 'VKICKER', 'VMONITOR'];

    self.basicNames = ['DRIFT', 'MONITOR', 'KICKER', 'QUADRUPOLE', 'RFCAVITY', 'SBEND'];

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[name].description;
    };
});

SIREPO.app.controller('SynergiaSourceController', function (appState, latticeService, panelState, requestSender, validationService, $scope) {
    var self = this;

    function calculateBunchParameters() {
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

    function processBeamDefinition() {
        processBunchFields();
        calculateBunchParameters();
    }

    function processBunchFields() {
        var bunch = appState.models.bunch;
        panelState.enableField('bunch', 'beta', false);
        var def = bunch.beam_definition;
        var bdv = validationService.getEnumValidator('BeamDefinition');
        ['energy', 'momentum', 'gamma'].forEach(function (f) {
            panelState.enableField('bunch', f, def === bdv.find(f));
        });
        var pv = validationService.getEnumValidator('Particle');
        ['mass', 'charge'].forEach(function(f) {
            panelState.enableField('bunch', f, bunch.particle === pv.find('other'));
        });
        var isFile = bunch.distribution == 'file';
        panelState.showRow('bunch', 'emit_x', ! isFile);
        ['rms_z', 'dpop', 'num_macro_particles', 'seed'].forEach(function(f) {
            panelState.showField('bunch', f, ! isFile);
        });
        panelState.showField('bunch', 'particleFile', isFile);
        var isLattice = bunch.distribution == 'lattice';
        ['beta_x', 'beta_y', 'alpha_x', 'alpha_y'].forEach(function(f) {
            panelState.enableField('bunch', f, ! isLattice);
            if (isLattice) {
                bunch[f] = appState.models.bunchTwiss[f];
            }
        });
        ['nonlinear_t', 'nonlinear_c', 'nonlinear_cutoff'].forEach(function(f) {
            panelState.showField('bunch', f, bunch.distribution.indexOf('nonlinear') >= 0);
        });
    }

    self.handleModalShown = function(name) {
        if (name == 'bunch') {
            processBunchFields();
        }
    };

    appState.whenModelsLoaded($scope, function() {
        processBeamDefinition();
        appState.watchModelFields($scope, ['bunch.distribution'], processBunchFields);
        appState.watchModelFields($scope, ['bunch.beam_definition', 'bunch.particle'], processBeamDefinition);
        appState.watchModelFields($scope, ['bunch.mass', 'bunch.energy', 'bunch.momentum', 'bunch.gamma'], calculateBunchParameters);
    });

    $scope.$on('bunchReport1.summaryData', function(e, info) {
        if (appState.isLoaded() && info.bunchTwiss) {
            appState.models.bunchTwiss = info.bunchTwiss;
            appState.saveChanges('bunchTwiss');
            processBunchFields();
        }
    });

    latticeService.initSourceController(self);
});

SIREPO.app.controller('VisualizationController', function (appState, frameCache, panelState, persistentSimulation, plotRangeService, $scope) {
    var self = this;
    var turnCount = 0;
    self.panelState = panelState;
    self.errorMessage = '';

    function handleStatus(data) {
        frameCache.setFrameCount(0, 'turnComparisonAnimation');
        turnCount = 0;
        self.errorMessage = data.error;
        if (data.startTime && ! data.error) {
            plotRangeService.computeFieldRanges(self, 'bunchAnimation', data.percentComplete);
            turnCount = data.turnCount;
            ['beamEvolutionAnimation', 'bunchAnimation', 'turnComparisonAnimation'].forEach(function(m) {
                appState.models[m].startTime = data.startTime;
                appState.saveQuietly(m);
                var key = m + '.frameCount';
                if (!(key in data)) {
                    key = 'frameCount';
                }
                if (m != 'turnComparisonAnimation') {
                    frameCache.setFrameCount(data[key], m);
                }
            });
            if (data.percentComplete == 100) {
                frameCache.setFrameCount(1, 'turnComparisonAnimation');
            }
        }
        frameCache.setFrameCount(data.frameCount || 0);
    }

    self.handleModalShown = function(name) {
        if (name == 'bunchAnimation') {
            plotRangeService.processPlotRange(self, name);
        }
    };

    self.hasTurnComparisonResults = function() {
        return frameCache.getFrameCount('turnComparisonAnimation') > 0;
    };

    appState.whenModelsLoaded($scope, function() {
        appState.watchModelFields($scope, ['bunchAnimation.plotRangeType'], function() {
            plotRangeService.processPlotRange(self, 'bunchAnimation');
        });
    });

    self.simState = persistentSimulation.initSimulationState($scope, 'animation', handleStatus, {
        beamEvolutionAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '2', 'y1', 'y2', 'y3', 'startTime'],
        bunchAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '2', 'x', 'y', 'histogramBins', 'plotRangeType', 'horizontalSize', 'horizontalOffset', 'verticalSize', 'verticalOffset', 'isRunning', 'startTime'],
        turnComparisonAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'y', 'turn1', 'turn2', 'startTime'],
    });

    self.simState.errorMessage = function() {
        return self.errorMessage;
    };

    self.simState.notRunningMessage = function() {
        return 'Simulation ' + self.simState.stateAsText();
    };

    self.simState.runningMessage = function() {
        if (appState.isLoaded() && turnCount) {
            return 'Simulating turn: ' + turnCount + ' / ' + appState.models.simulationSettings.turn_count;
        }
        return 'Simulation running';
    };
});

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-common-footer="nav"></div>',
            '<div data-import-dialog="" data-title="Import Synergia File" data-description="Select an MAD-X (.madx), MAD8 (.mad8), elegant (.lte) or Sirepo Export (.zip)" data-file-formats=".madx,.mad8,.lte,.zip"></div>',
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
		'<div data-ng-if="nav.isLoaded()" data-sim-sections="">',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'lattice\')}"><a data-ng-href="{{ nav.sectionURL(\'lattice\') }}"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>',
                  '<li class="sim-section" data-ng-if="latticeService.hasBeamlines()" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Bunch</a></li>',
                  '<li class="sim-section" data-ng-if="latticeService.hasBeamlines()" data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
                '</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
		//  '<div>App-specific setting item</div>',
	      '</app-settings>',
              '<app-header-right-sim-list>',
                '<ul class="nav navbar-nav sr-navbar-right">',
                  '<li><a href data-ng-click="nav.showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>',
                '</ul>',
              '</app-header-right-sim-list>',
            '</div>',
	].join(''),
        controller: function($scope) {
            $scope.latticeService = latticeService;
        },
    };
});

SIREPO.app.directive('turnCountField', function(appState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: [
            '<select class="form-control" data-ng-model="model[field]" data-ng-options="name as name for name in turnCountList()"></select>',
        ].join(''),
        controller: function($scope) {
            var turnCountList = [];
            $scope.turnCountList = function() {
                if (! appState.isLoaded() || ! $scope.model) {
                    return null;
                }
                var turnCount = appState.applicationState().simulationSettings.turn_count;
                if (turnCount == turnCount.length - 1) {
                    return turnCountList;
                }
                turnCountList.length = 0;
                for (var i = 1; i <= turnCount; i++) {
                    turnCountList.push('' + i);
                }
                return turnCountList;
            };
        },
    };
});
