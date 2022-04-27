'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="geometry3d" data-geometry-3d="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-id="reportId"></div>
    `;
});

SIREPO.app.controller('SourceController', function (appState, persistentSimulation, $scope) {
    const self = this;
    self.isGeometrySelected = () => {
        return appState.applicationState().geometryInput.dagmcFile;
    };
    self.isGeometryProcessed = () => {
        return appState.applicationState().volumes;
    };
    self.simScope = $scope;
    self.simComputeModel = 'dagmcAnimation';
    self.simHandleStatus = data => {
        if (data.volumes && ! appState.models.volumes) {
            appState.models.volumes = data.volumes;
            appState.saveChanges('volumes');
        }
    };
    self.simState = persistentSimulation.initSimulationState(self);
});

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
        `,
    };
});

SIREPO.app.directive('appHeader', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: `
            <div data-app-header-brand="nav"></div>
            <div data-app-header-left="nav"></div>
            <div data-app-header-right="nav">
              <app-header-right-sim-loaded>
                <div data-sim-sections="">
                  <li class="sim-section" data-ng-class="{active: nav.isActive('source')}"><a href data-ng-click="nav.openSection('source')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
              </app-settings>
              <app-header-right-sim-list>
              </app-header-right-sim-list>
            </div>
        `,
    };
});

SIREPO.app.directive('geometry3d', function(appState, plotting, requestSender, vtkToPNG) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            reportId: '<',
        },
        template: `
            <div style="float: right; margin-top: -10px; margin-bottom: 5px;">
            <div style="display: inline-block" data-ng-repeat="dim in ::dimensions track by $index">
            <button data-ng-attr-class="btn btn-{{ selectedDimension == dim ? \'primary\' : \'default\' }}" data-ng-click="setCamera(dim)">{{ dim | uppercase }}{{ viewDirection[dim] > 0 ? \'+\' : \'-\' }}</button>
            </div>
            </div>
            <div style="padding-bottom:1px; clear: both; border: 1px solid black">
              <div class="sr-geometry3d-content" style="width: 100%; height: 50vw;"></div>
            </div>
        `,
        controller: function($scope, $element) {
            $scope.isClientOnly = true;
            let fullScreenRenderer = null;
            const actorByVolume = {};

            function volumeURL(volId) {
                return requestSender.formatUrl(
                    'downloadDataFile',
                    {
                        '<simulation_id>': appState.models.simulation.simulationId,
                        '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        '<model>': 'dagmcAnimation',
                        '<frame>': volId,
                    });
            }

            function addVolume(volId) {
                const reader = vtk.IO.Core.vtkHttpDataSetReader.newInstance();
                const res = reader.setUrl(volumeURL(volId), {
                    compression: 'zip',
                    fullpath: true,
                    loadData: true,
                });
                const mapper = vtk.Rendering.Core.vtkMapper.newInstance();
                mapper.setInputConnection(reader.getOutputPort());
                const actor = vtk.Rendering.Core.vtkActor.newInstance();
                actor.setMapper(mapper);
                //TODO(pjm): user defined colors and opacity
                actor.getProperty().setColor(randomColor());
                actor.getProperty().setOpacity(0.3);
                getRenderer().addActor(actor);
                actorByVolume[volId] = actor;
                return res;
            }

            function getRenderer() {
                return fullScreenRenderer.getRenderer();
            }

            function loadVolumes(volIds) {
                return Promise.all(volIds.map(i => addVolume(i)));
            }

            function randomColor() {
                return [
                    Math.random(),
                    Math.random(),
                    Math.random(),
                ];
            }

            $scope.destroy = () => {
                //TODO(pjm): add vtk cleanup here
                fullScreenRenderer.getInteractor().unbindEvents();
            };

            $scope.init = () => {
                fullScreenRenderer = vtk.Rendering.Misc.vtkFullScreenRenderWindow.newInstance({
                    background: [1, 0.97647, 0.929412],
                    container: $('.sr-geometry3d-content')[0],
                });
                const vols = Object.values(appState.models.volumes);
                loadVolumes(vols).then(() => {
                    getRenderer().resetCamera();
                    fullScreenRenderer.getRenderWindow().render();
                });
            };

            $scope.resize = () => {

            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});
