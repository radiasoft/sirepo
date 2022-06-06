'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="DateTimePicker" data-ng-class="fieldClass">
          <div data-date-time-picker="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="SelectedScansTable" class="col-sm-12">
          <div data-scan-selector="" data-model-name="modelName"></div>
        </div>
    `;
    SIREPO.appReportTypes  = `
        <div data-ng-switch-when="pngImage" data-png-image="" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}"></div>
    `;
});

SIREPO.app.factory('raydataService', function(appState, panelState, requestSender, runMulti, simulationDataCache, timeService, $rootScope) {
    const self = {};
    let id = 0;

    function removeScanFromCache(scan) {
        if (! simulationDataCache.scans) {
            return;
        }
        delete simulationDataCache.scans[scan.uid];
    }

    self.columnPickerModal = () => {
        return $('#' + panelState.modalId('columnPicker'));
    };

    self.getScanField = function(scan, field) {
        if (['start', 'stop'].includes(field)) {
            return timeService.unixTimeToDateString(scan[field]);
        }
        return scan[field];
    };

    self.getScanInfoTableHeader = function(firstColHeading, cols) {
        return cols.length > 0 ? [firstColHeading].concat(cols) : [];
    };

    self.getScansInfo = function(successCallback, options) {
        function helper(successcallback, options) {
            const s = Object.keys(appState.models.selectedScans.uids);
            if (s.every((e) => {
                // POSIT: If start is present so are the other fields we need
                return e in (simulationDataCache.scans || {}) && simulationDataCache.scans[e].start;
            })) {
                successCallback(
                    s.map(
                        u => simulationDataCache.scans[u]
                    ).sort((a, b) => a.start - b.start),
                    simulationDataCache.scanInfoTableCols
                );
                return;
            }

            if (haveRecursed) {
                throw new Error(`infinite recursion detected scans=${JSON.stringify(s)} cache=${JSON.stringify(simulationDataCache.scans)}`);
            }
            requestSender.sendStatelessCompute(
                appState,
                (json) => {
                    self.updateScansInCache(json.data.scans);
                    self.updateScanInfoTableColsInCache(json.data.cols);
                    haveRecursed = true;
                    self.getScansInfo(successCallback, options);
                },
                {
                    catalogName: appState.models.scans.catalogName,
                    method: 'scan_info',
                    scans: s,
                    selectedColumns: appState.models.metadataColumns.selected,
                },
                options
            );
        }
        let haveRecursed = false;
        helper(successCallback, options);
    };

    self.getScansRequestPayload = function(scanUuids) {
        return (scanUuids || Object.keys(appState.models.selectedScans.uids)).map(s => {
            return {
                models: appState.models,
                report: s,
                simulationType: SIREPO.APP_SCHEMA.simulationType,
                simulationId: appState.models.simulation.simulationId,
            };
        });
    };

    self.maybeToggleScanSelection = function(scan, selected) {
        if (selected !== undefined) {
            scan.selected = selected;
        }
        else if ('selected' in scan) {
            scan.selected = !scan.selected;
        }
        else {
            scan.selected = true;
        }

        if (scan.selected) {
            appState.models.selectedScans.uids[scan.uid] = true;
            self.updateScansInCache([scan]);
        }
        else {
            delete appState.models.selectedScans.uids[scan.uid];
            removeScanFromCache(scan, appState);
        }
        appState.saveChanges('selectedScans');
    };

    self.nextPngImageId = function() {
        return 'raydata-png-image-' + (++id);
    };

    self.setPngDataUrl = function (element, png) {
        element.src = 'data:image/png;base64,' + png;
    };

    self.startAnalysis = function(modelKey, scanUuids) {
        runMulti.simulation(
            self.getScansRequestPayload(scanUuids),
            {modelName: modelKey}
        );
        $rootScope.$broadcast('runMultiSimulationStarted');
    };

    self.updateScanInfoTableColsInCache = function(cols) {
        simulationDataCache.scanInfoTableCols = cols;
        return cols;
    };

    self.updateScansInCache = function(scans) {
        if (!simulationDataCache.scans) {
            simulationDataCache.scans = {};
        }
        return scans.map((s) => {
            simulationDataCache.scans[s.uid] = angular.extend(
                simulationDataCache.scans[s.uid] || {},
                s
            );
            return simulationDataCache.scans[s.uid];
        });
    };

    self.updateScansInCacheFromRunMulti = function(reply) {
        return reply.map(s => {
            // runMulti replies have a 'request' and 'response' field
            // for each of the individual requests. This allows one to
            // map the request to the specific response in cases where
            // the response contains no identifying information. For
            // example, runStatus may return just the state and
            // lastUpdateTime which doesn't contain any info to know
            // which scan (uid) this is the status for.
            s.response.uid = s.request.report;
            return self.updateScansInCache([s.response])[0];
        });
    };

    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('AnalysisController', function(appState, persistentSimulation, raydataService, timeService, $scope) {
    const self = this;
    self.modelKey = 'analysisStatus';
    self.simScope = $scope;

    self.simComputeModel = 'pollBlueskyForScansAnimation';

    self.simState = persistentSimulation.initSimulationState(self);

    self.simHandleStatus = function(data) {
        // When not running we don't want to update the scans.
        // There may be scans that the user has removed but are
        // still being sent from the backend (in parallelStatus).
        if (data.state !== 'running' || ! data.scans) {
            return;
        }
        const u = [];
        data.scans.forEach((s) => {
            raydataService.maybeToggleScanSelection(s, true);
            u.push(s.uid);
        });
        if (u.length > 0) {
            raydataService.startAnalysis(null, u);
        }
    };

    self.startSimulation = () => {
        appState.models.pollBlueskyForScansAnimation.start = timeService.unixTimeNow();
        appState.saveChanges('pollBlueskyForScansAnimation', self.simState.runSimulation);
    };

    return self;
});

SIREPO.app.controller('DataSourceController', function() {
    // TODO(e-carlin): only let certain files to be uploaded
    const self = this;
    return self;
});

SIREPO.app.directive('analysisStatusPanel', function() {
    return {
        restrict: 'A',
        scope: {
            args: '='
        },
        template: `
            <div>
              <table class="table table-striped table-hover col-sm-4">
                <thead>
                  <tr>
                    <th data-ng-repeat="h in getHeader()">{{ h }}</th>
                  </tr>
                </thead>
                <tbody ng-repeat="s in scans">
                  <tr data-ng-click="enableModalClick(s) && showAnalysisOutputModal(s)">
                    <td><span data-header-tooltip="s.state"></span></td>
                    <td data-ng-repeat="c in getHeader().slice(1)">{{ getScanField(s, c) }}</td>
                  </tr>
                </tbody>
              </table>
              <div>
                <!-- "overflow: visible" because bootstrap css was defaulting to hidden  -->
                <div class="progress" data-ng-attr-style="overflow: visible" data-ng-if="showProgressBar">
                  <div class="progress-bar progress-bar-striped active" role="progressbar" aria-valuenow="{{ percentComplete }}" aria-valuemin="0" aria-valuemax="100" data-ng-attr-style="width: {{ percentComplete || 100 }}%"></div>
                </div>
              </div>
              <div class="col-sm-6 pull-right">
                <div data-disable-after-click="">
                  <button class="btn btn-default" data-ng-if="showStartButton()" data-ng-click="start()">{{ startButtonLabel }}</button>
                </div>
              </div>
              <div class="modal fade" id="sr-analysis-output" tabindex="-1" role="dialog">
                <div class="modal-dialog modal-lg">
                  <div class="modal-content">
                    <div class="modal-header bg-warning">
                      <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                      <span class="lead modal-title text-info">Output for scan {{ selectedScan.suid }}</span>
                    </div>
                    <div class="modal-body">
                      <span data-loading-spinner data-sentinel="images">
                        <div class="container-fluid">
                          <div class="row">
                            <div class="col-sm-12">
                                  <div data-ng-repeat="i in images">
                                <div class="panel panel-info">
                                  <div class="panel-heading"><span class="sr-panel-heading">{{ i.filename }}</span></div>
                                    <div class="panel-body">
                                          <div data-png-image="" data-image="{{ i.image }}"></div>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                          <br />
                          <div class="row">
                            <div class="col-sm-offset-6 col-sm-3">
                              <button data-dismiss="modal" class="btn btn-primary" style="width:100%">Close</button>
                            </div>
                          </div>
                        </div>
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function(appState, panelState, raydataService, requestSender, runMulti, stringsService, $interval, $rootScope, $scope) {
            let cols = [];
            let runStatusInterval = null;
            $scope.images = [];
            $scope.percentComplete = 0;
            $scope.scans = [];
            $scope.selectedScan = null;
            $scope.showProgressBar = false;

            function handleResult() {
                if (runStatusInterval) {
                    $interval.cancel(runStatusInterval);
                    runStatusInterval = null;
                }
                $scope.showProgressBar = false;
            }

            function handleGetScansInfo(scans, colz) {
                cols = colz;
                $scope.scans = scans;
                const r = runningPending(scans);
                if (r === 0) {
                    handleResult();
                    return;
                }
                $scope.showProgressBar = true;
                $scope.percentComplete = ((scans.length - r) / scans.length) * 100;
                startRunStatusInterval();
            }

            function runningPending(scans) {
                return scans.filter(
                    (s) => ['running', 'pending'].includes(s.state)
                ).length;
            }

            function runStatus(showLoadingSpinner) {
                const c = {
                    onError: () => {
                        handleResult();
                        panelState.maybeSetState($scope.args.modelKey, 'error');
                    }
                };
                if (showLoadingSpinner) {
                    c.modelName = $scope.args.modelKey;
                    c.panelState = panelState;
                }
                runMulti.status(
                    raydataService.getScansRequestPayload(),
                    (data) => {
                        raydataService.updateScansInCacheFromRunMulti(data.data);
                        raydataService.getScansInfo(
                            handleGetScansInfo,
                            c
                        );
                    },
                    c
                );
            }

            function startRunStatusInterval() {
                if (runStatusInterval) {
                    return;
                }
                // POSIT: 2000 ms is the nextRequestSeconds interval
                // the supervisor uses.
                runStatusInterval = $interval(() => runStatus(false), 2000);
            }

            $rootScope.$on('runMultiSimulationStarted', () => {
                startRunStatusInterval();
            });

            $rootScope.$on('$routeChangeSuccess', handleResult);

            $scope.enableModalClick = function(scan) {
                return ['completed', 'running'].includes(scan.state);
            };

            $scope.getHeader = function() {
                return raydataService.getScanInfoTableHeader(
                    'status',
                    cols
                );
            };

            $scope.getScanField = raydataService.getScanField;

            $scope.showAnalysisOutputModal = function(scan) {
                $scope.selectedScan = scan;
                var el = $('#sr-analysis-output');
                el.modal('show');
                el.on('hidden.bs.modal', function() {
                    el.off();
                });

                requestSender.sendAnalysisJob(
                    appState,
                    (data) => $scope.images = data.data,
                    {
                        method: 'output_files',
                        models: appState.models,
                        report: $scope.selectedScan.uid,
                    }
                );
            };

            $scope.showStartButton = function() {
                // When we are polling there may be some scans that
                // are missing (user has selected them from search)
                // but we don't want to show the start button because
                // we are running analysis from polling. Use
                // showProgressBar to cover this case.
                return ! $scope.showProgressBar && $scope.scans.some((s) => s.state === 'missing');
            };

            $scope.start = function() {
                raydataService.startAnalysis($scope.args.modelKey);
            };

            $scope.startButtonLabel = 'Start New Analysis';

            appState.whenModelsLoaded($scope, () => {
                $scope.$on('scansSelected.changed', () => {
                    raydataService.getScansInfo(handleGetScansInfo);
                });
                runStatus(true);
            });
        }
    };
});


SIREPO.app.factory('runMulti', function(panelState, requestSender) {
    const self = {};

    function sendRunMulti(api, successCallback, data, awaitReply, options) {
        panelState.maybeSetState(options.modelName, 'loading');
        requestSender.sendRequest(
            'runMulti',
            (data) => {
                panelState.maybeSetState(options.modelName, 'loadingDone');
                successCallback(data);
            },
            data.map((m) => {
                m.awaitReply = awaitReply;
                m.api = api;
                return m;
            }),
            () => {
                if (options.onError) {
                    options.onError();
                }
                panelState.maybeSetState(options.modelName, 'error');
            }
        );
    }

    self.simulation = function(data, options) {
        sendRunMulti('runSimulation', () => {}, data, false, options);
    };

    self.status = function(data, successCallback, options) {
        sendRunMulti('runStatus', successCallback, data, true, options);
    };

    return self;
});

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
        `
    };
});

SIREPO.app.directive('appHeader', function(appState) {
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
                <div data-ng-if="nav.isLoaded()" data-sim-sections="">
                  <li class="sim-section" data-ng-class="{active: nav.isActive('data-source')}"><a href data-ng-click="nav.openSection('dataSource')"><span class="glyphicon glyphicon-picture"></span> Data Source</a></li>
                  <li class="sim-section" data-ng-if="haveScans()" data-ng-class="{active: nav.isActive('analysis')}"><a data-ng-href="{{ nav.sectionURL('analysis') }}"><span class="glyphicon glyphicon-picture"></span> Analysis</a></li>
                </div>
              </app-header-right-sim-loaded>
            </div>
        `,
        controller: function($scope) {
            $scope.haveScans = function() {
                return ! $.isEmptyObject(appState.models.selectedScans.uids);
            };
        }
    };
});

SIREPO.app.directive('columnPicker', function() {
    return {
        restrict: 'A',
        scope: {
            title: '@',
            id: '@',
            availableColumns: '=',
            saveColumnChanges: '=',
        },
        template: `
            <div class="modal fade" data-ng-attr-id="{{ id }}" tabindex="-1" role="dialog">
              <div class="modal-dialog modal-lg">
                <div class="modal-content">
                  <div class="modal-header bg-info">
                    <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <span class="lead modal-title text-info">{{ title }}</span>
                  </div>
                  <div class="modal-body">
                    <div class="container-fluid">
                      <label for="scans-columns" style="margin-right: 10px;">Field:</label>
                      <select name="scans-columns" id="scans-columns" data-ng-model="selected" ng-change="selectColumn()">
                        <option ng-repeat="column in availableColumns">{{column}}</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope, appState, panelState, raydataService) {
            $scope.selected = null;

            $scope.selectColumn = function() {
                if ($scope.selected === null) {
                    return;
                }
                appState.models.metadataColumns.selected.push($scope.selected);
                $scope.saveColumnChanges();
                $scope.selected = null;
                raydataService.columnPickerModal().modal('hide');
            };
        },
    };
});

SIREPO.app.directive('dateTimePicker', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `<input type="datetime-local" class="form-control" ng-model="dateTime" required >`,
        controller: function($scope, timeService) {
            $scope.dateTime = $scope.model[$scope.field] ? timeService.unixTimeToDate($scope.model[$scope.field]) : '';
            $scope.$watch('dateTime', function(newTime, oldTime) {
                if (
                    (newTime && !oldTime) ||
                    (newTime && newTime.getTime() !== oldTime.getTime())
                ) {
                    $scope.model[$scope.field] = timeService.unixTime(newTime);
                }
            });
        }
    };
});

SIREPO.app.directive('pngImage', function(plotting) {
    return {
        restrict: 'A',
        scope: {
            image: '@'
        },
        template: `<img class="img-responsive" id="{{ id }}" />`,
        controller: function(raydataService, $element, $scope) {
            $scope.id = raydataService.nextPngImageId();
            raydataService.setPngDataUrl($element.children()[0], $scope.image);
        }
    };
});

SIREPO.app.directive('scanSelector', function() {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
        },
        template: `
            <div data-show-loading-and-error="" data-model-key="scans">
              <div data-ng-if="appState.models.scans.searchStartTime && appState.models.scans.searchStopTime">
                <button class="btn btn-info btn-xs" data-ng-click="addColumn()" style="float: right;"><span class="glyphicon glyphicon-plus"></span></button>
                <table class="table table-striped table-hover">
                  <thead>
                    <tr>
                      <th data-ng-repeat="column in columnHeaders track by $index" data-ng-mouseover="hoverChange($index, true)" data-ng-mouseleave="hoverChange($index, false)" data-ng-click="sortCol(column)" style="width: 100px; height: 40px;">
                        <span style="color:lightgray;" data-ng-class="arrowClass(column)"></span>
                        {{ column }}
                        <input type="checkbox" data-ng-checked="selectAllColumns" data-ng-show="showSelectAllButton($index)" data-ng-click="toggleSelectAll()"/>
                        <button type="submit" class="btn btn-primary btn-xs" data-ng-show="showDeleteButton($index)" data-ng-click="deleteCol(column)"><span class="glyphicon glyphicon-remove"></span></button>
                      </th>
                  </tr>
                  </thead>
                  <tbody>
                    <tr ng-repeat="s in scans | orderBy:orderByColumn:reverseSortScans">
                      <td><input type="checkbox" data-ng-checked="s.selected" data-ng-click="toggleScanSelection(s)"/></td>
                      <td data-ng-repeat="c in columnHeaders.slice(1)">{{ getScanField(s, c) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <div data-column-picker="" data-title="Add Column" data-id="sr-columnPicker-editor" data-available-columns="availableColumns" data-save-column-changes="saveColumnChanges"></div>
        `,
        controller: function(appState, errorService, panelState, raydataService, requestSender, $scope) {
            let hoveredIndex = null;
            let cols = [];
            let masterListColumns = [];
            const startOrStop = ['Start', 'Stop'];

            $scope.appState = appState;
            $scope.availableColumns = [];
            // POSIT: same columns as sirepo.template.raydata._DEFAULT_COLUMNS
            $scope.defaultColumns = ['start', 'stop', 'suid'];
            $scope.orderByColumn = 'start';
            $scope.reverseSortScans = false;
            $scope.scans = [];
            $scope.selectAllColumns = false;

            function searchStartOrStopTimeKey(startOrStop) {
                return `search${startOrStop}Time`;
            }

            $scope.addColumn = function() {
                raydataService.columnPickerModal().modal('show');
            };

            $scope.arrowClass = (column) => {
                if ($scope.orderByColumn !== column) {
                    return {};
                }
                return {
                    glyphicon: true,
                    [`glyphicon-arrow-${$scope.reverseSortScans ? 'up' : 'down'}`]: true,
                };
            };

            $scope.deleteCol = function(colName) {
                appState.models.metadataColumns.selected.splice(
                    appState.models.metadataColumns.selected.indexOf(colName),
                    1
                );
                $scope.saveColumnChanges();
            };

            $scope.getHeader = function() {
                return raydataService.getScanInfoTableHeader('select', cols);
            };

            $scope.getScanField = raydataService.getScanField;

            $scope.hoverChange = (index, hovered) => {
                if (! hovered) {
                    hoveredIndex = null;
                    return;
                }
                hoveredIndex = index;
            };

            $scope.saveColumnChanges = () => {
                $scope.setColumnHeaders();
                $scope.setAvailableColumns();
            };


            $scope.sendScanRequest = function() {
                if (!appState.models.scans.searchStartTime || !appState.models.scans.searchStopTime) {
                    return;
                }
                requestSender.sendStatelessCompute(
                    appState,
                    (json) => {
                        $scope.scans = [];
                        json.data.scans.forEach((s) => {
                            s.selected = s.uid in appState.models.selectedScans.uids;
                            $scope.scans.push(s);
                        });
                        // Remove scans that were selected but are not in the new search results
                        Object.keys(appState.models.selectedScans.uids).forEach((u) => {
                            if ($scope.scans.some((e) => e.uid === u)) {
                                return;
                            }
                            delete appState.models.selectedScans.uids[u];
                        });
                        cols = raydataService.updateScanInfoTableColsInCache(json.data.cols);
                        appState.saveQuietly('selectedScans');
                    },
                    {
                        catalogName: appState.models.scans.catalogName,
                        method: 'scans',
                        searchStartTime: appState.models.scans[
                            searchStartOrStopTimeKey(startOrStop[0])
                        ],
                        searchStopTime: appState.models.scans[
                            searchStartOrStopTimeKey(startOrStop[1])
                        ],
                        selectedColumns: appState.models.metadataColumns.selected,
                    },
                    {
                        modelName: $scope.modelName,
                        onError: (data) => {
                            errorService.alertText(data.error);
                            panelState.setLoading($scope.modelName, false);
                        },
                        panelState: panelState,
                    }
                );
            };

            $scope.setAvailableColumns = function() {
                $scope.availableColumns = masterListColumns.filter((value) => {
                    return value !== 'uid' && ! $scope.columnHeaders.includes(value);
                });
            };

            $scope.setColumnHeaders = function() {
                $scope.columnHeaders = [
                    'selected',
                    ...$scope.defaultColumns,
                    ...appState.models.metadataColumns.selected
                ];
            };

            $scope.showDeleteButton = (index) => {
                return index > $scope.defaultColumns.length && index === hoveredIndex;
            };

            $scope.showSelectAllButton = (index) => {
                return index === 0;
            };

            $scope.sortCol = (column) => {
                if (column === 'selected') {
                    return;
                }
                $scope.orderByColumn = column;
                $scope.reverseSortScans = ! $scope.reverseSortScans;
            };

            $scope.toggleScanSelection = raydataService.maybeToggleScanSelection;

            $scope.toggleSelectAll = () => {
                for (let i = 0; i < $scope.scans.length; i++) {
                    $scope.toggleScanSelection($scope.scans[i], ! $scope.selectAllColumns);
                }
                $scope.selectAllColumns = ! $scope.selectAllColumns;
            };

            $scope.$on('scans.changed', $scope.sendScanRequest);
            $scope.$watchCollection('appState.models.metadataColumns.selected', (newValue, previousValue) => {
                if (newValue !== previousValue) {
                    $scope.sendScanRequest();
                    appState.saveChanges('metadataColumns');
                }
            });
            $scope.setColumnHeaders();
            $scope.sendScanRequest();
            requestSender.sendStatelessCompute(
                appState,
                (json) => {
                    masterListColumns = json.columns;
                    $scope.setAvailableColumns();
                },
                {
                    catalogName: appState.models.scans.catalogName,
                    method: 'scan_fields',
                }
            );

        },
    };
});
