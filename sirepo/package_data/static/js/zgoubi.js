'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.appHomeTab = 'lattice';
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
        zeroLength: ['YMY'],
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
    self.basicNames = ['AUTOREF', 'BEND', 'CHANGREF', 'DRIFT', 'MARKER', 'MULTIPOL', 'QUADRUPO', 'SEXTUPOL', 'YMY'];

    function computeBendAngle(bend) {
    }

    function processChangrefFormat() {
        var model = appState.models.CHANGREF;
        ['XCE', 'YCE', 'ALE'].forEach(function(f) {
            panelState.showField('CHANGREF', f, model.format == 'old');
        });
        panelState.showField('CHANGREF', 'order', model.format == 'new');
    }

    function updateElementAttributes(item) {
        if (item.type == 'BEND') {
            item.angle = 0;
            delete item.travelLength;
            item.e1 = item.W_E;
            item.e2 = item.W_S;
            var computedAngle = 2 * Math.asin((item.B1 * item.l * 100)/(2 * appState.models.bunch.rigidity));
            item.travelLength = latticeService.arcLength(computedAngle, item.l);

            if (item.KPOS == '2') {
                // misaligned
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
        else if (item.type == 'CHANGREF') {
            item.angle = 0;
            if (item.format == 'old') {
                item.angle = - item.ALE;
            }
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

    self.handleModalShown = function(name) {
        if (name == 'CHANGREF') {
            processChangrefFormat();
        }
    };

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[name].description;
    };

    appState.whenModelsLoaded($scope, function() {
        appState.watchModelFields($scope, ['CHANGREF.format'], processChangrefFormat);

        if (! appState.models.simulation.isInitialized) {
            appState.models.elements.map(updateElementAttributes);
            appState.models.simulation.isInitialized = true;
            appState.saveChanges(['elements', 'simulation']);
        }

        $scope.$on('modelChanged', function(e, name) {
            var m = appState.models[name];
            if (m.type) {
                updateElementAttributes(m);
            }
        });
    });
});

SIREPO.app.controller('SourceController', function(appState, latticeService, panelState, $scope) {
    var self = this;
    var TWISS_FIELDS = ['alpha_Y', 'beta_Y', 'alpha_Z', 'beta_Z', 'DY', 'DT', 'DZ', 'DP', 'Y0', 'T0'];

    function processBunchTwiss() {
        var bunch = appState.models.bunch;
        panelState.showField('simulation', 'visualizationBeamlineId', bunch.match_twiss_parameters == '1');
        TWISS_FIELDS.forEach(function(f) {
            panelState.enableField('bunch', f, bunch.match_twiss_parameters == '0');
        });
    }

    function processParticleType() {
        var particle = appState.models.particle;
        ['M', 'Q', 'G', 'Tau'].forEach(function(f) {
            panelState.showField('particle', f, particle.particleType == 'Other');
        });
    }

    self.handleModalShown = function(name) {
        if (name == 'bunch') {
            processBunchTwiss();
            processParticleType();
        }
    };

    appState.whenModelsLoaded($scope, function() {
        appState.watchModelFields($scope, ['bunch.match_twiss_parameters'], processBunchTwiss);
        appState.watchModelFields($scope, ['particle.particleType'], processParticleType);
        processParticleType();
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

    latticeService.initSourceController(self);
});

SIREPO.app.controller('TwissController', function() {
    var self = this;
});

SIREPO.app.controller('VisualizationController', function (appState, frameCache, latticeService, panelState, persistentSimulation, plotRangeService, $rootScope, $scope) {
    var self = this;
    self.settingsModel = 'simulationStatus';
    self.panelState = panelState;
    self.errorMessage = '';

    function handleStatus(data) {
        self.errorMessage = data.error;
        if (data.startTime && ! data.error) {
            ['bunchAnimation', 'bunchAnimation2'].forEach(function(m) {
                plotRangeService.computeFieldRanges(self, m, data.percentComplete);
                appState.models[m].startTime = data.startTime;
                appState.saveQuietly(m);
            });
        }
        frameCache.setFrameCount(data.frameCount || 0);
    }

    self.bunchReportHeading = function(name) {
        return latticeService.bunchReportHeading(name);
    };

    self.handleModalShown = function(name) {
        if (name.indexOf('bunchAnimation') >= 0) {
            plotRangeService.processPlotRange(self, name);
        }
    };

    self.notRunningMessage = function() {
        return 'Simulation ' + self.simState.stateAsText();
    };

    self.startSimulation = function() {
        self.simState.saveAndRunSimulation('simulation');
    };

    self.simState = persistentSimulation.initSimulationState($scope, 'animation', handleStatus, {
        bunchAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '2', 'x', 'y', 'histogramBins', 'plotRangeType', 'horizontalSize', 'horizontalOffset', 'verticalSize', 'verticalOffset', 'isRunning', 'startTime'],
        bunchAnimation2: [SIREPO.ANIMATION_ARGS_VERSION + '2', 'x', 'y', 'histogramBins', 'plotRangeType', 'horizontalSize', 'horizontalOffset', 'verticalSize', 'verticalOffset', 'isRunning', 'startTime'],
    });

    appState.whenModelsLoaded($scope, function() {
        //TODO(pjm): need to work this into sirepo-lattice.js
        $scope.$on('simulation.changed', function(e, name) {
            $rootScope.$broadcast('activeBeamlineChanged');
        });
        appState.watchModelFields($scope, ['bunchAnimation.plotRangeType'], function() {
            plotRangeService.processPlotRange(self, 'bunchAnimation');
        });
        appState.watchModelFields($scope, ['bunchAnimation2.plotRangeType'], function() {
            plotRangeService.processPlotRange(self, 'bunchAnimation2');
        });
    });
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
