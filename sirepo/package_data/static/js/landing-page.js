'use strict';

var app = angular.module('LandingPageApp', ['ngRoute']);

app.value('appRoutes', {
    'home': '',
    'calculator': 'SR Calculator',
    'light-sources': 'Light Source Facilities',
    'wavefront': 'Wavefront Propagator',
});

app.config(function($routeProvider, appRoutesProvider) {
    var appRoutes = appRoutesProvider.$get();
    Object.keys(appRoutes).forEach(function(key) {
        $routeProvider.when('/' + key, {
            templateUrl: '/static/html/landing-page-' + key + '.html?' + LANDING_PAGE_APP_VERSION,
        });
    });
    $routeProvider.otherwise({
        redirectTo: '/home',
    });
});

app.controller('LandingPageController', function ($location, appRoutes) {
    var self = this;

    self.pageName = function() {
        return appRoutes[$location.path().substring(1)];
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
