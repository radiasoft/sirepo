'use strict';

var APP_SCHEMA;

// Load the application schema synchronously, before creating app module
//TODO(pjm): deprecated, change this to a requires/callback
$.ajax({
    url: typeof KARMA_TEST_MODE == 'undefined'
        ? ('/simulation-schema?' + SIREPO_APP_VERSION)
        : '/static/json/test-schema.json',
    data: {
        simulationType: SIREPO_APP_NAME,
    },
    success: function(result) {
        APP_SCHEMA = result;
    },
    error: function(xhr, status, err) {
        console.log("schema load failed: ", err);
    },
    async: false,
    method: typeof KARMA_TEST_MODE == 'undefined' ? 'POST' : 'GET',
    dataType: 'json',
});

var app = angular.module('SirepoApp', ['ngAnimate', 'ngDraggable', 'ngRoute', 'd3']);

var APP_LOCAL_ROUTES = {
    simulations: '/simulations',
    source: '/source/:simulationId',
    notFound: '/not-found',
};

app.value('localRoutes', APP_LOCAL_ROUTES);

app.config(function($routeProvider, localRoutesProvider) {
    var localRoutes = localRoutesProvider.$get();
    $routeProvider
        .when(localRoutes.simulations, {
            controller: 'SimulationsController as simulations',
            templateUrl: '/static/html/simulations.html?' + SIREPO_APP_VERSION,
        })
        .when(localRoutes.notFound, {
            templateUrl: '/static/html/not-found.html?' + SIREPO_APP_VERSION,
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
        $rootScope.$broadcast('modelChanged', name);
    }

    function broadcastLoaded() {
        $rootScope.$broadcast('modelsLoaded');
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

    self.addNewElectronBeam = function() {
        var newBeam = self.clone(self.models.electronBeam);
        delete newBeam.isReadOnly;
        newBeam.name = 'Beam Name';
        newBeam.id = self.maxId(self.models.electronBeams) + 1;
        self.models.electronBeams.push(newBeam);
        self.models.electronBeam = newBeam;
    };

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

    self.deepEquals = function(v1, v2) {
        if (angular.isArray(v1) && angular.isArray(v2)) {
            if (v1.length != v2.length)
                return false;
            for (var i = 0; i < v1.length; i++) {
                if (! self.deepEquals(v1[i], v2[i]))
                    return false;
            }
            return true;
        }
        if (angular.isObject(v1) && angular.isObject(v2)) {
            var keys = Object.keys(v1);
            if (keys.length != Object.keys(v2).length)
                return false;
            var isEqual = true;
            keys.forEach(function (k) {
                if (! self.deepEquals(v1[k], v2[k]))
                    isEqual = false;
            });
            return isEqual;
        }
        return v1 == v2;
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
                if (savedModelValues.beamline[i].id == id) {
                    return 'Intensity at ' + savedModelValues.beamline[i].title + ' Report, '
                        + savedModelValues.beamline[i].position + 'm';

                }
            }
        }
        var model = savedModelValues[name];
        var distance = '';
        if (model && model.distanceFromSource != null)
            distance = ', ' + model.distanceFromSource + 'm';
        else if (self.isReportModelName(name) && savedModelValues.beamline && savedModelValues.beamline.length)
            distance = ', ' + savedModelValues.beamline[0].position + 'm';
        return self.viewInfo(name).title + distance;
    };

    self.isAnimationModelName = function(name) {
        return name.indexOf('Animation') >= 0;
    };

    self.isLoaded = function() {
        return self.models.simulation && self.models.simulation.simulationId ? true: false;
    };

    self.isReportModelName = function(name) {
        //TODO(pjm): need better name for this, a model which doesn't affect other models
        return  name.indexOf('Report') >= 0 || self.isAnimationModelName(name) || name.indexOf('Status') >= 0;
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
                    '<simulation_type>': APP_SCHEMA.simulationType,
                }),
            function(data, status) {
                self.models = data.models;
                savedModelValues = self.cloneModel();
                updateReports();
                broadcastLoaded();
            });
    };

    self.maxId = function(items) {
        var max = 1;
        for (var i = 0; i < items.length; i++) {
            if (items[i].id > max)
                max = items[i].id;
        }
        return max;
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

    self.saveQuietly = function(name) {
        // saves the model, but doesn't broadcast the change
        savedModelValues[name] = self.cloneModel(name);
    }

    self.saveChanges = function(name) {
        if (name == 'electronBeam') {
            // keep beamSelector in sync with name, sort beams by name
            self.models.electronBeam.beamSelector = self.models.electronBeam.name;
            if (! self.models.electronBeam.isReadOnly) {
                // update the user defined beam in the electronBeams list
                for (var i = 0; i < self.models.electronBeams.length; i++) {
                    var beam = self.models.electronBeams[i];
                    if (beam.id == self.models.electronBeam.id) {
                        self.models.electronBeams.splice(i, 1, self.models.electronBeam);
                        break;
                    }
                }
            }
            self.models.electronBeams.sort(function(a, b) {
                return a.name.localeCompare(b.name);
            });
        }
        self.saveQuietly(name);

        if (name == 'electronBeam') {
            broadcastChanged(name);
            self.saveChanges('electronBeams');
            // save electronBeam and electronBeams, but only repolot reports once
            return;
        }
        broadcastChanged(name);
        if (! self.isReportModelName(name))
            updateReports();
    };

    self.viewInfo = function(name) {
        return APP_SCHEMA.view[name];
    };

    self.watchpointReportName = function(id) {
        return 'watchpointReport' + id;
    }

    return self;
});

app.factory('frameCache', function(appState, requestSender, $timeout, $rootScope) {
    var self = {};
    self.animationInfo = {};
    self.frameCount = 0;

    function animationArgs(modelName) {
        var values = appState.applicationState()[modelName];
        var fields = self.animationArgFields[modelName];
        var args = [];
        for (var i = 0; i < fields.length; i++)
            args.push(values[fields[i]]);
        return args.join('_');
    }

    self.clearFrames = function() {
        if (! appState.isLoaded())
            return;
        requestSender.sendRequest(
            'runCancel',
            function() {
                requestSender.sendRequest(
                    'clearFrames',
                    function() {
                        self.setFrameCount(0);
                    },
                    {
                        simulationId: appState.models.simulation.simulationId,
                        simulationType: APP_SCHEMA.simulationType,
                    });
            },
            {
                models: appState.applicationState(),
                simulationType: APP_SCHEMA.simulationType,
            });
    };

    self.getCurrentFrame = function(modelName) {
        var v = self.animationInfo[modelName];
        if (v)
            return v.currentFrame;
        return 0;
    };

    self.getFrame = function(modelName, index, isPlaying, callback) {
        if (! appState.isLoaded())
            return;
        var startTime = new Date().getTime();
        var delay = isPlaying
            ? 1000 / parseInt(appState.models[modelName].framesPerSecond)
            : 0;
        var frameId = [
            APP_SCHEMA.simulationType,
            appState.models.simulation.simulationId,
            modelName,
            animationArgs(modelName),
            index,
            appState.models.simulationStatus.startTime,
        ].join('-');
        requestSender.sendRequest(
            requestSender.formatUrl(
                'simulationFrame',
                {
                    '<frame_id>': frameId,
                }),
            function(data) {
                var endTime = new Date().getTime();
                var elapsed = endTime - startTime;
                if (elapsed < delay)
                    $timeout(function() {
                        callback(index, data);
                    }, delay - elapsed);
                else
                    callback(index, data);
            });
    };

    self.isLoaded = function() {
        return appState.isLoaded();
    };

    self.setAnimationArgs = function(argFields) {
        self.animationArgFields = argFields;
    };

    self.setCurrentFrame = function(modelName, currentFrame) {
        if (! self.animationInfo[modelName])
            self.animationInfo[modelName] = {};
        self.animationInfo[modelName].currentFrame = currentFrame;
    };

    self.setFrameCount = function(frameCount) {
        if ((frameCount > 0) && (frameCount != self.frameCount)) {
            var oldFrameCount = self.frameCount;
            self.frameCount = frameCount;
            $rootScope.$broadcast('framesLoaded', oldFrameCount);
        }
        else {
            self.frameCount = frameCount;
        }
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
            //console.log('cached: ', name);
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
        //console.log('requesting: ', name);
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

    function logError(data, status) {
        console.log('request failed: ', data);
        if (status == 404)
            self.localRedirect('notFound');
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

    self.getAuxiliaryData = function(name, path) {
        if (self[name] || self[name + ".loading"])
            return;
        self[name + ".loading"] = true;
        $http['get'](path + '?' + SIREPO_APP_VERSION)
            .success(function(data, status) {
                self[name] = data;
                delete self[name + ".loading"];
            })
            .error(function() {
                console.log(path, ' load failed!');
                delete self[name + ".loading"];
            });
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
                simulationType: APP_SCHEMA.simulationType,
            },
            function(data, status) {
                handleQueueResult(queueItem, {
                    error: (data == null && status == 0)
                        ? 'the server is unavailable'
                        : 'a server error occurred',
                });
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
                SIREPO_APP_NAME.toUpperCase(),
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

    self.showBeamline = function() {
        return SIREPO_APP_NAME == 'srw';
    };

    self.showDynamics = function() {
        return SIREPO_APP_NAME == 'warp';
    };
});

app.controller('SimulationsController', function ($scope, $window, activeSection, appState, requestSender) {
    activeSection.setActiveSection('simulations');
    var self = this;
    self.list = [];
    self.selected = null;
    appState.clearModels({
        simulation: {
            sourceType: 'u',
        },
    });
    $scope.$on('simulation.changed', function() {
        newSimulation(appState.models.simulation);
    });

    function newSimulation(model) {
        requestSender.sendRequest(
            'newSimulation',
            function(data) {
                self.open(data.models.simulation);
            },
            {
                name: model.name,
                sourceType: model.sourceType,
                simulationType: APP_SCHEMA.simulationType,
            });
    }

    function loadList() {
        requestSender.sendRequest(
            'listSimulations',
            function(data) {
                self.list = data;
            },
            {
                simulationType: APP_SCHEMA.simulationType,
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
                simulationType: APP_SCHEMA.simulationType,
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
                simulationType: APP_SCHEMA.simulationType,
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
            '<simulation_type>': APP_SCHEMA.simulationType,
        }), '_blank');
    };

    self.selectItem = function(item) {
        self.selected = item;
    };

    loadList();
});
