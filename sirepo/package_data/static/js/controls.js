'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;


SIREPO.app.config(function() {
    // TODO(pjm): copied from webcon
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="MiniFloat" class="col-sm-7">',
          '<input data-string-to-number="" data-ng-model="model[field]" data-min="info[4]" data-max="info[5]" class="form-control" style="text-align: right" data-lpignore="true" required />',
        '</div>',
    ].join('');
    // TODO(e-carlin): copied from madx
    SIREPO.lattice = {
        elementColor: {
            OCTUPOLE: 'yellow',
            QUADRUPOLE: 'red',
            SEXTUPOLE: 'lightgreen',
            VKICKER: 'blue',
        },
        elementPic: {
            aperture: ['COLLIMATOR', 'ECOLLIMATOR', 'RCOLLIMATOR'],
            bend: ['RBEND', 'SBEND'],
            drift: ['DRIFT'],
            lens: ['NLLENS'],
            magnet: ['HACDIPOLE', 'HKICKER', 'KICKER', 'MATRIX', 'MULTIPOLE', 'OCTUPOLE', 'QUADRUPOLE', 'RFMULTIPOLE', 'SEXTUPOLE', 'VACDIPOLE', 'VKICKER'],
            rf: ['CRABCAVITY', 'RFCAVITY', 'TWCAVITY'],
            solenoid: ['SOLENOID'],
            watch: ['INSTRUMENT', 'HMONITOR', 'MARKER', 'MONITOR', 'PLACEHOLDER', 'VMONITOR'],
            zeroLength: ['BEAMBEAM', 'CHANGEREF', 'DIPEDGE', 'SROTATION', 'TRANSLATION', 'XROTATION', 'YROTATION'],
        },
    };
});

SIREPO.app.factory('controlsService', function(appState) {
    var self = {};

    self.computeModel = function(analysisModel) {
        return 'animation';
    };
    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('ControlsController', function(appState, controlsService, frameCache, latticeService, persistentSimulation, $scope) {
    var self = this;
    self.simScope = $scope;
    self.latticeService = latticeService;

    self.advancedNames = [];
    self.basicNames = [];

    self.simHandleStatus = function(data) {
        if (data.frameCount) {
            frameCache.setFrameCount(1);
            // TODO(e-carlin): load reports
        }
    };

    function elementForId(id) {
        var model = null;
        appState.models.externalLattice.elements.some(function(m) {
            if (m._id == id) {
                model = m;
                return true;
            }
        });
        if (! model) {
            throw new Error('model not found for id: ' + id);
        }
        return model;
    }

    function getBeamlineElements(id, elements) {
        var found = appState.models.externalLattice.models.elements.some(function(el) {
            if (el._id == id) {
                elements.push(el);
                return true;
            }
        });
        if (! found) {
            appState.models.externalLattice.models.beamlines.some(function(bl) {
                if (bl.id == id) {
                    bl.items.forEach(function(id2) {
                        getBeamlineElements(id2, elements);
                    });
                    return true;
                }
            });
        }
        return elements;
    }

    function modelForElement(element) {
        return {
            modelKey: element.type,
            title: element.name.replace(/\_/g, ' '),
            viewName: element.type,
            getData: function() {
                return element;
            },
        };
    }

    appState.whenModelsLoaded($scope, function() {
        self.editorColumns = [];
        var schema = SIREPO.APP_SCHEMA.model;
        var beamlineId = appState.models.externalLattice.models.simulation.visualizationBeamlineId;
        getBeamlineElements(beamlineId, []).forEach(function(element) {
            if (schema[element.type]) {
                self.editorColumns.push([modelForElement(element)]);
            }
        });
    });

    $scope.$on('modelChanged', function(e, name) {
        //TODO(pjm): not a good element model detector
        if (name == name.toUpperCase()) {
            appState.saveQuietly('externalLattice');
        }
    });

    self.simState = persistentSimulation.initSimulationState(self);
    return self;
});

SIREPO.app.directive('appFooter', function(controlsService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-common-footer="nav"></div>',
            '<div data-import-dialog=""></div>',
        ].join(''),
    };
});

SIREPO.app.directive('appHeader', function(appState, panelState) {
    return {
	restrict: 'A',
	scope: {
            nav: '=appHeader',
	},
        template: [
            '<div data-app-header-brand="nav"></div>',
            '<div data-app-header-left="nav"></div>',
            '<div data-app-header-right="nav">',
              '<app-header-right-sim-loaded>',
		'<div data-sim-sections="">',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'controls\')}"><a href data-ng-click="nav.openSection(\'controls\')"><span class="glyphicon glyphicon-dashboard"></span> Controls</a></li>',
		'</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
		//  '<div>App-specific setting item</div>',
              '</app-settings>',
              '<app-header-right-sim-list>',
              '</app-header-right-sim-list>',
            '</div>',
	].join(''),
    };
});
