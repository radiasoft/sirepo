'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="DateTimePicker" data-ng-class="fieldClass">
          <div data-date-time-picker="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="ExecutedScansTable" class="col-sm-12">
          <div data-scans-table="" data-model-name="modelName" data-analysis-status="executed"></div>
        </div>
        <div data-ng-switch-when="RecentlyExecutedScansTable" class="col-sm-12">
          <div data-scans-table="" data-model-name="modelName" data-analysis-status="recentlyExecuted"></div>
        </div>
        <div data-ng-switch-when="RunAnalysisTable" class="col-sm-12">
          <div data-scans-table="" data-model-name="modelName" data-analysis-status="allStatuses"></div>
        </div>
        <div data-ng-switch-when="QueuedScansTable" class="col-sm-12">
          <div data-scans-table="" data-model-name="modelName" data-analysis-status="queued"></div>
        </div>
        <div data-ng-switch-when="CatalogName" data-ng-class="fieldClass">
          <div data-catalog-picker="" data-model="model" data-field="field"></div>
        </div>
    `;
    SIREPO.appReportTypes  = `
        <div data-ng-switch-when="pngImage" data-png-image="" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}"></div>
    `;
});

SIREPO.app.factory('raydataService', function(appState, panelState, timeService) {
    const self = {};
    let id = 0;

    //POSIT: _AnalysisStatus.NON_STOPPED in scan monitor
    self.ANALYSIS_STATUS_NON_STOPPED = ["pending", "running"];

    // POSIT: Matches _AnalysisStatus.NONE in scan monitor
    self.ANALYSIS_STATUS_NONE = "none";

    // POSIT: Matches _AnalysisStatus.PENDING in scan monitor
    self.ANALYSIS_STATUS_PENDING = "pending";

    // POSIT: status + sirepo.template.raydata._DEFAULT_COLUMNS
    self.DEFAULT_COLUMNS = ['status', 'start', 'stop', 'suid'];

    self.columnPickerModal = () => {
        return $('#' + panelState.modalId('columnPicker'));
    };

    self.getScanField = function(scan, field) {
        if (['start', 'stop'].includes(field)) {
            return timeService.unixTimeToDateString(scan[field]);
        }
        return scan[field];
    };

    self.nextPngImageId = function() {
        return 'raydata-png-image-' + (++id);
    };

    self.setPngDataUrl = function (element, png) {
        element.src = 'data:image/png;base64,' + png;
    };

    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('AnalysisQueueController', function() {
    const self = this;
    return self;
});

SIREPO.app.controller('AnalysisExecutedController', function() {
    const self = this;
    return self;
});

SIREPO.app.controller('ReplayController', function() {
    const self = this;
    return self;
});

SIREPO.app.controller('RunAnalysisController', function() {
    const self = this;
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('run-analysis')}"><a href data-ng-click="nav.openSection('runAnalysis')"><span class="glyphicon glyphicon-picture"></span> Run Analysis</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('analysis-executed')}"><a href data-ng-click="nav.openSection('analysisExecuted')"><span class="glyphicon glyphicon-picture"></span> Executed</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('analysis-queue')}"><a href data-ng-click="nav.openSection('analysisQueue')"><span class="glyphicon glyphicon-picture"></span> Queued</a></li>
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
            <div data-ng-hide="!awaitingCatalogNames">Loading...</div>
            <select class="form-control" data-ng-hide="awaitingCatalogNames" data-ng-model="model[field]" data-ng-options="name as name for name in catalogNames"></select>
        `,
        controller: function($scope, appState, errorService, requestSender) {
            $scope.catalogNames = [];
            $scope.awaitingCatalogNames = true;

            requestSender.sendStatelessCompute(
                appState,
                json => {
                    $scope.catalogNames = json.data.catalogs;
                    $scope.awaitingCatalogNames = false;
                },
                {
                    method: 'catalog_names',
                },
                {
                    onError: data => {
                        $scope.awaitingCatalogNames = false;
                        errorService.alertText(data.error);
                    },
                }
            );
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
                      <label style="margin-right: 10px;">Field:</label>
                      <select data-ng-model="selected" ng-change="selectColumn()">
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

SIREPO.app.directive('dotsAnimation', function() {
    return {
        restrict: 'A',
        scope: {
            text: '@',
        },
        template: `
          {{ text }}{{ dots }}
        `,
        controller: function($interval, $scope) {
            $scope.dots = '';

            $interval(() => {
                if ($scope.dots.length < 3) {
                    $scope.dots += '.';
                } else {
                    $scope.dots = '.';
                }
            }, 1000);
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
          <div class="text-center">
            <button type="submit" class="btn btn-primary" style="margin-top: 10px" data-ng-click="startReplay()" data-ng-disabled="disableReplayButton()">Start Replay</button>
            <div ng-if="replaying">
              <div data-dots-animation="" data-text="Replaying scans"></div>
            </div>
          </div>
        `,
        controller: function(appState, errorService, panelState, raydataService, requestSender, $scope) {
            $scope.replaying = false;

            $scope.disableReplayButton = () => {
                if (! (appState.models.replay.sourceCatalogName && appState.models.replay.destinationCatalogName && appState.models.replay.numScans)) {
                    return true;
                } else {
                    return $scope.replaying;
                }
            };

            $scope.startReplay = () => {
                $scope.replaying = true;
                requestSender.sendStatelessCompute(
                    appState,
                    () => {
                        $scope.replaying = false;
                    },
                    {
                        method: 'begin_replay',
                        sourceCatalogName: appState.models.replay.sourceCatalogName,
                        destinationCatalogName: appState.models.replay.destinationCatalogName,
                        numScans: appState.models.replay.numScans,
                    },
                    {
                        modelName: $scope.modelName,
                        onError: (data) => {
                            errorService.alertText(data.error);
                            panelState.setLoading($scope.modelName, false);
                            $scope.replaying = false;
                        },
                        panelState: panelState,
                    }
                );

            };
        },
    };
});

SIREPO.app.directive('scansTable', function() {
    return {
        restrict: 'A',
        scope: {
            analysisStatus: '@',
            modelName: '=',
        },
        template: `
            <div data-show-loading-and-error="" data-model-key="scans">
              <div>
                <button class="btn btn-info btn-xs" data-ng-click="addColumn()" style="float: right; margin:5px;"><span class="glyphicon glyphicon-plus"></span></button>
                <button class="btn btn-info btn-xs" data-ng-show="showPdfButton()" data-ng-click="downloadSelectedAnalyses()" style="float: right; margin:5px;">Download Selected Analysis PDFs</button>
                <table class="table table-striped table-hover">
                  <thead>
                    <tr>
                      <th style="width: 20px; height: 20px;" data-ng-show="showPdfColumn"><input type="checkbox" data-ng-checked="pdfSelectAllScans" data-ng-click="togglePdfSelectAll()"/> PDF</th>
                      <th data-ng-if="analysisStatus === 'allStatuses'" style="width: 50px; height: 40px;"></th>
                      <th style="width: 50px; height: 40px;"></th>
                      <th data-ng-repeat="column in columnHeaders track by $index" data-ng-mouseover="hoverChange($index, true)" data-ng-mouseleave="hoverChange($index, false)" data-ng-click="sortCol(column)" style="width: 100px; height: 40px;">
                        <span style="color:lightgray;" data-ng-class="arrowClass(column)"></span>
                        {{ column }}
                        <button type="submit" class="btn btn-primary btn-xs" data-ng-show="showDeleteButton($index)" data-ng-click="deleteCol(column)"><span class="glyphicon glyphicon-remove"></span></button>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr ng-repeat="s in scans | orderBy:orderByColumn:reverseSortScans" data-ng-click="setSelectedScan(s)">
                      <td style="width: 20px; height: 20px;" data-ng-show="showPdfColumn"><input type="checkbox" data-ng-show="showCheckbox(s)" data-ng-checked="pdfSelectedScans[s.uid]" data-ng-click="togglePdfSelectScan(s.uid, $event)"/></td>
                      <td data-ng-if="analysisStatus === 'allStatuses'"><button class="btn btn-info btn-xs" data-ng-click="runAnalysis(s, $event)" data-ng-disabled="disableRunAnalysis(s)">Run Analysis</button></td>
                      <td><button class="btn btn-info btn-xs" data-ng-click="showRunLogModal(s, $event)">View Log</button></td>
                      <td><span data-header-tooltip="s.status"></span></td>
                      <td data-ng-repeat="c in columnHeaders.slice(1)">{{ getScanField(s, c) }}</td>
                    </tr>
                  </tbody>
                </table>
                <div style="height: 20px;">
                  <div ng-if="awaitingScans" data-dots-animation="" data-text="Checking for new scans"></div>
                  <div ng-if="noScansReturned">No scans found</div>
                </div>
              </div>
            </div>
            <div data-column-picker="" data-title="Add Column" data-id="sr-columnPicker-editor" data-available-columns="availableColumns" data-save-column-changes="saveColumnChanges"></div>
            <div class="modal fade" id="{{ analysisModalId }}" tabindex="-1" role="dialog">
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
                      <br/>
                      <div class="row">
                        <div class="col-sm-offset-6 col-sm-3">
                        <button data-dismiss="modal" class="btn btn-primary" style="width:100%">Close</button>
                        </div>
                      </div>
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <div data-view-log-iframe-wrapper data-scan-id="runLogScanId" data-modal-id="runLogModalId" data-show-log="showLog"></div>
        `,
        controller: function(appState, errorService, panelState, raydataService, requestSender, $scope, $interval) {
            $scope.analysisModalId = 'sr-analysis-output-' + $scope.analysisStatus;
            $scope.availableColumns = [];
            $scope.awaitingScans = false;
            $scope.images = null;
            $scope.noScansReturned = false;
            $scope.orderByColumn = 'start';
            $scope.pdfSelectAllScans = false;
            $scope.pdfSelectedScans = {};
            $scope.pendingRunAnalysis = {};
            $scope.reverseSortScans = false;
            $scope.runLogModalId = 'sr-view-log-iframe-' + $scope.analysisStatus;
            $scope.runLogScanId = null;
            $scope.scans = [];
            $scope.selectedScan = null;
            $scope.showPdfColumn = $scope.analysisStatus === 'executed' || $scope.analysisStatus === 'allStatuses';

            let cols = [];
            let hoveredIndex = null;
            let masterListColumns = [];
            let scanRequestInterval = null;

            const errorOptions = {
                modelName: $scope.modelName,
                onError: (data) => {
                    if (scanRequestInterval) {
                        $interval.cancel(scanRequestInterval);
                        scanRequestInterval = null;
                    }
                    errorService.alertText(data.error);
                    panelState.setLoading($scope.modelName, false);
                },
                panelState: panelState,
            };

            $scope.showAnalysisOutputModal = () => {
                const el = $('#' + $scope.analysisModalId);
                el.modal('show');
                el.on('hidden.bs.modal', function() {
                    $scope.setSelectedScan(null);
                    el.off();
                });
                requestSender.sendStatelessCompute(
                    appState,
                    (json) => {
                        $scope.images = json.images;
                    },
                    {
                        method: 'analysis_output',
                        args: {
                            catalogName: appState.models.catalog.catalogName,
                            uid: $scope.selectedScan.uid
                        }
                    },
                    errorOptions
                );
            };

            function sendScanRequest () {
                const m = appState.models[$scope.modelName];
                if ('searchStartTime' in m && (!m.searchStartTime || !m.searchStopTime)) {
                    return;
                }
                function doRequest() {
                    $scope.awaitingScans = true;
                    $scope.noScansReturned = false;
                    requestSender.sendStatelessCompute(
                        appState,
                        (json) => {
                            $scope.awaitingScans = false;
                            $scope.scans = json.data.scans.slice();
                            if ($scope.scans.length === 0) {
                                $scope.noScansReturned = true;
                            }
                            for (const p in $scope.pdfSelectedScans) {
                                if ($scope.scans.findIndex(s => s.uid === p) === -1) {
                                    delete $scope.pdfSelectedScans[p];
                                }
                            }
                        },
                        {
                            method: 'scans',
                            args: {
                                analysisStatus: $scope.analysisStatus,
                                catalogName: appState.models.catalog.catalogName,
                                searchStartTime: m.searchStartTime,
                                searchStopTime: m.searchStopTime,
                                selectedColumns: appState.models.metadataColumns.selected,
                            }
                        },
                        errorOptions
                    );
                }
                if (scanRequestInterval) {
                    $interval.cancel(scanRequestInterval);
                    scanRequestInterval = null;
                }
                // Send once and then will happen on $interval
                doRequest();
                scanRequestInterval =  $interval(
                    doRequest,
                    5000
                );
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

            $scope.disableRunAnalysis = (scan) => {
                if ($scope.pendingRunAnalysis[scan.uid]) {
                    return true;
                }
                return raydataService.ANALYSIS_STATUS_NON_STOPPED.includes(scan.status);
            };

            $scope.downloadSelectedAnalyses = () => {
                requestSender.sendStatelessCompute(
                    appState,
                    function (data) {
                        saveAs(data, "analysis_pdfs.zip");
                    },
                    {
                        method: 'download_analysis_pdfs',
                        responseType: 'blob',
                        args: {
                            uids: Object.keys($scope.pdfSelectedScans),
                        }
                    },
                    errorOptions,
                );
            };

            $scope.getHeader = function() {
                return cols.length > 0 ? ['select'].concat(cols) : [];
            };

            $scope.getScanField = raydataService.getScanField;

            $scope.hoverChange = (index, hovered) => {
                if (! hovered) {
                    hoveredIndex = null;
                    return;
                }
                hoveredIndex = index;
            };

            $scope.runAnalysis = (scan, event) => {
                event.stopPropagation();
                $scope.pendingRunAnalysis[scan.uid] = true;
                requestSender.sendStatelessCompute(
                    appState,
                    (json) => {
                        $scope.scans[$scope.scans.findIndex(s => s.uid === scan.uid)].status = raydataService.ANALYSIS_STATUS_PENDING;
                        delete $scope.pendingRunAnalysis[scan.uid];
                    },
                    {
                        method: 'run_analysis',
                        args: {
                            catalogName: appState.models.catalog.catalogName,
                            uid: scan.uid,
                        }
                    },
                    {
                        modelName: $scope.modelName,
                        onError: (data) => {
                            if (scanRequestInterval) {
                                $interval.cancel(scanRequestInterval);
                                scanRequestInterval = null;
                                $scope.scans[$scope.scans.findIndex(s => s.uid === scan.uid)].status = raydataService.ANALYSIS_STATUS_PENDING;
                                delete $scope.pendingRunAnalysis[scan.uid];
                            }
                            errorService.alertText(data.error);
                            panelState.setLoading($scope.modelName, false);
                        },
                        panelState: panelState,
                    }
                );
            };

            $scope.saveColumnChanges = () => {
                $scope.setColumnHeaders();
                $scope.setAvailableColumns();
            };

            $scope.setAvailableColumns = function() {
                $scope.availableColumns = masterListColumns.filter((value) => {
                    return value !== 'uid' && ! $scope.columnHeaders.includes(value);
                });
            };

            $scope.setColumnHeaders = function() {
                $scope.columnHeaders = [
                    ...raydataService.DEFAULT_COLUMNS,
                    ...appState.models.metadataColumns.selected
                ];
            };

            $scope.setSelectedScan = (scan) => {
                $scope.selectedScan = scan;
                if ($scope.selectedScan !== null && ! [raydataService.ANALYSIS_STATUS_NONE, raydataService.ANALYSIS_STATUS_PENDING].includes($scope.selectedScan.status)) {
                    $scope.showAnalysisOutputModal();
                }
            };

            $scope.showCheckbox = (scan) => {
                return scan.pdf;
            };

            $scope.showDeleteButton = (index) => {
                return index > raydataService.DEFAULT_COLUMNS.length - 1 && index === hoveredIndex;
            };

            $scope.showPdfButton = () => {
                return $scope.showPdfColumn && Object.keys($scope.pdfSelectedScans).length;
            };

            $scope.showRunLogModal = (scan, event) => {
                event.stopPropagation();
                $scope.runLogScanId = scan.uid;
                $scope.showLog = true;
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

            $scope.togglePdfSelectAll = () => {
                $scope.pdfSelectedScans = {};
                $scope.pdfSelectAllScans = ! $scope.pdfSelectAllScans;
                if ($scope.pdfSelectAllScans) {
                    $scope.scans.forEach(s => {
                        if (s.pdf) {
                            $scope.pdfSelectedScans[s.uid] = true;
                        }
                    });
                }
            };

            $scope.togglePdfSelectScan = (uid, event) => {
                event.stopPropagation();
                if (uid in $scope.pdfSelectedScans) {
                    delete $scope.pdfSelectedScans[uid];
                } else {
                    $scope.pdfSelectedScans[uid] = true;
                }
            };

            $scope.$on(`${$scope.modelName}.changed`, sendScanRequest);
            $scope.$on('catalog.changed', sendScanRequest);
            $scope.$watchCollection('appState.models.metadataColumns.selected', (newValue, previousValue) => {
                if (newValue !== previousValue) {
                    sendScanRequest();
                    appState.saveChanges('metadataColumns');
                }
            });
            $scope.setColumnHeaders();
            sendScanRequest();
            requestSender.sendStatelessCompute(
                appState,
                (json) => {
                    masterListColumns = json.columns;
                    $scope.setAvailableColumns();
                },
                {
                    method: 'scan_fields',
                    args: {
                        catalogName: appState.models.catalog.catalogName,
                    }
                },
                errorOptions
            );

            $scope.$on("$destroy", function() {
                if (scanRequestInterval) {
                    $interval.cancel(scanRequestInterval);
                    scanRequestInterval = null;
                }
            });
        },
    };
});

SIREPO.app.directive('viewLogIframeWrapper', function() {
    return {
        restrict: 'A',
        scope: {
            scanId: '<',
            modalId: '<',
            showLog: '=',
        },
        template: `
            <div data-ng-if="showLogModal()"></div>
            <div data-view-log-iframe data-log-path="logPath" data-log-html="log" data-log-is-loading="logIsLoading" data-modal-id="modalId"></div>
        `,
        controller: function(appState, errorService, panelState, requestSender, $scope, $element) {
            $scope.logIsLoading = false;
            $scope.log = null;
            $scope.logPath = null;

            $scope.showLogModal = () => {
                if ($scope.showLog) {
                    $scope.showLog = false;
                    $('#' + $scope.modalId).modal('show');
                }
            };

            $scope.$on('$destroy', () => {
                $($element).off();
            });

            $($element).on('show.bs.modal','#' + $scope.modalId, function() {
                $scope.logIsLoading = true;
                requestSender.sendStatelessCompute(
                    appState,
                    (json) => {
                        $scope.logIsLoading = false;
                        $scope.log = json.run_log;
                        $scope.logPath = json.log_path;
                    },
                    {
                        method: 'analysis_run_log',
                        args: {
                            uid: $scope.scanId,
                        }
                    },
                    {
                        modelName: $scope.modelName,
                        onError: (data) => {
                            $scope.logIsLoading = false;
                            errorService.alertText(data.error);
                            panelState.setLoading($scope.modelName, false);
                        },
                        panelState: panelState,
                    }
                );
            });
        },
    };
});
