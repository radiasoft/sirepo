'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.SINGLE_FRAME_ANIMATION = [
        'bunchAnimation1',
        'bunchAnimation2',
        'bunchAnimation3',
    ];
    SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
    SIREPO.lattice = {
        canReverseBeamline: true,
        elementColor: {
            OCTUPOLE: 'yellow',
            QUADRUPOLE: 'red',
            SEXTUPOLE: 'lightgreen',
        },
        elementPic: {
            aperture: ['APERTURE'],
            bend: ['SBEND'],
            drift: ['DRIFT'],
            magnet: ['KICKER', 'MULTIPOLE', 'QUADRUPOLE', 'SEXTUPOLE'],
            rf: ['RFCAVITY'],
            solenoid: ['SOLENOID'],
            watch: ['MONITOR'],
            zeroLength: [],
        },
    };
    SIREPO.FILE_UPLOAD_TYPE = {
        'distribution.distributionFile': '.h5',
    };
    SIREPO.appFieldEditors = `
        <div data-ng-switch-when="FrameSlider" class="col-sm-12">
          <div data-frame-slider="" data-model="model" data-field="field"></div>
        </div>
    `;
});

SIREPO.app.factory('canvasService', function(appState, requestSender) {
    const self = {};
    let codeLabels = null;
    appState.setAppService(self);
    self.computeModel = analysisModel => 'animation';
    self.BUNCH_ANIMATIONS = ['bunchAnimation1', 'bunchAnimation2', 'bunchAnimation3'];

    const updateCodeLabels = () => {
        const m = SIREPO.APP_SCHEMA.model.simulationSettings;
        for (const c of SIREPO.APP_SCHEMA.constants.codes) {
            // update the schema simulationSettings labels
            m[c][0] = codeLabels[c];
        }
    };

    self.updateCodeVersions = (scope) => {
        if (codeLabels) {
            updateCodeLabels();
            return;
        }
        requestSender.sendStatelessCompute(
            appState,
            function(data) {
                if (data.elegant) {
                    codeLabels = data;
                    updateCodeLabels();
                }
            },
            {
                method: 'code_versions',
            },
        );
    };
    return self;
});

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
            <div data-elegant-import-dialog="" data-is-mad-x-only="1"></div>
        `,
    };
});

SIREPO.app.directive('appHeader', function(canvasService) {
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('lattice')}"><a href data-ng-click="nav.openSection('lattice')"><span class="glyphicon glyphicon-option-horizontal"></span>  Lattice</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('source')}"><a href data-ng-click="nav.openSection('source')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('comparison')}"><a href data-ng-click="nav.openSection('comparison')">Comparison</a></li>
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

SIREPO.app.controller('LatticeController', function(latticeService) {
    var self = this;
    self.latticeService = latticeService;
    self.advancedNames = [];
    self.basicNames = [
        "APERTURE",
        "DRIFT",
        "KICKER",
        "MONITOR",
        "MULTIPOLE",
        "QUADRUPOLE",
        "RFCAVITY",
        "SBEND",
        "SEXTUPOLE",
        "SOLENOID"
    ];
});

SIREPO.app.controller('SourceController', function(latticeService) {
    const self = this;
    latticeService.initSourceController(self);
});

SIREPO.app.controller('ComparisonController', function(canvasService, frameCache, persistentSimulation, $scope) {
    var self = this;
    self.simScope = $scope;
    self.errorMessage = '';

    self.startSimulation = function() {
        self.simState.saveAndRunSimulation(['simulation', 'simulationSettings']);
    };

    self.simHandleStatus = (data) => {
        self.errorMessage = data.error;
        frameCache.setFrameCount(data.frameCount || 0);
        for (const m of canvasService.BUNCH_ANIMATIONS) {
            frameCache.setFrameCount(data.bunchAnimationFrameCount || 0, m);
        }
    };

    self.simState = persistentSimulation.initSimulationState(self);
    self.simState.errorMessage = () => self.errorMessage;

    canvasService.updateCodeVersions($scope);

});

SIREPO.app.directive('phaseSpacePlots', function() {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div class="col-sm-12">
              <div data-simple-panel="bunchAnimation" data-is-report="1">
                <div class="col-sm-6">
                  <div data-field-editor="'selectedFrame'" data-model-name="'bunchAnimation'"
                    data-model="appState.models.bunchAnimation"></div>
                </div>
                <div class="col-sm-6">
                  <div class="pull-right">
                    <div data-ng-repeat="(b, v) in views track by $index"
                      style="display: inline-block; margin-right: 1ex">
                      <button type="button" class="btn btn-default" data-ng-class="{ 'btn-primary': isSelected(v) }"
                        data-ng-click="selectView(v)">{{ b }}</button>
                    </div>
                  </div>
                </div>
                <div class="clearfix"></div>
                <div class="row sr-screenshot">
                  <div class="col-md-4" data-ng-repeat="r in reports track by $index">
                    <div data-ng-if="isHeatmap(r)" data-heatmap="" data-model-name="{{ r }}"></div>
                    <div data-ng-if="! isHeatmap(r)" data-plot3d="" data-model-name="{{ r }}"></div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function(appState, canvasService, $scope) {
            $scope.appState = appState;
            $scope.views = {
                Horizontal: 'x-px',
                Vertical: 'y-py',
                'Cross-section': 'x-y',
                Longitudinal: 't-pt',
            };
            $scope.reports = canvasService.BUNCH_ANIMATIONS;

            $scope.isHeatmap = (report) => {
                return appState.models[report].plotType == 'heatmap';
            };

            $scope.isSelected = (xy) => {
                const b = appState.models.bunchAnimation;
                return [b.x, b.y].join('-') === xy;
            };

            $scope.selectView = (xy) => {
                const [x, y] = xy.split('-');
                const b = appState.models.bunchAnimation;
                b.x = x;
                b.y = y;
                appState.saveChanges('bunchAnimation');
            };

            $scope.$on('bunchAnimation.changed', (e) => {
                const b = appState.models.bunchAnimation;
                const updated = {};
                for (const r of $scope.reports) {
                    const m = appState.models[r];
                    for (const f of ['x', 'y', 'histogramBins', 'colorMap', 'plotType']) {
                        if (b[f] !== m[f]) {
                            m[f] = b[f];
                            updated[r] = true;
                        }
                    }
                }
                appState.saveChanges(Object.keys(updated));
            });
        },
    };
});

SIREPO.app.directive('frameSlider', function(appState, canvasService, frameCache, utilities) {
    return {
        restrict: 'A',
        scope: {
            field: '<',
            model: '=',
        },
        template: `
          <div data-ng-if="steps">
            <div data-slider="" data-model="model" data-field="field" data-min="min" data-max="max" data-steps="steps"></div>
          </div>
        `,
        controller: function($scope) {
            function setFrame() {
                const v = $scope.model[$scope.field];
                for (const m of canvasService.BUNCH_ANIMATIONS) {
                    frameCache.setCurrentFrame(m, v);
                    appState.models[m].frameIndex = v;
                }
                appState.saveChanges(canvasService.BUNCH_ANIMATIONS);
            }

            function updateRange() {
                if (frameCache.getFrameCount(canvasService.BUNCH_ANIMATIONS[0])) {
                    const c = frameCache.getFrameCount(canvasService.BUNCH_ANIMATIONS[0]);
                    $scope.model[$scope.field] = c - 1;
                    $scope.min = 0;
                    $scope.max = c - 1;
                    $scope.steps = c;
                }
                else {
                    $scope.steps = 0;
                }
            }

            $scope.$watch('model[field]', utilities.debounce(setFrame));
            $scope.$on('framesLoaded', updateRange);

            updateRange();
        },
    };
});
