'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.PLOTTING_COLOR_MAP = 'afmhot';
    SIREPO.SINGLE_FRAME_ANIMATION = ['twissAnimation', 'twissFromParticlesAnimation'];
    SIREPO.appReportTypes = [
        '<div data-ng-switch-when="matchSummaryAnimation" data-match-summary-panel="" class="sr-plot"></div>',
    ].join('');
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="FloatArray" data-ng-class="fieldClass">',
          '<input data-ng-model="model[field]" class="form-control" data-lpignore="true" required />',
        '</div>',
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
    SIREPO.lattice = {
        canReverseBeamline: true,
        elementColor: {
            OCTUPOLE: 'yellow',
            QUADRUPOLE: 'red',
            SEXTUPOLE: 'lightgreen',
            VKICKER: 'blue',
        },
        elementPic: {
            aperture: ['COLLIMATOR', 'ECOLLIMATOR', 'RCOLLIMATOR'],
            bend: ['RBEND', 'SBEND'],
            drift: ['DRIFT'],
            lens: ['NLLENS'],
            magnet: ['HACDIPOLE', 'HKICKER', 'KICKER', 'MATRIX', 'MULTIPOLE', 'OCTUPOLE', 'QUADRUPOLE', 'RFMULTIPOLE', 'SEXTUPOLE', 'VACDIPOLE', 'VKICKER'],
            rf: ['CRABCAVITY', 'RFCAVITY', 'TWCAVITY'],
            solenoid: ['SOLENOID'],
            watch: ['INSTRUMENT', 'HMONITOR', 'MARKER', 'MONITOR', 'PLACEHOLDER', 'VMONITOR'],
            zeroLength: ['BEAMBEAM', 'CHANGEREF', 'DIPEDGE', 'SROTATION', 'TRANSLATION', 'XROTATION', 'YROTATION'],
        },
    };
});

SIREPO.app.factory('madxService', function(appState, commandService, requestSender, rpnService) {
    var self = {};
    rpnService.isCaseInsensitive = true;
    self.twissFields = ['betx', 'bety', 'alfx', 'alfy', 'x', 'px', 'y', 'py'];

    self.computeModel = function(analysisModel) {
        return 'animation';
    };

    self.isParticleSimulation = function() {
        return commandService.findFirstCommand('ptc_create_layout') ? true : false;
    };

    appState.setAppService(self);

    commandService.canDeleteCommand = function(command) {
        commandService.deleteCommandWarning = '';
        if (
            ['beam'].indexOf(command._type) >= 0
        ) {
            if (commandService.findAllComands(command._type).length == 1) {
                commandService.deleteCommandWarning = commandService.formatCommandName(command) + ' is the only ' + command._type;
                return false;
            }
        }
        return true;
    };

    commandService.commandFileExtension = function(command) {
        return '.tfs';
    };

    return self;
});

SIREPO.app.controller('SourceController', function(appState, commandService, latticeService, madxService, $scope) {
    var self = this;

    function loadBeamCommand() {
        var cmd = commandService.findFirstCommand('beam');
        if (! cmd) {
            cmd = appState.models[commandService.createCommand('beam')];
            appState.models.commands.push(cmd);
            appState.saveQuietly('commands');
        }
        var name = commandService.commandModelName('beam');
        appState.models[name] = appState.clone(cmd);
        appState.applicationState()[name] = appState.cloneModel(name);
    }

    function saveBeamCommand() {
        var beam = commandService.findFirstCommand('beam');
        $.extend(
            beam,
            appState.models[commandService.commandModelName('beam')]
        );
        appState.saveQuietly('commands');
    }

    self.isParticleTrackingEnabled = function () {
        if (appState.isLoaded()) {
            return appState.applicationState().simulation.enableParticleTracking == '1';
        }
        return false;
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
        return 'Twiss Ellipse';
    };

    appState.whenModelsLoaded($scope, function() {
        loadBeamCommand();
        $scope.$on('bunch.changed', saveBeamCommand);

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

SIREPO.app.controller('CommandController', function(appState, commandService, latticeService, madxService, panelState, $scope) {
    var self = this;
    self.activeTab = 'basic';
    self.basicNames = [
        'beam', 'beta0', 'constraint', 'ealign', 'emit', 'endmatch', 'global', 'jacobian', 'lmdif',
        'makethin', 'match', 'migrad', 'option',
        'ptc_create_layout', 'ptc_create_universe', 'ptc_end',
        'ptc_normal', 'ptc_observe', 'ptc_select', 'ptc_setswitch', 'ptc_start',
        'ptc_track', 'ptc_track_end', 'ptc_trackline', 'ptc_twiss', 'resbeam', 'savebeta', 'select',
        'set', 'show', 'sodd', 'touschek', 'twiss', 'use', 'vary',
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

SIREPO.app.controller('VisualizationController', function(appState, commandService, madxService, frameCache, panelState, persistentSimulation, requestSender, $scope) {
    var self = this;
    self.appState = appState;
    self.errorMessage = '';
    self.outputFileMap = {};
    self.outputFiles = [];
    self.panelState = panelState;
    self.simScope = $scope;

    function cleanFilename(fn) {
        return fn.replace(/\.(?:tfs)/g, '');
    }

    self.simHandleStatus = function(data) {
        self.errorMessage = data.error;
        if (data.error) {
            data.frameCount = 0;
        }
        if (data.frameCount && data.outputInfo) {
            frameCache.setFrameCount(1);
            loadElementReports(data.outputInfo);
        }
    };

    function loadElementReports(outputInfo) {
        self.outputFiles = [];
        outputInfo.forEach(function(info) {
            if (info.modelKey == 'matchAnimation') {
                self.outputFiles.push({
                    info: info,
                    reportType: 'matchSummaryAnimation',
                    viewName: 'matchSummaryAnimation',
                    panelTitle: 'Match Summary',
                    modelAccess: {
                        modelKey: 'matchSummaryAnimation',
                    },
                });
                return;
            }
            if (info.modelKey == 'twissFromParticlesAnimation') {
                self.outputFiles.push({
                    info: info,
                    reportType: 'parameterWithLattice',
                    viewName: 'twissFromParticlesAnimation',
                    panelTitle: 'Twiss From Particles',
                    modelAccess: {
                        modelKey: 'twissFromParticlesAnimation',
                    },
                });
                return;
            }
            var outputFile = {
                info: info,
                reportType: info.isHistogram ? 'heatmap' : 'parameterWithLattice',
                viewName: (info.isHistogram ? 'heatmap' : 'plot') + 'FrameAnimation',
                filename: info.filename,
                modelAccess: {
                    modelKey: info.modelKey,
                    getData: function() {
                        return appState.models[info.modelKey];
                    },
                },
                panelTitle: cleanFilename(info.filename),
            };
            self.outputFiles.push(outputFile);
        });
        self.outputFiles.forEach(function (outputFile) {
            var info = outputFile.info;
            var modelKey = outputFile.modelAccess.modelKey;
            if (! appState.models[modelKey]) {
                appState.models[modelKey] = {
                    panelTitle: outputFile.panelTitle,
                    x: info.plottableColumns[0],
                    y1: info.plottableColumns[1],
                    y2: 'None',
                    y3: 'None',
                };
                // better twiss defaults
                if (info.filename.indexOf('twiss') >= 0 || info.modelKey.indexOf('twiss') >= 0) {
                    $.extend(appState.models[modelKey], {
                        includeLattice: "1",
                        x: 's',
                        y1: 'betx',
                        y2: 'bety',
                    });
                }
            }
            var m = appState.models[modelKey];
            appState.setModelDefaults(m, 'elementAnimation');
            var yColumnWithNone = appState.clone(info.plottableColumns);
            yColumnWithNone.unshift('None');
            m.valueList = {
                x: info.plottableColumns,
                y1: info.plottableColumns,
                y2: yColumnWithNone,
                y3: yColumnWithNone,
            };
            appState.saveQuietly(modelKey);
            frameCache.setFrameCount(info.pageCount || 1, modelKey);
        });
    }

    self.simState = persistentSimulation.initSimulationState(self);
    self.simState.errorMessage = function() {
        return self.errorMessage;
    };
    self.simState.logFileURL = function() {
        return requestSender.formatUrl('downloadDataFile', {
            '<simulation_id>': appState.models.simulation.simulationId,
            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
            '<model>': self.simState.model,
            '<frame>': SIREPO.APP_SCHEMA.constants.logFileFrameId,
        });
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
            '<div data-import-dialog="" data-title="Import MAD-X File" data-description="Select a MAD-X file." data-file-formats=".madx,.zip"></div>',
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

SIREPO.app.directive('elementAnimationModalEditor', function(appState, panelState, plotRangeService) {
    return {
        scope: {
            reportInfo: '=',
        },
        template: [
            '<div data-modal-editor="" data-view-name="{{ viewName }}" data-model-data="modelAccess"></div>',
        ].join(''),
        controller: function($scope) {
            $scope.modelKey = $scope.reportInfo.modelAccess.modelKey;
            $scope.viewName = $scope.reportInfo.viewName;
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

SIREPO.app.directive('matchSummaryPanel', function(appState, plotting) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<pre>{{ summaryText }}</pre>',
        ].join(''),
        controller: function($scope) {
            plotting.setTextOnlyReport($scope);
            $scope.load = function(json) {
                $scope.summaryText = json.summaryText;
            };
        },
        link: function link(scope, element) {
            scope.modelName = 'matchSummaryAnimation';
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('commandConfirmation', function(appState, commandService, latticeService) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div data-confirmation-modal="" data-id="sr-madx-command-confirmation" data-title="MAD-X Command Template" data-ok-text="OK" data-ok-clicked="useTemplate()">
              <form class="form-horizontal" autocomplete="off">
                <div class="form-group text-center">
                  <div>Would you like to preconfigure the commands for this simulation?</div>
                </div>
                <div class="form-group">
                  <div data-model-field="'commandTemplate'" data-model-name="'simulation'" data-label-size="4" data-field-size="8"></div>
                </div>
              </form>
              {{ init() }}
            </div>`,
        controller: function($scope) {
            function addCommands(commands) {
                commands.forEach(function(cmd) {
                    cmd._id = latticeService.nextId();
                    appState.models.commands.push(appState.setModelDefaults(
                        cmd,
                        commandService.commandModelName(cmd._type)));
                });
            }
            let isInitialized = false;

            $scope.init = () => {
                if (isInitialized) {
                    return;
                }
                isInitialized = true;
                var sim = appState.models.simulation;
                if (appState.models.commands.length <= 2 && sim.commandTemplate != 'none') {
                    $('#sr-madx-command-confirmation').modal('show');
                }
            };

            $scope.useTemplate = () => {
                var sim = appState.models.simulation;
                if (sim.commandTemplate == 'particle') {
                    addCommands([
                        { _type: 'ptc_create_universe', sector_nmul: 10, sector_nmul_max: 10 },
                        { _type: 'ptc_create_layout' },
                        { _type: 'ptc_track', element_by_element: '1', file: '1', icase: '6' },
                        { _type: 'ptc_track_end' },
                        { _type: 'ptc_end' },
                    ]);
                }
                else if (sim.commandTemplate == 'matching') {
                    addCommands([
                        { _type: 'match', sequence: appState.models.simulation.activeBeamlineId },
                        { _type: 'vary', step: 1e-5 },
                        { _type: 'lmdif', calls: 50, tolerance: 1e-8 },
                        { _type: 'endmatch' },
                    ]);
                }
                appState.saveChanges(['commands', 'simulation']);
            };
        },
    };
});

SIREPO.viewLogic('bunchView', function(appState, commandService, madxService, panelState, requestSender, $scope) {
    var energyFields = SIREPO.APP_SCHEMA.enum.BeamDefinition.map(function(e) {
        return e[0];
    });

    function calculateBunchParameters() {
        updateParticle();
        requestSender.sendStatelessCompute(
            appState,
            function(data) {
                if (data.command_beam && appState.isLoaded()) {
                    var beam = data.command_beam;
                    energyFields.forEach(function(f) {
                        if (beam[f]) {
                            try {
                                beam[f] = Number.parseFloat(beam[f].toExponential(9));
                            }
                            catch (err) {
                                // might be an rpn variable instead of a float
                            }
                        }
                    });
                    appState.models.command_beam = beam;
                }
            },
            {
                method: 'calculate_bunch_parameters',
                bunch: appState.clone(appState.models.bunch),
                command_beam: appState.clone(appState.models.command_beam),
                variables: appState.clone(appState.models.rpnVariables),
            }
        );
    }

    function updateParticle() {
        var beam = appState.models.command_beam;
        ['mass', 'charge'].forEach(function(f) {
            panelState.enableField('command_beam', f, beam.particle == 'other');
        });
        if (beam.particle != 'other') {
            var info = SIREPO.APP_SCHEMA.constants.particleMassAndCharge[beam.particle];
            beam.mass = info[0];
            beam.charge = info[1];
        }
        energyFields.forEach(function(f) {
            panelState.enableField('command_beam', f, appState.models.bunch.beamDefinition == f);
        });
    }

    function updateTwissFields() {
        var isEnabled = appState.models.bunch.matchTwissParameters == '1';
        panelState.showField('simulation', 'visualizationBeamlineId', isEnabled);
        madxService.twissFields.forEach(function(f) {
            panelState.enableField('bunch', f, ! isEnabled);
        });
    }

    appState.whenModelsLoaded($scope, function() {
        if (commandService.findFirstCommand('beam').brho == 0) {
            calculateBunchParameters();
        }
    });

    $scope.$on('bunchReport1.summaryData', function(e, info) {
        if (appState.isLoaded() && info.betx) {
            madxService.twissFields.forEach(function(f) {
                appState.models.bunch[f] = info[f];
            });
            appState.saveQuietly('bunch');
        }
    });

    $scope.whenSelected = function() {
        updateParticle();
        updateTwissFields();
    };

    $scope.watchFields = [
        ['command_beam.particle'], updateParticle,
        ['bunch.matchTwissParameters'], updateTwissFields,
        $.merge(['bunch.beamDefinition'], energyFields.map(function(f) { return 'command_beam.' + f; })),
            calculateBunchParameters,
    ];
});

SIREPO.viewLogic('simulationSettingsView', function(commandService, panelState, madxService, $scope) {
    $scope.whenSelected = function() {
        panelState.showField('bunch', 'numberOfParticles', madxService.isParticleSimulation());
        panelState.showField(
            'simulation',
            'computeTwissFromParticles',
            madxService.isParticleSimulation());
    };
});
