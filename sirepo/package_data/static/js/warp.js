'use strict';

app_local_routes.dynamics = '/dynamics/:simulationId';

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

app.controller('WARPDynamicsController', function(appState, panelState, requestSender, frameCache, $timeout, $scope) {
    var self = this;
    self.panelState = panelState;
    self.percentComplete = 0;
    self.totalFrames = 0;
    self.isDestroyed = false;
    self.isAborting = false;
    self.dots = '.';

    frameCache.setAnimationArgs({
        fieldAnimation: ['field', 'coordinate', 'mode'],
        particleAnimation: ['x', 'y', 'histogramBins'],
    });
    frameCache.setFrameCount(0);

    $scope.$on('$destroy', function () {
        self.isDestroyed = true;
    });

    function refreshStatus() {
        requestSender.sendRequest(
            'runStatus',
            function(data) {
                frameCache.setFrameCount(data.frameCount);
                self.totalFrames = data.totalFrames;
                if (self.isAborting)
                    return;
                if (data.state != 'running') {
                    if (data.state != appState.models.simulationStatus.state)
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
                appState.models.simulationStatus.state = data.state;
            },
            {
                models: appState.applicationState(),
                simulationType: APP_SCHEMA.simulationType,
            });
    }

    self.cancelSimulation = function() {
        if (appState.models.simulationStatus.state != 'running')
            return;
        appState.models.simulationStatus.state = 'canceled';
        self.isAborting = true;
        requestSender.sendRequest(
            'runCancel',
            function(data) {
                self.isAborting = false;
                appState.saveChanges('simulationStatus');
            },
            {
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

    self.isState = function(state) {
        if (appState.isLoaded())
            return appState.models.simulationStatus.state == state;
        return false;
    };

    self.runSimulation = function() {
        if (appState.models.simulationStatus.state == 'running')
            return;
        frameCache.setFrameCount(0);
        appState.models.simulationStatus.state = 'running';
        requestSender.sendRequest(
            'runBackground',
            function(data) {
                appState.models.simulationStatus.startTime = data['startTime'];
                appState.saveChanges('simulationStatus');
                refreshStatus();
            },
            {
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

app.controller('WARPSourceController', function($scope, appState, frameCache, $timeout) {
    var self = this;
    $scope.appState = appState;
    var constants = {
        echarge: 1.602176565e-19,
        eps0: 8.85418781762e-12,
        emass: 9.10938291e-31,
        clight: 299792458.0,
        gammafrm: 1.0,
    };
    constants.betafrm = Math.sqrt(1.0 -1.0 / Math.pow(constants.gammafrm, 2));

    function clearFrames() {
        //TODO(pjm): show a warning dialog before saving model if frame count > 10
        frameCache.clearFrames();
    }

    function fieldClass(field) {
        return '.model-' + field.replace('.', '-');
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
        var laserPulse = appState.models.laserPulse;
        var lambdaLaser = laserPulse.wavelength / 1e6 * constants.gammafrm * (1.0 + constants.betafrm);
        var grid = appState.models.simulationGrid;
        grid.zCount = Math.round((grid.zMax - grid.zMin) / 1e6 * grid.zCellsPerWavelength / lambdaLaser);
        grid.rCount = Math.round((grid.rMax - grid.rMin) * grid.rCellsPerSpotSize / laserPulse.waist);
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
        var grid = appState.models.simulationGrid;
        grid.rMin = 0;
        var lambdaLaser = laserPulse.wavelength / 1e6 * constants.gammafrm * (1.0 + constants.betafrm);
        grid.zMax = (2.0 * lambdaLaser * 1e6).toFixed(12);
        // scale to laser pulse
        if (grid.gridDimensions == 's') {
            grid.rLength = (grid.rScale * laserPulse.waist).toFixed(12);
            grid.zLength = (grid.zScale * laserPulse.duration / 1e6 * 4 * constants.clight).toFixed(12);
        }
        recalcCellCount();
    }

    $scope.$watch('appState.models.laserPulse.pulseDimensions', pulseDimensionsChanged);
    $scope.$watch('appState.models.laserPulse.length', recalcValues);
    $scope.$watch('appState.models.laserPulse.spotSize', recalcValues);
    $scope.$watch('appState.models.electronPlasma.density', recalcValues);
    $scope.$watch('appState.models.simulationGrid.gridDimensions', gridDimensionsChanged);
    $scope.$watch('appState.models.simulationGrid.rScale', recalcValues);
    $scope.$watch('appState.models.simulationGrid.zScale', recalcValues);
    $scope.$watch('appState.models.simulationGrid.rCellsPerSpotSize', recalcCellCount);
    $scope.$watch('appState.models.simulationGrid.zCellsPerWavelength', recalcCellCount);
    $scope.$watch('appState.models.simulationGrid.rLength', recalcLength);
    $scope.$watch('appState.models.simulationGrid.zLength', recalcLength);
    $scope.$watch('appState.models.laserPulse.duration', recalcValues);
    $scope.$watch('appState.models.laserPulse.wavelength', recalcValues);

    $scope.$on('laserPulse.changed', clearFrames);
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
