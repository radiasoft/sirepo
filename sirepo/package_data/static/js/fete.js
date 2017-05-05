'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function($routeProvider, localRoutesProvider) {
    if (SIREPO.IS_LOGGED_OUT) {
        return;
    }
    var localRoutes = localRoutesProvider.$get();
    $routeProvider
        .when(localRoutes.source, {
            controller: 'FeteSourceController as source',
            templateUrl: '/static/html/fete-source.html' + SIREPO.SOURCE_CACHE_KEY,
        });
});

SIREPO.app.controller('FeteSourceController', function (appState, frameCache, panelState, persistentSimulation, $scope) {
    var self = this;
    self.model = 'animation';
    self.simulationErrors = '';

    function updateAllFields() {
        updateBeamCurrent();
        updateBeamRadius();
        updateParticleZMin();
        updateParticlesPerStep();
    }

    function updateBeamCurrent() {
        panelState.showField('beam', 'beam_current', appState.models.beam.currentMode == '1');
    }

    function updateBeamRadius() {
        panelState.enableField('beam', 'x_radius', false);
        appState.models.beam.x_radius = appState.models.simulationGrid.channel_width / 2.0;
    }

    function updateParticleZMin() {
        var grid = appState.models.simulationGrid;
        panelState.enableField('simulationGrid', 'z_particle_min', false);
        grid.z_particle_min = grid.plate_spacing / grid.num_z / 8.0;
    }

    function updateParticlesPerStep() {
        var grid = appState.models.simulationGrid;
        panelState.enableField('simulationGrid', 'particles_per_step', false);
        grid.particles_per_step = grid.num_x * 10;
    }

    self.handleStatus = function(data) {
        self.simulationErrors = data.errors || '';
        frameCache.setFrameCount(data.frameCount);
        if (data.startTime && ! data.error) {
            ['currentAnimation', 'fieldAnimation', 'particleAnimation'].forEach(function(modelName) {
                appState.models[modelName].startTime = data.startTime;
                appState.saveQuietly(modelName);
            });
            frameCache.setFrameCount(1, 'particleAnimation');
        }
    };

    self.getFrameCount = function() {
        return frameCache.getFrameCount();
    };

    self.handleModalShown = function(name) {
        updateAllFields();
    };

    persistentSimulation.initProperties(self);
    frameCache.setAnimationArgs({
        currentAnimation: ['startTime'],
        fieldAnimation: ['field', 'startTime'],
        particleAnimation: ['renderCount', 'startTime'],
    });
    self.persistentSimulationInit($scope);
    appState.watchModelFields($scope, ['simulationGrid.num_x'], updateParticlesPerStep);
    appState.watchModelFields($scope, ['simulationGrid.plate_spacing', 'simulationGrid.num_z'], updateParticleZMin);
    appState.watchModelFields($scope, ['simulationGrid.channel_width'], updateBeamRadius);
    appState.watchModelFields($scope, ['beam.currentMode'], updateBeamCurrent);
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
              '<div class="navbar-brand"><a href data-ng-click="nav.openSection(\'simulations\')">FETE</a></div>',
            '</div>',
            '<div data-app-header-left="nav"></div>',
            '<ul class="nav navbar-nav navbar-right" data-login-menu=""></ul>',
            '<ul class="nav navbar-nav navbar-right" data-ng-show="isLoaded()">',
              '<li data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
            '</ul>',
            '<ul class="nav navbar-nav navbar-right" data-ng-show="nav.isActive(\'simulations\')">',
              '<li><a href data-ng-click="showSimulationModal()"><span class="glyphicon glyphicon-plus sr-small-icon"></span><span class="glyphicon glyphicon-file"></span> New Simulation</a></li>',
              '<li><a href data-ng-click="showNewFolderModal()"><span class="glyphicon glyphicon-plus sr-small-icon"></span><span class="glyphicon glyphicon-folder-close"></span> New Folder</a></li>',
            '</ul>',
        ].join(''),
        controller: function($scope) {
            $scope.hasLattice = function() {
                return appState.isLoaded();
            };
            $scope.isLoaded = function() {
                if ($scope.nav.isActive('simulations')) {
                    return false;
                }
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
