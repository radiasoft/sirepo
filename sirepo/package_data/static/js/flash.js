'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appDefaultSimulationValues.simulation.flashType = 'RTFlame';
    SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL = true;
    SIREPO.SINGLE_FRAME_ANIMATION = ['gridEvolutionAnimation'];
});

SIREPO.app.factory('flashService', function(appState) {
    var self = {};

    self.computeModel = function(analysisModel) {
        return 'animation';
    };

    self.isCapLaser = function() {
        return appState.isLoaded()
            &&  appState.models.simulation.flashType.indexOf('CapLaser') >= 0;
    };

    self.isFlashType = function(simType) {
        return appState.isLoaded()
            && simType == appState.models.simulation.flashType;
    };

    self.simulationModel = function() {
        return 'Simulation' + appState.models.simulation.flashType;
    };

    appState.setAppService(self);

    return self;
});


SIREPO.app.controller('PhysicsController', function (flashService) {
    var self = this;
    self.flashService = flashService;
});

SIREPO.app.controller('SourceController', function (appState, flashService, panelState, $scope) {
    var self = this;
    self.flashService = flashService;

    function setReadOnly(modelName) {
        [
            'sim_tionWall', 'sim_tionFill', 'sim_tradWall', 'sim_tradFill',
        ].forEach(function(f) {
            panelState.enableField(modelName, f, false);
        });
        // TODO(e-carlin): If we support more than alumina for wall species
        // then we should remove this readonly or keep it and update the Z and A
        // when the species changes.
        ['ms_wallA', 'ms_wallZ'].forEach(function(f) {
            panelState.enableField('Multispecies', f, false);
        });
    }

    function makeTempsEqual(modelField) {
        var t = modelField.indexOf('Fill') >= 0 ? 'Fill' : 'Wall';
        var s = appState.parseModelField(modelField);
        ['ion', 'rad'].forEach(function(f) {
            appState.models[flashService.simulationModel()]['sim_t' + f + t] = appState.models[s[0]][s[1]];
        });
    }

    function processCurrType() {
        var modelName = flashService.simulationModel();

        function showField(field, isShown) {
            panelState.showField(modelName, field, isShown);
        }

        var isFile = appState.models[modelName].sim_currType === '2';
        showField('sim_currFile', isFile);
        ['sim_peakCurr', 'sim_riseTime'].forEach(function(f) {
            showField(f, !isFile);
        });
    }

    appState.whenModelsLoaded($scope, function() {
        if (! flashService.isCapLaser()) {
            return;
        }
        $scope.$on('sr-tabSelected', function(event, modelName) {
            if (['SimulationCapLaser3D', 'SimulationCapLaserBELLA'].indexOf(modelName) >= 0) {
                // Must be done on sr-tabSelected because changing tabs clears the
                // readonly prop. This puts readonly back on.
                setReadOnly(modelName);
            }
            else if (modelName == 'Grid') {
                ['polar', 'spherical'].forEach(function(f) {
                    panelState.showEnum('Grid', 'geometry', f, ! flashService.isCapLaser());
                });
            }
        });
        appState.watchModelFields(
            $scope,
            ['Wall', 'Fill'].map(
                function(x) {
                    return flashService.simulationModel() + '.sim_tele' + x;
                }
            ),
            makeTempsEqual
        );
        processCurrType();
        appState.watchModelFields($scope, [flashService.simulationModel() + '.sim_currType'], processCurrType);
    });
});

SIREPO.app.controller('VisualizationController', function (appState, flashService, frameCache, persistentSimulation, $scope, $window) {
    var self = this;
    self.flashService = flashService;
    self.plotClass = 'col-md-6 col-xl-4';

    function handleStatus(data) {
        self.errorMessage = data.error;
        if ('frameCount' in data && ! data.error) {
            ['varAnimation', 'gridEvolutionAnimation'].forEach(function(m) {
                appState.saveQuietly(m);
                frameCache.setFrameCount(data.frameCount, m);
            });
        }
        frameCache.setFrameCount(data.frameCount || 0);
    }

    self.simState = persistentSimulation.initSimulationState(
        $scope,
        flashService.computeModel(),
        handleStatus
    );

    appState.whenModelsLoaded($scope, function() {
        $scope.$on('varAnimation.summaryData', function(e, data) {
            var newPlotClass = self.plotClass;
            if (data.aspectRatio > 2) {
                newPlotClass = 'col-md-5 col-xl-4';
            }
            else if (data.aspectRatio < 1) {
                newPlotClass = 'col-md-12 col-xl-6';
            }
            else {
                newPlotClass = 'col-md-6 col-xl-4';
            }
            if (newPlotClass != self.plotClass) {
                self.plotClass = newPlotClass;
                $($window).trigger('resize');
            }
        });
    });
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-th"></span> Source</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'physics\')}"><a href data-ng-click="nav.openSection(\'physics\')"><span class="glyphicon glyphicon-fire"></span> Physics</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'visualization\')}"><a href data-ng-click="nav.openSection(\'visualization\')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
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
