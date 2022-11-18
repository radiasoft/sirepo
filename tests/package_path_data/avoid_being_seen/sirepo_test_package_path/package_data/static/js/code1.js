'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appDefaultSimulationValues.simulation.elementPosition = 'absolute';
    SIREPO.lattice = {
        canReverseBeamline: true,
        elementPic: {
            solenoid: ['SOLENOID'],
        },
    };
});

SIREPO.app.factory('code1Service', function(appState, commandService, latticeService) {
    var self = {};

    self.computeModel = function(analysisModel) {
        return 'animation';
    };

    latticeService.includeCommandNames = true;
    appState.setAppService(self);

    return self;
});

SIREPO.app.controller('CommandController', function(commandService, panelState) {
    var self = this;
    self.activeTab = 'basic';
    self.basicNames = [
        'beam', 'distribution', 'fieldsolver', 'filter', 'geometry',
        'option', 'particlematterinteraction', 'select', 'track', 'wake',
    ];
    self.advancedNames = [];

    self.createElement = function(name) {
        panelState.showModalEditor(commandService.createCommand(name));
    };

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[commandService.commandModelName(name)].description;
    };
});


SIREPO.app.controller('LatticeController', function(appState, commandService, latticeService, rpnService, $scope) {
    var self = this;
    self.latticeService = latticeService;
    self.advancedNames = [
        'CCOLLIMATOR', 'CYCLOTRON', 'DEGRADER', 'FLEXIBLECOLLIMATOR',
        'HKICKER', 'KICKER', 'LOCAL_CARTESIAN_OFFSET', 'MONITOR', 'MULTIPOLE', 'MULTIPOLET',
        'OCTUPOLE', 'PROBE', 'RBEND', 'RBEND3D', 'RCOLLIMATOR', 'RINGDEFINITION', 'SBEND3D',
        'SCALINGFFAMAGNET', 'SEPTUM', 'SEXTUPOLE', 'SBEND', 'TRAVELINGWAVE',
        'TRIMCOIL', 'VARIABLE_RF_CAVITY', 'VARIABLE_RF_CAVITY_FRINGE_FIELD', 'VKICKER',
    ];
    self.basicNames = [
        'DRIFT', 'ECOLLIMATOR', 'MARKER', 'QUADRUPOLE', 'RFCAVITY', 'SOLENOID', 'SOURCE',
    ];
});

SIREPO.app.directive('appFooter', function() {
    return {
	restrict: 'A',
	scope: {
            nav: '=appFooter',
	},
        template: [
            '<div data-common-footer="nav"></div>',
            '<div data-import-dialog="" data-title="Import Code1 File" data-description="Select an Code1 .in or .madx file." data-file-formats=".in,.madx,.zip">',
            '</div>',
	].join(''),
    };
});

// must import code1Service so it registers with appState
SIREPO.app.directive('appHeader', function(appState, latticeService, code1Service, panelState) {
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'lattice\')}"><a href data-ng-click="nav.openSection(\'lattice\')"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'control\')}"><a data-ng-href="{{ nav.sectionURL(\'control\') }}"><span class="glyphicon glyphicon-list-alt"></span> Control</a></li>',
                  '<li class="sim-section" data-ng-if="hasBeamlinesAndCommands()" data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
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

            $scope.hasBeamlinesAndCommands = function() {
                if (! latticeService.hasBeamlines()) {
                    return false;
                }
                return appState.models.commands.length > 0;
            };
        },
    };
});

SIREPO.app.controller('SourceController', function(appState, commandService, latticeService, $scope) {
    var self = this;

    latticeService.initSourceController(self);
});
