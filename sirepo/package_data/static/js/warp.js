'use strict';

app_local_routes.dynamics = '/dynamics/:simulationId';
appDefaultSimulationValues = {
    simulation: {
        sourceType: 'laserPulse',
    },
};

app.config(function($routeProvider, localRoutesProvider) {
    var localRoutes = localRoutesProvider.$get();
    $routeProvider
        .when(localRoutes.source, {
            controller: 'WARPSourceController as source',
            templateUrl: '/static/html/warp-source.html?' + SIREPO_APP_VERSION,
        })
        .when(localRoutes.dynamics, {
            controller: 'WARPDynamicsController as dynamics',
            templateUrl: '/static/html/warp-dynamics.html?' + SIREPO_APP_VERSION,
        });
});

app.factory('warpService', function(appState, $rootScope) {
    var self = {};
    self.laserGridDimensions = null;
    self.beamGridDimensions = null;

    function initGridDimensions() {
        if (self.laserGridDimensions)
            return;
        self.laserGridDimensions = appState.clone(APP_SCHEMA.enum['GridDimensions']);
        self.beamGridDimensions = appState.clone(self.laserGridDimensions);
        self.laserGridDimensions.splice(2, 1);
        self.beamGridDimensions.splice(1, 1);
    }

    function isSourceType(sourceType) {
        if (appState.isLoaded())
            return appState.applicationState().simulation.sourceType == sourceType;
        return false;
    }

    self.isElectronBeam = function() {
        return isSourceType('electronBeam');
    };

    self.isLaserPulse = function() {
        return isSourceType('laserPulse');
    }

    $rootScope.$on('modelsLoaded', function() {
        initGridDimensions();
        APP_SCHEMA.enum['GridDimensions'] = self.isLaserPulse()
            ? self.laserGridDimensions
            : self.beamGridDimensions;
    });
    return self;
});

app.controller('WARPDynamicsController', function(appState, frameCache, panelState, requestSender, warpService, $scope, $timeout) {
    var self = this;
    var simulationModel = 'animation';
    self.panelState = panelState;
    self.percentComplete = 0;
    self.isDestroyed = false;
    self.isAborting = false;
    self.dots = '.';

    frameCache.setAnimationArgs(
        {
            fieldAnimation: ['field', 'coordinate', 'mode'],
            particleAnimation: ['x', 'y', 'histogramBins'],
            beamAnimation: ['x', 'y', 'histogramBins'],
        },
        simulationModel);
    frameCache.setFrameCount(0);

    $scope.$on('$destroy', function () {
        self.isDestroyed = true;
    });

    function refreshStatus() {
        requestSender.sendRequest(
            'runStatus',
            function(data) {
                frameCache.setFrameCount(data.frameCount);
                if (self.isAborting)
                    return;
                if (data.state != 'running') {
                    if (data.state != simulationState())
                        appState.saveChanges('simulationStatus');
                }
                else {
                    self.percentComplete = data.percentComplete;
                    if (! self.isDestroyed) {
                        self.dots += '.';
                        if (self.dots.length > 3)
                            self.dots = '.';
                        $timeout(refreshStatus, 2000);
                    }
                }
                setSimulationState(data.state);
            },
            {
                report: simulationModel,
                models: appState.applicationState(),
                simulationType: APP_SCHEMA.simulationType,
            });
    }

    function setSimulationState(state) {
        if (! appState.models.simulationStatus[simulationModel])
            appState.models.simulationStatus[simulationModel] = {}
        appState.models.simulationStatus[simulationModel].state = state;
    }

    function simulationState() {
        if (appState.models.simulationStatus[simulationModel])
            return appState.models.simulationStatus[simulationModel].state;
        return 'initial';
    }

    self.cancelSimulation = function() {
        if (simulationState() != 'running')
            return;
        setSimulationState('canceled');
        self.isAborting = true;
        requestSender.sendRequest(
            'runCancel',
            function(data) {
                self.isAborting = false;
                appState.saveChanges('simulationStatus');
            },
            {
                report: simulationModel,
                models: appState.applicationState(),
                simulationType: APP_SCHEMA.simulationType,
            });
    };

    self.displayPercentComplete = function() {
        if (self.percentComplete < 1)
            return 100;
        return self.percentComplete;
    };

    self.getFrameCount = function() {
        return frameCache.frameCount;
    };

    self.isInitializing = function() {
        if (self.isState('running'))
            return self.percentComplete < 1;
        return false;
    };

    self.isElectronBeam = function() {
        return warpService.isElectronBeam();
    };

    self.isState = function(state) {
        if (appState.isLoaded())
            return simulationState() == state;
        return false;
    };

    self.runSimulation = function() {
        if (simulationState() == 'running')
            return;
        frameCache.setFrameCount(0);
        setSimulationState('running');
        requestSender.sendRequest(
            'runBackground',
            function(data) {
                appState.models.simulationStatus[simulationModel].startTime = data['startTime'];
                appState.saveChanges('simulationStatus');
                refreshStatus();
            },
            {
                report: simulationModel,
                models: appState.applicationState(),
                simulationType: APP_SCHEMA.simulationType,
            });
    };

    if (appState.isLoaded())
        refreshStatus();
    else {
        $scope.$on('modelsLoaded', refreshStatus);
    }
});

app.controller('WARPSourceController', function(appState, frameCache, warpService, $scope, $timeout) {
    var self = this;
    $scope.appState = appState;
    var constants = {
        echarge: 1.602176565e-19,
        eps0: 8.85418781762e-12,
        emass: 9.10938291e-31,
        clight: 299792458.0,
    };

    function clearFrames() {
        //TODO(pjm): show a warning dialog before saving model if frame count > 10
        frameCache.clearFrames('animation');
    }

    function fieldClass(field) {
        return '.model-' + field.replace('.', '-');
    }

    function lambdaLaser() {
        return appState.models.laserPulse.wavelength / 1e6;
    }

    function lambdaPlasma() {
        return 3.34e7 / Math.sqrt(appState.models.electronPlasma.density);
    }

    function setVisibility(fields, isVisible, oldValue) {
        for (var i = 0; i < fields.length; i++) {
            var el = $(fieldClass(fields[i])).parent();
            if (isVisible) {
                if (oldValue)
                    el.slideDown()
            }
            else {
                if (oldValue)
                    el.slideUp()
                else
                    el.hide();
            }
        }
    }

    function setReadOnly(fields, isReadOnly) {
        for (var i = 0; i < fields.length; i++) {
            $(fieldClass(fields[i]) + ' input').prop('readonly', isReadOnly);
        }
    }

    function gridDimensionsChanged(newValue, oldValue) {
        if (! appState.isLoaded())
            return;
        var fields = {
            visible: ['simulationGrid.rScale', 'simulationGrid.zScale'],
            editable: ['simulationGrid.rLength', 'simulationGrid.zLength'],
        };
        var isAbsolute = appState.models.simulationGrid.gridDimensions == 'a';
        setVisibility(fields.visible, ! isAbsolute, oldValue);
        setReadOnly(fields.editable, ! isAbsolute);
        setReadOnly(['simulationGrid.rMin', 'simulationGrid.rMax', 'simulationGrid.zMin', 'simulationGrid.zMax', 'simulationGrid.rCount', 'simulationGrid.zCount'], true);
        var sourceFields = {
            laserPulse: ['simulationGrid.rCellsPerSpotSize', 'simulationGrid.zCellsPerWavelength'],
            electronBeam: ['simulationGrid.rCellResolution', 'simulationGrid.zCellResolution'],
        };
        setVisibility(sourceFields[self.isLaserPulse() ? 'laserPulse' : 'electronBeam'], true);
        setVisibility(sourceFields[self.isLaserPulse() ? 'electronBeam' : 'laserPulse'], false);
        recalcValues();
    }

    function pulseDimensionsChanged(newValue, oldValue) {
        if (! appState.isLoaded())
            return;
        var fields = {
            visible: ['laserPulse.length', 'laserPulse.spotSize'],
            editable: ['laserPulse.waist', 'laserPulse.duration'],
        };
        var isAbsolute = appState.models.laserPulse.pulseDimensions == 'a';
        setVisibility(fields.visible, ! isAbsolute, oldValue);
        setReadOnly(fields.editable, ! isAbsolute);
        recalcValues();
    }

    function recalcCellCount() {
        if (! appState.isLoaded())
            return;
        var grid = appState.models.simulationGrid;
        if (self.isLaserPulse()) {
            var laserPulse = appState.models.laserPulse;
            var lambda = lambdaLaser();
            grid.zCount = Math.round((grid.zMax - grid.zMin) / 1e6 * grid.zCellsPerWavelength / lambda);
            grid.rCount = Math.round((grid.rMax - grid.rMin) * grid.rCellsPerSpotSize / laserPulse.waist);
        }
        else {
            grid.zCount = Math.round(grid.zScale * grid.zCellResolution);
            grid.rCount = Math.round(grid.rScale * grid.rCellResolution);
        }
    }

    function recalcHistogramBins(newValue, oldValue) {
        if (! appState.isLoaded())
            return;
        if (newValue && oldValue) {
            appState.models.particleAnimation.histogramBins = newValue;
            appState.models.beamAnimation.histogramBins = Math.round(newValue * 0.6);
            appState.saveQuietly('particleAnimation');
            appState.saveQuietly('beamAnimation');
        }
    }

    function recalcLength() {
        if (! appState.isLoaded())
            return;
        var grid = appState.models.simulationGrid;
        grid.rMax = grid.rLength;
        grid.zMin = - grid.zLength;
    }

    function recalcValues() {
        if (! appState.isLoaded())
            return;
        var grid = appState.models.simulationGrid;
        if (self.isLaserPulse()) {
            var laserPulse = appState.models.laserPulse;
            var wplab = Math.sqrt(
                appState.models.electronPlasma.density
                    * Math.pow(constants.echarge, 2)
                    / (constants.eps0 * constants.emass));
            var kplab = wplab / constants.clight;
            // resonant wth plasma density
            if (laserPulse.pulseDimensions == 'r') {
                laserPulse.waist = (1e6 * laserPulse.spotSize / kplab).toFixed(12);
                laserPulse.duration = (1e12 * laserPulse.length / kplab / constants.clight).toFixed(12);
            }
            grid.rMin = 0;
            var lambda = lambdaLaser();
            grid.zMax = (2.0 * lambda * 1e6).toFixed(12);
            // scale to laser pulse
            if (grid.gridDimensions == 's') {
                grid.rLength = (grid.rScale * laserPulse.waist).toFixed(12);
                grid.zLength = (grid.zScale * laserPulse.duration / 1e6 * 4 * constants.clight).toFixed(12);
            }
        }
        else {
            var lambda = lambdaPlasma();
            grid.zMax = 0;
            if (grid.gridDimensions == 'e') {
                grid.rLength = 0.5 * grid.rScale * lambda * 1e6;
                grid.zLength = grid.zScale * lambda * 1e6;
            }
        }
        recalcLength();
        recalcCellCount();
    }

    self.isLaserPulse = function() {
        return warpService.isLaserPulse();
    };

    self.isElectronBeam = function() {
        return warpService.isElectronBeam();
    };

    $scope.$watch('appState.models.laserPulse.pulseDimensions', pulseDimensionsChanged);
    $scope.$watch('appState.models.laserPulse.length', recalcValues);
    $scope.$watch('appState.models.laserPulse.spotSize', recalcValues);
    $scope.$watch('appState.models.electronPlasma.density', recalcValues);
    $scope.$watch('appState.models.simulationGrid.gridDimensions', gridDimensionsChanged);
    $scope.$watch('appState.models.simulationGrid.rScale', recalcValues);
    $scope.$watch('appState.models.simulationGrid.zScale', recalcValues);
    $scope.$watch('appState.models.simulationGrid.rCellsPerSpotSize', recalcCellCount);
    $scope.$watch('appState.models.simulationGrid.zCellsPerWavelength', recalcCellCount);
    $scope.$watch('appState.models.simulationGrid.rCellResolution', recalcCellCount);
    $scope.$watch('appState.models.simulationGrid.zCellResolution', recalcCellCount);
    $scope.$watch('appState.models.simulationGrid.rLength', recalcLength);
    $scope.$watch('appState.models.simulationGrid.zLength', recalcLength);
    $scope.$watch('appState.models.laserPulse.duration', recalcValues);
    $scope.$watch('appState.models.laserPulse.wavelength', recalcValues);
    $scope.$watch('appState.models.simulationGrid.zCount', recalcHistogramBins);

    $scope.$on('laserPulse.changed', clearFrames);
    $scope.$on('electronBeam.changed', clearFrames);
    $scope.$on('electronPlasma.changed', clearFrames);
    $scope.$on('simulationGrid.changed', clearFrames);

    if (appState.isLoaded()) {
        if (! $(fieldClass('simulationGrid.xMin') + ' input').length) {
            $timeout(function() {
                gridDimensionsChanged();
                pulseDimensionsChanged();
            }, 100);
        }
    }

    $scope.$on(
        'laserPulse.changed',
        function() {
            appState.saveQuietly('simulationGrid');
        });
    $scope.$on(
        'electronPlasma.changed',
        function() {
            if (appState.models.laserPulse.pulseDimensions == 'r')
                appState.saveQuietly('laserPulse');
            appState.saveQuietly('simulationGrid');
        });

});

app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
        ].join(''),
    };
});

app.directive('appHeader', function(appState) {
    return {
        restirct: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: [
            '<div class="navbar-header">',
              '<a class="navbar-brand" href data-ng-click="nav.openSection(\'simulations\')"><img style="width: 40px; margin-top: -10px;" src="/static/img/radtrack.gif" alt="radiasoft"></a>',
              '<div class="navbar-brand"><a href data-ng-click="nav.openSection(\'simulations\')">WARP</a></div>',
            '</div>',
            '<div data-app-header-left="nav"></div>',
            '<ul class="nav navbar-nav navbar-right" data-ng-show="isLoaded()">',
              '<li data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
              '<li data-ng-class="{active: nav.isActive(\'dynamics\')}"><a href data-ng-click="nav.openSection(\'dynamics\')"><span class="glyphicon glyphicon-option-horizontal"></span> Dynamics</a></li>',
            '</ul>',
        ].join(''),
        controller: function($scope) {
            $scope.isLoaded = function() {
                return appState.isLoaded();
            };
        },
    };
});
