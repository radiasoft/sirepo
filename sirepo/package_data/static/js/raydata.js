'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    // TODO(e-carlin): rename selectedScansTable to something like ScansTable
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="DateTimePicker" data-ng-class="fieldClass">
          <div data-date-time-picker="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="SelectedScansTable" class="col-sm-12">
          <div data-scan-selector="" data-model-name="modelName"></div>
        </div>
        <div data-ng-switch-when="CatalogName" data-ng-class="fieldClass">
          <div data-catalog-picker="" data-model="model" data-field="field"></div>
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
        requestSender.sendStatelessCompute(
            appState,
            (json) => {
                self.updateScansInCache(json.data.scans);
                self.updateScanInfoTableColsInCache(json.data.cols);
                self.getScansInfo(successCallback, options);
                successCallback(
                    s.map(
                        u => simulationDataCache.scans[u]
                    ).sort((a, b) => a.start - b.start),
                    simulationDataCache.scanInfoTableCols
                );
            },
            {
                catalogName: appState.models.scans.catalogName,
                method: 'scan_info',
                scans: s,
                selectedColumns: appState.models.metadataColumns.selected,
            },
            options
        );
    };


    self.nextPngImageId = function() {
        return 'raydata-png-image-' + (++id);
    };

    self.setPngDataUrl = function (element, png) {
        element.src = 'data:image/png;base64,' + png;
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

    self.showStartNewPollButton = () => {
        return appState.models.pollBlueskyForScansAnimation.minutes > 0;
    };

    return self;
});

SIREPO.app.controller('DataSourceController', function() {
    // TODO(e-carlin): only let certain files to be uploaded
    const self = this;
    return self;
});

SIREPO.app.controller('ReplayController', function() {
    const self = this;
    return self;
});

SIREPO.app.controller('AnalysisQueueController', function() {
    const self = this;
    self.modelKey = 'analysisQueue';
    return self;
});

SIREPO.app.directive('analysisQueuePanel', function() {
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
                    <th></th>
                    <th data-ng-repeat="h in getHeader()">{{ h }}</th>
                  </tr>
                </thead>
                <tbody ng-repeat="s in queuedScans">
                  <tr>
                    <td><span data-header-tooltip="s.state"></span></td>
                    <td data-ng-repeat="c in getHeader()">{{ getQueuedScanFields(s, c) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
        `,
        controller: function(appState, errorService, panelState, raydataService, requestSender, runMulti, stringsService, $interval, $rootScope, $scope) {
            $scope.queuedScans = [];

            $scope.getHeader = function() {
                return ['uid', 'Start', 'Stop']
            };

            $scope.getQueuedScanFields = (scan, fieldName) => {
                if (['Start', 'Stop'].includes(fieldName)) {
                    return scan['metadata'][fieldName.toLowerCase()]['time']
                }
                if (['uid'].includes(fieldName)) {
                    return scan[fieldName.toLowerCase()]
                }
            }

            $scope.sendScanRequest = function() {
                requestSender.sendStatelessCompute(
                    appState,
                    (json) => {
                        $scope.queuedScans = [];
                        json.data.queuedScans.forEach((s) => {
                            $scope.queuedScans.push(s);
                        });
                    },
                    {
                        catalogName: appState.models.scans.catalogName,
                        method: 'queued_scans',
                    },
                    {
                        onError: (data) => {
                            errorService.alertText(data.error);
                        },
                    }
                );
            };

            $scope.sendScanRequest();
        }
    };
});

SIREPO.app.directive('analysisStatusPanel', function() {
    return {
        restrict: 'A',
        scope: {
            args: '='
        },
        template: `
TODO(e-carlin): impl
        `,
        controller: function() {
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('analysis-queue')}"><a href data-ng-click="nav.openSection('analysisQueue')"><span class="glyphicon glyphicon-picture"></span> Analysis Queue</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('analysis')}"><a data-ng-href="{{ nav.sectionURL('analysis') }}"><span class="glyphicon glyphicon-picture"></span> Analysis</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('replay')}"><a href data-ng-click="nav.openSection('replay')"><span class="glyphicon glyphicon-picture"></span> Replay</a></li>
                </div>
              </app-header-right-sim-loaded>
            </div>
        `,
    };
});

SIREPO.app.directive('catalogPicker', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <select class="form-control" data-ng-model="model[field]" data-ng-options="name as name for name in allCatalogs"></select>
        `,
        controller: function($scope, appState, requestSender) {
            $scope.allCatalogs = [];
            (function() {
                requestSender.sendStatelessCompute(
                    appState,
                    (json) => {
                        $scope.allCatalogs = json.data.catalogs;
                    },
                    {
                        method: 'all_catalogs',
                    },
                    {
                        onError: (data) => {
                            errorService.alertText(data.error);
                        },
                    }
                );
            })();
        },
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

SIREPO.app.directive('replayPanel', function() {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
        },
        template: `
          <form>
            <div class="form-group">
              <label for="newCatalog">Upload new catalog:</label>
              <input type="file" id="newCatalog">
            </div>
            <div class="form-group">
              <label for="sourceCatalog">Source catalog:</label>
              <select id="sourceCatalog">
                <option ng-repeat="catalog in catalogs">{{catalog}}</option>
              </select>
            </div>
            <div class="form-group">
              <label for="numScans">Number of scans:</label>
              <input type="text" id="numScans" required>
            </div>
            <div class="form-group">
              <label for="analysisNotebook">Select analysis notebook to run:</label>
              <select id="analysisNotebook">
                <option ng-repeat="notebook in notebooks">{{notebook}}</option>
              </select>
            </div>
            <button type="submit" class="btn btn-primary" data-ng-click="">Start Replay</button>
          </form>
        `,
        controller: function(appState, errorService, panelState, raydataService, requestSender, $scope) {
            // TODO(rorour):
            //  how does selected analysis notebook get saved with catalog? are there separate nbs (00-03) for csx and chx?
            //  progress bar?
            //  run notebook after replay?
            //  how to get available notebooks?
            $scope.catalogs = [];
            $scope.notebooks = ['00', '01'];

            $scope.sendCatalogsRequest = function() {
                requestSender.sendStatelessCompute(
                    appState,
                    (json) => {
                        $scope.catalogs = json.data.catalogs;
                    },
                    {
                        method: 'all_catalogs',
                    },
                    {
                        modelName: $scope.modelName,
                        onError: (data) => {
                            errorService.alertText(data.error);
                        },
                        panelState: panelState,
                    }
                );
            };

            $scope.sendCatalogsRequest();
        },
    };
});

// TODO(rorour): fix template indentation
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
                        <button type="submit" class="btn btn-primary btn-xs" data-ng-show="showDeleteButton($index)" data-ng-click="deleteCol(column)"><span class="glyphicon glyphicon-remove"></span></button>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr ng-repeat="s in scans | orderBy:orderByColumn:reverseSortScans" data-ng-click="showAnalysisOutputModal(s)">
                      <td data-ng-repeat="c in columnHeaders.slice(0)">{{ getScanField(s, c) }}</td>
                    </tr>
                  </tbody>
                </table>
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
                        method: 'completed_scans',
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

            $scope.showAnalysisOutputModal = (scan) => {
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
            }

            $scope.setAvailableColumns = function() {
                $scope.availableColumns = masterListColumns.filter((value) => {
                    return value !== 'uid' && ! $scope.columnHeaders.includes(value);
                });
            };

            $scope.setColumnHeaders = function() {
                $scope.columnHeaders = [
                    ...$scope.defaultColumns,
                    ...appState.models.metadataColumns.selected
                ];
            };

            $scope.showDeleteButton = (index) => {
                return index > $scope.defaultColumns.length && index === hoveredIndex;
            };

            $scope.sortCol = (column) => {
                if (column === 'selected') {
                    return;
                }
                $scope.orderByColumn = column;
                $scope.reverseSortScans = ! $scope.reverseSortScans;
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
