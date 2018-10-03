'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.controller('AdmController', function () {
    var self = this;

});

SIREPO.app.directive('appHeader', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: [
            '<div data-app-header-brand="nav"></div>',
            '<div data-app-header-right="nav">',
              '<app-settings>',
                //  '<div>App-specific setting item</div>',
              '</app-settings>',
            '</div>',
        ].join(''),
    };
});

SIREPO.app.directive('serverDataList', function() {
    return {
        restrict: 'A',
        template: [
            '<div>',
                '<table class="table">',
                '<tr>',
                    '<th data-ng-repeat="col in data[0]">{{ col }}</th>',
                '</tr>',
                '<tr data-ng-repeat="row in data track by $index" data-ng-if="$index > 0">',
                    '<td data-ng-repeat="col in row">{{ col }}</td>',
                '</tr>',
                '</table>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {

            $scope.data = [
                ['jobId', 'jobStart', 'jobState', 'jobReport'],
                ['123', '2018-10-03T16:09:09+00:05', 'running', 'TITLE 123'],
                ['456', '2018-10-01T16:21:09+00:05', 'complete', 'TITLE 456']
            ];
        },
    };
});

