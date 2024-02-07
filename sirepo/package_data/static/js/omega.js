'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="SimList" data-ng-class="fieldClass">
          <div data-dynamic-sim-list="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="SimArray">
          <div data-sim-array="" data-model="model" data-field="field" data-sub-model-name="coupledSim"></div>
        </div>
    `;

    SIREPO.appDownloadLinks = `
        <li data-ng-if="::hasDataFile"><a href data-ng-href="{{ dataFileURL(\'openpmd\') }}">OpenPMD Data File</a></li>
    `;
});

SIREPO.app.factory('omegaService', function(appState) {
    const self = {};
    const modelAccess = {};
    appState.setAppService(self);
    self.computeModel = analysisModel => 'animation';

    self.modelAccess = modelKey => {
        if (! modelAccess[modelKey]) {
            // this structure has no state, so it can be cached across simulations
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
              <div class="clearfix hidden-xxl"></div>
              <div data-ng-if="$index % 2 == 0" class="clearfix visible-xxl"></div>
              <div class="col-md-5 col-xxl-3">
                <div class="row">
                  <div class="col-sm-12">
                    <div data-ng-repeat="report in sim[0] track by $index">
                      <div data-report-panel="parameter" data-model-data="omegaService.modelAccess(report.modelKey)" data-model-name="{{ report.modelName }}" data-panel-title="{{ title(report) }}"></div>
                    </div>
                  </div>
                  <div class="col-sm-12">
                    <div data-ng-if="sim.length > 2">
                      <div data-report-panel="heatmap" data-panel-title="{{ title(sim[2][0]) }}" data-model-name="sim[2][0].modelName" data-model-data="omegaService.modelAccess(sim[2][0].modelKey)"></div>
                    </div>
                  </div>
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

            $scope.title = report => {
                const t = report.modelName.includes('Beam') ? 'Beam Parameters' : 'Field Distribution';
                return `Simulation ${report.simCount} ${t}`;
            };

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

SIREPO.app.directive('dynamicSimList', function(appState, requestSender) {
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
            const requestSimListByType = (simType) => {
                requestSender.sendRequest(
                    'listSimulations',
                    () => {},
                    {
                        simulationType: simType,
                    }
                );
            };
            if (SIREPO.APP_SCHEMA.relatedSimTypes) {
                SIREPO.APP_SCHEMA.relatedSimTypes.forEach(simType => {
                    requestSimListByType(simType);
                });
            }
            $scope.selectedCode = () => {
                if ($scope.model) {
                    $scope.code = $scope.model.simulationType;
                    return $scope.code;
                }
            };
        },
    };
});

SIREPO.app.directive('simArray', function(appState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            subModelName: '@',
        },
        template: `
          <div class="clearfix" style="margin-top:-20px"></div>
            <div class="col-sm-4 col-sm-offset-1 lead">{{:: label('simulationType') }}</div>
            <div class="col-sm-7 lead">{{:: label('simulationId') }}</div>
            <div class="col-sm-12">
              <div data-ng-repeat="sim in model[field] track by $index">
                <div class="form-group">
                  <div class="col-sm-1 control-label"><label>{{ $index + 1 }}</label></div>
                  <div data-model-field="'simulationType'" data-model-name="subModelName" data-model-data="modelData($index)" data-label-size="0" data-field-size="4"></div>
                  <div data-model-field="'simulationId'" data-model-name="subModelName" data-model-data="modelData($index)" data-label-size="0" data-field-size="6"></div>
                </div>
              </div>
            </div>
          </div>
        `,
        controller: function($scope) {
            const modelData = {};

            function checkArray() {
                // ensure there is always an empty selection available at the end of the list
                const a = $scope.model[$scope.field];
                if (! a.length || (a[a.length - 1].simulationType && a[a.length - 1].simulationId)) {
                    a.push(appState.setModelDefaults({}, $scope.subModelName));
                }
            }

            $scope.label = field => appState.modelInfo($scope.subModelName)[field][0];

            $scope.modelData = index => {
                if (! $scope.model) {
                    return;
                }
                checkArray();
                if (! modelData[index]) {
                    modelData[index] = {
                        getData: () => $scope.model[$scope.field][index],
                    };
                }
                return modelData[index];
            };
        },
    };
});

SIREPO.viewLogic('simWorkflowView', function(appState, $scope) {
    $scope.$on('simWorkflow.changed', () => {
        const w = appState.models.simWorkflow;
        const sims = [];
        for (const s of w.coupledSims) {
            if (s.simulationType && s.simulationId) {
                sims.push(s);
            }
        }
        sims.push(appState.setModelDefaults({}, 'coupledSim'));
        w.coupledSims = sims;
        appState.saveQuietly('simWorkflow');
    });
});
