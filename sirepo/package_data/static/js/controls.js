'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;


SIREPO.app.config(function() {
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
        if (data.frameCount && data.outputInfo) {
            frameCache.setFrameCount(1);
            // TODO(e-carlin): load reports
        }
    };

    function elementForId(id) {
        var model = null;
        appState.models.elements.some(function(m) {
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

    function modelForElement(element) {
        var modelKey = element.type + element._id;
        if (! appState.models[modelKey]) {
            appState.models[modelKey] = element;
            appState.saveQuietly(modelKey);
        }
        return {
            id: element._id,
            modelKey: modelKey,
            title: element.name.replace(/\_/g, ' '),
            viewName: element.type,
            element: element,
            getData: function() {
                return appState.models[modelKey];
            },
        };
    }

    function indexOfBeamline(id) {
        let index = null;
        appState.models.beamlines.some((b, i) => {
            if (b.id === id) {
                index = i;
                return true;
            }
        });
        if (! index) {
            throw new Error(`beamline not found with id=${id}`);
        }
        return index;
    }

    appState.whenModelsLoaded($scope, function() {
        self.editorColumns = [];
        var quadCount = 0;
        latticeService.getActiveBeamline().items.forEach((id) => {
            appState.models.beamlines[indexOfBeamline(id)].items.forEach((id) => {
                const e = elementForId(id);
                if ( ! ['KICKER', 'QUADRUPOLE', 'HKICKER', 'VKICKER'].includes(e.type)) {
                    return;
                }
                self.editorColumns.push([modelForElement(e)]);
            });
        });
    });

    self.simState = persistentSimulation.initSimulationState(self);
    return self;
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
