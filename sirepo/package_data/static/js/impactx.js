'use strict';

SIREPO.app.config(function() {
    SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
    SIREPO.appFieldEditors += ``;
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="FloatArray" class="col-sm-7">
          <input data-ng-model="model[field]" class="form-control" data-lpignore="true" required />
        </div>
    `;
    SIREPO.lattice = {
        elementColor: {
        },
        elementPic: {
            aperture: ['APERTURE'],
            bend: ['CFBEND', 'DIPEDGE', 'EXACTSBEND', 'SBEND', 'THINDIPOLE'],
            drift: ['CHRDRIFT', 'DRIFT', 'EXACTDRIFT'],
            lens: ['CHRPLASMALENS', 'NONLINEARLENS', 'TAPEREDPL'],
            magnet: ['CHRQUAD', 'CONSTF', 'KICKER', 'MULTIPOLE', 'QUAD', 'SOFTQUADRUPOLE'],
            rf: ['BUNCHER', 'CHRACC', 'RFCAVITY', 'SHORTRF'],
            solenoid: ['SOFTSOLENOID', 'SOL'],
            watch: ['BEAMMONITOR'],
            zeroLength: ['PROT'],
        },
    };
});

SIREPO.app.factory('impactxService', function(appState) {
    const self = {};

    self.computeModel = () => 'animation';

    appState.setAppService(self);
    return self;
});


SIREPO.app.controller('SourceController', function(latticeService) {
    const self = this;
    latticeService.initSourceController(self);
});

SIREPO.app.controller('VisualizationController', function (appState, frameCache, impactxService, panelState, persistentSimulation, $scope) {
    const self = this;
    self.simScope = $scope;
    self.errorMessage = '';

    self.simHandleStatus = (data) => {
    };
    self.simState = persistentSimulation.initSimulationState(self);
});

SIREPO.app.controller('LatticeController', function(appState, latticeService, $scope) {
    const self = this;
    self.latticeService = latticeService;

    self.advancedNames = SIREPO.APP_SCHEMA.constants.advancedElementNames;
    self.basicNames = SIREPO.APP_SCHEMA.constants.basicElementNames;

    const updateAllElements = () => {
        appState.models.elements.map(updateElementAttributes);
        appState.saveQuietly(['elements']);
    };

    const updateElementAttributes = (element) => {
        if (element.type == 'DIPEDGE') {
            element.angle = element.psi;
        }
        else if (element.type == 'EXACTSBEND') {
            element.angle = 'pi * ' + element.phi + ' / 180';
        }
    };

    const init = () => {
        //TODO(pjm): only run the first time
        updateAllElements();

        $scope.$on('modelChanged', function(e, name) {
            const m = appState.models[name];
            if (m.type) {
                updateElementAttributes(m);
            }
            else if (name == 'rpnVariables') {
                updateAllElements();
            }
        });
    };

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[name].description;
    };

    init();
});

SIREPO.app.directive('appFooter', function(impactxService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive('lattice')}"><a href data-ng-click="nav.openSection('lattice')"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('source')}"><a href data-ng-click="nav.openSection('source')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('visualization')}"><a href data-ng-click="nav.openSection('visualization')"><span class="glyphicon glyphicon-flash"></span> Visualization</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
              </app-settings>
              <app-header-right-sim-list>
              </app-header-right-sim-list>
            </div>
        `,
    };
});
