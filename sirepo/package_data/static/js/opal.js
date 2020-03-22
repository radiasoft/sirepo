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

SIREPO.app.factory('opalService', function(appState, commandService, latticeService) {
    var self = {};
    var COMMAND_TYPES = ['BeamList', 'DistributionList', 'FieldsolverList', 'GeometryList', 'ParticlematterinteractionList', 'WakeList'];

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

SIREPO.app.controller('LatticeController', function(appState, errorService, panelState, latticeService, $scope) {
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
    self.basicNames = ['DRIFT', 'ECOLLIMATOR', 'KICKER', 'MARKER', 'QUADRUPOLE', 'SBEND', 'SEXTUPOLE'];
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
                if (type == 'BINOMIAL' || type == 'GAUSSMATCHED') {
                    panelState.showField(name, 'sigmar', false);
                }
                panelState.showTab(name, tab.Cutoff, hasSigma(type) || type == 'GAUSSMATCHED');
                panelState.showTab(name, tab.Correlation, hasSigma(type));
                ['mx', 'my'].forEach(function(f) {
                    panelState.showField(name, f, type == 'BINOMIAL');
                });
                ['line', 'fmapfn', 'fmtype', 'ex', 'ey', 'et', 'residuum', 'maxstepsco', 'maxstepssi', 'ordermaps', 'magsym', 'rguess'].forEach(function(f) {
                    panelState.showField(name, f, type == 'GAUSSMATCHED');
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
                    panelState.showField(name, f, type == 'GAUSS' || type == 'BINOMIAL' || type == 'GAUSSMATCHED');
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
