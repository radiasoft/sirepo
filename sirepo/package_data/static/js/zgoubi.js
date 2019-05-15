'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.USER_MANUAL_URL = 'https://zgoubi.sourceforge.io/ZGOUBI_DOCS/Zgoubi.pdf';
SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="LatticeBeamlineList" data-ng-class="fieldClass">',
      '<div data-lattice-beamline-list="" data-model="model" data-field="field"></div>',
    '</div>',
].join('');
SIREPO.appReportTypes = [
    '<div data-ng-switch-when="twissSummary" data-twiss-summary-panel="" class="sr-plot"></div>',
].join('');
SIREPO.appImportText = 'Import an zgoubi.dat file';

SIREPO.lattice = {
    elementColor: {
        CHANGREF: 'orange',
        QUADRUPO: 'tomato',
        SEXTUPOL: 'lightgreen',
    },
    elementPic: {
        aperture: [],
        bend: ['AUTOREF', 'BEND', 'CHANGREF', 'MULTIPOL'],
        drift: ['DRIFT'],
        magnet: ['QUADRUPO', 'SEXTUPOL'],
        rf: ['CAVITE'],
        solenoid: [],
        watch: ['MARKER'],
        zeroLength: ['SCALING', 'YMY'],
    },
};

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-common-footer="nav"></div>',
            '<div data-import-dialog="" data-title="Import Zgoubi File" data-description="Select an zgoubi.dat file." data-file-formats=".dat"></div>',
        ].join(''),
    };
});

SIREPO.app.directive('appHeader', function(latticeService) {
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'lattice\')}"><a href data-ng-click="nav.openSection(\'lattice\')"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>',
                  '<li class="sim-section" data-ng-if="latticeService.hasBeamlines()" data-ng-class="{active: nav.isActive(\'source\')}"><a data-ng-href="{{ nav.sectionURL(\'source\') }}"><span class="glyphicon glyphicon-flash"></span> Bunch</a></li>',
                  '<li class="sim-section" data-ng-if="latticeService.hasBeamlines()" data-ng-class="{active: nav.isActive(\'twiss\')}"><a data-ng-href="{{ nav.sectionURL(\'twiss\') }}"><span class="glyphicon glyphicon-option-horizontal"></span> Twiss</a></li>',
                  '<li class="sim-section" data-ng-if="latticeService.hasBeamlines()" data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
                '</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
                //  '<div>App-specific setting item</div>',
              '</app-settings>',
              '<app-header-right-sim-list>',
                '<ul class="nav navbar-nav sr-navbar-right">',
                  '<li><a href data-ng-click="nav.showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>',
                '</ul>',
              '</app-header-right-sim-list>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.latticeService = latticeService;
        },
    };
});

SIREPO.app.controller('LatticeController', function(appState, panelState, latticeService, $scope) {
    var self = this;
    self.latticeService = latticeService;
    self.advancedNames = [];
    self.basicNames = ['AUTOREF', 'BEND', 'CHANGREF', 'DRIFT', 'MARKER', 'MULTIPOL', 'QUADRUPO', 'SCALING', 'SEXTUPOL', 'YMY'];
    var scaling = {};

    function updateScaling() {
        var MAX_SCALING_FAMILY = 5;
        scaling = {};
        appState.models.elements.some(function(m) {
            if (m.type == 'SCALING' && m.IOPT == '1') {
                for (var i = 1; i <= MAX_SCALING_FAMILY; i++) {
                    scaling[m['NAMEF' + i]] = m['SCL' + i];
                }
                return true;
            }
        });
    }

    function updateElementAttributes(item) {
        if ('KPOS' in item) {
            item.angle = 0;
            delete item.travelLength;
            item.e1 = item.W_E;
            item.e2 = item.W_S;
            var field = item.B1 || item.B_1;
            if (scaling[item.type]) {
                field *= scaling[item.type];
            }
            var computedAngle = 2 * Math.asin((field * item.l * 100)/(2 * appState.models.bunch.rigidity));
            item.travelLength = latticeService.arcLength(computedAngle, item.l);

            if (item.KPOS == '2') {
                //TODO(pjm): support misalignment YCE, ALE
            }
            else if (item.KPOS == '3') {
                if (item.ALE) {
                    item.angle = - item.ALE * 2;
                }
                else {
                    // angle computed from field, length and magnetic rigidity
                    item.angle = computedAngle;
                }
            }
        }

        if (item.type == 'CHANGREF') {
            item.angle = - item.ALE;
        }
        else if (item.type == 'MULTIPOL') {
            item.color = '';
            if (item.B_2) {
                item.color = SIREPO.lattice.elementColor.QUADRUPO;
            }
            else if (item.B_3) {
                item.color = SIREPO.lattice.elementColor.SEXTUPOL;
            }
        }
    }

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[name].description;
    };

    appState.whenModelsLoaded($scope, function() {

        if (! appState.models.simulation.isInitialized) {
            updateScaling();
            appState.models.elements.map(updateElementAttributes);
            appState.models.simulation.isInitialized = true;
            appState.saveChanges(['elements', 'simulation']);
        }

        $scope.$on('modelChanged', function(e, name) {
            var m = appState.models[name];
            if (m.type) {
                updateElementAttributes(m);
            }
            if (m.type == 'SCALING') {
                updateScaling();
                appState.models.elements.map(updateElementAttributes);
            }
        });
    });
});

SIREPO.app.controller('SourceController', function(appState, latticeService, panelState, zgoubiService, $scope) {
    var self = this;
    var TWISS_FIELDS = ['alpha_Y', 'beta_Y', 'alpha_Z', 'beta_Z', 'DY', 'DT', 'DZ', 'DP', 'Y0', 'T0'];
    var rigidity;

    function processBunchMethod() {
        var bunch = appState.models.bunch;
        panelState.showTab('bunch', 2, bunch.method == 'MCOBJET3');
        panelState.showTab('bunch', 3, bunch.method == 'MCOBJET3');
        panelState.showTab('bunch', 4, bunch.method == 'OBJET2.1');
    }

    function processBunchTwiss() {
        var bunch = appState.models.bunch;
        panelState.showField('simulation', 'visualizationBeamlineId', bunch.match_twiss_parameters == '1');
        TWISS_FIELDS.forEach(function(f) {
            panelState.enableField('bunch', f, bunch.match_twiss_parameters == '0');
        });
    }

    function processParticleSelector() {
        var bunch = appState.models.bunch;
        var count = bunch.particleCount2;
        if (! bunch.coordinates) {
            bunch.coordinates = [];
        }
        for (var i = 0; i < count; i++) {
            if (! bunch.coordinates[i]) {
                bunch.coordinates[i] = appState.setModelDefaults({}, 'particleCoordinate');
            }
        }
        appState.models.particleCoordinate = bunch.coordinates[parseInt(bunch.particleSelector) - 1];
    }

    function processParticleType() {
        var particle = appState.models.particle;
        ['M', 'Q', 'G', 'Tau'].forEach(function(f) {
            panelState.showField('particle', f, particle.particleType == 'Other');
        });
    }

    function processSpinTracking() {
        panelState.showRow('bunch', 'S_X', appState.models.bunch.spntrk == '1');
    }

    self.handleModalShown = function(name) {
        if (name == 'bunch') {
            processBunchTwiss();
            processParticleType();
            processBunchMethod();
            processSpinTracking();
            zgoubiService.processParticleCount2('bunch');
        }
    };

    appState.whenModelsLoaded($scope, function() {
        appState.watchModelFields($scope, ['bunch.match_twiss_parameters'], processBunchTwiss);
        appState.watchModelFields($scope, ['particle.particleType'], processParticleType);
        appState.watchModelFields($scope, ['bunch.method'], processBunchMethod);
        appState.watchModelFields($scope, ['bunch.particleCount2'], function() {
            zgoubiService.processParticleCount2('bunch');
        });
        appState.watchModelFields($scope, ['bunch.particleSelector'], processParticleSelector);
        appState.watchModelFields($scope, ['bunch.spntrk'], processSpinTracking);
        processSpinTracking();
        processParticleType();
        processBunchMethod();
        processParticleSelector();
        rigidity = appState.models.bunch.rigidity;
    });

    $scope.$on('bunchReport1.summaryData', function(e, info) {
        if (appState.isLoaded() && info.bunch) {
            var bunch = appState.models.bunch;
            if (bunch.match_twiss_parameters == '1') {
                TWISS_FIELDS.forEach(function(f) {
                    bunch[f] = info.bunch[f];
                });
                appState.saveQuietly('bunch');
            }
        }
    });

    $scope.$on('bunch.changed', function() {
        // reset the lattice if rigidity changes
        if (appState.models.bunch.rigidity != rigidity) {
            appState.models.simulation.isInitialized = false;
            appState.saveQuietly('simulation');
        }
    });

    latticeService.initSourceController(self);
});

SIREPO.app.controller('TwissController', function() {
    var self = this;
});

SIREPO.app.controller('VisualizationController', function (appState, frameCache, latticeService, panelState, persistentSimulation, plotRangeService, zgoubiService, $rootScope, $scope) {
    var self = this;
    self.panelState = panelState;
    self.errorMessage = '';

    function handleStatus(data) {
        self.errorMessage = data.error;
        if (data.startTime && ! data.error) {
            ['bunchAnimation', 'bunchAnimation2', 'energyAnimation'].forEach(function(m) {
                plotRangeService.computeFieldRanges(self, m, data.percentComplete);
                appState.models[m].startTime = data.startTime;
                appState.saveQuietly(m);
            });
            if (data.frameCount) {
                frameCache.setFrameCount(data.frameCount - 1, 'energyAnimation');
            }
        }
        frameCache.setFrameCount(data.frameCount || 0);
    }

    function processShowAllFrames(modelName) {
        var model = appState.models[modelName];
        panelState.showField(modelName, 'framesPerSecond', model.showAllFrames == '0');
        panelState.showField(
            modelName, 'particleSelector',
            model.showAllFrames == '1' && appState.models.bunch.method == 'OBJET2.1');
    }

    self.bunchReportHeading = function(name) {
        return latticeService.bunchReportHeading(name);
    };

    self.handleModalShown = function(name) {
        if (name.indexOf('Animation') >= 0) {
            plotRangeService.processPlotRange(self, name);
            processShowAllFrames(name);
            zgoubiService.processParticleCount2(name);
        }
    };

    self.startSimulation = function() {
        self.simState.saveAndRunSimulation('simulation');
    };

    self.simState = persistentSimulation.initSimulationState($scope, 'animation', handleStatus, {
        bunchAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '3', 'x', 'y', 'histogramBins', 'plotRangeType', 'horizontalSize', 'horizontalOffset', 'verticalSize', 'verticalOffset', 'isRunning', 'showAllFrames', 'particleSelector', 'startTime'],
        bunchAnimation2: [SIREPO.ANIMATION_ARGS_VERSION + '3', 'x', 'y', 'histogramBins', 'plotRangeType', 'horizontalSize', 'horizontalOffset', 'verticalSize', 'verticalOffset', 'isRunning', 'showAllFrames', 'particleSelector', 'startTime'],
        energyAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '3', 'x', 'y', 'histogramBins', 'plotRangeType', 'horizontalSize', 'horizontalOffset', 'verticalSize', 'verticalOffset', 'isRunning', 'showAllFrames', 'particleSelector', 'startTime'],
    });

    self.simState.errorMessage = function() {
        return self.errorMessage;
    };

    self.simState.notRunningMessage = function() {
        return 'Simulation ' + self.simState.stateAsText();
    };

    appState.whenModelsLoaded($scope, function() {
        //TODO(pjm): need to work this into sirepo-lattice.js
        $scope.$on('simulation.changed', function(e, name) {
            $rootScope.$broadcast('activeBeamlineChanged');
        });
        ['bunchAnimation', 'bunchAnimation2', 'energyAnimation'].forEach(function(m) {
            appState.watchModelFields($scope, [m + '.plotRangeType'], function() {
                plotRangeService.processPlotRange(self, m);
            });
            appState.watchModelFields($scope, [m + '.showAllFrames'], function() {
                processShowAllFrames(m);
            });
        });
    });
});

SIREPO.app.factory('zgoubiService', function(appState, panelState) {
    var self = {};

    self.processParticleCount2 = function(model) {
        var count = appState.models.bunch.particleCount2;
        SIREPO.APP_SCHEMA.enum.ParticleSelector.forEach(function(info) {
            var value = info[SIREPO.ENUM_INDEX_VALUE];
            panelState.showEnum(model, 'particleSelector', value, parseInt(value) <= count);
        });
    };

    return self;
});

SIREPO.app.directive('srCaviteEditor', function(appState, panelState) {
    return {
        restrict: 'A',
        controller: function($scope) {

            function processFields() {
                var cavite = appState.models.CAVITE;
                if (! cavite) {
                    return;
                }
                var option = cavite.IOPT;
                // fields by option:
                // 1: L, h, V
                // 2: L, h, V, sig_s
                // 3: V, sig_s
                // 7: f_RF, V, sig_s
                // 10: l, f_RF, ID, V, sig_s, IOP
                panelState.showField('CAVITE', 'L', option == 1 || option == 2);
                panelState.showField('CAVITE', 'h', option == 1 || option == 2);
                panelState.showField('CAVITE', 'V', option > 0);
                panelState.showField('CAVITE', 'sig_s', option > 1);
                panelState.showField('CAVITE', 'f_RF', option == 7 || option == 10);
                panelState.showField('CAVITE', 'l', option == 10);
                panelState.showField('CAVITE', 'ID', option == 10);
                panelState.showField('CAVITE', 'IOP', option == 10);
                if (option != 10) {
                    cavite.l = 0;
                }
            }

            appState.whenModelsLoaded($scope, function() {
                appState.watchModelFields($scope, ['CAVITE.IOPT'], processFields);
                processFields();
            });
        },
    };
});

SIREPO.app.directive('twissSummaryPanel', function(appState, plotting) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div class="form-horizontal">',
              '<div class="form-group sr-parameter-table-row" data-ng-repeat="item in ::summaryValues">',
                '<div class="col-sm-6 control-label"><div data-label-with-tooltip="" label="{{ item[1] }}" tooltip="{{ item[0] }}"></div></div>',
                '<div class="col-sm-6 form-control-static">{{ item[2] }}</div>',
              '</div>',
              '<div class="row">&nbsp;</div>',
              '<div class="row" data-ng-show="columnValues">',
                '<div class="col-sm-3 col-sm-offset-6 lead text-center">Horizontal</div>',
                '<div class="col-sm-3 lead text-center">Vertical</div>',
              '</div>',
              '<div class="form-group sr-parameter-table-row" data-ng-repeat="item in ::columnValues">',
                '<div class="col-sm-6 control-label"><div data-label-with-tooltip="" label="{{ item[0][1] }}" tooltip="{{ item[0][0] }}, {{ item[1][0] }}"></div></div>',
                '<div class="col-sm-3 form-control-static">{{ item[0][2] }}</div>',
                '<div class="col-sm-3 form-control-static">{{ item[1][2] }}</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            function addSummaryRows(rows) {
                $scope.columnValues = {};
                $scope.summaryValues = [];
                rows.forEach(function(row) {
                    var label = row[1];
                    if (/^(Horizontal|Vertical)\s/.test(label)) {
                        var index = /^Horizontal/.test(label) ? 0 : 1;
                        label = label.replace(/^.*?\s/, '');
                        label = label.charAt(0).toUpperCase() + label.slice(1);
                        if (! $scope.columnValues[label]) {
                            $scope.columnValues[label] = [];
                        }
                        row[1] = label;
                        $scope.columnValues[label][index] = row;
                    }
                    else {
                        $scope.summaryValues.push(row);
                    }
                });
            }

            function updateSummaryInfo(e, rows) {
                if (rows) {
                    addSummaryRows(rows);
                }
                else {
                    $scope.summaryRows = null;
                }
            }

            //TODO(pjm): these should be no-op in sirepo-plotting, for text reports, see jspec.js
            var noOp = function() {};
            $scope.clearData = noOp;
            $scope.destroy = noOp;
            $scope.init = noOp;
            $scope.resize = noOp;
            $scope.load = function(json) {
                updateSummaryInfo(null, appState.clone(json.summaryData));
            };
        },
        link: function link(scope, element) {
            scope.modelName = 'twissSummaryReport';
            plotting.linkPlot(scope, element);
        },
    };
});
