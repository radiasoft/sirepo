'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.appLocalRoutes.visualization = '/visualization/:simulationId';
SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
SIREPO.SINGLE_FRAME_ANIMATION = ['beamEvolutionAnimation'];
SIREPO.FILE_UPLOAD_TYPE = {
    'ring-lattice': '.tfs',
};
SIREPO.appReportTypes = [
    '<div data-ng-switch-when="rateCalculation" data-rate-calculation-panel="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
].join('');

SIREPO.app.config(function($routeProvider, localRoutesProvider) {
    if (SIREPO.IS_LOGGED_OUT) {
        return;
    }
    var localRoutes = localRoutesProvider.$get();
    $routeProvider
        .when(localRoutes.source, {
            controller: 'SourceController as source',
            templateUrl: '/static/html/jspec-source.html' + SIREPO.SOURCE_CACHE_KEY,
        })
        .when(localRoutes.visualization, {
            controller: 'VisualizationController as visualization',
            templateUrl: '/static/html/jspec-visualization.html' + SIREPO.SOURCE_CACHE_KEY,
        });
});

SIREPO.app.controller('SourceController', function(appState, panelState, $scope) {
    var self = this;

    function processElectronBeamShape() {
        var shape = appState.models.electronBeam.shape;
        ['current', 'radius'].forEach(function(f) {
            panelState.showField('electronBeam', f, shape == 'dc_uniform' || shape == 'bunched_uniform');
        });
        panelState.showField('electronBeam', 'length', shape == 'bunched_uniform');
        ['e_number', 'sigma_x', 'sigma_y', 'sigma_z'].forEach(function(f) {
            panelState.showField('electronBeam', f, shape == 'bunched_gaussian');
        });
    }

    function processIntrabeamScatteringMethod() {
        var method = appState.models.intrabeamScatteringRate.longitudinalMethod;
        panelState.showField('intrabeamScatteringRate', 'nz', method == 'nz');
        panelState.showField('intrabeamScatteringRate', 'log_c', method == 'log_c');
    }

    self.handleModalShown = function(name) {
        if (name == 'rateCalculationReport') {
            processIntrabeamScatteringMethod();
        }
    };

    appState.whenModelsLoaded($scope, function() {
        processElectronBeamShape();
        appState.watchModelFields($scope, ['electronBeam.shape'], processElectronBeamShape);
        appState.watchModelFields($scope, ['intrabeamScatteringRate.longitudinalMethod'], processIntrabeamScatteringMethod);
    });
});

SIREPO.app.controller('VisualizationController', function(appState, frameCache, panelState, persistentSimulation, $scope) {
    var self = this;
    self.settingsModel = 'simulationSettings';
    self.panelState = panelState;

    function handleStatus(data) {
        if (data.startTime && ! data.error) {
            ['beamEvolutionAnimation', 'particleAnimation'].forEach(function(m) {
                appState.models[m].startTime = data.startTime;
                appState.saveQuietly(m);
            });
            frameCache.setFrameCount(data.frameCount, 'beamEvolutionAnimation');
            frameCache.setFrameCount(data.frameCount, 'particleAnimation');
        }
        frameCache.setFrameCount(data.frameCount || 0);
    }

    self.simState = persistentSimulation.initSimulationState($scope, 'animation', handleStatus, {
        beamEvolutionAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'x', 'y1', 'y2', 'y3', 'startTime'],
        particleAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'x', 'y', 'histogramBins', 'startTime'],
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
            '<div data-import-dialog=""></div>',
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
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

SIREPO.app.directive('rateCalculationPanel', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div data-ng-if="! rates">',
              '<div class="lead">&nbsp;</div>',
            '</div>',
            '<div data-ng-if="rates">',
              '<div data-ng-repeat="rate in rates">',
                '<div class="col-sm-12">',
                  '<label>{{ rate[0] }}</label>',
                '</div>',
                '<div data-ng-repeat="value in rate[1] track by $index" class="text-right col-sm-4">{{ value }}</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var isRunning = false;

            $scope.runCalculation = function() {
                if (isRunning) {
                    return;
                }
                isRunning = true;
                $scope.rates = null;
                panelState.clear('rateCalculationReport');
                panelState.requestData('rateCalculationReport', function(data) {
                    isRunning = false;
                    $scope.rates = data.rate;
                });
            };
            $scope.$on('rateCalculationReport.changed', $scope.runCalculation);
        },
        link: function link(scope) {
            appState.whenModelsLoaded(scope, scope.runCalculation);
        },
    };
});
