'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="FileNameArray" data-ng-class="fieldClass">
          <div data-magnet-files="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="Changref2Array" class="col-sm-7">
          <div data-changref2-fields="" data-model="model" data-field="field"></div>
        </div>
    `;
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="twissSummary" data-twiss-summary-panel="" class="sr-plot"></div>
    `;
    SIREPO.appDownloadLinks = `
        <li data-export-zgoubi-link="" data-report-title="{{ reportTitle() }}"></li>
    `;
    SIREPO.lattice = {
        invalidElementName: /[#*'",]/g,
        elementColor: {
            CHANGREF: 'orange',
            CHANGREF_VALUE: 'orange',
            QUADRUPO: 'tomato',
            SEXTUPOL: 'lightgreen',
            TOSCA: 'cornflowerblue',
        },
        elementPic: {
            aperture: ['COLLIMA'],
            bend: ['AUTOREF', 'BEND', 'DIPOLE', 'CHANGREF', 'CHANGREF_VALUE', 'FFA', 'FFA_SPI', 'MULTIPOL'],
            drift: ['DRIFT'],
            magnet: ['QUADRUPO', 'SEXTUPOL', 'TOSCA'],
            rf: ['CAVITE'],
            solenoid: ['SOLENOID'],
            watch: ['MARKER'],
            zeroLength: ['SCALING', 'SPINR', 'YMY'],
        },
    };
});

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
            <div data-import-dialog="" data-title="Import Zgoubi File" data-description="Select a zgoubi.dat file." data-file-formats=".dat,.res">
              <div data-zgoubi-import-options=""></div>
            </div>
        `,
    };
});

SIREPO.app.directive('appHeader', function(latticeService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: `
            <div data-app-header-brand="nav"></div>
            <div data-app-header-left="nav"></div>
            <div data-app-header-right="nav">
              <app-header-right-sim-loaded>
                <div data-sim-sections="">
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'lattice\')}"><a href data-ng-click="nav.openSection(\'lattice\')"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>
                  <li class="sim-section" data-ng-if="latticeService.hasBeamlines()" data-ng-class="{active: nav.isActive(\'source\')}"><a data-ng-href="{{ nav.sectionURL(\'source\') }}"><span class="glyphicon glyphicon-flash"></span> Bunch</a></li>
                  <li class="sim-section" data-ng-if="latticeService.hasBeamlines()" data-ng-class="{active: nav.isActive(\'twiss\')}"><a data-ng-href="{{ nav.sectionURL(\'twiss\') }}"><span class="glyphicon glyphicon-option-horizontal"></span> Twiss</a></li>
                  <li class="sim-section" data-ng-if="latticeService.hasBeamlines()" data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
              </app-settings>
              <app-header-right-sim-list>
                <ul class="nav navbar-nav sr-navbar-right">
                  <li><a href data-ng-click="nav.showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>
                </ul>
              </app-header-right-sim-list>
            </div>
        `,
        controller: function($scope) {
            $scope.latticeService = latticeService;
        },
    };
});

SIREPO.app.controller('LatticeController', function(appState, errorService, panelState, latticeService, $scope) {
    var self = this;
    self.latticeService = latticeService;
    self.advancedNames = ['AUTOREF',  'TOSCA', 'YMY'];
    self.basicNames = ['BEND', 'CAVITE', 'CHANGREF', 'CHANGREF2', 'COLLIMA', 'DRIFT', 'DIPOLE', 'FFA', 'FFA_SPI', 'MARKER', 'MULTIPOL', 'QUADRUPO', 'SCALING', 'SEXTUPOL', 'SOLENOID', 'SPINR'];
    var scaling = null;

    function updateScaling() {
        var max = SIREPO.APP_SCHEMA.constants.maxScalingFamily;
        scaling = {};
        appState.models.elements.some(function(m) {
            if (m.type == 'SCALING' && m.IOPT == '1') {
                for (var i = 1; i <= max; i++) {
                    var key = m['NAMEF' + i];
                    if (m['LBL' + i]) {
                        key += '.' + m['LBL' + i];
                    }
                    scaling[key] = m['SCL' + i];
                }
                return true;
            }
        });
    }

    function updateElementAttributes(item) {
        if (! scaling) {
            updateScaling();
        }
        if ('KPOS' in item) {
            item.angle = 0;
            delete item.travelLength;
            item.e1 = item.W_E;
            item.e2 = item.W_S;
            var field = item.B1 || item.B_1;
            if (scaling[item.type]) {
                field *= scaling[item.type];
            }
            if (scaling[item.type + '.' + item.name]) {
                field *= scaling[item.type + '.' + item.name];
            }
            var computedAngle = 2 * Math.asin((field * item.l * 100)/(2 * appState.models.bunch.rigidity));
            if (item.type == 'BEND') {
                item.travelLength = latticeService.arcLength(computedAngle, item.l);
            }
            else {
                // only BEND seems to use the arcLength
                item.travelLength = item.l;
            }

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
        else if (item.type == 'CHANGREF2') {
            item.subElements.forEach(function(el) {
                if (el.transformType == 'ZR') {
                    el.angle = - el.transformValue;
                }
            });
            if (item.subElements.length > 1 && item.subElements[item.subElements.length - 1].transformType == 'none') {
                item.subElements.pop();
            }
        }
        else if (item.type == 'DIPOLE') {
            item.l = item.RM * (
                item.OMEGA_E - item.OMEGA_S +
                    Math.tan(item.ACN - item.OMEGA_E) +
                    Math.tan(item.AT - item.ACN + item.OMEGA_S));
            item.angle = item.AT;
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
        else if (item.type == 'FFA') {
            // FFA length matches zgoubi DSREF computation in ffagi.f
            var firstDipole = item.dipoles[0];
            item.l = item.RM * (
                firstDipole.OMEGA_E - firstDipole.OMEGA_S
                    + Math.tan(firstDipole.ACN - firstDipole.OMEGA_E)
                    + Math.tan(item.AT - firstDipole.ACN + firstDipole.OMEGA_S));
            item.angle = item.AT;
        }
        else if (item.type == 'FFA_SPI') {
            // FFA length matches zgoubi DSREF computation in ffgspi.f
            var firstDipole2 = item.dipoles[0];
            item.l = item.RM * (firstDipole2.OMEGA_E - firstDipole2.OMEGA_S);
            item.angle = item.AT;
        }
    }

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[name].description;
    };

    appState.whenModelsLoaded($scope, function() {
        var sim = appState.models.simulation;
        if (sim.warnings) {
            errorService.alertText(sim.warnings);
            delete sim.warnings;
        }

        if (! sim.isInitialized) {
            appState.models.elements.map(updateElementAttributes);
            sim.isInitialized = true;
            appState.saveChanges(['elements', 'simulation']);
        }

        $scope.$on('modelChanged', function(e, name) {
            var m = appState.models[name];
            if (m.type) {
                updateElementAttributes(m);
            }
            if (m.type == 'SCALING') {
                scaling = null;
                appState.models.elements.map(updateElementAttributes);
            }
        });

        $scope.$on('elementDeleted', function(e, name, element) {
            if (element.type == 'SCALING') {
                scaling = null;
                appState.models.elements.map(updateElementAttributes);
                appState.saveChanges('elements');
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
        panelState.showTab('bunch', 5, bunch.method.indexOf('OBJET3') == 0);
        panelState.showTab('bunch', 6, bunch.method.indexOf('OBJET3') == 0);
        panelState.showField('bunch', 'FNAME', bunch.method == 'OBJET3');
        panelState.showField('bunch', 'FNAME2', bunch.method == 'OBJET3.1');
        panelState.showField('bunch', 'FNAME3', bunch.method == 'OBJET3.2');
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
        for (var i = 0; i < bunch.particleCount2; i++) {
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
        panelState.showRow('SPNTRK', 'S_X', appState.models.SPNTRK.KSO == '1');
    }

    function processSRLoss() {
        var srLoss = appState.models.SRLOSS;
        panelState.showField('SRLOSS', 'applyToAll', srLoss.KSR == '1');
        panelState.showField('SRLOSS', 'keyword', srLoss.KSR == '1' && srLoss.applyToAll == '0');
    }

    self.handleModalShown = function(name) {
        if (name == 'bunch') {
            processBunchTwiss();
            processParticleType();
            processBunchMethod();
            processSpinTracking();
            processSRLoss();
            zgoubiService.processParticleCount2('bunch');
        }
    };

    appState.whenModelsLoaded($scope, function() {
        appState.watchModelFields($scope, ['bunch.match_twiss_parameters'], processBunchTwiss);
        appState.watchModelFields($scope, ['particle.particleType'], processParticleType);
        appState.watchModelFields($scope, ['bunch.method'], processBunchMethod);
        appState.watchModelFields($scope, ['bunch.particleCount2'], function() {
            zgoubiService.processParticleCount2('bunch');
            processParticleSelector();
        });
        appState.watchModelFields($scope, ['bunch.particleSelector'], processParticleSelector);
        appState.watchModelFields($scope, ['SPNTRK.KSO'], processSpinTracking);
        appState.watchModelFields($scope, ['SRLOSS.KSR', 'SRLOSS.applyToAll'], processSRLoss);
        processSpinTracking();
        processSRLoss();
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
    self.simScope = $scope;
    self.panelState = panelState;
    self.errorMessage = '';
    self.hasPlotFile = false;
    self.showSpin3d = false;

    self.simHandleStatus = function (data) {
        self.errorMessage = data.error;
        if ('percentComplete' in data && ! data.error) {
            ['bunchAnimation', 'bunchAnimation2', 'energyAnimation', 'elementStepAnimation', 'particleAnimation'].forEach(function(m) {
                plotRangeService.computeFieldRanges(self, m, data.percentComplete);
                appState.saveQuietly(m);
            });
            if (data.frameCount) {
                frameCache.setFrameCount(data.frameCount - 1, 'energyAnimation');
                frameCache.setFrameCount(data.frameCount - 1, 'elementStepAnimation');
                frameCache.setFrameCount(data.frameCount - 1, 'particleAnimation');
                updateTunesReport(data.showTunesReport, data.lastUpdateTime);
            }
            self.hasPlotFile = data.hasPlotFile;
            self.showSpin3d = data.showSpin3d;
        }
        frameCache.setFrameCount(data.frameCount || 0);
    };

    function processPlotType(modelName) {
        var model = appState.models[modelName];
        var isHeatmap = model.plotType != 'particle';
        panelState.showField(modelName, 'histogramBins', isHeatmap);
        panelState.showField(modelName, 'colorMap', isHeatmap);
        panelState.showTab(modelName, 2, isHeatmap);
    }

    function processShowAllFrames(modelName) {
        var model = appState.models[modelName];
        panelState.showField(modelName, 'framesPerSecond', model.showAllFrames == '0');
        panelState.showField(
            modelName, 'particleSelector',
            modelName == 'tunesReport'
                || modelName == 'particleAnimation'
                || (model.showAllFrames == '1' && zgoubiService.showParticleSelector()));
    }

    function updateTunesReport(showTunesReport, lastUpdateTime) {
        // tunesReport is tied to the current animation data
        // only show if particle count is <= 10 and number of turnes is >= 10
        appState.models.tunesReport.showTunesReport = showTunesReport;
        appState.models.tunesReport.lastUpdateTime = lastUpdateTime;
        // need to wait for report to become visible so it can respond to changes
        panelState.waitForUI(function() {
            appState.saveChanges('tunesReport');
        });
    }

    self.bunchReportHeading = function(name) {
        return latticeService.bunchReportHeading(name);
    };

    self.handleModalShown = function(name) {
        if (appState.isAnimationModelName(name)) {
            plotRangeService.processPlotRange(self, name);
            processShowAllFrames(name);
            processPlotType(name);
            zgoubiService.processParticleCount2(name);
        }
    };

    self.reportType = function(modelName) {
        if (appState.isLoaded()) {
            return appState.applicationState()[modelName].plotType;
        }
        return '3d';
    };

    self.showTunesReport = function() {
        return ! self.simState.isProcessing() && self.simState.hasFrames() && appState.models.tunesReport.showTunesReport;
    };

    self.startSimulation = function() {
        self.simState.saveAndRunSimulation('simulation');
    };

    self.simState = persistentSimulation.initSimulationState(self);

    self.simState.errorMessage = function() {
        return self.errorMessage;
    };

    appState.whenModelsLoaded($scope, function() {
        //TODO(pjm): need to work this into sirepo-lattice.js
        $scope.$on('simulation.changed', function(e, name) {
            $rootScope.$broadcast('activeBeamlineChanged');
        });
        ['bunchAnimation', 'bunchAnimation2', 'energyAnimation', 'elementStepAnimation'].forEach(function(m) {
            appState.watchModelFields($scope, [m + '.plotRangeType'], function() {
                plotRangeService.processPlotRange(self, m);
            });
            appState.watchModelFields($scope, [m + '.showAllFrames'], function() {
                processShowAllFrames(m);
            });
            appState.watchModelFields($scope, [m + '.plotType'], function() {
                processPlotType(m);
            });
        });
    });
});

SIREPO.app.factory('magnetService', function() {
    var self = {};

    self.hasFileFields = function(magnetType) {
        return magnetType.indexOf('-f') >= 0;
    };

    self.isMultiFile = function(magnetType) {
        return magnetType.indexOf('-mf') >= 0;
    };

    self.isSingleFile = function(magnetType) {
        return magnetType.indexOf('-sf') >= 0;
    };

    self.isZipFile = function(filename) {
        return filename && filename.match(/.zip$/i) ? true : false;
    };

    self.magnetFileCount = function(model) {
        var magnetType = model.magnetType;
        if (self.hasFileFields(magnetType)) {
            return model.fileCount;
        }
        if (self.isSingleFile(magnetType)) {
            return self.isZipFile(model.magnetFile) ? 1 : 0;
        }
        if (magnetType == '3d-mf-2v') {
            return Math.floor((model.IZ + 1 ) / 2);
        }
        if (magnetType == '3d-mf-1v') {
            return model.IZ;
        }
        throw new Error('unhandled magnetType: ' + magnetType);
    };

    self.magnetTypesForMesh = function(model) {
        // list of magnet types depends on mesh and Z
        var is2D = model.IZ == 1;
        if (model.meshType == 'cartesian') {
            if (is2D) {
                return ['2d-sf', '2d-sf-ags', '2d-sf-ags-p', '2d-mf-f'];
            }
            return ['3d-mf-2v', '3d-mf-1v', '3d-sf-2v', '3d-sf-1v', '3d-sf-8v', '3d-mf-f'];
        }
        // cylindrical
        if (is2D) {
            return ['2d-mf-f', '2d-mf-f-2v'];
        }
        return ['3d-sf-4v', '3d-mf-f-2v'];
    };

    return self;
});

SIREPO.app.factory('zgoubiService', function(appState, panelState) {
    var self = {};

    function particleCount() {
        var bunch = appState.models.bunch;
        if (bunch.method == 'MCOBJET3') {
            return bunch.particleCount;
        }
        return bunch.particleCount2;
    }

    self.computeModel = function(analysisModel) {
        return 'animation';
    };

    self.showParticleSelector = function() {
        return particleCount() <= SIREPO.APP_SCHEMA.constants.maxFilterPlotParticles;
    };

    self.processParticleCount2 = function(model) {
        var count = particleCount();
        SIREPO.APP_SCHEMA.enum.ParticleSelector.forEach(function(info) {
            var value = info[SIREPO.ENUM_INDEX_VALUE];
            panelState.showEnum(model, 'particleSelector', value, parseInt(value) <= count);
        });
    };

    appState.setAppService(self);

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

// editor used by both FFA and FFA_SPI models
function srFFAEditor(modelName) {

    return function(appState, panelState) {
        return {
            restrict: 'A',
            controller: function($scope) {
                var dipoleType = modelName == 'FFA'
                    ? 'ffaDipole'
                    : 'ffaSpiDipole';
                function processAlignment() {
                    var ffa = appState.models[modelName];
                    if (! ffa) {
                        return;
                    }
                    panelState.showRow(modelName, 'RE', ffa.KPOS == '2');
                    panelState.showField(modelName, 'DP', ffa.KPOS == '1');
                }

                function processDipoleCount() {
                    var ffa = appState.models[modelName];
                    if (! ffa) {
                        return;
                    }
                    SIREPO.APP_SCHEMA.enum.DipoleSelector.forEach(function(info) {
                        var value = info[SIREPO.ENUM_INDEX_VALUE];
                        panelState.showEnum(modelName, 'dipoleSelector', value, parseInt(value) <= ffa.N);
                    });
                }

                function processSelector() {
                    var ffa = appState.models[modelName];
                    if (! ffa) {
                        return;
                    }
                    if (! ffa.dipoles) {
                        ffa.dipoles = [];
                    }
                    for (var i = 0; i < ffa.N; i++) {
                        if (! ffa.dipoles[i]) {
                            ffa.dipoles[i] = appState.setModelDefaults({}, dipoleType);
                        }
                    }
                    appState.models[dipoleType] = ffa.dipoles[parseInt(ffa.dipoleSelector) - 1];
                }

                $scope.$on('sr-tabSelected', function() {
                    var ffa = appState.models[modelName];
                    if (! ffa) {
                        return;
                    }
                    processSelector();
                    processDipoleCount();
                    processAlignment();
                });

                appState.whenModelsLoaded($scope, function() {
                    appState.watchModelFields($scope, [modelName + '.dipoleSelector'], processSelector);
                    appState.watchModelFields($scope, [modelName + '.N'], processDipoleCount);
                    appState.watchModelFields($scope, [modelName + '.KPOS'], processAlignment);
                });
            },
        };
    };
}
SIREPO.app.directive('srFfaEditor', srFFAEditor('FFA'));
SIREPO.app.directive('srFfaspiEditor', srFFAEditor('FFA_SPI'));

SIREPO.app.directive('srSpinrEditor', function(appState, panelState) {
    return {
        restrict: 'A',
        controller: function($scope) {

            function processFields() {
                if (! appState.models.SPINR) {
                    return;
                }
                var option = appState.models.SPINR.IOPT;
                panelState.showField('SPINR', 'phi', option == 1 || option == 2);
                panelState.showField('SPINR', 'mu', option == 1);
                ['B', 'B_0', 'C_0', 'C_1', 'C_2', 'C_3'].forEach(function(f) {
                    panelState.showField('SPINR', f, option == 2);
                });
            }

            appState.whenModelsLoaded($scope, function() {
                appState.watchModelFields($scope, ['SPINR.IOPT'], processFields);
                processFields();
            });
        },
    };
});

SIREPO.app.directive('srToscaEditor', function(appState, magnetService, panelState, requestSender) {
    return {
        restrict: 'A',
        controller: function($scope) {

            function getTosca() {
                if (appState.isLoaded() && appState.models.TOSCA) {
                    if (! appState.models.TOSCA.fileNames) {
                        appState.models.TOSCA.fileNames = [];
                    }
                    return appState.models.TOSCA;
                }
                return null;
            }

            function processAlignment() {
                var tosca = getTosca();
                if (tosca) {
                    updateAlignment(tosca);
                }
            }

            function processFileCount() {
                var tosca = getTosca();
                if (tosca) {
                    updateFileFields(tosca);
                }
            }

            function processIntegrationBoundary() {
                var tosca = getTosca();
                if (tosca) {
                    updateIntegrationBoundary(tosca);
                }
            }

            function processMeshType() {
                var tosca = getTosca();
                if (tosca) {
                    updateMagnetType(tosca);
                    updateAlignment(tosca);
                }
            }

            function processMagnetFile() {
                var tosca = getTosca();
                if (tosca) {
                    //TODO(pjm): error message if zip file required and regular file supplied
                    requestSender.sendStatefulCompute(
                        appState,
                        function(data) {
                            if (appState.isLoaded() && data.toscaInfo) {
                                if (data.toscaInfo.magnetFile != tosca.magnetFile) {
                                    // ignore old requests
                                    return;
                                }
                                tosca.l = data.toscaInfo.toscaLength;
                                tosca.allFileNames = data.toscaInfo.fileList;
                                if (tosca.allFileNames.length == 1 && tosca.fileCount == 1) {
                                    tosca.fileNames = [tosca.allFileNames[0]];
                                }
                            }
                        },
                        {
                            method: 'tosca_info',
                            args: {
                                tosca: tosca,
                            }
                        }
                    );
                    updateMagnetFiles(tosca);
                }
            }

            function processZCount() {
                var tosca = getTosca();
                if (tosca) {
                    updateMagnetType(tosca);
                }
            }

            function updateAlignment(tosca) {
                ['XCE', 'YCE', 'ALE'].forEach(function(f) {
                    panelState.showField('TOSCA', f, tosca.meshType == 'cartesian');
                });
                ['RE', 'TE', 'RS', 'TS'].forEach(function(f) {
                    panelState.showField('TOSCA', f, tosca.meshType == 'cylindrical' && tosca.KPOS == '2');
                });
            }

            function updateFileFields(tosca) {
                var hasFileFields = magnetService.hasFileFields(tosca.magnetType);
                panelState.showField('TOSCA', 'fileCount', hasFileFields);
                [1, 2, 3, 4].forEach(function(idx) {
                    panelState.showField('TOSCA', 'field' + idx, hasFileFields && tosca.fileCount >= idx);
                });
            }

            function updateIntegrationBoundary(tosca) {
                var useBoundary = tosca.ID != '0';
                ['A', 'B', 'C'].forEach(function(f) {
                    panelState.showField('TOSCA', f, useBoundary);
                });
                ['Ap', 'Bp', 'Cp'].forEach(function(f) {
                    panelState.showField('TOSCA', f, tosca.ID == '2' || tosca.ID == '3');
                });
                ['App', 'Bpp', 'Cpp'].forEach(function(f) {
                    panelState.showField('TOSCA', f, tosca.ID == '3');
                });
            }

            function updateMagnetFiles(tosca) {
                panelState.showField(
                    'TOSCA', 'fileNames',
                    magnetService.isMultiFile(tosca.magnetType) || magnetService.isZipFile(tosca.magnetFile));
            }

            function updateMagnetType(tosca) {
                var items = magnetService.magnetTypesForMesh(tosca);
                var allItems = SIREPO.APP_SCHEMA.enum.TOSCAMagnetType.map(function(v) {
                    return v[0];
                });
                allItems.forEach(function(item) {
                    panelState.showEnum('TOSCA', 'magnetType', item, items.indexOf(item) >= 0);
                });
                if (items.indexOf(tosca.magnetType) < 0) {
                    // select the first item in the list if the current selection is invalid
                    tosca.magnetType = items[0];
                }
            }

            function updatePolynomialInterpolation(tosca) {
                panelState.showField('TOSCA', 'IORDRE', tosca.IZ == 1);
            }

            $scope.$on('sr-tabSelected', function() {
                var tosca = appState.models.TOSCA;
                if (! tosca) {
                    return;
                }
                updateMagnetType(tosca);
                updateAlignment(tosca);
                updateFileFields(tosca);
                updateIntegrationBoundary(tosca);
                updatePolynomialInterpolation(tosca);
                updateMagnetFiles(tosca);
            });

            appState.whenModelsLoaded($scope, function() {
                appState.watchModelFields($scope, ['TOSCA.meshType'], processMeshType);
                appState.watchModelFields($scope, ['TOSCA.IZ'], processZCount);
                appState.watchModelFields($scope, ['TOSCA.KPOS'], processAlignment);
                appState.watchModelFields($scope, ['TOSCA.fileCount'], processFileCount);
                appState.watchModelFields($scope, ['TOSCA.ID'], processIntegrationBoundary);
                appState.watchModelFields($scope, ['TOSCA.magnetFile'], processMagnetFile);
                processMagnetFile();
            });
        },
    };
});

SIREPO.app.directive('srTunesreportEditor', function(appState, panelState, zgoubiService) {
    return {
        restrict: 'A',
        controller: function($scope) {

            function processFields() {
                panelState.showField('tunesReport', 'plotAxis', appState.models.tunesReport.particleSelector == 'all');
                zgoubiService.processParticleCount2('tunesReport');
            }

            appState.whenModelsLoaded($scope, function() {
                appState.watchModelFields($scope, ['tunesReport.particleSelector'], processFields);
                processFields();
            });
        },
    };
});

SIREPO.app.directive('changref2Fields', function(appState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <div class="form-group form-group-sm">
            <div class="col-sm-5">
            <div class="text-center"><b>Type</b></div>
            </div>
            <div class="col-sm-6">
            <div class="text-center"><b>Amount</b></div>
            </div>
            </div>
            <div data-ng-repeat="idx in fieldRows()">
              <div class="form-group form-group-sm">
                <div data-field-editor="\'transformType\'" data-model-name="\'CHANGREF_VALUE\'" data-model="model[field][idx]"></div>
                <div data-field-editor="\'transformValue\'" data-model-name="\'CHANGREF_VALUE\'" data-model="model[field][idx]" data-field-size="6"></div>
              </div>
            </div>
        `,
        controller: function($scope) {
            var MAX_FIELDS = 9;
            var range = d3.range(1);
            $scope.subType = 'CHANGREF_VALUE';

            $scope.fieldRows = function() {
                if (! appState.isLoaded() || ! $scope.model) {
                    return null;
                }
                if (! $scope.model[$scope.field]) {
                    $scope.model[$scope.field] = [];
                }
                var values = $scope.model[$scope.field];
                for (var i = values.length - 2; i >= 0; i--) {
                    // remove none rows, except last one
                    if (values[i].transformType == 'none') {
                        values.splice(i, 1);
                    }
                }
                if (values.length == 0 || (values.length < MAX_FIELDS && values[values.length - 1].transformType != 'none')) {
                    values.push({
                        'type': $scope.subType,
                        'transformType': 'none',
                        'transformValue': 0,
                    });
                }
                if (range.length != values.length) {
                    range = d3.range(values.length);
                }
                return range;
            };
        },
    };
});

SIREPO.app.directive('exportZgoubiLink', function(appState, panelState, requestSender) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <a data-ng-show="showLink" data-ng-href="{{ zgoubiDataUrl() }}" target="_blank">zgoubi.dat</a>
        `,
        controller: function($scope) {
            $scope.showLink = false;

            $scope.zgoubiDataUrl = function() {
                if (! appState.isLoaded()) {
                    return null;
                }
                var modelKey = panelState.findParentAttribute($scope, 'modelKey');
                $scope.showLink = modelKey != 'beamlineReport';
                return requestSender.formatUrl('downloadDataFile', {
                    '<simulation_id>': appState.models.simulation.simulationId,
                    '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                    '<model>': modelKey,
                    '<frame>': appState.isAnimationModelName(modelKey) ? 1 : SIREPO.nonDataFileFrame,
                    '<suffix>': 'zgoubi.dat',
                });
            };
        },
    };
});

SIREPO.app.directive('magnetFiles', function(appState, magnetService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <div data-ng-repeat="idx in fileRange()">
              <select style="margin-bottom: 1ex" class="form-control" data-ng-model="model[field][idx]" data-ng-options="item for item in model.allFileNames track by item"></select>
            </div>
        `,
        controller: function($scope) {
            var range = [];

            $scope.fileRange = function() {
                if (! appState.isLoaded() || ! $scope.model) {
                    return null;
                }
                var count = magnetService.magnetFileCount($scope.model);
                if (count != range.length) {
                    range = new Array(count);
                    for (var i = 0; i < range.length; i++) {
                        range[i] = i;
                    }
                }
                return range;
            };
        },
    };
});

SIREPO.app.directive('twissSummaryPanel', function(appState, plotting) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div class="form-horizontal">
              <div class="form-group sr-parameter-table-row" data-ng-repeat="item in ::summaryValues">
                <div class="col-sm-6 control-label"><div data-label-with-tooltip="" label="{{ item[1] }}" tooltip="{{ item[0] }}"></div></div>
                <div class="col-sm-6 form-control-static">{{ item[2] }}</div>
              </div>
              <div class="row">&nbsp;</div>
              <div class="row" data-ng-show="columnValues">
                <div class="col-sm-3 col-sm-offset-6 lead text-center">Horizontal</div>
                <div class="col-sm-3 lead text-center">Vertical</div>
              </div>
              <div class="form-group sr-parameter-table-row" data-ng-repeat="item in ::columnValues">
                <div class="col-sm-6 control-label"><div data-label-with-tooltip="" label="{{ item[0][1] }}" tooltip="{{ item[0][0] }}, {{ item[1][0] }}"></div></div>
                <div class="col-sm-3 form-control-static">{{ item[0][2] }}</div>
                <div class="col-sm-3 form-control-static">{{ item[1][2] }}</div>
              </div>
            </div>
        `,
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


SIREPO.app.directive('zgoubiImportOptions', function(fileUpload, requestSender) {
    return {
        restrict: 'A',
        template: `
            <div data-ng-if="hasMissingFiles()" class="form-horizontal" style="margin-top: 1em;">
            <div style="margin-bottom: 1ex; white-space: pre;">{{ additionalFileText() }}</div>
            <input id="file-import" type="file" data-file-model="toscaFile.file" accept="*.zip">
            <div data-ng-if="uploadDatafile()"></div>
            </div>
        `,

        controller: function($scope) {
            var parentScope = $scope.$parent;
            var missingFiles;
            $scope.toscaFile = {
                file: {},
            };

            $scope.additionalFileText = function() {
                if (missingFiles) {
                    return 'Please upload a zip file which contains the following TOSCA input files:'
                        + "\n    " + missingFiles.join("\n    ");
                }
            };

            $scope.uploadDatafile = function() {
                if ($scope.toscaFile.file.name) {
                    parentScope.isUploading = true;
                    fileUpload.uploadFileToUrl(
                        $scope.toscaFile.file,
                        null,
                        requestSender.formatUrl(
                            'uploadLibFile',
                            {
                                // dummy id because no simulation id is available or required
                                '<simulation_id>': '11111111',
                                '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                                '<file_type>': 'TOSCA-magnetFile',
                            }),
                        function(data) {
                            parentScope.isUploading = false;
                            if (data.error) {
                                parentScope.fileUploadError = data.error;
                                return;
                            }
                            parentScope.fileUploadError = null;
                        });
                    $scope.toscaFile.file = {};
                }
                return false;
            };

            $scope.hasMissingFiles = function() {
                if (parentScope.fileUploadError) {
                    if (parentScope.errorData && parentScope.errorData.missingFiles) {
                        var set = {};
                        parentScope.errorData.missingFiles.forEach(function(err) {
                            err.TOSCA.forEach(function(name) {
                                set[name] = 1;
                            });
                        });
                        missingFiles = Object.keys(set).sort(function(a, b) {
                            return a.localeCompare(b);
                        });
                        delete parentScope.errorData;
                    }
                }
                else {
                    missingFiles = null;
                }
                return missingFiles && missingFiles.length;
            };
        },
    };
});

SIREPO.app.directive('particle3d', function(appState, plotting, plotToPNG, utilities) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: `
            <div class="sr-screenshot" data-ng-class="{\'sr-plot-loading\': isLoading(), \'sr-plot-cleared\': dataCleared}">
              <div class="main-title text-center">{{ title }}</div>
              <div class="sr-plot sr-plot-particle-3d vtk-canvas-holder">
              </div>
            </div>
        `,
        controller: function($scope, $element) {
            var fsRenderer = null;
            var actors = [];
            var orientationMarker = null;
            $scope.title = '';
            $scope.margin = {
                top: 0,
                right: 0,
                bottom: 0,
                left: 0,
            };

            function addPoints(data) {
                var numPts = data.length / 3;
                var points = new window.Float32Array(data);
                var pd = vtk.Common.DataModel.vtkPolyData.newInstance();
                pd.getPoints().setData(points, 3);
                var mapper = vtk.Rendering.Core.vtkSphereMapper.newInstance();
                var scale = new window.Float32Array(numPts);
                for (var i = 0; i < numPts; i++) {
                    scale[i] = 0.01;
                }
                pd.getPointData().addArray(
                    vtk.Common.Core.vtkDataArray.newInstance({
                        name: 'scaling',
                        values: scale,
                        numberOfComponents: 1,
                    }));
                var actor = vtk.Rendering.Core.vtkActor.newInstance();
                actor.getProperty().setLighting(false);
                actor.getProperty().setColor(0.3, 0.4, 0.9);
                actor.getProperty().setPointSize(4);
                mapper.setInputData(pd);
                mapper.setScaleArray('scaling');
                actor.setMapper(mapper);
                fsRenderer.getRenderer().addActor(actor);
                return actor;
            }

            function addSphere() {
                var sphere = vtk.Filters.Sources.vtkSphereSource.newInstance();
                var mapper = vtk.Rendering.Core.vtkMapper.newInstance();
                mapper.setInputConnection(sphere.getOutputPort());
                var actor = vtk.Rendering.Core.vtkActor.newInstance();
                actor.setMapper(mapper);
                actor.getProperty().setColor(0.9, 0.9, 0.9);
                actor.getProperty().setLighting(false);
                actor.getProperty().setOpacity(0.7);
                sphere.set({
                    'radius': 1,
                    'thetaResolution': 100,
                    'phiResolution': 100,
                });
                fsRenderer.getRenderer().addActor(actor);
                return actor;
            }

            function getVtkElement() {
                return $($element).find('.vtk-canvas-holder');
            }

            function refresh() {
                var aspectRatio = appState.models[$scope.modelName].aspectRatio;
                var rw = getVtkElement();
                var hw = plotting.constrainFullscreenSize($scope, rw.width(), aspectRatio);
                rw.height(hw[0]);
                rw.width(hw[1]);
                fsRenderer.resize();
            }

            function reset() {
                var renderer = fsRenderer.getRenderer();
                var cam = renderer.get().activeCamera;
                cam.setPosition(0, 0, 1);
                cam.setFocalPoint(0, 0, 0);
                cam.setViewUp(0, 1, 0);
                renderer.resetCamera();
                cam.zoom(1.5);
                orientationMarker.updateMarkerOrientation();
                fsRenderer.getRenderWindow().render();
            }

            $scope.destroy = function() {
                getVtkElement().off();
                fsRenderer.getInteractor().unbindEvents();
                fsRenderer.delete();
            };

            $scope.init = function() {
                var rw = getVtkElement();
                rw.on('dblclick', reset);
                fsRenderer = vtk.Rendering.Misc.vtkFullScreenRenderWindow.newInstance(
                    {
                        background: [1, 1, 1, 1],
                        container: rw[0],
                    });
                fsRenderer.getRenderer().getLights()[0].setLightTypeToSceneLight();
                orientationMarker = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
                    actor: vtk.Rendering.Core.vtkAxesActor.newInstance(),
                    interactor: fsRenderer.getInteractor()
                });
                orientationMarker.setEnabled(true);
                orientationMarker.setViewportCorner(
                    vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.TOP_RIGHT
                );
                plotToPNG.initVTK($element, fsRenderer);
            };

            $scope.load = function(json) {
                $scope.title = json.title;
                actors.forEach(function(actor) {
                    fsRenderer.getRenderer().removeActor(actor);
                });
                actors.push(addPoints(json.points));
                actors.push(addSphere());
                reset();
                refresh();
            };

            $scope.resize = refresh;

            $scope.$on('$destroy', function() {
                if (orientationMarker) {
                    orientationMarker.setEnabled(false);
                }
            });

        },
        link: function link(scope, element) {
            plotting.vtkPlot(scope, element);
        },
    };
});
