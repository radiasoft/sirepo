'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.SINGLE_FRAME_ANIMATION = ['wavefrontSummaryAnimation'];
});

SIREPO.app.factory('silasService', function(appState) {
    var self = {};
    self.computeModel = function(analysisModel) {
        return 'animation';
    };
    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('BeamlineController', function (appState, beamlineService, frameCache, persistentSimulation, $scope) {
    var self = this;
    self.simScope = $scope;
    self.appState = appState;
    self.beamlineModels = ['beamline'];
    self.prepareToSave = function() {};
    self.toolbarItemNames = ['crystal', 'mirror'];

    function wavefrontAnimationName(item) {
        return 'wavefrontAnimation' + item.id;
    }

    function updateCavityDistance() {
        var pos = 0;
        appState.models.beamline.forEach(function(item) {
            item.position = pos;
            pos += appState.models.simulationSettings.cavity_length / 2;
        });
        appState.saveChanges('beamline');
    }

    function updateWavefrontModels() {
        var names = [];
        self.wavefronts = [];
        appState.models.beamline.forEach(function(item) {
            names.push(wavefront(item));
        });
        appState.saveChanges(names);
    }

    function wavefront(item) {
        var modelKey = wavefrontAnimationName(item);
        if (! appState.models[modelKey]) {
            appState.models[modelKey] = {};
        }
        appState.models[modelKey].id = item.id;
        self.wavefronts.push({
            title: item.title,
            modelKey: modelKey,
            getData: function() {
                return appState.models[modelKey];
            },
        });
        return modelKey;
    }

    self.hasFrames = frameCache.hasFrames;

    self.simHandleStatus = function (data) {
        if (! appState.isLoaded()) {
            return;
        }
        if ((data.frameCount || 0) > 1) {
            appState.models.beamline.forEach(function(item, idx) {
                frameCache.setFrameCount(
                    data.wavefrontsFrameCount[idx],
                    wavefrontAnimationName(item));
            });
            frameCache.setFrameCount(data.frameCount);
        }
    };

    self.simState = persistentSimulation.initSimulationState(self);
    beamlineService.setEditable(false);
    appState.whenModelsLoaded($scope, updateWavefrontModels);
    $scope.$on('modelChanged', function(e, name) {
        if (! appState.isReportModelName(name)) {
            updateWavefrontModels();
        }
        if (name == 'simulationSettings') {
            updateCavityDistance();
        }
    });
});

SIREPO.app.directive('appFooter', function(appState, silasService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-common-footer="nav"></div>',
        ].join(''),
    };
});

SIREPO.app.directive('appHeader', function(appState) {
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'beamline\')}"><a href data-ng-click="nav.openSection(\'beamline\')"><span class="glyphicon glyphicon-option-horizontal"></span> Beamline</a></li>',
                '</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
              '</app-settings>',
              '<app-header-right-sim-list>',
                '<ul class="nav navbar-nav sr-navbar-right">',
                  '<li><a href data-ng-click="nav.showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>',
                '</ul>',
              '</app-header-right-sim-list>',
            '</div>',
        ].join(''),
    };
});

SIREPO.beamlineItemLogic('crystalView', function(appState, panelState, $scope) {
    $scope.whenSelected = function() {
        panelState.enableField('crystal', 'position', false);
    };
});

SIREPO.beamlineItemLogic('mirrorView', function(appState, panelState, $scope) {
    $scope.whenSelected = function() {
        panelState.enableField('mirror', 'position', false);
    };
});
