'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.appDefaultSimulationValues.simulation.sourceType = 'u';
SIREPO.INCLUDE_EXAMPLE_FOLDERS = true;
SIREPO.SINGLE_FRAME_ANIMATION = ['coherenceXAnimation', 'coherenceYAnimation', 'fluxAnimation', 'multiElectronAnimation'];
SIREPO.PLOTTING_COLOR_MAP = 'grayscale';
SIREPO.PLOTTING_SHOW_FWHM = true;
//TODO(pjm): provide API for this, keyed by field type
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="BeamList">',
      '<div data-model-selection-list="" data-model-name="modelName" data-model="model" data-field="field" data-field-class="fieldClass"></div>',
    '</div>',
    '<div data-ng-switch-when="UndulatorList">',
      '<div data-model-selection-list="" data-model-name="modelName" data-model="model" data-field="field" data-field-class="fieldClass"></div>',
    '</div>',
    '<div data-ng-switch-when="ImageFile" class="col-sm-7">',
      '<div data-image-file-field="" data-model="model" data-field="field"></div>',
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
].join('');
SIREPO.appDownloadLinks = [
    '<li data-lineout-csv-link="x"></li>',
    '<li data-lineout-csv-link="y"></li>',
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

SIREPO.app.factory('srwService', function(appState, appDataService, beamlineService, panelState, activeSection, $rootScope, $location, $route) {
    var self = {};
    self.applicationMode = 'default';
    appDataService.applicationMode = null;
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

    self.isApplicationMode = function(name) {
        return name == self.applicationMode;
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

    self.setShowCalcCoherence = function(isShown) {
        self.showCalcCoherence = isShown;
    };

    self.showBrillianceReport = function() {
        return self.isIdealizedUndulator();
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
        if($route.current && $route.current.$$route) {
            $route.current.$$route.reloadOnSearch = true;
        }
    });
    $rootScope.$on('$routeChangeSuccess', function() {
        var search = $location.search();
        if(search) {
            self.applicationMode = search.application_mode || 'default';
            appDataService.applicationMode = self.applicationMode;
            beamlineService.setEditable(self.applicationMode == 'default');
            if(activeSection.getActiveSection() === 'beamline') {
                // use the coherence from the url query if it exists
                if(search.coherence) {
                    beamlineService.coherence = search.coherence;
                }
                // if coherence was not previously set, set it to full.  Otherwise keep the stored value
                else {
                    if(! beamlineService.coherence) {
                        beamlineService.coherence = 'full';
                    }
                }
            }
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

SIREPO.app.controller('SRWBeamlineController', function (appState, beamlineService, panelState, requestSender, srwService, $scope, simulationQueue, $location, activeSection, $route) {
    var self = this;
    var grazingAngleElements = ['ellipsoidMirror', 'grating', 'sphericalMirror', 'toroidalMirror'];
    self.mirrorReportId = Math.floor(Math.random() * Number.MAX_SAFE_INTEGER);
    self.appState = appState;
    self.beamlineService = beamlineService;
    self.srwService = srwService;
    self.postPropagation = [];
    self.propagations = [];
    self.singleElectron = true;
    self.beamlineModels = ['beamline', 'propagation', 'postPropagation'];
    self.toolbarItemNames = [
        ['Refractive/Diffractive optics and transmission objects', ['lens', 'crl', 'zonePlate', 'fiber', 'aperture', 'obstacle', 'mask', 'sample']],
        ['Mirrors', ['mirror', 'sphericalMirror', 'ellipsoidMirror', 'toroidalMirror']],
        ['Elements of monochromator', ['crystal', 'grating']],
        'watch',
    ];

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

    function computeCrystalInit(item) {
        if (item.material != 'Unknown') {
            computeFields('compute_crystal_init', item, ['dSpacing', 'psi0r', 'psi0i', 'psiHr', 'psiHi', 'psiHBr', 'psiHBi']);
        }
    }

    function computeCrystalOrientation(item) {
        computeFields('compute_crystal_orientation', item, ['nvx', 'nvy', 'nvz', 'tvx', 'tvy', 'grazingAngle']);
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
            computeFields('compute_grazing_angle', item, ['normalVectorZ', 'normalVectorY', 'normalVectorX', 'tangentialVectorY', 'tangentialVectorX']);
        }
    }

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
        ['areaXStart', 'areaXEnd', 'areaYStart', 'areaYEnd'].forEach(function(f) {
            panelState.showField('sample', f, item.cropArea == '1');
        });
        ['tileRows', 'tileColumns'].forEach(function(f) {
            panelState.showField('sample', f, item.tileImage == '1');
        });
        panelState.showField('sample', 'rotateReshape', item.rotateAngle);
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
            if (name === 'mask' || name === 'sample') {
                updateMaterialFields(item);
                if (name == 'sample') {
                    updateSampleFields(item);
                }
            }
            if (grazingAngleElements.indexOf(name) >= 0) {
                updateVectorFields(item);
            }
        }
        panelState.showField('watchpointReport', 'fieldUnits', srwService.isGaussianBeam());
        panelState.showField('initialIntensityReport', 'fieldUnits', srwService.isGaussianBeam());
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

    self.setReloadOnSearch = function(value) {
        if($route.current && $route.current.$$route) {
            $route.current.$$route.reloadOnSearch = value;
        }
    };
    self.setSingleElectron = function(value) {
        value = !!value;
        if (value != self.singleElectron) {
            simulationQueue.cancelAllItems();
        }
        self.singleElectron = value;

        // store the coherence
        beamlineService.coherence = value ? 'full' : 'partial';
        var currentCoherence = $location.search().coherence || 'full';
        if (beamlineService.coherence != currentCoherence) {
            // only set search if changed - it causes a page reload
            $location.search('coherence', beamlineService.coherence);
        }
    };

    self.showPropagationModal = function() {
        self.prepareToSave();
        beamlineService.dismissPopup();
        $('#srw-propagation-parameters').modal('show');
    };

    self.showSimulationGrid = function() {
        panelState.showModalEditor('simulationGrid');
    };

    self.showTabs = function() {
        if (beamlineService.getWatchItems().length === 0) {
            if(self.isMultiElectron()) {
                self.setSingleElectron(true);
            }
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
        // set the single electron state based on the stored coherence value
        if(beamlineService.coherence) {
            if (appState.models.beamline.length == 0) {
                self.setSingleElectron(true);
            }
            else {
                self.setSingleElectron(beamlineService.coherence !== 'partial');
            }
        }

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
        beamlineService.watchBeamlineField($scope, 'crystal', ['material', 'energy', 'h', 'k', 'l'], computeCrystalInit, true);
        beamlineService.watchBeamlineField($scope, 'crystal', ['diffractionAngle', 'dSpacing', 'asymmetryAngle', 'psi0r', 'psi0i', 'rotationAngle'], computeCrystalOrientation, true);
        beamlineService.watchBeamlineField($scope, 'sample', ['cropArea', 'tileImage', 'rotateAngle'], updateSampleFields);
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

    $scope.$on('$destroy', function() {
        // clear the coherence if we went away from the beamline tab
        // but remember it in the service
        if(activeSection.getActiveSection() !== 'beamline') {
            $location.search('coherence', null);
        }
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
                    }
                    else {
                        appState.models.undulator.verticalAmplitude = formatFloat(data.amplitude);
                    }
                }
                else if (undulatorDefinition === 'B') {
                    if (amplitude === 'horizontalAmplitude') {
                        appState.models.undulator.horizontalDeflectingParameter = formatFloat(data.undulator_parameter);
                    }
                    else {
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
        }
        else if (name === 'trajectoryReport') {
            processTrajectoryReport();
            processTrajectoryAxis();
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
        disableBasicEditorBeamName();
        processUndulator();
        processGaussianBeamSize();
        processIntensityReport('sourceIntensityReport');
        processIntensityReport('intensityReport');

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

        appState.watchModelFields($scope, ['fluxAnimation.method', 'fluxAnimation.magneticField'], processFluxAnimation);

        appState.watchModelFields($scope, ['gaussianBeam.sizeDefinition', 'gaussianBeam.rmsSizeX', 'gaussianBeam.rmsSizeY', 'gaussianBeam.rmsDivergenceX', 'gaussianBeam.rmsDivergenceY', 'gaussianBeam.photonEnergy'], function() {
            if (srwService.isGaussianBeam()) {
                processGaussianBeamSize();
            }
        });

        appState.watchModelFields($scope, ['intensityReport.method'], updatePrecisionLabel);

        appState.watchModelFields($scope, ['tabulatedUndulator.undulatorType', 'undulator.length', 'undulator.period', 'simulation.sourceType'], processBeamParameters);

        appState.watchModelFields($scope, ['tabulatedUndulator.undulatorType'], processUndulator);

        appState.watchModelFields($scope, ['tabulatedUndulator.magneticFile', 'tabulatedUndulator.gap', 'tabulatedUndulator.undulatorType'], function() {
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
        });

        appState.watchModelFields($scope, ['trajectoryReport.timeMomentEstimation'], processTrajectoryReport);
        appState.watchModelFields($scope, ['trajectoryReport.plotAxisY'], processTrajectoryAxis);

        appState.watchModelFields($scope, ['brillianceReport.brightnessComponent'], processBrillianceReport);

        appState.watchModelFields($scope, ['undulator.horizontalDeflectingParameter', 'undulator.verticalDeflectingParameter'], function() {
            if (isActiveField('undulator', 'horizontalDeflectingParameter')) {
                processUndulatorDefinition('K', 'horizontalDeflectingParameter', 'horizontalAmplitude');
            }
            else if (isActiveField('undulator', 'verticalDeflectingParameter')) {
                processUndulatorDefinition('K', 'verticalDeflectingParameter', 'verticalAmplitude');
            }
        });

        appState.watchModelFields($scope, ['undulator.horizontalAmplitude', 'undulator.verticalAmplitude', 'undulator.period'], function() {
            if (isActiveField('undulator', 'horizontalAmplitude')) {
                processUndulatorDefinition('B', 'horizontalDeflectingParameter', 'horizontalAmplitude');
            }
            else if (isActiveField('undulator', 'verticalAmplitude')) {
                processUndulatorDefinition('B', 'verticalDeflectingParameter', 'verticalAmplitude');
            }
            else if (isActiveField('undulator', 'period')) {
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
            '<div data-import-python=""></div>',
        ].join(''),
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
        return [
            '<div class="navbar-header">',
              '<a class="navbar-brand" href="/en/landing.html"><img style="width: 40px; margin-top: -10px;" src="/static/img/sirepo.gif" alt="RadiaSoft"></a>',
              '<div class="navbar-brand"><a href="/old#/srw">',SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_NAME].longName,'</a>',
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
              '<div data-app-header-brand="nav"></div>',
              '<div class="navbar-left" data-app-header-left="nav"></div>',
              rightNav,
            '</div>',
        ].join(''),
        controller: function($scope) {

            $scope.srwService = srwService;

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

            function handleStatus(data) {
                $scope.isUploading = false;
                if (data.error) {
                    $scope.fileUploadError = data.error;
                    appState.deleteSimulation(appState.models.simulation.simulationId, function() {});
                }
                appState.clearModels();
                if (data.simulationId) {
                    hideAndRedirect(data.simulationId);
                }
            }

            function hideAndRedirect(simId) {
                $('#srw-simulation-import').modal('hide');
                requestSender.localRedirect('source', {
                    ':simulationId': simId,
                });
            }

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
                        }),
                    function(data) {
                        $scope.isUploading = false;
                        if (data.error) {
                            $scope.fileUploadError = data.error;
                        }
                        else if (data.models.backgroundImport) {
                            $scope.isUploading = true;
                            appState.loadModels(data.models.simulation.simulationId, function() {
                                simulationQueue.addTransientItem(
                                    'backgroundImport',
                                    appState.applicationState(),
                                    handleStatus);
                            });
                        }
                        else {
                            hideAndRedirect(data.models.simulation.simulationId);
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

SIREPO.app.directive('imageFileField', function(appState, requestSender, $http, errorService) {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            model: '=',
        },
        template: [
            '<div data-file-field="field" data-file-type="sample" data-model="model" data-selection-required="true" data-empty-selection-text="Select Image File">',
              '<a href target="_self" title="Download Processed Image" class="btn btn-default" data-ng-click="downloadProcessedImage()"><span class="glyphicon glyphicon-filter"></span></a>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.downloadProcessedImage = function() {
                if (!appState.isLoaded()) {
                    return;
                }
                var m = $scope.model.imageFile.match(/(([^\/]+)\.\w+)$/);
                if (!m) {
                    throw $scope.model.imageFile + ': invalid imageFile name';
                }
                var fn = m[2] + '_processed.' + $scope.model.outputImageFormat;

                //TODO(pjm): refactor this into a method in sirepo.js, remove $http
                var url = requestSender.formatUrl({
                    routeName: 'getApplicationData',
                    '<filename>': fn
                });
                var err = function (response) {
                    errorService.alertText('Download failed: status=' + response.status);
                };
                //TODO: Error handling
                $http.post(
                    url,
                    {
                        'simulationId': appState.models.simulation.simulationId,
                        'simulationType': SIREPO.APP_SCHEMA.simulationType,
                        'method': 'processedImage',
                        'baseImage': m[1],
                        'model': $scope.model,
                    },
                    {responseType: 'blob'}
                ).then(
                    function (response) {
                        if (response.status == 200) {
                            saveAs(response.data, fn);
                            return;
                        }
                        err(response);
                    },
                    err);
            };
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
        link: function link(scope) {
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
            disabled: '=',
        },
        template: [
            '<div data-ng-switch="::paramInfo.fieldType">',
              '<select data-ng-switch-when="AnalyticalTreatment" number-to-string class="input-sm" data-ng-model="param[paramInfo.fieldIndex]" data-ng-options="item[0] as item[1] for item in ::analyticalTreatmentEnum"></select>',
              '<input data-ng-disabled="disabled" data-ng-switch-when="Float" data-string-to-number="" type="text" class="srw-small-float" data-ng-class="{\'sr-disabled-text\': disabled}" data-ng-model="param[paramInfo.fieldIndex]">',
              '<input data-ng-disabled="disabled" data-ng-switch-when="Boolean" type="checkbox" data-ng-model="param[paramInfo.fieldIndex]" data-ng-true-value="1", data-ng-false-value="0">',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.analyticalTreatmentEnum = SIREPO.APP_SCHEMA.enum.AnalyticalTreatment;
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
            $scope.propagationSections = ['Propagator and Resizing', 'Auto-Resize', 'Orientation'];
            $scope.propagationInfo = [null, '<div style="text-align: left">Available for Standard Propagators</div>', null];
            $scope.parametersBySection = [
                [3, 4, 5, 6, 7, 8],
                [0, 1, 2],
                [12, 13, 14, 15, 16],
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
                    '<td class="input-sm">Final post-propagation (resize)</td>',
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

SIREPO.app.directive('simulationStatusPanel', function(appState, beamlineService, frameCache, persistentSimulation, srwService) {
    return {
        restrict: 'A',
        scope: {
            model: '@simulationStatusPanel',
            title: '@',
        },
        template: [
            '<form name="form" class="form-horizontal" autocomplete="off" novalidate>',
              '<div class="progress" data-ng-if="simState.isProcessing()">',
                '<div class="progress-bar" data-ng-class="{ \'progress-bar-striped active\': simState.isInitializing() }" role="progressbar" aria-valuenow="{{ simState.getPercentComplete() }}" aria-valuemin="0" aria-valuemax="100" data-ng-attr-style="width: {{ simState.getPercentComplete() }}%"></div>',
              '</div>',

              '<div data-ng-if="simState.isProcessing()">',
                '<div class="col-sm-6">',
                  '<div data-ng-show="simState.isStatePending()">',
                    '<span class="glyphicon glyphicon-hourglass"></span> {{ simState.stateAsText() }} {{ simState.dots }}',
                  '</div>',
                  '<div data-ng-show="simState.isInitializing()">',
                    '<span class="glyphicon glyphicon-hourglass"></span> Initializing Simulation {{ simState.dots }}',
                  '</div>',
                  '<div data-ng-show="simState.isStateRunning() && ! simState.isInitializing()">',
                    '{{ simState.stateAsText() }} {{ simState.dots }}',
                    '<div data-ng-show="! simState.isStatePending() && particleNumber">',
                      'Completed particle: {{ particleNumber }} / {{ particleCount}}',
                    '</div>',
                    '<div data-simulation-status-timer="simState.timeData" data-ng-show="! hasFluxCompMethod() || ! isApproximateMethod()"></div>',
                  '</div>',
                '</div>',
                '<div class="col-sm-6 pull-right" data-ng-show="! hasFluxCompMethod() || ! isApproximateMethod()">',
                  '<button class="btn btn-default" data-ng-click="cancelPersistentSimulation()">End Simulation</button>',
                '</div>',
              '</div>',
              '<div data-ng-show="simState.isStopped()">',
                '<div class="col-sm-6">',
                  'Simulation ',
                  '<span>{{ simState.stateAsText() }}</span>',
                  '<div data-ng-show="! simState.isStatePending() && ! simState.isInitializing() && particleNumber">',
                    'Completed particle: {{ particleNumber }} / {{ particleCount}}',
                  '</div>',
                  '<div data-ng-show="! hasFluxCompMethod() || ! isApproximateMethod()">',
                    '<div data-simulation-status-timer="simState.timeData"></div>',
                  '</div>',
                '</div>',
                '<div class="col-sm-6 pull-right" data-ng-show="! hasFluxCompMethod() || ! isApproximateMethod()">',
                  '<button class="btn btn-default" data-ng-click="startSimulation()">Start New Simulation</button>',
                '</div>',
              '</div>',
            '</form>',
        ].join(''),
        controller: function($scope) {

            //TODO(pjm): share with template/srw.py _REPORT_STYLE_FIELDS
            var plotFields = ['intensityPlotsWidth', 'intensityPlotsScale', 'colorMap', 'plotAxisX', 'plotAxisY', 'aspectRatio'];
            var multiElectronAnimation = null;
            $scope.frameCount = 1;

            function copyMultiElectronModel() {
                multiElectronAnimation = appState.cloneModel('multiElectronAnimation');
                plotFields.forEach(function(f) {
                    delete multiElectronAnimation[f];
                });
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
                if (data.frameId && (data.frameId != $scope.frameId)) {
                    $scope.frameId = data.frameId;
                    $scope.frameCount++;
                    frameCache.setFrameCount($scope.frameCount);
                    frameCache.setCurrentFrame($scope.model, $scope.frameCount - 1);
                    srwService.setShowCalcCoherence(data.calcCoherence);
                }
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

            $scope.cancelPersistentSimulation = function () {
                $scope.simState.cancelSimulation(function() {
                    if ($scope.hasFluxCompMethod() && $scope.isApproximateMethod()) {
                        $scope.startSimulation();
                    }
                });
            };

            $scope.hasFluxCompMethod = function () {
                return $scope.model === 'fluxAnimation';
            };

            $scope.isApproximateMethod = function () {
                return appState.isLoaded() && appState.models.fluxAnimation.method == -1;
            };

            $scope.startSimulation = function() {
                if ($scope.model == 'multiElectronAnimation') {
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
                copyMultiElectronModel();
            });

            var coherentArgs = $.merge([SIREPO.ANIMATION_ARGS_VERSION + '1'], plotFields);
            $scope.simState = persistentSimulation.initSimulationState($scope, $scope.model, handleStatus, {
                multiElectronAnimation: coherentArgs,
                fluxAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1'],
                coherenceXAnimation: coherentArgs,
                coherenceYAnimation: coherentArgs,
            });
       },
    };
});
