'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="EpicsFloat">
          <div class="col-sm-3">
            <div data-model="model" data-field="field" data-model-name="modelName" data-epics-input=""></div>
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

SIREPO.app.factory('epicsllrfService', function(appState, requestSender, $rootScope) {
    const self = {};
    let epicsData, simSchema;
    self.computeModel = () => 'animation';

    self.lineColors = {
        y1: "#1f77b4",
        y2: "#ff7f0e",
        y3: "#2ca02c",
        y4: "#d62728",
        y5: "#9467bd",
        y6: "#8c564b",
        y7: "#e377c2",
        y8: "#7f7f7f",
        y9: "#bcbd22",
    };

    self.yFields = Object.keys(self.lineColors);

    function deleteSchema() {
        if (simSchema) {
            const schema = SIREPO.APP_SCHEMA;
            for (const k in simSchema) {
                for (const f in simSchema[k]) {
                    delete schema[k][f];
                }
            }
            simSchema = null;
        }
    }

    self.initSchema = callback => {
        const c = appState.applicationState().epicsConfig.epicsSchema;
        if (c) {
            requestSender.sendStatelessCompute(
                appState,
                data => {
                    if (data.state === 'canceled') {
                        // often related to an "timeout waiting for agent to start" error
                        // on an overloaded server
                        throw new Error('EPICS configuration failed to load, check server logs');
                    }
                    const s = data.simSchema;
                    const schema = SIREPO.APP_SCHEMA;
                    for (const k in s) {
                        for (const f in s[k]) {
                            schema[k][f] = s[k][f];
                        }
                    }
                    for (const name in s.model) {
                        appState.models[name] = appState.setModelDefaults(appState.models[name] || {}, name);
                        appState.saveQuietly(name);
                    }
                    appState.models.epicsConfig.epicsModelPrefix = s.constants.epicsModelPrefix;
                    appState.saveQuietly('epicsConfig');
                    appState.saveChanges('simulation', () => {
                        simSchema = s;
                        callback();
                    });
                },
                {
                    method: 'get_epics_config',
                    args: {
                        epicsSchema: c,
                    },
                },
            );
        }
    };

    self.getEpicsValue = (modelName, field) => {
        if (epicsData) {
            return epicsData[`${modelName}:${field}`];
        }
        return null;
    };

    self.hasEpicsSchema = () => simSchema ? true : false;

    self.isEpicsModel = modelName => {
        return modelName.startsWith(SIREPO.APP_SCHEMA.constants.epicsModelPrefix);
    };

    self.setEpicsData = epics => {
        epicsData = epics;
    };

    $rootScope.$on('modelsUnloaded', deleteSchema);

    appState.setAppService(self);
    return self;
});


SIREPO.app.controller('epicsllrfController', function (appState, epicsllrfService, errorService, persistentSimulation, requestSender, $interval, $scope) {
    const self = this;
    let prevEpicsData;
    let noCache = true;
    let inRequest = false;
    self.simScope = $scope;

    function fieldType(modelName, field) {
        if (SIREPO.APP_SCHEMA.model[modelName] && SIREPO.APP_SCHEMA.model[modelName][field]) {
            return SIREPO.APP_SCHEMA.model[modelName][field][1];
        }
        return null;
    }

    function getDiff(modelName) {
        const d = [];
        for (const f in SIREPO.APP_SCHEMA.model[modelName]) {
            const e = epicsllrfService.getEpicsValue(modelName, f);
            const s = appState.models[modelName][f];
            if (e != s && isEditable(modelName, f)) {
                d.push({
                    field: f,
                    value: s,
                });
            }
        }
        return d;
    }

    function initReportNames() {
        self.editorModelName = SIREPO.APP_SCHEMA.constants.editorModelName;
        self.reportNames = [];
        for (const k in SIREPO.APP_SCHEMA.constants.epicsPlots) {
            if (appState.isReportModelName(k)) {
                self.reportNames.push(k);
            }
        }
        self.reportNames.sort((a, b) => a.localeCompare(b));
        if (SIREPO.APP_SCHEMA.constants.isManualSignalGenerator) {
            $scope.$on(self.editorModelName + '.changed', () => {
                requestSender.sendStatelessCompute(
                    appState,
                    data => {
                        if (data.error) {
                            errorService.alertText(data.error);
                        }
                    },
                    {
                        method: 'update_signal_generator',
                        args: {
                            model: appState.applicationState()[self.editorModelName],
                            modelName: self.editorModelName,
                            serverAddress: appState.applicationState().epicsServer.serverAddress,
                        },
                    }
                );
            });
        }
    }

    function initSchema() {
        if (appState.applicationState().epicsConfig.epicsSchema) {
            self.loadingSchemaMessage = "Loading EPICS definition";
        }
        epicsllrfService.initSchema(initReportNames);
    }

    function isEditable(modelName, field) {
        const t = fieldType(modelName, field);
        return t && ! t.startsWith('ReadOnly');
    }

    function loadEpicsData(epicsData) {
        if (epicsData && Object.keys(epicsData).length) {
            if (epicsData.error) {
                errorService.alertText(
                    epicsData.error
                );
                return;
            }
            epicsllrfService.setEpicsData(epicsData);
            const changed = [];
            for (const f in epicsData) {
                const [modelName, field] = f.split(':');
                if (angular.isArray(epicsData[f]) || fieldType(modelName, field) === 'ReadOnlyFloatArray') {
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
                        if (field === f) {
                            if (typeof epicsData[v.x] === 'number') {
                                // x may be a step value, convert to an array
                                epicsData[v.x] = SIREPO.UTILS.linearlySpacedArray(
                                    0, epicsData[v.x] * epicsData[v.y1].length,
                                    epicsData[v.y1].length,
                                );
                            }
                            visited[r] = true;
                            const plotData = {
                                report: r,
                                x: epicsData[v.x].slice(1),
                            };
                            for (const f of epicsllrfService.yFields) {
                                if (v[f]) {
                                    plotData[f] = epicsData[v[f]].slice(1);
                                }
                            }
                            $scope.$broadcast('sr-epicsllrf-waveform', plotData);
                        }
                    }
                }
            }
            prevEpicsData = epicsData;
        }
    }

    function readEpicsData() {
        const d = 1000 / parseFloat(appState.applicationState().epicsServer.updateFrequency);
        // per 2000ms, ex 2 Hz --> delay 500, repeat 4
        $interval(
            () => {
                if (inRequest || ! appState.isLoaded()) {
                    return;
                }
                inRequest = true;
                requestSender.sendAnalysisJob(
                    appState,
                    function (data) {
                        inRequest = false;
                        noCache = false;
                        if (! appState.isLoaded()) {
                            return;
                        }
                        if (data.epicsData) {
                            loadEpicsData(data.epicsData);
                        }
                    },
                    {
                        method: 'read_epics_values',
                        modelName: 'animation',
                        args: {
                            noCache: noCache,
                            computedValues: SIREPO.APP_SCHEMA.constants.computedValues,
                        },
                    }
                );
            },
            d,
            2000 / d,
        );
    }

    self.hasEpicsSchema = epicsllrfService.hasEpicsSchema;

    self.simHandleStatus = data => {
        if (self.simState.isStateRunning() && data.hasEpicsData) {
            readEpicsData();
        }
    };

    $scope.$on('modelChanged', (event, modelName) => {
        if (epicsllrfService.isEpicsModel(modelName)) {
            const d = getDiff(modelName);
            if (d.length) {
                requestSender.sendStatelessCompute(
                    appState,
                    data => {
                        if (data.error) {
                            errorService.alertText(data.error);
                        }
                    },
                    {
                        method: 'update_epics_value',
                        args: {
                            fields: d,
                            epicsModelPrefix: appState.applicationState().epicsConfig.epicsModelPrefix,
                            model: modelName,
                            serverAddress: appState.applicationState().epicsServer.serverAddress,
                        },
                    }
                );
            }
        }
    });

    $scope.$on('cancelChanges', (event, modelName) => {
        if (epicsllrfService.isEpicsModel(modelName)) {
            // epics model canceled, set values from epicsData
            for (const f in SIREPO.APP_SCHEMA.model[modelName]) {
                const v = epicsllrfService.getEpicsValue(modelName, f);
                if (v !== null) {
                    appState.models[modelName][f] = v;
                }
            }
            appState.saveChanges(modelName);
        }
    });

    $scope.$on('epicsConfig.changed', initSchema);

    self.simState = persistentSimulation.initSimulationState(self);
    initSchema();
});


SIREPO.app.directive('appFooter', function(epicsllrfService) {
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

SIREPO.app.directive('epicsValue', function(appState, epicsllrfService) {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            field: '=',
        },
        template: `
          <div data-ng-model="field" class="form-control-static col-sm-3">{{ fmtExp(epicsllrfService.getEpicsValue(modelName, field)) }}</div>
        `,
        controller: function($scope) {
            $scope.epicsllrfService = epicsllrfService;
            $scope.fmtExp = value => {
                return value === null ? "" : appState.formatExponential(value);
            };
        },
    };
});

SIREPO.app.directive('epicsInput', function(appState, epicsllrfService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            modelName: '=',
        },
        template:`
          <input data-string-to-number="" data-ng-class="{'highlight-cell': isDiff}" data-ng-change="{{ changed() }}" data-ng-model="model[field]" data-min="info[4]" data-max="info[5]" class="form-control" style="text-align: right" data-lpignore="true" required />
          `,
        controller: function($scope) {
            // check dirty initially when first loading data
            let checkDirty = true;
            $scope.epicsllrfService = epicsllrfService;
            $scope.changed = () => {
                const e = epicsllrfService.getEpicsValue($scope.modelName, $scope.field);
                const s = $scope.model[$scope.field];
                $scope.isDiff = e != s && e !== null;
                if (checkDirty && $scope.isDiff) {
                    checkDirty = false;
                    $scope.$parent.form.$setDirty();
                }
            };
        },
    };
});

SIREPO.app.directive('waveformLoader', function(appState, epicsllrfService, panelState, utilities) {
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
                const e = SIREPO.APP_SCHEMA.constants.epicsPlots;
                const l = e.plotLabels;
                if (plotScope) {
                    const plots = [];
                    for (const [f, c] of Object.entries(epicsllrfService.lineColors)) {
                        if (plotData[f]) {
                            plots.push({
                                color: c,
                                points: plotData[f],
                                label: l[e[$scope.modelName][f]],
                            });
                        }
                    }
                    plotScope.load({
                        x_range: [
                            utilities.arrayMin(plotData.x),
                            utilities.arrayMax(plotData.x),
                        ],
                        y_label: "",
                        x_label: l[e[$scope.modelName].x],
                        x_points: plotData.x,
                        plots: plots,
                        y_range: [0, 1],
                    });
                }
                plotData = null;
            }

            $scope.$on('sr-plotLinked', event => {
                plotScope = event.targetScope;
                plotScope.isClientOnly = true;
                if (plotData) {
                    updatePlot();
                }
            });
            $scope.$on('sr-epicsllrf-waveform', (event, data) => {
                if (data.report === $scope.modelName) {
                    plotData = data;
                    if (plotScope) {
                        updatePlot();
                    }
                }
            });
        },
    };
});
