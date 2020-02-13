'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.controller('RadiaSourceController', function (appState, panelState, $scope) {
    const self = this;

    appState.whenModelsLoaded($scope, function() {
        // initial setup
        //appState.watchModelFields($scope, ['model.field'], function() {
        //});
        //srdbg('RadiaSourceController');
    });
});

SIREPO.app.controller('RadiaVisualizationController', function (appState, panelState, $scope) {
    const self = this;

    appState.whenModelsLoaded($scope, function() {
        // initial setup
       // appState.watchModelFields($scope, ['model.field'], function() {
        //});
        //srdbg('RadiaVisualizationController', appState.models);
    });
});

SIREPO.app.directive('radiaViewer', function(appState, errorService, frameCache, geometry, layoutService, panelState, plotting, plotToPNG, requestSender, utilities, vtkPlotting, $timeout) {

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: [
            '<div class="col-md-6">',
                '<div data-basic-editor-panel="" data-view-name="{{modelName}}">',
                    '<button class="btn btn-default col-sm-2 col-sm-offset-5" data-ng-click="solve()">Solve</button>',
                    '<div data-vtk-display="" data-model-name=""></div>',
                '</div>',
            '</div>',

        ].join(''),
        controller: function($scope, $element) {

            $scope.model = appState.models[$scope.modelName];

            const cm = vtkPlotting.coordMapper();
            let renderer = null;
            let renderWindow = null;
            let vtkAPI = {};
            const watchFields = [
                 'magnetDisplay.pathType',
                 'magnetDisplay.viewType',
                 'solver.fieldType',
            ];


            function init() {
                srdbg('init...');
                appState.watchModelFields($scope, watchFields, updateViewer);
                if (! renderer) {
                    throw new Error('No renderer!');
                }
                //srdbg(appState.models.simulation);
                //renderer.getLights()[0].setLightTypeToSceneLight();
                const b = cm.buildSphere(null, null, [1, 0, 0]);
                b.actor.getProperty().setEdgeVisibility(true);
                vtkPlotting.addActor(renderer, b.actor);
                updateViewer();
            }

            function updateViewer() {
                srdbg('updateViewer');
                //panelState.requestData('display', function (d) {
                 //   srdbg('got display', d);
                //}, true);
                panelState.requestData('geometry');
                vtkAPI.setCam();
            }

            $scope.solve = function() {
                srdbg('SOLVE');
               // panelState.requestData('');
            };

            //appState.watchModelFields($scope, watchFields, updateViewer);

            appState.whenModelsLoaded($scope, function () {
                srdbg('radia models loaded');
                //appState.watchModelFields($scope, watchFields, updateViewer);
                //updateViewer();
            });

            // or keep stuff on vtk viewer scope?
            // start using custom javascript events to break away from angular?
            $scope.$on('vtk-init', function (e, d) {
                srdbg('VTK INIT', e, d);
                renderer = d.objects.renderer;
                renderWindow = d.objects.window;
                vtkAPI = d.api;
                init();
            });

        },
    };
});


SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-common-footer="nav"></div>',
        ].join(''),
    };
});

SIREPO.app.directive('appHeader', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: [
            '<div data-app-header-brand="nav"></div>',
            '<div data-app-header-left="nav"></div>',
            '<div data-app-header-right="nav">',
              '<app-header-right-sim-loaded>',
                '<div data-sim-sections="">',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'visualization\')}"><a href data-ng-click="nav.openSection(\'visualization\')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
                '</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
                //  '<div>App-specific setting item</div>',
              '</app-settings>',
              '<app-header-right-sim-list>',
                '<ul class="nav navbar-nav sr-navbar-right">',
                  '<li><a href data-ng-click=""><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>',
                '</ul>',
              '</app-header-right-sim-list>',
            '</div>',
        ].join(''),
    };
});
