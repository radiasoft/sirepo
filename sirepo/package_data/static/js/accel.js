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
        <div data-ng-switch-when="ReadOnlyFloat">
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


SIREPO.app.controller('accelController', function (accelService, appState, panelState, errorService, persistentSimulation, requestSender, $interval, $scope, $rootScope) {
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
        if (self.simState.isStateRunning() && data.hasEpicsData) {
            readEpicsData();
        }
    };

    let inRequest = false;
    function readEpicsData() {
        $interval(
            () => {
                if (inRequest) {
                    return;
                }
                inRequest = true;
                requestSender.sendStatelessCompute(
                    appState,
                    function (data) {
                        inRequest = false;
                        if (! appState.isLoaded()) {
                            return;
                        }
                        if (data.epicsData) {
                            loadEpicsData(data.epicsData);
                        }
                    },
                    {
                        method: 'read_epics_values',
                        simulationId: appState.models.simulation.simulationId,
                        report: 'animation',
                    }
                );
            },
            //TODO(pjm): calculate based on 2 seconds
            500,
            4,
        );
    }

    function loadEpicsData(epicsData) {
        if (epicsData && Object.keys(epicsData).length) {
            if (epicsData.error) {
                errorService.alertText(
                    epicsData.error
                );
                return;
            }
            accelService.setEpicsData(epicsData);
            const changed = [];
            for (const f in epicsData) {
                let [modelName, field] = f.split(':');
                if (fieldType(modelName, field) == 'ReadOnlyFloatArray') {
                    if (
                        (
                            prevEpicsData
                            && ! appState.deepEquals(prevEpicsData[f], epicsData[f])
                        )
                        || ! prevEpicsData
                    ) {
                        changed.push(f);
                    }
                }
            }
            const visited = {};
            for (const f of changed) {
                for (const [r, v] of Object.entries(SIREPO.APP_SCHEMA.constants.epicsPlots)) {
                    if (visited[r]) {
                        continue;
                    }
                    for (const [dim, field] of Object.entries(v)) {
                        if (field == f) {
                            for (const dim of ['x', 'y1', 'y2']) {
                                if (! angular.isArray(epicsData[v[dim]])) {
                                    //TODO(pjm): invalid epics data recieved
                                    prevEpicsData = null;
                                    return;
                                }
                            }
                            visited[r] = true;
                            $scope.$broadcast('sr-accel-waveform', [
                                r,
                                epicsData[v.x].slice(1),
                                epicsData[v.y1].slice(1),
                                epicsData[v.y2].slice(1),
                            ]);
                        }
                    }
                }
            }
            prevEpicsData = epicsData;
        }
    }

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

SIREPO.app.directive('epicsValue', function(appState, accelService, $timeout) {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            field: '=',
        },
        template: `
          <div data-ng-class="{'highlight-cell': isDiff}" data-ng-model="field" data-ng-change="{{ changed() }}" class="form-control-static col-sm-3">{{ accelService.getEpicsValue(modelName, field) }}</div>
        `,
        controller: function($scope) {
            $scope.accelService = accelService;
            $scope.changed = () => {
                const v = accelService.getEpicsValue($scope.modelName, $scope.field);
                if (nonReadOnlyDiff(appState.models.MTEST[$scope.field], v, $scope.field)) {
                    $scope.isDiff = true;
                } else {
                    $scope.isDiff = false;
                }
            };

            const nonReadOnlyDiff = (inputVal, epicsVal, pvName) => {
                if (! ["MinValue", "MaxValue", "MeanValue"].includes(pvName)){
                    if (inputVal != epicsVal && epicsVal !== null) {
                        return true;
                    }
                }
                return false;
            }
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
                const y1 = plotData[2];
                const y2 = plotData[3];
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
                                points: y1,
                                label: "Waveform 1",
                            },
                            {
                                color: '#ff7f0e',
                                points: y2,
                                label: "Waveform 2",
                            },
                        ],
                        y_range: [
                            Math.min(Math.min(...y1), Math.min(...y2)),
                            Math.max(Math.max(...y1), Math.max(...y2)),
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
