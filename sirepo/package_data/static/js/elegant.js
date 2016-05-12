'use strict';

app_local_routes.lattice = '/lattice/:simulationId';
app_local_routes.visualization = '/visualization/:simulationId';
appDefaultSimulationValues = {
    simulation: {},
};

app.config(function($routeProvider, localRoutesProvider) {
    var localRoutes = localRoutesProvider.$get();
    $routeProvider
        .when(localRoutes.source, {
            controller: 'ElegantSourceController as source',
            templateUrl: '/static/html/elegant-source.html?' + SIREPO_APP_VERSION,
        })
        .when(localRoutes.lattice, {
            controller: 'LatticeController as lattice',
            templateUrl: '/static/html/elegant-lattice.html?' + SIREPO_APP_VERSION,
        })
        .when(localRoutes.visualization, {
            controller: 'VisualizationController as visualization',
            templateUrl: '/static/html/elegant-visualization.html?' + SIREPO_APP_VERSION,
        });
});

app.controller('ElegantSourceController', function(appState, $scope) {
    var self = this;
    var longitudinalFields = ['sigma_s', 'sigma_dp', 'dp_s_coupling', 'emit_z', 'beta_z', 'alpha_z'];

    function dpsCouplingChanged() {
        // dp_s_coupling valid only between -1 and 1
        if (! appState.isLoaded())
            return;
        var v = parseFloat(appState.models.bunch.dp_s_coupling);
        if (v > 1)
            appState.models.bunch.dp_s_coupling = 1;
        else if (v < -1)
            appState.models.bunch.dp_s_coupling = -1;
    }

    function showFields(fields, delay) {
        for (var i = 0; i < longitudinalFields.length; i++) {
            var f = longitudinalFields[i];
            var selector = '.model-bunch-' + f;
            if (fields.indexOf(f) >= 0)
                $(selector).closest('.form-group').show(delay);
            else
                $(selector).closest('.form-group').hide(delay);
        }
    }

    function updateLongitudinalFields(delay) {
        if (! appState.isLoaded())
            return;
        var method = appState.models['bunch']['longitudinalMethod'];
        if (parseInt(method) == 1)
            showFields(['sigma_s', 'sigma_dp', 'dp_s_coupling'], delay);
        else if (parseInt(method) == 2)
            showFields(['sigma_s', 'sigma_dp', 'alpha_z'], delay);
        else
            showFields(['emit_z', 'beta_z', 'alpha_z'], delay);
    }

    self.bunchReports = [
        {id: 1},
        {id: 2},
        {id: 3},
        {id: 4},
    ];

    self.handleModalShown = function() {
        updateLongitudinalFields(0);
    };

    var modelAccessByItemId = {};

    self.modelAccess = function(itemId) {
        if (modelAccessByItemId[itemId])
            return modelAccessByItemId[itemId];
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
    $scope.$watch('appState.models.bunch.dp_s_coupling', dpsCouplingChanged);
});

app.controller('LatticeController', function(appState, panelState, $rootScope, $scope, $timeout, $window) {
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
        undulator: ['CORGPIPE', 'CWIGGLER', 'GFWIGGLER', 'LSRMDLTR', 'UKICKMAP', 'WIGGLER'],
        watch: ['HMON', 'MARK', 'MONI', 'PEPPOT', 'VMON', 'WATCH', ],
        zeroLength: ['CENTER', 'CHARGE', 'DSCATTER', 'ELSE', 'EMITTANCE', 'ENERGY', 'FLOOR', 'HISTOGRAM', 'IBSCATTER', 'ILMATRIX', 'MAGNIFY', 'MALIGN', 'MATR', 'MHISTOGRAM', 'PFILTER', 'REMCOR', 'RIMULT', 'ROTATE', 'SAMPLE', 'SCATTER', 'SCMULT', 'SCRIPT', 'SREFFECTS', 'STRAY', 'TFBDRIVER', 'TFBPICKUP', 'TRCOUNT', 'TRWAKE', 'TWISS', 'WAKE', 'ZLONGIT', 'ZTRANSVERSE'],
        rf: ['CEPL', 'FRFMODE', 'FTRFMODE', 'MODRF', 'MRFDF', 'RAMPP', 'RAMPRF', 'RFCA', 'RFCW', 'RFDF', 'RFMODE', 'RFTM110', 'RFTMEZ0', 'RMDF', 'TMCF', 'TRFMODE', 'TWLA', 'TWMTA', 'TWPL'],
    };

    function fixModelName(modelName) {
        var m = appState.models[modelName];
        // remove invalid characters
        m.name = m.name.replace(/[\s\#\*'"]/g, '');
        return;
    }

    function nextId() {
        return Math.max(
            appState.maxId(appState.models.elements, '_id'),
            appState.maxId(appState.models.beamlines)) + 1;
    }

    function sortBeamlines() {
        appState.models.beamlines.sort(function(a, b) {
            return a.name.localeCompare(b.name);
        });
    }

    function sortElements() {
        appState.models.elements.sort(function(a, b) {
            var res = a.type.localeCompare(b.type);
            if (res == 0)
                res = a.name.localeCompare(b.name);
            return res;
        });
    }

    function uniqueNameForType(prefix) {
        var names = {};
        var containerNames = ['elements', 'beamlines'];
        for (var i = 0; i < containerNames.length; i++) {
            var containerName = containerNames[i];
            for (var j = 0; j < appState.models[containerName].length; j++)
                names[appState.models[containerName][j].name] = 1;
        }
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
        if (! foundIt)
            appState.models[containerName].push(m);
        sortMethod();
        appState.saveChanges(containerName);
    }

    self.addToBeamline = function(item) {
        self.getActiveBeamline().items.push(item.id || item._id);
        appState.saveChanges('beamlines');
    };

    self.angleFormat = function(angle) {
        var degrees = angle * 180 / Math.PI;
        degrees = Math.round(degrees * 10) / 10;
        degrees %= 360;
        return degrees.toFixed(1);
    };

    self.createElement = function(type) {
        $('#s-newBeamlineElement-editor').modal('hide');
        var schema = APP_SCHEMA.model[type];
        var model = {
            _id: nextId(),
            type: type,
            name: uniqueNameForType(type.charAt(0)),
        };
        // set model defaults from schema
        var fields = Object.keys(schema);
        for (var i = 0; i < fields.length; i++) {
            var f = fields[i];
            if (schema[f][2] != undefined)
                model[f] = schema[f][2];
        }
        self.editElement(type, model);
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

    self.getActiveBeamline = function() {
        var id = self.activeBeamlineId;
        for (var i = 0; i < appState.models.beamlines.length; i++) {
            var b = appState.models.beamlines[i];
            if (b.id == id)
                return b;
        }
        return null;
    };

    self.getElements = function() {
        if (appState.isLoaded)
            return appState.models.elements;
        return emptyElements;
    }

    self.isElementModel = function(name) {
        return name == name.toUpperCase();
    };

    self.elementForId = function(id) {
        for (var i = 0; i < appState.models.beamlines.length; i++) {
            var b = appState.models.beamlines[i];
            if (b.id == id)
                return b;
        }
        for (var i = 0; i < appState.models.elements.length; i++) {
            var e = appState.models.elements[i];
            if (e._id == id)
                return e;
        }
        return null;
    };

    self.nameForId = function(id) {
        return self.elementForId(id).name;
    };

    self.newBeamline = function() {
        appState.models['beamline'] = {
            name: uniqueNameForType('BL'),
            id: nextId(),
            l: 0,
            count: 0,
            items: [],
        };
        panelState.showModalEditor('beamline');
    };

    self.newElement = function() {
        $('#s-newBeamlineElement-editor').modal('show');
    };

    //TODO(pjm): use library for this
    self.numFormat = function(num, units) {
        if (! angular.isDefined(num))
            return '';
        if (num < 1) {
            num *= 1000;
            units = 'm' + units;
        }
        if (Math.round(num * 100) == 0)
            return '0';
        if (num >= 100)
            return num.toFixed(0) + units;
        if (num >= 10)
            return num.toFixed(1) + units;
        return num.toFixed(2) + units;
    };

    self.setActiveTab = function(name) {
        self.activeTab = name;
    };

    self.splitPaneHeight = function() {
        var w = $($window);
        var el = $('.s-split-pane-frame');
        return (w.height() - el.offset().top - 15) + 'px';
    };

    self.titleForName = function(name) {
        return APP_SCHEMA.view[name].description;
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
            updateModels('beamline', 'id', 'beamlines', sortBeamlines);
            self.editBeamline(appState.models.beamline);
        }
        if (self.isElementModel(name)) {
            fixModelName(name);
            updateModels(name, '_id', 'elements', sortElements);
        }
    });

    if (appState.isLoaded()) {
        self.activeBeamlineId = appState.models.simulation.activeBeamlineId;
    }
    else {
        $scope.$on('modelsLoaded', function() {
            self.activeBeamlineId = appState.models.simulation.activeBeamlineId;
        });
    }
});

app.controller('VisualizationController', function(appState, frameCache, panelState, requestSender, $scope, $timeout) {
    var self = this;
    var simulationModel = 'animation';
    self.appState = appState;
    self.panelState = panelState;
    self.isAborting = false;
    self.isDestroyed = false;
    self.dots = '.';
    self.simulationStatusModelName = 'simulationStatus';
    self.simulationErrors = '';
    self.timeData = {
        elapsedDays: null,
        elapsedTime: null,
    };

    self.outputFiles = [];

    frameCache.setAnimationArgs({});
    frameCache.setFrameCount(0);

    function loadElementReports(outputInfo) {
        self.outputFiles = [];
        var animationArgs = {};

        for (var i = 0; i < outputInfo.length; i++) {
            var info = outputInfo[i];
            var modelKey = 'elementAnimation' + info.id;
            self.outputFiles.push({
                //TODO(pjm): need a proper test for this case
                reportType: info.columns[0] == 's' ? '2d' : 'heatmap',
                modelName: 'elementAnimation',
                filename: info['filename'],
                modelAccess: {
                    modelKey: modelKey,
                },
            });
            animationArgs[modelKey] = ['x', 'y', 'histogramBins', 'fileId'];
            if (appState.models[modelKey]) {
                var m = appState.models[modelKey];
                if (info.columns.indexOf(m.x) < 0)
                    m.x = info.columns[0];
                if (info.columns.indexOf(m.y) < 0)
                    m.y = info.columns[1];
                m.fileId = info.id;
                m.values = info.columns;
            }
            else {
                appState.models[modelKey] = {
                    x: info.columns[0],
                    y: info.columns[1],
                    histogramBins: 200,
                    fileId: info.id,
                    values: info.columns,
                    framesPerSecond: 2,
                };
                if (i > 0 && ! panelState.isHidden(modelKey))
                    panelState.toggleHidden(modelKey);
            }
            appState.saveQuietly(modelKey);
            frameCache.setFrameCount(info.page_count, modelKey);
        }
        frameCache.setAnimationArgs(animationArgs, simulationModel);
    }

    function refreshStatus() {
        requestSender.sendRequest(
            'runStatus',
            function(data) {
                if (self.isAborting)
                    return;
                self.simulationErrors = data.errors || '';
                if (data.frameCount) {
                    frameCache.setFrameCount(data.frameCount);
                    loadElementReports(data.outputInfo);
                }
                if (data.elapsedTime) {
                    self.timeData.elapsedDays = parseInt(data.elapsedTime / (60 * 60 * 24));
                    self.timeData.elapsedTime = new Date(1970, 0, 1);
                    self.timeData.elapsedTime.setSeconds(data.elapsedTime);
                }
                if (data.state != 'running') {
                    if (! data.frameCount) {
                        if (data.state == 'completed' && ! self.simulationErrors) {
                            // completed with no output, show link to elegant log
                            self.simulationErrors = 'No output produced. View the elegant log for more information.';
                        }
                        self.outputFiles = [];
                    }
                    if (data.state != simulationState())
                        appState.saveChanges('simulationStatus');
                }
                else {
                    if (! self.isDestroyed) {
                        self.dots += '.';
                        if (self.dots.length > 3)
                            self.dots = '.';
                        $timeout(refreshStatus, 2000);
                    }
                }
                setSimulationState(data.state);
            },
            {
                report: simulationModel,
                models: appState.applicationState(),
                simulationType: APP_SCHEMA.simulationType,
            });
    }

    function setSimulationState(state) {
        if (! appState.models.simulationStatus[simulationModel])
            appState.models.simulationStatus[simulationModel] = {}
        appState.models.simulationStatus[simulationModel].state = state;
    }

    function simulationState() {
        return appState.models.simulationStatus[simulationModel].state;
    }

    self.cancelSimulation = function() {
        if (simulationState() != 'running')
            return;
        setSimulationState('canceled');
        self.isAborting = true;
        requestSender.sendRequest(
            'runCancel',
            function(data) {
                self.isAborting = false;
                appState.saveChanges('simulationStatus');
            },
            {
                report: simulationModel,
                models: appState.applicationState(),
                simulationType: APP_SCHEMA.simulationType,
            });
    };

    self.getBeamlines = function() {
        if (! appState.isLoaded())
            return null;
        if (! appState.models.simulation.visualizationBeamlineId
            && appState.models.beamlines
            && appState.models.beamlines.length) {
            appState.models.simulation.visualizationBeamlineId = appState.models.beamlines[0].id;
        }
        return appState.models.beamlines;
    };

    self.isState = function(state) {
        if (appState.isLoaded())
            return simulationState() == state;
        return false;
    };

    self.logFileURL = function() {
        if (! appState.isLoaded())
            return '';
        return requestSender.formatUrl('downloadDataFile', {
            '<simulation_id>': appState.models.simulation.simulationId,
            '<simulation_type>': APP_SCHEMA.simulationType,
            //TODO(pjm): centralize animation model name
            '<model>': 'animation',
            '<frame>': -1,
        });
    };

    self.runSimulation = function() {
        if (simulationState() == 'running')
            return;
        appState.saveQuietly('simulation');
        frameCache.setFrameCount(0);
        self.timeData.elapsedTime = null;
        self.timeData.elapsedDays = null;
        self.outputFiles = [];
        setSimulationState('running');
        requestSender.sendRequest(
            'runBackground',
            function(data) {
                appState.models.simulationStatus[simulationModel].startTime = data['startTime'];
                appState.saveChanges('simulationStatus');
                refreshStatus();
            },
            {
                report: simulationModel,
                models: appState.applicationState(),
                simulationType: APP_SCHEMA.simulationType,
            });
    };

    $scope.$on('$destroy', function () {
        self.isDestroyed = true;
    });

    if (appState.isLoaded())
        refreshStatus();
    else {
        $scope.$on('modelsLoaded', refreshStatus);
    }
});

app.directive('appHeader', function(appState, panelState) {
    return {
        restirct: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: [
            '<div class="navbar-header">',
              '<a class="navbar-brand" href data-ng-click="nav.openSection(\'simulations\')"><img style="width: 40px; margin-top: -10px;" src="/static/img/radtrack.gif" alt="radiasoft"></a>',
              '<div class="navbar-brand"><a href data-ng-click="nav.openSection(\'simulations\')">elegant</a></div>',
            '</div>',
            '<div data-app-header-left="nav"></div>',
            '<ul class="nav navbar-nav navbar-right" data-ng-show="isLoaded()">',
              '<li data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
              '<li data-ng-class="{active: nav.isActive(\'lattice\')}"><a href data-ng-click="nav.openSection(\'lattice\')"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>',
              '<li data-ng-if="hasBeamlines()" data-ng-class="{active: nav.isActive(\'visualization\')}"><a href data-ng-click="nav.openSection(\'visualization\')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
            '</ul>',
        ].join(''),
        controller: function($scope) {
            $scope.isLoaded = function() {
                return appState.isLoaded();
            };
            $scope.hasBeamlines = function() {
                if (! appState.isLoaded())
                    return false;
                for (var i = 0; i < appState.models.beamlines.length; i++) {
                    var beamline = appState.models.beamlines[i];
                    if (beamline.items.length > 0)
                        return true;
                }
                return false;
            }
        },
    };
});

app.directive('beamlineEditor', function(appState, $document, $timeout) {
    return {
        restirct: 'A',
        scope: {
            lattice: '=controller',
        },
        template: [
            '<div data-ng-if="showEditor()" class="panel panel-info">',

              '<div class="panel-heading"><span class="s-panel-heading">Beamline Editor - {{ beamlineName() }}</span></div>',
              '<div class="panel-body" data-ng-drop="true" data-ng-drag-stop="dragStop($data)" data-ng-drop-success="dropPanel($data)" data-ng-drag-start="dragStart($data)">',
                '<p class="lead text-center"><small><em>drag and drop elements here to define the beamline</em></small></p>',
                '<div data-ng-dblclick="editItem(item)" data-ng-click="selectItem(item)" data-ng-drag="true" data-ng-drag-data="item" data-ng-repeat="item in beamlineItems" class="elegant-beamline-element" data-ng-class="{\'elegant-beamline-element-group\': item.inRepeat }" data-ng-drop="true" data-ng-drop-success="dropItem($index, $data)">',
                  '<div class="s-drop-left">&nbsp;</div>',
                  '<span data-ng-if="item.repeatCount" class="s-count">{{ item.repeatCount }}</span>',
                  '<div style="display: inline-block; cursor: move; -moz-user-select: none" class="badge elegant-icon elegant-beamline-element-with-count" data-ng-class="{\'elegant-item-selected\': isSelected(item.itemId)}"><span>{{ itemName(item) }}</span></div>',
                '</div>',
                '<div class="elegant-beamline-element s-last-drop" data-ng-drop="true" data-ng-drop-success="dropLast($data)"><div class="s-drop-left">&nbsp;</div></div>',
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
                if (! data || dragCanceled)
                    return;
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
                if (! data)
                    return;
                if (data.itemId) {
                    if (dragCanceled)
                        return;
                    dropSuccess = true;
                    var curr = $scope.beamlineItems.indexOf(data);
                    if (curr < index)
                        index--;
                    $scope.beamlineItems.splice(curr, 1);
                }
                else {
                    data = $scope.beamlineItems.splice($scope.beamlineItems.length - 1, 1)[0];
                }
                $scope.beamlineItems.splice(index, 0, data);
                updateBeamline();
            };

            $scope.dropLast = function(data) {
                if (! data || ! data.itemId)
                    return;
                if (dragCanceled)
                    return;
                dropSuccess = true;
                var curr = $scope.beamlineItems.indexOf(data);
                $scope.beamlineItems.splice(curr, 1);
                $scope.beamlineItems.push(data);
                updateBeamline();
            };

            $scope.dropPanel = function(data) {
                if (! data)
                    return;
                if (data.itemId) {
                    dropSuccess = true;
                    return;
                }
                if (data.id == activeBeamline.id)
                    return;
                var item = {
                    id: data.id || data._id,
                    itemId: appState.maxId($scope.beamlineItems, 'itemId') + 1,
                };
                $scope.beamlineItems.push(item);
                $scope.selectItem(item);
                updateBeamline();
            };

            $scope.editItem = function(item) {
                var el = $scope.lattice.elementForId(item.id);
                if (el.type)
                    $scope.lattice.editElement(el.type, el);
            };

            $scope.isSelected = function(itemId) {
                if (selectedItemId)
                    return itemId == selectedItemId;
                return false;
            };

            $scope.itemName = function(item) {
                item.name = $scope.lattice.nameForId(item.id);
                return item.name;
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

            $scope.showEditor = function() {
                if (! appState.isLoaded())
                    return false;
                if (! $scope.lattice.activeBeamlineId)
                    return false;
                var beamline = $scope.lattice.getActiveBeamline();
                if (activeBeamline && activeBeamline == beamline && beamline.items.length == $scope.beamlineItems.length)
                    return true;
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

app.directive('beamlineTable', function(appState) {
    return {
        restirct: 'A',
        scope: {
            lattice: '=controller',
        },
        template: [
            '<table style="width: 100%; table-layout: fixed" class="table table-hover">',
              '<colgroup>',
                '<col style="width: 12ex">',
                '<col>',
                '<col style="width: 10ex">',
                '<col style="width: 12ex">',
                '<col style="width: 10ex">',
              '</colgroup>',
              '<thead>',
                '<tr>',
                  '<th>Name</th>',
                  '<th>Description</th>',
                  '<th>Elements</th>',
                  '<th>Length</th>',
                  '<th>Bend</th>',
                '</tr>',
              '</thead>',
              '<tbody>',
                '<tr data-ng-class="{success: isActiveBeamline(beamline)}" data-ng-repeat="beamline in lattice.appState.models.beamlines track by beamline.id">',
                  '<td><div class="badge elegant-icon"><span data-ng-drag="true" data-ng-drag-data="beamline">{{ beamline.name }}</span></div></td>',
                  '<td style="overflow: hidden"><span style="color: #777; white-space: nowrap">{{ beamlineDescription(beamline) }}</span></td>',
                  '<td style="text-align: right">{{ beamline.count }}</td>',
                  '<td style="text-align: right">{{ beamlineLength(beamline) }}</td>',
                  '<td style="text-align: right">{{ beamlineBend(beamline, \'&nbsp;\') }}<span data-ng-if="beamlineBend(beamline)">&deg;</span><div data-ng-show="! isActiveBeamline(beamline)" class="s-button-bar-parent"><div class="s-button-bar"><button class="btn btn-info btn-xs s-hover-button" data-ng-click="addToBeamline(beamline)">Add to Beamline</button> <button data-ng-click="editBeamline(beamline)" class="btn btn-info btn-xs s-hover-button">Edit</button></div><div></td>',
                '</tr>',
              '</tbody>',
            '</table>',
        ].join(''),
        controller: function($scope) {

            function itemsToString(items) {
                var res = '(';
                if (! items.length)
                    res += ' ';
                for (var i = 0; i < items.length; i++) {
                    var id = items[i];
                    res += $scope.lattice.nameForId(id);
                    if (i != items.length - 1)
                        res += ',';
                }
                res += ')';
                return res;
            }

            $scope.addToBeamline = function(beamline) {
                $scope.lattice.addToBeamline(beamline);
            };

            $scope.beamlineBend = function(beamline, defaultValue) {
                if (angular.isDefined(beamline.angle))
                    return $scope.lattice.angleFormat(beamline.angle);
                return defaultValue;
            };

            $scope.beamlineDescription = function(beamline) {
                return itemsToString(beamline.items);
            };

            $scope.beamlineLength = function(beamline) {
                return $scope.lattice.numFormat(beamline.length, 'm');
            };

            $scope.editBeamline = function(beamline) {
                $scope.lattice.editBeamline(beamline);
            };

            $scope.isActiveBeamline = function(beamline) {
                if ($scope.lattice.activeBeamlineId)
                    return $scope.lattice.activeBeamlineId == beamline.id;
                return false;
            };
        },
    };
});

app.directive('elementTable', function(appState) {
    return {
        restirct: 'A',
        scope: {
            lattice: '=controller',
        },
        template: [
            '<table style="width: 100%; table-layout: fixed" class="table table-hover">',
              '<colgroup>',
                '<col style="width: 12ex">',
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
                '<tr class="cssFade" data-ng-show="isExpanded(category)" data-ng-repeat="element in category.elements track by element._id">',
                  '<td style="padding-left: 1em"><div class="badge elegant-icon"><span data-ng-drag="true" data-ng-drag-data="element">{{ element.name }}</span></div></td>',
                  '<td style="overflow: hidden"><span style="color: #777; white-space: nowrap">{{ elementDescription(category.name, element) }}</span></td>',
                  '<td style="text-align: right">{{ elementLength(element) }}</td>',
                  '<td style="text-align: right">{{ elementBend(element, \'&nbsp;\') }}<span data-ng-if="elementBend(element)">&deg;</span><div class="s-button-bar-parent"><div class="s-button-bar"><button data-ng-show="lattice.activeBeamlineId" class="btn btn-info btn-xs s-hover-button" data-ng-click="addToBeamline(element)">Add to Beamline</button> <button data-ng-click="editElement(category.name, element)" class="btn btn-info btn-xs s-hover-button">Edit</button></div><div></td>',
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
                var elements = appState.models.elements;

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

            $scope.editElement = function(type, item) {
                return $scope.lattice.editElement(type, item);
            };

            $scope.elementBend = function(element, defaultValue) {
                if (angular.isDefined(element.angle))
                    return $scope.lattice.angleFormat(element.angle);
                return defaultValue;
            };

            $scope.elementDescription = function(type, element) {
                if (! element)
                    return 'null';
                var schema = APP_SCHEMA.model[type];
                var res = '';
                var fields = Object.keys(element).sort();
                for (var i = 0; i < fields.length; i++) {
                    var f = fields[i];
                    if (f == 'name' || f == 'l' || f == 'angle' || f.indexOf('$') >= 0)
                        continue;
                    if (angular.isDefined(element[f]) && angular.isDefined(schema[f]))
                        if (schema[f][2] != element[f])
                            res += (res.length ? ',' : '') + f + '=' + element[f];
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

            $scope.$on('cancelChanges', function(e, name) {
                if (name == 'elements')
                    loadTree();
            });

            if (appState.isLoaded())
                loadTree();
            else
                $scope.$on('modelsLoaded', loadTree);
        },
    };
});

app.directive('elementAnimationModalEditor', function(appState) {
    return {
        scope: {
            modelKey: '@',
        },
        template: [
            '<div data-modal-editor="" view-name="elementAnimation" data-model-data="modelAccess"></div>',
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

app.directive('runSimulationFields', function() {
    return {
        template: [
            '<div>',
              '<div class="col-sm-3 control-label">',
                '<label>Beamline</label>',
              '</div>',
              '<div class="col-sm-4">',
                '<select class="form-control" data-ng-model="visualization.appState.models.simulation.visualizationBeamlineId" data-ng-options="item.id as item.name for item in visualization.getBeamlines()"></select>',
              '</div>',
              '<div class="col-sm-5" data-ng-show="visualization.isState(\'initial\')">',
               '<button class="btn btn-primary" data-ng-click="visualization.runSimulation()">Start Simulation</button>',
              '</div>',
              '<div class="col-sm-5" data-ng-hide="visualization.isState(\'initial\')">',
                '<button class="btn btn-default" data-ng-click="visualization.runSimulation()">Start New Simulation</button>',
              '</div>',
            '</div>',
        ].join(''),
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
