'use strict';

//TODO(pjm): needs consistent property/function naming convension
// functionNamesLikeThis, variableNamesLikeThis, ClassNamesLikeThis, EnumNamesLikeThis, methodNamesLikeThis, CONSTANT_VALUES_LIKE_THIS, foo.namespaceNamesLikeThis.bar, and filenameslikethis.js.

// Application meta-data
var _ENUM = {
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
    initialIntensityReport: {
        title: 'Initial Intensity Report',
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
    },
    watchpointReport: {
        title: 'Watchpoint Report',
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
    },
    aperture: {
        title: 'Aperture',
        basic: [],
        advanced: [
            ['title', 'Element Name', 'String'],
            ['position', 'Nominal Position [m]', 'Float'],
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
            templateUrl: '/static/html/simulations.html?20150626',
        })
        .when('/source/:simulationId', {
            controller: 'SourceController as source',
            templateUrl: '/static/html/source.html?20150626',
        })
        .when('/beamline/:simulationId', {
            controller: 'BeamlineController as beamline',
            templateUrl: '/static/html/beamline.html?20150626',
        })
        .otherwise({
            redirectTo: '/simulations'
        });
});

app.factory('appState', function($http, $rootScope) {
    var self = {};
    self.models = {};
    self.reportCache = {};
    self.saved_model_values = {};

    var clone_model = function(name) {
        var val = name ? self.models[name] : self.models;
        return JSON.parse(JSON.stringify(val));
    };

    function update_reports() {
        self.reportCache = {};
        for (var key in self.models) {
            if (key.indexOf('Report') > 0) {
                $rootScope.$broadcast(key + '.changed');
            }
        }
    }

    var model_info = function(name) {
        return _MODEL[name];
    };

    var run_queue = [];

    function execute_queue() {
        var current_queue = run_queue;
        if (current_queue.length === 0)
            return;
        $http.post('/srw/run', {
            report: current_queue[0][0],
            models: self.saved_model_values,
        }).success(function(data, status) {
            var item = current_queue.shift();

            if (data['error']) {
                self.models[item[0]]._error = data['error'];
            }
            else {
                self.reportCache[item[0]] = data;
                item[1](data);
            }
            //TODO(pjm): don't set loading to false unless there are no other queue items for this report
            if (self.models[item[0]])
                self.models[item[0]]._loading = false;
            execute_queue();
        }).error(function(data, status) {
            //TODO(pjm): combine error code with above
            console.log('run failed: ', status, ' ', data);
            current_queue.shift();
            execute_queue();
        });
    }

    self.clone_model = clone_model;
    self.model_info = model_info;
    self.is_loaded = function() {
        return self.models['simulation'] && self.models['simulation']['simulationId'];
    };
    self.clear_models = function(emptyValues) {
        self.reportCache = {};
        self.models = emptyValues || {};
        self.saved_model_values = {};
        run_queue = [];
    };
    self.load_models = function(simulationId) {
        if (self.is_loaded() && self.models['simulation']['simulationId'] == simulationId)
            return;
        self.clear_models();
        $http.get('/srw/simulation/' + simulationId)
            .success(function(data, status) {
                self.models = data['models'];
                self.saved_model_values = clone_model();
                update_reports();
            })
            .error(function(data, status) {
                console.log('load_models failed: ', simulationId);
            });
    };
    self.request_data = function(name, callback) {
        if (self.reportCache[name])
            callback(self.reportCache[name]);
        else if (self.models[name]) {
            self.models[name]._loading = true;
            self.models[name]._error = null;
            run_queue.push([name, callback]);
            if (run_queue.length == 1)
                execute_queue();
        }
    };
    self.save_changes = function(name) {
        console.log('save changes: ', name);
        delete(self.models[name]['_error']);
        self.saved_model_values[name] = clone_model(name);
        if (name.indexOf('Report') > 0) {
            self.reportCache[name] = null;
        }
        else {
            if (name == 'beamline') {
                // need to save all watchpoinReports and propagations for beamline changes
                for (var modelName in self.models) {
                    if (modelName.indexOf('watchpoinReport') || modelName.indexOf('propagation'))
                        self.saved_model_values[modelName] = clone_model(modelName);
                }
            }
            update_reports();
        }
        console.log('broadcast: ', name + '.changed');
        $rootScope.$broadcast(name + '.changed');
    };
    self.cancel_changes = function(name) {
        if (self.saved_model_values[name])
            self.models[name] = JSON.parse(JSON.stringify(self.saved_model_values[name]));
    };
    self.get_report_title = function(name) {
        //TODO(pjm): generalize this
        var match = name.match(/.*?(\d+)/);
        if (match) {
            var id = match[1];
            for (var i = 0; i < self.saved_model_values.beamline.length; i += 1) {
                if (self.saved_model_values.beamline[i].id == id)
                    return 'Intensity at ' + self.saved_model_values.beamline[i].title + ' Report';
            }
        }
        return model_info(name).title;
    }
    return self;
});

app.controller('SourceController', function ($rootScope, $route, appState) {
    $rootScope.activeSection = 'source';
    var self = this;
    appState.load_models($route.current.params['simulationId']);
});

app.controller('BeamlineController', function ($rootScope, $route, $location, $timeout, appState) {
    $rootScope.activeSection = 'beamline';
    appState.load_models($route.current.params['simulationId']);
    var self = this;
    self.toolbar_items = [
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
    self.is_dirty = false;

    function max_id(beamline) {
        var max = 1;
        for (var i = 0; i < beamline.length; i++) {
            if (beamline[i].id > max)
                max = beamline[i].id;
        }
        return max;
    }

    function add_item(item) {
        //TODO(pjm): conslidate clone() -- move this code into appState
        self.is_dirty = true;
        var new_item = $.extend(true, {}, item);
        new_item['id'] = max_id(appState.models.beamline) + 1;
        new_item['_show_popover'] = true;
        if (appState.models.beamline.length) {
            new_item.position = parseFloat(appState.models.beamline[appState.models.beamline.length - 1].position) + 1;
        }
        else {
            new_item.position = 20;
        }
        if (new_item['type'] == 'watch')
            appState.models['watchpointReport' + new_item['id']] = appState.clone_model('initialIntensityReport');
        appState.models.beamline.push(new_item);
        $('.srw-beamline-element-label').popover('hide');
    }

    self.save_changes = function() {
        self.is_dirty = false;
        // sort beamline based on position
        appState.models.beamline.sort(function(a, b) {
            return parseFloat(a['position']) - parseFloat(b['position']);
        });
        calculate_propagation();
        appState.save_changes('beamline');
    }

    self.cancel_changes = function() {
        appState.cancel_changes('beamline');
        //TODO(pjm): need to set clean later - the collection listener gets notified in later calls
        self.dismiss_popup();
        $timeout(function() {
            self.is_dirty = false;
        }, 300);
    }

    self.dismiss_popup = function() {
        $('.srw-beamline-element-label').popover('hide');
    }
    var _DEFAULT_ITEM_PROPAGATION_PARAMS = [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0];
    var _DEFAULT_DRIFT_PROPAGATION_PARAMS = [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0];

    self.propagations = [];
    self.post_propagation = [];

    function format_float(v) {
        var str = v.toFixed(4);
        str = str.replace(/0+$/, '');
        str = str.replace(/\.$/, '');
        return str;
    }

    function calculate_propagation() {
        if (! appState.is_loaded())
            return;
        var beamline = appState.models.beamline;
        if (! appState.models.propagation)
            appState.models.propagation = {};
        var propagation = appState.models.propagation;
        self.propagations = [];
        for (var i = 0; i < beamline.length; i++) {
            if (! propagation[beamline[i].id]) {
                propagation[beamline[i].id] = [
                    _DEFAULT_ITEM_PROPAGATION_PARAMS.slice(),
                    _DEFAULT_DRIFT_PROPAGATION_PARAMS.slice(),
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
                    title: 'Drift ' + format_float(d) + 'm',
                    params: p[1],
                });
            }
        }
        if (! appState.models.post_propagation || appState.models.post_propagation.length == 0)
            appState.models.post_propagation = _DEFAULT_ITEM_PROPAGATION_PARAMS.slice();
        self.post_propagation = appState.models.post_propagation;
    }

    self.get_beamline = function(itemType) {
        if (itemType && appState.is_loaded()) {
            // use the saved beamline for specific types (watch)
            var beamline = appState.saved_model_values.beamline;
            var res = [];
            for (var i = 0; i < beamline.length; i++) {
                if (beamline[i]['type'] == itemType)
                    res.push(beamline[i]);
            }
            return res;
        }
        return appState.models.beamline;
    }

    self.is_touchscreen = function() {
        return Modernizr.touch;
    }

    self.open_beamline_page = function() {
        $location.path('/beamline/' + appState.models['simulation']['simulationId']);
    }

    self.show_propagation_modal = function() {
        //TODO(pjm): should only set dirty if propagation value changes
        self.is_dirty = true;
        calculate_propagation();
        $('.srw-beamline-element-label').popover('hide');
        $('#srw-propagation-parameters').modal('show');
    }
    self.remove_element = function(item) {
        $('.srw-beamline-element-label').popover('hide');
        appState.models.beamline.splice(appState.models.beamline.indexOf(item), 1);
        self.is_dirty = true;
    }

    self.drop_complete = function(data) {
        if (data && ! data['id']) {
            add_item(data);
        }
    }
    self.drop_between = function(index, data) {
        if (! data)
            return;
        //console.log('drop_between: ', index, ' ', data, ' ', data['id'] ? 'old' : 'new');
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
            '<button data-ng-click="save_changes()" class="btn btn-primary {{ formName.$valid ? \'\' : \'disabled\' }}">Save Changes</button> ',
              '<button data-ng-click="cancel_changes()" class="btn btn-default">Cancel</button>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            function change_done() {
                $scope.formName.$setPristine();
                if ($scope.modalId)
                    $('#' + $scope.modalId).modal('hide');
            }
            $scope.$on($scope.modelName + '.changed', function() {
                change_done();
            });
            $scope.save_changes = function() {
                if ($scope.formName.$valid)
                    appState.save_changes($scope.modelName);
            };
            $scope.cancel_changes = function() {
                appState.cancel_changes($scope.modelName);
                change_done();
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

app.directive('plot2d', function(appState, d3Service) {

    var formatter;
    var margin = {top: 50, right: 50, bottom: 80, left: 70};

    function linspace(start, stop, nsteps) {
        var delta = (stop - start) / (nsteps - 1);
        return d3.range(start, stop + delta, delta).slice(0, nsteps);
    }

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            id: '@',
        },
        template: [
            '<svg></svg>',
            '<div style="margin-left: 30px" class="text-center"><strong>{{ x_range[0] | number }}</strong><input type="text" class="srw-plot2d-slider" value="" data-slider-min="0" data-slider-max="100" data-slider-step="1" data-slider-value="[0,100]" data-slider-tooltip="hide"><strong>{{ x_range[1] | number }}</strong></div>',
        ].join(''),
        controller: function($scope) {

            $scope.compute_peaks = function(json, dimensions, x_points) {
                var peak_spacing = dimensions[0] / 20;
                var min_pixel_height = dimensions[1] * .995;
                var x_peak_values = [];
                var sorted_points = d3.zip(x_points, json.points).sort(function(a, b) { return b[1] - a[1] });
                for (var i = 0; i < sorted_points.length / 2; i++) {
                    var p = sorted_points[i]
                    var x_pixel = $scope.x_axis_scale(p[0]);
                    var y_pixel = $scope.y_axis_scale(p[1]);
                    if (y_pixel >= min_pixel_height) {
                        break;
                    }
                    var found = false;
                    for (var j = 0; j < x_peak_values.length; j++) {
                        if (Math.abs(x_pixel - x_peak_values[j][2]) < peak_spacing) {
                            found = true;
                            break;
                        }
                    }
                    if (! found)
                        x_peak_values.push([p[0], p[1], x_pixel]);
                }
                //console.log('local maxes: ', x_peak_values.length);
                return x_peak_values;
            };

            $scope.init = function(id) {
                $scope.plot_id = '#' + id;
                formatter = d3.format(',.0f')
                $scope.slider = $($scope.plot_id + ' .srw-plot2d-slider').slider();
                $scope.slider.on('slide', $scope.slider_changed);
                $(window).resize($scope.resize);
                $scope.x_axis_scale = d3.scale.linear();
                $scope.y_axis_scale = d3.scale.linear();
                $scope.x_axis = d3.svg.axis()
                    .scale($scope.x_axis_scale)
                    .orient('bottom');
                $scope.x_axis_grid = d3.svg.axis()
                    .scale($scope.x_axis_scale)
                    .orient('bottom');
                $scope.y_axis = d3.svg.axis()
                    .scale($scope.y_axis_scale)
                    // this causes a "number of fractional digits" error in MSIE
                    //.tickFormat(d3.format('e'))
                    .tickFormat(function (value) {
                        return value.toExponential();
                    })
                    .ticks(5)
                    .orient('left');
                $scope.y_axis_grid = d3.svg.axis()
                    .scale($scope.y_axis_scale)
                    .orient('left');
                $scope.graph_line = d3.svg.line()
                    .x(function(d) {return $scope.x_axis_scale(d[0])})
                    .y(function(d) {return $scope.y_axis_scale(d[1])});

                $scope.svg = $scope.select('svg')
                var context = $scope.svg
                    .append('g')
                    .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');
                context.append('g')
                    .attr('class', 'x axis')
                context.append('g')
                    .attr('class', 'x axis grid')
                context.append('g')
                    .attr('class', 'y axis')
                context.append('g')
                    .attr('class', 'y axis grid')
                context.append('text')
                    .attr('transform', 'rotate(-90)')
                    .attr('class', 'y-axis-label')
                    .attr('y', - margin.left)
                    .attr('dy', '1em')
                    .style('text-anchor', 'middle');
                context.append('text')
                    .attr('class', 'x-axis-label')
                    .attr('dy', '1em')
                    .style('text-anchor', 'middle');
                context.append('text')
                    .attr('class', 'main-title')
                    .attr('y', - margin.top / 2)
                    .style('text-anchor', 'middle');

                var focus = context.append('g')
                    .attr('class', 'focus')
                    .style('display', 'none');
                focus.append('circle')
                    .attr('r', 6);
                focus.append('text')
                    .attr('class', 'focus-text')
                    .attr('x', 9)
                    .attr('dy', '.35em');
                context.append('rect')
                    .attr('class', 'overlay')
                    .on('mouseover', function() { focus.style('display', null); })
                    .on('mouseout', function() { focus.style('display', 'none'); })
                    .on('mousemove', $scope.mousemove);

                var viewport = context.append('svg')
                    .attr('class', 'plot-viewport');
                viewport.append('path')
                    .attr('class', 'line');
            };

            $scope.load = function(json) {
                var x_points = linspace(json.x_range[0], json.x_range[1], json.points.length);
                $scope.points = d3.zip(x_points, json.points);
                $scope.x_range = json.x_range;
                $scope.x_units = json.x_units;
                $scope.x_axis_scale.domain([json.x_range[0], json.x_range[1]]);
                $scope.y_axis_scale.domain([d3.min(json.points), d3.max(json.points)]);
                $scope.select('.y-axis-label').text(json.y_label);
                $scope.select('.x-axis-label').text(json.x_label);
                $scope.select('.main-title').text(json.title);
                $scope.select('.line').datum($scope.points);
                var dimensions = $scope.resize();
                $scope.x_peak_values = $scope.compute_peaks(json, dimensions, x_points);
            };

            $scope.mousemove = function() {
                if (! $scope.points)
                    return;
                var x0 = $scope.x_axis_scale.invert(d3.mouse(this)[0]);
                var local_max = null;
                for (var i = 0; i < $scope.x_peak_values.length; i++) {
                    var v = $scope.x_peak_values[i];
                    if (local_max === null || Math.abs(v[0] - x0) < Math.abs(local_max[0] - x0)) {
                        local_max = v;
                    }
                }
                if (local_max) {
                    var x_pixel = $scope.x_axis_scale(local_max[0]);
                    if (x_pixel < 0 || x_pixel >= $scope.select('.plot-viewport').attr('width'))
                        return;
                    var focus = $scope.select('.focus');
                    focus.attr('transform', 'translate(' + x_pixel + ',' + $scope.y_axis_scale(local_max[1]) + ')');
                    focus.select('text').text(formatter(local_max[0]) + ' ' + $scope.x_units);
                }
            };

            $scope.resize = function() {
                if (! $scope.points)
                    return;
                var width = parseInt($scope.select().style('width')) - margin.left - margin.right;
                var height = parseInt($scope.select().style('height')) - margin.top - margin.bottom;
                if (height > width)
                    height = width;
                $scope.x_axis_scale.range([-0.5, width - 0.5]);
                $scope.y_axis_scale.range([height - 0.5, 0 - 0.5]).nice();
                $scope.x_axis_grid.tickSize(-height);
                $scope.y_axis_grid.tickSize(-width);
                $scope.select('.x.axis')
                    .attr('transform', 'translate(0,' + height + ')')
                    .call($scope.x_axis);
                $scope.select('.x.axis.grid')
                    .attr('transform', 'translate(0,' + height + ')')
                    .call($scope.x_axis_grid); // tickLine == gridline
                $scope.select('.y.axis')
                    .call($scope.y_axis);
                $scope.select('.y.axis.grid')
                    .call($scope.y_axis_grid);
                $scope.select('.main-title')
                    .attr('x', width / 2);
                $scope.select('.y-axis-label')
                    .attr('x', - height / 2);
                $scope.select('.x-axis-label')
                    .attr('x', width / 2)
                // font height + 12 padding...
                    .attr('y', height + 26);
                $scope.select('.plot-viewport')
                    .attr('width', width)
                    .attr('height', height);
                $scope.select('svg .overlay')
                    .attr('width', width)
                    .attr('height', height)
                $scope.select('.line')
                    .attr('d', $scope.graph_line);
                return [width, height];
            }

            $scope.select = function(selector) {
                return d3.select($scope.plot_id + (selector ? (' ' + selector) : ''));
            };

            $scope.slider_changed = function(ev) {
                if (! $scope.points)
                    return;
                function compute_point(value) {
                    return Math.round($scope.x_range[0] + (value / 100) * ($scope.x_range[1] - $scope.x_range[0]));
                }
                var start_x = compute_point(ev.value[0]);
                var end_x = compute_point(ev.value[1]);
                $scope.x_axis_scale.domain([start_x, end_x]);

                var min_y, max_y;
                for (var i = 0; i < $scope.points.length; i++) {
                    var p = $scope.points[i];
                    if (p[0] < start_x)
                        continue;
                    if (p[0] > end_x)
                        break;
                    if (min_y === undefined || min_y > p[1])
                        min_y = p[1];
                    if (max_y === undefined || max_y < p[1])
                        max_y = p[1];
                }
                $scope.y_axis_scale.domain([min_y, max_y]);
                $scope.resize();
            };
        },
        link: function link(scope) {
            d3Service.d3().then(function(d3) {

                function request_data() {
                    if (! appState.is_loaded())
                        return;
                    //console.log('requesting data: ', scope.modelName);
                    appState.request_data(scope.modelName, function(data) {
                        //console.log('loading data: ', scope.modelName);
                        if (scope.svg)
                            scope.load(data);
                    });
                }
                scope.$on(scope.modelName + '.changed', request_data);
                scope.init(scope.id);
                request_data();
            });
            scope.$on('$destroy', function() {
                $(window).off('resize', scope.resize);
                $('.overlay').off();
                scope.svg.remove();
                scope.svg = null;
                scope.slider.off();
                scope.slider.data('slider').picker.off();
                scope.slider.remove();
            });
        },
    };
});

app.directive('plot3d', function(appState, d3Service) {

    var margin = 50;

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            id: '@',
        },
        controller: function($scope) {

            $scope.draw_bottompanel_cut = function() {
                var y_bottom = $scope.y_index_scale($scope.y_axis_scale.domain()[0]);
                var y_top = $scope.y_index_scale($scope.y_axis_scale.domain()[1]);
                var yv = Math.floor(y_bottom + (y_top - y_bottom + 1)/2);
                var row = $scope.heatmap[yv];
                var xv_min = $scope.x_index_scale.domain()[0];
                var xv_max = $scope.x_index_scale.domain()[1];
                var xi_min = Math.ceil($scope.x_index_scale(xv_min));
                var xi_max = Math.floor($scope.x_index_scale(xv_max));
                var xv_range = $scope.x_value_range.slice(xi_min, xi_max + 1);
                var zv_range = row.slice(xi_min, xi_max + 1);
                $scope.bottompanel_context.select($scope.plot_id + ' path')
                    .datum(d3.zip(xv_range, zv_range))
                    .attr('class', 'line')
                    .attr('d', $scope.bottompanel_cut_line);
            }

            $scope.draw_rightpanel_cut = function() {
                var yv_min = $scope.y_index_scale.domain()[0];
                var yv_max = $scope.y_index_scale.domain()[1];
                var yi_min = Math.ceil($scope.y_index_scale(yv_min));
                var yi_max = Math.floor($scope.y_index_scale(yv_max));
                var x_left = $scope.x_index_scale($scope.x_axis_scale.domain()[0]);
                var x_right = $scope.x_index_scale($scope.x_axis_scale.domain()[1]);
                var xv = Math.floor(x_left + (x_right - x_left + 1)/2);
                var data = $scope.heatmap.slice(yi_min, yi_max + 1).map(function (v, i) {
                    return [$scope.y_value_range[i], v[xv]];
                });
                $scope.rightpanel_context.select($scope.plot_id + ' path')
                    .datum(data)
                    .attr('class', 'line')
                    .attr('d', $scope.rightpanel_cut_line);
            }

            $scope.init = function(id) {
                $scope.plot_id = '#' + id;
                $scope.x_axis_scale = d3.scale.linear();
                $scope.x_index_scale = d3.scale.linear();
                $scope.y_axis_scale = d3.scale.linear();
                $scope.y_index_scale = d3.scale.linear();
                $scope.bottompanel_y_scale = d3.scale.linear();
                $scope.rightpanel_x_scale = d3.scale.linear();
                $scope.main_xAxis = d3.svg.axis()
                    .scale($scope.x_axis_scale)
                    .orient('bottom');
                $scope.main_yAxis = d3.svg.axis()
                    .scale($scope.y_axis_scale)
                    .orient('left');
                $scope.bottompanel_xAxis = d3.svg.axis()
                    .scale($scope.x_axis_scale)
                    .orient('bottom');
                $scope.bottompanel_yAxis = d3.svg.axis()
                    .scale($scope.bottompanel_y_scale)
                    // this causes a 'number of fractional digits' error in MSIE
                    //.tickFormat(d3.format('e'))
                    .tickFormat(function (value) {
                        return value.toExponential();
                    })
                    .ticks(5)
                    .orient('left');
                $scope.rightpanel_xAxis = d3.svg.axis()
                    .scale($scope.rightpanel_x_scale)
                    // this causes a 'number of fractional digits' error in MSIE
                    //.tickFormat(d3.format('e'))
                    .tickFormat(function (value) {
                        return value.toExponential();
                    })
                    .ticks(5)
                    .orient('bottom');
                $scope.rightpanel_yAxis = d3.svg.axis()
                    .scale($scope.y_axis_scale)
                    .orient('right');
                $scope.zoom = d3.behavior.zoom()
                    .scaleExtent([1, 10])
                    .on('zoom', $scope.refresh);
                var root_div = $scope.select()
                    .style('position', 'relative');
                $scope.canvas = root_div.append('canvas')
                    .style('position', 'absolute')
                    .attr('transform', 'translate(' + margin + ',' + margin + ')')
                    .style('left', margin + 'px')
                    .style('top', margin + 'px');
                $scope.svg = root_div.append('svg')
                    .style('position', 'relative')
                    .append('g')
                    .attr('transform', 'translate(' + margin + ',' + margin + ')');
                $scope.svg.append('text')
                    .attr('class', 'main-title')
                    .style('text-anchor', 'middle');
                // We make an invisible rectangle to intercept mouse events for zooming.
                $scope.mouse_rect = $scope.svg.append('rect')
                    .attr('class', 'mouse-rect')
                    .style('pointer-events', 'all')
                    .style('fill', 'none');
                $scope.ctx = $scope.canvas.node().getContext('2d');
                $scope.imageObj = new Image();
                $scope.imageObj.onload = function() {
                    // important - the image may not be ready initially
                    $scope.refresh();
                };
                $scope.svg.append('line')
                    .attr('class', 'y-cross-hair cross-hair')
                    .attr('y1', 0)
                    .attr('stroke-width', 1)
                    .attr('shape-rendering', 'crispEdges')
                    .attr('stroke', 'steelblue');
                $scope.svg.append('line')
                    .attr('class', 'x-cross-hair cross-hair')
                    .attr('x1', 0)
                    .attr('stroke-width', 1)
                    .attr('shape-rendering', 'crispEdges')
                    .attr('stroke', 'steelblue');
                $scope.svg.append('g')
                    .attr('class', 'y axis grid');
                $scope.svg.append('defs').append('clipPath')
                    .attr('id', 'bottomclip')
                    .append('rect')
                    .attr('class', 'bottompanel-rect');
                $scope.bottompanel_context = $scope.svg.append('g')
                    .attr('class', 'bottompanel');
                // Clips the line graph
                $scope.bottompanel_context.append('path')
                    .attr('clip-path', 'url(#bottomclip)');
                $scope.bottompanel_context.append('g')
                    .attr('class', 'x axis bottom');
                $scope.bottompanel_context.append('g')
                    .attr('class', 'x axis grid');
                $scope.bottompanel_context.append('text')
                    .attr('class', 'x-axis-label')
                    .style('text-anchor', 'middle');
                $scope.bottompanel_context.append('g')
                    .attr('class', 'y axis bottom');
                $scope.rightpanel_context = $scope.svg.append('g')
                    .attr('class', 'rightpanel');
                $scope.svg.append('defs').append('clipPath')
                    .attr('id', 'rightclip')
                    .append('rect')
                    .attr('class', 'rightpanel-rect');
                $scope.rightpanel_context.append('path')
                    .attr('clip-path', 'url(#rightclip)');
                $scope.rightpanel_context.append('g')
                    .attr('class', 'y axis right');
                $scope.rightpanel_context.append('g')
                    .attr('class', 'x axis right');
                $scope.rightpanel_context.append('text')
                    .attr('class', 'y-axis-label')
                    .style('text-anchor', 'middle')
                    .attr('transform', 'rotate(270)');
                $scope.svg.append('text')
                    .attr('class', 'z-axis-label')
                    .style('text-anchor', 'middle');
                $scope.bottompanel_cut_line = d3.svg.line()
                    .x(function(d) {return $scope.x_axis_scale(d[0])})
                    .y(function(d) {return $scope.bottompanel_y_scale(d[1])});
                $scope.rightpanel_cut_line = d3.svg.line()
                    .y(function(d) { return $scope.y_axis_scale(d[0]); })
                    .x(function(d) { return $scope.rightpanel_x_scale(d[1]); });

                $(window).resize($scope.resize);
            }

            $scope.init_draw = function(json, zmin, zmax) {
                var color = d3.scale.linear()
                    .domain([zmin, zmax])
                    .range(['#333', '#fff']);
                var xmax = json.x_range.length - 1;
                var ymax = json.y_range.length - 1;
                // Compute the pixel colors; scaled by CSS.
                var img = $scope.ctx.createImageData(json.x_range.length, json.y_range.length);
                for (var yi = 0, p = -1; yi <= ymax; ++yi) {
	            for (var xi = 0; xi <= xmax; ++xi) {
	                var c = d3.rgb(color($scope.heatmap[yi][xi]));
	                img.data[++p] = c.r;
	                img.data[++p] = c.g;
	                img.data[++p] = c.b;
	                img.data[++p] = 255;
	            }
                }
                // Keeping pixels as nearest neighbor (as anti-aliased as we can get
                // without doing more programming) allows us to see how the marginals
                // line up when zooming in a lot.
                $scope.ctx.mozImageSmoothingEnabled = false;
                $scope.ctx.webkitImageSmoothingEnabled = false;
                $scope.ctx.msImageSmoothingEnabled = false;
                $scope.ctx.imageSmoothingEnabled = false;
                $scope.ctx.putImageData(img, 0, 0);
                $scope.imageObj.src = $scope.canvas.node().toDataURL();
            }

            $scope.load = function(json) {
                $scope.heatmap = [];
                var xmax = json.x_range.length - 1;
                var ymax = json.y_range.length - 1;
                $scope.x_value_min = json.x_range[0];
                $scope.x_value_max = json.x_range[xmax];
                $scope.x_value_range = json.x_range.slice(0);
                $scope.y_value_min = json.y_range[0];
                $scope.y_value_max = json.y_range[ymax];
                $scope.y_value_range = json.y_range.slice(0);
                $scope.x_index_scale.range([0, xmax]);
                $scope.y_index_scale.range([0, ymax]);
                $scope.canvas.attr('width', json.x_range.length)
                    .attr('height', json.y_range.length);
                $scope.select('.main-title').text(json.title);
                $scope.select('.x-axis-label').text(json.x_label);
                $scope.select('.y-axis-label').text(json.y_label);
                $scope.select('.z-axis-label').text(json.z_label);
                $scope.x_axis_scale.domain([$scope.x_value_min, $scope.x_value_max]);
                $scope.x_index_scale.domain([$scope.x_value_min, $scope.x_value_max]);
                $scope.y_axis_scale.domain([$scope.y_value_min, $scope.y_value_max]);
                $scope.y_index_scale.domain([$scope.y_value_min, $scope.y_value_max]);

                var zmin = json.z_matrix[0][0]
                var zmax = json.z_matrix[0][0]
                for (var yi = 0; yi <= ymax; ++yi) {
                    // flip to match the canvas coordinate system (origin: top left)
                    // matplotlib is bottom left
                    $scope.heatmap[ymax - yi] = [];
                    for (var xi = 0; xi <= xmax; ++xi) {
	                var zi = json.z_matrix[yi][xi];
	                $scope.heatmap[ymax - yi][xi] = zi;
	                if (zmax < zi)
	                    zmax = zi;
	                else if (zmin > zi)
	                    zmin = zi;
                    }
                }
                $scope.bottompanel_y_scale.domain([zmin, zmax]);
                $scope.rightpanel_x_scale.domain([zmax, zmin]);
                $scope.init_draw(json, zmin, zmax);
                $scope.resize();
            }

            $scope.refresh = function() {
                var tx = 0, ty = 0, s = 1;
                if (d3.event && d3.event.translate) {
                    var t = d3.event.translate;
                    s = d3.event.scale;
                    tx = t[0];
                    ty = t[1];
                    tx = Math.min(
                        0,
                        Math.max(
                            tx,
                            $scope.canvas_size - (s * $scope.imageObj.width) / ($scope.imageObj.width / $scope.canvas_size)));
                    ty = Math.min(
                        0,
                        Math.max(
                            ty,
                            $scope.canvas_size - (s * $scope.imageObj.height) / ($scope.imageObj.height / $scope.canvas_size)));

                    var xdom = $scope.x_axis_scale.domain();
                    var ydom = $scope.y_axis_scale.domain();
                    var reset_s = 0;
                    if ((xdom[1] - xdom[0]) >= ($scope.x_value_max - $scope.x_value_min) * 0.9999) {
	                $scope.zoom.x($scope.x_axis_scale.domain([$scope.x_value_min, $scope.x_value_max]));
	                xdom = $scope.x_axis_scale.domain();

	                reset_s += 1;
                    }
                    if ((ydom[1] - ydom[0]) >= ($scope.y_value_max - $scope.y_value_min) * 0.9999) {
	                $scope.zoom.y($scope.y_axis_scale.domain([$scope.y_value_min, $scope.y_value_max]));
	                ydom = $scope.y_axis_scale.domain();
	                reset_s += 1;
                    }
                    if (reset_s == 2) {
	                $scope.mouse_rect.attr('class', 'mouse-zoom');
	                // Both axes are full resolution. Reset.
	                tx = 0;
	                ty = 0;
                    }
                    else {
	                $scope.mouse_rect.attr('class', 'mouse-move');
	                if (xdom[0] < $scope.x_value_min) {
                            //		tx = 0;
	                    $scope.x_axis_scale.domain([$scope.x_value_min, xdom[1] - xdom[0] + $scope.x_value_min]);
	                    xdom = $scope.x_axis_scale.domain();
	                }
	                if (xdom[1] > $scope.x_value_max) {
	                    xdom[0] -= xdom[1] - $scope.x_value_max;
	                    $scope.x_axis_scale.domain([xdom[0], $scope.x_value_max]);
	                }
	                if (ydom[0] < $scope.y_value_min) {
	                    $scope.y_axis_scale.domain([$scope.y_value_min, ydom[1] - ydom[0] + $scope.y_value_min]);
	                    ydom = $scope.y_axis_scale.domain();
	                }
	                if (ydom[1] > $scope.y_value_max) {
	                    ydom[0] -= ydom[1] - $scope.y_value_max;
	                    $scope.y_axis_scale.domain([ydom[0], $scope.y_value_max]);
	                }
                    }
                }

                $scope.ctx.clearRect(0, 0, $scope.canvas_size, $scope.canvas_size);
                if (s == 1) {
                    tx = 0;
                    ty = 0;
                    $scope.zoom.translate([tx, ty]);
                }
                $scope.ctx.drawImage(
                    $scope.imageObj,
                    tx*$scope.imageObj.width/$scope.canvas_size,
                    ty*$scope.imageObj.height/$scope.canvas_size,
                    $scope.imageObj.width*s,
                    $scope.imageObj.height*s
                );
                $scope.draw_bottompanel_cut();
                $scope.draw_rightpanel_cut();
                $scope.bottompanel_context.selectAll($scope.plot_id + ' .x.axis').call($scope.bottompanel_xAxis);
                $scope.bottompanel_context.selectAll($scope.plot_id + ' .y.axis').call($scope.bottompanel_yAxis);
                $scope.rightpanel_context.selectAll($scope.plot_id + ' .x.axis').call($scope.rightpanel_xAxis);
                $scope.rightpanel_context.selectAll($scope.plot_id + ' .y.axis').call($scope.rightpanel_yAxis);
                $scope.svg.selectAll($scope.plot_id + ' .x.axis.grid').call($scope.main_xAxis);
                $scope.svg.selectAll($scope.plot_id + ' .y.axis.grid').call($scope.main_yAxis);
            }

            $scope.resize = function() {
                var width = parseInt($scope.select().style('width')) - 2 * margin;
                var rightpanel_margin = {left: 10, right: 40};
                var bottompanel_margin = {top: 10, bottom: 30};
                $scope.canvas_size = 2 * (width - rightpanel_margin.left - rightpanel_margin.right) / 3;
                var bottompanel_height = 2 * $scope.canvas_size / 5 + bottompanel_margin.top + bottompanel_margin.bottom;
                var rightpanel_width = $scope.canvas_size / 2 + rightpanel_margin.left + rightpanel_margin.right;
                $scope.x_axis_scale.range([0, $scope.canvas_size - 1]);
                $scope.y_axis_scale.range([$scope.canvas_size - 1, 0]);
                $scope.bottompanel_y_scale.range([bottompanel_height - bottompanel_margin.top - bottompanel_margin.bottom - 1, 0]).nice();
                $scope.rightpanel_x_scale.range([0, rightpanel_width - rightpanel_margin.left - rightpanel_margin.right]).nice();
                $scope.main_xAxis.tickSize(- $scope.canvas_size - bottompanel_height + bottompanel_margin.bottom); // tickLine == gridline
                $scope.main_yAxis.tickSize(- $scope.canvas_size - rightpanel_width + rightpanel_margin.right); // tickLine == gridline
                $scope.zoom.center([$scope.canvas_size / 2, $scope.canvas_size / 2])
                    .x($scope.x_axis_scale.domain([$scope.x_value_min, $scope.x_value_max]))
                    .y($scope.y_axis_scale.domain([$scope.y_value_min, $scope.y_value_max]));
                $scope.select('canvas')
                    .style('width', $scope.canvas_size + 'px')
                    .style('height', $scope.canvas_size + 'px');
                $scope.select('svg')
                    .attr('width', margin * 2 + $scope.canvas_size + rightpanel_width)
                    .attr('height', margin * 2 + $scope.canvas_size + bottompanel_height)
                $scope.select('.main-title')
                    .attr('x', $scope.canvas_size / 2)
                    .attr('y', - margin / 2);
                $scope.select('.mouse-rect')
                    .attr('width', $scope.canvas_size)
                    .attr('height', $scope.canvas_size)
                    .call($scope.zoom);
                $scope.select('.y-cross-hair')
                    .attr('x1', Math.floor($scope.canvas_size/2) - 0)
                    .attr('x2', Math.floor($scope.canvas_size/2) - 0)
                    .attr('y2', $scope.canvas_size);
                $scope.select('.x-cross-hair')
                    .attr('y1', Math.floor($scope.canvas_size/2) + 0)
                    .attr('x2', $scope.canvas_size)
                    .attr('y2', Math.floor($scope.canvas_size/2) + 0);
                $scope.select('.bottompanel-rect')
                    .attr('width', $scope.canvas_size)
                    .attr('height', bottompanel_height - bottompanel_margin.top - bottompanel_margin.bottom);
                $scope.select('.bottompanel')
                    .attr('transform', 'translate(0,' + ($scope.canvas_size + bottompanel_margin.top) + ')');
                $scope.select('.x-axis-label')
                    .attr('x', $scope.canvas_size / 2)
                    .attr('y', bottompanel_height);
                $scope.select('.rightpanel-rect')
                    .attr('width', rightpanel_width - rightpanel_margin.left - rightpanel_margin.right)
                    .attr('height', $scope.canvas_size);
                $scope.select('.rightpanel')
                    .attr('transform', 'translate(' + ($scope.canvas_size + rightpanel_margin.left) + ',0)');
                $scope.select('.x.axis.bottom')
                    .attr('transform', 'translate(0,' + (bottompanel_height - bottompanel_margin.top - bottompanel_margin.bottom) + ')')
                    .call($scope.bottompanel_xAxis);
                $scope.select('.x.axis.right')
                    .attr('transform', 'translate(0,' + $scope.canvas_size + ')')
                    .call($scope.rightpanel_xAxis);
                $scope.select('.y-axis-label')
                    .attr('x', - $scope.canvas_size / 2)
                    .attr('y', rightpanel_width + 15);
                $scope.select('.z-axis-label')
                    .attr('x', $scope.canvas_size + rightpanel_width / 2)
                    .attr('y', $scope.canvas_size + margin);
                var ticks = function(axis, axisRange, isShorterAxis) {
                    var spacing = isShorterAxis ? 150 : 80;
                    var n = Math.max(Math.round($scope.canvas_size/spacing), 3);
                    axis.ticks(n);
                };
                ticks($scope.rightpanel_xAxis, true);
                ticks($scope.rightpanel_yAxis, false);
                ticks($scope.bottompanel_xAxis, false);
                ticks($scope.bottompanel_yAxis, true);
                ticks($scope.main_xAxis, false);
                ticks($scope.main_yAxis, false);
                $scope.select('.x.axis.grid')
                    .attr('transform', 'translate(0,' + (bottompanel_height - bottompanel_margin.top - bottompanel_margin.bottom) + ')')
                    .call($scope.zoom)
                    .call($scope.main_xAxis);
                $scope.select('.y.axis.grid')
                    .call($scope.zoom)
                    .call($scope.main_yAxis);
                $scope.select('.y.axis.right')
                    .attr('transform', 'translate(' + (rightpanel_width - rightpanel_margin.left - rightpanel_margin.right) + ',0)')
                    .call($scope.rightpanel_yAxis);
                $scope.select('.y.axis.bottom')
                    .call($scope.bottompanel_yAxis);
                $scope.refresh();
            }

            $scope.select = function(selector) {
                return d3.select($scope.plot_id + (selector ? (' ' + selector) : ''));
            };
        },
        link: function link(scope) {
            d3Service.d3().then(function(d3) {
                //TODO(pjm): consolidate this code with plot2d
                function request_data() {
                    if (! appState.is_loaded())
                        return;
                    //console.log('requesting data: ', scope.modelName);
                    appState.request_data(scope.modelName, function(data) {
                        //console.log('loading data: ', scope.modelName);
                        if (scope.svg)
                            scope.load(data);
                    });
                }
                scope.$on(scope.modelName + '.changed', request_data);
                scope.init(scope.id);
                request_data();
            });
            scope.$on('$destroy', function() {
                $(window).off('resize', scope.resize);
                scope.zoom.on('zoom', null);
                scope.svg.remove();
                scope.svg = null;
                scope.imageObj.onload = null;
            });
        },
    };
});

app.controller('NavController', function ($rootScope, $location, appState) {
    var self = this;
    self.page_title = function() {
        return $.grep(
            [
                self.section_title(),
                'SRW',
                'Radiasoft',
            ],
            function(n){ return n })
            .join(' - ');
    }
    self.section_title = function() {
        if ($rootScope.activeSection == 'simulations')
            return null;
        if (appState.is_loaded())
            return appState.models.simulation.name;
        return null;
    }
    self.open_section = function(name) {
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
    appState.clear_models({
        newSimulation: {},
    });
    var self = this;

    function new_simulation(name) {
        $http.post('/srw/new-simulation', {
            name: name,
        }).success(function(data, status) {
            self.open(data['models']['simulation']);
        }).error(function(data, status) {
            console.log('new-simulation failed: ', status, ' ', data);
        });
    }

    function load_list() {
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
    self.is_selected = function(item) {
        return self.selected && self.selected == item;
    }
    self.select_item = function(item) {
        self.selected = item;
    }
    self.delete_selected = function() {
        $http.post('/srw/delete-simulation', {
            simulationId: self.selected['simulationId'],
        }).success(function(data, status) {
            load_list();
        }).error(function(data, status) {
            console.log('delete-simulation failed: ', status, ' ', data);
        });
        self.selected = null;
    }
    $rootScope.$on('newSimulation.changed', function() {
        if (appState.models.newSimulation.name) {
            new_simulation(appState.models.newSimulation.name);
            appState.models.newSimulation.name = '';
            appState.save_changes('newSimulation');
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
    self.python_source = function(item) {
        $window.open('/srw/python-source/' + self.selected['simulationId'], '_blank');
    }
    load_list()
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

app.directive('beamlineItem', function($compile, $timeout) {
    return {
        scope: {
            item: '=',
        },
        template: [
            '<span class="srw-beamline-badge badge">{{ item.position }}m</span>',
            '<span data-ng-click="remove_element(item)" class="srw-beamline-close-icon glyphicon glyphicon-remove-circle"></span>',
            '<div class="srw-beamline-image">',
              '<span data-beamline-icon="", data-item="item"></span>',
            '</div>',
            '<div data-ng-attr-id="srw-item-{{ item.id }}" class="srw-beamline-element-label">{{ item.title }}<span class="caret"></span></div>',
        ].join(''),
        controller: function($scope) {
            $scope.remove_element = function(item) {
                $scope.$parent.beamline.remove_element(item);
            };
        },
        link: function(scope, element) {
            scope.$watchCollection('item', function(newValue, oldValue) {
                if (newValue != oldValue)
                    scope.$parent.beamline.is_dirty = true;
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

            function toggle_popover() {
                $('.srw-beamline-element-label').not(el).popover('hide');
                el.popover('toggle');
                scope.$apply();
            }
            if (scope.$parent.beamline.is_touchscreen()) {
                var has_touch_move = false;
                $(element).bind('touchstart', function() {
                    has_touch_move = false;
                });
                $(element).bind('touchend', function() {
                    if (! has_touch_move)
                        toggle_popover();
                    has_touch_move = false;
                });
                $(element).bind('touchmove', function() {
                    has_touch_move = true;
                });
            }
            else {
                $(element).click(function() {
                    toggle_popover();
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
                if (scope.$parent.beamline.is_touchscreen()) {
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
            $scope.basicFields = appState.model_info($scope.modelName).basic;
            $scope.panelTitle = appState.model_info($scope.modelName).title;
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
              '<div class="panel-heading" data-panel-heading="{{ appState.get_report_title(fullModelName) }}" data-model="appState.models[fullModelName]" data-editor-id="{{ editorId }}" data-allow-full-screen="1"></div>',
              '<panel-body data-model="appState.models[fullModelName]">',

                '<div data-ng-switch="reportPanel">',
                  '<div data-ng-switch-when="2d" data-plot2d="" class="srw-plot-2d" data-model-name="{{ fullModelName }}" id="{{ plotId }}"></div>',
                  '<div data-ng-switch-when="3d" data-plot3d="" class="srw-plot-3d" data-model-name="{{ fullModelName }}" id="{{ plotId }}"></div>',
                '</div>',
              '</panel-body>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var item_id = $scope.item ? $scope.item.id : '';
            $scope.appState = appState;
            $scope.fullModelName = $scope.modelName + item_id;
            $scope.editorId = 'srw-' + $scope.fullModelName + '-editor';
            $scope.plotId = 'srw-' + $scope.modelName + '-' + $scope.reportPanel + '-plot' + item_id;
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
	            '<span class="lead modal-title text-info">{{ appState.get_report_title(fullModelName) }}</span>',
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
            $scope.advancedFields = appState.model_info($scope.modalEditor).advanced;
            $scope.fullModelName = $scope.modalEditor + ($scope.itemId || '');
            $scope.editorId = 'srw-' + $scope.fullModelName + '-editor';
        },
        link: function(scope, element) {
            $(element).on('hidden.bs.modal', function(e) {
                // ensure that a dismissed modal doesn't keep changes
                // ok processing will have already saved data before the modal is hidden
                appState.cancel_changes(scope.fullModelName);
                scope.$digest();
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
                    '<button ng-click="beamline.dismiss_popup()" style="width: 100%" type="submit" class="btn btn-primary">Close</button>',
                  '</div>',
                '</div>',
                '<div class="form-group" data-ng-show="beamline.is_touchscreen()">',
                  '<div class="col-sm-offset-6 col-sm-3">',
                    '<button ng-click="remove_active_item()" style="width: 100%" type="submit" class="btn btn-danger">Delete</button>',
                  '</div>',
                '</div>',
              '</form>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.beamline = $scope.$parent.beamline;
            $scope.advancedFields = appState.model_info($scope.modelName).advanced;
            $scope.remove_active_item = function() {
                $scope.beamline.remove_element($scope.beamline.activeItem);
            }
            //TODO(pjm): investigate why id needs to be set in html for revisiting the beamline page
            //$scope.editorId = 'srw-' + $scope.modelName + '-editor';
        },
    };
});
