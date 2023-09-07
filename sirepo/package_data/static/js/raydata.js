'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="DateTimePicker" data-ng-class="fieldClass">
          <div data-date-time-picker="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="PresetTimePicker" data-ng-class="fieldClass">
          <div data-preset-time-picker="" data-model="model" data-model-name="modelName"></div>
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

    self.canViewOutput = scan => {
        return ! [self.ANALYSIS_STATUS_NONE, self.ANALYSIS_STATUS_PENDING].includes(scan.status);
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
                appState.saveChanges('metadataColumns');
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

            $scope.$watch('model.' + $scope.field, function(newTime, oldTime) {
                if (newTime !== oldTime) {
                    $scope.dateTime = timeService.unixTimeToDate(newTime);
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

SIREPO.app.directive('presetTimePicker', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            modelName: '=',
        },
        template: `
          <button type="button" class="btn btn-info btn-xs" data-ng-click="setSearchTimeLastHour()">Last Hour</button>
          <button type="button" class="btn btn-info btn-xs" data-ng-click="setSearchTimeLastDay()">Last Day</button>
        `,
        controller: function(appState, timeService, $scope) {
            $scope.setDefaultStartStopTime = () => {
                if (!$scope.model.searchStartTime && !$scope.model.searchStopTime) {
                    $scope.setSearchTimeLastHour();
                    appState.saveChanges($scope.modelName);
                }
            };

            $scope.setSearchTimeLastDay = () => {
                $scope.model.searchStartTime = timeService.roundUnixTimeToMinutes(timeService.unixTimeOneDayAgo());
                $scope.model.searchStopTime = timeService.roundUnixTimeToMinutes(timeService.unixTimeNow());
            };

            $scope.setSearchTimeLastHour = () => {
                $scope.model.searchStartTime = timeService.roundUnixTimeToMinutes(timeService.unixTimeOneHourAgo());
                $scope.model.searchStopTime = timeService.roundUnixTimeToMinutes(timeService.unixTimeNow());
            };

            $scope.setDefaultStartStopTime();
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
                <div class="pull-right" data-ng-if="pageLocationText">
                  <span class="raydata-button">{{ pageLocationText }}</span>
                  <button class="btn btn-info btn-xs raydata-button" data-ng-click="pagePrevious()"><span class="glyphicon glyphicon-chevron-left"></span></button>
                  <button class="btn btn-info btn-xs raydata-button" data-ng-click="pageNext()"><span class="glyphicon glyphicon-chevron-right"></span></button>
                </div>
                <button class="btn btn-info btn-xs raydata-button pull-right" data-ng-click="addColumn()"><span class="glyphicon glyphicon-plus"></span> Columns</button>
                <button class="btn btn-info btn-xs raydata-button pull-right" data-ng-show="showPdfButton()" data-ng-click="downloadSelectedAnalyses()">Download Selected Analysis PDFs</button>
                <table class="table table-striped table-hover">
                  <thead>
                    <tr>
                      <th style="width: 20px; height: 40px; white-space: nowrap" data-ng-show="showPdfColumn"><input type="checkbox" data-ng-checked="pdfSelectAllScans" data-ng-click="togglePdfSelectAll()"/> PDF</th>
                      <th data-ng-repeat="column in columnHeaders track by $index" data-ng-mouseover="hoverChange($index, true)" data-ng-mouseleave="hoverChange($index, false)" data-ng-click="sortCol(column)" style="width: 100px; height: 40px; white-space: nowrap">
                        <span style="color:lightgray;" data-ng-class="arrowClass(column)"></span>
                        <span style="cursor: pointer">{{ column }}</span>
                        <button type="submit" class="btn btn-info btn-xs" data-ng-style="{visibility: showDeleteButton($index) ? 'visible' : 'hidden'}" data-ng-click="deleteCol(column)"><span class="glyphicon glyphicon-remove"></span></button>
                      </th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr ng-repeat="s in scans">
                      <td style="width: 20px; height: 20px;" data-ng-show="showPdfColumn"><input type="checkbox" data-ng-show="showCheckbox(s)" data-ng-checked="pdfSelectedScans[s.uid]" data-ng-click="togglePdfSelectScan(s.uid)"/></td>
                      <td><span data-header-tooltip="s.status"></span></td>
                      <td data-ng-repeat="c in columnHeaders.slice(1)">{{ getScanField(s, c) }}</td>
                      <td style="white-space: nowrap">
                        <button data-ng-if="analysisStatus === 'allStatuses'" class="btn btn-info btn-xs" data-ng-click="runAnalysis(s)" data-ng-disabled="disableRunAnalysis(s)">Run Analysis</button>
                        <button class="btn btn-info btn-xs" data-ng-if="raydataService.canViewOutput(s)" data-ng-click="setAnalysisScan(s)">View Output</button>
                        <button class="btn btn-info btn-xs" data-ng-click="showRunLogModal(s)">View Log</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
                <div style="height: 20px;">
                  <div ng-show="awaitingScans">Checking for new scans</div>
                  <div ng-show="noScansReturned">No scans found</div>
                </div>
              </div>
            </div>
            <div data-column-picker="" data-title="Add Column" data-id="sr-columnPicker-editor" data-available-columns="availableColumns"></div>
            <div data-analysis-modal="" data-scan-id="analysisScanId" data-analysis-status="{{ analysisStatus }}"></div>
            <div data-log-modal="" data-scan-id="runLogScanId" data-analysis-status="{{ analysisStatus }}"></div>
        `,
        controller: function(appState, errorService, panelState, raydataService, requestSender, timeService, $scope, $interval) {
            $scope.analysisScanId = null;
            $scope.availableColumns = [];
            $scope.awaitingScans = false;
            $scope.noScansReturned = false;
            $scope.orderByColumn = 'start';
            $scope.pageLocationText = '';
            $scope.pdfSelectAllScans = false;
            $scope.pdfSelectedScans = {};
            $scope.pendingRunAnalysis = {};
            $scope.reverseSortScans = false;
            $scope.runLogScanId = null;
            $scope.scans = [];
            $scope.showPdfColumn = $scope.analysisStatus === 'executed' || $scope.analysisStatus === 'allStatuses';
            $scope.raydataService = raydataService;

            let cols = [];
            let currentPage = 0;
            let hoveredIndex = null;
            let masterListColumns = [];
            let scanOutputIndex = 1;
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

            function sendScanRequest(clearScans) {
                if (clearScans) {
                    scanOutputIndex++;
                    $scope.awaitingScans = false;
                    $scope.scans = [];
                }
                const m = appState.applicationState()[$scope.modelName];
                if ('searchStartTime' in m && (!m.searchStartTime || !m.searchStopTime)) {
                    return;
                }
                function doRequest() {
                    if ($scope.awaitingScans) {
                        return;
                    }
                    $scope.awaitingScans = true;
                    $scope.noScansReturned = false;
                    const expectedOutputIndex = scanOutputIndex;
                    requestSender.sendStatelessCompute(
                        appState,
                        (json) => {
                            if (expectedOutputIndex != scanOutputIndex) {
                                return;
                            }
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
                            if (json.data.pageCount > 1) {
                                $scope.pageLocationText = `page ${currentPage + 1} / ${json.data.pageCount}`;
                            }
                            else {
                                $scope.pageLocationText = '';
                            }
                        },
                        {
                            method: 'scans',
                            args: {
                                analysisStatus: $scope.analysisStatus,
                                catalogName: appState.applicationState().catalog.catalogName,
                                searchStartTime: m.searchStartTime,
                                searchStopTime: m.searchStopTime,
                                selectedColumns: appState.applicationState().metadataColumns.selected,
                                pageSize: m.pageSize,
                                pageNumber: currentPage,
                                searchText: m.searchText,
                                sortColumn: $scope.orderByColumn,
                                sortOrder: $scope.reverseSortScans,
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
                scanRequestInterval = $interval(
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
                appState.saveChanges('metadataColumns');
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

            $scope.formatJsonFile = (contents) => {
                return JSON.stringify(contents, undefined, 2);
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

            $scope.pageNext = () => {
                currentPage += 1;
                sendScanRequest(true);
            };

            $scope.pagePrevious = () => {
                if (currentPage > 0) {
                    currentPage -= 1;
                    sendScanRequest(true);
                }
            };

            $scope.runAnalysis = scan => {
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
                            catalogName: appState.applicationState().catalog.catalogName,
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

            $scope.setAnalysisScan = scan => {
                $scope.analysisScanId = scan.uid;
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

            $scope.showRunLogModal = scan => {
                $scope.runLogScanId = scan.uid;
            };

            $scope.showSelectAllButton = (index) => {
                return index === 0;
            };

            $scope.sortCol = (column) => {
                if (column === 'selected') {
                    return;
                }
                currentPage = 0;
                $scope.orderByColumn = column;
                $scope.reverseSortScans = ! $scope.reverseSortScans;
                sendScanRequest(true);
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

            $scope.togglePdfSelectScan = uid => {
                if (uid in $scope.pdfSelectedScans) {
                    delete $scope.pdfSelectedScans[uid];
                } else {
                    $scope.pdfSelectedScans[uid] = true;
                }
            };

            $scope.$on(`${$scope.modelName}.changed`, () => sendScanRequest(true));
            $scope.$on('catalog.changed', () => sendScanRequest(true));
            $scope.$on('metadataColumns.changed', () => {
                sendScanRequest(true);
                $scope.setColumnHeaders();
                $scope.setAvailableColumns();
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

SIREPO.app.directive('logModal', function() {
    return {
        restrict: 'A',
        scope: {
            analysisStatus: '@',
            scanId: '=',
        },
        template: `
            <div data-ng-if="showLogModal()"></div>
            <div data-view-log-iframe data-log-path="logPath" data-log-html="log" data-log-is-loading="logIsLoading" data-modal-id="modalId"></div>
        `,
        controller: function(appState, errorService, requestSender, $scope) {
            $scope.log = null;
            $scope.logIsLoading = false;
            $scope.logPath = null;
            $scope.modalId = 'sr-view-log-iframe-' + $scope.analysisStatus;

            function showModal() {
                const el = $('#' + $scope.modalId);
                el.on('hidden.bs.modal', function() {
                    $scope.scanId = null;
                    el.off();
                });
                $scope.logIsLoading = true;
                el.modal('show');
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
                        onError: data => {
                            $scope.logIsLoading = false;
                            errorService.alertText(data.error);
                        },
                    }
                );
            }

            $scope.$watch('scanId', () => {
                if ($scope.scanId) {
                    showModal();
                }
            });
        },
    };
});

SIREPO.app.directive('analysisModal', function() {
    return {
        restrict: 'A',
        scope: {
            analysisStatus: '@',
            scanId: '=',
        },
        template: `
            <div class="modal fade" id="{{ analysisModalId }}" tabindex="-1" role="dialog">
              <div class="modal-dialog modal-lg">
                <div class="modal-content">
                  <div class="modal-header bg-warning">
                    <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <span class="lead modal-title text-info">Output for scan {{ scanId }}</span>
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
                            <div data-ng-repeat="j in jsonFiles">
                              <div class="panel panel-info">
                                <div class="panel-heading"><span class="sr-panel-heading">{{ j.filename }}</span></div>
                                <div class="panel-body">
                                  <pre style="overflow: scroll; height: 150px">{{ formatJsonFile(j.json) }}</pre>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                      <br/>
                      <div class="row">
                        <div class="col-sm-offset-4 col-sm-4">
                        <button data-dismiss="modal" class="btn btn-primary" style="width:100%">Close</button>
                        </div>
                      </div>
                    </span>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function(appState, errorService, requestSender, $scope) {
            $scope.analysisModalId = 'sr-analysis-output-' + $scope.analysisStatus;
            $scope.images = null;
            $scope.jsonFiles = null;

            function showModal() {
                const el = $('#' + $scope.analysisModalId);
                el.modal('show');
                el.on('hidden.bs.modal', () => {
                    $scope.scanId = null;
                    el.off();
                });
                requestSender.sendStatelessCompute(
                    appState,
                    (json) => {
                        $scope.images = json.images;
                        $scope.jsonFiles = json.jsonFiles;
                    },
                    {
                        method: 'analysis_output',
                        args: {
                            catalogName: appState.models.catalog.catalogName,
                            uid: $scope.scanId
                        }
                    },
                    {
                        onError: data => {
                            errorService.alertText(data.error);
                        },
                    }
                );
            }

            $scope.$watch('scanId', () => {
                if ($scope.scanId !== null) {
                    showModal();
                }
            });
        },
    };
});
