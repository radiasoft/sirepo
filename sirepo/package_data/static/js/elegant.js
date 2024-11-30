'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.FILE_UPLOAD_TYPE = {
        'bunchFile-sourceFile': '.sdds,.h5',
    };
    SIREPO.PLOTTING_COLOR_MAP = 'afmhot';
    SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL = true;
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="BeamInputFile" class="col-sm-7">',
          '<div data-file-field="field" data-model="model" data-file-type="bunchFile-sourceFile" data-empty-selection-text="No File Selected"></div>',
        '</div>',
        '<div data-ng-switch-when="ElegantLatticeList" data-ng-class="fieldClass">',
          '<div data-elegant-lattice-list="" data-model="model" data-field="field"></div>',
        '</div>',
        '<div data-ng-switch-when="InputFileXY" class="col-sm-7">',
          '<div data-input-file-x-y="" data-model-name="modelName" data-model="model" data-field="field"></div>',
        '</div>',
        '<div data-ng-switch-when="StringArray" data-ng-class="fieldClass">',
          '<input data-ng-model="model[field]" class="form-control" data-lpignore="true" required />',
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
        '<div data-ng-switch-when="Float2StringArray" class="col-sm-7">',
          '<div data-number-list="" data-field="model[field]" data-info="info" data-type="Float" data-count="2"></div>',
        '</div>',
    ].join('');
    SIREPO.appDownloadLinks = [
        '<li data-ng-if="::hasDataFile"><a href data-ng-href="{{ dataFileURL(\'csv\') }}">CSV Data File</a></li>',
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
            aperture: ['APCONTOUR', 'CLEAN', 'ECOL', 'MAXAMP', 'PEPPOT', 'RCOL', 'SCRAPER', 'TAPERAPC', 'TAPERAPE', 'TAPERAPR'],
            bend: ['BRAT', 'BUMPER', 'CCBEND', 'CSBEND', 'CSRCSBEND', 'FMULT', 'FTABLE', 'KPOLY', 'KSBEND', 'KQUSE', 'MBUMPER', 'MULT', 'NIBEND', 'NISEPT', 'RBEN', 'SBEN', 'TUBEND'],
            drift: ['CSRDRIFT', 'DRIF', 'EDRIFT', 'EMATRIX', 'LSCDRIFT'],
            lens: ['LTHINLENS'],
            magnet: ['BMAPXY', 'BOFFAXE', 'HKICK', 'KICKER', 'KOCT', 'KQUAD', 'KSEXT', 'MATTER', 'OCTU', 'POLYSERIES', 'QUAD', 'QUFRINGE', 'SEXT', 'VKICK'],
            malign: ['MALIGN'],
            mirror: ['LMIRROR'],
            recirc: ['RECIRC'],
            rf: ['CEPL', 'FRFMODE', 'FTRFMODE', 'MODRF', 'MRFDF', 'RAMPP', 'RAMPRF', 'RFCA', 'RFCW', 'RFDF', 'RFMODE', 'RFTM110', 'RFTMEZ0', 'RMDF', 'SHRFDF', 'TMCF', 'TRFMODE', 'TWLA', 'TWMTA', 'TWPL'],
            solenoid: ['MAPSOLENOID', 'SOLE'],
            undulator: ['CORGPIPE', 'CWIGGLER', 'GFWIGGLER', 'LSRMDLTR', 'MATR', 'UKICKMAP', 'WIGGLER'],
            watch: ['HMON', 'MARK', 'MONI', 'VMON', 'WATCH'],
            zeroLength: ['BRANCH', 'CENTER', 'CHARGE', 'DSCATTER', 'ELSE', 'EMITTANCE', 'ENERGY', 'FLOOR', 'HISTOGRAM', 'IBSCATTER', 'ILMATRIX', 'IONEFFECTS', 'MAGNIFY', 'MHISTOGRAM', 'PFILTER', 'REFLECT','REMCOR', 'RIMULT', 'ROTATE', 'SAMPLE', 'SCATTER', 'SCMULT', 'SCRIPT', 'SLICE', 'SREFFECTS', 'STRAY', 'TFBDRIVER', 'TFBPICKUP', 'TRCOUNT', 'TRWAKE', 'TWISS', 'WAKE', 'ZLONGIT', 'ZTRANSVERSE'],
        },
    };
});

SIREPO.app.factory('elegantService', function(appState, commandService, requestSender, rpnService, $rootScope) {
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
                cmd.p_central = rpnService.getRpnValue(bunch.p_central_mev) / SIREPO.APP_SCHEMA.constants.ELEGANT_ME_EV;
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
        const rscmd = self.findFirstCommand('run_setup');
        if (rscmd && rscmd.use_beamline) {
            appState.models.simulation.visualizationBeamlineId = rscmd.use_beamline;
            appState.saveQuietly('simulation');
        }

        // update bunchSource, bunchFile, bunch models
        const bcmd = self.findFirstCommand(['bunched_beam', 'sdds_beam']);
        if (! bcmd) {
            return;
        }
        appState.models.bunchSource.inputSource = bcmd._type;
        appState.saveQuietly('bunchSource');
        const bunch = appState.models.bunch;
        if (rscmd) {
            if (rpnService.getRpnValue(rscmd.p_central_mev) !== 0) {
                bunch.p_central_mev = rscmd.p_central_mev;
            }
            else {
                bunch.p_central_mev = rpnService.getRpnValue(rscmd.p_central) * SIREPO.APP_SCHEMA.constants.ELEGANT_ME_EV;
            }
        }
        if (bcmd._type == 'bunched_beam') {
            updateBunchFromCommand(bunch, bcmd);
        }
        else {
            appState.models.bunchFile.sourceFile = bcmd.input;
            appState.saveQuietly('bunchFile');
        }
        // need to update source reports.
        appState.saveChanges('bunch');
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
        requestSender.sendStatefulCompute(
            appState,
            function(data) {
                if (appState.isLoaded() && data.input_type) {
                    cmd.input_type = data.input_type;
                    // spiffe beams require n_particles_per_ring
                    if (cmd.input_type == 'spiffe' && cmd.n_particles_per_ring == 0) {
                        cmd.n_particles_per_ring = 1;
                    }
                    appState.saveQuietly('commands');
                }
            },
            {
                method: 'get_beam_input_type',
                args: {
                    input_file: 'bunchFile-sourceFile.' + cmd.input,
                }
            }
        );
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
        updateTwissFromBunch(cmd, bunch);
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
        updateTwissFromBunch(cmd, bunch);
    }

    function updateTwissFromBunch(bunchedBeam, bunch) {
        if (bunchedBeam.use_twiss_command_values == '1') {
            return;
        }
        var cmd = self.findFirstCommand('twiss_output');
        if (cmd) {
            ['beta', 'alpha', 'eta', 'etap'].forEach(function(prefix) {
                ['_x', '_y'].forEach(function(suffix) {
                    var f = prefix + suffix;
                    cmd[f] = bunch[f];
                });
            });
        }
    }

    self.computeModel = function(analysisModel) {
        return 'animation';
    };

    self.dataFileURL = function(model, index) {
        if (! appState.isLoaded()) {
            return '';
        }
        return requestSender.formatUrl('downloadRunFile', {
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

    appState.setAppService(self);

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

    // overrides commandService.commandFileExtension for elegant file extensions
    commandService.commandFileExtension = function(command) {
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

    return self;
});

SIREPO.app.controller('CommandController', function(appState, commandService, latticeService, panelState) {
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
        'amplification_factors', 'analyze_map', 'aperture_data', 'change_particle', 'change_start', 'chaos_map',
        'closed_orbit', 'correct', 'correct_tunes', 'correction_matrix_output',
        'coupled_twiss_output', 'divide_elements', 'elastic_scattering', 'find_aperture',
        'floor_coordinates', 'frequency_map', 'global_settings', 'ignore_elements',
        'inelastic_scattering', 'insert_elements', 'insert_sceffects', 'ion_effects',
        'linear_chromatic_tracking_setup', 'link_control', 'link_elements', 'modulate_elements',
        'moments_output', 'momentum_aperture', 'obstruction_data', 'optimization_constraint', 'optimization_covariable',
        'parallel_optimization_setup', 'print_dictionary', 'ramp_elements', 'replace_elements',
        'rf_setup', 'rpn_expression', 'rpn_load', 'sasefel',
        'save_lattice', 'sdds_beam', 'set_reference_particle_output', 'slice_analysis', 'steering_element',
        'touschek_scatter', 'transmute_elements','tune_footprint', 'tune_shift_with_amplitude',
        'twiss_analysis',
    ];

    self.createElement = function(name) {
        var model = {
            _id: latticeService.nextId(),
            _type: name,
        };
        appState.setModelDefaults(model, commandService.commandModelName(name));
        var modelName = commandService.commandModelName(model._type);
        appState.models[modelName] = model;
        panelState.showModalEditor(modelName);
    };

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[commandService.commandModelName(name)].description;
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
        'ALPH', 'APCONTOUR', 'BEAMBEAM', 'BGGEXP', 'BMAPXY', 'BMXYZ', 'BOFFAXE', 'BRANCH', 'BRAT', 'BUMPER', 'CCBEND', 'CENTER',
        'CEPL', 'CHARGE', 'CLEAN', 'CORGPIPE',
        'CWIGGLER', 'DSCATTER', 'EDRIFT', 'EHKICK', 'EKICKER', 'ELSE',
        'EMATRIX', 'EMITTANCE', 'ENERGY', 'EVKICK', 'FLOOR',
        'FMULT', 'FRFMODE', 'FTABLE', 'FTRFMODE',
        'GFWIGGLER', 'GKICKMAP', 'HISTOGRAM', 'HKICK', 'HMON',
        'IBSCATTER', 'ILMATRIX', 'IONEFFECTS', 'KOCT', 'KPOLY',
        'KQUAD', 'KQUSE', 'KSBEND', 'KSEXT',
        'LMIRROR', 'LRWAKE', 'LSCDRIFT', 'LSRMDLTR', 'LTHINLENS',
        'MAGNIFY', 'MALIGN', 'MAPSOLENOID', 'MATR',
        'MATTER', 'MAXAMP', 'MBUMPER', 'MHISTOGRAM',
        'MODRF', 'MONI', 'MRFDF', 'MULT',
        'NIBEND', 'NISEPT', 'OCTU', 'PEPPOT',
        'PFILTER', 'POLYSERIES', 'QUFRINGE', 'RAMPP', 'RAMPRF',
        'RBEN', 'RCOL', 'RECIRC', 'REFLECT',
        'REMCOR', 'RFCA', 'RFCW', 'RFDF',
        'RFMODE', 'RFTM110', 'RFTMEZ0', 'RIMULT',
        'RMDF', 'ROTATE', 'SAMPLE', 'SBEN',
        'SCATTER', 'SCMULT', 'SCRAPER', 'SCRIPT', 'SHRFDF',
        'SLICE', 'SOLE', 'SPEEDBUMP', 'SREFFECTS', 'STRAY', 'TAPERAPC', 'TAPERAPE', 'TAPERAPR', 'TFBDRIVER',
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

SIREPO.app.controller('VisualizationController', function(appState, elegantService, frameCache, panelState, persistentSimulation, stringsService, $rootScope, $scope) {
    var self = this;
    self.simScope = $scope;
    self.appState = appState;
    self.panelState = panelState;
    self.outputFiles = [];
    self.outputFileMap = {};

    function cleanFilename(fn) {
        fn = fn.replace(/\-\%.*/, '');
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

    self.simHandleStatus = function (data) {
        self.simulationAlerts = data.alert || '';
        if (data.frameCount) {
            frameCache.setFrameCount(parseInt(data.frameCount));
            loadElementReports(data.outputInfo);
        }
        if (self.simState.isStopped()) {
            if (! data.frameCount) {
                if (data.state == 'completed' && ! self.simulationAlerts) {
                    // completed with no output, show link to elegant log
                    self.simulationAlerts = 'No output produced. View the ' + SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_NAME].longName  + ' log for more information.';
                }
                self.outputFiles = [];
                self.outputFileMap = {};
            }
        }
    };

    self.errorHeader = function() {
        if(! self.simulationAlerts || self.simulationAlerts == '') {
            return '';
        }
        return SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_NAME].longName + ' ' + (self.simulationAlerts.toLowerCase().indexOf('error') >= 0 ? 'Errors:' : 'Warnings:');
    };

    function loadElementReports(outputInfo) {
        self.outputFiles = [];
        self.outputFileMap = {};
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
            var m = null;
            if (appState.models[modelKey]) {
                m = appState.models[modelKey];
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
                };
                // Only display the first outputFile
                if (i > 0 && ! panelState.isHidden(modelKey)) {
                    panelState.toggleHidden(modelKey);
                }
            }
            if (outputFile.reportType != 'heatmap') {
                m.aspectRatio = 4.0 / 7;
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
            m.latticeId = info.latticeId;
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

    self.runningStatusText = function() {
        if (appState.isLoaded()) {
            var res = self.simState.stateAsText();
            var sim = appState.applicationState().simulation;
            if (sim.simulationMode == 'parallel') {
                res += ' in Parallel';
            }
            return res + self.simState.dots;
        }
        return '';
    };

    self.startButtonLabel = function() {
        return stringsService.startButtonLabel();
    };

    self.startSimulation = function() {
        self.simState.saveAndRunSimulation('simulation');
    };

    self.stopButtonLabel = function() {
        return stringsService.stopButtonLabel();
    };

    self.simState = persistentSimulation.initSimulationState(self);

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
        template: `
            <div data-common-footer="nav"></div>
            <div data-elegant-import-dialog=""></div>
        `,
    };
});

// elegantService is required to register with appState
SIREPO.app.directive('appHeader', function(appState, elegantService, latticeService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: `
            <div data-app-header-brand="" data-app-url="/en/particle-accelerators.html"></div>
            <div data-app-header-left="nav"></div>
            <div data-app-header-right="nav">
              <app-header-right-sim-loaded>
                <div data-ng-if="nav.isLoaded()" data-sim-sections="">
                  <li class="sim-section" data-ng-if="hasSourceCommand()" data-ng-class="{active: nav.isActive(\'source\')}"><a data-ng-href="{{ nav.sectionURL(\'source\') }}"><span class="glyphicon glyphicon-flash"></span> Source</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'lattice\')}"><a data-ng-href="{{ nav.sectionURL(\'lattice\') }}"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>
                  <li class="sim-section" data-ng-if="latticeService.hasBeamlines()" data-ng-class="{active: nav.isActive(\'control\')}"><a data-ng-href="{{ nav.sectionURL(\'control\') }}"><span class="glyphicon glyphicon-list-alt"></span> Control</a></li>
                  <li class="sim-section" data-ng-if="hasBeamlinesAndCommands()" data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
              </app-settings>
              <app-header-right-sim-list>
                <ul class="nav navbar-nav sr-navbar-right">
                  <li><a href data-ng-click="showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>
                </ul>
              </app-header-right-sim-list>
            </div>
        `,
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

SIREPO.app.directive('elegantLatticeList', function(appState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <select class="form-control" data-ng-model="model[field]" data-ng-options="name as name for name in elegantLatticeList()"></select>
        `,
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
        template: `
            <div data-modal-editor="" data-view-name="{{ viewName }}" data-model-data="modelAccess"></div>
        `,
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
        template: `
            <div style="display: inline-block" data-file-field="field" data-model="model" data-model-name="modelName" data-empty-selection-text="No File Selected"></div>
            <label style="margin: 0 1ex">X</label>
            <input data-ng-model="model[fieldX()]" style="display: inline-block; width: 8em" class="form-control" />
            <label style="margin: 0 1ex">Y</label>
            <input data-ng-model="model[fieldY()]" style="display: inline-block; width: 8em" class="form-control" />
        `,
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
        template: `
            <div data-ng-repeat="defaultSelection in parseValues() track by $index" style="display: inline-block" >
                <label style="margin-right: 1ex">{{valueLabels[$index] || 'Plane ' + $index}}</label>
                <select
                    class="form-control sr-number-list" data-ng-model="values[$index]" data-ng-change="didChange()"
                    data-ng-options="item[0] as item[1] for item in typeList">
                </select>
            </div>
        `,
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

SIREPO.app.directive('parameterTable', function(appState, panelState, $sce) {
    return {
        restrict: 'A',
        scope: {
        },
        template: `
            <div data-ng-if="outputInfo">
              <div data-basic-editor-panel="" data-want-buttons="" data-view-name="parameterTable">
                <form name="form" class="form-horizontal" autocomplete="off">
                  <div data-ng-repeat="item in parameterRows">
                    <div class="sr-parameter-table-row form-group">
                      <div class="control-label col-sm-5" data-label-with-tooltip="" data-label="{{ item.name }}" data-tooltip="{{ item.description }}"></div>
                      <div class="col-sm-5 form-control-static">{{ item.value }}<span ng-bind-html="item.units"></span></span></div>
                    </div>
                  </div>
                </form>
              </div>
            </div>
        `,
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

            function updateEmittance() {
                var bunch = appState.models.bunch;
                ['emit_x', 'emit_nx', 'emit_y', 'emit_ny'].forEach(function(f) {
                    if (panelState.isActiveField('bunch', f) && bunch[f] != 0) {
                        var prefix;
                        if (f.indexOf('emit_n') == 0) {
                            prefix = 'emit_';
                        }
                        else {
                            prefix = 'emit_n';
                        }
                        var dir = f.charAt(f.length - 1);
                        bunch[prefix + dir] = 0;
                    }
                });
            }

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
                appState.watchModelFields(
                    $scope,
                    ['bunch.emit_x', 'bunch.emit_y', 'bunch.emit_nx', 'bunch.emit_ny'],
                    updateEmittance);
            });
        },
    };
});

SIREPO.app.directive('viewLogModalWrapper', function() {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <a href data-ng-click="viewLog()">View Log</a>
            <div data-view-log-modal data-download-log="downloadLog" data-log-html="log" data-log-is-loading="logIsLoading" data-modal-id="modalId"></div>
        `,
        controller: function(appState, elegantService, requestSender, $scope) {
            $scope.logIsLoading = false;
            $scope.log = null;
            $scope.logPath = null;
            $scope.modalId = 'sr-view-log-modal';

            $scope.downloadLog = function() {
                var m = appState.models.simulationStatus.animation.computeModel;
                if (! m) {
                    return '';
                }
                return requestSender.formatUrl('downloadRunFile', {
                    '<simulation_id>': appState.models.simulation.simulationId,
                    '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                    '<model>': m,
                    '<frame>': -1,
                });
            };

            $scope.viewLog = function () {
                $scope.logIsLoading = true;
                $('#' + $scope.modalId).modal('show');
                requestSender.sendAnalysisJob(
                    appState,
                    (data) => {
                        $scope.logIsLoading = false;
                        $scope.log = data.html;
                    },
                    {
                        method: 'log_to_html',
                        computeModel: elegantService.computeModel(),
                        simulationId: appState.models.simulation.simulationId
                    }
                );
            };
        },
    };
});
