'use strict';

var SRW_EXAMPLES;
var LANDING_PAGE_SCHEMA;

SIREPO.srlog = console.log.bind(console);
SIREPO.srdbg = console.log.bind(console);

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

angular.element(document).ready(function() {
    $.ajax({
        url: '/static/json/srw-examples.json' + SIREPO.SOURCE_CACHE_KEY,
        success: function(result) {
            SRW_EXAMPLES = result;
        },
        error: function(xhr, status, err) {
            if (! SRW_EXAMPLES) {
                srlog("srw examples load failed: ", err);
            }
        },
        method: 'GET',
        dataType: 'json'
    });
});

//var app = angular.module('LandingPageApp', ['ngRoute']);

//app.value('srwAppRoutes', {});

/*
app.config(function(srwAppRoutesProvider, $locationProvider, $routeProvider) {
    $locationProvider.hashPrefix('');
    var srwAppRoutes = srwAppRoutesProvider.$get();
    Object.keys(LANDING_PAGE_SCHEMA.srwAppRoutes).forEach(function(key) {
        srwAppRoutes[key] = LANDING_PAGE_SCHEMA.srwAppRoutes[key];
    });

    $routeProvider.when('/home', {
        templateUrl: '/static/html/landing-page-home.html' + SIREPO.SOURCE_CACHE_KEY,
    });
    Object.keys(srwAppRoutes).forEach(function(key) {
        $routeProvider.when('/' + key, {
            template: [
                '<div data-page-heading="" data-landing-page="landingPage"></div>',
                '<div class="container">',
                    '<div class="row visible-xs">',
                        '<div class="lead text-center" data-ng-bind="landingPage.pageName()"></div>',
                    '</div>',
                    '<div data-ng-repeat="item in landingPage.itemsForCategory()" data-',
                    (key == 'light-sources' ? 'button-list' : 'big-button'),
                    '="item"></div>',
                '</div>',
            ].join('')
        });
    });
    $routeProvider.otherwise({
        redirectTo: '/home',
    });
});
*/
SIREPO.app.controller('SRWLightController', function ($location, srwAppRoutes) {
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
        return srwAppRoutes[pageCategory()];
    };

    self.pageTitle = function() {
        var name = self.pageName();
        return (name ? (name + ' - ') : '') + 'Synchrotron Radiation Workshop - Radiasoft';
    };

});

SIREPO.app.directive('srwExamples', function($scope) {
    return {
        restrict: 'A',
        scope: {
            section: '<',
        },
        template: [
            '<div data-page-heading="" data-srwl-controller="srwlController"></div>',
            '<div class="container">',
                '<div class="row visible-xs">',
                    '<div class="lead text-center" data-ng-bind="srwlController.pageName()"></div>',
                '</div>',
                '<div data-ng-repeat="item in srwlController.itemsForCategory()" data-',
                ($scope.section === 'light-sources' ? 'button-list' : 'big-button'),
                '="item"></div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
        },
    };
});

SIREPO.app.directive('bigButton', function() {
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

SIREPO.app.directive('buttonList', function() {
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


SIREPO.app.directive('pageHeading', function(srwAppRoutes) {
    function getTemplate() {
        var template = [
                '<div class="lp-main-header-content" data-ng-class="{\'lp-sub-header-content\': ! onMainLandingPage()}">',
                    '<a href="/#about">',
                        '<img class="lp-header-sr-logo" src="/static/img/SirepoLogo.png',SIREPO.SOURCE_CACHE_KEY,'">',
                    '</a>',
        ].join('');
        if (SIREPO.IS_SRW_LANDING_PAGE) {
            template += [
                '<div class="lp-srw-sub-header-text">',
                    '<a href="/#/srw">Synchrotron Radiation Workshop</a>',
                    ' <span class="hidden-xs" data-ng-if="landingPage.pageName()">-</span> ',
                    '<span class="hidden-xs" data-ng-if="landingPage.pageName()" data-ng-bind="landingPage.pageName()"></span>',
                '</div>',
            ].join('');
        }
        template += [
                    '<div data-ng-show="onMainLandingPage() || onSRWShortcutsPage()" data-ng-class="{\'lp-hide-wide\': ! onSRWShortcutsPage()}" class="pull-right">',
                        '<a href="http://radiasoft.net">',
                            '<img class="lp-header-rs-logo" src="/static/img/RSLogo.png',SIREPO.SOURCE_CACHE_KEY,'" alt="Radiasoft" />',
                        '</a>',
                    '</div>',
                '</div>',
        ].join('');
        return template;
    }
    return {
        restrict: 'A',
        scope: {
            landingPage: '=',
        },
        template: getTemplate(),
        controller: function($scope, $location) {
            $scope.onMainLandingPage = function() {
                return $location.path() === '/about';
            };
            $scope.onSRWShortcutsPage = function() {
                var route = $location.path().substring(1);
                return route === 'home' || Object.keys(srwAppRoutes).indexOf(route) >= 0;
            };
       },
    };
});
