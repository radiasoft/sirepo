'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="AnalysisParameter" class="col-sm-5">',
      '<div data-analysis-parameter="" data-model="model" data-field="field"></div>',
    '</div>',
    '<div data-ng-switch-when="AnalysisOptionalParameter" class="col-sm-5">',
      '<div data-analysis-parameter="" data-model="model" data-field="field" data-is-optional="true"></div>',
    '</div>',
].join('');

SIREPO.app.factory('webconService', function(appState) {
    var self = {};
    self.analysisParameters = null;

    self.setAnalysisParameters = function(columnInfo) {
        self.analysisParameters = columnInfo;
    };

    return self;
});

SIREPO.app.controller('AnalysisController', function (appState, frameCache, panelState, persistentSimulation, webconService, $scope, $timeout) {
    var self = this;

    function handleStatus(data) {
        if (appState.models.analysisData.file) {
            frameCache.setFrameCount(data.frameCount);
            if (data.columnInfo) {
                webconService.setAnalysisParameters(data.columnInfo);
            }
        }
    }

    self.hasFile = function() {
        return appState.isLoaded() && appState.applicationState().analysisData.file;
    };

    appState.whenModelsLoaded($scope, function() {
        $scope.$on('analysisData.changed', function() {
            frameCache.setFrameCount(0);
            if (appState.models.analysisData.file) {
                self.simState.saveAndRunSimulation('analysisData');
            }
        });
    });

    self.simState = persistentSimulation.initSimulationState($scope, 'animation', handleStatus, {
        analysisAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'x', 'y1', 'y2', 'y3', 'startTime'],
    });
});

SIREPO.app.directive('analysisParameter', function(webconService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            isOptional: '@',
        },
        template: [
            '<select class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in parameterValues()"></select>',
        ].join(''),
        controller: function($scope) {
            var analysisParameters, parameterValues;
            $scope.parameterValues = function() {
                if (analysisParameters == webconService.analysisParameters) {
                    return parameterValues;
                }
                analysisParameters = webconService.analysisParameters;
                parameterValues = [];
                var visited = {};
                analysisParameters.names.forEach(function(name, idx) {
                    // skip duplicate columns
                    if (! visited[name]) {
                        parameterValues.push(['' + idx, name]);
                        visited[name] = true;
                    }
                });
                parameterValues.sort(function(a, b) {
                    return a[1].localeCompare(b[1]);
                });
                if ($scope.isOptional) {
                    parameterValues.unshift(['none', 'None']);
                }
                return parameterValues;
            };
        },
    };
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'analysis\')}"><a href data-ng-click="nav.openSection(\'analysis\')"><span class="glyphicon glyphicon-tasks"></span> Analysis</a></li>',
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
