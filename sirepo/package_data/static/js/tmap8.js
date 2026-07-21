'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.SINGLE_FRAME_ANIMATION = ['plotAnimation'];
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="ParameterArray">
          <div data-parameter-array="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="distribution">
          <div data-rpn-uncertainty="" data-model="model" data-field="field"></div>
        </div>
    `;
});

SIREPO.app.factory('tmap8Service', function(appState) {
    const self = {};
    self.computeModel = () => 'animation';
    // ex. "Normal" -> "normalDistribution", matching the model names in tmap8-schema.json
    self.distributionModelName = (distributionType) => {
        return distributionType.charAt(0).toLowerCase() + distributionType.slice(1) + 'Distribution';
    };
    appState.setAppService(self);
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
            <div data-import-dialog=""></div>
        `,
    };
});

SIREPO.app.directive('appHeader', function(tmap8Service) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: `
            <div data-app-header-brand="nav"></div>
            <div data-app-header-left="nav"></div>
            <div data-app-header-right="nav">
              <app-settings></app-settings>
              <app-header-right-sim-list>
                <ul class="nav navbar-nav sr-navbar-right">
                  <li>
                    <a href data-ng-click="nav.showImportModal()">
                      <span class="glyphicon glyphicon-cloud-upload"></span> Import
                    </a>
                  </li>
                </ul>
              </app-header-right-sim-list>
            </div>
        `,
    };
});

SIREPO.app.controller('VizController', function(appState, frameCache, panelState, persistentSimulation, $scope) {
    const self = this;
    self.simScope = $scope;
    self.errorMessage = '';
    self.reportTitle = SIREPO.APP_SCHEMA.view.plotAnimation.title;

    const valueListFields = (modelName) => {
        const r = [];
        for (const [f, d] of Object.entries(SIREPO.APP_SCHEMA.model[modelName])) {
            if (d[1] === 'ValueList') {
                r.push(f);
            }
        }
        return r;
    };

    const initModel = (info) => {
        panelState.setError(info.modelKey, null);
        if (! appState.models[info.modelKey]) {
            appState.models[info.modelKey] = {};
        }
        const m = appState.setModelDefaults(appState.models[info.modelKey], info.modelKey);
        m.valueList = {};
        for (const f of valueListFields(info.modelKey)) {
            m.valueList[f] = info.columns;
        }
        const cols = info.columns.filter((c) => c !== 'None');
        if (! m.x) {
            m.x = cols[0] || 'None';
        }
        if (! m.y1) {
            m.y1 = cols[1] || cols[0] || 'None';
        }
        appState.saveQuietly(info.modelKey);
        self.reportTitle = info.name;
    };

    self.simHandleStatus = (resp) => {
        self.errorMessage = resp.error;
        if (resp.reports && resp.reports.length) {
            resp.reports.forEach((info) => {
                initModel(info);
                //frameCache.setFrameCount(info.frameCount, info.modelKey);
            });
        }
        frameCache.setFrameCount(resp.frameCount || 0);
    };

    self.startSimulation = function() {
        self.simState.saveAndRunSimulation(['rpnVariables']);
    };

    self.simState = persistentSimulation.initSimulationState(self);
});

SIREPO.app.directive('rpnUncertainty', function(appState, tmap8Service) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <div style="margin-left: -10em; margin-right: 3em">
              <div class="form-group">
                <div class="row" data-field-editor="'uncertaintyDistribution'" data-field-size="12"
                  data-label-size="12" data-model-name="'rpnVariable'" data-model="model"></div>
              </div>
              <div data-ng-repeat="v in viewFields track by v.track">
                <div class="form-group">
                  <div class="row" data-field-editor="v.field" data-field-size="12" data-label-size="12"
                    data-model-name="modelName" data-model="model[field]"></div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {

            function setView() {
                const t = $scope.model.uncertaintyDistribution;
                if (t) {
                    $scope.modelName = tmap8Service.distributionModelName(t);
                    $scope.viewFields = SIREPO.APP_SCHEMA.view[$scope.modelName].advanced
                        .map((f) => {
                            return {
                                field: f,
                                track: $scope.modelName + f,
                            };
                        });
                }
                else {
                    $scope.viewFields = null;
                }
            }

            $scope.$watch('model.uncertaintyDistribution', (newValue, oldValue) => {
                if (! $scope.model) {
                    return;
                }
                if (newValue !== oldValue) {
                    $scope.model[$scope.field] = {};
                    if (newValue) {
                        appState.setModelDefaults(
                            $scope.model[$scope.field],
                            tmap8Service.distributionModelName(newValue),
                        );
                    }
                }
                setView();
            });
        },
    };
});

SIREPO.app.directive('parameterArray', function(appState, errorService, requestSender, tmap8Service) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <div data-ng-if="isWaiting">
              <span class="glyphicon glyphicon-hourglass"></span>
              Reading input file.
            </div>
            <table class="table table-striped table-condensed" data-ng-if="appState.models.rpnVariables">
              <colgroup>
                <col style="width: 30%">
                <col style="width: 40%">
                <col style="width: 20%">
                <col style="width: 1%">
              </colgroup>
              <thead>
                <tr>
                  <th>Parameter Name</th>
                  <th>Value</th>
                  <th> </th>
                </tr>
              </thead>
              <tbody>
                <tr data-ng-repeat="v in appState.models.rpnVariables">
                  <td>
                    <strong>{{ v.name }}</strong>
                    <span data-ng-if="v.unit" data-text-with-math="'$' + v.unit + '$'"></span>
                    <br data-ng-if="v.comment" />
                    <em data-ng-if="v.comment"># {{ v.comment }}</em>
                  </td>
                  <td><div class="row" data-field-editor="\'value\'" data-field-size="12" data-label-size="0" data-model-name="\'rpnVariable\'" data-model="v"></div></td>
                  <td>
                    <div class="col-sm-12" data-rpn-static="" data-model="v" data-field="\'value\'"></div>
                  </td>
                  <td>
                    <button class="btn btn-default btn-xs pull-right" type="button" data-ng-click="toggleUncertainty(v)" data-ng-attr-title="{{ v.uncertaintyDistribution ? 'Remove uncertainty' : 'Add uncertainty' }}">
                      <span class="glyphicon" data-ng-class="v.uncertaintyDistribution ? 'glyphicon-minus' : 'glyphicon-plus'"></span>
                    </button>
                    <div class="row" data-ng-if="v.uncertaintyDistribution" data-field-editor="\'uncertainty\'" data-field-size="12" data-label-size="0" data-model-name="\'rpnVariable\'" data-model="v"></div>

                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        `,
        controller: function($scope) {
            $scope.appState = appState;
            $scope.isWaiting = false;

            $scope.toggleUncertainty = (v) => {
                if (v.uncertaintyDistribution) {
                    delete v.uncertaintyDistribution;
                    delete v.uncertainty;
                }
                else {
                    v.uncertaintyDistribution = SIREPO.APP_SCHEMA.enum.Distribution[0][0];
                    v.uncertainty = {};
                    appState.setModelDefaults(
                        v.uncertainty,
                        tmap8Service.distributionModelName(v.uncertaintyDistribution),
                    );
                }
            };

            $scope.$on('simulationSettings.changed', () => {
                if (appState.models.simulationSettings.inputFile && ! appState.models.rpnVariables) {
                    $scope.isWaiting = true;
                    requestSender.sendStatefulCompute(
                        appState,
                        (resp) => {
                            $scope.isWaiting = false;
                            if (resp.error) {
                                errorService.alertText(resp.error);
                                return
                            }
                            if (resp.parameters) {
                                appState.models.rpnVariables = resp.parameters;
                                appState.models.rpnCache = resp.cache;
                                appState.saveChanges(['rpnVariables', 'rpnCache'])
                            }
                        },
                        {
                            method: 'parse_parameters',
                            args: {
                                inputFile: appState.models.simulationSettings.inputFile,
                            },
                        }
                    );
                }
                else if (appState.models.rpnVariables) {
                    appState.saveQuietly('rpnVariables');
                }
            });
        },
    };
});
