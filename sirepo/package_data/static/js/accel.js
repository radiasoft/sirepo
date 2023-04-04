'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="EpicsFloat">
          <div class="col-sm-3">
            <input data-string-to-number="" data-ng-model="model[field]" data-min="info[4]" data-max="info[5]" class="form-control" style="text-align: right" data-lpignore="true" required />
          </div>
          <div data-epics-value="" data-model-name="modelName" data-field="field"></div>
        </div>
        <div data-ng-switch-when="EpicsInteger">
          <div class="col-sm-3">
            <input data-string-to-number="integer" data-ng-model="model[field]" data-min="info[4]" data-max="info[5]" class="form-control" style="text-align: right" data-lpignore="true" required />
          </div>
          <div data-epics-value="" data-model-name="modelName" data-field="field"></div>
        </div>
        <div data-ng-switch-when="ReadOnlyFloat" class="">
          <div class="text-right" data-epics-value="" data-model-name="modelName" data-field="field"></div>
        </div>
        <div data-ng-switch-when="EpicsEnum">
          <div class="col-sm-3">
            <select class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in enum[field]"></select>
          </div>
          <div data-epics-value="" data-model-name="modelName" data-field="field"></div>
        </div>
    `;
});

SIREPO.app.factory('accelService', function(appState) {
    const self = {};
    let epicsData;
    self.computeModel = () => 'animation';

    self.getEpicsValue = (modelName, field) => {
        if (epicsData) {
            return epicsData[`${modelName}:${field}`];
        }
        return null;
    };

    self.setEpicsData = epics => {
        epicsData = epics;
    };

    appState.setAppService(self);
    return self;
});


SIREPO.app.controller('accelController', function (accelService, appState, panelState, errorService, persistentSimulation, $scope, $rootScope) {
    const self = this;
    let prevEpicsData;
    self.simScope = $scope;

    function fieldType(modelName, field) {
        if (SIREPO.APP_SCHEMA.model[modelName] && SIREPO.APP_SCHEMA.model[modelName][field]) {
            return SIREPO.APP_SCHEMA.model[modelName][field][1];
        }
        return null;
    }

    self.simHandleStatus = data => {
        if (data.epicsData && Object.keys(data.epicsData).length) {
            if (data.epicsData.error) {
                errorService.alertText(
                    data.epicsData.error
                );
                return;
            }
            accelService.setEpicsData(data.epicsData);
            const changed = [];
            for (const f in data.epicsData) {
                let [modelName, field] = f.split(':');
                const m = appState.models[modelName];
                if (m && fieldType(modelName, field) == 'ReadOnlyFloatArray') {
                    if (
                        (
                            prevEpicsData
                            && appState.deepEquals(prevEpicsData[f], m[field])
                            && ! appState.deepEquals(data.epicsData[f], m[field])
                        )
                        || ! prevEpicsData
                    ) {
                        m[field] = data.epicsData[f];
                        appState.applicationState()[modelName][field] = m[field];
                        changed.push(f);
                    }
                }
            }
            for (const f of changed) {
                for (const [r, v] of Object.entries(SIREPO.APP_SCHEMA.constants.epicsPlots)) {
                    for (const [dim, field] of Object.entries(v)) {
                        if (field == f) {
                            $scope.$broadcast('sr-accel-waveform', [
                                r,
                                data.epicsData[v.x].slice(1),
                                data.epicsData[v.y].slice(1),
                            ]);
                        }
                    }
                }
            }
            prevEpicsData = data.epicsData;
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

SIREPO.app.directive('epicsValue', function(accelService, $timeout) {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            field: '=',
        },
        template: `
          <div data-ng-class="{'sr-updated-cell': isChanged}" data-ng-model="field" data-ng-change="{{ changed() }}" class="form-control-static col-sm-3">{{ accelService.getEpicsValue(modelName, field) }}</div>
        `,
        controller: function($scope) {
            const PV_UPDATE_TIMEOUT = 700;
            let prevValue;
            $scope.accelService = accelService;

            $scope.changed = () => {
                const v = accelService.getEpicsValue($scope.modelName, $scope.field);
                if (prevValue != v) {
                    prevValue = v;
                    $scope.isChanged = true;
                    $timeout(() => { $scope.isChanged = false; }, PV_UPDATE_TIMEOUT);
                }
            };
        },
    };
});

SIREPO.app.directive('waveformLoader', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        transclude: true,
        template: `
            <div>
              <div data-ng-transclude=""></div>
            </div>
        `,
        controller: function($scope, $rootScope) {
            let plotData, plotScope;

            function updatePlot() {
                const x = plotData[1];
                const y = plotData[2];
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
                plotScope.isClientOnly = true;
                if (plotData) {
                    updatePlot();
                }
            });
            $scope.$on('sr-accel-waveform', (event, data) => {
                if (data[0] == $scope.modelName) {
                    plotData = data;
                    if (plotScope) {
                        updatePlot();
                    }
                }
            });
        },
    };
});
