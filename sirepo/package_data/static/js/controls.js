'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="MadxSimList" data-ng-class="fieldClass">',
          '<div data-sim-list="" data-model="model" data-field="field" data-code="madx" data-route="lattice"></div>',
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
        '<div data-ng-switch-when="bpmMonitor" data-zoom="XY" data-bpm-monitor-plot="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
        '<div data-ng-switch-when="bpmHMonitor" data-zoom="X" data-bpm-monitor-plot="Horizontal" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
        '<div data-ng-switch-when="bpmVMonitor" data-zoom="Y" data-bpm-monitor-plot="Vertical" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
    ].join('');
});

SIREPO.app.factory('controlsService', function(appState) {
    const self = {};
    self.computeModel = () => 'animation';
    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('ControlsController', function(appState, frameCache, panelState, persistentSimulation, requestSender, $scope, $window) {
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
                // skip editable elements
                if (((SIREPO.APP_SCHEMA.view[element.type] || {}).advanced || []).length) {
                    return;
                }
                if (schema[element.type]) {
                    const m = modelDataForElement(element);
                    if (element.type.indexOf('MONITOR') >= 0) {
                        m.plotType = element.type == 'MONITOR'
                            ? 'bpmMonitor'
                            : (element.type == 'HMONITOR'
                               ? 'bpmHMonitor'
                               : 'bpmVMonitor');
                        m.modelKey += 'Report';
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
            appState.models.externalLattice = data.externalLattice;
            appState.models.optimizerSettings = data.optimizerSettings;
            $.extend(appState.models.command_twiss, findExternalCommand('twiss'));
            $.extend(appState.models.command_beam, findExternalCommand('beam'));
            appState.saveChanges(['command_beam', 'command_twiss', 'externalLattice', 'optimizerSettings']);
        });
    }

    function elementForId(id) {
        return findInContainer('elements', '_id', id);
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

    function updateKickers(event, rows) {
        var values = rows[rows.length -1];
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

    function windowResize() {
        self.colClearFix = $window.matchMedia('(min-width: 1600px)').matches
            ? 6 : 4;
    }

    self.cancelCallback = () => {
        $scope.$broadcast('sr-latticeUpdateComplete');
    };

    self.hasMadxLattice = () => appState.applicationState().externalLattice;

    self.simHandleStatus = data => {
        if (data.elementValues) {
            frameCache.setFrameCount(1);
            $scope.$broadcast('sr-elementValues', data.elementValues);
        }
        if (! self.simState.isProcessing()) {
            $scope.$broadcast('sr-latticeUpdateComplete');
        }
    };

    self.startSimulation = () => {
        $scope.$broadcast('sr-clearElementValues');
        appState.saveChanges('optimizerSettings', self.simState.runSimulation);
    };

    if (self.hasMadxLattice()) {
        buildEditorColumns();
    }
    windowResize();
    $scope.$on('sr-window-resize', windowResize);
    $scope.$on('dataFile.changed', dataFileChanged);
    $scope.$on('externalLattice.changed', buildEditorColumns);
    $scope.$on('modelChanged', saveLattice);
    $scope.$on('sr-elementValues', updateKickers);
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
                '<ul class="nav navbar-nav sr-navbar-right">',
                  '<li><a href data-ng-click="nav.showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>',
                '</ul>',
              '</app-header-right-sim-list>',
            '</div>',
	].join(''),
    };
});

SIREPO.app.directive('bpmMonitorPlot', function(appState, panelState, plot2dService, plotting) {
    return {
        restrict: 'A',
        scope: {
            bpmMonitorPlot: '@',
            modelName: '@',
            zoom: '@'
        },
        templateUrl: '/static/html/plot2d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            let points;
            let colName = $scope.modelName.substring(0, $scope.modelName.indexOf('Report'));
            $scope.isClientOnly = true;
            $scope[`isZoom${$scope.zoom}`] = true;

            function clearPoints() {
                points = [];
                plotting.addConvergencePoints($scope.select, '.plot-viewport', [], points);
                $scope.select('.plot-viewport').selectAll('.sr-scatter-point').remove();
                ['x', 'y'].forEach(dim => {
                    $scope.axes[dim].domain = [-1, 1];
                    $scope.axes[dim].scale.domain([-0.0021, 0.0021]).nice();
                });
            }

            function fitPoints() {
                if (points.length <= 1) {
                    return;
                }
                [0, 1].forEach(i => {
                    let dim = [1e6, -1e6];
                    points.forEach(p => {
                        if (p[i] < dim[0]) {
                            dim[0] = p[i];
                        }
                        if (p[i] > dim[1]) {
                            dim[1] = p[i];
                        }
                    });
                    let pad = (dim[1] - dim[0]) / 20;
                    if (pad == 0) {
                        pad = 0.1;
                    }
                    dim[0] -= pad;
                    dim[1] += pad;
                    $scope.axes[i == 0 ? 'x' : 'y'].scale.domain(dim).nice();
                });
            }

            function pushAndTrim(p) {
                const MAX_BPM_POINTS = SIREPO.APP_SCHEMA.constants.maxBPMPoints;
                points.push(p);
                if (points.length > MAX_BPM_POINTS) {
                    points = points.slice(points.length - MAX_BPM_POINTS);
                }
            }

            $scope.init = () => {
                plot2dService.init2dPlot($scope, {
                    margin: {top: 50, right: 10, bottom: 50, left: 75},
                });
                $scope.load();
            };

            $scope.load = () => {
                clearPoints();
                $scope.aspectRatio = 1;
                $scope.updatePlot({
                    x_label: 'x [m]',
                    y_label: 'y [m]',
                    title: $scope.bpmMonitorPlot + ' Monitor',
                });
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
                    .attr('style', (d, i) => {
                        let opacity = i == points.length - 1
                            ? 1
                            : (i + 1) / points.length * 0.8;
                        return `fill: rgba(0, 0, 255, ${opacity}); stroke-width: 1; stroke: black`;
                    });
            };

            $scope.$on('sr-elementValues', (event, rows) => {
                if (rows.length > 1) {
                    clearPoints();
                }
                rows.forEach(values => {
                    const point = [
                        parseFloat(values[colName + '.x'] || 0),
                        parseFloat(values[colName + '.y'] || 0),
                    ];
                    pushAndTrim(point);
                });
                fitPoints();
                plotting.addConvergencePoints($scope.select, '.plot-viewport', [], points);
                $scope.resize();
            });

            $scope.$on('sr-clearElementValues', () => {
                clearPoints();
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

const disableKickerLogic = function(panelState, $scope) {
    $scope.whenSelected = () => {
        panelState.enableFields('KICKER', [
            ['hkick', 'vkick'], false,
        ]);
        panelState.enableField('HKICKER', 'kick', false);
        panelState.enableField('VKICKER', 'kick', false);
    };
};

['kickerView', 'hkickerView', 'vkickerView'].forEach(view => {
    SIREPO.viewLogic(view, disableKickerLogic);
});

SIREPO.viewLogic('quadrupoleView', function(appState, panelState, $scope) {
    $scope.whenSelected = () => {
        const isEnabled = appState.models.simulationStatus
              && appState.models.simulationStatus.animation
              && ['pending', 'running'].indexOf(appState.models.simulationStatus.animation.state) < 0;
        panelState.enableField('QUADRUPOLE', 'k1', isEnabled);
    };
});

SIREPO.app.directive('optimizerTable', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<form name="form">',

              '<div class="form-group form-group-sm" data-model-field="\'method\'" data-form="form" data-model-name="\'optimizerSettings\'"></div>',


              '<table data-ng-show="appState.models.optimizerSettings.method == \'nmead\'" style="width: 100%; table-layout: fixed; margin-bottom: 10px" class="table table-hover">',
                '<colgroup>',
                  '<col style="width: 10em">',
                  '<col style="width: 20%>',
                  '<col style="width: 20%">',
                  '<col style="width: 20%">',
                '</colgroup>',
                '<thead>',
                  '<tr>',
                    '<th>Monitor Name</th>',
                    '<th data-ng-repeat="label in labels track by $index" class="text-center">{{ label }}</th>',
                  '</tr>',
                '</thead>',
                '<tbody>',
                  '<tr data-ng-repeat="target in appState.models.optimizerSettings.targets track by $index">',
                    '<td class="form-group form-group-sm"><p class="form-control-static">{{ target.name }}</p></td>',
                    '<td class="form-group form-group-sm" data-ng-repeat="field in fields track by $index">',
                      '<div data-ng-show="target.hasOwnProperty(field)">',
                        '<div class="row" data-field-editor="fields[$index]" data-field-size="12" data-model-name="\'optimizerTarget\'" data-model="target"></div>',
                      '</div>',
                    '</td>',
                  '</tr>',
                '</tbody>',
              '</table>',
            '</form>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
            $scope.fields = ['x', 'y', 'weight'];
            $scope.labels = $scope.fields.map(f => SIREPO.APP_SCHEMA.model.optimizerTarget[f][0]);
            $scope.showField = (item, field) => field in item;
        },
    };
});

SIREPO.app.directive('latticeFooter', function(appState, latticeService, utilities) {
    return {
        restrict: 'A',
        scope: {
            width: '@',
        },
        template: `
            <div>
              <svg ng-bind-html="readoutHTML()" ng-attr-width="{{ width }}" ng-attr-height="{{ readoutHeight }}"></svg>
            </div>`,
        controller: function($scope) {
            let readoutGroups = utilities.unique(
                Object.values(SIREPO.APP_SCHEMA.constants.readoutElements || {}).map(function (e) {
                    return e.group;
                })
            );
            let numReadoutCols = readoutGroups.length || 1;
            let readoutCellPadding = 3;
            let readoutCellHeight = 22;
            let readoutCellWidth = 300;
            let readoutTable = null;
            let selectedItem = null;
            $scope.margin = 3;

            function buildReadoutTable() {
                if (readoutTable) {
                    return;
                }
                let r = readoutItems();
                if ($.isEmptyObject(r)) {
                    return;
                }
                let numRows = Object.values(r).map(function (x) {
                    return Object.keys(x).length;
                });
                readoutTable = new SIREPO.DOM.SVGTable(
                    'sr-readout-table',
                    $scope.margin,
                    $scope.margin,
                    readoutCellWidth,
                    readoutCellHeight,
                    readoutCellPadding,
                    Math.max(0, ...numRows),
                    numReadoutCols,
                    null,
                    true,
                    readoutGroups
                );
                readoutTable.addClasses('sr-readout-table sr-readout-table-idle');
                updateReadoutElements();
            }

            function getReadoutItem(id) {
                let r = readoutItems();
                for (let g in r) {
                    if (r[g][id]) {
                        return r[g][id];
                    }
                }
                return null;
            }

            function hasReadout(item) {
                return readoutFields(item.element).length > 0;
            }

            function readoutFields(element) {
                return (SIREPO.APP_SCHEMA.constants.readoutElements[element.type] || {}).fields || [];
            }

            function parseElementModelField(modelField) {
                let mf = modelField.split('.');
                let el_id = parseInt(mf[0].split('_')[1]);
                const models = appState.models.externalLattice.models;
                let e = latticeService.elementForId(el_id, models);
                if (! e) {
                    return null;
                }
                return {
                    element: e,
                    field: mf[1],
                    model: mf[0],
                };
            }

            function readoutGroup(element) {
                return (SIREPO.APP_SCHEMA.constants.readoutElements[element.type] || {}).group;
            }

            function readoutItems() {
                let elements = {};
                const models = appState.models.externalLattice.models;
                models.beamlines[0].items.forEach(elId => {
                    let el = latticeService.elementForId(elId, models);
                    let rg = readoutGroup(el);
                    if (! rg) {
                        return;
                    }
                    if (! elements[rg]) {
                        elements[rg] = {};
                    }
                    elements[rg][elId] = {
                        element: el,
                    };
                });
                return elements;
            }

            function updateReadoutElement(element, color, opacity, borderWidth) {
                if (! readoutTable || ! element) {
                    return;
                }
                let r = readoutItems();
                let g = readoutGroup(element);
                let txt = `${element.name}: `;
                for (let f of readoutFields(element)) {
                    txt += `${f} = ${utilities.roundToPlaces(parseFloat(element[f]), 6)};&nbsp;`;
                }
                readoutTable.setCell(
                    Object.keys(r[g]).indexOf(`${element._id}`),
                    Object.keys(r).indexOf(g),
                    txt,
                    color,
                    opacity,
                    borderWidth
                );
            }

            function updateReadout(e, d) {
                let r = readoutItems();
                if ($.isEmptyObject(r)) {
                    return;
                }
                let dd = d[d.length - 1];
                // data is in the format {'el_<id>.<field>': <value>}
                for (let k in dd) {
                    let p = parseElementModelField(k);
                    let g = readoutGroup(p.element);
                    if (! p.element || ! g) {
                        continue;
                    }
                    let m = r[g][p.element._id];
                    if (! m) {
                        continue;
                    }
                    m.element[p.field] = dd[k];
                }
                updateReadoutElements();
            }

            function updateReadoutElements() {
                let r = readoutItems();
                // each readout group is a column
                for (let g in r) {
                    for (let id in r[g]) {
                        updateReadoutElement(r[g][id].element);
                    }
                }
            }

            function windowResize() {
                let r = readoutItems();
                let nRows = Object.values(r).map(function (x) {
                    return Object.keys(x).length;
                });
                let maxReadoutRows = 1 + Math.max(0, ...nRows);
                $scope.readoutHeight = 2 * $scope.margin +
                    (maxReadoutRows + 1) * readoutCellPadding + readoutCellHeight * maxReadoutRows;
            }

            $scope.readoutHTML = function() {
                if (! readoutTable) {
                    return  '';
                }
                return readoutTable.toTemplate();
            };

            $scope.$on('modelChanged', function(e, name) {
                updateReadoutElement((parseElementModelField(name) || {}).element);
            });

            $scope.$on('sr-clearElementValues', () => {
                readoutTable.removeClasses('sr-readout-table-idle');
                readoutTable.addClasses('sr-readout-table-active');
            });
            $scope.$on('sr-elementValues', updateReadout);
            $scope.$on('sr-latticeUpdateComplete', () => {
                if (! readoutTable) {
                    return;
                }
                readoutTable.removeClasses('sr-readout-table-active');
                readoutTable.addClasses('sr-readout-table-idle');
            });

            $scope.$on('sr-beamlineItemSelected', function(e, idx) {
                const models = appState.models.externalLattice.models;
                let id = models.beamlines[0].items[idx];
                let item = getReadoutItem(id);
                if (! item) {
                    return;
                }
                let c = 'none';
                let o = 0.0;
                let b = 1.0;
                if (selectedItem) {
                    updateReadoutElement(selectedItem.element, c, o, b);
                }
                if (selectedItem && selectedItem.element._id == id) {
                    selectedItem = null;
                }
                else {
                    selectedItem = item;
                    c = 'yellow';
                    o = 0.25;
                    b = 2.0;
                }
                updateReadoutElement(item.element, c, o, b);
            });

            $scope.$on('sr-window-resize', windowResize);

            buildReadoutTable();
            windowResize();
        },
    };
});
