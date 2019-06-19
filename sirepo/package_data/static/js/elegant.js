'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.USER_MANUAL_URL = 'https://ops.aps.anl.gov/manuals/elegant_latest/elegant.html';
SIREPO.USER_FORUM_URL = 'https://www3.aps.anl.gov/forums/elegant/';
SIREPO.ELEGANT_COMMAND_PREFIX = 'command_';
SIREPO.PLOTTING_COLOR_MAP = 'afmhot';
SIREPO.appImportText = 'Import an elegant command (.ele) or lattice (.lte) file';
//TODO(pjm): provide API for this, keyed by field type
SIREPO.appFieldEditors = [
    '<div data-ng-switch-when="BeamInputFile" class="col-sm-7">',
      '<div data-file-field="field" data-model="model" data-file-type="bunchFile-sourceFile" data-empty-selection-text="No File Selected"></div>',
    '</div>',
    '<div data-ng-switch-when="LatticeBeamlineList" data-ng-class="fieldClass">',
      '<div data-lattice-beamline-list="" data-model="model" data-field="field"></div>',
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
        '<input data-rpn-value="" data-ng-model="model[field]" class="form-control" style="text-align: right" data-lpignore="true" required />',
      '</div>',
      //TODO(pjm): fragile - hide rpnStaic value when in column mode, need better detection this case
      '<div data-ng-hide="{{ fieldSize && fieldSize != \'2\' }}" class="col-sm-2">',
        '<div data-rpn-static="" data-model="model" data-field="field"></div>',
      '</div>',
    '</div>',
    '<div data-ng-switch-when="StringArray" data-ng-class="fieldClass">',
      '<input data-ng-model="model[field]" class="form-control" data-lpignore="true" required />',
    '</div>',
    '<div data-ng-switch-when="ValueList" data-ng-class="fieldClass">',
      '<div class="form-control-static" data-ng-if="model.valueList[field].length == 1">{{ model.valueList[field][0] }}</div>',
      '<select data-ng-if="model.valueList[field].length != 1" class="form-control" data-ng-model="model[field]" data-ng-options="item as item for item in model.valueList[field]"></select>',
    '</div>',
    '<div data-ng-switch-when="FileValueList">',
      '<div data-ng-class="fieldClass">',
        '<div class="input-group">',
          '<select class="form-control" data-ng-model="model[field]" data-ng-options="item as item for item in model[\'valueList\'][field]"></select>',
            '<a href class="btn btn-default input-group-addon elegant-download-button" data-file-value-button="" data-ng-href="{{ fileDownloadURL(model) }}"><span class="glyphicon glyphicon-cloud-download"></span></a>',
        '</div>',
      '</div>',
    '</div>',
    '<div data-ng-switch-when="DistributionTypeStringArray" class="col-sm-7">',
        '<div data-enum-list="" data-field="model[field]" data-info="info" data-type-list="enum[\'DistributionType\']"></div>',
    '</div>',
    '<div data-ng-switch-when="BooleanStringArray" class="col-sm-7">',
        '<div data-enum-list="" data-field="model[field]" data-info="info" data-type-list="enum[\'Boolean\']"></div>',
    '</div>',
    '<div data-ng-switch-when="RandomizeStringArray" class="col-sm-7">',
        '<div data-enum-list="" data-field="model[field]" data-info="info" data-type-list="enum[\'Randomize\']"></div>',
    '</div>',
    '<div data-ng-switch-when="Integer3StringArray" class="col-sm-7">',
        '<div data-number-list="" data-field="model[field]" data-info="info" data-type="Integer" data-count="3"></div>',
    '</div>',
    '<div data-ng-switch-when="Integer6StringArray" class="col-sm-7">',
        '<div data-number-list="" data-field="model[field]" data-info="info" data-type="Integer" data-count="6"></div>',
    '</div>',
    '<div data-ng-switch-when="Float6StringArray" class="col-sm-7">',
        '<div data-number-list="" data-field="model[field]" data-info="info" data-type="Float" data-count="6"></div>',
    '</div>',
].join('');
SIREPO.appDownloadLinks = [
    '<li><a href data-ng-href="{{ dataFileURL(\'csv\') }}">CSV Data File</a></li>',
].join('');
SIREPO.lattice = {
    canReverseBeamline: true,
    elementColor: {
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
        LMIRROR: 'lightblue',
        REFLECT: 'blue',
    },
    elementPic: {
        alpha: ['ALPH'],
        bend: ['BRAT', 'BUMPER', 'CSBEND', 'CSRCSBEND', 'FMULT', 'FTABLE', 'KPOLY', 'KSBEND', 'KQUSE', 'MBUMPER', 'MULT', 'NIBEND', 'NISEPT', 'RBEN', 'SBEN', 'TUBEND'],
        drift: ['CSRDRIFT', 'DRIF', 'EDRIFT', 'EMATRIX', 'LSCDRIFT'],
        aperture: ['CLEAN', 'ECOL', 'MAXAMP', 'RCOL', 'SCRAPER'],
        lens: ['LTHINLENS'],
        magnet: ['BMAPXY', 'HKICK', 'KICKER', 'KOCT', 'KQUAD', 'KSEXT', 'MATTER', 'OCTU', 'QUAD', 'QUFRINGE', 'SEXT', 'VKICK'],
        malign: ['MALIGN'],
        mirror: ['LMIRROR'],
        recirc: ['RECIRC'],
        solenoid: ['MAPSOLENOID', 'SOLE'],
        undulator: ['CORGPIPE', 'CWIGGLER', 'GFWIGGLER', 'LSRMDLTR', 'MATR', 'UKICKMAP', 'WIGGLER'],
        watch: ['HMON', 'MARK', 'MONI', 'PEPPOT', 'VMON', 'WATCH'],
        zeroLength: ['BRANCH', 'CENTER', 'CHARGE', 'DSCATTER', 'ELSE', 'EMITTANCE', 'ENERGY', 'FLOOR', 'HISTOGRAM', 'IBSCATTER', 'ILMATRIX', 'IONEFFECTS', 'MAGNIFY', 'MHISTOGRAM', 'PFILTER', 'REFLECT','REMCOR', 'RIMULT', 'ROTATE', 'SAMPLE', 'SCATTER', 'SCMULT', 'SCRIPT', 'SLICE', 'SREFFECTS', 'STRAY', 'TFBDRIVER', 'TFBPICKUP', 'TRCOUNT', 'TRWAKE', 'TWISS', 'WAKE', 'ZLONGIT', 'ZTRANSVERSE'],
        rf: ['CEPL', 'FRFMODE', 'FTRFMODE', 'MODRF', 'MRFDF', 'RAMPP', 'RAMPRF', 'RFCA', 'RFCW', 'RFDF', 'RFMODE', 'RFTM110', 'RFTMEZ0', 'RMDF', 'TMCF', 'TRFMODE', 'TWLA', 'TWMTA', 'TWPL'],
    },
};

SIREPO.app.factory('elegantService', function(appState, requestSender, rpnService, $rootScope) {
    var self = {};
    var filenameRequired = ['command_floor_coordinates', 'HISTOGRAM', 'SLICE', 'WATCH'];
    var rootScopeListener = null;

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
            updateBeamInputType(cmd);
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
            appState.setModelDefaults(cmd, 'command_sdds_beam');
            cmd.input = appState.models.bunchFile.sourceFile;
            updateBeamInputType(cmd);
        }
        appState.saveQuietly('commands');
    }

    function commandsChanged() {
        var cmd = self.findFirstCommand('run_setup');
        if (cmd && cmd.use_beamline) {
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

    function updateBeamInputType(cmd) {
        // detemine the input file type (elegant or spiffe)
        requestSender.getApplicationData(
            {
                method: 'get_beam_input_type',
                input_file: 'bunchFile-sourceFile.' + cmd.input,
            },
            function(data) {
                if (appState.isLoaded() && data.input_type) {
                    cmd.input_type = data.input_type;
                    // spiffe beams require n_particles_per_ring
                    if (cmd.input_type == 'spiffe' && cmd.n_particles_per_ring == 0) {
                        cmd.n_particles_per_ring = 1;
                    }
                    appState.saveQuietly('commands');
                }
            });
    }

    function updateBunchFromCommand(bunch, cmd) {
        Object.keys(cmd).forEach(function(f) {
            if (f in bunch) {
                bunch[f] = cmd[f];
            }
        });
        bunch.longitudinalMethod = cmd.dp_s_coupling !== 0
            ? 1 // sigma s, sigma dp, dp s coupling
            : ((cmd.emit_z !== 0 || cmd.beta_z !== 0)
               ? 3 // emit z, beta z, alpha z
               : 2); // sigma s, sigma dp, alpha z
    }

    function updateCommandFromBunch(cmd, bunch) {
        Object.keys(bunch).forEach(function(f) {
            if (f in cmd) {
                cmd[f] = bunch[f];
            }
        });

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

    self.commandFileExtension = function(command) {
        //TODO(pjm): keep in sync with template/elegant.py _command_file_extension()
        if (command) {
            if (command._type == 'save_lattice') {
                return '.lte';
            }
            else if (command._type == 'global_settings') {
                return '.txt';
            }
        }
        return '.sdds';
    };

    self.dataFileURL = function(model, index) {
        if (! appState.isLoaded()) {
            return '';
        }
        return requestSender.formatUrl('downloadDataFile', {
            '<simulation_id>': appState.models.simulation.simulationId,
            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
            '<model>': model,
            '<frame>': index,
        });

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

    appState.whenModelsLoaded($rootScope, function() {
        if (rootScopeListener) {
            rootScopeListener();
        }
        // keep source page items in sync with the associated control command
        rootScopeListener = $rootScope.$on('modelChanged', function(e, name) {
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
            else if (filenameRequired.indexOf(name) >= 0) {
                // elegant will crash if these element's have no output filename
                var el = appState.models[name];
                if (el && ! el.filename) {
                    el.filename = '1';
                }
            }
        });
        //TODO(pjm): only required for when viewing after import
        // force update to bunch from command.bunched_beam
        appState.saveChanges('commands');
    });
    return self;
});

SIREPO.app.controller('CommandController', function(appState, elegantService, latticeService, panelState) {
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
        'coupled_twiss_output', 'divide_elements', 'elastic_scattering', 'find_aperture',
        'floor_coordinates', 'frequency_map', 'global_settings', 'ignore_elements',
        'inelastic_scattering', 'insert_elements', 'insert_sceffects', 'ion_effects',
        'linear_chromatic_tracking_setup', 'link_control', 'link_elements', 'modulate_elements',
        'moments_output', 'momentum_aperture', 'optimization_constraint', 'optimization_covariable',
        'parallel_optimization_setup', 'print_dictionary', 'ramp_elements', 'replace_elements',
        'rf_setup', 'rpn_expression', 'rpn_load', 'sasefel',
        'save_lattice', 'sdds_beam', 'slice_analysis', 'steering_element',
        'touschek_scatter', 'transmute_elements','tune_footprint', 'tune_shift_with_amplitude',
        'twiss_analysis',
    ];

    self.createElement = function(name) {
        var model = {
            _id: latticeService.nextId(),
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

SIREPO.app.controller('ElegantSourceController', function(appState, latticeService, panelState, $scope) {
    var self = this;

    self.isBunchSource = function(name) {
        if (appState.isLoaded()) {
            return appState.models.bunchSource.inputSource == name;
        }
        return false;
    };

    latticeService.initSourceController(self);
});

SIREPO.app.controller('LatticeController', function(latticeService) {
    var self = this;
    self.latticeService = latticeService;

    self.advancedNames = [
        'ALPH', 'BGGEXP', 'BMAPXY', 'BMXYZ', 'BRANCH', 'BRAT', 'BUMPER', 'CENTER',
        'CEPL', 'CHARGE', 'CLEAN', 'CORGPIPE',
        'CWIGGLER', 'DSCATTER', 'EDRIFT', 'EHKICK', 'EKICKER', 'ELSE',
        'EMATRIX', 'EMITTANCE', 'ENERGY', 'EVKICK', 'FLOOR',
        'FMULT', 'FRFMODE', 'FTABLE', 'FTRFMODE',
        'GFWIGGLER', 'HISTOGRAM', 'HKICK', 'HMON',
        'IBSCATTER', 'ILMATRIX', 'IONEFFECTS', 'KOCT', 'KPOLY',
        'KQUAD', 'KQUSE', 'KSBEND', 'KSEXT',
        'LMIRROR', 'LRWAKE', 'LSCDRIFT', 'LSRMDLTR', 'LTHINLENS',
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
        'SLICE', 'SOLE', 'SPEEDBUMP', 'SREFFECTS', 'STRAY', 'TFBDRIVER',
        'TFBPICKUP', 'TMCF', 'TRCOUNT', 'TRFMODE',
        'TRWAKE', 'TSCATTER', 'TUBEND', 'TWISS', 'TWLA',
        'TWMTA', 'TWPL', 'UKICKMAP', 'VKICK',
        'VMON', 'WAKE', 'ZLONGIT', 'ZTRANSVERSE',
    ];

    self.basicNames = [
        'CSBEND', 'CSRCSBEND', 'CSRDRIFT',
        'DRIF', 'ECOL', 'KICKER',
        'MARK', 'QUAD', 'SEXT',
        'WATCH', 'WIGGLER',
    ];

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[name].description;
    };
});

SIREPO.app.controller('VisualizationController', function(appState, elegantService, frameCache, panelState, persistentSimulation, $rootScope, $scope) {
    var self = this;
    self.appState = appState;
    self.panelState = panelState;
    self.outputFiles = [];
    self.outputFileMap = {};
    self.statusModel = 'simulationStatus';

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

    function handleStatus(data) {
        self.simulationErrors = data.errors || '';
        if (data.frameCount) {
            frameCache.setFrameCount(parseInt(data.frameCount));
            loadElementReports(data.outputInfo, data.startTime);
        }
        if (self.simState.isStopped()) {
            if (! data.frameCount) {
                if (data.state == 'completed' && ! self.simulationErrors) {
                    // completed with no output, show link to elegant log
                    self.simulationErrors = 'No output produced. View the ' + SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_NAME].longName  + ' log for more information.';
                }
                self.outputFiles = [];
                self.outputFileMap = {};
            }
        }
    }
    self.errorHeader = function() {
        if(! self.simulationErrors || self.simulationErrors == '') {
            return '';
        }
        return SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_NAME].longName + ' ' + (self.simulationErrors.toLowerCase().indexOf('error') >= 0 ? 'Errors:' : 'Warnings:');
    };

    function loadElementReports(outputInfo, startTime) {
        self.outputFiles = [];
        self.outputFileMap = {};
        var animationArgs = {};
        var similarRowCounts = {};

        outputInfo.forEach(function (info) {
            if (info.isAuxFile) {
                return;
            }
            if (! info.columns) {
                return;
            }
            panelState.setError(info.modelKey, null);
            var outputFile = {
                info: info,
                reportType: info.isHistogram ? 'heatmap' : 'parameterWithLattice',
                viewName: (info.isHistogram ? 'heatmap' : 'plot') + 'FrameAnimation',
                filename: info.filename,
                modelAccess: {
                    modelKey: info.modelKey,
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
                SIREPO.ANIMATION_ARGS_VERSION + '5',
                'x',
                'y1',
                'y2',
                'y3',
                'histogramBins',
                'xFileId',
                'plotRangeType',
                'horizontalSize',
                'horizontalOffset',
                'verticalSize',
                'verticalOffset',
                'startTime',
            ];
            var m = null;
            if (appState.models[modelKey]) {
                m = appState.models[modelKey];
                m.startTime = startTime;
                m.xFileId = info.id;
                m.xFile = info.filename;
                m.y1File = info.filename;
                if (info.plottableColumns.indexOf(m.x) < 0) {
                    m.x = info.plottableColumns[0];
                }
                if (! m.plotRangeType) {
                    m.plotRangeType = 'none';
                }
            }
            else {
                m = appState.models[modelKey] = {
                    xFile: info.filename,
                    y1File: info.filename,
                    x: info.plottableColumns[0],
                    xFileId: info.id,
                    startTime: startTime,
                };
                // Only display the first outputFile
                if (i > 0 && ! panelState.isHidden(modelKey)) {
                    panelState.toggleHidden(modelKey);
                }
            }
            appState.setModelDefaults(m, 'elementAnimation');
            m.valueList = {
                x: info.plottableColumns,
                y1: info.plottableColumns,
                xFile: [m.xFile],
                y1File: [m.xFile],
                y2File: info.similarFiles,
                y3File: info.similarFiles,
            };
            m.panelTitle = cleanFilename(m.xFile);
            yFileUpdate(modelKey);
            appState.saveQuietly(modelKey);
            frameCache.setFrameCount(info.pageCount, modelKey);
            if (! info.pageCount) {
                panelState.setError(modelKey, 'No output was generated for this report.');
            }
            appState.watchModelFields(
                $scope,
                [modelKey + '.y2File', modelKey + '.y3File'],
                function () {
                    yFileUpdate(modelKey);
                });
        });
        $rootScope.$broadcast('elementAnimation.outputInfo', outputInfo);
        frameCache.setAnimationArgs(animationArgs);
    }

    function yFileUpdate(modelKey) {
        var m = appState.models[modelKey];
        if (! m.y1 && m.y) {
            m.y1 = m.y;
        }
        ['y1', 'y2', 'y3'].forEach(function(f) {
            var field = f + 'File';
            if (m.valueList[field].indexOf(m[field]) < 0) {
                m[field] = m.xFile;
            }
            var info = self.outputFileMap[m[field]].info;
            m[field + 'Id'] = info.id;
            var cols = m.valueList[f] = appState.clone(info.plottableColumns);
            if (f != 'y1') {
                cols.unshift('None');
            }
            if (!m[f] || cols.indexOf(m[f]) < 0) {
                if (f == 'y1') {
                    m[f] = defaultYColumn(cols, m.x);
                }
                else {
                    m[f] = 'None';
                }
            }
        });
    }

    self.logFileURL = function() {
        return elegantService.dataFileURL(self.simState.model, -1);
    };

    self.startSimulation = function() {
        self.simState.saveAndRunSimulation('simulation');
    };

    self.simState = persistentSimulation.initSimulationState($scope, 'animation', handleStatus, {});

    // override persistentSimulation settings
    self.simState.isInitializing = function() {
        if (self.simState.percentComplete === 0 && self.simState.isProcessing()) {
            return true;
        }
        return self.simState.isStatePending();
    };
});

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-common-footer="nav"></div>',
            '<div data-elegant-import-dialog=""></div>',
        ].join(''),
    };
});

SIREPO.app.directive('appHeader', function(appState, latticeService) {
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
		'<div data-ng-if="nav.isLoaded()" data-sim-sections="">',
                  '<li class="sim-section" data-ng-if="hasSourceCommand()" data-ng-class="{active: nav.isActive(\'source\')}"><a data-ng-href="{{ nav.sectionURL(\'source\') }}"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'lattice\')}"><a data-ng-href="{{ nav.sectionURL(\'lattice\') }}"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>',
                  '<li class="sim-section" data-ng-if="latticeService.hasBeamlines()" data-ng-class="{active: nav.isActive(\'control\')}"><a data-ng-href="{{ nav.sectionURL(\'control\') }}"><span class="glyphicon glyphicon-list-alt"></span> Control</a></li>',
                  '<li class="sim-section" data-ng-if="hasBeamlinesAndCommands()" data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
                '</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
                //  '<div>App-specific setting item</div>',
              '</app-settings>',
              '<app-header-right-sim-list>',
                '<ul class="nav navbar-nav sr-navbar-right">',
                  '<li><a href data-ng-click="showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>',
                '</ul>',
              '</app-header-right-sim-list>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.latticeService = latticeService;

            $scope.hasBeamlinesAndCommands = function() {
                if (! latticeService.hasBeamlines()) {
                    return false;
                }
                return appState.models.commands.length > 0;
            };
            $scope.hasSourceCommand = function() {
                if (! $scope.nav.isLoaded()) {
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

            $scope.showImportModal = function() {
                $('#simulation-import').modal('show');
            };
        },
    };
});

SIREPO.app.directive('commandTable', function(appState, elegantService, latticeService, panelState) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div class="elegant-cmd-table">',
              '<div class="pull-right">',
                '<button class="btn btn-info btn-xs" data-ng-click="newCommand()" accesskey="c"><span class="glyphicon glyphicon-plus"></span> New <u>C</u>ommand</button>',
              '</div>',
              '<p class="lead text-center"><small><em>drag and drop commands or use arrows to reorder the list</em></small></p>',
              '<table class="table table-hover" style="width: 100%; table-layout: fixed">',
                '<tr data-ng-repeat="cmd in commands">',
                  '<td data-ng-drop="true" data-ng-drop-success="dropItem($index, $data)" data-ng-drag-start="selectItem($data)">',
                    '<div class="sr-button-bar-parent pull-right"><div class="sr-button-bar"><button class="btn btn-info btn-xs"  data-ng-disabled="$index == 0" data-ng-click="moveItem(-1, cmd)"><span class="glyphicon glyphicon-arrow-up"></span></button> <button class="btn btn-info btn-xs" data-ng-disabled="$index == commands.length - 1" data-ng-click="moveItem(1, cmd)"><span class="glyphicon glyphicon-arrow-down"></span></button> <button class="btn btn-info btn-xs sr-hover-button" data-ng-click="editCommand(cmd)">Edit</button> <button data-ng-click="expandCommand(cmd)" data-ng-disabled="isExpandDisabled(cmd)" class="btn btn-info btn-xs"><span class="glyphicon" data-ng-class="{\'glyphicon-chevron-up\': isExpanded(cmd), \'glyphicon-chevron-down\': ! isExpanded(cmd)}"></span></button> <button data-ng-click="deleteCommand(cmd)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div></div>',
                    '<div class="elegant-cmd-icon-holder" data-ng-drag="true" data-ng-drag-data="cmd">',
                      '<a style="cursor: move; -moz-user-select: none; font-size: 14px" class="badge sr-badge-icon" data-ng-class="{\'sr-item-selected\': isSelected(cmd) }" href data-ng-click="selectItem(cmd)" data-ng-dblclick="editCommand(cmd)">{{ cmd._type }}</a>',
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
                                    + '.' + f + elegantService.commandFileExtension(model);
                            }
                            else if (schema[f][1] == 'LatticeBeamlineList') {
                                var el = latticeService.elementForId(model[f]);
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
                for (var i = 0; i < $scope.commands.length; i++) {
                    commands.push(commandForId($scope.commands[i]._id));
                }
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
            // expects a negative number to move up, positive to move down
            $scope.moveItem = function(direction, command) {
                var d = direction == 0 ? 0 : (direction > 0 ? 1 : -1);
                var currentIndex = commandIndex(command);
                var newIndex = currentIndex + d;
                if(newIndex >= 0 && newIndex < $scope.commands.length) {
                    var tmp = $scope.commands[newIndex];
                    $scope.commands[newIndex] = command;
                    $scope.commands[currentIndex] = tmp;
                    saveCommands();
                }
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

            appState.whenModelsLoaded($scope, function() {
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
                            if (index >= 0) {
                                appState.models.commands.splice(index + 1, 0, appState.models[name]);
                            }
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
                loadCommands();
            });
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
                if (! appState.isLoaded() || ! $scope.model) {
                    return null;
                }
                var runSetupId = $scope.model._id;
                var res = ['Lattice'];
                var index = 0;
                for (var i = 0; i < appState.models.commands.length; i++) {
                    var cmd = appState.models.commands[i];
                    if (cmd._id == runSetupId) {
                        break;
                    }
                    if (cmd._type == 'save_lattice') {
                        index++;
                        if (cmd.filename) {
                            res.push('save_lattice' + (index > 1 ? index : ''));
                        }
                    }
                }
                if (! $scope.model[$scope.field]) {
                    $scope.model[$scope.field] = res[0];
                }
                return res;
            };
        },
    };
});

SIREPO.app.directive('elementAnimationModalEditor', function(appState, panelState, plotRangeService) {
    return {
        scope: {
            reportInfo: '=',
        },
        template: [
            '<div data-modal-editor="" data-view-name="{{ viewName }}" data-model-data="modelAccess"></div>',
        ].join(''),
        controller: function($scope) {
            var isFirstVisit = true;
            var plotRangeWatchers = [];

            $scope.fieldRange = $scope.reportInfo.info.fieldRange;
            $scope.modelKey = $scope.reportInfo.modelAccess.modelKey;
            $scope.viewName = $scope.reportInfo.viewName;
            $scope.modelAccess = {
                modelKey: $scope.modelKey,
                getData: function() {
                    var data = appState.models[$scope.modelKey];
                    return data;
                },
            };

            function processPlotRange(name, modelKey) {
                plotRangeService.processPlotRange($scope, name, modelKey);
            }

            function registerPlotRangeWatcher(name, modelKey) {
                if (plotRangeWatchers.indexOf(modelKey) >= 0) {
                    return;
                }
                plotRangeWatchers.push(modelKey);
                appState.watchModelFields($scope, [modelKey + '.plotRangeType'], function() {
                    processPlotRange(name, modelKey);
                });
            }

            $scope.$on('sr-tabSelected', function(evt, modelName, modelKey) {
                if (isFirstVisit) {
                    isFirstVisit = false;
                    return;
                }
                if (modelKey == $scope.modelKey) {
                    if ($scope.reportInfo.reportType == 'parameterWithLattice') {
                        panelState.showField(
                            name, 'includeLattice',
                            appState.models[modelKey].valueList.x.indexOf('s') >= 0);
                    }
                    panelState.showField(
                        modelName, 'framesPerSecond',
                        $scope.reportInfo.info.pageCount > 1);
                    registerPlotRangeWatcher(modelName, modelKey);
                    processPlotRange(modelName, modelKey);
                }
            });
        },
    };
});

SIREPO.app.directive('elegantImportDialog', function(appState, elegantService, fileManager, fileUpload, requestSender) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div class="modal fade" data-backdrop="static" id="simulation-import" tabindex="-1" role="dialog">',
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
                              '<label>Select Command (.ele), Lattice (.lte), or ', SIREPO.APP_SCHEMA.productInfo.shortName,' Export (.zip)</label>',
                              '<input id="elegant-file-import" type="file" data-file-model="elegantFile" accept=".ele,.lte,.zip" />',
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
                            '<p>Please upload the files below which are referenced in the ', SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_NAME].longName, ' file.</p>',
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
            $scope.title = 'Import ' + SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_NAME].shortName + ' File';
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
                $('#simulation-import').modal('hide');
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
                        '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        '<file_type>': fileType,
                        // unused param
                        '<simulation_id>': $scope.id,
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
                    folder: fileManager.getActiveFolderPath(),
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

SIREPO.app.directive('fileValueButton', function(elegantService) {
    return {
        controller: function($scope) {
            $scope.fileDownloadURL = function(model) {
                var search = model.file;
                var modelKey;
                model.valueList.file.forEach(function(filename, index) {
                    if (search == filename) {
                        modelKey = model.valueList.modelKey[index];
                    }
                });
                if (modelKey) {
                    return elegantService.dataFileURL(modelKey, 0);
                }
                return '';
            };
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

SIREPO.app.directive('enumList', function() {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            info: '<',
            typeList: '<',
        },
        template: [
            '<div data-ng-repeat="defaultSelection in parseValues() track by $index" style="display: inline-block" >',
                '<label style="margin-right: 1ex">{{valueLabels[$index] || \'Plane \' + $index}}</label>',
                '<select ',
                    'class="form-control elegant-list-value" data-ng-model="values[$index]" data-ng-change="didChange()"',
                    'data-ng-options="item[0] as item[1] for item in typeList">',
                '</select>',
            '</div>'
        ].join(''),
        controller: function($scope) {
            $scope.values = null;
            $scope.valueLabels = ($scope.info[4] || '').split(/\s*,\s*/);
            $scope.didChange = function() {
                $scope.field = $scope.values.join(', ');
            };
            $scope.parseValues = function() {
                if ($scope.field && ! $scope.values) {
                    $scope.values = $scope.field.split(/\s*,\s*/);
                }
                return $scope.values;
            };
        },
    };
});

SIREPO.app.directive('numberList', function() {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            info: '<',
            type: '@',
            count: '@',
        },
        template: [
            '<div data-ng-repeat="defaultSelection in parseValues() track by $index" style="display: inline-block" >',
            '<label style="margin-right: 1ex">{{valueLabels[$index] || \'Plane \' + $index}}</label>',
            '<input class="form-control elegant-list-value" data-string-to-number="{{ numberType }}" data-ng-model="values[$index]" data-ng-change="didChange()" class="form-control" style="text-align: right" required />',
            '</div>'
        ].join(''),
        controller: function($scope) {
            $scope.values = null;
            $scope.numberType = $scope.type.toLowerCase();
            //TODO(pjm): share implementation with enumList
            $scope.valueLabels = ($scope.info[4] || '').split(/\s*,\s*/);
            $scope.didChange = function() {
                $scope.field = $scope.values.join(', ');
            };
            $scope.parseValues = function() {
                if ($scope.field && ! $scope.values) {
                    $scope.values = $scope.field.split(/\s*,\s*/);
                }
                return $scope.values;
            };
        },
    };
});

SIREPO.app.directive('outputFileField', function(appState, elegantService) {
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

            $scope.items = function() {
                if (! $scope.model) {
                    return items;
                }
                var prefix = $scope.model.name;
                if ($scope.model._type) {
                    var index = 0;
                    for (var i = 0; i < appState.models.commands.length; i++) {
                        var m = appState.models.commands[i];
                        if (m._type == $scope.model._type) {
                            index++;
                            if (m == $scope.model) {
                                break;
                            }
                        }
                    }
                    prefix = $scope.model._type + (index > 1 ? index : '');
                }
                var name = prefix + '.' + $scope.field + elegantService.commandFileExtension($scope.model);
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
                      '<form name="form" class="form-horizontal" autocomplete="off">',
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
                        '<form name="addNewForm" class="form-horizontal" autocomplete="off">',
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
                        '<button data-ng-click="saveChanges()" class="btn btn-primary" data-ng-disabled="! form.$valid">Save Changes</button> ',
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
            var range = {
                min: scope.info[4],
                max: scope.info[5],
            };
            ngModel.$parsers.push(function(value) {
                requestIndex++;
                var currentRequestIndex = requestIndex;
                if (ngModel.$isEmpty(value)) {
                    return null;
                }
                if (SIREPO.NUMBER_REGEXP.test(value)) {
                    var v = parseFloat(value);
                    if (rpnVariableName) {
                        rpnService.recomputeCache(rpnVariableName, v);
                    }
                    if (range.min != undefined && v < range.min) {
                        return undefined;
                    }
                    if (range.max != undefined && v > range.max) {
                        return undefined;
                    }
                    ngModel.$setValidity('', true);
                    return v;
                }
                rpnService.computeRpnValue(value, function(v, err) {
                    // check for a stale request
                    if (requestIndex != currentRequestIndex) {
                        return;
                    }
                    ngModel.$setValidity('', err ? false : true);
                    if (rpnVariableName && ! err) {
                        rpnService.recomputeCache(rpnVariableName, v);
                    }
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

SIREPO.app.directive('runSimulationFields', function() {
    return {
        template: [
            '<div>',
              '<div class="col-sm-12" style="margin-bottom: 15px"><div class="row">',
                '<div data-model-field="\'simulationMode\'" data-model-name="\'simulation\'" data-label-size="2"></div>',
              '</div></div>',
              '<div data-model-field="\'visualizationBeamlineId\'" data-model-name="\'simulation\'" data-label-size="2"></div>',
              '<div class="col-sm-5" data-ng-show="visualization.simState.isStopped()">',
                '<button class="btn btn-default" data-ng-click="visualization.startSimulation()">Start New Simulation</button>',
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
              '<div data-basic-editor-panel="" data-want-buttons="" data-view-name="parameterTable">',
                '<form name="form" class="form-horizontal" autocomplete="off">',
                  '<div data-ng-repeat="item in parameterRows">',
                    '<div class="sr-parameter-table-row form-group">',
                      '<div class="control-label col-sm-5" data-label-with-tooltip="" data-label="{{ item.name }}" data-tooltip="{{ item.description }}"></div>',
                      '<div class="col-sm-5 form-control-static">{{ item.value }}<span ng-bind-html="item.units"></span></span></div>',
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
                var modelKeys = [];
                $scope.outputInfo.forEach(function (v) {
                    files.push(v.filename);
                    modelKeys.push(v.modelKey);
                });
                appState.models.parameterTable.valueList.file = files;
                appState.models.parameterTable.valueList.modelKey = modelKeys;
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
                if (! params) {
                    return;
                }
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
                //TODO(pjm): could generalize, see "special characters" section
                // http://www.aps.anl.gov/Accelerator_Systems_Division/Accelerator_Operations_Physics/manuals/SDDStoolkit/SDDStoolkitsu66.html
                if (units == 'm$be$nc') {
                    return $sce.trustAsHtml(' m<sub>e</sub>c');
                }
                if (units == 'm$a2$n') {
                    return $sce.trustAsHtml(' m<sup>2</sup>');
                }
                if (units == '1/m$a2$n') {
                    return $sce.trustAsHtml(' 1/(m<sup>2</sup>)');
                }
                if (units == '1/(2$gp$r)') {
                    return $sce.trustAsHtml(' 1/(2𝜋)');
                }
                if (/^[\w\/]+$/.exec(units)) {
                    return $sce.trustAsHtml(' ' + units);
                }
                if (units) {
                    srlog(units, ': unable to convert ' + SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_NAME].longName + ' units to HTML');
                }
                return $sce.trustAsHtml('');
            }

            $scope.outputInfo = null;
            appState.whenModelsLoaded($scope, function() {
                $scope.$on('elementAnimation.outputInfo', outputInfoChanged);
                appState.watchModelFields($scope, ['parameterTable.page'], pageChanged);
                appState.watchModelFields($scope, ['parameterTable.file'], fileChanged);
                modelsLoaded();
            });
        }
    };
});

SIREPO.app.directive('srBunchEditor', function(appState, panelState) {
    return {
        restrict: 'A',
        controller: function($scope) {
            function updateHalton() {
                panelState.showField('bunch', 'halton_radix', appState.models.bunch.optimized_halton == '0');
            }

            function updateLongitudinalFields() {
                var method = parseInt(appState.models.bunch.longitudinalMethod);
                panelState.showField('bunch', 'sigma_s', method == 1 || method == 2);
                panelState.showField('bunch', 'sigma_dp', method == 1 || method == 2);
                panelState.showField('bunch', 'dp_s_coupling', method == 1);
                panelState.showField('bunch', 'alpha_z', method == 2 || method == 3);
                panelState.showField('bunch', 'emit_z', method == 3);
                panelState.showField('bunch', 'beta_z', method == 3);
            }

            $scope.$on('sr-tabSelected', function(evt) {
                updateHalton();
                updateLongitudinalFields();
            });

            appState.whenModelsLoaded($scope, function() {
                appState.watchModelFields($scope, ['bunch.optimized_halton'], updateHalton);
                appState.watchModelFields($scope, ['bunch.longitudinalMethod'], updateLongitudinalFields);
            });
        },
    };
});
