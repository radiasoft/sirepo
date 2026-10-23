'use strict';

// Field values to apply to a statAnimation/stat2Animation model when the
// user picks a "Plot Presets" entry (schema constants.statPlotPresets) -- a
// shortcut for common combinations of x/y1-y5 fields, rather than picking
// each Value to Plot by hand.
const statPlotPresets = () => SIREPO.APP_SCHEMA.constants.statPlotPresets;

const STAT_PLOT_PRESET_FIELDS = [
    'x', 'y1', 'y2', 'y3', 'y4', 'y5',
    'y1Position', 'y2Position', 'y3Position', 'y4Position', 'y5Position',
];

// The preset key whose field values all match the model's current field
// values, or '' if the model doesn't currently match any preset (e.g. the
// user picked plot fields by hand instead of selecting a preset).
function presetKeyForModel(m) {
    const matches = (preset) => Object.keys(preset).every((f) => m[f] === preset[f]);
    const found = Object.entries(statPlotPresets()).find(([, preset]) => matches(preset));
    return found ? found[0] : '';
}

function applyStatPlotPreset(appState, modelName) {
    const m = appState.models[modelName];
    const preset = statPlotPresets()[m.plotPreset];
    if (! preset) {
        return;
    }
    Object.assign(m, preset);
    appState.saveChanges(modelName);
}

// element types only Relative (Lattice) positioning offers: a Volume places
// every element on one straight axis, which a bend turns the beam away from
const BEND_TYPES = ['RBEND', 'SBEND'];

// element types a Lattice tracks through by integrating their field (a
// field-map SOLENOID is one too), which have an integration algorithm
const FIELD_INTEGRATED_TYPES = ['CAVITY', 'COIL', 'CORRECTOR', 'SEXTUPOLE'];

// element types with an RF field, which autophasing phases
const RF_ELEMENT_TYPES = ['CAVITY'];

SIREPO.app.config(function() {
    SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
    SIREPO.SINGLE_FRAME_ANIMATION = ['statAnimation', 'stat2Animation'];
    SIREPO.appDefaultSimulationValues.simulation.elementPosition = 'absolute';
    SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL = true;
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="bpmTable" data-bpm-table-panel="" class="sr-plot sr-screenshot"></div>
    `;
    SIREPO.lattice = {
        elementColor: {},
        elementPic: {
            bend: BEND_TYPES,
            drift: ['DRIFT'],
            magnet: ['QUADRUPOLE', 'SEXTUPOLE', 'CORRECTOR'],
            rf: RF_ELEMENT_TYPES,
            solenoid: ['SOLENOID', 'COIL'],
            watch: ['SCREEN', 'BPM'],
        },
        latticeImport: '.h5',
    };
});

SIREPO.app.directive('bpmTablePanel', function(plotting) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div data-ng-if="! rows">
              <div class="lead">&nbsp;</div>
            </div>
            <div data-ng-if="rows">
              <div class="col-sm-12" style="margin-top: 1ex;">
                <table class="table">
                  <thead>
                  <tr>
                    <th class="text-right" data-ng-repeat="h in headers">{{ h }}</th>
                  </tr>
                  </thead>
                  <tr data-ng-repeat="row in rows">
                    <td data-ng-repeat="value in row track by $index" class="text-right">{{ value }}</td>
                  </tr>
                </table>
              </div>
            </div>
        `,
        controller: function($scope) {
            plotting.setTextOnlyReport($scope);
            $scope.headers = ['S [m]', 'Charge [e]', 'X [mm]', 'Y [mm]'];
            $scope.load = function(json) {
                $scope.rows = json.rows;
            };
        },
        link: function link(scope, element) {
            scope.modelName = 'bpmAnimation';
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.factory('rftrackService', function(appState) {
    const self = {};

    self.computeModel = () => 'animation';

    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('SourceController', function(latticeService) {
    const self = this;
    latticeService.initSourceController(self);
});

SIREPO.app.controller('VisualizationController', function(appState, frameCache, panelState, persistentSimulation, requestSender, $scope) {
    const self = this;
    self.simScope = $scope;
    self.errorMessage = '';

    const valueListFields = (modelName) => {
        const r = [];
        for (const [f, d] of Object.entries(SIREPO.APP_SCHEMA.model[modelName])) {
            if (d[1] === 'ValueList') {
                r.push(f);
            }
        }
        return r;
    };

    const initModel = (info, modelName) => {
        panelState.setError(info.modelKey, null);
        if (! appState.models[info.modelKey]) {
            appState.models[info.modelKey] = {};
        }
        const m = appState.setModelDefaults(appState.models[info.modelKey], modelName);
        m.valueList = {};
        for (const f of valueListFields(modelName)) {
            m[f] = m[f] || info[f];
            m.valueList[f] = info.columns;
        }
        appState.saveQuietly(info.modelKey);
    };

    const initSimState = () => {
        const s = persistentSimulation.initSimulationState(self);

        s.errorMessage = () => self.errorMessage;

        s.logFileURL = () => {
            return requestSender.formatUrl('downloadRunFile', {
                '<simulation_id>': appState.models.simulation.simulationId,
                '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                '<model>': self.simState.model,
                '<frame>': SIREPO.nonDataFileFrame,
            });
        };

        s.runningMessage = () => {
            return 'Simulation running';
        };
        return s;
    };

    const loadReports = (reports) => {
        self.outputFiles = [];
        reports.forEach((info) => {
            if (info.modelKey == 'statAnimation' || info.modelKey == 'stat2Animation') {
                initModel(info, info.modelKey);
                return;
            }
            if (info.modelKey == 'bpmAnimation') {
                initModel(info, info.modelKey);
                self.hasBpmReport = true;
                return;
            }
            initModel(info, 'elementAnimation');
            self.outputFiles.push({
                info: info,
                modelAccess: {
                    modelKey: info.modelKey,
                    getData: () => appState.models[info.modelKey],
                    getPlotType: () => appState.models[info.modelKey].plotType,
                },
                panelTitle: info.name,
            });
            frameCache.setFrameCount(info.frameCount, info.modelKey);
        });
    };

    self.simHandleStatus = (data) => {
        self.errorMessage = data.error;
        self.outputFiles = [];
        self.hasBpmReport = false;
        if (data.reports && data.reports.length) {
            loadReports(data.reports);
        }
        frameCache.setFrameCount(data.frameCount || 0);
    };

    self.statPlotPresets = SIREPO.APP_SCHEMA.enum.StatPlotPreset;
    self.applyStatPreset = (modelName) => applyStatPlotPreset(appState, modelName);

    // Keep the Plot Presets selector in sync with the model's actual plot
    // fields -- reset it to "Select a Preset..." if the user picks plot
    // fields by hand (e.g. through the panel's Edit dialog) that no longer
    // match the preset that was last selected.
    [['statAnimation'], ['stat2Animation']].forEach(([modelName]) => {
        $scope.$watchCollection(
            () => {
                const m = appState.models[modelName];
                return m ? STAT_PLOT_PRESET_FIELDS.map((f) => m[f]) : null;
            },
            () => {
                const m = appState.models[modelName];
                if (! m) {
                    return;
                }
                const key = presetKeyForModel(m);
                if (m.plotPreset !== key) {
                    m.plotPreset = key;
                    appState.saveQuietly(modelName);
                }
            }
        );
    });

    self.simState = initSimState();
});

SIREPO.app.controller('LatticeController', function(appState, latticeService) {
    const self = this;
    self.advancedNames = SIREPO.APP_SCHEMA.constants.advancedElementNames;
    Object.defineProperty(self, 'basicNames', {
        get: () => {
            const n = SIREPO.APP_SCHEMA.constants.basicElementNames;
            const s = appState.models.simulation;
            return s && s.elementPosition === 'absolute'
                ? n.filter((t) => ! BEND_TYPES.includes(t))
                : n;
        },
    });
    self.latticeService = latticeService;

    self.titleForName = (name) => SIREPO.APP_SCHEMA.view[name].title;
});

SIREPO.app.directive('appFooter', function(rftrackService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
            <div data-lattice-import-dialog=""></div>
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('lattice')}"><a href data-ng-click="nav.openSection('lattice')"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('source')}"><a href data-ng-click="nav.openSection('source')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('visualization')}"><a href data-ng-click="nav.openSection('visualization')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
              </app-settings>
              <app-header-right-sim-list>
                <ul class="nav navbar-nav sr-navbar-right">
                  <li><a href data-ng-click="nav.showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>
                </ul>
              </app-header-right-sim-list>
            </div>
        `,
    };
});

// showFields() arguments for a CAVITY's or SOLENOID's field-map fields
function fieldMapFields(m) {
    const isMap = m.fieldSource === 'fieldMap';
    return [
        ['fieldMapInterpolation'], isMap || m.fieldSource === '2dFieldMap',
        ['fieldMapFile', 'rescaleMode'], isMap,
        ['maxField'], isMap && m.rescaleMode === 'peak',
        ['scaleFactor'], isMap && m.rescaleMode === 'factor',
    ];
}

// the fields and tabs every element view shares: the aperture, and the
// Integration tab, which only a Lattice uses
function updateElementFields(appState, panelState, type) {
    const m = appState.models[type];
    if (! m) {
        return;
    }
    const isLattice = appState.models.simulation.elementPosition === 'relative';
    const s = appState.models.simulationSettings;
    // an element a Lattice integrates through its field, rather than
    // a transfer matrix
    const isIntegrated = FIELD_INTEGRATED_TYPES.includes(type)
        || (type === 'SOLENOID' && m.fieldSource === 'fieldMap');
    panelState.showFields(type, [
        ['aperture_x', 'aperture_y'], m.apertureShape !== 'none',
        ['scNsteps'], s.spaceCharge !== 'none' && s.scLatticeNsteps === 0,
        ['odeintAlgorithm'], isIntegrated,
        ['odeintEpsabs', 'odeintEpsrel'], isIntegrated && m.odeintAlgorithm.startsWith('rk'),
    ]);
    // after Main, Aperture and Misalignment
    panelState.showTab(type, 4, isLattice && type !== 'SCREEN');
}

// element views with no dynamic fields of their own
['BPM', 'COIL', 'CORRECTOR', 'DRIFT', 'RBEND'].forEach((type) => {
    SIREPO.viewLogic(type.toLowerCase() + 'View', function(appState, panelState, $scope) {
        const updateFields = () => updateElementFields(appState, panelState, type);
        $scope.whenSelected = updateFields;
        $scope.watchFields = [
            [type + '.apertureShape', type + '.odeintAlgorithm'], updateFields,
        ];
    });
});

SIREPO.viewLogic('beamView', function(appState, panelState, $scope) {

    const updateFields = () => {
        const m = appState.models.beam;
        const isOther = m.particle === 'other';
        const isCathode = m.distributionType === 'cathode';
        const isFromFile = m.distributionType === 'fromFile';
        const isTwiss = ! isCathode && ! isFromFile;
        panelState.showFields('beam', [
            ['mass', 'charge'], isOther,
            ['charge_nC', 'np'], ! isFromFile,
            ['distributionFile', 'fromFileNearRest'], isFromFile,
            ['beta_x', 'alpha_x', 'emit_x', 'beta_y', 'alpha_y', 'emit_y', 'sigma_t', 'sigma_pt'], isTwiss,
            ['laserTransverseProfile', 'sigX', 'laserTemporalProfile', 'cutoffX', 'cutoffY', 'cutoffT', 'ePhoton', 'phiEff', 'noiseReduc'], isCathode,
            ['riseTime', 'flatTopLength'], isCathode && m.laserTemporalProfile === 'plateau',
            ['sigT'], isCathode && m.laserTemporalProfile === 'gaussian',
        ]);
        panelState.showRow('beam', 'beta_x', isTwiss);
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['beam.particle', 'beam.distributionType', 'beam.laserTemporalProfile'], updateFields,
    ];
});

SIREPO.viewLogic('quadrupoleView', function(appState, panelState, $scope) {

    const updateFields = () => {
        const m = appState.models.QUADRUPOLE;
        if (! m) {
            return;
        }
        panelState.showFields('QUADRUPOLE', [
            ['gradient'], m.strengthType === 'gradient',
            ['k1'], m.strengthType === 'k1',
        ]);
        updateElementFields(appState, panelState, 'QUADRUPOLE');
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['QUADRUPOLE.strengthType', 'QUADRUPOLE.apertureShape', 'QUADRUPOLE.odeintAlgorithm'], updateFields,
    ];
});

SIREPO.viewLogic('solenoidView', function(appState, panelState, $scope) {

    const updateFields = () => {
        const m = appState.models.SOLENOID;
        if (! m) {
            return;
        }
        panelState.showFields('SOLENOID', [
            ['b_field', 'radius'], m.fieldSource !== 'fieldMap',
            ...fieldMapFields(m),
        ]);
        updateElementFields(appState, panelState, 'SOLENOID');
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['SOLENOID.fieldSource', 'SOLENOID.rescaleMode', 'SOLENOID.apertureShape', 'SOLENOID.odeintAlgorithm'], updateFields,
    ];
});

SIREPO.viewLogic('cavityView', function(appState, panelState, $scope) {

    const updateFields = () => {
        const m = appState.models.CAVITY;
        if (! m) {
            return;
        }
        panelState.showFields('CAVITY', [
            ['gradient'], m.fieldSource === 'analytic',
            ['fieldMapFile2d'], m.fieldSource === '2dFieldMap',
            ...fieldMapFields(m),
        ]);
        updateElementFields(appState, panelState, 'CAVITY');
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['CAVITY.fieldSource', 'CAVITY.rescaleMode', 'CAVITY.apertureShape', 'CAVITY.odeintAlgorithm'], updateFields,
    ];
});

SIREPO.viewLogic('sbendView', function(appState, panelState, $scope) {

    const updateFields = () => {
        if (! appState.models.SBEND) {
            return;
        }
        // a Volume's 3D fringe field depends on hgap alone
        panelState.showFields('SBEND', [
            ['fint'], appState.models.simulation.elementPosition === 'relative',
        ]);
        updateElementFields(appState, panelState, 'SBEND');
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['SBEND.apertureShape', 'SBEND.odeintAlgorithm'], updateFields,
    ];
});

SIREPO.viewLogic('screenView', function(appState, panelState, $scope) {

    const updateFields = () => {
        if (! appState.models.SCREEN) {
            return;
        }
        updateElementFields(appState, panelState, 'SCREEN');
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['SCREEN.apertureShape', 'SCREEN.odeintAlgorithm'], updateFields,
    ];
});

SIREPO.viewLogic('sextupoleView', function(appState, panelState, $scope) {

    const updateFields = () => {
        const m = appState.models.SEXTUPOLE;
        if (! m) {
            return;
        }
        panelState.showFields('SEXTUPOLE', [
            ['gradient'], m.strengthType === 'gradient',
            ['k2'], m.strengthType === 'k2',
        ]);
        updateElementFields(appState, panelState, 'SEXTUPOLE');
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['SEXTUPOLE.strengthType', 'SEXTUPOLE.apertureShape', 'SEXTUPOLE.odeintAlgorithm'], updateFields,
    ];
});

SIREPO.viewLogic('simulationView', function(appState, $scope) {
    $scope.watchFields = [
        ['simulation.elementPosition'], () => {
            // Volume-only settings (tracking range) and Lattice-only ones
            // (per-element step counts) aren't interchangeable, so this
            // can only be picked when the simulation is created.
            appState.models.simulation.elementPosition = appState.applicationState().simulation.elementPosition;
        },
    ];
});

SIREPO.viewLogic('simulationSettingsView', function(appState, panelState, latticeService, $scope) {

    const beamlineHasCavity = (beamline, visited) => {
        visited = visited || {};
        if (! beamline || ! beamline.items || visited[beamline.id]) {
            return false;
        }
        visited[beamline.id] = true;
        for (const itemId of beamline.items) {
            const item = latticeService.elementForId(itemId);
            if (! item) {
                continue;
            }
            if (item._id !== undefined) {
                // element
                if (RF_ELEMENT_TYPES.includes(item.type)) {
                    return true;
                }
            }
            else if (beamlineHasCavity(item, visited)) {
                // nested beamline
                return true;
            }
        }
        return false;
    };

    const updateFields = () => {
        const m = appState.models.simulationSettings;
        if (! m) {
            return;
        }
        // Lattice (relative positioning) has no tracking range or
        // integrator time step: those are Volume-only
        const isVolume = appState.models.simulation.elementPosition === 'absolute';
        const hasCavity = beamlineHasCavity(latticeService.getSimulationBeamline());
        panelState.showFields('simulationSettings', [
            ['scGridNx', 'scGridNy', 'scGridNz', 'scSmooth', 'scMirror'], m.spaceCharge === 'pic',
            ['scDtMm'], m.spaceCharge === 'pic' && isVolume,
            ['scLatticeNsteps'], m.spaceCharge !== 'none' && ! isVolume,
            ['autophase'], hasCavity,
            ['autophaseReference'], hasCavity && m.autophase === '1',
            ['autoTrackingRange', 'volumeDtMm', 'volumeTtDtMm', 'odeintAlgorithm', 'volumeTMaxMm'], isVolume,
            // the error tolerances only change a Runge-Kutta algorithm's steps
            ['odeintEpsabs', 'odeintEpsrel'], isVolume && m.odeintAlgorithm.startsWith('rk'),
            ['trackingS0', 'trackingS1'], isVolume && m.autoTrackingRange === '0',
        ]);
        // the advanced editor's "Tracking" tab has only Volume settings
        panelState.showTab('simulationSettings', 2, isVolume);
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['simulationSettings.spaceCharge', 'simulationSettings.autoTrackingRange', 'simulationSettings.autophase', 'simulationSettings.odeintAlgorithm', 'simulation.visualizationBeamlineId'], updateFields,
    ];
});
