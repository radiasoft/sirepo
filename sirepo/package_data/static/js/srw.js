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
SIREPO.appDownloadLinks = [
    '<li data-lineout-csv-link="x"></li>',
    '<li data-lineout-csv-link="y"></li>',
    '<li data-export-python-link=""></li>',
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

SIREPO.app.factory('srwService', function(appState, appDataService, beamlineService, panelState, $rootScope, $location) {
    var self = {};
    self.applicationMode = 'default';
    self.originalCharacteristicEnum = null;
    self.singleElectronCharacteristicEnum = null;

    // override appDataService functions
    appDataService.getApplicationMode = function () {
        return self.applicationMode;
    };
    appDataService.appDataForReset = function() {
        // delete the user-defined models first
         return {
             method: 'delete_user_models',
             electron_beam: appState.models.electronBeam,
             tabulated_undulator: appState.models.tabulatedUndulator,
         };
    };
    appDataService.canCopy = function() {
        if (self.applicationMode == 'calculator' || self.applicationMode == 'wavefront') {
            return false;
        }
        return true;
    };

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
        // Always show the distance, so commenting it out:
        // panelState.showField('simulation', 'distanceFromSource', appState.models.beamline.length === 0);
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

    self.getReportTitle = function(modelName, itemId) {
        if (modelName == 'multiElectronAnimation') {
            // multiElectronAnimation title is cached on the simulation model
            var title = appState.models.simulation.multiElectronAnimationTitle;
            if (title) {
                return title;
            }
        }
        return beamlineService.getReportTitle(modelName, itemId);
    };
    return self;
});


SIREPO.app.controller('SRWBeamlineController', function (appState, beamlineService, panelState, requestSender, srwService, $scope, simulationQueue) {
    var self = this;
    self.appState = appState;
    self.beamlineService = beamlineService;
    self.srwService = srwService;
    self.postPropagation = [];
    self.propagations = [];
    self.singleElectron = true;
    self.beamlineModels = ['beamline', 'propagation', 'postPropagation'];
    self.toolbarItemNames = [
        ['Refractive optics and transmission objects', ['lens', 'crl', 'fiber', 'aperture', 'obstacle', 'mask', 'sample']],
        ['Mirrors', ['mirror', 'sphericalMirror', 'ellipsoidMirror', 'toroidalMirror']],
        ['Elements of monochromator', ['crystal', 'grating']],
        'watch',
    ];

    function defaultItemPropagationParams() {
        return [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0, 0, 0, 0, 0, 0];
    }

    function defaultDriftPropagationParams() {
        return [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0, 0, 0, 0, 0, 0];
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

    function updateVectors(newValue, oldValue) {
        if (appState.isLoaded() && newValue !== null && newValue !== undefined && newValue !== oldValue) {
            var item = beamlineService.activeItem;
            if (item.autocomputeVectors === '1') {
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
    }

    $scope.beamlineService = beamlineService;
    $scope.$watch('beamlineService.activeItem.grazingAngle', updateVectors);
    $scope.$watch('beamlineService.activeItem.autocomputeVectors', updateVectors);

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

    function syncFirstElementPositionToDistanceFromSource() {
        // Synchronize first element position -> distance from source:
        if (appState.models.beamline.length > 0) {
            appState.models.simulation.distanceFromSource = appState.models.beamline[0].position;
            appState.saveChanges('simulation');
        }
    }

    function syncDistanceFromSourceToFirstElementPosition() {
        // Synchronize distance from source -> first element position:
        if (appState.models.beamline.length > 0) {
            var firstElementPosition = appState.models.beamline[0].position;
            var distanceFromSource = appState.models.simulation.distanceFromSource;
            if (firstElementPosition !== distanceFromSource) {
                var diff = firstElementPosition - distanceFromSource;
                for (var i = 0; i < appState.models.beamline.length; i++) {
                    appState.models.beamline[i].position = appState.models.beamline[i].position - diff;
                }
                appState.saveChanges('beamline');
            }
        }
    }

    appState.whenModelsLoaded($scope, function() {
        updatePhotonEnergyHelpText();
        syncFirstElementPositionToDistanceFromSource();
    });

    $scope.$on('beamline.changed', function() {
        syncFirstElementPositionToDistanceFromSource();
    });

    $scope.$on('simulation.changed', function() {
        updatePhotonEnergyHelpText();
        syncDistanceFromSourceToFirstElementPosition();
    });

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

    // Process fields of the Sample element (image manipulation tab):
    $scope.$watchCollection(wrapActiveItem(['cropArea']), function (newValues, oldValues) {
        ['areaXStart', 'areaXEnd', 'areaYStart', 'areaYEnd'].forEach(function(f) {
            panelState.showField('sample', f, ! (newValues[0] === "0" || newValues[0] === false));
        });
    });
    $scope.$watchCollection(wrapActiveItem(['tileImage']), function (newValues, oldValues) {
        ['tileRows', 'tileColumns'].forEach(function(f) {
            panelState.showField('sample', f, ! (newValues[0] === "0" || newValues[0] === false));
        });
    });
    $scope.$watchCollection(wrapActiveItem(['rotateAngle']), function (newValues, oldValues) {
        ['rotateReshape'].forEach(function(f) {
            panelState.showField('sample', f, (newValues[0] !== 0 && (typeof(newValues[0]) !== 'undefined')));
        });
    });
});

SIREPO.app.controller('SRWSourceController', function (appState, panelState, requestSender, srwService, $scope) {
    var self = this;
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
        return appState.models.electronBeamPosition.driftCalculationMethod === 'auto';
    }

    function isTwissDefinition() {
        return appState.models.electronBeam.beamDefinition === 't';
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
        var energy = appState.models.gaussianBeam.photonEnergy;
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
        panelState.enableField(reportName, 'magneticField', false);
        if (reportName === 'intensityReport') {
            panelState.showField(reportName, 'magneticField', false);
        }
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
        ['effectiveDeflectingParameter', 'horizontalDeflectingParameter', 'verticalDeflectingParameter', 'period', 'length'].forEach(function(f) {
            panelState.showField('undulator', f, ! srwService.isTabulatedUndulatorWithMagenticFile());
        });
        ['gap', 'phase', 'magneticFile', 'indexFileName'].forEach(function(f) {
            panelState.showField('tabulatedUndulator', f, srwService.isTabulatedUndulatorWithMagenticFile());
        });

        // Make the effective deflecting parameter read-only:
        panelState.enableField('undulator', 'effectiveDeflectingParameter', false);

        // Always hide some fields in the calculator mode:
        if (srwService.isApplicationMode('calculator')) {
            ['longitudinalPosition', 'horizontalSymmetry', 'verticalSymmetry'].forEach(function(f) {
                panelState.showField('undulator', f, false);
            });
        }
    }

    function processUndulatorDefinition(undulatorDefinition, deflectingParameter, amplitude) {
        if (! (srwService.isIdealizedUndulator() || srwService.isTabulatedUndulator())) {
            return;
        }
        requestSender.getApplicationData(
            {
                method: 'process_undulator_definition',
                undulator_definition: undulatorDefinition,
                undulator_parameter: appState.models.undulator[deflectingParameter],
                amplitude: appState.models.undulator[amplitude],
                undulator_period: appState.models.undulator.period / 1000,
                methodSignature: 'process_undulator_definition' + deflectingParameter,
            },
            function(data) {
                if (! appState.isLoaded()) {
                    return;
                }
                if (undulatorDefinition === 'K') {
                    if (deflectingParameter === 'horizontalDeflectingParameter') {
                        appState.models.undulator.horizontalAmplitude = formatFloat(data.amplitude);
                    } else {
                        appState.models.undulator.verticalAmplitude = formatFloat(data.amplitude);
                    }
                } else if (undulatorDefinition === 'B') {
                    if (amplitude === 'horizontalAmplitude') {
                        appState.models.undulator.horizontalDeflectingParameter = formatFloat(data.undulator_parameter);
                    } else {
                        appState.models.undulator.verticalDeflectingParameter = formatFloat(data.undulator_parameter);
                    }
                }
                appState.models.undulator.effectiveDeflectingParameter = formatFloat(Math.sqrt(
                    Math.pow(appState.models.undulator.horizontalDeflectingParameter, 2) +
                    Math.pow(appState.models.undulator.verticalDeflectingParameter, 2)
                ));
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

    self.handleModalShown = function(name) {
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
        } else if (name == 'undulator' || name == 'tabulatedUndulator') {
            // make sure the electronBeam.drift is also updated
            appState.saveQuietly('electronBeamPosition');
        } else if (name == 'gaussianBeam') {
            appState.models.sourceIntensityReport.photonEnergy = appState.models.gaussianBeam.photonEnergy;
            appState.models.simulation.photonEnergy = appState.models.gaussianBeam.photonEnergy;
            appState.saveQuietly('sourceIntensityReport');
            appState.saveQuietly('simulation');
        }
    });

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

    appState.whenModelsLoaded($scope, function() {
        changeFluxReportName('fluxReport');
        changeFluxReportName('fluxAnimation');
        disableBasicEditorBeamName();
        processUndulator();
        processGaussianBeamSize();

        appState.watchModelFields($scope, ['electronBeam.beamSelector', 'electronBeam.beamDefinition'], processBeamFields);

        appState.watchModelFields($scope, ['electronBeam.name'], function() {
            // keep beamSelector in sync with name
            appState.models.electronBeam.beamSelector = appState.models.electronBeam.name;
        });
        appState.watchModelFields($scope, ['tabulatedUndulator.name'], function() {
            // keep undulatorSelector in sync with name
            appState.models.tabulatedUndulator.undulatorSelector = appState.models.tabulatedUndulator.name;
        });

        appState.watchModelFields($scope, ['electronBeamPosition.driftCalculationMethod'], function() {
            processBeamParameters();
            processBeamFields();
        });

        appState.watchModelFields($scope, ['electronBeam.horizontalEmittance', 'electronBeam.horizontalBeta', 'electronBeam.horizontalAlpha', 'electronBeam.horizontalDispersion', 'electronBeam.horizontalDispersionDerivative', 'electronBeam.verticalEmittance', 'electronBeam.verticalBeta', 'electronBeam.verticalAlpha', 'electronBeam.verticalDispersion', 'electronBeam.verticalDispersionDerivative'], processBeamParameters);


        ['fluxReport', 'fluxAnimation'].forEach(function(f) {
            appState.watchModelFields($scope, [f + '.fluxType', f + '.distanceFromSource'], function() {
                changeFluxReportName(f);
            });
        });

        appState.watchModelFields($scope, ['fluxAnimation.method'], processFluxAnimation);

        appState.watchModelFields($scope, ['gaussianBeam.sizeDefinition', 'gaussianBeam.rmsSizeX', 'gaussianBeam.rmsSizeY', 'gaussianBeam.rmsDivergenceX', 'gaussianBeam.rmsDivergenceY', 'gaussianBeam.photonEnergy'], function() {
            if (srwService.isGaussianBeam()) {
                processGaussianBeamSize();
            }
        });

        appState.watchModelFields($scope, ['intensityReport.method'], updatePrecisionLabel);

        appState.watchModelFields($scope, ['tabulatedUndulator.undulatorType', 'undulator.length', 'undulator.period', 'simulation.sourceType'], processBeamParameters);

        appState.watchModelFields($scope, ['tabulatedUndulator.undulatorType'], processUndulator);

        appState.watchModelFields($scope, ['tabulatedUndulator.magneticFile'], function() {
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

        appState.watchModelFields($scope, ['trajectoryReport.timeMomentEstimation'], function() {
            processTrajectoryReport();
        });

        appState.watchModelFields($scope, ['undulator.horizontalDeflectingParameter', 'undulator.verticalDeflectingParameter'], function() {
            if (isActiveField('undulator', 'horizontalDeflectingParameter')) {
                processUndulatorDefinition('K', 'horizontalDeflectingParameter', 'horizontalAmplitude');
            } else if (isActiveField('undulator', 'verticalDeflectingParameter')) {
                processUndulatorDefinition('K', 'verticalDeflectingParameter', 'verticalAmplitude');
            }
        });

        appState.watchModelFields($scope, ['undulator.horizontalAmplitude', 'undulator.verticalAmplitude', 'undulator.period'], function() {
            if (isActiveField('undulator', 'horizontalAmplitude')) {
                processUndulatorDefinition('B', 'horizontalDeflectingParameter', 'horizontalAmplitude');
            } else if (isActiveField('undulator', 'verticalAmplitude')) {
                processUndulatorDefinition('B', 'verticalDeflectingParameter', 'verticalAmplitude');
            } else if (isActiveField('undulator', 'period')) {
                processUndulatorDefinition('B', 'verticalDeflectingParameter', 'verticalAmplitude');
                processUndulatorDefinition('B', 'horizontalDeflectingParameter', 'horizontalAmplitude');
            }
        });
    });
});

SIREPO.app.directive('appFooter', function(appState, srwService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-common-footer="nav"></div>',
            '<div data-modal-editor="" view-name="simulationGrid" data-parent-controller="nav"></div>',
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

    var rightNav = [
        '<div data-app-header-right="nav">',
          '<app-header-right-sim-loaded>',
            '<ul class="nav navbar-nav sr-navbar-right">',
              '<li data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
              '<li data-ng-class="{active: nav.isActive(\'beamline\')}"><a href data-ng-click="nav.openSection(\'beamline\')"><span class="glyphicon glyphicon-option-horizontal"></span> Beamline</a></li>',
            '</ul>',
          '</app-header-right-sim-loaded>',
          '<app-settings>',
              '<div data-ng-if="! srwService.isApplicationMode(\'calculator\') && nav.isActive(\'beamline\')"><a href data-ng-click="showSimulationGrid()"><span class="glyphicon glyphicon-th"></span> Initial Wavefront Simulation Grid</a></div>',
          '</app-settings>',
          '<app-header-right-sim-list>',
            '<ul class="nav navbar-nav sr-navbar-right">',
              '<li><a href data-ng-click="showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>',
            '</ul>',
          '</app-header-right-sim-list>',
        '</div>',
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
              '<ul data-ng-if="nav.isLoaded()" class="nav navbar-nav navbar-right">',
                '<li data-settings-menu="nav"></li>',
              '</ul>',
              '<ul class="nav navbar-nav navbar-right" data-ng-show="nav.isLoaded()">',
                '<li data-ng-if="nav.hasDocumentationUrl()"><a href data-ng-click="nav.openDocumentation()"><span class="glyphicon glyphicon-book"></span> Notes</a></li>',
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
              '<div data-app-header-brand="nav" data-app-url="/light"></div>',
              '<div class="navbar-left" data-app-header-left="nav"></div>',
              rightNav,
            '</div>',
        ].join(''),
        controller: function($scope) {

            $scope.srwService = srwService;

            $scope.showImportModal = function() {
                $('#srw-simulation-import').modal('show');
            };

            $scope.showSimulationGrid = function() {
                panelState.showModalEditor('simulationGrid');
            };
        },
    };
});

SIREPO.app.directive('exportPythonLink', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<a href data-ng-click="exportPython()">Export Python Code</a>',
        ].join(''),
        controller: function($scope) {
            $scope.exportPython = function() {
                panelState.pythonSource(
                    appState.models.simulation.simulationId,
                    panelState.findParentAttribute($scope, 'modelKey'));
            };
        },
    };
});

SIREPO.app.directive('headerTooltip', function() {
    return {
        restrict: 'A',
        scope: {
            tipText: '=headerTooltip',
        },
        template: [
            '<span class="glyphicon glyphicon-info-sign sr-info-pointer"></span>',
        ],
        link: function link(scope, element) {
            $(element).tooltip({
                title: scope.tipText,
                html: true,
                placement: 'bottom',
            });
            scope.$on('$destroy', function() {
                $(element).tooltip('destroy');
            });
        },
    };
});

//TODO(pjm): refactor and generalize with mirrorUpload
SIREPO.app.directive('importPython', function(appState, fileManager, fileUpload, requestSender) {
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
                        folder: fileManager.getActiveFolderPath(),
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

SIREPO.app.directive('propagationParameterFieldEditor', function() {
    return {
        restrict: 'A',
        scope: {
            param: '=',
            paramInfo: '=',
        },
        template: [
            '<div data-ng-switch="::paramInfo.fieldType">',
              '<select data-ng-switch-when="AnalyticalTreatment" number-to-string class="input-sm" data-ng-model="param[paramInfo.fieldIndex]" data-ng-options="item[0] as item[1] for item in ::analyticalTreatmentEnum"></select>',
              '<input data-ng-switch-when="Float" data-string-to-number="" type="text" class="srw-small-float" data-ng-model="param[paramInfo.fieldIndex]">',
              '<input data-ng-switch-when="Boolean" type="checkbox" data-ng-model="param[paramInfo.fieldIndex]" data-ng-true-value="1", data-ng-false-value="0">',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.analyticalTreatmentEnum = SIREPO.APP_SCHEMA.enum.AnalyticalTreatment;
        },
    };
});

SIREPO.app.directive('propagationParametersModal', function() {
    return {
        restrict: 'A',
        scope: {
            propagations: '=',
            postPropagation: '=',
        },
        template: [
            '<div class="modal fade" id="srw-propagation-parameters" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<div data-help-button="Propagation Parameters"></div>',
                    '<span class="lead modal-title text-info">Propagation Parameters</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<div class="row">',
                        '<ul class="nav nav-tabs">',
                          '<li data-ng-repeat="item in ::propagationSections track by $index" data-ng-class="{active: isPropagationSectionActive($index)}">',
                            '<a href data-ng-click="setPropagationSection($index)">{{:: item }}</a>',
                          '</li>',
                        '</ul>',
                        '<div data-propagation-parameters-table="" data-section-index="{{:: $index }}" data-propagations="propagations" data-post-propagation="postPropagation" data-ng-repeat="item in ::propagationSections track by $index"></div>',
                      '</div>',
                      '<div class="row">',
                        '<div class="col-sm-offset-6 col-sm-3">',
                          '<button data-dismiss="modal" class="btn btn-primary"style="width: 100%" >Close</button>',
                        '</div>',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var activePropagationSection = 0;
            $scope.propagationSections = ['Propagator and Resizing', 'Auto-Resize', 'Orientation'];

            $scope.isPropagationSectionActive = function(index) {
                return index == activePropagationSection;
            };

            $scope.setPropagationSection = function(index) {
                activePropagationSection = index;
            };
        },
    };
});

SIREPO.app.directive('propagationParametersTable', function(appState) {
    return {
        restrict: 'A',
        scope: {
            sectionIndex: '@',
            propagations: '=',
            postPropagation: '=',
        },
        template: [
            '<div data-ng-class="::classForSection(sectionIndex)" data-ng-show="$parent.isPropagationSectionActive(sectionIndex)">',
              '<table class="table table-striped table-condensed">',
                '<thead>',
                  '<tr>',
                    '<th>Element</th>',
                    '<th class="srw-tiny-heading" data-ng-repeat="item in ::parameterInfo track by $index">{{:: item.headingText }} <span data-ng-if="::item.headingTooltip" data-header-tooltip="::item.headingTooltip"</span></th>',
                  '</tr>',
                '</thead>',
                '<tbody>',
                  '<tr data-ng-repeat="prop in propagations track by $index" data-ng-class="{\'srw-disabled-item\': isDisabledPropagation(prop)}">',
                    '<td class="input-sm" style="vertical-align: middle">{{ prop.title }}</td>',
                    '<td class="sr-center" style="vertical-align: middle" data-ng-repeat="paramInfo in ::parameterInfo track by $index">',
                      '<div data-propagation-parameter-field-editor="" data-param="prop.params" data-param-info="paramInfo"></div>',
                    '</td>',
                  '</tr>',
                  '<tr class="warning">',
                    '<td class="input-sm">Final post-propagation (resize)</td>',
                    '<td class="sr-center" style="vertical-align: middle" data-ng-repeat="paramInfo in ::parameterInfo track by $index">',
                      '<div data-propagation-parameter-field-editor="" data-param="postPropagation" data-param-info="paramInfo"></div>',
                    '</td>',
                  '</tr>',
                '</tbody>',
              '</table>',
            '</div>',
        ].join(''),
        controller: function($scope) {

            function initParameters() {
                var info = appState.modelInfo('propagationParameters');
                var parametersBySection = [
                    [3, 4, 5, 6, 7, 8],
                    [0, 1, 2],
                    [12, 13, 14, 15, 16],
                ];
                $scope.parameterInfo = [];
                parametersBySection[$scope.sectionIndex].forEach(function(i) {
                    var field = i.toString();
                    $scope.parameterInfo.push({
                        headingText: info[field][0],
                        headingTooltip: info[field][3],
                        fieldType: info[field][1],
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
                return false;
            };

            initParameters();
        },
    };
});

SIREPO.app.directive('simulationStatusPanel', function(appState, beamlineService, frameCache, persistentSimulation) {
    return {
        restrict: 'A',
        scope: {
            model: '@simulationStatusPanel',
            title: '@',
        },
        template: [
            '<form name="form" class="form-horizontal" autocomplete="off" novalidate>',
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
                    '<div data-simulation-status-timer="timeData" data-ng-show="! hasFluxCompMethod() || ! isApproximateMethod()"></div>',
                  '</div>',
                '</div>',
                '<div class="col-sm-6 pull-right" data-ng-show="! hasFluxCompMethod() || ! isApproximateMethod()">',
                  '<button class="btn btn-default" data-ng-click="cancelPersistentSimulation()">End Simulation</button>',
                '</div>',
              '</div>',
              '<div data-ng-show="isStateStopped()">',
                '<div class="col-sm-6">',
                  'Simulation ',
                  '<span>{{ stateAsText() }}</span>',
                  '<div data-ng-show="! isStatePending() && ! isInitializing() && particleNumber">',
                    'Completed particle: {{ particleNumber }} / {{ particleCount}}',
                  '</div>',
                  '<div data-ng-show="! hasFluxCompMethod() || ! isApproximateMethod()">',
                    '<div data-simulation-status-timer="timeData"></div>',
                  '</div>',
                '</div>',
                '<div class="col-sm-6 pull-right" data-ng-show="! hasFluxCompMethod() || ! isApproximateMethod()">',
                  '<button class="btn btn-default" data-ng-click="saveAndRunSimulation()">Start New Simulation</button>',
                '</div>',
              '</div>',
            '</form>',
        ].join(''),
        controller: function($scope) {

            //TODO(pjm): share with template/srw.py _REPORT_STYLE_FIELDS
            var plotFields = ['intensityPlotsWidth', 'intensityPlotsScale', 'colorMap'];
            var multiElectronAnimation = null;

            function copyMultiElectronModel() {
                multiElectronAnimation = appState.cloneModel('multiElectronAnimation');
                plotFields.forEach(function(f) {
                    delete multiElectronAnimation[f];
                });
            }

            function hasReportParameterChanged() {
                if ($scope.model == 'multiElectronAnimation') {
                    // for the multiElectronAnimation, changes to the intensityPlots* fields don't require
                    // the simulation to be restarted
                    var oldModel = multiElectronAnimation;
                    copyMultiElectronModel();
                    if (appState.deepEquals(oldModel, multiElectronAnimation)) {
                        return false;
                    }
                }
                return true;
            }

            function methodForMethodNum(methodNum) {
                return SIREPO.APP_SCHEMA.enum.FluxMethod.filter(function (fm) {
                    return fm[0] == methodNum;
                })[0];
            }

            $scope.cancelPersistentSimulation = function () {
                var cancelSuccess = function (data, status) {
                    if( $scope.hasFluxCompMethod() && $scope.isApproximateMethod() ) {
                        $scope.saveAndRunSimulation();
                    }
                };
                // ignore error case
                $scope.cancelSimulation(cancelSuccess, cancelSuccess);
            };

            $scope.handleStatus = function(data) {
                if (data.method && data.method != appState.models.fluxAnimation.method) {
                    // the output file on the server was generated with a different flux method
                    $scope.timeData = {};
                    frameCache.setFrameCount(0);
                    return;
                }
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

            $scope.hasFluxCompMethod = function () {
                return $scope.model === 'fluxAnimation';
            };

            $scope.isApproximateMethod = function () {
                return appState.models.fluxAnimation.method == -1;
            };

            $scope.saveAndRunSimulation = function() {
                if ($scope.model == 'multiElectronAnimation') {
                    appState.models.simulation.multiElectronAnimationTitle = beamlineService.getReportTitle($scope.model);
                }
                appState.saveChanges('simulation', $scope.runSimulation);
            };

            appState.whenModelsLoaded($scope, function() {
                $scope.$on($scope.model + '.changed', function() {
                    if ($scope.isReadyForModelChanges && hasReportParameterChanged()) {
                        $scope.cancelPersistentSimulation();
                        frameCache.setFrameCount(0);
                        frameCache.clearFrames($scope.model);
                        $scope.percentComplete = 0;
                        $scope.particleNumber = 0;
                    }
                });
                copyMultiElectronModel();
            });

            persistentSimulation.initProperties($scope, $scope, {
                multiElectronAnimation: $.merge([SIREPO.ANIMATION_ARGS_VERSION + '1'], plotFields),
                fluxAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1'],
            });
       },
    };
});
