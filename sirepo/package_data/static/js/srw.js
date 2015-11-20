'use strict';

APP_LOCAL_ROUTES.beamline = '/beamline/:simulationId';

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
        });
});

app.factory('srwService', function(appState) {
    var self = {};
    self.updatePhotonEnergy = function(modelName, energy) {
        for (var name in appState.models) {
            if (appState.isReportModelName(name) && appState.models[name].photonEnergy != null) {
                if (energy != appState.models[name].photonEnergy) {
                    console.log('updating photon energy: ', name);
                    appState.models[name].photonEnergy = energy;
                    if (appState.isReportModelName(modelName))
                        appState.saveChanges(name);
                    else
                        appState.saveQuietly(name);
                }
            }
        }
    };
    return self;
});

app.controller('SRWBeamlineController', function (activeSection, appState, fileUpload, requestSender, srwService, $scope, $timeout) {
    activeSection.setActiveSection('beamline');
    var self = this;
    self.toolbarItems = [
        //TODO(pjm): move default values to separate area
        {type:'aperture', title:'Aperture', horizontalSize:1, verticalSize:1, shape:'r', horizontalOffset:0, verticalOffset:0},
        {type:'crl', title:'CRL', focalPlane:2, refractiveIndex:4.20756805e-06, attenuationLength:7.31294e-03, shape:1,
         horizontalApertureSize:1, verticalApertureSize:1, radius:1.5e-03, numberOfLenses:3, wallThickness:80.e-06},
        {type:'lens', title:'Lens', horizontalFocalLength:3, verticalFocalLength:1.e+23},
        {type:'ellipsoidMirror', title:'Ellipsoid Mirror', focalLength:1.7, grazingAngle:3.6, tangentialSize:0.5, sagittalSize:0.01, normalVectorX:0, normalVectorY:0.9999935200069984, normalVectorZ:-0.0035999922240050387, tangentialVectorX:0, tangentialVectorY:-0.0035999922240050387},
        {type:'mirror', title:'Flat Mirror', orientation:'x', grazingAngle:3.1415926, heightAmplification:1, horizontalTransverseSize:1, verticalTransverseSize:1, heightProfileFile:'mirror_1d.dat'},
        {type:'obstacle', title:'Obstacle', horizontalSize:0.5, verticalSize:0.5, shape:'r', horizontalOffset:0, verticalOffset:0},
        {type:'watch', title:'Watchpoint'},
    ];
    self.activeItem = null;
    self.isDirty = false;
    self.postPropagation = [];
    self.propagations = [];

    function addItem(item) {
        self.isDirty = true;
        var newItem = appState.clone(item);
        newItem.id = appState.maxId(appState.models.beamline) + 1;
        newItem.showPopover = true;
        if (appState.models.beamline.length) {
            newItem.position = parseFloat(appState.models.beamline[appState.models.beamline.length - 1].position) + 1;
        }
        else {
            newItem.position = 20;
        }
        if (newItem.type == 'watch')
            appState.models[appState.watchpointReportName(newItem.id)] = appState.cloneModel('initialIntensityReport');
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

    function modelChanged(event, name) {
        if (! appState.isLoaded())
            return;
        if (appState.applicationState()[name].photonEnergy)
            srwService.updatePhotonEnergy(name, appState.applicationState()[name].photonEnergy);
    }

    function updateIntensityFields() {
        $timeout(function() {
            var hidePrecision = appState.applicationState().simulation.sourceType == 'g';
            var fields = ['watchpointReport.precision', 'initialIntensityReport.precision'];
            for (var i = 0; i < fields.length; i++) {
                if (hidePrecision)
                    $(fieldClass(fields[i])).hide();
                else
                    $(fieldClass(fields[i])).show();
            }
        }, 500);
    }

    self.cancelChanges = function() {
        self.dismissPopup();
        appState.cancelChanges('beamline');
        self.isDirty = false;
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
        return appState.getWatchItems();
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
        self.isDirty = true;
    };

    self.saveChanges = function() {
        self.isDirty = false;
        // sort beamline based on position
        appState.models.beamline.sort(function(a, b) {
            return parseFloat(a.position) - parseFloat(b.position);
        });
        calculatePropagation();
        appState.saveBeamline();
    };

    self.showMirrorFileUpload = function() {
        self.fileUploadError = '';
        $('#srw-upload-mirror-file').modal('show');
    };

    self.showMirrorReport = function(model) {
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
        //TODO(pjm): should only set dirty if propagation value changes
        self.isDirty = true;
        calculatePropagation();
        self.dismissPopup();
        $('#srw-propagation-parameters').modal('show');
    };

    self.uploadMirrorFile = function(mirrorFile) {
        if (! mirrorFile)
            return;
        fileUpload.uploadFileToUrl(
            mirrorFile,
            requestSender.formatUrl(
                'uploadFile',
                {
                    '<simulation_id>': appState.models.simulation.simulationId,
                    '<simulation_type>': APP_SCHEMA.simulationType,
                }),
            function(data) {
                if (data.error) {
                    self.fileUploadError = data.error;
                    return;
                }
                else {
                    requestSender.mirrors.push(data.filename);
                    self.activeItem.heightProfileFile = data.filename;
                }
                $('#srw-upload-mirror-file').modal('hide');
            });
    };

    if (appState.isLoaded())
        updateIntensityFields();
    else {
        $scope.$on('modelsLoaded', updateIntensityFields);
    }

    $scope.$on('modelChanged', modelChanged);
});

app.controller('SRWSourceController', function (activeSection, appState, srwService, $scope) {
    activeSection.setActiveSection('source');
    var self = this;

    // keep gaussianBeam.photonEnergy in sync with report models
    function gaussianBeamChanged() {
        if (! appState.isLoaded)
            return;
        srwService.updatePhotonEnergy('gaussianBeam', appState.applicationState().gaussianBeam.photonEnergy);
    }

    function isSelected(sourceType) {
        if (appState.isLoaded())
            return appState.applicationState().simulation.sourceType == sourceType;
        return false;
    }

    self.isElectronBeam = function() {
        return self.isUndulator() || self.isMultipole();
    };

    self.isGaussianBeam = function() {
        return isSelected('g');
    };

    self.isMultipole = function() {
        return isSelected('m');
    };

    self.isUndulator = function() {
        return isSelected('u');
    };

    self.isPredefinedBeam = function() {
        if (appState.isLoaded())
            return appState.models.electronBeam.isReadOnly ? true : false;
        return false;
    };

    $scope.$on('gaussianBeam.changed', gaussianBeamChanged);
});
