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

SIREPO.app.directive('serverDataList', function(requestSender) {
    return {
        restrict: 'A',
        template: [
            '<div>',
                '<table class="table">',
                '<tr>',
                    '<th data-ng-repeat="c in data.columns">{{ c }}</th>',
                '</tr>',
                '<tr data-ng-repeat="r in data.data">',
                    '<td data-ng-repeat="c in r">',
                        '<span>{{ c }}</span>',
                    '</td>',
                '</tr>',
                '</table>',
                '<button class="btn btn-default" data-ng-click="getAdmJobs()">Refresh</button>',
            '</div>',
        ].join(''),
        controller: function($scope) {

            $scope.getAdmJobs = function (id) {
                requestSender.sendRequest(
                    'admJobs',
                    dataLoaded,
                    {
                        id: id,
                    });
            };
            $scope.getAdmJobs();


            function dataLoaded(data, status) {
                $scope.data = data;
            }
        },
    };
});
