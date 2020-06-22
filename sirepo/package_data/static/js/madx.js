'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.PLOTTING_COLOR_MAP = 'afmhot';
    SIREPO.appMadxExport = true;
    SIREPO.appImportText = 'Import a lattice (.madx) file';
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="Float2StringArray" class="col-sm-7">',
          '<div data-number-list="" data-field="model[field]" data-info="info" data-type="Float" data-count="2"></div>',
        '</div>',
        '<div data-ng-switch-when="Integer2StringArray" class="col-sm-7">',
          '<div data-number-list="" data-field="model[field]" data-info="info" data-type="Integer" data-count="2"></div>',
        '</div>',
        '<div data-ng-switch-when="Float6StringArray" class="col-sm-7">',
          '<div data-number-list="" data-field="model[field]" data-info="info" data-type="Float" data-count="6"></div>',
        '</div>',
    ].join('');
    SIREPO.appDownloadLinks = [
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
            QUADRUPOLE: 'red',
            QUFRINGE: 'salmon',
            SEXT: 'lightgreen',
            VKICK: 'blue',
            LMIRROR: 'lightblue',
            REFLECT: 'blue',
        },
        elementPic: {
            alpha: ['ALPH'],
            aperture: ['CLEAN', 'COLLIMATOR', 'ECOLLIMATOR', 'MAXAMP', 'PEPPOT', 'RCOL', 'SCRAPER'],
            bend: ['BRAT', 'BUMPER', 'SBEND', 'CSRCSBEND', 'FMULT', 'FTABLE', 'KPOLY', 'KSBEND', 'KQUSE', 'MBUMPER', 'MULT', 'NIBEND', 'NISEPT', 'RBEN', 'SBEN', 'TUBEND'],
            drift: ['CSRDRIFT', 'DRIFT', 'EDRIFT', 'EMATRIX', 'LSCDRIFT'],
            lens: ['LTHINLENS'],
            magnet: ['BMAPXY', 'HKICK', 'KICKER', 'KOCT', 'KQUAD', 'KSEXT', 'MATTER', 'OCTU', 'QUADRUPOLE', 'QUFRINGE', 'SEXT', 'VKICK'],
            malign: ['MALIGN'],
            mirror: ['LMIRROR'],
            recirc: ['RECIRC'],
            rf: ['CEPL', 'FRFMODE', 'FTRFMODE', 'MODRF', 'MRFDF', 'RAMPP', 'RAMPRF', 'RFCA', 'RFCW', 'RFDF', 'RFMODE', 'RFTM110', 'RFTMEZ0', 'RMDF', 'TMCF', 'TRFMODE', 'TWLA', 'TWMTA', 'TWPL'],
            solenoid: ['MAPSOLENOID', 'SOLE'],
            undulator: ['CORGPIPE', 'CWIGGLER', 'GFWIGGLER', 'LSRMDLTR', 'MATR', 'UKICKMAP', 'WIGGLER'],
            watch: ['HMON', 'MARK', 'MONI', 'VMON', 'WATCH'],
            zeroLength: ['BRANCH', 'CENTER', 'CHARGE', 'DSCATTER', 'ELSE', 'EMITTANCE', 'ENERGY', 'FLOOR', 'HISTOGRAM', 'IBSCATTER', 'ILMATRIX', 'IONEFFECTS', 'MAGNIFY', 'MHISTOGRAM', 'PFILTER', 'REFLECT','REMCOR', 'RIMULT', 'ROTATE', 'SAMPLE', 'SCATTER', 'SCMULT', 'SCRIPT', 'SLICE', 'SREFFECTS', 'STRAY', 'TFBDRIVER', 'TFBPICKUP', 'TRCOUNT', 'TRWAKE', 'TWISS', 'WAKE', 'ZLONGIT', 'ZTRANSVERSE'],
        },
    };
});

SIREPO.app.factory('madxService', function(appState, commandService, requestSender, rpnService, $rootScope) {
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
                    bunch.p_central_mev = rpnService.getRpnValue(cmd.p_central) * SIREPO.APP_SCHEMA.constants.ELEGANT_ME_EV;
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

    self.computeModel = function(analysisModel) {
        return 'animation';
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

    commandService.canDeleteCommand = function(command) {
        commandService.deleteCommandWarning = '';
        // Each of these fields must be present at least once
        if (
            [
                'beam',
                'ptc_create_universe',
                'ptc_create_layout',
                'ptc_track',
                'ptc_track_end',
                'ptc_end'
            ].indexOf(command._type) >= 0
        ) {
            if (commandService.findAllComands(command._type).length == 1) {
                commandService.deleteCommandWarning = commandService.formatCommandName(command) + ' is the only ' + command._type;
                return false;
            }
        }
        return true;
    };

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

SIREPO.app.controller('SourceController', function(appState, commandService, latticeService, panelState, $scope) {
    var self = this;

    var cmds = ['beam'];

    $scope.pt = false;
    self.isParticleTrackingEnabled = function () {
        $scope.pt = ((appState.models.simulation || {}).enableParticleTracking === '1');
        return $scope.pt;
    };

    self.reportModel = function() {
        return self.isParticleTrackingEnabled() ? 'bunchReport' : 'twissEllipseReport';
    };

    self.reports = function() {
        return self.isParticleTrackingEnabled() ? self.bunchReports : self.ellipseReports;
    };

    self.plotType = function() {
        return self.isParticleTrackingEnabled() ? 'heatmap' : 'parameter';
    };

    self.headings = function() {
        return self.isParticleTrackingEnabled() ? self.bunchReportHeading : self.twissEllipseReportHeading;
    };

    self.twissEllipseReportHeading = function(modelKey) {
        if (! appState.isLoaded()) {
            return;
        }
        return 'TWISS ELLIPSE';
    };

    function saveCommandList(type) {
        $.extend(
            commandService.findFirstCommand(type),
            appState.models[commandService.commandModelName(type)]
        );
        appState.saveChanges('commands');
    }

    appState.whenModelsLoaded($scope, function() {
        cmds.forEach(function(type) {
            var cmd = commandService.findFirstCommand(type);
            if (! cmd) {
                cmd = appState.models[commandService.createCommand(type)];
                appState.models.commands.push(cmd);
                appState.saveChanges('commands');
            }
            var name = commandService.commandModelName(type);
            appState.models[name] = appState.clone(cmd);
            appState.applicationState()[name] = appState.cloneModel(name);

            $scope.$on(name + '.changed', function() {
                saveCommandList(type);
            });

            $scope.$watch('pt', function (d) {
                //srdbg('PT CH', d);
            });
            $('#sr-command_beam-basicEditor h5').hide();
            $('#sr-command_distribution-basicEditor h5').hide();

        });

        // [1, 2, 3]?
        self.ellipseReports = [1, 2].map(function(id) {
            var modelKey = 'twissEllipseReport' + id;
            return {
                id: id,
                modelKey: modelKey,
                getData: function() {
                    return appState.models[modelKey];
                },
            };
        });
    });

    latticeService.initSourceController(self);
});

SIREPO.app.controller('CommandController', function(commandService, panelState) {
    var self = this;
    self.activeTab = 'basic';
    self.basicNames = [
        'beam', 'option', 'resbeam',
        'ptc_create_layout', 'ptc_create_universe', 'ptc_end',
        'ptc_normal', 'ptc_observe', 'ptc_start', 'ptc_track',
        'ptc_track_end', 'select', 'set', 'show', 'sodd',
        'twiss',
    ];
    self.advancedNames = [];

    self.createElement = function(name) {
        panelState.showModalEditor(commandService.createCommand(name));
    };

    self.titleForName = function(name) {
        return (SIREPO.APP_SCHEMA.view[commandService.commandModelName(name)] || {}).description;
    };
});

SIREPO.app.controller('LatticeController', function(latticeService) {
    var self = this;
    self.latticeService = latticeService;

    self.advancedNames = SIREPO.APP_SCHEMA.constants.advancedElementNames;
    self.basicNames = SIREPO.APP_SCHEMA.constants.basicElementNames;

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[name].description;
    };
});

SIREPO.app.controller('VisualizationController', function(appState, madxService, frameCache, panelState, persistentSimulation, $rootScope, $scope) {
    var self = this;
    self.appState = appState;
    self.panelState = panelState;
    self.outputFiles = [];
    self.outputFileMap = {};

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
        self.simulationAlerts = data.alert || '';
        if (data.frameCount) {
            frameCache.setFrameCount(1);
        }
    }

    self.startSimulation = function() {
        self.simState.saveAndRunSimulation('simulation');
    };

    self.simState = persistentSimulation.initSimulationState(
        $scope,
        madxService.computeModel(),
        handleStatus
    );
});

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-common-footer="nav"></div>',
            '<div data-mad-x-import-dialog=""></div>',
            '<div data-import-dialog="" data-title="Import MAD-X File" data-description="Select a MAD-X file." data-file-formats=".madx"></div>',
        ].join(''),
    };
});

// madxService is required to register with appState
SIREPO.app.directive('appHeader', function(appState, madxService, latticeService) {
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
                  //'<li class="sim-section" data-ng-if="hasSourceCommand()" data-ng-class="{active: nav.isActive(\'source\')}"><a data-ng-href="{{ nav.sectionURL(\'source\') }}"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'lattice\')}"><a data-ng-href="{{ nav.sectionURL(\'lattice\') }}"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a data-ng-href="{{ nav.sectionURL(\'source\') }}"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
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

SIREPO.app.directive('madXLatticeList', function(appState) {
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

SIREPO.app.directive('fileValueButton', function(madxService) {
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
                    return madxService.dataFileURL(modelKey, 0);
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

// TODO(e-carlin): share with elegant
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
            '<label style="margin-right: 1ex">{{ valueLabels[$index] }}</label>',
            '<input class="form-control sr-number-list" data-string-to-number="{{ numberType }}" data-ng-model="values[$index]" data-ng-change="didChange()" class="form-control" style="text-align: right" required />',
            '</div>'
        ].join(''),
        controller: function($scope) {
            $scope.values = null;
            $scope.numberType = $scope.type.toLowerCase();
            //TODO(pjm): share implementation with enumList
            $scope.valueLabels = $scope.info[4];
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
