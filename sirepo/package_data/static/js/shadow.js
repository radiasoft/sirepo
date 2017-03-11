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

SIREPO.app.controller('ShadowBeamlineController', function (appState, beamlineService, panelState, $scope) {
    var self = this;
    self.beamlineService = beamlineService;
    self.beamlineModels = ['beamline'];
    //TODO(pjm): also KB Mirror and  Monocromator
    //self.toolbarItemNames = ['aperture', 'obstacle', 'crystal', 'grating', 'lens', 'crl', 'mirror', 'watch'];
    self.toolbarItemNames = ['aperture', 'obstacle', 'mirror', 'watch'];
    self.prepareToSave = function() {};

    function updateMirrorDimensionFields(item) {
        panelState.showField('mirror', 'fshape', item.fhit_c == '1');
        ['halfWidthX1', 'halfWidthX2', 'halfLengthY1', 'halfLengthY2'].forEach(function(f) {
            panelState.showField('mirror', f, item.fhit_c == '1' && item.fshape == '1');
        });
        ['externalOutlineMajorAxis', 'externalOutlineMinorAxis'].forEach(function(f) {
            panelState.showField('mirror', f, item.fhit_c == '1' && (item.fshape == '2' || item.fshape == '3'));
        });
        ['internalOutlineMajorAxis', 'internalOutlineMinorAxis'].forEach(function(f) {
            panelState.showField('mirror', f, item.fhit_c == '1' && item.fshape == '3');
        });
    }

    function updateMirrorTypeFields(item) {
        panelState.showTab('mirror', 2, item.fmirr == '1' || item.fmirr == '2' || item.fmirr == '3' || item.fmirr == '4' || item.fmirr == '7');
    }

    function updateMirrorSurfaceFields(item) {
        panelState.showField('mirror', 'f_default', item.f_ext == '0');
        panelState.showField('mirror', 'f_side', item.f_ext == '0' && item.fmirr == '4');
        panelState.showField('mirror', 'rmirr', item.f_ext == '1' && item.fmirr == '1');
        ['axmaj', 'axmin', 'ell_the'].forEach(function(f) {
            panelState.showField('mirror', f, item.f_ext == '1' && (item.fmirr == '2' || item.fmirr == '7'));
        });
        ['r_maj', 'r_min'].forEach(function(f) {
            panelState.showField('mirror', f, item.f_ext == '1' && item.fmirr == '3');
        });
        panelState.showField('mirror', 'param', item.f_ext == '1' && item.fmirr == '4');
        ['ssour', 'simag', 'theta'].forEach(function(f) {
            panelState.showField('mirror', f, item.f_ext == '0' && item.f_default == '0');
        });
        ['f_convex', 'fcyl'].forEach(function(f) {
            panelState.showField('mirror', f, item.fmirr == '1' || item.fmirr == '2' || item.fmirr == '4' || item.fmirr == '7');
        });
        panelState.showField('mirror', 'cil_ang', item.fcyl == '1' && (item.fmirr == '1' || item.fmirr == '2' || item.fmirr == '4' || item.fmirr == '7'));
        panelState.showField('mirror', 'f_torus', item.fmirr == '3');
    }

    self.handleModalShown = function(name) {
        if (name == 'mirror' && beamlineService.activeItem) {
            updateMirrorTypeFields(beamlineService.activeItem);
            updateMirrorDimensionFields(beamlineService.activeItem);
            updateMirrorSurfaceFields(beamlineService.activeItem);
        }
    };

    beamlineService.watchBeamlineField($scope, 'mirror', ['fmirr'], updateMirrorTypeFields);
    beamlineService.watchBeamlineField($scope, 'mirror', ['f_ext', 'f_default', 'fcyl'], updateMirrorSurfaceFields);
    beamlineService.watchBeamlineField($scope, 'mirror', ['fhit_c', 'fshape'], updateMirrorDimensionFields);
});

SIREPO.app.controller('ShadowSourceController', function(appState, panelState, shadowService, $scope) {
    var self = this;
    self.shadowService = shadowService;

    function updateRayFilterFields() {
        var hasFilter = appState.models.rayFilter.f_bound_sour == '2';
        panelState.showField('rayFilter', 'distance', hasFilter);
        panelState.showRow('rayFilter', 'x1', hasFilter);
    }

    function updateGeometricSettings() {
        var geo = appState.models.geometricSource;
        ['wxsou', 'wzsou'].forEach(function(f) {
            panelState.showField('geometricSource', f, geo.fsour == '1' || geo.fsour == '2');
        });
        ['sigmax', 'sigmaz'].forEach(function(f) {
            panelState.showField('geometricSource', f, geo.fsour == '3');
        });
        ['hdiv1', 'hdiv2', 'vdiv1', 'vdiv2'].forEach(function(f) {
            panelState.showField('sourceDivergence', f, geo.fdist == '1' || geo.fdist == '2' || geo.fdist == '3');
        });
        ['sigdix', 'sigdiz'].forEach(function(f) {
            panelState.showField('geometricSource', f, geo.fdist == '3');
        });
        ['cone_max', 'cone_min'].forEach(function(f) {
            panelState.showField('geometricSource', f, geo.fdist == '5');
        });
        panelState.showField('geometricSource', 'wysou', geo.fsource_depth == '2');
        panelState.showField('geometricSource', 'sigmay', geo.fsource_depth == '3');
        panelState.showField('geometricSource', 'singleEnergyValue', geo.f_color == '1');
        ['ph1', 'ph2'].forEach(function(f) {
            panelState.showField('geometricSource', f, geo.f_color == '3');
        });
        ['f_coher', 'pol_angle', 'pol_deg'].forEach(function(f) {
            panelState.showField('geometricSource', f, geo.f_polar == '1');
        });
    }

    function updateWigglerSettings() {
        var wiggler = appState.models.wiggler;
        panelState.showField('wiggler', 'kValue', wiggler.b_from == '0');
        panelState.showField('wiggler', 'trajFile', wiggler.b_from == '1' || wiggler.b_from == '2');
        panelState.showField('wiggler', 'per', wiggler.b_from == '0' || wiggler.b_from == '2');
        panelState.showField('wiggler', 'shift_x_value', wiggler.shift_x_flag == '5');
        panelState.showField('wiggler', 'shift_betax_value', wiggler.shift_betax_flag == '5');
    }

    self.handleModalShown = function(name) {
        if (name == 'bendingMagnet' || name == 'geometricSource' || name == 'wiggler') {
            updateRayFilterFields();
        }
        if (name == 'geometricSource') {
            updateGeometricSettings();
        }
        else if (name == 'wiggler') {
            updateWigglerSettings();
        }
    };

    self.isSource = function(name) {
        return appState.isLoaded() && appState.models.simulation.sourceType == name;
    };

    appState.watchModelFields($scope, ['rayFilter.f_bound_sour'], updateRayFilterFields);
    appState.watchModelFields($scope, ['simulation.sourceType', 'geometricSource.fsour', 'geometricSource.fdist', 'geometricSource.fsource_depth', 'geometricSource.f_color', 'geometricSource.f_polar'], updateGeometricSettings);
    appState.watchModelFields($scope, ['wiggler.b_from', 'wiggler.shift_x_flag', 'wiggler.shift_betax_flag'], updateWigglerSettings);

    appState.whenModelsLoaded($scope, function() {
        updateGeometricSettings();
    });
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
