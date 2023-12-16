'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
    SIREPO.SINGLE_FRAME_ANIMATION = ['beamEvolutionAnimation', 'coolingRatesAnimation', 'forceTableAnimation'];
    SIREPO.FILE_UPLOAD_TYPE = {
        'ring-lattice': '.tfs,.txt',
    };
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="rateCalculation" data-rate-calculation-panel="" class="sr-plot sr-screenshot"></div>
    `;
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="ElegantSimList" data-ng-class="fieldClass">
          <div data-sim-list="" data-model="model" data-field="field" data-code="elegant" data-route="visualization"></div>
        </div>
        <div data-ng-switch-when="TwissFile" class="col-sm-7">
          <div data-twiss-file-field="" data-model="model" data-field="field" data-model-name="modelName"></div>
        </div>
    `;
});

SIREPO.app.factory('jspecService', function(appState) {
    var self = {};

    self.computeModel = function(analysisModel) {
        return 'animation';
    };

    appState.setAppService(self);

    return self;
});

SIREPO.app.controller('SourceController', function(appState, panelState, $scope) {
    var self = this;
    self.twissReportId = Math.floor(Math.random() * Number.MAX_SAFE_INTEGER);

    function processElectronBeamShape() {
        var shape = appState.models.electronBeam.shape;
        panelState.showField('electronBeam', 'radius', shape == 'dc_uniform' || shape == 'bunched_uniform');
        panelState.showField('electronBeam', 'current', shape == 'dc_uniform' || shape == 'bunched_uniform' || shape == 'bunched_uniform_elliptic');
        panelState.showField('electronBeam', 'length', shape == 'bunched_uniform' || shape == 'bunched_uniform_elliptic');
        ['e_number', 'sigma_x', 'sigma_y', 'sigma_z'].forEach(function(f) {
            panelState.showField('electronBeam', f, shape == 'bunched_gaussian');
        });
        ['rh', 'rv'].forEach(function(f) {
            panelState.showField('electronBeam', f, shape == 'bunched_uniform_elliptic');
        });
        // dynamically set the help text in the schema for the selected beam shape
        SIREPO.APP_SCHEMA.enum.ElectronBeamShape.forEach(function(v, i) {
            if (v[0] == shape) {
                SIREPO.APP_SCHEMA.model.electronBeam.shape[3] = SIREPO.APP_SCHEMA.enum.ElectronBeamShapeDescription[i][1];
            }
        });
    }

    function processElectronBeamType() {
        var ebeam = appState.models.electronBeam;
        var beam_type = ebeam.beam_type;
        if (beam_type == 'continuous') {
            // only one shape choice for continuous beams
            ebeam.shape = 'dc_uniform';
        }
        else {
            if (ebeam.shape == 'dc_uniform') {
                ebeam.shape = 'bunched_uniform';
            }
        }
        SIREPO.APP_SCHEMA.enum.ElectronBeamShape.forEach(function(v) {
            if (v[0].indexOf('bunched') >= 0) {
                panelState.showEnum('electronBeam', 'shape', v[0], beam_type == 'bunched');
            }
            else {
                panelState.showEnum('electronBeam', 'shape', v[0], beam_type == 'continuous');
            }
        });
    }

    function processGamma() {
        var ionBeam = appState.models.ionBeam;
        var gamma = 0;
        if (ionBeam.mass != 0) {
            gamma = (1 + ionBeam.kinetic_energy / ionBeam.mass).toFixed(6);
        }
        // electronBeam.gamma is not directly used on server side calculation
        appState.models.electronBeam.gamma = gamma;
        appState.applicationState().electronBeam.gamma = gamma;
        panelState.enableField('electronBeam', 'gamma', false);
    }

    function processIntrabeamScatteringMethod() {
        var method = appState.models.intrabeamScatteringRate.longitudinalMethod;
        panelState.showField('intrabeamScatteringRate', 'nz', method == 'nz');
        panelState.showField('intrabeamScatteringRate', 'log_c', method == 'log_c');
    }

    function processIonBeamType() {
        panelState.showField('ionBeam', 'rms_bunch_length', appState.models.ionBeam.beam_type == 'bunched');
    }

    function processLatticeSource() {
        var latticeSource = appState.models.ring.latticeSource;
        panelState.showField('ring', 'lattice', latticeSource == 'madx');
        panelState.showField('ring', 'elegantTwiss', latticeSource == 'elegant');
        panelState.showField('ring', 'elegantSirepo', latticeSource == 'elegant-sirepo');
    }

    function processParticle() {
        var n = 'ionBeam';
        ['mass', 'charge_number'].forEach(function(f) {
            panelState.showField(n, f, appState.models[n].particle === 'OTHER');
        });
    }

    function updateForceFormulas() {
        if (! SIREPO.APP_SCHEMA.feature_config.derbenevskrinsky_force_formula) {
            [
                'derbenevskrinsky',
                'unmagnetized',
                'budker',
            ].forEach(function(e) {
                panelState.showEnum('electronCoolingRate', 'force_formula', e, false);
            });
        }
    }

    self.showTwissEditor = function() {
        panelState.showModalEditor('twissReport');
    };

    $scope.$on('sr-tabSelected', () => {
        processIonBeamType();
        processElectronBeamType();
        processElectronBeamShape();
        processLatticeSource();
        processGamma();
        processParticle();
        updateForceFormulas();
        panelState.showEnum('electronCoolingRate', 'force_formula', 'pogorelov', false);
    });
    appState.watchModelFields($scope, ['ionBeam.beam_type'], processIonBeamType);
    appState.watchModelFields($scope, ['electronBeam.shape', 'electronBeam.beam_type'], processElectronBeamShape);
    appState.watchModelFields($scope, ['electronBeam.beam_type'], processElectronBeamType);
    appState.watchModelFields($scope, ['ring.latticeSource'], processLatticeSource);
    appState.watchModelFields($scope, ['ionBeam.mass', 'ionBeam.kinetic_energy'], processGamma);
    appState.watchModelFields($scope, ['ionBeam.particle'], processParticle);
    $scope.$on('sr-tabSelected', processIntrabeamScatteringMethod);
    $scope.$on('sr-tabSelected', updateForceFormulas);
    appState.watchModelFields($scope, ['intrabeamScatteringRate.longitudinalMethod'], processIntrabeamScatteringMethod);
});

SIREPO.app.controller('VisualizationController', function(appState, frameCache, panelState, persistentSimulation, plotRangeService, jspecService, $scope) {
    var self = this;
    self.simScope = $scope;
    self.hasParticles = false;
    self.hasRates = false;
    self.hasForceTable = false;

    self.simHandleStatus = function(data) {
        self.hasParticles = self.hasRates = self.hasForceTable = false;
        if ('percentComplete' in data && ! data.error) {
            self.hasParticles = data.hasParticles;
            self.hasRates = data.hasRates;
            self.hasForceTable = data.hasForceTable;
            plotRangeService.computeFieldRanges(self, 'particleAnimation', data.percentComplete);
        }
        frameCache.setFrameCount(data.frameCount || 0);
    };

    function processColorRange() {
        ['colorMin', 'colorMax'].forEach(function(f) {
            panelState.showField('particleAnimation', f, appState.models.particleAnimation.colorRangeType == 'fixed');
        });
    }

    function processForceTablePlot() {
        if (! appState.isLoaded()) {
            return;
        }
        var force = appState.models.forceTableAnimation;
        if (force.plot == 'longitudinal') {
            force.x = 'Vlong';
            force.y1 = 'flong';
        }
        else {
            force.x = 'Vtrans';
            force.y1 = 'fx';
        }
    }

    function processModel() {
        var settings = appState.models.simulationSettings;
        panelState.showField('simulationSettings', 'save_particle_interval', settings.model == 'particle');
        panelState.showRow('simulationSettings', 'ref_bet_x', settings.model == 'particle' && settings.e_cool == '0');
        panelState.showField('electronCoolingRate', 'sample_number', settings.model == 'particle');
    }

    function processTimeStep() {
        var s = appState.models.simulationSettings;
        if (panelState.isActiveField('simulationSettings', 'time') || panelState.isActiveField('simulationSettings', 'step_number')) {
            s.time_step = s.time / s.step_number;
        }
        else if (panelState.isActiveField('simulationSettings', 'time_step')) {
             s.time = s.step_number * s.time_step;
        }
    }

    self.simCompletionState = function() {
        if (! self.hasParticles) {
            return '';
        }
        return  SIREPO.APP_SCHEMA.strings.completionState;
    };

    $scope.$on('sr-tabSelected', function(evt, name) {
        processModel();
        if (name == 'particleAnimation') {
            processColorRange();
            plotRangeService.processPlotRange(self, name);
        }
        else if (name == 'beamEvolutionAnimation' || name == 'coolingRatesAnimation') {
            //TODO(pjm): plots have fixed x field 't', should set in template.jspec, see _X_FIELD
            appState.models[name].x = 't';
            plotRangeService.processPlotRange(self, name);
        }
        else if (name == 'forceTableAnimation') {
            plotRangeService.processPlotRange(self, name);
        }
    });

    appState.watchModelFields($scope, ['simulationSettings.model', 'simulationSettings.e_cool'], processModel);
    appState.watchModelFields(
        $scope,
        ['simulationSettings.time', 'simulationSettings.step_number', 'simulationSettings.time_step'],
        processTimeStep);
    appState.watchModelFields($scope, ['particleAnimation.colorRangeType'], processColorRange);
    appState.watchModelFields($scope, ['forceTableAnimation.plot'], processForceTablePlot);
    ['particleAnimation', 'beamEvolutionAnimation', 'coolingRatesAnimation', 'forceTableAnimation'].forEach(function(m) {
        appState.watchModelFields($scope, [m + '.plotRangeType'], function() {
            plotRangeService.processPlotRange(self, m);
        });
    });

    self.simState = persistentSimulation.initSimulationState(self);

    self.simState.runningMessage = function() {
        if (self.hasParticles) {
            return '';
        }
        return 'Simulation running';
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
            <div data-import-dialog=""></div>
        `,
    };
});

SIREPO.app.directive('appHeader', function() {
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'visualization\')}"><a href data-ng-click="nav.openSection(\'visualization\')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>
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
    };
});

SIREPO.app.directive('rateCalculationPanel', function(appState, plotting) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div data-ng-if="! rates">
              <div class="lead">&nbsp;</div>
            </div>
            <div data-ng-if="rates">
              <div class="col-sm-12" style="margin-top: 1ex;">
                <table class="table">
                  <thead>
                  <tr>
                    <th>&nbsp;</th>
                    <th class="text-right">Horizontal</th>
                    <th class="text-right">Vertical</th>
                    <th class="text-right">Longitudinal</th>
                  </tr>
                  </thead>
                  <tr data-ng-repeat="rate in rates">
                    <td><label>{{ rate[0] }}</label></td>
                    <td data-ng-repeat="value in rate[1] track by $index" class="text-right">{{ value }}</td>
                  </tr>
                </table>
              </div>
            </div>
        `,
        controller: function($scope) {
            plotting.setTextOnlyReport($scope);
            $scope.load = function(json) {
                $scope.rates = json.rate;
            };
        },
        link: function link(scope, element) {
            scope.modelName = 'rateCalculationReport';
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('twissFileField', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            model: '=',
            modelName: '=',
        },
        template: `
            <div data-file-field="field" data-model="model" data-model-name="modelName" data-selection-required="true">
              <button type="button" title="View Twiss Parameters" class="btn btn-default" data-ng-click="showFileReport()"><span class="glyphicon glyphicon-eye-open"></span></button>
            </div>
        `,
        controller: function($scope) {
            $scope.showFileReport = function() {
                appState.saveChanges('ring');
                var source = panelState.findParentAttribute($scope, 'source');
                var el = $('#jspec-twiss-plot');
                el.modal('show');
                el.on('shown.bs.modal', function() {
                    // this forces the plot to reload
                    source.twissReportShown = true;
                    $scope.$apply();
                });
                el.on('hidden.bs.modal', function() {
                    source.twissReportShown = false;
                    el.off();
                });
            };
        },
    };
});
