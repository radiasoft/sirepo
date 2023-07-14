'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="SimList" data-ng-class="fieldClass">
          <div data-dynamic-sim-list="" data-model="model" data-field="field"></div>
        </div>
    `;
});

SIREPO.app.factory('omegaService', function(appState) {
    const self = {};
    appState.setAppService(self);
    self.computeModel = function(analysisModel) {
        return 'animation';
    };
    return self;
});

SIREPO.app.controller('SourceController', function (appState, frameCache, persistentSimulation, $scope) {
    const self = this;
    let errorMessage;
    self.simScope = $scope;
    self.reports = null;

    self.simHandleStatus = data => {
        errorMessage = data.error;
        frameCache.setFrameCount(data.frameCount || 0);
        self.reports = data.reports;
        if (data.reports) {
            for (const r of data.reports) {
                frameCache.setFrameCount(r.modelName, r.frameCount);
            }
        }
    };

    self.simState = persistentSimulation.initSimulationState(self);
    //TODO(pjm): this should be default behavior in simStatusPanel
    self.simState.errorMessage = () => errorMessage;
    self.simCompletionState = () => '';
});

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
            <div data-import-dialog=""></div>
        `,
    };
});

SIREPO.app.directive('appHeader', function(omegaService) {
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
                <div data-sim-sections="">
                  <li class="sim-section" data-ng-class="{active: nav.isActive('source')}"><a href data-ng-click="nav.openSection('source')"> Source</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
              </app-settings>
              <app-header-right-sim-list>
                <ul class="nav navbar-nav sr-navbar-right">
                  <li><a href data-ng-click="nav.showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>
                </ul>
              </app-header-right-sim-list>
            </div>
        `,
    };
});

SIREPO.app.directive('beamAndPhasePlots', function(appState) {
    return {
        restrict: 'A',
        scope: {
            reports: '=',
        },
        template: `
            <div class="clearfix"></div>
            <div data-ng-repeat="simCount in count track by $index">
              <div class="clearfix hidden-xl"></div>
              <div class="col-md-5 col-xxl-3" data-ng-if="hasReport(beamReport(simCount))">
                <div data-report-panel="parameter" data-model-name="{{ beamReport(simCount) }}"></div>
              </div>
              <div class="col-md-7 col-xxl-3" data-ng-if="hasReport(phaseSpaceReport(simCount, 1))">
                <div data-simple-panel="{{ phaseSpaceReport(simCount, 1) }}" data-is-report="1">
                  <div class="sr-screenshot" style="display: grid; grid-template-columns: 50% 50%">
                    <div data-ng-repeat="reportCount in count track by $index">
                      <div data-heatmap="" data-model-name="{{ phaseSpaceReport(simCount, reportCount) }}"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
            $scope.count = [1, 2, 3, 4];
            $scope.beamReport = simCount => `sim${simCount}BeamAnimation`;
            $scope.phaseSpaceReport = (simCount, reportCount) => `sim${simCount}Phase${reportCount}Animation`;

            $scope.hasReport = name => {
                if ($scope.reports) {
                    for (const r of $scope.reports) {
                        if (r.modelName == name) {
                            return r.frameCount > 0;
                        }
                    }
                }
                return false;
            };

            $scope.$on('modelChanged', (e, name) => {
                for (const i of $scope.count) {
                    const updated = [];
                    const n = $scope.phaseSpaceReport(i, 1);
                    if (name === n) {
                        for (const j of $scope.count) {
                            if (j > 1) {
                                const p = $scope.phaseSpaceReport(i, j);
                                appState.models[p].colorMap = appState.models[n].colorMap;
                                appState.models[p].histogramBins = appState.models[n].histogramBins;
                                updated.push(p);
                            }
                        }
                        appState.saveChanges(updated);
                    }
                }
            });
        },
    };
});

SIREPO.app.directive('dynamicSimList', function(appState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
          <div data-ng-if="code == selectedCode() && code">
            <div data-sim-list="" data-model="model" data-field="field" data-code="{{ selectedCode() }}" data-route="visualization"></div>
          </div>
        `,
        controller: function($scope) {
            $scope.selectedCode = () => {
                if ($scope.field) {
                    const i = $scope.field.match(/(\d+)$/)[0];
                    if (i) {
                        $scope.code = $scope.model[`simType_${i}`];
                        return $scope.code;
                    }
                }
            };
        },
    };
});

SIREPO.viewLogic('simWorkflowView', function(appState, panelState, $scope) {
    function updateVisibility() {
        const wf = appState.models.simWorkflow;
        panelState.showFields('simWorkflow', [
            ['simId_2', 'simType_2'], wf.simType_1 && wf.simId_1,
            ['simId_3', 'simType_3'], wf.simType_2 && wf.simId_2,
            ['simId_4', 'simType_4'], wf.simType_3 && wf.simId_3,
        ]);
    }

    $scope.whenSelected = updateVisibility;
    $scope.watchFields = [
        [
            'simWorkflow.simType_1',
            'simWorkflow.simId_1',
            'simWorkflow.simType_2',
            'simWorkflow.simId_2',
            'simWorkflow.simType_3',
            'simWorkflow.simId_3',
        ], updateVisibility,
    ];
});
