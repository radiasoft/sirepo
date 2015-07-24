'use strict';

function wavefrontIntensityReportFields(title) {
    return {
        title: title,
        basic: [],
        advanced: [
            ['photonEnergy', 'Photon Energy [eV]', 'Float'],
            ['horizontalPosition', 'Horizontal Center Position [mm]', 'Float'],
            ['horizontalRange', 'Range of Horizontal Position [mm]', 'Float'],
            ['verticalPosition', 'Vertical Center Position [mm]', 'Float'],
            ['verticalRange', 'Range of Vertical Position [mm]', 'Float'],
            ['sampleFactor', 'Sampling Factor', 'Float'],
            ['method', 'Method for Integration', 'IntegrationMethod'],
            ['precision', 'Relative Precision', 'Float'],
            ['polarization', 'Polarization Component to Extract', 'Polarization'],
            ['characteristic', 'Characteristic to be Extracted', 'Characteristic'],
        ],
    };
}

// Application meta-data
var _ENUM = {
    ApertureShape: [
        ['r', 'Rectangular'],
        ['c', 'Circular'],
    ],
    Characteristic: [
        [0, 'Single-Electron Intensity'],
        [1, 'Multi-Electron Intensity'],
        [3, 'Single-Electron Flux'],
        [4, 'Multi-Electron Flux'],
        [5, 'Single-Electron Radiation Phase'],
        [6, 'Re(E): Real part of Single-Electron Electric Field'],
        [7, 'Im(E): Imaginary part of Single-Electron Electric Field'],
        [8, 'Single-Electron Intensity, integrated over Time or Photon Energy (i.e. Fluence)'],
    ],
    CRLShape: [
        [1, 'Parabolic'],
        [2, 'Circular'],
    ],
    FocalPlane: [
        [1, 'Horizontal'],
        [2, 'Vertical'],
        [3, 'Both'],
    ],
    Flux: [
        [1, 'Flux'],
        [2, 'Flux per Unit Surface'],
    ],
    IntegrationMethod: [
        [0, 'Manual'],
        [1, 'Auto-Undulator'],
        [2, 'Auto-Wiggler'],
    ],
    MirrorOrientation: [
        ['x', 'X'],
        ['y', 'Y'],
    ],
    Polarization: [
        [0, 'Linear Horizontal'],
        [1, 'Linear Vertical'],
        [2, 'Linear 45 degrees'],
        [3, 'Linear 135 degrees'],
        [4, 'Circular Right'],
        [5, 'Circular Left'],
        [6, 'Total'],
    ],
    PowerDensityMethod: [
        [1, 'Near Field'],
        [2, 'Far Field'],
    ],
    Symmetry: [
        [1, 'Symmetrical'],
        [-1, 'Anti-symmetrical'],
    ],
};
var _MODEL = {
    newSimulation: {
        title: 'New Simulation',
        advanced: [
            ['name', 'Name', 'String'],
        ],
    },
    simulation: {
        title: 'Simulation',
        advanced: [
            ['name', 'Name', 'String'],
        ],
    },
    electronBeam: {
        title: 'Electron Beam',
        basic: [
            ['beamName', 'Beam Name', 'BeamList'],
            ['current',  'Current [A]', 'Float'],
        ],
        advanced: [
            ['beamName', 'Beam Name', 'BeamList'],
            ['current',  'Current [A]', 'Float'],
            ['horizontalPosition', 'Average Horizontal Position [mm]', 'Float'],
            ['verticalPosition', 'Average Vertical Position [mm]', 'Float'],
            ['energyDeviation', 'Average Energy Deviation [GeV]', 'Float'],
        ],
    },
    undulator: {
        title: 'Undulator',
        basic: [
            ['period', 'Undulator Period [mm]', 'Float'],
            ['length', 'Undulator Length [m]', 'Float'],
            ['verticalAmplitude', 'Vertical Magnetic Field [T]', 'Float'],
        ],
        advanced: [
            ['period', 'Undulator Period [mm]', 'Float'],
            ['length', 'Undulator Length [m]', 'Float'],
            ['longitudinalPosition', 'Undulator Center Longitudinal Position [m]', 'Float'],
            ['horizontalAmplitude', 'Horizontal Magnetic Field [T]', 'Float'],
            ['horizontalSymmetry', 'Horizontal Symmetry', 'Symmetry'],
            ['horizontalInitialPhase', 'Initial Horizontal Phase [rad]', 'Float'],
            ['verticalAmplitude', 'Vertical Magnetic Field [T]', 'Float'],
            ['verticalSymmetry', 'Vertical Symmetry', 'Symmetry'],
            ['verticalInitialPhase', 'Initial Vertical Phase [rad]', 'Float'],
        ],
    },
    intensityReport: {
        title: 'Intensity Report',
        basic: [],
        advanced: [
            ['initialEnergy', 'Initial Photon Energy [eV]', 'Float'],
            ['finalEnergy', 'Final Photon Energy [eV]', 'Float'],
            ['horizontalPosition', 'Horizontal Position [mm]', 'Float'],
            ['verticalPosition', 'Vertical Position [mm]', 'Float'],
            ['method', 'Method for Integration', 'IntegrationMethod'],
            ['precision', 'Relative Precision', 'Float'],
            ['polarization', 'Polarization Component to Extract', 'Polarization'],
        ],
    },
    fluxReport: {
        title: 'Flux Report',
        basic: [],
        advanced: [
            ['initialEnergy', 'Initial Photon Energy [eV]', 'Float'],
            ['finalEnergy', 'Final Photon Energy [eV]', 'Float'],
            ['horizontalPosition', 'Horizontal Center Position [mm]', 'Float'],
            ['horizontalApertureSize', 'Horizontal Aperture Size [mm]', 'Float'],
            ['verticalPosition', 'Vertical Center Position [mm]', 'Float'],
            ['verticalApertureSize', 'Vertical Aperture Size [mm]', 'Float'],
            ['longitudinalPrecision', 'Longitudinal Integration Precision', 'Float'],
            ['azimuthalPrecision', 'Azimuthal Integration Precision', 'Float'],
            ['fluxType', 'Flux Calculation', 'Flux'],
            ['polarization', 'Polarization Component to Extract', 'Polarization'],
        ],
    },
    powerDensityReport: {
        title: 'Power Density Report',
        basic: [],
        advanced: [
            ['horizontalPosition', 'Horizontal Center Position [mm]', 'Float'],
            ['horizontalRange', 'Range of Horizontal Position [mm]', 'Float'],
            ['verticalPosition', 'Vertical Center Position [mm]', 'Float'],
            ['verticalRange', 'Range of Vertical Position [mm]', 'Float'],
            ['precision', 'Relative Precision', 'Float'],
            ['method', 'Power Density Computation Method', 'PowerDensityMethod'],
        ],
    },
    initialIntensityReport: wavefrontIntensityReportFields('Initial Intensity Report'),
    watchpointReport: wavefrontIntensityReportFields('Watchpoint Report'),
    aperture: {
        title: 'Aperture',
        basic: [],
        advanced: [
            ['title', 'Element Name', 'String'],
            ['position', 'Nominal Position [m]', 'Float'],
            ['shape', 'Shape', 'ApertureShape'],
            ['horizontalSize', 'Horizontal Size [mm]', 'Float'],
            ['verticalSize', 'Vertical Size [mm]', 'Float'],
        ],
    },
    lens: {
        title: 'Lens',
        basic: [],
        advanced: [
            ['title', 'Element Name', 'String'],
            ['position', 'Nominal Position [m]', 'Float'],
            ['horizontalFocalLength', 'Horizontal Focal Length [m]', 'Float'],
            ['verticalFocalLength', 'Vertical Focal Length [m]', 'Float'],
        ],
    },
    mirror: {
        title: 'Mirror',
        basic: [],
        advanced: [
            ['title', 'Element Name', 'String'],
            ['position', 'Nominal Position [m]', 'Float'],
            ['heightProfileFile', 'Height Profile Data File', 'File'],
            ['orientation', 'Orientation of Reflection Plane', 'MirrorOrientation'],
            ['grazingAngle', 'Grazing Angle [mrad]', 'Float'],
            ['heightAmplification', 'Height Amplification Coefficient', 'Float'],
            ['horizontalTransverseSize', 'Horizontal Transverse Size [mm]', 'Float'],
            ['verticalTransverseSize', 'Vertical Transverse Size [mm]', 'Float'],
        ],
    },
    crl: {
        title: 'CRL',
        basic: [],
        advanced: [
            ['title', 'Element Name', 'String'],
            ['position', 'Nominal Position [m]', 'Float'],
            ['focalPlane', 'Focal Plane', 'FocalPlane'],
            ['refractiveIndex', 'Refractive Index Decrements of Material', 'Float'],
            ['attenuationLength', 'Attenuation Length [m]', 'Float'],
            ['shape', 'Shape', 'CRLShape'],
            ['horizontalApertureSize', 'Horizontal Aperture Size [mm]', 'Float'],
            ['verticalApertureSize', 'Vertical Aperture Size [mm]', 'Float'],
            ['radius', 'Radius on Tip of Parabola [m]', 'Float'],
            ['numberOfLenses', 'Number of Lenses', 'Integer'],
            ['wallThickness', 'Wall Thickness at Tip of Parabola [m]', 'Float'],
        ],
    },
    watch: {
        title: 'Watchpoint',
        basic: [],
        advanced: [
            ['title', 'Element Name', 'String'],
            ['position', 'Nominal Position [m]', 'Float'],
        ],
    },
    obstacle: {
        title: 'Obstacle',
        basic: [],
        advanced: [
            ['title', 'Element Name', 'String'],
            ['position', 'Nominal Position [m]', 'Float'],
            ['shape', 'Shape', 'ApertureShape'],
            ['horizontalSize', 'Horizontal Size [mm]', 'Float'],
            ['verticalSize', 'Vertical Size [mm]', 'Float'],
        ],
    },
};

var app = angular.module('SRWApp', ['ngAnimate', 'ngDraggable', 'ngRoute', 'd3']);

app.config(function($routeProvider) {
    $routeProvider
        .when('/simulations', {
            controller: 'SimulationsController as simulations',
            templateUrl: '/static/html/simulations.html?20150723',
        })
        .when('/source/:simulationId', {
            controller: 'SourceController as source',
            templateUrl: '/static/html/source.html?20150723',
        })
        .when('/beamline/:simulationId', {
            controller: 'BeamlineController as beamline',
            templateUrl: '/static/html/beamline.html?20150723',
        })
        .otherwise({
            redirectTo: '/simulations'
        });
});

app.factory('appState', function($http, $rootScope) {
    var self = {};
    self.models = {};
    var reportCache = {};
    var savedModelValues = {};
    var runQueue = [];

    function cloneModel(name) {
        var val = name ? self.models[name] : self.models;
        return JSON.parse(JSON.stringify(val));
    }

    function executeQueue() {
        var currentQueue = runQueue;
        if (currentQueue.length === 0)
            return;
        $http.post('/srw/run', {
            report: currentQueue[0][0],
            models: savedModelValues,
        }).success(function(data, status) {
            var item = currentQueue.shift();

            if (data['error']) {
                self.models[item[0]]._error = data['error'];
            }
            else {
                reportCache[item[0]] = data;
                item[1](data);
            }
            //TODO(pjm): don't set loading to false unless there are no other queue items for this report
            if (self.models[item[0]])
                self.models[item[0]]._loading = false;
            executeQueue();
        }).error(function(data, status) {
            //TODO(pjm): combine error code with above
            console.log('run failed: ', status, ' ', data);
            currentQueue.shift();
            executeQueue();
        });
    }

    function updateReports() {
        reportCache = {};
        for (var key in self.models) {
            if (key.indexOf('Report') > 0) {
                $rootScope.$broadcast(key + '.changed');
            }
        }
    }

    self.cancelChanges = function(name) {
        if (savedModelValues[name])
            self.models[name] = JSON.parse(JSON.stringify(savedModelValues[name]));
    };

    self.clearModels = function(emptyValues) {
        reportCache = {};
        self.models = emptyValues || {};
        savedModelValues = {};
        runQueue = [];
    };

    self.getWatchItems = function() {
        if (self.isLoaded()) {
            var beamline = savedModelValues.beamline;
            var res = [];
            for (var i = 0; i < beamline.length; i++) {
                if (beamline[i]['type'] == 'watch')
                    res.push(beamline[i]);
            }
            return res;
        }
        return [];
    };

    self.getReportTitle = function(name) {
        //TODO(pjm): generalize this
        var match = name.match(/.*?(\d+)/);
        if (match) {
            var id = match[1];
            for (var i = 0; i < savedModelValues.beamline.length; i += 1) {
                if (savedModelValues.beamline[i].id == id)
                    return 'Intensity at ' + savedModelValues.beamline[i].title + ' Report';
            }
        }
        return self.modelInfo(name).title;
    }

    self.isLoaded = function() {
        return self.models['simulation'] && self.models['simulation']['simulationId'];
    };

    self.loadModels = function(simulationId) {
        if (self.isLoaded() && self.models['simulation']['simulationId'] == simulationId)
            return;
        self.clearModels();
        $http.get('/srw/simulation/' + simulationId)
            .success(function(data, status) {
                self.models = data['models'];
                savedModelValues = cloneModel();
                updateReports();
            })
            .error(function(data, status) {
                console.log('loadModels failed: ', simulationId);
            });
    };

    self.modelInfo = function(name) {
        return _MODEL[name];
    };

    self.requestData = function(name, callback) {
        if (reportCache[name])
            callback(reportCache[name]);
        else if (self.models[name]) {
            self.models[name]._loading = true;
            self.models[name]._error = null;
            runQueue.push([name, callback]);
            if (runQueue.length == 1)
                executeQueue();
        }
    };

    self.saveChanges = function(name) {
        console.log('save changes: ', name);
        delete(self.models[name]['_error']);
        savedModelValues[name] = cloneModel(name);
        if (name.indexOf('Report') > 0) {
            reportCache[name] = null;
        }
        else {
            if (name == 'beamline') {
                // need to save all watchpoinReports and propagations for beamline changes
                for (var modelName in self.models) {
                    if (modelName.indexOf('watchpoinReport') || modelName.indexOf('propagation'))
                        savedModelValues[modelName] = cloneModel(modelName);
                }
            }
            updateReports();
        }
        console.log('broadcast: ', name + '.changed');
        $rootScope.$broadcast(name + '.changed');
    };

    return self;
});

app.controller('SourceController', function ($rootScope, $route, appState) {
    $rootScope.activeSection = 'source';
    var self = this;
    appState.loadModels($route.current.params['simulationId']);
});

app.controller('BeamlineController', function ($rootScope, $route, $location, $timeout, appState) {
    $rootScope.activeSection = 'beamline';
    appState.loadModels($route.current.params['simulationId']);
    var self = this;
    self.toolbarItems = [
        //TODO(pjm): move default values to separate area
        {type:'aperture', title:'Aperture', horizontalSize:1, verticalSize:1},
        {type:'crl', title:'CRL', focalPlane:2, refractiveIndex:4.20756805e-06, attenuationLength:7.31294e-03, shape:1,
         horizontalApertureSize:1, verticalApertureSize:1, radius:1.5e-03, numberOfLenses:3, wallThickness:80.e-06},
        {type:'lens', title:'Lens', horizontalFocalLength:3, verticalFocalLength:1.e+23},
        {type:'mirror', title:'Mirror', orientation:'x', grazingAngle:3.1415926, heightAmplification:1, horizontalTransverseSize:1, verticalTransverseSize:1},
        {type:'obstacle', title:'Obstacle', horizontalSize:0.5, verticalSize:0.5},
        {type:'watch', title:'Watchpoint'},
    ];
    self.activeItem = null;
    self.isDirty = false;

    function maxId(beamline) {
        var max = 1;
        for (var i = 0; i < beamline.length; i++) {
            if (beamline[i].id > max)
                max = beamline[i].id;
        }
        return max;
    }

    function addItem(item) {
        //TODO(pjm): conslidate clone() -- move this code into appState
        self.isDirty = true;
        var newItem = $.extend(true, {}, item);
        newItem['id'] = maxId(appState.models.beamline) + 1;
        newItem['_show_popover'] = true;
        if (appState.models.beamline.length) {
            newItem.position = parseFloat(appState.models.beamline[appState.models.beamline.length - 1].position) + 1;
        }
        else {
            newItem.position = 20;
        }
        if (newItem['type'] == 'watch')
            appState.models['watchpointReport' + newItem['id']] = appState.cloneModel('initialIntensityReport');
        appState.models.beamline.push(newItem);
        $('.srw-beamline-element-label').popover('hide');
    }

    self.saveChanges = function() {
        self.isDirty = false;
        // sort beamline based on position
        appState.models.beamline.sort(function(a, b) {
            return parseFloat(a['position']) - parseFloat(b['position']);
        });
        calculatePropagation();
        appState.saveChanges('beamline');
    }

    self.cancelChanges = function() {
        appState.cancelChanges('beamline');
        //TODO(pjm): need to set clean later - the collection listener gets notified in later calls
        self.dismissPopup();
        $timeout(function() {
            self.isDirty = false;
        }, 300);
    }

    self.dismissPopup = function() {
        $('.srw-beamline-element-label').popover('hide');
    }

    self.propagations = [];
    self.postPropagation = [];

    function formatFloat(v) {
        var str = v.toFixed(4);
        str = str.replace(/0+$/, '');
        str = str.replace(/\.$/, '');
        return str;
    }

    function defaultItemPropagationParams() {
        return [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0];
    }

    function defaultDriftPropagationParams() {
        return [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0];
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

    self.getWatchItems = function() {
        return appState.getWatchItems();
    }

    self.getBeamline = function() {
        return appState.models.beamline;
    }

    self.isTouchscreen = function() {
        return Modernizr.touch;
    }

    self.openBeamlinePage = function() {
        $location.path('/beamline/' + appState.models['simulation']['simulationId']);
    }

    self.showPropagationModal = function() {
        //TODO(pjm): should only set dirty if propagation value changes
        self.isDirty = true;
        calculatePropagation();
        $('.srw-beamline-element-label').popover('hide');
        $('#srw-propagation-parameters').modal('show');
    }
    self.removeElement = function(item) {
        $('.srw-beamline-element-label').popover('hide');
        appState.models.beamline.splice(appState.models.beamline.indexOf(item), 1);
        self.isDirty = true;
    }

    self.dropComplete = function(data) {
        if (data && ! data['id']) {
            addItem(data);
        }
    }
    self.dropBetween = function(index, data) {
        if (! data)
            return;
        //console.log('dropBetween: ', index, ' ', data, ' ', data['id'] ? 'old' : 'new');
        var item;
        if (data['id']) {
            $('.srw-beamline-element-label').popover('hide');
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
    }
});

var NUMBER_REGEXP = /^\s*(\-|\+)?(\d+|(\d*(\.\d*)))([eE][+-]?\d+)?\s*$/;

app.directive('stringToNumber', function() {
    return {
        restrict: 'A',
        require: 'ngModel',
        link: function(scope, element, attrs, ngModel) {
            ngModel.$parsers.push(function(value) {
                if (ngModel.$isEmpty(value))
                    return null;
                if (NUMBER_REGEXP.test(value))
                    return parseFloat(value);
                return undefined;
            });
            ngModel.$formatters.push(function(value) {
                if (ngModel.$isEmpty(value))
                    return value;
                return value.toString();
            });
        }
    };
});

app.directive('fieldEditor', function(appState, $http) {
    return {
        restirct: 'A',
        scope: {
            fieldEditor: '=',
            model: '=',
        },
        template: [
            // field def: [name, label, type]
            '<label class="col-sm-5 control-label">{{ fieldEditor[1] }}</label>',
            '<div data-ng-switch="fieldEditor[2]">',
              '<div data-ng-switch-when="BeamList" class="col-sm-5">',
                '<select class="form-control" data-ng-model="model[fieldEditor[0]]" data-ng-options="item.name for item in appState.beams track by item.name"></select>',
              '</div>',
              '<div data-ng-switch-when="Float" class="col-sm-3">',
                '<input string-to-number="" data-ng-model="model[fieldEditor[0]]" class="form-control" style="text-align: right">',
              '</div>',
              '<div data-ng-switch-when="Integer" class="col-sm-3">',
                '<input data-ng-model="model[fieldEditor[0]]" class="form-control" style="text-align: right">',
              '</div>',
              //TODO(pjm): need file interface
              '<div data-ng-switch-when="File" class="col-sm-5">',
                '<p class="form-control-static"><a href="/static/dat/mirror_1d.dat"><span class="glyphicon glyphicon-file"></span> mirror_1d.dat</a></p>',
              '</div>',
              '<div data-ng-switch-when="String" class="col-sm-5">',
                '<input data-ng-model="model[fieldEditor[0]]" class="form-control">',
              '</div>',
              // assume it is an enum
              '<div data-ng-switch-default class="col-sm-5">',
                '<select class="form-control" data-ng-model="model[fieldEditor[0]]" data-ng-options="item[0] as item[1] for item in enum[fieldEditor[2]]"></select>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
        },
        link: function link(scope) {
            scope.enum = _ENUM;
            //TODO(pjm): move list loading logic into appState
            if (scope.fieldEditor[2] == 'BeamList') {
                if (appState.beams)
                    return;
                $http['get']('/static/json/beams.json')
                    .success(function(data, status) {
                        appState.beams = data;
                    })
                    .error(function() {
                        console.log('get beams.json failed!');
                    });
            }
        },
    };
});

app.directive('buttons', function(appState) {
    return {
        scope: {
            formName: '=',
            modelName: '=',
            modalId: '@',
        },
        template: [
            '<div class="col-sm-6 pull-right cssFade" data-ng-show="formName.$dirty">',
            '<button data-ng-click="saveChanges()" class="btn btn-primary {{ formName.$valid ? \'\' : \'disabled\' }}">Save Changes</button> ',
              '<button data-ng-click="cancelChanges()" class="btn btn-default">Cancel</button>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            function changeDone() {
                $scope.formName.$setPristine();
                if ($scope.modalId)
                    $('#' + $scope.modalId).modal('hide');
            }
            $scope.$on($scope.modelName + '.changed', function() {
                changeDone();
            });
            $scope.saveChanges = function() {
                if ($scope.formName.$valid)
                    appState.saveChanges($scope.modelName);
            };
            $scope.cancelChanges = function() {
                appState.cancelChanges($scope.modelName);
                changeDone();
            };
        }
    };
});

app.directive('panelHeading', function() {
    return {
        restrict: 'A',
        scope: {
            panelHeading: '@',
            model: '=',
            editorId: '@',
            allowFullScreen: '@',
        },
        controller: function($scope) {
            $scope.toggleVisible = function() {
                if ($scope.model)
                    $scope.model['_visible'] = ! $scope.model['_visible'];
            };
            $scope.isVisible = function() {
                if ($scope.model)
                    return $scope.model['_visible'];
                return false;
            };
            $scope.showEditor = function() {
                $('#' + $scope.editorId).modal('show');
            };
        },
        template: [
            '<span class="lead">{{ panelHeading }}</span>',
            '<div class="srw-panel-options pull-right">',
            '<a href data-ng-click="showEditor()" title="Edit"><span class="lead glyphicon glyphicon-pencil"></span></a> ',
            //'<a href data-ng-show="allowFullScreen" title="Download"><span class="lead glyphicon glyphicon-cloud-download"></span></a> ',
            //'<a href data-ng-show="allowFullScreen" title="Full screen"><span class="lead glyphicon glyphicon-fullscreen"></span></a> ',
            '<a href data-ng-click="toggleVisible()" data-ng-show="isVisible()" title="Hide"><span class="lead glyphicon glyphicon-triangle-top"></span></a> ',
            '<a href data-ng-click="toggleVisible()" data-ng-hide="isVisible()" title="Show"><span class="lead glyphicon glyphicon-triangle-bottom"></span></a>',
            '</div>',
        ].join(''),
    };
});

app.directive('panelBody', function() {
    return {
        restrict: 'E',
        transclude: true,
        scope: {
            model: '=',
        },
        controller: function($scope) {
        },
        template: [
            '<div data-ng-class="{\'srw-panel-loading\': model._loading, \'srw-panel-error\': model._error}" class="panel-body cssFade" data-ng-show="model._visible">',
            '<div data-ng-show="model._loading" class="lead srw-panel-wait"><span class="glyphicon glyphicon-hourglass"></span> Refreshing...</div>',
            '<div data-ng-show="model._error" class="lead srw-panel-wait"><span class="glyphicon glyphicon-exclamation-sign"></span> {{ model._error }}</div>',
            '<ng-transclude></ng-transclude>',
            '</div>',
        ].join(''),
    };
});

app.controller('NavController', function ($rootScope, $location, appState) {
    var self = this;
    self.pageTitle = function() {
        return $.grep(
            [
                self.sectionTitle(),
                'SRW',
                'Radiasoft',
            ],
            function(n){ return n })
            .join(' - ');
    }
    self.sectionTitle = function() {
        if ($rootScope.activeSection == 'simulations')
            return null;
        if (appState.isLoaded())
            return appState.models.simulation.name;
        return null;
    }
    self.openSection = function(name) {
        //TODO(pjm): centralize route management
        $location.path(
            ('/' + name) + (
                name == 'simulations'
                    ? ''
                    : ('/' + appState.models['simulation']['simulationId'])
            )
        );
    }
});

app.controller('SimulationsController', function ($rootScope, $http, $location, $window, appState) {
    $rootScope.activeSection = 'simulations';
    appState.clearModels({
        newSimulation: {},
    });
    var self = this;

    function newSimulation(name) {
        $http.post('/srw/new-simulation', {
            name: name,
        }).success(function(data, status) {
            self.open(data['models']['simulation']);
        }).error(function(data, status) {
            console.log('new-simulation failed: ', status, ' ', data);
        });
    }

    function loadList() {
        $http['get']('/srw/simulation-list')
            .success(function(data, status) {
                self.list = data;
            })
            .error(function() {
                console.log('get simulation list failed!');
            });
    }

    self.list = [];
    self.selected = null;
    self.isSelected = function(item) {
        return self.selected && self.selected == item;
    }
    self.selectItem = function(item) {
        self.selected = item;
    }
    self.deleteSelected = function() {
        $http.post('/srw/delete-simulation', {
            simulationId: self.selected['simulationId'],
        }).success(function(data, status) {
            loadList();
        }).error(function(data, status) {
            console.log('delete-simulation failed: ', status, ' ', data);
        });
        self.selected = null;
    }
    $rootScope.$on('newSimulation.changed', function() {
        if (appState.models.newSimulation.name) {
            newSimulation(appState.models.newSimulation.name);
            appState.models.newSimulation.name = '';
            appState.saveChanges('newSimulation');
        }
    });
    self.open = function(item) {
        //TODO(pjm): centralize route management
        $location.path('/source/' + item.simulationId);
    }
    self.copy = function(item) {
        $http.post('/srw/copy-simulation', {
            simulationId: self.selected['simulationId'],
        }).success(function(data, status) {
            self.open(data['models']['simulation']);
        }).error(function(data, status) {
            console.log('copy-simulation failed: ', status, ' ', data);
        });
    }
    self.pythonSource = function(item) {
        $window.open('/srw/python-source/' + self.selected['simulationId'], '_blank');
    }
    loadList()
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
              '<g data-ng-switch-when="mirror">',
                '<rect x="23" y="0" width="5", height="60" class="srw-mirror" />',
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
            '<span data-ng-click="removeElement(item)" class="srw-beamline-close-icon glyphicon glyphicon-remove-circle"></span>',
            '<div class="srw-beamline-image">',
              '<span data-beamline-icon="", data-item="item"></span>',
            '</div>',
            '<div data-ng-attr-id="srw-item-{{ item.id }}" class="srw-beamline-element-label">{{ item.title }}<span class="caret"></span></div>',
        ].join(''),
        controller: function($scope) {
            $scope.removeElement = function(item) {
                $scope.$parent.beamline.removeElement(item);
            };
        },
        link: function(scope, element) {
            scope.$watchCollection('item', function(newValue, oldValue) {
                if (newValue != oldValue)
                    scope.$parent.beamline.isDirty = true;
            });
            var el = $(element).find('.srw-beamline-element-label');
            el.popover({
                html: true,
                placement: 'bottom',
                container: '.srw-popup-container-lg',
                viewport: { selector: '.srw-beamline'},
                content: $('#srw-' + scope.item.type + '-editor'),
                trigger: 'manual',
            }).on('show.bs.popover', function() {
                scope.$parent.beamline.activeItem = scope.item;
            }).on('hide.bs.popover', function() {
                scope.$parent.beamline.activeItem = null;
            }).on('hidden.bs.popover', function() {
                var active = scope.$parent.beamline.activeItem;
                if (active && active.type == scope.item.type)
                    return;
                var editor = el.data('bs.popover').getContent();
                // return the editor to the editor-holder so it will be available for the
                // next element of this type
                if (editor && $('.srw-' + scope.item.type + '-editor').length == 0) {
                    $('.srw-editor-holder').append(editor);
                }
            });

            function togglePopover() {
                $('.srw-beamline-element-label').not(el).popover('hide');
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
                $(element).click(function() {
                    togglePopover();
                });
            }
            if (scope.item['_show_popover']) {
                delete scope.item['_show_popover'];
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
                    el.on('shown.bs.popover', function() {
                        $('.popover-content .form-control').first().select();
                    });
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

app.directive('panel', function(appState) {
    return {
        scope: {
            modelName: '@',
        },
        template: [
            '<div class="panel panel-info">',
              '<div class="panel-heading" data-panel-heading="{{ panelTitle }}" data-model="appState.models[modelName]" data-editor-id="{{ editorId }}"></div>',
              '<div class="panel-body cssFade" data-ng-show="appState.models[modelName]._visible">',
                '<form name="f0" class="form-horizontal">',
                  '<div class="form-group form-group-sm" data-ng-repeat="f in basicFields">',
                    '<div data-field-editor="f" data-model="appState.models[modelName]"></div>',
                  '</div>',
                  '<div data-buttons="" data-model-name="modelName" data-form-name="f0"></div>',
                '</form>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
            $scope.basicFields = appState.modelInfo($scope.modelName).basic;
            $scope.panelTitle = appState.modelInfo($scope.modelName).title;
            $scope.editorId = 'srw-' + $scope.modelName + '-editor';
        },
    };
});

app.directive('reportPanel', function(appState) {
    return {
        scope: {
            reportPanel: '@',
            modelName: '@',
            // optional, for watch reports
            item: '=',
        },
        template: [
            '<div class="panel panel-info">',
              '<div class="panel-heading" data-panel-heading="{{ appState.getReportTitle(fullModelName) }}" data-model="appState.models[fullModelName]" data-editor-id="{{ editorId }}" data-allow-full-screen="1"></div>',
              '<panel-body data-model="appState.models[fullModelName]">',

                '<div data-ng-switch="reportPanel">',
                  '<div data-ng-switch-when="2d" data-plot2d="" class="srw-plot-2d" data-model-name="{{ fullModelName }}" id="{{ plotId }}"></div>',
                  '<div data-ng-switch-when="3d" data-plot3d="" class="srw-plot-3d" data-model-name="{{ fullModelName }}" id="{{ plotId }}"></div>',
                '</div>',
              '</panel-body>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var itemId = $scope.item ? $scope.item.id : '';
            $scope.appState = appState;
            $scope.fullModelName = $scope.modelName + itemId;
            $scope.editorId = 'srw-' + $scope.fullModelName + '-editor';
            $scope.plotId = 'srw-' + $scope.modelName + '-' + $scope.reportPanel + '-plot' + itemId;
        },
    };
});

app.directive('modalEditor', function(appState) {
    return {
        scope: {
            modalEditor: '@',
            // optional, for watch reports
            itemId: '@',
        },
        template: [
            '<div class="modal fade" id="{{ editorId }}" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
  	            '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
	            '<span class="lead modal-title text-info">{{ appState.getReportTitle(fullModelName) }}</span>',
	          '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<div class="row">',
                        '<form name="f1" class="form-horizontal">',
                          '<div class="form-group form-group-sm" data-ng-repeat="f in advancedFields">',
                            '<div data-field-editor="f" data-model="appState.models[fullModelName]"></div>',
                          '</div>',
                          '<div data-buttons="" data-model-name="fullModelName" data-form-name="f1" data-modal-id="{{ editorId }}"></div>',
                        '</form>',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
            $scope.advancedFields = appState.modelInfo($scope.modalEditor).advanced;
            $scope.fullModelName = $scope.modalEditor + ($scope.itemId || '');
            $scope.editorId = 'srw-' + $scope.fullModelName + '-editor';
        },
        link: function(scope, element) {
            $(element).on('hidden.bs.modal', function(e) {
                // ensure that a dismissed modal doesn't keep changes
                // ok processing will have already saved data before the modal is hidden
                appState.cancelChanges(scope.fullModelName);
                scope.$apply();
            });
            scope.$on('$destroy', function() {
                // release modal data to prevent memory leak
                $(element).off();
                $('.modal').modal('hide').removeData('bs.modal');
            });
        },
    };
});

app.directive('beamlineEditor', function(appState) {
    return {
        scope: {
            modelName: '@',
        },
        template: [
            '<div>',
              '<form name="f2" class="form-horizontal">',
                '<div class="form-group form-group-sm" data-ng-repeat="f in advancedFields">',
                  '<div data-field-editor="f" data-model="beamline.activeItem"></div>',
                '</div>',
                '<div class="form-group">',
                  '<div class="col-sm-offset-6 col-sm-3">',
                    '<button ng-click="beamline.dismissPopup()" style="width: 100%" type="submit" class="btn btn-primary">Close</button>',
                  '</div>',
                '</div>',
                '<div class="form-group" data-ng-show="beamline.isTouchscreen()">',
                  '<div class="col-sm-offset-6 col-sm-3">',
                    '<button ng-click="removeActiveItem()" style="width: 100%" type="submit" class="btn btn-danger">Delete</button>',
                  '</div>',
                '</div>',
              '</form>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.beamline = $scope.$parent.beamline;
            $scope.advancedFields = appState.modelInfo($scope.modelName).advanced;
            $scope.removeActiveItem = function() {
                $scope.beamline.removeElement($scope.beamline.activeItem);
            }
            //TODO(pjm): investigate why id needs to be set in html for revisiting the beamline page
            //$scope.editorId = 'srw-' + $scope.modelName + '-editor';
        },
    };
});
