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
    '<div data-ng-switch-when="rateCalculation" data-rate-calculation-panel="" class="sr-plot"></div>',
].join('');
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="ElegantSimList" data-ng-class="fieldClass">',
      '<div data-elegant-sim-list="" data-model="model" data-field="field"></div>',
    '</div>',
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

    function processLatticeSource() {
        var latticeSource = appState.models.ring.latticeSource;
        panelState.showField('ring', 'lattice', latticeSource == 'madx');
        panelState.showField('ring', 'elegantTwiss', latticeSource == 'elegant');
        panelState.showField('ring', 'elegantSirepo', latticeSource == 'elegant-sirepo');
    }

    self.handleModalShown = function(name) {
        if (name == 'rateCalculationReport') {
            processIntrabeamScatteringMethod();
        }
    };

    appState.whenModelsLoaded($scope, function() {
        processElectronBeamShape();
        processLatticeSource();
        appState.watchModelFields($scope, ['electronBeam.shape'], processElectronBeamShape);
        appState.watchModelFields($scope, ['intrabeamScatteringRate.longitudinalMethod'], processIntrabeamScatteringMethod);
        appState.watchModelFields($scope, ['ring.latticeSource'], processLatticeSource);
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

SIREPO.app.directive('appHeader', function() {
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

SIREPO.app.directive('elegantSimList', function(appState, requestSender, $window) {
    return {
        restrict: 'A',
        template: [
            '<div style="white-space: nowrap">',
              '<select style="display: inline-block" class="form-control" data-ng-model="model[field]" data-ng-options="item.simulationId as item.name for item in simList"></select>',
              ' ',
              '<button type="button" title="View Simulation" class="btn btn-default" data-ng-click="openElegantSimulation()"><span class="glyphicon glyphicon-eye-open"></span></button>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.simList = null;
            $scope.openElegantSimulation = function() {
                if ($scope.model && $scope.model[$scope.field]) {
                    //TODO(pjm): this depends on the visualization route being present in both jspec and elegant apps
                    // need meta data for a page in another app
                    var url = '/elegant#' + requestSender.formatUrlLocal('visualization', {
                        ':simulationId': $scope.model[$scope.field],
                    });
                    $window.open(url, '_blank');
                }
            };
            appState.whenModelsLoaded($scope, function() {
                requestSender.getApplicationData(
                    {
                        method: 'get_elegant_sim_list',
                    },
                    function(data) {
                        if (appState.isLoaded() && data.simList) {
                            $scope.simList = data.simList.sort(function(a, b) {
                                return a.name.localeCompare(b.name);
                            });
                        }
                    });
            });
        },
    };
});

SIREPO.app.directive('rateCalculationPanel', function(appState, plotting) {
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
            //TODO(pjm): these should be no-op in sirepo-plotting, for text reports
            var noOp = function() {};
            $scope.clearData = noOp;
            $scope.destroy = noOp;
            $scope.init = noOp;
            $scope.resize = noOp;
            $scope.load = function(json) {
                $scope.rates = json.rate;
            };
        },
        link: function link(scope, element) {
            scope.modelName = 'rateCalculationReport';
            plotting.linkPlot(scope, element);
        },
    };
});
