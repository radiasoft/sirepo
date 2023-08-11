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
    const modelAccess = {};
    appState.setAppService(self);
    self.computeModel = analysisModel => 'animation';

    self.modelAccess = modelKey => {
        if (! modelAccess[modelKey]) {
            modelAccess[modelKey] = {
                modelKey: modelKey,
                getData: () => appState.models[modelKey],
            };
        }
        return modelAccess[modelKey];
    };
    return self;
});

SIREPO.app.controller('SourceController', function (appState, frameCache, omegaService, persistentSimulation, $scope) {
    const self = this;
    let errorMessage;
    self.omegaService = omegaService;
    self.simScope = $scope;
    self.reports = null;
    self.simAnalysisModel = 'animation';

    self.simHandleStatus = data => {
        errorMessage = data.error;
        frameCache.setFrameCount(data.frameCount || 0);
        self.reports = [];
        self.reportNames = [];
        if (data.outputInfo) {
            // sim --> report-group --> report
            for (const s of data.outputInfo) {
                for (const rg of s) {
                    for (const r of rg) {
                        self.reportNames.push(r);
                        let m = appState.models[r.modelKey];
                        if (! m) {
                            m = appState.models[r.modelKey] = {
                                simCount: r.simCount,
                                reportCount: r.reportCount,
                            };
                        }
                        appState.setModelDefaults(m, r.modelName);
                        appState.saveQuietly(r.modelKey);
                        frameCache.setFrameCount(1, r.modelKey);
                    }
                }
            }
            self.reports = data.outputInfo;
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

SIREPO.app.directive('beamAndPhasePlots', function(appState, omegaService) {
    return {
        restrict: 'A',
        scope: {
            reports: '=',
        },
        template: `
            <div class="clearfix"></div>
            <div data-ng-repeat="sim in reports track by $index">
              <div class="clearfix hidden-xl"></div>
              <div class="col-md-5 col-xxl-3">
                <div data-ng-repeat="report in sim[0] track by $index">
                  <div data-report-panel="parameter" data-model-data="omegaService.modelAccess(report.modelKey)" data-model-name="{{ report.modelName }}" data-panel-title="{{ title(report) }}"></div>
                </div>
              </div>
              <div class="col-md-7 col-xxl-3">
                <div data-simple-panel="simPhaseSpaceAnimation" data-model-key="sim[1][0].modelKey" data-is-report="1">
                  <div class="sr-screenshot" style="display: grid; grid-template-columns: 50% 50%">
                    <div data-ng-repeat="report in sim[1] track by $index">
                      <div data-heatmap="" data-model-name="{{ report.modelKey }}"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
            $scope.omegaService = omegaService;
            $scope.title = report => `Simulation ${report.simCount} Beam Parameters`;
            $scope.$on('modelChanged', (e, name) => {
                for (const sim of $scope.reports) {
                    if (name === sim[1][0].modelKey) {
                        const updated = [];
                        for (const r of sim[1]) {
                            if (name !== r.modelKey) {
                                const m = appState.models[r.modelKey];
                                m.colorMap = appState.models[name].colorMap;
                                m.histogramBins = appState.models[name].histogramBins;
                                updated.push(r.modelKey);
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
