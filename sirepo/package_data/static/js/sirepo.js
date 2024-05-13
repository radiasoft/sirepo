'use strict';
SIREPO.srlog = console.log.bind(console);
SIREPO.srdbg = console.log.bind(console);
SIREPO.traceWS = false;

// No timeout for now (https://github.com/radiasoft/sirepo/issues/317)
SIREPO.http_timeout = 0;
SIREPO.debounce_timeout = 350;
SIREPO.nonDataFileFrame = -1;
// Temporary until fix: https://github.com/radiasoft/sirepo/issues/6388
SIREPO.nonSimulationId = 'NONSIMID';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.beamlineItemLogic = function(name, init) {
    SIREPO.app.directive(name, function(beamlineService, utilities) {

        function watchFields(scope, fieldInfo, filterOldUndefined) {
            for (var idx = 0; idx < fieldInfo.length; idx += 2) {
                var fields = fieldInfo[idx];
                var callback = utilities.debounce(fieldInfo[idx + 1], SIREPO.debounce_timeout);
                beamlineService.watchBeamlineField(
                    scope, scope.modelName, fields, callback, filterOldUndefined);
            }
        }

        function whenItemSelected($scope, itemType, callback) {
            // parent's scope is used for cases where directive is a child of the editor
            $scope.$parent.$on('sr-tabSelected', function(event, modelName) {
                if (itemType == modelName && beamlineService.isActiveItem(itemType)) {
                    callback(beamlineService.activeItem);
                }
            });
        }

        return {
            restrict: 'A',
            scope: {
                fieldDef: '@' + name,
                modelName: '<',
                modelData: '<',
            },
            controller: init,
            link: function(scope) {
                if (scope.whenSelected) {
                    whenItemSelected(scope, scope.modelName, scope.whenSelected);
                }
                if (scope.watchFields) {
                    watchFields(scope, scope.watchFields);
                }
                if (scope.watchFieldsNoInit) {
                    watchFields(scope, scope.watchFieldsNoInit, true);
                }
            },
        };
    });
};

SIREPO.viewLogic = function(name, init) {
    SIREPO.app.directive(name, function(appState, panelState, utilities) {
        return {
            restrict: 'A',
            scope: {
                fieldDef: '@' + name,
                modelName: '<',
                modelData: '<',
            },
            controller: init,
            link: function(scope) {
                if (scope.whenSelected) {
                    scope.$parent.$on('sr-tabSelected', function(event, modelName, modelKey) {
                        if (scope.modelData) {
                            if (scope.modelData.modelKey == modelKey) {
                                scope.whenSelected();
                            }
                        }
                        else if (scope.modelName == modelName) {
                            scope.whenSelected();
                        }
                    });
                }
                if (scope.watchFields) {
                    for (var idx = 0; idx < scope.watchFields.length; idx += 2) {
                        var fields = scope.watchFields[idx];
                        var callback = utilities.debounce(scope.watchFields[idx + 1], SIREPO.debounce_timeout);
                        appState.watchModelFields(scope, fields, callback, true);
                    }
                }

                // must wait to get "angularized" form
                panelState.waitForUI(() => {
                    scope.form = scope.$parent.form;
                });
            },
        };
    });
};

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
        for (var type in SIREPO.APP_SCHEMA.dynamicModules) {
            mods = mods.concat(SIREPO.APP_SCHEMA.dynamicModules[type] || []);
        }
        mods = mods.concat(SIREPO.APP_SCHEMA.dynamicFiles.libURLs || []);
        return $.map(mods, loadDynamicModule);
    }

    $.ajax({
        url: '/simulation-schema' + SIREPO.SOURCE_CACHE_KEY,
        data: {
            simulationType: SIREPO.APP_NAME,
        },
        success: function(result) {
            if (result.state === 'srException') {
                throw new Error(`srException in /simulation-schema result=${JSON.stringify(result)}`);
            }
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
                if (err.toString().match(/forbidden/i)) {
                    window.location.href = "/http-forbidden";
                    return;
                }
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

SIREPO.refreshModalMap = {
    invalidSimulationSerial: {
        modal: "sr-invalidSimulationSerial",
        msg: 'This simulation has been updated outside of this browser',
        title: 'Simulation Conflict',
    },
    newRelease: {
        modal: "sr-newRelease",
        msg: 'Sirepo has been upgraded',
        title: 'Server Upgraded',
    },
};

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
SIREPO.app = angular.module('SirepoApp', ['ngDraggable', 'ngRoute', 'ngCookies', 'ngSanitize']).run(
    // Initialize factories not otherwise linked into dependency tree
    (asyncMsgSetCookies) => {}
);

SIREPO.app.value('localRoutes', {});

SIREPO.app.config(function(localRoutesProvider, $compileProvider, $locationProvider, $routeProvider, $sanitizeProvider) {
    let localRoutes = localRoutesProvider.$get();
    let defaultRoute = null;
    $locationProvider.hashPrefix('');
    $compileProvider.debugInfoEnabled(false);
    $compileProvider.commentDirectivesEnabled(false);
    $compileProvider.cssClassDirectivesEnabled(false);
    $sanitizeProvider.enableSvg(true);
    $sanitizeProvider.addValidAttrs(['id', 'label', 'style']);
    $sanitizeProvider.addValidElements(['select', 'option']);
    SIREPO.appFieldEditors = '';

    function addRoute(routeName) {
        var routeInfo = SIREPO.APP_SCHEMA.localRoutes[routeName];
        if (! routeInfo.config) {
            // the route isn't configured for the current app
            return;
        }
        const cfg = routeInfo.config;
        localRoutes[routeName] = routeInfo.route;
        if (cfg.templateUrl) {
            cfg.templateUrl += SIREPO.SOURCE_CACHE_KEY;
        }
        //TODO(pjm): may want to add an attribute to the route info rather than depend on the route param
        if (routeInfo.route.search(/:simulationId\b/) >= 0 && cfg.controller) {
            cfg.template = simulationDetailTemplate(cfg);
        }
        $routeProvider.when(routeInfo.route, cfg);
        if (routeName === SIREPO.APP_SCHEMA.appDefaults.route) {
            defaultRoute = routeName;
            if (routeInfo.route.indexOf(':') >= 0) {
                throw new Error('default route must not have params: ' + routeInfo.route);
            }
            cfg.redirectTo = routeInfo.route;
            $routeProvider.otherwise(cfg);
        }
    }

    function simulationDetailTemplate(cfg) {
        let res = '<div data-simulation-detail-page="" data-controller="' + cfg.controller + '"';
        delete cfg.controller;
        if (cfg.templateUrl) {
            res += ' data-template-url="' + cfg.templateUrl + '"';
            delete cfg.templateUrl;
        }
        else if (cfg.template) {
            res += ' data-template="' + cfg.template.replaceAll('"', '&quot;') + '"';
        }
        else {
            throw new Error('route must have template or templateUrl attribute: ' + cfg);
        }
        return res + '></div>';
    }

    for (var routeName in SIREPO.APP_SCHEMA.localRoutes) {
        addRoute(routeName);
    }
    if (! defaultRoute) {
        throw new Error('at least one route must be the default route');
    }
});

SIREPO.app.factory('authState', function(appDataService, appState, errorService, uri, $rootScope) {
    var self = appState.clone(SIREPO.authState);

    if (SIREPO.authState.isGuestUser
        && ! SIREPO.APP_SCHEMA.feature_config.hide_guest_warning
        && ! SIREPO.authState.isLoginExpired) {
        appState.whenModelsLoaded(
            $rootScope,
            function() {
                if (appDataService.isApplicationMode('default')) {
                    errorService.alertText(
                        'You are accessing Sirepo as a guest. ' +
                            'Guest sessions are regularly deleted. ' +
                            'To ensure that your work is saved, please click on Save Your Work!.'
                    );
                }
            }
        );
    }

    SIREPO.APP_SCHEMA.enum.JobRunMode = SIREPO.APP_SCHEMA.enum.JobRunMode.map(
        function (x) {
            return [x[0], self.jobRunModeMap[x[0]]];
        }
    );

    self.handleLogin = function (data, controller) {
        if (data.state === 'ok') {
            if (data.authState) {
                SIREPO.authState = data.authState;
                $.extend(self, SIREPO.authState);
            }
            uri.globalRedirectRoot();
            return;
        }
        controller.showWarning = true;
        controller.warningText = 'Server reported an error, please contact support@radiasoft.net.';
    };

    self.paymentPlanName = function() {
        return SIREPO.APP_SCHEMA.constants.paymentPlans[self.paymentPlan];
    };

    self.upgradePlanLink = function() {
        return '<a href="' + SIREPO.APP_SCHEMA.constants.plansUrl +
            '" target="_blank">' +
            SIREPO.APP_SCHEMA.constants.paymentPlans[self.upgradeToPlan] + '</a>';
    };

    return self;
});

SIREPO.app.factory('activeSection', function(authState, requestSender, $location, $route, $rootScope, appState) {
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
            appState.loadModels(
                $route.current.params.simulationId,
                // clear list items each time a simulation is loaded
                requestSender.clearListFilesData,
                self.getActiveSection());
        }
    });

    return self;
});

SIREPO.app.factory('appState', function(errorService, fileManager, requestQueue, requestSender, utilities, $document, $interval, $rootScope, $filter) {
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

    function broadcastSaved(name) {
        $rootScope.$broadcast(name + '.saved');
        $rootScope.$broadcast('modelSaved', name);
    }

    function deepEqualsNoSimulationStatus(models1, models2) {
        var status = [models1.simulationStatus, models2.simulationStatus];
        delete models1.simulationStatus;
        delete models2.simulationStatus;
        var res = self.deepEquals(models1, models2);
        models1.simulationStatus = status[0];
        models2.simulationStatus = status[1];
        return res;
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
        let models = self.models;
        for (let m in fieldsByModel) {
            if (models[m]) {
                if (! savedModelValues[m]) {
                    return true;
                }
                for (const f of Array.from(fieldsByModel[m])) {
                    if (! self.deepEquals(models[m][f], savedModelValues[m][f])) {
                        return true;
                    }
                }
            }
        }
        return false;
    };

    self.autoSave = function(callback) {
        if (! self.isLoaded() ||
            lastAutoSaveData && deepEqualsNoSimulationStatus(
                lastAutoSaveData.models, savedModelValues)
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
                        if (resp.error) {
                            errorService.alertText(resp.error);
                            return;
                        }
                        lastAutoSaveData = self.clone(resp);
                        ['simulationSerial', 'name', 'lastModified'].forEach(f => {
                            savedModelValues.simulation[f] =
                                self.models.simulation[f] = lastAutoSaveData.models.simulation[f];
                        });
                        if ($.isFunction(callback)) {
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

    self.deepEquals = function(v1, v2, doStripHashKey=false) {

        function stripHashKey(keys) {
            return doStripHashKey ? keys.filter(k => k !== '$$hashKey') : keys;
        }

        if (v1 === v2) {
            return true;
        }
        if (angular.isArray(v1) && angular.isArray(v2)) {
            if (v1.length !== v2.length) {
                return false;
            }
            for (let i = 0; i < v1.length; i++) {
                if (! self.deepEquals(v1[i], v2[i], doStripHashKey)) {
                    return false;
                }
            }
            return true;
        }
        if (angular.isObject(v1) && angular.isObject(v2)) {
            const keys = stripHashKey(Object.keys(v1));
            if (keys.length !== stripHashKey(Object.keys(v2)).length) {
                return false;
            }
            return ! keys.some(k => ! self.deepEquals(v1[k], v2[k], doStripHashKey));
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
            throw new Error('no value for enum: ' + enumName + '.' + value);
        }
        return res;
    };

    self.enumVals = function(enumName) {
        return SIREPO.APP_SCHEMA.enum[enumName].map(function (e) {
            return e[SIREPO.ENUM_INDEX_VALUE];
        });
    };

    // intermediate method to change from arrays to objects when defining model fields
    self.fieldProperties = function(modelName, fieldName) {
        // these won't exist for beamline elements
        // if(! self.models[modelName]) {
        //     throw modelName + ": no such model in simulation " + SIREPO.APP_SCHEMA.simulationType;
        // }

        var info = self.modelInfo(modelName, fieldName)[fieldName];
        if(! info) {
            throw new Error(fieldName + ": no such field in model " + modelName);
        }
        var infoNames = ['label', 'type', 'default', 'toolTip', 'min', 'max'];
        var p = {};
        info.forEach(function (v, i) {
            p[i] = v;
            p[infoNames[i]] = v;
        });
        return p;
    };

    self.formatDate = function(unixTime) {
        if (! unixTime) {
            return null;
        }
        return $filter('date')(unixTime * 1000, 'yyyy-MM-dd HH:mm:ss');
    };

    self.formatExponential = function(value) {
        if (Math.abs(value) >= 10000 || (value != 0 && Math.abs(value) < 0.001)) {
            value = (+value).toExponential(9).replace(/\.?0+e/, 'e');
        }
        return value;
    };

    self.formatFloat = function(v, decimals) {
        return +parseFloat(v).toFixed(decimals);
    };

    self.formatTime = function(unixTime) {
        function format(val) {
            return leftPadZero(Math.floor(val));
        }

        function leftPadZero(num) {
            if (num < 10) {
                return '0' + num;
            }
            return num;
        }

        var d = Math.floor(unixTime / (3600*24));
        var h = format(unixTime % (3600*24) / 3600);
        var m = format(unixTime % 3600 / 60);
        var s = format(unixTime % 60);
        var res = d > 0 ? d : '';
        if (res) {
            res += d === 1 ? ' day ': ' days ';
        }
        return res + h + ':' + m + ':' + s;
    };

    self.isAnimationModelName = function(name) {
        return name == 'animation' || name.indexOf('Animation') >= 0;
    };

    self.isLoaded = function() {
        return self.models.simulation && self.models.simulation.simulationId ? true: false;
    };

    // angular-independent isObject()
    self.isObject = function(x) {
        if (x === null) {
            return false;
        }
        return ( (typeof x === 'function') || (typeof x === 'object') );
    };

    self.isReportModelName = function(name) {
        //TODO(pjm): need better name for this, a model which doesn't affect other models
        return  name.indexOf('Report') >= 0 || self.isAnimationModelName(name) || name.indexOf('Status') >= 0;
    };

    self.isSubclass = function(model1, model2) {
        return this.superClasses(model1).includes(model2);
    };

    self.listSimulations = function(op, search) {
        requestSender.sendRequest(
            'listSimulations',
            function(data) {
                op(data);
            },
            {
                simulationType: SIREPO.APP_SCHEMA.simulationType,
                search: search,
            }
        );
    };

    self.loadModels = function(simulationId, callback, section) {
        if (self.isLoaded() && self.models.simulation.simulationId == simulationId) {
            return;
        }
        self.clearModels();
        var routeObj = {
            routeName: 'simulationData',
            simulation_id: simulationId,
            simulation_type: SIREPO.APP_SCHEMA.simulationType,
            pretty: false
        };
        if (section) {
            routeObj.section = section;
        }
        requestSender.sendRequest(
            routeObj,
            function(data) {
                if (data.notFoundCopyRedirect) {
                    requestSender.localRedirect('notFoundCopy', {
                        simulationIds: data.notFoundCopyRedirect.simulationId
                            + (data.notFoundCopyRedirect.userCopySimulationId
                               ? ('-' + data.notFoundCopyRedirect.userCopySimulationId)
                               : ''),
                        section: data.notFoundCopyRedirect.section,
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
            throw new Error('invalid model name: ' + name);
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

    self.setAppService = function (appService) {
        if (self.appService) {
            throw new Error('too many calls to setAppService new=', appService);
        }
        self.appService = appService;
        return;
    };

    self.saveChanges = function(name, callback) {
        // save changes on a model by name, or by an array of names
        if (typeof(name) == 'string') {
            name = [name];
        }
        let updatedFields = [];
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
                for (let f in self.models[name[i]]) {
                    const s = savedModelValues[name[i]];
                    if (! s || ! self.deepEquals(s[f], self.models[name[i]][f], true)) {
                        updatedFields.push(`${name[i]}.${f}`);
                    }
                }
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
            // broadcast when save is done, for taking actions on now-persisted model
            for (let m of updatedModels) {
                broadcastSaved(m);
            }
        });
    };

    self.setFieldDefaults = function(model, field, fieldInfo, overWrite=false) {
        let defaultVal = fieldInfo[SIREPO.INFO_INDEX_DEFAULT_VALUE];
        if (fieldInfo[SIREPO.INFO_INDEX_TYPE] === 'RandomId') {
            defaultVal = SIREPO.UTILS.randomString();
        }
        if (! model[field] || overWrite) {
            if (defaultVal !== undefined) {
                // for cases where the default value is an object, we must
                // clone it or the schema itself will change as the model changes
                model[field] = self.isObject(defaultVal) ? self.clone(defaultVal) : defaultVal;
            }
        }
    };

    self.setModelDefaults = function(model, modelName) {
        // set model defaults from schema
        const schema = SIREPO.APP_SCHEMA.model[modelName];
        const fields = Object.keys(schema);
        for (let i = 0; i < fields.length; i++) {
            const s = schema[fields[i]];
            self.setFieldDefaults(model, fields[i], s);
            const m = self.parseModelField(s[SIREPO.INFO_INDEX_TYPE]);
            if (! m || m[0] !== 'model') {
                continue;
            }
            model[fields[i]] = self.setModelDefaults({}, m[1]);
        }
        return model;
    };

    self.superClasses = (modelName) => {
        const m = SIREPO.APP_SCHEMA.model[modelName];
        const f = '_super';
        if (! m || ! m[f]) {
            return [];
        }
        // the first two slots are the label (usually '_') and 'model'
        return m[f].slice(2);
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

    self.watchModelFields = function($scope, modelFields, callback, useDeepEquals=false) {
        $scope.appState = self;
        modelFields.forEach(function(f) {
            // allows watching fields when creating a new simulation (isLoaded() returns false)
            const isSim = self.parseModelField(f)[0] === 'simulation';
            // elegant uses '-' in modelKey
            $scope.$watch('appState.models' + propertyToIndexForm(f), function (newValue, oldValue) {
                if ((self.isLoaded() || isSim) && newValue !== null && newValue !== undefined && newValue !== oldValue) {
                    // call in next cycle to allow UI to change layout first
                    $interval(callback, 1, 1, true, f);
                }
            }, useDeepEquals);
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
    self.canCopy = function() {
        return true;
    };
    return self;
});

SIREPO.app.factory('stringsService', function() {
    const strings = SIREPO.APP_SCHEMA.strings;

    function typeOfSimulation(modelName) {
        let s;
        if (modelName && strings[modelName] && strings[modelName].typeOfSimulation) {
            s = strings[modelName].typeOfSimulation;
        }
        return ucfirst(s || strings.typeOfSimulation);
    }

    function ucfirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    function lcfirst(str) {
        return str[0].toLowerCase() + str.substring(1);
    }

    return {
        formatKey: (name) => {
            return ucfirst(strings[name]);
        },
        formatTemplate: (template, args) => {
            return template.replace(
                /{(\w*)}/g,
                function(m, k) {
                    if (! (k in (args || {}))) {
                        if (! (k in strings)) {
                            throw new Error(`k=${k} not found in args=${args} or strings=${strings}`);
                        }
                        return strings[k];
                    }
                    return args[k];
                }
            );

        },
        newSimulationLabel: () => {
            return strings.newSimulationLabel || `New ${ucfirst(strings.simulationDataType)}`;
        },
        startButtonLabel: (modelName) => {
            return `Start New ${typeOfSimulation(modelName)}`;
        },
        stopButtonLabel: (modelName) => {
            return `End ${typeOfSimulation(modelName)}`;
        },
        typeOfSimulation: typeOfSimulation,
        ucfirst: ucfirst,
        lcfirst: lcfirst
    };
});

SIREPO.app.factory('timeService', function() {
    const UNIX_TIMESTAMP_SCALE = 1000;
    const self = {};

    self.roundUnixTimeToMinutes = (date) => {
        return Number.parseInt(date / 60) * 60;
    };

    self.unixTime = (date) => {
        return Math.round(date.getTime() / UNIX_TIMESTAMP_SCALE);
    };

    self.unixTimeNow = () => {
        return self.unixTime(new Date());
    };

    self.unixTimeOneDayAgo = () => {
        return self.unixTimeNow() - (60 * 60 * 24);
    };

    self.unixTimeOneHourAgo = () => {
        return self.unixTimeNow() - (60 * 60);
    };

    self.unixTimeOneWeekAgo = () => {
        return self.unixTimeNow() - (60 * 60 * 24 * 7);
    };


    self.unixTimeToDate = (unixTime) => {
        return new Date(unixTime * UNIX_TIMESTAMP_SCALE);
    };

    self.unixTimeToDateString = (unixTime) => {
        return self.unixTimeToDate(unixTime).toLocaleString(
            'en-US',
            {
                timeZoneName: 'short'
            }
        );
    };

    return self;
});

// manages validators for ngModels and provides other validation services
SIREPO.app.service('validationService', function(utilities) {

    this.fieldValidators = {};
    this.enumValidators = {};

    // lazy creation of validator, plus special handling
    this.getEnumValidator = function(enumName) {

        var validator = this.getFieldValidator(enumName);
        if (validator) {
            return validator;
        }
        var enums = SIREPO.APP_SCHEMA.enum[enumName];
        if (! enums) {
            throw new Error(enumName + ':' + ' no such enum');
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
            if (! validator.vFunc(name)) {
                throw new Error(validator.vMsg(name));
            }
            return name;
        };
        return validator;
    };

    this.getFieldValidator = function(name) {
        return this.fieldValidators[name];
    };

    this.getMessageForNGModel = function(name, ngModelValidatorName, ngModel) {
        if (! ngModel.$validators[ngModelValidatorName]) {
            return '';
        }
        var fv = this.getFieldValidator(name);
        return fv ? (! ngModel.$valid ? fv.vMsg(ngModel.$viewValue) : '') : '';
    };

    this.getModelFieldMessage = function (modelName, fieldName) {
        var fullName = utilities.modelFieldID(modelName, fieldName);
        var ngModel = utilities.ngModelForInput(modelName, fieldName);
        return this.getMessageForNGModel(fullName, fullName, ngModel);
    };

    this.reloadValidatorForNGModel = function(name, ngModelValidatorName, ngModel) {
        var fv = this.getFieldValidator(name);
        if (! ngModel.$validators[ngModelValidatorName]) {
            if (fv) {
                ngModel.$validators[ngModelValidatorName] = fv.vFunc;
            }
        }
    };

    this.removeFieldValidator = function(name) {
        if (this.fieldValidators[name]) {
            delete this.fieldValidators[name];
        }
    };

    this.removeModelFieldValidator = function(modelName, fieldName) {
        var fullName = utilities.modelFieldID(modelName, fieldName);
        var ngModel = utilities.ngModelForInput(modelName, fieldName);
        this.removeValidatorForNGModel(fullName, fullName, ngModel);
    };

    this.removeValidatorForNGModel = function(name, ngModelValidatorName, ngModel) {
        if (ngModel.$validators[ngModelValidatorName]) {
            delete ngModel.$validators[ngModelValidatorName];
        }
        this.removeFieldValidator(name);
    };

    this.setFieldValidator = function(name, validatorFn, messageFn, ngModel, ngModelValidatorName) {
        if (! this.fieldValidators[name]) {
            this.fieldValidators[name] = {};
        }
        this.fieldValidators[name].vFunc = validatorFn;
        this.fieldValidators[name].vMsg = messageFn;
        if (ngModel && ngModelValidatorName) {
            this.reloadValidatorForNGModel(name, ngModelValidatorName, ngModel);
        }
        return this.fieldValidators[name];
    };

    this.setModelFieldValidator = function(modelName, fieldName, validatorFn, messageFn) {
        var fullName = utilities.modelFieldID(modelName, fieldName);
        var ngModel = utilities.ngModelForInput(modelName, fieldName);
        return this.setFieldValidator(fullName, validatorFn, messageFn, ngModel, fullName);
    };

    // html5 validation
    this.validateField = function(model, field, inputType, isValid, msg) {
        return this.validateInputSelectorString(`.${utilities.modelFieldID(model, field)} ${inputType}`, isValid, msg);
    };

    this.validateInputSelectorString = function(str, isValid, msg) {
        return this.validateInputSelector($(str), isValid, msg);
    };

    this.validateInputSelector = function(sel, isValid, msg) {
        const f = sel[0];
        // do not invalidate if the selector is not found
        if (! f) {
            return true;
        }
        const fWarn = sel.siblings('.sr-input-warning').eq(0);
        const invalidClass = 'ng-invalid ng-dirty';
        fWarn.text(msg);
        fWarn.hide();
        f.setCustomValidity('');
        sel.removeClass(invalidClass);
        if (! isValid) {
            sel.addClass(invalidClass);
            f.setCustomValidity(msg);
            fWarn.show();
        }
        return isValid;
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
        if (SIREPO.APP_SCHEMA.enum[type]) {
            return this.getEnumValidator(type).vFunc(value);
        }
        // TODO(mvk): other types here, for now just accept everything
        return true;
    };

});


SIREPO.app.factory('frameCache', function(appState, panelState, requestSender, $interval, $rootScope, $timeout) {
    var self = {};
    var frameCountByModelKey = {};
    var masterFrameCount = 0;
    self.modelToCurrentFrame = {};

    self.frameId = function(frameReport, frameIndex) {
        function fieldToFrameParam(field) {
            if (angular.isObject(field)) {
                return JSON.stringify(field);
            }
            return `${field}`;
        }

        var c = appState.appService.computeModel(frameReport);
        var s = appState.models.simulationStatus[c];
        if (! s) {
            throw new Error('computeModel=' + c + ' missing simulationStatus');
        }
        var v = [
            // POSIT: same as sirepo.sim_data._FRAME_ID_KEYS
            frameIndex,
            frameReport,
            appState.models.simulation.simulationId,
            SIREPO.APP_SCHEMA.simulationType,
            s.computeJobHash,
            s.computeJobSerial,
        ];
        var m = appState.models;
        m = m[frameReport in m ? frameReport : c];
        var f = SIREPO.APP_SCHEMA.frameIdFields;
        f = f[frameReport in f ? frameReport : c];
        if (! f) {
            throw new Error('frameReport=' + frameReport + ' missing from schema frameIdFields');
        }
        // POSIT: same as sirepo.sim_data._FRAME_ID_SEP
        return v.concat(
            f.map(a => fieldToFrameParam(m[a]))
        ).join('*');
    };

    self.getCurrentFrame = function(modelName) {
        return self.modelToCurrentFrame[modelName] || 0;
    };

    self.getFrame = function(modelName, index, isPlaying, callback) {
        if (! appState.isLoaded()) {
            return;
        }
        function onError() {
            panelState.reportNotGenerated(modelName);
        }
        function now() {
            return new Date().getTime();
        }
        let isHidden = panelState.isHidden(modelName);
        let frameRequestTime = now();
        let waitTimeHasElapsed = false;
        const framePeriod = () => {
            if (! isPlaying || isHidden) {
                return 0;
            }
            const milliseconds = 1000;
            var x = appState.models[modelName].framesPerSecond;
            if (! x) {
                return  0.5 * milliseconds;
            }
            return  milliseconds / parseInt(x);
        };

        const requestFunction = function() {
            const i = appState.models.simulation.simulationId;
            $timeout(() => {
                if (! waitTimeHasElapsed) {
                    panelState.setLoading(modelName, true);
                }
            }, 5000);
            requestSender.sendRequest(
                {
                    routeName: 'simulationFrame',
                    frame_id: self.frameId(modelName, index),
                },
                function(data) {
                    waitTimeHasElapsed = true;
                    if (! appState.isLoaded()) {
                        return;
                    }
                    const c = appState.models.simulation.simulationId;
                    if (! c || c !== i) {
                        return;
                    }
                    panelState.setLoading(modelName, false);
                    if ('state' in data && data.state === 'missing') {
                        onError();
                        return;
                    }
                    let e = framePeriod() - (now() - frameRequestTime);
                    if (e <= 0) {
                        callback(index, data);
                        return;
                    }
                    $interval(
                        function() {
                            callback(index, data);
                        },
                        e,
                        1
                    );
                },
                null,
                onError
            );
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
            var s = self.getSimulationStatus(modelKey);
            if (! (s && s.computeJobHash)
            ) {
                // cannot request frames without computeJobHash
                return 0;
            }
            return frameCountByModelKey[modelKey];
        }
        return masterFrameCount;
    };

    self.getSimulationStatus = (modelKey) => {
        return appState.models.simulationStatus[appState.appService.computeModel(modelKey)];
    };

    self.setCurrentFrame = function(modelName, currentFrame) {
        self.modelToCurrentFrame[modelName] = currentFrame;
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
        self.modelToCurrentFrame = {};
        self.modelsUnloaded = {};
    });

    return self;
});

SIREPO.app.factory('authService', function(authState, uri, stringsService) {
    var self = {};

    function label(method) {
        if ('guest' == method) {
            return 'as Guest';
        }
        return 'with ' + stringsService.ucfirst(method);
    }

    self.methods = authState.visibleMethods.map(
        function (method) {
            return {
                'label': 'Sign in ' + label(method),
                'url': uri.formatLocal(
                    'loginWith',
                    {':method': method}
                )
            };
        }
    );
    self.loginUrl = uri.formatLocal('login');
    self.logoutUrl = uri.format(
        'authLogout',
        {simulation_type: SIREPO.APP_SCHEMA.simulationType}
    );
    return self;
});

/* SIREPO.app.factory('jobConfig', function(appState, requestSender) {
 *     var self = {};
 *
 *     requestSender.sendRequest(
 *         'jobConfig',
 *         function () {
 *
 *         },
 *         {
 *             simulationType: SIREPO.APP_SCHEMA.simulationType,
 *         },
 *         process,
 *     );
 *     return self;
 * });
 * */
SIREPO.app.factory('panelState', function(appState, uri, simulationQueue, utilities, $compile, $rootScope, $timeout, $window) {
    // Tracks the data, error, hidden and loading values
    var self = {};
    var panels = {};
    var pendingRequests = {};
    var queueItems = {};
    var waitForUICallbacks = null;
    var windowResize = utilities.debounce(function() {
        $rootScope.$broadcast('sr-window-resize');
    }, 250);
    self.ngViewScope = null;


    $rootScope.$on('clearCache', function() {
        self.clear();
    });

    $rootScope.$on('$viewContentLoaded', function (event) {
        // this is the parent scope used for modal editors created from showModalEditor()
        self.ngViewScope = event.targetScope;
    });

    function applyToFields(method, modelName, fieldInfo) {
        var enableFun = function(f) {
            self[method](modelName, f, true);
        };
        var disableFun = function(f) {
            self[method](modelName, f, false);
        };
        for (var idx = 0; idx < fieldInfo.length; idx += 2) {
            var field = fieldInfo[idx];
            var isEnabled = fieldInfo[idx + 1];
            if (angular.isArray(field)) {
                field.forEach(isEnabled ? enableFun : disableFun);
            }
            else {
                self[method](modelName, field, isEnabled);
            }
        }
    }

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
            let modelField = appState.parseModelField(field);
            if (! modelField) {
                modelField = [primaryModelName, field];
            }
            // handle compound fields of the form <modelName>.<fieldName>
            // since a top-level model can have a number of these, put the field names
            // in a Set (order does not matter)
            const x = appState.parseModelField(modelField[1]);
            if (x && x.length === 2) {
                const t = SIREPO.APP_SCHEMA.model[modelField[0]][x[0]][SIREPO.INFO_INDEX_TYPE];
                modelField = [t.split('.')[1], x[1]];
            }
            if (! names[modelField[0]]) {
                names[modelField[0]] = new Set();
            }
            names[modelField[0]].add(modelField[1]);
        }
        else {
            // [name, [cols]]
            if (typeof(field[0]) == 'string') {
                for (let i = 0; i < field[1].length; i++) {
                    iterateFields(primaryModelName, field[1][i], names);
                }
            }
            // [[name, [cols]], [name, [cols]], ...]
            else {
                for (let i = 0; i < field.length; i++) {
                    iterateFields(primaryModelName, field[i], names);
                }
            }
        }
    }

    function sendRequest(name, callback, errorCallback) {
        setPanelValue(name, 'loading', true);
        setPanelValue(name, 'error', null);
        var responseHandler = function(resp) {
            setPanelValue(name, 'loading', false);
            if (resp.error) {
                setPanelValue(name, 'error', resp.error);
                if (errorCallback) {
                    errorCallback(resp);
                }
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
        );
    }

    function setPanelValue(name, key, value) {
        if (! (name || key)) {
            throw new Error('missing name or key');
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

    function urlForExport(simulationId, route, args) {
        if (! simulationId) {
            return null;
        }
        const a = {
            simulation_id: simulationId,
            simulation_type: SIREPO.APP_SCHEMA.simulationType,
        };
        return uri.format(route, {...a, ...args});
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
        $(fc).find('button.dropdown-toggle').prop('disabled', ! isEnabled);
    };

    self.enableArrayField = function(model, field, index, isEnabled) {
        $(fieldClass(model, field)).find('input.form-control').eq(index).prop('readonly', ! isEnabled);
    };

    self.enableFields = function(model, fieldInfo) {
        applyToFields('enableField', model, fieldInfo);
    };

    self.exportArchiveUrl = (simulationId, filename) => {
        return urlForExport(simulationId, 'exportArchive', {
            filename:  filename,
        });
    };

    // lazy creation/storage of field delegates
    self.fieldDelegates = {};

    // if no associated view, check for a superclass that does have one
    self.getBaseModelKey = function(modelKey) {
        if (appState.viewInfo(modelKey)) {
            return modelKey;
        }
        if (! (modelKey in SIREPO.APP_SCHEMA.model)) {
            return modelKey;
        }
        var m = appState.modelInfo(modelKey);
        if (m._super) {
            for (var i = SIREPO.INFO_INDEX_DEFAULT_VALUE; i < m._super.length; ++i) {
                if (appState.viewInfo(m._super[i])) {
                    modelKey = m._super[i];
                    return modelKey;
                }
            }
        }
        return modelKey;
    };

    self.getFieldDelegate = function(modelName, field) {
        if (! self.fieldDelegates[modelName]) {
            self.fieldDelegates[modelName] = {};
        }
        if (! self.fieldDelegates[modelName][field]) {
            self.fieldDelegates[modelName][field] = {
                storedVal: appState.models[modelName][field],
            };
        }
        return self.fieldDelegates[modelName][field];
    };

    self.fileNameFromText = function(text, extension) {
        return text.replace(/(\_|\W|\s)+/g, '-').replace(/-+$/, '') + '.' + extension;
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
        names[primaryModelName] = new Set();
        for (var i = 0; i < fields.length; i++) {
            iterateFields(primaryModelName, fields[i], names);
        }
        return names;
    };

    self.getStatusText = function(name) {
        if (self.isRunning(name)) {
            var count = (queueItems[name] && queueItems[name].runStatusCount) || 0;
            var progressText = (appState.models[name] || {}).inProgressText  ||
                SIREPO.APP_SCHEMA.constants.inProgressText ||
                'Simulating';
            return progressText + ' ' + new Array(count % 3 + 2).join('.');
        }
        return appState.isAnimationModelName(name)
            ? 'Requesting Data'
            : 'Waiting';
    };

    self.isActiveField = function(model, field) {
        return $(fieldClass(model, field)).find('input, select').is(':focus');
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

    self.isWaiting = name => {
        return getPanelValue(name, 'waiting') ? true : false;
    };

    self.maybeSetState = function(model, state) {
        if (!model) {
            return;
        }
        const d = {
            error: () => self.reportNotGenerated(model),
            loading: () => self.setLoading(model, true),
            loadingDone: () => self.setLoading(model, false)
        };
        return d[state]();
    };

    self.modalId = function(name) {
        return 'sr-' + name + '-editor';
    };

    self.pythonSourceUrl = (simulationId, modelName, reportTitle) => {
        const args = {};
        if (modelName) {
            args['<model>'] = modelName;
        }
        if (reportTitle) {
            args['<title>'] = reportTitle;
        }
        return urlForExport(simulationId, 'pythonSource', args);
    };

    self.reportNotGenerated = function(modelName) {
        self.setLoading(modelName, false);
        self.setError(modelName, 'Report not generated');
    };

    self.requestData = function(name, callback, errorCallback) {
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
            queueItems[name] = sendRequest(name, wrappedCallback, errorCallback);
        });
        if (! self.isHidden(name)) {
            queueItems[name] = sendRequest(name, wrappedCallback, errorCallback);
        }
    };

    self.setError = function(name, error) {
        setPanelValue(name, 'error', error);
    };

    self.setFieldLabel = function(model, field, text) {
        $('.' + utilities.modelFieldID(model, field)  + ' .control-label label')
            .text(text);
    };

    self.setHidden = (name, doHide=true) => {
        if ((self.isHidden(name) && doHide) || (! self.isHidden(name) && ! doHide) ) {
            return;
        }
        self.toggleHidden(name);
    };

    self.setLoading = (name, isLoading) => setPanelValue(name, 'loading', isLoading);

    self.setData = (name, data) => setPanelValue(name, 'data', data);

    self.setWaiting = (name, isWaiting) => {
        setPanelValue(name, 'waiting', isWaiting);
    };

    self.showEnum = function(model, field, value, isShown, instance=null) {
        var eType = SIREPO.APP_SCHEMA.enum[appState.modelInfo(model)[field][SIREPO.INFO_INDEX_TYPE]];
        var optionIndex = -1;
        eType.forEach(function(row, index) {
            if (row[0] == value) {
                optionIndex = index;
            }
        });
        if (optionIndex < 0) {
            throw new Error('no enum value found for ' + model + '.' + field + ' = ' + value);
        }

        let sel = $(fieldClass(model, field));
        // apply to a specific instance
        if (instance != null) {
            sel = sel.eq(instance);
        }
        // apply to all instances
        const f = i => i % eType.length === optionIndex;
        let opt = sel.find('option').filter(f);

        if (! opt || ! opt.length) {
            // handle case where enum is displayed as a button group rather than a select
            opt = sel.find('button').filter(f);
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

    self.showArrayField = function(model, field, index, isShown) {
        const f = $(fieldClass(model, field)).find('input.form-control').eq(index);
        showValue(f, isShown);
        showValue(f.prev('label'), isShown);
    };

    self.showField = function(model, field, isShown) {
        //TODO(pjm): remove jquery and use attributes on the fieldEditor directive
        // try show/hide immediately, followed by timeout if UI hasn't finished layout yet
        showValue($(fieldClass(model, field)).closest('.form-group'), isShown);
        self.waitForUI(function() {  //MR: fix for https://github.com/radiasoft/sirepo/issues/730
            showValue($(fieldClass(model, field)).closest('.form-group'), isShown);
        });
    };

    self.showFields = function(modelName, fieldInfo) {
        applyToFields('showField', modelName, fieldInfo);
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
        modelKey = self.getBaseModelKey(modelKey);
        var editorId = '#' + self.modalId(modelKey);
        var showEvent = modelKey + '.editor.show';
        if ($(editorId).length) {
            $(editorId).modal('show');
            $rootScope.$broadcast(showEvent);
            if (modelKey === 'simulation') {
                $rootScope.$emit(showEvent);
            }
        }
        else {
            if (! template) {
                var name = modelKey.toLowerCase().replace('_', '');
                //TODO(pjm): DEPRECATED use viewLogic instead
                template = '<div data-modal-editor="" data-view-name="' + modelKey + '" data-sr-' + name + '-editor=""' + '></div>';
            }
            // add the modal to the ng-view element so it will get removed from the page when the location changes
            $('.sr-view-content').append($compile(template)(scope || self.ngViewScope));

            //TODO(pjm): timeout hack, otherwise jquery can't find the element
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

    self.toggleHiddenAndNotify = name => {
        self.toggleHidden(name);
        $rootScope.$broadcast(`panel.${name}.hidden`, self.isHidden(name));
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

SIREPO.app.factory('uri', ($location, $rootScope, $window) => {
    const self = {};
    const globalMap = {_name: 'global'};
    const localMap = {_name: 'local'};

    const _format = (map, routeOrParams, params) => {
        let n = routeOrParams;
        if (angular.isObject(routeOrParams)) {
            n = routeOrParams.routeName;
            if (! n) {
                throw new Error(routeOrParams + ': routeName must be supplied');
            }
            if (angular.isDefined(params)) {
                srlog(map, routeOrParams, params);
                throw new Error(params + ': params must be null if routeOrParams is an object: ' + routeOrParams);
            }
            params = angular.copy(routeOrParams);
            delete params.routeName;
        }
        var p = {};
        if (params) {
            for (var k in params) {
                // Deprecated params values: <simulationId> and :simulationId
                p[k.replace(/\W+/g, '')] = params[k];
            }
        }
        params = p;
        if (! map[n]) {
            throw new Error(`routeName=${n} not found in map=${map._name}`);
        }
        const r = map[n];
        let u = r.baseUri ? '/' + r.baseUri : '';
        let v = null;
        for (p of r.params) {
            if (p.name in params) {
                v = params[p.name];
            }
            else if (p.name === "simulation_type") {
                v = SIREPO.APP_SCHEMA.simulationType;
            }
            else if (p.isOptional) {
                break;
            }
            else {
                throw new Error(`param=${p.name} param missing map=${map._name} route=${r.name}`);
            }
            u = u + '/' + encodeURIComponent(_serializeValue(v, p.name));
        }
        return u;
    };

    // we can trust that the Python has validated the schema
    // so no need for complicated checks like in sirepo.uri_router.
    const _globalIterator = (p) => {
        var m = p.match(/^([\?\*]?)<(\w+)>$/);
        if (! m) {
            throw new Error(`param=${p} invalid syntax global route`);
        }
        return {
            name: m[2],
            isOptional: !! m[1],
        };
    };

    const _init = () => {
        for (let n in SIREPO.APP_SCHEMA.route) {
            let u = SIREPO.APP_SCHEMA.route[n].split('/');
            u.shift();
            globalMap[n] = {
                name: n,
                // root route has /*<path_info> so check for a non-param element
                baseUri: u[0].match(/^[^\*\?<]/) ? u.shift() : '',
                params: u.map(_globalIterator),
            };
        }

        for (let n in SIREPO.APP_SCHEMA.localRoutes) {
            localMap[n] = _routeMapLocal(n, SIREPO.APP_SCHEMA.localRoutes[n].route);
        }
    };

    const _localIterator = (p) => {
        var m = p.match(/^:(\w+)(\??)$/);
        if (! m) {
            throw new Error(`param=${p} invalid syntax local route`);
        }
        return {
            name: m[1],
            isOptional: !! m[2],
        };
    };

    const _routeMapLocal = (name, route) => {
        const u = route.split('/');
        u.shift();
        return {
            name: name,
            baseUri: u.shift(),
            params: u.map(_localIterator),
        };
    };

    const _routeNameOrUri = (routeNameOrUri, params) => {
        if (routeNameOrUri.indexOf('/') >= 0) {
            return routeNameOrUri;
        }
        return self.format(routeNameOrUri, params);
    };

    // Started from serializeValue in angular, but need more specialization.
    // https://github.com/angular/angular.js/blob/2420a0a77e27b530dbb8c41319b2995eccf76791/src/ng/http.js#L12
    const _serializeValue = (v, param) => {
        if (v === null) {
            throw new Error(param + ': may not be null');
        }
        if (typeof v == 'boolean') {
            //TODO(robnagler) probably needs to be true/false with test
            return v ? '1' : '0';
        }
        if (angular.isString(v)) {
            if (v === '') {
                throw new Error(param + ': may not be empty string');
            }
            return v;
        }
        if (angular.isNumber(v)) {
            return v.toString();
        }
        if (angular.isDate(v)) {
            return v.toISOString();
        }
        throw new Error(param + ': ' + (typeof v) + ' type cannot be serialized');
    };

    self.defaultRouteName = (appMode=null) => {
        return SIREPO.APP_SCHEMA.appModes[appMode || 'default'].localRoute;
    };

    self.firstComponent = (uri) => {
        return uri.split('/')[1];
    };

    self.format = (routeName, params) => {
        return _format(globalMap, routeName, params);
    };

    self.formatLocal = (routeName, params, app, routeMap=localMap) => {
        var u = '#' + _format(routeMap, routeName, params);
        return app ? '/' + app + u : u;
    };

    self.globalRedirect = (routeNameOrUri, params) => {
        var u = _routeNameOrUri(routeNameOrUri, params);
        var i = u.indexOf('#');
        // https://github.com/radiasoft/sirepo/issues/2160
        // hash is persistent even if setting href so explicitly
        // set hash before href to avoid loops (e.g. #/server-upgraded)
        if (i >= 0) {
            $window.location.hash = u.substring(i);
            u = u.substring(0, i);
        }
        else {
            $location.hash('#');
        }
        $window.location.href = u;
        // The whole app will reload.
        // Don't respond to additional location change events from the current app.
        $rootScope.$on('$locationChangeStart', function (event) {
            event.preventDefault();
        });
    };

    self.globalRedirectRoot = () => {
        self.globalRedirect(
            'root',
            {path_info: SIREPO.APP_SCHEMA.simulationType}
        );
    };

    self.isRouteParameter = (routeName, paramName) => {
        var r = localMap[routeName] || globalMap[routeName];
        if (! r) {
            throw new Error('Invalid routeName: ' + routeName);
        }
        return r.params.some(function(p) {
            return p.name == paramName;
        });
    };

    self.localRedirect = (routeNameOrUri, params) => {
        var u = routeNameOrUri;
        if (u.indexOf('/') < 0) {
            u = self.formatLocal(u, params);
        }
        if (u.charAt(0) == '#') {
            u = u.slice(1);
        }
        // needs to handle query params from calls using complete url differently
        u = u.split("?");

        if(u.length > 1 && u[1].trim()) {
            $location.path(u[0]).search(u[1]);
        } else {
            $location.path(u[0]);
        }
    };

    self.localRedirectHome = (simulationId, appMode=null) => {
        self.localRedirect(
            self.defaultRouteName(appMode),
            {':simulationId': simulationId}
        );
    };

    self.newLocalWindow = (routeName, params, app) => {
        $window.open(self.formatLocal(routeName, params, app), '_blank');
    };

    self.newWindow = (routeNameOrUri, params) => {
        $window.open(_routeNameOrUri(routeNameOrUri, params), '_blank');
    };

    self.openSimulation = (app, localRoute, simId) => {
        self.newWindow(
            'simulationRedirect',
            {
                simulation_type: app,
                local_route: localRoute,
                simulation_id: simId,
            },
        );
    };

    _init();
    return self;
});

// cannot import authState factory, because of circular import with requestSender
SIREPO.app.factory('msgRouter', ($http, $interval, $q, $window, errorService, uri) => {
    let asyncMsgMethods = {};
    let cookiesSorted = null;
    let cookiesVerbatim = null;
    let needReply = {};
    let reqSeq = 1;
    const self = {};
    let socket = null;
    let socketRetryBackoff = 0;
    const toSend = [];

    const _appendBuffers = (wsreq, buffers) => {
        buffers.splice(0, 0, wsreq.msg);
        const f = new Uint8Array(buffers.reduce((a, b) => a + b.length, 0));
        let i = 0;
        for (const b of buffers) {
            f.set(b, i);
            i += b.length;
        }
        wsreq.msg = f;
    };

    const _cookiesChangedAndRedirect = () => {
        if (cookiesVerbatim === document.cookie) {
            return false;
        }
        const c = cookiesSorted;
        _saveCookies();
        // first time is null, and reordering is ok
        if (c === null || c === cookiesSorted) {
            return false;
        }
        srlog("cookies changed via another browser tab, reloading application");
        uri.globalRedirectRoot();
        return true;
    };

    const _protocolError = (header, content, wsreq, errorMsg) => {
        const e = "sirepo.msgRouter protocolError=" + (errorMsg || "invalid reply from server");
        srlog(
            e,
            header.kind === SIREPO.APP_SCHEMA.websocketMsg.kind.asyncMsg
                ? ` asyncMsgMethod={header.method}`
                : wsreq && wsreq.header ? ` wsreq={wsreq.header.reqSeq}`
                : "wsreq=null",
            " header=",
            header,
            " content=",
            content
        );
        if (wsreq) {
            wsreq.deferred.reject({
                data: {state: "error", error: e},
                status: 500,
            });
        }
    };

    const _reply = (blob) => {
        let [header, content] = msgpack.decodeMulti(blob);
        const wsreq = needReply[header.reqSeq];
        if (header.version !== SIREPO.APP_SCHEMA.websocketMsg.version) {
            _protocolError(header, content, wsreq, "invalid version");
            return;
        }
        if (header.kind === SIREPO.APP_SCHEMA.websocketMsg.kind.asyncMsg) {
            if (! header.method) {
                _protocolError(header, content, wsreq, "missing method in content");
            }
            else if (! (header.method in asyncMsgMethods) ){
                _protocolError(header, content, wsreq, `unregistered asyncMsg method=${header.method}`);
            }
            else {
                asyncMsgMethods[header.method](content);
            }
            return;
        }
        const _replyError = (reply) => {
            if (SIREPO.traceWS) {
                srlog(`wsreq#${wsreq.header.reqSeq} replyError:`, reply);
            }
            wsreq.deferred.reject(reply);
        };
        if (! wsreq) {
            _protocolError(header, content, null, "reqSeq not found");
            return;
        }
        delete needReply[header.reqSeq];
        if (header.kind === SIREPO.APP_SCHEMA.websocketMsg.kind.srException) {
            const n = content.routeName;
            const r = {data: {}};
            if (n === "httpException") {
                r.status = content.params.code;
            }
            else {
                r.data.state = "srException";
                r.data.srException = content;
            }
            _replyError(r);
            return;
        }
        if (header.kind !== SIREPO.APP_SCHEMA.websocketMsg.kind.httpReply) {
            _protocolError(header, content, wsreq, "invalid websocketMsg.kind");
            return;
        }
        const b = wsreq.responseType === "blob";
        if (content instanceof Uint8Array) {
            if (! b) {
                _protocolError(header, content, wsreq, "unexpected blob content");
                return;
            }
            content = new Blob([content]);
        }
        else if (b) {
            if (content.error) {
                _replyError({data: content});
                return;
            }
            _protocolError(header, content, wsreq, "expected blob content");
            return;
        }
        else if (wsreq.responseType === "json") {
            if (angular.isString(content)) {
                content = JSON.parse(content);
            }
            else {
                if (content.error) {
                    _replyError({data: content});
                }
                else {
                    _replyError({
                        data: {
                            error: "unknown reply type, expecting json",
                            content: content
                        }
                    });
                }
                return;
            }
        }
        if (SIREPO.traceWS) {
            srlog(`wsreq#${wsreq.header.reqSeq} reply:`, content);
        }
        wsreq.deferred.resolve({
            data: content,
            status: 200
        });
    };

    const _reqData = (data, wsreq, done) => {
        if (! (data instanceof FormData)) {
            done([data]);
            return;
        }
        var d = {};
        var f = null;
        for (const [k, v] of data.entries()) {
            if (v instanceof File) {
                if (f) {
                    throw new Error(`too many form fields ${f.file.name} and ${v.name}`);
                }
                f = {key: k, file: v};
            }
            else {
                d[k] = v;
            }
        }
        if (! f) {
            done([data]);
            return;
        }
        // a bit of sanity since we assume this on the server side
        if (f.key !== "file") {
            throw new Error("file form fields must be named 'file' name=" + f.key);
        }
        _reqDataFile(d, f.key, f.file, done);
    };

    const _reqDataFile = (data, key, file, done) => {
        var r = new FileReader();
        r.readAsArrayBuffer(file);
        r.onerror = (event) => {
            srlog("failed to read file=" + file.name, event);
            errorService.alertText('Failed to read file=' + file.name);
            return;
        };
        r.onloadend = () => {
            delete data[key];
            done([
                data,
                {filename: file.name, blob: new Uint8Array(r.result),},
            ]);
        };
    };

    const _saveCookies = () => {
        // Keep two versions for faster checking in _cookiesChangedAndRedirect
        cookiesVerbatim = document.cookie;
        cookiesSorted = cookiesVerbatim.split(/\s*;\s*/).sort().join('; ');
    };

    const _send = () => {
        //if already req_seq use that so server can know if it is a resend
        if (toSend.length <= 0) {
            return;
        }
        if (socket === null) {
            _socket();
            return;
        }
        if (socket.readyState !== 1) {
            return;
        }
        while (toSend.length > 0) {
            const wsreq = toSend.shift();
            needReply[wsreq.header.reqSeq] = wsreq;
            socket.send(wsreq.msg);
        }
    };

    const _socket = () => {
        if (socket !== null) {
            return;
        }
        if (_cookiesChangedAndRedirect()) {
            return;
        }
        const s = new WebSocket(
            new URL($window.location.href).origin.replace(/^http/i, "ws") + "/ws",
        );
        s.onclose = _socketError;
        s.onerror = _socketError;
        s.onmessage = _socketOnMessage;
        s.onopen = _socketOnOpen;
        socket = s;
    };

    const _socketError = (event) => {
        // close: event.code : short, event.reason : str, wasClean : bool
        // error: app specific
        socket = null;
        if (socketRetryBackoff <= 0) {
            socketRetryBackoff = 1;
            srlog("WebSocket failed: event=", event);
            if (! event.wasClean) {
                toSend.unshift(...Object.values(needReply));
                needReply = {};
            }
        }
        //TODO(robnagler) some type of set status to communicate connection lost
        $interval(_socket, socketRetryBackoff * 1000, 1);
        if (socketRetryBackoff < 60) {
            socketRetryBackoff *= 2;
        }
    };

    const _socketOnMessage = (event) => {
        event.data.arrayBuffer().then(
            (blob) => {_reply(blob);},
            (error) => {srlog("WebSocket.onmessage error=", error, " event=", event);}
        );
    };

    const _socketOnOpen = (event) => {
        socketRetryBackoff = 0;
        _send();
    };

    const _timeout = (wsreq) => {
        const i = toSend.indexOf(wsreq);
        if (i >= 0) {
            toSend.splice(i, 1);
            return;
        }
        delete needReply[wsreq.reqSeq];
        _protocolError(null, null, wsreq, "request timed out");
    };

    self.registerAsyncMsg = (methodName, callback) => {
        if (methodName in asyncMsgMethods) {
            throw new Error(`duplicate registerAsyncMsg methodName="{methodName}"`);
        }
        asyncMsgMethods[methodName] = callback;
    };

    self.send = (url, data, httpConfig) => {
        if (_cookiesChangedAndRedirect()) {
            // app will reload so return a fake promise
            return {then: () => {}};
        }
        if (! SIREPO.authState.uiWebSocket) {
            return data ? $http.post(url, data, httpConfig)
                : $http.get(url, httpConfig);
        }
        let wsreq = {
            deferred: $q.defer(),
            header: {
                kind: SIREPO.APP_SCHEMA.websocketMsg.kind.httpRequest,
                reqSeq: reqSeq++,
                uri: decodeURIComponent(url),
                version: SIREPO.APP_SCHEMA.websocketMsg.version,
            },
            ...httpConfig,
        };
        wsreq.msg = msgpack.encode(wsreq.header);
        if (wsreq.timeout) {
            wsreq.timeout.then(() => {_timeout(wsreq);});
        }
        const c = (buffers) => {
            if (buffers) {
                _appendBuffers(
                    wsreq,
                    buffers.map((b) => (new msgpack.Encoder()).encodeSharedRef(b)),
                );
            }
            toSend.push(wsreq);
            _send();
        };
        if (SIREPO.traceWS) {
            srlog(`wsreq#${wsreq.header.reqSeq} send:`, wsreq.header.uri, data);
        }
        if (data === null) {
            c();
        }
        else {
            _reqData(data, wsreq, c);
        }
        return wsreq.deferred.promise;
    };

    self.updateCookies = (changeOp) => {
        if (_cookiesChangedAndRedirect()) {
            return false;
        }
        changeOp();
        _saveCookies();
        return true;
    };

    return self;

});

SIREPO.app.factory('requestSender', function(browserStorage, errorService, utilities, msgRouter, uri, $location, $injector, $interval, $q, $rootScope) {
    var self = {};
    var HTML_TITLE_RE = new RegExp('>([^<]+)</', 'i');
    var IS_HTML_ERROR_RE = new RegExp('^(?:<html|<!doctype)', 'i');
    const LOGIN_ROUTE_NAME = 'login';
    let LOGIN_URI = null;
    var REDIRECT_RE = new RegExp('window.location = "([^"]+)";', 'i');
    var SR_EXCEPTION_RE = new RegExp('/\\*sr_exception=(.+)\\*/');
    var listFilesData = {};
    const storageKey = "previousRoute";

    function checkLoginRedirect(event, route) {
        if (! SIREPO.authState.isLoggedIn
            || SIREPO.authState.needCompleteRegistration
            // Any controller that has 'login' in it will stay on page
            || (route.controller && route.controller.toLowerCase().indexOf('login') >= 0)
        ) {
            return;
        }
        let p = browserStorage.getString(storageKey);
        if (! p) {
            return;
        }
        browserStorage.removeItem(storageKey);
        p = p.split(' ');
        if (p[0] !== SIREPO.APP_SCHEMA.simulationType) {
            // wrong app so ignore
            return;
        }
        const r = uri.firstComponent(decodeURIComponent(p[1]));
        // After a reload from a login. Only redirect if
        // the route is different. The firstComponent is
        // always unique in our routes.
        if (uri.firstComponent($location.url()) !== r) {
            event.preventDefault();
            uri.localRedirect(decodeURIComponent(p[1]));
        }
    }

    function defaultErrorCallback(data, status) {
        const err = SIREPO.APP_SCHEMA.customErrors[status];
        if (err && err.route) {
            uri.localRedirect(err.route);
        }
        else {
            errorService.alertText('Request failed: ' + data.error);
        }
    }

    function saveLoginRedirect() {
        const u = $location.url();
        if (u == LOGIN_URI) {
            return true;
        }
        browserStorage.setString(
            storageKey,
            SIREPO.APP_SCHEMA.simulationType + ' ' + encodeURIComponent(u),
        );
    }

    function sendWithSimulationFields(url, appState, successCallback, data, errorCb) {
        data.simulationId = data.simulationId || appState.models.simulation.simulationId;
        data.simulationType = SIREPO.APP_SCHEMA.simulationType;
        self.sendRequest(url, successCallback, data, errorCb);
    }

    self.clearListFilesData = function() {
        listFilesData = {};
    };

    self.downloadRunFileUrl = (appState, params) => {
        return self.formatUrl(
            'downloadRunFile',
            {
                simulation_id: appState.models.simulation.simulationId,
                simulation_type: SIREPO.APP_SCHEMA.simulationType,
                frame: SIREPO.nonDataFileFrame,
                ...params
            },
        );
    };

    self.getListFilesData = function(name) {
        return listFilesData[name];
    };

    self.handleSRException = function(srException, errorCallback) {
        const e = srException;
        if (e.routeName == "httpRedirect") {
            uri.globalRedirect(e.params.uri, undefined);
            return;
        }
        if (e.routeName == "serverUpgraded" && e.params && e.params.reason in SIREPO.refreshModalMap) {
            $(`#${SIREPO.refreshModalMap[e.params.reason].modal}`).modal('show');
            return;
        }
        if (e.params && e.params.isModal && e.routeName.toLowerCase().includes('sbatch')) {
            e.params.errorCallback = errorCallback;
            $rootScope.$broadcast(
                'showSbatchLoginModal',
                {
                    errorCallback: errorCallback,
                    srExceptionParams: e.params,
                },
            );
            return;
        }
        if (e.routeName == LOGIN_ROUTE_NAME) {
            saveLoginRedirect();
            // if redirecting to login, but the app thinks it is already logged in,
            // then force a logout to avoid a login loop
            if (SIREPO.authState.isLoggedIn) {
                uri.globalRedirect('authLogout');
                return;
            }
        }
        uri.localRedirect(e.routeName, e.params);
        return;
    };

    self.loadListFiles = function(name, params, callback) {
        if (listFilesData[name] || listFilesData[name + ".loading"]) {
            if (callback) {
                callback(listFilesData[name]);
            }
            return;
        }
        listFilesData[name + ".loading"] = true;
        msgRouter.send(
            uri.format('listFiles'),
            params,
            {}
        ).then(
            function(response) {
                var data = response.data;
                listFilesData[name] = data;
                delete listFilesData[name + ".loading"];
                if (callback) {
                    callback(data);
                }
            },
            function() {
                srlog(params, ' loadListFiles failed!');
                delete listFilesData[name + ".loading"];
                if (! listFilesData[name]) {
                    // if loading fails, use an empty list to prevent load requests on each digest cycle, see #1339
                    listFilesData[name] = [];
                }
            },
        );
    };
    self.sendAnalysisJob = function(appState, callback, data) {
        sendWithSimulationFields('analysisJob', appState, callback, data);
    };

    self.sendDownloadRunFile = (appState, routeParams, successCb, errorCb) => {
        // When other types are requested, we can add them, e.g. blob or txt.
        if (routeParams.suffix !== "json") {
            throw new Error("invalid downloadDataFile suffix=" + (routeParams.suffix || ""));
        }
        self.sendRequest(
            self.downloadRunFileUrl(appState, routeParams),
            successCb,
            routeParams.suffix === "json" ? {responseType: "json"} : {},
            errorCb || (reply => {throw new Error(reply.error);})
        );
    };

    self.sendGlobalResources = function(appState, callback, data, errorCb) {
        sendWithSimulationFields('globalResources', appState, callback, data, errorCb);
    };

    self.sendRequest = function(urlOrParams, successCallback, requestData, errorCallback) {
        const blobResponse = (response, successCallback, thisErrorCallback) => {
            // These two content-types are what the server might return with a 200.
            const r = new RegExp('^(application/json|text/html)$');
            let d = response.data;
            if (d instanceof Blob) {
                successCallback(d);
                return;
            }
            if (r.test(d.type) || /^text/.test(d.type)) {
                d.text().then((text) => {d = text;});
            }
            thisErrorCallback({
                ...response,
                data: d,
            });
        };
        if (! errorCallback) {
            errorCallback = defaultErrorCallback;
        }
        if (! successCallback) {
            successCallback = function () {};
        }
        var url = angular.isString(urlOrParams) && urlOrParams.indexOf('/') >= 0
            ? urlOrParams
            : uri.format(urlOrParams);
        var timeout = $q.defer();
        var interval, t;
        var timed_out = false;
        const httpConfig = {timeout: timeout.promise};
        if (requestData && requestData.responseType) {
            httpConfig.responseType = requestData.responseType;
            delete requestData.responseType;
        }
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
        var req = msgRouter.send(url, requestData, httpConfig);
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
            else if (status === -1) {
                msg = 'Server unavailable';
            }
            else if (SIREPO.APP_SCHEMA.customErrors[status]) {
                msg = SIREPO.APP_SCHEMA.customErrors[status].msg;
            }
            if (angular.isString(data) && IS_HTML_ERROR_RE.exec(data)) {
                // Try to parse javascript-redirect.html
                var m = SR_EXCEPTION_RE.exec(data);
                if (m) {
                    // if this is invalid, will throw SyntaxError, which we
                    // cannot handle so it will just show up as error.
                    self.handleSRException(JSON.parse(m[1]), errorCallback);
                    return;
                }
                m = REDIRECT_RE.exec(data);
                if (m) {
                    if (m[1].indexOf('#/error') <= -1) {
                        srlog('javascriptRedirectDocument', m[1]);
                        uri.globalRedirect(m[1], undefined);
                        return;
                    }
                    srlog('javascriptRedirectDocument: staying on page', m[1]);
                    // set explicitly so we don't log below
                    data = {error: 'server error'};
                }
                else {
                    // HTML document with error msg in title
                    m = HTML_TITLE_RE.exec(data);
                    if (m) {
                        srlog('htmlErrorDocument', m[1]);
                        data = {error: m[1]};
                    }
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
                self.handleSRException(data.srException, errorCallback);
                return;
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
            errorCallback(data, status, response.data);
        };
        req.then(
            function(response) {
                if (httpConfig.responseType === 'blob') {
                    $interval.cancel(interval);
                    blobResponse(response, successCallback, thisErrorCallback);
                    return;
                }
                var data = response.data;
                // POSIT: isObject returns true for []
                if (! angular.isObject(data) || data.state === 'srException') {
                    thisErrorCallback(response);
                    return;
                }
                $interval.cancel(interval);
                successCallback(data, response.status);
            },
            thisErrorCallback,
        );
    };

    self.sendRpn = utilities.debounce(
        (appState, callback, data) => {
            data.variables = appState.models.rpnVariables;
            self.sendStatefulCompute(appState, callback, data);
        },
        SIREPO.debounce_timeout
    );

    self.sendStatefulCompute = function(appState, callback, data, errorCb) {
        sendWithSimulationFields('statefulCompute', appState, callback, data, errorCb);
    };

    self.sendStatelessCompute = function(appState, successCallback, data, options={}) {
        const maybeSetPanelState = (state) => {
            if (! options.panelState) {
                return;
            }
            options.panelState.maybeSetState(options.modelName, state);
        };

        const onError = (data) => {
            srlog('statelessCompute error: ', data.error);
            if (options.onError) {
                options.onError(data);
                return;
            }
            maybeSetPanelState('error');
        };

        maybeSetPanelState('loading');
        sendWithSimulationFields(
            'statelessCompute',
            appState,
            (data) => {
                if (data.state === 'error') {
                    onError(data);
                    return;
                }
                maybeSetPanelState('loadingDone');
                successCallback(data);
            },
            data,
            onError
        );
    };

    // Deprecated interface
    self.defaultRouteName = uri.defaultRouteName;
    self.formatUrlLocal = uri.formatLocal;
    self.formatUrl = uri.format;
    self.newLocalWindow = uri.newLocalWindow;
    self.newWindow = uri.newWindow;
    self.openSimulation = uri.openSimulation;
    self.globalRedirect = uri.globalRedirect;
    self.globalRedirectRoot = uri.globalRedirectRoot;
    self.localRedirect = uri.localRedirect;
    self.localRedirectHome = uri.localRedirectHome;
    self.isRouteParameter = uri.isRouteParameter;

    $rootScope.$on('$routeChangeStart', checkLoginRedirect);
    LOGIN_URI = uri.formatLocal(LOGIN_ROUTE_NAME).slice(1);
    return self;
});

SIREPO.app.factory('simulationQueue', function($rootScope, $interval, requestSender) {
    var self = {};
    var runQueue = [];

    function addItem(report, models, responseHandler, qMode) {
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
                forceRun: qMode === 'persistent',
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

    self.addTransientItem = function(report, models, responseHandler) {
        return addItem(report, models, responseHandler, 'transient');
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

    self.stopRunStatus = (qi) => {
        cancelInterval(qi);
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


SIREPO.app.factory('persistentSimulation', function(simulationQueue, appState, authState, frameCache, stringsService, $interval) {
    var self = {};
    const ELAPSED_TIME_INTERVAL_SECS = 1;

    self.initSimulationState = function(controller) {
        var state = {
            controller: controller,
            dots: '.',
            isReadyForModelChanges: false,
            model: controller.simComputeModel || appState.appService.computeModel(controller.simAnalysisModel || null),
            percentComplete: 0,
            queueState: null,
            simulationQueueItem: null,
            timeData: {},
        };

        function clearSimulation() {
            simulationQueue.removeItem(state.simulationQueueItem);
            state.simulationQueueItem = null;
        }

        function handleStatus(data) {
            setSimulationStatus(data);
            if (state.isStopped()) {
                state.timeData.elapsedTime = Math.max(
                    state.timeData.elapsedTime || 0, data.elapsedTime
                );
            }
            else {
                startElapsedTimeTimer(data.elapsedTime);
            }
            if (data.hasOwnProperty('percentComplete')) {
                state.percentComplete = data.percentComplete;
            }
            if (data.hasOwnProperty('queueState')) {
                state.queueState = data.queueState;
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
            controller.simHandleStatus(data);
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
            if (state.model in appState.models.simulationStatus) {
                delete appState.models.simulationStatus[state.model].alert;
                delete appState.models.simulationStatus[state.model].canceledAfterSecs;
            }
            data.report = state.model;
            appState.models.simulationStatus[state.model] = angular.extend(
                {}, appState.models.simulationStatus[state.model], data
            );
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

        function startElapsedTimeTimer(elapsedTime) {
            var d = state.timeData;
            if (d.elapsedTimeTimer) {
                return;
            }
            d.elapsedTime = elapsedTime;
            d.elapsedTimeTimer = $interval(
                function() {
                    if (! state.simulationQueueItem || state.simulationQueueItem.qState == 'removing') {
                        $interval.cancel(d.elapsedTimeTimer);
                        d.elapsedTimeTimer = null;
                        return;
                    }
                    state.timeData.elapsedTime += ELAPSED_TIME_INTERVAL_SECS;
                },
                ELAPSED_TIME_INTERVAL_SECS * 1000
            );
        }


        state.getAlert = function() {
            return simulationStatus().alert;
        };

        state.getCanceledAfterSecs = function() {
            return simulationStatus().canceledAfterSecs;
        };

        state.getDbUpdateTime = function() {
            return simulationStatus().dbUpdateTime;
        };

        state.getError = function() {
            return simulationStatus().error;
        };

        state.getFrameCount = function() {
            return frameCache.getFrameCount();
        };

        state.getPercentComplete = function() {
            if (state.percentComplete) {
                return state.percentComplete;
            }
            if (state.isInitializing() || state.isStatePending()) {
                return 100;
            }
            return state.percentComplete;
        };

        state.getQueueState = function() {
            if (state.queueState) {
                return stringsService.ucfirst(state.queueState);
            }
            return state.stateAsText();
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

        state.isStateCompleted = function() {
            return simulationStatus().state == 'completed';
        };

        state.isStateError = function() {
            return simulationStatus().state == 'error';
        };

        state.isStatePending = function() {
            return simulationStatus().state == 'pending';
        };

        state.isStatePurged = function() {
            return simulationStatus().state == 'job_run_purged';
        };

        state.isStateRunning = function() {
            return simulationStatus().state == 'running';
        };

        state.isStopped = function() {
            return ! state.isProcessing();
        };

        state.isWaitingOnAnotherSimulation = function() {
            return state.jobStatusMessage() === 'Waiting for another simulation to complete';
        };

        state.jobStatusMessage = function() {
            return simulationStatus().jobStatusMessage;
        };

        state.resetSimulation = function() {
            setSimulationStatus({state: 'missing'});
            frameCache.setFrameCount(0);
            appState.whenModelsLoaded(controller.simScope, runStatus);
        };

        state.runSimulation = function() {
            if (state.isStateRunning()) {
                return;
            }
            //TODO(robnagler) should be part of simulationStatus
            frameCache.setFrameCount(0);
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
            frameCache.setFrameCount(0);
            simulationStatus().state = 'pending';
            appState.saveChanges(models, state.runSimulation);
        };

        state.showJobSettings = function () {
            return authState.jobRunModeMap.sbatch &&
                appState.models[state.model] &&
                appState.models[state.model].jobRunMode ? 1 : 0;
        };

        state.stateAsText = function() {
            if (state.isStateError()) {
                var e = state.getError();
                if (e) {
                    let m = e.split(/[\n\r]+/)[0];
                    if (m.toLowerCase().includes('504')){
                        return 'Timeout Error. Please contact support@radiasoft.net if the problem persists';
                    }
                    return 'Error: ' + m;
                }
            }
            return stringsService.ucfirst(simulationStatus().state);
        };

        state.stopRunStatus = () => {
            simulationQueue.stopRunStatus(state.simulationQueueItem);
        };

        state.resetSimulation();
        controller.simScope.$on('$destroy', clearSimulation);
        controller.simScope.$on('sbatchLoginSuccess', function() {
            state.resetSimulation();
        });
        return state;
    };
    return self;
});

SIREPO.app.provider('$exceptionHandler', {
    $get: function(errorService) {
        return errorService.exceptionHandler;
    }
});

SIREPO.app.factory('errorService', function($log, $window) {
    var self = this;
    var alertText = null;

    self.exceptionHandler = function(exception, cause) {
        // preserve the default behaviour which will log the error
        // to the console, and allow the application to continue running.
        $log.error.apply($log, arguments);
        // now try to log the error to the server side.
        try {
            // use AJAX (in this example jQuery) and msgRouter
            var message = exception ? String(exception) : '';
            cause = cause ? String(cause) : '';
            self.logToServer(
                'clientException',
                message || '<no message>',
                cause || '<no cause>',
                exception.stack || '<no stack>'
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
            //POSIT: schema-common.json route.errorLogging,
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
    let simPaths = {};
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
        return self.getUserFolders()
            .map(item => self.pathName(item))
            .sort((a, b) => a.localeCompare(b));
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
                let sim = data[i].simulation;
                item.name = sim.name;
                item.notes = sim.notes;
                item.lastModified = sim.lastModified;
            }
            else {
                self.addToTree(data[i].simulation);
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
                    if (! folder.lastModified || item.lastModified > folder.lastModified) {
                        folder.lastModified = item.lastModified;
                    }
                }
                else {
                    folder = {
                        name: search,
                        parent: currentFolder,
                        isFolder: true,
                        children: [],
                        lastModified: item.lastModified,
                    };
                    currentFolder.children.push(folder);
                }
                currentFolder = folder;
            }

            newItem = {
                appMode: item.appMode,
                canExport: SIREPO.APP_SCHEMA.constants.canExportArchive,
                isExample: item.isExample,
                lastModified: item.lastModified,
                name: item.name,
                notes: item.notes,
                path: `${item.folder === '/' ? '' : item.folder + '/'}${item.name}`,
                parent: currentFolder,
                simulationId: item.simulationId,
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

    self.getSimPaths = () => simPaths;

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

    function getSimPathsFromTree() {
        return flatTree
            .filter(item => ! item.isFolder)
            .map(item => {
                return {
                    label: item.path,
                    value: item,
                };
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
        simPaths = getSimPathsFromTree();
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

    self.updateSim = sim => {
        self.removeSimFromTree(sim.simulationId);
        self.addToTree(sim);
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
        if (requestSender.isRouteParameter(name, 'simulationId')) {
            return {
                ':simulationId': appState.isLoaded() ? appState.models.simulation.simulationId : '',
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
                'Sirepo',
            ],
            function(n){ return n; })
            .join(' - ');
    };

    self.revertToOriginal = function(applicationMode, name) {
        if (! appState.isLoaded()) {
            return;
        }
        appState.deleteSimulation(
            appState.models.simulation.simulationId,
            function() {
                requestSender.globalRedirect(
                    'findByNameWithAuth',
                    {
                        simulation_name: name,
                        simulation_type: SIREPO.APP_SCHEMA.simulationType,
                        application_mode: applicationMode,
                    }
                );
            }
        );
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
        requestSender.localRedirect(SIREPO.APP_SCHEMA.appDefaults.route);
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

SIREPO.app.controller('LoginController', function (authService, authState, requestSender) {
    var self = this;
    self.authService = authService;

    if (authState.isLoggedIn && ! authState.isGuestUser && ! authState.needCompleteRegistration) {
        requestSender.localRedirect(SIREPO.APP_SCHEMA.appDefaults.route);
        return;
    }

    if (authState.visibleMethods.length === 1) {
        requestSender.localRedirect(
            'loginWith',
            {':method': authState.visibleMethods[0]}
        );
        return;
    }
});

SIREPO.app.controller('LoginWithController', function (authState, errorService, requestSender, $route) {
    var self = this;
    var m = $route.current.params.method || '';
    self.showWarning = false;
    self.warningText = '';
    self.method = m;
    if (m == 'guest') {
        self.msg = 'Creating your account. Please wait...';
        requestSender.sendRequest(
            {
                routeName: 'authGuestLogin',
                simulation_type: SIREPO.APP_SCHEMA.simulationType
            },
            function (data) {
                authState.handleLogin(data, self);
            }
        );
    }
    else if (m == 'email') {
        // handled by the emailLogin directive
    }
    else if (m == 'ldap') {
        // created ldapLogin directive
    }
    else {
        self.msg = '';
        errorService.alertText('Incorrect or invalid login method: ' + (m || '<none>'));
        requestSender.localRedirect('login');
    }
});

SIREPO.app.controller('LoginConfirmController', function (authState, requestSender, $route) {
    var self = this;
    var p = $route.current.params;
    self.data = {};
    self.showWarning = false;
    self.warningText = '';

    if ($route.current.templateUrl.indexOf('complete-registration') >= 0) {
        if (! SIREPO.authState.isLoggedIn) {
            requestSender.localRedirect('login');
            return;
        }
        if (! SIREPO.authState.needCompleteRegistration) {
            requestSender.localRedirect(SIREPO.APP_SCHEMA.appDefaults.route);
            return;
        }
        self.submit = function() {
            requestSender.sendRequest(
                'authCompleteRegistration',
                function (data) {
                    authState.handleLogin(data, self);
                },
                {
                    displayName: self.data.displayName,
                    simulationType: SIREPO.APP_NAME
                }
            );
        };
        return;
    }
    self.needCompleteRegistration = parseInt(p.needCompleteRegistration);
    self.submit = function() {
        requestSender.sendRequest(
            {
                routeName: 'authEmailAuthorized',
                '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                '<token>': p.token,
            },
            function (data) {
                authState.handleLogin(data, self);
            },
            {
                token: p.token,
                displayName: self.data.displayName,
            }
        );
    };
    return;
});

SIREPO.app.controller('LoginFailController', function (requestSender, stringsService, $route, $sce) {
    var self = this;
    var t = $sce.getTrustedHtml(stringsService.ucfirst($route.current.params.method || ''));
    var r = $route.current.params.reason || '';
    var login_text = function(text) {
        return '<a href="' + requestSender.formatUrlLocal('login')
             + '">' + text + '</a>';
    };
    var l = login_text('Please try to login again.');
    if (r == 'deprecated' || r == 'invalid-method') {
        self.msg = 'You can no longer login with ' + t + '. ' + l;
    }
    else if (r == 'email-token') {
        self.msg = 'You clicked on an expired link. ' + l;
    }
    else if (r == 'oauth-state') {
        self.msg = 'Something went wrong with ' + t + '. ' + l;
    }
    else if (r == 'guest-expired') {
        self.msg = 'Guest Access Expired: To continue using Sirepo '
            + 'we require you to authenticate using email.'
            + 'You will use this email to access your work going forward. '
            + login_text('Please click here to authenticate.');
    }
    else if (r == 'account-deleted') {
        self.msg = 'Something went wrong with ' + t + '. ' + l;
    }
    else {
        self.msg = 'Unexpected error. ' + l;
    }
});

SIREPO.app.controller('FindByNameController', function (appState, requestSender, $route) {
    var self = this;
    self.simulationName = $route.current.params.simulationName;
    appState.listSimulations(
        function() {
            // authenticated listSimulations successfully, now go to the URL
            requestSender.globalRedirect(
                'findByNameWithAuth',
                {
                    '<simulation_name>': self.simulationName,
                    '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                    '<application_mode>': $route.current.params.applicationMode,
                }
            );
        });
});

SIREPO.app.controller('ServerUpgradedController', function (errorService, requestSender) {
    var self = this;

    errorService.alertText('Sirepo has been upgraded, and your application has been restarted');
    requestSender.globalRedirectRoot();
});

SIREPO.app.controller('SimulationsController', function (appState, browserStorage, errorService, fileManager, panelState, requestSender, stringsService, $location, $rootScope, $scope) {
    var self = this;
    const storageKey = "iconView";
    self.stringsService = stringsService;
    $rootScope.$broadcast('simulationUnloaded');
    self.importText = SIREPO.APP_SCHEMA.strings.importText;
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
            function(data) {
                if (! $scope.$parent) {
                    // callback may occur after scope has been destroyed
                    // if the user has navigated off the simulations page
                    return;
                }
                self.isWaitingForList = false;
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

    function updateSelectedItem(op) {
        appState.loadModels(
            self.selectedItem.simulationId,
            function() {
                op();
                appState.saveQuietly('simulation');
                appState.autoSave(data => {
                    if (data.models) {
                        fileManager.updateSim(data.models.simulation);
                    }
                    clearModels();
                });
                self.selectedItem = null;
            });
    }

    self.canDelete = function(item) {
        if (item.isFolder) {
            return item.children.length === 0;
        }
        return ! item.isExample;
    };

    self.canDownloadInputFile = function() {
        return SIREPO.APP_SCHEMA.constants.canDownloadInputFile;
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
            requestSender.localRedirectHome(item.simulationId, item.appMode);
        }
    };

    self.pathName = function(folder) {
        return fileManager.pathName(folder);
    };

    self.pythonSourceUrl = function(item) {
        return panelState.pythonSourceUrl(item.simulationId);
    };

    self.exportArchiveUrl = function(item, extension) {
        return panelState.exportArchiveUrl(item.simulationId, `${item.name}.${extension}`);
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

    self.selectedItemType = function() {
        if (self.selectedItem && self.selectedItem.isFolder) {
            return 'Folder';
        }
        return 'Simulation';
    };

    self.getSimPaths = fileManager.getSimPaths;

    self.toggleIconView = function() {
        self.isIconView = ! self.isIconView;
        browserStorage.setBoolean(storageKey, self.isIconView);
    };

    self.isIconView = browserStorage.getBoolean(storageKey, true);

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
            if (name.search(/[A-Z]{2}/) == -1) {
                // format camel case as words
                name = name.replace(/([a-z])([A-Z])/g, '$1 $2');
            }
        }
        return name;
    };
});

// only uses angularjs $cookies for removing old cookies, which
// were encoded by $cookies.
SIREPO.app.factory('browserStorage', function($cookies, msgRouter) {
    const self = {};

    const _updateOld = () => {
        const toDelete = [];

        const _v1 = () => {
            const toCheck = [
                'net.sirepo.first_visit',
                'net.sirepo.get_started_notify',
                'net.sirepo.sim_list_view',
            ];

            for (let n of toCheck) {
                var c = $cookies.get(n);
                if (angular.isDefined(c)) {
                    toDelete.push(n);
                }
            }
        };

        const _v2 = () => {
            const incoming = $cookies.get('sirepo_cookie_js');
            if (! incoming) {
                return;
            }
            toDelete.push('sirepo_cookie_js');
            // only ones we care about
            const remap = {
                strt: 'getStarted',
                lv: 'iconView',
            };
            for (let c of incoming.split('|')) {
                let [k, v] = c.split(':');
                if (! (k && v) ) {
                    continue;
                }
                for (let e of v.split(';')) {
                    if (e && e.charAt(0) === 'v' && remap[k]) {
                        const b = e.split('=')[1];
                        // originally had an "i" for true on getStarted,
                        // and we are inverting getStarted (true => show)
                        self.setBoolean(remap[k], b === 'true' || b !== 'i' && b !== 'false');
                    }
                }
            }
        };
        _v1();
        _v2();
        msgRouter.updateCookies(() => {
            for (let k of toDelete) {
                $cookies.remove(k);
            }
        });
    };

    self.getBoolean = (name, defaultValue=false) => {
        const s = self.getString(name, null);
        if (s === null) {
             return defaultValue;
        }
        if (s === 'true') {
            return true;
        }
        if (s === 'false') {
            return false;
        }
        srlog(`browserStorage.getBoolean(${name}) invalid value=${s}`);
        self.removeItem(name);
        return defaultValue;
    };

    self.getString = (name, defaultValue=null) => {
        const rv = localStorage.getItem(name);
        return rv == null ? defaultValue : rv;
    };

    self.removeItem = (name) => {
        localStorage.removeItem(name);
    };

    self.setBoolean = (name, value) => {
        self.setString(name, value ? 'true' : 'false');
    };

    self.setString = (name, value) => {
        localStorage.setItem(name, value);
    };

    _updateOld();
    return self;
});

SIREPO.app.factory('asyncMsgSetCookies', ($cookies, msgRouter) => {
    const self = {};
    const asyncMsgMethod = (content) => {
        msgRouter.updateCookies(() => {
            for (let c of content) {
                document.cookie = c;
            }
        });
    };

    msgRouter.registerAsyncMsg('setCookies', asyncMsgMethod);
    return self;
});
