'use strict';

var LANDING_PAGE_SCHEMA;

SIREPO.srlog = console.log.bind(console);
SIREPO.srdbg = console.log.bind(console);

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

angular.element(document).ready(function() {
    $.ajax({
        url: '/static/json/landing-page-schema.json' + SIREPO.SOURCE_CACHE_KEY,
        success: function(result) {
            LANDING_PAGE_SCHEMA = result;
            angular.bootstrap(document, ['LandingPageApp']);
        },
        error: function(xhr, status, err) {
            if (! LANDING_PAGE_SCHEMA) {
                srlog("schema load failed: ", err);
            }
        },
        method: 'GET',
        dataType: 'json'
    });
});

var app = angular.module('LandingPageApp', ['ngRoute']);

app.value('appRoutes', {});

app.config(function(appRoutesProvider, $locationProvider, $routeProvider) {
    $locationProvider.hashPrefix('');

    var appRoutes = appRoutesProvider.$get();
    Object.keys(LANDING_PAGE_SCHEMA.appRoutes).forEach(function(key) {
        appRoutes[key] = LANDING_PAGE_SCHEMA.appRoutes[key];
    });

    $routeProvider.when('/about', {
        templateUrl: '/static/html/landing-page-about.html' + SIREPO.SOURCE_CACHE_KEY,
    });
    Object.keys(appRoutes).forEach(function(key) {
        $routeProvider.when('/' + key, {
            templateUrl: appRoutes[key].url + SIREPO.SOURCE_CACHE_KEY
        });
    });
    $routeProvider.otherwise({
        redirectTo: '/about',
    });
});

app.controller('LandingPageController', function ($http, $location) {
    var self = this;
    self.location = $location;

    self.comsolRegister = function() {
        $http.post('/comsol-register', {
            name: self.comsolName,
            email: self.comsolEmail,
        }).then(function() {
            self.comsolName = null;
            self.comsolEmail = null;
            $('#comsol-register-modal').modal('show');
        });
    };

    self.opps = LANDING_PAGE_SCHEMA.opportunities || [];

    self.onMainLandingPage = function () {
        return $location.path() === '/about';
    };

});
app.directive('lpCodesMenu', function(appRoutes) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div class="dropdown navbar-header-menu">',
                '<a href data-toggle="dropdown">Supported Codes <span class="caret"></span></a>',
                '<ul class="rs-light-green-background dropdown-menu dropdown-menu-left">',
                    '<li data-ng-repeat="route in codeRoutes" class="sr-model-list-item">',
                        '<a href="{{ route.codeURL }}" data-ng-click="">{{ route.codeTitle }}</a>',
                    '</li>',
                '</ul>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.codeRoutes = Object.keys(appRoutes)
                .map(function(k) {
                return appRoutes[k];
            }).filter(function (route) {
                return ! (! route.codeURL);
            }).sort(function (r1, r2) {
                return r1.codeTitle.localeCompare(r2.codeTitle);
            });
        },
    };
});

app.directive('lpBody', function(utilities, $document, $window) {
    return {
        restrict: 'A',
        scope: {},
        transclude: {
            lpInfoSlot: '?lpInfo',
            lpMediaSlot: '?lpMedia',
        },
        template: [
            '<div class="lp-flex-row" data-ng-class="{\'lp-main-header-offset\': onMainLandingPage()}">',
                '<div class="lp-flex-col col-md-7">',
                    '<div data-page-heading="" data-landing-page="landingPage"></div>',
                    '<div data-ng-transclude="lpInfoSlot">',
                        '<div data-lp-info-panel=""></div>',
                    '</div>',
                    '<div data-ng-show="showOpps()" class="lp-opportunities main-page" data-ng-class="{\'short\': applyOverlapClass() }" data-lp-opportunities="" data-opps="opps"></div>',
                '</div>',
                '<div class=" lp-flex-col col-md-5 rs-blue-background">',
                    '<div data-ng-if="onMainLandingPage()" class="lp-main-header lp-show-wide">',
                        '<div class="lp-main-header-content">',
                            '<a class="pull-right" href="http://radiasoft.net">',
                                '<img width="256px" height="auto" src="/static/img/RSLogo.png',SIREPO.SOURCE_CACHE_KEY,'" alt="RadiaSoft" />',
                            '</a>',
                        '</div>',
                    '</div>',
                    '<div data-ng-transclude="lpMediaSlot"  class="lp-full-height rs-blue-background">',
                        '<div data-lp-media-panel="" class="lp-full-height"></div>',
                    '</div>',
                '</div>',
            '</div>',
        ].join(''),
        link: function(scope) {
            scope.applyOverlapClass = function() {
                return $('.lp-opportunities')[0].getBoundingClientRect().bottom >= $window.innerHeight - 12 &&
                    utilities.checkContentOverlap('.lp-info-panel-content .lp-list', '.lp-opportunities', 0);
            };
        },
        controller: function($scope, $location) {

            $scope.opps = utilities.getOpportunities();

            $scope.onMainLandingPage = function () {
                return $location.path() === '/about';
            };

            $scope.showOpps = function() {
                return $scope.opps[0] && $scope.onMainLandingPage();
            };

            // just run the digest cycle to trigger applyOverlapClass
            function resize() {
                $scope.$apply();
            }

            $($window).on('resize', resize);

            $scope.$on('$destroy', function() {
                $($window).off('resize', resize);
            });
       },
    };
});

app.directive('lpInfoPanel', function(appRoutes, utilities) {
    return {
        restrict: 'A',
        scope: {},
        transclude: {
            lpInfoContentSlot: '?lpInfoContent',
            lpInfoDocsSlot: '?lpInfoDocs',
            lpInfoPubsSlot: '?lpInfoPubs',
            lpInfoDOEFooterSlot: '?lpInfoDoeFooter',
        },
        template: [
                '<div class="lp-info-panel-top-stripe rs-green-background">{{ infoPanelTitle() }}</div>',
                '<div class="lp-info-panel-content" data-ng-transclude="lpInfoContentSlot"></div>',
                '<div class="lp-info-panel-content" data-ng-transclude="lpInfoDocsSlot"></div>',
                '<div id="lpInfoPubs" class="lp-info-panel-content" data-ng-transclude="lpInfoPubsSlot"></div>',
                '<div id="lpInfoDOEFooter" data-ng-transclude="lpInfoDOEFooterSlot"></div>',
        ].join(''),
        controller: function($scope, $location) {
            $scope.infoPanelTitle = function() {
                var route = appRoutes[$location.path().substring(1)];
                return route ? route.infoPanelTitle || '' : '';
            };
            $scope.utilities = utilities;
        },
    };
});

app.directive('lpDoeFooter', function(utilities) {
    return {
        restrict: 'A',
        scope: {},
        transclude: {
            lpInfoDOEFooterTextSlot: '?lpInfoDoeFooterText',
        },
        template: [
            '<div class="lp-doe-footer" data-ng-class="{\'lp-doe-footer-would-overlap\': applyOverlapClass() }">',
                '<img src="/static/img/RGB_White-Seal_White-Mark_SC_Horizontal.png',SIREPO.SOURCE_CACHE_KEY,'">',
                '<div data-ng-transclude="lpInfoDOEFooterTextSlot"></div>',
            '</div>',
        ].join(''),
        link: function($scope) {
            $scope.applyOverlapClass = function() {
                return utilities.checkContentOverlap('div[data-lp-info-panel]', '.lp-doe-footer', 8);
            };
        },
    };
});

app.directive('lpMediaPanel', function(appRoutes, utilities) {
    return {
        restrict: 'A',
        scope: {},
        transclude: {
            lpMediaContentSlot: '?lpMediaContent',
        },
        template: [
            '<div class="lp-media-panel">',
                '<div class="lp-media-container">',
                    '<div class="lp-media-viewport">',
                        '<iframe data-ng-if="mediaPanelURL() != null" width="420px" height="315px" data-ng-src="{{ mediaPanelURL() }}" frameborder="0" gesture="media" allow="encrypted-media"></iframe>',
                    '</div>',
                    '<div data-ng-if="mediaPanelURL() != null" class="caption">{{ mediaPanelTitle() }}</div>',
                '</div>',
                '<div data-ng-transclude="lpMediaContentSlot"></div>',
                '<div data-ng-show="! onMainLandingPage()">',
                    '<div class="lp-media-rs-footer"  data-ng-class="{\'lp-media-rs-footer-would-overlap\': applyOverlapClass() }">',
                        '<a href="http://radiasoft.net">',
                            '<img width="256px" height="auto" src="/static/img/RSLogo.png',SIREPO.SOURCE_CACHE_KEY,'" alt="RadiaSoft" />',
                        '</a>',
                    '</div>',
                '</div>',
            '</div>',
        ].join(''),
        link: function($scope) {
            $scope.applyOverlapClass = function() {
                return utilities.checkContentOverlap('.lp-media-panel', '.lp-media-rs-footer', 8);
            };
        },
        controller: function($scope, $location, $sce) {
            var routeConfig  = appRoutes[$location.path().substring(1)] || {};
            var mediaConfig = routeConfig.mediaConfig || {};

            if(mediaConfig.placeholder) {
                $('.lp-media-viewport').css('background-image', 'url(' + mediaConfig.placeholder + ')');
            }

            $scope.onMainLandingPage = function () {
                return $location.path() === '/about';
            };
            $scope.mediaPanelTitle = function() {
                return mediaConfig.title || 'What is Sirepo?';
            };
            $scope.mediaPanelURL= function() {
                if(mediaConfig.url) {
                    return $sce.trustAsResourceUrl(mediaConfig.url);
                }
                return null;
            };
       },
    };
});

app.directive('lpOpportunities', function(utilities, $sce) {
    return {
        restrict: 'A',
        scope: {
            opps: '<',
        },
        template: [
            '<div class="lp-info">',
                '<span class="header">New Opportunity!</span>',
                '<ul>',
                '<li class="lp-opportunity">',
                    '<span class="title">{{ firstOpp.title }}</span>',
                    '<div><span data-ng-bind-html="firstText"></span> <span class="glyphicon glyphicon-star rs-blue" style="padding-left: 8px;"></span> <a href="{{ firstURL }}">Check it out</a></div>',
                '</li>',
                '</ul>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.opps = $scope.opps || utilities.getOpportunities();
            $scope.firstOpp = $scope.opps[0];
            $scope.firstText = $sce.trustAsHtml($scope.firstOpp.text);
            $scope.firstURL = $sce.trustAsResourceUrl($scope.firstOpp.url);
        },
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
                '<div class="lp-main-header-content" data-ng-class="{\'lp-sub-header-content\': ! onMainLandingPage()}">',
                    '<a href="/en/landing.html">',
                        '<img class="lp-header-sr-logo" src="/static/img/SirepoLogo.png',SIREPO.SOURCE_CACHE_KEY,'">',
                    '</a>',
                    '<div data-ng-show="onMainLandingPage()" class="pull-right lp-hide-wide">',
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
            landingPage: '=',
        },
        template: getTemplate(),
        controller: function($scope, $location) {
            $scope.onMainLandingPage = function() {
                return $location.path() === '/about';
            };
       },
    };
});

app.directive('modeSelector', function() {
    return {
        restrict: 'A',
        scope: {
            launchLabel: '@',
            modeMap: '<',
        },
        template: [
        '<div class="row">',
          '<div class="col-sm-6 col-sm-offset-3" style="font-weight: 500;">Select the mode you\'d like to run in</div>',
          '<div class="col-sm-12" style="display: flex; justify-content: flex-start; align-items: flex-end;">',
            '<div class="col-sm-6">',
              '<div class="panel">',
                '<div class="panel-heading">',
                  '<ul class="nav nav-tabs">',
                    '<li data-ng-class="{active: mode.default}"  data-ng-repeat="mode in modeMap track by $index" data-toggle="tab"><a href="#mode_{{$index}}" data-ng-click="setMode(mode)">{{ mode.name }}</a></li>',
                  '</ul>',
                '</div>',
                '<div class="panel-body">',
                  '<div class="tab-content">',
                    '<div data-ng-class="{active: mode == currentMode}" class="tab-pane" data-ng-repeat="mode in modeMap track by $index" data-ng-id="mode_{{$index}}">{{ mode.text }}</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
            '<div class="lp-launch-button" data-launch-button="" data-label="launchLabel" data-url="urlForMode()"></div>',
          '</div>',
        '</div>',
        ].join(''),
        link: function($scope) {
        },
        controller: function($scope, $element) {
            $scope.currentMode = $.grep($scope.modeMap, function(mode) {
                return mode.default;
            })[0];
            $scope.setMode = function(m) {
                $scope.currentMode = m;
            };
            $scope.urlForMode = function() {
                return $scope.currentMode.url;
            };
            $scope.textForMode = function() {
                return $scope.currentMode.text;
            };
       },
    };
});

app.service('utilities', function() {

    this.getOpportunities = function () {
        return LANDING_PAGE_SCHEMA.opportunities || [];
    };

    this.checkContentOverlap = function(container, footer, offset) {

        // exclude divs with no height
        var footerContent = $(footer).find('*').addBack('*').filter(function () {
            return $(this).outerHeight() > 0;
        }).toArray();
        var containerContent = $(container).find('*').filter(function () {
            return $(this).outerHeight() > 0;
        }).toArray();
        var contentBottom = this.bottomEdge(
            containerContent.filter(function (el) {
                return footerContent.indexOf(el) < 0;
            })
        );
        var footerTop = this.topEdge(footerContent);
        return contentBottom + offset > footerTop;
    };
    this.bottomEdge = function(elements) {
        return elements.reduce(function(newBottom, el) {
            return Math.max(newBottom, bottom(el));
        }, Number.MIN_SAFE_INTEGER);
    };
    this.topEdge = function(elements) {
        return elements.reduce(function(newTop, el) {
            return Math.min(newTop, $(el).offset().top);
        }, Number.MAX_SAFE_INTEGER);
    };
    function bottom(el) {
        return $(el).offset().top + $(el).outerHeight(true);
    }
});
