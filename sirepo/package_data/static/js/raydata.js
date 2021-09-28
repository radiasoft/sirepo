'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appReportTypes  = ['analysis', 'general', 'plan'].map((t) => {
	return `<div data-ng-switch-when="${t}Metadata" data-metadata-table="" data-type="${t}"></div>`;
    }).join('');
});

SIREPO.app.factory('raydataService', function(appState) {
    const self = {};
    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('AnalysisController', function(appState, frameCache, persistentSimulation, $scope) {
    const self = this;
    self.appState = appState;
    self.simScope = $scope;
    self.simComputeModel = 'analysisAnimation';
    self.simHandleStatus = function (data) {
        if (data.frameCount) {
            frameCache.setFrameCount(data.frameCount);
        }
    };
    self.simState = persistentSimulation.initSimulationState(self);
    return self;
});

SIREPO.app.controller('MetadataController', function(appState, frameCache, persistentSimulation, $scope) {
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
            '<div data-common-footer="nav"></div>'
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'metadata\')}"><a data-ng-href="{{ nav.sectionURL(\'metadata\') }}"><span class="glyphicon glyphicon-flash"></span> Metadata</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'analysis\')}"><a data-ng-href="{{ nav.sectionURL(\'analysis\') }}"><span class="glyphicon glyphicon-picture"></span> Analysis</a></li>
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
	    type: '@'
	},
        template: `
            <div data-ng-if="data">
              <div>
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
                    <td><button class="glyphicon glyphicon-plus" data-ng-if="isOverflown(v[0])" data-ng-click="toggleExpanded(v[0])"></span></td>
                    <td><button class="glyphicon glyphicon-minus" data-ng-if="expanded[v[0]]" data-ng-click="toggleExpanded(v[0])"></span></td>
                  </tr>
                  </tbody>
                </table>
              </div>
            </div>
	`,
	controller: function(appState, requestSender, $sce, $scope) {
	    $scope.data = null;
	    $scope.expanded = {};

	    function elementForKey(key) {
		return $('#' + $scope.elementId(key));
	    }

	    $scope.elementId = function(key) {
		return 'metadata-table-' + $scope.type + '-' + $scope.indexOfKey(key);
	    }

	    $scope.indexOfKey = function(key) {
		for (let i in $scope.data) {
		    if ($scope.data[i][0] === key) {
			return i;
		    }
		}
		throw new Error(`No key=${key} in data=${$scope.data}`);
	    }

	    $scope.isOverflown = function(key) {
		const e = elementForKey(key)
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

	    requestSender.statelessCompute(
		appState,
		{
		    method: $scope.type + '_metadata'
		},
		(data) => {
		    $scope.data  = Object.entries(data.data).map(([k, v]) => [k, v]);
		}
	    );
        },
    };
});
