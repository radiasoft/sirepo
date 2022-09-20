'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="DateTimePicker" data-ng-class="fieldClass">
          <div data-date-time-picker="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="QueuedScansTable" class="col-sm-12">
          <div data-scans-table="" data-model-name="modelName"></div>
        </div>
        <div data-ng-switch-when="CompletedScansTable" class="col-sm-12">
          <div data-scans-table-with-modal="" data-model-name="modelName"></div>
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

SIREPO.app.controller('AnalysisCompletedController', function() {
    const self = this;
    return self;
});

SIREPO.app.controller('ReplayController', function() {
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('analysis-completed')}"><a href data-ng-click="nav.openSection('analysisCompleted')"><span class="glyphicon glyphicon-picture"></span> Completed</a></li>
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
            <select class="form-control" data-ng-model="model[field]" data-ng-options="name as name for name in catalogNames"></select>
        `,
        controller: function($scope, appState, errorService, requestSender) {
            $scope.catalogNames = [];

            requestSender.sendStatelessCompute(
                appState,
                json => {
                    $scope.catalogNames = json.data.catalogs;
                },
                {
                    method: 'catalog_names',
                },
                {
                    onError: data => {
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
          <button type="submit" class="btn btn-primary" data-ng-click="">Start Replay</button>
        `,
    };
});

SIREPO.app.directive('scansTableWithModal', function() {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
        },
        template: `
            <div data-scans-table="" data-model-name="modelName" data-selected-scan="selectedScan" data-scans-status="scansStatus"></div>
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
        `,
        controller: function(appState, requestSender, $scope) {
            $scope.selectedScan = null;
            $scope.scansStatus = 'completed_scans';

            $scope.showAnalysisOutputModal = (scan) => {
                const el = $('#sr-analysis-output');
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

            $scope.$watch('selectedScan', () => {
                if ($scope.selectedScan !== null) {
                    $scope.showAnalysisOutputModal($scope.selectedScan);
                }
            });
        },
    };
});

SIREPO.app.directive('scansTable', function() {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            selectedScan: '=?',
            scansStatus: '=?',
        },
        template: `
            <div data-show-loading-and-error="" data-model-key="scans">
              <div>
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
                    <tr ng-repeat="s in scans | orderBy:orderByColumn:reverseSortScans" data-ng-click="setSelectedScan(s)">
                      <td data-ng-repeat="c in columnHeaders.slice(0)">{{ getScanField(s, c) }}</td>
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

            $scope.saveColumnChanges = () => {
                $scope.setColumnHeaders();
                $scope.setAvailableColumns();
            };

            $scope.sendScanRequest = function() {
                if ($scope.scansStatus && (!appState.models.completedScans.searchStartTime || !appState.models.completedScans.searchStopTime)) {
                    return;
                }
                requestSender.sendStatelessCompute(
                    appState,
                    (json) => {
                        $scope.scans = json.data.scans.slice();
                    },
                    {
                        catalogName: appState.models.catalog.catalogName,
                        method: 'scans',
                        scansStatus: $scope.scansStatus ? $scope.scansStatus : 'queued_scans',
                        searchStartTime: appState.models.completedScans[
                            searchStartOrStopTimeKey(startOrStop[0])
                        ],
                        searchStopTime: appState.models.completedScans[
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
                    ...$scope.defaultColumns,
                    ...appState.models.metadataColumns.selected
                ];
            };

            $scope.setSelectedScan = (scan) => {
                $scope.selectedScan = scan;
            };

            $scope.showDeleteButton = (index) => {
                return index > $scope.defaultColumns.length - 1 && index === hoveredIndex;
            };

            $scope.sortCol = (column) => {
                if (column === 'selected') {
                    return;
                }
                $scope.orderByColumn = column;
                $scope.reverseSortScans = ! $scope.reverseSortScans;
            };

            $scope.$on('completedScans.changed', $scope.sendScanRequest);
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
                    catalogName: appState.models.catalog.catalogName,
                    method: 'scan_fields',
                }
            );

        },
    };
});
