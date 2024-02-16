'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.controller('MyAppSourceController', function (appState, panelState, $scope) {
    var self = this;

    function handleDogDisposition() {
        panelState.showField('dog', 'favoriteTreat', appState.models.dog.disposition == 'friendly');
    }

    appState.whenModelsLoaded($scope, function() {
        // after the model data is available, hide/show the
        // favoriteTreat field depending on the disposition
        handleDogDisposition();
        appState.watchModelFields($scope, ['dog.disposition'], function() {
            // respond to changes in the disposition field value
            handleDogDisposition();
        });
    });
});

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
        `,
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
                <div data-sim-sections="">
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
              </app-settings>
              <app-header-right-sim-list>
              </app-header-right-sim-list>
            </div>
        `,
    };
});

SIREPO.app.directive('testComputeJob', function(appState, requestSender, simulationQueue) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div data-simple-panel="testReport">
              <div class="well">
                <button type="button" class="btn btn-default" data-ng-click="run('computeJob')">
                  Test Compute Job</button>
                <div>{{ computeJobOutput }}</div>
              </div>
              <div class="well">
                <button type="button" class="btn btn-default" data-ng-click="run('statefulCompute')">
                  Test Stateful Compute</button>
                <div>{{ statefulComputeOutput }}</div>
              </div>
            </div>
        `,
        controller: function($scope) {

            function setText(runCommand, text) {
                $scope[runCommand + 'Output'] = text;
            }

            function handleResult(runCommand, start, result) {
                if (result.error) {
                    setText(runCommand, 'Error: ' + result.error);
                    return;
                }
                setText(runCommand, 'Completed in ' + ((Date.now() - start) / 1000) + ' seconds');
            }

            $scope.run = (runCommand) => {
                setText(runCommand, 'Running...');
                const start = Date.now();
                if (runCommand === 'computeJob') {
                    simulationQueue.addTransientItem(
                        'testReport',
                        appState.applicationState(),
                        result => handleResult(runCommand, start, result),
                    );
                }
                else if (runCommand === 'statefulCompute') {
                    requestSender.sendStatefulCompute(
                        appState,
                        result => handleResult(runCommand, start, result),
                        {
                            method: 'test',
                            args: {},
                        },
                    );
                }
            };
        },
    };
});
