'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.SINGLE_FRAME_ANIMATION = ['plotAnimation', 'plot2Animation'];
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="BeamList" data-ng-class="fieldClass">',
          '<div data-command-list="" data-model="model" data-field="field" data-command-type="beam"></div>',
        '</div>',
        '<div data-ng-switch-when="FieldsolverList" data-ng-class="fieldClass">',
          '<div data-command-list="" data-model="model" data-field="field" data-command-type="fieldsolver"></div>',
        '</div>',
        '<div data-ng-switch-when="DistributionList" data-ng-class="fieldClass">',
          '<div data-command-list="" data-model="model" data-field="field" data-command-type="distribution"></div>',
        '</div>',
        '<div data-ng-switch-when="ParticlematterinteractionList" data-ng-class="fieldClass">',
          '<div data-command-list="" data-model="model" data-field="field" data-command-type="particlematterinteraction"></div>',
        '</div>',
        '<div data-ng-switch-when="WakeList" data-ng-class="fieldClass">',
          '<div data-command-list="" data-model="model" data-field="field" data-command-type="wake"></div>',
        '</div>',
        '<div data-ng-switch-when="GeometryList" data-ng-class="fieldClass">',
          '<div data-command-list="" data-model="model" data-field="field" data-command-type="geometry"></div>',
        '</div>',
    ].join('');
    SIREPO.lattice = {
        elementColor: {
            CCOLLIMATOR: 'magenta',
        },
        elementPic: {
            alpha: [],
            aperture: ['CCOLLIMATOR', 'ECOLLIMATOR', 'FLEXIBLECOLLIMATOR', 'PEPPERPOT', 'RCOLLIMATOR', 'SLIT'],
            bend: ['RBEND', 'RBEND3D', 'SBEND', 'SBEND3D', 'SEPTUM'],
            drift: ['DRIFT'],
            lens: [],
            magnet: ['CYCLOTRON', 'CYCLOTRONVALLEY', 'DEGRADER',
                     'HKICKER', 'KICKER', 'MULTIPOLE', 'MULTIPOLET', 'MULTIPOLETCURVEDCONSTRADIUS',
                     'MULTIPOLETCURVEDVARRADIUS', 'MULTIPOLETSTRAIGHT', 'OCTUPOLE',
                     'QUADRUPOLE', 'RINGDEFINITION', 'SCALINGFFAMAGNET', 'SEXTUPOLE',
                     'SOLENOID', 'STRIPPER', 'TRIMCOIL', 'VKICKER', 'WIRE'],
            malign: [],
            mirror: [],
            rf: ['PARALLELPLATE', 'RFCAVITY', 'VARIABLE_RF_CAVITY', 'VARIABLE_RF_CAVITY_FRINGE_FIELD'],
            solenoid: [],
            undulator: [],
            watch: ['HMONITOR', 'INSTRUMENT', 'MARKER', 'MONITOR', 'PROBE', 'VMONITOR'],
            zeroLength: ['PATCH', 'SEPARATOR', 'SOURCE', 'SROT', 'TRAVELINGWAVE', 'YROT'],
        },
    };
});

SIREPO.app.factory('opalService', function(appState, commandService, latticeService, rpnService) {
    var self = {};
    var COMMAND_TYPES = ['BeamList', 'DistributionList', 'FieldsolverList', 'GeometryList', 'ParticlematterinteractionList', 'WakeList'];
    commandService.hideCommandName = true;
    rpnService.isCaseInsensitive = true;

    function findCommands(type) {
        return appState.models.commands.filter(function(cmd) {
            return cmd._type == type;
        });
    }

    self.computeModel = function(analysisModel) {
        return 'animation';
    };

    commandService.canDeleteCommand = function(command) {
        commandService.deleteCommandWarning = '';
        // can't delete a command which is in use by other commands
        //TODO(pjm) for now check track use of beam, fieldsolver and distribution
        findCommands('track').some(function(track) {
            if (command._id  == track.beam
                || command._id == track.run_beam
                || command._id == track.run_fieldsolver
                || command._id == track.run_distribution) {
                commandService.deleteCommandWarning = commandService.formatCommandName(command) + ' is in use ';
                return true;
            }
        });
        if (commandService.deleteCommandWarning) {
            return false;
        }
        // can't delete the last option, beam, distribution, fieldsolver or track
        if (['option', 'beam', 'distribution', 'fieldsolver', 'track'].indexOf(command._type) >= 0) {
            if (findCommands(command._type).length == 1) {
                commandService.deleteCommandWarning = commandService.formatCommandName(command) + ' is the only ' + command._type;
                return false;
            }
        }
        return true;
    };

    // overrides commandService.commandFileExtension for opal file extensions
    commandService.commandFileExtension = function(command) {
        if (command) {
            if (command._type == 'list') {
                return '.dat';
            }
        }
        return '.h5';
    };

    commandService.formatCommandName = function(command) {
        return command.name + ':' + command._type.toUpperCase();
    };

    commandService.formatFieldValue = function(value, type) {
        if (COMMAND_TYPES.indexOf(type) >= 0) {
            var cmd = commandService.commandForId(value);
            if (cmd) {
                return cmd.name;
            }
        }
        return value;
    };

    latticeService.includeCommandNames = true;
    appState.setAppService(self);

    return self;
});

SIREPO.app.controller('CommandController', function(commandService, panelState) {
    var self = this;
    self.activeTab = 'basic';
    self.basicNames = [
        'attlist', 'beam', 'distribution', 'eigen',
        'envelope', 'fieldsolver', 'filter', 'geometry',
        'list', 'matrix', 'micado', 'option',
        'particlematterinteraction', 'select', 'start', 'survey',
        'threadall', 'threadbpm', 'track', 'twiss',
        'twiss3', 'twisstrack', 'wake',
    ];
    self.advancedNames = [];

    self.createElement = function(name) {
        panelState.showModalEditor(commandService.createCommand(name));
    };

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[commandService.commandModelName(name)].description;
    };
});

// All sims:
// DRIFT, QUADRUPOLE, SEXTUPOLE, OCTUPOLE, SOLENOID, CYCLOTRON, RINGDEFINITION, RFCAVITY, MONITOR, ECOLLIMATOR, RCOLLIMATOR, FLEXIBLECOLLIMATOR, DEGRADER, HKICKER, VKICKER, KICKER

// OPAL-T
// RBEND, SBEND, RBEND3D, MULTIPOLE

// OPAL-cycle
// SBEND3D, CCOLLIMATOR, SEPTUM, PROBE, STRIPPER,

SIREPO.app.controller('LatticeController', function(appState, commandService, latticeService, $scope) {
    var self = this;
    self.latticeService = latticeService;
    self.advancedNames = [
        'CCOLLIMATOR', 'CYCLOTRON', 'CYCLOTRONVALLEY', 'DEGRADER', 'FLEXIBLECOLLIMATOR',
        'HKICKER', 'HMONITOR', 'INSTRUMENT', 'MONITOR', 'MULTIPOLE', 'MULTIPOLET',
        'MULTIPOLETCURVEDCONSTRADIUS', 'MULTIPOLETCURVEDVARRADIUS', 'MULTIPOLETSTRAIGHT',
        'OCTUPOLE', 'PARALLELPLATE', 'PATCH', 'PEPPERPOT', 'PROBE', 'RBEND', 'RBEND3D',
        'RCOLLIMATOR', 'RFCAVITY', 'RINGDEFINITION', 'SBEND3D', 'SCALINGFFAMAGNET',
        'SEPARATOR', 'SEPTUM', 'SLIT', 'SOLENOID', 'SOURCE', 'SROT', 'STRIPPER',
        'TRAVELINGWAVE', 'TRIMCOIL', 'VARIABLE_RF_CAVITY',
        'VARIABLE_RF_CAVITY_FRINGE_FIELD', 'VKICKER', 'VMONITOR', 'WIRE', 'YROT',
    ];

    var m_e = 0.51099895000e-03;
    var m_p = 0.93827208816;
    var amu = 0.93149410242;
    var clight = 299792458.0e-9;
    var particleInfo = {
        // mass, charge
        ELECTRON: [m_e, -1.0],
        PROTON: [m_p, 1.0],
        POSITRON: [m_e, 1.0],
        ANTIPROTON: [m_p, -1.0],
        CARBON: [12 * amu, 12.0],
        HMINUS: [1.00837 * amu, -1.0],
        URANIUM: [238.050787 * amu, 35.0],
        MUON: [0.1056583755, -1.0],
        DEUTERON: [2.013553212745 * amu, 1.0],
        XENON: [124 * amu, 20.0],
        H2P: [2.01510 * amu, 1.0]
    };

    function bendAngle(particle, bend) {
        var mass = particleInfo[particle][0];
        var charge = particleInfo[particle][1];
        var gamma = bend.designenergy * 1e-3 / mass + 1;
        var betaGamma = Math.sqrt(Math.pow(gamma, 2) - 1);
        var fieldAmp = charge * Math.abs(Math.sqrt(Math.pow(bend.k0, 2) + Math.pow(bend.k0s, 2)) / charge);
        var radius = Math.abs((betaGamma * mass) / (clight * fieldAmp));
        return 2 * Math.asin(bend.l / (2 * radius));
    }

    function updateElementAttributes(item) {
        if (item.type == 'SBEND' || item.type == 'RBEND') {
            if (item.angle == 0 && item.designenergy) {
                var particle = commandService.findFirstCommand('beam').particle;
                item.angle = bendAngle(particle, item);
            }
        }
    }

    self.basicNames = ['DRIFT', 'ECOLLIMATOR', 'KICKER', 'MARKER', 'QUADRUPOLE', 'SBEND', 'SEXTUPOLE'];

    self.titleForName = function(name) {
        return SIREPO.APP_SCHEMA.view[name].description;
    };

    appState.whenModelsLoaded($scope, function() {
        var sim = appState.models.simulation;
        if (! sim.isInitialized) {
            appState.models.elements.map(updateElementAttributes);
            sim.isInitialized = true;
            appState.saveChanges(['elements', 'simulation']);
        }

        $scope.$on('modelChanged', function(e, name) {
            var m = appState.models[name];
            if (m.type) {
                updateElementAttributes(m);
            }
        });
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
            '<div data-import-dialog="" data-title="Import Opal File" data-description="Select an opal .in file." data-file-formats=".in">',
              '<div data-opal-import-options=""></div>',
            '</div>',
	].join(''),
    };
});

// must import opalService so it registers with appState
SIREPO.app.directive('appHeader', function(appState, latticeService, opalService, panelState) {
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'lattice\')}"><a href data-ng-click="nav.openSection(\'lattice\')"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'control\')}"><a data-ng-href="{{ nav.sectionURL(\'control\') }}"><span class="glyphicon glyphicon-list-alt"></span> Control</a></li>',
                  '<li class="sim-section" data-ng-if="hasBeamlinesAndCommands()" data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
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
        controller: function($scope) {
            $scope.latticeService = latticeService;

            $scope.hasBeamlinesAndCommands = function() {
                if (! latticeService.hasBeamlines()) {
                    return false;
                }
                return appState.models.commands.length > 0;
            };
        },
    };
});

SIREPO.app.controller('SourceController', function(appState, commandService, latticeService, $scope) {
    var self = this;

    function saveCommandList(type) {
        var cmd = commandService.findFirstCommand(type);
        $.extend(cmd, appState.models[commandService.commandModelName(type)]);
        appState.saveChanges('commands');
    }

    self.isFromFile = function() {
        if (appState.isLoaded() && appState.models.command_distribution) {
            return appState.models.command_distribution.type == 'FROMFILE';
        }
        return false;
    };

    appState.whenModelsLoaded($scope, function() {
        ['beam', 'distribution'].forEach(function(type) {
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
            $('#sr-command_beam-basicEditor h5').hide();
            $('#sr-command_distribution-basicEditor h5').hide();
        });
    });
    latticeService.initSourceController(self);
});

SIREPO.app.controller('VisualizationController', function (appState, commandService, frameCache, latticeService, panelState, persistentSimulation, plotRangeService, opalService, $scope) {
    var self = this;
    self.panelState = panelState;
    self.errorMessage = '';
    self.outputFiles = [];

    function cleanFilename(fn) {
        return fn.replace(/\.(?:h5|outfn)/g, '');
    }

    function handleStatus(data) {
        self.errorMessage = data.error;
        if ('percentComplete' in data && ! self.errorMessage) {
            ['bunchAnimation', 'plotAnimation', 'plot2Animation'].forEach(function(m) {
                plotRangeService.computeFieldRanges(self, m, data.percentComplete);
                appState.saveQuietly(m);
            });
            if (data.frameCount && data.outputInfo) {
                loadElementReports(data.outputInfo);
            }
        }
        frameCache.setFrameCount(data.frameCount || 0);
    }

    function loadElementReports(outputInfo) {
        self.outputFiles = [];
        outputInfo.forEach(function(info) {
            var outputFile = {
                info: info,
                reportType: 'heatmap',
                viewName: 'elementAnimation',
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
            panelState.setError(info.modelKey, null);
            if (! appState.models[info.modelKey]) {
                appState.models[info.modelKey] = {};
            }
            var m = appState.models[info.modelKey];
            appState.setModelDefaults(m, 'elementAnimation');
            appState.saveQuietly(info.modelKey);
            frameCache.setFrameCount(1, info.modelKey);
        });
    }

    self.simState = persistentSimulation.initSimulationState(
        $scope,
        opalService.computeModel(),
        handleStatus
    );

    self.simState.errorMessage = function() {
        return self.errorMessage;
    };

    appState.whenModelsLoaded($scope, function() {
        var cmd = commandService.findFirstCommand('track');
        var name = commandService.commandModelName(cmd._type);
        appState.models[name] = appState.clone(cmd);
        appState.applicationState()[name] = appState.cloneModel(name);
        $scope.$on(name + '.changed', function() {
            // save changes to track into the commands list
            var cmd = commandService.findFirstCommand('track');
            $.extend(cmd, appState.models[name]);
            appState.saveChanges('commands');
        });
        ['bunchAnimation'].forEach(function(m) {
            appState.watchModelFields($scope, [m + '.plotRangeType'], function() {
                plotRangeService.processPlotRange(self, m);
            });
        });

        $scope.$on('sr-tabSelected', function(evt, name) {
            if (name == 'bunchAnimation') {
                plotRangeService.processPlotRange(self, name);
            }
        });
    });
});

SIREPO.app.directive('commandList', function(appState, latticeService, panelState, commandService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            commandType: '@',
        },
        template: [
            '<select class="form-control" data-ng-model="model[field]" data-ng-options="item._id as item.name for item in listCommands()"></select>',
        ].join(''),
        controller: function($scope) {
            var list = [
                {
                    _id: '',
                    name: 'NOT SELECTED',
                },
            ];
            $scope.listCommands = function() {
                list.length = 1;
                appState.models.commands.forEach(function(c) {
                    if (c._type == $scope.commandType) {
                        list.push(c);
                    }
                });
                return list;
            };
        },
    };
});

SIREPO.app.directive('srCommandbeamEditor', function(appState, panelState) {
    return {
        restrict: 'A',
        controller: function($scope) {
            var name = 'command_beam';

            function processBeam() {
                var beam = appState.models[name];
                if (! beam) {
                    return;
                }
                ['mass', 'charge'].forEach(function(f) {
                    panelState.showField(name, f, beam.particle == 'OTHER' || ! beam.particle);
                });
            }

            $scope.$on('sr-tabSelected', processBeam);

            appState.whenModelsLoaded($scope, function() {
                appState.watchModelFields($scope, [
                    name + '.particle',
                ], processBeam);
            });
        },
    };
});

SIREPO.app.directive('srCommandtrackEditor', function(appState, panelState) {
    return {
        restrict: 'A',
        controller: function($scope) {
            var name = 'command_track';

            function processTrack() {
                var track = appState.models[name];
                if (! track) {
                    return;
                }
                panelState.showField(name, 'run_paramb', track.run_mbmode == 'AUTO');
            }

            $scope.$on('sr-tabSelected', processTrack);

            appState.whenModelsLoaded($scope, function() {
                appState.watchModelFields($scope, [
                    name + '.run_mbmode',
                ], processTrack);
            });
        },
    };
});

SIREPO.app.directive('srCommanddistributionEditor', function(appState, panelState) {
    return {
        restrict: 'A',
        controller: function($scope) {
            var name = 'command_distribution';
            var tab = {
                Cutoff: 2,
                Scale: 3,
                Offset: 4,
                Photoinjector: 5,
                Correlation: 6,
                Emission: 7,
                'Laser Profile': 8,
                Misc: 9,
            };

            function hasSigma(type) {
                return type == 'GAUSS'
                    || type == 'FLATTOP'
                    || type == 'BINOMIAL'
                    || type == 'GUNGAUSSFLATTOPTH'
                    || type == 'ASTRAFLATTOPTH';
            }

            function processEmitted() {
                var dist = appState.models[name];
                ['Photoinjector', 'Emission', 'Laser Profile'].forEach(function(t) {
                    panelState.showTab(name, tab[t], dist.emitted == '1');
                });
                ['zmult', 'offsetz'].forEach(function(f) {
                    panelState.showField(name, f, dist.emitted == '0');
                });
                ['tmult', 'offsett', 'emissionsteps', 'emissionmodel'].forEach(function(f) {
                    panelState.showField(name, f, dist.emitted == '1');
                });
                panelState.showField(name, 'ekin', dist.emitted == '1' && dist.emissionmodel == 'NONE' || dist.emissionmodel == 'ASTRA');
                ['elaser', 'w', 'fe', 'cathtemp'].forEach(function(f) {
                    panelState.showField(name, f, dist.emitted == '1' && dist.emissionmodel == 'NONEQUIL');
                });
                panelState.showField(name, 'sigmaz', hasSigma(dist.type) && dist.emitted == '0');
                panelState.showField(name, 'sigmat', hasSigma(dist.type) && dist.emitted == '1');
                panelState.showField(name, 'mz', dist.type == 'BINOMIAL' && dist.emitted == '0');
                panelState.showField(name, 'mt', dist.type == 'BINOMIAL' && dist.emitted == '1');
            }

            function processType() {
                var dist = appState.models[name];
                if (! dist) {
                    return;
                }
                var type = dist.type;
                panelState.showField(name, 'fname', type == 'FROMFILE');
                ['sigmax', 'sigmay', 'sigmar', 'sigmaz', 'sigmat', 'sigmapx', 'sigmapy', 'sigmapz', 'sigmapt'].forEach(function(f) {
                    panelState.showField(name, f, hasSigma(type));
                });
                if (type == 'BINOMIAL') {
                    panelState.showField(name, 'sigmar', false);
                }
                panelState.showTab(name, tab.Cutoff, hasSigma(type));
                panelState.showTab(name, tab.Correlation, hasSigma(type));
                ['mx', 'my'].forEach(function(f) {
                    panelState.showField(name, f, type == 'BINOMIAL');
                });
                if (type == 'GUNGAUSSFLATTOPTH' || type == 'ASTRAFLATTOPTH') {
                    dist.emitted = '1';
                    panelState.showField(name, 'emitted', false);
                }
                else {
                    panelState.showField(name, 'emitted', true);
                }
                panelState.showField(name, 'cutoff', type == 'GUNGAUSSFLATTOPTH');
                panelState.showField(name, 'cutoffr', type == 'GAUSS');
                ['cutoffpx', 'cutoffpy', 'cutoffpz'].forEach(function(f) {
                    panelState.showField(name, f, type == 'GAUSS' || type == 'BINOMIAL');
                });
                processEmitted();
            }

            $scope.$on('sr-tabSelected', processType);

            appState.whenModelsLoaded($scope, function() {
                appState.watchModelFields($scope, [
                    name + '.type',
                    name + '.emitted',
                    name + '.emissionmodel',
                ], processType);
            });
        },
    };
});

SIREPO.app.directive('opalImportOptions', function(fileUpload, requestSender) {
    return {
        restrict: 'A',
        template: [
            '<div data-ng-if="hasMissingFiles()" class="form-horizontal" style="margin-top: 1em;">',
              '<div style="margin-bottom: 1ex; white-space: pre;">{{ additionalFileText() }}</div>',
              '<div data-ng-repeat="info in missingFiles">',
                '<div data-ng-if="! info.hasFile" class="col-sm-11 col-sm-offset-1">',
                  '<span data-ng-if="info.invalidFilename" class="glyphicon glyphicon-flag text-danger"></span> <span data-ng-if="info.invalidFilename" class="text-danger">Filename does not match, expected: </span>',
                  '<label>{{ info.filename }}</label> ',
                  '({{ info.label + ": " + info.type }})',
                  '<input id="file-import" type="file" data-file-model="info.file">',
                  '<div data-ng-if="uploadDatafile(info)"></div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),

        controller: function($scope) {
            var parentScope = $scope.$parent;
            $scope.missingFiles = null;

            function checkFiles() {
                if (parentScope.fileUploadError) {
                    var hasFiles = true;
                    $scope.missingFiles.forEach(function(f) {
                        if (! f.hasFile) {
                            hasFiles = false;
                        }
                    });
                    if (hasFiles) {
                        parentScope.fileUploadError = null;
                    }
                }
            }

            $scope.additionalFileText = function() {
                if ($scope.missingFiles) {
                    return 'Please upload the files below which are referenced in the opal file.';
                }
            };

            $scope.uploadDatafile = function(info) {
                if (info.file.name) {
                    if (info.file.name != info.filename) {
                        if (! info.invalidFilename) {
                            info.invalidFilename = true;
                            $scope.$applyAsync();
                        }
                        return false;
                    }
                    info.invalidFilename = false;
                    parentScope.isUploading = true;
                    fileUpload.uploadFileToUrl(
                        info.file,
                        null,
                        requestSender.formatUrl(
                            'uploadFile',
                            {
                                // dummy id because no simulation id is available or required
                                '<simulation_id>': '11111111',
                                '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                                '<file_type>': info.file_type,
                            }),
                        function(data) {
                            parentScope.isUploading = false;
                            if (data.error) {
                                parentScope.fileUploadError = data.error;
                                return;
                            }
                            info.hasFile = true;
                            checkFiles();
                        });
                    info.file = {};
                }
                return false;
            };

            $scope.hasMissingFiles = function() {
                if (parentScope.fileUploadError) {
                    if (parentScope.errorData && parentScope.errorData.missingFiles) {
                        $scope.missingFiles = [];
                        parentScope.errorData.missingFiles.forEach(function(f) {
                            f.file = {};
                            $scope.missingFiles.push(f);
                        });
                        delete parentScope.errorData;
                    }
                }
                else {
                    $scope.missingFiles = null;
                }
                return $scope.missingFiles && $scope.missingFiles.length;
            };
        },
    };
});
