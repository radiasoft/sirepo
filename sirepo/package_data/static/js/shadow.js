'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="ReflectivityMaterial" data-ng-class="fieldClass">',
          '<input data-reflectivity-material="" data-ng-model="model[field]" class="form-control" required />',
        '</div>',
    ].join('');
    SIREPO.appDownloadLinks = `
        <li data-download-csv-link=""></li>
        <li data-export-python-link="" data-report-title="{{ reportTitle() }}"></li>'
    `;
});

SIREPO.app.factory('shadowService', function(appState, beamlineService, panelState, requestSender) {
    var self = {};
    self.getReportTitle = beamlineService.getReportTitle;

    function updateAutoTuningFields(item) {
        var modelName = item.type;
        panelState.showFields(modelName, [
            ['t_incidence', 't_reflection'], modelName == 'grating' || item.f_central == '0',
            'f_phot_cent', item.f_central == '1',
            'phot_cent', item.f_central == '1' && item.f_phot_cent == '0',
            'r_lambda', item.f_central == '1' && item.f_phot_cent == '1',
        ]);
    }

    function updateElementDimensionFields(item) {
        panelState.showFields(item.type, [
            'fshape', item.fhit_c == '1',
            [
                'halfWidthX1', 'halfWidthX2', 'halfLengthY1',
                'halfLengthY2',
            ], item.fhit_c == '1' && item.fshape == '1',
            [
                'externalOutlineMajorAxis', 'externalOutlineMinorAxis',
            ], item.fhit_c == '1' && (item.fshape == '2' || item.fshape == '3'),
            [
                'internalOutlineMajorAxis', 'internalOutlineMinorAxis',
            ], item.fhit_c == '1' && item.fshape == '3',
        ]);
    }

    function updateElementShapeFields(item) {
        panelState.showTab(
            item.type, 2,
            item.fmirr == '1' || item.fmirr == '2' || item.fmirr == '3'
                || item.fmirr == '4' || item.fmirr == '7');
    }

    function updateElementSurfaceFields(item) {
        panelState.showFields(item.type, [
            'f_default', item.f_ext == '0',
            'f_side', item.f_ext == '0' && item.fmirr == '4',
            'rmirr', item.f_ext == '1' && item.fmirr == '1',
            [
                'axmaj', 'axmin', 'ell_the',
            ], item.f_ext == '1' && (item.fmirr == '2' || item.fmirr == '7'),
            ['r_maj', 'r_min'], item.f_ext == '1' && item.fmirr == '3',
            'param', item.f_ext == '1' && item.fmirr == '4',
            ['ssour', 'simag', 'theta'], item.f_ext == '0' && item.f_default == '0',
            [
                'f_convex', 'fcyl',
            ], item.fmirr == '1' || item.fmirr == '2' || item.fmirr == '4'
                || item.fmirr == '7',
            'cil_ang', item.fcyl == '1'
                && (item.fmirr == '1' || item.fmirr == '2' || item.fmirr == '4'
                    || item.fmirr == '7'),
            'f_torus', item.fmirr == '3',
        ]);
    }

    self.computeModel = function(analysisModel) {
        return 'animation';
    };

    self.sendStatelessCompute = function(method, appState, callback, args) {
        requestSender.sendStatelessCompute(appState, callback,
            {
                method: method,
                args: args,
            }
        );
    };

    self.initAutoTuneView = function(scope, watchFields, callback) {
        self.initGeometryView(scope, watchFields, callback);
        var chain = scope.whenSelected;
        scope.whenSelected = function(item) {
            chain(item);
            updateAutoTuningFields(item);
        };
        scope.watchFields.push(['f_central', 'f_phot_cent'], updateAutoTuningFields);
    };

    self.initGeometryView = function(scope, watchFields, callback) {
        scope.whenSelected = function(item) {
            updateElementShapeFields(item);
            updateElementDimensionFields(item);
            updateElementSurfaceFields(item);
            callback(item);
        };
        scope.watchFields = [
            ['fmirr'], updateElementShapeFields,
            ['fhit_c', 'fshape'], updateElementDimensionFields,
            ['f_ext', 'f_default', 'fcyl'], updateElementSurfaceFields,
            watchFields, callback,
        ];
    };

    self.updateRayFilterFields = function() {
        var hasFilter = appState.models.rayFilter.f_bound_sour == '2';
        panelState.showField('rayFilter', 'distance', hasFilter);
        panelState.showRow('rayFilter', 'x1', hasFilter);
    };

    appState.setAppService(self);

    return self;
});

SIREPO.app.controller('BeamlineController', function (appState, beamlineService) {
    var self = this;
    self.appState = appState;
    self.beamlineService = beamlineService;
    self.beamlineModels = ['beamline'];
    //TODO(pjm): also KB Mirror and  Monocromator
    self.toolbarItemNames = ['aperture', 'obstacle', 'emptyElement', 'crystal', 'grating', 'lens', 'crl', 'mirror', 'watch', 'zonePlate'];
    self.prepareToSave = function() {};
    self.showBeamStatisticsReport = () => {
        return ['bendingMagnet', 'geometricSource', 'undulator'].indexOf(
            appState.models.simulation.sourceType) >= 0
            && appState.applicationState().beamline.length;
    };
});

SIREPO.app.controller('SourceController', function(appState, shadowService) {
    var self = this;
    self.appState = appState;
    self.shadowService = shadowService;
    self.isSource = function(name) {
        return appState.isLoaded() && appState.models.simulation.sourceType == name;
    };
});

SIREPO.beamlineItemLogic('crlView', function(panelState, $scope) {

    function updateCrlFields(item) {
        panelState.showFields('crl', [
            'lensDiameter', item.fhit_c == '1',
            'cil_ang', item.fcyl == '1' && item.fmirr != '5',
            [
                'rmirr', 'fcyl', 'useCCC',
                'initialCurvature',
            ], item.fmirr != '5',
        ]);
    }

    $scope.whenSelected = updateCrlFields;
    $scope.watchFields = [
        ['fhit_c', 'fmirr', 'fcyl'], updateCrlFields,
    ];
});

SIREPO.beamlineItemLogic('crystalView', function(panelState, shadowService, $scope) {

    function updateCrystalFields(item) {
        panelState.showFields(item.type, [
            ['mosaic_seed', 'spread_mos'], item.f_mosaic == '1',
            'thickness', item.f_mosaic == '1' || (item.f_mosaic == '0' && item.f_bragg_a == '1'),
            ['f_bragg_a', 'f_johansson'], item.f_mosaic == '0',
            'a_bragg', item.f_mosaic == '0' && item.f_bragg_a == '1',
            'order', item.f_mosaic == '0' && item.f_bragg_a == '1' && item.f_refrac == '1',
            'r_johansson', item.f_mosaic == '0' && item.f_johansson == '1',
        ]);
    }

    shadowService.initAutoTuneView(
        $scope,
        ['f_refrac', 'f_mosaic', 'f_bragg_a', 'f_johansson'],
        updateCrystalFields);
});

SIREPO.beamlineItemLogic('gratingView', function(panelState, shadowService, $scope) {

    function updateGratingFields(item) {
        panelState.showField('grating', 'rulingDensity', item.f_ruling == '0' || item.f_ruling == '1');
        panelState.showRow('grating', 'holo_r1', item.f_ruling == '2');
        ['holo_w', 'f_pw', 'f_pw_c', 'f_virtual'].forEach(function(f) {
            panelState.showField('grating', f, item.f_ruling == '2');
        });
        ['rulingDensityCenter', 'azim_fan', 'dist_fan', 'coma_fac'].forEach(function(f) {
            panelState.showField('grating', f, item.f_ruling == '3');
        });
        ['f_rul_abs', 'rulingDensityPolynomial', 'rul_a1', 'rul_a2', 'rul_a3', 'rul_a4'].forEach(function(f) {
            panelState.showField('grating', f, item.f_ruling == '5');
        });
        panelState.showField('grating', 'f_mono', item.f_central == '1');
        ['f_hunt', 'hunt_h', 'hunt_l', 'blaze'].forEach(function(f) {
            panelState.showField('grating', f, item.f_central == '1' && item.f_mono == '4');
        });
    }

    shadowService.initAutoTuneView(
        $scope,
        ['f_ruling', 'f_mono'],
        updateGratingFields);
});

SIREPO.beamlineItemLogic('mirrorView', function(panelState, shadowService, $scope) {

    function updateMirrorReflectivityFields(item) {
        panelState.showFields(item.type, [
            [
                'f_refl', 'reflectivityMinEnergy', 'reflectivityMaxEnergy',
            ], item.f_reflec == '1' || item.f_reflec == '2',
            [
                'prereflElement', 'prereflDensity', 'prereflStep',
            ], (item.f_reflec == '1' || item.f_reflec == '2') && item.f_refl == '0',
            [
                'f_thick', 'mlayerMinEnergy', 'mlayerMaxEnergy',
                'mlayerBilayerNumber', 'mlayerBilayerThickness', 'mlayerGammaRatio',
                'mlayerEvenRoughness', 'mlayerOddRoughness',
            ], (item.f_reflec == '1' || item.f_reflec == '2') && item.f_refl == '2',
        ]);
        panelState.showRow(
            item.type,
            'mlayerSubstrateMaterial',
            (item.f_reflec == '1' || item.f_reflec == '2') && item.f_refl == '2');
    }

    shadowService.initGeometryView(
        $scope,
        ['f_reflec', 'f_refl'],
        updateMirrorReflectivityFields);
});

var shadowPlotLogic = function(appState, panelState, shadowService, $scope) {
    // ColumnValue enum values which are in mm
    var MM_COLUMN_VALUES = ['1', '2', '3'];

    function updatePlotSizeFields() {
        var modelKey = $scope.modelData ? $scope.modelData.modelKey : $scope.modelName;
        var m = appState.models[modelKey];
        var showOverride = MM_COLUMN_VALUES.indexOf(m.x) >= 0 && MM_COLUMN_VALUES.indexOf(m.y) >= 0;
        panelState.showField($scope.modelName, 'overrideSize', showOverride);
        if (! showOverride) {
            m.overrideSize = '0';
        }
        panelState.showRow($scope.modelName, 'horizontalSize', m.overrideSize === '1');
    }

    $scope.whenSelected = updatePlotSizeFields;

    var name = $scope.modelData ? $scope.modelData.modelKey : $scope.modelName;
    $scope.watchFields = [
        [name + '.overrideSize', name + '.x', name + '.y'], updatePlotSizeFields,
    ];
};

[
    'plotXYReportView', 'initialIntensityReportView',
    'watchpointReportView',
].forEach(function(view) {
    SIREPO.viewLogic(view, shadowPlotLogic);
});

SIREPO.viewLogic('undulatorView', function(appState, panelState, shadowService, $scope) {

    function computeHarmonicPhotonEnergy() {
        if (appState.models.undulator.select_energy != 'harmonic') {
            return;
        }
        shadowService.sendStatelessCompute(
            'harmonic_photon_energy',
            appState,
            function(data) {
                if (appState.isLoaded()) {
                    var und = appState.models.undulator;
                    und.photon_energy = data.photon_energy.toFixed(2);
                    und.maxangle = data.maxangle.toFixed(4);
                }
            },
            {
                undulator: appState.models.undulator,
                undulatorBeam: appState.models.undulatorBeam,
            }
        );
    }

    function updateUndulatorFields() {
        var und = appState.models.undulator;
        panelState.enableFields('undulator', [
            ['photon_energy', 'maxangle'],  und.select_energy != 'harmonic',
        ]);
        panelState.showFields('undulator', [
            ['emin', 'emax', 'ng_e'], und.select_energy == 'range',
            'energy_harmonic', und.select_energy == 'harmonic',
            'photon_energy', und.select_energy == 'harmonic' || und.select_energy == 'single',
        ]);
    }

    $scope.whenSelected = function() {
        updateUndulatorFields();
        computeHarmonicPhotonEnergy();
    };

    $scope.watchFields = [
        ['undulator.select_energy'], updateUndulatorFields,
        [
            'undulator.energy_harmonic', 'undulator.k_horizontal',
            'undulator.k_vertical', 'undulator.period',
            'undulator.length', 'undulatorBeam.energy',
        ], computeHarmonicPhotonEnergy,
    ];
});

SIREPO.viewLogic('wigglerView', function(appState, panelState, shadowService, $scope) {

    function updateWigglerSettings() {
        var wiggler = appState.models.wiggler;
        panelState.showFields('wiggler', [
            'kValue', wiggler.b_from == '0',
            'trajFile', wiggler.b_from == '1' || wiggler.b_from == '2',
            'per', wiggler.b_from == '0' || wiggler.b_from == '2',
            'shift_x_value', wiggler.shift_x_flag == '5',
            'shift_betax_value', wiggler.shift_betax_flag == '5',
        ]);
    }

    $scope.whenSelected = function() {
        updateWigglerSettings();
        shadowService.updateRayFilterFields();
    };

    $scope.watchFields = [
        ['rayFilter.f_bound_sour'], shadowService.updateRayFilterFields,
        ['wiggler.b_from', 'wiggler.shift_x_flag', 'wiggler.shift_betax_flag'], updateWigglerSettings,
    ];
});

SIREPO.viewLogic('bendingMagnetView', function(appState, panelState, shadowService, $scope) {

    function computeFieldRadius() {
        let bm = appState.models.bendingMagnet;
        let isRadius = bm.calculateFieldMethod == 'radius';
        const c = 299792458;
        const e = 1e9 / c * appState.models.electronBeam.bener;
        if (isRadius) {
            if (bm.r_magnet) {
                bm.magneticField = e / bm.r_magnet;
            }
        }
        else if (bm.magneticField) {
            bm.r_magnet = e / bm.magneticField;
        }
        panelState.enableFields('bendingMagnet', [
            'r_magnet', isRadius,
            'magneticField', ! isRadius,
        ]);
    }

    $scope.whenSelected = () => {
        shadowService.updateRayFilterFields();
        computeFieldRadius();
    };
    $scope.watchFields = [
        ['rayFilter.f_bound_sour'], shadowService.updateRayFilterFields,
        [
            'bendingMagnet.calculateFieldMethod',
            'bendingMagnet.r_magnet',
            'bendingMagnet.magneticField',
        ], computeFieldRadius,
    ];
});

SIREPO.viewLogic('geometricSourceView', function(appState, panelState, shadowService, $scope) {

    function updateGeometricSettings() {
        var geo = appState.models.geometricSource;
        panelState.showFields('geometricSource', [
            ['wxsou', 'wzsou'], geo.fsour == '1' || geo.fsour == '2',
            ['sigmax', 'sigmaz'], geo.fsour == '3',
            ['sigdix', 'sigdiz'], geo.fdistr == '3',
            ['cone_max', 'cone_min'], geo.fdistr == '5',
            'wysou', geo.fsource_depth == '2',
            'sigmay', geo.fsource_depth == '3',
            'singleEnergyValue', geo.f_color == '1',
            ['ph1', 'ph2'], geo.f_color == '3',
            ['f_coher', 'pol_angle', 'pol_deg'], geo.f_polar == '1',
        ]);
        panelState.showFields('sourceDivergence', [
            ['hdiv1', 'hdiv2', 'vdiv1', 'vdiv2'], geo.fdistr == '1' || geo.fdistr == '2' || geo.fdistr == '3',
        ]);
    }

    $scope.whenSelected = function() {
        updateGeometricSettings();
        shadowService.updateRayFilterFields();
    };
    $scope.watchFields = [
        ['rayFilter.f_bound_sour'], shadowService.updateRayFilterFields,
        [
            'simulation.sourceType', 'geometricSource.fsour',
            'geometricSource.fdistr', 'geometricSource.fsource_depth',
            'geometricSource.f_color', 'geometricSource.f_polar',
        ], updateGeometricSettings,
    ];
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
            <div data-sim-conversion-modal="" data-conv-method="convert_to_srw"></div>
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
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'beamline\')}"><a href data-ng-click="nav.openSection(\'beamline\')"><span class="glyphicon glyphicon-option-horizontal"></span> Beamline</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
                <div><a href data-ng-click="openSRWConfirm()"><span class="glyphicon glyphicon-upload"></span> Open as a New SRW Simulation</a></div>
              </app-settings>
              <app-header-right-sim-list>
                <ul class="nav navbar-nav sr-navbar-right">
                  <li><a href data-ng-click="nav.showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>
                </ul>
              </app-header-right-sim-list>
            </div>
        `,
        controller: function($scope) {
            $scope.openSRWConfirm = function() {
                $('#sr-conv-dialog').modal('show');
            };
        }
    };
});


SIREPO.app.directive('reflectivityMaterial', function() {
    return {
        restrict: 'A',
        require: 'ngModel',
        link: function(scope, element, attrs, ngModel) {
            ngModel.$parsers.push(function(value) {
                if (ngModel.$isEmpty(value)) {
                    return null;
                }
                var isValid = true;
                if (! /^[A-Za-z0-9().]+$/.test(value)) {
                    isValid = false;
                }
                else if (/^[a-z0-9]/.test(value)) {
                    isValid = false;
                }
                else if (/[0-9][a-z]/.test(value)) {
                    isValid = false;
                }
                ngModel.$setValidity('', isValid);
                return value;
            });
        }
    };
});
