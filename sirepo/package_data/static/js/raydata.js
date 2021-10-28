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

SIREPO.app.factory('raydataService', function(appState) {
    const self = {};
    let id = 0;
    self.computeModel = function(analysisModel) {
        return 'animation';
    };

    self.nextPngImageId = () => {
	return 'raydata-png-image-' + ++id;
    };

    self.setPngDataUrl = (element, png) => {
	element.src = 'data:image/png;base64,' + png;
    }

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
	    category: '@',
	    modelName: '@'
	},
        template: `
            <div class="table-responsive"  data-ng-if="data">
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
	    $scope.data = null;
	    $scope.expanded = {};

	    function elementForKey(key) {
		return $('#' + $scope.elementId(key));
	    }

	    $scope.elementId = function(key) {
		return 'metadata-table-' + $scope.category + '-' + $scope.indexOfKey(key);
	    };

	    $scope.indexOfKey = function(key) {
		for (let i in $scope.data) {
		    if ($scope.data[i][0] === key) {
			return i;
		    }
		}
		throw new Error(`No key=${key} in data=${$scope.data}`);
	    };

	    // TODO(e-carlin): when expaneded it overflow the plot box
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

	    requestSender.statelessCompute(
		appState,
		{
		    method: 'metadata',
		    category: $scope.category
		},
		(data) => {
		    $scope.data  = Object.entries(data.data).map(([k, v]) => [k, v]);
		},
		{
		    modelName: $scope.modelName,
		    panelStateHandle: panelState,
		}
	    );
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
		raydataService.setPngDataUrl($('#' + $scope.id)[0], json.image)
            };
	},
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});
