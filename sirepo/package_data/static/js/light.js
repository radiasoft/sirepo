'use strict';

SIREPO.srlog = console.log.bind(console);
SIREPO.srdbg = console.log.bind(console);

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

var SRW_EXAMPLES = [
    {
        "category": "calculator",
        "name": "Synchrotron Radiation",
        "image": "source-undulator.png",
        "examples": [
            {
                "name": "Undulator Radiation",
                "image": "source-undulator.png"
            },
            {
                "name": "Bending Magnet Radiation",
                "image": "source-bending-magnet.png"
            },
            {
                "name": "Idealized Free Electron Laser Pulse",
                "image": "source-fel.png"
            }
        ]
    },
    {
        "category": "wavefront",
        "name": "Wavefront Propagation",
        "image": "young-double-slit.png",
        "examples": [
            {
                "name": "Diffraction by an Aperture",
                "image": "circular-aperture.png"
            },
            {
                "name": "Young's Double Slit Experiment",
                "image": "young-double-slit.png"
            },
            {
                "name": "Young's Double Slit Experiment (green laser)",
                "image": "young-double-slit.png"
            },
            {
                "name": "Young's Double Slit Experiment (green laser, no lens)",
                "image": "young-double-slit.png"
            }
        ]
    },
    {
        "category": "light-sources",
        "name": "Light Source Facilities",
        "image": "nsls-ii.png",
        "examples": [
            {
                "name": "NSLS-II beamline",
                "simulations": [
                    {
                        "image": "nsls-ii-hxn.png",
                        "simulationName": "NSLS-II HXN beamline"
                    },
                    {
                        "image": "nsls-ii-srx.png",
                        "simulationName": "NSLS-II SRX beamline"
                    },
                    {
                        "image": "nsls-ii-chx.png",
                        "simulationName": "NSLS-II CHX beamline"
                    },
                    {
                        "image": "nsls-ii-smi.png",
                        "simulationName": "NSLS-II SMI beamline"
                    },
                    {
                        "image": "nsls-ii-fmx.png",
                        "simulationName": "NSLS-II FMX beamline"
                    },
                    {
                        "image": "nsls-ii-esm.png",
                        "simulationName": "NSLS-II ESM beamline"
                    },
                    {
                        "image": "nsls-ii-csx.png",
                        "simulationName": "NSLS-II CSX-1 beamline"
                    }
                ]
            },
            {
                "name": "LCLS beamline",
                "simulations": [
                    {
                        "name": "LCLS SXR",
                        "image": "lcls.png",
                        "simulationName": "LCLS SXR beamline"
                    }
                ]
            }
        ]
    }
];

var LIGHT_SCHEMA = {
    "appRoutes": {
        "calculator": "SR Calculator",
        "light-sources": "Light Source Facilities",
        "wavefront": "Wavefront Propagation"
    }
};

var app = angular.module('SRWLightGateway', ['ngRoute']);
app.value('appRoutes', {});

app.config(function(appRoutesProvider, $locationProvider, $routeProvider) {
    $locationProvider.hashPrefix('');
    var appRoutes = appRoutesProvider.$get();
    Object.keys(LIGHT_SCHEMA.appRoutes).forEach(function(key) {
        appRoutes[key] = LIGHT_SCHEMA.appRoutes[key];
    });

    $routeProvider.when('/home', {
        template: `
            <div data-page-heading="" data-lc="lc"></div>
            <div class="container">
              <div data-ng-repeat="item in lc.srwExamples" data-big-button="item"></div>
              <div class="lp-launch-button text-center" data-launch-button="" data-label="\'Launch SRW Full\'" data-url="\'/srw\'"></div>
            </div>
        `
    });
    Object.keys(appRoutes).forEach(function(key) {
        $routeProvider.when('/' + key, {
            template: `
                <div data-page-heading="" data-lc="lc"></div>
                <div class="container">
                    <div class="row visible-xs">
                        <div class="lead text-center" data-ng-bind="lc.pageName()"></div>
                    </div>
                    <div data-ng-repeat="item in lc.itemsForCategory()" data-${key === 'light-sources' ? 'button-list' : 'big-button'}="item"></div>
                </div>
            `,
        });
    });
    $routeProvider.otherwise({
        redirectTo: '/home',
    });
});

app.controller('LightController', function (appRoutes, $location) {
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
        template: `
            <div class="row">
              <div data-ng-class="item.class">
                <a data-ng-href="{{ item.url }}" class="btn btn-default thumbnail lp-big-button"><h3 data-ng-if="item.name">{{ item.name }}</h3><img data-ng-if="item.image" data-ng-src="/static/img/{{ item.image }}" alt="{{ item.name }}" /><span class="lead text-primary" style="white-space: pre" data-ng-if="item.buttonText">{{ item.buttonText }}</span></a>
              </div>
            </div>
        `,
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
        template: `
            <div class="row">
              <div class="col-md-8 col-md-offset-2">
                <div class="well">
                  <h3>{{ item.name }}</h3>
                  <div data-ng-repeat="item in item.simulations" data-big-button="item" data-wide-col="1"></div>
                </div>
              </div>
            </div>
        `,
    };
});

app.directive('launchButton', function() {
    return {
        restrict: 'A',
        scope: {
            label: '<',
            url: '<',
        },
        template: `
            <a class="btn btn-default" data-ng-href="{{ url }}"><h4>{{ label }}</h4></a>
        `,
    };
});

app.directive('pageHeading', function() {
    return {
        restrict: 'A',
        scope: {
            lc: '=',
        },
        template: `
            <nav class="navbar navbar-default navbar-static-top">
              <div class="container-fluid">
                <a class="navbar-brand" href="/en/xray-beamlines.html">
                  <img style="width: 40px; margin-top: -10px" src="/static/img/sirepo.gif${SIREPO.SOURCE_CACHE_KEY}">
                </a>
                <div class="navbar-brand">
                  <a data-ng-if="lc.pageName()" href="#home">Synchrotron Radiation Workshop</a>
                  <span data-ng-if="! lc.pageName()">Synchrotron Radiation Workshop</span>
                   <span class="hidden-xs" data-ng-if="lc.pageName()">-</span>
                  <span class="hidden-xs" data-ng-if="lc.pageName()" data-ng-bind="lc.pageName()"></span>
                </div>
              </div>
            </nav>
        `,
    };
});
