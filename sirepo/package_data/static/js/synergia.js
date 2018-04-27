'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.appLocalRoutes.lattice = '/lattice/:simulationId';

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
        });
});

SIREPO.app.controller('LatticeController', function(latticeService) {
    var self = this;
    self.latticeService = latticeService;

    self.advancedNames = ['MONITOR', 'RFCAVITY'];

    self.basicNames = [
        'DRIFT', 'SBEN', 'QUAD',
    ];

    self.elementColor = {
        QUAD: 'red',
    };

    self.elementPic = {
        bend: ['SBEN'],
        drift: ['DRIFT'],
        magnet: ['QUAD'],
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
                '</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
		//  '<div>App-specific setting item</div>',
	      '</app-settings>',
              '<app-header-right-sim-list>',
              '</app-header-right-sim-list>',
            '</div>',
	].join(''),
    };
});
