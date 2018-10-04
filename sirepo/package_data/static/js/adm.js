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
                    '<th data-ng-repeat="col in data[0]">{{ col }}</th>',
                '</tr>',
                '<tr data-ng-repeat="row in data" data-ng-if="$index > 0">',
                    '<td data-ng-repeat="col in row">',
                        '<a data-ng-if="$index == 0" href="" data-ng-click="getServerData(col)">{{ col }}</a>',
                        '<span data-ng-if="$index > 0">{{ col }}</span>',
                    '</td>',
                '</tr>',
                '</table>',
                '<button class="btn btn-default" data-ng-click="getServerData()">Refresh</button>',
            '</div>',
        ].join(''),
        controller: function($scope) {

            $scope.getServerData = function (id) {
                srdbg('getting data for id', id);
                requestSender.sendRequest(
                    'getServerData',
                    dataLoaded,
                    {
                        id: id,
                    });
            };
            $scope.getServerData();


            function dataLoaded(data, status) {
                $scope.data = data;
            }
        },
    };
});

