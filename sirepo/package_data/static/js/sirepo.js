'use strict';

var APP_SCHEMA;

// Load the application schema synchronously, before creating app module
//TODO(pjm): deprecated, change this to a requires/callback
$.ajax({
    url: '/static/json/schema.json?' + SIREPO_APP_VERSION,
    success: function(result) {
        APP_SCHEMA = result;
    },
    error: function(xhr, status, err) {
        console.log("schema load failed: ", err);
    },
    async: false,
});

var app = angular.module('SRWApp', ['ngAnimate', 'ngDraggable', 'ngRoute', 'd3']);

app.value('localRoutes', {
    simulations: '/simulations',
    source: '/source/:simulationId',
    beamline: '/beamline/:simulationId',
});

app.config(function($routeProvider, localRoutesProvider) {
    var localRoutes = localRoutesProvider.$get();
    $routeProvider
        .when(localRoutes.simulations, {
            controller: 'SimulationsController as simulations',
            templateUrl: '/static/html/simulations.html?' + SIREPO_APP_VERSION,
        })
        .when(localRoutes.source, {
            controller: 'SourceController as source',
            templateUrl: '/static/html/source.html?' + SIREPO_APP_VERSION,
        })
        .when(localRoutes.beamline, {
            controller: 'BeamlineController as beamline',
            templateUrl: '/static/html/beamline.html?' + SIREPO_APP_VERSION,
        })
        .otherwise({
            redirectTo: localRoutes.simulations,
        });
});

app.factory('activeSection', function($route, appState) {
    var self = this;
    var activeSection = null;

    self.getActiveSection = function() {
        return activeSection;
    };

    self.setActiveSection = function(name) {
        activeSection = name;
        if ($route.current.params.simulationId)
            appState.loadModels($route.current.params.simulationId);
    };

    return self;
});

app.factory('appState', function($rootScope, requestSender) {
    var self = {};
    self.models = {};
    var savedModelValues = {};

    function broadcastClear() {
        $rootScope.$broadcast('clearCache');
    }

    function broadcastChanged(name) {
        $rootScope.$broadcast(name + '.changed');
    }

    function isPropagationModelName(name) {
        return name.toLowerCase().indexOf('propagation') >= 0;
    }

    function isWatchpointReportModelName(name) {
        return name.indexOf('watchpointReport') >= 0;
    }

    function updateReports() {
        broadcastClear();
        for (var key in self.models) {
            if (self.isReportModelName(key))
                broadcastChanged(key);
        }
    }

    self.applicationState = function() {
        return savedModelValues;
    };

    self.cancelChanges = function(name) {
        if (savedModelValues[name])
            self.models[name] = self.clone(savedModelValues[name]);
    };

    self.clearModels = function(emptyValues) {
        broadcastClear();
        self.models = emptyValues || {};
        savedModelValues = {};
    };

    self.clone = function(obj) {
        return JSON.parse(JSON.stringify(obj));
    };

    self.cloneModel = function(name) {
        var val = name ? self.models[name] : self.models;
        return self.clone(val);
    };

    self.getWatchItems = function() {
        if (self.isLoaded()) {
            var beamline = savedModelValues.beamline;
            var res = [];
            for (var i = 0; i < beamline.length; i++) {
                if (beamline[i].type == 'watch')
                    res.push(beamline[i]);
            }
            return res;
        }
        return [];
    };

    self.getReportTitle = function(name) {
        //TODO(pjm): generalize this
        var match = name.match(/.*?(\d+)/);
        if (match) {
            var id = match[1];
            for (var i = 0; i < savedModelValues.beamline.length; i += 1) {
                if (savedModelValues.beamline[i].id == id)
                    return 'Intensity at ' + savedModelValues.beamline[i].title + ' Report';
            }
        }
        return self.viewInfo(name).title;
    };

    self.isLoaded = function() {
        return self.models.simulation && self.models.simulation.simulationId ? true: false;
    };

    self.isReportModelName = function(name) {
        return name.indexOf('Report') >= 0;
    };

    self.loadModels = function(simulationId) {
        if (self.isLoaded() && self.models.simulation.simulationId == simulationId)
            return;
        self.clearModels();
        requestSender.sendRequest(
            requestSender.formatUrl(
                'simulationData',
                {
                    '<simulation_id>': simulationId,
                }),
            function(data, status) {
                self.models = data.models;
                savedModelValues = self.cloneModel();
                updateReports();
            });
    };

    self.modelInfo = function(name) {
        return APP_SCHEMA.model[name];
    };

    self.saveBeamline = function() {
        // culls and saves propagation and watchpoint models
        var propagations = {}
        var watchpoints = {};
        for (var i = 0; i < self.models.beamline.length; i++) {
            var item = self.models.beamline[i];
            propagations[item.id] = self.models.propagation[item.id];
            if (item.type == 'watch')
                watchpoints[self.watchpointReportName(item.id)] = true;
        }
        self.models.propagation = propagations;

        // need to save all watchpointReports and propagations for beamline changes
        for (var modelName in self.models) {
            if (isWatchpointReportModelName(modelName) && ! watchpoints[modelName]) {
                // deleted watchpoint, remove the report model
                delete self.models[modelName];
                delete savedModelValues[modelName];
                continue;
            }
            if (isWatchpointReportModelName(modelName) || isPropagationModelName(modelName))
                savedModelValues[modelName] = self.cloneModel(modelName);
        }
        self.saveChanges('beamline');
    };

    self.saveChanges = function(name) {
        savedModelValues[name] = self.cloneModel(name);
        if (! self.isReportModelName(name))
            updateReports();
        broadcastChanged(name);
    };

    self.viewInfo = function(name) {
        return APP_SCHEMA.view[name];
    };

    self.watchpointReportName = function(id) {
        return 'watchpointReport' + id;
    }

    return self;
});

app.factory('panelState', function($window, $rootScope, appState, requestQueue) {
    // Tracks the data, error, hidden and loading values
    var self = {};
    var panels = {};
    $rootScope.$on('clearCache', function() {
        self.clear();
    });

    function getPanelValue(name, key) {
        if (panels[name] && panels[name][key])
            return panels[name][key];
        return null;
    }

    function setPanelValue(name, key, value) {
        if (! (name || key))
            throw 'missing name or key';
        if (! panels[name])
            panels[name] = {};
        panels[name][key] = value;
    }

    self.clear = function(name) {
        if (name)
            panels[name] = {}
        else
            panels = {};
    };

    self.getError = function(name) {
        return getPanelValue(name, 'error');
    };

    self.isHidden = function(name) {
        return getPanelValue(name, 'hidden') ? true : false;
    };

    self.isLoading = function(name) {
        return getPanelValue(name, 'loading') ? true : false;
    };

    self.requestData = function(name, callback) {
        if (! appState.isLoaded())
            return;
        var data = getPanelValue(name, 'data');
        if (data) {
            callback(data);
            return;
        }
        setPanelValue(name, 'loading', true);
        setPanelValue(name, 'error', null);
        var responseHandler = function(data, error) {
            setPanelValue(name, 'loading', false);
            if (error) {
                setPanelValue(name, 'error', error);
            }
            else {
                setPanelValue(name, 'data', data);
                setPanelValue(name, 'error', null);
                callback(data);
            }
        };
        requestQueue.addItem([name, appState.applicationState(), responseHandler]);
    };

    self.toggleHidden = function(name) {
        setPanelValue(name, 'hidden', ! self.isHidden(name));
        if (! self.isHidden(name) && appState.isReportModelName(name)) {
            // needed to resize a hidden report
            $($window).trigger('resize');
        }
    };

    return self;
});

app.factory('requestSender', function($http, $location, localRoutes) {
    var self = {};

    function logError(data) {
        console.log('request failed: ', data);
    }

    function formatUrl(map, routeName, params) {
        if (! map[routeName])
            throw 'unknown routeName: ' + routeName;
        var url = map[routeName];
        if (params) {
            for (var k in params)
                url = url.replace(k, params[k]);
        }
        return url;
    }

    self.formatLocalUrl = function(routeName, params) {
        return formatUrl(localRoutes, routeName, params);
    }

    self.formatUrl = function(routeName, params) {
        return formatUrl(APP_SCHEMA.route, routeName, params);
    };

    self.localRedirect = function(routeName, params) {
        $location.path(self.formatLocalUrl(routeName, params));
    }

    self.sendRequest = function(urlOrName, successCallback, data, errorCallback) {
        var url = urlOrName.indexOf('/') >= 0
            ? urlOrName
            : self.formatUrl(urlOrName);
        var promise = data
            ? $http.post(url, data)
            : $http.get(url);
        promise.success(successCallback);
        if (errorCallback)
            promise.error(errorCallback);
        else
            promise.error(logError);
    };

    return self;
});

app.factory('requestQueue', function($rootScope, requestSender) {
    var self = {};
    var runQueue = [];
    var queueId = 1;
    $rootScope.$on('clearCache', function() {
        runQueue = [];
        queueId++;
    });

    function executeQueue() {
        var queueItem = runQueue[0];
        if (! queueItem)
            return;

        requestSender.sendRequest(
            'runSimulation',
            function(data) {
                handleQueueResult(queueItem, data);
            },
            {
                report: queueItem.item[0],
                models: queueItem.item[1],
            },
            function() {
                handleQueueResult(queueItem, { error: 'a server error occurred' });
            });
    }

    function handleQueueResult(queueItem, data) {
        if (! runQueue.length)
            return;
        if (runQueue[0].id != queueItem.id)
            return;
        runQueue.shift();
        if (data.error)
            queueItem.item[2](null, data.error);
        else
            queueItem.item[2](data);
        executeQueue();
    }

    self.addItem = function(item) {
        var queueItem = {
            id: queueId,
            item: item,
        };
        if (runQueue.length > 0)
            // give this item priority over others
            runQueue.splice(1, 0, queueItem);
        else {
            runQueue.push(queueItem);
            executeQueue();
        }
    };

    return self;
});

app.controller('BeamlineController', function (activeSection, appState) {
    activeSection.setActiveSection('beamline');
    var self = this;
    self.toolbarItems = [
        //TODO(pjm): move default values to separate area
        {type:'aperture', title:'Aperture', horizontalSize:1, verticalSize:1, shape:'r', horizontalOffset:0, verticalOffset:0},
        {type:'crl', title:'CRL', focalPlane:2, refractiveIndex:4.20756805e-06, attenuationLength:7.31294e-03, shape:1,
         horizontalApertureSize:1, verticalApertureSize:1, radius:1.5e-03, numberOfLenses:3, wallThickness:80.e-06},
        {type:'lens', title:'Lens', horizontalFocalLength:3, verticalFocalLength:1.e+23},
        {type:'mirror', title:'Mirror', orientation:'x', grazingAngle:3.1415926, heightAmplification:1, horizontalTransverseSize:1, verticalTransverseSize:1, heightProfileFile:'mirror_1d.dat'},
        {type:'obstacle', title:'Obstacle', horizontalSize:0.5, verticalSize:0.5, shape:'r', horizontalOffset:0, verticalOffset:0},
        {type:'watch', title:'Watchpoint'},
    ];
    self.activeItem = null;
    self.isDirty = false;
    self.postPropagation = [];
    self.propagations = [];

    function addItem(item) {
        self.isDirty = true;
        var newItem = appState.clone(item);
        newItem.id = maxId(appState.models.beamline) + 1;
        newItem.showPopover = true;
        if (appState.models.beamline.length) {
            newItem.position = parseFloat(appState.models.beamline[appState.models.beamline.length - 1].position) + 1;
        }
        else {
            newItem.position = 20;
        }
        if (newItem.type == 'watch')
            appState.models[appState.watchpointReportName(newItem.id)] = appState.cloneModel('initialIntensityReport');
        appState.models.beamline.push(newItem);
        self.dismissPopup();
    }

    function calculatePropagation() {
        if (! appState.isLoaded())
            return;
        var beamline = appState.models.beamline;
        if (! appState.models.propagation)
            appState.models.propagation = {};
        var propagation = appState.models.propagation;
        self.propagations = [];
        for (var i = 0; i < beamline.length; i++) {
            if (! propagation[beamline[i].id]) {
                propagation[beamline[i].id] = [
                    defaultItemPropagationParams(),
                    defaultDriftPropagationParams(),
                ];
            }
            var p = propagation[beamline[i].id];
            if (beamline[i].type != 'watch')
                self.propagations.push({
                    title: beamline[i].title,
                    params: p[0],
                });
            if (i == beamline.length - 1)
                break;
            var d = parseFloat(beamline[i + 1].position) - parseFloat(beamline[i].position)
            if (d > 0) {
                self.propagations.push({
                    title: 'Drift ' + formatFloat(d) + 'm',
                    params: p[1],
                });
            }
        }
        if (! appState.models.postPropagation || appState.models.postPropagation.length == 0)
            appState.models.postPropagation = defaultItemPropagationParams();
        self.postPropagation = appState.models.postPropagation;
    }

    function defaultItemPropagationParams() {
        return [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0];
    }

    function defaultDriftPropagationParams() {
        return [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0];
    }

    function formatFloat(v) {
        var str = v.toFixed(4);
        str = str.replace(/0+$/, '');
        str = str.replace(/\.$/, '');
        return str;
    }

    function maxId(beamline) {
        var max = 1;
        for (var i = 0; i < beamline.length; i++) {
            if (beamline[i].id > max)
                max = beamline[i].id;
        }
        return max;
    }

    self.cancelChanges = function() {
        self.dismissPopup();
        appState.cancelChanges('beamline');
        self.isDirty = false;
    };

    self.dismissPopup = function() {
        $('.srw-beamline-element-label').popover('hide');
    };

    self.dropBetween = function(index, data) {
        if (! data)
            return;
        //console.log('dropBetween: ', index, ' ', data, ' ', data.id ? 'old' : 'new');
        var item;
        if (data.id) {
            self.dismissPopup();
            var curr = appState.models.beamline.indexOf(data);
            if (curr < index)
                index--;
            appState.models.beamline.splice(curr, 1);
            item = data;
        }
        else {
            // move last item to this index
            item = appState.models.beamline.pop()
        }
        appState.models.beamline.splice(index, 0, item);
        if (appState.models.beamline.length > 1) {
            if (index === 0) {
                item.position = parseFloat(appState.models.beamline[1].position) - 0.5;
            }
            else if (index === appState.models.beamline.length - 1) {
                item.position = parseFloat(appState.models.beamline[appState.models.beamline.length - 1].position) + 0.5;
            }
            else {
                item.position = Math.round(100 * (parseFloat(appState.models.beamline[index - 1].position) + parseFloat(appState.models.beamline[index + 1].position)) / 2) / 100;
            }
        }
    };

    self.dropComplete = function(data) {
        if (data && ! data.id) {
            addItem(data);
        }
    };

    self.getBeamline = function() {
        return appState.models.beamline;
    };

    self.getWatchItems = function() {
        return appState.getWatchItems();
    };

    self.isTouchscreen = function() {
        return Modernizr.touch;
    };

    self.removeElement = function(item) {
        self.dismissPopup();
        appState.models.beamline.splice(appState.models.beamline.indexOf(item), 1);
        self.isDirty = true;
    };

    self.saveChanges = function() {
        self.isDirty = false;
        // sort beamline based on position
        appState.models.beamline.sort(function(a, b) {
            return parseFloat(a.position) - parseFloat(b.position);
        });
        calculatePropagation();
        appState.saveBeamline();
    };

    self.showPropagationModal = function() {
        //TODO(pjm): should only set dirty if propagation value changes
        self.isDirty = true;
        calculatePropagation();
        self.dismissPopup();
        $('#srw-propagation-parameters').modal('show');
    };
});

app.controller('NavController', function (activeSection, appState, requestSender) {
    var self = this;

    self.activeSection = function() {
        return activeSection.getActiveSection();
    };

    self.openSection = function(name) {
        requestSender.localRedirect(name, {
            ':simulationId': appState.isLoaded()
                ? appState.models.simulation.simulationId
                : null,
        });
    };

    self.pageTitle = function() {
        return $.grep(
            [
                self.sectionTitle(),
                'SRW',
                'Radiasoft',
            ],
            function(n){ return n })
            .join(' - ');
    };

    self.sectionTitle = function() {
        if (appState.isLoaded())
            return appState.models.simulation.name;
        return null;
    };
});

app.controller('SimulationsController', function ($scope, $window, activeSection, appState, requestSender) {
    activeSection.setActiveSection('simulations');
    var self = this;
    self.list = [];
    self.selected = null;
    appState.clearModels({
        simulation: {},
    });
    $scope.$on('simulation.changed', function() {
        if (appState.models.simulation.name)
            newSimulation(appState.models.simulation.name);
    });

    function newSimulation(name) {
        requestSender.sendRequest(
            'newSimulation',
            function(data) {
                self.open(data.models.simulation);
            },
            {
                name: name,
            });
    }

    function loadList() {
        requestSender.sendRequest(
            'listSimulations',
            function(data) {
                self.list = data;
            });
    }

    self.copy = function(item) {
        requestSender.sendRequest(
            'copySimulation',
            function(data) {
                self.open(data.models.simulation);
            },
            {
                simulationId: self.selected.simulationId,
            });
    };

    self.deleteSelected = function() {
        requestSender.sendRequest(
            'deleteSimulation',
            function() {
                loadList();
            },
            {
                simulationId: self.selected.simulationId,
            });
        self.selected = null;
    };

    self.isSelected = function(item) {
        return self.selected && self.selected == item ? true : false;
    };

    self.open = function(item) {
        requestSender.localRedirect('source', {
            ':simulationId': item.simulationId,
        });
    };

    self.pythonSource = function(item) {
        $window.open(requestSender.formatUrl('pythonSource', {
            '<simulation_id>': self.selected.simulationId,
        }), '_blank');
    };

    self.selectItem = function(item) {
        self.selected = item;
    };

    loadList();
});

app.controller('SourceController', function (activeSection) {
    activeSection.setActiveSection('source');
});
