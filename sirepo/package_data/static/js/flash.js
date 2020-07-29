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

    self.flashTypeIn = function(types) {
        for (var i = 0; i < types.length; i++) {
            if (self.isFlashType(types[i])) {
                return true;
            }
        }
        return false;
    };

    self.isFlashType = function(simType) {
        if (appState.isLoaded()) {
            return simType == appState.models.simulation.flashType;
        }
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

SIREPO.app.controller('SourceController', function (flashService, appState, $scope, panelState) {
    var self = this;
    self.flashService = flashService;

    function fieldClass(field) {
        return '.model-' + field.replace(/:/g, '\\:');
    }

    function setReadOnly() {
        function readOnly(field) {
                $(fieldClass(field) + ' input').prop('readonly', true);
        }

        ['Wall', 'Fill'].forEach(function(x) {
            ['ion', 'rad'].forEach(function(y) {
                readOnly(self.flashService.simulationModel() +'-sim_t' + y + x);
            });
        });
        // TODO(e-carlin): If we support more than alumina for wall species
        // then we should remove this readonly or keep it and update the Z and A
        // when the species changes.
        ['A', 'Z'].forEach(function(x) {readOnly('Multispecies-ms_wall' + x);});
    }

    function makeTempsEqual(modelField) {
        var t =  modelField.includes('Fill') ? 'Fill' : 'Wall';
        var s = modelField.split('.');
        ['ion', 'rad'].forEach(function(f) {
            appState.models[self.flashService.simulationModel()]['sim_t' + f + t] = appState.models[s[0]][s[1]];
        });
    }

    function proccessCurrType(modelField) {
        function showField(field, isShown) {
            panelState.showField(s[0], field, isShown);
        }

        function showFileDialog(isShown) {
            showField('sim_currFile', isShown);
            ['sim_peakCurr', 'sim_riseTime'].forEach(function(f) {
                showField(f, !isShown);
            });
        }

        var s = modelField.split('.');
        var v = appState.models[s[0]][s[1]];
        showFileDialog(!(v === '0' || v === '1'));
    }

    appState.whenModelsLoaded($scope, function() {

        if (! self.flashService.flashTypeIn(['CapLaserBELLA', 'CapLaser3D'])) {
            return;
        }
        // Must be done on sr-tabSelected because changing tabs clears the
        // readonly prop. This puts readonly back on.
        $scope.$on('sr-tabSelected', setReadOnly);
        appState.watchModelFields(
            $scope,
            ['Wall', 'Fill'].map(
                function(x) {
                    return self.flashService.simulationModel() + '.sim_tele' + x;
                }
            ),
            makeTempsEqual
        );
        var t = self.flashService.simulationModel() + '.sim_currType';
        proccessCurrType(t);
        appState.watchModelFields($scope, [t], proccessCurrType);
    });
});

SIREPO.app.controller('VisualizationController', function (appState, flashService, frameCache, persistentSimulation, $scope, $window) {
    var self = this;
    self.scope = $scope;
    self.flashService = flashService;
    self.plotClass = 'col-md-6 col-xl-4';

    self.simHandleStatus = function(data) {
        self.errorMessage = data.error;
        if ('frameCount' in data && ! data.error) {
            ['varAnimation', 'gridEvolutionAnimation'].forEach(function(m) {
                appState.saveQuietly(m);
                frameCache.setFrameCount(data.frameCount, m);
            });
        }
        frameCache.setFrameCount(data.frameCount || 0);
    };

    self.simState = persistentSimulation.initSimulationState(self);

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
