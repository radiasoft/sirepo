'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;
var READ_ONLY_EBEAM = false;

SIREPO.appLocalRoutes.beamline = '/beamline/:simulationId';
SIREPO.appDefaultSimulationValues.simulation.sourceType = 'u';

SIREPO.app.config(function($routeProvider, localRoutesProvider) {
    var localRoutes = localRoutesProvider.$get();
    $routeProvider
        .when(localRoutes.source, {
            controller: 'SRWSourceController as source',
            templateUrl: '/static/html/srw-source.html?' + SIREPO.APP_VERSION,
        })
        .when(localRoutes.beamline, {
            controller: 'SRWBeamlineController as beamline',
            templateUrl: '/static/html/srw-beamline.html?' + SIREPO.APP_VERSION,
        });
});

SIREPO.app.factory('srwService', function(appState, $rootScope, $location) {
    var self = {};
    self.applicationMode = 'default';
    self.originalCharacteristicEnum = null;
    self.singleElectronCharacteristicEnum = null;

    function initCharacteristic() {
        if (self.originalCharacteristicEnum)
            return;
        self.originalCharacteristicEnum = SIREPO.APP_SCHEMA.enum.Characteristic;
        var characteristic = appState.clone(SIREPO.APP_SCHEMA.enum.Characteristic);
        characteristic.splice(1, 1);
        for (var i = 0; i < characteristic.length; i++)
            characteristic[i][1] = characteristic[i][1].replace(/Single-Electron /g, '');
        self.singleElectronCharacteristicEnum = characteristic;
    }

    function isSelected(sourceType) {
        if (appState.isLoaded())
            return appState.applicationState().simulation.sourceType == sourceType;
        return false;
    }

    self.getReportTitle = function(modelName, itemId) {
        var savedModelValues = appState.applicationState();
        if (itemId && savedModelValues.beamline) {
            for (var i = 0; i < savedModelValues.beamline.length; i += 1) {
                if (savedModelValues.beamline[i].id == itemId) {
                    return 'Intensity at ' + savedModelValues.beamline[i].title + ' Report, '
                        + savedModelValues.beamline[i].position + 'm';
                }
            }
        }
        var model = savedModelValues[modelName];
        var distance = '';
        if (model && 'distanceFromSource' in model)
            distance = ', ' + model.distanceFromSource + 'm';
        else if (appState.isAnimationModelName(modelName))
            distance = '';
        else if (appState.isReportModelName(modelName) && savedModelValues.beamline && savedModelValues.beamline.length)
            distance = ', ' + savedModelValues.beamline[0].position + 'm';
        return appState.viewInfo(modelName).title + distance;
    };

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
        if (appState.isLoaded())
            return appState.models.electronBeam.isReadOnly ? READ_ONLY_EBEAM : false;
        return false;
    };

    self.isTabulatedUndulator = function() {
        return isSelected('t');
    };

    self.setupWatchpointDirective = function($scope) {
        var modelKey = 'watchpointReport' + $scope.itemId;
        $scope.modelAccess = {
            modelKey: modelKey,
            getData: function() {
                return appState.models[modelKey];
            },
        };

        $scope.reportTitle = function() {
            return self.getReportTitle('watchpointReport', $scope.itemId);
        };
    };

    $rootScope.$on('$routeChangeSuccess', function() {
        var search = $location.search();
        if (search && search.application_mode)
            self.applicationMode = search.application_mode;
    });

    appState.whenModelsLoaded($rootScope, function() {
        initCharacteristic();
        // don't show multi-electron values in certain cases
        SIREPO.APP_SCHEMA.enum.Characteristic = (self.isApplicationMode('wavefront') || self.isGaussianBeam())
            ? self.singleElectronCharacteristicEnum
            : self.originalCharacteristicEnum;
    });

    return self;
});

SIREPO.app.controller('SRWBeamlineController', function (appState, panelState, requestSender, srwService, $scope, simulationQueue) {
    var self = this;

    var crystalDefaults = {
            type: 'crystal',
            title: 'Crystal',
            material: 'Unknown',
            h: 1,
            k: 1,
            l: 1,
            energy: 9000.0,
            grazingAngle: 1.5707963,
            asymmetryAngle: 0.0,
            rotationAngle: 0.0,
            crystalThickness: 0.01,
            dSpacing: null,  // 3.13557135638,
            psi0r: null,  // -1.20811311251e-05,
            psi0i: null,  // 2.26447987254e-07,
            psiHr: null,  // -6.38714117487e-06,
            psiHi: null,  // 1.58100017439e-07,
            psiHBr: null,  // -6.38714117487e-06,
            psiHBi: null,  // 1.58100017439e-07,
            nvx: null,  // 0.0,
            nvy: null,  // 0.0,
            nvz: null,  // -1.0,
            tvx: null,  // 1.0,
            tvy: null,  // 0.0,
            heightProfileFile: null,
            orientation: 'x',
            heightAmplification: 1,
    };

    self.toolbarItems = [
        //TODO(pjm): move default values to separate area
        {type:'aperture', title:'Aperture', horizontalSize:1, verticalSize:1, shape:'r', horizontalOffset:0, verticalOffset:0},
        {type:'crl', title:'CRL', focalPlane:2, material:'Be', method: 'server', refractiveIndex:4.20756805e-06, attenuationLength:7.31294e-03, focalDistance:null, absoluteFocusPosition:null, shape:1,
         horizontalApertureSize:1, verticalApertureSize:1, tipRadius:1.5e3, radius:1.5e-3, numberOfLenses:3, tipWallThickness:80, wallThickness:80e-6},
        {type:'fiber', title:'Fiber', focalPlane:1, method:'server', externalMaterial:'User-defined', externalRefractiveIndex:4.20756805e-06, externalAttenuationLength:7312.94e-06, externalDiameter:100.e-06, coreMaterial:'User-defined', coreRefractiveIndex:4.20756805e-06, coreAttenuationLength:7312.94e-06, coreDiameter:10.e-06, horizontalCenterPosition:0.0, verticalCenterPosition:0.0},
        {type:'grating', title:'Grating', tangentialSize:0.2, sagittalSize:0.015, grazingAngle:12.9555790185373, normalVectorX:0, normalVectorY:0.99991607766, normalVectorZ:-0.0129552166147, tangentialVectorX:0, tangentialVectorY:0.0129552166147, diffractionOrder:1, grooveDensity0:1800, grooveDensity1:0.08997, grooveDensity2:3.004e-6, grooveDensity3:9.7e-11, grooveDensity4:0,},
        {type:'lens', title:'Lens', horizontalFocalLength:3, verticalFocalLength:1.e+23, horizontalOffset:0, verticalOffset:0},
        {type:'ellipsoidMirror', title:'Ellipsoid Mirror', focalLength:1.7, grazingAngle:3.6, tangentialSize:0.5, sagittalSize:0.01, normalVectorX:0, normalVectorY:0.9999935200069984, normalVectorZ:-0.0035999922240050387, tangentialVectorX:0, tangentialVectorY:-0.0035999922240050387, heightProfileFile:null, orientation:'x', heightAmplification:1},
        {type:'mirror', title:'Flat Mirror', orientation:'x', grazingAngle:3.1415926, heightAmplification:1, horizontalTransverseSize:1, verticalTransverseSize:1, heightProfileFile:'mirror_1d.dat'},
        {type:'sphericalMirror', title:'Spherical Mirror', 'radius':1049, grazingAngle:3.1415926, 'tangentialSize':0.3, 'sagittalSize':0.11, 'normalVectorX':0, 'normalVectorY':0.9999025244842406, 'normalVectorZ':-0.013962146326506367,'tangentialVectorX':0, 'tangentialVectorY':0.013962146326506367, heightProfileFile:null, orientation:'x', heightAmplification:1},
        {type:'obstacle', title:'Obstacle', horizontalSize:0.5, verticalSize:0.5, shape:'r', horizontalOffset:0, verticalOffset:0},
        crystalDefaults,
        {type:'mask', title:'Mask', material:'User-defined', method:'server', refractiveIndex:1.0, attenuationLength:1.0,
         maskThickness:1.0, gridShape:0, gridTiltAngle:0.4363323129985824, horizontalSamplingInterval:7.32e-01, verticalSamplingInterval:7.32e-01,
         horizontalGridPitch:20, verticalGridPitch:20, horizontalPixelsNumber:1024, verticalPixelsNumber:1024,
         horizontalGridsNumber:21, verticalGridsNumber:21, horizontalGridDimension:5, verticalGridDimension:5,
         horizontalMaskCoordinate:0.0, verticalMaskCoordinate:0.0},
        {type:'watch', title:'Watchpoint'},
    ];
    self.panelState = panelState;
    self.srwService = srwService;
    self.activeItem = null;
    self.postPropagation = [];
    self.propagations = [];
    self.analyticalTreatmentEnum = SIREPO.APP_SCHEMA.enum.AnalyticalTreatment;
    self.singleElectron = true;

    function addItem(item) {
        var newItem = appState.clone(item);
        newItem.id = appState.maxId(appState.models.beamline) + 1;
        newItem.showPopover = true;
        if (appState.models.beamline.length) {
            newItem.position = parseFloat(appState.models.beamline[appState.models.beamline.length - 1].position) + 1;
        }
        else {
            newItem.position = 20;
        }
        if (newItem.type == 'ellipsoidMirror')
            newItem.firstFocusLength = newItem.position;
        if (newItem.type == 'watch')
            appState.models[watchpointReportName(newItem.id)] = appState.cloneModel('initialIntensityReport');
        appState.models.beamline.push(newItem);
        self.dismissPopup();
    }

    function calculatePropagation() {
        if (! appState.isLoaded())
            return;
        var beamline = appState.models.beamline;
        if (! appState.models.propagation)
            appState.models.propagation = {};
        var propagation = appState.models.propagation;
        self.propagations = [];
        for (var i = 0; i < beamline.length; i++) {
            if (! propagation[beamline[i].id]) {
                propagation[beamline[i].id] = [
                    defaultItemPropagationParams(),
                    defaultDriftPropagationParams(),
                ];
            }
            var p = propagation[beamline[i].id];
            if (beamline[i].type != 'watch')
                self.propagations.push({
                    title: beamline[i].title,
                    params: p[0],
                });
            if (i == beamline.length - 1)
                break;
            var d = parseFloat(beamline[i + 1].position) - parseFloat(beamline[i].position);
            if (d > 0) {
                self.propagations.push({
                    title: 'Drift ' + formatFloat(d) + 'm',
                    params: p[1],
                });
            }
        }
        if (! appState.models.postPropagation || appState.models.postPropagation.length === 0)
            appState.models.postPropagation = defaultItemPropagationParams();
        self.postPropagation = appState.models.postPropagation;
    }

    function defaultItemPropagationParams() {
        return [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0];
    }

    function defaultDriftPropagationParams() {
        return [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0];
    }

    function fieldClass(field) {
        return '.model-' + field.replace('.', '-');
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

    function isWatchpointReportModelName(name) {
        return name.indexOf('watchpointReport') >= 0;
    }

    function saveBeamline() {
        // culls and saves propagation and watchpoint models
        var propagations = {};
        var watchpoints = {};
        for (var i = 0; i < appState.models.beamline.length; i++) {
            var item = appState.models.beamline[i];
            propagations[item.id] = appState.models.propagation[item.id];
            if (item.type == 'watch')
                watchpoints[watchpointReportName(item.id)] = true;
        }
        appState.models.propagation = propagations;

        // need to save all watchpointReports and propagations for beamline changes
        var savedModelValues = appState.applicationState();
        for (var modelName in appState.models) {
            if (isWatchpointReportModelName(modelName) && ! watchpoints[modelName]) {
                // deleted watchpoint, remove the report model
                delete appState.models[modelName];
                delete savedModelValues[modelName];
                continue;
            }
            if (isWatchpointReportModelName(modelName))
                savedModelValues[modelName] = appState.cloneModel(modelName);
        }
        appState.saveChanges(['beamline', 'propagation', 'postPropagation']);
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
        }
    }

    function watchpointReportName(id) {
        return 'watchpointReport' + id;
    }

    self.cancelBeamlineChanges = function() {
        self.dismissPopup();
        appState.cancelChanges(['beamline', 'propagation', 'postPropagation']);
    };

    self.checkIfDirty = function() {
        var savedValues = appState.applicationState();
        var models = appState.models;
        if (appState.deepEquals(savedValues.beamline, models.beamline)
            && appState.deepEquals(savedValues.propagation, models.propagation)
            && appState.deepEquals(savedValues.postPropagation, models.postPropagation)) {
            return false;
        }
        return true;
    };

    self.dismissPopup = function() {
        $('.srw-beamline-element-label').popover('hide');
    };

    self.dropBetween = function(index, data) {
        if (! data)
            return;
        var item;
        if (data.id) {
            self.dismissPopup();
            var curr = appState.models.beamline.indexOf(data);
            if (curr < index)
                index--;
            appState.models.beamline.splice(curr, 1);
            item = data;
        }
        else {
            // move last item to this index
            item = appState.models.beamline.pop();
        }
        appState.models.beamline.splice(index, 0, item);
        if (appState.models.beamline.length > 1) {
            if (index === 0) {
                item.position = parseFloat(appState.models.beamline[1].position) - 0.5;
            }
            else if (index === appState.models.beamline.length - 1) {
                item.position = parseFloat(appState.models.beamline[appState.models.beamline.length - 1].position) + 0.5;
            }
            else {
                item.position = Math.round(100 * (parseFloat(appState.models.beamline[index - 1].position) + parseFloat(appState.models.beamline[index + 1].position)) / 2) / 100;
            }
        }
    };

    self.dropComplete = function(data) {
        if (data && ! data.id) {
            addItem(data);
        }
    };

    self.getBeamline = function() {
        return appState.models.beamline;
    };

    self.getWatchItems = function() {
        if (appState.isLoaded()) {
            var beamline = appState.applicationState().beamline;
            var res = [];
            for (var i = 0; i < beamline.length; i++) {
                if (beamline[i].type == 'watch')
                    res.push(beamline[i]);
            }
            return res;
        }
        return [];
    };

    self.handleModalShown = function(name) {
        if (appState.isLoaded()) {
            if (srwService.isGaussianBeam()) {
                $('.model-watchpointReport-fieldUnits').show(0);
                $('.model-initialIntensityReport-fieldUnits').show(0);
            }
            else {
                $('.model-watchpointReport-fieldUnits').hide(0);
                $('.model-initialIntensityReport-fieldUnits').hide(0);
            }
        }
    };

    self.isDefaultMode = function() {
        return srwService.isApplicationMode('default');
    };

    self.isPropagationReadOnly = function() {
        //TODO(pjm): may want to disable this for novice users
        //return ! self.isDefaultMode();
        return false;
    };

    self.isSingleElectron = function() {
        return self.singleElectron;
    };

    self.isMultiElectron = function() {
        return ! self.isSingleElectron();
    };

    self.isTouchscreen = function() {
        return Modernizr.touch;
    };

    self.mirrorReportTitle = function() {
        if (self.activeItem && self.activeItem.title)
            return self.activeItem.title;
        return '';
    };

    self.removeElement = function(item) {
        self.dismissPopup();
        appState.models.beamline.splice(appState.models.beamline.indexOf(item), 1);
    };

    self.disableElement = function(item) {
        self.dismissPopup();
        // appState.models.beamline.splice(appState.models.beamline.indexOf(item), 1);
    };

    self.saveBeamlineChanges = function() {
        // sort beamline based on position
        appState.models.beamline.sort(function(a, b) {
            return parseFloat(a.position) - parseFloat(b.position);
        });
        calculatePropagation();
        saveBeamline();
    };

    self.setActiveItem = function(item) {
        self.activeItem = item;
    };

    self.setSingleElectron = function(value) {
        value = !!value;
        if (value != self.singleElectron)
            simulationQueue.cancelAllItems();
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
        calculatePropagation();
        self.dismissPopup();
        $('#srw-propagation-parameters').modal('show');
    };

    self.showTabs = function() {
        if (self.getWatchItems().length === 0)
            return false;
        if (srwService.isApplicationMode('wavefront'))
            return false;
        if (srwService.isGaussianBeam())
            return false;
        return true;
    };

    //TODO(pjm): coupled with controller named "beamline"
    $scope.$watch('beamline.activeItem.grazingAngle', function (newValue, oldValue) {
        if (newValue !== null && angular.isDefined(newValue) && isFinite(newValue) && angular.isDefined(oldValue) && isFinite(oldValue)) {
            var item = self.activeItem;
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
            fieldsList.push('beamline.activeItem.' + fields[i].toString());
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
        var item = self.activeItem;
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
        var crlMethodFormGroup = $('div.model-crl-method').closest('.form-group');
        if (newValues[0] === 'User-defined') {
            crlMethodFormGroup.hide(0);
        } else {
            crlMethodFormGroup.show(0);
        }
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
        var item = self.activeItem;
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
        var fiberMethodFormGroup = $('div.model-fiber-method').closest('.form-group');
        if (newValues[1] === 'User-defined' && newValues[2] === 'User-defined') {
            fiberMethodFormGroup.hide(0);
        } else {
            fiberMethodFormGroup.show(0);
        }
        if (checkDefined(newValues)) {
            computeFiberCharacteristics();
        }
    });

    var maskFields = [
        'method',
        'material',
    ];
    function computeMaskCharacteristics() {
        var item = self.activeItem;
        if (item.type === 'mask') {
            requestSender.getApplicationData(
                {
                    method: 'compute_mask_characteristics',
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
                        } else {
                            item[fields[i]] = item[fields[i]].toFixed(6);
                        }
                    }
                }
            );
        }
    }
    $scope.$watchCollection(wrapActiveItem(maskFields), function (newValues, oldValues) {
        var maskMethodFormGroup = $('div.model-mask-method').closest('.form-group');
        if (newValues[1] === 'User-defined') {
            maskMethodFormGroup.hide(0);
        } else {
            maskMethodFormGroup.show(0);
        }
        if (checkDefined(newValues)) {
            computeMaskCharacteristics();
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
            var item = self.activeItem;
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
            var item = self.activeItem;
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

    $scope.$watch('beamline.activeItem.position', function(newValue, oldValue) {
        if (newValue !== null && angular.isDefined(newValue) && isFinite(newValue) && angular.isDefined(oldValue) && isFinite(oldValue)) {
            var item = self.activeItem;
            if (item.firstFocusLength)
                item.firstFocusLength = newValue;
        }
    });
});

SIREPO.app.controller('SRWSourceController', function (appState, srwService, $scope, $timeout, requestSender) {
    var self = this;
    self.srwService = srwService;
    $scope.appState = appState;

    function formatFloat(v, n) {
        if (typeof(n) === 'undefined') {
            n = 8;
        }
        var formattedValue = +parseFloat(v).toFixed(n);
        return formattedValue;
    }

    function disableField(reportName, field, value, ifDisable, property) {
        if (! appState.isLoaded() || typeof(value) === 'undefined')
            return;
        if (typeof(property) === 'undefined') {
            property = 'disabled';
        }
        var modelReport = '.model-' + reportName + '-';
        $(modelReport + field).find('.form-control').prop(property, ifDisable);
        if (value !== 'skip') {
            appState.models[reportName][field] = value;
        }
    }

    function processBeamParameters() {
        if (! appState.isLoaded())
            return;
        var und;
        if (appState.models.simulation.sourceType === 't') {
            und = 'tabulatedUndulator';
        } else {
            und = 'undulator';
        }

        var beamDefinition = appState.models.electronBeam.beamDefinition;
        var columnHeading = 'column-heading';
        var fieldsOfTwiss = ['horizontalEmittance', 'horizontalBeta', 'horizontalAlpha', 'horizontalDispersion', 'horizontalDispersionDerivative',
                             'verticalEmittance', 'verticalBeta', 'verticalAlpha', 'verticalDispersion', 'verticalDispersionDerivative'];
        var fieldsOfMoments = ['rmsSizeX', 'rmsDivergX', 'xxprX', 'rmsSizeY', 'rmsDivergY', 'xxprY'];

        requestSender.getApplicationData(
            {
                method: 'process_beam_parameters',
                source_type: appState.models.simulation.sourceType,
                undulator_type: appState.models.tabulatedUndulator.undulatorType,
                undulator_period: appState.models[und].period / 1000,
                undulator_length: appState.models[und].length,
                ebeam: appState.models.electronBeam,
            },
            function(data) {
                var i;
                if (appState.models.electronBeam.driftCalculationMethod === 'auto') {
                    disableField('electronBeam', 'drift', data.drift, true);
                } else {
                    disableField('electronBeam', 'drift', 'skip', false);
                }
                for (i = 0; i < fieldsOfMoments.length; i++) {
                    var val = 'skip';
                    if (beamDefinition === 't') {
                        val = formatFloat(data[fieldsOfMoments[i]]);
                    }
                    disableField('electronBeam', fieldsOfMoments[i], val, false);
                }
            }
        );

        var modelReport = '.model-electronBeam-';
        var duration = 0;  // ms
        var i;
        if (beamDefinition === "t") {  // Twiss
            $($(modelReport + columnHeading)[0]).show(duration);
            $($(modelReport + columnHeading)[1]).show(duration);
            $($(modelReport + columnHeading)[2]).hide(duration);
            $($(modelReport + columnHeading)[3]).hide(duration);
            for (i = 0; i < fieldsOfTwiss.length; i++) {
                $(modelReport + fieldsOfTwiss[i]).closest('.form-group').show(duration);
            }
            for (i = 0; i < fieldsOfMoments.length; i++) {
                $(modelReport + fieldsOfMoments[i]).closest('.form-group').hide(duration);
            }
        } else if (beamDefinition === "m") {  // Moments
            $($(modelReport + columnHeading)[0]).hide(duration);
            $($(modelReport + columnHeading)[1]).hide(duration);
            $($(modelReport + columnHeading)[2]).show(duration);
            $($(modelReport + columnHeading)[3]).show(duration);
            for (i = 0; i < fieldsOfTwiss.length; i++) {
                $(modelReport + fieldsOfTwiss[i]).closest('.form-group').hide(duration);
            }
            for (i = 0; i < fieldsOfMoments.length; i++) {
                $(modelReport + fieldsOfMoments[i]).closest('.form-group').show(duration);
            }
        } else {
            return;
        }
    }

    function processFluxMethod(methodNumber, reportName) {
        if (! appState.isLoaded() || typeof(methodNumber) === 'undefined')
            return;
        // Get magnetic field values from server:
        requestSender.getApplicationData(
            {
                method: 'process_flux_reports',
                method_number: methodNumber,
                report_name: reportName,
                source_type: appState.models.simulation.sourceType,
                undulator_type: appState.models.tabulatedUndulator.undulatorType,
            },
            function(data) {
                disableField(reportName, 'magneticField', data.magneticField, true);
            }
        );
        var fieldsOfApproximateMethod = ['initialHarmonic', 'finalHarmonic', 'longitudinalPrecision', 'azimuthalPrecision'];
        var fieldsOfAccurateMethod = ['precision', 'numberOfMacroElectrons'];
        methodNumber = methodNumber.toString();
        var modelReport = '.model-' + reportName + '-';
        var i;
        if (methodNumber === "-1") {  // ["-1", "Use Approximate Method"]
            for (i = 0; i < fieldsOfApproximateMethod.length; i++) {
                $(modelReport + fieldsOfApproximateMethod[i]).closest('.form-group').show(0);
            }
            for (i = 0; i < fieldsOfAccurateMethod.length; i++) {
                $(modelReport + fieldsOfAccurateMethod[i]).closest('.form-group').hide(0);
            }
        } else if ($.inArray(methodNumber, ["0", "1", "2"]) != -1) {
            for (i = 0; i < fieldsOfApproximateMethod.length; i++) {
                $(modelReport + fieldsOfApproximateMethod[i]).closest('.form-group').hide(0);
            }
            for (i = 0; i < fieldsOfAccurateMethod.length; i++) {
                $(modelReport + fieldsOfAccurateMethod[i]).closest('.form-group').show(0);
            }
        } else {
            return;
        }
    }

    function processIntensityReports(reportName, fieldsToDisable, methodName) {
        if (! appState.isLoaded())
            return;
        requestSender.getApplicationData(
            {
                method: methodName,
                source_type: appState.models.simulation.sourceType,
                undulator_type: appState.models.tabulatedUndulator.undulatorType,
            },
            function(data) {
                for (var i = 0; i < fieldsToDisable.length; i++) {
                    var true_false = true;
                    if (fieldsToDisable[i] === 'method') {
                        true_false = false;
                    }
                    disableField(reportName, fieldsToDisable[i], data[fieldsToDisable[i]], true_false);
                }
            }
        );
    }

    function processTrajectoryReport() {
        if (! appState.isLoaded())
            return;
        var fieldsOfManualMethod = ['initialTimeMoment', 'finalTimeMoment'];
        var reportName = 'trajectoryReport';
        var modelReport = '.model-' + reportName + '-';
        var i;
        // Hide initial and final c*t fields in case of automatic set of limits:
        if (appState.models[reportName].timeMomentEstimation == 'auto') {
            for (i = 0; i < fieldsOfManualMethod.length; i++) {
                $(modelReport + fieldsOfManualMethod[i]).closest('.form-group').hide(0);
            }
        } else {
            for (i = 0; i < fieldsOfManualMethod.length; i++) {
                $(modelReport + fieldsOfManualMethod[i]).closest('.form-group').show(0);
            }
        }
        if (appState.models.simulation.sourceType !== 't' || appState.models.tabulatedUndulator.undulatorType !== 'u_t') {
            disableField(reportName, 'magneticField', 1, true);
        }
    }

    function processUndulatorDefinition(reportName, undulatorDefinition) {
        if (! appState.isLoaded() || typeof(reportName) === 'undefined')
            return;
        requestSender.getApplicationData(
            {
                method: 'process_undulator_definition',
                undulator_definition: undulatorDefinition,
                undulator_parameter: appState.models[reportName].undulatorParameter,
                vertical_amplitude: appState.models[reportName].verticalAmplitude,
                undulator_period: appState.models[reportName].period / 1000,
            },
            function(data) {
                if (undulatorDefinition === 'K') {
                    disableField(reportName, 'verticalAmplitude', formatFloat(data.vertical_amplitude), false, 'readOnly');
                } else {
                    disableField(reportName, 'undulatorParameter', formatFloat(data.undulator_parameter), false, 'readOnly');
                }
            }
        );
    }

    function processUndulator(undType) {
        if (! appState.isLoaded() || typeof(undType) === 'undefined') {
            return;
        }
        var columnHeading = 'column-heading';
        var fieldsOfIdealizedUndulator = ['undulatorParameter', 'period', 'length', 'horizontalAmplitude', 'horizontalInitialPhase', 'horizontalSymmetry', 'verticalAmplitude', 'verticalInitialPhase', 'verticalSymmetry'];
        var fieldsOfTabulatedUndulator = ['gap', 'phase', 'magneticFile', 'indexFile'];
        var modelReport = '.model-tabulatedUndulator-';
        var modelIdealizedReport = '.model-undulator-';
        var duration = 0;  // ms
        var i;

        // Limit and hide some fields in the calculator mode:
        if (srwService.isApplicationMode('calculator')) {
            var fieldsToHide = ['longitudinalPosition', 'horizontalSymmetry', 'verticalSymmetry'];
            for (i = 0; i < fieldsToHide.length; i++) {
                $(modelIdealizedReport + fieldsToHide[i]).closest('.form-group').hide(duration);
            }
        }

        if (undType === "u_t") {  // tabulated
            $(modelReport + columnHeading).hide(duration);
            for (i = 0; i < fieldsOfTabulatedUndulator.length; i++) {
                $(modelReport + fieldsOfTabulatedUndulator[i]).closest('.form-group').show(duration);
            }
            for (i = 0; i < fieldsOfIdealizedUndulator.length; i++) {
                $(modelReport + fieldsOfIdealizedUndulator[i]).closest('.form-group').hide(duration);
            }
        } else if (undType === "u_i") {  // idealized
            $(modelReport + columnHeading).show(duration);
            for (i = 0; i < fieldsOfTabulatedUndulator.length; i++) {
                $(modelReport + fieldsOfTabulatedUndulator[i]).closest('.form-group').hide(duration);
            }
            for (i = 0; i < fieldsOfIdealizedUndulator.length; i++) {
                $(modelReport + fieldsOfIdealizedUndulator[i]).closest('.form-group').show(duration);
            }
        } else {
            return;
        }
    }

    function disableEbeamName(true_false) {
        if (typeof true_false === 'undefined') {
            true_false = true;
            if ($('.modal-dialog .model-electronBeam-beamSelector').is(':visible')) {
                true_false = false;
            }
        }
        disableField('electronBeam', 'name', 'skip', true_false);
    }

    // Watch 'cancelChanges' event to disable the name field in the basic menu:
    $scope.$on('cancelChanges', function(e, name) {
        if (name === 'electronBeam') {
            disableEbeamName(true);
        }
    });

    self.handleModalShown = function(name) {
        if (appState.isLoaded()) {
            if (srwService.isGaussianBeam()) {
                $('.model-sourceIntensityReport-fieldUnits').closest('.form-group').show(0);
            } else {
                // Disable eBeam name in the basic menu:
                disableEbeamName(false);

                $('.model-intensityReport-fieldUnits').closest('.form-group').hide(0);
                $('.model-sourceIntensityReport-fieldUnits').closest('.form-group').hide(0);
            }
            if (srwService.isApplicationMode('calculator')) {
                $('.model-sourceIntensityReport-magneticField').closest('.form-group').hide(0);
            }

            if (name === 'fluxAnimation') {
                processFluxMethod(appState.models.fluxAnimation.method, name);
            } else if (name === 'intensityReport') {
                processIntensityReports(name, ['method', 'magneticField'], 'process_intensity_reports');
            } else if (name === 'sourceIntensityReport') {
                processIntensityReports(name, ['magneticField'], 'process_intensity_reports');
            } else if (name === 'trajectoryReport') {
                processTrajectoryReport();
            } else if (name === 'electronBeam') {
                processBeamParameters();
            }
        }
    };

    function wrapFields(reportNames, fields) {
        var fieldsList = [];
        for (var i = 0; i < reportNames.length; i++) {
            for (var j = 0; j < fields.length; j++) {
                fieldsList.push('appState.models.' + reportNames[i] + '.' + fields[j].toString());
            }
        }
        return '[' + fieldsList.toString() + ']';
    }

    /******************************************************************************************************************/
    /* Smart electron beam processing */
    /*
        TODO(MR):
       +1) Process switching between 'pd' and 'ud' correctly. Need to watch if a value is changed in the 'pd' and make it 'ud'.
       +2) Renaming of the beam in the drop-down menu once the name is changed by user and make it 'ud'.
       +3) Populate Moments parameters after switching between 'pd' beams.
       >4) Save the file with the beams to the common server path where they can be accessed by all simulations.
    */

    function getPredefinedBeams() {
        // Get pre-defined beams list from static JSON file.
        requestSender.loadAuxiliaryData('beams', '/static/json/beams.json');
        return requestSender.getAuxiliaryData('beams');
    }

    function checkPreDefinedBeam(electronBeam) {
        // Check if the beam is pre-defined (name is in the list of names of pre-defined beams and the type of the beam is 'pd').
        var isPredefinedBeam = false;
        var beamNumber = null;
        var predefinedBeams = getPredefinedBeams();
        for (var i = 0; i < predefinedBeams.length; i++) {
            if (electronBeam.name === predefinedBeams[i].name && electronBeam.beamType === 'pd') {
                isPredefinedBeam = true;
                beamNumber = i;
                break;
            }
        }
        return {
            isPredefinedBeam: isPredefinedBeam,
            beamNumber: beamNumber,
        };
    }

    function updateBeamType(beamType) {
        // Update the beam type ('pd' = predefined, 'ud' = user-defined) and isReadOnly attribute.
        appState.models.electronBeam.beamType = beamType;
        if (beamType === 'pd') {
            appState.models.electronBeam.isReadOnly = true;
        } else {
            appState.models.electronBeam.isReadOnly = false;
        }
        // Print the beam type and related isReadOnly attribute (to be removed in production).
        // $('.beamType').text(appState.models.electronBeam.beamType + ' ' + appState.models.electronBeam.isReadOnly);
    }

    function addUserDefinedBeam() {
        // Check if the beam exists in the list of user-defined beams, and add it, if not found:
        var found = false;
        for (var i = 0; i < appState.models.electronBeams.length; i++) {
            if (appState.models.electronBeam.name === appState.models.electronBeams[i].name) {
                appState.models.electronBeams.splice(i, 1, appState.models.electronBeam);
                found = true;
                break;
            }
        }
        if (! found) {
            appState.models.electronBeams.push(appState.models.electronBeam);
        }
        appState.models.electronBeam.beamSelector = appState.models.electronBeam.name;

        // Save the beams list so that it is updated in the beam selector menu:
        appState.saveQuietly('electronBeams');
    }

    var fieldsOfMoments = ['rmsSizeX', 'rmsDivergX', 'xxprX', 'rmsSizeY', 'rmsDivergY', 'xxprY'];

    // Watch for changes of the beam in the beam selector.
    // Watch for beam type is necessary to distinguish between a user-defined and pre-defined beams with the same name.
    $scope.$watchCollection(wrapFields(['electronBeam'], ['beamSelector', 'beamType', 'name']), function(newValues, oldValues) {
        $timeout(function() {
            if (srwService.isElectronBeam()) {
                // Populate missed fields of moments if any of them does not exist or empty:
                for (var i = 0; i < fieldsOfMoments.length; i++) {
                    if ($.inArray(fieldsOfMoments[i], appState.models.electronBeam) < 0 || appState.models.electronBeam[fieldsOfMoments[i]] === null) {
                        processBeamParameters();
                        break;
                    }
                }

                // Check if a selected beam is pre-defined and assign the beam type:
                var v = checkPreDefinedBeam(appState.models.electronBeam);
                var isPredefinedBeam = v.isPredefinedBeam;
                var beamNumber = v.beamNumber;
                if (isPredefinedBeam) {
                    // Copy all the values from the pre-defined beam:
                    appState.models.electronBeam = appState.clone(getPredefinedBeams()[beamNumber]);
                    updateBeamType('pd');
                } else {
                    updateBeamType('ud');
                }

                // These fields may be empty the old pre-defined beams, so need to define them:
                if ($.inArray('driftCalculationMethod', appState.models.electronBeam) < 0) {
                    appState.models.electronBeam.driftCalculationMethod = 'auto';
                }
                if ($.inArray('beamDefinition', appState.models.electronBeam) < 0) {
                    appState.models.electronBeam.beamDefinition = 't';
                }
                // Enable/disable the drop-down menus depending on the beam type:
                disableField('electronBeam', 'driftCalculationMethod', 'skip', appState.models.electronBeam.isReadOnly);
                disableField('electronBeam', 'beamDefinition', 'skip', appState.models.electronBeam.isReadOnly);

                // Check if the beam exists in the list of user-defined beams, and add it, if not found:
                addUserDefinedBeam();
            }
        });
    });

    // Prepare the list of fields to watch, exclude some of them:
    var ebeamKeys = Object.keys(SIREPO.APP_SCHEMA.model.electronBeam);
    // Don't watch these fields:
    var excludeEbeamKeys = ['name', 'driftCalculationMethod', 'drift', 'beamDefinition', 'beamSelector', 'beamType', 'isReadOnly'];
    // Fields of moments should be excluded as well since they are calculated automatically:
    excludeEbeamKeys = excludeEbeamKeys.concat(fieldsOfMoments);
    var removeIdx = [];
    var i;
    for (i = 0; i < excludeEbeamKeys.length; i++) {
        for (var j = 0; j < ebeamKeys.length; j++) {
            if (excludeEbeamKeys[i] === ebeamKeys[j]) {
                removeIdx.push(j);
                break;
            }
        }
    }
    for (i = 0; i < removeIdx.length; i++) {
        ebeamKeys.splice(removeIdx[i], 1);
    }

    // Watch for change of any non-excluded parameters to make the beam user-defined if anything is changed:
    $scope.$watchCollection(wrapFields(['electronBeam'], ebeamKeys), function(newValues, oldValues) {
        // First of all, don't do anything if there is no advanced menu:
        if (! $('.modal-dialog .model-electronBeam-beamSelector').is(':visible')) {
            return;
        }

        // Prepare a limited set of fields to compare both the pre-defined beam parameters from server and the parameters in client:
        var v = checkPreDefinedBeam(appState.models.electronBeam);
        var isPredefinedBeam = v.isPredefinedBeam;
        var beamNumber = v.beamNumber;

        var clientData = $.extend(true, {}, appState.models.electronBeam);
        var serverData = $.extend(true, {}, getPredefinedBeams()[beamNumber]);
        for (var i = 0; i < excludeEbeamKeys.length; i++) {
            delete clientData[excludeEbeamKeys[i]];
            delete serverData[excludeEbeamKeys[i]];
        }
        delete clientData.beamType;
        delete serverData.beamType;

        // Perform comparison and assign correct beam type:
        if (! appState.deepEquals(clientData, serverData)) {
            updateBeamType('ud');
        } else {
            updateBeamType('pd');
        }

        // Check if the beam exists in the list of user-defined beams, and add it, if not found:
        addUserDefinedBeam();
    });

    var electronBeamWatchFields = [
        'driftCalculationMethod',
        'beamDefinition',
        'horizontalEmittance',
        'horizontalBeta',
        'horizontalAlpha',
        'horizontalDispersion',
        'horizontalDispersionDerivative',
        'verticalEmittance',
        'verticalBeta',
        'verticalAlpha',
        'verticalDispersion',
        'verticalDispersionDerivative',
    ];
    $scope.$watchCollection(wrapFields(['electronBeam'], electronBeamWatchFields), function (newValues, oldValues) {
        $timeout(function() {
            if (srwService.isElectronBeam()) {
                processBeamParameters();
            }
        });
    });

    $scope.$watch('appState.models.fluxAnimation.method', function (newValue, oldValue) {
        $timeout(function() {
            if (srwService.isElectronBeam()) {
                processFluxMethod(newValue, 'fluxAnimation');
            }
        });
    });

    $scope.$watch('appState.models.intensityReport.method', function (newValue, oldValue) {
        $timeout(function() {
            if (srwService.isElectronBeam()) {
                var precisionLabel = SIREPO.APP_SCHEMA.model.intensityReport.precision[0];
                if (appState.models.intensityReport.method === "0") {
                    precisionLabel = 'Step Size';
                }
                $('.model-intensityReport-precision').find('label').text(precisionLabel);
            }
        });
    });

    $scope.$watch('appState.models.trajectoryReport.timeMomentEstimation', function (newValues, oldValues) {
        $timeout(function() {
            if (srwService.isElectronBeam()) {
                processTrajectoryReport();
            }
        });
    });

    function processUndulatorWithTimeout(undType) {
        $timeout(function() {
            if (srwService.isElectronBeam()) {
                processUndulator(undType);
            }
        });
    }

    $scope.$on('simulation.changed', function() {
        processUndulatorWithTimeout('u_t');
    });

    $scope.$watch('appState.models.tabulatedUndulator.undulatorType', function (newValue, oldValue) {
        processUndulatorWithTimeout(newValue);
    });

    $scope.$watch('appState.models.tabulatedUndulator.magneticFile', function (newValue, oldValue) {
        if (newValue && oldValue) {
            requestSender.getApplicationData(
                {
                    method: 'compute_undulator_length',
                    report_model: appState.models.tabulatedUndulator,
                },
                function(data) {
                    appState.models.tabulatedUndulator.length = data.length;
                }
            );
        }
    });

    function undulatorReportName() {
        if (srwService.isTabulatedUndulator())
            return 'tabulatedUndulator';
        return 'undulator';
    }

    function activeField() {
        //TODO(pjm) scope() is a debug-only method, need to generalize element watchers
        return angular.element(document.activeElement).scope().field;
    }

    $scope.$watchCollection(wrapFields(['undulator', 'tabulatedUndulator'], ['undulatorParameter']), function (newValues, oldValues) {
        $timeout(function() {
            if (srwService.isElectronBeam() && (srwService.isIdealizedUndulator() || srwService.isTabulatedUndulator())) {
                if (activeField() === 'undulatorParameter') {
                    processUndulatorDefinition(undulatorReportName(), 'K');
                }
            }
        });
    });

    $scope.$watchCollection(wrapFields(['undulator', 'tabulatedUndulator'], ['verticalAmplitude', 'period']), function (newValues, oldValues) {
        $timeout(function() {
            if (srwService.isElectronBeam() && (srwService.isIdealizedUndulator() || srwService.isTabulatedUndulator())) {
                if ((activeField() === 'verticalAmplitude') || (activeField() === 'period') || (typeof(activeField()) === 'undefined')) {
                    processUndulatorDefinition(undulatorReportName(), 'B');
                }
            }
        });
    });
});

SIREPO.app.directive('appFooter', function(appState) {
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

            function updateSimulationGridFields(delay) {
                if (! appState.isLoaded())
                    return;
                var method = appState.models.simulation.samplingMethod;
                if (parseInt(method) == 1) {
                    $('.model-simulation-sampleFactor').show(delay);
                    $('.model-simulation-horizontalPointCount').hide(delay);
                    $('.model-simulation-verticalPointCount').hide(delay);
                }
                else {
                    $('.model-simulation-sampleFactor').hide(delay);
                    $('.model-simulation-horizontalPointCount').show(delay);
                    $('.model-simulation-verticalPointCount').show(delay);
                }
            }

            // hook for sampling method changes
            $scope.nav.handleModalShown = function(name) {
                updateSimulationGridFields(0);
            };
            $scope.$watch('appState.models.simulation.samplingMethod', function (newValue, oldValue) {
                updateSimulationGridFields(400);
            });
        },
    };
});

SIREPO.app.directive('appHeader', function(appState, panelState, requestSender, srwService, $location, $window) {

    var settingsIcon = [
        '<li class="dropdown"><a href class="dropdown-toggle srw-settings-menu hidden-xs" data-toggle="dropdown"><span class="s-panel-icon glyphicon glyphicon-cog"></span></a>',
          '<ul class="dropdown-menu">',
            '<li data-ng-if="! srwService.isApplicationMode(\'calculator\')"><a href data-ng-click="showSimulationGrid()"><span class="glyphicon glyphicon-th"></span> Initial Wavefront Simulation Grid</a></li>',
            '<li data-ng-if="srwService.isApplicationMode(\'default\')"><a href data-ng-click="showDocumentationUrl()"><span class="glyphicon glyphicon-book"></span> Simulation Documentation URL</a></li>',
            '<li><a href data-ng-click="jsonDataFile()"><span class="glyphicon glyphicon-cloud-download"></span> Export JSON Data File</a></li>',
            '<li data-ng-if="canCopy()"><a href data-ng-click="copy()"><span class="glyphicon glyphicon-copy"></span> Open as a New Copy</a></li>',
            '<li data-ng-if="isExample()"><a href data-target="#srw-reset-confirmation" data-toggle="modal"><span class="glyphicon glyphicon-repeat"></span> Discard Changes to Example</a></li>',
            '<li data-ng-if="! isExample()"><a href data-target="#srw-delete-confirmation" data-toggle="modal""><span class="glyphicon glyphicon-trash"></span> Delete</a></li>',
            '<li data-ng-if="hasRelatedSimulations()" class="divider"></li>',
            '<li data-ng-if="hasRelatedSimulations()" class="s-dropdown-submenu">',
              '<a href><span class="glyphicon glyphicon-chevron-left"></span> Related Simulations</a>',
        '<ul class="dropdown-menu">',
        '<li data-ng-repeat="item in relatedSimulations"><a href data-ng-click="openRelatedSimulation(item)">{{ item.name }}</a></li>',
        '</ul>',
            '</li>',
          '</ul>',
        '</li>',
    ].join('');

    var rightNav = [
        '<ul class="nav navbar-nav navbar-right" data-ng-show="nav.isActive(\'simulations\') && ! srwService.isApplicationMode(\'light-sources\')">',
          '<li><a href data-ng-click="showSimulationModal()"><span class="glyphicon glyphicon-plus s-small-icon"></span><span class="glyphicon glyphicon-file"></span> New Simulation</a></li>',
          '<li><a href data-ng-click="showNewFolderModal()"><span class="glyphicon glyphicon-plus s-small-icon"></span><span class="glyphicon glyphicon-folder-close"></span> New Folder</a></li>',
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
                if (srwService.applicationMode == 'calculator' || srwService.applicationMode == 'wavefront')
                    return false;
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
                if (appState.isLoaded())
                    return appState.models.simulation.documentationUrl;
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
                if (appState.isLoaded())
                    return appState.models.simulation.isExample;
                return false;
            };

            $scope.isLoaded = function() {
                if ($scope.nav.isActive('simulations'))
                    return false;
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

SIREPO.app.directive('beamlineIcon', function() {
    return {
        scope: {
            item: '=',
        },
        template: [
            '<svg class="srw-beamline-item-icon" viewbox="0 0 50 60" data-ng-switch="item.type">',
              '<g data-ng-switch-when="lens">',
                '<path d="M25 0 C30 10 30 50 25 60" class="srw-lens" />',
                '<path d="M25 60 C20 50 20 10 25 0" class="srw-lens" />',
              '</g>',
              '<g data-ng-switch-when="aperture">',
                '<rect x="23", y="0", width="5", height="24" class="srw-aperture" />',
                '<rect x="23", y="36", width="5", height="24" class="srw-aperture" />',
              '</g>',
              '<g data-ng-switch-when="ellipsoidMirror">',
                '<path d="M20 0 C30 10 30 50 20 60" class="srw-mirror" />',
              '</g>',
              '<g data-ng-switch-when="grating">',
                '<polygon points="24,0 20,15, 24,17 20,30 24,32 20,45 24,47 20,60 24,60 28,60 28,0" class="srw-mirror" />',
              '</g>',
              '<g data-ng-switch-when="mirror">',
                '<rect x="23" y="0" width="5", height="60" class="srw-mirror" />',
              '</g>',
              '<g data-ng-switch-when="sphericalMirror">',
                '<path d="M20 0 C30 10 30 50 20 60 L33 60 L33 0 L20 0" class="srw-mirror" />',
              '</g>',
              '<g data-ng-switch-when="obstacle">',
                '<rect x="15" y="20" width="20", height="20" class="srw-obstacle" />',
              '</g>',
              '<g data-ng-switch-when="crl">',
                '<rect x="15", y="0", width="20", height="60" class="srw-crl" />',
                '<path d="M25 0 C30 10 30 50 25 60" class="srw-lens" />',
                '<path d="M25 60 C20 50 20 10 25 0" class="srw-lens" />',
                '<path d="M15 0 C20 10 20 50 15 60" class="srw-lens" />',
                '<path d="M15 60 C10 50 10 10 15 0" class="srw-lens" />',
                '<path d="M35 0 C40 10 40 50 35 60" class="srw-lens" />',
                '<path d="M35 60 C30 50 30 10 35 0" class="srw-lens" />',
              '</g>',
              '<g data-ng-switch-when="crystal">',
                '<rect x="8" y="25" width="50", height="6" class="srw-crystal" transform="translate(0) rotate(-30 50 50)" />',
              '</g>',
              '<g data-ng-switch-when="fiber" transform="translate(0) rotate(20 20 40)">',
                '<path d="M-10,35 L10,35" class="srw-fiber"/>',
                '<ellipse cx="10" cy="35" rx="3" ry="5" class="srw-fiber" />',
                '<path d="M10,30 L40,29 40,41 L10,40" class="srw-fiber"/>',
                '<ellipse cx="40" cy="35" rx="3"  ry="6" class="srw-fiber-right" />',
                '<path d="M40,35 L60,35" class="srw-fiber"/>',
              '</g>',
              '<g data-ng-switch-when="mask">',
                '<rect x="2" y="10" width="60", height="60" />',
                '<circle cx="11" cy="20" r="2" class="srw-mask" />',
                '<circle cx="21" cy="20" r="2" class="srw-mask" />',
                '<circle cx="31" cy="20" r="2" class="srw-mask" />',
                '<circle cx="41" cy="20" r="2" class="srw-mask" />',
                '<circle cx="11" cy="30" r="2" class="srw-mask" />',
                '<circle cx="21" cy="30" r="2" class="srw-mask" />',
                '<circle cx="31" cy="30" r="2" class="srw-mask" />',
                '<circle cx="41" cy="30" r="2" class="srw-mask" />',
                '<circle cx="11" cy="40" r="2" class="srw-mask" />',
                '<circle cx="21" cy="40" r="2" class="srw-mask" />',
                '<circle cx="31" cy="40" r="2" class="srw-mask" />',
                '<circle cx="41" cy="40" r="2" class="srw-mask" />',
                '<circle cx="11" cy="50" r="2" class="srw-mask" />',
                '<circle cx="21" cy="50" r="2" class="srw-mask" />',
                '<circle cx="31" cy="50" r="2" class="srw-mask" />',
                '<circle cx="41" cy="50" r="2" class="srw-mask" />',
              '</g>',
              '<g data-ng-switch-when="watch">',
                '<path d="M5 30 C 15 45 35 45 45 30" class="srw-watch" />',
                '<path d="M45 30 C 35 15 15 15 5 30" class="srw-watch" />',
                '<circle cx="25" cy="30" r="10" class="srw-watch" />',
                '<circle cx="25" cy="30" r="4" class="srw-watch-pupil" />',
              '</g>',
            '</svg>',
        ].join(''),
    };
});

SIREPO.app.directive('beamlineItem', function($timeout) {
    return {
        scope: {
            item: '=',
        },
        template: [
            '<span class="srw-beamline-badge badge">{{ item.position }}m</span>',
            '<span data-ng-if="showDeleteButton()" data-ng-click="removeElement(item)" class="srw-beamline-close-icon glyphicon glyphicon-remove-circle"></span>',
            '<span data-ng-if="showDisableButton()" data-ng-click="disableElement(item)" class="srw-beamline-disable-icon glyphicon glyphicon-off"></span>',
            '<div class="srw-beamline-image">',
              '<span data-beamline-icon="", data-item="item"></span>',
            '</div>',
            '<div data-ng-attr-id="srw-item-{{ item.id }}" class="srw-beamline-element-label">{{ item.title }}<span class="caret"></span></div>',
        ].join(''),
        controller: function($scope) {
            $scope.removeElement = function(item) {
                $scope.$parent.beamline.removeElement(item);
            };
            $scope.disableElement = function(item) {
                $scope.$parent.beamline.disableElement(item);
            };
            $scope.showDeleteButton = function() {
                return $scope.$parent.beamline.isDefaultMode();
            };
            $scope.showDisableButton = function() {
                //TODO(pjm): show disable button when feature is implemented
                // return $scope.$parent.beamline.isDefaultMode();
                return false;
            };
        },
        link: function(scope, element) {
            var el = $(element).find('.srw-beamline-element-label');
            el.popover({
                html: true,
                placement: 'bottom',
                container: '.srw-popup-container-lg',
                viewport: { selector: '.srw-beamline'},
                content: $('#srw-' + scope.item.type + '-editor'),
            }).on('show.bs.popover', function() {
                $('.srw-beamline-element-label').not(el).popover('hide');
                scope.$parent.beamline.setActiveItem(scope.item);
            }).on('shown.bs.popover', function() {
                $('.popover-content .form-control').first().select();
            }).on('hide.bs.popover', function() {
                scope.$parent.beamline.setActiveItem(null);
                var editor = el.data('bs.popover').getContent();
                // return the editor to the editor-holder so it will be available for the
                // next element of this type
                if (editor) {
                    $('.srw-editor-holder').trigger('s.resetActivePage');
                    $('.srw-editor-holder').append(editor);
                }
            });

            function togglePopover() {
                el.popover('toggle');
                scope.$apply();
            }
            if (scope.$parent.beamline.isTouchscreen()) {
                var hasTouchMove = false;
                $(element).bind('touchstart', function() {
                    hasTouchMove = false;
                });
                $(element).bind('touchend', function() {
                    if (! hasTouchMove)
                        togglePopover();
                    hasTouchMove = false;
                });
                $(element).bind('touchmove', function() {
                    hasTouchMove = true;
                });
            }
            else {
                $(element).find('.srw-beamline-image').click(function() {
                    togglePopover();
                });
            }
            if (scope.item.showPopover) {
                delete scope.item.showPopover;
                // when the item is added, it may have been dropped between items
                // don't show the popover until the position has been determined
                $timeout(function() {
                    var position = el.parent().position().left;
                    var width = $('.srw-beamline-container').width();
                    var itemWidth = el.width();
                    if (position + itemWidth > width) {
                        var scrollPoint = $('.srw-beamline-container').scrollLeft();
                        $('.srw-beamline-container').scrollLeft(position - width + scrollPoint + itemWidth);
                    }
                    el.popover('show');
                }, 500);
            }
            scope.$on('$destroy', function() {
                if (scope.$parent.beamline.isTouchscreen()) {
                    $(element).bind('touchstart', null);
                    $(element).bind('touchend', null);
                    $(element).bind('touchmove', null);
                }
                else {
                    $(element).find('.srw-beamline-image').off();
                    $(element).off();
                }
                var el = $(element).find('.srw-beamline-element-label');
                el.off();
                var popover = el.data('bs.popover');
                // popover has a memory leak with $tip user_data which needs to be cleaned up manually
                if (popover && popover.$tip)
                    popover.$tip.removeData('bs.popover');
                el.popover('destroy');
            });
        },
    };
});

SIREPO.app.directive('beamlineItemEditor', function(appState) {
    return {
        scope: {
            modelName: '@',
        },
        template: [
            '<div>',
              '<div data-help-button="{{ title }}"></div>',
              '<form name="form" class="form-horizontal" novalidate>',
                '<div data-advanced-editor-pane="" data-view-name="modelName" data-model-data="modelAccess"></div>',
                '<div class="form-group">',
                  '<div class="col-sm-offset-6 col-sm-3">',
                    '<button ng-click="beamline.dismissPopup()" style="width: 100%" type="submit" class="btn btn-primary" data-ng-class="{\'disabled\': ! form.$valid}">Close</button>',
                  '</div>',
                '</div>',
                '<div class="form-group" data-ng-show="beamline.isTouchscreen() && beamline.isDefaultMode()">',
                  '<div class="col-sm-offset-6 col-sm-3">',
                    '<button ng-click="removeActiveItem()" style="width: 100%" type="submit" class="btn btn-danger">Delete</button>',
                  '</div>',
                '</div>',
              '</form>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.beamline = $scope.$parent.beamline;
            $scope.title = appState.viewInfo($scope.modelName).title;
            $scope.advancedFields = appState.viewInfo($scope.modelName).advanced;
            $scope.removeActiveItem = function() {
                $scope.beamline.removeElement($scope.beamline.activeItem);
            };
            $scope.modelAccess = {
                modelKey: $scope.modelName,
                getData: function() {
                    return $scope.beamline.activeItem;
                },
            };
            //TODO(pjm): investigate why id needs to be set in html for revisiting the beamline page
            //$scope.editorId = 'srw-' + $scope.modelName + '-editor';
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
                if (appState.isLoaded())
                    return appState.models.simulation.name;
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
            import_args.hide(0);
            $scope.fileType = function(pythonFile) {
                if (typeof(pythonFile) === 'undefined')
                    return;
                if (pythonFile.name.search('.py') >= 0) {
                    import_args.show(0);
                } else {
                    import_args.hide(0);
                }
            };
            $scope.importPythonFile = function(pythonFile, importArgs) {
                if (typeof(importArgs) === 'undefined')
                    importArgs = '';
                if (! pythonFile)
                    return;
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

SIREPO.app.directive('resetSimulationModal', function(appState, srwService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=resetSimulationModal',
        },
        template: [
            '<div data-confirmation-modal="" data-id="srw-reset-confirmation" data-title="Reset Simulation?" data-ok-text="Discard Changes" data-ok-clicked="revertToOriginal()">Discard changes to &quot;{{ simulationName() }}&quot;?</div>',
        ].join(''),
        controller: function($scope) {
            $scope.revertToOriginal = function() {
                $scope.nav.revertToOriginal(
                    srwService.applicationMode,
                    appState.models.simulation.name);
            };
            $scope.simulationName = function() {
                if (appState.isLoaded())
                    return appState.models.simulation.name;
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
                if (data.frameId && (data.frameId != $scope.frameId)) {
                    $scope.frameId = data.frameId;
                    $scope.frameCount++;
                    frameCache.setFrameCount($scope.frameCount);
                    frameCache.setCurrentFrame($scope.model, $scope.frameCount - 1);
                }
            };

            persistentSimulation.initProperties($scope);
            frameCache.setAnimationArgs({
                multiElectronAnimation: [],
                fluxAnimation: ['fluxType'],
            });
            $scope.$on($scope.model + '.changed', function() {
                if ($scope.isReadyForModelChanges) {
                    frameCache.setFrameCount(0);
                    frameCache.clearFrames($scope.model);
                }
            });
            $scope.persistentSimulationInit($scope);
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

SIREPO.app.directive('watchpointModalEditor', function(srwService) {
    return {
        scope: {
            parentController: '=',
            itemId: '=',
        },
        template: [
            '<div data-modal-editor="" view-name="watchpointReport" data-parent-controller="parentController" data-model-data="modelAccess" data-modal-title="reportTitle()"></div>',
        ].join(''),
        controller: function($scope) {
            srwService.setupWatchpointDirective($scope);
        },
    };
});

SIREPO.app.directive('watchpointReport', function(srwService) {
    return {
        scope: {
            itemId: '=',
        },
        template: [
            '<div data-report-panel="3d" data-model-name="watchpointReport" data-model-data="modelAccess" data-panel-title="{{ reportTitle() }}"></div>',
        ].join(''),
        controller: function($scope) {
            srwService.setupWatchpointDirective($scope);
        },
    };
});
