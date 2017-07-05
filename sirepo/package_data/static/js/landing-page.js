'use strict';

var SRW_EXAMPLES;

SIREPO.srlog = console.log.bind(console);
SIREPO.srdbg = console.log.bind(console);

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.IS_SRW_LANDING_PAGE = window.location.href.match(/\/light/);

angular.element(document).ready(function() {
    $.ajax({
        url: '/static/json/srw-examples.json' + SIREPO.SOURCE_CACHE_KEY,
        success: function(result) {
            SRW_EXAMPLES = result;
            angular.bootstrap(document, ['LandingPageApp']);
        },
        error: function(xhr, status, err) {
            if (! SRW_EXAMPLES) {
                srlog("srw examples load failed: ", err);
            }
        },
        method: 'GET',
        dataType: 'json',
    });
});

var app = angular.module('LandingPageApp', ['ngRoute']);

app.value('appRoutes', {
    'calculator': 'SR Calculator',
    'light-sources': 'Light Source Facilities',
    'wavefront': 'Wavefront Propagation',
});

app.config(function(appRoutesProvider, $locationProvider, $routeProvider) {
    $locationProvider.hashPrefix('');
    // srw landing page
    if (SIREPO.IS_SRW_LANDING_PAGE) {
        var appRoutes = appRoutesProvider.$get();
        $routeProvider.when('/home', {
            templateUrl: '/static/html/landing-page-home.html' + SIREPO.SOURCE_CACHE_KEY,
        });
        Object.keys(appRoutes).forEach(function(key) {
            $routeProvider.when('/' + key, {
                template: '<div data-ng-repeat="item in landingPage.itemsForCategory()" data-'
                    + (key == 'light-sources' ? 'button-list' : 'big-button')
                    + '="item"></div>',
            });
        });
        $routeProvider.otherwise({
            redirectTo: '/home',
        });
    }
    // root landing page
    else {
        $routeProvider.when('/about', {
            templateUrl: '/static/html/landing-page-about.html' + SIREPO.SOURCE_CACHE_KEY,
        });
        $routeProvider.otherwise({
            redirectTo: '/about',
        });
    }
});

app.controller('LandingPageController', function ($location, appRoutes) {
    var self = this;
    self.srwExamples = SRW_EXAMPLES;

    function pageCategory() {
        return $location.path().substring(1);
    }

    self.itemsForCategory = function() {
        for (var i = 0; i < self.srwExamples.length; i++) {
            if (self.srwExamples[i].category == pageCategory()) {
                return self.srwExamples[i].examples;
            }
        }
    };

    self.itemUrl = function(item) {
        if (item.category) {
            return '#/' + item.category;
        }
        return '/find-by-name/srw/' + pageCategory() + '/' + encodeURIComponent(item.simulationName || item.name);
    };

    self.pageName = function() {
        return appRoutes[pageCategory()];
    };

    self.pageTitle = function() {
        if (SIREPO.IS_SRW_LANDING_PAGE) {
            var name = self.pageName();
            return (name ? (name + ' - ') : '') + 'Synchrotron Radiation Workshop - Radiasoft';
        }
        return 'Sirepo - Radiasoft';
    };
});

app.directive('bigButton', function() {
    return {
        restrict: 'A',
        scope: {
            item: '=bigButton',
            wideCol: '@',
        },
        template: [
            '<div class="row">',
              '<div data-ng-class="item.class">',
                '<a data-ng-href="{{ item.url }}" class="btn btn-default thumbnail lp-big-button"><h3 data-ng-if="item.name">{{ item.name }}</h3><img data-ng-if="item.image" data-ng-src="/static/img/{{ item.image }}" alt="{{ item.name }}" /><span class="lead text-primary" style="white-space: pre" data-ng-if="item.buttonText">{{ item.buttonText }}</span></a>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var current = $scope;
            var controller;
            while (current) {
                controller = current.landingPage;
                if (controller) {
                    break;
                }
                current = current.$parent;
            }
            $scope.item.class = $scope.wideCol
                ? 'col-md-8 col-md-offset-2'
                : 'col-md-6 col-md-offset-3';
            $scope.item.url = controller.itemUrl($scope.item);
        },
    };
});

app.directive('buttonList', function() {
    return {
        restrict: 'A',
        scope: {
            item: '=buttonList',
        },
        template: [
            '<div class="row">',
              '<div class="col-md-8 col-md-offset-2">',
                '<div class="well">',
                  '<h3>{{ item.name }}</h3>',
                  '<div data-ng-repeat="item in item.simulations" data-big-button="item" data-wide-col="1"></div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
    };
});

function lpCodeDetailsClass(codeName) {
    return 'lp-' + codeName.toLowerCase() + '-details';
}

app.directive('codeDetails', function() {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            codeName: '@codeDetails',
        },
        template: [
            '<div style="display: none" data-ng-attr-class="{{ moreClass }}">',
              '<div style="display: inline" data-ng-transclude=""></div> ',
              '<div class="text-right"><small><a href data-ng-click="hideDetails()"><i>less</i> <span class="glyphicon glyphicon-chevron-up"></span></a></small></div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.moreClass = lpCodeDetailsClass($scope.codeName);
            $scope.hideDetails = function() {
                $('.' + $scope.moreClass).slideUp(
                    400,
                    function() {
                        $scope.$parent[$scope.codeName] = false;
                        $scope.$apply();
                    });
            };
        },
    };
});

app.directive('codeSummary', function() {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            codeName: '@codeSummary',
        },
        template: [
            '<table><tr><td valign="top">',
              '<a target="_blank" class="btn btn-default lp-code-button" data-ng-href="{{ codeHref() }}"><h4>{{ codeName }}</h4></a>',
            '</td><td>',
              '<p>',
                '<div style="display: inline" data-ng-transclude=""></div> ',
                '<small><a href style="float: right" data-ng-hide="$parent[codeName]" data-ng-click="showDetails()"><i>more</i> <span class="glyphicon glyphicon-chevron-down"></span></a></small>',
              '</p>',
            '</td></tr></table>',
        ].join(''),
        controller: function($scope) {
            $scope.$parent[$scope.codeName] = false;
            $scope.codeHref = function() {
                if ($scope.codeName == 'SRW') {
                    return '/light';
                }
                if ($scope.codeName == 'Shadow3') {
                    return '/shadow';
                }
                return '/' + $scope.codeName.toLowerCase().replace(/\W/g, '');
            };
            $scope.showDetails = function() {
                $('.' + lpCodeDetailsClass($scope.codeName)).slideDown();
                $scope.$parent[$scope.codeName] = true;
            };
        },
    };
});

app.directive('pageHeading', function() {
    function getTemplate() {
        if (SIREPO.IS_SRW_LANDING_PAGE) {
            return [
                '<div><a href="#/home">Synchrotron Radiation Workshop</a>',
                  ' <span class="hidden-xs" data-ng-if="landingPage.pageName()">-</span> ',
                  '<span class="hidden-xs" data-ng-if="landingPage.pageName()" data-ng-bind="landingPage.pageName()"></span>',
                '</div>',
            ].join('');
        }
        return [
            '<div>Sirepo</div>',
        ].join('');
    }
    return {
        restrict: 'A',
        scope: {
            landingPage: '=',
        },
        template: getTemplate(),
    };
});
