'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="MadxSimList" data-ng-class="fieldClass">',
          '<div data-sim-list="" data-model="model" data-field="field" data-code="madx" data-route="lattice"></div>',
        '</div>',
        '<div data-ng-switch-when="AmpTable">',
          '<div data-amp-table=""></div>',
        '</div>',
        '<div data-ng-switch-when="AmpField">',
          '<div data-amp-field=""></div>',
        '</div>',
    ].join('');
    // TODO(e-carlin): copied from madx
    SIREPO.lattice = {
        elementColor: {
            OCTUPOLE: 'yellow',
            QUADRUPOLE: 'red',
            SEXTUPOLE: 'lightgreen',
            KICKER: 'black',
            HKICKER: 'black',
            VKICKER: 'black',
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
    const mevToKg = 5.6096e26;
    const defaultFactor = 100;
    const elementaryCharge = 1.602e-19; // Coulomb
    const fieldMap = {
        QUADRUPOLE: 'K1',
        KICKER: 'KICK',
        HKICKER: 'KICK',
        VKICKER: 'KICK',
    };

    function beamInfo() {
        const beam = appState.applicationState().command_beam;
        let pInfo = SIREPO.APP_SCHEMA.constants.particleMassAndCharge[beam.particle];
        if (! pInfo) {
            pInfo = [beam.mass, beam.charge];
        }
        return {
            mass: pInfo[0] / mevToKg,
            charge: pInfo[1] * elementaryCharge,
            gamma: beam.gamma,
            beta: Math.sqrt(1 - (1 / (beam.gamma * beam.gamma))),
        };
    }

    function computeCurrent(kick, factor) {
        const b = beamInfo();
        return kick * b.gamma * b.mass * b.beta * SIREPO.APP_SCHEMA.constants.clight
            / (b.charge * factor);
    }

    function computeKick(current, factor) {
        const b = beamInfo();
        return current * b.charge * factor
            / (b.gamma * b.mass * b.beta * SIREPO.APP_SCHEMA.constants.clight);
    }

    function interpolateTable(value, tableName, fromIndex, toIndex) {
        const table = self.getAmpTables()[tableName];
        if (! table || table.length == 0) {
            return defaultFactor;
        }
        if (table.length == 1 || value < table[0][fromIndex]) {
            return table[0][toIndex];
        }
        let i = 1;
        while (i < table.length) {
            if (table[i][fromIndex] > value) {
                return (value - table[i-1][fromIndex]) / (table[i][fromIndex] - table[i-1][fromIndex])
                    * (table[i][toIndex] - table[i-1][toIndex]) + table[i-1][toIndex];
            }
            i += 1;
        }
        return table[table.length - 1][toIndex];
    }

    self.buildReverseMap = (tableName) => {
        const table = self.getAmpTables()[tableName];
        table.forEach((row) => row[2] = computeKick(row[0], row[1]));
    };

    self.computeModel = () => 'animation';

    self.currentField = (kickField) => 'current_' + kickField;

    self.currentToKick = (model, kickField) => {
        const current = model[self.currentField(kickField)];
        if (! model.ampTable) {
            return computeKick(current, defaultFactor);
        }
        return computeKick(
            current,
            interpolateTable(current, model.ampTable, 0, 1));
    };

    self.fieldForCurrent = (modelName) => fieldMap[modelName];

    self.getAmpTables = () => {
        return appState.applicationState().ampTables || {};
    };

    self.isKickField = (field) => field.search(/^(.?kick|k1)$/) >= 0;

    self.kickField = (currentField) => currentField.replace('current_', '');

    self.kickToCurrent = (model, kickField) => {
        const kick = model[kickField];
        if (! model.ampTable) {
            return computeCurrent(kick, defaultFactor);
        }
        self.buildReverseMap(model.ampTable);
        return computeCurrent(
            kick,
            interpolateTable(kick, model.ampTable, 2, 1));
    };

    self.latticeModels = () => appState.models.externalLattice.models;

    self.noOptimizationRunning = () => {
        return appState.models.simulationStatus
            && appState.models.simulationStatus.animation
            && ['pending', 'running'].indexOf(
                appState.models.simulationStatus.animation.state
            ) < 0;
    }

    self.setReadoutTableActive = (setActive) => {
        const p = 'sr-readout-table';
        const t = $('#' + p);
        const c = setActive ? ['active', 'idle'] : ['idle', 'active']
        t.addClass(`${p}-${c[0]}`);
        t.removeClass(`${p}-${c[1]}`);
    };

    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('ControlsController', function(appState, controlsService, frameCache, latticeService, panelState, persistentSimulation, requestSender, $scope, $window) {
    const self = this;
    self.appState = appState;
    self.simScope = $scope;
    self.srReadoutTableOvservers = [];

    function buildWatchColumns() {
        self.watches = [];
        const schema = SIREPO.APP_SCHEMA.model;
        controlsService.latticeModels().beamlines[0].items.forEach(
            elId => {
                const element = elementForId(elId);
                if (element.type.indexOf('MONITOR') >= 0) {
                    const m = modelDataForElement(element);
                    m.plotType = element.type == 'MONITOR'
                        ? 'bpmMonitor'
                        : (element.type == 'HMONITOR'
                           ? 'bpmHMonitor'
                           : 'bpmVMonitor');
                    m.modelKey += 'Report';
                    self.watches.push(m);
                }
            });
    }

    function computeCurrent() {
        for (let el of controlsService.latticeModels().elements) {
            for (let f in el) {
                if (controlsService.isKickField(f)
                    && ! el[controlsService.currentField(f)]) {
                    el[controlsService.currentField(f)] = controlsService.kickToCurrent(el, f);
                }
            }
        }
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
            computeCurrent();
            appState.saveChanges('externalLattice', getInitialMonitorPositions);
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
        controlsService.latticeModels()[container].some(m => {
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

    function getInitialMonitorPositions() {
        const o = new MutationObserver(function (mutations) {
            $('#sr-readout-table').length && controlsService.setReadoutTableActive(true);
        });
        self.srReadoutTableOvservers.push(o)
        o.observe(document, {
        childList: true,
        subtree: true
        })

        panelState.clear('initialMonitorPositionsReport');
        panelState.requestData('initialMonitorPositionsReport', (data) => {
            self.srReadoutTableOvservers.forEach((o) => o.disconnect());
            controlsService.setReadoutTableActive(false);
            handleElementValues(data);
        });
    }

    function handleElementValues(data) {
        if (! data.elementValues) {
            return;
        }
        frameCache.setFrameCount(1);
        updateKickers(data.elementValues);
        $scope.$broadcast('sr-elementValues', data.elementValues);
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
        if (name == name.toUpperCase()) {
            const m = appState.models[name];
            $.extend(elementForId(m._id), m);
            appState.removeModel(name);
            appState.saveChanges('externalLattice');
        }
        if (['command_beam', 'command_twiss'].includes(name)) {
            $.extend(findExternalCommand(name), appState.models[name]);
            appState.saveChanges('externalLattice');
        }
    }

    function updateKickers(values) {
        if (! values.length) {
            return;
        }
        for (let k in values[values.length - 1]) {
            let mf = k.split('.');
            if (controlsService.isKickField(mf[1])) {
                const el = latticeService.elementForId(
                    mf[0].split('_')[1],
                    controlsService.latticeModels());
                el[mf[1]] = values[values.length - 1][k];
                el[controlsService.currentField(mf[1])] = controlsService.kickToCurrent(el, mf[1]);
                if (appState.models[el._type] && appState.models[el._type]._id == el._id) {
                    appState.models[el._type] = el;
                }
            }
        }
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

    //TODO(pjm): init from template to allow listeners to register before data is received
    self.init = () => {
        if (! self.simState) {
            self.simState = persistentSimulation.initSimulationState(self);
            getInitialMonitorPositions();
        }
    };

    self.simHandleStatus = data => {
        if (data.elementValues) {
            handleElementValues(data);
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
        buildWatchColumns();
        if (! appState.models.ampTables) {
            computeCurrent();
        }
    }
    else {
        $scope.$on('dataFile.changed', dataFileChanged);
        $scope.$on('externalLattice.changed', buildWatchColumns);
    }
    windowResize();
    $scope.$on('sr-window-resize', windowResize);
    $scope.$on('modelChanged', saveLattice);
    $scope.$on('cancelChanges', function(e, name) {
        if (name == name.toUpperCase()) {
            appState.removeModel(name);
            appState.cancelChanges('externalLattice');
        }
    });
    appState.watchModelFields(
        $scope,
        ['externalLattice.models.elements'],
        getInitialMonitorPositions
    );

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
                        if (i == points.length - 1) {
                            return `fill: rgba(0, 0, 255, 0.7); stroke-width: 4; stroke: black`;
                        }
                        let opacity = (i + 1) / points.length * 0.5;
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
            ['current_hkick', 'current_vkick'], false,
        ]);
        panelState.enableField('HKICKER', 'current_kick', false);
        panelState.enableField('VKICKER', 'current_kick', false);
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

SIREPO.app.directive('latticeFooter', function(appState, controlsService, latticeService, panelState, utilities) {
    return {
        restrict: 'A',
        scope: {
            width: '@',
        },
        template: `
            <div style="display: inline-block">
              <svg ng-bind-html="readoutHTML()" ng-attr-width="{{ readoutWidth }}" ng-attr-height="{{ readoutHeight }}"></svg>
            </div>
            <div data-ng-if="monitors.length" style="display: inline-block; vertical-align: top">
              <table class="table table-hover table-condensed">
                <tr><th colspan="3">Monitors</th></tr>
                <tr data-ng-repeat="m in monitors track by m.name">
                  <td><strong>{{m.name}}</strong></td>
                  <td class="text-right">{{m.x}}</td>
                  <td class="text-right">{{m.y}}</td>
                </tr>
              </table>
            </div>
            `,
        controller: function($scope) {
            const labels = {
                current_k1: 'current',
                current_hkick: 'hcurrent',
                current_vkick: 'vcurrent',
                current_kick: 'current',
            };
            const readoutGroups = utilities.unique(
                Object.values(SIREPO.APP_SCHEMA.constants.readoutElements || {}).map(function (e) {
                    return e.group;
                })
            );
            const margin = 3;
            const numReadoutCols = readoutGroups.length || 1;
            const readoutCellHeight = 22;
            const readoutCellPadding = 3;
            const readoutCellWidth = 350;
            let readoutTable = null;
            let selectedItem = null;
            $scope.readoutWidth = (readoutCellWidth + margin) * 2;
            $scope.monitors = [];

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
                    margin,
                    margin,
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

            function detectOverlap(positions, pos) {
                for (let p of positions) {
                    if (rectanglesOverlap(pos, p)) {
                        return p;
                    }
                }
            }

            function elementClicked(name) {
                const models = controlsService.latticeModels();
                models.elements.some((el) => {
                    if (el.name == name) {
                        latticeService.editElement(el.type, el, models);
                        return true;
                    }
                });
            }

            function formatMonitorValue(value) {
                if (value) {
                    return parseFloat(value).toFixed(6);
                }
                return '';
            }

            function getReadoutItem(id) {
                let r = readoutItems();
                for (let g in r) {
                    for (let item of r[g]) {
                        if (item.element._id == id) {
                            return item;
                        }
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

            function readoutGroup(element) {
                return (SIREPO.APP_SCHEMA.constants.readoutElements[element.type] || {}).group;
            }

            function readoutItems() {
                let elements = {};
                const models = controlsService.latticeModels();
                models.beamlines[0].items.forEach(elId => {
                    let el = latticeService.elementForId(elId, models);
                    let rg = readoutGroup(el);
                    if (! rg) {
                        return;
                    }
                    if (! elements[rg]) {
                        elements[rg] = [];
                    }
                    // elements are in beamline order
                    elements[rg].push({
                        element: el,
                    });
                });
                return elements;
            }

            function rectanglesOverlap(pos1, pos2) {
                if (pos1.left > pos2.right || pos2.left > pos1.right) {
                    return false;
                }
                if (pos1.top > pos2.bottom || pos2.top > pos1.bottom) {
                    return false;
                }
                return true;
            }

            function labelElements() {
                $('.sr-lattice-label').remove();
                const parentRect = $('#sr-lattice')[0].getBoundingClientRect();
                const positions = [];
                $("[class^='sr-beamline']").each( (_ , element) => {
                    positions.push(element.getBoundingClientRect());
                });
                $('#sr-lattice').find('title').each((v, el) => {
                    const values = $(el).text().split(': ');
                    if (! SIREPO.APP_SCHEMA.model[values[1]]) {
                        return;
                    }
                    const isMonitor = values[1].indexOf('MONITOR') >= 0;
                    const rect = el.parentElement.getBoundingClientRect();
                    let pos = [
                        rect.left - parentRect.left + (rect.right - rect.left),
                        rect.top - parentRect.top,
                    ];
                    if (! isMonitor) {
                        pos[0] -= 25;
                        pos[1] = rect.bottom - parentRect.top + 5;
                    }

                    let div = $('<div/>', {
                        class: 'sr-lattice-label badge'
                    })
                        .html(values[0])
                        .css({
                            left: pos[0],
                            top: pos[1],
                            position: 'absolute',
                            //'z-index': 1000,
                            cursor: 'pointer',
                            'user-select': 'none',
                        })
                        .on('dblclick', () => elementClicked(values[0]))
                        .appendTo($('.sr-lattice-holder'));
                    const maxChecks = 8;
                    let checkCount = 1;
                    let p = detectOverlap(positions, div[0].getBoundingClientRect());
                    let yOffset = 0;
                    const c = 3;
                    while (p) {
                        if (isMonitor) {
                            const d = div[0].getBoundingClientRect().bottom - p.top - 1;
                            if (d > c) {
                                yOffset -= d;
                            }
                            yOffset -= c;
                        }
                        else {
                            const d = p.bottom - div[0].getBoundingClientRect().top + 1;
                            if (d > c) {
                                yOffset += d;
                            }
                            yOffset += c;
                        }
                        div.css({
                            top: pos[1] + yOffset,
                        });
                        p = detectOverlap(positions, div[0].getBoundingClientRect());
                        if (checkCount++ > maxChecks) {
                            break;
                        }
                    }
                    positions.push(div[0].getBoundingClientRect());
                });
            }

            function updateMonitors(event, rows) {
                $scope.monitors = [];
                if (! rows.length) {
                    return;
                }
                const models = controlsService.latticeModels();
                models.beamlines[0].items.forEach(elId => {
                    const el = latticeService.elementForId(elId, models);
                    if (el.type.indexOf('MONITOR') < 0) {
                        return;
                    }
                    const el_id = 'el_' + el._id;
                    $scope.monitors.push({
                        name: el.name,
                        x: formatMonitorValue(rows[0][el_id + '.x']),
                        y: formatMonitorValue(rows[0][el_id + '.y']),
                    });
                });
            }

            function updateReadoutElement(element, color, opacity, borderWidth) {
                if (! readoutTable || ! element) {
                    return;
                }
                let r = readoutItems();
                let g = readoutGroup(element);
                let txt = `${element.name}: `;
                for (let f of readoutFields(element)) {
                    txt += `${labels[f]} = ${utilities.roundToPlaces(parseFloat(element[f]), 6)};&nbsp;`;
                }
                let idx = 0;
                while (r[g][idx].element._id != element._id) {
                    idx += 1;
                    if (idx >= r[g].length) {
                        throw new Error('element not found: ', element);
                    }
                }
                readoutTable.setCell(
                    idx,
                    Object.keys(r).indexOf(g),
                    txt,
                    color,
                    opacity,
                    borderWidth
                );
            }

            function updateReadoutElements() {
                let r = readoutItems();
                // each readout group is a column
                for (let g in r) {
                    for (let item of r[g]) {
                        updateReadoutElement(item.element);
                    }
                }
            }

            function windowResize() {
                let r = readoutItems();
                let nRows = Object.values(r).map(x => x.length);
                let maxReadoutRows = 1 + Math.max(0, ...nRows);
                $scope.readoutHeight = 2 * margin +
                    (maxReadoutRows + 1) * readoutCellPadding + readoutCellHeight * maxReadoutRows;
            }

            $scope.destroy = function() {
                $('.sr-lattice-label').off();
            };

            $scope.readoutHTML = function() {
                if (! readoutTable) {
                    return  '';
                }
                return readoutTable.toTemplate();
            };

            $scope.$on('modelChanged', function(e, name) {
                if (SIREPO.APP_SCHEMA.constants.readoutElements[name]) {
                    updateReadoutElements();
                }
            });

            $scope.$on('sr-clearElementValues', () => {
                controlsService.setReadoutTableActive(true);
            });
            $scope.$on('sr-elementValues', updateReadoutElements);
            $scope.$on('sr-latticeUpdateComplete', () => {
                if (! readoutTable) {
                    return;
                }
                readoutTable.removeClasses('sr-readout-table-active');
                readoutTable.addClasses('sr-readout-table-idle');
            });

            $scope.$on('sr-beamlineItemSelected', function(e, idx) {
                const models = controlsService.latticeModels();
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
            $scope.$on('sr-elementValues', updateMonitors);
            $scope.$on('sr-renderBeamline', () => panelState.waitForUI(labelElements));

            buildReadoutTable();
            windowResize();
        },
    };
});

SIREPO.app.directive('ampTable', function(appState, controlsService) {
    return {
        restrict: 'A',
        template: `
            <div class="col-sm-6">
            <div class="lead">
              <span>{{ fieldName }}</span>
              = <span data-text-with-math="desc"></span></div>
            <div class="text-warning">{{ errorMessage }}</div>
            <div data-ng-show="showFileInput()">
              <input id="sr-amp-table-input" type="file" data-file-model="ampTableFile" accept=".csv"/>
            </div>
            <select data-ng-show="! showFileInput()" class="form-control" data-ng-model="model[field]" data-ng-options="item as item for item in fileNames"></select>
            <div style="margin-top: 1em; max-height: 30vh; overflow-y: auto;" data-ng-if="model[field]">
              <table class="table table-hover table-condensed">
                <tr>
                  <th class="text-center">Current</th>
                  <th class="text-center">Factor</th>
                  <th class="text-center">{{ fieldHeading }}</th>
                </tr>
                <tr data-ng-repeat="row in getTable() track by $index">
                  <td class="text-right" data-ng-repeat="cell in row track by $index">{{ cell }}</td>
                </tr>
              </table>
            </div>
            </div>
            `,
        controller: function($scope) {
            $scope.fieldName = controlsService.fieldForCurrent($scope.modelName);
            $scope.fieldHeading = 'Computed ' + $scope.fieldName[0].toUpperCase()
                + $scope.fieldName.toLowerCase().substring(1);
            $scope.desc = '$\\frac {current [\\text A] \\cdot charge [\\text C]} {gamma \\cdot mass [\\text{kg}] \\cdot beta \\cdot c [\\text{m/s}]} \\cdot factor$';
            const addNewFile = '<Add New File>';
            buildFileNames();

            function buildFileNames() {
                let names = Object.keys(controlsService.getAmpTables()).sort((a, b) => a.localeCompare(b));
                names.unshift('');
                names.push(addNewFile);
                $scope.fileNames = names;
            }

            function parseText(text) {
                let rows = [];
                text.split(/\s*\n/).forEach(line => {
                    let row = line.split(/\s*,\s*/);
                    if (row.length >= 2) {
                        rows.push(row);
                    }
                });
                if (rows.length && rows[0][0].search(/\w/) >= 0) {
                    // ignore header
                    rows.shift();
                }
                if (! appState.models.ampTables) {
                    appState.models.ampTables = {};
                }
                const name = $scope.ampTableFile.name;
                const table = rows.map(
                    row => row.map(v => parseFloat(v))
                ).sort((a, b) => a[0] - b[0]);
                if (! validateTable(table)) {
                    $scope.$applyAsync();
                    return;
                }
                appState.models.ampTables[name] = table;
                appState.saveQuietly('ampTables');
                $scope.model[$scope.field] = name;
                controlsService.buildReverseMap(name);
                // buildReverseMap works on saved model values, need to update working models
                appState.models.ampTables[name] = appState.applicationState().ampTables[name];
                buildFileNames();
                $scope.$applyAsync();
            }

            function validateTable(table) {
                $scope.errorMessage = '';
                if (! table.length) {
                    $scope.errorMessage = 'No rows found';
                    return false;
                }
                for (let i = 0; i < table.length; i++) {
                    const row = table[i];
                    if (row.length < 2) {
                        $scope.errorMessage = `Row #${i + 1}: Invalid row: ${row}`;
                        return false;
                    }
                    else if (isNaN(row[0]) || isNaN(row[1])) {
                        $scope.errorMessage = `Row #${i + 1}: Invalid number: ${row}`;
                        return false;
                    }
                }
                return true;
            }

            function selectFile() {
                const v = $scope.model[$scope.field];
                if (v == addNewFile) {
                    $scope.showFile = true;
                }
            }

            $scope.getTable = () => controlsService.getAmpTables()[$scope.model[$scope.field]];

            $scope.showFileInput = () => {
                if (! $scope.model) {
                    return false;
                }
                if (! $scope.model[$scope.field]) {
                    $scope.model[$scope.field] = '';
                }
                if ($scope.showFile) {
                    return true;
                }
                if ($scope.fileNames.length <= 2) {
                    return true;
                }
                return false;
            };

            $scope.$watch('ampTableFile', () => {
                if ($scope.ampTableFile) {
                    $scope.ampTableFile.text().then(parseText);
                }
            });
            $scope.$on('cancelChanges', () => {
                $scope.ampTableFile = null;
                $('#sr-amp-table-input').val(null);
                $scope.showFile = false;
                $scope.errorMessage = '';
            });
            appState.watchModelFields($scope, [$scope.modelName + '.' + $scope.field], selectFile);
        },
    };
});

SIREPO.app.directive('ampField', function(appState, controlsService) {
    return {
        restrict: 'A',
        template: `
            <div class="col-sm-3">
              <input data-ng-model="model[field]" class="form-control" style="text-align: right" data-lpignore="true" required />
            </div>
            <div class="col-sm-4"><div class="form-control-static" style="text-overflow: ellipsis; overflow: hidden; margin-left: -15px; padding-left: 0; white-space: nowrap"><strong>{{ fieldForCurrent() }}</strong> {{ computedKick(); }}</div></div>`,
        controller: function($scope) {

            $scope.computedKick = () => {
                if (! $scope.model) {
                    return;
                }
                if (! $scope.model[$scope.field]) {
                    $scope.model[$scope.field] = controlsService.kickToCurrent(
                        $scope.model,
                        controlsService.kickField($scope.field));
                }
                const res = controlsService.currentToKick(
                    $scope.model,
                    controlsService.kickField($scope.field));
                if (! isNaN(res)) {
                    return res.toFixed(6);
                }
            };

            $scope.fieldForCurrent = () => {
                return controlsService.fieldForCurrent($scope.modelName);
            };
        },
    };
});
