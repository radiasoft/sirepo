'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appDefaultSimulationValues.simulation.sourceType = 'u';
    SIREPO.INCLUDE_EXAMPLE_FOLDERS = true;
    SIREPO.SINGLE_FRAME_ANIMATION = ['coherenceXAnimation', 'coherenceYAnimation', 'fluxAnimation', 'multiElectronAnimation'];
    SIREPO.PLOTTING_COLOR_MAP = 'grayscale';
    SIREPO.PLOTTING_SHOW_FWHM = true;
    SIREPO.appReportTypes = [
        '<div data-ng-switch-when="beamline3d" data-beamline-3d="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-id="reportId"></div>',
    ].join('');
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="BeamList">',
          '<div data-model-selection-list="" data-model-name="modelName" data-model="model" data-field="field" data-field-class="fieldClass"></div>',
        '</div>',
        '<div data-ng-switch-when="UndulatorList">',
          '<div data-model-selection-list="" data-model-name="modelName" data-model="model" data-field="field" data-field-class="fieldClass"></div>',
        '</div>',
        '<div data-ng-switch-when="ImageFile" class="col-sm-7">',
          '<div data-file-field="field" data-file-type="sample" data-model="model" data-selection-required="true" data-empty-selection-text="Select Image File"></div>',
        '</div>',
        '<div data-ng-switch-when="MagneticZipFile" class="col-sm-7">',
          '<div data-file-field="field" data-file-type="undulatorTable" data-model="model" data-selection-required="true" data-empty-selection-text="Select Magnetic Zip File"></div>',
        '</div>',
        '<div data-ng-switch-when="ArbitraryFieldFile" class="col-sm-7">',
          '<div data-file-field="field" data-file-type="arbitraryField" data-model="model" data-selection-required="true" data-empty-selection-text="Select Magnetic Data File"></div>',
        '</div>',
        '<div data-ng-switch-when="MirrorFile" class="col-sm-7">',
          '<div data-mirror-file-field="" data-model="model" data-field="field" data-model-name="modelName" ></div>',
        '</div>',
        '<div data-ng-switch-when="WatchPoint" data-ng-class="fieldClass">',
          '<div data-watch-point-list="" data-model="model" data-field="field" data-model-name="modelName"></div>',
        '</div>',
        '<div data-ng-switch-when="OutputImageFormat">',
          '<div data-sample-preview=""></div>',
        '</div>',
        '<div data-ng-switch-when="SampleRandomShapeArray" class="col-sm-7">',
          '<div data-sample-random-shapes="" data-model="model" data-field="field"></div>',
        '</div>',
    ].join('');
    SIREPO.appDownloadLinks = [
        '<li data-lineout-csv-link="x"></li>',
        '<li data-lineout-csv-link="y"></li>',
        '<li data-lineout-csv-link="full"></li>',
        '<li data-export-python-link="" data-report-title="{{ reportTitle() }}"></li>',
    ].join('');
    SIREPO.appPanelHeadingButtons = [
        '<div data-ng-if="isReport && ! hasData()" class="dropdown" style="display: inline-block">',
        '<a href class="dropdown-toggle" data-toggle="dropdown" title="Download"> <span class="sr-panel-heading glyphicon glyphicon-cloud-download" style="margin-bottom: 0"></span></a> ',
        '<ul class="dropdown-menu dropdown-menu-right">',
        '<li data-export-python-link="" data-report-title="{{ reportTitle() }}"></li>',
        '</ul>',
        '</div>',
    ].join('');

    SIREPO.PLOTTING_SHOW_CONVERGENCE_LINEOUTS = true;
});

SIREPO.app.factory('srwService', function(activeSection, appDataService, appState, beamlineService, panelState, requestSender, $location, $rootScope, $route) {
    var FORMAT_DECIMALS = 8;
    var self = {};
    self.originalCharacteristicEnum = null;
    self.singleElectronCharacteristicEnum = null;
    self.showCalcCoherence = false;

    // override appDataService functions
    appDataService.appDataForReset = function() {
        // delete the user-defined models first
         return {
             method: 'delete_user_models',
             electron_beam: appState.models.electronBeam,
             tabulated_undulator: appState.models.tabulatedUndulator,
         };
    };
    appDataService.canCopy = function() {
        if (appDataService.applicationMode == 'calculator' || appDataService.applicationMode == 'wavefront') {
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
        for (var i = 0; i < characteristic.length; i++) {
            characteristic[i][1] = characteristic[i][1].replace(/Single-Electron /g, '');
        }
        self.singleElectronCharacteristicEnum = characteristic;
    }

    function isSelected(sourceType) {
        if (appState.isLoaded()) {
            return appState.applicationState().simulation.sourceType == sourceType;
        }
        return false;
    }

    self.computeModel = function(analysisModel) {
        if (analysisModel === 'coherenceYAnimation' || analysisModel === 'coherenceXAnimation') {
            return 'multiElectronAnimation';
        }
        return analysisModel;
    };

    self.disableReloadOnSearch = function() {
        if ($route.current && $route.current.$$route) {
            $route.current.$$route.reloadOnSearch = false;
        }
    };

    self.formatFloat = function(v) {
        return +parseFloat(v).toFixed(FORMAT_DECIMALS);
    };

    self.getReportTitle = function(modelName, itemId) {
        if (! appState.isLoaded()) {
            return '';
        }
        if (modelName == 'multiElectronAnimation') {
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
        return requestSender.getApplicationData(
            {
                method: 'model_list',
                model_name: modelName,
                methodSignature: 'model_list ' + modelName + (sig || ''),
            },
            callback);
    };

    self.processBeamParameters = function() {
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
                    ebeam[f] = data[f];
                });
                appState.models.electronBeamPosition.drift = data.drift;
            }
        );
    };

    self.processIntensityLimit = function(modelName, modelKey) {
        ['minIntensityLimit', 'maxIntensityLimit'].forEach(function(f) {
            panelState.showField(modelName, f, appState.models[modelKey || modelName].useIntensityLimits == '1');
        });
    };

    self.setShowCalcCoherence = function(isShown) {
        self.showCalcCoherence = isShown;
    };

    self.showBrillianceReport = function() {
        return self.isIdealizedUndulator() || (self.isTabulatedUndulator() && ! self.isTabulatedUndulatorWithMagenticFile());
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

    $rootScope.$on('$locationChangeSuccess', function (event) {
        // reset reloadOnSearch so that back/next browser buttons will trigger a page load
        if ($route.current && $route.current.$$route) {
            $route.current.$$route.reloadOnSearch = true;
        }
    });

    $rootScope.$on('$routeChangeSuccess', function() {
        var search = $location.search();
        if(search) {
            appDataService.applicationMode = search.application_mode || 'default';
        }
    });

    appState.setAppService(self);

    appState.whenModelsLoaded($rootScope, function() {
        initCharacteristic();
        // don't show multi-electron values in certain cases
        SIREPO.APP_SCHEMA.enum.Characteristic = (self.isApplicationMode('wavefront') || self.isGaussianBeam())
            ? self.singleElectronCharacteristicEnum
            : self.originalCharacteristicEnum;
    });

    return self;
});

SIREPO.app.controller('SRWBeamlineController', function (activeSection, appState, beamlineService, panelState, requestSender, simulationQueue, srwService, $scope, $location) {
    var self = this;
    var grazingAngleElements = ['ellipsoidMirror', 'sphericalMirror', 'toroidalMirror'];
    // tabs: single, multi, beamline3d
    var activeTab = 'single';
    self.mirrorReportId = Math.floor(Math.random() * Number.MAX_SAFE_INTEGER);
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
    self.isBeamline3dEnabled = SIREPO.APP_SCHEMA.feature_config.beamline3d;

    function attenuationPrefixes(item) {
        return item.type == 'fiber'
            ? ['external', 'core']
            : ['main', 'complementary'];
    }

    function computeCRLCharacteristics(item) {
        updateCRLFields(item);
        requestSender.getApplicationData(
            {
                method: 'compute_crl_characteristics',
                optical_element: item,
                photon_energy: appState.models.simulation.photonEnergy,
            },
            function(data) {
                ['refractiveIndex', 'attenuationLength'].forEach(function(f) {
                    formatMaterialOutput(item, data, f);
                });
                ['focalDistance', 'absoluteFocusPosition'].forEach(function(f) {
                    item[f] = parseFloat(data[f]).toFixed(4);
                });
            });
    }

    function computePGMValue(item) {
        updateGratingFields(item);
        //  computeFields('compute_PGM_value', item, ['energyAvg', 'cff', 'grazingAngle', 'orientation']);
        requestSender.getApplicationData(
            {
                method: 'compute_PGM_value',
                optical_element: item,
                photon_energy: appState.models.simulation.photonEnergy,
            },
            function(data) {
                 ['energyAvg', 'cff', 'grazingAngle', 'orientation'].forEach(function(f) {
                    item[f] = data[f];
                });
                ['nvx', 'nvy', 'nvz', 'tvx', 'tvy', 'outoptvx', 'outoptvy', 'outoptvz', 'outframevx', 'outframevy'].forEach(function(f) {
                    item[f] = data[f];
                    formatOrientationOutput(item, data, f);
                });
            });
    }

    function computeCrystalInit(item) {
        if (item.material != 'Unknown') {
            updateCrystalInitFields(item);
            computeFields('compute_crystal_init', item, ['dSpacing', 'psi0r', 'psi0i', 'psiHr', 'psiHi', 'psiHBr', 'psiHBi', 'orientation']);
        }
    }

    function computeCrystalOrientation(item) {
        updateCrystalOrientationFields(item);
        //computeFields('compute_crystal_orientation', item, ['nvx', 'nvy', 'nvz', 'tvx', 'tvy', 'outoptvx', 'outoptvy', 'outoptvz', 'outframevx', 'outframevy', 'orientation']);
        requestSender.getApplicationData(
            {
                method: 'compute_crystal_orientation',
                optical_element: item,
                photon_energy: appState.models.simulation.photonEnergy,
            },
            function(data) {
                ['nvx', 'nvy', 'nvz', 'tvx', 'tvy', 'outoptvx', 'outoptvy', 'outoptvz', 'outframevx', 'outframevy'].forEach(function(f) {
                    item[f] = data[f];
                    formatOrientationOutput(item, data, f);
                });
            });
    }

    function computeDeltaAttenCharacteristics(item) {
        updateMaterialFields(item);
        requestSender.getApplicationData(
            {
                method: 'compute_delta_atten_characteristics',
                optical_element: item,
                photon_energy: appState.models.simulation.photonEnergy,
            },
            function(data) {
                ['refractiveIndex', 'attenuationLength'].forEach(function(f) {
                    formatMaterialOutput(item, data, f);
                });
            });
    }

    function computeDualAttenCharacteristics(item) {
        // fiber or zonePlate items
        var prefixes = attenuationPrefixes(item);
        updateDualFields(item);
        requestSender.getApplicationData(
            {
                method: 'compute_dual_characteristics',
                optical_element: item,
                photon_energy: appState.models.simulation.photonEnergy,
                prefix1: prefixes[0],
                prefix2: prefixes[1],
            },
            function(data) {
                [prefixes[0] + 'RefractiveIndex', prefixes[0] + 'AttenuationLength', prefixes[1] + 'RefractiveIndex', prefixes[1] + 'AttenuationLength'].forEach(function(f) {
                    formatMaterialOutput(item, data, f);
                });
            });
    }

    function computeFields(method, item, fields) {
        requestSender.getApplicationData(
            {
                method: method,
                optical_element: item,
            },
            function(data) {
                fields.forEach(function(f) {
                    item[f] = data[f];
                });
            });

    }

    function computeVectors(item) {
        updateVectorFields(item);
        if (item.grazingAngle && item.autocomputeVectors != 'none') {
            computeFields('compute_grazing_orientation', item, ['normalVectorZ', 'normalVectorY', 'normalVectorX', 'tangentialVectorY', 'tangentialVectorX']);
        }
    }

    function defaultItemPropagationParams() {
        return [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0, 0, 0, 0, 0, 0];
    }

    function defaultDriftPropagationParams() {
        return [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0, 0, 0, 0, 0, 0];
    }

    function formatDriftFloat(v) {
        var str = v.toFixed(4);
        str = str.replace(/0+$/, '');
        str = str.replace(/\.$/, '');
        return str;
    }

    function formatMaterialOutput(item, data, f) {
        item[f] = parseFloat(data[f]);
        if (item[f] === 0) {
            // pass
        }
        else if (item[f] < 1e-3) {
            item[f] = item[f].toExponential(6);
        }
        else if (item[f] === 1) {
            // pass
        }
        else {
            item[f] = item[f].toFixed(6);
        }
    }

    function formatOrientationOutput(item, data, f) {
        item[f] = parseFloat(data[f]);
        if (item[f] === 1) {
            item[f] = item[f].toFixed(1);
        }
        else if (item[f] === 0) {
            item[f] = item[f].toFixed(1);
        }
        else {
            item[f] = item[f].toFixed(12);
        }
    }

    function isUserDefined(v) {
        return v === 'User-defined';
    }

    function syncFirstElementPositionToDistanceFromSource() {
        // Synchronize first element position -> distance from source:
        if (appState.models.beamline.length > 0) {
            if (appState.models.simulation.distanceFromSource != appState.models.beamline[0].position) {
                appState.models.simulation.distanceFromSource = appState.models.beamline[0].position;
                appState.saveChanges('simulation');
            }
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

    function updateCRLFields(item) {
        panelState.enableField('crl', 'focalDistance', false);
        updateMaterialFields(item);
    }

    function updateCrystalInitFields(item) {
        ['dSpacing', 'psi0r', 'psi0i', 'psiHr', 'psiHi', 'psiHBr', 'psiHBi'].forEach(function(f) {
            panelState.enableField(item.type, f, false);
        });
    }

    function updateCrystalOrientationFields(item) {
        ['nvx', 'nvy', 'nvz', 'tvx', 'tvy'].forEach(function(f) {
            panelState.enableField(item.type, f, false);
        });
    }

    function updateGratingFields(item) {
        panelState.enableField(item.type, 'cff', item.computeParametersFrom === '1');
        panelState.enableField(item.type, 'grazingAngle', item.computeParametersFrom === '2');
        ['nvx', 'nvy', 'nvz', 'tvx', 'tvy', 'outoptvx', 'outoptvy', 'outoptvz', 'outframevx', 'outframevy'].forEach(function(f) {
            panelState.enableField(item.type, f, item.computeParametersFrom === '3');
        });
    }

    function updateDualFields(item) {
        var prefixes = attenuationPrefixes(item);
        panelState.showField(item.type, 'method', ! isUserDefined(item[prefixes[0] + 'Material']) || ! isUserDefined(item[prefixes[1] + 'Material']));
        prefixes.forEach(function(prefix) {
            panelState.enableField(item.type, prefix + 'RefractiveIndex', isUserDefined(item[prefix + 'Material']));
            panelState.enableField(item.type, prefix + 'AttenuationLength', isUserDefined(item[prefix + 'Material']) || item.method === 'calculation');

        });
    }

    function updateMaterialFields(item) {
        panelState.showField(item.type, 'method', ! isUserDefined(item.material));
        panelState.enableField(item.type, 'refractiveIndex', isUserDefined(item.material));
        panelState.enableField(item.type, 'attenuationLength', isUserDefined(item.material) || item.method === 'calculation');
    }

    function updatePhotonEnergyHelpText() {
        if (appState.isLoaded()) {
            var msg = 'The photon energy is: ' + appState.models.simulation.photonEnergy + ' eV';
            [
                ['crl'],
                ['mask'],
                ['fiber', 'external'],
                ['fiber', 'core'],
                ['sample'],
                ['zonePlate', 'main'],
                ['zonePlate', 'complementary'],
            ].forEach(function(model) {
                var name = model[0];
                var prefix = model[1] || '';
                ['refractiveIndex', 'attenuationLength'].forEach(function(f) {
                    if (prefix) {
                        f = prefix + f.charAt(0).toUpperCase() + f.slice(1);
                    }
                    SIREPO.APP_SCHEMA.model[name][f][3] = msg;
                });
            });
        }
    }

    function updateSampleFields(item) {
        panelState.showTab('sample', 2, item.sampleSource == 'file');
        panelState.showTab('sample', 3, item.sampleSource == 'randomDisk');
        ['resolution'].forEach(function(f) {
            panelState.showField('sample', f, item.sampleSource == 'file');
        });
        ['dens', 'rx', 'ry', 'nx', 'ny'].forEach(function(f) {
            panelState.showField('sample', f, item.sampleSource == 'randomDisk');
        });
        if (item.sampleSource == 'file') {
            ['areaXStart', 'areaXEnd', 'areaYStart', 'areaYEnd'].forEach(function(f) {
                panelState.showField('sample', f, item.cropArea == '1');
            });
            ['tileRows', 'tileColumns'].forEach(function(f) {
                panelState.showField('sample', f, item.tileImage == '1');
            });
            panelState.showField('sample', 'rotateReshape', item.rotateAngle);
            panelState.showField('sample', 'backgroundColor', item.cutoffBackgroundNoise);
        }
        else if (item.sampleSource == 'randomDisk') {
            panelState.showField('sample', 'rand_obj_size', item.obj_type != '4' && item.obj_type != '5');
            panelState.showField('sample', 'rand_poly_side', item.obj_type == '4');
            panelState.showField('sample', 'obj_size_ratio', item.obj_type != '4' && item.obj_type != '5' && item.rand_obj_size == '0');
            panelState.showField('sample', 'poly_sides', item.obj_type == '4' && item.rand_poly_side == '0');
            panelState.showField('sample', 'rand_shapes', item.obj_type == '5');
        }
    }

    function updateVectorFields(item) {
        ['normalVectorX', 'normalVectorY', 'normalVectorZ', 'tangentialVectorX', 'tangentialVectorY'].forEach(function(f) {
            panelState.enableField(item.type, f, item.autocomputeVectors === 'none');
        });
    }

    self.handleModalShown = function(name) {
        var item = beamlineService.activeItem;
        if (item && item.type == name) {
            if (name === 'crl') {
                updateCRLFields(item);
            }
            else if (name === 'fiber' || name === 'zonePlate') {
                updateDualFields(item);
            }
            else if (name === 'mask' || name === 'sample') {
                updateMaterialFields(item);
                if (name == 'sample') {
                    updateSampleFields(item);
                }
            }
            else if (name === 'grating'){
                updateGratingFields(item);
            }
            else if (name == 'crystal') {
                //if (item.materal != 'Unknown' && ! item.nvz) {
                if (item.materal != 'Unknown') {
                    computeCrystalInit(item);
                }
                updateCrystalOrientationFields(item);
            }
            if (grazingAngleElements.indexOf(name) >= 0) {
                updateVectorFields(item);
            }
        }
        panelState.showField('watchpointReport', 'fieldUnits', srwService.isGaussianBeam());
        panelState.showField('initialIntensityReport', 'fieldUnits', srwService.isGaussianBeam());
        if (appState.models[name] && appState.models[name].useIntensityLimits) {
            srwService.processIntensityLimit(name);
        }
    };

    self.isActiveTab = function(tab) {
        return tab == activeTab;
    };

    self.isEditable = function() {
        beamlineService.setEditable(srwService.isApplicationMode('default'));
        return beamlineService.isEditable();
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
            if(beamline[i].type == 'grating' || beamline[i].type == 'crystal'){
                p[0][12] = beamline[i].outoptvx;
                p[0][13] = beamline[i].outoptvy;
                p[0][14] = beamline[i].outoptvz;
                p[0][15] = beamline[i].outframevx;
                p[0][16] = beamline[i].outframevy;
            }
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
                    title: 'Drift ' + formatDriftFloat(d) + 'm',
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

    self.setActiveTab = function(tab) {
        if (tab != activeTab) {
            srwService.disableReloadOnSearch();
            $location.search('tab', tab);
            activeTab = tab;
            if (activeTab != 'single') {
                // tab changed, cancel single-electron queue items
                simulationQueue.cancelAllItems();
            }
        }
    };

    self.showPropagationModal = function() {
        self.prepareToSave();
        beamlineService.dismissPopup();
        $('#srw-propagation-parameters').modal('show');
    };

    self.showSimulationGrid = function() {
        panelState.showModalEditor('simulationGrid', null, $scope);
    };

    self.setWatchpointActive = function(item) {
        if(! self.isWatchpointActive(item)) {
            self.setWatchpointForPartiallyCoherentReport(item.id);
        }
    };
    self.isWatchpointActive = function(item) {
        return ! item.isDisabled && self.getWatchpointForPartiallyCoherentReport() == item.id;
    };
    self.setWatchpointForPartiallyCoherentReport = function(wpId) {
         appState.models.multiElectronAnimation.watchpointId = wpId;
         appState.saveChanges('multiElectronAnimation');
    };
    self.getWatchpointForPartiallyCoherentReport = function() {
         return appState.models.multiElectronAnimation.watchpointId;
    };
    $scope.$on('multiElectronAnimation.changed', function(event) {
        var wpIdArr = beamlineService.getWatchIds();
        if(wpIdArr.length == 0) {
            return;
        }

        var doSave = false;
        var wpId = appState.models.multiElectronAnimation.watchpointId;
        var activeItem = beamlineService.getItemById(wpId);
        // if previous watchpoint for the multiElectronAnimation report is now gone,
        // use the last watchpoint in the beamline
        if(! activeItem || wpIdArr.indexOf(wpId) < 0) {
            wpId = wpIdArr[wpIdArr.length - 1];
            doSave = true;
        }
        if(doSave) {
            self.setWatchpointForPartiallyCoherentReport(wpId);
        }

    });

    appState.whenModelsLoaded($scope, function() {
        srwService.setShowCalcCoherence(false);
        updatePhotonEnergyHelpText();
        syncFirstElementPositionToDistanceFromSource();
        grazingAngleElements.forEach(function(m) {
            beamlineService.watchBeamlineField($scope, m, ['grazingAngle', 'autocomputeVectors'], computeVectors);
        });
        beamlineService.watchBeamlineField($scope, 'crl', ['material', 'method', 'numberOfLenses', 'position', 'tipRadius', 'refractiveIndex'], computeCRLCharacteristics);
        beamlineService.watchBeamlineField($scope, 'fiber', ['method', 'externalMaterial', 'coreMaterial'], computeDualAttenCharacteristics);
        beamlineService.watchBeamlineField($scope, 'zonePlate', ['method', 'mainMaterial', 'complementaryMaterial'], computeDualAttenCharacteristics);
        ['mask', 'sample'].forEach(function(m) {
            beamlineService.watchBeamlineField($scope, m, ['method', 'material'], computeDeltaAttenCharacteristics);
        });
        beamlineService.watchBeamlineField($scope, 'grating', ['energyAvg', 'cff', 'grazingAngle', 'rollAngle', 'computeParametersFrom'], computePGMValue, true);
        beamlineService.watchBeamlineField($scope, 'crystal', ['material', 'energy', 'diffractionAngle', 'h', 'k', 'l'], computeCrystalInit, true);
        beamlineService.watchBeamlineField($scope, 'crystal', ['energy', 'diffractionAngle', 'useCase', 'dSpacing', 'asymmetryAngle', 'psi0r', 'psi0i'], computeCrystalOrientation, true);
        beamlineService.watchBeamlineField($scope, 'sample', ['cropArea', 'tileImage', 'rotateAngle'], updateSampleFields);
        beamlineService.watchBeamlineField($scope, 'sample', ['sampleSource', 'cropArea', 'tileImage', 'rotateAngle', 'cutoffBackgroundNoise', 'obj_type', 'rand_obj_size', 'rand_poly_side'], updateSampleFields);
        ['initialIntensityReport', 'multiElectronAnimation'].forEach(function(m) {
            appState.watchModelFields($scope, [m + '.useIntensityLimits'], function() {
                srwService.processIntensityLimit(m);
            });
        });
        $scope.$on('beamline.changed', syncFirstElementPositionToDistanceFromSource);
        $scope.$on('simulation.changed', function() {
            updatePhotonEnergyHelpText();
            syncDistanceFromSourceToFirstElementPosition();
        });
    });

    $scope.$on('modelChanged', function(e, name) {
        if(name !== 'initialIntensityReport') {
            return;
        }
        var rpt = appState.models.initialIntensityReport;
        if(! rpt || ! parseInt(rpt.copyCharacteristic)) {
            return;
        }
        var watchRpts = beamlineService.getWatchReports();
        for(var wIndex = 0; wIndex < watchRpts.length; ++wIndex) {
            var watchRptName = watchRpts[wIndex];
            var watchRpt = appState.models[watchRptName];
            if(watchRpt.characteristic !== rpt.characteristic) {
                watchRpt.characteristic = rpt.characteristic;
                appState.saveChanges(watchRptName);
            }
        }
    });

    $scope.$on('$routeChangeSuccess', function() {
        var search = $location.search();
        if (search) {
            if (search.tab) {
                self.setActiveTab(search.tab);
            }
            // old tab name in bookmarks
            else if (search.coherence) {
                if (search.coherence == 'partial') {
                    self.setActiveTab('multi');
                }
                $location.search('coherence', null);
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

SIREPO.app.controller('SRWSourceController', function (appState, panelState, requestSender, srwService, $scope) {
    var self = this;
    $scope.appState = appState;
    self.srwService = srwService;

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

    function processBrillianceReport() {
        var report = appState.models.brillianceReport;
        var isKTuning = report.brightnessComponent == 'k-tuning';
        panelState.showEnum('brillianceReport', 'reportType', '1', isKTuning);
        if (! isKTuning && report.reportType == '1') {
            report.reportType = '0';
        }
        ['detuning', 'minDeflection', 'initialHarmonic', 'finalHarmonic'].forEach(function(f) {
            panelState.showField('brillianceReport', f, isKTuning);
        });
        ['energyDelta', 'harmonic'].forEach(function(f) {
            panelState.showField('brillianceReport', f, ! isKTuning);
        });
    }

    function processFluxAnimation() {
        // ["-1", "Use Approximate Method"]
        var approxMethodKey = -1;
        var isApproximateMethod = appState.models.fluxAnimation.method == approxMethodKey;
        panelState.enableField('fluxAnimation', 'magneticField', srwService.isTabulatedUndulatorWithMagenticFile());
        if (srwService.isTabulatedUndulatorWithMagenticFile()) {
            if (appState.models.fluxAnimation.magneticField == '2' && isApproximateMethod) {
                appState.models.fluxAnimation.method = '1';
            }
        }
        else {
            appState.models.fluxAnimation.magneticField = '1';
        }

        // No approximate flux method with accurate magnetic field
        panelState.showEnum('fluxAnimation', 'method', approxMethodKey, appState.models.fluxAnimation.magneticField == 1);

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

    function processTrajectoryAxis() {
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
                undulator.effectiveDeflectingParameter = srwService.formatFloat(Math.sqrt(
                    Math.pow(undulator.horizontalDeflectingParameter, 2) +
                    Math.pow(undulator.verticalDeflectingParameter, 2)
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
        if (name === 'undulator') {
            panelState.enableField('undulator', 'effectiveDeflectingParameter', false);
        }
        if (name === 'brillianceReport') {
            processBrillianceReport();
        }
        else if (name === 'fluxAnimation') {
            processFluxAnimation();
        }
        else if (name === 'intensityReport') {
            processIntensityReport(name);
        }
        else if (name === 'sourceIntensityReport') {
            panelState.showField(name, 'magneticField', ! srwService.isApplicationMode('calculator'));
            processIntensityReport(name);
            srwService.updateSimulationGridFields();
            srwService.processIntensityLimit(name);
        }
        else if (name === 'trajectoryReport') {
            processTrajectoryReport();
            processTrajectoryAxis();
        }
        else if (name == 'powerDensityReport') {
            srwService.processIntensityLimit(name);
        }
    };

    $scope.$on('modelChanged', function(e, name) {
        if (name == 'undulator' || name == 'tabulatedUndulator') {
            // make sure the electronBeam.drift is also updated
            appState.saveQuietly('electronBeamPosition');
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

    function changeFluxReportName(modelName) {
        var tag = $($("div[data-model-name='" + modelName + "']").find('.sr-panel-heading')[0]);
        var distance = appState.models[modelName].distanceFromSource + 'm';
        var fluxType = SIREPO.APP_SCHEMA.enum.Flux[appState.models[modelName].fluxType-1][1];
        var title = SIREPO.APP_SCHEMA.view[modelName].title;
        var repName;
        if (fluxType !== 'Flux') {
            repName = title.replace(
                'Flux',
                fluxType
            ) + ' for Finite Emittance Electron Beam';
        }
        else {
            repName = title;
        }
        repName += ', ' + distance;
        tag.text(repName);
    }

    appState.whenModelsLoaded($scope, function() {
        changeFluxReportName('fluxReport');
        changeFluxReportName('fluxAnimation');
        processGaussianBeamSize();
        processIntensityReport('sourceIntensityReport');
        processIntensityReport('intensityReport');

        ['fluxReport', 'fluxAnimation'].forEach(function(f) {
            appState.watchModelFields($scope, [f + '.fluxType', f + '.distanceFromSource'], function() {
                changeFluxReportName(f);
            });
        });

        appState.watchModelFields($scope, ['fluxAnimation.method', 'fluxAnimation.magneticField'], processFluxAnimation);

        appState.watchModelFields($scope, ['gaussianBeam.sizeDefinition', 'gaussianBeam.rmsSizeX', 'gaussianBeam.rmsSizeY', 'gaussianBeam.rmsDivergenceX', 'gaussianBeam.rmsDivergenceY', 'gaussianBeam.photonEnergy'], function() {
            if (srwService.isGaussianBeam()) {
                processGaussianBeamSize();
            }
        });

        appState.watchModelFields($scope, ['intensityReport.method'], updatePrecisionLabel);

        appState.watchModelFields($scope, ['trajectoryReport.timeMomentEstimation'], processTrajectoryReport);
        appState.watchModelFields($scope, ['trajectoryReport.plotAxisY'], processTrajectoryAxis);

        appState.watchModelFields($scope, ['brillianceReport.brightnessComponent'], processBrillianceReport);

        appState.watchModelFields($scope, ['undulator.horizontalDeflectingParameter', 'undulator.verticalDeflectingParameter'], function() {
            if (panelState.isActiveField('undulator', 'horizontalDeflectingParameter')) {
                processUndulatorDefinition('K', 'horizontalDeflectingParameter', 'horizontalAmplitude');
            }
            else if (panelState.isActiveField('undulator', 'verticalDeflectingParameter')) {
                processUndulatorDefinition('K', 'verticalDeflectingParameter', 'verticalAmplitude');
            }
        });

        appState.watchModelFields($scope, ['undulator.horizontalAmplitude', 'undulator.verticalAmplitude', 'undulator.period'], function() {
            if (panelState.isActiveField('undulator', 'horizontalAmplitude')) {
                processUndulatorDefinition('B', 'horizontalDeflectingParameter', 'horizontalAmplitude');
            }
            else if (panelState.isActiveField('undulator', 'verticalAmplitude')) {
                processUndulatorDefinition('B', 'verticalDeflectingParameter', 'verticalAmplitude');
            }
            else if (panelState.isActiveField('undulator', 'period')) {
                processUndulatorDefinition('B', 'verticalDeflectingParameter', 'verticalAmplitude');
                processUndulatorDefinition('B', 'horizontalDeflectingParameter', 'horizontalAmplitude');
            }
        });
        appState.watchModelFields(
            $scope, ['sourceIntensityReport.samplingMethod'],
            srwService.updateSimulationGridFields);
        ['powerDensityReport', 'sourceIntensityReport'].forEach(function(m) {
            appState.watchModelFields($scope, [m + '.useIntensityLimits'], function() {
                srwService.processIntensityLimit(m);
            });
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
            '<div data-import-python=""></div>',
        ].join(''),
    };
});

SIREPO.app.directive('srElectronbeamEditor', function(appState, panelState, srwService, utilities) {
    return {
        restrict: 'A',
        controller: function($scope) {
            var allBeamNames = [];
            var predefinedBeams = {};

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

            function processBeamFields() {
                var isTwissDefinition = appState.models.electronBeam.beamDefinition === 't';
                var isAutoDrift = appState.models.electronBeamPosition.driftCalculationMethod === 'auto';
                // show/hide column headings and input fields for the twiss/moments sections
                panelState.showRow('electronBeam', 'horizontalEmittance', isTwissDefinition);
                panelState.showRow('electronBeam', 'rmsSizeX', ! isTwissDefinition);
                panelState.enableField('electronBeamPosition', 'drift', ! isAutoDrift);
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

            $scope.$on('sr-tabSelected', function() {
                processBeamFields();
                loadBeamList();
            });

            appState.whenModelsLoaded($scope, function() {
                appState.watchModelFields($scope, ['electronBeam.beamDefinition'], processBeamFields);
                appState.watchModelFields($scope, ['electronBeam.beamSelector', 'electronBeamPosition.driftCalculationMethod'], function() {
                    srwService.processBeamParameters();
                    processBeamFields();
                });
                ['horizontal', 'vertical'].forEach(function(dir) {
                    appState.watchModelFields(
                        $scope,
                        ['Emittance', 'Beta', 'Alpha', 'Dispersion', 'DispersionDerivative'].map(function(f) {
                            return 'electronBeam.' + dir + f;
                        }), srwService.processBeamParameters);
                });
                appState.watchModelFields(
                    $scope,
                    Object.keys(SIREPO.APP_SCHEMA.model.electronBeam).map(function(f) {
                        return 'electronBeam.' + f;
                    }),
                    utilities.debounce(checkBeamName));
            });
        },
    };
});

SIREPO.app.directive('srTabulatedundulatorEditor', function(appState, panelState, requestSender, srwService) {
    return {
        restrict: 'A',
        controller: function($scope) {

            function processUndulator() {
                panelState.showRow('undulator', 'horizontalAmplitude', ! srwService.isTabulatedUndulatorWithMagenticFile());
                ['effectiveDeflectingParameter', 'horizontalDeflectingParameter', 'verticalDeflectingParameter', 'period', 'length'].forEach(function(f) {
                    panelState.showField('undulator', f, ! srwService.isTabulatedUndulatorWithMagenticFile());
                });
                ['gap', 'phase', 'magneticFile'].forEach(function(f) {
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

            function processUndulatorLength() {
                requestSender.getApplicationData(
                    {
                        method: 'compute_undulator_length',
                        tabulated_undulator: appState.models.tabulatedUndulator,
                    },
                    function(data) {
                        if (appState.isLoaded() && data.length) {
                            appState.models.undulator.length = data.length;
                        }
                    }
                );
            }

            appState.whenModelsLoaded($scope, function() {
                processUndulator();
                appState.watchModelFields($scope, ['tabulatedUndulator.undulatorType'], processUndulator);

                appState.watchModelFields($scope, ['tabulatedUndulator.undulatorType', 'undulator.length', 'undulator.period', 'simulation.sourceType'], srwService.processBeamParameters);

                appState.watchModelFields($scope, ['tabulatedUndulator.magneticFile', 'tabulatedUndulator.gap', 'tabulatedUndulator.undulatorType'], processUndulatorLength);
            });
        },
    };
});

SIREPO.app.directive('srSimulationgridEditor', function(appState, srwService) {
    return {
        restrict: 'A',
        controller: function($scope) {
            appState.whenModelsLoaded($scope, function() {
                appState.watchModelFields(
                    $scope, ['simulation.samplingMethod', 'sourceIntensityReport.samplingMethod'],
                    srwService.updateSimulationGridFields);
                srwService.updateSimulationGridFields();
            });
        },
    };
});

SIREPO.app.directive('appHeader', function(appState, panelState, requestSender, srwService) {

    var rightNav = [
        '<div data-app-header-right="nav">',
          '<app-header-right-sim-loaded>',
            '<div data-sim-sections="">',
              '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
              '<li class="sim-section" data-ng-class="{active: nav.isActive(\'beamline\')}"><a href data-ng-click="nav.openSection(\'beamline\')"><span class="glyphicon glyphicon-option-horizontal"></span> Beamline</a></li>',
            '</div>',
          '</app-header-right-sim-loaded>',
          '<app-settings>',
            //  '<div>App-specific setting item</div>',
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
              '<a class="navbar-brand" href="/en/landing.html"><img style="width: 40px; margin-top: -10px;" src="/static/img/sirepo.gif" alt="RadiaSoft"></a>',
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
        template: [
            '<div data-ng-if="srwService.isApplicationMode(\'calculator\')">',
              navHeader('calculator', 'SR Calculator'),
              '<ul data-ng-if="nav.isLoaded()" class="nav navbar-nav navbar-right">',
                '<li data-settings-menu="nav"></li>',
                '<li><a href="https://github.com/radiasoft/sirepo/issues" target="_blank"><span class="glyphicon glyphicon-exclamation-sign"></span> Issues</a></li>',
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
              '<div data-app-header-brand="" data-app-url="{{ ::appURL() }}"></div>',
              '<div class="navbar-left" data-app-header-left="nav"></div>',
              rightNav,
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.srwService = srwService;

            $scope.appURL = function() {
                return SIREPO.APP_SCHEMA.feature_config.app_url;
            };

            $scope.showImportModal = function() {
                $('#srw-simulation-import').modal('show');
            };
        },
    };
});

SIREPO.app.directive('exportPythonLink', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            reportTitle: '@',
        },
        template: [
            '<a href data-ng-click="exportPython()">Export Python Code</a>',
        ].join(''),
        controller: function($scope) {
            $scope.exportPython = function() {
                panelState.pythonSource(
                    appState.models.simulation.simulationId,
                    panelState.findParentAttribute($scope, 'modelKey'),
                    $scope.reportTitle);
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
SIREPO.app.directive('importPython', function(appState, fileManager, fileUpload, requestSender, simulationQueue) {
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
                          '<button data-ng-click="importPythonFile(pythonFile, importArgs)" class="btn btn-primary" data-ng-disabled="isUploading || ! pythonFile">Import File</button>',
                          ' <button data-dismiss="modal" class="btn btn-default" data-ng-disabled="isUploading">Cancel</button>',
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
        template: [
            '<div data-file-field="field" data-file-type="mirror" data-model="model" data-selection-required="modelName == \'mirror\'" data-empty-selection-text="No Mirror Error">',
              '<button type="button" title="View Graph" class="btn btn-default" data-ng-click="showFileReport()"><span class="glyphicon glyphicon-eye-open"></span></button>',
            '</div>',
        ].join(''),
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

SIREPO.app.directive('modelSelectionList', function(appState, requestSender, srwService) {
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
              '</ul>',
            '</div>',
        ].join(''),
        controller: function($scope) {

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
                requestSender.getApplicationData(
                    {
                        method: 'delete_user_models',
                        electron_beam: $scope.isElectronBeam() ? item : null,
                        tabulated_undulator: $scope.isTabulatedUndulator() ? item : null,
                    },
                    $scope.loadModelList);
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
        },
        template: [
            '<div data-ng-switch="::paramInfo.fieldType">',
              '<select data-ng-switch-when="AnalyticalTreatment" number-to-string class="input-sm" data-ng-model="param[paramInfo.fieldIndex]" data-ng-options="item[0] as item[1] for item in ::analyticalTreatmentEnum"></select>',
              '<select data-ng-switch-when="WavefrontShiftTreatment" number-to-string class="input-sm" data-ng-model="param[paramInfo.fieldIndex]" data-ng-options="item[0] as item[1] for item in ::wavefrontShiftTreatmentEnum"></select>',
              '<input data-ng-disabled="disabled" data-ng-switch-when="Float" data-string-to-number="" type="text" class="srw-small-float" data-ng-class="{\'sr-disabled-text\': disabled}" data-ng-model="param[paramInfo.fieldIndex]">',
              '<input data-ng-disabled="disabled" data-ng-switch-when="Boolean" type="checkbox" data-ng-model="param[paramInfo.fieldIndex]" data-ng-true-value="1", data-ng-false-value="0">',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.analyticalTreatmentEnum = SIREPO.APP_SCHEMA.enum.AnalyticalTreatment;
            $scope.wavefrontShiftTreatmentEnum = SIREPO.APP_SCHEMA.enum.WavefrontShiftTreatment;
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
                            '<a href data-ng-click="setPropagationSection($index)">{{:: item }} <span data-ng-if="propagationInfo[$index]" data-header-tooltip="propagationInfo[$index]"></span></a>',
                          '</li>',
                        '</ul>',
                        '<div data-propagation-parameters-table="" data-section-index="{{:: $index }}" data-sections="propagationSections"  data-section-params="parametersBySection[$index]" data-prop-type-index="propTypeIndex" data-propagations="propagations" data-post-propagation="postPropagation" data-ng-repeat="item in ::propagationSections track by $index"></div>',
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
            $scope.propagationSections = ['Propagator and Resizing', 'Auto-Resize', 'Orientation', 'Grid Shift'];
            $scope.propagationInfo = [null, '<div style="text-align: left">Available for Standard Propagators</div>', null, null];
            $scope.parametersBySection = [
                [3, 4, 5, 6, 7, 8],
                [0, 1, 2],
                [12, 13, 14, 15, 16],
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
                 if( info[s][SIREPO.INFO_INDEX_LABEL] === 'Propagator' ) {
                    $scope.propTypeIndex = parseInt(s);
                    break;
                }
            }
        },
    };
});

SIREPO.app.directive('propagationParametersTable', function(appState) {
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
                  '<tr data-ng-repeat="prop in propagations track by $index" data-ng-class="{\'srw-disabled-item\': isDisabledPropagation(prop), \'sr-disabled-text\': isControlDisabledForProp(prop)}" >',
                    '<td class="input-sm" style="vertical-align: middle">{{ prop.title }}</td>',
                    '<td class="sr-center" style="vertical-align: middle" data-ng-repeat="paramInfo in ::parameterInfo track by $index">',
                      '<div data-propagation-parameter-field-editor="" data-param="prop.params" data-param-info="paramInfo" data-disabled="isControlDisabledForProp(prop)"></div>',
                    '</td>',
                  '</tr>',
                  '<tr class="warning">',
                    '<td class="input-sm">Final post-propagation</td>',
                    '<td class="sr-center" style="vertical-align: middle" data-ng-repeat="paramInfo in ::parameterInfo track by $index">',
                      '<div data-propagation-parameter-field-editor="" data-param="postPropagation" data-param-info="paramInfo" data-disabled="isControlDisabledForParams(postPropagation)"></div>',
                    '</td>',
                  '</tr>',
                '</tbody>',
              '</table>',
            '</div>',
        ].join(''),
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
                return false;
            };

            $scope.isControlDisabledForProp = function(prop) {
                var p = prop ? (prop.params || []) : [];
                return $scope.isControlDisabledForParams(p);
            };
            $scope.isControlDisabledForParams = function(params) {
                if(params[$scope.propTypeIndex] == 0) {
                    return false;
                }
                return $scope.sectionIndex == $scope.resizeSectionIndex;
            };

            initParameters();
        },
    };
});

SIREPO.app.directive('samplePreview', function(appState, requestSender, $http) {
    return {
        restrict: 'A',
        template: [
            '<div class="col-xs-5" style="white-space: nowrap">',
              '<select class="form-control" style="display: inline-block" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in enum[info[1]]"></select> ',
              '<a href target="_self" title="Download Processed Image" class="btn btn-default" data-ng-click="downloadProcessedImage()"><span class="glyphicon glyphicon-cloud-download"></span></a>',
            '</div>',
            '<div class="col-sm-12">',
              '<div class="lead text-center">',
                '<span data-ng-if="errorMessage">{{ errorMessage }}</span>',
                '<span data ng-if="isLoading && ! errorMessage">Loading image ...</span>',
                '</div>',
              '{{ loadImageFile() }}',
              '<img class="img-responsive srw-processed-image" />',
            '</div>',
          ].join(''),
        controller: function($scope) {
            var imageData;
            $scope.isLoading = false;
            $scope.errorMessage = '';

            function downloadImage(format, callback) {
                var filename = $scope.model.imageFile.match(/([^\/]+)\.\w+$/)[1] + '_processed.' + format;
                var url = requestSender.formatUrl({
                    routeName: 'getApplicationData',
                    '<filename>': filename,
                });
                var m = appState.clone($scope.model);
                m.outputImageFormat = format;
                $http.post(
                    url,
                    {
                        'simulationId': appState.models.simulation.simulationId,
                        'simulationType': SIREPO.APP_SCHEMA.simulationType,
                        'method': 'processedImage',
                        'baseImage': $scope.model.imageFile,
                        'model': m,
                    },
                    {
                        responseType: 'blob',
                    }
                ).then(
                    function (response) {
                        if (response.status == 200) {
                            callback(filename, response);
                            return;
                        }
                        error(response);
                    },
                    error);
            }

            function error(response) {
                $scope.errorMessage = 'An error occurred creating the preview image';
            }

            $scope.loadImageFile = function() {
                if (! appState.isLoaded() || imageData || $scope.isLoading) {
                    return;
                }
                $scope.isLoading = true;
                downloadImage('png', function(filename, response) {
                    imageData = response.data;
                    $scope.isLoading = false;
                    if (imageData.type == 'application/json') {
                        // an error message has been returned
                        imageData.text().then(function(text) {
                            $scope.errorMessage = JSON.parse(text).error;
                            $scope.$digest();
                        });
                    }
                    else {
                        var urlCreator = window.URL || window.webkitURL;
                        if ($('.srw-processed-image').length) {
                            $('.srw-processed-image')[0].src = urlCreator.createObjectURL(imageData);
                        }
                    }
                });
            };

            $scope.downloadProcessedImage = function() {
                if (! appState.isLoaded()) {
                    return;
                }
                downloadImage(
                    $scope.model.outputImageFormat,
                    function(filename, response) {
                        saveAs(response.data, filename);
                    });
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
        template: [
            '<div data-ng-repeat="shape in shapes track by shape.id" style="display: inline-block; margin-right: 1em">',
              '<div class="checkbox"><label><input type="checkbox" value="{{ shape.id }}" data-ng-click="toggle(shape)" data-ng-checked="isChecked(shape)">{{ shape.name }}</label></div>',
            '</div>',
        ].join(''),
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

SIREPO.app.directive('simulationStatusPanel', function(appState, beamlineService, frameCache, panelState, persistentSimulation, srwService) {
    return {
        restrict: 'A',
        scope: {
            model: '@simulationStatusPanel',
            title: '@',
        },
        template: [
            '<form name="form" class="form-horizontal" autocomplete="off" novalidate>',
              '<div data-cancelled-due-to-timeout-alert="simState"></div>',
              '<div class="progress" data-ng-if="simState.isProcessing()">',
                '<div class="progress-bar" data-ng-class="{ \'progress-bar-striped active\': simState.isInitializing() }" role="progressbar" aria-valuenow="{{ simState.getPercentComplete() }}" aria-valuemin="0" aria-valuemax="100" data-ng-attr-style="width: {{ simState.getPercentComplete() }}%"></div>',
              '</div>',

              '<div data-ng-if="simState.isProcessing()">',
                '<div class="col-sm-6">',
                  '<div data-pending-link-to-simulations="" data-sim-state="simState"></div>',
                  '<div data-ng-show="simState.isInitializing()">',
                    '<span class="glyphicon glyphicon-hourglass"></span> Initializing Simulation {{ simState.dots }}',
                  '</div>',
                  '<div data-ng-show="simState.isStateRunning() && ! simState.isInitializing()">',
                    '{{ simState.stateAsText() }} {{ simState.dots }}',
                    '<div data-ng-show="! simState.isStatePending() && particleNumber">',
                      'Completed particle: {{ particleNumber }} / {{ particleCount}}',
                    '</div>',
                    '<div data-simulation-status-timer="simState.timeData" data-ng-show="! isFluxWithApproximateMethod()"></div>',
                  '</div>',
                '</div>',
                '<div class="col-sm-6 pull-right" data-ng-show="! isFluxWithApproximateMethod()">',
                  '<button class="btn btn-default" data-ng-click="cancelPersistentSimulation()">End Simulation</button>',
                '</div>',
              '</div>',
              '<div data-ng-show="simState.isStopped() && ! isFluxWithApproximateMethod()">',
                '<div class="col-sm-6">',
                  'Simulation ',
                  '<span>{{ simState.stateAsText() }}</span>',
                  '<div data-ng-show="! simState.isStatePending() && ! simState.isInitializing() && particleNumber">',
                    'Completed particle: {{ particleNumber }} / {{ particleCount}}',
                  '</div>',
                  '<div>',
                    '<div data-simulation-status-timer="simState.timeData"></div>',
                  '</div>',
                '</div>',
            //TODO(pjm): share with simStatusPanel directive in sirepo-components.js
                '<div data-ng-if="simState.showJobSettings()">',
                  '<div class="form-group form-group-sm">',
                    '<div class="col-sm-12" data-model-field="\'jobRunMode\'" data-model-name="simState.model" data-label-size="6" data-field-size="6"></div>',
                    '<div data-sbatch-options="simState"></div>',
                  '</div>',
                '</div>',
                '<div class="col-sm-6 pull-right">',
                  '<button class="btn btn-default" data-ng-click="startSimulation()">Start New Simulation</button>',
                '</div>',
              '</div>',
            '</form>',
        ].join(''),
        controller: function($scope, appState, authState) {
            var clientFields = ['colorMap', 'aspectRatio', 'plotScale'];
            var serverFields = ['intensityPlotsWidth', 'rotateAngle', 'rotateReshape'];
            var oldModel = null;

            function copyModel() {
                oldModel = appState.cloneModel($scope.model);
                serverFields.concat(clientFields).forEach(function(f) {
                    delete oldModel[f];
                });
                return oldModel;
            }

            function handleStatus(data) {
                if (! appState.isLoaded()) {
                    return;
                }
                if (data.method && data.method != appState.models.fluxAnimation.method) {
                    // the output file on the server was generated with a different flux method
                    $scope.simState.timeData = {};
                    frameCache.setFrameCount(0);
                    return;
                }
                if (data.percentComplete) {
                    $scope.particleNumber = data.particleNumber;
                    $scope.particleCount = data.particleCount;
                }
                if (data.frameCount) {

                    if (data.frameCount != frameCache.getFrameCount($scope.model)) {
                        frameCache.setFrameCount(data.frameCount);
                        frameCache.setCurrentFrame($scope.model, data.frameIndex);
                    }
                    srwService.setShowCalcCoherence(data.calcCoherence);
                }
                if ($scope.isFluxWithApproximateMethod() && data.state == 'stopped' && ! data.frameCount) {
                    $scope.cancelPersistentSimulation();
                }
            }

            function hasReportParameterChanged() {
                // for the multiElectronAnimation, changes to the intensityPlots* fields don't require
                // the simulation to be restarted
                var model = oldModel;
                if (appState.deepEquals(model, copyModel())) {
                    return false;
                }
                return true;
            }

            $scope.cancelPersistentSimulation = function () {
                $scope.simState.cancelSimulation(function() {
                    if ($scope.isFluxWithApproximateMethod()) {
                        $scope.startSimulation();
                    }
                });
            };

            $scope.isFluxWithApproximateMethod = function() {
                return $scope.model === 'fluxAnimation'
                    && appState.isLoaded() && appState.models.fluxAnimation.method == -1;
            };

            $scope.startSimulation = function() {
                // The available jobRunModes can change. Default to parallel if
                // the current jobRunMode doesn't exist
                var j = appState.models[$scope.simState.model];
                if (j && j.jobRunMode && j.jobRunMode in authState.jobRunModeMap === false) {
                    j.jobRunMode = 'parallel';
                }
                frameCache.setFrameCount(0);
                if ($scope.model == 'multiElectronAnimation') {
                    appState.saveChanges($scope.simState.model);
                    appState.models.simulation.multiElectronAnimationTitle = beamlineService.getReportTitle($scope.model);
                }
                $scope.simState.saveAndRunSimulation('simulation');
            };

            appState.whenModelsLoaded($scope, function() {
                $scope.$on($scope.model + '.changed', function() {
                    if ($scope.simState.isReadyForModelChanges && hasReportParameterChanged()) {
                        $scope.cancelPersistentSimulation();
                        frameCache.setFrameCount(0);
                        $scope.percentComplete = 0;
                        $scope.particleNumber = 0;
                    }
                });
                copyModel();
            });

            $scope.simState = persistentSimulation.initSimulationState(
                $scope,
                srwService.computeModel($scope.model),
                handleStatus
            );
       },
    };
});

SIREPO.app.directive('beamline3d', function(appState, plotting, srwService, vtkToPNG) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            reportId: '<',
        },
        template: [
            '<div style="float: right; margin-top: -10px; margin-bottom: 5px;">',
            '<div style="display: inline-block" data-ng-repeat="dim in ::dimensions track by $index">',
            '<button data-ng-attr-class="btn btn-{{ selectedDimension == dim ? \'primary\' : \'default\' }}" data-ng-click="setCamera(dim)">{{ dim | uppercase }}{{ viewDirection[dim] > 0 ? \'+\' : \'-\' }}</button>&nbsp;',
            '</div>',
            '</div>',
            '<div style="padding-bottom:1px; clear: both; border: 1px solid black">',
              //TODO(pjm): use explicity width/height, update in resize()
              '<div class="sr-beamline3d-content" style="width: 100%; height: 50vw;"></div>',
            '</div>',
            // force the Download Report menu to appear
            '<svg></svg>',
        ].join(''),
        controller: function($scope, $element) {
            var LABEL_FONT_HEIGHT = 96;
            var LABEL_FONT = 'normal ' + LABEL_FONT_HEIGHT + 'px Arial';
            var MAX_CONDENSED_LENGTH = 3;
            var MIN_CONDENSED_LENGTH = 0.7;
            var beamline, fsRenderer, labelCanvas, labels, orientationMarker, pngCanvas;
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
                if (! beamline.length) {
                    return;
                }
                // x, y, z
                var pos = [0, 0, 0];
                // x, y, z
                var angle = [0, 0, 0];
                var rotationMatrix = vtk.Common.Core.vtkMatrixBuilder.buildFromRadian();
                var points = beamline[0].type == 'drift' ? pos.slice() : [];
                var labelSize = maxTextDimensions(beamline);
                beamline.forEach(function(item) {
                    if (item.type == 'drift') {
                        var length = item.length;
                        var p1 = [0, 0, length];
                        rotationMatrix.apply(p1);
                        pos[0] += p1[0];
                        pos[1] += p1[1];
                        pos[2] += p1[2];
                        return;
                    }
                    var center = pos.slice();
                    if (points.length) {
                        var last = points.length - 3;
                        if (center[0] == points[last]
                            && center[1] == points[last + 1]
                            && center[2] == points[last + 2]) {
                            // skip duplicate, avoids tubeFilter coincident point errors.
                            // only label the first element at one position
                            item.name = '';
                        }
                        else {
                            $.merge(points, center);
                        }
                    }
                    else {
                        $.merge(points, center);
                    }
                    var rotate = [degrees(angle[0]), degrees(angle[1]), degrees(angle[2])];
                    if (item.xAngle) {
                        center[1] += item.height / 2 * (item.xAngle < 0 ? -1 : 1);
                        angle[0] += item.xAngle;
                        rotationMatrix.rotateX(item.xAngle);
                        rotate[0] += degrees(item.xAngle / 2);
                    }
                    if (item.yAngle) {
                        center[0] += item.width / 2 * (item.yAngle < 0 ? -1 : 1);
                        angle[1] -= item.yAngle;
                        rotationMatrix.rotateY(-item.yAngle);
                        rotate[1] += degrees(-item.yAngle / 2);
                    }
                    if (item.zAngle) {
                        angle[2] += item.zAngle;
                    }
                    addBeamlineItem(item, center, rotate, labelSize);
                });
                return points;
            }

            function addBeamlineItem(item, center, rotate, labelSize) {
                addBox(item, center, rotate);
                if (item.type == 'aperture') {
                    addBox(item, center, rotate, {
                        xLength: item.height,
                        yLength: item.width,
                    });
                }
                if (options().showLabels == '1') {
                    addLabel(item, labelSize, center);
                }
            }

            function addBox(item, center, rotate, props) {
                props = $.extend({
                    xLength: item.width,
                    yLength: item.height,
                    zLength: item.size,
                    center: center,
                    rotations: rotate,
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

            function addLabel(item, labelSize, center) {
                if (! item.name || ! labelSize.width) {
                    return;
                }
                var plane = vtk.Filters.Sources.vtkPlaneSource.newInstance({
                    xResolution: 1,
                    yResolution: 1,
                });
                var actor = addActor(
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
                    elementCenter: center,
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

            function buildBeamline() {
                beamline = [];
                var pos = 0;
                if (options().includeSource == "1") {
                    //TODO(pjm): use undulator center position and length
                    beamline.push({
                        type: 'source',
                        name: 'Source',
                        size: srwService.isGaussianBeam() ? 0.1 : 2.5,
                        height: srwService.isGaussianBeam() ? 0.2 : 1,
                        width: srwService.isGaussianBeam() ? 0.2 : 1,
                    });
                }
                else {
                    if (appState.applicationState().beamline.length) {
                        pos = appState.applicationState().beamline[0].position - 1;
                    }
                }
                var prevItem;
                appState.applicationState().beamline.forEach(function(item) {
                    if (pos < item.position) {
                        var length = item.position - pos;
                        if (options().condenseBeamline == '1') {
                            if (length > MAX_CONDENSED_LENGTH) {
                                length = MAX_CONDENSED_LENGTH;
                            }
                            else if (length < MIN_CONDENSED_LENGTH) {
                                length = MIN_CONDENSED_LENGTH;
                            }
                        }
                        beamline.push({
                            type: 'drift',
                            length: length,
                        });
                        pos = item.position;
                    }
                    if (item.isDisabled) {
                        return;
                    }
                    item = appState.clone(item);
                    item.name = item.title;
                    if (item.type == 'aperture') {
                        $.extend(item, {
                            height: 1,
                            width: 0.4,
                            size: 0.1,
                            color: color('#666666'),
                        });
                    }
                    else if (item.type == 'mirror') {
                        item.opacity = 0.4;
                        //TODO(pjm): unit conversion
                        item.grazingAngle *= 1e-3;
                        if (item.orientation == 'x') {
                            $.extend(item, {
                                height: mirrorSize(item.verticalTransverseSize * 1e-3),
                                width: 0.1,
                                size: mirrorSize(item.horizontalTransverseSize * 1e-3),
                                yAngle: item.grazingAngle,
                            });
                        }
                        else {
                            $.extend(item, {
                                height: 0.1,
                                width: mirrorSize(item.horizontalTransverseSize * 1e-3),
                                size: mirrorSize(item.verticalTransverseSize * 1e-3),
                                xAngle: item.grazingAngle,
                            });
                        }
                    }
                    else if (item.type.search(/mirror|grating|crystal/i) >= 0) {
                        item.grazingAngle *= 1e-3;
                        item.opacity = 0.4;
                        if (item.type == 'crystal') {
                            $.extend(item, {
                                opacity: 0.1,
                                color: color('#9269ff'),
                                normalVectorX: item.nvx,
                                normalVectorY: item.nvy,
                            });
                            if (prevItem && prevItem.type == 'crystal' && item.position == prevItem.position) {
                                // add a small drift between crystals if necessary
                                item.name = '';
                                beamline.push({
                                    type: 'drift',
                                    length: 0.2,
                                });
                            }
                        }
                        else if (item.type == 'grating') {
                            item.color = color('#ff6992');
                        }
                        if (Math.abs(item.normalVectorX) > Math.abs(item.normalVectorY)) {
                            // horizontal mirror
                            $.extend(item, {
                                height: mirrorSize(item.sagittalSize || 0),
                                width: 0.1,
                                size: mirrorSize(item.tangentialSize || 0),
                                yAngle: Math.abs(item.grazingAngle),
                            });
                            if (item.normalVectorX < 0) {
                                item.yAngle = - Math.abs(item.yAngle);
                            }
                        }
                        else {
                            // vertical mirror
                            $.extend(item, {
                                height: 0.1,
                                width: mirrorSize(item.sagittalSize || 0),
                                size: mirrorSize(item.tangentialSize || 0),
                                xAngle: Math.abs(item.grazingAngle),
                            });
                            if (item.normalVectorY > 0) {
                                item.xAngle = - Math.abs(item.xAngle);
                            }
                        }
                    }
                    else if (item.type == 'lens') {
                        $.extend(item, {
                            opacity: 0.3,
                            size: 0.1,
                            width: 0.5,
                            height: 0.5,
                            color: color('#ffff99'),
                        });
                    }
                    else if (item.type == 'zonePlate') {
                        $.extend(item, {
                            size: 0.1,
                            width: 0.8,
                            height: 0.8,
                            color: color('#000000'),
                        });
                    }
                    else if (item.type == 'crl') {
                        $.extend(item, {
                            //TODO(pjm): how to size a crl?
                            width: 0.5,
                            height: 0.5,
                            size: 0.5,
                            color: color('#3962af'),
                        });
                    }
                    else if (item.type == 'fiber') {
                        $.extend(item, {
                            size: 0.5,
                            width: 0.15,
                            height: 0.15,
                            color: color('#999999'),
                        });
                    }
                    else if (item.type == 'obstacle') {
                        $.extend(item, {
                            size: 0.15,
                            width: 0.15,
                            height: 0.15,
                            color: color('#000000'),
                        });
                    }
                    else if (item.type == 'watch') {
                        $.extend(item, {
                            width: 0.5,
                            height: 0.5,
                            size: 0.25,
                            color: color('#ffff99'),
                        });
                    }
                    else {
                        return;
                    }
                    beamline.push(item);
                    prevItem = item;
                });
            }

            function color(v) {
                return vtk.Common.Core.vtkMath.hex2float(v);
            }

            function degrees(radians) {
                return radians * 180 / Math.PI;
            }

            function itemText(item) {
                if (item.name) {
                    var res = item.name;
                    if (options().showPosition == '1' && item.position) {
                        res += ', ' + parseFloat(item.position).toFixed(1) + 'm';
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
                return Math.max(Math.min(size, 1), 0.5);
            }

            function options() {
                return appState.applicationState().beamline3DReport;
            }

            function radians(degrees) {
                return degrees * Math.PI / 180;
            }

            function refresh(colInfo) {
                //TODO(pjm): use colInfo from beamline_orient.dat to set orientation
                removeActors();
                buildBeamline();
                labels = [];
                $scope.selectedDimension = null;
                $scope.viewDirection = {
                    x: 1,
                    y: 1,
                    z: 1,
                };
                addBeam(addBeamline());
                addOrientationMarker();
                $scope.setCamera($scope.dimensions[0]);
                pngCanvas.copyCanvas();
            }

            function removeActors() {
                var renderer = fsRenderer.getRenderer();
                renderer.getActors().forEach(function(actor) {
                    renderer.removeActor(actor);
                });
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
                pngCanvas.destroy();
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
                fsRenderer.getInteractor().onAnimation(vtk.macro.debounce(updateOrientation, 250));
                pngCanvas = vtkToPNG.pngCanvas($scope.reportId, fsRenderer, $element);
            };

            $scope.load = function(json) {
                refresh(json.cols);
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
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

// field handlers for watchpointReports.
// normal model editors have unique names and don't require separate directives like this
SIREPO.app.directive('watchpointHandler', function(appState, beamlineService, panelState, srwService) {
    return {
        restrict: 'A',
        controller: function($scope) {
            var modelKey = beamlineService.watchpointReportName($scope.item.id);

            function processIntensityLimit() {
                srwService.processIntensityLimit('watchpointReport', modelKey);
            }

            appState.watchModelFields(
                $scope,
                [modelKey + '.useIntensityLimits'],
                processIntensityLimit);

            $scope.$on('sr-tabSelected', processIntensityLimit);
        },
    };
});
