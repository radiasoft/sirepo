'use strict';
SIREPO.srlog = console.log.bind(console);
SIREPO.srdbg = console.log.bind(console);

// No timeout for now (https://github.com/radiasoft/sirepo/issues/317)
SIREPO.http_timeout = 0;

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

// start the angular app after the app's json schema file has been loaded
angular.element(document).ready(function() {

    function loadDynamicModule(src) {
        return src.match(/\.css$/)
            ? addTag(src, 'link', 'head', 'href', {'rel': 'stylesheet'})
            : addTag(src, 'script', 'body', 'src', {'type': 'text/javascript', 'async': true});
    }

    function addTag(src, name, parent, uri, attrs) {
        var d = $.Deferred();
        var t = document.createElement(name);
        t[uri] = src + SIREPO.SOURCE_CACHE_KEY;
        $.extend(t, attrs);
        document.getElementsByTagName(parent)[0].appendChild(t);
        t.onload = function () {
            d.resolve();
        };
        return d.promise();
    }

    function loadDynamicModules() {
        var mods = [];
        for(var type in SIREPO.APP_SCHEMA.dynamicModules) {
            mods = mods.concat(SIREPO.APP_SCHEMA.dynamicModules[type] || []);
        }
        mods = mods.concat(SIREPO.APP_SCHEMA.dynamicFiles.libURLs || []);
        return $.map(
            mods,
            function(src) {
                return loadDynamicModule(src);
            });
    }

    $.ajax({
        url: '/simulation-schema' + SIREPO.SOURCE_CACHE_KEY,
        data: {
            simulationType: SIREPO.APP_NAME,
        },
        success: function(result) {
            SIREPO.APP_SCHEMA = result;
            $.when.apply($, loadDynamicModules()).then(
                function() {
                    angular.bootstrap(document, ['SirepoApp']);
                }
            );
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

SIREPO.appDefaultSimulationValues = {
    simulation: {
        folder: '/'
    },
    simFolder: {},
};

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
SIREPO.app = angular.module('SirepoApp', ['ngDraggable', 'ngRoute', 'ngCookies', 'ngSanitize']);

SIREPO.app.value('localRoutes', {});

SIREPO.app.config(function(localRoutesProvider, $compileProvider, $locationProvider, $routeProvider) {
    var localRoutes = localRoutesProvider.$get();
    $locationProvider.hashPrefix('');
    $compileProvider.debugInfoEnabled(false);
    $compileProvider.commentDirectivesEnabled(false);
    $compileProvider.cssClassDirectivesEnabled(false);

    function addRoute(routeName) {
        var routeInfo = SIREPO.APP_SCHEMA.localRoutes[routeName];
        if (! routeInfo.config) {
            // the route isn't configured for the current app
            return;
        }
        localRoutes[routeName] = routeInfo.route;
        var cfg = routeInfo.config;
        cfg.templateUrl += SIREPO.SOURCE_CACHE_KEY;
        $routeProvider.when(routeInfo.route, cfg);
        if (routeInfo.isDefault) {
            if (routeInfo.route.indexOf(':') >= 0) {
                throw 'default route must not have params: ' + routeInfo.route;
            }
            cfg.redirectTo = routeInfo.route;
            $routeProvider.otherwise(cfg);
        }
    }

    for (var routeName in SIREPO.APP_SCHEMA.localRoutes) {
        addRoute(routeName);
    }
});

SIREPO.app.factory('authState', function(appState) {
    var self = appState.clone(SIREPO.authState);

    return self;
});

SIREPO.app.factory('activeSection', function($route, $rootScope, $location, appState, authState) {
    var self = this;

    self.getActiveSection = function() {
        if (! authState.isLoggedIn) {
            return null;
        }
        var m = ($location.path() || '').match(/^\/([^\/]+)/);
        return m ? m[1] : null;
    };

    $rootScope.$on('$routeChangeSuccess', function() {
        if ($route.current.params.simulationId) {
            appState.loadModels($route.current.params.simulationId, null, self.getActiveSection());
        }
    });

    return self;
});

SIREPO.app.factory('appState', function(errorService, fileManager, requestQueue, requestSender, $document, $interval, $rootScope, $window) {
    var self = {
        models: {},
    };
    var QUEUE_NAME = 'saveSimulationData';
    var AUTO_SAVE_SECONDS = 60;
    var lastAutoSaveData = null;
    var autoSaveTimer = null;
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
        self.updateReports();
        broadcastLoaded();
        self.resetAutoSaveTimer();
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
                    if (! self.deepEquals(models[m][f], savedModelValues[m][f])) {
                        return true;
                    }
                }
            }
        }
        return false;
    };

    self.autoSave = function(callback, errorCallback) {
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
                    errorCallback: function (resp) {
                        if ($.isFunction(errorCallback)) {
                            //TODO(robnagler) this should be errorCallback
                            errorCallback(resp);
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

    self.copySimulation = function(simulationId, op, name, folder) {
        requestSender.sendRequest(
            'copySimulation',
            op,
            {
                simulationId: simulationId,
                simulationType: SIREPO.APP_SCHEMA.simulationType,
                name: name,
                folder: folder || '/',
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
            function() {
              op();
              fileManager.removeSimFromTree(simulationId);
            },
            {
                simulationId: simulationId,
                simulationType: SIREPO.APP_SCHEMA.simulationType,
            });
    };

    self.enumDescription = function(enumName, value) {
        var res = null;
        SIREPO.APP_SCHEMA.enum[enumName].forEach(function(v) {
            if (v[0] == value) {
                res = v[1];
            }
        });
        if (res === null) {
            throw 'no value for enum: ' + enumName + '.' + value;
        }
        return res;
    };

    // intermediate method to change from arrays to objects when defining model fields
    self.fieldProperties = function(modelName, fieldName) {
        // these won't exist for beamline elements
        // if(! self.models[modelName]) {
        //     throw modelName + ": no such model in simulation " + SIREPO.APP_SCHEMA.simulationType;
        // }

        var info = self.modelInfo(modelName, fieldName)[fieldName];
        if(! info) {
            throw fieldName + ": no such field in model " + modelName;
        }
        var infoNames = ['label', 'type', 'default', 'toolTip', 'min', 'max'];
        var p = {};
        info.forEach(function (v, i) {
            p[i] = v;
            p[infoNames[i]] = v;
        });
        return p;
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
            function(data) {
                if (data.errorRedirect) {
                    $window.location.href = data.errorRedirect;
                }
                else {
                    op(data);
                }
            },
            {
                simulationType: SIREPO.APP_SCHEMA.simulationType,
                search: search,
            });
    };

    self.loadModels = function(simulationId, callback, section) {
        if (self.isLoaded() && self.models.simulation.simulationId == simulationId) {
            return;
        }
        self.clearModels();
        var routeObj = {
            routeName: 'simulationData',
            '<simulation_id>': simulationId,
            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
            '<pretty>': false
        };
        if(section) {
            routeObj['<section>'] = section;
        }
        requestSender.sendRequest(
            routeObj,
            function(data) {
                if (data.redirect) {
                    requestSender.localRedirect('notFoundCopy', {
                        ':simulationIds': data.redirect.simulationId
                            + (data.redirect.userCopySimulationId
                               ? ('-' + data.redirect.userCopySimulationId)
                               : ''),
                        ':section': data.redirect.section,
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

    self.newSimulation = function(model, op, errOp) {
        var data = self.clone(model);
        data.simulationType = SIREPO.APP_SCHEMA.simulationType;
        requestSender.sendRequest('newSimulation', op, data, errOp);
    };

    self.optFieldName = function(modelName, fieldName, model) {
        var res = modelName;
        if (model && model.id) {
            res += '#' + model.id;
        }
        return res + '.' + fieldName;
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
                self.updateReports();
            }
            if (callback) {
                callback();
            }
        });
    };

    self.setModelDefaults = function(model, modelName) {
        // set model defaults from schema
        var schema = SIREPO.APP_SCHEMA.model[modelName];
        var fields = Object.keys(schema);
        for (var i = 0; i < fields.length; i++) {
            var f = fields[i];
            if (! model[f]) {
                if (schema[f][2] !== undefined) {
                    model[f] = schema[f][2];
                }
            }
        }
        return model;
    };

    self.ucfirst = function(s) {
        return s.charAt(0).toUpperCase() + s.slice(1);
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
            var id = template.replace('{}', index);
            if (values[id]) {
                index++;
            }
            else {
                return id;
            }
        }
    };

    self.updateReports = function() {
        broadcastClear();
        for (var key in self.models) {
            if (self.isReportModelName(key)) {
                broadcastChanged(key);
            }
        }
    };

    self.viewInfo = function(name) {
        return SIREPO.APP_SCHEMA.view[name] || SIREPO.APP_SCHEMA.common.view[name];
    };

    self.watchModelFields = function($scope, modelFields, callback) {
        $scope.appState = self;
        modelFields.forEach(function(f) {
            // elegant uses '-' in modelKey
            f = propertyToIndexForm(f);
            $scope.$watch('appState.models' + f, function (newValue, oldValue) {
                if (self.isLoaded() && newValue !== null && newValue !== undefined && newValue !== oldValue) {
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

SIREPO.app.factory('appDataService', function() {
    var self = {};

    self.applicationMode = 'default';
    self.isApplicationMode = function(name) {
        return name == self.getApplicationMode();
    };

    // override these methods in app's service
    self.getApplicationMode = function() {
        return self.applicationMode;
    };
    self.appDataForReset = function() {
        return null;
    };
    self.canCopy = function() {
        return true;
    };
    return self;
});

SIREPO.app.factory('notificationService', function(cookieService, $sce) {

    var self = {};

    self.notifications = {};

    self.addNotification = function(notification) {
        if(! notification.name || ! notification.content) {
            return;
        }
        self.notifications[notification.name] = notification;
    };

    self.dismiss = function(name) {
        if(name) {
            self.dismissNotification(self.getNotification(name));
        }
    };

    self.dismissNotification = function(notification) {
        if(notification) {
            self.sleepNotification(notification);
        }
    };

    self.getContent = function(name) {
        if(! name || ! self.getNotification(name)) {
            return '';
        }
        return self.getNotification(name).content;
    };

    self.getNotification = function(name) {
        return self.notifications[name];
    };

    self.removeNotification = function(notification) {
        delete self.notifications[notification.name];
        cookieService.removeCookie(cookieDef(notification));
    };

    self.shouldPresent = function(name) {
        var now = new Date();
        var notification = self.notifications[name];
        if(! notification || ! notification.active) {
            return false;
        }

        if (! cookieService.cleanExpiredCookie(cookieDef(notification))) {
            var vcd = SIREPO.APP_SCHEMA.cookies.firstVisit;
            var vc = cookieService.getCookie(vcd);
            var lstVisitDays = vc.t - cookieService.timeoutOrDefault(vcd);
            // we need millisecond comparison here
            return now.getTime() > (lstVisitDays + (notification.delay || 0)) * SIREPO.APP_SCHEMA.constants.oneDayMillis;
        }

        return false;
    };

    self.sleepNotification = function(notification) {
        cookieService.addCookie(cookieDef(notification), 'i');
        //TODO(pjm): this prevents Firefox from showing the notification right after it is dismissed
        notification.active = false;
    };

    function cookieDef(notification) {
        return SIREPO.APP_SCHEMA.cookies[notification.cookie];
    }

    return self;
});

// manages validators for ngModels and provides other validation services
SIREPO.app.service('validationService', function(utilities) {

    this.fieldValidators = {};
    this.enumValidators = {};

    this.setFieldValidator = function(name, validatorFn, messageFn) {
        if(! this.fieldValidators[name]) {
            this.fieldValidators[name] = {};
        }
        this.fieldValidators[name].vFunc = validatorFn;
        this.fieldValidators[name].vMsg = messageFn;
        return this.fieldValidators[name];
    };
    this.getFieldValidator = function(name) {
        return this.fieldValidators[name];
    };
    this.removeFieldValidator = function(name) {
        if(this.fieldValidators[name]) {
            delete this.fieldValidators[name];
        }
    };
    this.reloadValidatorForModel = function(name, modelValidatorName, ngModel) {
        var fv = this.getFieldValidator(name);
        if(! ngModel.$validators[modelValidatorName]) {
            if(fv) {
                ngModel.$validators[modelValidatorName] = fv.vFunc;
            }
        }
    };
    this.getMessageForModel = function(name, modelValidatorName, ngModel) {
        if(! ngModel.$validators[modelValidatorName]) {
            return '';
        }
        var fv = this.getFieldValidator(name);
        return fv ? (! ngModel.$valid ? fv.vMsg(ngModel.$viewValue) : '') : '';
    };

    // lazy creation of validator, plus special handling
    this.getEnumValidator = function(enumName) {

        var validator = this.getFieldValidator(enumName);
        if(validator) {
            return validator;
        }
        var enums = SIREPO.APP_SCHEMA.enum[enumName];
        if(! enums) {
            throw enumName + ':' + ' no such enum';
        }
        var isValid = function(name) {
            return enums.map(function (e) {
                return e[SIREPO.ENUM_INDEX_VALUE];
            }).indexOf('' + name) >= 0;
        };
        var err = function(name) {
            return name + ':' + ' no such value in ' + enumName;
        };
        validator = this.setFieldValidator(enumName, isValid, err);
        validator.find = function (name) {
            if(! validator.vFunc(name)) {
                throw validator.vMsg(name);
            }
            return name;
        };
        return validator;
    };

    this.validateFieldOfType = function(value, type) {
        if (value === undefined || value === null || value === '')  {
            // null files OK, at least sometimes
            if (type === 'MirrorFile') {
                return true;
            }
            return false;
        }
        if (type === 'Float' || type === 'Integer') {
            if (SIREPO.NUMBER_REGEXP.test(value)) {
                var v;
                if (type  === 'Integer') {
                    v = parseInt(value);
                    return v == value;
                }
                return isFinite(parseFloat(value));
            }
        }
        if (type === 'String') {
            return true;
        }
        if(SIREPO.APP_SCHEMA.enum[type]) {
            return this.getEnumValidator(type).vFunc(value);
        }
        // TODO(mvk): other types here, for now just accept everything
        return true;
    };

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
                },
                null,
                // error handling
                function(data) {
                    //TODO(pjm): need error wrapping on server similar to runStatus route
                    panelState.setError(modelName, 'Report not generated');
                });
        };
        if (isHidden) {
            panelState.addPendingRequest(modelName, requestFunction);
        }
        else {
            requestFunction();
        }
    };

    self.hasFrames = function(modelName) {
        if (modelName) {
            return self.getFrameCount(modelName) > 0;
        }
        return self.getFrameCount() > 0;
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

SIREPO.app.factory('authService', function(appState, authState, requestSender) {
    var self = {};

    function label(method) {
        if ('guest' == method) {
            return 'as Guest';
        }
        return 'with ' + appState.ucfirst(method);
    }

    self.methods = authState.visibleMethods.map(
        function (method) {
            return {
                'label': 'Sign in ' + label(method),
                'url': requestSender.formatUrlLocal(
                    'loginWith',
                    {':method': method}
                )
            };
        }
    );
    self.logoutUrl = requestSender.formatUrl(
        'authLogout',
        {'<simulation_type>': SIREPO.APP_SCHEMA.simulationType}
    );
    return self;
});

SIREPO.app.factory('panelState', function(appState, requestSender, simulationQueue, utilities, validationService, $compile, $rootScope, $timeout, $window) {
    // Tracks the data, error, hidden and loading values
    var self = {};
    var panels = {};
    var pendingRequests = {};
    var queueItems = {};
    var waitForUICallbacks = null;
    var windowResize = utilities.debounce(function() {
        $rootScope.$broadcast('sr-window-resize');
    }, 250);


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
        if(selector) {
            if (isShown) {
                selector.show();
            }
            else {
                selector.hide();
            }
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

    self.fileNameFromText = function(text, extension) {
        return text.replace(/(\_|\W|\s)+/g, '-') + '.' + extension;
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
            var progressText = SIREPO.APP_SCHEMA.constants.inProgressText ||
                (appState.models[name] || {}).inProgressText ||
                'Simulating';
            return progressText + ' ' + new Array(count % 3 + 2).join('.');
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

    self.pythonSource = function(simulationId, modelName, reportName) {
        var args = {
            '<simulation_id>': simulationId,
            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
        };
        if (modelName) {
            args['<model>'] = modelName;
        }
        if (reportName) {
            args['<report>'] = reportName;
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

    self.setFieldLabel = function(model, field, text) {
        $('.' + utilities.modelFieldID(model, field)  + ' .control-label label')
            .text(text);
    };

    self.showEnum = function(model, field, value, isShown) {
        var eType = SIREPO.APP_SCHEMA.enum[appState.modelInfo(model)[field][SIREPO.INFO_INDEX_TYPE]];
        var optionIndex = -1;
        eType.forEach(function(row, index) {
            if (row[0] == value) {
                optionIndex = index;
            }
        });
        if (optionIndex < 0) {
            throw 'no enum value found for ' + model + '.' + field + ' = ' + value;
        }
        var opt = $(fieldClass(model, field)).find('option')[optionIndex];
        if (! opt) {
            // handle case where enum is displayed as a button group rather than a select
            opt = $(fieldClass(model, field)).find('button')[optionIndex];
        }
        showValue($(opt), isShown);
        // this is required for MSIE 11 and Safari which can't hide select options
        if (isShown) {
            $(opt).removeAttr('disabled');
        }
        else {
            $(opt).attr('disabled', 'disabled');
        }
    };

    self.showField = function(model, field, isShown) {
        //TODO(pjm): remove jquery and use attributes on the fieldEditor directive
        // try show/hide immediately, followed by timeout if UI hasn't finished layout yet
        showValue($(fieldClass(model, field)).closest('.form-group'), isShown);
        self.waitForUI(function() {  //MR: fix for https://github.com/radiasoft/sirepo/issues/730
            showValue($(fieldClass(model, field)).closest('.form-group'), isShown);
        });
    };

    //TODO(pjm): should be renamed, showColumnEditor()
    self.showRow = function(model, field, isShown) {
        //TODO(pjm): remove jquery and use attributes on the fieldEditor directive
        showValue($(fieldClass(model, field)).closest('.sr-column-editor').parent(), isShown);
        self.waitForUI(function() {  //MR: fix for https://github.com/radiasoft/sirepo/issues/730
            showValue($(fieldClass(model, field)).closest('.sr-column-editor').parent(), isShown);
        });
    };

    self.showTab = function(model, pageNumber, isShown) {
        showValue($('.' + model + '-page-' + pageNumber), isShown);
    };

    self.showModalEditor = function(modelKey, template, scope) {
        var editorId = '#' + self.modalId(modelKey);
        var showEvent = modelKey + '.editor.show';
        if ($(editorId).length) {
            $(editorId).modal('show');
            $rootScope.$broadcast(showEvent);
        }
        else {
            if (! template) {
                var name = modelKey.toLowerCase().replace('_', '');
                template = '<div data-modal-editor="" data-view-name="' + modelKey + '" data-sr-' + name + '-editor=""' + '></div>';
            }
            $('body').append($compile(template)(scope || $rootScope));
            //TODO(pjm): timeout hack, other jquery can't find the element
            self.waitForUI(function() {
                $(editorId).modal('show');
                $rootScope.$broadcast(showEvent);
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
        }
        else {
            state.panelState.hidden.push(name);
            if (queueItems[name]) {
                simulationQueue.cancelItem(queueItems[name]);
                delete queueItems[name];
            }
        }
        // needed to resize a hidden report and other panels
        if (appState.isReportModelName(name)) {
            windowResize();
        }
    };

    self.waitForUI = function(callback) {
        // groups callbacks within one $timeout()
        if (waitForUICallbacks) {
            waitForUICallbacks.push(callback);
        }
        else {
            waitForUICallbacks = [callback];
            $timeout(function() {
                // new callbacks may be added during this cycle
                var callbacks = waitForUICallbacks;
                waitForUICallbacks = null;
                callbacks.forEach(function(callback) {
                    callback();
                });
            });
        }
    };

    $($window).resize(windowResize);

    return self;
});

SIREPO.app.factory('requestSender', function(cookieService, errorService, localRoutes, $http, $location, $interval, $q, $rootScope) {
    var self = {};
    var getApplicationDataTimeout = {};
    var IS_HTML_ERROR_RE = new RegExp('^(?:<html|<!doctype)', 'i');
    var HTML_TITLE_RE = new RegExp('>([^<]+)</', 'i');

    function checkCookieRedirect(event, route) {
        if (! SIREPO.authState.displayName || route.controller.indexOf('login') >= 0) {
            return;
        }
        var prevRoute = cookieService.getCookieValue(SIREPO.APP_SCHEMA.cookies.previousRoute);
        if (prevRoute) {
            cookieService.removeCookie(SIREPO.APP_SCHEMA.cookies.previousRoute);
            var parts = prevRoute.split(' ');
            if (parts[0] == SIREPO.APP_SCHEMA.simulationType) {
                event.preventDefault();
                $location.path(parts[1]);
            }
        }
    }

    function logError(data, status) {
        var err = SIREPO.APP_SCHEMA.customErrors[status];
        if (err && err.route) {
            self.localRedirect(err.route);
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

    function saveCookieRedirect(route) {
        var v = SIREPO.APP_SCHEMA.simulationType + ' ' + route;
        cookieService.addCookie(SIREPO.APP_SCHEMA.cookies.previousRoute, v);
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
            if (v === '') {
                throw param + ': may not be empty string';
            }
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

    self.defaultRouteName = function() {
        return SIREPO.APP_SCHEMA.appModes.default.localRoute;
    };

    self.formatUrlLocal = function(routeName, params, app) {
        var u = '#' + formatUrl(localRoutes, routeName, params);
        return app ? '/' + app + u : u;
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
                if (! self[name]) {
                    // if loading fails, use an empty list to prevent load requests on each digest cycle, see #1339
                    self[name] = [];
                }
            });
    };

    self.handleSRException = function(data) {
        var srException = data.srException;
        if (srException.routeName == 'login') {
            // save return route after login on client
            var prevRoute = $location.url();
            if (prevRoute != '/' + srException.routeName) {
                saveCookieRedirect(prevRoute);
            }
        }
        self.localRedirect(srException.routeName, srException.params);
        return;
    };

    self.localRedirect = function(routeName, params) {
        var r = self.formatUrlLocal(routeName, params);
        $location.path(r.slice(1));
    };

    self.localRedirectHome = function(simulationId) {
        self.localRedirect(self.defaultRouteName(), {
            ':simulationId': simulationId,
        });
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
        //srdbg('req url/data', url, data);
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
            if (angular.isString(data) && IS_HTML_ERROR_RE.exec(data)) {
                var m = HTML_TITLE_RE.exec(data);
                if (m) {
                    srlog(m[1], ': error response from server');
                    data = {error: m[1]};
                }
            }
            if ($.isEmptyObject(data)) {
                data = {};
            }
            else if (! angular.isObject(data)) {
                errorService.logToServer(
                    'serverResponseError', data, 'unexpected response type or empty');
                data = {};
            }
            if (! data.state) {
                data.state = 'error';
            }
            if (data.state == 'srException') {
                self.handleSRException(data);
                return;
            }
            if (status == -1) {
                msg = 'Server unavailable';
            }
            else if (SIREPO.APP_SCHEMA.customErrors[status]) {
                msg = SIREPO.APP_SCHEMA.customErrors[status].msg;
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
                if (angular.isObject(data)) {
                    successCallback(data, response.status);
                }
                else {
                    thisErrorCallback(data, response.status);
                }
            },
            thisErrorCallback);
    };

    $rootScope.$on('$routeChangeStart', checkCookieRedirect);

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

    function cancelItems(mode) {
        var rq = runQueue;
        runQueue = [];
        rq.forEach(function(item) {
            if (! mode || item.qMode == mode) {
                self.removeItem(item);
            }
            else {
                runQueue.push(item);
            }
        });
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

        var process = function(resp) {
            if (qi.qState == 'removing') {
                return;
            }
            if (! (resp.state == 'running' || resp.state == 'pending')) {
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
        cancelItems();
    };

    // TODO(mvk): handle possible queue state conflicts
    self.cancelItem = function (qi, successCallback, errorCallback) {
        if (! qi) {
            return false;
        }
        qi.qMode = 'transient';
        var isProcessingTransient = qi.qState == 'processing' && ! qi.persistent;
        if (qi.qState == 'processing') {
            requestSender.sendRequest('runCancel', successCallback, qi.request, errorCallback);
            qi.qState = 'canceled';
        }
        self.removeItem(qi);
        if (isProcessingTransient) {
            runFirstTransientItem();
        }
        return true;
    };

    self.cancelTransientItems = function() {
        cancelItems('transient');
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
    $rootScope.$on('clearCache', self.cancelTransientItems);

    return self;
});

SIREPO.app.factory('requestQueue', function($rootScope, requestSender) {
    var self = {};
    var queueMap = {};
    self.currentQI = null;

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
        self.currentQI = qi;
        if ( qi.requestSent ) {
            return;
        }
        qi.requestSent = true;
        qi.params = qi.paramsCallback();
        var process = function(ok, resp, status) {
            self.currentQI = null;
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
        self.currentQI = null;
    };

    self.addItem = function(queueName, paramsCallback) {
        getQueue(queueName).push({
            requestSent: false,
            paramsCallback: paramsCallback
        });
        sendNextItem(queueName);
    };
    self.getCurrentQI = function(queueName) {
        return self.currentQI;
    };
    return self;
});


SIREPO.app.factory('persistentSimulation', function(simulationQueue, appState, frameCache) {
    var self = {};

    self.initSimulationState = function($scope, model, handleStatusCallback, animationArgs) {
        var state = {
            dots: '.',
            isReadyForModelChanges: false,
            model: model,
            percentComplete: 0,
            simulationQueueItem: null,
            timeData: {
                elapsedDays: null,
                elapsedTime: null,
            },
        };

        function clearSimulation() {
            simulationQueue.removeItem(state.simulationQueueItem);
            state.simulationQueueItem = null;
        }

        function handleStatus(data) {
            setSimulationStatus(data);
            if (data.elapsedTime) {
                state.timeData.elapsedDays = parseInt(data.elapsedTime / (60 * 60 * 24));
                state.timeData.elapsedTime = new Date(1970, 0, 1);
                state.timeData.elapsedTime.setSeconds(data.elapsedTime);
            }
            if (data.percentComplete) {
                state.percentComplete = data.percentComplete;
            }
            if (state.isProcessing()) {
                state.dots += '.';
                if (state.dots.length > 3) {
                    state.dots = '.';
                }
            }
            else {
                state.simulationQueueItem = null;
            }
            handleStatusCallback(data);
        }

        function runStatus() {
            state.isReadyForModelChanges = true;
            state.simulationQueueItem = simulationQueue.addPersistentStatusItem(
                state.model,
                appState.models,
                handleStatus
            );
        }

        function setSimulationStatus(data) {
            if (!appState.models.simulationStatus) {
                appState.models.simulationStatus = {};
            }
            data.report = state.model;
            appState.models.simulationStatus[state.model] = data;
            if (appState.isLoaded()) {
                // simulationStatus is not saved to server from client
                appState.saveQuietly('simulationStatus');
            }
        }

        function simulationStatus() {
            if (appState.models.simulationStatus && appState.models.simulationStatus[state.model]) {
                return appState.models.simulationStatus[state.model];
            }
            return {state: 'pending'};
        }

        state.cancelSimulation = function(callback) {
            setSimulationStatus({state: 'canceled'});
            var queueHadItem = simulationQueue.cancelItem(state.simulationQueueItem, callback, callback);
            state.simulationQueueItem = null;
            if (! queueHadItem && callback) {
                callback();
            }
        };

        state.getError = function() {
            return simulationStatus().error;
        };

        state.getFrameCount = function() {
            return frameCache.getFrameCount();
        };

        state.getPercentComplete = function() {
            if (state.isInitializing() || state.isStatePending()) {
                return 100;
            }
            return state.percentComplete;
        };

        state.hasFrames = function() {
            return state.getFrameCount() > 0;
        };

        state.hasTimeData = function () {
            return state.timeData && state.timeData.elapsedTime;
        };

        state.isInitializing = function() {
            if (state.isStateRunning()) {
                return frameCache.getFrameCount() < 1;
            }
            return false;
        };

        state.isProcessing = function() {
            return state.isStatePending() || state.isStateRunning();
        };

        state.isStateCanceled = function() {
            return simulationStatus().state == 'canceled';
        };

        state.isStateError = function() {
            return simulationStatus().state == 'error';
        };

        state.isStatePending = function() {
            return simulationStatus().state == 'pending';
        };

        state.isStateRunning = function() {
            return simulationStatus().state == 'running';
        };

        state.isStopped = function() {
            return ! state.isProcessing();
        };

        state.runSimulation = function() {
            if (state.isStateRunning()) {
                return;
            }
            //TODO(robnagler) should be part of simulationStatus
            frameCache.setFrameCount(0);
            state.timeData.elapsedTime = null;
            state.timeData.elapsedDays = null;
            setSimulationStatus({state: 'pending'});
            state.simulationQueueItem = simulationQueue.addPersistentItem(
                state.model,
                appState.applicationState(),
                handleStatus
            );
        };

        state.saveAndRunSimulation = function(models) {
            if (state.isProcessing()) {
                return;
            }
            simulationStatus().state = 'pending';
            appState.saveChanges(models, state.runSimulation);
        };

        state.stateAsText = function() {
            if (state.isStateError()) {
                var e = state.getError();
                if (e) {
                    return 'Error: ' + e.split(/[\n\r]+/)[0];
                }
            }
            return appState.ucfirst(simulationStatus().state);
        };

        frameCache.setAnimationArgs(animationArgs);
        setSimulationStatus({state: 'stopped'});
        frameCache.setFrameCount(0);
        $scope.$on('$destroy', clearSimulation);
        appState.whenModelsLoaded($scope, runStatus);

        return state;
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

SIREPO.app.factory('fileManager', function(requestSender) {
    var COMPOUND_PATH_SEPARATOR = ':';
    var self = {};

    var activeFolderPath = null;

    var activeFolder = null;
    self.fileTree = [
        {
            name: '/',
            isFolder: true,
            children: [],
        },
    ];
    var flatTree = [];
    var simList = [];
    var fList = [];

    function compoundPathToPath(compoundPath) {
        var p = compoundPath.replace(new RegExp(COMPOUND_PATH_SEPARATOR, 'g'), '\/');
        return p === '' ? '/' : p;
    }

    function pathToCompoundPath(path) {
        return path.replace(/^\//,'').replace(/\//g, COMPOUND_PATH_SEPARATOR);
    }


    self.decodePath = function(path) {
        return compoundPathToPath(decodeURIComponent(path));
    };

    self.pathName = function(folder) {
        if (folder == self.rootFolder()) {
            return '/';
        }
        var path = '/' + folder.name;
        while (folder.parent != self.rootFolder()) {
            folder = folder.parent;
            path = '/' + folder.name + path;
        }
        return path;
    };
    self.getFolderWithPath = function(pathName) {
        if(pathName === '/') {
            return self.rootFolder();
        }
        var pathArr = pathName.split('/').filter(function (value) {
            return value !== "";
        });
        var folder = self.rootFolder();
        for(var pIndex = 0; pIndex < pathArr.length; ++pIndex) {
            var child = null;
            for(var cIndex = 0; cIndex < folder.children.length; ++cIndex) {
                child = folder.children[cIndex];
                if(child.isFolder && child.name === pathArr[pIndex]) {
                    break;
                }
            }
            if(child == null) {
                return null;
            }
            if(pIndex == pathArr.length - 1) {
                return child;
            }
            folder = child;
        }
        return null;
    };

    self.nextNameInFolder = function(baseName, folderPath) {
        var folder = self.getFolderWithPath(folderPath);
        var names = {};
        var hasName = false;
        folder.children.forEach(function (c) {
            names[c.name] = true;
            hasName = hasName || c.name === baseName;
        });
        if(! hasName) {
            return baseName;
        }
        var count = 2;
        var name = baseName;
        name = name.replace(/\s+\d+$/, '');
        while (names[name + ' ' + count]) {
            count++;
        }
        return  name + ' ' + count;
    };

    self.rootFolder = function() {
        return self.fileTree[0];
    };

    self.getActiveFolderPath = function() {
        return activeFolderPath;
    };

    self.setActiveFolderPath = function(path) {
        activeFolderPath = path;
    };

    self.getActiveFolder = function() {
        return activeFolder;
    };

    self.setActiveFolder = function(item) {
        activeFolder = item;
    };

    // consider a folder an example if any of the simulations under it is
    self.isFolderExample = function (item) {
        if(! item || ! item.isFolder) {
            return false;
        }
        // root folder contains everything so exclude it
        if(item.name === '/') {
            return false;
        }
        for(var cIndex = 0; cIndex < item.children.length; ++ cIndex) {
            var child = item.children[cIndex];
            if(! child.isFolder) {
                if (child.isExample) {
                    return true;
                }
            }
            else {
                if(self.isFolderExample(child)) {
                    return true;
                }
            }
        }
        return false;
    };
    self.isActiveFolderExample = function () {
        return self.isFolderExample(self.getActiveFolder());
    };
    self.isItemExample = function(item) {
        if(! item.isFolder) {
            return item.isExample;
        }
        return self.isFolderExample(item);
    };
    self.getUserFolders = function(excludeFolder) {
        return self.flattenTree().filter(function(item) {
            if (item != excludeFolder && item.isFolder) {
                if (SIREPO.INCLUDE_EXAMPLE_FOLDERS || ! self.isFolderExample(item)) {
                    return true;
                }
            }
            return false;
        });
    };
    self.getUserFolderPaths = function() {
        return self.getUserFolders().map(function (item) {
            return self.pathName(item);
        }).sort(function(a, b) {
            return a.localeCompare(b);
        });
    };
    self.defaultCreationFolder = function() {
        var cf = self.getUserFolderPaths().indexOf(self.getActiveFolderPath()) >= 0 ? self.getActiveFolder() : self.rootFolder();
        return cf;
    };
    self.defaultCreationFolderPath = function() {
        return self.pathName(self.defaultCreationFolder());
    };

    function findSimInTree(simId) {
        var sim = flatTree.filter(function (item) {
            return item.simulationId === simId;
        });
        if(sim && sim.length > 0) {
            return sim[0];
        }
        return null;
    }
    self.updateTreeFromFileList = function(data) {
        for(var i = 0; i < data.length; i++) {
            var item = findSimInTree(data[i].simulationId);
            if (item) {
                item.name = data[i].name;
            }
            else {
                self.addToTree(data[i]);
            }
        }
        var listItemIds = data.map(function(item) {
            return item.simulationId;
        });
        var orphanItemIds = simList.filter(function(item) {
            return listItemIds.indexOf(item) < 0;
        });
        for(var j = 0; j < orphanItemIds.length; ++j) {
            self.removeFromTree(findSimInTree(orphanItemIds[j]));
        }
    };
    self.addToTree = function(item) {
        var newItem;
        if(item.isFolder) {
            var parent = item.parent ? item.parent : self.rootFolder();
            parent.children.push(item);
            newItem = item;
        }
        else {
            var path = item.folder == '/'
                ? []
                : item.folder.slice(1).split('/');
            var currentFolder = self.rootFolder();

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

            newItem = {
                parent: currentFolder,
                name: item.name,
                simulationId: item.simulationId,
                lastModified: item.last_modified,
                isExample: item.isExample,
            };
            currentFolder.children.push(newItem);
        }
        self.updateFlatTree();
        return newItem;
    };
    self.folderList = function(excludeFolder) {
        return fList.filter(function (f) {
           return f != excludeFolder;
        });
    };

    self.getFileTree = function () {
        return self.fileTree;
    };

    self.getSimList = function () {
        return simList;
    };
    function getSimListFromTree() {
        return flatTree.filter(function(item) {
            return ! item.isFolder;
        }).map(function(item) {
            return item.simulationId;
        });
    }
    function getFolderListFromTree() {
        return flatTree.filter(function(item) {
           return item.isFolder;
        });
    }

    self.flattenTree = function(tree) {
        var items = [];
        if(! tree) {
            tree = self.fileTree;
            items.push(self.rootFolder());
        }
        for(var i = 0; i < tree.length; ++i) {
            var treeFolders = tree[i].children.filter(function(item) {
                return item.isFolder;
            });
            items = items.concat(tree[i].children);
            items = items.concat(self.flattenTree(treeFolders));
        }
        return items;
    };
    self.updateFlatTree = function() {
        flatTree = self.flattenTree();
        simList = getSimListFromTree();
        fList = getFolderListFromTree();
    };

    self.removeSimFromTree = function(simId) {
        self.removeFromTree(findSimInTree(simId));
    };
    self.removeFromTree = function(item) {
        if(item) {
            var parent = item.parent;
            parent.children.splice(parent.children.indexOf(item), 1);
            self.updateFlatTree();
        }
    };
    self.doesFolderContainFolder = function(f1, f2) {
        if(f2 == self.rootFolder() || ! f1.children) {
            return false;
        }
        if(f1 == self.rootFolder() || f1.children.indexOf(f2) >= 0) {
            return true;
        }
        for(var cIndex = 0; cIndex < f1.children.length; ++cIndex) {
            if(self.doesFolderContainFolder(f1.children[cIndex], f2)) {
                return true;
            }
        }
        return false;
    };

    self.redirectToPath = function(path) {
        var compoundPath = pathToCompoundPath(path);
        if (compoundPath === '') {
            requestSender.localRedirect('simulations');
        }
        else {
            requestSender.localRedirect(
                'simulationsFolder',
                {
                    ':folderPath?': compoundPath,
                }
            );
        }
    };

    return self;
});

SIREPO.app.controller('NavController', function (activeSection, appState, fileManager, requestSender, $scope, $window, $route) {

    var self = this;

    function openSection(name) {
        requestSender.localRedirect(name, sectionParams(name));
    }

    function sectionParams(name) {
        if (name === 'simulationsFolder') {
            return {
                ':folderPath?': ''
            };
        }
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
            var path = appState.models.simulation.folder;
            appState.autoSave(function() {
                // return to the simulation's folder
                fileManager.redirectToPath(path);
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
                'RadiaSoft',
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
        return requestSender.formatUrlLocal(name, sectionParams(name));
    };

    self.getLocation = function() {
        return $window.location.href;
    };

    $scope.$on('$locationChangeStart', function () {
        // changing the search triggers a location change, but if we don't want to
        // reload the entire page, do not show the page loader
        var showPageLoader = true;
        if($route.current) {
            showPageLoader = $route.current.reloadOnSearch;
        }
        SIREPO.setPageLoaderVisible(showPageLoader);
    });
    $scope.$on('$viewContentLoaded', function () {
        SIREPO.setPageLoaderVisible(false);
    });


});

SIREPO.app.controller('NotFoundCopyController', function (requestSender, $route) {
    var self = this;
    var ids = $route.current.params.simulationIds.split('-');
    self.simulationId = ids[0];
    self.userCopySimulationId = ids[1];

    function localRedirect(simId) {
        requestSender.localRedirect(
            $route.current.params.section || requestSender.defaultRouteName(),
            {
                ':simulationId': simId,
            });
    }

    self.cancelButton = function() {
        requestSender.localRedirect('simulations');
    };

    self.copyButton = function() {
        requestSender.sendRequest(
            'copyNonSessionSimulation',
            function(data) {
                localRedirect(data.models.simulation.simulationId);
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
        localRedirect(self.userCopySimulationId);
    };
});

SIREPO.app.controller('LoginController', function (authService) {
    var self = this;
    self.authService = authService;
});

SIREPO.app.controller('LoginWithController', function ($route, $window, errorService, appState, requestSender) {
    var self = this;
    var m = $route.current.params.method || '';
    self.method = m;
    if (m == 'guest' || m == 'github') {
        self.msg = 'Logging in via ' + m + '. Please wait...';
        $window.location.href = requestSender.formatUrl(
            'auth' + appState.ucfirst(m) + 'Login',
            {'<simulation_type>': SIREPO.APP_SCHEMA.simulationType}
        );
        return;
    }
    else if (m == 'email') {
        // handled by the emailLogin directive
    }
    else {
        self.msg = '';
        errorService.alertText('Incorrect or invalid login method: ' + (m || '<none>'));
        requestSender.localRedirect('login');
    }
});

SIREPO.app.controller('LoginFailController', function (appState, requestSender, $route, $sce) {
    var self = this;
    var t = $sce.getTrustedHtml(appState.ucfirst($route.current.params.method || ''));
    var r = $route.current.params.reason || '';
    var l = '<a href="' + requestSender.formatUrlLocal('login')
        + '">Please try to login again.</a>';
    if (r == 'deprecated' || r == 'invalid-method') {
        self.msg = 'You can no longer login with ' + t + '. ' + l;
    }
    else if (r == 'email-token') {
        self.msg = 'You clicked on an expired link. ' + l;
    }
    else if (r == 'oauth-state') {
        self.msg = 'Something went wrong with ' + t + '. ' + l;
    }
    else {
        self.msg = 'Unexpected error. ' + l;
    }
});

SIREPO.app.controller('SimulationsController', function (appState, cookieService, errorService, fileManager, notificationService, panelState, requestSender, $location, $rootScope, $sce, $scope, $window) {
    var self = this;

    $rootScope.$broadcast('simulationUnloaded');
    var n = appState.clone(SIREPO.APP_SCHEMA.notifications.getStarted);
    n.content = [
        '<div class="text-center"><strong>Welcome to Sirepo - ',
        $sce.getTrustedHtml(SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_SCHEMA.simulationType].longName),
        '!</strong></div>',
        'Below are some example simulations and folders containing simulations. Click on the simulation to open and view simulation results. You can create a new simulation by selecting the New Simulation link above.',
    ].join('');
    notificationService.addNotification(n);

    self.importText = SIREPO.appImportText;
    self.fileTree = fileManager.getFileTree();
    var SORT_DESCENDING = '-';
    self.activeFolder = fileManager.getActiveFolder();
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
    self.selectedItem = null;
    self.sortField = 'name';
    self.isWaitingForSim = false;

    self.fileManager = fileManager;

    function clearModels() {
        appState.clearModels(appState.clone(SIREPO.appDefaultSimulationValues));
    }

    function loadList() {
        self.isWaitingForList = ! fileManager.getSimList().length;
        appState.listSimulations(
            $location.search(),
            function(data) {
                if (! $scope.$parent) {
                    // callback may occur after scope has been destroyed
                    // if the user has navigated off the simulations page
                    return;
                }
                self.isWaitingForList = false;
                data.sort(function(a, b) {
                    return a.last_modified.localeCompare(b.last_modified);
                });
                fileManager.updateTreeFromFileList(data);
                checkURLForFolder();
            });
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
        return fileManager.rootFolder();
    }

    function setActiveFolder(item) {
        var prevPath = self.pathName(self.activeFolder || item);
        self.activeFolder = item;
        self.activeFolderPath = [];
        while (item) {
            self.activeFolderPath.unshift(item);
            item = item.parent;
        }
        fileManager.setActiveFolderPath(self.pathName(self.activeFolder));
        fileManager.setActiveFolder(self.activeFolder);
        if (prevPath === self.pathName(self.activeFolder)) {
            return;
        }
        fileManager.redirectToPath(self.pathName(self.activeFolder));
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

    function updateSelectedItem(op, errorCallback) {
        appState.loadModels(
            self.selectedItem.simulationId,
            function() {
                op();
                appState.saveQuietly('simulation');
                appState.autoSave(clearModels, errorCallback);
                self.selectedItem = null;
            });
    }

    self.canDelete = function(item) {
        if (item.isFolder) {
            return item.children.length === 0;
        }
        return ! item.isExample;
    };

    self.copyCfg = {
        copyName: '',
        copyFolder: '/',
        isExample: false,
        completion: function(data) {
            self.openItem(data.models.simulation);
            },
    };

    self.copyItem = function(item) {
        self.selectedItem = item;
        self.copyCfg.copyName = fileManager.nextNameInFolder(item.name, self.pathName(self.activeFolder));
        self.copyCfg.copyFolder = fileManager.defaultCreationFolderPath();
        $('#sr-copy-confirmation').modal('show');
    };

    self.deleteItem = function(item) {
        if (item.isFolder) {
            fileManager.removeFromTree(item);
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
                fileManager.removeFromTree(self.selectedItem);
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
        self.moveFolderList =  fileManager.getUserFolders(item);
        if(item.isFolder) {
            self.moveFolderList = self.moveFolderList.filter(function (userFolder) {
                return ! fileManager.doesFolderContainFolder(item, userFolder);
            });
        }
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
            requestSender.localRedirectHome(item.simulationId);
        }
    };

    self.pathName = function(folder) {
        return fileManager.pathName(folder);
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
        self.itemToUpdate = item;
        self.renameName = item.name;
        self.originalName = item.name;
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
            }, function (resp) {
                self.itemToUpdate.name = self.originalName;
                errorService.alertText('Invalid Name: \'' + self.renameName + '\' already in use');
            });
        }
    };

    self.selectedItemType = function() {
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
        cookieService.addCookie(SIREPO.APP_SCHEMA.cookies.listView, self.isIconView);
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

    var lv = cookieService.getCookieValue(SIREPO.APP_SCHEMA.cookies.listView);
    self.isIconView = (lv == null ? true : lv);
    clearModels();
    $scope.$on('simulation.changed', function() {
        self.isWaitingForSim = true;
        self.newSimName = appState.models.simulation.name;
        appState.newSimulation(
            appState.models.simulation,
            function(data) {
                self.isWaitingForSim = false;
                self.newSimName = '';
                fileManager.addToTree(data.models.simulation);
                self.openItem(data.models.simulation);
            });
    });
    $scope.$on('simFolder.changed', function() {
        var name = appState.models.simFolder.name;
        name = name.replace(/[\/]/g, '');
        fileManager.addToTree({
            name: name,
            parent: fileManager.getFolderWithPath(appState.models.simFolder.parent) || self.activeFolder,
            isFolder: true,
            children: [],
        });
        appState.models.simFolder.name = '';
        appState.saveQuietly('simFolder');
    });
    loadList();

    // invoked in loadList() callback
    function checkURLForFolder() {
        //TODO(pjm): need a generalized way to get path
        var canonicalPath = fileManager.decodePath($location.path().replace('/simulations', ''));
        if (canonicalPath === fileManager.getActiveFolderPath()) {
            return;
        }
        var newFolder = folderForPathInList(canonicalPath, [rootFolder()]);
        if (newFolder) {
            fileManager.setActiveFolderPath(canonicalPath);
            fileManager.setActiveFolder(newFolder);
            self.openItem(newFolder);
        }
        else {
            requestSender.localRedirect('notFound');
        }
    }
    function folderForPathInList (folderPath, folderList) {
        for (var i = 0; i < folderList.length; ++i) {
            var item = folderList[i];
            if (! item.isFolder) {
                continue;
            }
            var lPath = self.pathName(item);
            if (lPath === folderPath) {
                return item;
            }
            var childFolder = folderForPathInList(folderPath, item.children);
            if (childFolder) {
                return childFolder;
            }
        }
        return null;
    }

});

SIREPO.app.filter('simulationName', function() {
    return function(name) {
        if (name) {
            // clean up name so it formats well in HTML
            name = name.replace(/\_/g, ' ');
            name = name.replace(/([a-z])([A-Z])/g, '$1 $2');
        }
        return name;
    };
});

// Handles cookies stored in a single string, based on a definition in the schema.
// Public functions expect definitions in the format
//
//  {
//      <name: <string>>,
//      <value: <json type>>,
//      [valType: [string, see getCookieValue()],
//      [timeout: [cookie lifetime in days]]
//  }
//
// The client cookie then has the format
//  <name 1>:v=<value 1>;t=<timeout 1>;|...
SIREPO.app.factory('cookieService', function($cookies) {

    var svc = {};

    var oneDayMillis = SIREPO.APP_SCHEMA.constants.oneDayMillis;

    var cdelim = '|';
    var nDelim = ':';
    var pDelim = ';';
    var kvDelim = '=';

    var fiveYearsDays = 5*365;
    var fiveYearsMillis = fiveYearsDays * oneDayMillis;

    // used to delete the old cookies
    var cookieMap = {
        'net.sirepo.first_visit': SIREPO.APP_SCHEMA.cookies.firstVisit,
        'net.sirepo.get_started_notify': SIREPO.APP_SCHEMA.cookies.getStarted,
        'net.sirepo.sim_list_view': SIREPO.APP_SCHEMA.cookies.listView,
    };

    svc.addCookie = function (cookieDef, value) {
        add(cookieDef.name, value || cookieDef.value, svc.timeoutOrDefault(cookieDef));
    };

    svc.cleanExpiredCookie = function (cookieDef) {
        var cobj = get(cookieDef.name);
        if (cobj && cobj.t && parseInt(cobj.t) < new Date().getTime() / oneDayMillis) {
            remove(name);
            return null;
        }
        return cobj;
    };

    svc.getCookie = function (cookieDef) {
        return get(cookieDef.name);
    };

    svc.getCookieValue = function (cookieDef) {
        var cobj = svc.getCookie(cookieDef);
        if (! cobj) {
            return null;
        }
        var val = cobj.v;
        if (cookieDef.valType && cookieDef.valType.toLowerCase() === 'b') {
            return val.toLowerCase() === 'true';
        }
        if (cookieDef.valType && cookieDef.valType.toLowerCase() === 'n') {
            return parseFloat(val);
        }
        return val;
    };

    svc.removeCookie = function (cookieDef) {
        remove(cookieDef.name);
    };

    svc.timeoutOrDefault = function (cookieDef) {
        return cookieDef.timeout || fiveYearsDays;
    };

    // to reduce the string size, and because that's usually as accurate as we need,
    // timeout is in days
    function add(name, value, timeoutDays) {
        var allDelim = cdelim + nDelim + pDelim + kvDelim;
        var delimRE = new RegExp('[' + allDelim + ']+');
        if(delimRE.test(name) || delimRE.test(value) ) {
            throw name + ': Cookie name/value cannot contain delimiters ' + allDelim;
        }
        var cobj = readSRCookie();
        if(! cobj[name]) {
            cobj[name] = {};
        }
        cobj[name].t = Math.floor((new Date().getTime() / oneDayMillis)) + parseInt(timeoutDays) || 0;
        cobj[name].v = value;
        writeSRCookie(cobj);
    }

    function checkFirstVisit() {
        if (! svc.cleanExpiredCookie(SIREPO.APP_SCHEMA.cookies.firstVisit)) {
            svc.addCookie(SIREPO.APP_SCHEMA.cookies.firstVisit);
        }
    }

    function fixupOldCookies() {
        for(var cname in cookieMap) {
            var c = $cookies.get(cname);
            if(angular.isDefined(c)) {
                svc.addCookie(cookieMap[cname]);
                $cookies.remove(cname);
            }
        }
    }

    function get(name) {
        return readSRCookie()[name];
    }

    function pack(cobj) {
        var cstr = '';
        for(var name in cobj) {
            cstr = cstr + name + nDelim;
            for(var k in cobj[name]) {
                cstr = cstr + k + kvDelim + cobj[name][k] + pDelim;
            }
            cstr = cstr + cdelim;
        }
        return cstr;
    }

    function parse(cstr) {
        var cobj = {};
        var cookies = (cstr || '').split(cdelim);
        cookies.forEach(function (c) {
            var nameVals = c.split(nDelim);
            if(nameVals && nameVals[0]) {
                cobj[nameVals[0]] = {};
                nameVals[1].split(pDelim).forEach(function (kvs) {
                    if(kvs && kvs !== '') {
                        var kv = kvs.split(kvDelim);
                        cobj[nameVals[0]][kv[0]] = kv[1];
                    }
                });
            }
        });
        return cobj;
    }

    function readSRCookie() {
        return parse($cookies.get(SIREPO.APP_SCHEMA.constants.clientCookie));
    }

    function remove(name) {
        var cobj = readSRCookie();
        if(cobj && cobj[name]) {
            delete cobj[name];
            writeSRCookie(cobj);
        }
    }

    function writeSRCookie(cobj) {
        $cookies.put(SIREPO.APP_SCHEMA.constants.clientCookie,
            pack(cobj),
            {expires: new Date(new Date().getTime() + fiveYearsMillis)}
        );
    }

    fixupOldCookies();
    checkFirstVisit();

    return svc;
});
