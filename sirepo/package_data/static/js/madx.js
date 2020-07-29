'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.PLOTTING_COLOR_MAP = 'afmhot';
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

SIREPO.app.factory('madxService', function(appState, commandService, requestSender, rpnService, $rootScope) {
    var self = {};
    rpnService.isCaseInsensitive = true;

    self.computeModel = function(analysisModel) {
        return 'animation';
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
        'beam', 'constraint', 'lmdif', 'match', 'endmatch', 'option',
        'ptc_create_layout', 'ptc_create_universe', 'ptc_end',
        'ptc_normal', 'ptc_observe', 'ptc_savebeta', 'ptc_start', 'ptc_select',
        'ptc_track', 'ptc_track_end', 'resbeam', 'select', 'set', 'show',
        'sodd', 'twiss', 'vary',
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
    self.scope = $scope;
    self.appState = appState;
    self.panelState = panelState;
    self.outputFiles = [];
    self.outputFileMap = {};

    function cleanFilename(fn) {
        return fn.replace(/\.(?:tfs)/g, '');
    }

    self.simHandleStatus = function(data) {
        self.simulationAlerts = data.alert || '';
        if (data.frameCount) {
            frameCache.setFrameCount(1);
            loadElementReports(data.outputInfo);
        }
    }

    function loadElementReports(outputInfo) {
        self.outputFiles = [];
        outputInfo.forEach(function(info) {
            var outputFile = {
                info: info,
                reportType: info.isHistogram ? 'heatmap' : 'parameterWithLattice',
                viewName: info.modelKey.split(/(\d+)/)[0],
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
        self.outputFiles.forEach(function (outputFile, i) {
            var info = outputFile.info;
            var modelKey = outputFile.modelAccess.modelKey;
            if (! appState.models[modelKey]) {
                appState.models[modelKey] = {
                    panelTitle: outputFile.panelTitle
                };
                appState.setModelDefaults(appState.models[modelKey], 'elementAnimation');
            }
            appState.saveQuietly(modelKey);
            frameCache.setFrameCount(1, modelKey);
        });
    }

    self.startSimulation = function() {
        self.simState.saveAndRunSimulation('simulation');
    };

    self.simState = persistentSimulation.initSimulationState(self);
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
