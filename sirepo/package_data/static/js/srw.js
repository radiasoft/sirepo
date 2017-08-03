'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.appLocalRoutes.beamline = '/beamline/:simulationId';
SIREPO.appDefaultSimulationValues.simulation.sourceType = 'u';
SIREPO.PLOTTING_COLOR_MAP = 'grayscale';
//TODO(pjm): provide API for this, keyed by field type
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="BeamList">',
      '<div data-model-selection-list="" data-model-name="modelName" data-model="model" data-field="field" data-field-class="fieldClass"></div>',
    '</div>',
    '<div data-ng-switch-when="UndulatorList">',
      '<div data-model-selection-list="" data-model-name="modelName" data-model="model" data-field="field" data-field-class="fieldClass"></div>',
    '</div>',
    '<div data-ng-switch-when="ImageFile" class="col-sm-7">',
      '<div data-file-field="field" data-file-type="sample" data-want-file-report="false" data-want-image-file="true" data-model="model" data-selection-required="true" data-empty-selection-text="Select Image File"></div>',
    '</div>',
    '<div data-ng-switch-when="MagneticZipFile" class="col-sm-7">',
      '<div data-file-field="field" data-file-type="undulatorTable" data-model="model" data-selection-required="true" data-empty-selection-text="Select Magnetic Zip File"></div>',
    '</div>',
    '<div data-ng-switch-when="MirrorFile" class="col-sm-7">',
      '<div data-file-field="field" data-file-type="mirror" data-want-file-report="true" data-model="model" data-selection-required="modelName == \'mirror\'" data-empty-selection-text="No Mirror Error"></div>',
    '</div>',
].join('');
SIREPO.PLOTTING_SHOW_CONVERGENCE_LINEOUTS = true;

SIREPO.app.config(function($routeProvider, localRoutesProvider) {
    if (SIREPO.IS_LOGGED_OUT) {
        return;
    }
    var localRoutes = localRoutesProvider.$get();
    $routeProvider
        .when(localRoutes.source, {
            controller: 'SRWSourceController as source',
            templateUrl: '/static/html/srw-source.html' + SIREPO.SOURCE_CACHE_KEY,
        })
        .when(localRoutes.beamline, {
            controller: 'SRWBeamlineController as beamline',
            templateUrl: '/static/html/srw-beamline.html' + SIREPO.SOURCE_CACHE_KEY,
        });
});

SIREPO.app.factory('srwService', function(appState, beamlineService, panelState, $rootScope, $location) {
    var self = {};
    self.applicationMode = 'default';
    self.originalCharacteristicEnum = null;
    self.singleElectronCharacteristicEnum = null;

    function initCharacteristic() {
        if (self.originalCharacteristicEnum) {
            return;
        }
        self.originalCharacteristicEnum = SIREPO.APP_SCHEMA.enum.Characteristic;
        var characteristic = appState.clone(SIREPO.APP_SCHEMA.enum.Characteristic);
        characteristic.splice(1, 1);
        for (var i = 0; i < characteristic.length; i++)
            characteristic[i][1] = characteristic[i][1].replace(/Single-Electron /g, '');
        self.singleElectronCharacteristicEnum = characteristic;
    }

    function isSelected(sourceType) {
        if (appState.isLoaded()) {
            return appState.applicationState().simulation.sourceType == sourceType;
        }
        return false;
    }

    self.isApplicationMode = function(name) {
        return name == self.applicationMode;
    };

    self.isElectronBeam = function() {
        return self.isIdealizedUndulator() || self.isTabulatedUndulator() || self.isMultipole();
    };

    self.isGaussianBeam = function() {
        return isSelected('g');
    };

    self.isIdealizedUndulator = function() {
        return isSelected('u');
    };

    self.isMultipole = function() {
        return isSelected('m');
    };

    self.isPredefinedBeam = function() {
        if (appState.isLoaded()) {
            return appState.models.electronBeam.isReadOnly ? true : false;
        }
        return false;
    };

    self.isTabulatedUndulator = function() {
        return isSelected('t');
    };

    self.isTabulatedUndulatorWithMagenticFile = function() {
        return self.isTabulatedUndulator() && appState.models.tabulatedUndulator.undulatorType == 'u_t';
    };

    self.updateSimulationGridFields = function() {
        if (! appState.isLoaded()) {
            return;
        }
        ['simulation', 'sourceIntensityReport'].forEach(function(f) {
            var isAutomatic = appState.models[f].samplingMethod == 1;
            panelState.showField(f, 'sampleFactor', isAutomatic);
            panelState.showField(f, 'horizontalPointCount', ! isAutomatic);
            panelState.showField(f, 'verticalPointCount', ! isAutomatic);
        });
    };

    $rootScope.$on('$routeChangeSuccess', function() {
        var search = $location.search();
        if (search && search.application_mode) {
            self.applicationMode = search.application_mode;
            beamlineService.setEditable(self.applicationMode == 'default');
        }
    });

    appState.whenModelsLoaded($rootScope, function() {
        initCharacteristic();
        // don't show multi-electron values in certain cases
        SIREPO.APP_SCHEMA.enum.Characteristic = (self.isApplicationMode('wavefront') || self.isGaussianBeam())
            ? self.singleElectronCharacteristicEnum
            : self.originalCharacteristicEnum;
    });

    self.getReportTitle = beamlineService.getReportTitle;
    return self;
});


SIREPO.app.controller('SRWBeamlineController', function (appState, beamlineService, panelState, requestSender, srwService, $scope, simulationQueue) {
    var self = this;
    self.appState = appState;
    self.beamlineService = beamlineService;
    self.srwService = srwService;
    self.postPropagation = [];
    self.propagations = [];
    self.analyticalTreatmentEnum = SIREPO.APP_SCHEMA.enum.AnalyticalTreatment;
    self.singleElectron = true;
    self.beamlineModels = ['beamline', 'propagation', 'postPropagation'];
    self.toolbarItemNames = ['aperture', 'obstacle', 'mask', 'fiber', 'crystal', 'grating', 'lens', 'crl', 'mirror', 'sphericalMirror', 'ellipsoidMirror', 'watch', 'sample'];

    function defaultItemPropagationParams() {
        return [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0];
    }

    function defaultDriftPropagationParams() {
        return [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0];
    }

    function formatFloat(v) {
        var str = v.toFixed(4);
        str = str.replace(/0+$/, '');
        str = str.replace(/\.$/, '');
        return str;
    }

    function isPropagationModelName(name) {
        return name.toLowerCase().indexOf('propagation') >= 0;
    }

    function updatePhotonEnergyHelpText() {
        if (appState.isLoaded()) {
            var msg = 'The photon energy is: ' + appState.models.simulation.photonEnergy + ' eV';
            SIREPO.APP_SCHEMA.model.crl.refractiveIndex[3] = msg;
            SIREPO.APP_SCHEMA.model.crl.attenuationLength[3] = msg;
            SIREPO.APP_SCHEMA.model.mask.refractiveIndex[3] = msg;
            SIREPO.APP_SCHEMA.model.mask.attenuationLength[3] = msg;
            SIREPO.APP_SCHEMA.model.fiber.externalRefractiveIndex[3] = msg;
            SIREPO.APP_SCHEMA.model.fiber.externalAttenuationLength[3] = msg;
            SIREPO.APP_SCHEMA.model.fiber.coreRefractiveIndex[3] = msg;
            SIREPO.APP_SCHEMA.model.fiber.coreAttenuationLength[3] = msg;
            SIREPO.APP_SCHEMA.model.sample.refractiveIndex[3] = msg;
            SIREPO.APP_SCHEMA.model.sample.attenuationLength[3] = msg;
        }
    }

    self.handleModalShown = function(name) {
        if (appState.isLoaded()) {
            panelState.showField('watchpointReport', 'fieldUnits', srwService.isGaussianBeam());
            panelState.showField('initialIntensityReport', 'fieldUnits', srwService.isGaussianBeam());
        }
    };

    self.isDisabledPropagation = function(prop) {
        if (prop.item) {
            return prop.item.isDisabled;
        }
        return false;
    };

    self.isPropagationReadOnly = function() {
        return false;
    };

    self.isSingleElectron = function() {
        return self.singleElectron;
    };

    self.isMultiElectron = function() {
        return ! self.isSingleElectron();
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
            if (beamline[i].type != 'watch') {
                self.propagations.push({
                    item: beamline[i],
                    title: beamline[i].title,
                    params: p[0],
                });
            }
            if (i == beamline.length - 1) {
                break;
            }
            var d = parseFloat(beamline[i + 1].position) - parseFloat(beamline[i].position);
            if (d > 0) {
                self.propagations.push({
                    title: 'Drift ' + formatFloat(d) + 'm',
                    params: p[1],
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
    };

    self.setSingleElectron = function(value) {
        value = !!value;
        if (value != self.singleElectron) {
            simulationQueue.cancelAllItems();
        }
        self.singleElectron = value;
    };

    self.showFileReport = function(type, model) {
        self.mirrorReportShown = true;
        appState.models.mirrorReport = model;
        appState.saveQuietly('mirrorReport');
        var el = $('#srw-mirror-plot');
        el.modal('show');
        el.on('shown.bs.modal', function() {
            // this forces the plot to reload
            appState.saveChanges('mirrorReport');
        });
        el.on('hidden.bs.modal', function() {
            self.mirrorReportShown = false;
            el.off();
        });
    };

    self.showPropagationModal = function() {
        self.prepareToSave();
        beamlineService.dismissPopup();
        $('#srw-propagation-parameters').modal('show');
    };

    self.showTabs = function() {
        if (beamlineService.getWatchItems().length === 0) {
            return false;
        }
        if (srwService.isApplicationMode('wavefront')) {
            return false;
        }
        if (srwService.isGaussianBeam()) {
            return false;
        }
        return true;
    };

    $scope.beamlineService = beamlineService;
    $scope.$watch('beamlineService.activeItem.grazingAngle', function (newValue, oldValue) {
        if (newValue !== null && angular.isDefined(newValue) && angular.isDefined(oldValue)) {
            var item = beamlineService.activeItem;
            if (item.type === 'grating' || item.type === 'ellipsoidMirror' || item.type === 'sphericalMirror') {
                requestSender.getApplicationData(
                    {
                        method: 'compute_grazing_angle',
                        optical_element: item,
                    },
                    function(data) {
                        var fields = ['normalVectorZ', 'normalVectorY', 'normalVectorX', 'tangentialVectorY', 'tangentialVectorX'];
                        for (var i = 0; i < fields.length; i++) {
                            item[fields[i]] = data[fields[i]];
                        }
                    }
                );
            }
        }
    });

    function checkChanged(newValues, oldValues) {
        for (var i = 0; i < newValues.length; i++) {
            if (! angular.isDefined(newValues[i]) || newValues[i] === null || newValues[i] === 'Unknown' || ! angular.isDefined(oldValues[i])) {
                return false;
            }
        }
        return true;
    }

    function checkDefined(values) {
        for (var i = 0; i < values.length; i++) {
            if (typeof(values[i]) === 'undefined' || values[i] === null) {
                return false;
            }
        }
        return true;
    }

    function wrapActiveItem(fields) {
        var fieldsList = [];
        for (var i=0; i<fields.length; i++) {
            fieldsList.push('beamlineService.activeItem.' + fields[i].toString());
        }
        return '[' + fieldsList.toString() + ']';
    }

    appState.whenModelsLoaded($scope, updatePhotonEnergyHelpText);
    $scope.$on('simulation.changed', updatePhotonEnergyHelpText);

    var CRLFields = [
        'material',
        'method',
        'numberOfLenses',
        'position',
        'tipRadius',
        'refractiveIndex',
    ];
    function computeCRLCharacteristics() {
        var item = beamlineService.activeItem;
        if (item.type === 'crl') {
            requestSender.getApplicationData(
                {
                    method: 'compute_crl_characteristics',
                    optical_element: item,
                    photon_energy: appState.models.simulation.photonEnergy,
                },
                function(data) {
                    var fields = ['refractiveIndex', 'attenuationLength'];
                    for (var i = 0; i < fields.length; i++) {
                        item[fields[i]] = parseFloat(data[fields[i]]).toExponential(6);
                    }

                    fields = ['focalDistance', 'absoluteFocusPosition'];
                    for (i = 0; i < fields.length; i++) {
                        item[fields[i]] = parseFloat(data[fields[i]]).toFixed(4);
                    }
                }
            );
        }
    }
    $scope.$watchCollection(wrapActiveItem(CRLFields), function (newValues, oldValues) {
        panelState.showField('crl', 'method', newValues[0] != 'User-defined');
        if (checkDefined(newValues)) {
            computeCRLCharacteristics();
        }
    });

    var fiberFields = [
        'method',
        'externalMaterial',
        'coreMaterial',
    ];
    function computeFiberCharacteristics() {
        var item = beamlineService.activeItem;
        if (item.type === 'fiber') {
            requestSender.getApplicationData(
                {
                    method: 'compute_fiber_characteristics',
                    optical_element: item,
                    photon_energy: appState.models.simulation.photonEnergy,
                },
                function(data) {
                    var fields = [
                        'externalRefractiveIndex', 'externalAttenuationLength',
                        'coreRefractiveIndex', 'coreAttenuationLength',
                    ];
                    for (var i = 0; i < fields.length; i++) {
                        item[fields[i]] = parseFloat(data[fields[i]]).toExponential(6);
                    }
                }
            );
        }
    }
    $scope.$watchCollection(wrapActiveItem(fiberFields), function (newValues, oldValues) {
        panelState.showField('fiber', 'method', ! (newValues[1] === 'User-defined' && newValues[2] === 'User-defined'));
        if (checkDefined(newValues)) {
            computeFiberCharacteristics();
        }
    });

    function computeDeltaAttenCharacteristics() {
        var item = beamlineService.activeItem;
        requestSender.getApplicationData(
            {
                method: 'compute_delta_atten_characteristics',
                optical_element: item,
                photon_energy: appState.models.simulation.photonEnergy,
            },
            function(data) {
                var fields = [
                    'refractiveIndex', 'attenuationLength',
                ];
                for (var i = 0; i < fields.length; i++) {
                    item[fields[i]] = parseFloat(data[fields[i]]);
                    if (item[fields[i]] < 1e-3) {
                        item[fields[i]] = item[fields[i]].toExponential(6);
                    }
                    else if (item[fields[i]] === 1) {
                        // pass
                    }
                    else {
                        item[fields[i]] = item[fields[i]].toFixed(6);
                    }
                }
            }
        );
    }
    $scope.$watchCollection(wrapActiveItem(['method', 'material']), function (newValues, oldValues) {
        if (beamlineService.activeItem) {
            var item = beamlineService.activeItem;
            if (item.type === 'mask' || item.type === 'sample') {
                panelState.showField(item.type, 'method', newValues[1] != 'User-defined');
                if (checkDefined(newValues)) {
                    computeDeltaAttenCharacteristics();
                }
            }
        }
    });

    var crystalInitFields = [
        'material',
        'energy',
        'h',
        'k',
        'l',
    ];
    $scope.$watchCollection(wrapActiveItem(crystalInitFields), function (newValues, oldValues) {
        if (checkChanged(newValues, oldValues)) {
            var item = beamlineService.activeItem;
            if (item.type === 'crystal') {
                requestSender.getApplicationData(
                    {
                        method: 'compute_crystal_init',
                        optical_element: item,
                    },
                    function(data) {
                        var fields = ['dSpacing', 'psi0r', 'psi0i', 'psiHr', 'psiHi', 'psiHBr', 'psiHBi', 'grazingAngle'];
                        for (var i = 0; i < fields.length; i++) {
                            item[fields[i]] = data[fields[i]];
                        }
                    }
                );
            }
        }
    });

    var crystalOrientationFields = [
        'grazingAngle',
        'dSpacing',
        'asymmetryAngle',
        'psi0r',
        'psi0i',
        'rotationAngle',
    ];
    $scope.$watchCollection(wrapActiveItem(crystalOrientationFields), function (newValues, oldValues) {
        if (checkChanged(newValues, oldValues)) {
            var item = beamlineService.activeItem;
            if (item.type === 'crystal') {
                requestSender.getApplicationData(
                    {
                        method: 'compute_crystal_orientation',
                        optical_element: item,
                    },
                    function(data) {
                        var fields = ['nvx', 'nvy', 'nvz', 'tvx', 'tvy'];
                        for (var i = 0; i < fields.length; i++) {
                            item[fields[i]] = data[fields[i]];
                        }
                    }
                );
            }
        }
    });
});

SIREPO.app.controller('SRWSourceController', function (appState, panelState, requestSender, srwService, $scope) {
    var self = this;
    var isReadyForInput = false;
    // required for $watch below
    $scope.appState = appState;
    self.srwService = srwService;
    var FORMAT_DECIMALS = 8;

    function isActiveField(model, field) {
        var fieldClass = '.model-' + model + '-' + field;
        return $(fieldClass).find('input').is(':focus');
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
        return res.toFixed(6);
    }

    function disableBasicEditorBeamName() {
        $('#sr-electronBeam-basicEditor .model-electronBeam-name input').prop('readonly', true);
    }

    function formatFloat(v) {
        return +parseFloat(v).toFixed(FORMAT_DECIMALS);
    }

    function isAutoDrift() {
        if (isReadyForInput) {
            return appState.models.electronBeamPosition.driftCalculationMethod === 'auto';
        }
        return false;
    }

    function isTwissDefinition() {
        if (isReadyForInput) {
            return appState.models.electronBeam.beamDefinition === 't';
        }
        return false;
    }

    function processBeamFields() {
        var isPredefinedBeam = srwService.isPredefinedBeam();
        var ebeam = appState.models.electronBeam;
        // enable/disable beam fields
        for (var f in ebeam) {
            panelState.enableField('electronBeam', f, ! isPredefinedBeam);
        }
        disableBasicEditorBeamName();
        // show/hide column headings and input fields for the twiss/moments sections
        panelState.showRow('electronBeam', 'horizontalEmittance', isTwissDefinition());
        panelState.showRow('electronBeam', 'rmsSizeX', ! isTwissDefinition());
        panelState.enableField('electronBeamPosition', 'drift', ! isAutoDrift());
    }

    function processBeamParameters() {
        requestSender.getApplicationData(
            {
                method: 'process_beam_parameters',
                source_type: appState.models.simulation.sourceType,
                undulator_type: appState.models.tabulatedUndulator.undulatorType,
                undulator_period: appState.models.undulator.period / 1000,
                undulator_length: appState.models.undulator.length,
                ebeam: appState.clone(appState.models.electronBeam),
                ebeam_position: appState.clone(appState.models.electronBeamPosition),
            },
            function(data) {
                if (! appState.isLoaded()) {
                    return;
                }
                var ebeam = appState.models.electronBeam;
                ['rmsSizeX', 'rmsDivergX', 'xxprX', 'rmsSizeY', 'rmsDivergY', 'xxprY'].forEach(function(f) {
                    ebeam[f] = formatFloat(data[f]);
                });
                appState.models.electronBeamPosition.drift = data.drift;
            }
        );
    }

    function processFluxAnimation() {
        panelState.enableField('fluxAnimation', 'magneticField', srwService.isTabulatedUndulatorWithMagenticFile());
        if (! srwService.isTabulatedUndulatorWithMagenticFile()) {
            appState.models.fluxAnimation.magneticField = 1;
        }
        // ["-1", "Use Approximate Method"]
        var isApproximateMethod = appState.models.fluxAnimation.method == -1;
        ['initialHarmonic', 'finalHarmonic', 'longitudinalPrecision', 'azimuthalPrecision'].forEach(function(f) {
            panelState.showField('fluxAnimation', f, isApproximateMethod);
        });
        ['precision', 'numberOfMacroElectrons'].forEach(function(f) {
            panelState.showField('fluxAnimation', f, ! isApproximateMethod);
        });
    }

    function processGaussianBeamSize() {
        var energy = appState.models.simulation.photonEnergy;
        var isWaist = appState.models.gaussianBeam.sizeDefinition == 1;
        panelState.enableField('gaussianBeam', 'rmsSizeX', isWaist);
        panelState.enableField('gaussianBeam', 'rmsSizeY', isWaist);
        panelState.enableField('gaussianBeam', 'rmsDivergenceX', ! isWaist);
        panelState.enableField('gaussianBeam', 'rmsDivergenceY', ! isWaist);

        if (isWaist) {
            appState.models.gaussianBeam.rmsDivergenceX = convertGBSize('rmsSizeX', energy);
            appState.models.gaussianBeam.rmsDivergenceY = convertGBSize('rmsSizeY', energy);
        }
        else {
            appState.models.gaussianBeam.rmsSizeX = convertGBSize('rmsDivergenceX', energy);
            appState.models.gaussianBeam.rmsSizeY = convertGBSize('rmsDivergenceY', energy);
        }
    }

    function processIntensityReport(reportName) {
        panelState.showField(reportName, 'fieldUnits', srwService.isGaussianBeam());
        updatePrecisionLabel();
        requestSender.getApplicationData(
            {
                method: 'process_intensity_reports',
                source_type: appState.models.simulation.sourceType,
                undulator_type: appState.models.tabulatedUndulator.undulatorType,
            },
            function(data) {
                if (! appState.isLoaded()) {
                    return;
                }
                appState.models[reportName].magneticField = data.magneticField;
                panelState.enableField(reportName, 'magneticField', false);
            }
        );
    }

    function processTrajectoryReport() {
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

        if (! srwService.isTabulatedUndulatorWithMagenticFile()) {
            appState.models.trajectoryReport.magneticField = 1;
            panelState.enableField('trajectoryReport', 'magneticField', false);
        }
    }

    function processUndulator() {
        panelState.showRow('undulator', 'horizontalAmplitude', ! srwService.isTabulatedUndulatorWithMagenticFile());
        ['undulatorParameter', 'period', 'length'].forEach(function(f) {
            panelState.showField('undulator', f, ! srwService.isTabulatedUndulatorWithMagenticFile());
        });
        ['gap', 'phase', 'magneticFile', 'indexFileName'].forEach(function(f) {
            panelState.showField('tabulatedUndulator', f, srwService.isTabulatedUndulatorWithMagenticFile());
        });
        // Always hide some fields in the calculator mode:
        if (srwService.isApplicationMode('calculator')) {
            ['longitudinalPosition', 'horizontalSymmetry', 'verticalSymmetry'].forEach(function(f) {
                panelState.showField('undulator', f, false);
            });
        }
    }

    function processUndulatorDefinition(undulatorDefinition) {
        if (! (srwService.isIdealizedUndulator() || srwService.isTabulatedUndulator())) {
            return;
        }
        requestSender.getApplicationData(
            {
                method: 'process_undulator_definition',
                undulator_definition: undulatorDefinition,
                undulator_parameter: appState.models.undulator.undulatorParameter,
                vertical_amplitude: appState.models.undulator.verticalAmplitude,
                undulator_period: appState.models.undulator.period / 1000,
            },
            function(data) {
                if (! appState.isLoaded()) {
                    return;
                }
                if (undulatorDefinition === 'K') {
                    appState.models.undulator.verticalAmplitude = formatFloat(data.vertical_amplitude);
                }
                else {
                    appState.models.undulator.undulatorParameter = formatFloat(data.undulator_parameter);
                }
            }
        );
    }

    function updatePrecisionLabel() {
        if (srwService.isElectronBeam()) {
            var precisionLabel = SIREPO.APP_SCHEMA.model.intensityReport.precision[0];
            if (appState.models.intensityReport.method === "0") {
                precisionLabel = 'Step Size';
            }
            $('.model-intensityReport-precision').find('label').text(precisionLabel);
        }
    }

    function watchModelFields(modelFields, callback) {
        modelFields.forEach(function(f) {
            $scope.$watch('appState.models.' + f, function (newValue, oldValue) {
                if (isReadyForInput && newValue != oldValue) {
                    callback();
                }
            });
        });
    }

    self.handleModalShown = function(name) {
        if (! isReadyForInput) {
            return;
        }
        if (name === 'fluxAnimation') {
            processFluxAnimation();
        }
        else if (name === 'intensityReport') {
            processIntensityReport(name);
        }
        else if (name === 'sourceIntensityReport') {
            panelState.showField(name, 'magneticField', ! srwService.isApplicationMode('calculator'));
            processIntensityReport(name);
            srwService.updateSimulationGridFields();
        }
        else if (name === 'trajectoryReport') {
            processTrajectoryReport();
        }
        else if (name === 'electronBeam') {
            processBeamFields();
        }
    };

    $scope.$on('modelChanged', function(e, name) {
        if (name == 'simulation') {
            processUndulator();
        }
        else if (name == 'undulator' || name == 'tabulatedUndulator') {
            // make sure the electronBeam.drift is also updated
            appState.saveQuietly('electronBeamPosition');
        }
    });

    watchModelFields(['electronBeam.beamSelector', 'electronBeam.beamDefinition'], processBeamFields);

    watchModelFields(['electronBeam.name'], function() {
        // keep beamSelector in sync with name
        appState.models.electronBeam.beamSelector = appState.models.electronBeam.name;
    });
    watchModelFields(['tabulatedUndulator.name'], function() {
        // keep undulatorSelector in sync with name
        appState.models.tabulatedUndulator.undulatorSelector = appState.models.tabulatedUndulator.name;
    });

    watchModelFields(['electronBeamPosition.driftCalculationMethod'], function() {
        processBeamParameters();
        processBeamFields();
    });

    watchModelFields(['electronBeam.horizontalEmittance', 'electronBeam.horizontalBeta', 'electronBeam.horizontalAlpha', 'electronBeam.horizontalDispersion', 'electronBeam.horizontalDispersionDerivative', 'electronBeam.verticalEmittance', 'electronBeam.verticalBeta', 'electronBeam.verticalAlpha', 'electronBeam.verticalDispersion', 'electronBeam.verticalDispersionDerivative'], processBeamParameters);

    function changeFluxReportName(modelName) {
        var tag = $($("div[data-model-name='" + modelName + "']").find('.sr-panel-heading')[0]);
        // var distance = tag.text().split(',')[1];
        var distance = appState.models[modelName].distanceFromSource + 'm';
        var fluxType = SIREPO.APP_SCHEMA.enum.Flux[appState.models[modelName].fluxType-1][1];
        var title = SIREPO.APP_SCHEMA.view[modelName].title;
        var repName;
        if (fluxType !== 'Flux') {
            repName = title.replace(
                'Flux',
                fluxType
            ) + ' for Finite Emittance Electron Beam';
        } else {
            repName = title + ' Report';
        }
        repName += ', ' + distance;
        tag.text(repName);
    }

    ['fluxReport', 'fluxAnimation'].forEach(function(f) {
        watchModelFields([f + '.fluxType', f + '.distanceFromSource'], function() {
            changeFluxReportName(f);
        });
    });

    watchModelFields(['fluxAnimation.method'], processFluxAnimation);

    watchModelFields(['gaussianBeam.sizeDefinition', 'gaussianBeam.rmsSizeX', 'gaussianBeam.rmsSizeY', 'gaussianBeam.rmsDivergenceX', 'gaussianBeam.rmsDivergenceY', 'simulation.photonEnergy'], function() {
        if (srwService.isGaussianBeam()) {
            processGaussianBeamSize();
        }
    });

    watchModelFields(['intensityReport.method'], updatePrecisionLabel);

    watchModelFields(['tabulatedUndulator.undulatorType', 'undulator.length', 'undulator.period', 'simulation.sourceType'], processBeamParameters);

    watchModelFields(['tabulatedUndulator.undulatorType'], processUndulator);

    watchModelFields(['tabulatedUndulator.magneticFile'], function() {
        requestSender.getApplicationData(
            {
                method: 'compute_undulator_length',
                tabulated_undulator: appState.models.tabulatedUndulator,
            },
            function(data) {
                if (! appState.isLoaded()) {
                    return;
                }
                appState.models.tabulatedUndulator.length = data.length;
            }
        );
    });

    watchModelFields(['trajectoryReport.timeMomentEstimation'], function() {
        processTrajectoryReport();
    });

    watchModelFields(['undulator.undulatorParameter'], function() {
        if (isActiveField('undulator', 'undulatorParameter')) {
            processUndulatorDefinition('K');
        }
    });

    watchModelFields(['undulator.verticalAmplitude', 'undulator.period'], function() {
        if (! isActiveField('undulator', 'undulatorParameter')) {
            processUndulatorDefinition('B');
        }
    });

    appState.whenModelsLoaded($scope, function() {
        //TODO(pjm): move isReadyForInput to panelState
        isReadyForInput = true;
        changeFluxReportName('fluxReport');
        changeFluxReportName('fluxAnimation');
        disableBasicEditorBeamName();
        processUndulator();
        processGaussianBeamSize();
    });
});

SIREPO.app.directive('appFooter', function(appState, srwService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-delete-simulation-modal="nav"></div>',
            '<div data-reset-simulation-modal="nav"></div>',
            '<div data-modal-editor="" view-name="simulationGrid" data-parent-controller="nav"></div>',
            '<div data-modal-editor="" view-name="simulationDocumentation"></div>',
            '<div data-import-python=""></div>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
            // hook for sampling method changes
            $scope.nav.handleModalShown = srwService.updateSimulationGridFields;
            $scope.$watch('appState.models.simulation.samplingMethod', srwService.updateSimulationGridFields);
            $scope.$watch('appState.models.sourceIntensityReport.samplingMethod', srwService.updateSimulationGridFields);
        },
    };
});

SIREPO.app.directive('appHeader', function(appState, panelState, requestSender, srwService, $location, $window) {

    var settingsIcon = [
        '<li class="dropdown"><a href class="dropdown-toggle hidden-xs" data-toggle="dropdown"><span class="glyphicon glyphicon-cog"></span> <span class="caret"></span></a>',
          '<ul class="dropdown-menu">',
            '<li data-ng-if="! srwService.isApplicationMode(\'calculator\') && nav.isActive(\'beamline\')"><a href data-ng-click="showSimulationGrid()"><span class="glyphicon glyphicon-th"></span> Initial Wavefront Simulation Grid</a></li>',
            '<li data-ng-if="srwService.isApplicationMode(\'default\')"><a href data-ng-click="showDocumentationUrl()"><span class="glyphicon glyphicon-book"></span> Simulation Documentation URL</a></li>',
            '<li><a href data-ng-click="jsonDataFile()"><span class="glyphicon glyphicon-cloud-download"></span> Export JSON Data File</a></li>',
            '<li data-ng-if="canCopy()"><a href data-ng-click="copy()"><span class="glyphicon glyphicon-copy"></span> Open as a New Copy</a></li>',
            '<li data-ng-if="isExample()"><a href data-target="#srw-reset-confirmation" data-toggle="modal"><span class="glyphicon glyphicon-repeat"></span> Discard Changes to Example</a></li>',
            '<li data-ng-if="! isExample()"><a href data-target="#srw-delete-confirmation" data-toggle="modal""><span class="glyphicon glyphicon-trash"></span> Delete</a></li>',
            '<li data-ng-if="hasRelatedSimulations()" class="divider"></li>',
            '<li data-ng-if="hasRelatedSimulations()" class="sr-dropdown-submenu">',
              '<a href><span class="glyphicon glyphicon-chevron-left"></span> Related Simulations</a>',
        '<ul class="dropdown-menu">',
        '<li data-ng-repeat="item in relatedSimulations"><a href data-ng-click="openRelatedSimulation(item)">{{ item.name }}</a></li>',
        '</ul>',
            '</li>',
          '</ul>',
        '</li>',
    ].join('');

    var rightNav = [
        '<ul class="nav navbar-nav navbar-right" data-login-menu="" data-ng-if="srwService.isApplicationMode(\'default\')"></ul>',
        '<ul class="nav navbar-nav navbar-right" data-ng-show="nav.isActive(\'simulations\') && ! srwService.isApplicationMode(\'light-sources\')">',
          '<li><a href data-ng-click="showSimulationModal()"><span class="glyphicon glyphicon-plus sr-small-icon"></span><span class="glyphicon glyphicon-file"></span> New Simulation</a></li>',
          '<li><a href data-ng-click="showNewFolderModal()"><span class="glyphicon glyphicon-plus sr-small-icon"></span><span class="glyphicon glyphicon-folder-close"></span> New Folder</a></li>',
          '<li><a href data-ng-click="showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>',
        '</ul>',
        '<ul class="nav navbar-nav navbar-right" data-ng-show="isLoaded()">',
          '<li data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
          '<li data-ng-class="{active: nav.isActive(\'beamline\')}"><a href data-ng-click="nav.openSection(\'beamline\')"><span class="glyphicon glyphicon-option-horizontal"></span> Beamline</a></li>',
          '<li data-ng-if="hasDocumentationUrl()"><a href data-ng-click="openDocumentation()"><span class="glyphicon glyphicon-book"></span> Notes</a></li>',
          settingsIcon,
        '</ul>',
    ].join('');

    function navHeader(mode, modeTitle, $window) {
        return [
            '<div class="navbar-header">',
              '<a class="navbar-brand" href="/#about"><img style="width: 40px; margin-top: -10px;" src="/static/img/radtrack.gif" alt="radiasoft"></a>',
              '<div class="navbar-brand"><a href="/light">Synchrotron Radiation Workshop</a>',
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
        template: [
            '<div data-ng-if="srwService.isApplicationMode(\'calculator\')">',
              navHeader('calculator', 'SR Calculator'),
              '<ul data-ng-if="isLoaded()" class="nav navbar-nav navbar-right">',
                settingsIcon,
              '</ul>',
              '<ul class="nav navbar-nav navbar-right" data-ng-show="isLoaded()">',
                '<li data-ng-if="hasDocumentationUrl()"><a href data-ng-click="openDocumentation()"><span class="glyphicon glyphicon-book"></span> Notes</a></li>',
              '</ul>',
            '</div>',
            '<div data-ng-if="srwService.isApplicationMode(\'wavefront\')">',
              navHeader('wavefront', 'Wavefront Propagation'),
              rightNav,
            '</div>',
            '<div data-ng-if="srwService.isApplicationMode(\'light-sources\')">',
              navHeader('light-sources', 'Light Source Facilities'),
              rightNav,
            '</div>',
            '<div data-ng-if="srwService.isApplicationMode(\'default\')">',
              '<div class="navbar-header">',
                '<a class="navbar-brand" href="/#about"><img style="width: 40px; margin-top: -10px;" src="/static/img/radtrack.gif" alt="radiasoft"></a>',
                '<div class="navbar-brand"><a href="/light">Synchrotron Radiation Workshop</a></div>',
              '</div>',
              '<div class="navbar-left" data-app-header-left="nav"></div>',
              rightNav,
            '</div>',
        ].join(''),
        controller: function($scope) {
            var currentSimulationId = null;

            function simulationId() {
                return appState.models.simulation.simulationId;
            }

            $scope.srwService = srwService;
            $scope.relatedSimulations = [];

            $scope.canCopy = function() {
                if (srwService.applicationMode == 'calculator' || srwService.applicationMode == 'wavefront') {
                    return false;
                }
                return true;
            };

            $scope.copy = function() {
                appState.copySimulation(
                    simulationId(),
                    function(data) {
                        requestSender.localRedirect('source', {
                            ':simulationId': data.models.simulation.simulationId,
                        });
                    });
            };

            $scope.jsonDataFile = function(item) {
                $window.open(requestSender.formatUrl('simulationData', {
                    '<simulation_id>': simulationId(),
                    '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                    '<pretty>': true,
                }), '_blank');
            };

            $scope.hasDocumentationUrl = function() {
                if (appState.isLoaded()) {
                    return appState.models.simulation.documentationUrl;
                }
                return false;
            };

            $scope.hasRelatedSimulations = function() {
                if (appState.isLoaded()) {
                    if (currentSimulationId == appState.models.simulation.simulationId) {
                        return $scope.relatedSimulations.length > 0;
                    }
                    currentSimulationId = appState.models.simulation.simulationId;
                    requestSender.sendRequest(
                        'listSimulations',
                        function(data) {
                            for (var i = 0; i < data.length; i++) {
                                var item = data[i];
                                if (item.simulationId == currentSimulationId) {
                                    data.splice(i, 1);
                                    break;
                                }
                            }
                            $scope.relatedSimulations = data;
                        },
                        {
                            simulationType: SIREPO.APP_SCHEMA.simulationType,
                            search: {
                                'simulation.folder': appState.models.simulation.folder,
                            },
                        });
                }
                return false;
            };

            $scope.isExample = function() {
                if (appState.isLoaded()) {
                    return appState.models.simulation.isExample;
                }
                return false;
            };

            $scope.isLoaded = function() {
                if ($scope.nav.isActive('simulations')) {
                    return false;
                }
                return appState.isLoaded();
            };

            $scope.openDocumentation = function() {
                $window.open(appState.models.simulation.documentationUrl, '_blank');
            };

            $scope.openRelatedSimulation = function(item) {
                if ($scope.nav.isActive('beamline')) {
                    requestSender.localRedirect('beamline', {
                        ':simulationId': item.simulationId,
                    });
                    return;
                }
                requestSender.localRedirect('source', {
                    ':simulationId': item.simulationId,
                });
            };

            $scope.showImportModal = function() {
                $('#srw-simulation-import').modal('show');
            };

            $scope.showNewFolderModal = function() {
                panelState.showModalEditor('simulationFolder');
            };

            $scope.showSimulationModal = function() {
                panelState.showModalEditor('simulation');
            };

            $scope.showDocumentationUrl = function() {
                panelState.showModalEditor('simulationDocumentation');
            };

            $scope.showSimulationGrid = function() {
                panelState.showModalEditor('simulationGrid');
            };
        },
    };
});

SIREPO.app.directive('deleteSimulationModal', function(appState, $location) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div data-confirmation-modal="" data-id="srw-delete-confirmation" data-title="Delete Simulation?" data-ok-text="Delete" data-ok-clicked="deleteSimulation()">Delete simulation &quot;{{ simulationName() }}&quot;?</div>',
        ].join(''),
        controller: function($scope) {
            $scope.deleteSimulation = function() {
                appState.deleteSimulation(
                    appState.models.simulation.simulationId,
                    function() {
                        $location.path('/simulations');
                    });
            };
            $scope.simulationName = function() {
                if (appState.isLoaded()) {
                    return appState.models.simulation.name;
                }
                return '';
            };
        },
    };
});

//TODO(pjm): refactor and generalize with mirrorUpload
SIREPO.app.directive('importPython', function(appState, fileUpload, requestSender) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div class="modal fade" id="srw-simulation-import" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<div data-help-button="{{ title }}"></div>',
                    '<span class="lead modal-title text-info">{{ title }}</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<form name="importForm">',
                        '<div class="form-group">',
                          '<label>Select File</label>',
                          '<input id="srw-python-file-import" type="file" data-file-model="pythonFile">',
                          '<div data-ng-if="fileType(pythonFile)"></div>',
                          '<br />',
                          '<div class="srw-python-file-import-args"><label>Optional arguments:</label><input type="text" style="width: 100%" data-ng-model="importArgs"></div><br>',
                          '<div class="text-warning"><strong>{{ fileUploadError }}</strong></div>',
                        '</div>',
                        '<div data-ng-if="isUploading" class="col-sm-6 pull-right">Please Wait...</div>',
                        '<div class="clearfix"></div>',
                        '<div class="col-sm-6 pull-right">',
                          '<button data-ng-click="importPythonFile(pythonFile, importArgs)" class="btn btn-primary" data-ng-class="{\'disabled\': isUploading}">Import File</button>',
                          ' <button data-dismiss="modal" class="btn btn-default" data-ng-class="{\'disabled\': isUploading}">Cancel</button>',
                        '</div>',
                      '</form>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.fileUploadError = '';
            $scope.isUploading = false;
            $scope.title = 'Import Python or JSON Simulation File';
            var import_args = $('.srw-python-file-import-args');
            import_args.hide();
            $scope.fileType = function(pythonFile) {
                if (typeof(pythonFile) === 'undefined') {
                    return;
                }
                if (pythonFile.name.search('.py') >= 0) {
                    import_args.show();
                }
                else {
                    import_args.hide();
                }
            };
            $scope.importPythonFile = function(pythonFile, importArgs) {
                if (typeof(importArgs) === 'undefined') {
                    importArgs = '';
                }
                if (! pythonFile) {
                    return;
                }
                $scope.isUploading = true;
                fileUpload.uploadFileToUrl(
                    pythonFile,
                    {
                        folder: appState.getActiveFolderPath(),
                        arguments: importArgs,
                    },
                    requestSender.formatUrl(
                        'importFile',
                        {
                            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        }),
                    function(data) {
                        $scope.isUploading = false;
                        if (data.error) {
                            $scope.fileUploadError = data.error;
                        }
                        else {
                            $('#srw-simulation-import').modal('hide');
                            requestSender.localRedirect('source', {
                                ':simulationId': data.models.simulation.simulationId,
                            });
                        }
                    });
            };
        },
        link: function(scope, element) {
            $(element).on('show.bs.modal', function() {
                $('#srw-python-file-import').val(null);
                scope.fileUploadError = '';
            });
            scope.$on('$destroy', function() {
                $(element).off();
            });
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
        template: [
            mobileTitle('calculator', 'SR Calculator'),
            mobileTitle('wavefront', 'Wavefront Propagation'),
            mobileTitle('light-sources', 'Light Source Facilities'),
        ].join(''),
        controller: function($scope) {
            $scope.srwService = srwService;
        },
    };
});

SIREPO.app.directive('modelSelectionList', function(appState, requestSender) {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            model: '=',
            field: '=',
            fieldClass: '=',
        },
        template: [
            '<div class="dropdown" data-ng-class="fieldClass">',
              '<button style="display: inline-block" class="btn btn-default dropdown-toggle form-control" type="button" data-toggle="dropdown">{{ model[field] }} <span class="caret"></span></button>',
              '<ul class="dropdown-menu" style="margin-left: 15px">',
                '<li data-ng-if="isElectronBeam()" class="dropdown-header">Predefined Electron Beams</li>',
                '<li data-ng-repeat="item in modelList | orderBy:\'name\' track by item.name">',
                  '<a href data-ng-click="selectItem(item)">{{ item.name }}</a>',
                '</li>',
                '<li data-ng-if="isElectronBeam() && userModelList.length" class="divider"></li>',
                '<li data-ng-if="isElectronBeam() && userModelList.length" class="dropdown-header">User Defined Electron Beams</li>',
                '<li data-ng-repeat="item in userModelList | orderBy:\'name\' track by item.id" class="sr-model-list-item">',
                  '<a href data-ng-click="selectItem(item)">{{ item.name }}<span data-ng-show="! isSelectedItem(item)" data-ng-click="deleteItem(item, $event)" class="glyphicon glyphicon-remove"></span></a>',
                '</li>',
                '<li data-ng-if="! isElectronBeam() && userModelList.length" class="divider"></li>',
                '<li><a href data-ng-if="! isElectronBeam()" data-ng-click="addNewUndulator()"><span class="glyphicon glyphicon-plus"></span> Add New</a></li>',
              '</ul>',
            '</div>',
            '<div class="col-sm-2" data-ng-if="model.isReadOnly">',
              '<div class="form-control-static"><a href data-ng-click="editItem()">Edit Beam</a></div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;

            function newModelId() {
                return appState.uniqueName($scope.userModelList, 'id', appState.models.simulation.simulationId + ' {}');
            }

            $scope.addNewUndulator = function() {
                ['tabulatedUndulator', 'undulator'].forEach(function(name) {
                    appState.models[name] = appState.clone(appState.models[name]);
                });
                appState.models.tabulatedUndulator.id = newModelId();
                appState.models.tabulatedUndulator.name = '';
                appState.models.undulatorSelector = '';
                //TODO(pjm): add panelState.setFocus(model, field)
                $('.model-tabulatedUndulator-name .form-control').first().select();
            };
            $scope.editItem = function() {
                // copy the current model, rename and show editor
                var newModel = appState.clone(appState.models[$scope.modelName]);
                delete newModel.isReadOnly;
                newModel.name = appState.uniqueName($scope.userModelList, 'name', newModel.name + ' (copy {})');
                if ($scope.isElectronBeam()) {
                    newModel.beamSelector = newModel.name;
                }
                else {
                    newModel.undulatorSelector = newModel.name;
                }
                newModel.id = newModelId();
                appState.models[$scope.modelName] = newModel;
            };
            $scope.deleteItem = function(item, $event) {
                $event.stopPropagation();
                $event.preventDefault();
                requestSender.getApplicationData(
                    {
                        method: 'delete_user_models',
                        electron_beam: $scope.isElectronBeam() ? item : null,
                        tabulated_undulator: $scope.isElectronBeam() ? null : item,
                    },
                    $scope.loadModelList);
            };
            $scope.isElectronBeam = function() {
                return $scope.modelName == 'electronBeam';
            };
            $scope.isSelectedItem = function(item) {
                return item.id == appState.models[$scope.modelName].id;
            };
            $scope.loadModelList = function() {
                requestSender.getApplicationData(
                    {
                        method: 'model_list',
                        model_name: $scope.modelName,
                        methodSignature: 'model_list ' + $scope.modelName,
                    },
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
                if (! $scope.isElectronBeam()) {
                    appState.models.undulator = item.undulator;
                }
            };
        },
        link: function link(scope, element) {
            scope.loadModelList();
            scope.$on('modelChanged', function(e, name) {
                if (name != scope.modelName) {
                    return;
                }
                var model = appState.models[scope.modelName];
                if (model.isReadOnly) {
                    return;
                }
                var foundIt = false;
                model = appState.clone(model);
                if (! scope.isElectronBeam()) {
                    model.undulator = appState.clone(appState.models.undulator);
                }
                for (var i = 0; i < scope.userModelList.length; i++) {
                    if (scope.userModelList[i].id == model.id) {
                        scope.userModelList[i] = model;
                        foundIt = true;
                        break;
                    }
                }
                if (! foundIt) {
                    scope.userModelList.push(model);
                }
            });
        },
    };
});

SIREPO.app.directive('resetSimulationModal', function(appState, requestSender, srwService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=resetSimulationModal',
        },
        template: [
            '<div data-confirmation-modal="" data-id="srw-reset-confirmation" data-title="Reset Simulation?" data-ok-text="Discard Changes" data-ok-clicked="revertToOriginal()">Discard changes to &quot;{{ simulationName() }}&quot;?</div>',
        ].join(''),
        controller: function($scope) {
            function revertSimulation() {
                $scope.nav.revertToOriginal(
                    srwService.applicationMode,
                    appState.models.simulation.name);
            }

            $scope.revertToOriginal = function() {
                // delete the user-defined models first
                requestSender.getApplicationData(
                    {
                        method: 'delete_user_models',
                        electron_beam: appState.models.electronBeam,
                        tabulated_undulator: appState.models.tabulatedUndulator,
                    },
                    revertSimulation);
            };
            $scope.simulationName = function() {
                if (appState.isLoaded()) {
                    return appState.models.simulation.name;
                }
                return '';
            };
        },
    };
});

SIREPO.app.directive('simulationStatusPanel', function(frameCache, persistentSimulation) {
    return {
        restrict: 'A',
        scope: {
            model: '@simulationStatusPanel',
            title: '@',
        },
        template: [
            '<form name="form" class="form-horizontal" novalidate>',
              '<div class="progress" data-ng-if="isStateProcessing()">',
                '<div class="progress-bar" data-ng-class="{ \'progress-bar-striped active\': isInitializing() }" role="progressbar" aria-valuenow="{{ displayPercentComplete() }}" aria-valuemin="0" aria-valuemax="100" data-ng-attr-style="width: {{ displayPercentComplete() }}%"></div>',
              '</div>',

              '<div data-ng-if="isStateProcessing()">',
                '<div class="col-sm-6">',
                  '<div data-ng-show="isStatePending()">',
                    '<span class="glyphicon glyphicon-hourglass"></span> {{ stateAsText() }} {{ dots }}',
                  '</div>',
                  '<div data-ng-show="isInitializing()">',
                    '<span class="glyphicon glyphicon-hourglass"></span> Initializing Simulation {{ dots }}',
                  '</div>',
                  '<div data-ng-show="isStateRunning() && ! isInitializing()">',
                    '{{ stateAsText() }} {{ dots }}',
                    '<div data-ng-show="! isStatePending() && particleNumber">',
                      'Completed particle: {{ particleNumber }} / {{ particleCount}}',
                    '</div>',
                    '<div data-simulation-status-timer="timeData"></div>',
                  '</div>',
                '</div>',
                '<div class="col-sm-6 pull-right">',
                  '<button class="btn btn-default" data-ng-click="cancelSimulation()">End Simulation</button>',
                '</div>',
              '</div>',
              '<div data-ng-show="isStateStopped()">',
                '<div class="col-sm-6">',
                  'Simulation ',
                  '<span>{{ stateAsText() }}</span>',
                  '<div data-ng-show="! isStatePending() && ! isInitializing() && particleNumber">',
                    'Completed particle: {{ particleNumber }} / {{ particleCount}}',
                  '</div>',
                  '<div>',
                    '<div data-simulation-status-timer="timeData"></div>',
                  '</div>',
                '</div>',
                '<div class="col-sm-6 pull-right">',
                  '<button class="btn btn-default" data-ng-click="runSimulation()">Start New Simulation</button>',
                '</div>',
              '</div>',
            '</form>',
        ].join(''),
        controller: function($scope) {
            $scope.handleStatus = function(data) {
                if (data.percentComplete) {
                    $scope.particleNumber = data.particleNumber;
                    $scope.particleCount = data.particleCount;
                }
                if (data.frameId && (data.frameId != $scope.frameId)) {
                    $scope.frameId = data.frameId;
                    $scope.frameCount++;
                    frameCache.setFrameCount($scope.frameCount);
                    frameCache.setCurrentFrame($scope.model, $scope.frameCount - 1);
                }
            };

            persistentSimulation.initProperties($scope, $scope, {
                multiElectronAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1'],
                fluxAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'fluxType'],
            });
            $scope.$on($scope.model + '.changed', function() {
                if ($scope.isReadyForModelChanges) {
                    $scope.cancelSimulation();
                    frameCache.setFrameCount(0);
                    frameCache.clearFrames($scope.model);
                    $scope.percentComplete = 0;
                    $scope.particleNumber = 0;
                }
            });
        },
    };
});

SIREPO.app.directive('tooltipEnabler', function() {
    return {
        link: function(scope, element) {
            $('[data-toggle="tooltip"]').tooltip({
                html: true,
                placement: 'bottom',
            });
            scope.$on('$destroy', function() {
                $('[data-toggle="tooltip"]').tooltip('destroy');
            });
        },
    };
});
