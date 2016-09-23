'use strict';

var SRW_EXAMPLES;

SIREPO.srlog = console.log.bind(console);
SIREPO.srdbg = console.log.bind(console);

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

angular.element(document).ready(function() {
    $.ajax({
        url: '/static/json/srw-examples.json?' + SIREPO.APP_VERSION,
        success: function(result) {
            SRW_EXAMPLES = result;
            angular.bootstrap(document, ['LandingPageApp']);
        },
        error: function(xhr, status, err) {
            if (! SRW_EXAMPLES)
                srlog("srw examples load failed: ", err);
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

app.config(function($routeProvider, appRoutesProvider) {
    var appRoutes = appRoutesProvider.$get();
    $routeProvider.when('/home', {
        templateUrl: '/static/html/landing-page-home.html?' + SIREPO.APP_VERSION,
    });
    Object.keys(appRoutes).forEach(function(key) {
        $routeProvider.when('/' + key, {
            template: '<div data-ng-repeat="item in landingPage.itemsForCategory()" data-big-button="{{ item.name }}" data-image="{{ item.image }}" data-href="{{ landingPage.itemUrl(item) }}"></div>',
        });
    });
    $routeProvider.otherwise({
        redirectTo: '/home',
    });
});

app.controller('LandingPageController', function ($location, appRoutes) {
    var self = this;
    self.srwExamples = SRW_EXAMPLES;

    function pageCategory() {
        return $location.path().substring(1);
    }

    self.itemsForCategory = function() {
        for (var i = 0; i < self.srwExamples.length; i++) {
            if (self.srwExamples[i].category == pageCategory())
                return self.srwExamples[i].examples;
        }
    };

    self.itemUrl = function(item) {
        return '/find-by-name/srw/' + pageCategory() + '/' + encodeURIComponent(item.name);
    };

    self.pageName = function() {
        return appRoutes[pageCategory()];
    };

    self.pageTitle = function() {
        var name = self.pageName();
        return (name ? (name + ' - ') : '') + 'Synchrotron Radiation Workshop - Radiasoft';
    };
});

app.directive('bigButton', function() {
    return {
        scope: {
            title: '@bigButton',
            image: '@',
            href: '@',
        },
        template: [
            '<div class="row">',
              '<div class="col-md-6 col-md-offset-3">',
                '<a data-ng-href="{{ href }}" class="btn btn-default thumbnail lp-big-button"><h3>{{ title }}</h3><img data-ng-src="/static/img/{{ image }}" alt="{{ title }}" /></a>',
              '</div>',
            '</div>',
        ].join(''),
    };
});
