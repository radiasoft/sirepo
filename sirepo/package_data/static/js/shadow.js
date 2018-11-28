'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
SIREPO.PLOTTING_SHOW_FWHM = true;
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="ReflectivityMaterial" data-ng-class="fieldClass">',
      '<input data-reflectivity-material="" data-ng-model="model[field]" class="form-control" required />',
    '</div>',
].join('');
SIREPO.appDownloadLinks = [
    '<li data-lineout-csv-link="x"></li>',
    '<li data-lineout-csv-link="y"></li>',
].join('');

SIREPO.app.factory('shadowService', function(appState, beamlineService, panelState) {
    // ColumnValue enum values which are in mm
    var MM_COLUMN_VALUES = ['1', '2', '3'];
    var self = {};
    self.getReportTitle = beamlineService.getReportTitle;

    self.updatePlotSizeFields = function(modelKey, modelName) {
        var m = appState.models[modelKey];
        var showOverride = MM_COLUMN_VALUES.indexOf(m.x) >= 0 && MM_COLUMN_VALUES.indexOf(m.y) >= 0;
        panelState.showField(modelName || modelKey, 'overrideSize', showOverride);
        if (! showOverride) {
            m.overrideSize = '0';
        }
        panelState.showRow(modelName || modelKey, 'horizontalSize', m.overrideSize === '1');
    };

    self.watchPlotSize = function($scope, modelKey, modelName) {
        appState.watchModelFields($scope, [modelKey + '.overrideSize', modelKey + '.x', modelKey + '.y'], function() {
            self.updatePlotSizeFields(modelKey, modelName);
        });
    };
    return self;
});

SIREPO.app.controller('ShadowBeamlineController', function (appState, beamlineService, panelState, shadowService, $scope) {
    var self = this;
    var watchpointNames = [];
    self.beamlineService = beamlineService;
    self.beamlineModels = ['beamline'];
    //TODO(pjm): also KB Mirror and  Monocromator
    //self.toolbarItemNames = ['aperture', 'obstacle', 'crystal', 'grating', 'lens', 'crl', 'mirror', 'watch'];
    self.toolbarItemNames = ['aperture', 'obstacle', 'crystal', 'grating', 'crl', 'mirror', 'watch'];
    self.prepareToSave = function() {};

    function updateAutoTuningFields(item) {
        var modelName = item.type;
        ['t_incidence', 't_reflection'].forEach(function(f) {
            panelState.showField(modelName, f, modelName == 'grating' || item.f_central == '0');
        });
        panelState.showField(modelName, 'f_phot_cent', item.f_central == '1');
        panelState.showField(modelName, 'phot_cent', item.f_central == '1' && item.f_phot_cent == '0');
        panelState.showField(modelName, 'r_lambda', item.f_central == '1' && item.f_phot_cent == '1');
    }

    function updateCrlFields(item) {
        var modelName = item.type;
        panelState.showField(modelName, 'lensDiameter', item.fhit_c == '1');
        ['rmirr', 'fcyl', 'useCCC', 'initialCurvature'].forEach(function(f) {
            panelState.showField(modelName, f, item.fmirr != '5');
        });
        panelState.showField(modelName, 'cil_ang', item.fcyl == '1' && item.fmirr != '5');
    }

    function updateCrystalFields(item) {
        ['mosaic_seed', 'spread_mos'].forEach(function(f) {
            panelState.showField('crystal', f, item.f_mosaic == '1');
        });
        panelState.showField('crystal', 'thickness', item.f_mosaic == '1' || (item.f_mosaic == '0' && item.f_bragg_a == '1'));
        ['f_bragg_a', 'f_johansson'].forEach(function(f) {
            panelState.showField('crystal', f, item.f_mosaic == '0');
        });
        panelState.showField('crystal', 'a_bragg', item.f_mosaic == '0' && item.f_bragg_a == '1');
        panelState.showField('crystal', 'order', item.f_mosaic == '0' && item.f_bragg_a == '1' && item.f_refrac == '1');
        panelState.showField('crystal', 'r_johansson', item.f_mosaic == '0' && item.f_johansson == '1');
    }

    function updateElementDimensionFields(item) {
        var modelName = item.type;
        panelState.showField(modelName, 'fshape', item.fhit_c == '1');
        ['halfWidthX1', 'halfWidthX2', 'halfLengthY1', 'halfLengthY2'].forEach(function(f) {
            panelState.showField(modelName, f, item.fhit_c == '1' && item.fshape == '1');
        });
        ['externalOutlineMajorAxis', 'externalOutlineMinorAxis'].forEach(function(f) {
            panelState.showField(modelName, f, item.fhit_c == '1' && (item.fshape == '2' || item.fshape == '3'));
        });
        ['internalOutlineMajorAxis', 'internalOutlineMinorAxis'].forEach(function(f) {
            panelState.showField(modelName, f, item.fhit_c == '1' && item.fshape == '3');
        });
    }

    function updateElementSurfaceFields(item) {
        var modelName = item.type;
        panelState.showField(modelName, 'f_default', item.f_ext == '0');
        panelState.showField(modelName, 'f_side', item.f_ext == '0' && item.fmirr == '4');
        panelState.showField(modelName, 'rmirr', item.f_ext == '1' && item.fmirr == '1');
        ['axmaj', 'axmin', 'ell_the'].forEach(function(f) {
            panelState.showField(modelName, f, item.f_ext == '1' && (item.fmirr == '2' || item.fmirr == '7'));
        });
        ['r_maj', 'r_min'].forEach(function(f) {
            panelState.showField(modelName, f, item.f_ext == '1' && item.fmirr == '3');
        });
        panelState.showField(modelName, 'param', item.f_ext == '1' && item.fmirr == '4');
        ['ssour', 'simag', 'theta'].forEach(function(f) {
            panelState.showField(modelName, f, item.f_ext == '0' && item.f_default == '0');
        });
        ['f_convex', 'fcyl'].forEach(function(f) {
            panelState.showField(modelName, f, item.fmirr == '1' || item.fmirr == '2' || item.fmirr == '4' || item.fmirr == '7');
        });
        panelState.showField(modelName, 'cil_ang', item.fcyl == '1' && (item.fmirr == '1' || item.fmirr == '2' || item.fmirr == '4' || item.fmirr == '7'));
        panelState.showField(modelName, 'f_torus', item.fmirr == '3');
    }

    function updateElementShapeFields(item) {
        var modelName = item.type;
        panelState.showTab(modelName, 2, item.fmirr == '1' || item.fmirr == '2' || item.fmirr == '3' || item.fmirr == '4' || item.fmirr == '7');
    }

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

    function updateMirrorReflectivityFields(item) {
        ['f_refl', 'reflectivityMinEnergy', 'reflectivityMaxEnergy'].forEach(function(f) {
            panelState.showField('mirror', f, item.f_reflec == '1' || item.f_reflec == '2');
        });
        ['prereflElement', 'prereflDensity', 'prereflStep'].forEach(function(f) {
            panelState.showField('mirror', f, (item.f_reflec == '1' || item.f_reflec == '2') && item.f_refl == '0');
        });
        ['f_thick', 'mlayerMinEnergy', 'mlayerMaxEnergy', 'mlayerBilayerNumber', 'mlayerBilayerThickness', 'mlayerGammaRatio', 'mlayerEvenRoughness', 'mlayerOddRoughness'].forEach(function(f) {
            panelState.showField('mirror', f, (item.f_reflec == '1' || item.f_reflec == '2') && item.f_refl == '2');
        });
        panelState.showRow('mirror', 'mlayerSubstrateMaterial', (item.f_reflec == '1' || item.f_reflec == '2') && item.f_refl == '2');
    }

    self.handleModalShown = function(name, modelKey) {
        var item = beamlineService.activeItem;
        if (item && item.type == name) {
            if (name == 'mirror' || name == 'crystal' || name == 'grating') {
                updateElementShapeFields(item);
                updateElementDimensionFields(item);
                updateElementSurfaceFields(item);
            }
            if (name == 'crystal' || name == 'grating') {
                updateAutoTuningFields(item);
            }
            if (name == 'mirror') {
                updateMirrorReflectivityFields(item);
            }
            else if (name == 'crystal') {
                updateCrystalFields(item);
            }
            else if (name == 'grating') {
                updateGratingFields(item);
            }
            else if (name == 'crl') {
                updateCrlFields(item);
            }
        }
        if (name == 'initialIntensityReport') {
            shadowService.updatePlotSizeFields(name);
        }
        else if (modelKey && beamlineService.isWatchpointReportModelName(modelKey)) {
            shadowService.updatePlotSizeFields(modelKey, 'watchpointReport');
            if (watchpointNames.indexOf(modelKey) < 0) {
                watchpointNames.push(modelKey);
                shadowService.watchPlotSize($scope, modelKey, 'watchpointReport');
            }
        }
    };

    appState.whenModelsLoaded($scope, function() {
        ['mirror', 'crystal', 'grating'].forEach(function(m) {
            beamlineService.watchBeamlineField($scope, m, ['fmirr'], updateElementShapeFields);
            beamlineService.watchBeamlineField($scope, m, ['f_ext', 'f_default', 'fcyl'], updateElementSurfaceFields);
            beamlineService.watchBeamlineField($scope, m, ['fhit_c', 'fshape'], updateElementDimensionFields);
        });
        ['crystal', 'grating'].forEach(function(m) {
            beamlineService.watchBeamlineField($scope, m, ['f_central', 'f_phot_cent'], updateAutoTuningFields);
        });
        beamlineService.watchBeamlineField($scope, 'mirror', ['f_reflec', 'f_refl'], updateMirrorReflectivityFields);
        beamlineService.watchBeamlineField($scope, 'crystal', ['f_refrac', 'f_mosaic', 'f_bragg_a', 'f_johansson'], updateCrystalFields);
        beamlineService.watchBeamlineField($scope, 'grating', ['f_ruling', 'f_mono'], updateGratingFields);
        beamlineService.watchBeamlineField($scope, 'crl', ['fhit_c', 'fmirr', 'fcyl'], updateCrlFields);
        shadowService.watchPlotSize($scope, 'initialIntensityReport');
    });
});

SIREPO.app.controller('ShadowSourceController', function(appState, panelState, shadowService, $scope) {
    var self = this;
    self.shadowService = shadowService;

    function updateRayFilterFields() {
        var hasFilter = appState.models.rayFilter.f_bound_sour == '2';
        panelState.showField('rayFilter', 'distance', hasFilter);
        panelState.showRow('rayFilter', 'x1', hasFilter);
    }

    function updateGeometricSettings() {
        var geo = appState.models.geometricSource;
        ['wxsou', 'wzsou'].forEach(function(f) {
            panelState.showField('geometricSource', f, geo.fsour == '1' || geo.fsour == '2');
        });
        ['sigmax', 'sigmaz'].forEach(function(f) {
            panelState.showField('geometricSource', f, geo.fsour == '3');
        });
        ['hdiv1', 'hdiv2', 'vdiv1', 'vdiv2'].forEach(function(f) {
            panelState.showField('sourceDivergence', f, geo.fdistr == '1' || geo.fdistr == '2' || geo.fdistr == '3');
        });
        ['sigdix', 'sigdiz'].forEach(function(f) {
            panelState.showField('geometricSource', f, geo.fdistr == '3');
        });
        panelState.showRow('sourceDivergence', 'hdiv1', geo.fdistr == '1' || geo.fdistr == '2' || geo.fdistr == '3');
        ['cone_max', 'cone_min'].forEach(function(f) {
            panelState.showField('geometricSource', f, geo.fdistr == '5');
        });
        panelState.showField('geometricSource', 'wysou', geo.fsource_depth == '2');
        panelState.showField('geometricSource', 'sigmay', geo.fsource_depth == '3');
        panelState.showField('geometricSource', 'singleEnergyValue', geo.f_color == '1');
        ['ph1', 'ph2'].forEach(function(f) {
            panelState.showField('geometricSource', f, geo.f_color == '3');
        });
        ['f_coher', 'pol_angle', 'pol_deg'].forEach(function(f) {
            panelState.showField('geometricSource', f, geo.f_polar == '1');
        });
    }

    function updateWigglerSettings() {
        var wiggler = appState.models.wiggler;
        panelState.showField('wiggler', 'kValue', wiggler.b_from == '0');
        panelState.showField('wiggler', 'trajFile', wiggler.b_from == '1' || wiggler.b_from == '2');
        panelState.showField('wiggler', 'per', wiggler.b_from == '0' || wiggler.b_from == '2');
        panelState.showField('wiggler', 'shift_x_value', wiggler.shift_x_flag == '5');
        panelState.showField('wiggler', 'shift_betax_value', wiggler.shift_betax_flag == '5');
    }

    self.handleModalShown = function(name) {
        if (name == 'bendingMagnet' || name == 'geometricSource' || name == 'wiggler') {
            updateRayFilterFields();
        }
        if (name == 'geometricSource') {
            updateGeometricSettings();
        }
        else if (name == 'wiggler') {
            updateWigglerSettings();
        }
        else if (name == 'plotXYReport') {
            shadowService.updatePlotSizeFields('plotXYReport');
        }
    };

    self.isSource = function(name) {
        return appState.isLoaded() && appState.models.simulation.sourceType == name;
    };

    appState.whenModelsLoaded($scope, function() {
        updateGeometricSettings();
        appState.watchModelFields($scope, ['rayFilter.f_bound_sour'], updateRayFilterFields);
        appState.watchModelFields($scope, ['simulation.sourceType', 'geometricSource.fsour', 'geometricSource.fdistr', 'geometricSource.fsource_depth', 'geometricSource.f_color', 'geometricSource.f_polar'], updateGeometricSettings);
        appState.watchModelFields($scope, ['wiggler.b_from', 'wiggler.shift_x_flag', 'wiggler.shift_betax_flag'], updateWigglerSettings);
        shadowService.watchPlotSize($scope, 'plotXYReport');
    });
});

SIREPO.app.directive('appFooter', function() {
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

SIREPO.app.directive('appHeader', function() {
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'beamline\')}"><a href data-ng-click="nav.openSection(\'beamline\')"><span class="glyphicon glyphicon-option-horizontal"></span> Beamline</a></li>',
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
    };
});

//TODO(pjm): consolidate this with similar code in rpnValue directive
SIREPO.app.directive('reflectivityMaterial', function(appState, requestSender) {
    var requestIndex = 0;
    return {
        restrict: 'A',
        require: 'ngModel',
        link: function(scope, element, attrs, ngModel) {
            ngModel.$parsers.push(function(value) {
                if (ngModel.$isEmpty(value)) {
                    return null;
                }
                requestIndex++;
                var currentRequestIndex = requestIndex;
                requestSender.getApplicationData(
                    {
                        method: 'validate_material',
                        material_name: value,
                    },
                    function(data) {
                        // check for a stale request
                        if (requestIndex != currentRequestIndex) {
                            return;
                        }
                        var err = data.error;
                        ngModel.$setValidity('', err ? false : true);
                    });
                return value;
            });
            ngModel.$formatters.push(function(value) {
                if (ngModel.$isEmpty(value)) {
                    return value;
                }
                return value.toString();
            });
        }
    };
});
