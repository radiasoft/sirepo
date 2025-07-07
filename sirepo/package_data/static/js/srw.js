'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appDefaultSimulationValues.simulation.sourceType = 'u';
    SIREPO.SHOW_HELP_BUTTONS = true;
    SIREPO.INCLUDE_EXAMPLE_FOLDERS = true;
    SIREPO.SINGLE_FRAME_ANIMATION = ['coherenceXAnimation', 'coherenceYAnimation', 'coherentModesAnimation', 'fluxAnimation', 'multiElectronAnimation'];
    SIREPO.PLOTTING_COLOR_MAP = 'grayscale';
    SIREPO.PLOTTING_SHOW_FWHM = true;
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="beamline3d" data-beamline-3d="" class="sr-plot" data-model-name="{{ modelKey }}"></div>
    `;
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="BeamList">
          <div data-model-selection-list="" data-model-name="modelName" data-model="model" data-field="field" data-field-class="fieldClass"></div>
        </div>
        <div data-ng-switch-when="FloatStringArray" class="col-sm-12">
            <div data-srw-number-list="" data-model="model" data-field="model[field]" data-info="info" data-type="Float" data-count=""></div>
        </div>
        <div data-ng-switch-when="UndulatorList">
          <div data-model-selection-list="" data-model-name="modelName" data-model="model" data-field="field" data-field-class="fieldClass"></div>
        </div>
        <div data-ng-switch-when="ImageFile" class="col-sm-7">
          <div data-file-field="field" data-file-type="sample" data-model="model" data-selection-required="true" data-empty-selection-text="Select Image File"></div>
        </div>
        <div data-ng-switch-when="MagneticZipFile" class="col-sm-7">
          <div data-file-field="field" data-file-type="undulatorTable" data-model="model" data-selection-required="true" data-empty-selection-text="Select Magnetic Zip File"></div>
        </div>
        <div data-ng-switch-when="ArbitraryFieldFile" class="col-sm-7">
          <div data-file-field="field" data-file-type="arbitraryField" data-model="model" data-selection-required="true" data-empty-selection-text="Select Magnetic Data File"></div>
        </div>
        <div data-ng-switch-when="MirrorFile" class="col-sm-7">
          <div data-mirror-file-field="" data-model="model" data-field="field" data-model-name="modelName" ></div>
        </div>
        <div data-ng-switch-when="RandomSeed" class="col-sm-7">
          <div data-random-seed="" data-model="model" data-field="field" data-model-name="modelName" data-form="form" data-max="info[5]" data-view-name="viewName"></div>
        </div>
        <div data-ng-switch-when="RSOptElements" class="col-sm-12">
          <div data-rs-opt-elements="" data-model="model" data-field="field" data-model-name="modelName" data-form="form" data-field-class="fieldClass"></div>
        </div>
        <div data-ng-switch-when="WatchPoint" data-ng-class="fieldClass">
          <div data-watch-point-list="" data-model="model" data-field="field" data-model-name="modelName"></div>
        </div>
        <div data-ng-switch-when="OutputImageFormat">
          <div data-sample-preview=""></div>
        </div>
        <div data-ng-switch-when="SampleRandomShapeArray" class="col-sm-7">
          <div data-sample-random-shapes="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="Material" data-ng-class="fieldClass">
          <div data-material-editor="" data-model-name="modelName" data-model="model" data-field="field"></div>
        </div>
    `;
    SIREPO.appDownloadLinks = `
        <li data-download-csv-link=""></li>
        <li data-export-python-link="" data-report-title="{{ reportTitle() }}"></li>
    `;
    SIREPO.appPanelHeadingButtons = `
        <div data-ng-if="isReport && ! hasData()" class="dropdown" style="display: inline-block">
        <a href class="dropdown-toggle" data-toggle="dropdown" title="Download"> <span class="sr-panel-heading glyphicon glyphicon-cloud-download" style="margin-bottom: 0"></span></a>
        <ul class="dropdown-menu dropdown-menu-right">
        <li data-export-python-link="" data-report-title="{{ reportTitle() }}"></li>
        </ul>
        </div>
    `;

    SIREPO.PLOTTING_SHOW_CONVERGENCE_LINEOUTS = true;
    SIREPO.BEAMLINE_WATCHPOINT_MODEL_PREFIX = 'beamlineAnimation';
});

SIREPO.app.factory('srwService', function(appDataService, appState, beamlineService, panelState, requestSender, utilities, $location, $rootScope) {
    var self = {};
    self.showCalcCoherence = false;

    appDataService.canCopy = function() {
        if (appDataService.applicationMode == 'calculator' || appDataService.applicationMode == 'wavefront') {
            return false;
        }
        return true;
    };

    function attenuationPrefixes(item) {
        return item.type == 'fiber'
            ? ['external', 'core']
            : ['main', 'complementary'];
    }

    function computeUndulatorDefinition(undulatorDefinition, deflectingParameter, amplitude) {
        if (! (self.isIdealizedUndulator() || self.isTabulatedUndulator())) {
            return;
        }
        requestSender.sendStatelessCompute(
            appState,
            function(data) {
                if (! appState.isLoaded()) {
                    return;
                }
                var undulator = appState.models.undulator;
                if (undulatorDefinition === 'K') {
                    if (deflectingParameter === 'horizontalDeflectingParameter') {
                        undulator.horizontalAmplitude = data.amplitude;
                    }
                    else {
                        undulator.verticalAmplitude = data.amplitude;
                    }
                }
                else if (undulatorDefinition === 'B') {
                    if (amplitude === 'horizontalAmplitude') {
                        undulator.horizontalDeflectingParameter = data.undulator_parameter;
                    }
                    else {
                        undulator.verticalDeflectingParameter = data.undulator_parameter;
                    }
                }
                undulator.effectiveDeflectingParameter = self.formatFloat(
                    Math.sqrt(
                        Math.pow(undulator.horizontalDeflectingParameter, 2) +
                            Math.pow(undulator.verticalDeflectingParameter, 2)
                    ),
                    8);
            },
            {
                    method: 'process_undulator_definition',
                    undulator_definition: undulatorDefinition,
                    undulator_parameter: appState.models.undulator[deflectingParameter],
                    amplitude: appState.models.undulator[amplitude],
                    undulator_period: appState.models.undulator.period / 1000,
                    methodSignature: 'process_undulator_definition' + deflectingParameter,
            }
        );
    }

    function isSelected(sourceType) {
        if (appState.isLoaded()) {
            return appState.applicationState().simulation.sourceType == sourceType;
        }
        return false;
    }

    function isUserDefinedMaterial(v) {
        return v === 'User-defined';
    }

    self.addSummaryDataListener = function(scope) {
        scope.$on('summaryData', function(e, modelKey, info) {
            // update plot size info from summaryData
            if (appState.isLoaded()) {
                var range = info.fieldRange;
                var m = appState.models[modelKey];
                // only set the default plot range if no override is currently used
                if (m && 'usePlotRange' in m && m.usePlotRange == '0') {
                    m.horizontalSize = (range[4] - range[3]) *1e3;
                    m.horizontalOffset = (range[3] + range[4]) *1e3 / 2;
                    m.verticalSize = (range[7] - range[6]) *1e3;
                    m.verticalOffset = (range[6] + range[7]) *1e3 / 2;
                    appState.saveQuietly(modelKey);
                }
                if (m && 'useIntensityLimits' in m && m.useIntensityLimits == '0') {
                    m.minIntensityLimit = utilities.safeNumber(info.fieldIntensityRange[0]);
                    m.maxIntensityLimit = utilities.safeNumber(info.fieldIntensityRange[1]);
                    appState.saveQuietly(modelKey);
                }
            }
        });
    };

    self.computeBeamParameters = function(replyHandler=null) {
        requestSender.sendStatelessCompute(
            appState,
            function(data) {
                if (! appState.isLoaded()) {
                    return;
                }
                var ebeam = appState.models.electronBeam;
                ['rmsSizeX', 'rmsDivergX', 'xxprX', 'rmsSizeY', 'rmsDivergY', 'xxprY'].forEach(function(f) {
                    ebeam[f] = data[f];
                });
                appState.models.electronBeamPosition.drift = data.drift;
                if (replyHandler) {
                    replyHandler();
                }
            },
            {
                method: 'process_beam_parameters',
                source_type: appState.models.simulation.sourceType,
                undulator_type: appState.models.tabulatedUndulator.undulatorType,
                undulator_period: appState.models.undulator.period / 1000,
                undulator_length: appState.models.undulator.length,
                ebeam: appState.clone(appState.models.electronBeam),
                ebeam_position: appState.clone(appState.models.electronBeamPosition),
            }
        );
    };

    self.computeDeltaAttenCharacteristics = function(item) {
        self.updateMaterialFields(item);
        requestSender.sendStatelessCompute(
            appState,
            function(data) {
                ['refractiveIndex', 'attenuationLength'].forEach(function(f) {
                    item[f] = self.formatMaterial(data[f]);
                });
            },
            {
                method: 'delta_atten_characteristics',
                optical_element: item,
                photon_energy: appState.models.simulation.photonEnergy,
            }
        );
    };

    self.computeDualAttenCharacteristics = function(item) {
        // fiber or zonePlate items
        var prefixes = attenuationPrefixes(item);
        self.updateDualFields(item);
        requestSender.sendStatelessCompute(
            appState,
            function(data) {
                [
                    prefixes[0] + 'RefractiveIndex',
                    prefixes[0] + 'AttenuationLength',
                    prefixes[1] + 'RefractiveIndex',
                    prefixes[1] + 'AttenuationLength',
                ].forEach(function(f) {
                    item[f] = self.formatMaterial(data[f]);
                });
            },
            {
                method: 'dual_characteristics',
                optical_element: item,
                photon_energy: appState.models.simulation.photonEnergy,
                prefix1: prefixes[0],
                prefix2: prefixes[1],
            }
        );
    };

    self.computeFields = function(method, item, fields) {
        requestSender.sendStatelessCompute(
            appState,
            function(data) {
                fields.forEach(function(f) {
                    item[f] = data[f];
                });
            },
            {
                method: method,
                optical_element: item,
            }
        );
    };

    self.computeModel = function(analysisModel) {
        if (analysisModel === 'coherenceYAnimation' || analysisModel === 'coherenceXAnimation') {
            return 'multiElectronAnimation';
        }
        if (analysisModel.indexOf('beamlineAnimation') >= 0) {
            return 'beamlineAnimation';
        }
        return analysisModel;
    };

    self.formatFields = function(model, data, fields) {
        for (var f in fields) {
            var method = fields[f];
            model[f] = self[method](data[f]);
        }
    };

    self.formatFloat = function(v, decimals) {
        return +parseFloat(v).toFixed(decimals);
    };

    self.formatFloat4 = function(v) {
        return self.formatFloat(v, 4);
    };

    self.formatMaterial = function(v) {
        v = parseFloat(v);
        if (v === 0 || v === 1) {
            return v;
        }
        if (v < 1e-3) {
            return v.toExponential(6);
        }
        return self.formatFloat(v, 6);
    };

    self.formatOrientationFields = function(item, data) {
        // format all fields with formatOrientation
        return self.formatFields(item, data, [
            'nvx', 'nvy', 'nvz', 'tvx', 'tvy', 'outoptvx',
            'outoptvy', 'outoptvz', 'outframevx', 'outframevy',
        ].reduce(function(o, val) {
            o[val] = 'formatOrientation';
            return o;
        }, {}));
    };

    self.formatOrientation = function(v) {
        v = parseFloat(v);
        if (v === 0 || v === 1) {
            return v;
        }
        return self.formatFloat(v, 12);
    };

    self.rsOptElementOffsetField = function(p) {
        return `${p}Offsets`;
    };

    self.updateRSOptElements = function() {
        const optElModel = 'rsOptElement';
        const optEls = SIREPO.APP_SCHEMA.constants.rsOptElements;
        const items = (appState.models.beamline || []).filter(i => optEls[i.type]);
        const els = appState.models.exportRsOpt.elements;
        for (const item of items) {
            let e = self.findRSOptElement(item.id);
            if (e) {
                // element name may have changed
                e.title = item.title;
                continue;
            }
            e = appState.setModelDefaults({}, optElModel);
            els.push(e);

            e.title = item.title;
            e.type = item.type;
            e.id = item.id;
            const props = optEls[item.type];
            for (const p in props) {
                appState.setFieldDefaults(
                    e,
                    self.rsOptElementOffsetField(p),
                    props[p].offsetInfo || SIREPO.APP_SCHEMA.constants.rsOptDefaultOffsetInfo[p],
                    true
                );
                e[p] = {
                    fieldNames: props[p].fieldNames,
                    initial: [],
                    offsets: [],
                };
                for (const f of props[p].fieldNames || []) {
                    e[p].initial.push(item[f] ? parseFloat(item[f]) : 0.0);
                }
            }
        }
        // remove outdated elements
        for (let i = els.length - 1; i >= 0; --i) {
            if (! beamlineService.getItemById(els[i].id)) {
                els.splice(i, 1);
            }
        }
        // put in beamline order
        let ids = items.map(function (i) {
            return i.id;
        });
        els.sort(function (e1, e2) {
            return ids.indexOf(e1.id) - ids.indexOf(e2.id);
        });
        appState.saveQuietly('exportRsOpt');
        return els;
    };

    self.findRSOptElement = function(id) {
        for (let e of appState.models.exportRsOpt.elements) {
            if (e.id === id) {
                return e;
            }
        }
        return null;
    };

    self.getFluxTitle = function(modelName) {
        let res = beamlineService.getReportTitle(modelName);
        if (appState.models[modelName].fluxType == '2') {
            return res.replace(
                'Spectral Flux',
                'Spectral Flux per Unit Surface for Finite Emittance Electron Beam');
        }
        return res;
    };

    self.getLastElementPosition = () => {
        let res = 0;
        for (const b of appState.models.beamline) {
            if (! b.isDisabled) {
                res = b.position;
            }
        }
        return res;
    };

    self.getReportTitle = function(modelName, itemId) {
        if (! appState.isLoaded()) {
            return '';
        }
        if (modelName == 'multiElectronAnimation') {
            //TODO(pjm): why not cache it on the multiElectronAnimation model?
            // multiElectronAnimation title is cached on the simulation model
            var title = appState.models.simulation.multiElectronAnimationTitle;
            if (title) {
                return title;
            }
        }
        return beamlineService.getReportTitle(modelName, itemId);
    };

    self.isApplicationMode = function(name) {
        return name == appDataService.applicationMode;
    };

    self.isElectronBeam = function() {
        return self.isIdealizedUndulator() || self.isTabulatedUndulator() || self.isMultipole() || self.isArbitraryMagField();
    };

    self.isGaussianBeam = function() {
        return isSelected('g');
    };

    self.isIdealizedUndulator = function() {
        return isSelected('u');
    };

    self.isArbitraryMagField = function() {
        return isSelected('a');
    };

    self.isMultipole = function() {
        return isSelected('m');
    };

    self.isTabulatedUndulator = function() {
        return isSelected('t');
    };

    self.isTabulatedUndulatorWithMagenticFile = function() {
        return self.isTabulatedUndulator() && appState.models.tabulatedUndulator.undulatorType == 'u_t';
    };

    self.loadModelList = function(modelName, callback, sig) {
        return requestSender.sendStatefulCompute(
            appState,
            callback,
            {
                method: 'model_list',
                args: {
                    methodSignature: 'model_list ' + modelName + (sig || ''),
                    model_name: modelName,
                }
            }
        );
    };

    self.setShowCalcCoherence = function(isShown) {
        self.showCalcCoherence = isShown;
    };

    self.showBrillianceReport = function() {
        return self.isIdealizedUndulator() || (self.isTabulatedUndulator() && ! self.isTabulatedUndulatorWithMagenticFile());
    };

    self.updateAmplitude = function() {
        if (panelState.isActiveField('undulator', 'horizontalAmplitude')) {
            computeUndulatorDefinition('B', 'horizontalDeflectingParameter', 'horizontalAmplitude');
        }
        else if (panelState.isActiveField('undulator', 'verticalAmplitude')) {
            computeUndulatorDefinition('B', 'verticalDeflectingParameter', 'verticalAmplitude');
        }
        else if (panelState.isActiveField('undulator', 'period')) {
            computeUndulatorDefinition('B', 'verticalDeflectingParameter', 'verticalAmplitude');
            computeUndulatorDefinition('B', 'horizontalDeflectingParameter', 'horizontalAmplitude');
        }
    };

    self.updateDeflectingParameters = function() {
        if (panelState.isActiveField('undulator', 'horizontalDeflectingParameter')) {
            computeUndulatorDefinition('K', 'horizontalDeflectingParameter', 'horizontalAmplitude');
        }
        else if (panelState.isActiveField('undulator', 'verticalDeflectingParameter')) {
            computeUndulatorDefinition('K', 'verticalDeflectingParameter', 'verticalAmplitude');
        }
    };

    self.updateDualFields = function(item) {
        var prefixes = attenuationPrefixes(item);
        panelState.showField(
            item.type, 'method',
            ! isUserDefinedMaterial(item[prefixes[0] + 'Material'])
                || ! isUserDefinedMaterial(item[prefixes[1] + 'Material']));
        prefixes.forEach(function(prefix) {
            panelState.enableField(
                item.type, prefix + 'RefractiveIndex',
                isUserDefinedMaterial(item[prefix + 'Material']));
            panelState.enableField(
                item.type, prefix + 'AttenuationLength',
                isUserDefinedMaterial(item[prefix + 'Material'])
                    || item.method === 'calculation');
        });
    };

    self.updateIntensityLimit = function(modelName, modelKey) {
        panelState.showFields(modelName, [
            ['minIntensityLimit', 'maxIntensityLimit'],
            appState.models[modelKey || modelName].useIntensityLimits == '1',
        ]);
    };

    self.updatePlotRange = function(modelName, modelKey) {
        panelState.showRow(
            modelName,
            'horizontalOffset',
            appState.models[modelKey || modelName].usePlotRange == '1');
    };

    self.updateIntensityReport = function(modelName) {
        panelState.showField(modelName, 'fieldUnits', self.isGaussianBeam());
        if (self.isElectronBeam()) {
            var precisionLabel = SIREPO.APP_SCHEMA.model[modelName].precision[0];
            if (appState.models[modelName].method === '0') {
                precisionLabel = 'Step Size';
            }
            //TODO(pjm): replace jquery
            $('.model-' + modelName + '-precision').find('label').text(precisionLabel);
        }
    };

    self.updateMaterialFields = function(item) {
        panelState.showField(item.type, 'method', ! isUserDefinedMaterial(item.material));
        panelState.enableFields(item.type, [
            'refractiveIndex', isUserDefinedMaterial(item.material),
            'attenuationLength', isUserDefinedMaterial(item.material) || item.method === 'calculation',
        ]);
    };

    self.updateSimulationGridFields = function() {
        ['simulation', 'sourceIntensityReport', 'coherentModesAnimation'].forEach(function(f) {
            var isAutomatic = appState.models[f].samplingMethod == 1;
            panelState.showFields(f, [
                'sampleFactor', isAutomatic,
                'horizontalPointCount', ! isAutomatic,
                'verticalPointCount', ! isAutomatic,
            ]);
        });
    };

    $rootScope.$on('$routeChangeSuccess', function() {
        var search = $location.search();
        if (search) {
            appDataService.applicationMode = search.application_mode || 'default';
        }
    });

    appState.setAppService(self);

    return self;
});

SIREPO.app.controller('BeamlineController', function (activeSection, appState, beamlineService, panelState, simulationQueue, srwService, $scope, $location) {
    var self = this;
    // tabs: single, multi, beamline3d
    var activeTab = 'single';
    self.appState = appState;
    self.beamlineService = beamlineService;
    self.srwService = srwService;
    self.postPropagation = [];
    self.propagations = [];
    self.beamlineModels = ['beamline', 'propagation', 'postPropagation'];
    self.toolbarItemNames = [
        ['Refractive/Diffractive optics and transmission objects', ['lens', 'crl', 'zonePlate', 'fiber', 'aperture', 'obstacle', 'mask', 'sample']],
        ['Mirrors', ['mirror', 'sphericalMirror', 'ellipsoidMirror', 'toroidalMirror']],
        ['Elements of monochromator', ['crystal', 'grating']],
        'watch',
    ];

    function copyIntensityReportCharacteristics() {
        var intensityReport = appState.models.beamlineAnimation0;
        if (intensityReport.copyCharacteristic == '0') {
            return;
        }
        var updatedModels = [];
        beamlineService.getWatchReports().forEach(function(modelKey) {
            var r = appState.models[modelKey];
            if (r.characteristic !== intensityReport.characteristic) {
                r.characteristic = intensityReport.characteristic;
                updatedModels.push(modelKey);
            }
        });
        if (updatedModels.length) {
            appState.saveChanges(updatedModels);
        }
    }

    function defaultItemPropagationParams() {
        return [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0, 0, 0, 0, 0, 0];
    }

    function defaultDriftPropagationParams() {
        return [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0, 0, 0, 0, 0, 0];
    }

    function firstElementPosition() {
        return appState.models.beamline.length
            ? appState.models.beamline[0].position
            : 0;
    }

    function syncFirstElementPositionToDistanceFromSource() {
        // Synchronize first element position -> distance from source
        if (firstElementPosition() > 0) {
            var sim = appState.models.simulation;
            if (sim.distanceFromSource != firstElementPosition()) {
                sim.distanceFromSource = firstElementPosition();
                appState.saveChanges('simulation');
            }
        }
    }

    function setWatchpointForPartiallyCoherentReport(wpId) {
         appState.models.multiElectronAnimation.watchpointId = wpId;
         appState.saveChanges('multiElectronAnimation');
    }

    function syncDistanceFromSourceToFirstElementPosition() {
        // Synchronize distance from source -> first element position:
        if (firstElementPosition()) {
            var sim = appState.models.simulation;
            if (firstElementPosition() !== sim.distanceFromSource) {
                var diff = firstElementPosition() - sim.distanceFromSource;
                appState.models.beamline.forEach(function(item) {
                    item.position = item.position - diff;
                });
                appState.saveChanges('beamline');
            }
        }
    }

    function updateMultiElectronWatchpoint() {
        var watchIds = beamlineService.getWatchIds();
        if (watchIds.length) {
            // if previous watchpoint for the multiElectronAnimation report is now gone,
            // use the last watchpoint in the beamline
            if (watchIds.indexOf(appState.models.multiElectronAnimation.watchpointId) < 0) {
                setWatchpointForPartiallyCoherentReport(watchIds[watchIds.length - 1]);
            }
        }
    }

    function updateWatchpointReports() {
        // special code to update initialIntensityReport and watchpointReports
        // from beamlineAnimation models so sirepo_bluesky can continue to use those models
        for (let name in appState.models) {
            let targetName;
            if (name == 'beamlineAnimation0') {
                targetName = 'initialIntensityReport';
            }
            else if (name.indexOf('beamlineAnimation') >= 0) {
                targetName = name.replace('beamlineAnimation', 'watchpointReport');
            }
            if (targetName) {
                appState.models[targetName] = appState.clone(appState.models[name]);
                appState.saveQuietly(targetName);
            }
        }
    }

    self.getWatchpointForPartiallyCoherentReport = function() {
         return appState.models.multiElectronAnimation.watchpointId;
    };

    self.isActiveTab = function(tab) {
        return tab == activeTab;
    };

    self.isEditable = function() {
        beamlineService.setEditable(srwService.isApplicationMode('default'));
        return beamlineService.isEditable();
    };

    self.isWatchpointActive = function(item) {
        return ! item.isDisabled && self.getWatchpointForPartiallyCoherentReport() == item.id;
    };

    self.prepareToSave = function() {
        if (! appState.isLoaded()) {
            return;
        }
        var beamline = appState.models.beamline;
        if (! appState.models.propagation) {
            appState.models.propagation = {};
        }
        var propagation = appState.models.propagation;
        self.propagations = [];
        var i;
        for (i = 0; i < beamline.length; i++) {
            if (! propagation[beamline[i].id]) {
                propagation[beamline[i].id] = [
                    defaultItemPropagationParams(),
                    defaultDriftPropagationParams(),
                ];
            }
            var p = propagation[beamline[i].id];

            if (beamline[i].type != 'watch' && beamline[i].type != 'grating' && beamline[i].type != 'crystal') {
                self.propagations.push({
                    item: beamline[i],
                    title: beamline[i].title,
                    params: p[0],
                    defaultparams: [p[0][12], p[0][13], p[0][14], p[0][15], p[0][16] ],
                });
            }

            if (beamline[i].type != 'watch' && (beamline[i].type == 'grating' || beamline[i].type == 'crystal')) {
                self.propagations.push({
                    item: beamline[i],
                    title: beamline[i].title,
                    params: p[0],
                    defaultparams: [beamline[i].outoptvx, beamline[i].outoptvy, beamline[i].outoptvz, beamline[i].outframevx, beamline[i].outframevy],
                });
            }

            if (i == beamline.length - 1) {
                break;
            }
            var d = parseFloat(beamline[i + 1].position) - parseFloat(beamline[i].position);
            if (d > 0) {
                self.propagations.push({
                    position: beamline[i].position,
                    title: 'Drift ' + srwService.formatFloat4(d) + ' m',
                    params: p[1],
                    defaultparams: [p[1][12], p[1][13], p[1][14], p[1][15], p[1][16] ],
                });
            }
        }
        if (! appState.models.postPropagation || appState.models.postPropagation.length === 0) {
            appState.models.postPropagation = defaultItemPropagationParams();
        }
        self.postPropagation = appState.models.postPropagation;

        var newPropagations = {};
        for (i = 0; i < appState.models.beamline.length; i++) {
            var item = appState.models.beamline[i];
            newPropagations[item.id] = appState.models.propagation[item.id];
        }
        appState.models.propagation = newPropagations;
        updateWatchpointReports();
    };

    self.setActiveTab = function(tab) {
        if (tab != activeTab) {
            $location.search('tab', tab);
            activeTab = tab;
        }
    };

    self.setWatchpointActive = function(item) {
        if (! self.isWatchpointActive(item)) {
            setWatchpointForPartiallyCoherentReport(item.id);
        }
    };

    self.showBeamline3dTab = () => appState.models.beamline.length > 0;

    self.showMultiTab = function() {
        if (! appState.isLoaded()) {
            return false;
        }
        if (beamlineService.getWatchItems().length === 0
            || srwService.isApplicationMode('wavefront')
            || srwService.isGaussianBeam()) {
            if (activeTab == 'multi') {
                // reset to single-electron results
                self.setActiveTab('single');
            }
            return false;
        }
        return true;
    };

    self.showPropagationModal = function() {
        self.prepareToSave();
        beamlineService.dismissPopup();
        $('#srw-propagation-parameters').modal('show');
    };

    self.showSimulationGrid = function() {
        beamlineService.dismissPopup();
        panelState.showModalEditor('simulationGrid', null, $scope);
    };

    appState.whenModelsLoaded($scope, function() {
        srwService.setShowCalcCoherence(false);
        syncFirstElementPositionToDistanceFromSource();
        $scope.$on('beamline.changed', syncFirstElementPositionToDistanceFromSource);
        $scope.$on('simulation.changed', syncDistanceFromSourceToFirstElementPosition);
        $scope.$on('multiElectronAnimation.changed', updateMultiElectronWatchpoint);
        $scope.$on('beamlineAnimation0.changed', copyIntensityReportCharacteristics);
        $scope.$on('modelChanged', (event, modelName) => {
            if (modelName.indexOf('beamlineAnimation') >= 0) {
                updateWatchpointReports();
            }
        });
        srwService.addSummaryDataListener($scope);
        var search = $location.search();
        if (search) {
            if (search.tab) {
                self.setActiveTab(search.tab);
            }
        }
    });

    $scope.$on('$destroy', function() {
        var section = activeSection.getActiveSection();
        if (section == 'beamline' || section == 'copy-session') {
            // preserve search when staying on the beamline page, or coming from a shared session
            return;
        }
        $location.search('tab', null);
    });
});

SIREPO.app.controller('MLController', function (appState, panelState, persistentSimulation, requestSender, srwService, $scope, $window) {
    const self = this;
    self.appState = appState;
    self.srwService = srwService;
    self.simScope = $scope;
    self.resultsFile = null;
    self.simComputeModel = 'machineLearningAnimation';
    self.simState = persistentSimulation.initSimulationState(self);

    self.createActivaitSimulation = () => {
        requestSender.sendRequest(
            'newSimulation',
            data => {
                requestSender.openSimulation(
                    'activait',
                    'data',
                    data.models.simulation.simulationId
                );
            },
            {
                folder: '/',
                name: appState.models.simulation.name,
                simulationType: 'activait',
                notes: 'rsopt results from SRW',
                sourceSimFile: self.resultsFile,
                sourceSimId: appState.models.simulation.simulationId,
                sourceSimType: 'srw',
            },
            err => {
                throw new Error('Error creating simulation' + err);
            }
        );
    };

    self.resultsFileURL = () => {
        return requestSender.formatUrl('downloadDataFile', {
            '<simulation_id>': appState.models.simulation.simulationId,
            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
            '<model>': self.simComputeModel,
            '<frame>': SIREPO.nonDataFileFrame,
            '<suffix>': 'h5',
        });
    };

    self.showRunSimPanel = () => appState.applicationState().exportRsOpt.totalSamples > 0;

    self.simHandleStatus = data => {
        if (data.error) {
        }
        if ('percentComplete' in data && ! data.error) {
            if (self.simState.isStateCompleted()) {
                if (data.outputInfo && data.outputInfo.length) {
                    self.resultsFile = data.outputInfo[0].filename;
                }
            }
        }
    };

    self.startSimulation = model => {
        self.resultsFile = null;
        self.simState.saveAndRunSimulation([model, 'simulation']);
    };


});

SIREPO.app.controller('SourceController', function (appState, panelState, srwService, $scope) {
    var self = this;
    self.appState = appState;
    self.srwService = srwService;

    $scope.$on('modelChanged', function(e, name) {
        if (name == 'undulator' || name == 'tabulatedUndulator') {
            // make sure the electronBeam.drift is also updated
            srwService.computeBeamParameters(() => {
                    appState.saveChanges(['electronBeamPosition', 'electronBeam']);
                }
            );
        }
        else if (name == 'gaussianBeam') {
            appState.models.sourceIntensityReport.photonEnergy = appState.models.gaussianBeam.photonEnergy;
            appState.models.simulation.photonEnergy = appState.models.gaussianBeam.photonEnergy;
            appState.saveQuietly('sourceIntensityReport');
            appState.saveQuietly('simulation');
        }
        else if (name == 'sourceIntensityReport') {
            if (! appState.models.beamline.length) {
                var sim = appState.models.simulation;
                var sourceReport = appState.models.sourceIntensityReport;
                sim.photonEnergy = sourceReport.photonEnergy;
                sim.distanceFromSource = sourceReport.distanceFromSource;
                appState.saveChanges('simulation');
            }
        }
    });

    appState.whenModelsLoaded($scope, function() {
        srwService.addSummaryDataListener($scope);
    });
});


SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
            <div data-import-python=""></div>
            <div data-sim-conversion-modal="" data-conv-method="create_shadow_simulation"></div>
            <div data-download-status="" data-label="" data-title="" data-sim-state="{}"></div>
        `,
    };
});

var srwGrazingAngleLogic = function(panelState, srwService, $scope) {
    var fields = [
        'normalVectorX', 'normalVectorY', 'normalVectorZ',
        'tangentialVectorX', 'tangentialVectorY',
    ];
    function computeVectors(item) {
        updateVectorFields(item);
        if (item.grazingAngle && item.autocomputeVectors != 'none') {
            srwService.computeFields('compute_grazing_orientation', item, fields);
        }
    }

    function updateVectorFields(item) {
        panelState.enableFields(item.type, [
            fields, item.autocomputeVectors === 'none',
        ]);
    }

    $scope.whenSelected = updateVectorFields;
    $scope.watchFields = [
        ['grazingAngle', 'autocomputeVectors'], computeVectors,
    ];
};

// three mirrors share the same view logic
[
    'ellipsoidMirrorView', 'sphericalMirrorView', 'toroidalMirrorView',
].forEach(function(m) {
    SIREPO.beamlineItemLogic(m, srwGrazingAngleLogic);
});

var srwIntensityLimitLogic = function(appState, panelState, srwService, $scope) {

    const modelKey = $scope.modelData ? $scope.modelData.modelKey : $scope.modelName;

    function hasSamplingMethod() {
        return $scope.modelName == 'sourceIntensityReport' || $scope.modelName == 'coherentModesAnimation';
    }

    function updateDetector() {
        if ($scope.modelName == 'powerDensityReport' || $scope.modelName == 'coherentModesAnimation') {
            panelState.showField($scope.modelName, 'useDetector', false);
        }
        const m = appState.models[modelKey];
        if (m.useDetector === '1') {
            m.usePlotRange = '0';
        }
        panelState.showField($scope.modelName, 'intensityPlotsWidth', m.useDetector === '0');
        panelState.showField($scope.modelName, 'useDetectorAspectRatio', m.useDetector === '1');
        panelState.showRow($scope.modelName, 'd_rx', m.useDetector === '1');
    }

    function updateIntensityLimit() {
        srwService.updateIntensityLimit(
            $scope.modelName,
            $scope.modelData ? $scope.modelData.modelKey : null);
    }

    function updatePlotRange() {
        srwService.updatePlotRange(
            $scope.modelName,
            $scope.modelData ? $scope.modelData.modelKey : null);
    }

    function updateSelected() {
        updateIntensityLimit();
        updatePlotRange();
        updateDetector();
        var schemaModel = SIREPO.APP_SCHEMA.model[$scope.modelName];
        if (schemaModel.fieldUnits) {
            panelState.showField($scope.modelName, 'fieldUnits', srwService.isGaussianBeam());
        }
        if (schemaModel.characteristic) {
            var isLimitCharacteristic = srwService.isApplicationMode('wavefront') || srwService.isGaussianBeam();
            //TODO(pjm): should not update schema
            schemaModel.characteristic[1] =
                isLimitCharacteristic ? 'CharacteristicSimple' : 'Characteristic';
        }
        if (hasSamplingMethod()) {
            srwService.updateSimulationGridFields();
            srwService.updateIntensityReport($scope.modelName);
        }
        else if ($scope.modelName == 'multiElectronAnimation') {
            updateWavefrontSource();
        }
    }

    function updateWavefrontSource() {
        const isSource = appState.models.multiElectronAnimation.wavefrontSource == 'source';
        panelState.showFields('multiElectronAnimation', [
            [
                'stokesParameter',
                'numberOfMacroElectrons',
                'integrationMethod',
                'photonEnergyBandWidth',
            ], isSource,
            'coherentModesFile', ! isSource,
        ]);
        panelState.showField('simulation', 'photonEnergy', isSource);
    }
    $scope.whenSelected = updateSelected;
    $scope.watchFields = [
        [
            modelKey + '.useIntensityLimits',
        ], updateIntensityLimit,
        [
            ($scope.modelData ? $scope.modelData.modelKey : $scope.modelName)
                + '.usePlotRange',
        ], updatePlotRange,
        [
            modelKey + '.useDetector',
        ], updateDetector,
    ];
    if (hasSamplingMethod()) {
        $scope.watchFields.push(
            [$scope.modelName + '.samplingMethod'], srwService.updateSimulationGridFields,
            [$scope.modelName + '.method'], function() {
                srwService.updateIntensityReport($scope.modelName);
            });
    }
    else if ($scope.modelName == 'multiElectronAnimation') {
        $scope.watchFields.push(
            ['multiElectronAnimation.wavefrontSource'], updateWavefrontSource);
    }
};

[
    'initialIntensityReportView', 'multiElectronAnimationView', 'powerDensityReportView',
    'sourceIntensityReportView', 'watchpointReportView', 'coherentModesAnimationView',
].forEach(function(view) {
    SIREPO.viewLogic(view, srwIntensityLimitLogic);
});

SIREPO.viewLogic('brillianceReportView', function(appState, panelState, $scope) {

    function updateBrillianceReport() {
        var report = appState.models.brillianceReport;
        var isKTuning = report.brightnessComponent == 'k-tuning';
        panelState.showEnum('brillianceReport', 'reportType', '1', isKTuning);
        if (! isKTuning && report.reportType == '1') {
            report.reportType = '0';
        }
        panelState.showFields('brillianceReport', [
            [
                'detuning', 'minDeflection', 'initialHarmonic',
                'finalHarmonic',
            ], isKTuning,
            ['energyDelta', 'harmonic'], ! isKTuning,
        ]);
    }

    $scope.whenSelected = updateBrillianceReport;
    $scope.watchFields = [
        ['brillianceReport.brightnessComponent'], updateBrillianceReport,
    ];
});

SIREPO.beamlineItemLogic('crlView', function(appState, panelState, requestSender, srwService, $scope) {

    function computeCRLCharacteristics(item) {
        updateCRLFields(item);
        requestSender.sendStatelessCompute(
            appState,
            function(data) {
                srwService.formatFields(item, data, {
                    refractiveIndex: 'formatMaterial',
                    attenuationLength: 'formatMaterial',
                    focalDistance: 'formatFloat4',
                    absoluteFocusPosition: 'formatFloat4',
                });
            },
            {
                method: 'crl_characteristics',
                optical_element: item,
                photon_energy: appState.models.simulation.photonEnergy,
            }
        );
    }

    function updateCRLFields(item) {
        panelState.enableField('crl', 'focalDistance', false);
        srwService.updateMaterialFields(item);
    }

    $scope.whenSelected = updateCRLFields;
    $scope.watchFields = [
        [
            'material', 'method', 'numberOfLenses', 'position',
            'tipRadius', 'refractiveIndex',
        ], computeCRLCharacteristics,
    ];
});

SIREPO.beamlineItemLogic('crystalView', function(appState, panelState, requestSender, srwService, $scope) {

    function computeCrystalInit(item) {
        panelState.enableFields(item.type, [
                [
                    'dSpacing', 'psi0r', 'psi0i', 'psiHr',
                    'psiHi', 'psiHBr', 'psiHBi',
                ], item.material == 'Unknown',
            ]);
        if (item.material != 'Unknown') {
            srwService.computeFields('crystal_init', item, [
                'dSpacing', 'psi0r', 'psi0i', 'psiHr', 'psiHi',
                'psiHBr', 'psiHBi', 'orientation',
            ]);
        }
    }

    function computeCrystalOrientation(item) {
        updateCrystalOrientationFields(item);
        requestSender.sendStatelessCompute(
            appState,
            function(data) {
                srwService.formatOrientationFields(item, data);
            },
            {
                method: 'crystal_orientation',
                optical_element: item,
                photon_energy: appState.models.simulation.photonEnergy,
            }
        );
    }

    function updateCrystal(item) {
        computeCrystalInit(item);
        updateCrystalOrientationFields(item);
    }

    function updateCrystalOrientationFields(item) {
        panelState.enableFields(item.type, [
            ['nvx', 'nvy', 'nvz', 'tvx', 'tvy'], false,
        ]);
    }

    $scope.whenSelected = updateCrystal;
    $scope.watchFieldsNoInit = [
        [
            'material', 'energy', 'diffractionAngle', 'h', 'k', 'l'
        ], computeCrystalInit,
        [
            'energy', 'diffractionAngle', 'useCase', 'dSpacing',
            'asymmetryAngle', 'psi0r', 'psi0i',
        ], computeCrystalOrientation,
    ];
});

SIREPO.viewLogic('electronBeamView', function(appState, panelState, srwService, utilities, $scope) {
    if ($scope.fieldDef == 'basic') {
        return;
    }

    var allBeamNames = [];
    var predefinedBeams = {};

    function checkBeamName() {
        var ebeam = appState.models.electronBeam;

        if (predefinedBeams[ebeam.name]) {
            if (isBeamEqual(ebeam, predefinedBeams[ebeam.name])) {
                ebeam.isReadOnly = true;
                delete ebeam.id;
                ebeam.beamSelector = ebeam.name;
            }
            else {
                ebeam.name = appState.uniqueName(allBeamNames, 'name', ebeam.name + ' {}');
                ebeam.isReadOnly = false;
            }
        }
    }

    function computeAndUpdate() {
        srwService.computeBeamParameters();
        updateBeamFields();
    }

    function isBeamEqual(beam1, beam2) {
        var isEqual = true;
        Object.keys(SIREPO.APP_SCHEMA.model.electronBeam).some(function(f) {
            if (f != 'beamSelector' && f != 'name') {
                if (beam1[f] != beam2[f]) {
                    isEqual = false;
                    return true;
                }
            }
        });
        return isEqual;
    }

    function loadBeamList() {
        srwService.loadModelList(
            'electronBeam',
            function(data) {
                allBeamNames = [];
                predefinedBeams = {};
                if (data.modelList) {
                    data.modelList.forEach(function(m) {
                        allBeamNames.push({ name: m.name });
                        if (m.isReadOnly) {
                            predefinedBeams[m.name] = m;
                        }
                    });
                }
                if (appState.isLoaded()) {
                    checkBeamName();
                }
            }, '2');
    }

    function updateBeamFields() {
        var isTwissDefinition = appState.models.electronBeam.beamDefinition === 't';
        var isAutoDrift = appState.models.electronBeamPosition.driftCalculationMethod === 'auto';
        // show/hide column headings and input fields for the twiss/moments sections
        panelState.showRow('electronBeam', 'horizontalEmittance', isTwissDefinition);
        panelState.showRow('electronBeam', 'rmsSizeX', ! isTwissDefinition);
        panelState.enableField('electronBeamPosition', 'drift', ! isAutoDrift);
    }

    $scope.whenSelected = function() {
        updateBeamFields();
        loadBeamList();
    };
    $scope.watchFields = [
        ['electronBeam.beamDefinition'], updateBeamFields,
        [
            'electronBeam.beamSelector',
            'electronBeamPosition.driftCalculationMethod',
        ], computeAndUpdate,
        [
            'electronBeam.horizontalEmittance', 'electronBeam.horizontalBeta',
            'electronBeam.horizontalAlpha', 'electronBeam.horizontalDispersion',
            'electronBeam.horizontalDispersionDerivative',
            'electronBeam.verticalEmittance', 'electronBeam.verticalBeta',
            'electronBeam.verticalAlpha', 'electronBeam.verticalDispersion',
            'electronBeam.verticalDispersionDerivative',
        ], () => srwService.computeBeamParameters(),
        Object.keys(SIREPO.APP_SCHEMA.model.electronBeam).map(function(f) {
            return 'electronBeam.' + f;
        }), utilities.debounce(checkBeamName),
    ];
});

SIREPO.beamlineItemLogic('fiberView', function(srwService, $scope) {
    $scope.whenSelected = srwService.updateDualFields;
    $scope.watchFields = [
        [
            'method', 'externalMaterial', 'coreMaterial',
        ], srwService.computeDualAttenCharacteristics,
    ];
});

SIREPO.viewLogic('exportRsOptView', function(appState, panelState, persistentSimulation, requestSender, $compile, $scope, $rootScope) {

    const self = this;
    self.simScope = $scope;
    self.simComputeModel = 'exportRsOpt';

    function addExportUI() {
        $('#sr-exportRsOpt-basicEditor .model-panel-heading-buttons').append(
            $compile(
                `
                    <a href data-ng-click="export()" class="dropdown-toggle" data-toggle="dropdown" title="Export ML Script">
                        <span class="sr-panel-heading glyphicon glyphicon-cloud-download" style="margin-bottom: 0"></span>
                   </a>
                `
            )($scope)
        );
    }

    self.simHandleStatus = data => {
        if (self.simState.isStopped()) {
            $('#sr-download-status').modal('hide');
        }
        if (self.simState.isStateCompleted()) {
            requestSender.newWindow('downloadDataFile', {
                '<simulation_id>': appState.models.simulation.simulationId,
                '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                '<model>': 'exportRsOpt',
                '<frame>': SIREPO.nonDataFileFrame,
                '<suffix>': 'zip'
            });
        }
    };

    self.startSimulation = function(model) {
        $('#sr-download-status').modal('show');
        $rootScope.$broadcast('download.started', self.simState, 'Export Script', 'Exporting exportRsOpt.zip');
        self.simState.saveAndRunSimulation([model]);
    };

    self.simState = persistentSimulation.initSimulationState(self);

    $scope.export = () => {
        self.startSimulation($scope.modelName);
    };

    appState.whenModelsLoaded($scope, () => {
        addExportUI();
    });

});

SIREPO.viewLogic('fluxAnimationView', function(appState, panelState, srwService, $scope) {

    // sm_meth fluxAnimation.method "Flux Computation Method" 1: auto-undulator 2: auto-wiggler -1: use approximate
    // sm_mag fluxAnimation.magneticField "Magnetic Field Treatment" 1: approximate 2: accurate (tabulated)

    function updateFluxAnimation() {
        var approxMethodKey = '-1';
        var isApproximateMethod = appState.models.fluxAnimation.method == approxMethodKey;
        if (srwService.isArbitraryMagField()) {
            appState.models.fluxAnimation.magneticField = '2';
        }
        panelState.enableField(
            'fluxAnimation', 'magneticField',
            srwService.isTabulatedUndulatorWithMagenticFile());
        if (srwService.isTabulatedUndulatorWithMagenticFile() || srwService.isArbitraryMagField()) {
            if (appState.models.fluxAnimation.magneticField == '2' && isApproximateMethod) {
                appState.models.fluxAnimation.method = '1';
            }
        }
        else {
            appState.models.fluxAnimation.magneticField = '1';
        }

        // No approximate flux method with accurate magnetic field
        panelState.showEnum('fluxAnimation', 'method', approxMethodKey, appState.models.fluxAnimation.magneticField == 1);
        panelState.showFields('fluxAnimation', [
            [
                'initialHarmonic', 'finalHarmonic', 'longitudinalPrecision',
                'azimuthalPrecision',
            ], isApproximateMethod,
            ['precision', 'numberOfMacroElectrons'], ! isApproximateMethod,
        ]);
    }

    $scope.whenSelected = updateFluxAnimation;
    $scope.watchFields = [
        ['fluxAnimation.magneticField'], updateFluxAnimation,
    ];
});

SIREPO.viewLogic('gaussianBeamView', function(appState, panelState, srwService, $scope) {
    if ($scope.fieldDef == 'basic') {
        return;
    }

    function convertGBSize(field, energy) {
        var value = appState.models.gaussianBeam[field];
        var waveLength = (1239.84193 * 1e-9) / energy;  // [m]
        var factor = waveLength / (4 * Math.PI);
        var res = null;
        // TODO(MR): get units automatically.
        res = factor / (value * 1e-6) * 1e6;  // [um] -> [urad] or [urad] -> [um]
        if (isNaN(res) || ! isFinite(res)) {
            return null;
        }
        return srwService.formatFloat(res, 6);
    }

    function updateGaussianBeamSize() {
        if (! srwService.isGaussianBeam()) {
            return;
        }
        var beam = appState.models.gaussianBeam;
        var energy = beam.photonEnergy;
        var isWaist = beam.sizeDefinition == '1';
        panelState.enableFields('gaussianBeam', [
            'rmsSizeX', isWaist,
            'rmsSizeY', isWaist,
            'rmsDivergenceX', ! isWaist,
            'rmsDivergenceY', ! isWaist,
        ]);

        if (isWaist) {
            beam.rmsDivergenceX = convertGBSize('rmsSizeX', energy);
            beam.rmsDivergenceY = convertGBSize('rmsSizeY', energy);
        }
        else {
            beam.rmsSizeX = convertGBSize('rmsDivergenceX', energy);
            beam.rmsSizeY = convertGBSize('rmsDivergenceY', energy);
        }
    }

    $scope.whenSelected = updateGaussianBeamSize;
    $scope.watchFields = [
        [
            'gaussianBeam.sizeDefinition', 'gaussianBeam.rmsSizeX',
            'gaussianBeam.rmsSizeY', 'gaussianBeam.rmsDivergenceX',
            'gaussianBeam.rmsDivergenceY', 'gaussianBeam.photonEnergy',
        ], updateGaussianBeamSize,
    ];
});

SIREPO.beamlineItemLogic('gratingView', function(appState, panelState, requestSender, srwService, $scope) {

    function computePGMValue(item) {
        if (item.computeParametersFrom == '3') {
            return;
        }
        updateGratingFields(item);
        requestSender.sendStatelessCompute(
            appState,
            function(data) {
                 ['energyAvg', 'cff', 'grazingAngle', 'orientation'].forEach(function(f) {
                     item[f] = data[f];
                 });
                srwService.formatOrientationFields(item, data);
            },
            {
                method: 'PGM_value',
                optical_element: item,
                photon_energy: appState.models.simulation.photonEnergy,
            }
        );
    }

    function updateGratingFields(item) {
        panelState.enableFields(item.type, [
            'cff', item.computeParametersFrom === '1',
            'grazingAngle', item.computeParametersFrom === '2',
            [
                'nvx', 'nvy', 'nvz', 'tvx', 'tvy', 'outoptvx', 'outoptvy',
                'outoptvz', 'outframevx', 'outframevy',
            ], item.computeParametersFrom === '3',
        ]);
    }

    $scope.whenSelected = updateGratingFields;
    $scope.watchFields = [
        [
            'energyAvg', 'cff', 'grazingAngle', 'rollAngle', 'computeParametersFrom',
        ], computePGMValue,
    ];
});

SIREPO.viewLogic('intensityReportView', function(srwService, $scope) {

    function updateIntensityReport() {
        srwService.updateIntensityReport('intensityReport');
    }

    $scope.whenSelected = updateIntensityReport;
    $scope.watchFields = [
        ['intensityReport.method'], updateIntensityReport,
    ];
});

SIREPO.beamlineItemLogic('maskView', function(srwService, $scope) {
    $scope.whenSelected = srwService.updateMaterialFields;
    $scope.watchFields = [
        ['method', 'material'], srwService.computeDeltaAttenCharacteristics,
    ];
});

SIREPO.beamlineItemLogic('sampleView', function(panelState, srwService, $scope) {

    function updateSample(item) {
        srwService.updateMaterialFields(item);
        updateSampleFields(item);
    }

    function updateSampleFields(item) {
        panelState.showTab('sample', 2, item.sampleSource == 'file');
        panelState.showTab('sample', 3, item.sampleSource == 'randomDisk');
        panelState.showFields('sample', [
            'resolution', item.sampleSource == 'file',
            ['dens', 'rx', 'ry', 'nx', 'ny'], item.sampleSource == 'randomDisk',
            ['areaXStart', 'areaXEnd', 'areaYStart', 'areaYEnd'], item.cropArea == '1',
            ['tileRows', 'tileColumns'], item.tileImage == '1',
            'rotateReshape', item.rotateAngle,
            'backgroundColor', item.cutoffBackgroundNoise,
            'rand_obj_size', item.obj_type != '4' && item.obj_type != '5',
            'rand_poly_side', item.obj_type == '4',
            'obj_size_ratio', item.obj_type != '4' && item.obj_type != '5' && item.rand_obj_size == '0',
            'poly_sides', item.obj_type == '4' && item.rand_poly_side == '0',
            'rand_shapes', item.obj_type == '5',
        ]);
    }

    $scope.whenSelected = updateSample;
    $scope.watchFields = [
        [
            'cropArea', 'cutoffBackgroundNoise', 'obj_type', 'rand_obj_size',
            'rand_poly_side', 'rotateAngle', 'sampleSource', 'tileImage',
        ], updateSampleFields,
        [
            'method', 'material',
        ], srwService.computeDeltaAttenCharacteristics,
    ];
});

SIREPO.viewLogic('simulationGridView', function($scope, panelState, srwService) {
    $scope.whenSelected = () => {
        srwService.updateSimulationGridFields();
        panelState.showField('simulation', 'fieldUnits', srwService.isGaussianBeam());
    };
    $scope.watchFields = [
        ['simulation.samplingMethod'], srwService.updateSimulationGridFields,
    ];
});

SIREPO.viewLogic('tabulatedUndulatorView', function(appState, panelState, requestSender, srwService, $scope) {
    if ($scope.fieldDef == 'basic') {
        return;
    }
    function computeUndulatorLength() {
        requestSender.sendStatefulCompute(
            appState,
            function(data) {
                if (appState.isLoaded() && data.length) {
                    appState.models.undulator.length = data.length;
                }
            },
            {
                method: 'undulator_length',
                args: {
                    tabulated_undulator: appState.models.tabulatedUndulator,
                }
            }
        );
    }

    function updateUndulator() {
        panelState.showRow('undulator', 'horizontalAmplitude', ! srwService.isTabulatedUndulatorWithMagenticFile());
        panelState.showFields('undulator', [
            [
                'effectiveDeflectingParameter', 'horizontalDeflectingParameter',
                'verticalDeflectingParameter', 'period', 'length',
            ], ! srwService.isTabulatedUndulatorWithMagenticFile(),
        ]);
        panelState.showFields('tabulatedUndulator', [
            ['gap', 'phase', 'magneticFile'], srwService.isTabulatedUndulatorWithMagenticFile(),
        ]);

        // Make the effective deflecting parameter read-only:
        panelState.enableField('undulator', 'effectiveDeflectingParameter', false);

        // Always hide some fields in the calculator mode:
        if (srwService.isApplicationMode('calculator')) {
            panelState.showFields('undulator', [
                ['longitudinalPosition', 'horizontalSymmetry', 'verticalSymmetry'], false,
            ]);
        }
    }

    $scope.whenSelected = updateUndulator;
    $scope.watchFields = [
        ['tabulatedUndulator.undulatorType'], updateUndulator,
        [
            'tabulatedUndulator.magneticFile', 'tabulatedUndulator.gap',
            'tabulatedUndulator.undulatorType',
        ], computeUndulatorLength,
        [
            'undulator.horizontalDeflectingParameter',
            'undulator.verticalDeflectingParameter'
        ], srwService.updateDeflectingParameters,
        [
            'undulator.horizontalAmplitude', 'undulator.verticalAmplitude',
            'undulator.period',
        ], srwService.updateAmplitude,
    ];
});

SIREPO.viewLogic('trajectoryReportView', function(appState, panelState, srwService, $scope) {

    function updateTrajectoryAxis() {
        // change enum list for plotAxisY2 depending on the selected plotAxisY value
        var selected = appState.models.trajectoryReport.plotAxisY;
        var group;
        [
            ['X', 'Y', 'Z'],
            ['Bx', 'By', 'Bz'],
            ['BetaX', 'BetaY', 'BetaZ'],
        ].forEach(function(g) {
            if (g.indexOf(selected) >= 0) {
                group = g;
            }
        });
        var y2 = appState.models.trajectoryReport.plotAxisY2;
        var validY2 = false;
        SIREPO.APP_SCHEMA.enum.TrajectoryPlotAxis.forEach(function(row) {
            var isValid = group && group.indexOf(row[0]) >= 0 && selected != row[0];
            panelState.showEnum('trajectoryReport', 'plotAxisY2', row[0], isValid);
            if (isValid && y2 == row[0]) {
                validY2 = true;
            }
        });
        if (! validY2) {
            appState.models.trajectoryReport.plotAxisY2 = 'None';
        }
    }

    function updateTrajectoryMoments() {
        if (! srwService.isElectronBeam()) {
            return;
        }
        var isAutomatic = appState.models.trajectoryReport.timeMomentEstimation == 'auto';
        ['initialTimeMoment', 'finalTimeMoment'].forEach(function(f) {
            panelState.showField('trajectoryReport', f, ! isAutomatic);
            if (isAutomatic) {
                appState.models.trajectoryReport[f] = 0;
            }
        });
    }

    function updateTrajectoryReport() {
        updateTrajectoryAxis();
        updateTrajectoryMoments();
    }

    $scope.whenSelected = updateTrajectoryReport;
    $scope.watchFields = [
        ['trajectoryReport.timeMomentEstimation'], updateTrajectoryMoments,
        ['trajectoryReport.plotAxisY'], updateTrajectoryAxis,
    ];
});

SIREPO.viewLogic('undulatorView', function(appState, panelState, srwService, $scope) {
    $scope.whenSelected = function() {
        panelState.enableField('undulator', 'effectiveDeflectingParameter', false);
    };
    $scope.watchFields = [
        [
            'undulator.horizontalDeflectingParameter',
            'undulator.verticalDeflectingParameter'
        ], srwService.updateDeflectingParameters,
        [
            'undulator.horizontalAmplitude', 'undulator.verticalAmplitude',
            'undulator.period',
        ], srwService.updateAmplitude,
    ];
});

SIREPO.beamlineItemLogic('zonePlateView', function(srwService, $scope) {
    $scope.whenSelected = srwService.updateDualFields;
    $scope.watchFields = [
        [
            'method', 'mainMaterial', 'complementaryMaterial',
        ], srwService.computeDualAttenCharacteristics,
    ];
});

SIREPO.app.directive('appHeader', function(appState, panelState, srwService) {

    var rightNav = [
        '<div data-app-header-right="nav">',
          '<app-header-right-sim-loaded>',
            '<div data-sim-sections="">',
              '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
              '<li class="sim-section" data-ng-class="{active: nav.isActive(\'beamline\')}"><a href data-ng-click="nav.openSection(\'beamline\')"><span class="glyphicon glyphicon-option-horizontal"></span> Beamline</a></li>',
              '<li data-ng-if="showRsOptML()" class="sim-section" data-ng-class="{active: nav.isActive(\'ml\')}"><a href data-ng-click="nav.openSection(\'ml\')"><span class="glyphicon glyphicon-equalizer"></span> Machine Learning</a></li>',
            '</div>',
          '</app-header-right-sim-loaded>',
          '<app-settings>',
            '<div data-ng-if="showOpenShadow()"><a href data-ng-click="openShadowConfirm()"><span class="glyphicon glyphicon-upload"></span> Open as a New Shadow Simulation</a></div>',
          '</app-settings>',
          '<app-header-right-sim-list>',
            '<ul class="nav navbar-nav sr-navbar-right">',
              '<li><a href data-ng-click="showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>',
            '</ul>',
          '</app-header-right-sim-list>',
        '</div>',
    ].join('');

    function navHeader(mode, modeTitle) {
        var appInfo = SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_NAME];
        return [
            '<div class="navbar-header">',
              '<a class="navbar-brand" href="/"><img style="width: 40px; margin-top: -10px;" src="/static/img/sirepo.gif" alt="Sirepo"></a>',
              '<div class="navbar-brand">',
                '<a class="hidden-md hidden-sm" href="/light">', appInfo.longName, '</a>',
                '<a class="hidden-xs hidden-lg hidden-xl" href="/light">', appInfo.shortName, '</a>',
                '<span class="hidden-xs"> - </span>',
                '<a class="hidden-xs" href="/light#/' + mode + '" class="hidden-xs">' + modeTitle + '</a>',
                '<span class="hidden-xs" data-ng-if="nav.sectionTitle()"> - </span>',
                '<span class="hidden-xs" data-ng-bind="nav.sectionTitle()"></span>',
              '</div>',
            '</div>',
            mode == 'light-sources'
                ? [
                    '<ul class="nav navbar-nav">',
                      '<li data-ng-class="{active: nav.isActive(\'simulations\')}"><a href data-ng-click="nav.openSection(\'simulations\')"><span class="glyphicon glyphicon-th-list"></span> Simulations</a></li>',
                    '</ul>',
                ].join('')
                : '',
        ].join('');
    }

    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: `
            <div data-ng-if="srwService.isApplicationMode(\'calculator\')">
              ${navHeader('calculator', 'SR Calculator')}
              <ul data-ng-if="nav.isLoaded()" class="nav navbar-nav navbar-right">
                <li data-settings-menu="nav"></li>
                <li><a href="https://github.com/radiasoft/sirepo/issues" target="_blank"><span class="glyphicon glyphicon-exclamation-sign"></span> Issues</a></li>
              </ul>
              <ul class="nav navbar-nav navbar-right" data-ng-show="nav.isLoaded()">
                <li data-ng-if="nav.hasDocumentationUrl()"><a href data-ng-click="nav.openDocumentation()"><span class="glyphicon glyphicon-book"></span> Notes</a></li>
              </ul>
            </div>
            <div data-ng-if="srwService.isApplicationMode(\'wavefront\')">
              ${navHeader('wavefront', 'Wavefront Propagation')}
              ${rightNav}
            </div>
            <div data-ng-if="srwService.isApplicationMode(\'light-sources\')">
              ${navHeader('light-sources', 'Light Source Facilities')}
              ${rightNav}
            </div>
            <div data-ng-if="srwService.isApplicationMode(\'default\')">
              <div data-app-header-brand="" data-app-url="{{ ::appURL() }}"></div>
              <div class="navbar-left" data-app-header-left="nav"></div>
              ${rightNav}
            </div>
        `,
        controller: function($scope) {
            $scope.srwService = srwService;

            $scope.appURL = function() {
                return SIREPO.APP_SCHEMA.feature_config.app_url;
            };

            $scope.openShadowConfirm = function() {
                $('#sr-conv-dialog').modal('show');
            };

            $scope.openExportRsOpt = function() {
                panelState.showModalEditor('exportRsOpt');
            };

            $scope.showImportModal = function() {
                $('#srw-simulation-import').modal('show');
            };

            $scope.showOpenShadow = function() {
                return SIREPO.APP_SCHEMA.feature_config.show_open_shadow
                    && (srwService.isGaussianBeam() || srwService.isIdealizedUndulator() || srwService.isMultipole()
                     || (srwService.isTabulatedUndulator() && ! srwService.isTabulatedUndulatorWithMagenticFile()));
            };

            $scope.showRsOptML = function() {
                return SIREPO.APP_SCHEMA.feature_config.show_rsopt_ml &&
                    appState.models.beamline && appState.models.beamline.length > 0;
            };
        },
    };
});

//TODO(pjm): refactor and generalize with mirrorUpload
SIREPO.app.directive('importPython', function(appState, fileManager, fileUpload, requestSender, simulationQueue) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div class="modal fade" id="srw-simulation-import" tabindex="-1" role="dialog">
              <div class="modal-dialog modal-lg">
                <div class="modal-content">
                  <div class="modal-header bg-info">
                    <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <div data-help-button="{{ title }}"></div>
                    <span class="lead modal-title text-info">{{ title }}</span>
                  </div>
                  <div class="modal-body">
                    <div class="container-fluid">
                      <form name="importForm">
                        <div class="form-group">
                          <label>Select File</label>
                          <input id="srw-python-file-import" type="file" data-file-model="pythonFile">
                          <div data-ng-if="fileType(pythonFile)"></div>
                          <br />
                          <div class="srw-python-file-import-args"><label>Optional arguments:</label><input type="text" style="width: 100%" data-ng-model="importArgs"></div><br>
                          <div class="text-warning"><strong>{{ fileUploadError }}</strong></div>
                        </div>
                        <div data-ng-if="isUploading" class="col-sm-6 pull-right">Please Wait...</div>
                        <div class="clearfix"></div>
                        <div class="col-sm-6 pull-right">
                          <button data-ng-click="importPythonFile(pythonFile, importArgs)" class="btn btn-primary" data-ng-disabled="isUploading || ! pythonFile">Import File</button>
                           <button data-dismiss="modal" class="btn btn-default" data-ng-disabled="isUploading">Cancel</button>
                        </div>
                      </form>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
            $scope.fileUploadError = '';
            $scope.isUploading = false;
            $scope.title = 'Import Python or JSON Simulation File';

            $scope.fileType = function(pythonFile) {
                var importArgs = $('.srw-python-file-import-args');
                if (pythonFile && pythonFile.name.indexOf('.py') >= 0) {
                    importArgs.show();
                }
                else {
                    importArgs.hide();
                }
            };
            $scope.importPythonFile = function(pythonFile, importArgs) {
                if (! pythonFile) {
                    return;
                }
                $scope.isUploading = true;
                fileUpload.uploadFileToUrl(
                    pythonFile,
                    {
                        folder: fileManager.getActiveFolderPath(),
                        arguments: importArgs || '',
                    },
                    requestSender.formatUrl(
                        'importFile',
                        {
                            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        }
                    ),
                    function(data) {
                        $scope.isUploading = false;
                        if (data.error) {
                            $scope.fileUploadError = data.error;
                        }
                        else {
                            $('#srw-simulation-import').modal('hide');
                            requestSender.localRedirect('source', {
                                ':simulationId': data.models.simulation.simulationId
                            });
                        }
                    });
            };
        },
        link: function(scope, element) {
            $(element).on('show.bs.modal', function() {
                $('#srw-python-file-import').val(null);
                delete scope.pythonFile;
                scope.fileUploadError = '';
            });
            scope.$on('$destroy', function() {
                $(element).off();
            });
        },
    };
});

SIREPO.app.directive('mirrorFileField', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            field: '=',
            model: '=',
        },
        template: `
            <div data-file-field="field" data-file-type="mirror" data-model="model" data-selection-required="modelName == \'mirror\'" data-empty-selection-text="No Mirror Error">
              <button type="button" title="View Graph" class="btn btn-default" data-ng-click="showFileReport()"><span class="glyphicon glyphicon-eye-open"></span></button>
            </div>
        `,
        controller: function($scope) {
            $scope.showFileReport = function() {
                var beamline = panelState.findParentAttribute($scope, 'beamline');
                appState.models.mirrorReport = $scope.model;
                appState.saveQuietly('mirrorReport');
                var el = $('#srw-mirror-plot');
                el.modal('show');
                el.on('shown.bs.modal', function() {
                    // this forces the plot to reload
                    beamline.mirrorReportShown = true;
                    $scope.$apply();
                    appState.saveChanges('mirrorReport');
                });
                el.on('hidden.bs.modal', function() {
                    beamline.mirrorReportShown = false;
                    el.off();
                });
            };
        },
    };
});

SIREPO.app.directive('rsOptElements', function(appState, frameCache, panelState, srwService, utilities, validationService) {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            form: '=',
            model: '=',
        },
        template: `
            <div class="sr-object-table" style="border-width: 2px; border-color: black;">
              <div style="border-style: solid; border-width: 1px; border-color: #00a2c5;">
              <table class="table table-hover table-condensed" style="">
                <thead>
                    <tr>
                        <td style="font-weight: bold">Element</td>
                        <td style="font-weight: bold">Parameter Variations</td>
                    </tr>
                </thead>
                <tbody>
                    <tr data-ng-repeat="e in rsOptElements track by $index">
                      <td><div class="checkbox checkbox-inline"><label><input type="checkbox" data-ng-model="e.enabled" data-ng-change="updateTotalSamples()"> {{ e.title }}</label></div></td>
                      <td data-ng-repeat="p in rsOptParams" data-ng-if="hasFields(e, p)">
                        <div data-ng-show="showFields(e)" style="font-weight: bold; text-align: center; line-height: 2">{{ rsOptElementFields[$index] }}</div>
                        <div data-ng-show="showFields(e)" data-model-field="srwService.rsOptElementOffsetField(p)" data-model-name="modelName" data-model-data="elementModelData(e)" data-label-size="0" data-custom-info="elementInfo(e, p)"></div>
                      </td>
                    </tr>
                </tbody>
              </table>
              </div>
            </div>
        `,
        controller: function($scope) {
            const els = SIREPO.APP_SCHEMA.constants.rsOptElements;
            let exportFields = ['exportRsOpt.elements', 'exportRsOpt.numSamples', 'exportRsOpt.scanType'];
            let elementFields = [];

            $scope.appState = appState;
            $scope.elementData = {};
            $scope.srwService = srwService;
            $scope.modelName = 'rsOptElement';
            $scope.rsOptElements = [];
            $scope.rsOptParams = [];
            $scope.rsOptElementFields = [];

            $scope.hasFields = function(e, p) {
                return els[e.type][p];
            };

            $scope.elementInfo = function(e, p) {
                return els[e.type][p].offsetInfo;
            };

            $scope.elementModelData = function(e) {
                return $scope.elementData[e.id];
            };

            $scope.showFields = function(e) {
                return e.enabled !== '0' && e.enabled;
            };

            $scope.updateTotalSamples = function() {
                let numParams = 0;
                for (let e of $scope.rsOptElements.filter((e) => {
                    return $scope.showFields(e);
                })) {
                    for (let p of $scope.rsOptParams) {
                        if (! e[p]) {
                            continue;
                        }
                        numParams += e[srwService.rsOptElementOffsetField(p)]
                            .split(',')
                            .reduce((c, x) => c + (parseFloat(x) ? 1 : 0), 0);
                    }
                }
                $scope.model.totalSamples = numParams === 0 ? 0 :
                    ($scope.model.scanType === 'random' ? $scope.model.numSamples :
                    Math.pow($scope.model.numSamples, numParams));
                updateFormValid(numParams);
            };

            function updateElements() {
                $scope.rsOptElements = srwService.updateRSOptElements();
                $scope.elementData = {};
                for (let e of $scope.rsOptElements) {
                    const el = e;
                    $scope.elementData[el.id] = {
                        getData: function() {
                            return el;
                        }
                    };
                }
                updateParams();
            }

            function updateFormValid(numParams) {
                validationService.validateField(
                    'exportRsOpt',
                    'totalSamples',
                    'input',
                    numParams > 0,
                    'select at least one element and vary at least one parameter'
                );
            }

            function updateParams() {
                let s = new Set();
                for (let e in els) {
                    for (let k of Object.keys(els[e])) {
                        s.add(k);
                    }
                }
                $scope.rsOptParams = [...s];
                $scope.rsOptElementFields = [];
                SIREPO.APP_SCHEMA.view.rsOptElement.basic = [];
                let m = SIREPO.APP_SCHEMA.model[$scope.modelName];

                // dynamically change the schema
                for (let p of $scope.rsOptParams) {
                    const fp = srwService.rsOptElementOffsetField(p);
                    m[fp] = SIREPO.APP_SCHEMA.constants.rsOptDefaultOffsetInfo[p];
                    $scope.rsOptElementFields.push(m[fp][SIREPO.INFO_INDEX_LABEL]);
                    SIREPO.APP_SCHEMA.view.rsOptElement.basic.push(fp);
                }
                $scope.updateTotalSamples();
            }

            function updateElementWatchFields() {
                for (let i = 0; i < $scope.model.elements.length; ++i) {
                    let e = $scope.model.elements[i];
                    for (let p of $scope.rsOptParams) {
                        if (e[p]) {
                            elementFields.push(`exportRsOpt.elements.${i}.${srwService.rsOptElementOffsetField(p)}`);
                        }
                    }
                }
            }

            function showRandomSeeed() {
                panelState.showField('exportRsOpt', 'randomSeed', $scope.model.scanType === 'random');
            }

            $scope.$on('exportRsOpt.editor.show', () => {
                updateElements();
            });

            updateElements();
            updateElementWatchFields();
            panelState.waitForUI(() => {
                panelState.enableField('exportRsOpt', 'totalSamples', false);
            });
            appState.watchModelFields($scope, exportFields, $scope.updateTotalSamples);
            appState.watchModelFields($scope, elementFields, $scope.updateTotalSamples);
            appState.watchModelFields($scope, ['exportRsOpt.scanType'], showRandomSeeed);
            $scope.$on('beamline.changed', updateElements);
            $scope.$on('exportRsOpt.changed', updateElements);
        },
    };
});

SIREPO.app.directive('mobileAppTitle', function(srwService) {
    function mobileTitle(mode, modeTitle) {
        return [
            '<div data-ng-if="srwService.isApplicationMode(\'' + mode + '\')" class="row visible-xs">',
              '<div class="col-xs-12 lead text-center">',
                '<a href="/light#/' + mode + '">' + modeTitle + '</a>',
                ' - {{ nav.sectionTitle() }}',
              '</div>',
            '</div>',
        ].join('');
    }

    return {
        restrict: 'A',
        scope: {
            nav: '=mobileAppTitle',
        },
        template: `
            ${mobileTitle('calculator', 'SR Calculator')}
            ${mobileTitle('wavefront', 'Wavefront Propagation')}
            ${mobileTitle('light-sources', 'Light Source Facilities')}
        `,
        controller: function($scope) {
            $scope.srwService = srwService;
        },
    };
});

SIREPO.app.directive('modelSelectionList', function(appState, srwService) {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            model: '=',
            field: '=',
            fieldClass: '=',
        },
        template: `
            <div class="dropdown" data-ng-class="fieldClass">
              <button style="display: inline-block" class="btn btn-default dropdown-toggle form-control" type="button" data-toggle="dropdown">{{ model[field] }} <span class="caret"></span></button>
              <ul class="dropdown-menu" style="margin-left: 15px">
                <li data-ng-if="isElectronBeam()" class="dropdown-header">Predefined Electron Beams</li>
                <li data-ng-repeat="item in modelList | orderBy:\'name\' track by item.name">
                  <a href data-ng-click="selectItem(item)">{{ item.name }}</a>
                </li>
                <li data-ng-if="isElectronBeam() && userModelList.length" class="divider"></li>
                <li data-ng-if="isElectronBeam() && userModelList.length" class="dropdown-header">User Defined Electron Beams</li>
                <li data-ng-repeat="item in userModelList | orderBy:\'name\' track by item.id" class="sr-model-list-item">
                  <a href data-ng-click="selectItem(item)">{{ item.name }}<span data-ng-show="! isSelectedItem(item)" data-ng-click="deleteItem(item, $event)" class="glyphicon glyphicon-remove"></span></a>
                </li>
              </ul>
            </div>
        `,
        controller: function($scope, requestSender) {

            function addNewModel(model) {
                model.id = appState.uniqueName($scope.userModelList, 'id', appState.models.simulation.simulationId + ' {}');
                // ensure the name is unique across all existing models
                var allModels = [];
                $.merge(allModels, $scope.modelList);
                $.merge(allModels, $scope.userModelList);
                allModels.some(function(m) {
                    if (model.name == m.name) {
                        model.name = appState.uniqueName(allModels, 'name', model.name + ' {}');
                        return true;
                    }
                });
                delete model.isReadOnly;
                var cloned = appState.clone(model);
                if ($scope.isTabulatedUndulator()) {
                    cloned.undulator = appState.clone(appState.models.undulator);
                }
                $scope.userModelList.push(cloned);
            }

            function updateListFromModel(model) {
                if (! $scope.userModelList) {
                    return;
                }
                $scope.userModelList.some(function(m) {
                    if (m.id == model.id) {
                        $.extend(m, appState.clone(model));
                        if ($scope.isTabulatedUndulator()) {
                            $.extend(m.undulator, appState.clone(appState.models.undulator));
                        }
                        return true;
                    }
                });
            }

            $scope.deleteItem = function(item, $event) {
                $event.stopPropagation();
                $event.preventDefault();
                requestSender.sendStatefulCompute(
                    appState,
                    $scope.loadModelList,
                    {
                        method: 'delete_user_models',
                        args: {
                            electron_beam: $scope.isElectronBeam() ? item : null,
                            tabulated_undulator: $scope.isTabulatedUndulator() ? item : null,
                        }
                    }
                );
            };
            $scope.isElectronBeam = function() {
                return $scope.modelName == 'electronBeam';
            };
            $scope.isTabulatedUndulator = function() {
                return $scope.modelName == 'tabulatedUndulator';
            };
            $scope.isSelectedItem = function(item) {
                return item.id == appState.models[$scope.modelName].id;
            };
            $scope.loadModelList = function() {
                srwService.loadModelList(
                    $scope.modelName,
                    function(data) {
                        $scope.modelList = [];
                        $scope.userModelList = [];
                        if (appState.isLoaded() && data.modelList) {
                            for (var i = 0; i < data.modelList.length; i++) {
                                var model = data.modelList[i];
                                (model.isReadOnly
                                 ? $scope.modelList
                                 : $scope.userModelList
                                ).push(model);
                            }
                        }
                    });
            };
            $scope.selectItem = function(item) {
                item = appState.clone(item);
                appState.models[$scope.modelName] = item;
                item[$scope.field] = item.name;
                if ($scope.isTabulatedUndulator()) {
                    appState.models.undulator = item.undulator;
                }
            };
            $scope.$on($scope.modelName + '.changed', function(e, name) {
                var model = appState.models[$scope.modelName];
                var selectorName = ($scope.isElectronBeam() ? 'beam' : 'undulator') + 'Selector';

                if (model.name != model[selectorName]) {
                    // use has edited the name, add the info as a new model
                    addNewModel(model);
                    model[selectorName] = model.name;
                    appState.saveQuietly($scope.modelName);
                }
                else if (! model.isReadOnly) {
                    // save custom model values into list
                    updateListFromModel(model);
                }
            });
        },
        link: function(scope) {
            scope.loadModelList();
        },
    };
});

SIREPO.app.directive('propagationParameterFieldEditor', function() {
    return {
        restrict: 'A',
        scope: {
            param: '=',
            paramInfo: '=',
            disabled: '=',
            prop: '='
        },
        template: `
            <div data-ng-switch="::paramInfo.fieldType">
              <select data-ng-switch-when="AnalyticalTreatment" number-to-string class="input-sm" data-ng-model="param[paramInfo.fieldIndex]" data-ng-options="item[0] as item[1] for item in ::analyticalTreatmentEnum"></select>
              <select data-ng-switch-when="WavefrontShiftTreatment" number-to-string class="input-sm" data-ng-model="param[paramInfo.fieldIndex]" data-ng-options="item[0] as item[1] for item in ::wavefrontShiftTreatmentEnum"></select>
              <input data-ng-disabled="disabled" data-ng-switch-when="Float" data-string-to-number="" type="text" class="srw-small-float" data-ng-class="{\'sr-disabled-text\': disabled}" data-ng-model="param[paramInfo.fieldIndex]">
              <input data-ng-disabled="disabled" data-ng-switch-when="Boolean" type="checkbox" data-ng-model="param[paramInfo.fieldIndex]" data-ng-true-value="1", data-ng-false-value="0">
              <button class="btn btn-default btn-xs" data-ng-disabled="disabled" data-ng-switch-when="Button" data-ng-model="param[paramInfo.fieldIndex]" data-ng-click="resetDefault()"><span class="glyphicon glyphicon-repeat"> </span></button>
            </div>
        `,
        controller: function($scope) {
            $scope.analyticalTreatmentEnum = SIREPO.APP_SCHEMA.enum.AnalyticalTreatment;
            $scope.wavefrontShiftTreatmentEnum = SIREPO.APP_SCHEMA.enum.WavefrontShiftTreatment;
            $scope.resetDefault = function() {
               // This is hard coded Param index for Orientation Table
               if ($scope.prop && $scope.prop.hasOwnProperty("defaultparams")) {
                 $scope.param[12] = $scope.prop.defaultparams[0];
                 $scope.param[13] = $scope.prop.defaultparams[1];
                 $scope.param[14] = $scope.prop.defaultparams[2];
                 $scope.param[15] = $scope.prop.defaultparams[3];
                 $scope.param[16] = $scope.prop.defaultparams[4];
               }
             };
        },
    };
});

SIREPO.app.directive('propagationParametersModal', function(appState) {
    return {
        restrict: 'A',
        scope: {
            propagations: '=',
            postPropagation: '=',
        },
        template: `
            <div class="modal fade" id="srw-propagation-parameters" tabindex="-1" role="dialog">
              <div class="modal-dialog modal-lg">
                <div class="modal-content">
                  <div class="modal-header bg-info">
                    <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <div data-help-button="Propagation Parameters"></div>
                    <span class="lead modal-title text-info">Propagation Parameters</span>
                  </div>
                  <div class="modal-body">
                    <div class="container-fluid">
                      <div class="row">
                        <ul class="nav nav-tabs">
                          <li data-ng-repeat="item in ::propagationSections track by $index" data-ng-class="{active: isPropagationSectionActive($index)}">
                            <a href data-ng-click="setPropagationSection($index)">{{:: item }} <span data-ng-if="propagationInfo[$index]" data-header-tooltip="propagationInfo[$index]"></span></a>
                          </li>
                        </ul>
                        <div data-propagation-parameters-table="" data-section-index="{{:: $index }}" data-sections="propagationSections"  data-section-params="parametersBySection[$index]" data-prop-type-index="propTypeIndex" data-propagations="propagations" data-post-propagation="postPropagation" data-ng-repeat="item in ::propagationSections track by $index"></div>
                      </div>
                      <div class="row">
                        <div class="col-sm-offset-6 col-sm-3">
                          <button data-dismiss="modal" class="btn btn-primary"style="width: 100%" >Close</button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
            var activePropagationSection = 0;
            $scope.propagationSections = ['Propagator and Resizing', 'Auto-Resize', 'Orientation', 'Grid Shift'];
            $scope.propagationInfo = [null, '<div style="text-align: left">Available for Standard Propagators</div>', null, null];
            $scope.parametersBySection = [
                [3, 4, 5, 6, 7, 8],
                [0, 1, 2],
                [12, 13, 14, 15, 16, 17],
                [9,10,11],
            ];

            $scope.isPropagationSectionActive = function(index) {
                return index == activePropagationSection;
            };

            $scope.setPropagationSection = function(index) {
                activePropagationSection = index;
            };

            var info = appState.modelInfo('propagationParameters');
            $scope.propTypeIndex = -1;
            for( var s in info ) {
                 if ( info[s][SIREPO.INFO_INDEX_LABEL] === 'Propagator' ) {
                    $scope.propTypeIndex = parseInt(s);
                    break;
                }
            }
        },
    };
});

SIREPO.app.directive('propagationParametersTable', function(appState, srwService) {
    return {
        restrict: 'A',
        scope: {
            sectionIndex: '@',
            sections: '=',
            sectionParams: '=',
            propTypeIndex: '=',
            propagations: '=',
            postPropagation: '=',
        },
        template: `
            <div data-ng-class="::classForSection(sectionIndex)" data-ng-show="$parent.isPropagationSectionActive(sectionIndex)">
              <table class="table table-striped table-condensed">
                <thead>
                  <tr>
                    <th>Element</th>
                    <th class="srw-tiny-heading" data-ng-repeat="item in ::parameterInfo track by $index">{{:: item.headingText }} <span data-ng-if="::item.headingTooltip" data-header-tooltip="::item.headingTooltip"</span></th>
                  </tr>
                </thead>
                <tbody>
                  <tr data-ng-repeat="prop in propagations track by $index" data-ng-class="{\'srw-disabled-item\': isDisabledPropagation(prop), \'sr-disabled-text\': isControlDisabledForProp(prop)}" >
                    <td class="input-sm" style="vertical-align: middle">{{ prop.title }}</td>
                    <td class="sr-center" style="vertical-align: middle" data-ng-repeat="paramInfo in ::parameterInfo track by $index">
                      <div data-propagation-parameter-field-editor="" data-prop="prop" data-param="prop.params" data-param-info="paramInfo" data-row-index="$index" data-disabled="isControlDisabledForProp(prop)"></div>
                    </td>
                  </tr>
                  <tr class="warning">
                    <td class="input-sm">Final post-propagation</td>
                    <td class="sr-center" style="vertical-align: middle" data-ng-repeat="paramInfo in ::parameterInfo track by $index">
                      <div data-propagation-parameter-field-editor="" data-prop="prop" data-param="postPropagation" data-param-info="paramInfo" data-disabled="isControlDisabledForParams(postPropagation)"></div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
        `,
        controller: function($scope) {

            function initParameters() {
                var info = appState.modelInfo('propagationParameters');
                $scope.resizeSectionIndex = $scope.sections.indexOf('Auto-Resize');
                $scope.parameterInfo = [];
                $scope.sectionParams.forEach(function(i) {
                    var field = i.toString();
                    $scope.parameterInfo.push({
                        headingText: info[field][SIREPO.INFO_INDEX_LABEL],
                        headingTooltip: info[field][3],
                        fieldType: info[field][SIREPO.INFO_INDEX_TYPE],
                        fieldIndex: i,
                    });
                });
            }

            $scope.classForSection = function(sectionIndex) {
                return sectionIndex == 1
                    ? 'col-md-8 col-md-offset-2'
                    : 'col-sm-12';
            };

            $scope.isDisabledPropagation = function(prop) {
                if (prop.item) {
                    return prop.item.isDisabled;
                }
                if (prop.position && prop.position >= srwService.getLastElementPosition()) {
                    return true;
                }
                return false;
            };

            $scope.isControlDisabledForProp = function(prop) {
                var p = prop ? (prop.params || []) : [];
                return $scope.isControlDisabledForParams(p);
            };
            $scope.isControlDisabledForParams = function(params) {
                if (params[$scope.propTypeIndex] == 0) {
                    return false;
                }
                return $scope.sectionIndex == $scope.resizeSectionIndex;
            };

            initParameters();
        },
    };
});

SIREPO.app.directive('samplePreview', function(appState, requestSender) {
    return {
        restrict: 'A',
        template: `
            <div class="col-xs-5" style="white-space: nowrap">
              <select class="form-control" style="display: inline-block" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in enum[info[1]]"></select>
              <a href target="_self" title="Download Processed Image" class="btn btn-default" data-ng-click="downloadProcessedImage()"><span class="glyphicon glyphicon-cloud-download"></span></a>
            </div>
            <div class="col-sm-12">
              <div class="lead text-center">
                <span data-ng-if="errorMessage">{{ errorMessage }}</span>
                <span data ng-if="isLoading && ! errorMessage">Loading image ...</span>
                </div>
              {{ loadImageFile() }}
              <img class="img-responsive srw-processed-image" />
            </div>
          `,
        controller: function($scope) {
            let imageData;
            $scope.isLoading = false;
            $scope.errorMessage = '';

            const downloadImage = (format, callback) => {
                let m = appState.clone($scope.model);
                const f = $scope.model.imageFile;
                m.outputImageFormat = format;
                $scope.errorMessage = '';
                requestSender.sendStatefulCompute(
                    appState,
                    function(data) {
                        callback(
                            data,
                            f.match(/([^\/]+)\.\w+$/)[1] + '_processed.' + format,
                        );
                    },
                    {
                        baseImage: f,
                        method: 'sample_preview',
                        model: m,
                        // TODO(robnagler) should come from schema, and be filled in automatically.
                        responseType: 'blob',
                    },
                    (response) => {
                        $scope.errorMessage = 'An error occurred creating the preview image';
                    },
                );
            };

            $scope.loadImageFile = function() {
                if (! appState.isLoaded() || imageData || $scope.isLoading) {
                    return;
                }
                $scope.isLoading = true;
                downloadImage(
                    'png',
                    (data) => {
                        imageData = data;
                        $scope.isLoading = false;
                        if ($('.srw-processed-image').length) {
                            // TODO(robnagler) need to call revokeObjectURL for previous url
                            $('.srw-processed-image')[0].src = URL.createObjectURL(data);
                        }
                    },
                );
            };

            $scope.downloadProcessedImage = function() {
                if (! appState.isLoaded()) {
                    return;
                }
                downloadImage(
                    $scope.model.outputImageFormat,
                    (data, filename) => {
                        saveAs(data, filename);
                    },
                );
            };
        },
    };
});

SIREPO.app.directive('sampleRandomShapes', function(appState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <div data-ng-repeat="shape in shapes track by shape.id" style="display: inline-block; margin-right: 1em">
              <div class="checkbox"><label><input type="checkbox" value="{{ shape.id }}" data-ng-click="toggle(shape)" data-ng-checked="isChecked(shape)">{{ shape.name }}</label></div>
            </div>
        `,
        controller: function($scope) {
            $scope.shapes = ['Rectangle', 'Ellipse', 'Triangle', 'Polygon'].map(
                function(name, idx) {
                    return {
                        name: name,
                        id: idx + 1,
                        checked: false,
                    };
                });
            $scope.isChecked = function(shape) {
                if ($scope.model && $scope.field && $scope.model[$scope.field]) {
                    return $scope.model && $scope.model[$scope.field].indexOf(shape.id) >= 0;
                }
                return false;
            };
            $scope.toggle = function(shape) {
                var m = $scope.model;
                if (m) {
                    if ($scope.isChecked(shape)) {
                        m[$scope.field].splice(m[$scope.field].indexOf(shape.id), 1);
                    }
                    else {
                        m[$scope.field].push(shape.id);
                    }
                }
            };
        },
    };
});

SIREPO.app.directive('simulationStatusPanel', function(appState, beamlineService, frameCache, panelState, persistentSimulation, srwService, requestSender) {
    return {
        restrict: 'A',
        scope: {
            model: '@simulationStatusPanel',
            title: '@',
        },
        template: `
           <div data-ng-if="(simState.getFrameCount() > 0) || errorMessage()" class="well well-lg">
              <a style="position: relative;" href="{{ logFileURL() }}" target="_blank">SRW run log file</a>
              <br>
              <a style="position: relative;" href="{{ progressLogURL() }}" target="_blank">SRW progress log file</a>
           </div>
            <form name="form" class="form-horizontal" autocomplete="off" novalidate>
              <div data-canceled-due-to-timeout-alert="simState"></div>
              <div data-ng-if="simState.isProcessing()" data-sim-state-progress-bar="" data-sim-state="simState"></div>
              <div data-ng-if="simState.isProcessing()">
                <div class="col-sm-6">
                  <div data-pending-link-to-simulations="" data-sim-state="simState"></div>
                  <div data-ng-show="simState.isInitializing()">
                    <span class="glyphicon glyphicon-hourglass"></span> {{ initMessage() }} {{ simState.dots }}
                  </div>
                  <div data-ng-show="simState.isStateRunning() && ! simState.isInitializing()">
                    {{ simState.stateAsText() }} {{ simState.dots }}
                    <div data-ng-show="! simState.isStatePending() && particleNumber">
                      Completed {{ runStepName }}: {{ particleNumber }} / {{ particleCount}}
                    </div>
                  </div>
                  <div data-ng-show="simState.hasTimeData()">
                    <div data-simulation-status-timer="simState" data-ng-show="! isFluxWithApproximateMethod()"></div>
                  </div>
                </div>
                <div class="col-sm-6 pull-right" data-ng-show="! isFluxWithApproximateMethod()">
                  <button data-ng-show="! isLoading()" class="btn btn-default" data-ng-click="cancelPersistentSimulation()">{{ stopButtonLabel() }}</button>
                </div>
              </div>
              <div data-ng-show="simState.isStopped() && ! isFluxWithApproximateMethod()">
                <div data-simulation-stopped-status="simState"></div>
                <div class="col-sm-12" data-ng-show="showFrameCount()">
                  Completed {{ runStepName }}: {{ particleNumber }} / {{ particleCount}}
                </div>
                <div class="col-sm-12" data-simulation-status-timer="simState"></div>
                <div data-job-settings-sbatch-login-and-start-simulation data-sim-state="simState" data-start-simulation="startSimulation()"></div>
              </div>
            </form>
        `,
        controller: function($scope, appState, authState, stringsService) {
            var clientFields = ['colorMap', 'aspectRatio', 'plotScale'];
            var serverFields = ['intensityPlotsWidth', 'rotateAngle', 'rotateReshape'];
            var oldModel = null;
            var self = this;
            self.simScope = $scope;
            self.simAnalysisModel = $scope.model;
            $scope.runStepName = 'macro-electrons';

            function copyModel() {
                oldModel = appState.cloneModel($scope.model);
                serverFields.concat(clientFields).forEach(function(f) {
                    delete oldModel[f];
                });
                return oldModel;
            }

            function hidePanel(modelName) {
                if (! panelState.isHidden(modelName)) {
                    panelState.toggleHidden(modelName);
                }
            }

            function isCoherentModes() {
                return $scope.model == 'coherentModesAnimation';
            }

            function setActiveAnimation() {
                //TODO(pjm):multiple independent animation models on the same page will confuse the
                // plots because the frameCache is global. hide opposite report on the source page
                if ($scope.model == 'fluxAnimation') {
                    hidePanel('coherentModesAnimation');
                }
                else if ($scope.model == 'coherentModesAnimation') {
                    hidePanel('fluxAnimation');
                }
            }

            $scope.logFileURL = () => {
                if (! appState.isLoaded()) {
                    return '';
                }
                return logFileRequest('run.log');
            };

            $scope.progressLogURL = () => {
                return logFileRequest('__srwl_logs__');
            };

            self.simHandleStatus = function(data) {
                if ($scope.simState.isProcessing()) {
                    setActiveAnimation();
                }
                if (data.method && data.method != appState.models.fluxAnimation.method) {
                    // the output file on the server was generated with a different flux method
                    $scope.simState.timeData = {};
                    frameCache.setFrameCount(0);
                    return;
                }
                if (data.percentComplete) {
                    if (! isCoherentModes()) {
                        $scope.particleNumber = data.particleNumber;
                        $scope.runStepName = appState.models[$scope.model].wavefrontSource == 'cmd'
                            ? 'mode' : 'macro-electrons';
                    }
                    $scope.particleCount = data.particleCount;
                }
                if (data.frameCount) {
                    if (data.frameCount != frameCache.getFrameCount($scope.model)) {
                        frameCache.setFrameCount(data.frameCount, $scope.model);
                        frameCache.setCurrentFrame($scope.model, data.frameIndex);
                        frameCache.setFrameCount(data.frameCount);
                    }
                    srwService.setShowCalcCoherence(data.calcCoherence);
                }
                else {
                    frameCache.setFrameCount(0, $scope.model);
                }
                if ($scope.isFluxWithApproximateMethod() && data.state == 'stopped' && ! data.frameCount) {
                    $scope.cancelPersistentSimulation();
                }
            };

            function hasReportParameterChanged() {
                // for the multiElectronAnimation, changes to the intensityPlots* fields don't require
                // the simulation to be restarted
                var model = oldModel;
                if (appState.deepEquals(model, copyModel())) {
                    return false;
                }
                return true;
            }

            function logFileRequest(logKind) {
                return  requestSender.formatUrl('downloadDataFile', {
                    '<simulation_id>': appState.models.simulation.simulationId,
                    '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                    '<model>': $scope.simState.model,
                    '<frame>': SIREPO.nonDataFileFrame,
                    '<suffix>': logKind,
                });
            }

            $scope.cancelPersistentSimulation = function() {
                $scope.simState.cancelSimulation(function() {
                    if ($scope.isFluxWithApproximateMethod()) {
                        $scope.startSimulation();
                    }
                });
            };

            $scope.initMessage = () => {
                if (isCoherentModes() && $scope.particleCount) {
                    return 'Calculating 4D cross-spectral density';
                }
                return 'Running: awaiting output';
            };

            $scope.isFluxWithApproximateMethod = function() {
                return $scope.model === 'fluxAnimation'
                    && appState.isLoaded() && appState.models.fluxAnimation.method == -1;
            };

            $scope.isLoading = () => panelState.isLoading($scope.simState.model);

            $scope.showFrameCount = () => {
                if (isCoherentModes()) {
                    return false;
                }
                if ($scope.simState.isStatePending() || $scope.simState.isInitializing() || $scope.simState.isStatePurged()) {
                    return false;
                }
                return $scope.particleNumber;
            };

            $scope.stopButtonLabel = function() {
                return stringsService.stopButtonLabel();
            };

            $scope.startSimulation = function() {
                setActiveAnimation();
                $scope.particleCount = 0;
                // The available jobRunModes can change. Default to parallel if
                // the current jobRunMode doesn't exist
                var j = appState.models[$scope.simState.model];
                if (j && j.jobRunMode && j.jobRunMode in authState.jobRunModeMap === false) {
                    j.jobRunMode = 'parallel';
                }
                frameCache.setFrameCount(0, $scope.model);
                appState.saveQuietly($scope.simState.model);
                if ($scope.model == 'multiElectronAnimation') {
                    appState.models.simulation.multiElectronAnimationTitle = beamlineService.getReportTitle($scope.model);
                }
                $scope.simState.saveAndRunSimulation('simulation');
            };

            appState.whenModelsLoaded($scope, function() {
                if (isCoherentModes()) {
                    return;
                }
                $scope.$on($scope.model + '.changed', function() {
                    if ($scope.simState.isReadyForModelChanges && hasReportParameterChanged()) {
                        $scope.cancelPersistentSimulation();
                        frameCache.setFrameCount(0, $scope.model);
                        $scope.percentComplete = 0;
                        $scope.particleNumber = 0;
                    }
                });
                copyModel();
            });

            $scope.simState = persistentSimulation.initSimulationState(self);
       },
    };
});

SIREPO.app.directive('beamline3d', function(appState, plotting, plotToPNG, srwService) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: `
            <div style="float: right; margin-top: -10px; margin-bottom: 5px;">
            <div style="display: inline-block" data-ng-repeat="dim in ::dimensions track by $index">
            <button data-ng-attr-class="btn btn-{{ selectedDimension == dim ? \'primary\' : \'default\' }}" data-ng-click="setCamera(dim)">{{ dim | uppercase }}{{ viewDirection[dim] > 0 ? \'+\' : \'-\' }}</button>&nbsp;
            </div>
            </div>
            <div class="sr-screenshot">
              <div style="padding-bottom:1px; clear: both; border: 1px solid black">
                <div class="sr-beamline3d-content" style="width: 100%; height: 50vw;"></div>
              </div>
            </div>
        `,
        controller: function($scope, $element) {
            var LABEL_FONT_HEIGHT = 96;
            var LABEL_FONT = 'normal ' + LABEL_FONT_HEIGHT + 'px Arial';
            var MAX_CONDENSED_LENGTH = 3;
            var MIN_CONDENSED_LENGTH = 0.7;
            var beamline, fsRenderer, labelCanvas, labels, orientationMarker;
            var itemDisplayDefaults = {
                aperture: {
                    color: color('#666666'),
                    height: 1,
                    width: 0.4,
                },
                crl: {
                    color: color('#3962af'),
                    height: 0.5,
                    size: 0.5,
                    width: 0.5,
                },
                crystal: {
                    color: color('#9269ff'),
                    opacity: 0.1,
                },
                default: {
                    color: color('#000000'),
                    height: 0.8,
                    size: 0.1,
                    width: 0.8,
                },
                fiber: {
                    color: color('#999999'),
                    height: 0.15,
                    size: 0.5,
                    width: 0.15,
                },
                grating: {
                    color: color('#ff6992'),
                },
                lens: {
                    color: color('#ffff99'),
                    height: 0.5,
                    opacity: 0.3,
                    width: 0.5,
                },
                mirror: {
                    color: color('#39af62'),
                    height: 0.1,
                    opacity: 0.4,
                    width: 0.1,
                },
                obstacle: {
                    color: color('#000000'),
                    height: 0.15,
                    size: 0.15,
                    width: 0.15,
                },
                watch: {
                    color: color('#ffff99'),
                    height: 0.5,
                    size: 0.25,
                    width: 0.5,
                },
            };
            $scope.dimensions = ['x', 'y', 'z'];
            $scope.viewDirection = null;
            $scope.selectedDimension = null;

            function addActor(source, prop, texture) {
                var actor = vtk.Rendering.Core.vtkActor.newInstance();
                actor.getProperty().set(prop);
                var mapper = vtk.Rendering.Core.vtkMapper.newInstance();
                mapper.setInputConnection(source.getOutputPort());
                actor.setMapper(mapper);
                if (texture) {
                    actor.addTexture(texture);
                }
                fsRenderer.getRenderer().addActor(actor);
                return actor;
            }

            function addBeam(points) {
                var pd = vtk.Common.DataModel.vtkPolyData.newInstance();
                pd.getPoints().setData(new window.Float32Array(points), 3);
                var lines = [points.length / 3];
                for (var i = 0; i < points.length / 3; i++) {
                    lines.push(i);
                }
                pd.getLines().setData(new window.Uint32Array(lines));
                var tubeFilter = vtk.Filters.General.vtkTubeFilter.newInstance({
                    numberOfSides: 25,
                    capping: true,
                    radius: 0.05,
                });
                tubeFilter.setInputData(pd);
                addActor(tubeFilter, {
                    lighting: false,
                    color: color('#99a2ff'),
                });
            }

            function addBeamline() {
                var points = options.includeSource == '1'
                    ? []
                    : [0, 0, beamline[0].center[2] - 1];
                var labelSize = maxTextDimensions(beamline);
                var prevItem = null;
                beamline.forEach(function(item) {
                    if (prevItem && appState.deepEquals(item.center, prevItem.center)) {
                        // skip duplicate, avoids tubeFilter coincident point errors.
                        // only label the first element at one position
                        item.name = '';
                    }
                    else {
                        $.merge(points, item.center);
                    }
                    addBeamlineItem(item, labelSize);
                    prevItem = item;
                });
                return points;
            }

            function addBeamlineItem(item, labelSize) {
                addBox(item);
                if (item.type == 'aperture') {
                    addBox(item, {
                        xLength: item.height,
                        yLength: item.width,
                    });
                }
                if (options().showLabels == '1') {
                    addLabel(item, labelSize);
                }
            }

            function addBox(item, props) {
                props = $.extend({
                    xLength: item.width,
                    yLength: item.height,
                    zLength: item.size,
                    center: item.center,
                    rotations: item.rotate,
                }, props || {});
                addActor(
                    vtk.Filters.Sources.vtkCubeSource.newInstance(props),
                    {
                        color: item.color || color('#39af62'),
                        edgeVisibility: true,
                        lighting: true,
                        opacity: item.opacity || 1,
                    });
            }

            function addLabel(item, labelSize) {
                if (! item.name || ! labelSize.width) {
                    return;
                }
                var plane = vtk.Filters.Sources.vtkPlaneSource.newInstance({
                    xResolution: 1,
                    yResolution: 1,
                });
                addActor(
                    plane,
                    {
                        color: color('#ffffff'),
                        //edgeVisibility: true,
                        lighting: false,
                    },
                    vtk.Rendering.Core.vtkTexture.newInstance({
                        interpolate: true,
                        inputData: [labelImage(itemText(item), labelSize)],
                    }));
                labels.push({
                    plane: plane,
                    elementCenter: item.center,
                    labelSize: labelSize,
                });
            }

            function addOrientationMarker() {
                orientationMarker = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
                    actor: vtk.Rendering.Core.vtkAxesActor.newInstance(),
                    interactor: fsRenderer.getRenderWindow().getInteractor(),
                    viewportCorner: vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.TOP_RIGHT,
                    viewportSize: 0.15,
                });
                orientationMarker.setEnabled(true);
            }

            function buildBeamline(positionInfo) {
                beamline = [];
                if (options().includeSource == "1") {
                    //TODO(pjm): use undulator center position and length
                    beamline.push({
                        type: 'source',
                        name: 'Source',
                        size: srwService.isGaussianBeam() ? 0.1 : 2.5,
                        height: srwService.isGaussianBeam() ? 0.2 : 1,
                        width: srwService.isGaussianBeam() ? 0.2 : 1,
                        center: [0, 0, 0],
                        rotate: [0, 0, 0],
                    });
                }
                var infoIdx = 0;
                var prev = {
                    point: [0, 0, 0],
                    trimmed: [0, 0, 0],
                };
                appState.applicationState().beamline.forEach(function(item) {
                    if (item.isDisabled) {
                        return;
                    }
                    var pos = positionInfo[infoIdx];
                    var point = pos.point.slice();
                    if (options().condenseBeamline == '1') {
                        trimPoint(point, prev);
                        prev = {
                            point: pos.point,
                            trimmed: point,
                        };
                    }
                    // algorithm from https://www.learnopencv.com/rotation-matrix-to-euler-angles/
                    var sy = Math.sqrt(Math.pow(pos.orient[0][0], 2) + Math.pow(pos.orient[1][0], 2));
                    var xrot, yrot, zrot;
                    if (Math.abs(sy) < 1e-6) {
                        xrot = Math.atan2(-pos.orient[1][2], pos.orient[1][1]);
                        yrot = Math.atan2(-pos.orient[2][0], sy);
                        zrot = 0;
                    }
                    else {
                        xrot = Math.atan2(pos.orient[2][1], pos.orient[2][2]);
                        yrot = Math.atan2(-pos.orient[2][0], sy);
                        zrot = Math.atan2(pos.orient[1][0], pos.orient[0][0]);
                    }
                    item = $.extend(appState.clone(item), {
                        name: item.title,
                        center: point,
                        rotate: [
                            -degrees(xrot), degrees(yrot), -degrees(zrot),
                        ],
                    });
                    // skip height profile
                    infoIdx += item.heightProfileFile ? 2 : 1;
                    setItemProps(item);
                    beamline.push(item);
                });
            }

            function color(v) {
                return vtk.Common.Core.vtkMath.hex2float(v);
            }

            function degrees(radians) {
                return radians * 180 / Math.PI;
            }

            function isReflector(itemType) {
                return itemType.search(/mirror|grating|crystal/i) >= 0;
            }

            function itemText(item) {
                if (item.name) {
                    var res = item.name;
                    if (options().showPosition == '1' && item.position) {
                        res += ', ' + srwService.formatFloat(item.position, 1) + ' m';
                    }
                    return res;
                }
                return '';
            }

            function labelCanvasSize(labelSize) {
                return {
                    width: labelSize.width + 5,
                    height: labelSize.height * 2,
                };
            }

            function labelImage(text, labelSize) {
                var size = labelCanvasSize(labelSize);
                labelCanvas.width = size.width;
                labelCanvas.height = size.height;
                var ctxt = labelCanvas.getContext('2d');
                ctxt.fillStyle = 'rgba(0, 0, 0, 0)';
                ctxt.fillRect(0, 0, labelCanvas.width, labelCanvas.height);
                ctxt.save();
                ctxt.translate(0, labelCanvas.height);
                ctxt.scale(1, -1);
                ctxt.translate(0, labelCanvas.height / 2);
                ctxt.textAlign = 'left';
                ctxt.fillStyle = 'black';
                ctxt.font = LABEL_FONT;
                ctxt.textBaseline = 'middle';
                ctxt.fillText(text, 0, 0);
                ctxt.restore();
                return vtk.Common.Core.vtkImageHelper.canvasToImageData(labelCanvas);
            }

            function labelPlanePoints(labelSize, center, dir) {
                var size = labelCanvasSize(labelSize);
                // label height in meters
                var labelHeight = 0.7;
                var labelWidth = labelHeight * size.width / size.height;
                var origin;

                if (dir == 'z') {
                    // margin from element center in meters
                    var labelMargin = 1;
                    origin = [center[0] + $scope.viewDirection[dir] * labelMargin, center[1] - labelHeight / 2, center[2]];
                    return [
                        origin,
                        [origin[0] + $scope.viewDirection[dir] * labelWidth, origin[1], origin[2]],
                        [origin[0], origin[1] + labelHeight, origin[2]],
                    ];
                }
                else {
                    // rotate the text by 50 degrees
                    var angle = radians(50);
                    var angle2 = Math.PI / 2 - angle;
                    origin = [center[0], center[1], center[2] + $scope.viewDirection[dir] * labelHeight / 4];
                    var idx = dir == 'x' ? 1 : 0;
                    // label margin from element center in meters
                    origin[idx] += 0.5;
                    var point1 = [
                        origin[0],
                        origin[1],
                        origin[2] + $scope.viewDirection[dir] * labelWidth * Math.cos(angle2)];
                    var point2 = [
                        origin[0],
                        origin[1],
                        origin[2] - $scope.viewDirection[dir] * labelHeight * Math.cos(angle)];
                    point1[idx] += labelWidth * Math.sin(angle2);
                    point2[idx] += labelHeight * Math.sin(angle);
                    return [origin, point1, point2];
                }
                throw new Error('no plane for alignment: ' + $scope.viewDirection[dir] + dir);
            }

            function maxTextDimensions() {
                var ctxt = labelCanvas.getContext('2d');
                ctxt.font = LABEL_FONT;
                var maxX = 0;
                beamline.forEach(function(item) {
                    if (item.name) {
                        var width = ctxt.measureText(itemText(item)).width;
                        if (width > maxX) {
                            maxX = width;
                        }
                    }
                });
                return {
                    width: maxX,
                    height: LABEL_FONT_HEIGHT,
                };
            }

            function mirrorSize(size) {
                return Math.max(Math.min(size || 0, 1), 0.5);
            }

            function options() {
                return appState.applicationState().beamline3DReport;
            }

            function radians(degrees) {
                return degrees * Math.PI / 180;
            }

            function removeActors() {
                var renderer = fsRenderer.getRenderer();
                renderer.getActors().forEach(function(actor) {
                    renderer.removeActor(actor);
                });
            }

            function setItemProps(item) {
                $.extend(item, itemDisplayDefaults.default);
                if (isReflector(item.type)) {
                    $.extend(item, itemDisplayDefaults.mirror);
                }
                $.extend(item, itemDisplayDefaults[item.type] || {});
                if (item.type == 'mirror') {
                    if (item.orientation == 'x') {
                        $.extend(item, {
                            height: mirrorSize(item.verticalTransverseSize * 1e-3),
                            width: mirrorSize(item.horizontalTransverseSize * 1e-3),
                        });
                    }
                    else {
                        $.extend(item, {
                            height: mirrorSize(item.horizontalTransverseSize * 1e-3),
                            width: mirrorSize(item.verticalTransverseSize * 1e-3),
                        });
                    }
                }
                else if (isReflector(item.type)) {
                    if (item.type == 'crystal') {
                        $.extend(item, {
                            normalVectorX: item.nvx,
                            normalVectorY: item.nvy,
                        });
                    }
                    if (Math.abs(item.normalVectorX) > Math.abs(item.normalVectorY)) {
                        // horizontal mirror
                        $.extend(item, {
                            height: mirrorSize(item.sagittalSize),
                            width: mirrorSize(item.tangentialSize),
                        });
                    }
                    else {
                        // vertical mirror
                        $.extend(item, {
                            height: mirrorSize(item.tangentialSize),
                            width: mirrorSize(item.sagittalSize),
                        });
                    }
                }
            }

            function trimPoint(point, prev) {
                var d = Math.sqrt(
                    Math.pow(point[0] - prev.point[0], 2)
                        + Math.pow(point[1] - prev.point[1], 2)
                        + Math.pow(point[2] - prev.point[2], 2));
                var scale = 1;
                if (d > MAX_CONDENSED_LENGTH) {
                    scale = MAX_CONDENSED_LENGTH / d;
                }
                else if (d > 0 && d < MIN_CONDENSED_LENGTH) {
                    scale = MIN_CONDENSED_LENGTH / d;
                }
                for (var i = 0; i <= 2; i++) {
                    point[i] = prev.trimmed[i] + (point[i] - prev.point[i]) * scale;
                }
            }

            function updateOrientation() {
                if ($scope.selectedDimension) {
                    $scope.selectedDimension = null;
                    $scope.$apply();
                }
            }

            $scope.clearData = function() {};

            $scope.destroy = function() {
                window.removeEventListener('resize', fsRenderer.resize);
                fsRenderer.getInteractor().unbindEvents();
            };

            $scope.init = function() {
                if (! appState.isLoaded()) {
                    appState.whenModelsLoaded($scope, $scope.init);
                    return;
                }
                fsRenderer = vtk.Rendering.Misc.vtkFullScreenRenderWindow.newInstance({
                    background: color('#ffffff'),
                    container: $('.sr-beamline3d-content')[0],
                });
                labelCanvas = document.createElement('canvas');
                labelCanvas.getContext('2d', { willReadFrequently: true,});
                fsRenderer.getInteractor().onAnimation(vtk.macro.debounce(updateOrientation, 250));
                plotToPNG.initVTK($element, fsRenderer);
            };

            $scope.load = function(json) {
                removeActors();
                if (! json.elements) {
                    return;
                }
                buildBeamline(json.elements);
                labels = [];
                $scope.selectedDimension = null;
                $scope.viewDirection = {
                    x: 1,
                    y: 1,
                    z: 1,
                };
                if (beamline.length) {
                    addBeam(addBeamline());
                }
                if (! orientationMarker) {
                    addOrientationMarker();
                }
                $scope.setCamera($scope.dimensions[0]);
            };

            $scope.resize = function() {};

            $scope.setCamera = function(dim) {
                if ($scope.selectedDimension == dim) {
                    $scope.viewDirection[dim] = -$scope.viewDirection[dim];
                }
                $scope.selectedDimension = dim;
                // align all labels
                labels.forEach(function(label) {
                    var planePoints = labelPlanePoints(label.labelSize, label.elementCenter, dim);
                    label.plane.setOrigin(planePoints[0]);
                    label.plane.setPoint1(planePoints[1]);
                    label.plane.setPoint2(planePoints[2]);
                });
                // position the camera
                var renderer = fsRenderer.getRenderer();
                var cam = renderer.get().activeCamera;
                cam.setFocalPoint(0, 0, 0);
                if (dim == 'x') {
                    cam.setPosition(- $scope.viewDirection.x, 0, 0);
                    cam.setViewUp(0, 1, 0);
                }
                else if (dim == 'y') {
                    cam.setPosition(0, $scope.viewDirection.y, 0);
                    cam.setViewUp(1, 0, 0);
                }
                else {
                    cam.setPosition(0, 0, $scope.viewDirection.z);
                    cam.setViewUp(0, 1, 0);
                }
                // can experiment with this. Higher viewAngle causes more label distortion
                // smaller viewAngle mimics parallel projection
                if (options().projection == 'parallel') {
                    cam.setParallelProjection(true);
                }
                else {
                    cam.setViewAngle(15);
                }
                renderer.resetCamera();
                cam.zoom(1.5);
                orientationMarker.updateMarkerOrientation();
                fsRenderer.getRenderWindow().render();
            };

            $scope.$on('$destroy', function() {
                if (orientationMarker) {
                    orientationMarker.setEnabled(false);
                }
            });

        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('srwNumberList', function(appState) {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            model: '=',
            info: '<',
            type: '@',
            count: '@',
        },
        template: `
            <div class="row" data-ng-repeat="defaultSelection in parseValues() track by $index">
            <div class="col-sm-5 text-right control-label">
                <label>{{ valueLabels[$index] || \'Plane \' + $index }}</label>
            </div>
            <div class="col-sm-7">
                <input class="form-control sr-list-value" data-string-to-number="{{ numberType }}" data-ng-model="values[$index]" data-min="min" data-max="max" data-ng-change="didChange()" class="form-control" style="text-align: right" required />
            </div>
            </div>
        `,
        controller: function($scope, $element) {
            let lastModel = null;
            // NOTE: does not appear to like 'model.field' format
            $scope.values = null;
            $scope.numberType = $scope.type.toLowerCase();
            $scope.min = $scope.numberType === 'int' ? Number.MIN_SAFE_INTEGER : -Number.MAX_VALUE;
            $scope.max = $scope.numberType === 'int' ? Number.MAX_SAFE_INTEGER : Number.MAX_VALUE;
            $scope.valueLabels = ($scope.info[4] || '').split(/\s*,\s*/);
            $scope.didChange = function() {
                $scope.field = $scope.values.join(', ');
            };
            $scope.parseValues = function() {
                // values were sticking around when the model changed
                if (! lastModel || lastModel !== $scope.model) {
                    lastModel = $scope.model;
                    $scope.values = null;
                }
                if ($scope.field && ! $scope.values) {
                    $scope.values = $scope.field.split(/\s*,\s*/);
                }
                return $scope.values;
            };
        },
    };
});

SIREPO.app.directive('materialEditor', function(appState) {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            field: '=',
            model: '=',
        },
        template: `
            <select class="form-control" data-ng-model="model[field]"
              data-ng-options="item[0] as item[1] for item in items"></select>
            <div class="sr-input-warning">{{ energyWarning }}</div>
        `,
        controller: function($scope) {
            const energyRange = SIREPO.APP_SCHEMA.constants.materialEnergyRange;

            function updateChoices() {
                if (! $scope.model) {
                    return;
                }
                const e = appState.applicationState().simulation.photonEnergy;
                if (e >= energyRange[0] && e <= energyRange[1]) {
                    $scope.items = SIREPO.APP_SCHEMA.enum.CRLMaterial;
                    $scope.energyWarning = '';
                }
                else {
                    $scope.items = [
                        SIREPO.APP_SCHEMA.enum.CRLMaterial[0],
                    ];
                    $scope.model[$scope.field] = $scope.items[0][0];
                    $scope.energyWarning = `Photon energy ${e} eV is outside of computable range:`
                                         + ` ${energyRange[0]} - ${energyRange[1]} eV`;
                }
            }

            updateChoices();
            $scope.$on('simulation.changed', updateChoices);
        },
    };
});
