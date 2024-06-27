'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appDefaultSimulationValues.simulation.elementPosition = 'absolute';
    SIREPO.SINGLE_FRAME_ANIMATION = ['beamline3dAnimation', 'plotAnimation', 'plot2Animation'];
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="BeamList" data-ng-class="fieldClass">
          <div data-command-list="" data-model="model" data-field="field" data-command-type="beam"></div>
        </div>
        <div data-ng-switch-when="FieldsolverList" data-ng-class="fieldClass">
          <div data-command-list="" data-model="model" data-field="field" data-command-type="fieldsolver"></div>
        </div>
        <div data-ng-switch-when="DistributionList" data-ng-class="fieldClass">
          <div data-command-list="" data-model="model" data-field="field" data-command-type="distribution"></div>
        </div>
        <div data-ng-switch-when="ParticlematterinteractionList" data-ng-class="fieldClass">
          <div data-command-list="" data-model="model" data-field="field" data-command-type="particlematterinteraction"></div>
        </div>
        <div data-ng-switch-when="WakeList" data-ng-class="fieldClass">
          <div data-command-list="" data-model="model" data-field="field" data-command-type="wake"></div>
        </div>
        <div data-ng-switch-when="GeometryList" data-ng-class="fieldClass">
          <div data-command-list="" data-model="model" data-field="field" data-command-type="geometry"></div>
        </div>
    `;
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="beamline3d" data-beamline-3d="" class="sr-plot" data-model-name="{{ modelKey }}"></div>
    `;
    SIREPO.appDownloadLinks = `
        <li data-download-csv-link=""></li>
    `;
    SIREPO.lattice = {
        canReverseBeamline: true,
        elementColor: {
            CCOLLIMATOR: 'magenta',
            SEXTUPOLE: 'lightgreen',
            OCTUPOLE: 'yellow',
        },
        elementPic: {
            alpha: [],
            aperture: ['CCOLLIMATOR', 'ECOLLIMATOR', 'FLEXIBLECOLLIMATOR', 'RCOLLIMATOR'],
            bend: ['RBEND', 'RBEND3D', 'SBEND', 'SBEND3D', 'SEPTUM'],
            drift: ['DRIFT'],
            lens: [],
            magnet: ['CYCLOTRON', 'CYCLOTRONVALLEY', 'DEGRADER',
                     'HKICKER', 'KICKER', 'MULTIPOLE', 'MULTIPOLET', 'OCTUPOLE',
                     'QUADRUPOLE', 'RINGDEFINITION', 'SCALINGFFAMAGNET', 'SEXTUPOLE',
                     'TRIMCOIL', 'UNDULATOR', 'VACUUM', 'VERTICALFFAMAGNET', 'VKICKER', 'WIRE'],
            malign: [],
            mirror: [],
            rf: ['RFCAVITY', 'VARIABLE_RF_CAVITY', 'VARIABLE_RF_CAVITY_FRINGE_FIELD'],
            solenoid: ['SOLENOID'],
            undulator: [],
            watch: ['MARKER', 'MONITOR', 'PROBE'],
            zeroLength: ['LOCAL_CARTESIAN_OFFSET', 'SOURCE', 'TRAVELINGWAVE'],
        },
    };
});

SIREPO.app.factory('opalService', function(appState, commandService, latticeService, rpnService) {
    var self = {};
    var COMMAND_TYPES = ['BeamList', 'DistributionList', 'FieldsolverList', 'GeometryList', 'ParticlematterinteractionList', 'WakeList'];
    commandService.hideCommandName = true;
    rpnService.isCaseInsensitive = true;

    self.computeModel = function(analysisModel) {
        return 'animation';
    };

    commandService.canDeleteCommand = function(command) {
        commandService.deleteCommandWarning = '';
        // can't delete a command which is in use by other commands
        //TODO(pjm) for now check track use of beam, fieldsolver and distribution
        commandService.findAllComands('track').some(function(track) {
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
            if (commandService.findAllComands(command._type).length == 1) {
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
        'beam', 'distribution', 'dumpemfields', 'dumpfields', 'fieldsolver', 'filter', 'geometry',
        'option', 'particlematterinteraction', 'select', 'track', 'wake',
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
// SBEND3D, CCOLLIMATOR, SEPTUM, PROBE

SIREPO.app.controller('LatticeController', function(appState, commandService, latticeService, rpnService, $scope) {
    var self = this;
    self.latticeService = latticeService;
    self.advancedNames = [
        'CCOLLIMATOR', 'CYCLOTRON', 'DEGRADER', 'FLEXIBLECOLLIMATOR',
        'HKICKER', 'KICKER', 'LOCAL_CARTESIAN_OFFSET', 'MONITOR', 'MULTIPOLE', 'MULTIPOLET',
        'OCTUPOLE', 'PROBE', 'RBEND', 'RBEND3D', 'RCOLLIMATOR', 'RINGDEFINITION', 'SBEND3D',
        'SCALINGFFAMAGNET', 'SEPTUM', 'SEXTUPOLE', 'SBEND', 'TRAVELINGWAVE',
        'TRIMCOIL', 'UNDULATOR', 'VACUUM', 'VARIABLE_RF_CAVITY', 'VARIABLE_RF_CAVITY_FRINGE_FIELD', 'VERTICALFFAMAGNET', 'VKICKER',
    ];
    self.basicNames = [
        'DRIFT', 'ECOLLIMATOR', 'MARKER', 'QUADRUPOLE', 'RFCAVITY', 'SOLENOID', 'SOURCE',
    ];
    var constants = SIREPO.APP_SCHEMA.constants;

    function bendAngle(particle, bend) {
        var p = constants.particleMassAndCharge[particle];
        var mass = p[0];
        var charge = p[1];
        var gamma = rpnService.getRpnValue(bend.designenergy) * 1e-3 / mass + 1;
        var betaGamma = Math.sqrt(Math.pow(gamma, 2) - 1);
        var fieldAmp = charge * Math.abs(
            Math.sqrt(
                Math.pow(rpnService.getRpnValue(bend.k0), 2)
                    + Math.pow(rpnService.getRpnValue(bend.k0s), 2))
                / charge);
        var radius = Math.abs((betaGamma * mass) / (constants.clight * fieldAmp));
        return 2 * Math.asin(rpnService.getRpnValue(bend.l) / (2 * radius));
    }

    function updateElementAttributes(item) {
        if (item.type == 'SBEND' || item.type == 'RBEND') {
            if (item.angle == 0 && item.designenergy) {
                var particle = commandService.findFirstCommand('beam').particle;
                item.angle = bendAngle(particle, item);
            }
        }
        if (item.type == 'SBEND') {
            item.travelLength = latticeService.arcLength(
                rpnService.getRpnValue(item.angle),
                rpnService.getRpnValue(item.l));
        }
    }

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
        template: `
            <div data-common-footer="nav"></div>
            <div data-elegant-import-dialog=""></div>
        `,
    };
});

// must import opalService so it registers with appState
SIREPO.app.directive('appHeader', function(appState, latticeService, opalService, panelState) {
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
                <div data-ng-if="nav.isLoaded()" data-sim-sections="">
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'lattice\')}"><a href data-ng-click="nav.openSection(\'lattice\')"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'control\')}"><a data-ng-href="{{ nav.sectionURL(\'control\') }}"><span class="glyphicon glyphicon-list-alt"></span> Control</a></li>
                  <li class="sim-section" data-ng-if="hasBeamlinesAndCommands()" data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
              </app-settings>
              <app-header-right-sim-list>
                <ul class="nav navbar-nav sr-navbar-right">
                  <li><a href data-ng-click="nav.showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>
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
        });
    });
    latticeService.initSourceController(self);
});

SIREPO.app.controller('VisualizationController', function (appState, commandService, frameCache, latticeService, panelState, persistentSimulation, plotRangeService, requestSender, opalService, $scope) {
    var self = this;
    self.simScope = $scope;
    self.panelState = panelState;
    self.errorMessage = '';
    self.outputFiles = [];

    function cleanFilename(fn) {
        return fn.replace(/\.(?:h5|outfn)/g, '');
    }

    self.hasBeamline3d = function() {
        return frameCache.hasFrames() && self.simState.getPercentComplete() == 100;
    };

    self.simHandleStatus = function (data) {
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
    };

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

    self.simState = persistentSimulation.initSimulationState(self);

    self.simState.errorMessage = function() {
        return self.errorMessage;
    };

    self.simState.logFileURL = function() {
        return requestSender.formatUrl('downloadRunFile', {
            '<simulation_id>': appState.models.simulation.simulationId,
            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
            '<model>': self.simState.model,
            '<frame>': SIREPO.nonDataFileFrame,
        });
    };

    appState.whenModelsLoaded($scope, function() {
        var cmd = commandService.findFirstCommand('track');
        if (! cmd.line || ! latticeService.elementForId(cmd.line)) {
            cmd.line = appState.models.simulation.activeBeamlineId;
            appState.saveQuietly('commands');
        }
        var name = commandService.commandModelName(cmd._type);
        appState.models[name] = appState.clone(cmd);
        appState.applicationState()[name] = appState.cloneModel(name);
        $scope.$on(name + '.changed', function() {
            // save changes to track into the commands list
            var cmd = commandService.findFirstCommand('track');
            $.extend(cmd, appState.models[name]);
            appState.models.simulation.visualizationBeamlineId = cmd.line;
            appState.saveChanges(['commands', 'simulation']);
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
        template: `
            <select class="form-control" data-ng-model="model[field]" data-ng-options="item._id as item.name for item in listCommands()"></select>
        `,
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

SIREPO.app.directive('beamline3d', function(appState, geometry, panelState, plotting, plotToPNG, vtkPlotting) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: `
            <div class="row">
              <div data-ng-class="{'sr-plot-loading': isLoading(), 'sr-plot-cleared': dataCleared}">
                <div data-vtk-display="" data-model-name="{{ modelName }}" data-enable-axes="true" data-axis-cfg="axisCfg" data-axis-obj="axisObj" data-reset-side="y"></div>
              </div>
            </div>`,
        controller: function($scope, $element) {
            let data, renderer, vtkScene;
            const coordMapper = new SIREPO.VTK.CoordMapper();

            function createAxes(bounds) {
                const pb = renderer.computeVisiblePropBounds();
                if (bounds) {
                    if (bounds[0][0] < pb[4]) {
                        pb[4] = bounds[0][0];
                    }
                    if (bounds[0][1] > pb[5]) {
                        pb[5] = bounds[0][1];
                    }
                }
                const b = SIREPO.VTK.VTKUtils.buildBoundingBox(pb, 0.01);
                vtkScene.addActor(b.actor);
                $scope.axisObj = new SIREPO.VTK.ViewPortBox(b.source, vtkScene.renderer);
                $scope.axisCfg = {};
                SIREPO.GEOMETRY.GeometryUtils.BASIS().forEach(dim => {
                    const idx = geometry.basis.indexOf(dim);
                    $scope.axisCfg[dim] = {
                        label: dim + ' [m]',
                        min: pb[idx * 2],
                        max: pb[idx * 2 + 1],
                        numPoints: 2,
                        screenDim: dim == 'x' ? 'y' : 'x',
                        showCentral: dim === appState.models.simulation.beamAxis,
                    };
                });
            }

            function getVtkElement() {
                return $($element).find('.vtk-canvas-holder');
            }

            function buildScene() {
                vtkScene.removeActors();
                let pd = vtk.Common.DataModel.vtkPolyData.newInstance();
                pd.getPoints().setData(new window.Float32Array(data.points), 3);
                pd.getPolys().setData(new window.Uint32Array(data.polys));
                let colors = [];
                for (let i = 0; i < data.colors.length; i++) {
                    colors.push(data.colors[i] * 255.0 + 0.5);
                }
                pd.getCellData().setScalars(vtk.Common.Core.vtkDataArray.newInstance({
                    numberOfComponents: 4,
                    values: colors,
                    dataType: vtk.Common.Core.vtkDataArray.VtkDataTypes.UNSIGNED_CHAR,
                }));
                const b = coordMapper.buildActorBundle();
                b.mapper.setInputData(pd);
                vtkScene.addActor(b.actor);
                createAxes(data.bounds);
                vtkScene.resetView();

                if ($scope.axisObj) {
                    panelState.waitForUI(() => $scope.$broadcast('axes.refresh'));
                }
            }

            $scope.destroy = () => {
                getVtkElement().off();
            };

            $scope.init = $scope.resize = () => {};

            $scope.$on('vtk-init', (e, d) => {
                vtkScene = d;
                vtkScene.setCamProperty('y', 'viewUp', [1, 0, 0]);
                renderer = vtkScene.renderer;
                vtkScene.setMarker(
                    SIREPO.VTK.VTKUtils.buildOrientationMarker(
                        vtk.Rendering.Core.vtkAxesActor.newInstance(),
                        vtkScene.renderWindow.getInteractor(),
                        vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.TOP_RIGHT
                    )
                );
                if (data) {
                    buildScene();
                }
                plotToPNG.initVTK($element, vtkScene.renderer);
            });

            $scope.load = (json) => {
                data = json;
                if (renderer) {
                    buildScene();
                }
            };
        },
        link: function link(scope, element) {
            plotting.vtkPlot(scope, element);
        },
    };
});

SIREPO.viewLogic('beamlineView', function(latticeService, panelState, $scope) {

    function updateAbsolutePositionFields() {
        panelState.showFields('beamline', [
            ['x', 'y', 'z', 'theta', 'phi', 'psi'], latticeService.isAbsolutePositioning(),
        ]);
    }

    $scope.whenSelected = updateAbsolutePositionFields;
});

SIREPO.viewLogic('simulationView', function(appState, panelState, $scope) {
    $scope.watchFields = [
        ['simulation.elementPosition'], () => {
            // don't allow changing the elementPosition
            appState.models.simulation.elementPosition = appState.applicationState().simulation.elementPosition;
        },
    ];
});

['plotAnimation', 'plot2Animation'].forEach((name) => {
    SIREPO.viewLogic(name + 'View', function(latticeService, panelState, $scope) {
        $scope.whenSelected = () => {
            panelState.showField(name, 'includeLattice', ! latticeService.isAbsolutePositioning());
        };
    });
});
