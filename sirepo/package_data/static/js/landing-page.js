'use strict';

var SRW_EXAMPLES;
var LANDING_PAGE_SCHEMA;

SIREPO.srlog = console.log.bind(console);
SIREPO.srdbg = console.log.bind(console);

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.IS_SRW_LANDING_PAGE = window.location.href.match(/\/light/);

//TODO(mvk): refactor srw light properly (part of #1304)
angular.element(document).ready(function() {
    $.ajax({
        url: '/static/json/srw-examples.json' + SIREPO.SOURCE_CACHE_KEY,
        success: function(result) {
            SRW_EXAMPLES = result;
            //angular.bootstrap(document, ['LandingPageApp']);
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

var app = angular.module('LandingPageApp', ['ngRoute']);

app.value('appRoutes', {});
app.value('srwAppRoutes', {});

app.config(function(appRoutesProvider, srwAppRoutesProvider, $locationProvider, $routeProvider) {
    $locationProvider.hashPrefix('');
    // srw landing page
    if (SIREPO.IS_SRW_LANDING_PAGE) {
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
    }
    // root landing page
    else {
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
    }
});

app.controller('LandingPageController', function (appRoutes, srwAppRoutes, $http, $location) {
    var self = this;
    self.srwExamples = SRW_EXAMPLES;

    function pageCategory() {
        return $location.path().substring(1);
    }

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
        if (SIREPO.IS_SRW_LANDING_PAGE) {
            var name = self.pageName();
            return (name ? (name + ' - ') : '') + 'Synchrotron Radiation Workshop - Radiasoft';
        }
        return 'Sirepo - Radiasoft';
    };

    self.onMainLandingPage = function () {
        return $location.path() === '/about';
    };

    self.getModeMap = function(route) {
        return appRoutes[route].modeMap;
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

app.directive('lpBody', function() {
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
                '</div>',
                '<div class=" lp-flex-col col-md-5 rs-blue-background">',
                    '<div data-ng-if="onMainLandingPage()" class="lp-main-header lp-show-wide">',
                        '<div class="lp-main-header-content">',
                            '<a class="pull-right" href="http://radiasoft.net">',
                                '<img width="256px" height="auto" src="/static/img/RSLogo.png',SIREPO.SOURCE_CACHE_KEY,'" alt="Radiasoft" />',
                            '</a>',
                        '</div>',
                    '</div>',
                    '<div data-ng-transclude="lpMediaSlot"  class="lp-full-height rs-blue-background">',
                        '<div data-lp-media-panel="" class="lp-full-height"></div>',
                    '</div>',
                '</div>',
            '</div>',
        ].join(''),
        controller: function($scope, $location) {
            $scope.onMainLandingPage = function () {
                return $location.path() === '/about';
            };
       },
    };
});

app.directive('lpInfoPanel', function(appRoutes) {
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
                            '<img width="256px" height="auto" src="/static/img/RSLogo.png',SIREPO.SOURCE_CACHE_KEY,'" alt="Radiasoft" />',
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

app.directive('pageHeading', function(srwAppRoutes) {
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

app.directive('modeSelector', function(utilities) {
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
