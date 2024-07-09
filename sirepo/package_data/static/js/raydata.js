'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="DateTimePicker" class="col-sm-7">
          <div data-date-time-picker="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="PresetTimePicker" class="col-sm-7">
          <div class="text-right" data-preset-time-picker="" data-model="model" data-model-name="modelName"></div>
        </div>
        <div data-ng-switch-when="RecentlyExecutedScansTable" class="col-sm-12">
          <div data-scans-table="" data-model-name="modelName" data-analysis-status="recentlyExecuted"></div>
        </div>
        <div data-ng-switch-when="RunAnalysisTable" class="col-sm-12">
          <div class="row" data-scans-table="" data-model-name="modelName" data-analysis-status="allStatuses"></div>
        </div>
        <div data-ng-switch-when="QueuedScansTable" class="col-sm-12">
          <div data-scans-table="" data-model-name="modelName" data-analysis-status="queued"></div>
        </div>
        <div data-ng-switch-when="CatalogNamePicker" data-ng-class="fieldClass">
          <div data-catalog-picker="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="CatalogNameDisplay" data-ng-class="fieldClass">
          <div data-catalog-name-display="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="SearchTerms">
          <div data-search-terms="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="SearchTermText" data-ng-class="fieldClass">
          <div data-search-term-text="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="ColumnList" data-ng-class="fieldClass">
          <div data-column-list="" data-model="model" data-field="field"></div>
        </div>
    `;
    SIREPO.appReportTypes  = `
        <div data-ng-switch-when="pngImage" data-png-image="" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}"></div>
    `;
});

SIREPO.app.factory('raydataService', function(appState, $rootScope) {
    const self = {};
    let id = 0;

    //POSIT: _AnalysisStatus.NON_STOPPED in scan monitor
    self.ANALYSIS_STATUS_NON_STOPPED = ["pending", "running"];

    // POSIT: Matches scan monitor values in _AnalysisStatus
    self.ANALYSIS_STATUS_COMPLETED = "completed";
    self.ANALYSIS_STATUS_NONE = "none";
    self.ANALYSIS_STATUS_PENDING = "pending";

    self.detailScan = null;

    self.canViewOutput = scan => {
        return ! [self.ANALYSIS_STATUS_NONE, self.ANALYSIS_STATUS_PENDING].includes(scan.status);
    };

    self.setDetailScan = scan => {
        self.detailScan = scan;
    };

    self.nextPngImageId = () => {
        return 'raydata-png-image-' + (++id);
    };

    self.setPngDataUrl = (element, png) => {
        element.src = 'data:image/png;base64,' + png;
    };

    appState.setAppService(self);

    $rootScope.$on('modelsUnloaded', () => self.setDetailScan(null));

    return self;
});

SIREPO.app.factory('columnsService', function(appState, requestSender, $rootScope) {
    const self = {};

    self.allColumns = null;
    self.allColumnsWithHeading = null;
    self.selectSearchFieldText = 'Select Search Field';

    function loadColumns() {
        requestSender.sendStatelessCompute(
            appState,
            json => {
                if (json.columns) {
                    self.updateColumns(json.columns);
                }
            },
            {
                method: 'scan_fields',
                args: {
                    catalogName: appState.models.catalog.catalogName,
                }
            },
        );
    }

    self.defaultColumns = (analysisStatus, appState) => {
        const res = [
	    'status',
	    'start',
	    'stop',
	    'suid',
	    ...(SIREPO.APP_SCHEMA.constants.defaultColumns[appState.models.catalog.catalogName] || []),
	];
        if (analysisStatus == 'queued') {
            res.splice(1, 0, 'queue order');
        }
        return res;
    };

    self.updateColumns = columns => {
        if (! columns || ! columns.length) {
            return;
        }
        let updated = false;
        if (! self.allColumns) {
            self.allColumns = columns;
            updated = true;
        }
        else {
            for (const c of columns) {
                if (! self.allColumns.includes(c)) {
                    self.allColumns.push(c);
                    updated = true;
                }
            }
        }
        if (updated) {
            self.allColumns = self.allColumns.slice();
            self.allColumns.sort((a, b) => a.localeCompare(b));
            self.allColumnsWithHeading = [
                self.selectSearchFieldText,
                ...self.allColumns,
            ];
        }
    };

    if (appState.isLoaded()) {
        loadColumns();
    }
    $rootScope.$on('modelsUnloaded', () => {
        self.allColumns = null;
        self.allColumnsWithHeading = null;
    });
    $rootScope.$on('modelsLoaded', loadColumns);

    return self;
});

SIREPO.app.factory('scanService', function($rootScope) {
    const self = {};
    let cachedScans = {};

    self.cachedScans = analysisStatus => {
        return cachedScans[analysisStatus];
    };

    self.setCachedScans = (analysisStatus, scanInfo) => {
        cachedScans[analysisStatus] = scanInfo;
        return cachedScans[analysisStatus];
    };

    $rootScope.$on('modelsUnloaded', () => {
        cachedScans = {};
    });

    return self;
});

SIREPO.app.controller('AnalysisQueueController', function() {
    const self = this;
    return self;
});

SIREPO.app.controller('ReplayController', function() {
    const self = this;
    return self;
});

SIREPO.app.controller('RunAnalysisController', function(raydataService) {
    const self = this;
    self.raydataService = raydataService;
    return self;
});

SIREPO.app.directive('appFooter', function(raydataService) {
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
                </div>
              </app-header-right-sim-loaded>
            </div>
        `,
    };
});

SIREPO.app.directive('catalogNameDisplay', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <div class="form-control-static text-uppercase"><strong>{{ model[field] }}</strong></div>
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
            <select class="form-control text-uppercase" data-ng-hide="awaitingCatalogNames" data-ng-model="model[field]" data-ng-options="name as name for name in catalogNames" required></select>
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
        scope: {},
        template: `
            <div class="form-group form-group-sm pull-right" style="margin: 0; font-weight: 700">
              <select class="form-control" data-ng-model="selected" ng-change="selectColumn()">
                <option ng-repeat="column in availableColumns">{{column}}</option>
              </select>
            </div>
        `,
        controller: function($scope, appState, columnsService) {
            $scope.selected = null;
            $scope.availableColumns = null;
            const addColumnText = 'Add Column';

            function setAvailableColumns() {
                $scope.availableColumns = columnsService.allColumns.filter(value => {
                    return ! appState.models.metadataColumns.selected.includes(value);
                });
                $scope.availableColumns.unshift(addColumnText);
                $scope.selected = addColumnText;
            }

            $scope.selectColumn = () => {
                if ($scope.selected === null) {
                    return;
                }
                appState.models.metadataColumns.selected.push($scope.selected);
                appState.saveChanges('metadataColumns');
            };

            $scope.$on('metadataColumns.changed', setAvailableColumns);
            $scope.columnsService = columnsService;
            $scope.$watch('columnsService.allColumns', setAvailableColumns);

            setAvailableColumns();
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
          <button type="button" class="btn btn-info btn-xs" data-ng-click="setSearchTimeLastWeek()">Last Week</button>
          <button type="button" class="btn btn-info btn-xs" data-ng-click="setSearchTimeMaxRange()">All Time</button>
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

            $scope.setSearchTimeLastWeek = () => {
                $scope.model.searchStartTime = timeService.roundUnixTimeToMinutes(timeService.unixTimeOneWeekAgo());
                $scope.model.searchStopTime = timeService.roundUnixTimeToMinutes(timeService.unixTimeNow());
            };

            $scope.setSearchTimeMaxRange = () => {
                $scope.model.searchStartTime = timeService.roundUnixTimeToMinutes(60);
                $scope.model.searchStopTime = timeService.roundUnixTimeToMinutes(timeService.unixTimeNow());
            };

            $scope.setDefaultStartStopTime();
        }
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
            <div>
              <div>
                <div class="pull-right" data-ng-if="pageLocationText">
                  <span class="raydata-button">{{ pageLocationText }}</span>
                  <button class="btn btn-info btn-xs raydata-button" data-ng-click="pagePrevious()" data-ng-disabled="! canPreviousPage()"><span class="glyphicon glyphicon-chevron-left"></span></button>
                  <button class="btn btn-info btn-xs raydata-button" data-ng-click="pageNext()" data-ng-disabled="! canNextPage()"><span class="glyphicon glyphicon-chevron-right"></span></button>
                </div>
                <div data-ng-if="columnsService.allColumns" data-column-picker=""></div>
                <button class="btn btn-info btn-xs raydata-button pull-right" data-ng-show="showPdfButton()" data-ng-click="downloadSelectedAnalyses()">Download Selected Analysis PDFs</button>
                <table class="table table-striped table-hover">
                  <thead>
                    <tr>
                      <th style="width: 20px; height: 40px; white-space: nowrap" data-ng-show="showPdfColumn"><input type="checkbox" data-ng-checked="pdfSelectAllScans" data-ng-click="togglePdfSelectAll()"/> <span style="vertical-align: top">PDF</span></th>
                      <th data-ng-repeat="column in columnHeaders track by $index" class="raydata-removable-column" style="width: 100px; height: 40px; white-space: nowrap">
                        <span data-ng-if="columnIsSortable(column)" style="color:lightgray;" data-ng-class="arrowClass(column)"></span>
                        <span data-ng-attr-style="{{ columnIsSortable(column) ? 'cursor: pointer;' : '' }}" data-ng-click="sortCol(column)">{{ column }}</span>
                        <button type="submit" class="btn btn-info btn-xs raydata-remove-column-button" data-ng-if="showDeleteButton($index)" data-ng-click="deleteCol(column)"><span class="glyphicon glyphicon-remove"></span></button>
                      </th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr ng-repeat="s in scans track by $index" data-ng-click="raydataService.setDetailScan(s)" data-ng-attr-style="{{ analysisStatus === 'allStatuses' ? 'cursor: pointer;' : '' }}">
                      <td style="width: 1%" data-ng-show="showPdfColumn"><input type="checkbox" data-ng-show="showCheckbox(s)" data-ng-checked="pdfSelectedScans[s.rduid]" data-ng-click="togglePdfSelectScan(s.rduid)"/></td>
                      <td width="1%"><span data-header-tooltip="s.status"></span></td>
                      <td data-ng-if="analysisStatus == 'queued'">
                        <div data-queue-order="" scan="s" number-of-scans="{{ scans.length }}" data-refresh-scans="refreshScans()"></div>
                      </td>
                      <td data-ng-repeat="c in columnHeaders.slice(analysisStatus == 'queued' ? 2 : 1)"><div data-scan-cell-value="s[c]", data-column-name="c"></div></td>
                      <td style="white-space: nowrap" width="1%">
                        <button data-ng-if="analysisStatus === 'allStatuses'" class="btn btn-info btn-xs" data-ng-click="runAnalysis(s.rduid)" data-ng-disabled="disableRunAnalysis(s)">Run Analysis</button>
                        <button class="btn btn-info btn-xs" data-ng-disabled="! raydataService.canViewOutput(s)" data-ng-click="setAnalysisScan(s)">View Output</button>
                        <button class="btn btn-info btn-xs" data-ng-click="showRunLogModal(s)">View Log</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
                <div style="height: 40px; position: relative;">
                  <span data-loading-spinner data-sentinel="!isLoadingNewScans">
                  <div ng-show="isRefreshingScans && ! isLoadingNewScans">Checking for new scans</div>
                  <div ng-show="noScansReturned">No scans found</div>
                  <div ng-show="searchError"><span class="bg-warning">{{ searchError }}</span></div>
                </div>
              </div>
            </div>
            <div data-analysis-modal="" data-scan-id="analysisScanId" data-analysis-status="{{ analysisStatus }}"></div>
            <div data-log-modal="" data-scan-id="runLogScanId" data-analysis-status="{{ analysisStatus }}"></div>
            <div data-confirm-analysis-modal="" data-scan-id="confirmScanId" data-ok-clicked="runAnalysis(confirmScanId, true)"></div>
        `,
        controller: function(appState, columnsService, errorService, panelState, raydataService, requestSender, scanService, $scope, $interval) {
            $scope.analysisScanId = null;
            $scope.columnsService = columnsService;
            $scope.confirmScanId = null;
            $scope.isLoadingNewScans = false;
            $scope.isRefreshingScans = false;
            $scope.noScansReturned = false;
            $scope.pageLocationText = '';
            $scope.pdfSelectAllScans = false;
            $scope.pdfSelectedScans = {};
            $scope.raydataService = raydataService;
            $scope.runLogScanId = null;
            $scope.scans = [];
            $scope.showPdfColumn = $scope.analysisStatus === 'allStatuses';

            let scanOutputIndex = 1;
            let pendingRunAnalysis = {};
            let scanRequestInterval = null;
            let scanArgs = {
                pageCount: 0,
                pageNumber: 0,
                sortColumn: $scope.analysisStatus == 'queued' ? 'queue order' : 'start',
                sortOrder: $scope.analysisStatus == 'queued',
            };

            const errorOptions = {
                modelName: $scope.modelName,
                onError: data => {
                    cancelRequestInterval();
                    errorService.alertText(data.error);
                    panelState.setLoading($scope.modelName, false);
                },
                panelState: panelState,
            };

            function buildSearchTerms(searchTerms) {
                const res = [];
                if (! searchTerms) {
                    return res;
                }
                searchTerms.forEach(search => {
                    if (search.column != columnsService.selectSearchFieldText
                        && search.term) {
                        res.push({
                            column: search.column,
                            term: search.term,
                        });
                    }
                });
                return res;
            }

            function cancelRequestInterval() {
                if (scanRequestInterval) {
                    $interval.cancel(scanRequestInterval);
                    scanRequestInterval = null;
                }
            }

            function findScan(scanId) {
                return $scope.scans[
                    $scope.scans.findIndex(s => s.rduid === scanId)
                ];
            }

            function init() {
                setColumnHeaders();
                if (scanService.cachedScans($scope.analysisStatus)) {
                    loadScans(scanService.cachedScans($scope.analysisStatus));
                    sendScanRequest(false, false);
                }
                else {
                    sendScanRequest(true);
                }
            }

            function loadScans(scanInfo) {
                $scope.scans = scanInfo.scans.slice();
                columnsService.updateColumns(scanInfo.cols);
                $scope.isLoadingNewScans = false;
                $scope.isRefreshingScans = false;
                $scope.noScansReturned = $scope.scans.length === 0;
                for (const p in $scope.pdfSelectedScans) {
                    if (! findScan(p)) {
                        delete $scope.pdfSelectedScans[p];
                    }
                }
                if (raydataService.detailScan) {
                    for (const s in $scope.scans) {
                        if ($scope.scans[s].rduid === raydataService.detailScan.rduid) {
                            raydataService.setDetailScan($scope.scans[s]);
                            break;
                        }
                    }
                }
                scanArgs.pageCount = scanInfo.pageCount || 0;
                scanArgs.pageNumber = scanInfo.pageNumber;
                scanArgs.sortColumn = scanInfo.sortColumn;
                scanArgs.sortOrder = scanInfo.sortOrder;
                updatePageLocation();
            }

            function sendScanRequest(clearScans, resetPager) {
                if (clearScans) {
                    scanOutputIndex++;
                    $scope.isRefreshingScans = false;
                    $scope.scans = [];
                    $scope.isLoadingNewScans = true;
                    raydataService.setDetailScan(null);
                }
                if (resetPager) {
                    scanArgs.pageNumber = 0;
                }
                const m = appState.applicationState()[$scope.modelName];
                function doRequest() {
                    $scope.searchError = validateSearchFields();
                    if ($scope.searchError) {
                        $scope.isLoadingNewScans = false;
                        $scope.isRefreshingScans = false;
                        return;
                    }
                    if ($scope.isRefreshingScans) {
                        return;
                    }
                    $scope.isRefreshingScans = true;
                    $scope.noScansReturned = false;
                    const expectedOutputIndex = scanOutputIndex;
                    requestSender.sendStatelessCompute(
                        appState,
                        json => {
                            if (expectedOutputIndex != scanOutputIndex) {
                                return;
                            }
                            loadScans(scanService.setCachedScans($scope.analysisStatus, json.data));
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
                                pageNumber: scanArgs.pageNumber,
                                searchText: m.searchText,
                                searchTerms: buildSearchTerms(m.searchTerms),
                                sortColumn: scanArgs.sortColumn,
                                sortOrder: scanArgs.sortOrder,
                            }
                        },
                        errorOptions
                    );
                }
                cancelRequestInterval();
                // Send once and then will happen on $interval
                doRequest();
                scanRequestInterval = $interval(doRequest, 5000);
            }

            function setColumnHeaders() {
                $scope.columnHeaders = [
                    ...columnsService.defaultColumns($scope.analysisStatus, appState),
                    ...appState.models.metadataColumns.selected
                ];
            }

            function setScanPending(scanId) {
                const s = findScan(scanId);
                s.status = raydataService.ANALYSIS_STATUS_PENDING;
                delete pendingRunAnalysis[scanId];
            }

            function updatePageLocation() {
                if (scanArgs.pageCount > 1) {
                    $scope.pageLocationText = `page ${scanArgs.pageNumber + 1} / ${scanArgs.pageCount}`;
                }
                else {
                    $scope.pageLocationText = '';
                }
            }

            function validateSearchFields() {
                const m = appState.applicationState()[$scope.modelName];
                if ('searchStartTime' in m) {
                    if (!m.searchStartTime || !m.searchStopTime) {
                        return 'Missing start or stop time';
                    }
                    if (m.searchStartTime >= m.searchStopTime) {
                        return 'The selected start must be prior to the selected stop time';
                    }
                }
                return '';
            }

            $scope.arrowClass = column => {
                if (scanArgs.sortColumn !== column) {
                    return {};
                }
                return {
                    glyphicon: true,
                    [`glyphicon-arrow-${scanArgs.sortOrder ? 'up' : 'down'}`]: true,
                };
            };

            $scope.canNextPage = () => {
                return ! $scope.isLoadingNewScans && (scanArgs.pageNumber + 1 < scanArgs.pageCount);
            };

            $scope.canPreviousPage = () => {
                return ! $scope.isLoadingNewScans && (scanArgs.pageNumber > 0);
            };

            $scope.deleteCol = colName => {
                appState.models.metadataColumns.selected.splice(
                    appState.models.metadataColumns.selected.indexOf(colName),
                    1
                );
                appState.saveChanges('metadataColumns');
            };

            $scope.disableRunAnalysis = scan => {
                if (pendingRunAnalysis[scan.rduid]) {
                    return true;
                }
                return raydataService.ANALYSIS_STATUS_NON_STOPPED.includes(scan.status);
            };

            $scope.downloadSelectedAnalyses = () => {
                requestSender.sendStatelessCompute(
                    appState,
                    data => {
                        saveAs(data, "analysis_pdfs.zip");
                    },
                    {
                        method: 'download_analysis_pdfs',
                        responseType: 'blob',
                        args: {
                            rduids: Object.keys($scope.pdfSelectedScans),
                            catalogName: appState.applicationState().catalog.catalogName,
                        }
                    },
                    errorOptions,
                );
            };

            $scope.pageNext = () => {
                if ($scope.canNextPage()) {
                    scanArgs.pageNumber += 1;
                    updatePageLocation();
                    sendScanRequest(true);
                }
            };

            $scope.pagePrevious = () => {
                if ($scope.canPreviousPage()) {
                    scanArgs.pageNumber -= 1;
                    updatePageLocation();
                    sendScanRequest(true);
                }
            };

            $scope.refreshScans = () => {
                sendScanRequest(true, true);
            };

            $scope.runAnalysis = (scanId, forceRun) => {
                if (! forceRun) {
                    const scan = findScan(scanId);
                    // confirm if the scan has already completed successfully,
                    // or if the status is "none", but it has a pdf document available
                    if (appState.models.runAnalysis.confirmRunAnalysis === '0'
                        && (
                            scan.status === raydataService.ANALYSIS_STATUS_COMPLETED
                            || (scan.status === raydataService.ANALYSIS_STATUS_NONE && scan.pdf)
                        )
                    ) {
                        $scope.confirmScanId = scanId;
                        return;
                    }
                }
                pendingRunAnalysis[scanId] = true;
                requestSender.sendStatelessCompute(
                    appState,
                    json => {
                        setScanPending(scanId);
                    },
                    {
                        method: 'run_analysis',
                        args: {
                            catalogName: appState.applicationState().catalog.catalogName,
                            rduid: scanId,
                        }
                    },
                    {
                        modelName: $scope.modelName,
                        onError: data => {
                            cancelRequestInterval();
                            setScanPending(scanId);
                            errorService.alertText(data.error);
                            panelState.setLoading($scope.modelName, false);
                        },
                        panelState: panelState,
                    }
                );
            };

            $scope.setAnalysisScan = scan => {
                $scope.analysisScanId = scan.rduid;
            };

            $scope.showCheckbox = scan => {
                return scan.pdf;
            };

            $scope.showDeleteButton = index => {
                return index > columnsService.defaultColumns($scope.analysisStatus, appState).length - 1;
            };

            $scope.showPdfButton = () => {
                return $scope.showPdfColumn && Object.keys($scope.pdfSelectedScans).length;
            };

            $scope.showRunLogModal = scan => {
                $scope.runLogScanId = scan.rduid;
            };

            $scope.columnIsSortable = (column) => {
                return column !== 'stop';
            };

            $scope.sortCol = column => {
                if (! $scope.columnIsSortable(column)) {
                    return;
                }
                scanArgs.sortColumn = column;
                scanArgs.sortOrder = ! scanArgs.sortOrder;
                sendScanRequest(true, true);
            };

            $scope.togglePdfSelectAll = () => {
                $scope.pdfSelectedScans = {};
                $scope.pdfSelectAllScans = ! $scope.pdfSelectAllScans;
                if ($scope.pdfSelectAllScans) {
                    $scope.scans.forEach(s => {
                        if (s.pdf) {
                            $scope.pdfSelectedScans[s.rduid] = true;
                        }
                    });
                }
            };

            $scope.togglePdfSelectScan = rduid => {
                if (rduid in $scope.pdfSelectedScans) {
                    delete $scope.pdfSelectedScans[rduid];
                } else {
                    $scope.pdfSelectedScans[rduid] = true;
                }
            };

            $scope.$on(`${$scope.modelName}.changed`, () => sendScanRequest(true, true));
            $scope.$on('catalog.changed', () => sendScanRequest(true, true));
            $scope.$on('metadataColumns.changed', () => {
                sendScanRequest(true);
                setColumnHeaders();
            });
            $scope.$on("$destroy", cancelRequestInterval);

            init();
        },
    };
});

SIREPO.app.directive('scanCellValue', function() {
    return {
        restrict: 'A',
        scope: {
            scanCellValue: '=',
            columnName: '=',
        },
        template: `
            <div class="pull-right" data-ng-show="canExpand">
              <button class="btn btn-default btn-xs" data-ng-click="toggleExpand()">
                <span class="glyphicon"
                  data-ng-class="{'glyphicon-chevron-down': ! isExpanded, 'glyphicon-chevron-up': isExpanded}">
                </span>
              </button>
            </div>
            <div style="white-space: pre-wrap">{{ getScanFieldText() }}<span data-ng-show="canExpand && !isExpanded">...</span></div>
        `,
        controller: function(timeService, utilities, $scope) {

            $scope.canExpand = false;
            $scope.isExpanded = false;

            function objectToText(value) {
                const r = utilities.objectToText(value);
                if ($scope.isExpanded) {
                    return r;
                }
                const t = utilities.trimText(r, 5, 300);
                $scope.canExpand = t != r;
                return t;
            }

            $scope.getScanFieldText = () => {
                if (['start', 'stop'].includes($scope.columnName)) {
                    return timeService.unixTimeToDateString($scope.scanCellValue);
                }
                if (angular.isObject($scope.scanCellValue)) {
                    return objectToText($scope.scanCellValue);
                }
                return $scope.scanCellValue;
            };

            $scope.toggleExpand = () => {
                $scope.isExpanded = ! $scope.isExpanded;
            };
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
                    $scope.$apply();
                });
                $scope.logIsLoading = true;
                el.modal('show');
                requestSender.sendStatelessCompute(
                    appState,
                    json => {
                        $scope.logIsLoading = false;
                        $scope.log = json.run_log;
                        $scope.logPath = json.log_path;
                    },
                    {
                        method: 'analysis_run_log',
                        args: {
			    catalogName: appState.applicationState().catalog.catalogName,
			    rduid: $scope.scanId,
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
                                  <div data-png-image="" data-image="{{ i.data }}"></div>
                                </div>
                              </div>
                            </div>
                            <div data-ng-repeat="j in jsonFiles">
                              <div class="panel panel-info">
                                <div class="panel-heading"><span class="sr-panel-heading">{{ j.filename }}</span></div>
                                <div class="panel-body">
                                  <pre style="overflow: scroll; height: 150px">{{ formatJsonFile(j.data) }}</pre>
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
                $scope.images = null;
                $scope.jsonFiles = null;
                const el = $('#' + $scope.analysisModalId);
                el.modal('show');
                el.on('hidden.bs.modal', () => {
                    $scope.scanId = null;
                    el.off();
                    $scope.$apply();
                });
                requestSender.sendStatelessCompute(
                    appState,
                    json => {
                        $scope.images = json.images;
                        $scope.jsonFiles = json.jsonFiles;
                    },
                    {
                        method: 'analysis_output',
                        args: {
                            catalogName: appState.models.catalog.catalogName,
                            rduid: $scope.scanId
                        }
                    },
                    {
                        onError: data => {
                            errorService.alertText(data.error);
                        },
                    }
                );
            }

            $scope.formatJsonFile = contents => {
                return JSON.stringify(contents, undefined, 2);
            };

            $scope.$watch('scanId', () => {
                if ($scope.scanId !== null) {
                    showModal();
                }
            });
        },
    };
});

SIREPO.app.directive('confirmAnalysisModal', function() {
    return {
        restrict: 'A',
        scope: {
            scanId: '=',
            okClicked: '&',
        },
        template: `
           <div data-confirmation-modal="" data-id="{{ modalId }}" data-title="Run Analysis" data-ok-text="Run Analysis" data-ok-clicked="okClicked()">
              <p>This scan has already had an analysis completed. Would you like to re-run the analysis?</p>
              <form class="form-horizontal" autocomplete="off">
                <div data-label-size="10" data-field-size="2" data-model-field="\'confirmRunAnalysis\'" data-model-name="\'runAnalysis\'"></div>
              </form>
            </div>
        `,
        controller: function(appState, errorService, requestSender, $scope) {
            $scope.modalId = 'raydata-confirm-run-analysis';
            $scope.$watch('scanId', () => {
                if ($scope.scanId !== null) {
                    const el = $('#' + $scope.modalId);
                    el.on('hidden.bs.modal', function() {
                        $scope.scanId = null;
                        el.off();
                        $scope.$apply();
                    });
                    el.modal('show');
                }
            });
        },
    };
});

SIREPO.app.directive('columnList', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            },
        template: `
            <select data-ng-if="columnsService.allColumnsWithHeading"
              class="form-control pull-right" style="width: auto"
              data-ng-model="model[field]"
              data-ng-options="item as item for item in columnsService.allColumnsWithHeading">
            </select>
        `,
        controller: function($scope, columnsService) {
            $scope.columnsService = columnsService;
        },
    };
});

SIREPO.app.directive('scanDetail', function() {
    return {
        restrict: 'A',
        scope: {
            scan: '<',
        },
        template: `
            <div><strong>Scan Detail</strong></div>
            <div class="well" style="height: 250px; overflow: auto;">
            <div data-ng-if="scan">
              <div><strong>Scan Id:</strong> {{ scan.rduid }}</div>
              <div data-ng-if="analysisElapsedTime()"><strong>Analysis Elapsed Time:</strong> {{ analysisElapsedTime() }} seconds</div>
              <div data-ng-if="detailedStatusFile()">
                <div><strong>Current Consecutive Failures:</strong> {{ consecutiveFailures() }}</div>
              </div>
              <div data-ng-if="detailedStatusFile()">
                <div><strong>Most Recent Status</strong></div>
                <pre>{{ currentStatus() }}</pre>
              </div>
              <div data-ng-if="detailedStatusFile()">
                <div><strong>Detailed Status File</strong></div>
                <pre>{{ detailedStatus() }}</pre>
              </div>
            </div>
            </div>
`,
        controller: function($scope, columnsService, utilities) {
            function failureInRun(run) {
                let r = false;
                for (const f of Object.values($scope.detailedStatusFile()[run])) {
                    if (f.status === 'failed') {
                        r = true;
                    }
                }
                return r;
            }

            function getSortedRunIndexes() {
                return Object.keys($scope.detailedStatusFile()).map((x) => parseInt(x)).sort();
            }

            function mostRecentAnalysisDetails() {
                return $scope.detailedStatusFile()? $scope.detailedStatusFile()[Math.max(...getSortedRunIndexes())] : '';
             }

            $scope.analysisElapsedTime = () => {
                return $scope.scan && $scope.scan.analysis_elapsed_time ? $scope.scan.analysis_elapsed_time : null;
            };

            $scope.consecutiveFailures = () => {
                if (! $scope.detailedStatusFile()) {
                    return '';
                }
                let r = 0;
                for (const k of getSortedRunIndexes().reverse()) {
                    if (failureInRun(k)) {
                        r += 1;
                    } else {
                        return r;
                    }
                }

                return r;
            };

            $scope.currentStatus = () => {
                let r = '';
                for (const k of Object.keys(mostRecentAnalysisDetails())) {
                    r += k + ': ' + mostRecentAnalysisDetails()[k].status + '\n';
                }
                return r;
            };

            $scope.detailedStatus = () => {
                return utilities.objectToText($scope.detailedStatusFile()).replace(
                    /(start:|stop:)(\s*)(\d+\.?\d*)/gi,
                    (_, p1, p2, p3) => {
                        return p1 + p2 + (new Date(parseFloat(p3)*1000)).toString();
                    }
                )
                ;
            };

            $scope.detailedStatusFile = () => {
                return $scope.scan && $scope.scan.detailed_status && Object.keys($scope.scan.detailed_status).length > 0 ? $scope.scan.detailed_status : null;
            };
        },
    };
});


SIREPO.app.directive('searchTerms', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <div data-ng-if="showTerms()" class="raydata-search-terms col-sm-12">
              <div class="form-group"
                data-ng-repeat="searchTerm in model.searchTerms track by $index"
                data-ng-show="showRow($index)">
                <div class="col-sm-2"></div>
                <div data-field-editor="'column'" data-label-size="0"
                   data-field-size="3" data-model-name="'searchTerm'"
                   data-model="searchTerm"></div>
                 <div data-field-editor="'term'" data-label-size="0"
                   data-field-size="5" data-model-name="'searchTerm'"
                   data-model="searchTerm"></div>
                 <div class="col-sm-2" style="margin-top: 5px; margin-left: -15px"
                   data-ng-show="! isEmpty($index)">
                   <button class="btn btn-danger btn-xs" type="button"
                     data-ng-click="deleteRow($index)">
                     <span class="glyphicon glyphicon-remove"></span>
                   </button>
                 </div>
               </div>
            </div>`,
        controller: function(appState, columnsService, $scope) {
            $scope.columnsService = columnsService;
            const maxSearchTerms = 10;
            let isInitialized = false;

            function updateTerms() {
                let needSave = ! $scope.model.searchTerms.length;
                for (let i = 0; i < maxSearchTerms; i++) {
                    if (! $scope.model.searchTerms[i]) {
                        $scope.model.searchTerms[i] = {
                            column: columnsService.selectSearchFieldText,
                            term: '',
                        };
                    }
                }
                if (needSave) {
                    appState.saveQuietly('runAnalysis');
                }
            }

            $scope.deleteRow = idx => {
                $scope.model.searchTerms.splice(idx, 1);
                updateTerms();
            };

            $scope.isEmpty = idx => {
                const search = $scope.model.searchTerms[idx];
                return (
                    search.column != columnsService.selectSearchFieldText
                    || search.term
                ) ? false : true;
            };

            $scope.showRow = idx => (idx == 0) || ! $scope.isEmpty(idx - 1);

            $scope.showTerms = () => {
                if (columnsService.allColumns) {
                    if (! isInitialized) {
                        isInitialized = true;
                        updateTerms();
                    }
                    return true;
                }
                return false;
            };
        },
    };
});

SIREPO.app.directive('searchTermText', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            },
        template: `
          <input data-ng-disabled="disabled()" data-ng-model="model[field]" class="form-control" data-lpignore="true" />
        `,
        controller: function($scope, columnsService) {
            $scope.disabled = () => {
                return $scope.model.column === columnsService.selectSearchFieldText;
            };
        },
    };
});


SIREPO.app.directive('queueOrder', function() {
    return {
        restrict: 'A',
        scope: {
            scan: '=',
            numberOfScans: '@',
            refreshScans: '&',
        },
        template: `
            {{ scan['queue order'] }} &nbsp;
            <span data-ng-show="scan['queue order'] > 0">
              <button data-ng-repeat="b in buttons track by $index" type="button"
                class="btn btn-info btn-xs" title="{{ b.title }}" data-ng-click="b.click()"
                data-ng-style="{ visibility: b.visible() ? 'visible' : 'hidden', transform: b.rotate }"><span
                  class="glyphicon glyphicon-step-forward"></span>
              </button>
            </span>
        `,
        controller: function(appState, requestSender, $scope) {
            $scope.buttons = [
                {
                    title: 'Move to end of queue',
                    rotate: 'rotate(90deg)',
                    visible: () => $scope.scan['queue order'] < $scope.numberOfScans - 1,
                    click: () => reorderScan('last'),
                },
                {
                    title: 'Move to beginning of queue',
                    rotate: 'rotate(270deg)',
                    visible: () => $scope.scan['queue order'] > 1,
                    click: () => reorderScan('first'),
                },
            ];

            function reorderScan(action) {
                requestSender.sendStatelessCompute(
                    appState,
                    () => $scope.refreshScans(),
                    {
                        method: 'reorder_scan',
                        args: {
                            catalogName: appState.models.catalog.catalogName,
                            rduid: $scope.scan.rduid,
                            action: action,
                        }
                    },
                );
            }
        },
    };
});
