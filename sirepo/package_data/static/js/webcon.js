'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.INCLUDE_EXAMPLE_FOLDERS = true;
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="Equation" class="col-sm-7">',
      '<div data-equation="equation" data-model="model" data-field="field" data-parent-controller="source"></div>',
    '</div>',
    '<div data-ng-switch-when="EquationVariables" class="col-sm-7">',
      '<div data-equation-variables="" data-model="model" data-field="field"></div>',
    '</div>',
].join('');
SIREPO.app.controller('WebconSourceController', function (appState, panelState, $scope) {
    var self = this;

    function validateEquation() {
        //srdbg('VALIDATING', $scope);
    }

    self.validateEquation = function(eq) {
        srdbg('VALIDATING', eq);
    };

    appState.whenModelsLoaded($scope, function() {
        srdbg('loaded', appState.models);
        validateEquation();
        appState.watchModelFields($scope, ['fitter.equation', 'fitter.variables'], function() {
            validateEquation();
        });
    });
});

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-common-footer="nav"></div>',
        ].join(''),
    };
});

SIREPO.app.directive('appHeader', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: [
            '<div data-app-header-brand="nav"></div>',
            '<div data-app-header-left="nav"></div>',
            '<div data-app-header-right="nav">',
              '<app-header-right-sim-loaded>',
                '<div data-sim-sections="">',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
                '</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
                //  '<div>App-specific setting item</div>',
              '</app-settings>',
              '<app-header-right-sim-list>',
              '</app-header-right-sim-list>',
            '</div>',
        ].join(''),
    };
});

SIREPO.app.directive('equation', function(appState) {
    return {
        scope: {
            controller: '=parentController',
            model: '=',
            field: '='
        },
        template: [
            '<div>',
                '<input type="text" data-ng-model="model[field]" data-ng-change="validate()" class="form-control" required>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            srdbg('eq', $scope.model);

            $scope.validate = function () {
                //$scope.controller.validateEquation($scope.model.equation);

            };

        },
    };
});

SIREPO.app.directive('equationVariables', function() {
    return {
        restrict: 'A',
        scope: {
            equation: '<',
            field: '=',
            model: '=',
        },
        template: [
            '<div>',
                '<input type="text" data-ng-model="model[field]" class="form-control" required />',
            '</div>'
        ].join(''),
        controller: function($scope) {
            var opsRegEx = /[\+\-\*/\^\(\)]/;
            var reserved = ['sin', 'cos', 'tan', 'abs'];
            $scope.values = null;
            $scope.didChange = function() {
                $scope.field = $scope.values.join(', ');
            };
            $scope.parseValues = function() {
                if ($scope.field && ! $scope.values) {
                    $scope.values = $scope.field.split(/\s*,\s*/);
                }
                return $scope.values;
            };
        },
    };
});


SIREPO.app.directive('fitReport', function(appState) {
    return {
        //scope: {
        //    controller: '=parentController',
        //    model: '=',
        //},
        template: [
            '<div class="col-md-6 col-xl-4">',
                '<div data-report-panel="parameter" data-request-priority="1" data-model-name="fitterReport"></div>',
                //'<div data-equation="" data-model="model" data-field="field"></div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            srdbg('scope', $scope);
            //srdbg('model/field', $scope.model, $scope.field);
        },
    };
});