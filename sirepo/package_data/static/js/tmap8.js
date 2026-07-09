'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="ParameterArray">
          <div data-parameter-array="" data-model="model" data-field="field"></div>
        </div>
    `;
});

SIREPO.app.factory('tmap8Service', function(appState) {
    const self = {};
    self.computeModel = () => 'animation';
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

SIREPO.app.controller('VizController', function(appState, frameCache, persistentSimulation, $scope) {
    const self = this;
    self.simScope = $scope;

    self.simHandleStatus = (resp) => {
        console.log('status resp:', resp);
    };

    self.startSimulation = function() {
        self.simState.saveAndRunSimulation(['rpnVariables']);
    };

    self.simState = persistentSimulation.initSimulationState(self);
});

SIREPO.app.directive('parameterArray', function(appState, errorService, requestSender) {
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
                <col style="width: 25%">
                <col style="width: 50%">
                <col style="width: 25%">
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
                  <td>{{ v.name }} {{ v.unit ? '[' + v.unit + ']' : '' }}</td>
                  <td><div class="row" data-field-editor="\'value\'" data-field-size="12" data-label-size="0" data-model-name="\'rpnVariable\'" data-model="v"></div></td>
                  <td><div class="col-sm-12" data-rpn-static="" data-model="v" data-field="\'value\'"></div></td>
                </tr>
              </tbody>
            </table>
          </div>
        `,
        controller: function($scope) {
            $scope.appState = appState;
            $scope.isWaiting = false;

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
                                appState.saveChanges('rpnVariables')
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
