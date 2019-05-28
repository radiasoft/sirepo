'use strict';

var SRW_EXAMPLES;
var LIGHT_SCHEMA;

SIREPO.srlog = console.log.bind(console);
SIREPO.srdbg = console.log.bind(console);

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

angular.element(document).ready(function() {
    $.ajax({
        url: '/static/json/srw-examples.json' + SIREPO.SOURCE_CACHE_KEY,
        success: function(result) {
            SRW_EXAMPLES = result;
            $.ajax({
                url: '/static/json/light-schema.json' + SIREPO.SOURCE_CACHE_KEY,
                success: function(result) {
                    LIGHT_SCHEMA = result;
                    angular.bootstrap(document, ['SRWLightGateway']);
                },
                error: function(xhr, status, err) {
                    if (! LIGHT_SCHEMA) {
                        srlog("schema load failed: ", err);
                    }
                },
                method: 'GET',
                dataType: 'json',
            });
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

var app = angular.module('SRWLightGateway', ['ngRoute']);

app.value('appRoutes', {});

app.config(function(appRoutesProvider, $locationProvider, $routeProvider) {
    $locationProvider.hashPrefix('');
    var appRoutes = appRoutesProvider.$get();
    Object.keys(LIGHT_SCHEMA.appRoutes).forEach(function(key) {
        appRoutes[key] = LIGHT_SCHEMA.appRoutes[key];
    });

    $routeProvider.when('/home', {
        template: [
            '<div data-page-heading="" data-lc="lc"></div>',
            '<div data-ng-repeat="item in lc.srwExamples" data-big-button="item"></div>',
            '<div class="lp-launch-button text-center" data-launch-button="" data-label="\'Launch SRW Full\'" data-url="\'/srw\'"></div>',
        ].join('')
    });
    Object.keys(appRoutes).forEach(function(key) {
        $routeProvider.when('/' + key, {
            template: [
                '<div data-page-heading="" data-lc="lc"></div>',
                '<div class="container">',
                    '<div class="row visible-xs">',
                        '<div class="lead text-center" data-ng-bind="lc.pageName()"></div>',
                    '</div>',
                    '<div data-ng-repeat="item in lc.itemsForCategory()" data-',
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

app.controller('LightController', function (appRoutes, $http, $location) {
    var self = this;
    self.srwExamples = SRW_EXAMPLES;
    self.location = $location;

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
        var name = self.pageName();
        return (name ? (name + ' - ') : '') + 'Synchrotron Radiation Workshop - RadiaSoft';
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
                controller = current.lc;
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

app.directive('launchButton', function() {
    return {
        restrict: 'A',
        scope: {
            label: '<',
            url: '<',
        },
        template: [
            '<a class="btn btn-default" data-ng-href="{{ url }}"><h4>{{ label }}</h4></a>',
        ].join(''),
    };
});

app.directive('pageHeading', function() {
    function getTemplate() {
        var template = [
                '<div class="lp-main-header-content lp-sub-header-content">',
                    '<a href="/old#about">',
                        '<img class="lp-header-sr-logo" src="/static/img/SirepoLogo.png',SIREPO.SOURCE_CACHE_KEY,'">',
                    '</a>',
        ].join('');
        template += [
            '<div class="lp-srw-sub-header-text">',
                '<a href="/old#/xray-beamlines.html">Synchrotron Radiation Workshop</a>',
                ' <span class="hidden-xs" data-ng-if="lc.pageName()">-</span> ',
                '<span class="hidden-xs" data-ng-if="lc.pageName()" data-ng-bind="lc.pageName()"></span>',
            '</div>',
        ].join('');
        template += [
                    '<div class="pull-right">',
                        '<a href="http://radiasoft.net">',
                            '<img class="lp-header-rs-logo" src="/static/img/RSLogo.png',SIREPO.SOURCE_CACHE_KEY,'" alt="RadiaSoft" />',
                        '</a>',
                    '</div>',
                '</div>',
        ].join('');
        return template;
    }
    return {
        restrict: 'A',
        scope: {
            lc: '=',
        },
        template: getTemplate(),
        controller: function($scope, $location) {
       },
    };
});
