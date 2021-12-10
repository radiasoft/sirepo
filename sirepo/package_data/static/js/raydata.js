'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appReportTypes  = ['analysis', 'general', 'plan'].map((c) => {
	return `<div data-ng-switch-when="${c}Metadata" data-metadata-table="" data-category="${c}" class="sr-plot" data-model-name="{{ modelKey }}"></div>`;
    }).join('') + `
        <div data-ng-switch-when="pngImage" data-png-image="" class="sr-plot" data-model-name="{{ modelKey }}"></div>
    `;
});

SIREPO.app.factory('raydataService', function(appState, requestSender, runMulti, simulationDataCache, timeService, $rootScope) {
    const self = {};
    let id = 0;

    function removeScanFromCache(scan) {
	if (! simulationDataCache.scans) {
	    return;
	}
	delete simulationDataCache.scans[scan.uid];
    }

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
	    const s = Object.keys(appState.models.scans.selected);
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
		    method: 'scan_info',
		    scans: s,
		},
		options
	    );
	}
	let haveRecursed = false;
	helper(successCallback, options);
    };

    self.getScansRequestPayload = function(scanUuids) {
	return (scanUuids || Object.keys(appState.models.scans.selected)).map(s => {
	    return {
		models: appState.models,
		report: s,
		simulationType: SIREPO.APP_SCHEMA.simulationType,
		simulationId: appState.models.simulation.simulationId,
	    };
	});
    };

    self.maybeToggleScanSelection = function(scan, selected) {
	if (! ('selected' in scan)) {
	    scan.selected = false;
	}
	scan.selected = !scan.selected;
	if (selected !== undefined) {
	    scan.selected = selected;
	}
	if (scan.selected) {
	    appState.models.scans.selected[scan.uid] = true;
	    self.updateScansInCache([scan]);
	}
	else {
	    if (appState.models.scans.visualizationId == scan.uid) {
		appState.models.scans.visualizationId = null;
	    }
	    delete appState.models.scans.selected[scan.uid];
	    removeScanFromCache(scan, appState);
	}
	appState.saveChanges('scans');
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
    }

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
	appState.models.pollBlueskyForScansAnimation.start = timeService.getCurrentUnixTime();
	appState.saveChanges('pollBlueskyForScansAnimation', self.simState.runSimulation);
    };

    return self;
});

SIREPO.app.controller('DataSourceController', function() {
    // TODO(e-carlin): only let certain files to be uploaded
    const self = this;
    return self;
});

SIREPO.app.controller('MetadataController', function(appState) {
    const self = this;

    self.haveVisualizationId = function() {
	return appState.models.scans.visualizationId;
    };

    self.metadataTableArgs = function(category) {
	return {
	    category: category
	};
    };

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

	    function getSelectedScans() {
		return Object.keys(appState.models.scans.selected).map(s => {
		    return {
			models: appState.models,
			report: s,
			simulationType: SIREPO.APP_SCHEMA.simulationType,
			simulationId: appState.models.simulation.simulationId
		    };
		});
	    }

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
		$scope.$on('scans.changed', () => {
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
                  <li class="sim-section" data-ng-if="haveScans()" data-ng-class="{active: nav.isActive('metadata')}"><a data-ng-href="{{ nav.sectionURL('metadata') }}"><span class="glyphicon glyphicon-flash"></span> Metadata</a></li>
                  <li class="sim-section" data-ng-if="haveScans()" data-ng-class="{active: nav.isActive('analysis')}"><a data-ng-href="{{ nav.sectionURL('analysis') }}"><span class="glyphicon glyphicon-picture"></span> Analysis</a></li>
                </div>
              </app-header-right-sim-loaded>
	    </div>
        `,
	controller: function($scope) {
	    $scope.haveScans = function() {
		return ! $.isEmptyObject(appState.models.scans.selected);
	    };
	}
    };
});

SIREPO.app.directive('metadataTable', function() {
    return {
        restrict: 'A',
        scope: {
	    args: '='
	},
        template: `
            <div class="table-responsive" data-ng-if="data">
              <table class="table">
                <thead>
                <tr>
                  <th>Field</th>
                  <th>Value</th>
                  <th></th>
                  <th></th>
                </tr>
                </thead>
                <tbody>
                <tr data-ng-repeat="(_, v) in data">
                  <td>{{ v[0] }}</td>
                  <td id="{{ elementId(v[0]) }}" class="raydata-overflow-text">{{ v[1] }}</td>
                  <td><button class="glyphicon glyphicon-plus" data-ng-if="wouldOverflow(v[0])" data-ng-click="toggleExpanded(v[0])"></span></td>
                  <td><button class="glyphicon glyphicon-minus" data-ng-if="expanded[v[0]]" data-ng-click="toggleExpanded(v[0])"></span></td>
                </tr>
                </tbody>
              </table>
            </div>
	`,
	controller: function(appState, panelState, requestSender, $scope) {
	    $scope.expanded = {};

	    function elementForKey(key) {
		return $('#' + $scope.elementId(key));
	    }

	    function getMetadata(){
		const u = appState.models.scans.visualizationId;
		if (! u) {
		    $scope.data = null;
		    return;
		}
		requestSender.sendStatelessCompute(
		    appState,
		    (data) => {
			$scope.data = Object.entries(data.data).map(([k, v]) => [k, v]);
		    },
		    {
			method: 'metadata',
			category: $scope.args.category,
			uid: u
		    },
		    {
			modelName: $scope.args.modelKey,
			panelState: panelState,
		    }
		);
	    }

	    function indexOfKey(key) {
		for (let i in $scope.data) {
		    if ($scope.data[i][0] === key) {
			return i;
		    }
		}
		throw new Error(`No key=${key} in data=${$scope.data}`);
	    }

	    $scope.elementId = function(key) {
		return 'metadata-table-' + $scope.args.category + '-' + indexOfKey(key);
	    };


	    $scope.wouldOverflow = function(key) {
		const e = elementForKey(key);
		return e.prop('clientWidth') < e.prop('scrollWidth');
	    };

	    $scope.toggleExpanded = function(key) {
		if ( key in $scope.expanded ) {
		    $scope.expanded[key] = ! $scope.expanded[key];
		}
		else {
		    $scope.expanded[key] = true;
		}
		elementForKey(key).toggleClass('raydata-overflow-text');
	    };

	    // Cannot use appState.watchModelFields because it does
	    // not update when values are null which visualizationId
	    // will be set to when no scan is checked
            $scope.$watch(
		() => appState.models.scans.visualizationId,
		getMetadata
	    );
	    appState.whenModelsLoaded($scope, getMetadata);
        },
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
	    args: '='
	},
        template: `
	    <div>
	      <form name="searchForm">
	        <div class="form-group col-xs-4 row">
	          <label>Start</label>
	          <input type="datetime-local" class="form-control" ng-model="searchStartTime" required >
	        </div>
		<div class="clearfix"></div>
	        <div class="form-group col-xs-4 row">
	          <label>Stop</label>
	          <input type="datetime-local" class="form-control" ng-model="searchStopTime" required >
	        </div>
		<div class="clearfix"></div>
                <button type="submit" class="btn btn-primary" data-ng-show="showSearchButton()" data-ng-click="search()">Search</button>
	      </form>
              <table class="table table-striped table-hover col-sm-4">
                <thead>
                  <tr>
                    <th data-ng-repeat="h in getHeader()">{{ h }}</th>
                  </tr>
                </thead>
                <tbody ng-repeat="s in scans">
                  <tr>
                    <td><input type="checkbox" data-ng-checked="s.selected" data-ng-click="toggleScanSelection(s)"/></td>
                    <td data-ng-repeat="c in getHeader().slice(1)">{{ getScanField(s, c) }}</td>
                  </tr>
                </tbody>
              </table>
	    </div>
        `,
        controller: function(appState, errorService, panelState, raydataService, requestSender, timeService, $scope) {
	    let cols = [];
	    const startOrStop = ['Start', 'Stop'];
	    $scope.scans = [];

	    function searchStartOrStopTimeKey(startOrStop) {
		return `search${startOrStop}Time`;
	    }

	    startOrStop.forEach((x) => {
		const k = searchStartOrStopTimeKey(x);
		$scope[k] = appState.models.scans[k] ? timeService.unixTimeToDate(appState.models.scans[k]) : null;
	    });

	    $scope.getHeader = function() {
		return raydataService.getScanInfoTableHeader('select', cols);
	    };

	    $scope.getScanField = raydataService.getScanField;


	    $scope.search = function() {
		for (let i = 0; i < startOrStop.length; i++) {
		    const k = searchStartOrStopTimeKey(startOrStop[i]);
		    if ($scope[k]) {
			appState.models.scans[k] = timeService.getUnixTime($scope[k]);
		    }
		    if (!appState.models.scans[k]) {
			return;
		    }
		}
		$scope.searchForm.$setPristine();
		requestSender.sendStatelessCompute(
		    appState,
		    (json) => {
			$scope.scans = [];
			json.data.scans.forEach((s) => {
			    s.selected = s.uid in appState.models.scans.selected;
			    $scope.scans.push(s);
			});
			// Remove scans that were selected but are not in the new search results
			Object.keys(appState.models.scans.selected).forEach((u) => {
			    if ($scope.scans.some((e) => e.uid === u)) {
				return;
			    }
			    if (appState.models.scans.visualizationId === u) {
				appState.models.scans.visualizationId = null;
			    }
			    delete appState.models.scans.selected[u];
			});
			cols = raydataService.updateScanInfoTableColsInCache(json.data.cols);
			appState.saveChanges('scans');
		    },
		    {
			method: 'scans',
			searchStartTime: appState.models.scans[
			    searchStartOrStopTimeKey(startOrStop[0])
			],
			searchStopTime: appState.models.scans[
			    searchStartOrStopTimeKey(startOrStop[1])
			],
		    },
		    {
			modelName: $scope.args.modelKey,
			onError: (data) => {
			    errorService.alertText(data.error);
			    panelState.setLoading($scope.args.modelKey, false);
			},
			panelState: panelState,
		    }
		);
	    };

	    $scope.showSearchButton = function() {
		return $scope.searchForm.$dirty && $scope.searchStartTime && $scope.searchStopTime;
	    };

	    $scope.toggleScanSelection = raydataService.maybeToggleScanSelection;
	    appState.whenModelsLoaded($scope, () => $scope.search());
        },
    };
});

SIREPO.app.directive('visualizationScanSelector', function() {
    return {
        restrict: 'A',
        scope: {
	    args: '='
	},
        template: `
	    <div>
	      <form name="form">
                <table class="table table-striped table-hover col-sm-4">
                  <thead>
                    <tr>
                      <th data-ng-repeat="h in getHeader()">{{ h }}</th>
                    </tr>
                  </thead>
                  <tbody ng-repeat="s in scans">
                    <tr>
                      <td><input type="radio" data-ng-model="appState. models.scans.visualizationId" data-ng-value="s.uid"/></td>
                      <td data-ng-repeat="c in getHeader().slice(1)">{{ getScanField(s, c) }}</td>
                    </tr>
                  </tbody>
                </table>
                <div class="col-sm-12 text-center" data-buttons="" data-model-name="modelName" data-fields="fields"></div>
	      </form>
	    </div>
        `,
        controller: function(appState, panelState, raydataService, $scope) {
	    $scope.appState = appState;
            $scope.modelName = 'scans';
            $scope.fields = ['visualizationId'];

	    let cols = [];

	    function getScanInfo() {
		raydataService.getScansInfo(
		    (scans, colz) => {
			$scope.scans = scans;
			cols = colz;
		    },
		    {
			modelName: $scope.args.modelKey,
			panelState: panelState,
		    }
		);
	    }

	    $scope.getHeader = function() {
		return raydataService.getScanInfoTableHeader('select', cols);
	    };

	    $scope.getScanField = raydataService.getScanField;

	    appState.watchModelFields($scope, ['scans.selected'], getScanInfo);
	    getScanInfo();
        },
    };
});
