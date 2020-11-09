'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;


SIREPO.app.config(function() {
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="MadxSimList" data-ng-class="fieldClass">',
          '<div data-sim-list="" data-model="model" data-field="field" data-code="madx"></div>',
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
    var self = {};

    self.computeModel = function(analysisModel) {
        return 'animation';
    };
    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('ControlsController', function(appState, controlsService, frameCache, latticeService, panelState, persistentSimulation, requestSender, $scope) {
    var self = this;
    self.simScope = $scope;
    self.appState = appState;
    self.latticeService = latticeService;

    self.advancedNames = [];
    self.basicNames = [];
    self.beamPositionReports = [];

    function dataFileChanged() {
        requestSender.getApplicationData({
            method: 'get_external_lattice',
            simulationId: appState.models.dataFile.madxSirepo
        }, function(data) {
            appState.models.externalLattice = data;
            appState.saveChanges(['externalLattice']);
        });
    }

    function elementForId(id) {
        return elementForValue('_id', id);
    }

    function elementForName(name) {
        return elementForValue('name', name);
    }

    function elementForValue(key, value) {
        var model = null;
        appState.models.externalLattice.models.elements.some(function(m) {
            if (m[key] == value) {
                model = m;
                return true;
            }
        });
        if (! model) {
            throw new Error(`model not found for ${key}: ${value}`);
        }
        return model;
    }

    function findExternalCommand(name) {
        var res;
        name = name.replace('command_', '');
        appState.models.externalLattice.models.commands.some(function(cmd) {
            if (cmd._type == name) {
                res = cmd;
                return true;
            }
        });
        return res;
    }

    function getBeamlineElements(id, elements) {
        var found = appState.models.externalLattice.models.elements.some(function(el) {
            if (el._id == id) {
                elements.push(el);
                return true;
            }
        });
        if (! found) {
            appState.models.externalLattice.models.beamlines.some(function(bl) {
                if (bl.id == id) {
                    bl.items.forEach(function(id2) {
                        getBeamlineElements(id2, elements);
                    });
                    return true;
                }
            });
        }
        return elements;
    }

    function modelForElement(element) {
        return {
            modelKey: element.name,
            title: element.name.replace(/\_/g, ' '),
            viewName: element.type,
            getData: function() {
                return element;
            },
        };
    }

    function updateFromMonitorValues(monitorValues) {
        monitorValues.forEach((value) => {
            // TODO(e-carlin): need a better connection between element name,
            // monitor values and the bpmMonitorPlots
            $scope.$broadcast(
                'sr-pointData-' + elementForName(value.name).name,
                [value.x, value.y]
            );
        });
    }

    self.hasMadxLattice = function() {
        return appState.isLoaded() && appState.applicationState().dataFile.madxSirepo;
    };

    self.simHandleStatus = function(data) {
        if (data.monitorValues) {
            frameCache.setFrameCount(1);
            panelState.waitForUI(function() {
                updateFromMonitorValues(data.monitorValues);
            });
        }
    };

    appState.whenModelsLoaded($scope, function() {
        function buildEditorColumns() {
            self.editorColumns = [];
            self.watches = [];
            var schema = SIREPO.APP_SCHEMA.model;
            var beamlineId = appState.models.externalLattice.models.simulation.visualizationBeamlineId;
            getBeamlineElements(beamlineId, []).forEach(function(element) {
                if (schema[element.type]) {
                    const m = modelForElement(element);
                    if (element.type.indexOf('MONITOR') >= 0) {
                        m.plotType = element.type == 'MONITOR' ? 'bpmMonitor'
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
        $scope.$on('dataFile.changed', dataFileChanged);
        $scope.$on('externalLattice.changed', function() {
            buildEditorColumns();
        });
        self.editorColumns = [];
        self.watches = [];
        buildEditorColumns();
        $scope.$on('modelChanged', function(e, name) {
            //TODO(pjm): not a good element model detector
            if (name == name.toUpperCase()) {
                appState.saveQuietly('externalLattice');
            }
            if (['command_beam', 'command_twiss'].includes(name)) {
                $.extend(findExternalCommand(name), appState.models[name]);
                appState.saveQuietly('externalLattice');
            }
        });
    });

    self.simState = persistentSimulation.initSimulationState(self);

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
            var points;

            $scope.isClientOnly = true;
            $scope.isZoomXY = true;

            $scope.init = function() {
                plot2dService.init2dPlot($scope, {
                    margin: {top: 50, right: 10, bottom: 50, left: 75},
                });
                $scope.load();
            };

            $scope.load = function() {
                points = [];
                $scope.aspectRatio = 1;
                ['x', 'y'].forEach(function(dim) {
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

            $scope.refresh = function() {
                plotting.refreshConvergencePoints($scope.select, '.plot-viewport', $scope.graphLine);
                $scope.select('.plot-viewport').selectAll('.webcon-scatter-point')
                    .data(points)
                    .enter().append('circle')
                    .attr('class', 'webcon-scatter-point')
                    .attr('r', 8);
                $scope.select('.plot-viewport').selectAll('.webcon-scatter-point')
                    .attr('cx', $scope.graphLine.x())
                    .attr('cy', $scope.graphLine.y())
                    .attr('style', function(d) {
                        return 'fill: rgba(0, 0, 255, 0.4); stroke-width: 2; stroke: black';
                    });
            };

            function pushAndTrim(p) {
                var MAX_BPM_POINTS = 10;
                points.push(p);
                if (points.length > MAX_BPM_POINTS) {
                    points = points.slice(points.length - MAX_BPM_POINTS);
                }
            }

            $scope.$on('sr-pointData-' + $scope.modelName, function(event, point) {
                if (! point) {
                    return;
                }
                if (point[0] === undefined) {
                    return;
                }
                pushAndTrim(point);
                plotting.addConvergencePoints($scope.select, '.plot-viewport', [], points);
                $scope.refresh();
            });
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
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
