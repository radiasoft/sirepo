'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="LatticeBeamlineList" data-ng-class="fieldClass">',
          '<div data-lattice-beamline-list="" data-model="model" data-field="field"></div>',
        '</div>',
        '<div data-ng-switch-when="OptionalLatticeBeamlineList" data-ng-class="fieldClass">',
          '<div data-lattice-beamline-list="" data-model="model" data-field="field" data-is-optional="true"></div>',
        '</div>',
        '<div data-ng-switch-when="RPNBoolean" data-ng-class="fieldClass">',
          '<div data-rpn-boolean="" data-model="model" data-field="field"></div>',
        '</div>',
        '<div data-ng-switch-when="RPNValue">',
          '<div data-rpn-editor=""></div>',
        '</div>',
        '<div data-ng-switch-when="OptionalRPNValue">',
          '<div data-rpn-editor=""></div>',
        '</div>',
    ].join('');
});

SIREPO.app.factory('latticeService', function(appState, panelState, rpnService, utilities, validationService, $rootScope) {
    var self = {};
    var COMMAND_PREFIX = 'command_';
    self.activeBeamlineId = null;
    self.deleteVarWarning = '';
    self.includeCommandNames = false;
    self.wantRpnVariables = SIREPO.APP_SCHEMA.model.rpnVariable ? true : false;

    //TODO(pjm): share with template/elegant.py _PLOT_TITLE
    var plotTitle = {
        'x-xp': 'Horizontal',
        'x-px': 'Horizontal',
        'Y-T': 'Horizontal',
        'y-yp': 'Vertical',
        'y-py': 'Vertical',
        'Z-P': 'Vertical',
        'x-y': 'Cross-section',
        'Y-Z': 'Cross-section',
        't-p': 'Longitudinal',
        'z-zp': 'Longitudinal',
        'z-pz': 'Longitudinal',
    };

    function elementNameInvalidMsg(newName) {
        return newName == '' ? '' : newName + ' already exists';
    }

    function elementNameValidator(currentName) {
        var names = self.elementNameMap();
        return function(newNameV) {
            if (newNameV == currentName) {
                return true;
            }
            return ! names[newNameV];
        };
    }

    function fixModelName(modelName) {
        var m = appState.models[modelName];
        // remove invalid characters
        m.name = m.name.replace(SIREPO.lattice.invalidElementName || /[\s#*'",]/g, '');
        return;
    }

    function showDeleteWarning(type, element, beamlines) {
        var names = {};
        for (var i = 0; i < beamlines.length; i++) {
            names[self.elementForId(beamlines[i]).name] = true;
        }
        names = Object.keys(names).sort();
        var idField = type == 'elements' ? '_id' : 'id';
        self.deleteWarning = {
            type: type,
            element: element,
            typeName: type == 'elements' ? 'Element' : 'Beamline',
            name: self.elementForId(element[idField]).name,
            beamlineName: Object.keys(names).length > 1
                ? ('beamlines (' + names.join(', ') + ')')
                : ('beamline ' + names[0]),
        };
        $(beamlines.length ? '#sr-element-in-use-dialog' : '#sr-delete-element-dialog').modal('show');
    }

    function sortBeamlines() {
        appState.models.beamlines.sort(function(a, b) {
            return a.name.localeCompare(b.name);
        });
    }

    function sortElements() {
        appState.models.elements.sort(function(a, b) {
            var res = a.type.localeCompare(b.type);
            if (res === 0) {
                res = a.name.localeCompare(b.name);
            }
            return res;
        });
    }

    function updateModels(name, idField, containerName, sortMethod) {
        // update element/elements or beamline/beamlines
        var m = appState.models[name];
        var foundIt = false;
        for (var i = 0; i < appState.models[containerName].length; i++) {
            var el = appState.models[containerName][i];
            if (m[idField] == el[idField]) {
                appState.models[containerName][i] = m;
                foundIt = true;
                break;
            }
        }
        if (! foundIt) {
            if (self.elementNameMap()[m.name]) {
                m.name = self.uniqueNameForType(m.name + '-');
            }
            appState.models[containerName].push(m);
        }
        sortMethod();
        // process this outside of the current digest cycle, allows lattice to update from model
        panelState.waitForUI(function() {
            appState.removeModel(name);
            appState.saveChanges(containerName);
        });
    }

    self.COMMAND_PREFIX = COMMAND_PREFIX;

    self.addToBeamline = function(item) {
        self.getActiveBeamline().items.push(item.id || item._id);
        appState.saveChanges('beamlines');
    };

    self.angleFormat = function(angle) {
        var degrees = self.radiansToDegrees(rpnService.getRpnValue(angle));
        degrees = Math.round(degrees * 10) / 10;
        degrees %= 360;
        return degrees.toFixed(1);
    };

    self.arcLength = function(angle, length) {
        return angle * length / (2 * Math.sin(angle / 2));
    };

    self.bunchReportHeading = function(modelKey) {
        if (! appState.isLoaded()) {
            return;
        }
        var bunch = appState.models[modelKey];
        if (! bunch) {
            return '';
        }
        var key = bunch.x + '-' + bunch.y;
        return (plotTitle[key] || (bunch.x + ' / ' + bunch.y)) + ' Phase Space';
    };

    self.commandModelName = function(type) {
        return COMMAND_PREFIX + type;
    };

    self.createElement = function(type) {
        var model = self.getNextElement(type);
        appState.setModelDefaults(model, type);
        self.editElement(type, model);
    };

    self.deleteElement = function() {
        var type = self.deleteWarning.type;
        var element = self.deleteWarning.element;
        self.deleteWarning = null;
        var idField = type == 'elements' ? '_id' : 'id';
        for (var i = 0; i < appState.models[type].length; i++) {
            var el = appState.models[type][i];
            if (el[idField] == element[idField]) {
                var saveModelNames = [type];
                if(type === 'beamlines' && el[idField] == appState.models.simulation.visualizationBeamlineId) {
                    appState.models.simulation.visualizationBeamlineId = self.activeBeamlineId;
                    saveModelNames.push('simulation');
                }
                appState.models[type].splice(i, 1);
                appState.saveChanges(saveModelNames);
                $rootScope.$broadcast('elementDeleted', type, element);
                return;
            }
        }
        return;
    };

    self.editElement = function(type, item) {
        appState.models[type] = item;
        self.setValidator(type, item);
        panelState.showModalEditor(type);
    };

    self.elementNameMap = function() {
        var res = {};
        var containers = ['elements', 'beamlines'];
        if (self.includeCommandNames) {
            containers.push('commands');
        }
        containers.forEach(function(containerName) {
            var container = appState.models[containerName] || [];
            for (var i = 0; i < container.length; i++) {
                res[container[i].name] = 1;
            }
        });
        return res;
    };

    self.degreesToRadians = function(v) {
        return v * Math.PI / 180;
    };

    self.deleteElementPrompt = function(type, element) {
        var idField = type == 'elements' ? '_id' : 'id';
        var beamlines = self.getBeamlinesWhichContainId(element[idField]);
        showDeleteWarning(type, element, beamlines);
    };

    self.editBeamline = function(beamline, updateNoWait) {
        self.activeBeamlineId = beamline.id;
        appState.models.simulation.activeBeamlineId = beamline.id;
        if (! appState.models.simulation.visualizationBeamlineId) {
            appState.models.simulation.visualizationBeamlineId = beamline.id;
        }
        appState.saveChanges('simulation');
        $rootScope.$broadcast('activeBeamlineChanged', updateNoWait);
    };

    self.elementForId = function(id, models) {
        models = models || appState.models;
        var i;
        id = Math.abs(id);
        for (i = 0; i < models.beamlines.length; i++) {
            var b = models.beamlines[i];
            if (b.id == id) {
                return b;
            }
        }
        for (i = 0; i < models.elements.length; i++) {
            var e = models.elements[i];
            if (e._id == id) {
                return e;
            }
        }
        return null;
    };

    self.getActiveBeamline = function() {
        return self.elementForId(self.activeBeamlineId);
    };

    self.getSimulationBeamline = function() {
        if (appState.isLoaded()) {
            return self.elementForId(
                appState.applicationState().simulation.visualizationBeamlineId);
        }
        return null;
    };

    self.getBeamlinesWhichContainId = function(id) {
        var res = [];
        for (var i = 0; i < appState.models.beamlines.length; i++) {
            var b = appState.models.beamlines[i];
            for (var j = 0; j < b.items.length; j++) {
                if (id == Math.abs(b.items[j])) {
                    res.push(b.id);
                }
            }
        }
        return res;
    };

    self.nameForId = function(id) {
        return self.elementForId(id).name;
    };

    self.getNextBeamline = function() {
        var beamline = {
            name: self.uniqueNameForType('BL'),
            id: self.nextId(),
            l: 0,
            count: 0,
            items: [],
        };
        self.setValidator('beamline', beamline);
        return beamline;
    };

    self.getNextElement = function(type) {
        return {
            _id: self.nextId(),
            type: type,
            name: self.uniqueNameForType(type.charAt(0)),
        };
    };

    self.hasBeamlines = function() {
        if (appState.isLoaded()) {
            for (var i = 0; i < appState.models.beamlines.length; i++) {
                var beamline = appState.models.beamlines[i];
                if (beamline.items.length > 0) {
                    return true;
                }
            }
        }
        return false;
    };

    self.initSourceController = function(controller) {
        controller.bunchReports = [1, 2, 3, 4].map(function(id) {
            var modelKey = 'bunchReport' + id;
            return {
                id: id,
                modelKey: modelKey,
                getData: function() {
                    return appState.models[modelKey];
                },
            };
        });
        controller.bunchReportHeading = function(item) {
            return self.bunchReportHeading('bunchReport' + item.id);
        };
    };

    self.isCommandModelName = function(name) {
        return name.indexOf(COMMAND_PREFIX) === 0;
    };

    self.isElementModelName = function(name) {
        var schema = SIREPO.APP_SCHEMA.model[name];
        return schema && 'name' in schema && name == name.toUpperCase();
    };

    self.isReversed = function(beamlineId) {
        return beamlineId < 0;
    };

    self.newBeamline = function() {
        appState.models.beamline = self.getNextBeamline();
        panelState.showModalEditor('beamline');
    };

    self.newElement = function() {
        $('#' + panelState.modalId('newBeamlineElement')).modal('show');
    };

    self.nextId = function() {
        return Math.max(
            appState.maxId(appState.models.elements, '_id'),
            appState.maxId(appState.models.beamlines),
            appState.maxId(appState.models.commands || [], '_id')) + 1;
    };

    //TODO(pjm): use library for this
    self.numFormat = function(num, units) {
        num = rpnService.getRpnValue(num);
        if (! angular.isDefined(num)) {
            return '';
        }
        var sign = num < 0 ? -1 : 1;
        num = Math.abs(num);
        if (Math.round(num * 100) === 0) {
            return '0';
        }
        if (num >= 1000) {
            return (sign * num).toFixed(0) + units;
        }
        if (num >= 100) {
            return (sign * num).toFixed(1) + units;
        }
        if (num >= 10) {
            return (sign * num).toFixed(2) + units;
        }
    return (sign * num).toFixed(3) + units;
    };

    self.radiansToDegrees = function(v) {
        return v * 180 / Math.PI;
    };

    self.setValidator = function(modelName, model) {
        validationService.setFieldValidator(
            utilities.modelFieldID(modelName, 'name'),
            elementNameValidator(model.name),
            elementNameInvalidMsg);
    };

    self.showRpnVariables = function() {
        appState.models.rpnVariables = appState.models.rpnVariables.sort(function(a, b) {
            return a.name.localeCompare(b.name);
        });
        $('#sr-variables').modal('show');
    };

    self.uniqueNameForType = function(prefix) {
        var names = self.elementNameMap();
        var name = prefix;
        var index = 1;
        while (names[name + index]) {
            index++;
        }
        return name + index;
    };

    //TODO(pjm): listeners should only be added for apps which have an "elegant" style beamline, need a better test
    if (SIREPO.APP_SCHEMA.model.DRIFT || SIREPO.APP_SCHEMA.model.DRIF) {
        appState.whenModelsLoaded($rootScope, function() {
            self.activeBeamlineId = appState.models.simulation.activeBeamlineId;
        });

        $rootScope.$on('modelChanged', function(e, name) {
            if (name == 'beamline') {
                fixModelName(name);
                var id = appState.models.beamline.id;
                updateModels('beamline', 'id', 'beamlines', sortBeamlines);
                self.editBeamline({ id: id });
            }
            if (self.isElementModelName(name)) {
                fixModelName(name);
                updateModels(name, '_id', 'elements', sortElements);
            }
        });

        $rootScope.$on('cancelChanges', function(e, name) {
            if (name == 'beamline') {
                appState.removeModel(name);
                appState.cancelChanges('beamlines');
            }
            else if (self.isElementModelName(name)) {
                appState.removeModel(name);
                appState.cancelChanges('elements');
            }
        });

        $rootScope.$on('modelsUnloaded', function() {
            self.activeBeamlineId = null;
        });
    }

    return self;
});

SIREPO.app.service('rpnService', function(appState, requestSender, $rootScope) {
    var rpnBooleanValues = null;
    var self = this;
    self.isCaseInsensitive = false;

    function clearBooleanValues() {
        rpnBooleanValues = null;
    }

    self.computeRpnValue = function(value, callback) {
        if (self.isCaseInsensitive) {
            value = value.toLowerCase ? value.toLowerCase() : value;
        }
        if (value in appState.models.rpnCache) {
            callback(appState.models.rpnCache[value]);
            return;
        }
        requestSender.getApplicationData(
            {
                method: 'rpn_value',
                value: value,
                variables: appState.models.rpnVariables,
            },
            function(data) {
                if (! data.error) {
                    if (appState.isLoaded()) {
                        appState.models.rpnCache[value] = data.result;
                    }
                }
                callback(data.result, data.error);
            });
    };

    self.getRpnBooleanForField = function(model, field) {
        if (appState.isLoaded() && model && field) {
            if (! rpnBooleanValues) {
                rpnBooleanValues = [];
                if (appState.models.rpnVariables) {
                    for (var i = 0; i < appState.models.rpnVariables.length; i++) {
                        var v = appState.models.rpnVariables[i];
                        rpnBooleanValues.push([v.name, 'var: ' + v.name]);
                    }
                    rpnBooleanValues = rpnBooleanValues.sort(function(a, b) {
                        return a[1].localeCompare(b[1]);
                    });
                }
                rpnBooleanValues.unshift(
                    ['0', 'No'],
                    ['1', 'Yes']);
            }
            return rpnBooleanValues;
        }
        return null;
    };

    self.getRpnValue = function(v) {
        if (angular.isUndefined(v) || v === null) {
            return v;
        }
        if (self.isCaseInsensitive) {
            v = v.toLowerCase ? v.toLowerCase() : v;
        }
        if (appState.models.rpnCache && v in appState.models.rpnCache) {
            return appState.models.rpnCache[v];
        }
        var value = parseFloat(v);
        if (isNaN(value)) {
            return undefined;
        }
        return value;
    };

    self.getRpnValueForField = function(model, field) {
        if (appState.isLoaded() && model && field) {
            var v = model[field];
            if (SIREPO.NUMBER_REGEXP.test(v)) {
                return '';
            }
            return self.getRpnValue(v);
        }
        return '';
    };

    self.recomputeCache = function(varName, value) {
        var recomputeRequired = false;
        var re = new RegExp("\\b" + varName + "\\b");
        for (var k in appState.models.rpnCache) {
            if (k == varName) {
                appState.models.rpnCache[k] = value;
            }
            else if (k.match(re)) {
                recomputeRequired = true;
            }
        }
        if (! recomputeRequired) {
            return;
        }
        requestSender.getApplicationData(
            {
                method: 'recompute_rpn_cache_values',
                cache: appState.models.rpnCache,
                variables: appState.models.rpnVariables,
            },
            function(data) {
                if (appState.isLoaded() && data.cache) {
                    appState.models.rpnCache = data.cache;
                }
            });
    };

    $rootScope.$on('rpnVariables.changed', clearBooleanValues);
    appState.whenModelsLoaded($rootScope, clearBooleanValues);
});

SIREPO.app.directive('beamlineEditor', function(appState, latticeService, panelState, $document, $timeout, $window) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div data-ng-show="showEditor()" class="panel panel-info" style="margin-bottom: 0">',
              '<div class="panel-heading"><span class="sr-panel-heading">Beamline Editor - {{ beamlineName() }}</span>',
                '<div class="sr-panel-options pull-right">',
                  '<a href data-ng-click="showBeamlineNameModal()" title="Edit"><span class="sr-panel-heading glyphicon glyphicon-pencil"></span></a> ',
                '</div>',
              '</div>',
              '<div data-ng-attr-style="height: {{ editorHeight() }}" class="panel-body sr-lattice-editor-panel" data-ng-drop="true" data-ng-drag-stop="dragStop($data)" data-ng-drop-success="dropPanel($data)" data-ng-drag-start="dragStart($data)">',
                '<p class="lead text-center"><small><em>drag and drop elements here to define the beamline</em></small></p>',
                '<div data-ng-repeat="item in beamlineItems track by item.itemId" class="sr-lattice-item-holder" data-ng-drop="true" data-ng-drop-success="dropItem($index, $data)">',
                  '<div style="display: inline-block;" class="sr-editor-item-hover">',
                    '<div data-ng-drag="true" data-ng-drag-data="item" data-ng-dblclick="editItem(item, $event)" data-ng-mousedown="onMouseDown(item, $event)" oncontextmenu="return false" data-ng-click="selectItem(item, $event)" class="badge sr-lattice-item sr-badge-icon" data-ng-class="{\'sr-item-selected\': selectedItem == item, \'sr-lattice-icon\': item.isBeamline}"><span>{{ item.name }}</span></div>',
                    ' <span class="sr-lattice-close-icon glyphicon glyphicon-remove-circle" title="Delete Element" data-ng-click="deleteItem(item)"></span>',
                  '</div>',
                '</div>',
                '<div class="sr-lattice-item-holder" data-ng-drop="true" data-ng-drop-success="dropLast($data)">',
                  '<div style="visibility: hidden" class="badge sr-lattice-item sr-badge-icon"><span>last</span></div>',
                '</div>',
              '</div>',
            '</div>',
            '<div data-confirmation-modal="" data-id="sr-delete-lattice-item-dialog" data-title="{{ selectedItem.name }}" data-ok-text="Delete" data-ok-clicked="deleteSelectedItem()">Delete item <strong>{{ selectedItem.name }}</strong>?</div>',
            '<div data-confirmation-modal="" data-id="sr-beamline-from-elements-dialog" data-title="Create Beamline From Elements" data-ok-text="Save Changes" data-ok-clicked="createBeamlineFromElements()">',
              '<form class="form-horizontal" autocomplete="off">',
                '<label class="col-sm-4 control-label">Beamline Name</label>',
                '<div class="col-sm-8">',
                  '<input data-safe-path="" class="form-control" data-ng-model="newBeamline.name" required/>',
                  '<div class="sr-input-warning" data-ng-show="showWarning">{{warningText}}</div>',
                '</div>',
              '</form>',
            '</div>',
            '<div style="display:none">',
            '<div class="sr-lattice-item-popover">',
              '<div class="text-center">',
                '<button class="btn btn-default" data-ng-click="unpackBeamline()">Unpack</button>',
                ' <button class="btn btn-default" data-ng-if=":: canReverseBeamline()" data-ng-click="reverseBeamline()">Reverse</button>',
                ' <button class="btn btn-default" data-ng-click="clearPopover()">Cancel</button>',
              '</div>',
            '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.beamlineItems = [];
            $scope.selectedItem = null;
            $scope.newBeamline = {};
            var activeBeamline = null;
            var dragCanceled = false;
            var dropSuccess = false;
            var isBeamlineCache = {};
            var itemNameCache = {};
            var lastSelectedItem = null;

            function isBeamline(id) {
                var res = isBeamlineCache[id];
                if (res === undefined) {
                    var el = latticeService.elementForId(id);
                    res = el.type ? false : true;
                    isBeamlineCache[id] = res;
                }
                return res;
            }

            function itemName(id) {
                var res = itemNameCache[id];
                if (res === undefined) {
                    res = latticeService.nameForId(id);
                    res = (latticeService.isReversed(id) ? '-' : '') + res;
                    // cache is cleared below if item model is changed
                    itemNameCache[id] = res;
                }
                return res;
            }

            function newBeamlineItem(id, itemId) {
                return {
                    id: id,
                    itemId: itemId,
                    isBeamline: isBeamline(id),
                    name: itemName(id),
                };
            }

            function showPopover(item, $event) {
                if (item.isBeamline) {
                    if (! $scope.popoverContent) {
                        // keep a single reference to prevent garbage collection when dismissed?
                        $scope.popoverContent = $('.sr-lattice-item-popover');
                    }
                    var target = $($event.target).closest('.sr-lattice-item');
                    target.popover({
                        trigger: 'manual',
                        html: true,
                        placement: 'top',
                        container: $scope.element,
                        title: 'Modify the beamline?',
                        content: $scope.popoverContent,
                    });
                    $scope.selectItem(item);
                    target.popover('toggle');
                }
            }

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

            $scope.canReverseBeamline = function() {
                return SIREPO.lattice.canReverseBeamline;
            };

            $scope.clearPopover = function() {
                $('.sr-lattice-item').popover('hide');
            };

            $scope.createBeamlineFromElements = function() {
                var ids = [];
                var inCopy = false;
                $scope.beamlineItems.some(function(item) {
                    if (item.itemId == $scope.selectedItem.itemId
                        || item.itemId == lastSelectedItem.itemId) {
                        if (ids.length) {
                            ids.push(item.id);
                            return true;
                        }
                        inCopy = true;
                    }
                    if (inCopy) {
                        ids.push(item.id);
                    }
                });
                var targetIndices = [];
                for (var i = 0; i < $scope.beamlineItems.length - ids.length + 1; i++) {
                    var foundIt = true;
                    for (var j = 0; j < ids.length; j++) {
                        if ($scope.beamlineItems[i + j].id != ids[j]) {
                            foundIt = false;
                            break;
                        }
                    }
                    if (foundIt) {
                        targetIndices.unshift(i);
                        i += ids.length - 1;
                    }
                }
                // replaces all occurrences, targetIndices is reverse sorted
                targetIndices.forEach(function(idx) {
                    activeBeamline.items.splice(idx, ids.length, $scope.newBeamline.id);
                });
                $scope.newBeamline.items = ids;
                appState.models.beamline = $scope.newBeamline;
                appState.saveChanges('beamline');
                // force the new beamline to recalc length
                latticeService.editBeamline($scope.newBeamline, true);
                latticeService.editBeamline(activeBeamline);
            };

            $scope.deleteItem = function(data) {
                $scope.selectItem(data);
                $('#sr-delete-lattice-item-dialog').modal('show');
            };

            $scope.deleteSelectedItem = function() {
                $scope.beamlineItems.splice($scope.beamlineItems.indexOf($scope.selectedItem), 1);
                updateBeamline();
                $scope.selectedItem = null;
            };

            $scope.dragStart = function(data) {
                dragCanceled = false;
                dropSuccess = false;
                $scope.selectItem(data);
                var idx;
                if (data._id) {
                    // dragging in a new element
                    idx = $scope.beamlineItems.length;
                }
                else {
                    // dragging an existing element
                    idx = $scope.beamlineItems.indexOf(data);
                }
                if (idx >= 0) {
                    var count = 0;
                    $('.sr-lattice-editor-panel').find('.sr-lattice-item').each(function() {
                        $(this).removeClass('sr-move-left');
                        $(this).removeClass('sr-move-right');
                        $(this).addClass(count++ > idx ? 'sr-move-left' : 'sr-move-right');
                    });
                }
            };

            $scope.dragStop = function(data) {
                if (! data || dragCanceled) {
                    return;
                }
                if (data.itemId) {
                    $timeout(function() {
                        if (! dropSuccess) {
                            $scope.deleteItem(data);
                        }
                    });
                }
            };

            $scope.dropItem = function(index, data) {
                if (! data) {
                    return;
                }
                if (data.itemId) {
                    if (dragCanceled) {
                        return;
                    }
                    dropSuccess = true;
                    var curr = $scope.beamlineItems.indexOf(data);
                    $scope.beamlineItems.splice(curr, 1);
                }
                else {
                    data = $scope.beamlineItems.splice($scope.beamlineItems.length - 1, 1)[0];
                }
                $scope.beamlineItems.splice(index, 0, data);
                updateBeamline();
            };

            $scope.dropLast = function(data) {
                if (! data || ! data.itemId) {
                    return;
                }
                if (dragCanceled) {
                    return;
                }
                $scope.dropItem($scope.beamlineItems.length - 1, data);
            };

            $scope.dropPanel = function(data) {
                if (! data) {
                    return;
                }
                if (data.itemId) {
                    dropSuccess = true;
                    return;
                }
                if (data.id == activeBeamline.id) {
                    return;
                }
                var item = newBeamlineItem(data.id || data._id, appState.maxId($scope.beamlineItems, 'itemId') + 1);
                $scope.beamlineItems.push(item);
                $scope.selectItem(item);
                updateBeamline();
            };

            $scope.editorHeight = function() {
                var w = $($window);
                var el = $scope.element;
                if (el) {
                    return (w.height() - el.offset().top - 15) + 'px';
                }
                return '0';
            };

            $scope.editItem = function(item, $event) {
                var el = latticeService.elementForId(item.id);
                if (el.type) {
                    latticeService.editElement(el.type, el);
                }
                else {
                    showPopover(item, $event);
                }
            };

            $scope.onKeyDown = function(e) {
                // escape key - simulation a mouseup to cancel dragging
                if (e.keyCode == 27) {
                    if ($scope.selectedItem) {
                        dragCanceled = true;
                        $document.triggerHandler('mouseup');
                    }
                }
            };

            $scope.onMouseDown = function(item, $event) {
                // right mouse button
                if ($event.buttons == 2) {
                    showPopover(item, $event);
                }
            };

            $scope.reverseBeamline = function() {
                $scope.clearPopover();
                if (! $scope.selectedItem || ! $scope.selectedItem.isBeamline) {
                    return;
                }
                var item = $scope.selectedItem;
                item.id = -item.id;
                item.name = itemName(item.id);
                updateBeamline();
            };

            $scope.selectItem = function(item, $event) {
                $scope.clearPopover();
                if ($event && $event.shiftKey && $scope.selectedItem && (item != $scope.selectedItem)) {
                    lastSelectedItem = item;
                    $scope.newBeamline = latticeService.getNextBeamline();
                    $('#sr-beamline-from-elements-dialog').modal('show');
                    return;
                }
                $('.sr-selected-lattice-item').removeClass('sr-selected-lattice-item');
                $scope.selectedItem = item;
                var idx = $scope.beamlineItems.indexOf($scope.selectedItem);
                $('.sr-beamline-' + idx).addClass('sr-selected-lattice-item');
            };

            $scope.showBeamlineNameModal = function() {
                if (activeBeamline) {
                    appState.models.beamline = activeBeamline;
                    latticeService.setValidator('beamline', activeBeamline);
                    panelState.showModalEditor('beamline');
                }
            };

            $scope.showEditor = function() {
                if (! appState.isLoaded()) {
                    return false;
                }
                if (! latticeService.activeBeamlineId) {
                    return false;
                }
                var beamline = latticeService.getActiveBeamline();
                if (activeBeamline && activeBeamline == beamline && beamline.items.length == $scope.beamlineItems.length) {
                    return true;
                }
                activeBeamline = beamline;
                $scope.selectItem();
                $scope.beamlineItems = [];
                activeBeamline.items.forEach(function(id, idx) {
                    $scope.beamlineItems.push(newBeamlineItem(id, idx + 1));
                });
                return true;
            };

            $scope.unpackBeamline = function() {
                $scope.clearPopover();
                if (! $scope.selectedItem || ! $scope.selectedItem.isBeamline) {
                    return;
                }
                var idx = $scope.beamlineItems.indexOf($scope.selectedItem);
                if (idx >= 0) {
                    var items = latticeService.elementForId($scope.selectedItem.id).items;
                    if (latticeService.isReversed($scope.selectedItem.id)) {
                        items = items.slice().reverse();
                    }
                    activeBeamline.items = activeBeamline.items.slice(0, idx)
                        .concat(items)
                        .concat(activeBeamline.items.slice(idx + 1));
                    appState.saveChanges('beamlines');
                }
            };

            $scope.$on('modelChanged', function(e, name) {
                if (appState.models[name] && (appState.models[name].id || appState.models[name]._id)) {
                    var id = appState.models[name].id || appState.models[name]._id;
                    if (itemNameCache[id]) {
                        delete itemNameCache[id];
                        $scope.beamlineItems.forEach(function(item) {
                            if (item.id == id) {
                                item.name = itemName(id);
                            }
                        });
                    }
                }
            });

            $scope.$on('sr-beamlineItemSelected', function(e, beamlineIndex) {
                $scope.selectItem($scope.beamlineItems[beamlineIndex]);
            });
        },
        link: function(scope, element) {
            $document.on('keydown', scope.onKeyDown);
            scope.$on('$destroy', function() {
                $document.off('keydown', scope.onKeyDown);
            });
            scope.element = $(element).find('.sr-lattice-editor-panel').first();
        }
    };
});

SIREPO.app.directive('elementPicker', function(latticeService) {
    return {
        restrict: 'A',
        scope: {
            controller: '=',
            title: '@',
            id: '@',
            smallElementClass: '@',
        },
        template: [
            '<div class="modal fade" data-ng-attr-id="{{ id }}" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<span class="lead modal-title text-info">{{ title }}</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<div class="row" data-ng-show="::showTabs">',
                        '<div class="col-sm-12">',
                          '<ul class="nav nav-tabs">',
                            '<li role="presentation" data-ng-class="{active: activeTab == \'basic\'}"><a href data-ng-click="activeTab = \'basic\'">Basic</a></li>',
                            '<li role="presentation" data-ng-class="{active: activeTab == \'advanced\'}"><a href data-ng-click="activeTab = \'advanced\'">Advanced</a></li>',
                            '<li role="presentation" data-ng-class="{active: activeTab == \'all\'}"><a href data-ng-click="activeTab = \'all\'">All Elements</a></li>',
                          '</ul>',
                        '</div>',
                      '</div>',
                      '<br />',
                      '<div data-ng-if="activeTab == \'basic\'" class="row">',
                        '<div data-ng-repeat="name in controller.basicNames" class="col-sm-4">',
                          '<button style="width: 100%; margin-bottom: 1ex;" class="btn btn-default" type="button" data-ng-click="createElement(name)" data-ng-attr-title="{{ controller.titleForName(name) }}">{{ name }}</button>',
                        '</div>',
                      '</div>',
                      '<div data-ng-if="activeTab == \'advanced\'" class="row">',
                        '<div data-ng-repeat="name in controller.advancedNames" class="{{ smallElementClass }}">',
                          '<button style="width: 100%; margin-bottom: 1ex; overflow: hidden;" class="btn btn-default btn-sm" type="button" data-ng-click="createElement(name)" data-ng-attr-title="{{ controller.titleForName(name) }}">{{ name }}</button>',
                        '</div>',
                      '</div>',
                      '<div data-ng-if="activeTab == \'all\'" class="row">',
                        '<div data-ng-repeat="name in allNames" class="{{ smallElementClass }}">',
                          '<button style="width: 100%; margin-bottom: 1ex; overflow: hidden" class="btn btn-default btn-sm" type="button" data-ng-click="createElement(name)" data-ng-attr-title="{{ controller.titleForName(name) }}">{{ name }}</button>',
                        '</div>',
                      '</div>',
                      '<br />',
                      '<div class="row">',
                        '<div class="col-sm-offset-6 col-sm-3">',
                          '<button data-dismiss="modal" class="btn btn-primary" style="width:100%">Close</button>',
                        '</div>',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.activeTab = 'basic';
            $scope.allNames = $scope.controller.basicNames.concat($scope.controller.advancedNames).sort();
            $scope.showTabs = $scope.controller.advancedNames.length > 0;

            $scope.createElement = function(name) {
                // don't show the new editor until the picker panel is gone
                // the modal show/hide in bootstrap doesn't handle layered modals
                // and the browser scrollbar can be lost in some cases
                var picker = $('#' + $scope.id);
                picker.on('hidden.bs.modal', function() {
                    picker.off();
                    if ($scope.controller.createElement) {
                        $scope.controller.createElement(name);
                    }
                    else {
                        latticeService.createElement(name);
                    }
                    $scope.$applyAsync();
                });
                picker.modal('hide');
            };
        },
    };
});

SIREPO.app.directive('parameterWithLattice', function(appState) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            reportId: '<',
            beamlineId: '<',
        },
        template: [
            '<div data-ng-if="showLattice()"><div id="sr-lattice" data-lattice="" class="sr-plot" data-model-name="{{ modelName }}" data-flatten="1"></div></div>',
            '<div id="sr-parameters" data-parameter-plot="" class="sr-plot" data-model-name="{{ modelName }}" data-report-id="reportId"></div>',
        ].join(''),
        controller: function($scope, $element) {
            var latticeScope, plotScope;
            var isNestedSVG = false;

            function updateLattice() {
                if ($scope.showLattice() && latticeScope && plotScope) {
                    if (! isNestedSVG) {
                        // nest the SVG so the "download as png" gets both images
                        isNestedSVG = true;
                        var svgs = $($element).find('svg');
                        $(svgs[1]).prepend(svgs[0]);
                    }
                    latticeScope.updateFixedAxis(plotScope.getXAxis(), plotScope.margin.left);
                    $scope.$applyAsync();
                }
                else if (isNestedSVG) {
                    isNestedSVG = false;
                    $($element).find('svg svg').first().remove();
                }
            }

            $scope.showLattice = function() {
                if (appState.isLoaded()) {
                    if (appState.applicationState()[$scope.modelName].includeLattice == '1') {
                        if (plotScope && ! plotScope.onRefresh) {
                            plotScope.onRefresh = updateLattice;
                        }
                        return true;
                    }
                    else if (plotScope && plotScope.onRefresh) {
                        delete plotScope.onRefresh;
                        updateLattice();
                    }
                }
                return false;
            };

            $scope.$on('sr-latticeLinked', function(event) {
                latticeScope = event.targetScope;
                event.stopPropagation();
                updateLattice();
            });
            $scope.$on('sr-plotLinked', function(event) {
                if (event.targetScope.focusPoints) {
                    plotScope = event.targetScope;
                    event.stopPropagation();
                }
            });
        },
    };
});

SIREPO.app.directive('lattice', function(appState, latticeService, panelState, plotting, rpnService, utilities, $rootScope, $window) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            flatten: '@',
            pathToModels: '@',
        },
        templateUrl: '/static/html/lattice.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            var emptyList = [];
            var beamlineItems = emptyList;
            var panTranslate = [0, 0];
            var picTypeCache = null;
            var svgBounds = null;
            var zoom = null;
            var zoomScale = 1;
            $scope.plotStyle = $scope.flatten ? '' : 'cursor: zoom-in;';
            $scope.isClientOnly = true;
            $scope.margin = $scope.flatten ? 0 : 3;
            $scope.width = 1;
            $scope.height = 1;
            $scope.xScale = 1;
            $scope.yScale = 1;
            $scope.xOffset = 0;
            $scope.yOffset = 0;
            $scope.markerWidth = 1;
            $scope.markerUnits = '';
            $scope.svgGroups = [];

            function adjustPosition(pos, x, y) {
                var radAngle = latticeService.degreesToRadians(pos.angle);
                pos.x += rpnValue(x) * Math.cos(radAngle);
                pos.y += rpnValue(x) * Math.sin(radAngle);
                pos.x -= rpnValue(y) * Math.sin(radAngle);
                pos.y += rpnValue(y) * Math.cos(radAngle);
            }

            function itemTrackHash(item, group, length, angle) {
                return group.items.length + '-' + item.name + '-' + item._id + '-' + length + '-'
                    + group.rotate + '-' + group.rotateX + '-' + group.rotateY + '-' + (angle || 0) + '-' + item.beamlineIndex;
            }

            function subScaleWatch() {
                var xsMax = 50;
                return {
                    x: ($scope.xScale > xsMax ? xsMax / $scope.xScale  : 1),
                    y: 1,
                };
            }

            //TODO(pjm): this monster method needs to get broken into a separate service with karma tests
            function applyGroup(items, pos) {
                var group = {
                    rotate: pos.angle,
                    rotateX: pos.x,
                    rotateY: pos.y,
                    items: [],
                };
                $scope.svgGroups.push(group);
                var x = 0;
                var oldRadius = pos.radius;
                var newAngle = 0;
                var maxHeight = 0;

                for (var i = 0; i < items.length; i++) {
                    var item = items[i];
                    var picType = getPicType(item.type);
                    var length = rpnValue(item.l || item.xmax || 0);
                    if (picType == 'zeroLength') {
                        length = 0;
                    }
                    var travelLength = item.travelLength || length;
                    if (item.type.indexOf('RBEN') >= 0 && length > 0) {
                        // rben actual distance is the arclength
                        var bendAngle = rpnValue(item.angle || 0);
                        if (bendAngle != 0) {
                            travelLength = latticeService.arcLength(bendAngle, length);
                        }
                    }
                    if ($scope.flatten) {
                        length = travelLength;
                    }
                    var elRadius = rpnValue(item.rx || item.x_max || 0);
                    pos.length += travelLength;
                    //TODO(pjm): need to refactor picType processing
                    if (picType == 'bend') {
                        var angle = rpnValue(item.angle || item.kick || item.hkick || 0);
                        if (pos.inReverseBend) {
                            angle = -angle;
                        }
                        if ($scope.flatten) {
                            angle = 0;
                        }
                        var width = Math.abs(length);
                        var radius = length / 2;
                        if (item.type.indexOf('SBEN') >= 0 && angle != 0 && length != 0
                            // OPAL SBAND is a special case, length == chord length
                            && SIREPO.APP_SCHEMA.simulationType != 'opal') {
                            // compute the chord length from the arclength
                            var d1 = 2 * length / angle;
                            length = d1 * Math.sin(length / d1);
                        }
                        if (angle != 0 && length != 0) {
                            // compute bend radius
                            radius = length * Math.sin(angle / 2) / Math.sin(Math.PI - angle);
                        }
                        var height = width > 0 ? 0.75 : 1;
                        maxHeight = Math.max(maxHeight, height);
                        var enter = [pos.radius + pos.x + x, pos.y];
                        var enterEdge = rpnValue(item.e1 || 0);
                        var exitEdge = rpnValue(item.e2 || 0);
                        if (item.type.indexOf('RBEN') >= 0) {
                            enterEdge += angle / 2;
                            exitEdge += angle / 2;
                        }
                        if ($scope.flatten) {
                            enterEdge = 0;
                            exitEdge = 0;
                        }
                        var exit = [enter[0] + radius + Math.cos(angle) * radius,
                                    pos.y + Math.sin(angle) * radius];
                        var exitAngle = exitEdge - angle;
                        var points = [
                                [enter[0] - Math.sin(-enterEdge) * height / 2,
                                 enter[1] - Math.cos(-enterEdge) * height / 2],
                                [enter[0] + Math.sin(-enterEdge) * height / 2,
                                 enter[1] + Math.cos(-enterEdge) * height / 2],
                                [exit[0] + Math.sin(exitAngle) * height / 2,
                                 exit[1] + Math.cos(exitAngle) * height / 2],
                                [exit[0] - Math.sin(exitAngle) * height / 2,
                                 exit[1] - Math.cos(exitAngle) * height / 2],
                        ];
                        // trim overlap if necessary
                        if (length >= 0) {
                            if (points[1][0] > points[2][0]) {
                                points[1] = points[2] = lineIntersection(points);
                            }
                            else if (points[0][0] > points[3][0]) {
                                points[0] = points[3] = lineIntersection(points);
                            }
                        }
                        else {
                            if (points[1][0] < points[2][0]) {
                                points[1] = points[2] = lineIntersection(points);
                            }
                            else if (points[0][0] < points[3][0]) {
                                points[0] = points[3] = lineIntersection(points);
                            }
                        }
                        group.items.push({
                            picType: picType,
                            element: item,
                            color: getPicColor(item, 'blue'),
                            points: points,
                            trackHash: itemTrackHash(item, group, length, angle),
                            title: item.name + ': ' + item.type,
                        });
                        x += radius;
                        newAngle = latticeService.radiansToDegrees(angle);
                        pos.radius = radius;
                        if (item.type == 'CHANGREF' && ! $scope.flatten) {
                            adjustPosition(pos, item.XCE, -item.YCE);
                        }
                        else if (item.type == 'CHANGREF_VALUE' && ! $scope.flatten) {
                            if (item.transformType == 'XS') {
                                adjustPosition(pos, item.transformValue, 0);
                            }
                            else if (item.transformType == 'YS') {
                                adjustPosition(pos, 0, -item.transformValue);
                            }
                        }
                    }
                    else {
                        if (length < 0) {
                            // negative length, back up
                            x += length;
                        }
                        var groupItem = {
                            picType: picType,
                            element: item,
                            x: pos.radius + pos.x + x,
                            height: 0,
                            width: Math.abs(length),
                            title: item.name + ': ' + item.type,
                        };
                        if (picType == 'watch') {
                            groupItem.height = 1;
                            groupItem.y = pos.y;
                            groupItem.color = getPicColor(item, 'lightgreen');
                            groupItem.subScaling = subScaleWatch;
                        }
                        else if (picType == 'drift') {
                            groupItem.color = getPicColor(item, 'lightgrey');
                            groupItem.height = 0.1;
                            groupItem.y = pos.y - groupItem.height / 2;
                        }
                        else if (picType == 'aperture') {
                            groupItem.color = 'lightgrey';
                            groupItem.apertureColor = getPicColor(item, 'black');
                            groupItem.height = 0.1;
                            groupItem.y = pos.y - groupItem.height / 2;
                            if (groupItem.width === 0) {
                                groupItem.x -= 0.01;
                                groupItem.width = 0.02;
                            }
                            groupItem.opening = elRadius || 0.1;
                        }
                        else if (picType == 'alpha') {
                            var alphaAngle = 40.71;
                            newAngle = 180 - 2 * alphaAngle * (length < 0 ? -1 : 1);
                            //TODO(pjm): implement different angle depending on ALPH.part field
                            if (groupItem.width < 0.3) {
                                groupItem.width = 0.3;
                            }
                            groupItem.angle = alphaAngle;
                            groupItem.height = groupItem.width;
                            groupItem.y = pos.y - groupItem.height / 2;
                            if (length < 0) {
                                groupItem.angle = 180 - groupItem.angle;
                                groupItem.x -= length;
                                x -= length;
                            }
                            length = 0;
                            pos.radius = 0;
                        }
                        else if (picType == 'malign') {
                            groupItem.color = getPicColor(item, 'black');
                            groupItem.picType = 'zeroLength';
                            groupItem.height = 0.5;
                            groupItem.y = pos.y;
                            // adjust position by z and x offsets
                            adjustPosition(pos, item.dz, item.dx);
                            newAngle = - latticeService.radiansToDegrees(Math.atan(Math.sqrt(Math.pow(rpnValue(item.dxp), 2))));
                        }
                        else if (picType == 'mirror') {
                            if ('theta' in item) {
                                var thetaAngle = latticeService.radiansToDegrees(rpnValue(item.theta));
                                newAngle = 180 - 2 * thetaAngle;
                                groupItem.angle = thetaAngle;
                                pos.radius = 0;
                            }
                            else {
                                groupItem.angle = 0;
                            }
                            groupItem.color = getPicColor(item, 'black');
                            groupItem.height = Math.abs(elRadius) || 0.2;
                            groupItem.width = groupItem.height / 10;
                            groupItem.y = pos.y - groupItem.height / 2;
                            length = 0;
                            if (elRadius < 0) {
                                groupItem.x -= groupItem.width;
                            }
                        }
                        else if (picType == 'magnet') {
                            if (! length) {
                                groupItem.height = 0.2;
                                groupItem.y = pos.y;
                                groupItem.picType = 'zeroLength';
                                groupItem.color = 'black';
                            }
                            else {
                                groupItem.height = 0.5;
                                groupItem.y = pos.y - groupItem.height / 2;
                                groupItem.color = getPicColor(item, 'red');
                            }
                        }
                        else if (picType == 'undulator') {
                            groupItem.height = 0.25;
                            groupItem.y = pos.y - groupItem.height / 2;
                            groupItem.color = getPicColor(item, 'gray');
                            var periods = Math.round(rpnValue(item.periods || item.poles || 0));
                            if (periods <= 0) {
                                periods = Math.round(5 * groupItem.width);
                            }
                            groupItem.blockWidth = groupItem.width / (2 * periods);
                            groupItem.blocks = [];
                            groupItem.blockHeight = 0.03;
                            for (var j = 0; j < 2 * periods; j++) {
                                groupItem.blocks.push([
                                    groupItem.x + j * groupItem.blockWidth,
                                    j % 2
                                        ? groupItem.y + groupItem.height / 4
                                        : groupItem.y + groupItem.height * 3 / 4 - groupItem.blockHeight,
                                ]);
                            }
                        }
                        else if (picType == 'zeroLength' || (picType == 'rf' && groupItem.width < 0.005)) {
                            groupItem.color = getPicColor(item, 'black');
                            groupItem.picType = 'zeroLength';
                            groupItem.height = 0.5;
                            groupItem.y = pos.y;
                            //TODO(pjm): special zgoubi type, shift Y/Z axis 180
                            if (item.type == 'YMY') {
                                pos.inReverseBend = ! pos.inReverseBend;
                            }
                        }
                        else if (picType == 'rf') {
                            groupItem.height = 0.3;
                            groupItem.y = pos.y;
                            var ovalCount = Math.round(groupItem.width / (groupItem.height / 2)) || 1;
                            groupItem.ovalWidth = groupItem.width / ovalCount;
                            groupItem.ovals = [];
                            for (var k = 0; k < ovalCount; k++) {
                                groupItem.ovals.push(groupItem.x + k * groupItem.ovalWidth + groupItem.ovalWidth / 2);
                            }
                            groupItem.color = getPicColor(item, 'gold');
                        }
                        else if (picType == 'recirc') {
                            groupItem.radius = 0.3;
                            groupItem.y = pos.y;
                            groupItem.leftEdge = groupItem.x - groupItem.radius;
                            groupItem.rightEdge = groupItem.x + groupItem.radius;
                            groupItem.color = getPicColor(item, 'lightgreen');
                        }
                        else if (picType == 'lens') {
                            groupItem.height = 0.2;
                            groupItem.width = 0.02;
                            groupItem.x -= 0.01;
                            groupItem.y = pos.y - groupItem.height / 2;
                            groupItem.color = getPicColor(item, 'lightblue');
                        }
                        else if (picType == 'solenoid') {
                            if (length === 0) {
                                groupItem.width = 0.3;
                                groupItem.x -= 0.15;
                            }
                            groupItem.height = groupItem.width;
                            groupItem.y = pos.y - groupItem.height / 2;
                            groupItem.color = getPicColor(item, 'lightblue');
                        }
                        else {
                            groupItem.color = getPicColor(item, 'green');
                            groupItem.height = 0.2;
                            groupItem.y = pos.y - groupItem.height / 2;
                        }
                        maxHeight = Math.max(maxHeight, groupItem.height);
                        groupItem.trackHash = itemTrackHash(item, group, length);
                        group.items.push(groupItem);
                        if (length >= 0) {
                            x += length;
                            if (x > pos.bounds[2]) {
                                pos.bounds[2] = x;
                            }
                        }
                        else {
                            if (x < pos.bounds[0]) {
                                pos.bounds[0] = x;
                            }
                        }
                    }
                }
                if (pos.angle === 0) {
                    pos.x += x + oldRadius;
                }
                else {
                    pos.x += Math.sin(latticeService.degreesToRadians(90 - pos.angle)) * (x + oldRadius);
                    pos.y += Math.sin(latticeService.degreesToRadians(pos.angle)) * (x + oldRadius);
                }
                updateBounds(pos.bounds, pos.x, pos.y, Math.max(maxHeight, pos.radius));
                if ($scope.flatten) {
                    newAngle = 0;
                }
                group.trackHash = $scope.svgGroups.length + ' ' + group.items.map(function(item) {
                    return item.trackHash;
                }).join(' ');
                pos.angle += newAngle;
            }

            function beamlineContainsElement(beamlineItems, id, beamlineCache) {
                if (beamlineItems.indexOf(id) >= 0) {
                    return true;
                }
                if (! beamlineCache) {
                    beamlineCache = {};
                    $scope.models.beamlines.forEach(function(b) {
                        beamlineCache[b.id] = b.items;
                    });
                }
                for (var i = 0; i < beamlineItems.length; i++) {
                    var bid = beamlineItems[i];
                    if (beamlineCache[bid]) {
                        if (beamlineContainsElement(beamlineCache[bid], id, beamlineCache)) {
                            return true;
                        }
                        delete beamlineCache[bid];
                    }
                }
                return false;
            }

            function beamlineValue(beamline, field, value) {
                if (beamline[field] != value) {
                    beamline[field] = value;
                    return 1;
                }
                return 0;
            }

            function calculateInitialBeamlineMetrics() {
                // when lattice is initially loaded after import, calculate stats for all beamlines
                var beamlines = $scope.models.beamlines;
                if (beamlines.length && ! angular.isDefined(beamlines[0].count)) {
                    beamlines.forEach(function(beamline) {
                        loadItemsFromBeamline(true, beamline);
                    });
                }
            }

            function computePositions() {
                var pos = {
                    x: 0,
                    y: 0,
                    angle: 0,
                    radius: 0,
                    bounds: [0, 0, 0, 0],
                    count: 0,
                    length: 0,
                    inReverseBend: false,
                };
                var explodedItems = explodeItems(beamlineItems);
                var group = [];
                var groupDone = false;
                for (var i = 0; i < explodedItems.length; i++) {
                    if (groupDone) {
                        applyGroup(group, pos);
                        group = [];
                        groupDone = false;
                    }
                    var item = explodedItems[i];
                    var picType = getPicType(item.type);
                    //TODO(pjm): CHANGREF is zgoubi-specific
                    if (picType != 'drift' && item.type.indexOf('CHANGREF') < 0) {
                        pos.count++;
                    }
                    if (isAngleItem(picType)) {
                        groupDone = true;
                    }
                    group.push(item);
                }
                if (group.length) {
                    applyGroup(group, pos);
                }
                if (explodedItems.length && isAngleItem(getPicType(explodedItems[explodedItems.length - 1].type))) {
                    applyGroup([], pos);
                }
                svgBounds = pos.bounds;
                return pos;
            }

            //TODO(pjm): will infinitely recurse if beamlines are self-referential
            function explodeItems(items, res, reversed, beamlineIndex) {
                if (! res) {
                    res = [];
                }
                if (reversed) {
                    items = items.slice().reverse();
                }
                for (var i = 0; i < items.length; i++) {
                    var id = items[i];
                    var item = appState.clone(latticeService.elementForId(id, $scope.models));
                    item.beamlineIndex = beamlineIndex === undefined ? i : beamlineIndex;
                    item.indexClass = 'sr-beamline-' + item.beamlineIndex;
                    if (item.type) {
                        if (item.subElements) {
                            $.merge(res, item.subElements);
                        }
                        else {
                            res.push(item);
                        }
                    }
                    else {
                        explodeItems(item.items, res, latticeService.isReversed(id), item.beamlineIndex);
                    }
                }
                return res;
            }

            function getPicColor(item, defaultColor) {
                return item.color || SIREPO.lattice.elementColor[item.type] || defaultColor;
            }

            function getPicType(type) {
                if (! picTypeCache) {
                    picTypeCache = {};
                    var elementPic = SIREPO.lattice.elementPic;
                    for (var picType in elementPic) {
                        var types = elementPic[picType];
                        for (var i = 0; i < types.length; i++) {
                            picTypeCache[types[i]] = picType;
                        }
                    }
                }
                return picTypeCache[type];
            }

            function isAngleItem(picType) {
                return picType == 'bend' || picType == 'alpha' || picType == 'mirror' || picType == 'malign';
            }

            function lineIntersection(p) {
                var s1_x = p[1][0] - p[0][0];
                var s1_y = p[1][1] - p[0][1];
                var s2_x = p[3][0] - p[2][0];
                var s2_y = p[3][1] - p[2][1];
                var t = (s2_x * (p[0][1] - p[2][1]) - s2_y * (p[0][0] - p[2][0])) / (-s2_x * s1_y + s1_x * s2_y);
                return [
                    p[0][0] + (t * s1_x),
                    p[0][1] + (t * s1_y)];
            }

            function loadItemsFromBeamline(forceUpdate, beamline) {
                if ($scope.pathToModels) {
                    beamline = latticeService.elementForId(
                        appState.models[$scope.pathToModels].models.simulation.visualizationBeamlineId,
                        $scope.models);
                }
                beamline = beamline || ($scope.flatten && $scope.modelName != 'twissReport'
                    ? latticeService.getSimulationBeamline()
                    : latticeService.getActiveBeamline());
                if (! beamline) {
                    beamlineItems = emptyList;
                    return;
                }
                if (! forceUpdate && appState.deepEquals(beamline.items, beamlineItems)) {
                    return;
                }
                beamlineItems = appState.clone(beamline.items);
                $scope.svgGroups = [];
                var pos = computePositions();
                if (! $scope.flatten && beamlineValue(beamline, 'distance', Math.sqrt(Math.pow(pos.x, 2) + Math.pow(pos.y, 2)))
                    + beamlineValue(beamline, 'length', pos.length)
                    + beamlineValue(beamline, 'angle', latticeService.degreesToRadians(pos.angle))
                    + beamlineValue(beamline, 'count', pos.count)) {
                    appState.saveQuietly('beamlines');
                }
                $scope.resize();
            }

            function recalcScaleMarker() {
                if ($scope.flatten) {
                    return;
                }
                //TODO(pjm): use library for this
                $scope.markerUnits = '1 m';
                $scope.markerWidth = $scope.xScale * zoomScale;
                if ($scope.markerWidth < 20) {
                    $scope.markerUnits = '10 m';
                    $scope.markerWidth *= 10;
                    if ($scope.markerWidth < 20) {
                        $scope.markerUnits = '100 m';
                        $scope.markerWidth *= 10;
                    }
                }
                else if ($scope.markerWidth > 200) {
                    $scope.markerUnits = '10 cm';
                    $scope.markerWidth /= 10;
                    if ($scope.markerWidth > 200) {
                        $scope.markerUnits = '1 cm';
                        $scope.markerWidth /= 10;
                    }
                }
            }

            function resetZoomAndPan() {
                zoomScale = 1;
                zoom.scale(zoomScale);
                panTranslate = [0, 0];
                zoom.translate(panTranslate);
                updateZoomAndPan();
            }

            function rpnValue(num) {
                return rpnService.getRpnValue(num);
            }

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            function updateBounds(bounds, x, y, buffer) {
                if (-buffer < bounds[0]) {
                    bounds[0] = -buffer;
                }
                if (x - buffer < bounds[0]) {
                    bounds[0] = x - buffer;
                }
                if (y - buffer < bounds[1]) {
                    bounds[1] = y - buffer;
                }
                if (x + buffer > bounds[2]) {
                    bounds[2] = x + buffer;
                }
                if (y + buffer > bounds[3]) {
                    bounds[3] = y + buffer;
                }
            }

            function updateZoomAndPan() {
                recalcScaleMarker();
                select('.sr-zoom-plot').attr("transform", "translate(" + panTranslate + ")scale(" + zoomScale + ")");
            }

            function zoomed() {
                zoomScale = d3.event.scale;

                if (zoomScale == 1) {
                    panTranslate = [0, 0];
                    zoom.translate(panTranslate);
                }
                else {
                    //TODO(pjm): don't allow translation outside of image boundaries
                    panTranslate = d3.event.translate;
                }
                updateZoomAndPan();
                $scope.$digest();
            }

            $scope.destroy = function() {
                if (zoom) {
                    zoom.on('zoom', null);
                }
            };

            $scope.init = function() {
                zoom = d3.behavior.zoom()
                    .scaleExtent([1, 50]);
                if (! $scope.flatten) {
                    zoom.on('zoom', zoomed);
                    //TODO(pjm): call stopPropagation() on item double-click instead, would allow double-click zoom on empty space
                    select('svg').call(zoom)
                        .on('dblclick.zoom', null);
                }
                $scope.resize();
            };

            $scope.itemClicked = function(item) {
                $rootScope.$broadcast('sr-beamlineItemSelected', item.beamlineIndex);
            };

            $scope.itemDblClicked = function(item) {
                if ($scope.pathToModels) {
                    return;
                }
                latticeService.editElement(item.type, item);
            };

            $scope.resize = function() {
                if (select().empty()) {
                    return;
                }
                var width = parseInt(select().style('width'));
                if (isNaN(width)) {
                    return;
                }
                $scope.width = width;
                if ($scope.flatten) {
                    return;
                }
                $scope.height = $scope.width;
                var windowHeight = $($window).height();
                var maxHeightFactor = utilities.isFullscreen() ? 1.5 : 2.5;
                if ($scope.height > windowHeight / maxHeightFactor) {
                    $scope.height = windowHeight / maxHeightFactor;
                }

                if (svgBounds) {
                    var w = svgBounds[2] - svgBounds[0];
                    var h = svgBounds[3] - svgBounds[1];
                    if (w === 0 || h === 0) {
                        return;
                    }
                    var scaleWidth = ($scope.width - $scope.margin) / w;
                    var scaleHeight = ($scope.height - $scope.margin) / h;
                    var scale = 1;
                    var xOffset = 0;
                    var yOffset = 0;
                    if (scaleWidth < scaleHeight) {
                        scale = scaleWidth;
                        yOffset = ($scope.height - h * scale) / 2;
                    }
                    else {
                        scale = scaleHeight;
                        xOffset = ($scope.width - w * scale) / 2;
                    }
                    $scope.xScale = scale;
                    $scope.yScale = scale;
                    $scope.xOffset = - svgBounds[0] * scale + xOffset;
                    $scope.yOffset = - svgBounds[1] * scale + yOffset;
                    recalcScaleMarker();
                }
            };

            $scope.updateFixedAxis = function(axis, leftMargin, yScale, height, yOffset) {
                if (! axis.domain) {
                    return;
                }
                var widthInPixels = axis.scale.range()[1];
                var currentDomainWidth = axis.scale.domain()[1] - axis.scale.domain()[0];
                var scale = widthInPixels / currentDomainWidth;
                var leftPoint = (axis.scale.domain()[0] - axis.domain[0]) * scale;
                $scope.yScale = yScale || 20;
                $scope.height = height || 50;
                $scope.yOffset = yOffset || 40;
                $scope.xScale = scale;
                $scope.xOffset = leftMargin - leftPoint;
            };

            function renderBeamline(forceUpdate, updateNoWait) {
                if (updateNoWait) {
                    // don't wait for the UI, recalc beamline immediately
                    loadItemsFromBeamline(forceUpdate);
                    return;
                }
                // only show the loading message for simulations with a lot of elements
                $scope.isLoading = $scope.models.elements.length > 25;
                panelState.waitForUI(function() {
                    $scope.isLoading = false;
                    loadItemsFromBeamline(forceUpdate);
                });
            }

            appState.whenModelsLoaded($scope, function() {
                function getModels() {
                    $scope.models = $scope.pathToModels ? appState.models[$scope.pathToModels].models : appState.models;
                }

                getModels();
                calculateInitialBeamlineMetrics();
                renderBeamline();

                $scope.$on($scope.pathToModels + '.changed', function(e, name) {
                    getModels();
                    renderBeamline(true);
                });

                $scope.$on('modelChanged', function(e, name) {
                    if (name == 'beamlines') {
                        renderBeamline();
                    }
                    if (name == 'rpnVariables') {
                        renderBeamline(true);
                    }
                    if ($scope.models[name] && $scope.models[name]._id) {
                        if (beamlineContainsElement(beamlineItems, $scope.models[name]._id)) {
                            renderBeamline(true);
                        }
                    }
                });

                $scope.$on('activeBeamlineChanged', function($event, updateNoWait) {
                    renderBeamline(false, updateNoWait);
                    resetZoomAndPan();
                });
            });
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
            scope.$emit('sr-latticeLinked');
        },
    };
});

SIREPO.app.directive('latticeBeamlineList', function(appState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            isOptional: '@',
        },
        template: [
            '<select class="form-control" data-ng-model="model[field]" data-ng-options="item.id as item.name for item in beamlineList()"></select>',
        ].join(''),
        controller: function($scope) {
            var list = [
                {
                    id: '',
                    name: 'NOT SELECTED',
                },
            ];
            $scope.beamlineList = function() {
                if (! appState.isLoaded() || ! $scope.model) {
                    return null;
                }
                if ($scope.isOptional) {
                    list.length = 1;
                    return list.concat(appState.models.beamlines);
                }
                if (! $scope.model[$scope.field]
                    && appState.models.beamlines
                    && appState.models.beamlines.length) {
                    $scope.model[$scope.field] = appState.models.beamlines[0].id;
                }
                return appState.models.beamlines;
            };
        },
    };
});

SIREPO.app.directive('latticeBeamlineTable', function(appState, latticeService, panelState, $window) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<table style="width: 100%; table-layout: fixed; margin-bottom: 10px" class="table table-hover">',
              '<colgroup>',
                '<col style="width: 20ex">',
                '<col style="width: 100%">',
                '<col data-ng-show="isLargeWindow()" style="width: 10ex">',
                '<col data-ng-show="isLargeWindow()" style="width: 12ex">',
                '<col style="width: 12ex">',
                '<col style="width: 10ex">',
              '</colgroup>',
              '<thead>',
                '<tr>',
                  '<th>Name</th>',
                  '<th>Description</th>',
                  '<th data-ng-show="isLargeWindow()">Elements</th>',
                  '<th data-ng-show="isLargeWindow()">Start-End</th>',
                  '<th>Length</th>',
                  '<th>Bend</th>',
                '</tr>',
              '</thead>',
              '<tbody>',
                '<tr data-ng-class="{success: isActiveBeamline(beamline)}" data-ng-repeat="beamline in appState.models.beamlines track by beamline.id">',
                  '<td><div class="badge sr-badge-icon sr-lattice-icon" data-ng-class="{\'sr-lattice-icon-disabled\': wouldBeamlineSelfNest(beamline)}"><span data-ng-drag="! wouldBeamlineSelfNest(beamline)" data-ng-drag-data="beamline">{{ beamline.name }}</span></div></td>',
                  '<td style="overflow: hidden"><span style="color: #777; white-space: nowrap">{{ beamlineDescription(beamline) }}</span></td>',
                  '<td data-ng-show="isLargeWindow()" style="text-align: right">{{ beamline.count }}</td>',
                  '<td data-ng-show="isLargeWindow()" style="text-align: right">{{ beamlineDistance(beamline) }}</td>',
                  '<td style="text-align: right">{{ beamlineLength(beamline) }}</td>',
                  '<td style="text-align: right">{{ beamlineBend(beamline, \'&nbsp;\') }}',
                    '<span data-ng-if="beamlineBend(beamline)">&deg;</span>',
                    '<div class="sr-button-bar-parent">',
                        '<div class="sr-button-bar" data-ng-class="{\'sr-button-bar-active\': isActiveBeamline(beamline)}" >',
                            '<button class="btn btn-info btn-xs sr-hover-button" data-ng-click="copyBeamline(beamline)">Copy</button>',
                            '<span data-ng-show="! isActiveBeamline(beamline)" >',
                            ' <button class="btn btn-info btn-xs sr-hover-button" data-ng-disabled="wouldBeamlineSelfNest(beamline)" data-ng-click="latticeService.addToBeamline(beamline)">Add to Beamline</button>',
                            ' <button data-ng-click="latticeService.editBeamline(beamline)" class="btn btn-info btn-xs sr-hover-button">Edit</button>',
                            ' <button data-ng-show="! isActiveBeamline(beamline)" data-ng-click="deleteBeamline(beamline)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button>',
                            '</span>',
                        '</div>',
                    '<div>',
                  '</td>',
                '</tr>',
              '</tbody>',
            '</table>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
            $scope.latticeService = latticeService;
            var windowSize = 0;
            var isNested = {};
            var descriptionCache = {};

            function computeNesting() {
                isNested = {};
                appState.models.beamlines.forEach(function(beamline) {
                    computeNestingBeamline(beamline);
                });
            }

            function computeNestingBeamline(beamline, blItems) {
                if (isNested[beamline.id]) {
                    return;
                }
                var activeBeamline = latticeService.getActiveBeamline();
                if(! activeBeamline || activeBeamline.id === beamline.id) {
                    isNested[beamline.id] = true;
                    return;
                }
                if(! blItems) {
                    blItems = beamline.items || [];
                }
                if(blItems.indexOf(activeBeamline.id) >= 0) {
                    isNested[beamline.id] = true;
                    return;
                }
                for(var i = 0; i < blItems.length; i++) {
                    var nextItems = latticeService.elementForId(blItems[i]).items;
                    if(nextItems && computeNestingBeamline(beamline, nextItems)) {
                        isNested[beamline.id] = true;
                        return;
                    }
                }
            }

            function itemsToString(items) {
                var res = '(';
                if (! items.length) {
                    res += ' ';
                }
                for (var i = 0; i < items.length; i++) {
                    var id = items[i];
                    res += (id < 0 ? '-' : '') + latticeService.nameForId(id);
                    if (i != items.length - 1) {
                        res += ',';
                    }
                }
                res += ')';
                return res;
            }

            function windowResize() {
                windowSize = $($window).width();
            }

            $scope.copyBeamline = function(beamline) {
                var newBeamline = latticeService.getNextBeamline();
                for(var prop in beamline) {
                    if(prop != 'id' && prop != 'name' && prop != 'items') {
                        newBeamline[prop] = beamline[prop];
                    }
                }
                newBeamline.items = beamline.items.slice();
                appState.models.beamline = newBeamline;
                panelState.showModalEditor('beamline');
            };

            $scope.beamlineBend = function(beamline, defaultValue) {
                if (angular.isDefined(beamline.angle)) {
                    return latticeService.angleFormat(beamline.angle);
                }
                return defaultValue;
            };

            $scope.beamlineDescription = function(beamline) {
                if (descriptionCache[beamline.id]) {
                    return descriptionCache[beamline.id];
                }
                var res = itemsToString(beamline.items);
                descriptionCache[beamline.id] = res;
                return res;
            };

            $scope.beamlineDistance = function(beamline) {
                return latticeService.numFormat(beamline.distance, 'm');
            };

            $scope.beamlineLength = function(beamline) {
                return latticeService.numFormat(beamline.length, 'm');
            };

            $scope.deleteBeamline = function(beamline) {
                latticeService.deleteElementPrompt('beamlines', beamline);
            };

            $scope.isActiveBeamline = function(beamline) {
                if (latticeService.activeBeamlineId) {
                    return latticeService.activeBeamlineId == beamline.id;
                }
                return false;
            };

            $scope.isLargeWindow = function() {
                return windowSize >= 1200;
            };

            $scope.wouldBeamlineSelfNest = function (beamline) {
                return isNested[beamline.id];
            };

            appState.whenModelsLoaded($scope, function() {
                $scope.$on('beamlines.changed', function() {
                    computeNesting();
                    descriptionCache = {};
                });
                $scope.$on('elements.changed', function() {
                    descriptionCache = {};
                });
                $scope.$on('activeBeamlineChanged', computeNesting);
                $scope.$on('sr-window-resize',  windowResize);
                computeNesting();
                windowResize();
            });
        },
    };
});

SIREPO.app.directive('latticeElementPanels', function(latticeService) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div class="col-sm-12 col-md-6 col-xl-5">',
              '<div data-split-panels="" style="height: {{ panelHeight() }}">',
                '<div id="sr-top-panel" class="split split-vertical">',
                  '<div class="panel panel-info" style="margin-bottom: 0">',
                    '<div class="panel-heading"><span class="sr-panel-heading">Beamlines</span></div>',
                    '<div class="panel-body" style="padding-bottom: 0">',
                      '<button class="btn btn-info btn-xs pull-right" accesskey="b" data-ng-click="latticeService.newBeamline()"><span class="glyphicon glyphicon-plus"></span> New <u>B</u>eamline</button>',
                      '<div data-lattice-beamline-table=""></div>',
                    '</div>',
                  '</div>',
                '</div>',
                '<div id="sr-bottom-panel" class="split split-vertical">',
                  '<div class="panel panel-info" style="margin-bottom: 10px">',
                    '<div class="panel-heading"><span class="sr-panel-heading">Beamline Elements</span></div>',
                    '<div class="panel-body">',
                      '<div class="pull-right">',
                        '<button data-ng-if=":: latticeService.wantRpnVariables" class="btn btn-info btn-xs" data-ng-click="latticeService.showRpnVariables()"><span class="glyphicon glyphicon-list-alt"></span> Variables</button> ',
                        '<button class="btn btn-info btn-xs" data-ng-click="latticeService.newElement()" accesskey="e"><span class="glyphicon glyphicon-plus"></span> New <u>E</u>lement</button>',
                      '</div>',
                      '<div data-lattice-element-table=""></div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.latticeService = latticeService;
        },
    };
});

SIREPO.app.directive('latticeElementTable', function(appState, latticeService, $rootScope) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<table style="width: 100%; table-layout: fixed; margin-bottom: 0" class="table table-hover">',
              '<colgroup>',
                '<col style="width: 20ex">',
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
                  '<td style="cursor: pointer" colspan="4" data-ng-click="toggleCategory(category)" ><span class="glyphicon" data-ng-class="{\'glyphicon-collapse-up\': ! category.isCollapsed, \'glyphicon-collapse-down\': category.isCollapsed}"></span> <b>{{ category.name }}</b></td>',
                '</tr>',
                '<tr data-ng-show="! category.isCollapsed" data-ng-repeat="element in category.elements track by element._id">',
                  '<td style="padding-left: 1em"><div class="badge sr-badge-icon"><span data-ng-drag="true" data-ng-drag-data="element">{{ element.name }}</span></div></td>',
                  '<td style="overflow: hidden"><span style="color: #777; white-space: nowrap">{{ element.description }}</span></td>',
                  '<td style="text-align: right">{{ elementLength(element) }}</td>',
                  '<td style="text-align: right">{{ element.bend || \'&nbsp;\' }}<span data-ng-if="element.isBend">&deg;</span><div class="sr-button-bar-parent"><div class="sr-button-bar"><button class="btn btn-info btn-xs sr-hover-button" data-ng-click="copyElement(element)">Copy</button> <button data-ng-show="latticeService.activeBeamlineId" class="btn btn-info btn-xs sr-hover-button" data-ng-click="latticeService.addToBeamline(element)">Add to Beamline</button> <button data-ng-click="editElement(category.name, element)" class="btn btn-info btn-xs sr-hover-button">Edit</button> <button data-ng-click="deleteElement(element)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div><div></td>',
                '</tr>',
              '</tbody>',
            '</table>',
        ].join(''),
        controller: function($scope) {
            $scope.latticeService = latticeService;
            $scope.tree = [];
            var collapsedElements = {};
            var descriptionCache = {};

            function computeBend(element) {
                var angle = element.angle;
                if (angular.isDefined(angle)) {
                    element.isBend = true;
                    element.bend = latticeService.angleFormat(angle);
                }
            }

            function elementDescription(element) {
                if (! element) {
                    return 'null';
                }
                if (angular.isDefined(descriptionCache[element._id])) {
                    return descriptionCache[element._id];
                }
                var schema = SIREPO.APP_SCHEMA.model[element.type];
                var res = '';
                var fields = Object.keys(element).sort();
                for (var i = 0; i < fields.length; i++) {
                    var f = fields[i];
                    if (f == 'name' || f == 'l' || f == 'angle' || f.indexOf('$') >= 0) {
                        continue;
                    }
                    if (angular.isDefined(element[f]) && angular.isDefined(schema[f])) {
                        if (schema[f][1] == 'OutputFile' && element[f]) {
                            //TODO(pjm): elegant specific
                            res += f + '=' + element.name + '.' + f + '.sdds ';
                        }
                        else if (schema[f][2] != element[f]) {
                            var v = element[f];
                            if (angular.isArray(v)) {
                                //TODO(pjm): zgoubi specific
                                if (v.length && v[0].transformType) {
                                    for (var j = 0; j < v.length; j++) {
                                        var item = v[j];
                                        res += item.transformType + '=' + item.transformValue + ' ';
                                    }
                                }
                            }
                            else {
                                res += f + '=' + v + ' ';
                            }
                        }
                    }
                }
                descriptionCache[element._id] = res;
                return res;
            }

            function loadTree() {
                $scope.tree = [];
                descriptionCache = {};
                var category = null;
                appState.applicationState().elements.forEach(function(element) {
                    if (! category || category.name != element.type) {
                        category = {
                            name: element.type,
                            elements: [],
                            isCollapsed: collapsedElements[element.type],
                        };
                        $scope.tree.push(category);
                    }
                    var clonedElement = appState.clone(element);
                    computeBend(clonedElement);
                    clonedElement.description = elementDescription(clonedElement);
                    category.elements.push(clonedElement);
                });
            }

            $scope.deleteElement = function(element) {
                latticeService.deleteElementPrompt('elements', element);
            };

            $scope.editElement = function(type, item) {
                var el = latticeService.elementForId(item._id);
                return latticeService.editElement(type, el);
            };

            $scope.copyElement = function(element) {
                var elementCopy = latticeService.getNextElement(element.type);
                for(var prop in element) {
                    if(prop != '_id' && prop != 'name') {
                        elementCopy[prop] = element[prop];
                    }
                }
                // element does not exist yet so cannot use local edit
                latticeService.editElement(elementCopy.type, elementCopy);
            };

            $scope.elementLength = function(element) {
                return latticeService.numFormat(element.l, 'm');
            };

            $scope.toggleCategory = function(category) {
                category.isCollapsed = ! category.isCollapsed;
                collapsedElements[category.name] = category.isCollapsed;
            };

            $scope.$on('modelChanged', function(e, name) {
                if (name == 'elements') {
                    loadTree();
                }
            });

            $scope.$on('elementDeleted', function(e, name) {
                if (name == 'elements') {
                    loadTree();
                }
            });
            appState.whenModelsLoaded($scope, loadTree);
        },
    };
});

SIREPO.app.directive('latticeTab', function(latticeService, panelState, utilities, $window) {
    return {
        restrict: 'A',
        scope: {
            controller: '=',
        },
        template: [
            '<div class="container-fluid">',
              '<div class="row">',
                '<div class="col-sm-12 col-md-6 col-xl-7">',
                  '<div class="row">',
                    '<div data-ng-if="latticeService.activeBeamlineId" class="col-sm-12">',
                      '<div data-report-panel="lattice" data-model-name="beamlineReport" data-panel-title="Lattice - {{ latticeService.getActiveBeamline().name }}"><a data-ng-show="showTwissReportButton()" data-ng-click="showTwissReport()" style="position: absolute; bottom: 3em" class="btn btn-default btn-xs" href>{{ twissReportTitle() }}</a></div>',
                    '</div>',
                    '<div class="col-sm-12">',
                      '<div data-beamline-editor=""></div>',
                    '</div>',
                  '</div>',
                '</div>',
                '<div lattice-element-panels=""></div>',
              '</div>',
            '</div>',
            '<div data-ng-drag-clone=""><div class="badge sr-badge-icon sr-item-selected"><span>{{ clonedData.name }}</span></div></div>',
            '<div data-element-picker="" data-controller="controller" data-title="New Beamline Element" data-id="sr-newBeamlineElement-editor" data-small-element-class="col-sm-2"></div>',
            '<div data-confirmation-modal="" data-id="sr-element-in-use-dialog" data-title="{{ latticeService.deleteWarning.typeName }} {{ latticeService.deleteWarning.name }}" data-ok-text="" data-cancel-text="Close">The {{ latticeService.deleteWarning.typeName }} <strong>{{ latticeService.deleteWarning.name }}</strong> is used by the <strong>{{ latticeService.deleteWarning.beamlineName }}</strong> and can not be deleted.</div>',
            '<div data-confirmation-modal="" data-id="sr-delete-element-dialog" data-title="{{ latticeService.deleteWarning.typeName }} {{ latticeService.deleteWarning.name }}" data-ok-text="Delete" data-ok-clicked="latticeService.deleteElement()">Delete {{ latticeService.deleteWarning.typeName }} <strong>{{ latticeService.deleteWarning.name }}</strong>?</div>',

            '<div data-confirmation-modal="" data-id="sr-var-in-use-dialog" data-title="Variable in Use" data-ok-text="" data-cancel-text="Close">{{ latticeService.deleteVarWarning  }} and can not be deleted.</div>',

            '<div data-ng-if=":: latticeService.wantRpnVariables" data-var-editor=""></div>',
            '<div class="modal fade" id="sr-lattice-twiss-plot" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-warning">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<span class="lead modal-title text-info">{{ twissReportTitle() }}</span>',
                    '<div class="sr-panel-options pull-right">',
                      '<a style="margin-top: -2px; margin-right: 10px" href data-ng-click="showTwissEditor()" title="Edit"><span class="sr-panel-heading glyphicon glyphicon-pencil"></span></a> ',
                    '</div>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<div class="row">',
                        '<div class="col-sm-12" data-ng-if="twissReportShown">',
                          '<div data-report-content="parameterWithLattice" data-model-key="twissReport" data-report-id="reportId"></div>',
                        '</div>',
                      '</div>',
                      '<br />',
                      '<div class="row">',
                        '<div class="col-sm-offset-6 col-sm-3">',
                          '<button data-dismiss="modal" class="btn btn-primary" style="width:100%">Close</button>',
                        '</div>',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.reportId = Math.floor(Math.random() * Number.MAX_SAFE_INTEGER);
            $scope.latticeService = latticeService;

            function hasTwissReport() {
                return SIREPO.APP_SCHEMA.model.twissReport ? true : false;
            }

            $scope.showTwissReportButton = function() {
                if (hasTwissReport()) {
                    var beamline = latticeService.getActiveBeamline();
                    return beamline && beamline.length != 0;
                }
                return false;
            };
            $scope.showTwissReport = function() {
                if (utilities.isFullscreen()) {
                    utilities.exitFullscreenFn().call(document);
                }
                var el = $('#sr-lattice-twiss-plot');
                el.modal('show');
                el.on('shown.bs.modal', function() {
                    $scope.twissReportShown = true;
                    $scope.$digest();
                });
                el.on('hidden.bs.modal', function() {
                    $scope.twissReportShown = false;
                    el.off();
                });
            };
            $scope.twissReportTitle = function() {
                if (hasTwissReport()) {
                    return SIREPO.APP_SCHEMA.view.twissReport.title;
                }
                return '';
            };
            $scope.showTwissEditor = function() {
                panelState.showModalEditor('twissReport');
            };
        },
    };
});

SIREPO.app.directive('rpnBoolean', function(rpnService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: [
            '<select class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in rpnBooleanValues()"></select>',
        ].join(''),
        controller: function($scope) {
            $scope.rpnBooleanValues = function() {
                return rpnService.getRpnBooleanForField($scope.model, $scope.field);
            };
        },
    };
});

SIREPO.app.directive('rpnStatic', function(rpnService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: [
            '<div data-ng-attr-title="{{ computedRpnValue(); }}" class="form-control-static" style="text-overflow: ellipsis; overflow: hidden; margin-left: -15px; padding-left: 0; white-space: nowrap">{{ computedRpnValue(); }}</div>',
        ].join(''),
        controller: function($scope) {
            $scope.computedRpnValue = function() {
                return rpnService.getRpnValueForField($scope.model, $scope.field);
            };
        },
    };
});

SIREPO.app.directive('rpnEditor', function() {
    return {
        restrict: 'A',
        template: [
          '<div data-ng-class="fieldClass">',
            '<input data-rpn-value="" data-ng-model="model[field]" class="form-control" style="text-align: right" data-lpignore="true" data-ng-required="isRequired()" />',
          '</div>',
          //TODO(pjm): fragile - hide rpnStaic value when in column mode, need better detection this case
          '<div data-ng-hide="{{ fieldSize && fieldSize != \'2\' }}" class="col-sm-2">',
            '<div data-rpn-static="" data-model="model" data-field="field"></div>',
          '</div>',
        ].join(''),
    };
});

SIREPO.app.directive('rpnValue', function(appState, rpnService) {
    var requestIndex = 0;
    return {
        restrict: 'A',
        require: 'ngModel',
        link: function(scope, element, attrs, ngModel) {
            var rpnVariableName = scope.modelName == 'rpnVariable' ? scope.model.name : null;
            var range = {
                min: scope.info[4],
                max: scope.info[5],
            };

            scope.isRequired = function() {
                if (scope.info && scope.info[1] == 'OptionalRPNValue') {
                    return false;
                }
                if (appState.isLoaded()) {
                    if (scope.model && scope.model.isOptional) {
                        return false;
                    }
                }
                return true;
            };

            ngModel.$parsers.push(function(value) {
                requestIndex++;
                var currentRequestIndex = requestIndex;
                if (ngModel.$isEmpty(value)) {
                    return null;
                }
                if (SIREPO.NUMBER_REGEXP.test(value)) {
                    var v = parseFloat(value);
                    if (rpnVariableName) {
                        rpnService.recomputeCache(rpnVariableName, v);
                    }
                    if (range.min != undefined && v < range.min) {
                        return undefined;
                    }
                    if (range.max != undefined && v > range.max) {
                        return undefined;
                    }
                    ngModel.$setValidity('', true);
                    return v;
                }
                rpnService.computeRpnValue(value, function(v, err) {
                    // check for a stale request
                    if (requestIndex != currentRequestIndex) {
                        return;
                    }
                    ngModel.$setValidity('', err ? false : true);
                    if (rpnVariableName && ! err) {
                        rpnService.recomputeCache(rpnVariableName, v);
                    }
                });
                return value;
            });
            ngModel.$formatters.push(function(value) {
                if (ngModel.$isEmpty(value)) {
                    return value;
                }
                return value.toString();
            });
        }
    };
});

SIREPO.app.directive('varEditor', function(appState, latticeService, requestSender) {
    return {
        scope: {},
        template: [
            '<div class="modal fade" data-backdrop="static" id="sr-variables" tabindex="-1" role="dialog">',
              '<div class="modal-dialog">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
                    '<button type="button" class="close" data-ng-click="cancelChanges()"><span>&times;</span></button>',
                    '<span class="lead modal-title text-info">Variables</span>',
                  '</div>',
                  '<div class="modal-body" style="max-height: 80vh; overflow-y: scroll;">',
                    '<div class="container-fluid">',
                      '<form name="form" class="form-horizontal" autocomplete="off">',
                        '<div class="form-group form-group-sm">',
                          '<table class="table table-striped table-condensed">',
                            '<colgroup>',
                              '<col style="width: 25%">',
                              '<col style="width: 50%">',
                              '<col style="width: 25%">',
                              '<col>',
                            '</colgroup>',
                            '<thead>',
                              '<tr>',
                                '<th>Variable Name</th>',
                                '<th>Value</th>',
                                '<th> </th>',
                                '<th> </th>',
                              '</tr>',
                            '</thead>',
                            '<tbody>',
                              '<tr data-ng-repeat="var in appState.models.rpnVariables">',
                                '<td>{{ var.name }}</td>',
                                '<td><div class="row" data-field-editor="\'value\'" data-field-size="12" data-label-size="0" data-model-name="\'rpnVariable\'" data-model="var"></div></td>',
                                '<td><div class="col-sm-12" data-rpn-static="" data-model="var" data-field="\'value\'"></div></td>',
                                '<td style="vertical-align: middle">',
                                  '<button class="btn btn-danger btn-xs" data-ng-click="deleteVar($index)" title="Delete Variable"><span class="glyphicon glyphicon-remove"></span></button>',
                                '</td>',
                              '</tr>',
                              '<tr>',
                                '<td>',
                                  '<div class="row"><div class="col-sm-12">',
                                    '<input class="form-control" data-var-name="" data-ng-model="newVar.name" />',
                                  '</div></div>',
                                '</td>',
                                '<td>',
                                  '<div class="row" data-field-editor="\'value\'" data-field-size="12" data-label-size="0" data-model-name="\'rpnVariable\'" data-model="newVar"></div>',
                                '</td>',
                                '<td><div class="col-sm-12" data-rpn-static="" data-model="newVar" data-field="\'value\'"></div></td>',
                                '<td>',
                                  '<button class="btn btn-primary btn-xs" data-ng-disabled="! hasNewVar()" data-ng-click="addVar()" title="Add Variable"><span class="glyphicon glyphicon-plus"></span></button>',
                                '</td>',
                              '</tr>',
                            '</tbody>',
                          '</table>',
                        '</div>',
                        '<div class="row">',
                          '<div class="col-sm-6 pull-right">',
                            '<button data-ng-click="saveChanges()" class="btn btn-primary" data-ng-disabled="! form.$valid">Save Changes</button> ',
                            '<button data-ng-click="cancelChanges()" class="btn btn-default">Cancel</button>',
                          '</div>',
                        '</div>',
                      '</form>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {
            $scope.appState = appState;

            function initNewVar() {
                $scope.newVar = {
                    isOptional: true,
                };
                if ($scope.form) {
                    $scope.form.$setPristine();
                }
            }

            function nameExists(name) {
                return appState.models.rpnVariables.map(function(v) {
                    return v.name;
                }).indexOf(name) >= 0;
            }

            $scope.addVar = function() {
                if ($scope.hasNewVar()) {
                    var name = $scope.newVar.name;
                    if (nameExists(name)) {
                        $scope.newVar.name = appState.uniqueName(
                            appState.models.rpnVariables, 'name', name + '{}');
                    }
                    appState.models.rpnVariables.push({
                        name: $scope.newVar.name,
                        value: $scope.newVar.value,
                    });
                    initNewVar();
                }
            };

            $scope.cancelChanges = function() {
                $('#sr-variables').modal('hide');
                appState.cancelChanges('rpnVariables');
                appState.cancelChanges('rpnCache');
                initNewVar();
            };

            $scope.deleteVar = function(idx) {
                var v = appState.models.rpnVariables[idx];
                requestSender.getApplicationData(
                    {
                        method: 'validate_rpn_delete',
                        name: v.name,
                        variables: appState.models.rpnVariables,
                        simulationId: appState.models.simulation.simulationId,
                    },
                    function(data) {
                        latticeService.deleteVarWarning = '';
                        if (! appState.isLoaded()) {
                            return;
                        }
                        if (data.error) {
                            latticeService.deleteVarWarning = data.error;
                            $('#sr-var-in-use-dialog').modal('show');
                        }
                        else if (v == appState.models.rpnVariables[idx]) {
                            appState.models.rpnVariables.splice(idx, 1);
                        }
                    });
            };

            $scope.hasNewVar = function() {
                return 'name' in $scope.newVar
                    && 'value' in $scope.newVar
                    && $scope.newVar.name !== ''
                    && $scope.newVar.value !== '';
            };

            $scope.saveChanges = function() {
                $('#sr-variables').modal('hide');
                if ($scope.hasNewVar()) {
                    $scope.addVar();
                }
                appState.saveChanges(['rpnVariables', 'rpnCache']);
                initNewVar();
            };

            initNewVar();
        },
    };
});

SIREPO.app.directive('varName', function(latticeService) {
    return {
        restrict: 'A',
        require: 'ngModel',
        scope: {},
        link: function(scope, element, attrs, ngModel) {
            var latticeNames;

            function isElementOrCommandName(value) {
                if (! latticeNames) {
                    latticeNames = {};
                    for (var m in SIREPO.APP_SCHEMA.model) {
                        if (latticeService.isElementModelName(m)) {
                            latticeNames[m.toLowerCase()] = true;
                        }
                        else if (latticeService.isCommandModelName(m)) {
                            latticeNames[m.replace(latticeService.COMMAND_PREFIX, '').toLowerCase()] = true;
                        }
                    }
                }
                return latticeNames[value.toLowerCase()];
            }

            ngModel.$parsers.push(function(value) {
                if (ngModel.$isEmpty(value))  {
                    return null;
                }
                if (! value.match(/^[A-Z][A-Z0-9_.]*$/i)) {
                    return undefined;
                }
                if ((SIREPO.APP_SCHEMA.constants.latticeKeywords || []).includes(value.toLowerCase())) {
                    return undefined;
                }
                if (isElementOrCommandName(value)) {
                    return undefined;
                }
                return value;
            });
        }
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
