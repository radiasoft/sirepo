'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.SINGLE_FRAME_ANIMATION = [
        'wavefrontSummaryAnimation',
        'laserPulse1Animation',
        'laserPulse2Animation',
        'laserPulse3Animation',
        'laserPulse4Animation',
        'plotAnimation',
        'plot2Animation',
    ];
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="SelectElement" data-ng-class="fieldClass">',
          '<div data-select-element="" data-model="model" data-field="field"></div>',
        '</div>',
    ].join('');
    SIREPO.appDownloadLinks = [
        '<li data-export-python-link="" data-report-title="{{ reportTitle() }}"></li>',
    ].join('');
});

SIREPO.app.factory('silasService', function(appState) {
    var self = {};
    self.computeModel = (analysisModel) => {
        if (['crystalAnimation', 'plotAnimation', 'plot2Animation'].indexOf(analysisModel) >= 0) {
            return 'crystalAnimation';
        }
        return 'animation';
    };
    self.getCrystal = () => {
        return appState.models.beamline[1];
    };
    self.getFirstMirror = () => {
        return appState.models.beamline[0];
    };
    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('BeamlineController', function (appState, beamlineService, frameCache, persistentSimulation, silasService, $scope) {
    var self = this;
    self.simScope = $scope;
    self.appState = appState;
    self.beamlineModels = ['beamline'];
    self.prepareToSave = () => {};
    self.toolbarItemNames = ['crystal', 'mirror'];

    function updateCavityDistance() {
        var pos = 0;
        appState.models.beamline.forEach((item) => {
            item.position = pos;
            pos += appState.models.simulationSettings.cavity_length / 2;
        });
        appState.saveChanges('beamline');
    }

    function updateWavefrontModels() {
        var names = [];
        self.wavefronts = [];
        appState.models.beamline.forEach((item) => names.push(wavefront(item)));
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
            getData: () => appState.models[modelKey],
        });
        return modelKey;
    }

    function wavefrontAnimationName(item) {
        return 'wavefrontAnimation' + item.id;
    }

    self.hasFrames = frameCache.hasFrames;

    self.hasLaserProfile = function(isInitial) {
        if (! self.hasFrames()) {
            return false;
        }
        if (isInitial) {
            return true;
        }
        return self.simState.getPercentComplete() == 100;
    };

    self.simHandleStatus = (data) => {
        if (! appState.isLoaded()) {
            return;
        }
        if ((data.frameCount || 0) > 1) {
            appState.models.beamline.forEach((item, idx) => {
                frameCache.setFrameCount(
                    data.wavefrontsFrameCount[idx],
                    wavefrontAnimationName(item));
            });
            frameCache.setFrameCount(data.frameCount);
        }
    };

    self.simState = persistentSimulation.initSimulationState(self);
    beamlineService.setEditable(false);
    appState.whenModelsLoaded($scope, () => {
        var oldWidth = silasService.getCrystal().width;
        updateWavefrontModels();
        $scope.$on('modelChanged', (e, name) => {
            if (! appState.isReportModelName(name)) {
                updateWavefrontModels();
            }
            if (name == 'simulationSettings') {
                updateCavityDistance();
            }
            else if (name == 'beamline') {
                var width = silasService.getCrystal().width;
                if (oldWidth != width) {
                    oldWidth = width;
                    appState.models.crystalCylinder.crystalWidth = width;
                    appState.saveQuietly('crystalCylinder');
                    frameCache.setFrameCount(0);
                }
            }
        });
        $scope.$on('wavefrontSummaryAnimation.summaryData', function (e, data) {
            if (data.crystalWidth && data.crystalWidth != silasService.getCrystal().width) {
                frameCache.setFrameCount(0);
            }
        });
    });
});

SIREPO.app.controller('CrystalController', function (appState, frameCache, persistentSimulation, silasService, $scope) {
    var self = this;
    self.appState = appState;
    self.simScope = $scope;
    self.simAnalysisModel = 'crystalAnimation';

    self.simHandleStatus = (data) => {
        if (! appState.isLoaded()) {
            return;
        }
        frameCache.setFrameCount(data.frameCount);
    };

    self.simState = persistentSimulation.initSimulationState(self);

    appState.whenModelsLoaded($scope, () => {
        $scope.$on('plotAnimation.summaryData', function (e, data) {
            if (data.crystalWidth && data.crystalWidth != silasService.getCrystal().width) {
                frameCache.setFrameCount(0);
            }
        });
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
            '<div data-import-dialog=""></div>',
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'laser-cavity\')}"><a href data-ng-click="nav.openSection(\'laser-cavity\')"><span class="glyphicon glyphicon-option-horizontal"></span> Laser Cavity</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'crystal\')}"><a href data-ng-click="nav.openSection(\'crystal\')"><span class="glyphicon glyphicon-th"></span> Crystal</a></li>',
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

SIREPO.app.directive('selectElement', function(appState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: [
            '<select class="form-control" data-ng-model="model[field]" data-ng-options="item.id as item.name for item in elementList()"></select>',
        ].join(''),
        controller: function($scope) {
            var list;

            $scope.elementList = () => {
                if (! appState.isLoaded() || ! $scope.model) {
                    return null;
                }
                if (! list) {
                    list = [{
                        id: 'all',
                        name: 'All Elements',
                    }];
                    appState.models.beamline.forEach((item) => {
                        list.push({
                            id: item.id,
                            name: item.title,
                        });
                    });
                }
                return list;
            };

            $scope.$on('beamline.changed', () => {
                list = null;
            });
        },
    };
});

SIREPO.beamlineItemLogic('crystalView', function(appState, panelState, $scope) {
    $scope.whenSelected = () => panelState.enableField('crystal', 'position', false);
});

SIREPO.beamlineItemLogic('mirrorView', function(appState, panelState, $scope) {
    $scope.whenSelected = () => panelState.enableField('mirror', 'position', false);
});

SIREPO.viewLogic('simulationSettingsView', function(appState, panelState, requestSender, silasService, $scope) {

    function computeRMSSize(field, saveChanges) {
        var beamline = appState.applicationState().beamline;
        requestSender.getApplicationData({
            method: 'compute_rms_size',
            gaussianBeam: appState.models.gaussianBeam,
            simulationSettings: appState.models.simulationSettings,
            mirror: silasService.getFirstMirror(),
            crystal: silasService.getCrystal(),
        }, (data) => {
            if (data.rmsSize) {
                appState.models.gaussianBeam.rmsSize = appState.formatFloat(data.rmsSize * 1e6, 4);
                if (saveChanges) {
                    appState.saveQuietly('gaussianBeam');
                }
            }
        });
    }

    $scope.whenSelected = () => panelState.enableField('gaussianBeam', 'rmsSize', false);
    $scope.watchFields = [
        [
            'simulationSettings.cavity_length',
            'gaussianBeam.photonEnergy',
        ], computeRMSSize,
    ];

    $scope.$on('modelChanged', (e, name) => {
        if (name == 'beamline') {
            computeRMSSize(name, true);
        }
    });
});

SIREPO.viewLogic('crystalCylinderView', function(appState, panelState, silasService, $scope) {
    $scope.whenSelected = () => {
        appState.models.crystalCylinder.crystalWidth = silasService.getCrystal().width;
        panelState.enableFields('crystalCylinder', [
            'crystalWidth', false,
        ]);
    };
});
