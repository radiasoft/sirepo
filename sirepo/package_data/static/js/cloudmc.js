'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="geometry3d" data-geometry-3d="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-id="reportId"></div>
    `;
    SIREPO.appFieldEditors = `
        <div data-ng-switch-when="Color" data-ng-class="fieldClass">
          <input type="color" data-ng-model="model[field]" class="sr-color-button">
        </div>
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

SIREPO.app.directive('geometry3d', function(appState, panelState, plotting, requestSender, vtkToPNG, vtkPlotting, $rootScope) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            reportId: '<',
        },
        template: `
            <div data-vtk-display="" class="vtk-display" style="width: 100%; height: 80vh;" data-show-border="true" data-model-name="{{ modelName }}" data-event-handlers="eventHandlers" data-reset-side="z" data-enable-axes="true" data-axis-cfg="axisCfg" data-axis-obj="axisObj" data-enable-selection="true"></div>
        `,
        controller: function($scope) {
            $scope.isClientOnly = true;
            $scope.model = appState.models[$scope.modelName];

            let picker = null;
            let fullScreenRenderer = null;
            let renderer = null;
            let renderWindow = null;
            let vtkAPI = null;
            const bundleByVolume = {};
            const coordMapper = new SIREPO.VTK.CoordMapper();
            const watchFields = ['geometry3DReport.bgColor', 'geometry3DReport.showEdges'];

            function buildOpacityDelegate() {
                const m = $scope.modelName;
                const f = 'opacity';
                const d = panelState.getFieldDelegate(m, f);
                d.range = function() {
                    return {
                        min: appState.fieldProperties(m, f).min,
                        max: appState.fieldProperties(m, f).max,
                        step: 0.01
                    };
                };
                d.readout = function() {
                    return appState.modelInfo(m)[f][SIREPO.INFO_INDEX_LABEL];
                };
                d.update = setGlobalProperties;
                d.watchFields = [];
                $scope.fieldDelegate = d;
            }

            function addVolume(volId) {
                const reader = vtk.IO.Core.vtkHttpDataSetReader.newInstance();
                const res = reader.setUrl(volumeURL(volId), {
                    compression: 'zip',
                    fullpath: true,
                    loadData: true,
                });
                const v = getVolumeById(volId);
                const b = coordMapper.buildActorBundle(reader, {
                    color: v.color,
                    opacity: v.opacity,
                    edgeVisibility: $scope.model.showEdges === '1',
                });
                bundleByVolume[volId] = b;
                renderer.addActor(b.actor);
                return res;
            }

            function getVolumeById(volId) {
                for (const n in appState.models.volumes) {
                    const v = appState.models.volumes[n];
                    if (v.volId === volId) {
                        return v;
                    }
                }
                return null;
            }

            function getVolumeByActor(a) {
                for (const volId in bundleByVolume) {
                    if (bundleByVolume[volId].actor === a) {
                        return getVolumeById(volId);
                    }
                }
                return null;
            }

            function handlePick(callData) {
                if (renderer !== callData.pokedRenderer) {
                    return;
                }

                // regular clicks are generated when spinning the scene - we'll select/deselect with ctrl-click
                if (vtkAPI.getMode() === VTKUtils.INTERACTION_MODE_MOVE ||
                    (vtkAPI.getMode() === VTKUtils.INTERACTION_MODE_SELECT && ! callData.controlKey)
                ) {
                    return;
                }

                const pos = callData.position;
                picker.pick([pos.x, pos.y, 0.0], renderer);

                const pas = picker.getActors();

                // it seems the 1st actor in the array is the closest to the viewer
                const actor = pas[0];
                const v = getVolumeByActor(actor);
            }

            function loadVolumes(volIds) {
                //TODO(pjm): update progress bar with each promise resolve?
                return Promise.all(volIds.map(i => addVolume(i)));
            }

            function setGlobalProperties() {
                if (! renderer) {
                    return;
                }
                vtkAPI.setBg(appState.models.geometry3DReport.bgColor);
                for (const volId in bundleByVolume) {
                    const b = bundleByVolume[volId];
                    const v = getVolumeById(volId);
                    b.setActorProperty(
                        'opacity',
                        v.isVisible ? v.opacity * appState.models.geometry3DReport.opacity : 0
                    );
                    b.setActorProperty(
                        'edgeVisibility',
                        appState.models.geometry3DReport.showEdges === '1'
                    );
                }
                renderWindow.render();
            }

            function setVolumeProperty(bundle, name, value) {
                bundle.setActorProperty(name, value);
                renderWindow.render();
            }

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

            // the vtk teardown is handled in vtkPlotting
            $scope.destroy = () => {};

            $scope.init = () => {
                buildOpacityDelegate();
                setGlobalProperties();
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
                picker = vtk.Rendering.Core.vtkCellPicker.newInstance();
                picker.setPickFromList(false);
                renderWindow.getInteractor().onLeftButtonPress(handlePick);
            });

            $scope.$on('sr-volume-visibility-toggled', (event, volId, isVisible) => {
                setVolumeProperty(
                    bundleByVolume[volId], 'opacity', isVisible ? getVolumeById(volId).opacity : 0
                );
            });

            for (const p of SIREPO.APP_SCHEMA.constants.volumeProperties) {
                $scope.$on(`sr-volume-${p}.changed`, (event, volId, val) => {
                    if (p === 'opacity') {
                        getVolumeById(volId).isVisible = val > 0;
                    }
                    setVolumeProperty(bundleByVolume[volId], p, val);
                });
            }

            appState.watchModelFields($scope, watchFields, setGlobalProperties);
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
                <input id="volume-{{ row.name }}-opacity-range" type="range" min="0" max="1.0" step="0.01" data-ng-model="row.opacity" data-ng-change="broadcastOpacityChanged(row)">
                <input id="volume-{{ row.name }}-color" type="color" data-ng-model="row.color" data-ng-change="broadcastColorChanged(row)">
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
                    row.color = SIREPO.VTK.VTKUtils.colorToHex(row.color || randomColor());
                    row.opacity = row.opacity || 0.3;
                    const v = row.isVisible;
                    row.isVisible = v === undefined ? true : v;
                    $scope.rows.push(row);
                }
                appState.saveChanges('volumes');
                //TODO(pjm): sort rows by name
            }

            function randomColor() {
                return Array(3).fill(0).map(() => Math.random());
            }

            for (const p of SIREPO.APP_SCHEMA.constants.volumeProperties) {
                $scope[`broadcast${SIREPO.UTILS.capitalize(p)}Changed`] = row => {
                    appState.saveChanges('volumes');
                    $rootScope.$broadcast(`sr-volume-${p}.changed`, row.volId, row[p]);
                }
            }

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
