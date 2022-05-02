'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="geometry3d" data-geometry-3d="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-id="reportId"></div>
    `;
});

SIREPO.app.controller('GeometryController', function (appState, persistentSimulation, $scope) {
    const self = this;
    self.isGeometrySelected = () => {
        return appState.applicationState().geometryInput.dagmcFile;
    };
    self.isGeometryProcessed = () => {
        return Object.keys(appState.applicationState().volumes).length;
    };
    self.simScope = $scope;
    self.simComputeModel = 'dagmcAnimation';
    self.simHandleStatus = data => {
        if (data.volumes && ! self.isGeometryProcessed()) {
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('geometry')}"><a href data-ng-click="nav.openSection('geometry')"><span class="glyphicon glyphicon-globe"></span> Geometry</a></li>
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

SIREPO.app.directive('geometry3d', function(appState, plotting, requestSender, vtkToPNG, vtkPlotting, $rootScope) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            reportId: '<',
        },
        template: `
            <!--<div style="padding-bottom:1px; clear: both; border: 1px solid black">-->
              <div data-vtk-display="" class="vtk-display" style="width: 100%; height: 80vh;" data-show-border="true" data-model-name="{{ modelName }}" data-event-handlers="eventHandlers" data-enable-axes="false" data-axis-cfg="axisCfg" data-axis-obj="axisObj" data-enable-selection="true"></div>
              <!--<div class="sr-geometry3d-content" style="width: 100%; height: 80vh;"></div>-->
            <!--</div>-->
        `,
        controller: function($scope) {
            $scope.isClientOnly = true;
            let fullScreenRenderer = null;
            let renderer = null;
            let renderWindow = null;
            let vtkAPI = null;
            const actorByVolume = {};
            const bgColor = 1;
            const coordMapper = new SIREPO.VTK.CoordMapper();

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
                const b = coordMapper.buildActorBundle(reader, {
                    setColor: randomColor(),
                    setOpacity: 0.3,
                });
                //TODO(pjm): user defined colors and opacity per actor
                renderer.addActor(b.actor);
                actorByVolume[volId] = b.actor;
                return res;
            }

            function getRenderer() {
                return fullScreenRenderer.getRenderer();
            }

            function loadVolumes(volIds) {
                //TODO(pjm): update progress bar with each promise resolve?
                return Promise.all(volIds.map(i => addVolume(i)));
            }

            function randomColor() {
                return Array(3).fill(0).map(() => Math.random());
            }

            $scope.destroy = () => {
                //TODO(pjm): add vtk cleanup here
                fullScreenRenderer.getInteractor().unbindEvents();
            };

            $scope.init = () => {
                //TODO(pjm): need a "loading and/or progress bar" before results are available
                //fullScreenRenderer = vtk.Rendering.Misc.vtkFullScreenRenderWindow.newInstance({
                //    background: [1, 0.97647, 0.929412],
                //    container: $('.sr-geometry3d-content')[0],
                //});
                //const vols = [];
                //for (const n in appState.models.volumes) {
                //    vols.push(appState.models.volumes[n].volId);
                //}
                //loadVolumes(Object.values(vols)).then(() => {
                    //getRenderer().resetCamera();
                    //fullScreenRenderer.getRenderWindow().render();
                    //renderer.resetCamera();
                    //renderWindow.render();
                //});
            };

            $scope.resize = () => {
                //TODO(pjm): reposition camera?
            };

            $scope.$on('vtk-init', (e, d) => {
                $rootScope.$broadcast('vtk.showLoader');
                fullScreenRenderer = d.objects.fsRenderer;
                renderWindow = d.objects.window;
                renderer = d.objects.renderer;
                vtkAPI = d.api;

                const ca = vtk.Rendering.Core.vtkAnnotatedCubeActor.newInstance();
                vtk.Rendering.Core.vtkAnnotatedCubeActor.Presets.applyPreset('default', ca);
                const df = ca.getDefaultStyle();
                df.fontFamily = 'Arial';
                df.faceRotation = 45;
                ca.setDefaultStyle(df);

                const m = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
                    actor: ca,
                    interactor: renderWindow.getInteractor()
                });
                m.setViewportCorner(
                    vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.TOP_RIGHT
                );
                m.setViewportSize(0.07);
                m.computeViewport();
                m.setMinPixelSize(50);
                m.setMaxPixelSize(100);
                vtkAPI.setMarker(m);

                const vols = [];
                for (const n in appState.models.volumes) {
                    vols.push(appState.models.volumes[n].volId);
                }
                loadVolumes(Object.values(vols)).then(() => {
                    $rootScope.$broadcast('vtk.hideLoader');
                    renderWindow.render();
                    renderer.resetCamera();
                    renderWindow.render();
                });
                // move pickers to vtkdisplay?
                //cPicker = vtk.Rendering.Core.vtkCellPicker.newInstance();
                //cPicker.setPickFromList(false);
                //ptPicker = vtk.Rendering.Core.vtkPointPicker.newInstance();
                //ptPicker.setPickFromList(true);
                //ptPicker.initializePickList();
                //renderWindow.getInteractor().onLeftButtonPress(handlePick);
                //init();
            });

            $scope.$on('sr-volume-visibility-toggled', (event, volId, isVisible) => {
                actorByVolume[volId].getProperty().setOpacity(isVisible ? 0.3 : 0);
                renderWindow.render();
            });

            $scope.$on('sr-volume-alpha.changed', (event, volId, alpha) => {
                actorByVolume[volId].getProperty().setOpacity(alpha);
                renderWindow.render();
            });

        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('volumeMaterial', function(appState) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div style="padding: 10px">
              volume/material editor goes here
            </div>
        `,
    };
});

SIREPO.app.directive('volumeSelector', function(appState, $rootScope) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div style="padding: 0.5ex 1ex;">
              <div style="display: inline-block; cursor: pointer" data-ng-click="toggleAll()">
                <span class="glyphicon" data-ng-class="allVisible ? 'glyphicon-check' : 'glyphicon-unchecked'"></span>
              </div>
            </div>
            <div data-ng-repeat="row in rows track by $index" style="padding: 0.5ex 0 0.5ex 1ex; white-space: nowrap; overflow: hidden">
              <div>
                <div style="display: inline-block; cursor: pointer; white-space: nowrap" data-ng-click="toggleSelected(row)">
                  <span class="glyphicon" data-ng-class="row.isVisible ? 'glyphicon-check' : 'glyphicon-unchecked'"></span>
                   {{ row.name }}
                </div>
                <input id="volume-{{ row.name }}-alpha-range" type="range" min="0" max="1.0" step="0.01" data-ng-model="row.alpha" data-ng-change="setAlpha(row)">
              </div>
            </div>
        `,
        controller: function($scope) {
            $scope.allVisible = true;

            function init() {
                $scope.rows = [];
                for (const n in appState.models.volumes) {
                    const row = appState.models.volumes[n];
                    row.name = n;
                    row.isVisible = true;
                    row.alpha = 0.3;
                    $scope.rows.push(row);
                }
                //TODO(pjm): sort rows by name
            }
            
            $scope.setAlpha = row => {
                $rootScope.$broadcast('sr-volume-alpha.changed', row.volId, row.alpha);
            };
            $scope.toggleAll = () => {
                $scope.allVisible = ! $scope.allVisible;
                Object.values(appState.models.volumes).forEach(v => {
                    if (v.isVisible != $scope.allVisible) {
                        $scope.toggleSelected(v);
                    }
                });
            };

            $scope.toggleSelected = (row) => {
                row.isVisible = ! row.isVisible;
                appState.saveChanges('volumes');
                $rootScope.$broadcast('sr-volume-visibility-toggled', row.volId, row.isVisible);
            };

            init();
        },
    };
});

SIREPO.app.directive('volumeTabs', function() {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <ul class="nav nav-tabs">
              <li data-ng-repeat="tab in tabs track by $index" role="presentation" data-ng-class="{ active: activeTab == tab}"><a href data-ng-click="setTab($index)"><strong>{{ tab }}</strong></a></li>
            </ul>
            <div data-ng-show="activeTab == tabs[0]" data-volume-selector=""></div>
            <div data-ng-show="activeTab == tabs[1]" data-volume-material=""></div>
        `,
        controller: function($scope) {
            $scope.tabs = ['Viewer', 'Material'];
            $scope.activeTab = $scope.tabs[0];
            $scope.setTab = index => $scope.activeTab = $scope.tabs[index];
        },
    };
});
