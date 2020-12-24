'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="MadxSimList" data-ng-class="fieldClass">',
          '<div data-sim-list="" data-model="model" data-field="field" data-code="madx" data-route="lattice"></div>',
        '</div>',
        // TODO(pjm): copied from webcon
        '<div data-ng-switch-when="MiniFloat" class="col-sm-7">',
          '<input data-string-to-number="" data-ng-model="model[field]" data-min="info[4]" data-max="info[5]" class="form-control" style="text-align: right" data-lpignore="true" required />',
        '</div>',
    ].join('');
    // TODO(e-carlin): copied from madx
    SIREPO.lattice = {
        elementColor: {
            OCTUPOLE: 'yellow',
            QUADRUPOLE: 'red',
            SEXTUPOLE: 'lightgreen',
            VKICKER: 'blue',
        },
        elementPic: {
            aperture: ['COLLIMATOR', 'ECOLLIMATOR', 'RCOLLIMATOR'],
            bend: ['RBEND', 'SBEND'],
            drift: ['DRIFT'],
            lens: ['NLLENS'],
            magnet: ['HACDIPOLE', 'HKICKER', 'KICKER', 'MATRIX', 'MULTIPOLE', 'OCTUPOLE', 'QUADRUPOLE', 'RFMULTIPOLE', 'SEXTUPOLE', 'VACDIPOLE', 'VKICKER'],
            rf: ['CRABCAVITY', 'RFCAVITY', 'TWCAVITY'],
            solenoid: ['SOLENOID'],
            watch: ['INSTRUMENT', 'HMONITOR', 'MARKER', 'MONITOR', 'PLACEHOLDER', 'VMONITOR'],
            zeroLength: ['BEAMBEAM', 'CHANGEREF', 'DIPEDGE', 'SROTATION', 'TRANSLATION', 'XROTATION', 'YROTATION'],
        },
    };
    SIREPO.appReportTypes = [
        '<div data-ng-switch-when="bpmMonitor" data-bpm-monitor-plot="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
        '<div data-ng-switch-when="bpmHMonitor" data-bpm-monitor-plot="Horizontal" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
        '<div data-ng-switch-when="bpmVMonitor" data-bpm-monitor-plot="Vertical" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
    ].join('');
});

SIREPO.app.factory('controlsService', function(appState) {
    const self = {};
    self.computeModel = () => 'animation';
    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('ControlsController', function(appState, frameCache, panelState, persistentSimulation, requestSender, $scope) {
    const self = this;
    self.appState = appState;
    self.simScope = $scope;

    function buildEditorColumns() {
        self.editorColumns = [];
        self.watches = [];
        const schema = SIREPO.APP_SCHEMA.model;
        appState.models.externalLattice.models.beamlines[0].items.forEach(
            elId => {
                const element = elementForId(elId);
                if (schema[element.type]) {
                    const m = modelDataForElement(element);
                    if (element.type.indexOf('MONITOR') >= 0) {
                        m.plotType = element.type == 'MONITOR'
                            ? 'bpmMonitor'
                            : (element.type == 'HMONITOR'
                               ? 'bpmHMonitor'
                               : 'bpmVMonitor');
                        self.watches.push(m);
                        return;
                    }
                    self.editorColumns.push(m);
                }
            });
    }

    function dataFileChanged() {
        requestSender.getApplicationData({
            method: 'get_external_lattice',
            simulationId: appState.models.dataFile.madxSirepo
        }, data => {
            appState.models.externalLattice = data;
            $.extend(appState.models.command_twiss, findExternalCommand('twiss'));
            $.extend(appState.models.command_beam, findExternalCommand('beam'));
            appState.saveChanges(['command_beam', 'command_twiss', 'externalLattice']);
        });
    }

    function elementForId(id) {
        return findInContainer('elements', '_id', id);
    }

    function enableLatticeFields(isEnabled) {
        panelState.enableField('QUADRUPOLE', 'k1', isEnabled);
        panelState.enableField('HKICKER', 'kick', isEnabled);
        panelState.enableField('VKICKER', 'kick', isEnabled);
        panelState.enableFields('KICKER', [
            ['hkick', 'vkick'], isEnabled,
        ]);
    }

    function findExternalCommand(name) {
        return findInContainer('commands', '_type', name.replace('command_', ''));
    }

    function findInContainer(container, key, value) {
        let res;
        appState.models.externalLattice.models[container].some(m => {
            if (m[key] == value) {
                res = m;
                return true;
            }
        });
        if (! res) {
            throw new Error(`model not found for ${key}: ${value}`);
        }
        return res;
    }

    function modelDataForElement(element) {
        return {
            modelKey: 'el_' + element._id,
            title: element.name.replace(/\_/g, ' '),
            viewName: element.type,
            getData: () => element,
        };
    }

    function saveLattice(e, name) {
        //TODO(pjm): not a good element model detector
        if (name == name.toUpperCase()) {
            appState.saveQuietly('externalLattice');
        }
        if (['command_beam', 'command_twiss'].includes(name)) {
            $.extend(findExternalCommand(name), appState.models[name]);
            appState.saveQuietly('externalLattice');
        }
    }

    function updateKickers(event, values) {
        self.editorColumns.forEach(m => {
            Object.keys(values).forEach(k => {
                const modelField = appState.parseModelField(k);
                if (modelField[0] == m.modelKey) {
                    m.getData()[modelField[1]] = values[k];
                }
            });
        });
        appState.saveQuietly('externalLattice');
    }

    self.hasMadxLattice = () => {
        return appState.isLoaded() && appState.applicationState().externalLattice;
    };

    self.simHandleStatus = data => {
        if (data.error || data.percentComplete == 100) {
            enableLatticeFields(true);
        }
        else {
            enableLatticeFields(false);
        }
        if (data.elementValues) {
            frameCache.setFrameCount(1);
            $scope.$broadcast('sr-elementValues', data.elementValues);
        }
    };

    appState.whenModelsLoaded($scope, () => {
        if (self.hasMadxLattice()) {
            buildEditorColumns();
        }
        $scope.$on('dataFile.changed', dataFileChanged);
        $scope.$on('externalLattice.changed', buildEditorColumns);
        $scope.$on('modelChanged', saveLattice);
        $scope.$on('sr-elementValues', updateKickers);
        $scope.$on('animation.changed', () => enableLatticeFields(false));
        self.simState = persistentSimulation.initSimulationState(self);
    });

    return self;
});

SIREPO.app.directive('appFooter', function(controlsService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-common-footer="nav"></div>',
            '<div data-import-dialog=""></div>',
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'controls\')}"><a href data-ng-click="nav.openSection(\'controls\')"><span class="glyphicon glyphicon-dashboard"></span> Controls</a></li>',
		'</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
		//  '<div>App-specific setting item</div>',
              '</app-settings>',
              '<app-header-right-sim-list>',
              '</app-header-right-sim-list>',
            '</div>',
	].join(''),
    };
});

SIREPO.app.directive('bpmMonitorPlot', function(appState, plot2dService, plotting) {
    return {
        restrict: 'A',
        scope: {
            bpmMonitorPlot: '@',
            modelName: '@',
        },
        templateUrl: '/static/html/plot2d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            let points;

            $scope.isClientOnly = true;
            $scope.isZoomXY = true;

            $scope.init = () => {
                plot2dService.init2dPlot($scope, {
                    margin: {top: 50, right: 10, bottom: 50, left: 75},
                });
                $scope.load();
            };

            $scope.load = () => {
                points = [];
                $scope.aspectRatio = 1;
                ['x', 'y'].forEach(dim => {
                    $scope.axes[dim].domain = [-1, 1];
                    //TODO(pjm): set the domain intelligently
                    $scope.axes[dim].scale.domain([-0.0021, 0.0021]).nice();
                });
                $scope.updatePlot({
                    x_label: 'x [m]',
                    y_label: 'y [m]',
                    title: $scope.bpmMonitorPlot + ' Monitor',
                });
                plotting.addConvergencePoints($scope.select, '.plot-viewport', [], []);
            };

            $scope.refresh = () => {
                plotting.refreshConvergencePoints($scope.select, '.plot-viewport', $scope.graphLine);
                $scope.select('.plot-viewport').selectAll('.sr-scatter-point')
                    .data(points)
                    .enter().append('circle')
                    .attr('class', 'sr-scatter-point')
                    .attr('r', 8);
                $scope.select('.plot-viewport').selectAll('.sr-scatter-point')
                    .attr('cx', $scope.graphLine.x())
                    .attr('cy', $scope.graphLine.y())
                    .attr('style', 'fill: rgba(0, 0, 255, 0.4); stroke-width: 2; stroke: black');
            };

            function pushAndTrim(p) {
                const MAX_BPM_POINTS = 10;
                points.push(p);
                if (points.length > MAX_BPM_POINTS) {
                    points = points.slice(points.length - MAX_BPM_POINTS);
                }
            }

            $scope.$on('sr-elementValues', (event, values) => {
                const point = [
                    values[$scope.modelName + '.x'],
                    values[$scope.modelName + '.y'],
                ];
                pushAndTrim(point);
                plotting.addConvergencePoints($scope.select, '.plot-viewport', [], points);
                $scope.refresh();
            });
        },
        link: (scope, element) => plotting.linkPlot(scope, element),
    };
});

SIREPO.viewLogic('commandBeamView', function(appState, panelState, $scope) {

    function updateParticleFields() {
        panelState.showFields('command_beam', [
            ['mass', 'charge'], appState.models.command_beam.particle == 'other',
        ]);
    }

    $scope.whenSelected = updateParticleFields;
    $scope.watchFields = [
        ['command_beam.particle'], updateParticleFields,
    ];
});
