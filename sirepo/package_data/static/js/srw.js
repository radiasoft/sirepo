'use strict';

app_local_routes.beamline = '/beamline/:simulationId';

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

    function isSelected(sourceType) {
        if (appState.isLoaded())
            return appState.applicationState().simulation.sourceType == sourceType;
        return false;
    }

    self.isApplicationMode = function(name) {
        return name == self.applicationMode;
    };

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

    $rootScope.$on('$routeChangeSuccess', function() {
        var search = $location.search();
        if (search && search.application_mode) {
            self.applicationMode = search.application_mode;
            if (self.isApplicationMode('wavefront') || self.isApplicationMode('calculator')) {
                // no multi-electron
                var characteristic = APP_SCHEMA.enum['Characteristic'];
                if (characteristic[1][0] == "1")
                    characteristic.splice(1, 1);
                for (var i = 0; i < characteristic.length; i++)
                    characteristic[i][1] = characteristic[i][1].replace(/Single-Electron /g, '');
            }
        }
    });

    return self;
});

app.controller('SRWBeamlineController', function (appState, fileUpload, frameCache, panelState, requestSender, srwService, $scope, $timeout) {
    var self = this;
    self.toolbarItems = [
        //TODO(pjm): move default values to separate area
        {type:'aperture', title:'Aperture', horizontalSize:1, verticalSize:1, shape:'r', horizontalOffset:0, verticalOffset:0},
        {type:'crl', title:'CRL', focalPlane:2, refractiveIndex:4.20756805e-06, attenuationLength:7.31294e-03, shape:1,
         horizontalApertureSize:1, verticalApertureSize:1, radius:1.5e-03, numberOfLenses:3, wallThickness:80.e-06},
        {type:'grating', title:'Grating', tangentialSize:0.2, sagittalSize:0.015, grazingAngle:12.9555790185373, normalVectorX:0, normalVectorY:0.99991607766, normalVectorZ:-0.0129552166147, tangentialVectorX:0, tangentialVectorY:0.0129552166147, diffractionOrder:1, grooveDensity0:1800, grooveDensity1:0.08997, grooveDensity2:3.004e-6, grooveDensity3:9.7e-11, grooveDensity4:0,},
        {type:'lens', title:'Lens', horizontalFocalLength:3, verticalFocalLength:1.e+23, horizontalOffset:0, verticalOffset:0},
        {type:'ellipsoidMirror', title:'Ellipsoid Mirror', focalLength:1.7, grazingAngle:3.6, tangentialSize:0.5, sagittalSize:0.01, normalVectorX:0, normalVectorY:0.9999935200069984, normalVectorZ:-0.0035999922240050387, tangentialVectorX:0, tangentialVectorY:-0.0035999922240050387, heightProfileFile:null, orientation:'x', heightAmplification:1},
        {type:'mirror', title:'Flat Mirror', orientation:'x', grazingAngle:3.1415926, heightAmplification:1, horizontalTransverseSize:1, verticalTransverseSize:1, heightProfileFile:'mirror_1d.dat'},
        {type:'sphericalMirror', title:'Spherical Mirror', 'radius':1049, 'tangentialSize':0.3, 'sagittalSize':0.11, 'grazingAngle':13.9626000172, 'normalVectorX':0, 'normalVectorY':0.9999025244842406, 'normalVectorZ':-0.013962146326506367,'tangentialVectorX':0, 'tangentialVectorY':0.013962146326506367, heightProfileFile:null, orientation:'x', heightAmplification:1},
        {type:'obstacle', title:'Obstacle', horizontalSize:0.5, verticalSize:0.5, shape:'r', horizontalOffset:0, verticalOffset:0},
        {type:'watch', title:'Watchpoint'},
    ];
    self.panelState = panelState;
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

    function preserveSign(item, field, newValue) {
        var oldValue = item[field];
        var wasNegative = isFinite(oldValue) && parseFloat(oldValue) < 0;
        item[field] = newValue;
        if ((wasNegative && item[field] > 0) || item[field] < 0)
            item[field] = - item[field];
    }

    self.cancelChanges = function() {
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
        return appState.getWatchItems();
    };

    self.handleModalShown = function(name, el) {
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

    self.saveChanges = function() {
        // sort beamline based on position
        appState.models.beamline.sort(function(a, b) {
            return parseFloat(a.position) - parseFloat(b.position);
        });
        calculatePropagation();
        appState.saveBeamline();
    };

    self.setActiveItem = function(item) {
        self.activeItem = item;
    };

    self.setSingleElectron = function(value) {
        self.singleElectron = value;
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
        calculatePropagation();
        self.dismissPopup();
        $('#srw-propagation-parameters').modal('show');
    };

    self.showTabs = function() {
        if (appState.getWatchItems().length == 0)
            return false;
        if (srwService.isApplicationMode('wavefront'))
            return false;
        return true;
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

    //TODO(pjm): coupled with controller named "beamline"
    $scope.$watch('beamline.activeItem.grazingAngle', function (newValue, oldValue) {
        if (newValue !== null && angular.isDefined(newValue) && isFinite(newValue) && angular.isDefined(oldValue) && isFinite(oldValue)) {
            var item = self.activeItem;
            var grazingAngle = parseFloat(newValue) / 1000.0;
            preserveSign(item, 'normalVectorZ', Math.sin(grazingAngle));

            if (isFinite(item.normalVectorY) && parseFloat(item.normalVectorY) == 0) {
                preserveSign(item, 'normalVectorX', Math.cos(grazingAngle));
                preserveSign(item, 'tangentialVectorX', Math.sin(grazingAngle));
                item.tangentialVectorY = 0;
            }
            if (isFinite(item.normalVectorX) && parseFloat(item.normalVectorX) == 0) {
                preserveSign(item, 'normalVectorY', Math.cos(grazingAngle));
                item.tangentialVectorX = 0
                preserveSign(item, 'tangentialVectorY', Math.sin(grazingAngle));
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

    //TODO(pjm): refactor and combine common code with WARP controller
    //TODO(pjm): merged from SRWMultiElectronController, separate into modules
    self.isAborting = false;
    self.isDestroyed = false;
    self.dots = '.';
    self.frameId = '-1';
    self.frameCount = 1;
    self.isReadyForModelChanges = false;
    self.elapsedDays = null;
    self.elapsedTime = null;

    frameCache.setAnimationArgs({
        multiElectronAnimation: [],
    });
    frameCache.setFrameCount(0);

    $scope.$on('$destroy', function () {
        self.isDestroyed = true;
    });

    function refreshStatus() {
        self.isReadyForModelChanges = true;
        requestSender.sendRequest(
            'runStatus',
            function(data) {
                //frameCache.setFrameCount(data.frameCount);
                if (self.isAborting)
                    return;

                if (data.frameId && (data.frameId != self.frameId)) {
                    self.frameId = data.frameId;
                    self.frameCount++;
                    frameCache.setFrameCount(self.frameCount);
                    frameCache.setCurrentFrame('multiElectronAnimation', self.frameCount - 1);
                }
                if (data.elapsedTime) {
                    self.elapsedDays = parseInt(data.elapsedTime / (60 * 60 * 24));
                    self.elapsedTime = new Date(1970, 0, 1);
                    self.elapsedTime.setSeconds(data.elapsedTime);
                }

                if (data.state != 'running') {
                    if (data.state != appState.models.simulationStatus.state)
                        appState.saveChanges('simulationStatus');
                }
                else {
                    if (! self.isDestroyed) {
                        self.dots += '.';
                        if (self.dots.length > 3)
                            self.dots = '.';
                        $timeout(refreshStatus, 4000);
                    }
                }
                appState.models.simulationStatus.state = data.state;
            },
            {
                models: appState.applicationState(),
                simulationType: APP_SCHEMA.simulationType,
            });
    }

    self.cancelSimulation = function() {
        if (appState.models.simulationStatus.state != 'running')
            return;
        appState.models.simulationStatus.state = 'canceled';
        self.isAborting = true;
        requestSender.sendRequest(
            'runCancel',
            function(data) {
                self.isAborting = false;
                appState.saveChanges('simulationStatus');
            },
            {
                models: appState.applicationState(),
                simulationType: APP_SCHEMA.simulationType,
            });
    };

    self.isInitializing = function() {
        if (self.isState('running'))
            return frameCache.frameCount < 1;
        return false;
    };

    self.isState = function(state) {
        if (appState.isLoaded())
            return appState.models.simulationStatus.state == state;
        return false;
    };

    self.runSimulation = function() {
        if (appState.models.simulationStatus.state == 'running')
            return;
        frameCache.setFrameCount(0);
        self.elapsedTime = null;
        self.elapsedDays = null;
        appState.models.simulationStatus.state = 'running';
        requestSender.sendRequest(
            'runBackground',
            function(data) {
                appState.models.simulationStatus.startTime = data['startTime'];
                appState.saveChanges('simulationStatus');
                refreshStatus();
            },
            {
                models: appState.applicationState(),
                simulationType: APP_SCHEMA.simulationType,
            });
    };

    $scope.$on('multiElectronAnimation.changed', function() {
        if (self.isReadyForModelChanges) {
            frameCache.setFrameCount(0);
            frameCache.clearFrames();
        }
    });

    if (appState.isLoaded())
        refreshStatus();
    else {
        $scope.$on('modelsLoaded', refreshStatus);
    }
});

app.controller('SRWSourceController', function (srwService) {
    var self = this;
    self.srwService = srwService;
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
            '<div data-modal-editor="simulationGrid" data-parent-controller="nav"></div>',
            '<div data-import-python=""></div>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;

            function updateSimulationGridFields(delay) {
                if (! appState.isLoaded())
                    return;
                var method = appState.models['simulation']['samplingMethod'];
                if (parseInt(method) == 1) {
                    $('.model-simulationGrid-sampleFactor').show(delay);
                    $('.model-simulation-horizontalPointCount').hide(delay);
                    $('.model-simulation-verticalPointCount').hide(delay);
                }
                else {
                    $('.model-simulationGrid-sampleFactor').hide(delay);
                    $('.model-simulation-horizontalPointCount').show(delay);
                    $('.model-simulation-verticalPointCount').show(delay);
                }
            }

            // hook for sampling method changes
            $scope.nav.handleModalShown = function(name, el) {
                updateSimulationGridFields(0);
            };
            $scope.$watch('appState.models.simulation.samplingMethod', function (newValue, oldValue) {
                updateSimulationGridFields(400);
            });
        },
    };
});

app.directive('appHeader', function(appState, srwService, requestSender, $location, $window) {

    var settingsIcon = [
        '<li class="dropdown"><a href class="dropdown-toggle srw-settings-menu hidden-xs" data-toggle="dropdown"><span class="srw-panel-icon glyphicon glyphicon-cog"></span></a>',
          '<ul class="dropdown-menu">',
            '<li data-ng-if="! srwService.isApplicationMode(\'calculator\')"><a href data-ng-click="showSimulationGrid()"><span class="glyphicon glyphicon-th"></span> Wavefront Simulation Grid</a></li>',
            '<li><a href data-ng-click="pythonSource()"><span class="glyphicon glyphicon-cloud-download"></span> Export Python Code</a></li>',
            '<li data-ng-if="canCopy()"><a href data-ng-click="copy()"><span class="glyphicon glyphicon-copy"></span> Open as a New Copy</a></li>',
            '<li data-ng-if="isExample()"><a href data-target="#srw-reset-confirmation" data-toggle="modal"><span class="glyphicon glyphicon-repeat"></span> Discard Changes to Example</a></li>',
            '<li data-ng-if="! isExample()"><a href data-target="#srw-delete-confirmation" data-toggle="modal""><span class="glyphicon glyphicon-trash"></span> Delete</a></li>',
          '</ul>',
        '</li>',
    ].join('');

    var rightNav = [
        '<ul class="nav navbar-nav navbar-right" data-ng-show="nav.isActive(\'simulations\') && ! srwService.isApplicationMode(\'light-sources\')">',
          '<li><a href data-target="#srw-simulation-editor" data-toggle="modal"><span class="glyphicon glyphicon-plus"></span> New</a></li>',
          '<li><a href data-ng-click="openImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>',
        '</ul>',

        '<ul class="nav navbar-nav navbar-right" data-ng-show="isLoaded()">',
          '<li data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
          '<li data-ng-class="{active: nav.isActive(\'beamline\')}"><a href data-ng-click="nav.openSection(\'beamline\')"><span class="glyphicon glyphicon-option-horizontal"></span> Beamline</a></li>',
          settingsIcon,
        '</ul>',
    ].join('');

    function navHeader(mode, modeTitle) {
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

            $scope.isExample = function() {
                if (appState.isLoaded())
                    return appState.models.simulation.isExample;
                return false;
            };

            $scope.isLoaded = function() {
                return appState.isLoaded();
            };

            $scope.openImportModal = function() {
                $('#srw-simulation-import').modal('show');
            };

            $scope.pythonSource = function(item) {
                $window.open(requestSender.formatUrl('pythonSource', {
                    '<simulation_id>': simulationId(),
                    '<simulation_type>': APP_SCHEMA.simulationType,
                }), '_blank');
            };

            $scope.showSimulationGrid = function() {
                $('#srw-simulationGrid-editor').modal('show');
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
            '<div class="srw-beamline-image">',
              '<span data-beamline-icon="", data-item="item"></span>',
            '</div>',
            '<div data-ng-attr-id="srw-item-{{ item.id }}" class="srw-beamline-element-label">{{ item.title }}<span class="caret"></span></div>',
        ].join(''),
        controller: function($scope) {
            $scope.removeElement = function(item) {
                $scope.$parent.beamline.removeElement(item);
            };
            $scope.showDeleteButton = function() {
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
                if (editor)
                    $('.srw-editor-holder').append(editor);
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
              '<form name="form" class="form-horizontal" novalidate>',
                '<div class="form-group form-group-sm" data-ng-repeat="f in advancedFields">',
                  '<div data-field-editor="f" data-model-name="modelName" data-model="beamline.activeItem"></div>',
                '</div>',
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
            $scope.advancedFields = appState.viewInfo($scope.modelName).advanced;
            $scope.removeActiveItem = function() {
                $scope.beamline.removeElement($scope.beamline.activeItem);
            }
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
                    '<span class="lead modal-title text-info">Import Python Beamline File</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<form name="importForm">',
                        '<div class="form-group">',
                          '<label>Select File</label>',
                          '<input id="srw-python-file-import" type="file" data-file-model="pythonFile">',
                          '<br />',
                          '<div class="text-warning"><strong>{{ fileUploadError }}</strong></div>',
                        '</div>',
                        '<div class="col-sm-6 pull-right">',
                          '<button data-ng-click="importPythonFile(pythonFile)" class="btn btn-primary">Import File</button>',
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

            $scope.importPythonFile = function(pythonFile) {
                if (! pythonFile)
                    return;
                fileUpload.uploadFileToUrl(
                    pythonFile,
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
                $scope.nav.revertToOriginal(srwService.applicationMode);
            };
            $scope.simulationName = function() {
                if (appState.isLoaded())
                    return appState.models.simulation.name;
                return '';
            };
        },
    };
});

app.directive('simulationStatusTimer', function() {
    return {
        restrict: 'A',
        scope: {
            controller: '=simulationStatusTimer',
        },
        template: [
            '<div data-ng-if="controller.elapsedTime">',
              '<br />Elapsed time: {{ controller.elapsedDays }} {{ controller.elapsedTime | date:\'HH:mm:ss\' }}',
            '</div>',
        ].join(''),
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
