'use strict';

// start the angular app after the app's json schema file has been loaded
angular.element(document).ready(function() {
    $.ajax({
        url: '/simulation-schema?' + SIREPO.APP_VERSION,
        data: {
            simulationType: SIREPO.APP_NAME,
        },
        success: function(result) {
            SIREPO.APP_SCHEMA = result;
            angular.bootstrap(document, ['SirepoApp']);
        },
        error: function(xhr, status, err) {
            if (! SIREPO.APP_SCHEMA)
                console.log("schema load failed: ", err);
        },
        method: 'POST',
        dataType: 'json',
    });
});

SIREPO.appLocalRoutes = {
    simulations: '/simulations',
    source: '/source/:simulationId',
    notFound: '/not-found',
    notFoundCopy: '/copy-session/:simulationIds',
};

SIREPO.appDefaultSimulationValues = {
    simulation: {},
    simulationFolder: {},
};

SIREPO.app = angular.module('SirepoApp', ['ngDraggable', 'ngRoute', 'd3', 'shagstrom.angular-split-pane']);

SIREPO.app.value('localRoutes', SIREPO.appLocalRoutes);

SIREPO.app.config(function($routeProvider, localRoutesProvider) {
    var localRoutes = localRoutesProvider.$get();
    $routeProvider
        .when(localRoutes.simulations, {
            controller: 'SimulationsController as simulations',
            templateUrl: '/static/html/simulations.html?' + SIREPO.APP_VERSION,
        })
        .when(localRoutes.notFound, {
            templateUrl: '/static/html/not-found.html?' + SIREPO.APP_VERSION,
        })
        .when(localRoutes.notFoundCopy, {
            controller: 'NotFoundCopyController as notFoundCopy',
            templateUrl: '/static/html/copy-session.html?' + SIREPO.APP_VERSION,
        })
        .otherwise({
            redirectTo: localRoutes.simulations,
        });
});

SIREPO.app.factory('activeSection', function($route, $rootScope, $location, appState) {
    var self = this;

    self.getActiveSection = function() {
        var match = ($location.path() || '').match(/^\/([^\/]+)/);
        return match
            ? match[1]
            : null;
    };

    $rootScope.$on('$routeChangeSuccess', function() {
        if ($route.current.params.simulationId)
            appState.loadModels($route.current.params.simulationId);
    });

    return self;
});

SIREPO.app.factory('appState', function(requestSender, $rootScope, $interval) {
    var self = {};
    self.models = {};
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

    self.autoSave = function(callback) {
        if (! self.isLoaded)
            return;
        self.resetAutoSaveTimer();
        if (lastAutoSaveData && self.deepEquals(lastAutoSaveData, savedModelValues)) {
            // no changes
            if (callback)
                callback();
            return;
        }
        lastAutoSaveData = self.clone(savedModelValues);
        requestSender.sendRequest(
            'saveSimulationData',
            callback,
            {
                models: savedModelValues,
                simulationType: SIREPO.APP_SCHEMA.simulationType,
            });
    };

    self.cancelChanges = function(name) {
        // cancel changes on a model by name, or by an array of names
        if (typeof(name) == 'string')
            name = [name];

        for (var i = 0; i < name.length; i++) {
            if (savedModelValues[name[i]])
                self.models[name[i]] = self.clone(savedModelValues[name[i]]);
            $rootScope.$broadcast('cancelChanges', name[i]);
        }
    };

    self.clearModels = function(emptyValues) {
        broadcastClear();
        self.models = emptyValues || {};
        savedModelValues = self.clone(self.models);
        if (autoSaveTimer)
            $interval.cancel(autoSaveTimer);
    };

    self.clone = function(obj) {
        return JSON.parse(JSON.stringify(obj));
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
        return name.indexOf('Animation') >= 0;
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
        if (self.isLoaded() && self.models.simulation.simulationId == simulationId)
            return;
        self.clearModels();
        requestSender.sendRequest(
            requestSender.formatUrl(
                'simulationData',
                {
                    '<simulation_id>': simulationId,
                    '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                }),
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
                self.models = data.models;
                savedModelValues = self.cloneModel();
                updateReports();
                broadcastLoaded();
                self.resetAutoSaveTimer();
                if (callback)
                    callback();
            });
    };

    self.maxId = function(items, idField) {
        var max = 1;
        if (! idField)
            idField = 'id';
        for (var i = 0; i < items.length; i++) {
            if (items[i][idField] > max)
                max = items[i][idField];
        }
        return max;
    };

    self.modelInfo = function(name) {
        return SIREPO.APP_SCHEMA.model[name];
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
        if (match)
            return [match[1], match[2]];
        return null;
    };

    self.removeModel = function(name) {
        delete self.models[name];
        delete savedModelValues[name];
    };

    self.resetAutoSaveTimer = function() {
        // auto save data every 60 seconds
        if (autoSaveTimer)
            $interval.cancel(autoSaveTimer);
        autoSaveTimer = $interval(self.autoSave, 60000);
    };

    self.saveQuietly = function(name) {
        // saves the model, but doesn't broadcast the change
        savedModelValues[name] = self.cloneModel(name);
    };

    self.saveChanges = function(name) {
        // save changes on a model by name, or by an array of names
        if (typeof(name) == 'string')
            name = [name];
        var updatedModels = [];
        var requireReportUpdate = false;

        for (var i = 0; i < name.length; i++) {
            if (self.deepEquals(savedModelValues[name[i]], self.models[name[i]])) {
                // let the UI know the primary model has changed, even if it hasn't
                if (i === 0)
                    updatedModels.push(name[i]);
            }
            else {
                self.saveQuietly(name[i]);
                updatedModels.push(name[i]);
                if (! self.isReportModelName(name[i]))
                    requireReportUpdate = true;
            }
        }

        for (i = 0; i < updatedModels.length; i++) {
            if (requireReportUpdate && self.isReportModelName(updatedModels[i]))
                continue;
            broadcastChanged(updatedModels[i]);
        }

        if (requireReportUpdate)
            updateReports();
    };

    self.setActiveFolderPath = function(path) {
        activeFolderPath = path;
    };

    self.viewInfo = function(name) {
        return SIREPO.APP_SCHEMA.view[name];
    };

    self.whenModelsLoaded = function(callback) {
        if (self.isLoaded())
            callback();
        else
            $rootScope.$on('modelsLoaded', callback);
    };

    return self;
});

SIREPO.app.factory('frameCache', function(appState, panelState, requestSender, $timeout, $rootScope) {
    var self = {};
    var frameCountByModelKey = {};
    var masterFrameCount = 0;
    self.animationInfo = {};


    function animationArgs(modelName) {
        var values = appState.applicationState()[modelName];
        var fields = self.animationArgFields[modelName];
        var args = [];
        for (var i = 0; i < fields.length; i++)
            args.push(values[fields[i]]);
        return args.join('_');
    }

    self.clearFrames = function(modelName) {
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
                        report: self.animationModelName || modelName,
                        simulationId: appState.models.simulation.simulationId,
                        simulationType: SIREPO.APP_SCHEMA.simulationType,
                    });
            },
            {
                report: self.animationModelName || modelName,
                models: appState.applicationState(),
                simulationType: SIREPO.APP_SCHEMA.simulationType,
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
        var isHidden = panelState.isHidden(modelName);
        var startTime = new Date().getTime();
        var delay = isPlaying && ! isHidden
            ? 1000 / parseInt(appState.models[modelName].framesPerSecond)
            : 0;
        var frameId = [
            SIREPO.APP_SCHEMA.simulationType,
            appState.models.simulation.simulationId,
            modelName,
            animationArgs(modelName),
            index,
            appState.models.simulationStatus[self.animationModelName || modelName].startTime,
        ].join('*');

        var requestFunction = function() {
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
        if (isHidden)
            panelState.addPendingRequest(modelName, requestFunction);
        else
            requestFunction();
    };

    self.isLoaded = function() {
        return appState.isLoaded();
    };

    self.getFrameCount = function(modelKey) {
        if (modelKey in frameCountByModelKey)
            return frameCountByModelKey[modelKey];
        return masterFrameCount;
    };

    self.setAnimationArgs = function(argFields, animationModelName) {
        self.animationArgFields = argFields;
        if (animationModelName)
            self.animationModelName = animationModelName;
    };

    self.setCurrentFrame = function(modelName, currentFrame) {
        if (! self.animationInfo[modelName])
            self.animationInfo[modelName] = {};
        self.animationInfo[modelName].currentFrame = currentFrame;
    };

    self.setFrameCount = function(frameCount, modelKey) {
        if (modelKey) {
            frameCountByModelKey[modelKey] = frameCount;
            return;
        }
        if (frameCount == masterFrameCount)
            return;
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

    return self;
});

SIREPO.app.factory('panelState', function(appState, requestQueue, $compile, $rootScope, $timeout, $window) {
    // Tracks the data, error, hidden and loading values
    var self = {};
    var panels = {};
    var pendingRequests = {};
    $rootScope.$on('clearCache', function() {
        self.clear();
    });

    function clearPanel(name) {
        delete panels[name];
        delete pendingRequests[name];
    }

    function getPanelValue(name, key) {
        if (panels[name] && panels[name][key])
            return panels[name][key];
        return null;
    }

    function sendRequest(name, callback) {
        appState.resetAutoSaveTimer();
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
        requestQueue.addItem(name, appState.applicationState(), responseHandler);
    }

    function setPanelValue(name, key, value) {
        if (! (name || key))
            throw 'missing name or key';
        if (! panels[name])
            panels[name] = {};
        panels[name][key] = value;
    }

    self.addPendingRequest = function(name, requestFunction) {
        pendingRequests[name] = requestFunction;
    };

    self.clear = function(name) {
        if (name)
            clearPanel(name);
        else {
            for (name in panels)
                clearPanel(name);
        }
    };

    self.getError = function(name) {
        return getPanelValue(name, 'error');
    };

    self.isHidden = function(name) {
        if (! appState.isLoaded())
            return true;
        var state = appState.applicationState();
        if (state.panelState)
            return state.panelState.hidden.indexOf(name) >= 0;
        return false;
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
        if (self.isHidden(name)) {
            self.addPendingRequest(name, function() {
                sendRequest(name, callback);
            });
        }
        else
            sendRequest(name, callback);
    };

    self.setError = function(name, error) {
        setPanelValue(name, 'error', error);
    };

    self.showModalEditor = function(modelKey, template, scope) {
        var editorId = '#s-' + modelKey + '-editor';

        if ($(editorId).length)
            $(editorId).modal('show');
        else {
            if (! template)
                template = '<div data-modal-editor="" data-view-name="' + modelKey + '"></div>';
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

            if (pendingRequests[name]) {
                var requestFunction = pendingRequests[name];
                delete pendingRequests[name];
                requestFunction();
            }
            // needed to resize a hidden report
            if (appState.isReportModelName(name))
                $($window).trigger('resize');
        }
        else
            state.panelState.hidden.push(name);
    };

    return self;
});

SIREPO.app.factory('requestSender', function(localRoutes, $http, $location, $timeout) {
    var self = {};
    var getApplicationDataTimeout;

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
    };

    self.formatUrl = function(routeName, params) {
        return formatUrl(SIREPO.APP_SCHEMA.route, routeName, params);
    };

    self.getApplicationData = function(data, callback) {
        // debounce the method so server calls don't go on every keystroke
        if (getApplicationDataTimeout)
            $timeout.cancel(getApplicationDataTimeout);
        getApplicationDataTimeout = $timeout(function() {
            getApplicationDataTimeout = null;
            data.simulationType = SIREPO.APP_SCHEMA.simulationType;
            self.sendRequest('getApplicationData', callback, data);
        }, 350);
    };

    self.getAuxiliaryData = function(name) {
        return self[name];
    };

    self.loadAuxiliaryData = function(name, path, callback) {
        if (self[name] || self[name + ".loading"]) {
            if (callback)
                callback(self[name]);
            return;
        }
        self[name + ".loading"] = true;
        $http.get(path + '?' + SIREPO.APP_VERSION)
            .success(function(data, status) {
                self[name] = data;
                delete self[name + ".loading"];
                if (callback)
                    callback(data);
            })
            .error(function() {
                console.log(path, ' load failed!');
                delete self[name + ".loading"];
            });
    };

    self.localRedirect = function(routeName, params, search) {
        $location.path(self.formatLocalUrl(routeName, params));
        if (search)
            $location.search(search);
    };

    self.sendRequest = function(urlOrName, successCallback, data, errorCallback) {
        var url = urlOrName.indexOf('/') >= 0
            ? urlOrName
            : self.formatUrl(urlOrName);
        var promise = data
            ? $http.post(url, data)
            : $http.get(url);
        if (successCallback)
            promise.success(successCallback);
        if (errorCallback)
            promise.error(errorCallback);
        else
            promise.error(logError);
    };

    return self;
});

SIREPO.app.factory('requestQueue', function($rootScope, $interval, requestSender) {
    var self = {};
    var runQueue = [];
    var queueId = 1;
    var poller = null;

    function cancelPoller() {
        if (! poller)
            return;
        $interval.cancel(poller);
        poller = null;
    }

    function clearQueue() {
        var qi = runQueue[0]
        cancelPoller();
        if (! qi)
            return;
        console.log('clearQueue: ' + qi.request.report);
        runQueue.length = 0
        requestSender.sendRequest('zrunCancel', null, qi.request);
    }


    function executeQueue() {
        var qi = runQueue[0];
        if (! qi)
            return;
        console.log('executeQueue: ' + qi.request.report);
        var process = function(resp, status) {
            cancelPoller();
            // handle errors
            if ($.isEmptyObject(resp) || resp.error || status != 200) {
                if (!resp.error)
                    resp.error = (resp === null && status === 0)
                        ? 'the server is unavailable'
                        : 'a server error occurred',
                console.log('error: ' + qi.request.report + ' ' + status + ' resp=' + resp);
                handleQueueResult(qi, resp);
                return;
            }
            if (resp.state != 'running') {
                handleQueueResult(qi, resp);
                return;
            }
            if (resp.hasOwnProperty('reportParametersHash'))
                qi.request = resp
            poller = $interval(
                function () {
                    requestSender.sendRequest(
                        'zrunResult', process, qi.request, process);
                },
                1000,
                1
            );
        };
        requestSender.sendRequest('zrunSimulation', process, qi.request, process);
    }

    function handleQueueResult(qi, resp) {
        if (! runQueue.length)
            return;
        if (runQueue[0].id != qi.id)
            return;
        runQueue.shift();
        if (resp.error)
            qi.responseHandler(null, resp.error);
        else
            qi.responseHandler(resp);
        executeQueue();
    }

    self.addItem = function(report, models, responseHandler) {
        var qi = {
            id: queueId,
            responseHandler: responseHandler,
            request: {
                report: report,
                models: models,
                simulationType: SIREPO.APP_SCHEMA.simulationType
            }
        };
        runQueue.push(qi);
        console.log('addItem: ' + qi.request.report + ' runqueu: ' + runQueue.length);
        if (runQueue.length == 1)
            executeQueue();
    };

    $rootScope.$on('$routeChangeSuccess', clearQueue);
    $rootScope.$on('clearCache', clearQueue);

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
    $get: function(exceptionLoggingService) {
        return exceptionLoggingService;
    }
});

SIREPO.app.factory('exceptionLoggingService', function($log, $window, traceService) {
    function error(exception, cause) {
        // preserve the default behaviour which will log the error
        // to the console, and allow the application to continue running.
        $log.error.apply($log, arguments);
        // now try to log the error to the server side.
        try{
            var errorMessage = exception.toString();
            // use our traceService to generate a stack trace
            var stackTrace = traceService.printStackTrace({e: exception});
            // use AJAX (in this example jQuery) and NOT
            // an angular service such as $http
            $.ajax({
                type: 'POST',
                //url: localRoutes.errorLogging,
                url: '/error-logging',
                contentType: 'application/json',
                data: angular.toJson({
                    url: $window.location.href,
                    message: errorMessage,
                    type: 'exception',
                    stackTrace: stackTrace,
                    cause: cause || '',
                })
            });
        }
        catch (loggingError) {
            $log.warn('Error server-side logging failed');
            $log.log(loggingError);
        }
    }
    return error;
});

SIREPO.app.controller('NavController', function (activeSection, appState, requestSender, $window) {
    var self = this;

    function openSection(name, search) {
        requestSender.localRedirect(name, {
            ':simulationId': appState.isLoaded()
                ? appState.models.simulation.simulationId
                : null,
        }, search);
    }

    self.isActive = function(name) {
        return activeSection.getActiveSection() == name;
    };

    self.openSection = function(name) {
        if (name == 'simulations' && appState.isLoaded()) {
            appState.autoSave(function() {
                openSection(name, {
                    show_item_id: appState.models.simulation.simulationId,
                });
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
                SIREPO.APP_NAME.toUpperCase(),
                'Radiasoft',
            ],
            function(n){ return n; })
            .join(' - ');
    };

    self.revertToOriginal = function(applicationMode, name) {
        if (! appState.isLoaded())
            return;
        var url = requestSender.formatUrl(
            'findByName',
            {
                '<simulation_name>': encodeURIComponent(name),
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
        if (appState.isLoaded())
            return appState.models.simulation.name;
        return null;
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

SIREPO.app.controller('SimulationsController', function (appState, panelState, requestSender, $location, $scope, $window) {
    var self = this;
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
    var showItemId = $location.search().show_item_id;

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
                if (item.last_modified > folder.lastModified)
                    folder.lastModified = item.last_modified;
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
                    if (showItemId && (item.simulationId == showItemId))
                        showItem = item;
                }
                if (showItem)
                    self.openItem(showItem.parent);
                else
                    self.openItem(rootFolder());
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
        if (item.isFolder)
            return item.children.length === 0;
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
        $('#s-copy-confirmation').modal('show');
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
        if (item.isFolder)
            removeItemFromFolder(item);
        else {
            self.selectedItem = item;
            $('#s-delete-confirmation').modal('show');
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
        return self.sortField.charAt(0) != '-';
    };

    self.moveItem = function(item) {
        self.selectedItem = item;
        self.targetFolder = item.parent;
        self.moveFolderList = folderList(item);
        $('#s-move-confirmation').modal('show');
    };

    self.moveSelected = function() {
        var parent = self.selectedItem.parent;
        if (self.targetFolder == parent)
            return;
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
        if (self.isRootFolder(folder))
            return '/';
        var path = '/' + folder.name;
        while (folder.parent != rootFolder()) {
            folder = folder.parent;
            path = '/' + folder.name + path;
        }
        return path;
    };

    self.pythonSource = function(item) {
        $window.open(requestSender.formatUrl('pythonSource', {
            '<simulation_id>': item.simulationId,
            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
        }), '_blank');
    };

    self.renameItem = function(item) {
        self.selectedItem = item;
        self.renameName = item.name;
        $('#s-rename-confirmation').modal('show');
    };

    self.renameSelected = function() {
        if (! self.renameName || (self.renameName == self.selectedItem.name))
            return;
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
        if (self.selectedItem && self.selectedItem.isFolder)
            return 'Folder';
        return 'Simulation';
    };

    self.showSimulationModal = function() {
        panelState.showModalEditor('simulation');
    };

    self.toggleIconView = function() {
        self.isIconView = ! self.isIconView;
    };

    self.toggleFolder = function(item) {
        if (item == self.activeFolder)
            item.isOpen = ! item.isOpen;
        else {
            setActiveFolder(item);
            item.isOpen = true;
        }
    };

    self.toggleSort = function(field) {
        if (self.sortField.indexOf(field) >= 0) {
            self.sortField = self.isSortAscending() ? ('-' + field) : field;
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
