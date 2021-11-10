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

SIREPO.app.factory('raydataService', function(appState, simulationDataCache, timeService) {
    const self = {};
    let id = 0;

    self.addScanInfoTableColsToCache = (cols) => {
	simulationDataCache.scanInfoTableCols = cols;
	return cols;
    };

    self.addScanToCache = (scan) => {
	if (!simulationDataCache.scans) {
	    simulationDataCache.scans = {};
	}
	simulationDataCache.scans[scan.uid] = scan;
    };

    self.computeModel = function(analysisModel) {
        return 'animation';
    };

    self.getScanField = (scan, field) => {
	if (['start', 'stop'].includes(field)) {
	    return timeService.unixTimeToDateString(scan[field]);
	}
	return scan[field];
    };

    self.getScanInfoTableHeader = (cols) => {
	return cols.length > 0 ? ['select'].concat(cols) : [];
    };


    self.nextPngImageId = () => {
	return 'raydata-png-image-' + (++id);
    };


    self.removeScanFromCache = (scan) => {
	if (!simulationDataCache.scans) {
	    return;
	}
	delete simulationDataCache.scans[scan.uid];
    };

    self.setPngDataUrl = (element, png) => {
	element.src = 'data:image/png;base64,' + png;
    };

    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('AnalysisController', function(appState, frameCache, panelState, persistentSimulation, raydataService, $scope) {
    const self = this;
    self.appState = appState;
    self.simScope = $scope;
    self.pngOutputFiles = [];

    self.simHandleStatus = function (data) {
        if (data.frameCount) {
            frameCache.setFrameCount(data.frameCount);
        }
	if ((data.pngOutputFiles || []).length > 0) {
	    const f = [];
	    data.pngOutputFiles.forEach((e) => {
		if (self.pngOutputFiles.includes(e.name)) {
		    return;
		}
		appState.models[e.name] = {
		    filename: e.filename
		};
		f.push(e.name);
		if (! panelState.isHidden(e.name)) {
		    panelState.toggleHidden(e.name);
		}
	    });
	    appState.saveChanges(f, () => self.pngOutputFiles.push(...f));
	} else {
	    self.pngOutputFiles = [];
	}
    };

    self.simState = persistentSimulation.initSimulationState(self);
    return self;
});

SIREPO.app.controller('DataSourceController', function() {
    // TODO(e-carlin): only let certain files to be uploaded
    const self = this;
    return self;
});

SIREPO.app.controller('MetadataController', function(appState) {
    const self = this;

    self.haveVisualizationId = () => {
	return appState.models.scans.visualizationId;
    };

    self.metadataTableArgs = (category) => {
	return {
	    category: category
	};
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
		<div data-ng-if="nav.isLoaded()" data-sim-sections="">
                  <li class="sim-section" data-ng-class="{active: nav.isActive('data-source')}"><a href data-ng-click="nav.openSection('dataSource')"><span class="glyphicon glyphicon-picture"></span> Data Source</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('metadata')}"><a data-ng-href="{{ nav.sectionURL('metadata') }}"><span class="glyphicon glyphicon-flash"></span> Metadata</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('analysis')}"><a data-ng-href="{{ nav.sectionURL('analysis') }}"><span class="glyphicon glyphicon-picture"></span> Analysis</a></li>
                </div>
              </app-header-right-sim-loaded>
	    </div>
        `
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

	    const elementForKey = (key) => {
		return $('#' + $scope.elementId(key));
	    };

	    const getMetadata = () => {
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
			panelStateHandle: panelState,
		    }
		);
	    };

	    const indexOfKey = (key) => {
		for (let i in $scope.data) {
		    if ($scope.data[i][0] === key) {
			return i;
		    }
		}
		throw new Error(`No key=${key} in data=${$scope.data}`);
	    };

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
	    modelName: '@'
	},
        template: `<img class="img-responsive" id="{{ id }}" />`,
	controller: function(raydataService, $scope) {
            plotting.setTextOnlyReport($scope);
	    $scope.id = raydataService.nextPngImageId();

            $scope.load = (json) => {
		raydataService.setPngDataUrl($('#' + $scope.id)[0], json.image);
            };
	},
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('scanSelector', function(panelState) {
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
                    <td><input type="checkbox" data-ng-checked="s.selected" data-ng-click="selectOrDeselect(s)"/></td>
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

	    const searchStartOrStopTimeKey = (startOrStop) => {
		return `search${startOrStop}Time`;
	    };

	    startOrStop.forEach((x) => {
		const k = searchStartOrStopTimeKey(x);
		$scope[k] = appState.models.scans[k] ? timeService.unixTimeToDate(appState.models.scans[k]) : null;
	    });

	    $scope.getHeader = () => raydataService.getScanInfoTableHeader(cols);

	    $scope.getScanField = raydataService.getScanField;


	    $scope.search = () => {
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
			cols = raydataService.addScanInfoTableColsToCache(json.data.cols);
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
			panelStateHandle: panelState,
			onError: (data) => {
			    errorService.alertText(data.error);
			    panelState.setLoading($scope.args.modelKey, false);
			}
		    }
		);
	    };

	    $scope.showSearchButton = () => {
		return $scope.searchForm.$dirty && $scope.searchStartTime && $scope.searchStopTime;
	    };

	    $scope.selectOrDeselect = (scan) => {
		scan.selected = !scan.selected;
		if (scan.selected) {
		    appState.models.scans.selected[scan.uid] = true;
		    raydataService.addScanToCache(scan);
		} else {
		    if (appState.models.scans.visualizationId == scan.uid) {
			appState.models.scans.visualizationId = null;
		    }
		    delete appState.models.scans.selected[scan.uid];
		    raydataService.removeScanFromCache(scan, appState);
		}
		appState.saveChanges('scans');
	    };
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
	    <div data-ng-if="!haveScans()">
            No scans selected. Visit the <a href data-ng-click="redirectToDataSource()"><span class="glyphicon glyphicon-picture"></span> Data Source</a> tab to select scans.
	    </div>
	    <div data-ng-if="haveScans()">
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
        controller: function(appState, panelState, raydataService, requestSender, simulationDataCache, $scope) {
	    $scope.appState = appState;
            $scope.modelName = 'scans';
            $scope.fields = ['visualizationId'];

	    let cols = [];

	    const getScanInfo = () => {
		const s = appState.models.scans.selected;
		if (Object.keys(s).every((e) => e in (simulationDataCache.scans || {}))) {
		    $scope.scans = Object.keys(s).map((u) => simulationDataCache.scans[u]).sort((a, b) => {
			return a.start > b.start ? 1 : -1;
		    });
		    cols = simulationDataCache.scanInfoTableCols;
		    return;
		}
		requestSender.sendStatelessCompute(
		    appState,
		    (json) => {
			$scope.scans = json.data.scans;
			$scope.scans.forEach(raydataService.addScanToCache);
			cols = raydataService.addScanInfoTableColsToCache(json.data.cols);
		    },
		    {
			method: 'scan_info',
			scans: s,
		    },
		    {
			modelName: $scope.args.modelKey,
			panelStateHandle: panelState,
		    }
		);
	    };

	    $scope.getHeader = () => raydataService.getScanInfoTableHeader(cols);

	    $scope.getScanField = raydataService.getScanField;

	    $scope.haveScans = () => {
		return ! $.isEmptyObject(appState.models.scans.selected);
	    };

	    $scope.redirectToDataSource = () => requestSender.localRedirect(
		'dataSource',
		{':simulationId': appState.models.simulation.simulationId}
	    );

	    appState.watchModelFields($scope, ['scans.selected'], getScanInfo);
	    getScanInfo();
        },
    };
});
