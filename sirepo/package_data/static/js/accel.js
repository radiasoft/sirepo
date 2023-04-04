'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.factory('accelService', function(appState) {
    const self = {};
    self.computeModel = () => 'animation';
    appState.setAppService(self);
    return self;
});


SIREPO.app.controller('accelController', function (appState, panelState, errorService, persistentSimulation, $scope, $rootScope) {
    const self = this;
    self.simScope = $scope;
    self.simHandleStatus = data => {
        if (data.epicsData) {
            if (data.epicsData.error) {
                errorService.alertText(
                    data.epicsData.error
                );
                return;
            }
            const updated = [];
            for (const f in data.epicsData) {
                let modelName, field;
                [modelName, field] = f.split(':');
                const m = appState.models[modelName];
                if (m) {
                    if (field in m) {
                        if (m[field] != data.epicsData[f]) {
                            m[field] = data.epicsData[f];
                            if (! updated.includes(modelName)) {
                                updated.push(modelName);
                            }
                        }
                    }
                }
            }
            if (updated) {
                appState.saveQuietly(updated);
                const x = appState.models.MTEST.TimeBase.slice(1);
                const y = appState.models.MTEST.Waveform.slice(1);
                $scope.$broadcast('sr-accel-waveform', [x, y]);
            }
        }
    };

    self.simState = persistentSimulation.initSimulationState(self);
});


SIREPO.app.directive('appFooter', function(accelService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
        `,
    };
});


SIREPO.app.directive('appHeader', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: `
            <div data-app-header-brand="nav"></div>
            <div data-app-header-left="nav"></div>
            <div data-app-header-right="nav">
              <app-header-right-sim-loaded>
                <div data-sim-sections="">
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
              </app-settings>
              <app-header-right-sim-list>
              </app-header-right-sim-list>
            </div>
        `,
    };
});

SIREPO.app.directive('waveformLoader', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {},
        transclude: true,
        template: `
            <div>
              <div data-ng-transclude=""></div>
            </div>
        `,
        controller: function($scope, $rootScope) {
            let plotData, plotScope;

            function updatePlot() {
                const x = plotData[0];
                const y = plotData[1];
                plotData = null;
                if (plotScope) {
                    plotScope.clearData();
                    plotScope.load({
                        x_range: [
                            Math.min(...x),
                            Math.max(...x),
                        ],
                        y_label: "",
                        x_label: "Time",
                        x_points: x,
                        plots: [
                            {
                                color: '#1f77b4',
                                points: y,
                                label: "",
                            },
                        ],
                        y_range: [
                            Math.min(...y),
                            Math.max(...y),
                        ],
                    });
                }
            }

            $scope.$on('sr-plotLinked', event => {
                plotScope = event.targetScope;
                if (plotData) {
                    updatePlot();
                }
            });
            $scope.$on('sr-accel-waveform', (event, data) => {
                plotData = data;
                if (plotScope) {
                    updatePlot();
                }
            });
        },
    };
});
