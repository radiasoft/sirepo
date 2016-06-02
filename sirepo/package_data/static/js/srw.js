'use strict';

app_local_routes.beamline = '/beamline/:simulationId';
appDefaultSimulationValues = {
    simulation: {
        sourceType: 'u',
    },
};

app.config(function($routeProvider, localRoutesProvider) {
    var localRoutes = localRoutesProvider.$get();
    $routeProvider
        .when(localRoutes.source, {
            controller: 'SRWSourceController as source',
            templateUrl: '/static/html/srw-source.html?' + SIREPO_APP_VERSION,
        })
        .when(localRoutes.beamline, {
            controller: 'SRWBeamlineController as beamline',
            templateUrl: '/static/html/srw-beamline.html?' + SIREPO_APP_VERSION,
        })
});

app.factory('srwService', function(appState, $rootScope, $location) {
    var self = {};
    self.applicationMode = 'default';
    self.originalCharacteristicEnum = null;
    self.singleElectronCharacteristicEnum = null;

    function initCharacteristic() {
        if (self.originalCharacteristicEnum)
            return;
        self.originalCharacteristicEnum = APP_SCHEMA.enum['Characteristic'];
        var characteristic = appState.clone(APP_SCHEMA.enum['Characteristic']);
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
        if (model && model.distanceFromSource != null)
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
            return appState.models.electronBeam.isReadOnly ? true : false;
        return false;
    };

    self.isTabulatedUndulator = function() {
        return isSelected('t');
    };

    self.setupWatchpointDirective = function($scope) {
        var modelKey = 'watchpointReport' + $scope.itemId
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

    $rootScope.$on('modelsLoaded', function() {
        initCharacteristic();
        // don't show multi-electron values in certain cases
        APP_SCHEMA.enum['Characteristic'] = (self.isApplicationMode('wavefront') || self.isGaussianBeam())
            ? self.singleElectronCharacteristicEnum
            : self.originalCharacteristicEnum;
    });

    return self;
});

app.controller('SRWBeamlineController', function (appState, panelState, requestSender, srwService, $scope) {
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
        {type:'crl', title:'CRL', focalPlane:2, refractiveIndex:4.20756805e-06, attenuationLength:7.31294e-03, shape:1,
         horizontalApertureSize:1, verticalApertureSize:1, radius:1.5e-03, numberOfLenses:3, wallThickness:80.e-06},
        {type:'grating', title:'Grating', tangentialSize:0.2, sagittalSize:0.015, grazingAngle:12.9555790185373, normalVectorX:0, normalVectorY:0.99991607766, normalVectorZ:-0.0129552166147, tangentialVectorX:0, tangentialVectorY:0.0129552166147, diffractionOrder:1, grooveDensity0:1800, grooveDensity1:0.08997, grooveDensity2:3.004e-6, grooveDensity3:9.7e-11, grooveDensity4:0,},
        {type:'lens', title:'Lens', horizontalFocalLength:3, verticalFocalLength:1.e+23, horizontalOffset:0, verticalOffset:0},
        {type:'ellipsoidMirror', title:'Ellipsoid Mirror', focalLength:1.7, grazingAngle:3.6, tangentialSize:0.5, sagittalSize:0.01, normalVectorX:0, normalVectorY:0.9999935200069984, normalVectorZ:-0.0035999922240050387, tangentialVectorX:0, tangentialVectorY:-0.0035999922240050387, heightProfileFile:null, orientation:'x', heightAmplification:1},
        {type:'mirror', title:'Flat Mirror', orientation:'x', grazingAngle:3.1415926, heightAmplification:1, horizontalTransverseSize:1, verticalTransverseSize:1, heightProfileFile:'mirror_1d.dat'},
        {type:'sphericalMirror', title:'Spherical Mirror', 'radius':1049, 'tangentialSize':0.3, 'sagittalSize':0.11, 'normalVectorX':0, 'normalVectorY':0.9999025244842406, 'normalVectorZ':-0.013962146326506367,'tangentialVectorX':0, 'tangentialVectorY':0.013962146326506367, heightProfileFile:null, orientation:'x', heightAmplification:1},
        {type:'obstacle', title:'Obstacle', horizontalSize:0.5, verticalSize:0.5, shape:'r', horizontalOffset:0, verticalOffset:0},
        crystalDefaults,
        {type:'watch', title:'Watchpoint'},
    ];
    self.panelState = panelState;
    self.srwService = srwService;
    self.activeItem = null;
    self.postPropagation = [];
    self.propagations = [];
    self.analyticalTreatmentEnum = APP_SCHEMA.enum['AnalyticalTreatment'];
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
            var d = parseFloat(beamline[i + 1].position) - parseFloat(beamline[i].position)
            if (d > 0) {
                self.propagations.push({
                    title: 'Drift ' + formatFloat(d) + 'm',
                    params: p[1],
                });
            }
        }
        if (! appState.models.postPropagation || appState.models.postPropagation.length == 0)
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
        var propagations = {}
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
    };

    function watchpointReportName(id) {
        return 'watchpointReport' + id;
    }

    self.cancelBeamlineChanges = function() {
        self.dismissPopup();
        appState.cancelChanges('beamline');
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
        //console.log('dropBetween: ', index, ' ', data, ' ', data.id ? 'old' : 'new');
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
            item = appState.models.beamline.pop()
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
        return false
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
        self.singleElectron = value;
    };

    self.showFileReport = function(type, model) {
        self.mirrorReportShown = true;
        appState.models.mirrorReport = model;
        var el = $('#srw-mirror-plot');
        el.modal('show');
        el.on('shown.bs.modal', function() {
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
        if (self.getWatchItems().length == 0)
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
    });

    function checkChanged(newValues, oldValues) {
        for (var i=0; i<newValues.length; i++) {
            if (! angular.isDefined(newValues[i]) || newValues[i] === null || newValues[i] === 'Unknown' || ! angular.isDefined(oldValues[i])) {
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
            requestSender.getApplicationData(
                {
                    method: 'compute_crystal_init',
                    optical_element: item,
                },
                function(data) {
                    var fields = ['dSpacing', 'psi0r', 'psi0i', 'psiHr', 'psiHi', 'psiHBr', 'psiHBi'];
                    for (var i = 0; i < fields.length; i++) {
                        item[fields[i]] = data[fields[i]];
                    }
                }
            );
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
    });

    $scope.$watch('beamline.activeItem.position', function(newValue, oldValue) {
        if (newValue !== null && angular.isDefined(newValue) && isFinite(newValue) && angular.isDefined(oldValue) && isFinite(oldValue)) {
            var item = self.activeItem;
            if (item.firstFocusLength)
                item.firstFocusLength = newValue;
        }
    });
});

app.controller('SRWSourceController', function (appState, srwService, $scope, $timeout, requestSender) {
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

        if (appState.models.simulation.sourceType === 'u') {
            var und = 'undulator';
        } else if (appState.models.simulation.sourceType === 't') {
            var und = 'tabulatedUndulator';
        } else {
            var und = 'undulator';
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
                undulator_period: appState.models[und]['period'] / 1000,
                undulator_length: appState.models[und]['length'],
            },
            function(data) {
                if (appState.models.electronBeam.isReadOnly) {
                    disableField('electronBeam', 'driftCalculationMethod', 'auto', true);
                    disableField('electronBeam', 'drift', data['drift'], true);
                    disableField('electronBeam', 'beamDefinition', 't', true);
                    for (var i = 0; i < fieldsOfMoments.length; i++) {
                        disableField('electronBeam', fieldsOfMoments[i], data[fieldsOfMoments[i]], true);
                    }
                } else {
                    disableField('electronBeam', 'driftCalculationMethod', 'skip', false);
                    if (appState.models.electronBeam.driftCalculationMethod === 'auto') {
                        disableField('electronBeam', 'drift', data['drift'], true);
                    } else {
                        disableField('electronBeam', 'drift', 'skip', false);
                    }
                    disableField('electronBeam', 'beamDefinition', 'skip', false);
                    for (var i = 0; i < fieldsOfMoments.length; i++) {
                        disableField('electronBeam', fieldsOfMoments[i], 'skip', false);
                    }
                }
            }
        );

        var modelReport = '.model-electronBeam-';
        var duration = 0;  // ms
        if (beamDefinition === "t") {  // Twiss
            $($(modelReport + columnHeading)[0]).show(duration);
            $($(modelReport + columnHeading)[1]).show(duration);
            $($(modelReport + columnHeading)[2]).hide(duration);
            $($(modelReport + columnHeading)[3]).hide(duration);
            for (var i = 0; i < fieldsOfTwiss.length; i++) {
                $(modelReport + fieldsOfTwiss[i]).closest('.form-group').show(duration);
            }
            for (var i = 0; i < fieldsOfMoments.length; i++) {
                $(modelReport + fieldsOfMoments[i]).closest('.form-group').hide(duration);
            }
        } else if (beamDefinition === "m") {  // Moments
            $($(modelReport + columnHeading)[0]).hide(duration);
            $($(modelReport + columnHeading)[1]).hide(duration);
            $($(modelReport + columnHeading)[2]).show(duration);
            $($(modelReport + columnHeading)[3]).show(duration);
            for (var i = 0; i < fieldsOfTwiss.length; i++) {
                $(modelReport + fieldsOfTwiss[i]).closest('.form-group').hide(duration);
            }
            for (var i = 0; i < fieldsOfMoments.length; i++) {
                $(modelReport + fieldsOfMoments[i]).closest('.form-group').show(duration);
            }
        } else {
            return;
        }
    }

    function processFluxMethod(methodNumber, reportName) {
        if (! appState.isLoaded() || typeof methodNumber === "undefined")
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
                disableField(reportName, 'magneticField', data['magneticField'], true);
            }
        );
        var fieldsOfApproximateMethod = ['initialHarmonic', 'finalHarmonic', 'longitudinalPrecision', 'azimuthalPrecision'];
        var fieldsOfAccurateMethod = ['precision'];
        methodNumber = methodNumber.toString();
        var modelReport = '.model-' + reportName + '-';
        if (methodNumber === "-1") {  // ["-1", "Use Approximate Method"]
            for (var i = 0; i < fieldsOfApproximateMethod.length; i++) {
                $(modelReport + fieldsOfApproximateMethod[i]).show(0);
            }
            for (var i = 0; i < fieldsOfAccurateMethod.length; i++) {
                $(modelReport + fieldsOfAccurateMethod[i]).hide(0);
            }
        } else if ($.inArray(methodNumber, ["0", "1", "2"]) != -1) {
            for (var i = 0; i < fieldsOfApproximateMethod.length; i++) {
                $(modelReport + fieldsOfApproximateMethod[i]).hide(0);
            }
            for (var i = 0; i < fieldsOfAccurateMethod.length; i++) {
                $(modelReport + fieldsOfAccurateMethod[i]).show(0);
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

    function processUndulatorDefinition(reportName, undulatorDefinition) {
        if (! appState.isLoaded() || typeof(reportName) === 'undefined')
            return;
        requestSender.getApplicationData(
            {
                method: 'process_undulator_definition',
                undulator_definition: undulatorDefinition,
                undulator_parameter: appState.models[reportName]['undulatorParameter'],
                vertical_amplitude: appState.models[reportName]['verticalAmplitude'],
                undulator_period: appState.models[reportName]['period'] / 1000,
            },
            function(data) {
                if (undulatorDefinition === 'K') {
                    disableField(reportName, 'verticalAmplitude', formatFloat(data['vertical_amplitude']), false, 'readOnly');
                } else {
                    disableField(reportName, 'undulatorParameter', formatFloat(data['undulator_parameter']), false, 'readOnly');
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
        var duration = 0;  // ms
        if (undType === "u_t") {  // tabulated
            $(modelReport + columnHeading).hide(duration);
            for (var i = 0; i < fieldsOfTabulatedUndulator.length; i++) {
                $(modelReport + fieldsOfTabulatedUndulator[i]).closest('.form-group').show(duration);
            }
            for (var i = 0; i < fieldsOfIdealizedUndulator.length; i++) {
                $(modelReport + fieldsOfIdealizedUndulator[i]).closest('.form-group').hide(duration);
            }
        } else if (undType === "u_i") {  // idealized
            $(modelReport + columnHeading).show(duration);
            for (var i = 0; i < fieldsOfTabulatedUndulator.length; i++) {
                $(modelReport + fieldsOfTabulatedUndulator[i]).closest('.form-group').hide(duration);
            }
            for (var i = 0; i < fieldsOfIdealizedUndulator.length; i++) {
                $(modelReport + fieldsOfIdealizedUndulator[i]).closest('.form-group').show(duration);
            }
        } else {
            return;
        }
    }

    self.handleModalShown = function(name) {
        if (appState.isLoaded()) {
            if (srwService.isGaussianBeam()) {
                $('.model-sourceIntensityReport-fieldUnits').show(0);
            }
            else {
                $('.model-sourceIntensityReport-fieldUnits').hide(0);
            }
            if (srwService.isApplicationMode('calculator')) {
                $('.model-intensityReport-fieldUnits').hide(0);
                $('.model-sourceIntensityReport-magneticField').hide(0);
            }

            if (name === 'fluxAnimation') {
                processFluxMethod(appState.models.fluxAnimation.method, name);
            } else if (name === 'intensityReport') {
                processIntensityReports(name, ['method', 'magneticField'], 'process_intensity_reports');
            } else if (name === 'sourceIntensityReport') {
                processIntensityReports(name, ['magneticField'], 'process_intensity_reports');
            } else if (name === 'electronBeam') {
                processBeamParameters();
            }
        }
    };

    $scope.$on('electronBeam.changed', function() {
        var beam = appState.models.electronBeam;
        var beams = appState.models.electronBeams;
        beam.beamSelector = beam.name;
        if (! beam.isReadOnly) {
            // update the user defined beam in the electronBeams list
            for (var i = 0; i < beams.length; i++) {
                if (beams[i].id == beam.id) {
                    beams.splice(i, 1, beam);
                    break;
                }
            }
        }
        beams.sort(function(a, b) {
            return a.name.localeCompare(b.name);
        });
        appState.saveQuietly('electronBeam');
        appState.saveQuietly('electronBeams');
    });

    function wrapFields(reportNames, fields) {
        var fieldsList = [];
        for (var i = 0; i < reportNames.length; i++) {
            for (var j = 0; j < fields.length; j++) {
                fieldsList.push('appState.models.' + reportNames[i] + '.' + fields[j].toString());
            }
        }
        return '[' + fieldsList.toString() + ']';
    }

    $scope.$watchCollection(wrapFields(['electronBeam'], ['driftCalculationMethod', 'beamDefinition']), function (newValues, oldValues) {
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

    $scope.$watch('appState.models.tabulatedUndulator.undulatorType', function (newValue, oldValue) {
        $timeout(function() {
            if (srwService.isElectronBeam()) {
                processUndulator(newValue);
            }
        });
    });

    function undulatorReportName() {
        var reportName = 'undulator';
        if (srwService.isTabulatedUndulator()) {
            var reportName = 'tabulatedUndulator';
        }
        return reportName;
    }

    function activeField() {
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
                if ((activeField() === 'verticalAmplitude') || (activeField() === 'period')) {
                    processUndulatorDefinition(undulatorReportName(), 'B');
                }
            }
        });
    });
});

app.directive('appFooter', function(appState) {
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
                var method = appState.models['simulation']['samplingMethod'];
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

app.directive('appHeader', function(appState, panelState, requestSender, srwService, $location, $window) {

    var settingsIcon = [
        '<li class="dropdown"><a href class="dropdown-toggle srw-settings-menu hidden-xs" data-toggle="dropdown"><span class="s-panel-icon glyphicon glyphicon-cog"></span></a>',
          '<ul class="dropdown-menu">',
            '<li data-ng-if="! srwService.isApplicationMode(\'calculator\')"><a href data-ng-click="showSimulationGrid()"><span class="glyphicon glyphicon-th"></span> Initial Wavefront Simulation Grid</a></li>',
            '<li data-ng-if="srwService.isApplicationMode(\'default\')"><a href data-ng-click="showDocumentationUrl()"><span class="glyphicon glyphicon-book"></span> Simulation Documentation URL</a></li>',
            '<li><a href data-ng-click="pythonSource()"><span class="glyphicon glyphicon-cloud-download"></span> Export Python Code</a></li>',
            '<li data-ng-if="canCopy()"><a href data-ng-click="copy()"><span class="glyphicon glyphicon-copy"></span> Open as a New Copy</a></li>',
            '<li data-ng-if="isExample()"><a href data-target="#srw-reset-confirmation" data-toggle="modal"><span class="glyphicon glyphicon-repeat"></span> Discard Changes to Example</a></li>',
            '<li data-ng-if="! isExample()"><a href data-target="#srw-delete-confirmation" data-toggle="modal""><span class="glyphicon glyphicon-trash"></span> Delete</a></li>',
          '</ul>',
        '</li>',
    ].join('');

    var rightNav = [
        '<ul class="nav navbar-nav navbar-right" data-ng-show="nav.isActive(\'simulations\') && ! srwService.isApplicationMode(\'light-sources\')">',
          '<li><a href data-ng-click="showSimulationModal()"><span class="glyphicon glyphicon-plus"></span> New</a></li>',
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
              '<a class="navbar-brand" href="/light"><img style="width: 40px; margin-top: -10px;" src="/static/img/radtrack.gif" alt="radiasoft"></a>',
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
        restirct: 'A',
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
                '<a class="navbar-brand" href="/light"><img style="width: 40px; margin-top: -10px;" src="/static/img/radtrack.gif" alt="radiasoft"></a>',
                '<div class="navbar-brand"><a href="/light">Synchrotron Radiation Workshop</a></div>',
              '</div>',
              '<div class="navbar-left" data-app-header-left="nav"></div>',
              rightNav,
            '</div>',
        ].join(''),
        controller: function($scope) {
            function simulationId() {
                return appState.models.simulation.simulationId;
            }

            $scope.srwService = srwService;

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

            $scope.hasDocumentationUrl = function() {
                if (appState.isLoaded())
                    return appState.models.simulation.documentationUrl;
                return false;
            };

            $scope.isExample = function() {
                if (appState.isLoaded())
                    return appState.models.simulation.isExample;
                return false;
            };

            $scope.isLoaded = function() {
                return appState.isLoaded();
            };

            $scope.openDocumentation = function() {
                $window.open(appState.models.simulation.documentationUrl, '_blank');
            };

            $scope.showImportModal = function() {
                $('#srw-simulation-import').modal('show');
            };

            $scope.showSimulationModal = function() {
                panelState.showModalEditor('simulation');
            };

            $scope.pythonSource = function(item) {
                $window.open(requestSender.formatUrl('pythonSource', {
                    '<simulation_id>': simulationId(),
                    '<simulation_type>': APP_SCHEMA.simulationType,
                }), '_blank');
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

app.directive('beamlineIcon', function() {
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

app.directive('beamlineItem', function($timeout) {
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
                return $scope.$parent.beamline.isDefaultMode();
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

app.directive('beamlineItemEditor', function(appState) {
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
            }
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

app.directive('deleteSimulationModal', function(appState, $location) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div data-confirmation-modal="" data-id="srw-delete-confirmation" data-title="Delete Simulation?" data-text="Delete simulation &quot;{{ simulationName() }}&quot;?" data-ok-text="Delete" data-ok-clicked="deleteSimulation()"></div>',
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
app.directive('importPython', function(fileUpload, requestSender) {
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
                          '<br />',
                          'Optional arguments: <input id="srw-python-file-import-args" type="text" style="width: 100%" data-ng-model="importArgs"><br>',
                          '<div class="text-warning"><strong>{{ fileUploadError }}</strong></div>',
                        '</div>',
                        '<div class="col-sm-6 pull-right">',
                          '<button data-ng-click="importPythonFile(pythonFile, importArgs)" class="btn btn-primary">Import File</button>',
                          ' <button data-dismiss="modal" class="btn btn-default">Cancel</button>',
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
            $scope.title = 'Import Python Beamline File';
            $scope.importPythonFile = function(pythonFile, importArgs) {
                if (typeof importArgs === "undefined") {
                    var importArgs = '';
                }
                if (! pythonFile)
                    return;
                fileUpload.uploadFileToUrl(
                    pythonFile,
                    importArgs,
                    requestSender.formatUrl(
                        'importFile',
                        {
                            '<simulation_type>': APP_SCHEMA.simulationType,
                        }),
                    function(data) {
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
                scope.fileUploadError = ''
            });
        },
    };
});

app.directive('mobileAppTitle', function(srwService) {
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
        restirct: 'A',
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

app.directive('resetSimulationModal', function(appState, srwService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=resetSimulationModal',
        },
        template: [
            '<div data-confirmation-modal="" data-id="srw-reset-confirmation" data-title="Reset Simulation?" data-text="Discard changes to &quot;{{ simulationName() }}&quot;?" data-ok-text="Discard Changes" data-ok-clicked="revertToOriginal()"></div>',
        ].join(''),
        controller: function($scope) {
            $scope.revertToOriginal = function() {
                $scope.nav.revertToOriginal(
                    srwService.applicationMode,
                    srwService.isApplicationMode('light-sources')
                        ? appState.models.simulation.facility
                        : appState.models.simulation.name);
            };
            $scope.simulationName = function() {
                if (appState.isLoaded())
                    return appState.models.simulation.name;
                return '';
            };
        },
    };
});

app.directive('simulationStatusPanel', function(appState, frameCache, panelState, requestSender, $timeout) {
    return {
        restrict: 'A',
        scope: {
            model: '@simulationStatusPanel',
            title: '@',
        },
        template: [
            '<form name="form" class="form-horizontal" novalidate>',
              '<div data-ng-if="isState(\'initial\')">',
                '<div class="col-sm-6 pull-right">',
                  '<button class="btn btn-primary" data-ng-click="runSimulation()">Start Simulation</button>',
                '</div>',
              '</div>',
              '<div data-ng-if="isState(\'running\')">',
                '<div class="col-sm-6">',
                  '<div data-ng-if="isInitializing()">',
                    '<span class="glyphicon glyphicon-hourglass"></span> Initializing Simulation {{ dots }}',
                  '</div>',
                  '<div data-ng-hide="isInitializing()">',
                    'Simulation Running {{ dots }}',
                    '<div data-simulation-status-timer="timeData"></div>',
                  '</div>',
                '</div>',
                '<div class="col-sm-6 pull-right">',
                  '<button class="btn btn-default" data-ng-click="cancelSimulation()">End Simulation</button>',
                '</div>',
              '</div>',
              '<div data-ng-if="isState(\'completed\') || isState(\'canceled\')">',
                '<div class="col-sm-6">',
                  'Simulation ',
                  '<span data-ng-if="isState(\'completed\')">Completed</span><span data-ng-if="isState(\'canceled\')">Stopped</span>',
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
            var isAborting = false;
            var isDestroyed = false;
            var frameId = '-1';
            var frameCount = 1;
            var isReadyForModelChanges = false;
            $scope.dots = '.';
            $scope.timeData = {
                elapsedDays: null,
                elapsedTime: null,
            };
            $scope.panelState = panelState;

            frameCache.setAnimationArgs({
                multiElectronAnimation: [],
                fluxAnimation: ['fluxType'],
            });
            frameCache.setFrameCount(0);

            $scope.$on('$destroy', function () {
                isDestroyed = true;
            });

            function refreshStatus() {
                if (! appState.isLoaded())
                    return;
                isReadyForModelChanges = true;
                requestSender.sendRequest(
                    'runStatus',
                    function(data) {
                        if (isAborting)
                            return;

                        if (data.frameId && (data.frameId != frameId)) {
                            frameId = data.frameId;
                            frameCount++;
                            frameCache.setFrameCount(frameCount);
                            frameCache.setCurrentFrame($scope.model, frameCount - 1);
                        }
                        if (data.elapsedTime) {
                            $scope.timeData.elapsedDays = parseInt(data.elapsedTime / (60 * 60 * 24));
                            $scope.timeData.elapsedTime = new Date(1970, 0, 1);
                            $scope.timeData.elapsedTime.setSeconds(data.elapsedTime);
                        }

                        if (data.state != 'running') {
                            if (data.state != simulationState())
                                appState.saveChanges('simulationStatus');
                        }
                        else {
                            if (! isDestroyed) {
                                $scope.dots += '.';
                                if ($scope.dots.length > 3)
                                    $scope.dots = '.';
                                $timeout(refreshStatus, 4000);
                            }
                        }
                        setSimulationState(data.state);
                    },
                    {
                        report: $scope.model,
                        models: appState.applicationState(),
                        simulationType: APP_SCHEMA.simulationType,
                    });
            }

            function setSimulationState(state) {
                if (! appState.models.simulationStatus[$scope.model])
                    appState.models.simulationStatus[$scope.model] = {}
                appState.models.simulationStatus[$scope.model].state = state;
            }

            function simulationState() {
                if (appState.models.simulationStatus[$scope.model])
                    return appState.models.simulationStatus[$scope.model].state;
                return 'initial';
            }

            $scope.cancelSimulation = function() {
                if (simulationState() != 'running')
                    return;
                setSimulationState('canceled');
                isAborting = true;
                requestSender.sendRequest(
                    'runCancel',
                    function(data) {
                        isAborting = false;
                        appState.saveChanges('simulationStatus');
                    },
                    {
                        report: $scope.model,
                        models: appState.applicationState(),
                        simulationType: APP_SCHEMA.simulationType,
                    });
            };

            $scope.isInitializing = function() {
                if ($scope.isState('running'))
                    return frameCache.getFrameCount() < 1;
                return false;
            };

            $scope.isState = function(state) {
                if (appState.isLoaded())
                    return simulationState() == state;
                return false;
            };

            $scope.runSimulation = function() {
                if (simulationState() == 'running')
                    return;
                frameCache.setFrameCount(0);
                $scope.timeData.elapsedTime = null;
                $scope.timeData.elapsedDays = null;
                setSimulationState('running');
                requestSender.sendRequest(
                    'runBackground',
                    function(data) {
                        appState.models.simulationStatus[$scope.model].startTime = data['startTime'];
                        appState.saveChanges('simulationStatus');
                        refreshStatus();
                    },
                    {
                        report: $scope.model,
                        models: appState.applicationState(),
                        simulationType: APP_SCHEMA.simulationType,
                    });
            };

            $scope.$on($scope.model + '.changed', function() {
                if (isReadyForModelChanges) {
                    frameCache.setFrameCount(0);
                    frameCache.clearFrames($scope.model);
                }
            });

            if (appState.isLoaded())
                refreshStatus();
            else {
                $scope.$on('modelsLoaded', refreshStatus);
            }
        },
    };
});

app.directive('tooltipEnabler', function() {
    return {
        link: function(scope, element) {
            $('[data-toggle="tooltip"]').tooltip({
                html: true,
                placement: 'bottom',
            });
        },
    };
});

app.directive('watchpointModalEditor', function(srwService) {
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

app.directive('watchpointReport', function(srwService) {
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
