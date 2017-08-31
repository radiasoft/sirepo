'use strict';
SIREPO.srlog = console.log.bind(console);
SIREPO.srdbg = console.log.bind(console);

// No timeout for now (https://github.com/radiasoft/sirepo/issues/317)
SIREPO.http_timeout = 0;

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

// start the angular app after the app's json schema file has been loaded
angular.element(document).ready(function() {
    $.ajax({
        url: '/simulation-schema' + SIREPO.SOURCE_CACHE_KEY,
        data: {
            simulationType: SIREPO.APP_NAME,
        },
        success: function(result) {
            SIREPO.APP_SCHEMA = result;
            angular.bootstrap(document, ['SirepoApp']);
        },
        error: function(xhr, status, err) {
            if (! SIREPO.APP_SCHEMA) {
                srlog("schema load failed: ", err);
            }
        },
        method: 'POST',
        dataType: 'json',
    });
});

SIREPO.appLocalRoutes = {
    simulations: '/simulations',
    source: '/source/:simulationId',
    loggedOut: '/logged-out',
    notFound: '/not-found',
    notFoundCopy: '/copy-session/:simulationIds',
};

SIREPO.appDefaultSimulationValues = {
    simulation: {},
    simulationFolder: {},
};

SIREPO.IS_LOGGED_OUT = SIREPO.userState && SIREPO.userState.loginState == 'logged_out';


SIREPO.ANIMATION_ARGS_VERSION = 'v';

SIREPO.ANIMATION_ARGS_VERSION_RE = /^v\d+$/;

angular.module('log-broadcasts', []).config(['$provide', function ($provide) {
    $provide.decorator('$rootScope', function ($delegate) {
        var _emit = $delegate.$emit;
        var _broadcast = $delegate.$broadcast;

        $delegate.$emit = function () {
            return _emit.apply(this, arguments);
        };

        $delegate.$broadcast = function () {
            return _broadcast.apply(this, arguments);
        };

        return $delegate;
    });
}]);

// Add "log-broadcasts" in dependencies if you want to see all broadcasts
SIREPO.app = angular.module('SirepoApp', ['ngDraggable', 'ngRoute', 'd3', 'shagstrom.angular-split-pane', 'underscore']);

SIREPO.app.value('localRoutes', SIREPO.appLocalRoutes);

SIREPO.app.config(function(localRoutesProvider, $compileProvider, $locationProvider, $routeProvider) {
    $locationProvider.hashPrefix('');
    $compileProvider.debugInfoEnabled(false);
    var localRoutes = localRoutesProvider.$get();
    if (SIREPO.IS_LOGGED_OUT) {
        $routeProvider.otherwise({
            controller: 'LoggedOutController as loggedOut',
            templateUrl: '/static/html/logged-out.html' + SIREPO.SOURCE_CACHE_KEY,
        });
        return;
    }
    $routeProvider
        .when(localRoutes.simulations, {
            controller: 'SimulationsController as simulations',
            templateUrl: '/static/html/simulations.html' + SIREPO.SOURCE_CACHE_KEY,
        })
        .when(localRoutes.notFound, {
            templateUrl: '/static/html/not-found.html' + SIREPO.SOURCE_CACHE_KEY,
        })
        .when(localRoutes.notFoundCopy, {
            controller: 'NotFoundCopyController as notFoundCopy',
            templateUrl: '/static/html/copy-session.html' + SIREPO.SOURCE_CACHE_KEY,
        })
        .otherwise({
            redirectTo: localRoutes.simulations,
        });
});

SIREPO.app.factory('activeSection', function($route, $rootScope, $location, appState) {
    var self = this;

    self.getActiveSection = function() {
        if (SIREPO.IS_LOGGED_OUT) {
            return null;
        }
        var match = ($location.path() || '').match(/^\/([^\/]+)/);
        return match
            ? match[1]
            : null;
    };

    $rootScope.$on('$routeChangeSuccess', function() {
        if ($route.current.params.simulationId) {
            appState.loadModels($route.current.params.simulationId);
        }
    });

    return self;
});

SIREPO.app.factory('appState', function(errorService, requestSender, requestQueue, $document, $rootScope, $interval, _) {
    var self = {
        models: {},
    };
    var QUEUE_NAME = 'saveSimulationData';
    var AUTO_SAVE_SECONDS = 60;
    var lastAutoSaveData = null;
    var autoSaveTimer = null;
    var savedModelValues = {};
    var activeFolderPath = null;

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

    function propertyToIndexForm(key) {
        return key.split('.').map(function (x) {
            return "['" + x + "']";
        }).join('');
    }

    function refreshSimulationData(data) {
        self.models = data.models;
        self.models.simulationStatus = {};
        savedModelValues = self.cloneModel();
        lastAutoSaveData = self.clone(data);
        updateReports();
        broadcastLoaded();
        self.resetAutoSaveTimer();
    }

    function updateReports() {
        broadcastClear();
        for (var key in self.models) {
            if (self.isReportModelName(key)) {
                broadcastChanged(key);
            }
        }
    }

    self.applicationState = function() {
        return savedModelValues;
    };

    self.areFieldsDirty = function(fieldsByModel) {
        // have any in the list of model fields changed between models and savedModelValues?
        if (! self.isLoaded()) {
            return false;
        }
        var models = self.models;
        for (var m in fieldsByModel) {
            if (models[m]) {
                if (! savedModelValues[m]) {
                    return true;
                }
                for (var i = 0; i < fieldsByModel[m].length; i++) {
                    var f = fieldsByModel[m][i];
                    if (models[m][f] != savedModelValues[m][f]) {
                        return true;
                    }
                }
            }
        }
        return false;
    };

    self.autoSave = function(callback) {
        if (! self.isLoaded() ||
            lastAutoSaveData && self.deepEquals(lastAutoSaveData.models, savedModelValues)
        ) {
            // no changes
            if ($.isFunction(callback)) {
                callback({'state': 'noChanges'});
            }
            return;
        }
        requestQueue.addItem(
            QUEUE_NAME,
            function() {
                self.resetAutoSaveTimer();
                lastAutoSaveData.models = self.clone(savedModelValues);
                return {
                    urlOrParams: 'saveSimulationData',
                    successCallback: function (resp) {
                        if (resp.error && resp.error == 'invalidSerial') {
                            srlog(resp.simulationData.models.simulation.simulationId, ': update collision newSerial=', resp.simulationData.models.simulation.simulationSerial, '; refreshing');
                            refreshSimulationData(resp.simulationData);
                            errorService.alertText("Another browser updated this simulation.This window's state has been refreshed. Please retry your action.");
                        }
                        else {
                            lastAutoSaveData = self.clone(resp);
                            savedModelValues.simulation.simulationSerial
                                = lastAutoSaveData.models.simulation.simulationSerial;
                            self.models.simulation.simulationSerial
                                = lastAutoSaveData.models.simulation.simulationSerial;
                            savedModelValues.simulation.name
                                = lastAutoSaveData.models.simulation.name;
                            self.models.simulation.name
                                = lastAutoSaveData.models.simulation.name;
                        }
                        if ($.isFunction(callback)) {
                            callback(resp);
                        }
                    },
                    errorCallback: function (resp, status) {
                        if ($.isFunction(callback)) {
                            //TODO(robnagler) this should be errorCallback
                            callback(resp);
                        }
                    },
                    data: lastAutoSaveData
                };
            }
        );
    };

    self.cancelChanges = function(name) {
        // cancel changes on a model by name, or by an array of names
        if (typeof(name) == 'string') {
            name = [name];
        }

        for (var i = 0; i < name.length; i++) {
            if (savedModelValues[name[i]]) {
                self.models[name[i]] = self.clone(savedModelValues[name[i]]);
            }
            $rootScope.$broadcast('cancelChanges', name[i]);
        }
    };

    self.clearModels = function(emptyValues) {
        requestQueue.cancelItems(QUEUE_NAME);
        broadcastClear();
        self.models = emptyValues || {};
        savedModelValues = self.clone(self.models);
        if (autoSaveTimer) {
            $interval.cancel(autoSaveTimer);
        }
        $rootScope.$broadcast('modelsUnloaded');
    };

    self.clone = function(obj) {
        return angular.copy(obj);
    };

    self.cloneModel = function(name) {
        var val = name ? self.models[name] : self.models;
        return self.clone(val);
    };

    self.copySimulation = function(simulationId, op, name) {
        requestSender.sendRequest(
            'copySimulation',
            op,
            {
                simulationId: simulationId,
                simulationType: SIREPO.APP_SCHEMA.simulationType,
                name: name,
            });
    };

    self.deepEquals = function(v1, v2) {
        if (angular.isArray(v1) && angular.isArray(v2)) {
            if (v1.length != v2.length) {
                return false;
            }
            for (var i = 0; i < v1.length; i++) {
                if (! self.deepEquals(v1[i], v2[i])) {
                    return false;
                }
            }
            return true;
        }
        if (angular.isObject(v1) && angular.isObject(v2)) {
            var keys = Object.keys(v1);
            if (keys.length != Object.keys(v2).length) {
                return false;
            }
            var isEqual = true;
            keys.forEach(function (k) {
                if (! self.deepEquals(v1[k], v2[k])) {
                    isEqual = false;
                }
            });
            return isEqual;
        }
        return v1 == v2;
    };

    self.deleteSimulation = function(simulationId, op) {
        requestSender.sendRequest(
            'deleteSimulation',
            op,
            {
                simulationId: simulationId,
                simulationType: SIREPO.APP_SCHEMA.simulationType,
            });
    };

    self.getActiveFolderPath = function() {
        return activeFolderPath;
    };

    self.isAnimationModelName = function(name) {
        return name == 'animation' || name.indexOf('Animation') >= 0;
    };

    self.isLoaded = function() {
        return self.models.simulation && self.models.simulation.simulationId ? true: false;
    };

    self.isReportModelName = function(name) {
        //TODO(pjm): need better name for this, a model which doesn't affect other models
        return  name.indexOf('Report') >= 0 || self.isAnimationModelName(name) || name.indexOf('Status') >= 0;
    };

    self.listSimulations = function(search, op) {
        requestSender.sendRequest(
            'listSimulations',
            op,
            {
                simulationType: SIREPO.APP_SCHEMA.simulationType,
                search: search,
            });
    };

    self.loadModels = function(simulationId, callback) {
        if (self.isLoaded() && self.models.simulation.simulationId == simulationId) {
            return;
        }
        self.clearModels();
        requestSender.sendRequest(
            {
                routeName: 'simulationData',
                '<simulation_id>': simulationId,
                '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                '<pretty>': false
            },
            function(data, status) {
                if (data.redirect) {
                    requestSender.localRedirect('notFoundCopy', {
                        ':simulationIds': data.redirect.simulationId
                            + (data.redirect.userCopySimulationId
                               ? ('-' + data.redirect.userCopySimulationId)
                               : ''),
                    });
                    return;
                }
                refreshSimulationData(data);
                if (callback) {
                    callback();
                }
            }
        );
    };

    self.maxId = function(items, idField) {
        var max = 1;
        if (! idField) {
            idField = 'id';
        }
        for (var i = 0; i < items.length; i++) {
            if (items[i][idField] > max) {
                max = items[i][idField];
            }
        }
        return max;
    };

    self.modelInfo = function(name) {
        var info = SIREPO.APP_SCHEMA.model[name];
        if (! info) {
            throw 'invalid model name: ' + name;
        }
        return info;
    };

    self.newSimulation = function(model, op) {
        requestSender.sendRequest(
            'newSimulation',
            op,
            {
                name: model.name,
                folder: model.folder,
                sourceType: model.sourceType,
                simulationType: SIREPO.APP_SCHEMA.simulationType,
            });
    };

    self.parseModelField = function(name) {
        // returns [model, field] from a "model.field" name
        var match = name.match(/(.*?)\.(.*)/);
        if (match) {
            return [match[1], match[2]];
        }
        return null;
    };

    self.removeModel = function(name) {
        delete self.models[name];
        delete savedModelValues[name];
    };

    self.resetAutoSaveTimer = function() {
        // auto save data every 60 seconds
        if (autoSaveTimer) {
            $interval.cancel(autoSaveTimer);
        }
        autoSaveTimer = $interval(self.autoSave, AUTO_SAVE_SECONDS * 1000);
    };

    self.saveQuietly = function(name) {
        // saves the model, but doesn't broadcast the change
        savedModelValues[name] = self.cloneModel(name);
    };

    self.saveChanges = function(name, callback) {
        // save changes on a model by name, or by an array of names
        if (typeof(name) == 'string') {
            name = [name];
        }
        var updatedModels = [];
        var requireReportUpdate = false;

        for (var i = 0; i < name.length; i++) {
            if (self.deepEquals(savedModelValues[name[i]], self.models[name[i]])) {
                // let the UI know the primary model has changed, even if it hasn't
                if (i === 0) {
                    updatedModels.push(name[i]);
                }
            }
            else {
                self.saveQuietly(name[i]);
                updatedModels.push(name[i]);
                if (! self.isReportModelName(name[i])) {
                    requireReportUpdate = true;
                }
            }
        }
        // broadcast model changes prior to autoSave, allows for additional model changes before persisting
        for (i = 0; i < updatedModels.length; i++) {
            if (requireReportUpdate && self.isReportModelName(updatedModels[i])) {
                continue;
            }
            broadcastChanged(updatedModels[i]);
        }
        self.autoSave(function() {
            if (requireReportUpdate) {
                updateReports();
            }
            if (callback) {
                callback();
            }
        });
    };

    self.setActiveFolderPath = function(path) {
        activeFolderPath = path;
    };

    self.setModelDefaults = function(model, modelName) {
        // set model defaults from schema
        var schema = SIREPO.APP_SCHEMA.model[modelName];
        var fields = Object.keys(schema);
        for (var i = 0; i < fields.length; i++) {
            var f = fields[i];
            if (schema[f][2] !== undefined) {
                model[f] = schema[f][2];
            }
        }
        return model;
    };

    self.uniqueName = function(items, idField, template) {
        // find a unique name comparing against a list of items
        // template has {} replaced with a counter, ex. "my name (copy {})"
        var values = {};
        for (var i = 0; i < items.length; i++) {
            values[items[i][idField]] = true;
        }
        var index = 1;
        while (true) {
            var foundIt = false;
            var id = template.replace('{}', index);
            if (values[id]) {
                index++;
            }
            else {
                return id;
            }
        }
    };

    self.viewInfo = function(name) {
        return SIREPO.APP_SCHEMA.view[name];
    };

    self.watchModelFields = function($scope, modelFields, callback) {
        $scope.appState = self;
        modelFields.forEach(function(f) {
            // elegant uses '-' in modelKey
            f = propertyToIndexForm(f);
            $scope.$watch('appState.models' + f, function (newValue, oldValue) {
                if (self.isLoaded() && newValue !== null && newValue !== oldValue) {
                    // call in next cycle to allow UI to change layout first
                    $interval(callback, 1, 1);
                }
            });
        });
    };

    self.whenModelsLoaded = function($scope, callback) {
        var wrappedCallback = function() {
            $document.ready(function() {
                $scope.$applyAsync(callback);
            });
        };
        $scope.$on('modelsLoaded', wrappedCallback);
        if (self.isLoaded()) {
            wrappedCallback();
        }
    };

    return self;
});

SIREPO.app.factory('frameCache', function(appState, panelState, requestSender, $interval, $rootScope) {
    var self = {};
    var frameCountByModelKey = {};
    var masterFrameCount = 0;
    self.animationInfo = {};

    function animationArgs(modelName) {
        var values = appState.applicationState()[modelName];
        var fields = self.animationArgFields[modelName];
        var args = fields.map(function (f) {
            return f.match(SIREPO.ANIMATION_ARGS_VERSION_RE) ? f : values[f];
        });
        return args.join('_');
    }

    self.clearFrames = function(modelName) {
        // TODO(robnagler) if there are locally cached frames, they
        // would be cleared here, but right now they are in the browser
        // cache so do nothing.
        return;
    };

    self.getCurrentFrame = function(modelName) {
        var v = self.animationInfo[modelName];
        if (v) {
            return v.currentFrame;
        }
        return 0;
    };

    self.getFrame = function(modelName, index, isPlaying, callback) {
        if (! appState.isLoaded()) {
            return;
        }
        var isHidden = panelState.isHidden(modelName);
        var frameRequestTime = new Date().getTime();
        var delay = isPlaying && ! isHidden
            ? 1000 / parseInt(appState.models[modelName].framesPerSecond)
            : 0;
        var frameId = [
            SIREPO.APP_SCHEMA.simulationType,
            appState.models.simulation.simulationId,
            modelName,
            animationArgs(modelName),
            index,
        ].join('*');
        var requestFunction = function() {
            requestSender.sendRequest(
                {
                    'routeName': 'simulationFrame',
                    '<frame_id>': frameId,
                },
                function(data) {
                    var endTime = new Date().getTime();
                    var elapsed = endTime - frameRequestTime;
                    if (elapsed < delay) {
                        $interval(
                            function() {
                                callback(index, data);
                            },
                            delay - elapsed,
                            1
                        );
                    }
                    else {
                        callback(index, data);
                    }
                });
        };
        if (isHidden) {
            panelState.addPendingRequest(modelName, requestFunction);
        }
        else {
            requestFunction();
        }
    };

    self.isLoaded = function() {
        return appState.isLoaded();
    };

    self.getFrameCount = function(modelKey) {
        if (modelKey in frameCountByModelKey) {
            return frameCountByModelKey[modelKey];
        }
        return masterFrameCount;
    };

    self.setAnimationArgs = function(argFields) {
        self.animationArgFields = argFields;
    };

    self.setCurrentFrame = function(modelName, currentFrame) {
        if (! self.animationInfo[modelName]) {
            self.animationInfo[modelName] = {};
        }
        self.animationInfo[modelName].currentFrame = currentFrame;
    };

    self.setFrameCount = function(frameCount, modelKey) {
        if (modelKey) {
            frameCountByModelKey[modelKey] = frameCount;
            return;
        }
        if (frameCount == masterFrameCount) {
            return;
        }
        if (frameCount === 0) {
            masterFrameCount = frameCount;
            frameCountByModelKey = {};
            $rootScope.$broadcast('framesCleared');
        }
        else if (frameCount > 0) {
            var oldFrameCount = masterFrameCount;
            masterFrameCount = frameCount;
            $rootScope.$broadcast('framesLoaded', oldFrameCount);
        }
        else {
            masterFrameCount = frameCount;
        }
    };

    $rootScope.$on('modelsUnloaded', function() {
        masterFrameCount = 0;
        frameCountByModelKey = {};
        self.animationInfo = {};
    });

    return self;
});

SIREPO.app.factory('panelState', function(appState, requestSender, simulationQueue, $compile, $rootScope, $timeout, $window) {
    // Tracks the data, error, hidden and loading values
    var self = {};
    var panels = {};
    var pendingRequests = {};
    var queueItems = {};

    $rootScope.$on('clearCache', function() {
        self.clear();
    });

    function clearPanel(name) {
        delete panels[name];
        delete pendingRequests[name];
        // doesn't clear the queueItems, queueItem will be canceled if necessary in requestData()
    }

    function fieldClass(model, field) {
        return '.model-' + model + '-' + field;
    }

    function getPanelValue(name, key) {
        if (panels[name] && panels[name][key]) {
            return panels[name][key];
        }
        return null;
    }

    function iterateFields(primaryModelName, field, names) {
        // iterate the view definition and build a {modelName => [field, ...]} map.
        // may be a string field, [tab-name, [cols]], or [[col-header, [cols]], [col-header, [cols]]]
        if (typeof(field) == 'string') {
            var modelField = appState.parseModelField(field);
            if (! modelField) {
                modelField = [primaryModelName, field];
            }
            if (! names[modelField[0]]) {
                names[modelField[0]] = [];
            }
            names[modelField[0]].push(modelField[1]);
        }
        else {
            var i;
            // [name, [cols]]
            if (typeof(field[0]) == 'string') {
                for (i = 0; i < field[1].length; i++) {
                    iterateFields(primaryModelName, field[1][i], names);
                }
            }
            // [[name, [cols]], [name, [cols]], ...]
            else {
                for (i = 0; i < field.length; i++) {
                    iterateFields(primaryModelName, field[i], names);
                }
            }
        }
    }

    function sendRequest(name, callback, forceRun) {
        setPanelValue(name, 'loading', true);
        setPanelValue(name, 'error', null);
        var responseHandler = function(resp) {
            setPanelValue(name, 'loading', false);
            if (resp.error) {
                setPanelValue(name, 'error', resp.error);
            }
            else {
                setPanelValue(name, 'data', resp);
                setPanelValue(name, 'error', null);
                callback(resp);
            }
        };
        return simulationQueue.addTransientItem(
            name,
            appState.applicationState(),
            responseHandler,
            forceRun
        );
    }

    function setPanelValue(name, key, value) {
        if (! (name || key)) {
            throw 'missing name or key';
        }
        if (! panels[name]) {
            panels[name] = {};
        }
        panels[name][key] = value;
    }

    function showValue(selector, isShown) {
        if (isShown) {
            selector.show();
        }
        else {
            selector.hide();
        }
    }

    self.addPendingRequest = function(name, requestFunction) {
        pendingRequests[name] = requestFunction;
    };

    self.clear = function(name) {
        if (name) {
            clearPanel(name);
        }
        else {
            for (name in panels) {
                clearPanel(name);
            }
        }
    };

    self.enableField = function(model, field, isEnabled) {
        //TODO(pjm): remove jquery and use attributes on the fieldEditor directive
        var fc = fieldClass(model, field);
        // UI fields could be an input, select, or button
        $(fc).find('input.form-control').prop('readonly', ! isEnabled);
        $(fc).find('select.form-control').prop('disabled', ! isEnabled);
        $(fc).find('.sr-enum-button').prop('disabled', ! isEnabled);
    };

    self.findParentAttribute = function(scope, name) {
        while (scope && ! scope[name]) {
            scope = scope.$parent;
        }
        return scope[name];
    };

    self.getError = function(name) {
        return getPanelValue(name, 'error');
    };

    self.getFieldsByModel = function(primaryModelName, fields) {
        var names = {};
        names[primaryModelName] = [];
        for (var i = 0; i < fields.length; i++) {
            iterateFields(primaryModelName, fields[i], names);
        }
        return names;
    };

    self.getStatusText = function(name) {
        if (self.isRunning(name)) {
            var count = (queueItems[name] && queueItems[name].runStatusCount) || 0;
            return 'Simulating ' + new Array(count % 3 + 2).join('.');
        }
        return 'Waiting';
    };

    self.isHidden = function(name) {
        if (! appState.isLoaded()) {
            return true;
        }
        var state = appState.applicationState();
        if (state.panelState) {
            return state.panelState.hidden.indexOf(name) >= 0;
        }
        return false;
    };

    self.isLoading = function(name) {
        return getPanelValue(name, 'loading') ? true : false;
    };

    self.isRunning = function(name) {
        return queueItems[name] && queueItems[name].qState == 'processing' ? true : false;
    };

    self.modalId = function(name) {
        return 'sr-' + name + '-editor';
    };

    self.pythonSource = function(simulationId, modelName) {
        var args = {
            '<simulation_id>': simulationId,
            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
        };
        if (modelName) {
            args['<model>'] = modelName;
        }
        $window.open(requestSender.formatUrl('pythonSource', args), '_blank');
    };

    self.requestData = function(name, callback, forceRun) {
        if (! appState.isLoaded()) {
            return;
        }
        var data = getPanelValue(name, 'data');
        if (data) {
            callback(data);
            return;
        }
        var wrappedCallback = function(data) {
            delete pendingRequests[name];
            delete queueItems[name];
            callback(data);
        };
        if (queueItems[name]) {
            simulationQueue.cancelItem(queueItems[name]);
        }
        self.addPendingRequest(name, function() {
            queueItems[name] = sendRequest(name, wrappedCallback, forceRun);
        });
        if (! self.isHidden(name)) {
            queueItems[name] = sendRequest(name, wrappedCallback, forceRun);
        }
    };

    self.setError = function(name, error) {
        setPanelValue(name, 'error', error);
    };

    self.showField = function(model, field, isShown) {
        //TODO(pjm): remove jquery and use attributes on the fieldEditor directive
        $timeout(function() {  //MR: fix for https://github.com/radiasoft/sirepo/issues/730
            showValue($(fieldClass(model, field)).closest('.form-group'), isShown);
        });
    };

    self.showRow = function(model, field, isShown) {
        //TODO(pjm): remove jquery and use attributes on the fieldEditor directive
        $timeout(function() {  //MR: fix for https://github.com/radiasoft/sirepo/issues/730
            showValue($(fieldClass(model, field)).closest('.row').parent(), isShown);
        });
    };

    self.showTab = function(model, pageNumber, isShown) {
        showValue($('.' + model + '-page-' + pageNumber), isShown);
    };

    self.showModalEditor = function(modelKey, template, scope) {
        var editorId = '#' + self.modalId(modelKey);

        if ($(editorId).length) {
            $(editorId).modal('show');
        }
        else {
            if (! template) {
                template = '<div data-modal-editor="" data-view-name="' + modelKey + '"></div>';
            }
            $('body').append($compile(template)(scope || $rootScope));
            //TODO(pjm): timeout hack, other jquery can't find the element
            $timeout(function() {
                $(editorId).modal('show');
            });
        }
    };

    self.toggleHidden = function(name) {
        var state = appState.applicationState();
        if (! state.panelState) {
            state.panelState = {
                hidden: [],
            };
        }
        if (self.isHidden(name)) {
            state.panelState.hidden.splice(state.panelState.hidden.indexOf(name), 1);

            if (pendingRequests[name] && ! queueItems[name]) {
                var requestFunction = pendingRequests[name];
                requestFunction();
            }
            // needed to resize a hidden report
            if (appState.isReportModelName(name)) {
                $($window).trigger('resize');
            }
        }
        else {
            state.panelState.hidden.push(name);
            if (queueItems[name]) {
                simulationQueue.cancelItem(queueItems[name]);
                delete queueItems[name];
            }
        }
    };

    return self;
});

SIREPO.app.factory('requestSender', function(errorService, localRoutes, $http, $location, $interval, $q, _) {
    var self = {};
    var getApplicationDataTimeout = {};
    var IS_HTML_ERROR_RE = new RegExp('^(?:<html|<!doctype)', 'i');
    var HTML_TITLE_RE = new RegExp('>([^<]+)</', 'i');

    function logError(data, status) {
        if (status == 404) {
            self.localRedirect('notFound');
        }
        else {
            errorService.alertText('Request failed: ' + data.error);
        }
    }

    function formatUrl(map, routeOrParams, params) {
        var routeName = routeOrParams;
        if (angular.isObject(routeOrParams)) {
            routeName = routeOrParams.routeName;
            if (! routeName) {
                throw routeOrParams + ': routeName must be supplied';
            }
            if (angular.isDefined(params)) {
                srlog(arguments);
                throw params + ': params must be null if routeOrParams is an object: ' + routeOrParams;
            }
            params = angular.copy(routeOrParams);
            delete params.routeName;
        }
        if (! map[routeName]) {
            throw routeName + ': routeName not found';
        }
        var url = map[routeName];
        if (params) {
            for (var k in params) {
                if (url.indexOf(k) < 0) {
                    throw k + ': param not found in route: ' + map[routeName];
                }
                url = url.replace(
                    k,
                    encodeURIComponent(serializeValue(params[k], k)));
            }
        }
        // remove optional params missed and then that were replaced
        url = url.replace(/\/\?<[^>]+>/g, '');
        url = url.replace(/\/\?/g, '/');
        var missing = url.match(/<[^>]+>/g);
        if (missing) {
            throw missing.join() + ': missing parameter(s) for route: ' + map[routeName];
        }
        return url;
    }

    // Started from serializeValue in angular, but need more specialization.
    // https://github.com/angular/angular.js/blob/2420a0a77e27b530dbb8c41319b2995eccf76791/src/ng/http.js#L12
    function serializeValue(v, param) {
        if (v === null) {
            throw param + ': may not be null';
        }
        if (typeof v == 'boolean') {
            //TODO(robnagler) probably needs to be true/false with test
            return v ? '1' : '0';
        }
        if (angular.isString(v)) {
            if (v === '')
                throw param + ': may not be empty string';
            return v;
        }
        if (angular.isNumber(v)) {
            return v.toString();
        }
        if (angular.isDate(v)) {
            return v.toISOString();
        }
        throw param + ': ' + (typeof v) + ' type cannot be serialized';
    }

    self.formatAuthUrl = function(oauthType) {
        return self.formatUrl('oauthLogin', {
            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
            '<oauth_type>': oauthType,
        }) + '?next=' + $location.url();
    };

    self.formatUrlLocal = function(routeName, params) {
        return formatUrl(localRoutes, routeName, params);
    };

    self.formatUrl = function(routeName, params) {
        return formatUrl(SIREPO.APP_SCHEMA.route, routeName, params);
    };

    self.getApplicationData = function(data, callback) {
        // debounce the method so server calls don't go on every keystroke
        // track method calls by methodSignature (for shared methods) or method name (for unique methods)
        var signature = data.methodSignature || data.method;
        if (getApplicationDataTimeout[signature]) {
            $interval.cancel(getApplicationDataTimeout[signature]);
        }
        getApplicationDataTimeout[signature] = $interval(function() {
            delete getApplicationDataTimeout[signature];
            data.simulationType = SIREPO.APP_SCHEMA.simulationType;
            self.sendRequest('getApplicationData', callback, data);
        }, 350, 1);
    };

    self.getAuxiliaryData = function(name) {
        return self[name];
    };

    self.isRouteParameter = function(routeName, paramName) {
        return (localRoutes[routeName] || SIREPO.APP_SCHEMA.route[routeName]).indexOf(paramName) >= 0;
    };

    self.loadAuxiliaryData = function(name, path, callback) {
        if (self[name] || self[name + ".loading"]) {
            if (callback) {
                callback(self[name]);
            }
            return;
        }
        self[name + ".loading"] = true;
        $http.get(path + '' + SIREPO.SOURCE_CACHE_KEY).then(
            function(response) {
                var data = response.data;
                self[name] = data;
                delete self[name + ".loading"];
                if (callback) {
                    callback(data);
                }
            },
            function() {
                srlog(path, ' load failed!');
                delete self[name + ".loading"];
            });
    };

    self.localRedirect = function(routeName, params) {
        $location.path(self.formatUrlLocal(routeName, params));
    };

    self.sendRequest = function(urlOrParams, successCallback, data, errorCallback) {
        if (! errorCallback) {
            errorCallback = logError;
        }
        if (! successCallback) {
            successCallback = function () {};
        }
        var url = angular.isString(urlOrParams) && urlOrParams.indexOf('/') >= 0
            ? urlOrParams
            : self.formatUrl(urlOrParams);
        var timeout = $q.defer();
        var interval, t;
        var timed_out = false;
        t = {timeout: timeout.promise};
        if (SIREPO.http_timeout > 0) {
            interval = $interval(
                function () {
                    timed_out = true;
                    timeout.resolve();
                },
                SIREPO.http_timeout,
                1
            );
        }
        var req = data
            ? $http.post(url, data, t)
            : $http.get(url, t);
        var thisErrorCallback = function(response) {
            var data = response.data;
            var status = response.status;
            $interval.cancel(interval);
            var msg = null;
            if (timed_out) {
                msg = 'request timed out after '
                    + Math.round(SIREPO.http_timeout/1000)
                    + ' seconds';
                status = 504;
            }
            else if (status === 0) {
                msg = 'the server is unavailable';
                status = 503;
            }
            if (_.isString(data) && IS_HTML_ERROR_RE.exec(data)) {
                var m = HTML_TITLE_RE.exec(data);
                if (m) {
                    srlog(m[1], ': error response from server');
                    data = {error: m[1]};
                }
            }
            if (_.isEmpty(data)) {
                data = {};
            }
            else if (! _.isObject(data)) {
                errorService.logToServer(
                    'serverResponseError', data, 'unexpected response type or empty');
                data = {};
            }
            if (! data.state) {
                data.state = 'error';
            }
            if (! data.error) {
                if (msg) {
                    data.error = msg;
                }
                else {
                    srlog(response);
                    data.error = 'a server error occurred' + (status ? (': status=' + status) : '');
                }
            }
            srlog(data.error);
            errorCallback(data, status);
        };
        req.then(
            function(response) {
                var data = response.data;
                $interval.cancel(interval);
                if (_.isObject(data)) {
                    successCallback(data, response.status);
                }
                else {
                    thisErrorCallback(data, response.status);
                }
            },
            thisErrorCallback);
    };

    return self;
});

SIREPO.app.factory('simulationQueue', function($rootScope, $interval, requestSender) {
    var self = {};
    var runQueue = [];

    function addItem(report, models, responseHandler, qMode, forceRun) {
        models = angular.copy(models);
        // Not used server side and contains a lot of stuff
        delete models.simulationStatus;
        var qi = {
            firstRoute: qMode == 'persistentStatus' ? 'runStatus' : 'runSimulation',
            qMode: qMode,
            persistent: qMode.indexOf('persistent') > -1,
            qState: 'pending',
            runStatusCount: 0,
            request: {
                forceRun: qMode == 'persistent' || forceRun ? true : false,
                report: report,
                models: models,
                simulationType: SIREPO.APP_SCHEMA.simulationType,
                simulationId: models.simulation.simulationId,
            },
            responseHandler: responseHandler,
        };
        runQueue.push(qi);
        if (qi.persistent) {
            runItem(qi);
        }
        else {
            runFirstTransientItem();
        }
        return qi;
    }

    function cancelInterval(qi) {
        if (! qi.interval) {
            return;
        }
        $interval.cancel(qi.interval);
        qi.interval = null;
    }

    function handleResult(qi, resp) {
        qi.qState = 'done';
        self.removeItem(qi);
        qi.responseHandler(resp);
        runFirstTransientItem();
    }

    function runFirstTransientItem() {
        $.each(
            runQueue,
            function(i, e) {
                if (e.persistent) {
                    return true;
                }
                if (e.qState == 'pending') {
                    runItem(e);
                }
                return false;
            }
        );
    }

    function runItem(qi) {
        var handleStatus = function(qi, resp) {
            qi.request = resp.nextRequest;
            qi.interval = $interval(
                function () {
                    qi.runStatusCount++;
                    requestSender.sendRequest(
                        'runStatus', process, qi.request, process);
                },
                // Sanity check in case of defect on server
                Math.max(1, resp.nextRequestSeconds) * 1000,
                1
            );
            if (qi.persistent) {
                qi.responseHandler(resp);
            }
        };

        var process = function(resp, status) {
            if (qi.qState == 'removing') {
                return;
            }
            resp.isStateProcessing = resp.state == 'running' || resp.state == 'pending';
            if (! resp.isStateProcessing) {
                handleResult(qi, resp);
                return;
            }
            handleStatus(qi, resp);
        };

        cancelInterval(qi);
        qi.qState = 'processing';
        requestSender.sendRequest(qi.firstRoute, process, qi.request, process);
    }

    self.addPersistentStatusItem = function(report, models, responseHandler) {
        return addItem(report, models, responseHandler, 'persistentStatus');
    };

    self.addPersistentItem = function(report, models, responseHandler) {
        return addItem(report, models, responseHandler, 'persistent');
    };

    self.addTransientItem = function(report, models, responseHandler, forceRun) {
        return addItem(report, models, responseHandler, 'transient', forceRun);
    };

    self.cancelAllItems = function() {
        var rq = runQueue;
        runQueue = [];
        while (rq.length > 0) {
            self.removeItem(rq.shift());
        }
    };

    self.cancelItem = function (qi) {
        if (! qi) {
            return;
        }
        qi.qMode = 'transient';
        var isProcessingTransient = qi.qState == 'processing' && ! qi.persistent;
        if (qi.qState == 'processing') {
            requestSender.sendRequest('runCancel', null, qi.request);
            qi.qState = 'canceled';
        }
        self.removeItem(qi);
        if (isProcessingTransient) {
            runFirstTransientItem();
        }
    };

    self.removeItem = function(qi) {
        if (! qi) {
            return;
        }
        var qs = qi.qState;
        if (qs == 'removing') {
            return;
        }
        qi.qState = 'removing';
        var i = runQueue.indexOf(qi);
        if (i > -1) {
            runQueue.splice(i, 1);
        }
        cancelInterval(qi);
        if (qs == 'processing' && ! qi.persistent) {
            requestSender.sendRequest('runCancel', null, qi.request);
        }
    };

    $rootScope.$on('$routeChangeSuccess', self.cancelAllItems);
    $rootScope.$on('clearCache', self.cancelAllItems);

    return self;
});

SIREPO.app.factory('requestQueue', function($rootScope, requestSender) {
    var self = {};
    var queueMap = {};

    function getQueue(name) {
        if (! queueMap[name] ) {
            queueMap[name] = [];
        }
        return queueMap[name];
    }

    function sendNextItem(name) {
        var q = getQueue(name);
        if ( q.length <= 0 ) {
            return;
        }
        var qi = q[0];
        if ( qi.requestSent ) {
            return;
        }
        qi.requestSent = true;
        qi.params = qi.paramsCallback();
        var process = function(ok, resp, status) {
            if (qi.canceled) {
                sendNextItem(name);
                return;
            }
            q.shift();
            var cb = ok ? qi.params.successCallback : qi.params.errorCallback;
            if (cb) {
                cb(resp, status);
            }
            sendNextItem(name);
        };
        requestSender.sendRequest(
            qi.params.urlOrParams,
            function (resp, status) {process(true, resp, status);},
            qi.params.data,
            function (resp, status) {process(false, resp, status);}
        );
    }

    self.cancelItems = function(queueName) {
        var q = getQueue(queueName);
        q.forEach(function(qi) {qi.canceled = true;});
        q.length = 0;
    };

    self.addItem = function(queueName, paramsCallback) {
        getQueue(queueName).push({
            requestSent: false,
            paramsCallback: paramsCallback
        });
        sendNextItem(queueName);
    };
    return self;
});

SIREPO.app.factory('persistentSimulation', function(simulationQueue, appState, panelState, frameCache) {
    var self = {};
    self.initProperties = function(controller, $scope, animationArgs) {
        controller.frameId = '-1';
        controller.frameCount = 1;
        controller.isReadyForModelChanges = false;
        controller.simulationQueueItem = null;
        controller.dots = '.';
        controller.timeData = {
            elapsedDays: null,
            elapsedTime: null,
        };
        controller.panelState = panelState;
        controller.percentComplete = 0;

        function handleStatus(data) {
            setSimulationStatus(data);
            if (data.elapsedTime) {
                controller.timeData.elapsedDays = parseInt(data.elapsedTime / (60 * 60 * 24));
                controller.timeData.elapsedTime = new Date(1970, 0, 1);
                controller.timeData.elapsedTime.setSeconds(data.elapsedTime);
            }
            if (data.percentComplete) {
                controller.percentComplete = data.percentComplete;
            }
            if (data.isStateProcessing) {
                controller.dots += '.';
                if (controller.dots.length > 3) {
                    controller.dots = '.';
                }
            }
            else {
                controller.simulationQueueItem = null;
            }
            controller.handleStatus(data);
        }

        function isState(state) {
            if (! appState.isLoaded()) {
                return false;
            }
            for (var i = 1; i < arguments.length; i++) {
                if (state == arguments[i]) {
                    return true;
                }
            }
            return false;
        }

        function persistentSimulationInit($scope) {
            if (! controller.model) {
                throw 'missing persistentSimulation model';
            }
            setSimulationStatus({state: 'stopped'});
            frameCache.setFrameCount(0);
            $scope.$on('$destroy', controller.clearSimulation);
            appState.whenModelsLoaded($scope, runStatus);
        }

        function runStatus() {
            controller.isReadyForModelChanges = true;
            controller.simulationQueueItem = simulationQueue.addPersistentStatusItem(
                controller.model,
                appState.models,
                handleStatus
            );
        }

        function setSimulationStatus(data) {
            if (!appState.models.simulationStatus) {
                appState.models.simulationStatus = {};
            }
            data.report = controller.model;
            appState.models.simulationStatus[controller.model] = data;
            if (appState.isLoaded()) {
                // simulationStatus is not saved to server from client
                appState.saveQuietly('simulationStatus');
            }
        }

        controller.cancelSimulation = function() {
            setSimulationStatus({state: 'canceled'});
            simulationQueue.cancelItem(controller.simulationQueueItem);
            controller.simulationQueueItem = null;
        };

        controller.clearSimulation = function() {
            simulationQueue.removeItem(controller.simulationQueueItem);
            controller.simulationQueueItem = null;
        };

        controller.displayPercentComplete = function() {
            if (controller.isInitializing() || controller.isStatePending()) {
                return 100;
            }
            return controller.percentComplete;
        };

        controller.hasTimeData = function () {
            return controller.timeData && controller.timeData.elapsedTime !== null;
        };

        controller.isInitializing = function() {
            if (controller.isStateProcessing() && ! controller.isStatePending()) {
                return frameCache.getFrameCount() < 1;
            }
            return false;
        };

        controller.isStatePending = function() {
            return controller.simulationStatus().state == 'pending';
        };

        controller.isStateProcessing = function() {
            return controller.simulationStatus().isStateProcessing;
        };

        controller.isStateRunning = function() {
            return controller.simulationStatus().state == 'running';
        };

        controller.isStateStopped = function() {
            return ! controller.isStateProcessing();
        };

        controller.runSimulation = function() {
            if (controller.isStateProcessing()) {
                //TODO(robnagler) this shouldn't happen? (double click?)
                return;
            }
            //TODO(robnagler) should be part of simulationStatus
            frameCache.setFrameCount(0);
            controller.timeData.elapsedTime = null;
            controller.timeData.elapsedDays = null;
            setSimulationStatus({state: 'pending'});
            controller.simulationQueueItem = simulationQueue.addPersistentItem(
                controller.model,
                appState.models,
                handleStatus
            );
        };

        controller.simulationState = function() {
            return controller.simulationStatus().state;
        };

        controller.simulationStatus = function() {
            if (appState.models.simulationStatus && appState.models.simulationStatus[controller.model]) {
                return appState.models.simulationStatus[controller.model];
            }
            return {state: 'pending'};
        };

        controller.stateAsText = function() {
            var s = controller.simulationState();
            var msg;
            msg = s.charAt(0).toUpperCase() + s.slice(1);
            if (s == 'error') {
                var e = controller.simulationStatus().error;
                if (e) {
                    msg += ': ' + e.split(/[\n\r]+/)[0];
                }
            }
            return msg;
        };

        frameCache.setAnimationArgs(animationArgs);
        persistentSimulationInit($scope);
    };
    return self;
});

// Exception logging from
// http://engineering.talis.com/articles/client-side-error-logging/
SIREPO.app.factory('traceService', function() {
    var self = {};
    self.printStackTrace = printStackTrace;
    return self;
});

SIREPO.app.provider('$exceptionHandler', {
    $get: function(errorService) {
        return errorService.exceptionHandler;
    }
});

SIREPO.app.factory('errorService', function($log, $window, traceService) {
    var self = this;
    var alertText = null;

    self.exceptionHandler = function(exception, cause) {
        // preserve the default behaviour which will log the error
        // to the console, and allow the application to continue running.
        $log.error.apply($log, arguments);
        // now try to log the error to the server side.
        try {
            var message = exception ? String(exception) : '';
            cause = cause ? String(cause) : '';
            // use our traceService to generate a stack trace
            var stackTrace = traceService.printStackTrace({e: exception});
            // use AJAX (in this example jQuery) and NOT
            // an angular service such as $http
            self.logToServer(
                'clientException',
                message || '<no message>',
                cause || '<no cause>',
                stackTrace
            );
            self.alertText(
                'Application Error: ' + (message || cause || 'unknown state') +
                    '. A report was sent to the server.'
            );
        }
        catch (loggingError) {
            $log.error(loggingError, ': unable to prepare error to logToServer');
        }
    };

    self.logToServer = function(errorType, message, cause, stackTrace) {
        $.ajax({
            type: 'POST',
            //url: localRoutes.errorLogging,
            url: '/error-logging',
            contentType: 'application/json',
            data: angular.toJson({
                url: $window.location.href,
                message: message,
                type: errorType,
                stackTrace: stackTrace,
                cause: cause,
            }),
            error: function(jqXRH, textStatus, errorThrown) {
                $log.error(
                    textStatus,
                    ': logToServer failed: originalMessage=',
                    message,
                    '; exception=',
                    errorThrown
                );
            },
        });
    };

    self.alertText = function(value) {
        if (angular.isDefined(value)) {
            alertText = value;
        }
        return alertText;
    };

    return self;
});

SIREPO.app.controller('NavController', function (activeSection, appState, requestSender, $window) {
    var self = this;

    function openSection(name) {
        requestSender.localRedirect(name, sectionParams(name));
    }

    function sectionParams(name) {
        if (requestSender.isRouteParameter(name, ':simulationId') && appState.isLoaded()) {
            return {
                ':simulationId': appState.models.simulation.simulationId,
            };
        }
        return {};
    }

    self.isActive = function(name) {
        return activeSection.getActiveSection() == name;
    };

    self.openSection = function(name) {
        if (name == 'simulations' && appState.isLoaded()) {
            appState.autoSave(function() {
                openSection(name);
            });
        }
        else {
            openSection(name);
        }
    };

    self.pageTitle = function() {
        return $.grep(
            [
                self.sectionTitle(),
                SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_NAME].shortName,
                'Radiasoft',
            ],
            function(n){ return n; })
            .join(' - ');
    };

    self.revertToOriginal = function(applicationMode, name) {
        if (! appState.isLoaded()) {
            return;
        }
        var url = requestSender.formatUrl(
            'findByName',
            {
                '<simulation_name>': name,
                '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                '<application_mode>': applicationMode,
            });
        appState.deleteSimulation(
            appState.models.simulation.simulationId,
            function() {
                $window.location.href = url;
            });
    };

    self.sectionTitle = function() {
        if (appState.isLoaded()) {
            return appState.models.simulation.name;
        }
        return null;
    };

    self.sectionURL = function(name) {
        if (! name) {
            name = 'source';
        }
        return '#' + requestSender.formatUrlLocal(name, sectionParams(name));
    };
});

SIREPO.app.controller('NotFoundCopyController', function (requestSender, $route) {
    var self = this;
    var ids = $route.current.params.simulationIds.split('-');
    self.simulationId = ids[0];
    self.userCopySimulationId = ids[1];

    self.cancelButton = function() {
        requestSender.localRedirect('simulations');
    };

    self.copyButton = function() {
        requestSender.sendRequest(
            'copyNonSessionSimulation',
            function(data) {
                requestSender.localRedirect('source', {
                    ':simulationId': data.models.simulation.simulationId,
                });
            },
            {
                simulationId: self.simulationId,
                simulationType: SIREPO.APP_SCHEMA.simulationType,
            });
    };

    self.hasUserCopy = function() {
        return self.userCopySimulationId;
    };

    self.openButton = function() {
        requestSender.localRedirect('source', {
            ':simulationId': self.userCopySimulationId,
        });
    };
});

SIREPO.app.controller('LoggedOutController', function (requestSender) {
    var self = this;
    self.anonymousUrl = requestSender.formatAuthUrl('anonymous');
    self.githubUrl = requestSender.formatAuthUrl('github');
});

SIREPO.app.controller('SimulationsController', function (appState, panelState, requestSender, $location, $scope, $window) {
    var self = this;
    var SORT_DESCENDING = '-';
    self.activeFolder = null;
    self.activeFolderPath = [];
    self.listColumns = [
        {
            field: 'name',
            heading: 'Name',
        },
        {
            field: 'lastModified',
            heading: 'Last Modified',
        }];
    //TODO(pjm): store view state in db preference or client cookie
    self.isIconView = true;
    self.fileTree = [];
    self.selectedItem = null;
    self.sortField = 'name';

    function addToTree(item) {
        var path = item.folder == '/'
            ? []
            : item.folder.slice(1).split('/');
        var currentFolder = rootFolder();

        while (path.length) {
            var search = path.shift();
            var folder = null;
            for (var i = 0; i < currentFolder.children.length; i++) {
                if (search == currentFolder.children[i].name && currentFolder.children[i].isFolder) {
                    folder = currentFolder.children[i];
                    break;
                }
            }
            if (folder) {
                if (item.last_modified > folder.lastModified) {
                    folder.lastModified = item.last_modified;
                }
            }
            else {
                folder = {
                    name: search,
                    parent: currentFolder,
                    isFolder: true,
                    children: [],
                    lastModified: item.last_modified,
                };
                currentFolder.children.push(folder);
            }
            currentFolder = folder;
        }
        var newItem = {
            parent: currentFolder,
            name: item.name,
            simulationId: item.simulationId,
            lastModified: item.last_modified,
        };
        currentFolder.children.push(newItem);
        return newItem;
    }

    function clearModels() {
        appState.clearModels(appState.clone(SIREPO.appDefaultSimulationValues));
    }

    function folderList(excludeFolder, res, searchFolder) {
        if (! res) {
            searchFolder = rootFolder();
            res = [searchFolder];
        }
        for (var i = 0; i < searchFolder.children.length; i++) {
            var child = searchFolder.children[i];
            if (child.isFolder && child != excludeFolder) {
                res.push(child);
                folderList(excludeFolder, res, child);
            }
        }
        return res;
    }

    function loadList() {
        var showItem = null;
        var activeFolder = appState.getActiveFolderPath();
        appState.listSimulations(
            $location.search(),
            function(data) {
                data.sort(function(a, b) {
                    return a.last_modified.localeCompare(b.last_modified);
                });
                self.fileTree = [
                    {
                        name: '/',
                        isFolder: true,
                        children: [],
                    },
                ];
                for (var i = 0; i < data.length; i++) {
                    var item = addToTree(data[i]);
                    if (activeFolder && data[i].folder == activeFolder) {
                        showItem = item;
                    }
                }
                if (showItem) {
                    self.openItem(showItem.parent);
                }
                else {
                    self.openItem(rootFolder());
                }
            });
    }

    function removeItemFromFolder(item) {
        var parent = item.parent;
        parent.children.splice(parent.children.indexOf(item), 1);
    }

    function renameSelectedItem() {
        self.selectedItem.name = self.renameName;
    }

    function reparentSelectedItem(oldParent) {
        oldParent.children.splice(oldParent.children.indexOf(self.selectedItem), 1);
        self.selectedItem.parent = self.targetFolder;
        self.targetFolder.children.push(self.selectedItem);
        self.targetFolder = null;
    }

    function rootFolder() {
        return self.fileTree[0];
    }

    function setActiveFolder(item) {
        self.activeFolder = item;
        self.activeFolderPath = [];
        while (item) {
            self.activeFolderPath.unshift(item);
            item = item.parent;
        }
        appState.setActiveFolderPath(self.pathName(self.activeFolder));
    }

    function updateSelectedFolder(oldPath) {
        requestSender.sendRequest(
            'updateFolder',
            function() {
                self.selectedItem = null;
            },
            {
                oldName: oldPath,
                newName: self.pathName(self.selectedItem),
                simulationType: SIREPO.APP_SCHEMA.simulationType,
            });
    }

    function updateSelectedItem(op) {
        appState.loadModels(
            self.selectedItem.simulationId,
            function() {
                op();
                appState.saveQuietly('simulation');
                appState.autoSave(clearModels);
                self.selectedItem = null;
            });
    }

    self.canDelete = function(item) {
        if (item.isFolder) {
            return item.children.length === 0;
        }
        return true;
    };

    self.copyItem = function(item) {
        self.selectedItem = item;
        var names = {};
        for (var i = 0; i < self.activeFolder.children.length; i++) {
            names[self.activeFolder.children[i].name] = true;
        }
        var count = 2;
        var name = item.name;
        name = name.replace(/\s+\d+$/, '');
        while (names[name + ' ' + count])
            count++;
        self.copyName = name + ' ' + count;
        $('#sr-copy-confirmation').modal('show');
    };

    self.copySelected = function() {
        appState.copySimulation(
            self.selectedItem.simulationId,
            function(data) {
                self.openItem(data.models.simulation);
            },
            self.copyName);
    };

    self.deleteItem = function(item) {
        if (item.isFolder) {
            removeItemFromFolder(item);
        }
        else {
            self.selectedItem = item;
            $('#sr-delete-confirmation').modal('show');
        }
    };

    self.deleteSelected = function() {
        appState.deleteSimulation(
            self.selectedItem.simulationId,
            function() {
                removeItemFromFolder(self.selectedItem);
                self.selectedItem = null;
            });
    };

    self.isActiveFolder = function(item) {
        return item == self.activeFolder;
    };

    self.isRootFolder = function(item) {
        return item == rootFolder();
    };

    self.isSortAscending = function() {
        return self.sortField.charAt(0) != SORT_DESCENDING;
    };

    self.moveItem = function(item) {
        self.selectedItem = item;
        self.targetFolder = item.parent;
        self.moveFolderList = folderList(item);
        $('#sr-move-confirmation').modal('show');
    };

    self.moveSelected = function() {
        var parent = self.selectedItem.parent;
        if (self.targetFolder == parent) {
            return;
        }
        if (self.selectedItem.isFolder) {
            var oldPath = self.pathName(self.selectedItem);
            reparentSelectedItem(parent);
            updateSelectedFolder(oldPath);
        }
        else {
            updateSelectedItem(function() {
                appState.models.simulation.folder = self.pathName(self.targetFolder);
                reparentSelectedItem(parent);
            });
        }
    };

    self.openItem = function(item) {
        if (item.isFolder) {
            item.isOpen = true;
            setActiveFolder(item);
            var current = item;
            while (current != rootFolder()) {
                current = current.parent;
                current.isOpen = true;
            }
        }
        else {
            requestSender.localRedirect('source', {
                ':simulationId': item.simulationId,
            });
        }
    };

    self.pathName = function(folder) {
        if (self.isRootFolder(folder)) {
            return '/';
        }
        var path = '/' + folder.name;
        while (folder.parent != rootFolder()) {
            folder = folder.parent;
            path = '/' + folder.name + path;
        }
        return path;
    };

    self.pythonSource = function(item) {
        panelState.pythonSource(item.simulationId);
    };

    self.exportArchive = function(item, extension) {
        $window.open(requestSender.formatUrl('exportArchive', {
            '<simulation_id>': item.simulationId,
            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
            '<filename>': item.name + '.' + extension,
        }), '_blank');
    };

    self.renameItem = function(item) {
        self.selectedItem = item;
        self.renameName = item.name;
        $('#sr-rename-confirmation').modal('show');
    };

    self.renameSelected = function() {
        if (! self.renameName || (self.renameName == self.selectedItem.name)) {
            return;
        }
        if (self.selectedItem.isFolder) {
            var oldPath = self.pathName(self.selectedItem);
            renameSelectedItem();
            updateSelectedFolder(oldPath);
        }
        else {
            updateSelectedItem(function() {
                appState.models.simulation.name = self.renameName;
                renameSelectedItem();
            });
        }
    };

    self.selectedItemType = function(item) {
        if (self.selectedItem && self.selectedItem.isFolder) {
            return 'Folder';
        }
        return 'Simulation';
    };

    self.showSimulationModal = function() {
        panelState.showModalEditor('simulation');
    };

    self.toggleIconView = function() {
        self.isIconView = ! self.isIconView;
    };

    self.toggleFolder = function(item) {
        if (item == self.activeFolder) {
            item.isOpen = ! item.isOpen;
        }
        else {
            setActiveFolder(item);
            item.isOpen = true;
        }
    };

    self.toggleSort = function(field) {
        if (self.sortField.indexOf(field) >= 0) {
            self.sortField = self.isSortAscending() ? (SORT_DESCENDING + field) : field;
        }
        else {
            self.sortField = field;
        }
    };

    clearModels();
    $scope.$on('simulation.changed', function() {
        appState.models.simulation.folder = self.pathName(self.activeFolder);
        appState.newSimulation(
            appState.models.simulation,
            function(data) {
                self.openItem(data.models.simulation);
            });
    });
    $scope.$on('simulationFolder.changed', function() {
        var name = appState.models.simulationFolder.name;
        name = name.replace(/[\/]/g, '');
        self.activeFolder.children.push({
            name: name,
            parent: self.activeFolder,
            isFolder: true,
            children: [],
        });
        appState.models.simulationFolder.name = '';
        appState.saveQuietly('simulationFolder');
    });
    loadList();
});
