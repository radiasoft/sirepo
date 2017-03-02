'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.appLocalRoutes.beamline = '/beamline/:simulationId';
SIREPO.PLOTTING_SUMMED_LINEOUTS = true;

SIREPO.app.config(function($routeProvider, localRoutesProvider) {
    if (SIREPO.IS_LOGGED_OUT) {
        return;
    }
    var localRoutes = localRoutesProvider.$get();
    $routeProvider
        .when(localRoutes.source, {
            controller: 'ShadowSourceController as source',
            templateUrl: '/static/html/shadow-source.html' + SIREPO.SOURCE_CACHE_KEY,
        })
        .when(localRoutes.beamline, {
            controller: 'ShadowBeamlineController as beamline',
            templateUrl: '/static/html/shadow-beamline.html' + SIREPO.SOURCE_CACHE_KEY,
        });
});

SIREPO.app.factory('shadowService', function(beamlineService) {
    var self = {};
    self.getReportTitle = beamlineService.getReportTitle;
    return self;
});

SIREPO.app.controller('ShadowBeamlineController', function (beamlineService) {
    var self = this;
    self.beamlineService = beamlineService;
    self.beamlineModels = ['beamline'];
    //TODO(pjm): also KB Mirror and  Monocromator
    //self.toolbarItemNames = ['aperture', 'obstacle', 'crystal', 'grating', 'lens', 'crl', 'mirror', 'watch'];
    self.toolbarItemNames = ['aperture', 'obstacle', 'watch'];
    self.prepareToSave = function() {};
});

SIREPO.app.controller('ShadowSourceController', function(shadowService) {
    var self = this;
    self.shadowService = shadowService;
});

SIREPO.app.directive('appHeader', function(appState, panelState) {
    return {
        restirct: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: [
            '<div class="navbar-header">',
              '<a class="navbar-brand" href="/#about"><img style="width: 40px; margin-top: -10px;" src="/static/img/radtrack.gif" alt="radiasoft"></a>',
              '<div class="navbar-brand"><a href data-ng-click="nav.openSection(\'simulations\')">SHADOW</a></div>',
            '</div>',
            '<div data-app-header-left="nav"></div>',
            '<ul class="nav navbar-nav navbar-right" data-login-menu=""></ul>',
            '<ul class="nav navbar-nav navbar-right" data-ng-show="isLoaded()">',
              '<li data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
              '<li data-ng-class="{active: nav.isActive(\'beamline\')}"><a href data-ng-click="nav.openSection(\'beamline\')"><span class="glyphicon glyphicon-option-horizontal"></span> Beamline</a></li>',
            '</ul>',
            '<ul class="nav navbar-nav navbar-right" data-ng-show="nav.isActive(\'simulations\')">',
              '<li><a href data-ng-click="showSimulationModal()"><span class="glyphicon glyphicon-plus sr-small-icon"></span><span class="glyphicon glyphicon-file"></span> New Simulation</a></li>',
              '<li><a href data-ng-click="showNewFolderModal()"><span class="glyphicon glyphicon-plus sr-small-icon"></span><span class="glyphicon glyphicon-folder-close"></span> New Folder</a></li>',
            '</ul>',
        ].join(''),
        controller: function($scope) {
            $scope.isLoaded = function() {
                if ($scope.nav.isActive('simulations'))
                    return false;
                return appState.isLoaded();
            };
            $scope.showNewFolderModal = function() {
                panelState.showModalEditor('simulationFolder');
            };
            $scope.showSimulationModal = function() {
                panelState.showModalEditor('simulation');
            };
        },
    };
});
