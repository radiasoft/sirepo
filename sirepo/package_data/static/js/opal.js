'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.SINGLE_FRAME_ANIMATION = ['plotAnimation'];
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="LatticeBeamlineList" data-ng-class="fieldClass">',
      '<div data-lattice-beamline-list="" data-model="model" data-field="field"></div>',
    '</div>',
].join('');
SIREPO.lattice = {
    elementColor: {
        CCOLLIMATOR: 'magenta',
    },
    elementPic: {
        alpha: [],
        aperture: ['ECOLLIMATOR', 'FLEXIBLECOLLIMATOR', 'PEPPERPOT', 'RCOLLIMATOR', 'SLIT'],
        bend: ['RBEND', 'RBEND3D', 'SBEND', 'SBEND3D', 'SEPTUM'],
        drift: ['DRIFT'],
        lens: [],
        magnet: ['CCOLLIMATOR', 'CYCLOTRON', 'CYCLOTRONVALLEY', 'DEGRADER',
                 'HKICKER', 'KICKER', 'MULTIPOLE', 'MULTIPOLET', 'MULTIPOLETCURVEDCONSTRADIUS',
                 'MULTIPOLETCURVEDVARRADIUS', 'MULTIPOLETSTRAIGHT', 'OCTUPOLE',
                 'QUADRUPOLE', 'RINGDEFINITION', 'SCALINGFFAMAGNET', 'SEXTUPOLE',
                 'SOLENOID', 'STRIPPER', 'TRIMCOIL', 'VKICKER', 'WIRE'],
        malign: [],
        mirror: [],
        rf: ['PARALLELPLATE', 'RFCAVITY', 'VARIABLE_RF_CAVITY', 'VARIABLE_RF_CAVITY_FRINGE_FIELD'],
        solenoid: [],
        undulator: [],
        watch: ['HMONITOR', 'INSTRUMENT', 'MARKER', 'MONITOR', 'PROBE', 'VMONITOR'],
        zeroLength: ['PATCH', 'SEPARATOR', 'SOURCE', 'SROT', 'TRAVELINGWAVE', 'YROT'],
    },
};

SIREPO.app.factory('opalService', function(appState) {
    var self = {};

    self.computeModel = function(analysisModel) {
        return 'animation';
    };

    appState.setAppService(self);

    return self;
});

SIREPO.app.controller('CommandController', function(appState, commandService, latticeService, panelState) {
    var self = this;
    self.activeTab = 'basic';
    self.basicNames = [
        'attlist', 'beam', 'distribution', 'eigen',
        'envelope', 'fieldsolver', 'filter', 'geometry',
        'list', 'matrix', 'micado', 'option',
        'particlematterinteraction', 'run', 'start', 'survey',
        'threadall', 'threadbpm', 'track', 'twiss',
        'twiss3', 'twisstrack', 'wake',
    ];
    self.advancedNames = [];

    self.createElement = function(name) {
        var model = {
            _id: latticeService.nextId(),
            _type: name,
        };
        appState.setModelDefaults(model, commandService.commandModelName(name));
        var modelName = commandService.commandModelName(model._type);
        appState.models[modelName] = model;
        panelState.showModalEditor(modelName);
    };

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[commandService.commandModelName(name)].description;
    };
});

// All sims:
// DRIFT, QUADRUPOLE, SEXTUPOLE, OCTUPOLE, SOLENOID, CYCLOTRON, RINGDEFINITION, RFCAVITY, MONITOR, ECOLLIMATOR, RCOLLIMATOR, FLEXIBLECOLLIMATOR, DEGRADER, HKICKER, VKICKER, KICKER

// OPAL-T
// RBEND, SBEND, RBEND3D, MULTIPOLE

// OPAL-cycle
// SBEND3D, CCOLLIMATOR, SEPTUM, PROBE, STRIPPER,

SIREPO.app.controller('LatticeController', function(appState, errorService, panelState, latticeService, $scope) {
    var self = this;
    self.latticeService = latticeService;
    self.advancedNames = [
        'CCOLLIMATOR', 'CYCLOTRON', 'CYCLOTRONVALLEY', 'DEGRADER', 'FLEXIBLECOLLIMATOR',
        'HKICKER', 'HMONITOR', 'INSTRUMENT', 'MONITOR', 'MULTIPOLE', 'MULTIPOLET',
        'MULTIPOLETCURVEDCONSTRADIUS', 'MULTIPOLETCURVEDVARRADIUS', 'MULTIPOLETSTRAIGHT',
        'OCTUPOLE', 'PARALLELPLATE', 'PATCH', 'PEPPERPOT', 'PROBE', 'RBEND', 'RBEND3D',
        'RCOLLIMATOR', 'RFCAVITY', 'RINGDEFINITION', 'SBEND3D', 'SCALINGFFAMAGNET',
        'SEPARATOR', 'SEPTUM', 'SLIT', 'SOLENOID', 'SOURCE', 'SROT', 'STRIPPER',
        'TRAVELINGWAVE', 'TRIMCOIL', 'VARIABLE_RF_CAVITY',
        'VARIABLE_RF_CAVITY_FRINGE_FIELD', 'VKICKER', 'VMONITOR', 'WIRE', 'YROT',
    ];
    self.basicNames = ['DRIFT', 'ECOLLIMATOR', 'KICKER', 'MARKER', 'QUADRUPOLE', 'SBEND', 'SEXTUPOLE'];
});

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

SIREPO.app.directive('appHeader', function(appState, latticeService, panelState) {
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
                  '<li class="sim-section" data-ng-if="latticeService.hasBeamlines()" data-ng-class="{active: nav.isActive(\'control\')}"><a data-ng-href="{{ nav.sectionURL(\'control\') }}"><span class="glyphicon glyphicon-list-alt"></span> Control</a></li>',
                  '<li class="sim-section" data-ng-if="hasBeamlinesAndCommands()" data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
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

            $scope.hasBeamlinesAndCommands = function() {
                if (! latticeService.hasBeamlines()) {
                    return false;
                }
                return appState.models.commands.length > 0;
            };
        },
    };
});

SIREPO.app.controller('VisualizationController', function (appState, frameCache, latticeService, panelState, persistentSimulation, plotRangeService, opalService, $scope) {
    var self = this;
    self.panelState = panelState;
    self.errorMessage = '';

    function handleStatus(data) {
        self.errorMessage = data.error;
        if ('percentComplete' in data && ! data.error) {
            ['bunchAnimation', 'plotAnimation'].forEach(function(m) {
                plotRangeService.computeFieldRanges(self, m, data.percentComplete);
                appState.saveQuietly(m);
            });
        }
        frameCache.setFrameCount(data.frameCount || 0);
    }

    self.simState = persistentSimulation.initSimulationState(
        $scope,
        opalService.computeModel(),
        handleStatus
    );

    self.handleModalShown = function(name) {
        if (appState.isAnimationModelName(name)) {
            plotRangeService.processPlotRange(self, name);
        }
    };

    appState.whenModelsLoaded($scope, function() {
        ['bunchAnimation'].forEach(function(m) {
            appState.watchModelFields($scope, [m + '.plotRangeType'], function() {
                plotRangeService.processPlotRange(self, m);
            });
        });
    });
});
