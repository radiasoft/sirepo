'use strict';

// Field values to apply to a statAnimation/stat2Animation model when the
// user picks a "Plot Presets" entry -- a shortcut for common combinations
// of x/y1-y5 fields, rather than picking each Value to Plot by hand.
const STAT_PLOT_PRESETS = {
    twiss: {
        x: 's',
        y1: 'beta_x', y1Position: 'left',
        y2: 'beta_y', y2Position: 'left',
        y3: 'alpha_x', y3Position: 'right',
        y4: 'alpha_y', y4Position: 'right',
        y5: 'None',
    },
    emittanceSigma: {
        x: 's',
        y1: 'emitt_x', y1Position: 'left',
        y2: 'emitt_y', y2Position: 'left',
        y3: 'sigma_x', y3Position: 'right',
        y4: 'sigma_y', y4Position: 'right',
        y5: 'None',
    },
    onAxisFields: {
        x: 's',
        y1: 'Ez', y1Position: 'left',
        y2: 'Bz', y2Position: 'right',
        y3: 'None',
        y4: 'None',
        y5: 'None',
    },
    energyGain: {
        x: 's',
        y1: 'mean_K', y1Position: 'left',
        y2: 'None',
        y3: 'None',
        y4: 'None',
        y5: 'None',
    },
    transverseSize: {
        x: 's',
        y1: 'sigma_x', y1Position: 'left',
        y2: 'sigma_y', y2Position: 'left',
        y3: 'emitt_4d', y3Position: 'right',
        y4: 'None',
        y5: 'None',
    },
    bunchLength: {
        x: 's',
        y1: 'sigma_z', y1Position: 'left',
        y2: 'mean_K', y2Position: 'right',
        y3: 'None',
        y4: 'None',
        y5: 'None',
    },
    centroidMotion: {
        x: 's',
        y1: 'mean_x', y1Position: 'left',
        y2: 'mean_y', y2Position: 'left',
        y3: 'None',
        y4: 'None',
        y5: 'None',
    },
};

const STAT_PLOT_PRESET_FIELDS = [
    'x', 'y1', 'y2', 'y3', 'y4', 'y5',
    'y1Position', 'y2Position', 'y3Position', 'y4Position', 'y5Position',
];

// The preset key whose field values all match the model's current field
// values, or '' if the model doesn't currently match any preset (e.g. the
// user picked plot fields by hand instead of selecting a preset).
function presetKeyForModel(m) {
    const matches = (preset) => Object.keys(preset).every((f) => m[f] === preset[f]);
    const found = Object.entries(STAT_PLOT_PRESETS).find(([, preset]) => matches(preset));
    return found ? found[0] : '';
}

function applyStatPlotPreset(appState, modelName) {
    const m = appState.models[modelName];
    const preset = STAT_PLOT_PRESETS[m.plotPreset];
    if (! preset) {
        return;
    }
    Object.assign(m, preset);
    appState.saveChanges(modelName);
}

SIREPO.app.config(function() {
    SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
    SIREPO.SINGLE_FRAME_ANIMATION = ['statAnimation', 'stat2Animation'];
    SIREPO.appDefaultSimulationValues.simulation.elementPosition = 'absolute';
    SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL = true;
    SIREPO.appFieldEditors += ``;
    SIREPO.lattice = {
        elementColor: {
        },
        elementPic: {
            bend: ['RBEND'],
            drift: ['DRIFT'],
            magnet: ['QUADRUPOLE', 'CORRECTOR'],
            rf: ['CAVITY'],
            solenoid: ['SOLENOID'],
            watch: ['SCREEN'],
        },
    };
});

SIREPO.app.factory('rftrackService', function(appState) {
    const self = {};

    self.computeModel = () => 'animation';

    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('SourceController', function(appState, latticeService, $scope) {
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

SIREPO.app.controller('LatticeController', function(latticeService, appState) {
    const self = this;
    self.advancedNames = SIREPO.APP_SCHEMA.constants.advancedElementNames;
    self.basicNames = SIREPO.APP_SCHEMA.constants.basicElementNames;
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
              </app-header-right-sim-list>
            </div>
        `,
    };
});

SIREPO.viewLogic('beamView', function(appState, panelState, $scope) {

    // The "*Longitudinal" and "*Cathode Emission" section headers are
    // plain labels, not fields -- panelState.showField()/showRow() has
    // nothing to select for them directly (showRow() only hides a
    // data-column-editor row, e.g. the Horizontal/Vertical Twiss columns
    // below). Each label is rendered as the sibling immediately before
    // the first field in its own section, so hiding/showing that first
    // field's preceding ".lead.text-center" sibling keeps the header in
    // sync with its fields without a new framework mechanism.
    const showSectionLabel = (firstField, isShown) => {
        const toggle = () => {
            const label = $('.model-beam-' + firstField)
                .closest('.form-group').parent().prev();
            if (isShown) {
                label.show();
            }
            else {
                label.hide();
            }
        };
        toggle();
        panelState.waitForUI(toggle);
    };

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
            ['sigX', 'riseTime', 'flatTopLength', 'cutoffX', 'cutoffY', 'cutoffT', 'ePhoton', 'phiEff', 'noiseReduc'], isCathode,
        ]);
        panelState.showRow('beam', 'beta_x', isTwiss);
        showSectionLabel('sigma_t', isTwiss);
        showSectionLabel('sigX', isCathode);
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['beam.particle', 'beam.distributionType'], updateFields,
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
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['QUADRUPOLE.strengthType'], updateFields,
    ];
});

SIREPO.viewLogic('solenoidView', function(appState, panelState, $scope) {

    const updateFields = () => {
        const m = appState.models.SOLENOID;
        if (! m) {
            return;
        }
        const isMap = m.fieldSource === 'fieldMap';
        panelState.showFields('SOLENOID', [
            ['b_field'], ! isMap,
            ['fieldMapFile', 'rescaleMode'], isMap,
            ['maxField'], isMap && m.rescaleMode === 'peak',
            ['scaleFactor'], isMap && m.rescaleMode === 'factor',
        ]);
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['SOLENOID.fieldSource', 'SOLENOID.rescaleMode'], updateFields,
    ];
});

SIREPO.viewLogic('cavityView', function(appState, panelState, $scope) {

    const updateFields = () => {
        const m = appState.models.CAVITY;
        if (! m) {
            return;
        }
        const isMap = m.fieldSource === 'fieldMap';
        panelState.showFields('CAVITY', [
            ['gradient'], ! isMap,
            ['fieldMapFile', 'rescaleMode'], isMap,
            ['maxField'], isMap && m.rescaleMode === 'peak',
            ['scaleFactor'], isMap && m.rescaleMode === 'factor',
        ]);
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['CAVITY.fieldSource', 'CAVITY.rescaleMode'], updateFields,
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
                if (item.type === 'CAVITY') {
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
        panelState.showFields('simulationSettings', [
            ['scGridNx', 'scGridNy', 'scGridNz', 'scDtMm', 'scSmooth', 'scMirror'], m.spaceCharge === 'pic',
            ['autophase'], beamlineHasCavity(latticeService.getSimulationBeamline()),
            ['trackingS0', 'trackingS1'], m.autoTrackingRange === '0',
        ]);
    };

    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['simulationSettings.spaceCharge', 'simulationSettings.autoTrackingRange', 'simulation.visualizationBeamlineId'], updateFields,
    ];
});
