'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.SINGLE_FRAME_ANIMATION = ['beamPositionAnimation', 'instrumentAnimationTwiss'];
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="MadxSimList" data-ng-class="fieldClass">
          <div data-sim-list="" data-model="model" data-field="field" data-code="madx" data-route="lattice"></div>
        </div>
        <div data-ng-switch-when="AmpTable">
          <div data-amp-table=""></div>
        </div>
        <div data-ng-switch-when="AmpField">
          <div data-amp-field=""></div>
        </div>
        <div data-ng-switch-when="ProcessVariables" class="col-sm-12">
          <div element-pv-fields=""></div>
        </div>
    `;
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
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="bpmMonitor" data-zoom="XY" data-bpm-monitor-plot="" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}"></div>
        <div data-ng-switch-when="bpmHMonitor" data-zoom="X" data-bpm-monitor-plot="Horizontal" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}"></div>
        <div data-ng-switch-when="bpmVMonitor" data-zoom="Y" data-bpm-monitor-plot="Vertical" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}"></div>
        <div data-ng-switch-when="parameterWithExternalLattice" data-parameter-with-lattice="" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}" data-path-to-models="externalLattice"></div>
    `;
});

SIREPO.app.factory('controlsService', function(appState, latticeService, requestSender) {
    const self = {};
    const mevToKg = 5.6096e26;
    const elementaryCharge = 1.602e-19; // Coulomb
    const fieldMap = {
        QUADRUPOLE: 'K1',
        KICKER: 'KICK',
        HKICKER: 'KICK',
        VKICKER: 'KICK',
    };

    self.beamlineElements = models => {
        if (! models) {
            models = self.latticeModels();
        }
        return models.beamlines[0].items.map(
            elId => latticeService.elementForId(elId, models));
    };

    self.canChangeCurrents = () => {
        if (self.isDeviceServerReadOnly()) {
            return false;
        }
        return appState.models.simulationStatus
            && appState.models.simulationStatus.instrumentAnimation
            && ['pending', 'running'].indexOf(
                appState.models.simulationStatus.instrumentAnimation.state
            ) < 0;
    };

    self.computeModel = analysisModel => {
	if (analysisModel.includes('instrument') || analysisModel === 'beamPositionAnimation') {
	    return 'instrumentAnimation';
	}
	return 'animation';
    };

    self.currentField = (kickField) => 'current_' + kickField;

    self.currentToKick = (model, kickField) => {
        requestSender.sendStatelessCompute(
            appState,
            data => {
                model[kickField] = data.kick;
            },
            {
                method: 'current_to_kick',
                args: {
                    command_beam: appState.models.command_beam,
                    //TODO(pjm): not sure why null values get sent but undefined values do not
                    amp_table: self.getAmpTables()[model.ampTable] || null,
                    current: model[self.currentField(kickField)],
                    default_factor: appState.models.controlSettings.defaultFactor,
                },
            });
    };

    self.elementForId = (elId) => latticeService.elementForId(elId, self.latticeModels());

    self.fieldForCurrent = (modelName) => fieldMap[modelName];

    self.getAmpTables = () => appState.applicationState().ampTables || {};

    self.hasMadxLattice = () => appState.applicationState().externalLattice;

    self.isDeviceServer = () => appState.models.controlSettings.operationMode === 'DeviceServer';

    self.isDeviceServerReadOnly = () => {
        return self.isDeviceServer()
            && appState.models.controlSettings.readOnly === '1';
    };

    self.isDeviceServerWithUpdates = () => {
        return self.isDeviceServer()
            && appState.models.controlSettings.readOnly === '0';
    };

    self.isMonitor = (el) => el.type.indexOf('MONITOR') >= 0;

    self.isQuadOrKicker = (elType) => elType === 'QUADRUPOLE' || elType.indexOf('KICKER') >= 0;

    self.kickField = (currentField) => currentField.replace('current_', '');

    self.kickToCurrent = (model, currentField) => {
        if (! model[self.kickField(currentField)]) {
            return;
        }
        //TODO(pjm): combine implementation with currentToKick
        requestSender.sendStatelessCompute(
            appState,
            data => {
                model[currentField] = data.current;
            },
            {
                method: 'kick_to_current',
                args: {
                    command_beam: appState.models.command_beam,
                    amp_table: self.getAmpTables()[model.ampTable] || null,
                    kick: model[self.kickField(currentField)],
                    default_factor: appState.models.controlSettings.defaultFactor,
                },
            });
    };

    self.latticeModels = () => appState.models.externalLattice.models;

    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('ControlsController', function(appState, controlsService, errorService, frameCache, latticeService, panelState, persistentSimulation, requestSender, $scope, $window) {
    const self = this;
    self.appState = appState;
    self.controlsService = controlsService;
    self.panelState = panelState;
    self.simScope = $scope;
    let beamlineElementChanged = false;

    self.simAnalysisModel = 'instrumentAnimation';
    function buildWatchColumns() {
        self.watches = [];
        for (let el of controlsService.beamlineElements()) {
            if (controlsService.isMonitor(el)) {
                const m = modelDataForElement(el);
                m.plotType = el.type === 'MONITOR'
                    ? 'bpmMonitor'
                    : (el.type === 'HMONITOR'
                       ? 'bpmHMonitor'
                       : 'bpmVMonitor');
                m.modelKey += 'Report';
                self.watches.push(m);
            }
        }
    }

    function dataFileChanged() {
        requestSender.sendStatefulCompute(
            appState,
            data => {
                if (data.error) {
                    errorService.alertText(data.error);
                    return;
                }
                const k = [
                    'externalLattice',
                    'optimizerSettings',
                    'controlSettings',
                    'command_beam',
                    'bunch',
                ];
                for (let f of k) {
                    appState.models[f] = data[f];
                }
                appState.saveChanges(k);
            },
            {
                method: 'get_external_lattice',
                args: {
                    simulationId: appState.models.dataFile.madxSirepo
                }
            }
        );
    }

    function findExternalModel(name) {
        if (name.startsWith('command_')) {
            return findInContainer('commands', '_type', name.replace('command_', ''));
        }
        return controlsService.latticeModels()[name];
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

    function handleElementValues(data) {
        if (! data.elementValues || data.elementValues.length == 0) {
            return;
        }
        updateElements(data.elementValues);
        $scope.$broadcast('sr-elementValues', data.elementValues, data);
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
            $.extend(controlsService.elementForId(m._id), m);
            appState.removeModel(name);
            appState.saveQuietly('externalLattice');
        }
        if (['command_beam', 'bunch'].includes(name)) {
            $.extend(findExternalModel(name), appState.models[name]);
            appState.saveQuietly('externalLattice');
        }
    }

    function updateElements(values) {
        if (! values.length) {
            return;
        }
        for (let k in values[values.length - 1]) {
            if (k === 'cost') {
                continue;
            }
            let mf = k.split('.');
            const el = controlsService.elementForId(mf[0].split('_')[1]);
            el[mf[1]] = parseFloat(values[values.length - 1][k]);
        }
        appState.saveQuietly('externalLattice');
    }

    function windowResize() {
        self.colClearFix = $window.matchMedia('(min-width: 1600px)').matches
            ? 6 : 4;
    }

    self.cancelCallback = () => controlsService.runningMessage = '';

    //TODO(pjm): init from template to allow listeners to register before data is received
    self.init = () => {
        if (! self.simState) {
            self.simState = persistentSimulation.initSimulationState(self);
            self.simState.runningMessage = () => controlsService.runningMessage;
        }
    };

    self.simHandleStatus = data => {
        if (self.simState.isProcessing()) {
            if (controlsService.isDeviceServerReadOnly()) {
                controlsService.runningMessage = 'Monitoring Beamline';
            }
            else {
                controlsService.runningMessage = 'Running Optimization';
            }
            $scope.isRunningOptimizer = true;
        }
        controlsService.optimizationCost = 0;
        if (data.elementValues && data.elementValues.length) {
            handleElementValues(data);
            loadHeatmapReports(data);
            controlsService.optimizationCost = parseFloat(data.elementValues[data.elementValues.length - 1].cost);
        }
        if (! self.simState.isProcessing()) {
            if ($scope.isRunningOptimizer) {
                $scope.isRunningOptimizer = false;
                controlsService.runningMessage = '';
                appState.saveChanges('externalLattice');
            }
        }
        frameCache.setFrameCount(data.frameCount);
    };

    function loadHeatmapReports(data) {
        self.instrumentAnimations = [];
        const all = {};
        for (let m in appState.models) {
            if (m.includes('instrumentAnimation') && appState.models[m].id) {
                all[appState.models[m].id] = m;
            }
        }
        for (const el of controlsService.beamlineElements()) {
            if (el.type !== 'INSTRUMENT') {
                continue;
            }
            const m = all[el._id];
            if (m) {
                appState.models[m].valueList = {
                    x: data.ptcTrackColumns,
                    y1: data.ptcTrackColumns,
                };
                appState.models[m].particlePlotSize = appState.models.controlSettings.particlePlotSize;
                self.instrumentAnimations.push({
                    modelKey: m,
                    getData: genGetDataFunction(m),
                });
                if (data.frameCount) {
                    frameCache.setFrameCount(data.frameCount, m);
                    frameCache.setCurrentFrame(m, data.frameCount);
                    if (SIREPO.SINGLE_FRAME_ANIMATION.indexOf(m) < 0) {
                        SIREPO.SINGLE_FRAME_ANIMATION.push(m);
                    }
                }
            }
        }
        appState.models.instrumentAnimationAll.valueList = {
            x: data.ptcTrackColumns,
            y1: data.ptcTrackColumns,
        };
        appState.models.instrumentAnimationAll.particlePlotSize = appState.models.controlSettings.particlePlotSize;
        return;
    }

    function genGetDataFunction(m) {
        return () => appState.models[m];
    }

    function initInstruments() {
        const k  = [];
        for (const e of appState.models.externalLattice.models.elements) {
            if (e.type !== 'INSTRUMENT') {
                continue;
            }
            const n = 'instrumentAnimation' + e._id;
            if (! appState.models[n]) {
                k.push(n);
                appState.models[n] = appState.setModelDefaults({
                    id: e._id,
                    viewName: 'instrumentAnimation',
                }, 'instrumentAnimation');
            }
        }
        return k;
    }

    self.hasInstrumentAnimations = () => {
        if (self.instrumentAnimations != null && self.instrumentAnimations.length) {
            // only show particle plots if twiss is available
            return frameCache.getFrameCount('instrumentAnimationTwiss');
        }
        return false;
    };

    self.startSimulation = () => {
        controlsService.runningMessage = 'Starting Optimization';
        $scope.isRunningOptimizer = true;
        $scope.$broadcast('sr-clearElementValues');
        const k = initInstruments();
        appState.models.controlSettings.simMode = 'optimizer';
        k.push('optimizerSettings', 'externalLattice', 'controlSettings');
        appState.saveChanges(k, self.simState.runSimulation);
    };

    if (controlsService.hasMadxLattice()) {
        buildWatchColumns();
    }
    else {
        $scope.$on('dataFile.changed', dataFileChanged);
        $scope.$on('externalLattice.changed', buildWatchColumns);
    }
    windowResize();
    $scope.$on('sr-window-resize', windowResize);
    $scope.$on('modelChanged', (e, name) => {
        saveLattice(e, name);
        if (controlsService.isQuadOrKicker(name)) {
            appState.models.controlSettings.simMode = 'singleUpdates';
            appState.saveQuietly('controlSettings');
            beamlineElementChanged = true;
        }
    });
    $scope.$on('cancelChanges', (e, name) => {
        if (name == name.toUpperCase()) {
            appState.removeModel(name);
            appState.cancelChanges('externalLattice');
        }
    });
    $scope.$on('controlSettings.changed', () => {
        for (const m in appState.models) {
            if (m.includes('instrumentAnimation') && m != 'instrumentAnimationAll') {
                appState.models[m].particlePlotSize = appState.models.controlSettings.particlePlotSize;
                appState.saveQuietly(m);
            }
        }
    });
    $scope.$on('initialMonitorPositionsReport.summaryData', (e, data) => {
        beamlineElementChanged = false;
        handleElementValues(data, true);
    });
    $scope.$on('instrumentAnimationAll.changed', () => {
        if (! self.instrumentAnimations) {
            return;
        }
        const m = [];
        self.instrumentAnimations.forEach((e, i) => {
            for (const key in appState.models[e.modelKey]) {
                if (key != 'id') {
                    appState.models[e.modelKey][key] = appState.models.instrumentAnimationAll[key];
                }
            }
            m.push(e.modelKey);
        });
        appState.saveChanges(m);
    });
    return self;
});


SIREPO.app.directive('appFooter', function(controlsService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
            <div data-import-dialog=""></div>
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('controls')}"><a href data-ng-click="nav.openSection('controls')"><span class="glyphicon glyphicon-dashboard"></span> Controls</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
                <div><a href data-ng-click="openSettings()"><span class="glyphicon glyphicon-th-list"></span> Control Settings</a></div>
              </app-settings>
              <app-header-right-sim-list>
                <ul class="nav navbar-nav sr-navbar-right">
                  <li><a href data-ng-click="nav.showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>
                </ul>
              </app-header-right-sim-list>
            </div>
        `,
        controller: function($scope) {
            $scope.openSettings = () => {
                panelState.showModalEditor('beamline');
            };
        },
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
            let defaultDomain = [
                -appState.models.controlSettings.bpmPlotSize/2,
                 appState.models.controlSettings.bpmPlotSize/2
                ];
            let points;
            let colName = $scope.modelName.substring(0, $scope.modelName.indexOf('Report'));
            $scope.isClientOnly = true;
            $scope[`isZoom${$scope.zoom}`] = true;

            function clearPoints() {
                points = [];
                defaultDomain = [
                    -appState.models.controlSettings.bpmPlotSize/2,
                    appState.models.controlSettings.bpmPlotSize/2
               ];
                plotting.addConvergencePoints($scope.select, '.plot-viewport', [], points);
                $scope.select('.plot-viewport').selectAll('.sr-scatter-point').remove();
                ['x', 'y'].forEach(dim => {
                    $scope.axes[dim].domain = [-1, 1];
                    $scope.axes[dim].scale.domain(appState.clone(defaultDomain));
                });
            }

            function pushAndTrim(p) {
                const MAX_BPM_POINTS = SIREPO.APP_SCHEMA.constants.maxBPMPoints;
                if (points.length && appState.deepEquals(p, points[points.length - 1])) {
                    return;
                }
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
                            return 'fill: rgba(0, 0, 255, 0.7); stroke-width: 4; stroke: orange';
                        }
                        let opacity = (i + 1) / points.length * 0.5;
                        return `fill: rgba(0, 0, 255, ${opacity}); stroke-width: 0`;
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
                plotting.addConvergencePoints($scope.select, '.plot-viewport', [], points);
                $scope.resize();
            });

            $scope.$on('sr-clearElementValues', () => {
                clearPoints();
                $scope.refresh();
            });

            $scope.$on('controlSettings.changed', () => {
                clearPoints();
                $scope.resize();
            });
        },
        link: (scope, element) => plotting.linkPlot(scope, element),
    };
});

SIREPO.viewLogic('beamlineView', function(appState, controlsService, panelState, $scope) {

    function updateURLField() {
        panelState.showFields('controlSettings', [
            [
                'deviceServerURL', 'readOnly', 'deviceServerUser', 'deviceServerProcName',
                'deviceServerProcId', 'deviceServerMachine',
            ], controlsService.isDeviceServer(),
            ['inputLogFile', 'defaultFactor'], ! controlsService.isDeviceServer(),
        ]);
    }

    $scope.whenSelected = updateURLField;
    $scope.watchFields = [
        ['controlSettings.operationMode'], updateURLField,
    ];
});

SIREPO.viewLogic('commandBeamView', function(appState, panelState, $scope) {

    function updateParticleFields() {
        panelState.showFields('command_beam', [
            ['mass', 'charge'], appState.models.command_beam.particle === 'other',
        ]);
    }

    $scope.whenSelected = updateParticleFields;
    $scope.watchFields = [
        ['command_beam.particle'], updateParticleFields,
    ];
});

['kickerView', 'hkickerView', 'vkickerView'].forEach(view => {
    SIREPO.viewLogic(
        view,
        function(appState, controlsService, panelState, $scope) {
            $scope.whenSelected = () => {
                const r = controlsService.canChangeCurrents();
                panelState.enableFields('KICKER', [
                    ['current_hkick', 'current_vkick'], r,
                ]);
                ['HKICKER', 'VKICKER'].forEach(m => {
                    panelState.enableField(m, 'current_kick', r);
                });
            };
        }
    );
});

['monitorView', 'hmonitorView', 'vmonitorView'].forEach(view => {
    SIREPO.viewLogic(
        view,
        function(panelState, $scope) {
            $scope.whenSelected = () => {
                panelState.enableFields('MONITOR', [
                    ['x', 'y'], false,
                ]);
                panelState.enableFields('HMONITOR', 'x', false);
                panelState.enableFields('VMONITOR', 'y', false);
            };
        }
    );
});

SIREPO.viewLogic('quadrupoleView', function(appState, controlsService, panelState, $scope) {
    $scope.whenSelected = () => {
        panelState.enableField(
            'QUADRUPOLE',
            'current_k1',
            controlsService.canChangeCurrents()
        );
    };
});

SIREPO.app.directive('optimizationPicker', function(appState, controlsService, stringsService) {
    return {
        restrict: 'A',
        scope: {
            controller: '='
        },
        template: `
            <div>
              <div class="container-fluid">
                <div class="row" data-ng-show="::showTabs">
                  <div class="col-sm-12">
                    <ul class="nav nav-tabs">
                      <li role="presentation" data-ng-class="{active: activeTab == 'targets'}"><a href data-ng-click="activeTab = 'targets'">Targets</a></li>
                      <li role="presentation" data-ng-class="{active: activeTab == 'inputs'}"><a href data-ng-click="activeTab = 'inputs'">Inputs</a></li>
                    </ul>
                  </div>
                </div>
                <br />
              <div data-ng-if="activeTab == 'targets'" class="row">
                <div class="clearfix" data-optimizer-table=""></div>
              </div>
                <div data-ng-if="activeTab == 'inputs'" class="row">
                  <div class="container-fluid">
                    <form name="form">
                      <table ng-repeat="(inputType, inputs) in appState.models.optimizerSettings.inputs" style="float: left; margin: 1em;">
                        <thead>
                          <th>{{stringsService.ucfirst(inputType)}}</th>
                        </thead>
                        <tbody>
                          <tr ng-repeat="(id, enabled) in inputs" >
                            <td class="form-group form-group-sm" >
                              <label class="form-check-label">
                                <input type="checkbox" ng-model="inputs[id]" />
                                  {{controlsService.elementForId(id).name}}
                              </label>
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </form>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
            $scope.appState = appState;
            $scope.controlsService = controlsService;
            $scope.activeTab = 'targets';
            $scope.showTabs = true;
            $scope.stringsService = stringsService;
        },
    };
});

SIREPO.app.directive('optimizerTable', function(appState) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <form name="form" class="form-horizontal">
              <div class="form-group form-group-sm" data-model-field="'method'" data-form="form" data-model-name="'optimizerSettings'"></div>
              <div data-ng-if="showTolerance()" class="form-group form-group-sm" data-model-field="'tolerance'" data-form="form" data-model-name="'optimizerSettings'"></div>
              <table data-ng-show="appState.models.optimizerSettings.method == 'nmead'" style="width: 100%; table-layout: fixed; margin-bottom: 10px" class="table table-hover">
                <colgroup>
                  <col style="width: 10em">
                  <col style="width: 20%>
                  <col style="width: 20%">
                  <col style="width: 20%">
                </colgroup>
                <thead>
                  <tr>
                    <th>Monitor Name</th>
                    <th data-ng-repeat="label in labels track by $index" class="text-center">{{ label }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr data-ng-repeat="target in appState.models.optimizerSettings.targets track by $index">
                    <td class="form-group form-group-sm"><p class="form-control-static">{{ target.name }}</p></td>
                    <td class="form-group form-group-sm" data-ng-repeat="field in fields track by $index">
                      <div data-ng-show="target.hasOwnProperty(field)">
                        <div class="row" data-field-editor="fields[$index]" data-field-size="12" data-model-name="'optimizerTarget'" data-model="target"></div>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </form>
        `,
        controller: function($scope) {
            $scope.appState = appState;
            $scope.fields = ['x', 'y', 'weight'];
            $scope.labels = $scope.fields.map(f => SIREPO.APP_SCHEMA.model.optimizerTarget[f][0]);
            $scope.showTolerance = () => appState.models.optimizerSettings.method == 'nmead';
        },
    };
});


SIREPO.app.directive('logSelector', function(appState, controlsService, requestSender, utilities, $rootScope) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div class="col-sm-12" data-ng-if="showSelector()">
              <label>Selected log file time</label>
              <input type="range" data-ng-model="appState.models.controlSettings.selectedTimeIndex" min="0" max="{{ logViewer.maxIndex }}">
              <div>{{ logViewer.displayValue }}</div>
            </div>
        `,
        controller: function($scope) {
            $scope.appState = appState;
            $scope.logViewer = {
                maxIndex: 0,
                displayValue: '',
                isInitialized: false,
            };

            const updateFromLog = utilities.debounce(() => {
                if (! appState.isLoaded()) {
                    return;
                }
                $scope.logViewer.displayValue = new Date($scope.logViewer.timeValues[
                    appState.models.controlSettings.selectedTimeIndex] * 1000).toGMTString();
                requestSender.sendStatefulCompute(
                    appState,
                    data => {
                        if (! appState.isLoaded()) {
                            return;
                        }
                        $rootScope.$broadcast('initialMonitorPositionsReport.summaryData', {
                            elementValues: [data.values],
                        });
                        // can't save controlSettings directly or plots would clear
                        appState.models.controlSettings.simMode = 'singleUpdates';
                        appState.saveQuietly('controlSettings');
                        appState.models.initialMonitorPositionsReport.changed = ! appState.models.initialMonitorPositionsReport.changed;
                        appState.saveChanges('initialMonitorPositionsReport');
                    },
                    {
                        method: 'get_log_file_values_at_index',
                        index: appState.models.controlSettings.selectedTimeIndex,
                        models: appState.models.externalLattice.models,
                        lib_file: appState.models.controlSettings.inputLogFile,
                    });
            }, SIREPO.debounce_timeout);

            function init() {
                $scope.logViewer.isInitialized = true;
                appState.watchModelFields($scope, ['controlSettings.selectedTimeIndex'], updateFromLog);

                requestSender.sendStatefulCompute(
                    appState,
                    data => {
                        $scope.logViewer.timeValues = data.timeValues;
                        $scope.logViewer.maxIndex = data.timeValues.length - 1;
                        updateFromLog();
                    },
                    {
                        method: 'get_log_file_time_list',
                        lib_file: appState.models.controlSettings.inputLogFile,
                    });
            }

            function isEnabled() {
                if (controlsService.isDeviceServer() || ! appState.applicationState().controlSettings.inputLogFile) {
                    return false;
                }
                return true;
            }

            $scope.showSelector = () => {
                if (! isEnabled()) {
                    return false;
                }
                return $scope.logViewer.maxIndex > 0;
            };

            $scope.$on('controlSettings.changed', () => {
                if (isEnabled() && ! $scope.logViewer.isInitialized) {
                    init();
                }
            });

            if (isEnabled()) {
                init();
            }
        },
    };
});

SIREPO.app.directive('latticeFooter', function(appState, controlsService, frameCache, latticeService, panelState, $timeout) {
    return {
        restrict: 'A',
        scope: {
            width: '@',
            modelName: '@',
        },
        template: `
            <div data-log-selector=""></div>
            <div class="row">
              <div class="col-sm-8 col-xl-7 text-right" ng-if="modelName == 'beamlines'">
                <div data-ng-repeat="table in tables track by table.reading" style="display: inline-block; vertical-align: top; margin-right: 1.5em">
                  <div data-ng-if="readings[table.reading].length">
                    <table class="table table-hover table-condensed" data-ng-attr-style="min-width: {{ table.columns.length * 10 }}em">
                      <tr><th colspan="3">{{ table.label }}</th></tr>
                      <tr data-ng-repeat="row in readings[table.reading] track by row.name" data-ng-class="{warning: row.id == selectedId}">
                        <td class="text-left" data-ng-click="elementClicked(row.name)" data-ng-dblclick="elementClicked(row.name, true)" style="padding: 0; user-select: none; cursor: pointer"><strong>{{row.name}}</strong></td>
                        <td style="padding: 0" data-ng-class="{'sr-updated-cell': row.changed[col]}" data-ng-repeat="col in table.columns track by $index" class="text-right">{{row[col]}}</td>
                      </tr>
                    </table>
                  </div>
                </div>
                <div class="text-center" data-ng-if="controlsService.runningMessage" style="margin-left: 3em">
                  <span class="glyphicon glyphicon-repeat sr-running-icon"></span>
                   {{ controlsService.runningMessage }}<span data-ng-if="controlsService.optimizationCost"></span><span data-ng-if="controlsService.optimizationCost != 0 && ! controlsService.isDeviceServerReadOnly()">, cost: {{ controlsService.optimizationCost | number : 6 }}</span>
                </div>
              </div>

              <div style="position: relative; margin: 0 -15px; padding: 0" class="col-sm-4 col-xl-5" data-ng-if="hasTwissReport()">
                <h4 style="position: absolute; top: -2%; left: 10%;">Twiss Parameters</h4>
                <button style="position: absolute; top: -1%; right: 5%;" ng-click="showTwissEditor()" class="btn bg-info">
                  <span class="glyphicon glyphicon-pencil text-primary"></span>
                </button>
                <div data-report-content="parameter" data-model-key="instrumentAnimationTwiss""></div>
              </div>

              <div style="position: relative; margin: 0 -15px; padding: 0" class="col-sm-4 col-xl-5" data-ng-if="hasBeamPositionAnimation()">
                <h4 style="position: absolute; top: -2%; left: 10%;">Beam Position at Monitors</h4>
                <div data-report-content="parameter" data-model-key="beamPositionAnimation"></div>
              </div>

              <div style="position: relative; margin: 0 -15px; padding: 0" class="col-sm-4 col-xl-5" data-ng-if="hasInitialMonitorPositionsReport()">
                <h4 style="position: absolute; top: -2%; left: 10%;">Beam Position at Monitors</h4>
                <div data-report-content="parameter" data-model-key="initialMonitorPositionsReport"></div>
              </div>
            </div>
            `,
        controller: function($scope) {
            const prevValue = {};
            $scope.controlsService = controlsService;
            $scope.tables = [
                {
                    label: 'Kicker Current [A]',
                    reading: 'kicker',
                    columns: ['current_hkick', 'current_vkick'],
                    types: ['KICKER', 'HKICKER', 'VKICKER'],
                    colMapping: {
                        HKICKER: {
                            current_hkick: 'current_kick',
                        },
                        VKICKER: {
                            current_vkick: 'current_kick',
                        },
                    },
                },
                {
                    label: 'Quadrupole Current [A]',
                    reading: 'quadrupole',
                    columns: ['current_k1'],
                    types: ['QUADRUPOLE'],
                },
                {
                    label: 'Monitor [m]',
                    reading: 'monitor',
                    columns: ['x', 'y'],
                    types: ['MONITOR', 'HMONITOR', 'VMONITOR'],
                },
            ];
            $scope.selectedId = null;
            $scope.readings = {};

            function detectOverlap(positions, pos) {
                for (let p of positions) {
                    if (rectanglesOverlap(pos, p)) {
                        return p;
                    }
                }
            }

            function elementForName(name) {
                let res;
                controlsService.latticeModels().elements.some(el => {
                    if (el.name == name) {
                        res = el;
                        return true;
                    }
                });
                return res;
            }

            $scope.elementClicked = (name, showEditor) => {
                const el = elementForName(name);
                if (el) {
                    setSelectedId(el._id);
                    if (showEditor) {
                        latticeService.editElement(el.type, el, controlsService.latticeModels());
                    }
                }
            };

            function setSelectedId(elId) {
                if ($scope.selectedId != elId) {
                    if ($scope.selectedId) {
                        const node = $('.sr-lattice-label-' + $scope.selectedId);
                        node.removeClass('sr-selected-badge');
                    }
                    $scope.selectedId = elId;
                    const node = $('.sr-lattice-label-' + $scope.selectedId);
                    node.addClass('sr-selected-badge');
                }
            }

            function formatReading(value) {
                return angular.isDefined(value) ? parseFloat(value).toFixed(6) : '';
            }

            function labelElements() {
                $('.sr-lattice-label').remove();
                const parentRect = $('#sr-lattice')[0].getBoundingClientRect();
                const positions = [];
                const labeled = [];
                $("[class^='sr-beamline']").each( (_ , element) => {
                    positions.push(element.getBoundingClientRect());
                });
                $('#sr-lattice').find('title').each((v, node) => {
                    const values = $(node).text().split(': ');
                    if (! SIREPO.APP_SCHEMA.model[values[1]] && values[1] != 'INSTRUMENT') {
                        return;
                    }
                    const isMonitorOrInstrument = (values[1].indexOf('MONITOR') >= 0) || (values[1].indexOf('INSTRUMENT') >= 0);
                    const rect = node.parentElement.getBoundingClientRect();
                    let pos = [
                        rect.left - parentRect.left + (rect.right - rect.left) - 25,
                        isMonitorOrInstrument
                            ? rect.top - parentRect.top - 5
                            : rect.bottom - parentRect.top + 5,

                    ];
                    const el = elementForName(values[0]);
                    let div = $('<div/>', {
                        class: 'sr-lattice-label badge' + (el ? (' sr-lattice-label-' + el._id) : ''),
                    })
                        .html(values[0])
                        .css({
                            left: pos[0],
                            top: pos[1],
                            position: 'absolute',
                            cursor: 'pointer',
                            'user-select': 'none',
                        })
                        .on('click', () => {
                            $scope.elementClicked(values[0]);
                            $scope.$applyAsync();
                        })
                        .on('dblclick', () => {
                            $scope.elementClicked(values[0], true);
                            $scope.$applyAsync();
                        })
                        .appendTo($('.sr-lattice-holder'));
                    const maxChecks = 8;
                    let checkCount = 1;
                    let p = detectOverlap(positions, div[0].getBoundingClientRect());
                    let yOffset = 0;
                    const c = 3;
                    while (p) {
                        if (isMonitorOrInstrument) {
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

            function loadTwissReport(data) {
                if (! data || ! data.twissColumns || controlsService.isDeviceServer()) {
                    frameCache.setFrameCount(0, 'instrumentAnimationTwiss');
                    return;
                }
                data.twissColumns.unshift('None');
                appState.models.instrumentAnimationTwiss.valueList = {
                    x: data.twissColumns,
                    y1: data.twissColumns,
                    y2: data.twissColumns,
                    y3: data.twissColumns,
                };
                if (data.frameCount) {
                    frameCache.setFrameCount(data.frameCount, 'instrumentAnimationTwiss');
                    frameCache.setCurrentFrame('instrumentAnimationTwiss', data.frameCount);
                }
            }

            function updateReadings(event, values, data) {
                loadTwissReport(data);
                $scope.readings = {
                    monitor: [],
                    kicker: [],
                    quadrupole: [],
                };
                for (let el of controlsService.beamlineElements(appState.applicationState().externalLattice.models)) {
                    for (let table of $scope.tables) {
                        for (let type of table.types) {
                            if (el.type == type) {
                                const row = {
                                    id: el._id,
                                    name: el.name,
                                    changed: {},
                                };
                                for (let col of table.columns) {
                                    let v;
                                    if (table.colMapping && table.colMapping[type]) {
                                        if (table.colMapping[type][col]) {
                                            v = el[table.colMapping[type][col]];
                                        }
                                    }
                                    else if (col in el) {
                                        v = el[col];
                                    }
                                    row[col] = formatReading(v);
                                    const k = col + row.id;
                                    row.changed[col] = prevValue[k] != row[col];
                                    prevValue[k] = row[col];
                                }
                                $scope.readings[table.reading].push(row);
                            }
                        }
                    }
                }
                $timeout(() => {
                    for (let r in $scope.readings) {
                        for (let row of $scope.readings[r]) {
                            row.changed = {};
                        }
                    }
                }, 1500);
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

            $scope.destroy = () => $('.sr-lattice-label').off();

            $scope.hasBeamPositionAnimation = () => {
                const s = appState.applicationState().controlSettings;
                return s.operationMode === 'DeviceServer'
                    && s.simMode == 'optimizer'
                    && frameCache.getFrameCount('beamPositionAnimation');
            };

            $scope.hasInitialMonitorPositionsReport = () => {
                return appState.applicationState().controlSettings.simMode == 'singleUpdates';
            };

            $scope.hasTwissReport = () => {
                if (controlsService.isDeviceServer()) {
                    frameCache.setFrameCount(0, 'instrumentAnimationTwiss');
                    return false;
                }
                return appState.applicationState().controlSettings.simMode == 'optimizer'
                    && frameCache.getFrameCount('instrumentAnimationTwiss');
            };

            $scope.showTwissEditor = () => panelState.showModalEditor('instrumentAnimationTwiss');

            $scope.$on('sr-beamlineItemSelected', (e, idx) => {
                setSelectedId(controlsService.latticeModels().beamlines[0].items[idx]);
            });
            $scope.$on('sr-elementValues', updateReadings);
            $scope.$on('sr-renderBeamline', () => {
                panelState.waitForUI(labelElements);
            });
            $scope.$on('modelChanged', (e, name) => {
                if (controlsService.isQuadOrKicker(name)) {
                    updateReadings();
                }
            });
        },
    };
});

SIREPO.app.directive('ampTable', function(appState, controlsService, latticeService) {
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
                </tr>
                <tr data-ng-repeat="row in getTable() track by $index">
                  <td class="text-right">{{ row[0] }}</td>
                  <td class="text-right">{{ row[1] }}</td>
                </tr>
              </table>
            </div>
            </div>
            `,
        controller: function($scope) {
            $scope.fieldName = controlsService.fieldForCurrent($scope.modelName);
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
                return rows.map(
                    row => row.map(v => parseFloat(v))
                ).sort((a, b) => a[0] - b[0]);
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
                if (v == addNewFile || ! v) {
                    $scope.showFile = true;
                }
                else {
                    for (const f in $scope.model) {
                        if (f.indexOf('current_') >= 0) {
                            controlsService.kickToCurrent(
                                $scope.model,
                                f);
                        }
                    }
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
                    $scope.ampTableFile.text().then(text => {
                        const table = parseText(text);
                        if (validateTable(table)) {
                            const name = $scope.ampTableFile.name;
                            appState.models.ampTables[name] = table;
                            appState.saveQuietly('ampTables');
                            $scope.model[$scope.field] = name;
                            buildFileNames();
                        }
                        $scope.$applyAsync();
                    });
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
              <input data-ng-model="model[field]" data-string-to-number="" class="form-control" style="text-align: right" data-lpignore="true" required />
            </div>
            <div class="col-sm-4"><div class="form-control-static" style="text-overflow: ellipsis; overflow: hidden; margin-left: -15px; padding-left: 0; white-space: nowrap"><strong>{{ currentField }}</strong> {{ model[kickField] | number:6 }}</div></div>`,
        controller: function($scope) {
            $scope.currentField = controlsService.fieldForCurrent($scope.modelName);
            $scope.kickField = controlsService.kickField($scope.field);
            $scope.$watch('model.' + $scope.field, () => {
                if ($scope.model && angular.isDefined($scope.model[$scope.field])) {
                    controlsService.currentToKick(
                        $scope.model,
                        controlsService.kickField($scope.field));
                }
            });
        },
    };
});

SIREPO.app.directive('elementPvFields', function(appState, controlsService, latticeService) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <form name="form" style="margin-top:-2em"><div class="col-sm-12">
              <div class="form-group form-group-sm" data-ng-if="controlsService.hasMadxLattice()" style="max-height: 75vh; overflow-y: auto;">
                <table class="table table-condensed">
                  <tr>
                    <th class="text-center" data-ng-repeat="h in headers track by $index">{{ h }}</th>
                    <th></th>
                  </tr>
                  <tr data-ng-class="{warning: pv.isWritable == '1'}" data-ng-repeat="pv in appState.models.controlSettings.processVariables track by $index">
                    <td data-ng-repeat="f in fields track by $index">
                      <div class="form-control-static">{{ ::getValue(pv, f) }}</div>
                    </td>
                    <td>
                      <div>
                        <input data-ng-model="pv.pvName" class="form-control" data-lpignore="true" />
                      </div>
                    </td>
                  </tr>
                </table>
              </div>
            </div></form>
        `,
        controller: function($scope) {
            $scope.modelName = 'beamline';
            $scope.appState = appState;
            $scope.controlsService = controlsService;
            $scope.pvFields = ['controlsService.processVariables'];
            $scope.headers = ['Type', 'Element Name', 'Description', 'Process Variable Name'];
            $scope.fields = ['type', 'name', 'description'];

            $scope.getValue = (pv, field) => {
                const el = controlsService.elementForId(pv.elId);
                if (field === 'description') {
                    let res = '';
                    if (pv.pvDimension != 'none') {
                        res += pv.pvDimension + ' ';
                    }
                    if (controlsService.isMonitor(el)) {
                        res += 'position ';
                    }
                    else if (controlsService.isQuadOrKicker(el.type)) {
                        res += 'current ';
                    }
                    res += pv.isWritable === '1' ? 'setting' : 'reading';
                    return res;
                }
                return el[field];
            };
        },
    };
});

SIREPO.app.directive('deviceServerMonitor', function(appState, controlsService) {
    return {
        restrict: 'A',
        scope: {
            simState: '=deviceServerMonitor',
        },
        template: `
            <button data-ng-show="! simState.isProcessing()" class="btn btn-default" data-ng-click="startMonitor()">Start Monitor</button>
            <button data-ng-show="simState.isProcessing()" class="btn btn-default" data-ng-click="stopMonitor()">Stop Monitor</button>
            <div style="margin-top: 1em" data-ng-show="simState.isStateError()">
              <div class="col-sm-12">{{ simState.stateAsText() }}</div>
            </div>
        `,
        controller: function($scope) {
            $scope.startMonitor = () => {
                appState.models.controlSettings.simMode = 'optimizer';
                appState.saveChanges('controlSettings', $scope.simState.runSimulation);
            };

            $scope.stopMonitor = () => {
                $scope.simState.cancelSimulation();
                controlsService.runningMessage = '';
            };
        },
    };
});
