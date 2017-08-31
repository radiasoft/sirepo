'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.appLocalRoutes.lattice = '/lattice/:simulationId';
SIREPO.appLocalRoutes.control = '/control/:simulationId';
SIREPO.appLocalRoutes.visualization = '/visualization/:simulationId';
SIREPO.ELEGANT_COMMAND_PREFIX = 'command_';
SIREPO.PLOTTING_COLOR_MAP = 'afmhot';
//TODO(pjm): provide API for this, keyed by field type
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="BeamInputFile" class="col-sm-7">',
      '<div data-file-field="field" data-model="model" data-file-type="bunchFile-sourceFile" data-empty-selection-text="No File Selected"></div>',
    '</div>',
    '<div data-ng-switch-when="ElegantBeamlineList" data-ng-class="fieldClass">',
      '<div data-elegant-beamline-list="" data-model="model" data-field="field"></div>',
    '</div>',
    '<div data-ng-switch-when="ElegantLatticeList" data-ng-class="fieldClass">',
      '<div data-elegant-lattice-list="" data-model="model" data-field="field"></div>',
    '</div>',
    '<div data-ng-switch-when="InputFileXY" class="col-sm-7">',
      '<div data-input-file-x-y="" data-model-name="modelName" data-model="model" data-field="field"></div>',
    '</div>',
    '<div data-ng-switch-when="OutputFile" data-ng-class="fieldClass">',
      '<div data-output-file-field="field" data-model="model"></div>',
    '</div>',
    '<div data-ng-switch-when="RPNBoolean" data-ng-class="fieldClass">',
      '<div data-rpn-boolean="" data-model="model" data-field="field"></div>',
    '</div>',
    '<div data-ng-switch-when="RPNValue">',
      '<div data-ng-class="fieldClass">',
        '<input data-rpn-value="" data-ng-model="model[field]" class="form-control" style="text-align: right" required />',
      '</div>',
      '<div class="col-sm-2">',
        '<div data-rpn-static="" data-model="model" data-field="field"></div>',
      '</div>',
    '</div>',
    '<div data-ng-switch-when="StringArray" data-ng-class="fieldClass">',
      '<input data-ng-model="model[field]" class="form-control" required />',
    '</div>',
    '<div data-ng-switch-when="ValueList" data-ng-class="fieldClass">',
      '<select class="form-control" data-ng-model="model[field]" data-ng-options="item as item for item in model[\'valueList\'][field]"></select>',
    '</div>',
    '<div data-ng-switch-when="DistributionType" data-ng-class="fieldClass">',
        '<div data-distribution-type="" data-model="model" data-field="model[field]" data-info="info" data-type-list="enum[info[1]]"></div>',
    '</div>',
].join('');
SIREPO.appDownloadLinks = [
    '<li><a href data-ng-href="{{ dataFileURL(\'csv\') }}">CSV Data File</a></li>',
].join('');

SIREPO.app.config(function($routeProvider, localRoutesProvider) {
    if (SIREPO.IS_LOGGED_OUT) {
        return;
    }
    var localRoutes = localRoutesProvider.$get();
    $routeProvider
        .when(localRoutes.source, {
            controller: 'ElegantSourceController as source',
            templateUrl: '/static/html/elegant-source.html' + SIREPO.SOURCE_CACHE_KEY,
        })
        .when(localRoutes.lattice, {
            controller: 'LatticeController as lattice',
            templateUrl: '/static/html/elegant-lattice.html' + SIREPO.SOURCE_CACHE_KEY,
        })
        .when(localRoutes.control, {
            controller: 'CommandController as control',
            templateUrl: '/static/html/elegant-control.html' + SIREPO.SOURCE_CACHE_KEY,
        })
        .when(localRoutes.visualization, {
            controller: 'VisualizationController as visualization',
            templateUrl: '/static/html/elegant-visualization.html' + SIREPO.SOURCE_CACHE_KEY,
        });
});

SIREPO.app.factory('elegantService', function(appState, rpnService, $rootScope) {
    var self = {};

    function bunchChanged() {
        // update bunched_beam fields
        var bunch = appState.models.bunch;
        var cmd = self.findFirstCommand('bunched_beam');
        if (cmd) {
            updateCommandFromBunch(cmd, bunch);
        }
        cmd = self.findFirstCommand('run_setup');
        if (cmd) {
            if (rpnService.getRpnValue(cmd.p_central) === 0) {
                cmd.p_central_mev = bunch.p_central_mev;
            }
            else {
                cmd.p_central = rpnService.getRpnValue(bunch.p_central_mev) / SIREPO.APP_SCHEMA.constant.ELEGANT_ME_EV;
            }
        }
        appState.saveQuietly('commands');
    }

    function bunchFileChanged() {
        var cmd = self.findFirstCommand('sdds_beam');
        if (cmd) {
            cmd.input = appState.models.bunchFile.sourceFile;
            appState.saveQuietly('commands');
        }
    }

    function bunchSourceChanged() {
        // replace first sdds_beam/bunched_beam if necessary
        var cmd = self.findFirstCommand(['bunched_beam', 'sdds_beam']);
        if (! cmd) {
            return;
        }
        var type = appState.models.bunchSource.inputSource;
        if (cmd._type == type) {
            return;
        }
        if (type == 'bunched_beam') {
            delete cmd.inputSource;
            cmd._type = type;
            appState.setModelDefaults(cmd, 'command_bunched_beam');
            updateCommandFromBunch(cmd, appState.models.bunch);
        }
        else if (type == 'sdds_beam') {
            for (var k in cmd) {
                if (k != '_id') {
                    delete cmd[k];
                }
            }
            cmd._type = type;
            cmd.input = appState.models.bunchFile.sourceFile;
        }
        appState.saveQuietly('commands');
    }

    function commandsChanged() {
        var cmd = self.findFirstCommand('run_setup');
        if (cmd) {
            appState.models.simulation.visualizationBeamlineId = cmd.use_beamline;
            appState.saveQuietly('simulation');
        }

        // update bunchSource, bunchFile, bunch models
        cmd = self.findFirstCommand(['bunched_beam', 'sdds_beam']);
        if (! cmd) {
            return;
        }
        appState.models.bunchSource.inputSource = cmd._type;
        appState.saveQuietly('bunchSource');
        if (cmd._type == 'bunched_beam') {
            var bunch = appState.models.bunch;
            updateBunchFromCommand(bunch, cmd);

            // p_central_mev
            cmd = self.findFirstCommand('run_setup');
            if (cmd) {
                if (rpnService.getRpnValue(cmd.p_central_mev) !== 0) {
                    bunch.p_central_mev = cmd.p_central_mev;
                }
                else {
                    bunch.p_central_mev = rpnService.getRpnValue(cmd.p_central) * SIREPO.APP_SCHEMA.constant.ELEGANT_ME_EV;
                }
            }
            // need to update source reports.
            appState.saveChanges('bunch');
        }
        else {
            appState.models.bunchFile.sourceFile = cmd.input;
            appState.saveQuietly('bunchFile');
        }
    }

    function simulationChanged() {
        var cmd = self.findFirstCommand('run_setup');
        if (! cmd) {
            return;
        }
        cmd.use_beamline = appState.models.simulation.visualizationBeamlineId;
        appState.saveQuietly('commands');
    }

    function updateBunchFromCommand(bunch, cmd) {
        bunch.n_particles_per_bunch = cmd.n_particles_per_bunch;
        bunch.emit_x = cmd.emit_x * 1e9;
        bunch.beta_x = cmd.beta_x;
        bunch.alpha_x = cmd.alpha_x;
        bunch.emit_y = cmd.emit_y * 1e9;
        bunch.beta_y = cmd.beta_y;
        bunch.alpha_y = cmd.alpha_y;
        bunch.longitudinalMethod = cmd.dp_s_coupling !== 0
            ? 1 // sigma s, sigma dp, dp s coupling
            : ((cmd.emit_z !== 0 || cmd.beta_z !== 0)
               ? 3 // emit z, beta z, alpha z
               : 2); // sigma s, sigma dp, alpha z
        bunch.sigma_s = cmd.sigma_s * 1e6;
        bunch.sigma_dp = cmd.sigma_dp;
        bunch.dp_s_coupling = cmd.dp_s_coupling;
        bunch.emit_z = cmd.emit_z * 1e9;
        bunch.beta_z = cmd.beta_z;
        bunch.alpha_z = cmd.alpha_z;
    }

    function updateCommandFromBunch(cmd, bunch) {
        cmd.n_particles_per_bunch = bunch.n_particles_per_bunch;
        cmd.emit_x = bunch.emit_x / 1e9;
        cmd.beta_x = bunch.beta_x;
        cmd.alpha_x = bunch.alpha_x;
        cmd.emit_y = bunch.emit_y / 1e9;
        cmd.beta_y = bunch.beta_y;
        cmd.alpha_y = bunch.alpha_y;
        cmd.sigma_s = bunch.sigma_s / 1e6;
        cmd.sigma_dp = bunch.sigma_dp;
        cmd.dp_s_coupling = bunch.dp_s_coupling;
        cmd.emit_z = bunch.emit_z / 1e9;
        cmd.beta_z = bunch.beta_z;
        cmd.alpha_z = bunch.alpha_z;
        if (bunch.longitudinalMethod == 1) {
            cmd.emit_z = 0;
            cmd.beta_z = 0;
            cmd.alpha_z = 0;
        }
        else if (bunch.longitudinalMethod == 2) {
            cmd.emit_z = 0;
            cmd.beta_z = 0;
            cmd.dp_s_coupling = 0;
        }
        else if (bunch.longitudinalMethod == 3) {
            cmd.sigma_dp = 0;
            cmd.sigma_s = 0;
            cmd.dp_s_coupling = 0;
        }
    }

    self.commandModelName = function(type) {
        return SIREPO.ELEGANT_COMMAND_PREFIX + type;
    };

    self.elementForId = function(id) {
        var i;
        id = Math.abs(id);
        for (i = 0; i < appState.models.beamlines.length; i++) {
            var b = appState.models.beamlines[i];
            if (b.id == id) {
                return b;
            }
        }
        for (i = 0; i < appState.models.elements.length; i++) {
            var e = appState.models.elements[i];
            if (e._id == id) {
                return e;
            }
        }
        return null;
    };

    self.findFirstCommand = function(types, commands) {
        if (! commands) {
            if (! appState.isLoaded()) {
                return null;
            }
            commands = appState.models.commands;
        }
        if (typeof(types) == 'string') {
            types = [types];
        }
        for (var i = 0; i < commands.length; i++) {
            var cmd = commands[i];
            for (var j = 0; j < types.length; j++) {
                if (cmd._type == types[j]) {
                    return cmd;
                }
            }
        }
        return null;
    };

    self.isCommandModelName = function(name) {
        return name.indexOf(SIREPO.ELEGANT_COMMAND_PREFIX) === 0;
    };

    self.nextId = function() {
        return Math.max(
            appState.maxId(appState.models.elements, '_id'),
            appState.maxId(appState.models.beamlines),
            appState.maxId(appState.models.commands, '_id')) + 1;
    };

    // keep source page items in sync with the associated control command
    $rootScope.$on('modelChanged', function(e, name) {
        var cmd, bunch;
        if (name == 'bunchSource') {
            bunchSourceChanged();
        }
        else if (name == 'bunchFile') {
            bunchFileChanged();
        }
        else if (name == 'bunch') {
            bunchChanged();
        }
        else if (name == 'simulation') {
            simulationChanged();
        }
        else if (name == 'commands') {
            commandsChanged();
        }
        else if (name == 'WATCH') {
            // elegant will crash if the watch has no output filename
            var watch = appState.models.WATCH;
            if (watch && ! watch.filename) {
                watch.filename = '1';
            }
        }
    });

    return self;
});

SIREPO.app.service('rpnService', function(appState, requestSender, $rootScope) {
    var rpnBooleanValues = null;

    function clearBooleanValues() {
        rpnBooleanValues = null;
    }

    this.computeRpnValue = function(value, callback) {
        if (value in appState.models.rpnCache) {
            callback(appState.models.rpnCache[value]);
            return;
        }
        requestSender.getApplicationData(
            {
                method: 'rpn_value',
                value: value,
                variables: appState.models.rpnVariables,
            },
            function(data) {
                if (! data.error) {
                    if (appState.isLoaded())
                        appState.models.rpnCache[value] = data.result;
                }
                callback(data.result, data.error);
            });
    };

    this.getRpnBooleanForField = function(model, field) {
        if (appState.isLoaded() && model && field) {
            if (! rpnBooleanValues) {
                rpnBooleanValues = [];
                if (appState.models.rpnVariables) {
                    for (var i = 0; i < appState.models.rpnVariables.length; i++) {
                        var v = appState.models.rpnVariables[i];
                        rpnBooleanValues.push([v.name, 'var: ' + v.name]);
                    }
                    rpnBooleanValues = rpnBooleanValues.sort(function(a, b) {
                        return a[1].localeCompare(b[1]);
                    });
                }
                rpnBooleanValues.unshift(
                    ['0', 'No'],
                    ['1', 'Yes']);
            }
            return rpnBooleanValues;
        }
        return null;
    };

    this.getRpnValue = function(v) {
        if (angular.isUndefined(v))
            return v;
        if (v in appState.models.rpnCache)
            return appState.models.rpnCache[v];
        var value = parseFloat(v);
        if (isNaN(value))
            return undefined;
        return value;
    };

    this.getRpnValueForField = function(model, field) {
        if (appState.isLoaded() && model && field) {
            var v = model[field];
            if (SIREPO.NUMBER_REGEXP.test(v))
                return '';
            return this.getRpnValue(v);
        }
        return '';
    };

    this.recomputeCache = function(varName, value) {
        var recomputeRequired = false;
        var re = new RegExp("\\b" + varName + "\\b");
        for (var k in appState.models.rpnCache) {
            if (k == varName)
                appState.models.rpnCache[k] = value;
            else if (k.match(re))
                recomputeRequired = true;
        }
        if (! recomputeRequired)
            return;
        requestSender.getApplicationData(
            {
                method: 'recompute_rpn_cache_values',
                cache: appState.models.rpnCache,
                variables: appState.models.rpnVariables,
            },
            function(data) {
                if (appState.isLoaded() && data.cache)
                    appState.models.rpnCache = data.cache;
            });
    };

    $rootScope.$on('rpnVariables.changed', clearBooleanValues);
    appState.whenModelsLoaded($rootScope, clearBooleanValues);
});

SIREPO.app.controller('CommandController', function(appState, elegantService, panelState) {
    var self = this;
    self.activeTab = 'basic';
    self.basicNames = [
        'alter_elements', 'bunched_beam', 'chromaticity',
        'error_control', 'error_element', 'load_parameters',
        'matrix_output', 'optimization_setup', 'optimization_term',
        'optimization_variable', 'optimize', 'run_control',
        'run_setup', 'twiss_output', 'track',
        'vary_element',
    ];
    self.advancedNames = [
        'amplification_factors', 'analyze_map', 'aperture_data', 'change_particle',
        'closed_orbit', 'correct', 'correct_tunes', 'correction_matrix_output',
        'coupled_twiss_output', 'divide_elements', 'find_aperture', 'floor_coordinates',
        'frequency_map', 'global_settings', 'insert_elements', 'insert_sceffects',
        'linear_chromatic_tracking_setup', 'link_control', 'link_elements', 'modulate_elements',
        'moments_output', 'momentum_aperture', 'optimization_constraint', 'optimization_covariable',
        'parallel_optimization_setup', 'print_dictionary', 'ramp_elements', 'replace_elements',
        'rf_setup', 'rpn_expression', 'rpn_load', 'sasefel',
        'save_lattice', 'sdds_beam', 'slice_analysis', 'steering_element',
        'touschek_scatter', 'transmute_elements','tune_footprint', 'tune_shift_with_amplitude',
        'twiss_analysis',
    ];
    self.allNames = self.basicNames.concat(self.advancedNames).sort();

    self.createElement = function(name) {
        $('#' + panelState.modalId('newCommand')).modal('hide');
        var model = {
            _id: elegantService.nextId(),
            _type: name,
        };
        appState.setModelDefaults(model, elegantService.commandModelName(name));
        var modelName = elegantService.commandModelName(model._type);
        appState.models[modelName] = model;
        panelState.showModalEditor(modelName);
    };

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[elegantService.commandModelName(name)].description;
    };
});

SIREPO.app.controller('ElegantSourceController', function(appState, elegantService, $scope, $timeout) {
    var self = this;
    var longitudinalFields = ['sigma_s', 'sigma_dp', 'dp_s_coupling', 'emit_z', 'beta_z', 'alpha_z'];
    //TODO(pjm): share with template/elegant.py _PLOT_TITLE
    var plotTitle = {
        'x-xp': 'Horizontal',
        'y-yp': 'Vertical',
        'x-y': 'Cross-section',
        't-p': 'Longitudinal',
    };

    function validateSaving() {
        if (! appState.isLoaded()) {
            return;
        }
        var bunch = appState.models.bunch;
        validateGreaterThanZero(bunch, 'beta_x');
        validateGreaterThanZero(bunch, 'beta_y');
        validateGreaterThanZero(bunch, 'n_particles_per_bunch');
        validateGreaterThanZero(bunch, 'p_central_mev');
        appState.saveQuietly('bunch');
    }

    function validateGreaterThanZero(model, field) {
        if (parseFloat(model[field]) <= 0) {
            model[field] = 1;
        }
    }

    function validateGreaterOrEqualToZero(model, field) {
        if (parseFloat(model[field]) < 0) {
            model[field] = 0;
        }
    }

    function validateTyping() {
        if (! appState.isLoaded()) {
            return;
        }
        var bunch = appState.models.bunch;
        // dp_s_coupling valid only between -1 and 1
        var v = parseFloat(bunch.dp_s_coupling);
        if (v > 1) {
            bunch.dp_s_coupling = 1;
        }
        else if (v < -1) {
            bunch.dp_s_coupling = -1;
        }
        validateGreaterOrEqualToZero(bunch, 'emit_x');
        validateGreaterOrEqualToZero(bunch, 'emit_y');
        validateGreaterOrEqualToZero(bunch, 'emit_z');
        validateGreaterOrEqualToZero(bunch, 'beta_z');
    }

    function showFields(fields, delay) {
        for (var i = 0; i < longitudinalFields.length; i++) {
            var f = longitudinalFields[i];
            var selector = '.model-bunch-' + f;
            if (fields.indexOf(f) >= 0) {
                $(selector).closest('.form-group').show(delay);
            }
            else {
                $(selector).closest('.form-group').hide(delay);
            }
        }
    }

    function updateLongitudinalFields(delay) {
        if (! appState.isLoaded()) {
            return;
        }
        var method = appState.models.bunch.longitudinalMethod;
        if (parseInt(method) == 1) {
            showFields(['sigma_s', 'sigma_dp', 'dp_s_coupling'], delay);
        }
        else if (parseInt(method) == 2) {
            showFields(['sigma_s', 'sigma_dp', 'alpha_z'], delay);
        }
        else {
            showFields(['emit_z', 'beta_z', 'alpha_z'], delay);
        }
    }

    self.bunchReports = [
        {id: 1},
        {id: 2},
        {id: 3},
        {id: 4},
    ];

    self.bunchReportHeading = function(item) {
        if (! appState.isLoaded()) {
            return;
        }
        var bunch = appState.models['bunchReport' + item.id];
        var key = bunch.x + '-' + bunch.y;
        return 'Bunch Report - ' + (plotTitle[key] || (bunch.x + ' / ' + bunch.y));
    };

    self.handleModalShown = function() {
        updateLongitudinalFields(0);
    };

    self.isBunchSource = function(name) {
        if (! appState.isLoaded()) {
            return false;
        }
        return appState.models.bunchSource.inputSource == name;
    };

    var modelAccessByItemId = {};

    self.modelAccess = function(itemId) {
        if (modelAccessByItemId[itemId]) {
            return modelAccessByItemId[itemId];
        }
        var modelKey = 'bunchReport' + itemId;
        modelAccessByItemId[itemId] = {
            modelKey: modelKey,
            getData: function() {
                return appState.models[modelKey];
            },
        };
        return modelAccessByItemId[itemId];
    };

    // watch path depends on appState as an attribute of $scope
    $scope.appState = appState;
    $scope.$watch('appState.models.bunch.longitudinalMethod', function () {
        updateLongitudinalFields(400);
    });
    $scope.$watchCollection('appState.models.bunch', validateTyping);
    $scope.$on('bunch.changed', validateSaving);
});

SIREPO.app.controller('LatticeController', function(appState, elegantService, panelState, rpnService, $rootScope, $scope, $window) {
    var self = this;
    var emptyElements = [];

    self.appState = appState;
    self.activeTab = 'basic';
    self.activeBeamlineId = null;

    self.basicNames = [
        'CSBEND', 'CSRCSBEND', 'CSRDRIFT',
        'DRIF', 'ECOL', 'KICKER',
        'MARK', 'QUAD', 'SEXT',
        'WATCH', 'WIGGLER',
    ];

    self.advancedNames = [
        'ALPH', 'BMAPXY', 'BUMPER', 'CENTER',
        'CEPL', 'CHARGE', 'CLEAN', 'CORGPIPE',
        'CWIGGLER', 'DSCATTER', 'EDRIFT', 'ELSE',
        'EMATRIX', 'EMITTANCE', 'ENERGY', 'FLOOR',
        'FMULT', 'FRFMODE', 'FTABLE', 'FTRFMODE',
        'GFWIGGLER', 'HISTOGRAM', 'HKICK', 'HMON',
        'IBSCATTER', 'ILMATRIX', 'KOCT', 'KPOLY',
        'KQUAD', 'KQUSE', 'KSBEND', 'KSEXT',
        'LMIRROR', 'LSCDRIFT', 'LSRMDLTR', 'LTHINLENS',
        'MAGNIFY', 'MALIGN', 'MAPSOLENOID', 'MATR',
        'MATTER', 'MAXAMP', 'MBUMPER', 'MHISTOGRAM',
        'MODRF', 'MONI', 'MRFDF', 'MULT',
        'NIBEND', 'NISEPT', 'OCTU', 'PEPPOT',
        'PFILTER', 'QUFRINGE', 'RAMPP', 'RAMPRF',
        'RBEN', 'RCOL', 'RECIRC', 'REFLECT',
        'REMCOR', 'RFCA', 'RFCW', 'RFDF',
        'RFMODE', 'RFTM110', 'RFTMEZ0', 'RIMULT',
        'RMDF', 'ROTATE', 'SAMPLE', 'SBEN',
        'SCATTER', 'SCMULT', 'SCRAPER', 'SCRIPT',
        'SOLE', 'SREFFECTS', 'STRAY', 'TFBDRIVER',
        'TFBPICKUP', 'TMCF', 'TRCOUNT', 'TRFMODE',
        'TRWAKE', 'TUBEND', 'TWISS', 'TWLA',
        'TWMTA', 'TWPL', 'UKICKMAP', 'VKICK',
        'VMON', 'WAKE', 'ZLONGIT', 'ZTRANSVERSE',
    ];

    self.allNames = self.basicNames.concat(self.advancedNames).sort();

    self.elementPic = {
        alpha: ['ALPH'],
        bend: ['BUMPER', 'CSBEND', 'CSRCSBEND', 'FMULT', 'HKICK', 'KICKER', 'KPOLY', 'KSBEND', 'KQUSE', 'MBUMPER', 'MULT', 'NIBEND', 'NISEPT', 'RBEN', 'SBEN', 'TUBEND'],
        drift: ['CSRDRIFT', 'DRIF', 'EDRIFT', 'EMATRIX', 'LSCDRIFT'],
        aperture: ['CLEAN', 'ECOL', 'MAXAMP', 'RCOL', 'SCRAPER'],
        lens: ['LTHINLENS'],
        magnet: ['BMAPXY', 'FTABLE', 'KOCT', 'KQUAD', 'KSEXT', 'MATTER', 'OCTU', 'QUAD', 'QUFRINGE', 'SEXT', 'VKICK'],
        mirror: ['LMIRROR', 'REFLECT'],
        recirc: ['RECIRC'],
        solenoid: ['MAPSOLENOID', 'SOLE'],
        undulator: ['CORGPIPE', 'CWIGGLER', 'GFWIGGLER', 'LSRMDLTR', 'MATR', 'UKICKMAP', 'WIGGLER'],
        watch: ['HMON', 'MARK', 'MONI', 'PEPPOT', 'VMON', 'WATCH'],
        zeroLength: ['CENTER', 'CHARGE', 'DSCATTER', 'ELSE', 'EMITTANCE', 'ENERGY', 'FLOOR', 'HISTOGRAM', 'IBSCATTER', 'ILMATRIX', 'MAGNIFY', 'MALIGN', 'MHISTOGRAM', 'PFILTER', 'REMCOR', 'RIMULT', 'ROTATE', 'SAMPLE', 'SCATTER', 'SCMULT', 'SCRIPT', 'SREFFECTS', 'STRAY', 'TFBDRIVER', 'TFBPICKUP', 'TRCOUNT', 'TRWAKE', 'TWISS', 'WAKE', 'ZLONGIT', 'ZTRANSVERSE'],
        rf: ['CEPL', 'FRFMODE', 'FTRFMODE', 'MODRF', 'MRFDF', 'RAMPP', 'RAMPRF', 'RFCA', 'RFCW', 'RFDF', 'RFMODE', 'RFTM110', 'RFTMEZ0', 'RMDF', 'TMCF', 'TRFMODE', 'TWLA', 'TWMTA', 'TWPL'],
    };

    self.elementColor = {
        BMAPXY: 'magenta',
        FTABLE: 'magenta',
        KOCT: 'lightyellow',
        KQUAD: 'tomato',
        KSEXT: 'lightgreen',
        MATTER: 'black',
        OCTU: 'yellow',
        QUAD: 'red',
        QUFRINGE: 'salmon',
        SEXT: 'lightgreen',
        VKICK: 'blue',
        'LMIRROR': 'lightblue',
        'REFLECT': 'blue',
    };

    function elementsByName() {
        var res = {};
        var containerNames = ['elements', 'beamlines'];
        for (var i = 0; i < containerNames.length; i++) {
            var containerName = containerNames[i];
            for (var j = 0; j < appState.models[containerName].length; j++)
                res[appState.models[containerName][j].name] = 1;
        }
        return res;
    }

    function fixModelName(modelName) {
        var m = appState.models[modelName];
        // remove invalid characters
        m.name = m.name.replace(/[\s#*'",]/g, '');
        return;
    }

    function getBeamlinesWhichContainId(id) {
        var res = [];
        for (var i = 0; i < appState.models.beamlines.length; i++) {
            var b = appState.models.beamlines[i];
            for (var j = 0; j < b.items.length; j++) {
                if (id == Math.abs(b.items[j])) {
                    res.push(b.id);
                }
            }
        }
        return res;
    }

    function showDeleteWarning(type, element, beamlines) {
        var names = {};
        for (var i = 0; i < beamlines.length; i++) {
            names[self.elementForId(beamlines[i]).name] = true;
        }
        names = Object.keys(names).sort();
        var idField = type == 'elements' ? '_id' : 'id';
        self.deleteWarning = {
            type: type,
            element: element,
            typeName: type == 'elements' ? 'Element' : 'Beamline',
            name: self.elementForId(element[idField]).name,
            beamlineName: Object.keys(names).length > 1
                ? ('beamlines (' + names.join(', ') + ')')
                : ('beamline ' + names[0]),
        };
        $(beamlines.length ? '#sr-element-in-use-dialog' : '#sr-delete-element-dialog').modal('show');
    }

    function sortBeamlines() {
        appState.models.beamlines.sort(function(a, b) {
            return a.name.localeCompare(b.name);
        });
    }

    function sortElements() {
        appState.models.elements.sort(function(a, b) {
            var res = a.type.localeCompare(b.type);
            if (res === 0) {
                res = a.name.localeCompare(b.name);
            }
            return res;
        });
    }

    function uniqueNameForType(prefix) {
        var names = elementsByName();
        var name = prefix;
        var index = 1;
        while (names[name + index])
            index++;
        return name + index;
    }

    function updateModels(name, idField, containerName, sortMethod) {
        // update element/elements or beamline/beamlines
        var m = appState.models[name];
        var foundIt = false;
        for (var i = 0; i < appState.models[containerName].length; i++) {
            var el = appState.models[containerName][i];
            if (m[idField] == el[idField]) {
                foundIt = true;
                break;
            }
        }
        if (! foundIt) {
            if (elementsByName()[m.name]) {
                m.name = uniqueNameForType(m.name + '-');
            }
            appState.models[containerName].push(m);
        }
        sortMethod();
        appState.removeModel(name);
        appState.saveChanges(containerName);
    }

    self.addToBeamline = function(item) {
        self.getActiveBeamline().items.push(item.id || item._id);
        appState.saveChanges('beamlines');
    };

    self.angleFormat = function(angle) {
        var degrees = rpnService.getRpnValue(angle) * 180 / Math.PI;
        degrees = Math.round(degrees * 10) / 10;
        degrees %= 360;
        return degrees.toFixed(1);
    };

    self.createElement = function(type) {
        $('#' + panelState.modalId('newBeamlineElement')).modal('hide');
        var model = {
            _id: elegantService.nextId(),
            type: type,
            name: uniqueNameForType(type.charAt(0)),
        };
        appState.setModelDefaults(model, type);
        self.editElement(type, model);
    };

    self.deleteElement = function() {
        var type = self.deleteWarning.type;
        var element = self.deleteWarning.element;
        self.deleteWarning = null;
        var idField = type == 'elements' ? '_id' : 'id';
        for (var i = 0; i < appState.models[type].length; i++) {
            var el = appState.models[type][i];
            if (el[idField] == element[idField]) {
                appState.models[type].splice(i, 1);
                appState.saveChanges(type);
                $rootScope.$broadcast('elementDeleted', type);
                return;
            }
        }
        return;
    };

    self.deleteElementPrompt = function(type, element) {
        var idField = type == 'elements' ? '_id' : 'id';
        var beamlines = getBeamlinesWhichContainId(element[idField]);
        showDeleteWarning(type, element, beamlines);
    };

    self.editBeamline = function(beamline) {
        self.activeBeamlineId = beamline.id;
        appState.models.simulation.activeBeamlineId = beamline.id;
        appState.saveChanges('simulation');
        $rootScope.$broadcast('activeBeamlineChanged');
    };

    self.editElement = function(type, item) {
        appState.models[type] = item;
        panelState.showModalEditor(type);
    };

    self.elementForId = function(id) {
        return elegantService.elementForId(id);
    };

    self.getActiveBeamline = function() {
        var id = self.activeBeamlineId;
        for (var i = 0; i < appState.models.beamlines.length; i++) {
            var b = appState.models.beamlines[i];
            if (b.id == id) {
                return b;
            }
        }
        return null;
    };

    self.getElements = function() {
        if (appState.isLoaded) {
            return appState.models.elements;
        }
        return emptyElements;
    };

    self.isElementModel = function(name) {
        return name == name.toUpperCase();
    };

    self.nameForId = function(id) {
        return self.elementForId(id).name;
    };

    self.newBeamline = function() {
        appState.models.beamline = {
            name: uniqueNameForType('BL'),
            id: elegantService.nextId(),
            l: 0,
            count: 0,
            items: [],
        };
        panelState.showModalEditor('beamline');
    };

    self.newElement = function() {
        $('#' + panelState.modalId('newBeamlineElement')).modal('show');
    };

    //TODO(pjm): use library for this
    self.numFormat = function(num, units) {
        if (! angular.isDefined(num)) {
            return '';
        }
        num = rpnService.getRpnValue(num);
        if (num < 1) {
            num *= 1000;
            units = 'm' + units;
        }
        if (Math.round(num * 100) === 0) {
            return '0';
        }
        if (num >= 1000) {
            return num.toFixed(0) + units;
        }
        if (num >= 100) {
            return num.toFixed(1) + units;
        }
        if (num >= 10) {
            return num.toFixed(2) + units;
        }
        return num.toFixed(3) + units;
    };

    self.showRpnVariables = function() {
        appState.models.rpnVariables = appState.models.rpnVariables.sort(function(a, b) {
            return a.name.localeCompare(b.name);
        });
        $('#elegant-rpn-variables').modal('show');
    };

    self.setActiveTab = function(name) {
        self.activeTab = name;
    };

    self.splitPaneHeight = function() {
        var w = $($window);
        var el = $('.sr-split-pane-frame');
        return Math.round(w.height() - el.offset().top - 15) + 'px';
    };

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[name].description;
    };

    $scope.$on('cancelChanges', function(e, name) {
        if (name == 'beamline') {
            appState.removeModel(name);
            appState.cancelChanges('beamlines');
        }
        else if (self.isElementModel(name)) {
            appState.removeModel(name);
            appState.cancelChanges('elements');
        }
    });

    $scope.$on('modelChanged', function(e, name) {
        if (name == 'beamline') {
            fixModelName(name);
            var id = appState.models.beamline.id;
            updateModels('beamline', 'id', 'beamlines', sortBeamlines);
            self.editBeamline({ id: id });
        }
        if (self.isElementModel(name)) {
            fixModelName(name);
            updateModels(name, '_id', 'elements', sortElements);
        }
    });
    appState.whenModelsLoaded($scope, function() {
        self.activeBeamlineId = appState.models.simulation.activeBeamlineId;
        //TODO(pjm): only required for when viewing after import
        // force update to bunch from command.bunched_beam
        appState.saveChanges('commands');
    });
});

SIREPO.app.controller('VisualizationController', function(appState, elegantService, frameCache, panelState, persistentSimulation, requestSender, $rootScope, $scope) {
    var self = this;
    self.model = 'animation';
    self.appState = appState;
    self.panelState = panelState;
    self.dots = '.';
    self.simulationErrors = '';
    self.timeData = {
        elapsedDays: null,
        elapsedTime: null,
    };
    self.outputFiles = [];
    self.outputFileMap = {};
    self.auxFiles = [];

    function cleanFilename(fn) {
        return fn.replace(/\.(?:sdds|output_file|filename)/g, '');
    }

    function defaultYColumn(columns, xCol) {
        for (var i = 0; i < columns.length; i++) {
            // Ignore "ElementOccurence" column
            if (columns[i].indexOf('Element') < 0 && columns[i] != xCol ) {
                return columns[i];
            }
        }
        return columns[1];
    }

    function fileURL(index, model) {
        if (! appState.isLoaded()) {
            return '';
        }
        return requestSender.formatUrl('downloadDataFile', {
            '<simulation_id>': appState.models.simulation.simulationId,
            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
            '<model>': model || self.model,
            '<frame>': index,
        });
    }

    function hideField(modelName, field) {
        $('.model-' + modelName + '-' + field).closest('.form-group').hide();
    }

    function loadElementReports(outputInfo, startTime) {
        self.outputFiles = [];
        self.outputFileMap = {};
        self.auxFiles = [];
        var animationArgs = {};
        var similarRowCounts = {};

        outputInfo.forEach(function (info, i) {
            if (info.isAuxFile) {
                self.auxFiles.push({
                    filename: info.filename,
                    id: info.id,
                });
                return;
            }
            if (! info.columns) {
                return;
            }
            var modelKey = 'elementAnimation' + info.id;
            panelState.setError(modelKey, null);
            var outputFile = {
                info: info,
                reportType: reportTypeForColumns(info.plottableColumns),
                modelName: 'elementAnimation',
                filename: info.filename,
                modelAccess: {
                    modelKey: modelKey,
                },
            };
            self.outputFiles.push(outputFile);
            self.outputFileMap[outputFile.filename] = outputFile;
            var rowCountsKey = info.rowCounts.join(' ');
            if (!(rowCountsKey in similarRowCounts)) {
                similarRowCounts[rowCountsKey] = [];
            }
            similarRowCounts[rowCountsKey].push(info.filename);
            info.similarFiles = similarRowCounts[rowCountsKey];
        });

        self.outputFiles.forEach(function (outputFile, i) {
            var info = outputFile.info;
            var modelKey = outputFile.modelAccess.modelKey;
            animationArgs[modelKey] = [
                SIREPO.ANIMATION_ARGS_VERSION + '2',
                'x',
                'y',
                'histogramBins',
                'xFileId',
                'yFileId',
                'startTime',
            ];
            var m = null;
            if (appState.models[modelKey]) {
                m = appState.models[modelKey];
                m.startTime = startTime;
                m.xFileId = info.id;
                m.xFile = info.filename;
                if (info.plottableColumns.indexOf(m.x) < 0) {
                    m.x = info.plottableColumns[0];
                }
            }
            else {
                m = appState.models[modelKey] = {
                    xFile: info.filename,
                    yFile: info.filename,
                    x: info.plottableColumns[0],
                    y: null,
                    histogramBins: 200,
                    fileId: info.id,
                    xFileId: info.id,
                    yFileId: info.id,
                    framesPerSecond: 2,
                    startTime: startTime,
                };
                // Only display the first outputFile
                if (i > 0 && ! panelState.isHidden(modelKey)) {
                    panelState.toggleHidden(modelKey);
                }
            }
            m.valueList = {
                x: info.plottableColumns,
                yFile: info.similarFiles,
            };
            self.yFileUpdate(modelKey);
            appState.saveQuietly(modelKey);
            frameCache.setFrameCount(info.pageCount, modelKey);
            appState.watchModelFields(
                $scope,
                [modelKey + '.yFile'],
                function () {self.yFileUpdate(modelKey);}
            );
        });
        $rootScope.$broadcast('elementAnimation.outputInfo', outputInfo);
        frameCache.setAnimationArgs(animationArgs);
    }

    //TODO(pjm): keep in sync with template/elegant.py _is_2d_plot()
    function reportTypeForColumns(columns) {
        if ((columns.indexOf('x') >=0 && columns.indexOf('xp') >= 0)
            || (columns.indexOf('y') >= 0 && columns.indexOf('yp') >= 0)
            || (columns.indexOf('t') >= 0 && columns.indexOf('p') >= 0)) {
            return 'heatmap';
        }
        return '2d';
    }

    function showField(modelName, field) {
        $('.model-' + modelName + '-' + field).closest('.form-group').show();
    }

    self.downloadFileUrl = function(item) {
        var modelKey = 'elementAnimation' + item.id;
        return fileURL(1, modelKey);
    };

    self.handleModalShown = function(name, modelKey) {
        self.outputFiles.forEach(function(info) {
            if (info.modelAccess.modelKey == modelKey) {
                if (info.reportType == 'heatmap') {
                    showField(name, 'histogramBins');
                    hideField(name, 'framesPerSecond');
                }
                else {
                    hideField(name, 'histogramBins');
                    if (frameCache.getFrameCount(modelKey) > 1) {
                        showField(name, 'framesPerSecond');
                    }
                    else {
                        hideField(name, 'framesPerSecond');
                    }
                }
            }
        });
    };

    self.handleStatus = function(data) {
        self.simulationErrors = data.errors || '';
        if (data.frameCount) {
            frameCache.setFrameCount(parseInt(data.frameCount));
            loadElementReports(data.outputInfo, data.startTime);
        }
        if (self.isStateStopped()) {
            if (! data.frameCount) {
                if (data.state == 'completed' && ! self.simulationErrors) {
                    // completed with no output, show link to elegant log
                    self.simulationErrors = 'No output produced. View the elegant log for more information.';
                }
                self.outputFiles = [];
                self.outputFileMap = {};
            }
        }
    };

    self.hasOutput = function() {
        return self.isStateStopped();
    };

    self.logFileURL = function() {
        return fileURL(-1);
    };

    self.saveAndRunSimulation = function() {
        appState.saveChanges('simulation', self.runSimulation);
    };

    self.yFileUpdate = function (modelKey) {
        var m = appState.models[modelKey];
        if (m.valueList.yFile.indexOf(m.yFile) < 0) {
            m.yFile = m.xFile;
        }
        var info = self.outputFileMap[m.yFile].info;
        m.yFileId = info.id;
        var cols = m.valueList.y = info.plottableColumns;
        if (!m.y || cols.indexOf(m.y) < 0) {
            m.y = defaultYColumn(cols, m.x);
        }
        m.panelTitle = cleanFilename(m.xFile);
        if (m.xFile != m.yFile) {
            m.panelTitle += ' / ' + cleanFilename(m.yFile);
        }
    };

    persistentSimulation.initProperties(self, $scope, {});

    // override persistentSimulation settings
    self.isInitializing = function() {
        if (self.percentComplete === 0 && self.isStateProcessing()) {
            return true;
        }
        return self.isStatePending();
    };
});

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-elegant-import-dialog=""></div>',
        ].join(''),
    };
});

SIREPO.app.directive('appHeader', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: [
            '<div class="navbar-header">',
              '<a class="navbar-brand" href="/#about"><img style="width: 40px; margin-top: -10px;" src="/static/img/radtrack.gif" alt="radiasoft"></a>',
              '<div class="navbar-brand"><a data-ng-href="{{ nav.sectionURL(\'simulations\') }}">elegant</a></div>',
            '</div>',
            '<div data-app-header-left="nav"></div>',
            '<ul class="nav navbar-nav navbar-right" data-login-menu=""></ul>',
            '<ul class="nav navbar-nav navbar-right" data-ng-show="isLoaded()">',
              '<li data-ng-if="hasSourceCommand()" data-ng-class="{active: nav.isActive(\'source\')}"><a data-ng-href="{{ nav.sectionURL(\'source\') }}"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
              '<li data-ng-class="{active: nav.isActive(\'lattice\')}"><a data-ng-href="{{ nav.sectionURL(\'lattice\') }}"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>',
              '<li data-ng-if="hasBeamlines()" data-ng-class="{active: nav.isActive(\'control\')}"><a data-ng-href="{{ nav.sectionURL(\'control\') }}"><span class="glyphicon glyphicon-list-alt"></span> Control</a></li>',
              '<li data-ng-if="hasBeamlinesAndCommands()" data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
            '</ul>',
            '<ul class="nav navbar-nav navbar-right" data-ng-show="nav.isActive(\'simulations\')">',
              '<li><a href data-ng-click="showSimulationModal()"><span class="glyphicon glyphicon-plus sr-small-icon"></span><span class="glyphicon glyphicon-file"></span> New Simulation</a></li>',
              '<li><a href data-ng-click="showNewFolderModal()"><span class="glyphicon glyphicon-plus sr-small-icon"></span><span class="glyphicon glyphicon-folder-close"></span> New Folder</a></li>',
              '<li><a href data-ng-click="showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>',
            '</ul>',
        ].join(''),
        controller: function($scope) {
            $scope.hasBeamlines = function() {
                if (! $scope.isLoaded()) {
                    return false;
                }
                for (var i = 0; i < appState.models.beamlines.length; i++) {
                    var beamline = appState.models.beamlines[i];
                    if (beamline.items.length > 0) {
                        return true;
                    }
                }
                return false;
            };
            $scope.hasBeamlinesAndCommands = function() {
                if (! $scope.hasBeamlines()) {
                    return false;
                }
                return appState.models.commands.length > 0;
            };
            $scope.hasSourceCommand = function() {
                if (! $scope.isLoaded()) {
                    return false;
                }
                for (var i = 0; i < appState.models.commands.length; i++) {
                    var cmd = appState.models.commands[i];
                    if (cmd._type == 'bunched_beam' || cmd._type == 'sdds_beam') {
                        return true;
                    }
                }
                return false;
            };
            $scope.isLoaded = function() {
                if ($scope.nav.isActive('simulations')) {
                    return false;
                }
                return appState.isLoaded();
            };
            $scope.showImportModal = function() {
                $('#elegant-import').modal('show');
            };
            $scope.showNewFolderModal = function() {
                panelState.showModalEditor('simulationFolder');
            };
            $scope.showSimulationModal = function() {
                panelState.showModalEditor('simulation');
            };
        },
    };
});

SIREPO.app.directive('beamlineEditor', function(appState, panelState, $document, $timeout, $window) {
    return {
        restrict: 'A',
        scope: {
            lattice: '=controller',
        },
        template: [
            '<div data-ng-if="showEditor()" class="panel panel-info" style="margin-bottom: 0">',
              '<div class="panel-heading"><span class="sr-panel-heading">Beamline Editor - {{ beamlineName() }}</span>',
                '<div class="sr-panel-options pull-right">',
                  '<a href data-ng-click="showBeamlineNameModal()" title="Edit"><span class="sr-panel-heading glyphicon glyphicon-pencil"></span></a> ',
                '</div>',
              '</div>',
              '<div style="height: {{ editorHeight() }}" class="panel-body elegant-beamline-editor-panel" data-ng-drop="true" data-ng-drag-stop="dragStop($data)" data-ng-drop-success="dropPanel($data)" data-ng-drag-start="dragStart($data)">',
                '<p class="lead text-center"><small><em>drag and drop elements here to define the beamline</em></small></p>',
                '<div data-ng-dblclick="editItem(item)" data-ng-click="selectItem(item)" data-ng-drag="true" data-ng-drag-data="item" data-ng-repeat="item in beamlineItems" class="elegant-beamline-element" data-ng-class="{\'elegant-beamline-element-group\': item.inRepeat }" data-ng-drop="true" data-ng-drop-success="dropItem($index, $data)">',
                  '<div class="sr-drop-left">&nbsp;</div>',
                  '<span data-ng-if="item.repeatCount" class="sr-count">{{ item.repeatCount }}</span>',
                  '<div style="display: inline-block; cursor: move; -moz-user-select: none" class="badge elegant-icon elegant-beamline-element-with-count" data-ng-class="{\'elegant-item-selected\': isSelected(item.itemId), \'elegant-beamline-icon\': isBeamline(item)}"><span>{{ itemName(item) }}</span></div>',
                '</div>',
                '<div class="elegant-beamline-element sr-last-drop" data-ng-drop="true" data-ng-drop-success="dropLast($data)"><div class="sr-drop-left">&nbsp;</div></div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var selectedItemId = null;
            $scope.beamlineItems = [];
            var activeBeamline = null;
            var dragCanceled = false;
            var dropSuccess = false;

            function updateBeamline() {
                var items = [];
                for (var i = 0; i < $scope.beamlineItems.length; i++) {
                    items.push($scope.beamlineItems[i].id);
                }
                activeBeamline.items = items;
                appState.saveChanges('beamlines');
            }

            $scope.beamlineName = function() {
                return activeBeamline ? activeBeamline.name : '';
            };

            $scope.dragStart = function(data) {
                dragCanceled = false;
                dropSuccess = false;
                $scope.selectItem(data);
            };

            $scope.dragStop = function(data) {
                if (! data || dragCanceled) {
                    return;
                }
                if (data.itemId) {
                    $timeout(function() {
                        if (! dropSuccess) {
                            var curr = $scope.beamlineItems.indexOf(data);
                            $scope.beamlineItems.splice(curr, 1);
                            updateBeamline();
                        }
                    });
                }
            };

            $scope.dropItem = function(index, data) {
                if (! data) {
                    return;
                }
                if (data.itemId) {
                    if (dragCanceled) {
                        return;
                    }
                    dropSuccess = true;
                    var curr = $scope.beamlineItems.indexOf(data);
                    if (curr < index) {
                        index--;
                    }
                    $scope.beamlineItems.splice(curr, 1);
                }
                else {
                    data = $scope.beamlineItems.splice($scope.beamlineItems.length - 1, 1)[0];
                }
                $scope.beamlineItems.splice(index, 0, data);
                updateBeamline();
            };

            $scope.dropLast = function(data) {
                if (! data || ! data.itemId) {
                    return;
                }
                if (dragCanceled) {
                    return;
                }
                dropSuccess = true;
                var curr = $scope.beamlineItems.indexOf(data);
                $scope.beamlineItems.splice(curr, 1);
                $scope.beamlineItems.push(data);
                updateBeamline();
            };

            $scope.dropPanel = function(data) {
                if (! data) {
                    return;
                }
                if (data.itemId) {
                    dropSuccess = true;
                    return;
                }
                if (data.id == activeBeamline.id) {
                    return;
                }
                var item = {
                    id: data.id || data._id,
                    itemId: appState.maxId($scope.beamlineItems, 'itemId') + 1,
                };
                $scope.beamlineItems.push(item);
                $scope.selectItem(item);
                updateBeamline();
            };

            $scope.editorHeight = function() {
                var w = $($window);
                var el = $('.elegant-beamline-editor-panel');
                return (w.height() - el.offset().top - 15) + 'px';
            };

            $scope.editItem = function(item) {
                var el = $scope.lattice.elementForId(item.id);
                if (el.type) {
                    $scope.lattice.editElement(el.type, el);
                }
                else {
                    // reverse the beamline
                    item.id = -item.id;
                    updateBeamline();
                }
            };

            $scope.isBeamline = function(item) {
                var el = $scope.lattice.elementForId(item.id);
                return el.type ? false : true;
            };

            $scope.isSelected = function(itemId) {
                if (selectedItemId) {
                    return itemId == selectedItemId;
                }
                return false;
            };

            $scope.itemName = function(item) {
                item.name = $scope.lattice.nameForId(item.id);
                return (item.id < 0 ? '-' : '') + item.name;
            };

            $scope.onKeyDown = function(e) {
                // escape key - simulation a mouseup to cancel dragging
                if (e.keyCode == 27) {
                    if (selectedItemId) {
                        dragCanceled = true;
                        $document.triggerHandler('mouseup');
                    }
                }
            };

            $scope.selectItem = function(item) {
                selectedItemId = item ? item.itemId : null;
            };

            $scope.showBeamlineNameModal = function() {
                if (activeBeamline) {
                    appState.models.beamline = activeBeamline;
                    panelState.showModalEditor('beamline');
                }
            };

            $scope.showEditor = function() {
                if (! appState.isLoaded()) {
                    return false;
                }
                if (! $scope.lattice.activeBeamlineId) {
                    return false;
                }
                var beamline = $scope.lattice.getActiveBeamline();
                if (activeBeamline && activeBeamline == beamline && beamline.items.length == $scope.beamlineItems.length) {
                    return true;
                }
                activeBeamline = beamline;
                $scope.selectItem();
                $scope.beamlineItems = [];
                var itemId = 1;
                for (var i = 0; i < activeBeamline.items.length; i++) {
                    $scope.beamlineItems.push({
                        id: activeBeamline.items[i],
                        itemId: itemId++,
                    });
                }
                return true;
            };
        },
        link: function(scope, element, attrs) {
            $document.on('keydown', scope.onKeyDown);
            scope.$on('$destroy', function() {
                $document.off('keydown', scope.onKeyDown);
            });
        }
    };
});

SIREPO.app.directive('beamlineTable', function(appState, $window) {
    return {
        restrict: 'A',
        scope: {
            lattice: '=controller',
        },
        template: [
            '<table style="width: 100%; table-layout: fixed" class="table table-hover">',
              '<colgroup>',
                '<col style="width: 20ex">',
                '<col>',
                '<col data-ng-show="isLargeWindow()" style="width: 10ex">',
                '<col data-ng-show="isLargeWindow()" style="width: 12ex">',
                '<col style="width: 12ex">',
                '<col style="width: 10ex">',
              '</colgroup>',
              '<thead>',
                '<tr>',
                  '<th>Name</th>',
                  '<th>Description</th>',
                  '<th data-ng-show="isLargeWindow()">Elements</th>',
                  '<th data-ng-show="isLargeWindow()">Start-End</th>',
                  '<th>Length</th>',
                  '<th>Bend</th>',
                '</tr>',
              '</thead>',
              '<tbody>',
                '<tr data-ng-class="{success: isActiveBeamline(beamline)}" data-ng-repeat="beamline in lattice.appState.models.beamlines track by beamline.id">',
                  '<td><div class="badge elegant-icon elegant-beamline-icon"><span data-ng-drag="true" data-ng-drag-data="beamline">{{ beamline.name }}</span></div></td>',
                  '<td style="overflow: hidden"><span style="color: #777; white-space: nowrap">{{ beamlineDescription(beamline) }}</span></td>',
                  '<td data-ng-show="isLargeWindow()" style="text-align: right">{{ beamline.count }}</td>',
                  '<td data-ng-show="isLargeWindow()" style="text-align: right">{{ beamlineDistance(beamline) }}</td>',
                  '<td style="text-align: right">{{ beamlineLength(beamline) }}</td>',
                  '<td style="text-align: right">{{ beamlineBend(beamline, \'&nbsp;\') }}<span data-ng-if="beamlineBend(beamline)">&deg;</span><div data-ng-show="! isActiveBeamline(beamline)" class="sr-button-bar-parent"><div class="sr-button-bar"><button class="btn btn-info btn-xs sr-hover-button" data-ng-click="addToBeamline(beamline)">Add to Beamline</button> <button data-ng-click="editBeamline(beamline)" class="btn btn-info btn-xs sr-hover-button">Edit</button> <button data-ng-click="deleteBeamline(beamline)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div><div></td>',
                '</tr>',
              '</tbody>',
            '</table>',
        ].join(''),
        controller: function($scope) {

            var windowSize = 0;

            function itemsToString(items) {
                var res = '(';
                if (! items.length)
                    res += ' ';
                for (var i = 0; i < items.length; i++) {
                    var id = items[i];
                    res += $scope.lattice.nameForId(id);
                    if (i != items.length - 1) {
                        res += ',';
                    }
                }
                res += ')';
                return res;
            }

            $scope.addToBeamline = function(beamline) {
                $scope.lattice.addToBeamline(beamline);
            };

            $scope.beamlineBend = function(beamline, defaultValue) {
                if (angular.isDefined(beamline.angle)) {
                    return $scope.lattice.angleFormat(beamline.angle);
                }
                return defaultValue;
            };

            $scope.beamlineDescription = function(beamline) {
                return itemsToString(beamline.items);
            };

            $scope.beamlineDistance = function(beamline) {
                return $scope.lattice.numFormat(beamline.distance, 'm');
            };

            $scope.beamlineLength = function(beamline) {
                return $scope.lattice.numFormat(beamline.length, 'm');
            };

            $scope.deleteBeamline = function(beamline) {
                $scope.lattice.deleteElementPrompt('beamlines', beamline);
            };

            $scope.editBeamline = function(beamline) {
                $scope.lattice.editBeamline(beamline);
            };

            $scope.isActiveBeamline = function(beamline) {
                if ($scope.lattice.activeBeamlineId) {
                    return $scope.lattice.activeBeamlineId == beamline.id;
                }
                return false;
            };

            $scope.isLargeWindow = function() {
                return windowSize >= 1200;
            };

            function windowResize() {
                windowSize = $($window).width();
            }

            $($window).resize(windowResize);
            windowResize();
            $scope.$on('$destroy', function() {
                $($window).off('resize', windowResize);
            });
        },
    };
});

SIREPO.app.directive('commandTable', function(appState, elegantService, panelState) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div class="elegant-cmd-table">',
              '<div class="pull-right">',
                '<button class="btn btn-info btn-xs" data-ng-click="newCommand()" accesskey="c"><span class="glyphicon glyphicon-plus"></span> New <u>C</u>ommand</button>',
              '</div>',
              '<p class="lead text-center"><small><em>drag and drop commands to reorder the list</em></small></p>',
              '<table class="table table-hover" style="width: 100%; table-layout: fixed">',
                '<tr data-ng-repeat="cmd in commands">',
                  '<td data-ng-drop="true" data-ng-drop-success="dropItem($index, $data)" data-ng-drag-start="selectItem($data)">',
                    '<div class="sr-button-bar-parent pull-right"><div class="sr-button-bar"><button class="btn btn-info btn-xs sr-hover-button" data-ng-click="editCommand(cmd)">Edit</button> <button data-ng-click="expandCommand(cmd)" data-ng-disabled="isExpandDisabled(cmd)" class="btn btn-info btn-xs"><span class="glyphicon" data-ng-class="{\'glyphicon-triangle-top\': isExpanded(cmd), \'glyphicon-triangle-bottom\': ! isExpanded(cmd)}"></span></button> <button data-ng-click="deleteCommand(cmd)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div></div>',
                    '<div class="elegant-cmd-icon-holder" data-ng-drag="true" data-ng-drag-data="cmd">',
                      '<a style="cursor: move; -moz-user-select: none; font-size: 14px" class="badge elegant-icon" data-ng-class="{\'elegant-item-selected\': isSelected(cmd) }" href data-ng-click="selectItem(cmd)" data-ng-dblclick="editCommand(cmd)">{{ cmd._type }}</a>',
                    '</div>',
                    '<div data-ng-show="! isExpanded(cmd) && cmd.description" style="margin-left: 3em; margin-right: 1em; color: #777; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ cmd.description }}</div>',
                    '<div data-ng-show="isExpanded(cmd) && cmd.description" style="color: #777; margin-left: 3em; white-space: pre-wrap">{{ cmd.description }}</div>',
                  '</td>',
                '</tr>',
                '<tr><td style="height: 3em" data-ng-drop="true" data-ng-drop-success="dropLast($data)"> </td></tr>',
              '</table>',
              '<div data-ng-show="commands.length > 2" class="pull-right">',
                '<button class="btn btn-info btn-xs" data-ng-click="newCommand()" accesskey="c"><span class="glyphicon glyphicon-plus"></span> New <u>C</u>ommand</button>',
              '</div>',
            '</div>',
            '<div data-confirmation-modal="" data-id="elegant-delete-command-confirmation" data-title="Delete Command?" data-ok-text="Delete" data-ok-clicked="deleteSelected()">Delete command &quot;{{ selectedItemName() }}&quot;?</div>',
        ].join(''),
        controller: function($scope) {
            var selectedItemId = null;
            var expanded = {};
            $scope.commands = [];

            function commandDescription(cmd, commandIndex) {
                var schema = SIREPO.APP_SCHEMA.model[elegantService.commandModelName(cmd._type)];
                var res = '';
                var model = commandForId(cmd._id);
                var fields = Object.keys(model).sort();
                for (var i = 0; i < fields.length; i++) {
                    var f = fields[i];
                    if (angular.isDefined(model[f]) && angular.isDefined(schema[f])) {
                        if (schema[f][2] != model[f]) {
                            res += (res.length ? ",\n" : '') + f + ' = ';
                            if (schema[f][1] == 'OutputFile') {
                                res += cmd._type
                                    + (commandIndex > 1 ? commandIndex : '')
                                    + '.' + f + fileExtension(model);
                            }
                            else if (schema[f][1] == 'ElegantBeamlineList') {
                                //res += elegantService.elementForId(model[f]).name;
                                var el = elegantService.elementForId(model[f]);
                                if (el) {
                                    res += el.name;
                                }
                                else {
                                    res += '<missing beamline>';
                                }
                            }
                            else {
                                res += model[f];
                            }
                        }
                    }
                }
                return res;
            }

            function commandForId(id) {
                for (var i = 0; i < appState.models.commands.length; i++) {
                    var c = appState.models.commands[i];
                    if (c._id == id) {
                        return c;
                    }
                }
                return null;
            }

            function commandIndex(data) {
                return $scope.commands.indexOf(data);
            }

            function fileExtension(model) {
                return model._type == 'save_lattice' ? '.lte' : '.sdds';
            }

            function loadCommands() {
                var commands = appState.applicationState().commands;
                $scope.commands = [];
                var commandIndex = {};
                for (var i = 0; i < commands.length; i++) {
                    var cmd = commands[i];
                    if (cmd._type in commandIndex) {
                        commandIndex[cmd._type]++;
                    }
                    else {
                        commandIndex[cmd._type] = 1;
                    }
                    $scope.commands.push({
                        _type: cmd._type,
                        _id: cmd._id,
                        description: commandDescription(cmd, commandIndex[cmd._type]),
                    });
                }
            }

            function saveCommands() {
                var commands = [];
                for (var i = 0; i < $scope.commands.length; i++)
                    commands.push(commandForId($scope.commands[i]._id));
                appState.models.commands = commands;
                appState.saveChanges('commands');
            }

            function selectedItemIndex() {
                if (selectedItemId) {
                    for (var i = 0; i < $scope.commands.length; i++) {
                        if ($scope.commands[i]._id == selectedItemId) {
                            return i;
                        }
                    }
                }
                return -1;
            }

            $scope.deleteCommand = function(data) {
                if (! data) {
                    return;
                }
                $scope.selectItem(data);
                $('#elegant-delete-command-confirmation').modal('show');
            };

            $scope.deleteSelected = function() {
                var index = selectedItemIndex();
                if (index >= 0) {
                    selectedItemId = null;
                    $scope.commands.splice(index, 1);
                    saveCommands();
                }
            };

            $scope.dropItem = function(index, data) {
                if (! data) {
                    return;
                }
                var i = commandIndex(data);
                data = $scope.commands.splice(i, 1)[0];
                if (i < index) {
                    index--;
                }
                $scope.commands.splice(index, 0, data);
                saveCommands();
            };

            $scope.dropLast = function(data) {
                if (! data) {
                    return;
                }
                data = $scope.commands.splice(commandIndex(data), 1)[0];
                $scope.commands.push(data);
                saveCommands();
            };

            $scope.editCommand = function(cmd) {
                var modelName = elegantService.commandModelName(cmd._type);
                appState.models[modelName] = commandForId(cmd._id);
                panelState.showModalEditor(modelName);
            };

            $scope.isExpanded = function(cmd) {
                return expanded[cmd._id];
            };

            $scope.expandCommand = function(cmd) {
                expanded[cmd._id] = ! expanded[cmd._id];
            };

            $scope.isExpandDisabled = function(cmd) {
                if (cmd.description && cmd.description.indexOf("\n") > 0) {
                    return false;
                }
                return true;
            };

            $scope.isSelected = function(cmd) {
                return selectedItemId == cmd._id;
            };

            $scope.newCommand = function() {
                $('#' + panelState.modalId('newCommand')).modal('show');
            };

            $scope.selectItem = function(cmd) {
                selectedItemId = cmd._id;
            };

            $scope.selectedItemName = function() {
                if (selectedItemId) {
                    return commandForId(selectedItemId)._type;
                }
                return '';
            };

            $scope.$on('modelChanged', function(e, name) {
                if (name == 'commands') {
                    loadCommands();
                }
                if (elegantService.isCommandModelName(name)) {
                    var foundIt = false;
                    for (var i = 0; i < $scope.commands.length; i++) {
                        if ($scope.commands[i]._id == appState.models[name]._id) {
                            foundIt = true;
                            break;
                        }
                    }
                    if (! foundIt) {
                        var index = selectedItemIndex();
                        if (index >= 0)
                            appState.models.commands.splice(index + 1, 0, appState.models[name]);
                        else {
                            appState.models.commands.push(appState.models[name]);
                        }
                        $scope.selectItem(appState.models[name]);
                    }
                    appState.removeModel(name);
                    appState.saveChanges('commands');
                }
            });

            $scope.$on('cancelChanges', function(e, name) {
                if (elegantService.isCommandModelName(name)) {
                    appState.removeModel(name);
                    appState.cancelChanges('commands');
                }
            });

            appState.whenModelsLoaded($scope, loadCommands);
        },
    };
});

SIREPO.app.directive('elegantBeamlineList', function(appState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: [
            '<select class="form-control" data-ng-model="model[field]" data-ng-options="item.id as item.name for item in beamlineList()"></select>',
        ].join(''),
        controller: function($scope) {
            $scope.beamlineList = function() {
                if (! appState.isLoaded() || ! $scope.model)
                    return null;
                if (! $scope.model[$scope.field]
                    && appState.models.beamlines
                    && appState.models.beamlines.length) {
                    $scope.model[$scope.field] = appState.models.beamlines[0].id;
                }
                return appState.models.beamlines;
            };
        },
    };
});

SIREPO.app.directive('elegantLatticeList', function(appState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: [
            '<select class="form-control" data-ng-model="model[field]" data-ng-options="name as name for name in elegantLatticeList()"></select>',
        ].join(''),
        controller: function($scope) {
            $scope.elegantLatticeList = function() {
                if (! appState.isLoaded() || ! $scope.model)
                    return null;
                var runSetupId = $scope.model._id;
                var res = ['Lattice'];
                var index = 0;
                for (var i = 0; i < appState.models.commands.length; i++) {
                    var cmd = appState.models.commands[i];
                    if (cmd._id == runSetupId)
                        break;
                    if (cmd._type == 'save_lattice') {
                        index++;
                        if (cmd.filename)
                            res.push('save_lattice' + (index > 1 ? index : ''));
                    }
                }
                if (! $scope.model[$scope.field])
                    $scope.model[$scope.field] = res[0];
                return res;
            };
        },
    };
});

SIREPO.app.directive('elementPicker', function() {
    return {
        restrict: 'A',
        scope: {
            controller: '=',
            title: '@',
            id: '@',
            smallElementClass: '@',
        },
        template: [
            '<div class="modal fade" data-ng-attr-id="{{ id }}" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<span class="lead modal-title text-info">{{ title }}</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<div class="row">',
                        '<div class="col-sm-12">',
                          '<ul class="nav nav-tabs">',
                            '<li role="presentation" data-ng-class="{active: controller.activeTab == \'basic\'}"><a href data-ng-click="controller.activeTab = \'basic\'">Basic</a></li>',
                            '<li role="presentation" data-ng-class="{active: controller.activeTab == \'advanced\'}"><a href data-ng-click="controller.activeTab = \'advanced\'">Advanced</a></li>',
                            '<li role="presentation" data-ng-class="{active: controller.activeTab == \'all\'}"><a href data-ng-click="controller.activeTab = \'all\'">All Elements</a></li>',
                          '</ul>',
                        '</div>',
                      '</div>',
                      '<br />',
                      '<div data-ng-if="controller.activeTab == \'basic\'" class="row">',
                        '<div data-ng-repeat="name in controller.basicNames" class="col-sm-4">',
                          '<button style="width: 100%; margin-bottom: 1ex;" class="btn btn-default" type="button" data-ng-click="controller.createElement(name)" data-ng-attr-title="{{ controller.titleForName(name) }}">{{ name }}</button>',
                        '</div>',
                      '</div>',
                      '<div data-ng-if="controller.activeTab == \'advanced\'" class="row">',
                        '<div data-ng-repeat="name in controller.advancedNames" class="{{ smallElementClass }}">',
                          '<button style="width: 100%; margin-bottom: 1ex;" class="btn btn-default btn-sm" type="button" data-ng-click="controller.createElement(name)" data-ng-attr-title="{{ controller.titleForName(name) }}">{{ name }}</button>',
                        '</div>',
                      '</div>',
                      '<div data-ng-if="controller.activeTab == \'all\'" class="row">',
                        '<div data-ng-repeat="name in controller.allNames" class="{{ smallElementClass }}">',
                          '<button style="width: 100%; margin-bottom: 1ex;" class="btn btn-default btn-sm" type="button" data-ng-click="controller.createElement(name)" data-ng-attr-title="{{ controller.titleForName(name) }}">{{ name }}</button>',
                        '</div>',
                      '</div>',
                      '<br />',
                      '<div class="row">',
                        '<div class="col-sm-offset-6 col-sm-3">',
                          '<button data-dismiss="modal" class="btn btn-primary" style="width:100%">Close</button>',
                        '</div>',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
    };
});

SIREPO.app.directive('elementTable', function(appState) {
    return {
        restrict: 'A',
        scope: {
            lattice: '=controller',
        },
        template: [
            '<table style="width: 100%; table-layout: fixed" class="table table-hover">',
              '<colgroup>',
                '<col style="width: 20ex">',
                '<col>',
                '<col style="width: 12ex">',
                '<col style="width: 10ex">',
              '</colgroup>',
              '<thead>',
                '<tr>',
                  '<th>Name</th>',
                  '<th>Description</th>',
                  '<th>Length</th>',
                  '<th>Bend</th>',
                '</tr>',
              '</thead>',
              '<tbody data-ng-repeat="category in tree track by category.name">',
                '<tr>',
                  '<td style="cursor: pointer" colspan="4" data-ng-click="toggleCategory(category)" ><span class="glyphicon" data-ng-class="{\'glyphicon-collapse-up\': isExpanded(category), \'glyphicon-collapse-down\': ! isExpanded(category)}"></span> <b>{{ category.name }}</b></td>',
                '</tr>',
                '<tr data-ng-show="isExpanded(category)" data-ng-repeat="element in category.elements track by element._id">',
                  '<td style="padding-left: 1em"><div class="badge elegant-icon"><span data-ng-drag="true" data-ng-drag-data="element">{{ element.name }}</span></div></td>',
                  '<td style="overflow: hidden"><span style="color: #777; white-space: nowrap">{{ elementDescription(category.name, element) }}</span></td>',
                  '<td style="text-align: right">{{ elementLength(element) }}</td>',
                  '<td style="text-align: right">{{ elementBend(element, \'&nbsp;\') }}<span data-ng-if="elementBend(element)">&deg;</span><div class="sr-button-bar-parent"><div class="sr-button-bar"><button data-ng-show="lattice.activeBeamlineId" class="btn btn-info btn-xs sr-hover-button" data-ng-click="addToBeamline(element)">Add to Beamline</button> <button data-ng-click="editElement(category.name, element)" class="btn btn-info btn-xs sr-hover-button">Edit</button> <button data-ng-click="deleteElement(element)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div><div></td>',
                '</tr>',
              '</tbody>',
            '</table>',
        ].join(''),
        controller: function($scope) {
            $scope.tree = [];
            var collapsedElements = {};

            function loadTree() {
                //TODO(pjm): merge new tree with existing to avoid un-needed UI updates
                $scope.tree = [];
                var category = null;
                var elements = appState.applicationState().elements;

                for (var i = 0; i < elements.length; i++) {
                    var element = elements[i];
                    if (! category || category.name != element.type) {
                        category = {
                            name: element.type,
                            elements: [],
                        };
                        $scope.tree.push(category);
                    }
                    category.elements.push(element);
                }
            }

            $scope.addToBeamline = function(element) {
                $scope.lattice.addToBeamline(element);
            };

            $scope.deleteElement = function(element) {
                $scope.lattice.deleteElementPrompt('elements', element);
            };

            $scope.editElement = function(type, item) {
                var el = $scope.lattice.elementForId(item._id);
                return $scope.lattice.editElement(type, el);
            };

            $scope.elementBend = function(element, defaultValue) {
                if (angular.isDefined(element.angle)) {
                    return $scope.lattice.angleFormat(element.angle);
                }
                return defaultValue;
            };

            $scope.elementDescription = function(type, element) {
                if (! element) {
                    return 'null';
                }
                var schema = SIREPO.APP_SCHEMA.model[type];
                var res = '';
                var fields = Object.keys(element).sort();
                for (var i = 0; i < fields.length; i++) {
                    var f = fields[i];
                    if (f == 'name' || f == 'l' || f == 'angle' || f.indexOf('$') >= 0) {
                        continue;
                    }
                    if (angular.isDefined(element[f]) && angular.isDefined(schema[f])) {
                        if (schema[f][1] == 'OutputFile' && element[f]) {
                            res += (res.length ? ',' : '') + f + '=' + element.name + '.' + f + '.sdds';
                        }
                        else if (schema[f][2] != element[f]) {
                            res += (res.length ? ',' : '') + f + '=' + element[f];
                        }
                    }
                }
                return res;
            };

            $scope.elementLength = function(element) {
                return $scope.lattice.numFormat(element.l, 'm');
            };

            $scope.isExpanded = function(category) {
                return ! collapsedElements[category.name];
            };

            $scope.toggleCategory = function(category) {
                collapsedElements[category.name] = ! collapsedElements[category.name];
            };

            $scope.$on('modelChanged', function(e, name) {
                if (name == 'elements') {
                    loadTree();
                }
            });

            $scope.$on('elementDeleted', function(e, name) {
                if (name == 'elements') {
                    loadTree();
                }
            });
            appState.whenModelsLoaded($scope, loadTree);
        },
    };
});

SIREPO.app.directive('elementAnimationModalEditor', function(appState) {
    return {
        scope: {
            modelKey: '@',
            controller: '=parentController',
        },
        template: [
            '<div data-modal-editor="" view-name="elementAnimation" data-model-data="modelAccess" data-parent-controller="controller"></div>',
        ].join(''),
        controller: function($scope) {
            $scope.modelAccess = {
                modelKey: $scope.modelKey,
                getData: function() {
                    var data = appState.models[$scope.modelKey];
                    return data;
                },
            };
        },
    };
});

SIREPO.app.directive('elegantImportDialog', function(appState, elegantService, fileUpload, requestSender) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div class="modal fade" data-backdrop="static" id="elegant-import" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<div data-help-button="{{ title }}"></div>',
                    '<span class="lead modal-title text-info">{{ title }}</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                        '<form class="form-horizontal" name="importForm">',
                          '<div data-ng-show="filename" class="form-group">',
                            '<label class="col-xs-4 control-label">Importing file</label>',
                            '<div class="col-xs-8">',
                              '<p class="form-control-static">{{ filename }}</p>',
                            '</div>',
                          '</div>',
                          '<div data-ng-show="isState(\'ready\') || isState(\'lattice\')">',
                            '<div data-ng-show="isState(\'ready\')" class="form-group">',
                              '<label>Select Command (.ele) or Lattice (.lte) File</label>',
                              '<input id="elegant-file-import" type="file" data-file-model="elegantFile" accept=".ele,.lte" />',
                              '<br />',
                              '<div class="text-warning"><strong>{{ fileUploadError }}</strong></div>',
                            '</div>',
                            '<div data-ng-show="isState(\'lattice\')" class="form-group">',
                              '<label>Select Lattice File ({{ latticeFileName }})</label>',
                              '<input id="elegant-lattice-import" type="file" data-file-model="elegantFile" accept=".lte" />',
                              '<br />',
                              '<div class="text-warning"><strong>{{ fileUploadError }}</strong></div>',
                            '</div>',
                            '<div class="col-sm-6 pull-right">',
                              '<button data-ng-click="importElegantFile(elegantFile)" class="btn btn-primary" data-ng-class="{\'disabled\': isMissingImportFile() }">Import File</button>',
                              ' <button data-dismiss="modal" class="btn btn-default">Cancel</button>',
                            '</div>',
                          '</div>',
                          '<div data-ng-show="isState(\'import\') || isState(\'load-file-lists\')" class="col-sm-6 col-sm-offset-6">',
                            'Uploading file - please wait.',
                            '<br /><br />',
                          '</div>',
                          '<div data-ng-show="isState(\'missing-files\')">',
                            '<p>Please upload the files below which are referenced in the elegant file.</p>',
                            '<div class="form-group" data-ng-repeat="item in missingFiles">',
                              '<div class="col-sm-8 col-sm-offset-1">',
                                '<span data-ng-if="item[5] && isCorrectMissingFile(item)" class="glyphicon glyphicon-ok"></span> ',
                                '<span data-ng-if="item[5] && ! isCorrectMissingFile(item)" class="glyphicon glyphicon-flag text-danger"></span> <span data-ng-if="item[5] && ! isCorrectMissingFile(item)" class="text-danger">Filename does not match, expected: </span>',
                                '<label>{{ auxFileLabel(item) }}</label> ({{ auxFileName(item) }})',
                                '<input type="file" data-file-model="item[5]" />',
                              '</div>',
                            '</div>',
                            '<div class="text-warning"><strong>{{ fileUploadError }}</strong></div>',
                            '<div class="col-sm-6 pull-right">',
                              '<button data-ng-click="importMissingFiles()" class="btn btn-primary" data-ng-class="{\'disabled\': isMissingFiles() }">{{ importMissingFilesButtonText() }}</button>',
                              ' <button data-dismiss="modal" class="btn btn-default">Cancel</button>',
                            '</div>',
                          '</div>',
                        '</form>',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.title = 'Import Elegant File';
            // states: ready, import, lattice, load-file-lists, missing-files
            $scope.state = 'ready';

            function classifyInputFiles(model, modelType, modelName, requiredFiles) {
                var inputFiles = modelInputFiles(modelType);
                for (var i = 0; i < inputFiles.length; i++) {
                    if (model[inputFiles[i]]) {
                        if (! requiredFiles[modelType]) {
                            requiredFiles[modelType] = {};
                        }
                        if (! requiredFiles[modelType][inputFiles[i]]) {
                            requiredFiles[modelType][inputFiles[i]] = {};
                        }
                        requiredFiles[modelType][inputFiles[i]][model[inputFiles[i]]] = modelName;
                    }
                }
            }

            function hasMissingLattice(data) {
                var runSetup = elegantService.findFirstCommand('run_setup', data.models.commands);
                if (! runSetup || runSetup.lattice == 'Lattice') {
                    return false;
                }
                $scope.latticeFileName = runSetup.lattice;
                return true;
            }

            function hideAndRedirect() {
                $('#elegant-import').modal('hide');
                requestSender.localRedirect('lattice', {
                    ':simulationId': $scope.id,
                });
            }

            function loadFileLists() {
                $scope.state = 'load-file-lists';
                if (! $scope.missingFileLists.length) {
                    verifyMissingFiles();
                    return;
                }
                var fileType = $scope.missingFileLists.pop();
                requestSender.loadAuxiliaryData(
                    fileType,
                    requestSender.formatUrl('listFiles', {
                        '<simulation_id>': $scope.id,
                        '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        '<file_type>': fileType,
                    }),
                    loadFileLists);
            }

            function modelInputFiles(type) {
                var res = [];
                var elementSchema = SIREPO.APP_SCHEMA.model[type];
                for (var f in elementSchema) {
                    if (elementSchema[f][1].indexOf('InputFile') >= 0) {
                        res.push(f);
                    }
                }
                return res;
            }

            function verifyInputFiles(data) {
                if (hasMissingLattice(data)) {
                    $scope.state = 'lattice';
                    $scope.elegantFile = null;
                    return;
                }
                var requiredFiles = {};
                var i;
                for (i = 0; i < data.models.elements.length; i++) {
                    var el = data.models.elements[i];
                    classifyInputFiles(el, el.type, el.name, requiredFiles);
                }
                for (i = 0; i < data.models.commands.length; i++) {
                    var cmd = data.models.commands[i];
                    classifyInputFiles(cmd, elegantService.commandModelName(cmd._type), cmd._type, requiredFiles);
                }
                $scope.inputFiles = [];
                for (var type in requiredFiles) {
                    for (var field in requiredFiles[type]) {
                        for (var filename in requiredFiles[type][field]) {
                            var fileType = type + '-' + field;
                            //TODO(pjm): special case for BeamInputFile which shares files between bunchFile and command_sdds_beam
                            if (type == 'command_sdds_beam' && field == 'input') {
                                fileType = 'bunchFile-sourceFile';
                            }
                            $scope.inputFiles.push([type, field, filename, fileType, requiredFiles[type][field][filename]]);
                        }
                    }
                }
                verifyFileLists();
            }

            function verifyFileLists() {
                var res = [];
                for (var i = 0; i < $scope.inputFiles.length; i++) {
                    var fileType = $scope.inputFiles[i][3];
                    if (! requestSender.getAuxiliaryData(fileType)) {
                        res.push(fileType);
                    }
                }
                $scope.missingFileLists = res;
                loadFileLists();
            }

            function verifyMissingFiles() {
                var res = [];
                for (var i = 0; i < $scope.inputFiles.length; i++) {
                    var filename = $scope.inputFiles[i][2];
                    var fileType = $scope.inputFiles[i][3];
                    var list = requestSender.getAuxiliaryData(fileType);
                    if (list.indexOf(filename) < 0) {
                        res.push($scope.inputFiles[i]);
                    }
                }
                if (! res.length) {
                    hideAndRedirect();
                    return;
                }
                $scope.state = 'missing-files';
                $scope.missingFiles = res.sort(function(a, b) {
                    if (a[0] < b[0]) {
                        return -1;
                    }
                    if (a[0] > b[0]) {
                        return 1;
                    }
                    if (a[1] < b[1]) {
                        return -1;
                    }
                    if (a[1] > b[1]) {
                        return 1;
                    }
                    return 0;
                });
            }

            $scope.auxFileLabel = function(item) {
                return item[2];
            };

            $scope.auxFileName = function(item) {
                return item[4]
                    + ': '
                    + (elegantService.isCommandModelName(item[0])
                       ? ''
                       : (item[0] + ' '))
                    + item[1];
            };

            $scope.importElegantFile = function(elegantFile) {
                if (! elegantFile) {
                    return;
                }
                var args = {
                    folder: appState.getActiveFolderPath(),
                };
                if ($scope.state == 'lattice') {
                    args.simulationId = $scope.id;
                }
                else {
                    $scope.resetState();
                    $scope.filename = elegantFile.name;
                }
                $scope.state = 'import';
                fileUpload.uploadFileToUrl(
                    elegantFile,
                    args,
                    requestSender.formatUrl(
                        'importFile',
                        {
                            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        }),
                    function(data) {
                        if (data.error) {
                            $scope.resetState();
                            $scope.fileUploadError = data.error;
                        }
                        else {
                            $scope.id = data.models.simulation.simulationId;
                            $scope.simulationName = data.models.simulation.name;
                            verifyInputFiles(data);
                        }
                    });
            };

            $scope.importMissingFiles = function() {
                $scope.state = 'import';
                var dataResponseHandler = function(data) {
                    if (data.error) {
                        $scope.state = 'missing-files';
                        $scope.fileUploadError = data.error;
                        return;
                    }
                    requestSender.getAuxiliaryData(data.fileType).push(data.filename);
                    hideAndRedirect();
                };
                for (var i = 0; i < $scope.missingFiles.length; i++) {
                    var f = $scope.missingFiles[i][5];
                    var fileType = $scope.missingFiles[i][3];

                    fileUpload.uploadFileToUrl(
                        f,
                        null,
                        requestSender.formatUrl(
                            'uploadFile',
                            {
                                '<simulation_id>': $scope.id,
                                '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                                '<file_type>': fileType,
                            }),
                        dataResponseHandler);
                }
            };

            $scope.importMissingFilesButtonText = function() {
                if (! $scope.missingFiles) {
                    return '';
                }
                return 'Import File' + ($scope.missingFiles.length > 1 ? 's' : '');
            };

            $scope.isCorrectMissingFile = function(item) {
                if (! item[5]) {
                    return false;
                }
                return item[2] == item[5].name;
            };

            $scope.isMissingFiles = function() {
                if (! $scope.missingFiles) {
                    return true;
                }
                for (var i = 0; i < $scope.missingFiles.length; i++) {
                    if (! $scope.missingFiles[i][5]) {
                        return true;
                    }
                    if (! $scope.isCorrectMissingFile($scope.missingFiles[i])) {
                        return true;
                    }
                }
                return false;
            };

            $scope.isMissingImportFile = function() {
                return ! $scope.elegantFile;
            };

            $scope.isState = function(state) {
                return $scope.state == state;
            };

            $scope.resetState = function() {
                $scope.id = null;
                $scope.elegantFile = null;
                $scope.filename = '';
                $scope.simulationName = '';
                $scope.state = 'ready';
                $scope.fileUploadError = '';
                $scope.latticeFileName = '';
                $scope.inputFiles = null;
            };

            $scope.resetState();
        },
        link: function(scope, element) {
            $(element).on('show.bs.modal', function() {
                $('#elegant-file-import').val(null);
                $('#elegant-lattice-import').val(null);
                scope.resetState();
            });
            scope.$on('$destroy', function() {
                $(element).off();
            });
        },
    };
});

SIREPO.app.directive('inputFileXY', function() {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            model: '=',
            field: '=',
        },
        template: [
            '<div style="display: inline-block" data-file-field="field" data-model="model" data-model-name="modelName" data-empty-selection-text="No File Selected"></div>',
            ' <label style="margin: 0 1ex">X</label> ',
            '<input data-ng-model="model[fieldX()]" style="display: inline-block; width: 8em" class="form-control" />',
            ' <label style="margin: 0 1ex">Y</label> ',
            '<input data-ng-model="model[fieldY()]" style="display: inline-block; width: 8em" class="form-control" />',
        ].join(''),
        controller: function($scope) {
            $scope.fieldX = function() {
                return $scope.field + 'X';
            };
            $scope.fieldY = function() {
                return $scope.field + 'Y';
            };
        },
    };
});

SIREPO.app.directive('distributionType', function() {
    return {
        restrict: 'A',
        scope: {
            model: '<',
            field: '=',
            info: '<',
            typeList: '<',
        },
        template: [
            '<div data-ng-repeat="defaultSelection in field.split(\',\') track by $index" style="display: inline-block" >',
                '<span class="elegant-dropdown-label">{{distLabels[$index] || \'Plane \' + $index}}: </span>',
                '<select ',
                    'class="form-control elegant-dropdown-select" data-ng-model="distributions[$index]" data-ng-change="didChange(distributions[$index])"',
                    'data-ng-options="item[0] as item[1] for item in typeList">',
                '</select>',
            '</div>'
        ].join(''),
        controller: function($scope) {
            $scope.distributions = $scope.field.split(/\s*,\s*/);
            $scope.distLabels = ($scope.info[4] || '').split(/\s*,\s*/);
            $scope.didChange = function(item) {
                $scope.field = $scope.distributions.join(', ');
            };
        },
    };
});

SIREPO.app.directive('lattice', function(appState, panelState, plotting, rpnService, $window) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/lattice.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            //TODO(pjm): need a way to get at the controller for info, or provide in a common service.
            $scope.latticeController = panelState.findParentAttribute($scope, 'lattice');
            $scope.isClientOnly = true;
            $scope.margin = 3;
            $scope.width = 1;
            $scope.height = 1;
            $scope.scale = 1;
            $scope.xOffset = 0;
            $scope.yOffset = 0;
            $scope.zoomScale = 1;
            $scope.panTranslate = [0, 0];
            $scope.markerWidth = 1;
            $scope.markerUnits = '';

            var emptyList = [];
            $scope.items = [];
            $scope.svgGroups = [];
            $scope.svgBounds = null;
            var picTypeCache = null;

            function rpnValue(num) {
                return rpnService.getRpnValue(num);
            }

            function applyGroup(items, pos) {
                var group = {
                    rotate: pos.angle,
                    rotateX: pos.x,
                    rotateY: pos.y,
                    items: [],
                };
                $scope.svgGroups.push(group);
                var x = 0;
                var oldRadius = pos.radius;
                var newAngle = 0;
                var maxHeight = 0;

                for (var i = 0; i < items.length; i++) {
                    var item = items[i];
                    var picType = $scope.getPicType(item.type);
                    var length = rpnValue(item.l || item.xmax || 0);
                    if (picType == 'zeroLength')
                        length = 0;
                    var elRadius = rpnValue(item.rx || item.x_max || 0);
                    pos.length += length;
                    if (length < 0) {
                        // negative length, back up
                        x += length;
                        length = 0;
                    }
                    //TODO(pjm): need to refactor picType processing
                    if (picType == 'bend') {
                        var radius = length / 2;
                        var angle = rpnValue(item.angle || item.kick || item.hkick || 0);
                        maxHeight = Math.max(maxHeight, length);
                        var height = 0.75;
                        var enter = [pos.radius + pos.x + x, pos.y];
                        //TODO(pjm): if angle is arc length, need to convert it to a rendered length
                        // if (length > 0 && angle != 0) {
                        //     var noArcLength = Math.abs(2 * Math.sin(angle / 2) * length / angle);
                        //     length = noArcLength;
                        // }
                        if (length === 0) {
                            length = 0.1;
                            enter[0] -= 0.05;
                        }
                        var enterEdge = rpnValue(item.e1 || 0);
                        var exitEdge = rpnValue(item.e2 || 0);
                        if (item.type == 'RBEN') {
                            enterEdge = 0;
                            exitEdge = 0;
                        }
                        var exit = [enter[0] + length / 2 + Math.cos(angle) * length / 2,
                                    pos.y + Math.sin(angle) * length / 2];
                        var exitAngle = exitEdge - angle;
                        var points = [
                                [enter[0] - Math.sin(-enterEdge) * height / 2,
                                 enter[1] - Math.cos(-enterEdge) * height / 2],
                                [enter[0] + Math.sin(-enterEdge) * height / 2,
                                 enter[1] + Math.cos(-enterEdge) * height / 2],
                                [exit[0] + Math.sin(exitAngle) * height / 2,
                                 exit[1] + Math.cos(exitAngle) * height / 2],
                                [exit[0] - Math.sin(exitAngle) * height / 2,
                                 exit[1] - Math.cos(exitAngle) * height / 2],
                        ];
                        // trim overlap if necessary
                        if (points[1][0] > points[2][0]) {
                            points[1] = points[2] = lineIntersection(points);
                        }
                        else if (points[0][0] > points[3][0]) {
                            points[0] = points[3] = lineIntersection(points);
                        }
                        group.items.push({
                            picType: picType,
                            element: item,
                            color: $scope.getPicColor(item.type, 'blue'),
                            points: points,
                        });
                        x += radius;
                        newAngle = angle * 180 / Math.PI;
                        pos.radius = radius;
                    }
                    else {
                        var groupItem = {
                            picType: picType,
                            element: item,
                            x: pos.radius + pos.x + x,
                            height: 0,
                            width: length,
                        };
                        if (picType == 'watch') {
                            groupItem.height = 1;
                            groupItem.y = pos.y;
                            groupItem.color = $scope.getPicColor(item.type, 'lightgreen');
                        }
                        else if (picType == 'drift') {
                            groupItem.color = $scope.getPicColor(item.type, 'lightgrey');
                            groupItem.height = 0.1;
                            groupItem.y = pos.y - groupItem.height / 2;
                        }
                        else if (picType == 'aperture') {
                            groupItem.color = 'lightgrey';
                            groupItem.apertureColor = $scope.getPicColor(item.type, 'black');
                            groupItem.height = 0.1;
                            groupItem.y = pos.y - groupItem.height / 2;
                            if (groupItem.width === 0) {
                                groupItem.x -= 0.01;
                                groupItem.width = 0.02;
                            }
                            groupItem.opening = elRadius || 0.1;
                        }
                        else if (picType == 'alpha') {
                            var alphaAngle = 40.71;
                            newAngle = 180 - 2 * alphaAngle;
                            if (length < 0.3)
                                groupItem.width = 0.3;
                            groupItem.angle = alphaAngle;
                            groupItem.height = groupItem.width;
                            groupItem.y = pos.y - groupItem.height / 2;
                            length = 0;
                        }
                        else if (picType == 'magnet') {
                            groupItem.height = 0.5;
                            groupItem.y = pos.y - groupItem.height / 2;
                            groupItem.color = $scope.getPicColor(item.type, 'red');
                        }
                        else if (picType == 'undulator') {
                            groupItem.height = 0.25;
                            groupItem.y = pos.y - groupItem.height / 2;
                            groupItem.color = $scope.getPicColor(item.type, 'gray');
                            var periods = Math.round(rpnValue(item.periods || item.poles || 0));
                            if (periods <= 0)
                                periods = Math.round(5 * length);
                            groupItem.blockWidth = groupItem.width / (2 * periods);
                            groupItem.blocks = [];
                            groupItem.blockHeight = 0.03;
                            for (var j = 0; j < 2 * periods; j++) {
                                groupItem.blocks.push([
                                    groupItem.x + j * groupItem.blockWidth,
                                    j % 2
                                        ? groupItem.y + groupItem.height / 4
                                        : groupItem.y + groupItem.height * 3 / 4 - groupItem.blockHeight,
                                ]);
                            }
                        }
                        else if (picType == 'zeroLength' || picType == 'mirror' || (picType == 'rf' && length < 0.005)) {
                            groupItem.color = $scope.getPicColor(item.type, 'black');
                            groupItem.picType = 'zeroLength';
                            groupItem.height = 0.5;
                            groupItem.y = pos.y;
                        }
                        else if (picType == 'rf') {
                            groupItem.height = 0.3;
                            groupItem.y = pos.y;
                            var ovalCount = Math.round(length / (groupItem.height / 2)) || 1;
                            groupItem.ovalWidth = length / ovalCount;
                            groupItem.ovals = [];
                            for (var k = 0; k < ovalCount; k++) {
                                groupItem.ovals.push(groupItem.x + k * groupItem.ovalWidth + groupItem.ovalWidth / 2);
                            }
                            groupItem.color = $scope.getPicColor(item.type, 'gold');
                        }
                        else if (picType == 'recirc') {
                            groupItem.radius = 0.3;
                            groupItem.y = pos.y;
                            groupItem.leftEdge = groupItem.x - groupItem.radius;
                            groupItem.rightEdge = groupItem.x + groupItem.radius;
                            groupItem.color = $scope.getPicColor(item.type, 'lightgreen');
                        }
                        else if (picType == 'lens') {
                            groupItem.height = 0.2;
                            groupItem.width = 0.02;
                            groupItem.x -= 0.01;
                            groupItem.y = pos.y - groupItem.height / 2;
                            groupItem.color = $scope.getPicColor(item.type, 'lightblue');
                        }
                        else if (picType == 'solenoid') {
                            if (length === 0) {
                                groupItem.width = 0.3;
                                groupItem.x -= 0.15;
                            }
                            groupItem.height = groupItem.width;
                            groupItem.y = pos.y - groupItem.height / 2;
                            groupItem.color = $scope.getPicColor(item.type, 'lightblue');
                        }
                        else {
                            groupItem.color = $scope.getPicColor(item.type, 'green');
                            groupItem.height = 0.2;
                            groupItem.y = pos.y - groupItem.height / 2;
                        }
                        maxHeight = Math.max(maxHeight, groupItem.height);
                        //groupItem.x = pos.radius + pos.x + x;
                        group.items.push(groupItem);
                        x += length;
                    }
                }
                if (pos.angle === 0) {
                    pos.x += x + oldRadius;
                }
                else {
                    pos.x += Math.sin((90 - pos.angle) * Math.PI / 180) * (x + oldRadius);
                    pos.y += Math.sin(pos.angle * Math.PI / 180) * (x + oldRadius);
                }
                updateBounds(pos.bounds, pos.x, pos.y, Math.max(maxHeight, pos.radius));
                pos.angle += newAngle;
            }

            function computePositions() {
                var pos = {
                    x: 0,
                    y: 0,
                    angle: 0,
                    radius: 0,
                    bounds: [0, 0, 0, 0],
                    count: 0,
                    length: 0,
                };
                var explodedItems = explodeItems($scope.items);
                var group = [];
                var groupDone = false;
                for (var i = 0; i < explodedItems.length; i++) {
                    if (groupDone) {
                        applyGroup(group, pos);
                        group = [];
                        groupDone = false;
                    }
                    //var item = $scope.latticeController.elementForId($scope.items[i]);
                    var item = explodedItems[i];
                    var picType = $scope.getPicType(item.type);
                    if (picType != 'drift')
                        pos.count++;
                    if (picType == 'bend' || picType == 'alpha')
                        groupDone = true;
                    group.push(item);
                }
                if (group.length)
                    applyGroup(group, pos);
                $scope.svgBounds = pos.bounds;
                if (explodedItems.length > 0 && 'angle' in explodedItems[explodedItems.length - 1])
                    pos.x += pos.radius;
                return pos;
            }

            //TODO(pjm): will infinitely recurse if beamlines are self-referential
            function explodeItems(items, res, reversed) {
                if (! res)
                    res = [];
                if (reversed)
                    items = items.slice().reverse();
                for (var i = 0; i < items.length; i++) {
                    var id = items[i];
                    var item = $scope.latticeController.elementForId(id);
                    if (item.type)
                        res.push(item);
                    else {
                        explodeItems(item.items, res, id < 0);
                    }
                }
                return res;
            }

            function lineIntersection(p) {
                var s1_x = p[1][0] - p[0][0];
                var s1_y = p[1][1] - p[0][1];
                var s2_x = p[3][0] - p[2][0];
                var s2_y = p[3][1] - p[2][1];
                var t = (s2_x * (p[0][1] - p[2][1]) - s2_y * (p[0][0] - p[2][0])) / (-s2_x * s1_y + s1_x * s2_y);
                return [
                    p[0][0] + (t * s1_x),
                    p[0][1] + (t * s1_y)];
            }

            function loadItemsFromBeamline(forceUpdate) {
                var id = $scope.latticeController.activeBeamlineId;
                if (! id) {
                    $scope.items = emptyList;
                    return;
                }
                var beamline = $scope.latticeController.getActiveBeamline();
                if (! forceUpdate && appState.deepEquals(beamline.items, $scope.items)) {
                    return;
                }
                $scope.items = appState.clone(beamline.items);
                $scope.svgGroups = [];
                var pos = computePositions();
                beamline.distance = Math.sqrt(Math.pow(pos.x, 2) + Math.pow(pos.y, 2));
                beamline.length = pos.length;
                beamline.angle = pos.angle * Math.PI / 180;
                beamline.count = pos.count;
                $scope.resize();
            }

            function recalcScaleMarker() {
                //TODO(pjm): use library for this
                $scope.markerUnits = '1 m';
                $scope.markerWidth = $scope.scale * $scope.zoomScale;
                if ($scope.markerWidth < 20) {
                    $scope.markerUnits = '10 m';
                    $scope.markerWidth *= 10;
                    if ($scope.markerWidth < 20) {
                        $scope.markerUnits = '100 m';
                        $scope.markerWidth *= 10;
                    }
                }
                else if ($scope.markerWidth > 200) {
                    $scope.markerUnits = '10 cm';
                    $scope.markerWidth /= 10;
                    if ($scope.markerWidth > 200) {
                        $scope.markerUnits = '1 cm';
                        $scope.markerWidth /= 10;
                    }
                }
            }

            function resetZoomAndPan() {
                $scope.zoomScale = 1;
                $scope.zoom.scale($scope.zoomScale);
                $scope.panTranslate = [0, 0];
                $scope.zoom.translate($scope.panTranslate);
                updateZoomAndPan();
            }

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            function updateBounds(bounds, x, y, buffer) {
                if (x - buffer < bounds[0])
                    bounds[0] = x - buffer;
                if (y - buffer < bounds[1])
                    bounds[1] = y - buffer;
                if (x + buffer > bounds[2])
                    bounds[2] = x + buffer;
                if (y + buffer > bounds[3])
                    bounds[3] = y + buffer;
            }

            function updateZoomAndPan() {
                recalcScaleMarker();
                $scope.container.attr("transform", "translate(" + $scope.panTranslate + ")scale(" + $scope.zoomScale + ")");
            }

            function zoomed() {
                $scope.zoomScale = d3.event.scale;

                if ($scope.zoomScale == 1) {
                    $scope.panTranslate = [0, 0];
                    $scope.zoom.translate($scope.panTranslate);
                }
                else {
                    //TODO(pjm): don't allow translation outside of image boundaries
                    $scope.panTranslate = d3.event.translate;
                }
                updateZoomAndPan();
                $scope.$digest();
            }

            $scope.getPicColor = function(type, defaultColor) {
                return $scope.latticeController.elementColor[type] || defaultColor;
            };

            $scope.getPicType = function(type) {
                if (! picTypeCache) {
                    picTypeCache = {};
                    var elementPic = $scope.latticeController.elementPic;
                    for (var picType in elementPic) {
                        var types = elementPic[picType];
                        for (var i = 0; i < types.length; i++)
                            picTypeCache[types[i]] = picType;
                    }
                }
                return picTypeCache[type];
            };

            $scope.itemClicked = function(item) {
                $scope.latticeController.editElement(item.type, item);
            };

            $scope.resize = function() {
                var width = parseInt(select().style('width'));
                if (isNaN(width))
                    return;
                $scope.width = width;
                $scope.height = $scope.width;
                var windowHeight = $($window).height();
                if ($scope.height > windowHeight / 2.5)
                    $scope.height = windowHeight / 2.5;

                if ($scope.svgBounds) {
                    var w = $scope.svgBounds[2] - $scope.svgBounds[0];
                    var h = $scope.svgBounds[3] - $scope.svgBounds[1];
                    if (w === 0 || h === 0)
                        return;
                    var scaleWidth = $scope.width / w;
                    var scaleHeight = $scope.height / h;
                    var scale = 1;
                    var xOffset = 0;
                    var yOffset = 0;
                    if (scaleWidth < scaleHeight) {
                        scale = scaleWidth;
                        yOffset = ($scope.height - h * scale) / 2;
                    }
                    else {
                        scale = scaleHeight;
                        xOffset = ($scope.width - w * scale) / 2;
                    }
                    $scope.scale = scale;
                    $scope.xOffset = - $scope.svgBounds[0] * scale + xOffset;
                    $scope.yOffset = - $scope.svgBounds[1] * scale + yOffset;
                    recalcScaleMarker();
                }
            };

            $scope.init = function() {
                $scope.zoom = d3.behavior.zoom()
                    .scaleExtent([1, 50])
                    .on('zoom', zoomed);
                //TODO(pjm): call stopPropagation() on item double-click instead, would allow double-click zoom on empty space
                select('svg').call($scope.zoom)
                    .on('dblclick.zoom', null);
                $scope.container = select('.sr-zoom-plot');
                loadItemsFromBeamline();
            };

            $scope.destroy = function() {
                if ($scope.zoom)
                    $scope.zoom.on('zoom', null);
            };

            $scope.$on('modelChanged', function(e, name) {
                if (name == 'beamlines')
                    loadItemsFromBeamline();
                if (name == 'rpnVariables')
                    loadItemsFromBeamline(true);
                if (appState.models[name] && appState.models[name]._id) {
                    if ($scope.items.indexOf(appState.models[name]._id) >= 0)
                        loadItemsFromBeamline(true);
                }
            });

            $scope.$on('cancelChanges', function(e, name) {
                if (name == 'elements')
                    loadItemsFromBeamline(true);
            });

            $scope.$on('activeBeamlineChanged', function() {
                loadItemsFromBeamline();
                resetZoomAndPan();
            });
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('outputFileField', function(appState) {
    return {
        restrict: 'A',
        scope: {
            field: '=outputFileField',
            model: '=',
        },
        template: [
            '<select class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in items()"></select>',
        ].join(''),
        controller: function($scope) {
            var items = [];
            var filename = '';

            function fileExtension() {
                if ($scope.model && $scope.model._type == 'save_lattice')
                    return '.lte';
                return '.sdds';
            }

            $scope.items = function() {
                if (! $scope.model)
                    return items;
                var prefix = $scope.model.name;
                if ($scope.model._type) {
                    var index = 0;
                    for (var i = 0; i < appState.models.commands.length; i++) {
                        var m = appState.models.commands[i];
                        if (m._type == $scope.model._type) {
                            index++;
                            if (m == $scope.model)
                                break;
                        }
                    }
                    prefix = $scope.model._type + (index > 1 ? index : '');
                }
                var name = prefix + '.' + $scope.field + fileExtension();
                if (name != filename) {
                    filename = name;
                    items = [
                        ['', 'None'],
                        ['1', name],
                    ];
                }
                return items;
            };
        },
    };
});

SIREPO.app.directive('rpnBoolean', function(rpnService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: [
            '<select class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in elegantRpnBooleanValues()"></select>',
        ].join(''),
        controller: function($scope) {
            $scope.elegantRpnBooleanValues = function() {
                return rpnService.getRpnBooleanForField($scope.model, $scope.field);
            };
        },
    };
});

SIREPO.app.directive('rpnEditor', function(appState) {
    return {
        scope: {},
        template: [
            '<div class="modal fade" data-backdrop="static" id="elegant-rpn-variables" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<span class="lead modal-title text-info">RPN Variables</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<form name="form" class="form-horizontal">',
                        '<div class="row">',
                          '<div data-ng-if="hasFirstColumn()" class="col-sm-2 text-center"><h5>Name</h5></div>',
                          '<div data-ng-if="hasFirstColumn()" class="col-sm-2 text-center"><h5>Value</h5></div>',
                          '<div data-ng-if="hasSecondColumn()" class="col-sm-offset-2 col-sm-2 text-center"><h5>Name</h5></div>',
                          '<div data-ng-if="hasSecondColumn()" class="col-sm-2 text-center"><h5>Value</h5></div>',
                        '</div>',
                        '<div class="row">',
                          '<div class="form-group-sm" data-ng-repeat="rpnVar in appState.models.rpnVariables">',
                            '<div data-field-editor="\'value\'" data-field-size="2" data-label-size="2" data-custom-label="rpnVar.name" data-model-name="\'rpnVariable\'" data-model="appState.models.rpnVariables[$index]"></div>',
                          '</div>',
                        '</div>',
                      '</form>',

                      '<div data-ng-hide="showAddNewFields" class="row">',
                        '<div class="col-sm-3">',
                          '<button data-ng-click="showAddNewFields = true" class="btn btn-default"><span class="glyphicon glyphicon-plus"></span> Add New</button>',
                        '</div>',
                      '</div>',

                      '<div data-ng-show="showAddNewFields" class="row">',
                        '<br />',
                        '<form name="addNewForm" class="form-horizontal">',
                          '<div class="form-group-sm">',
                            '<div class="col-sm-2">',
                              '<input class="form-control" required data-ng-model="newRpn.name" />',
                            '</div>',
                            '<div data-field-editor="\'value\'" data-field-size="2" data-label-size="0" data-model-name="\'rpnVariable\'" data-model="newRpn"></div>',
                            '<div class="col-sm-4">',
                              '<button formnovalidate data-ng-click="saveVariable()" data-ng-class="{\'disabled\': ! addNewForm.$valid}" class="btn btn-default">Add Variable</button> ',
                              '<button formnovalidate data-ng-click="cancelVariable()" class="btn btn-default">Cancel</button>',
                            '</div>',
                          '</div>',
                        '</form>',
                      '</div>',

                      '<div data-ng-hide="showAddNewFields" class="col-sm-6 pull-right">',
                        '<button data-ng-click="saveChanges()" class="btn btn-primary" data-ng-class="{\'disabled\': ! form.$valid}">Save Changes</button> ',
                        '<button data-ng-click="cancelChanges()" class="btn btn-default">Cancel</button>',
                      '</div>',

                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.showAddNewFields = false;
            $scope.appState = appState;
            $scope.newRpn = {};
            $scope.originalRpnCache = {};
            $scope.isSaved = false;

            $scope.cancelChanges = function() {
                $scope.isSaved = false;
                $('#elegant-rpn-variables').modal('hide');
            };

            $scope.cancelVariable = function() {
                $scope.newRpn = {};
                $scope.showAddNewFields = false;
                $scope.addNewForm.$setPristine();
            };

            $scope.hasFirstColumn = function() {
                if ($scope.showAddNewFields) {
                    return true;
                }
                if (appState.isLoaded()) {
                    return appState.models.rpnVariables.length > 0;
                }
                return false;
            };

            $scope.hasSecondColumn = function() {
                if (appState.isLoaded()) {
                    return appState.models.rpnVariables.length > 1;
                }
                return false;
            };

            $scope.saveVariable = function() {
                appState.models.rpnVariables.push({
                    name: $scope.newRpn.name,
                    value: $scope.newRpn.value,
                });
                $scope.cancelVariable();
            };

            $scope.saveChanges = function() {
                $('#elegant-rpn-variables').modal('hide');
                $scope.isSaved = true;
            };
        },
        link: function(scope, element) {
            $(element).on('show.bs.modal', function() {
                scope.isSaved = false;
                scope.originalRpnCache = appState.clone(appState.models.rpnCache);
            });
            $(element).on('hidden.bs.modal', function() {
                if (scope.isSaved) {
                    for (var i = 0; i < appState.models.rpnVariables.length; i++) {
                        var v = appState.models.rpnVariables[i];
                        appState.models.rpnCache[v.name] = v.value in appState.models.rpnCache
                            ? appState.models.rpnCache[v.value] : parseFloat(v.value);
                    }
                    appState.saveChanges('rpnVariables');
                    scope.isSaved = false;
                }
                else {
                    appState.cancelChanges('rpnVariables');
                    appState.models.rpnCache = scope.originalRpnCache;
                }
                scope.cancelVariable();
                scope.$applyAsync();
            });
            scope.$on('$destroy', function() {
                $(element).off();
            });
        },
    };
});

SIREPO.app.directive('rpnStatic', function(rpnService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: [
            '<div class="form-control-static pull-right">{{ elegantComputedRpnValue(); }}</div>',
        ].join(''),
        controller: function($scope) {
            $scope.elegantComputedRpnValue = function() {
                return rpnService.getRpnValueForField($scope.model, $scope.field);
            };
        },
    };
});

SIREPO.app.directive('rpnValue', function(appState, rpnService) {
    var requestIndex = 0;
    return {
        restrict: 'A',
        require: 'ngModel',
        link: function(scope, element, attrs, ngModel) {
            var rpnVariableName = scope.modelName == 'rpnVariable' ? scope.model.name : null;
            ngModel.$parsers.push(function(value) {
                if (ngModel.$isEmpty(value))
                    return null;
                if (SIREPO.NUMBER_REGEXP.test(value)) {
                    ngModel.$setValidity('', true);
                    var v = parseFloat(value);
                    if (rpnVariableName)
                        rpnService.recomputeCache(rpnVariableName, v);
                    return v;
                }
                requestIndex++;
                var currentRequestIndex = requestIndex;
                rpnService.computeRpnValue(value, function(v, err) {
                    // check for a stale request
                    if (requestIndex != currentRequestIndex)
                        return;
                    ngModel.$setValidity('', err ? false : true);
                    if (rpnVariableName && ! err)
                        rpnService.recomputeCache(rpnVariableName, v);
                });
                return value;
            });
            ngModel.$formatters.push(function(value) {
                if (ngModel.$isEmpty(value))
                    return value;
                return value.toString();
            });
        }
    };
});

SIREPO.app.directive('runSimulationFields', function() {
    return {
        template: [
            '<div>',
              '<div class="col-sm-12" style="margin-bottom: 15px"><div class="row">',
                '<div data-model-field="\'simulationMode\'" data-model-name="\'simulation\'" data-label-size="2"></div>',
              '</div></div>',
              '<div data-model-field="\'visualizationBeamlineId\'" data-model-name="\'simulation\'" data-label-size="2"></div>',
              '<div class="col-sm-5" data-ng-show="visualization.isStateStopped()">',
                '<button class="btn btn-default" data-ng-click="visualization.saveAndRunSimulation()">Start New Simulation</button>',
              '</div>',
            '</div>',
        ].join(''),
    };
});


SIREPO.app.directive('parameterTable', function(appState, panelState, $sce) {
    return {
        restrict: 'A',
        scope: {
        },
        template: [
            '<div data-ng-if="outputInfo">',
              '<div data-basic-editor-panel="" data-want-buttons="" data-view-name="parameterTable" data-parent-controller="visualization">',
                '<form name="form" class="form-horizontal">',
                  '<div data-ng-repeat="item in parameterRows">',
                    '<div class="elegant-parameter-table-row form-group form-group-sm">',
                      '<div class="control-label col-sm-5" data-label-with-tooltip="" data-label="{{ item.name }}" data-tooltip="{{ item.description }}"></div>',
                      '<div class="col-sm-5 elegant-parameter-table-value">{{ item.value }}<span ng-bind-html="item.units"></span></span></div>',
                    '</div>',
                  '</div>',
                '</form>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {

            function fileChanged() {
                if (! $scope.outputInfo) {
                    return;
                }
                // If not found, just set to first file
                $scope.fileInfo = $scope.outputInfo[0];
                $scope.outputInfo.forEach(function (v) {
                    if (v.filename == appState.models.parameterTable.file) {
                        $scope.fileInfo = v;
                    }
                });
                appState.models.parameterTable.file = $scope.fileInfo.filename;
                var pages = [];
                for (var i = 0; i < $scope.fileInfo.pageCount; i++) {
                    pages.push(i);
                }
                appState.models.parameterTable.valueList.page = pages;
                pageChanged();
            }

            function modelsLoaded() {
                if (!appState.models.parameterTable) {
                    appState.models.parameterTable = {
                        file: null,
                        page: null,
                        valueList: {
                            file: null,
                            page: null,
                        },
                    };
                }
            }

            function outputInfoChanged(e, outputInfo) {
                $scope.outputInfo = outputInfo;
                if (! outputInfo) {
                    return;
                }
                var files = [];
                $scope.outputInfo.forEach(function (v) {
                    files.push(v.filename);
                });
                appState.models.parameterTable.valueList.file = files;
                fileChanged();
            }

            function pageChanged() {
                if (! $scope.fileInfo) {
                    return;
                }
                var page = appState.models.parameterTable.page;
                // If no page or more than count, reset to 0
                if (!page || page >= $scope.fileInfo.pageCount) {
                    appState.models.parameterTable.page = page = 0;
                }
                var params = $scope.fileInfo.parameters;
                var defs = $scope.fileInfo.parameterDefinitions;
                var rows = [];
                Object.keys(params).sort(
                    function(a, b) {
                        return a.localeCompare(b);
                    }
                ).forEach(function (k) {
                    rows.push({
                        name: k,
                        value: params[k][page],
                        units: unitsAsHtml(defs[k].units),
                        description: defs[k].description,
                    });
                });
                $scope.parameterRows = rows;
                appState.saveChanges('parameterTable');
            }

            function unitsAsHtml(units) {
                //TODO(robnagler) Needs to be generalized. Don't know all the cases though
                if (units == 'm$be$nc') {
                    return $sce.trustAsHtml(' m<sub>e</sub>c');
                }
                if (/^\w+$/.exec(units)) {
                    return $sce.trustAsHtml(' ' + units);
                }
                if (units) {
                    srlog(units, ': unable to convert elegant units to HTML');
                }
                return $sce.trustAsHtml('');
            }

            $scope.outputInfo = null;
            $scope.appState = appState;
            appState.whenModelsLoaded($scope, modelsLoaded);
            $scope.$on('elementAnimation.outputInfo', outputInfoChanged);
            appState.watchModelFields($scope, ['parameterTable.page'], pageChanged);
            appState.watchModelFields($scope, ['parameterTable.file'], fileChanged);
        }
    };
});


//TODO(pjm): required for stacked modal for editors with fileUpload field, rework into sirepo-components.js
// from http://stackoverflow.com/questions/19305821/multiple-modals-overlay
$(document).on('show.bs.modal', '.modal', function () {
    var zIndex = 1040 + (10 * $('.modal:visible').length);
    $(this).css('z-index', zIndex);
    setTimeout(function() {
        $('.modal-backdrop').not('.modal-stack').css('z-index', zIndex - 1).addClass('modal-stack');
    }, 0);
});
