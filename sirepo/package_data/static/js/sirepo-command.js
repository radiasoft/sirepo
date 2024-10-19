'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="OutputFile" data-ng-class="fieldClass">
          <div data-output-file-field="field" data-model="model"></div>
        </div>
        <div data-ng-switch-when="MultiOutputFile" data-ng-class="fieldClass">
          <div data-output-file-field="field" data-model="model" data-is-multi="1"></div>
        </div>
    `;
});

SIREPO.app.factory('commandService', function(appState, latticeService, panelState, validationService) {
    var self = {};
    self.deleteCommandWarning = '';

    self.canDeleteCommand = function(command) {
        return true;
    };

    self.createCommand = function(name) {
        var model = {
            _id: latticeService.nextId(),
            _type: name,
            name: latticeService.uniqueNameForType(name.substring(0, 2).toUpperCase()),
        };
        appState.setModelDefaults(model, self.commandModelName(name));
        var modelName = self.commandModelName(model._type);
        appState.models[modelName] = model;
        return modelName;
    };

    self.commandFileExtension = function(command) {
        //TODO(pjm): each app will need to supply this
        return '';
    };

    self.commandForId = function(id) {
        for (var i = 0; i < appState.models.commands.length; i++) {
            var c = appState.models.commands[i];
            if (c._id == id) {
                return c;
            }
        }
        return null;
    };

    self.commandModelName = latticeService.commandModelName;

    self.editCommand = function(item) {
        var modelName = self.commandModelName(item._type);
        appState.models[modelName] = self.commandForId(item._id) || item;
        if (latticeService.includeCommandNames) {
            latticeService.setValidator(modelName, item);
        }
        panelState.showModalEditor(modelName);
    };

    self.findAllComands =  function(type) {
        return appState.models.commands.filter(function(cmd) {
            return cmd._type == type;
        });
    };

    self.findFirstCommand = function(type) {
        var res;
        appState.models.commands.some(function(cmd) {
            if (cmd._type == type) {
                res = cmd;
                return true;
            }
        });
        return res;
    };

    self.formatCommandName = function(cmd) {
        return cmd._type;
    };

    self.formatFieldValue = function(value, type) {
        return value;
    };

    self.getNextCommand = type => {
         return {
             _id: latticeService.nextId(),
             type: type,
             name: latticeService.uniqueNameForType(type.substring(0, 2).toUpperCase()),
         };
    };


    self.isCommandModelName = latticeService.isCommandModelName;

    return self;
});

SIREPO.app.directive('commandTab', function(latticeService, commandService) {
    return {
        restrict: 'A',
        scope: {
            controller: '=',
        },
        template: `
            <div class="container-fluid">
              <div class="row">
                <div class="col-md-10 col-md-offset-1 col-xl-8 col-xl-offset-2">
                  <div class="sr-command-panel panel panel-info">
                    <div class="panel-heading"><span class="sr-panel-heading">Commands</span></div>
                    <div class="panel-body">
                      <div data-command-table=""></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div data-var-editor=""></div>
            <div data-confirmation-modal="" data-id="sr-var-in-use-dialog" data-title="Variable in Use" data-ok-text="" data-cancel-text="Close">{{ latticeService.deleteVarWarning  }} and can not be deleted.</div>
            <div data-confirmation-modal="" data-id="sr-command-in-use-dialog" data-title="Command in Use" data-ok-text="" data-cancel-text="Close">{{ commandService.deleteCommandWarning  }} and can not be deleted.</div>
            <div data-element-picker="" data-controller="controller" data-title="New Command" data-id="sr-newCommand-editor" data-small-element-class="col-sm-3"></div>
        `,
        controller: function($scope) {
            $scope.latticeService = latticeService;
            $scope.commandService = commandService;
        },
    };
});

SIREPO.app.directive('commandTable', function(appState, commandService, latticeService, panelState) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div class="sr-command-table">
            <div class="pull-right">
                <button data-ng-if=":: wantRpnVariables" class="btn btn-info btn-xs" data-ng-click="latticeService.showRpnVariables()"><span class="glyphicon glyphicon-list-alt"></span> Variables</button>
                <button class="btn btn-info btn-xs" data-ng-click="newCommand()" accesskey="c"><span class="glyphicon glyphicon-plus"></span> New <u>C</u>ommand</button>
              </div>
              <p class="lead text-center"><small><em>drag and drop commands or use arrows to reorder the list</em></small></p>
              <table class="table table-condensed" style="width: 100%; table-layout: fixed">
                <tr data-ng-repeat="cmd in commands" data-ng-class="{'sr-disabled-item': cmd.isDisabled == '1'}">
                  <td>
                    <div data-sr-item-holder="" data-handle-drop="dropItem($index, item)" data-handle-dragenter="dragEnter()">
                      <div data-ng-class="{'sr-move-after': cmd.isMoveAfter, 'sr-move-before': ! cmd.isMoveAfter}">
                        <div class="sr-item" data-ng-class="{'sr-row-drag': cmd.isDragging}">
                          <div class="sr-button-bar-parent pull-right"><div class="sr-button-bar" data-ng-class="{'sr-disabled-item': cmd.isDisabled == '1'}"><button class="btn btn-info btn-xs" data-ng-disabled="$index == 0" data-ng-click="moveItem(-1, cmd)" title="Move item up"><span class="glyphicon glyphicon-arrow-up"></span></button> <button class="btn btn-info btn-xs" data-ng-disabled="$index == commands.length - 1" data-ng-click="moveItem(1, cmd)" title="Move item down"><span class="glyphicon glyphicon-arrow-down"></span></button> <button class="btn btn-info btn-xs sr-hover-button" data-ng-click="copyCommand(cmd)">Copy</button> <button class="btn btn-info btn-xs sr-hover-button" data-ng-click="editCommand(cmd)">Edit</button> <button data-ng-click="toggleDisableCommand(cmd)" class="btn btn-info btn-xs"><span class="glyphicon" data-ng-class="{'glyphicon-ok-circle': cmd.isDisabled == '1', 'glyphicon-ban-circle': cmd.isDisabled == '0'}" data-ng-attr-title="{{ enableItemToggleTitle(cmd) }}"></span></button> <button data-ng-click="expandCommand(cmd)" data-ng-disabled="isExpandDisabled(cmd)" class="btn btn-info btn-xs" data-ng-attr-title="{{ expandCommandTitle(cmd) }}"><span class="glyphicon" data-ng-class="{'glyphicon-chevron-up': isExpanded(cmd), 'glyphicon-chevron-down': ! isExpanded(cmd)}"></span></button> <button data-ng-click="deleteCommand(cmd)" class="btn btn-danger btn-xs" title="Delete item"><span class="glyphicon glyphicon-remove"></span></button></div></div>
                          <div class="badge sr-badge-icon sr-item-badge" data-sr-draggable="cmd" data-handle-selected="selectItem(item)" data-ng-class="{'sr-item-selected': isSelected(cmd)}" data-ng-dblclick="editCommand(cmd)">{{ commandName(cmd) }}</div>
                          <div data-ng-show="! isExpanded(cmd) && cmd.description" style="margin-left: 3em; margin-right: 1em; color: #777; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ cmd.description }}</div>
                          <div data-ng-show="isExpanded(cmd) && cmd.description" style="color: #777; margin-left: 3em; white-space: pre-wrap">{{ cmd.description }}</div>
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
                <tr><td><div data-sr-item-holder="" data-handle-drop="dropLast(item)" data-handle-dragenter="dragEnter()"></div></td></tr>
              </table>
              <div data-ng-show="commands.length > 2" class="pull-right">
                <button class="btn btn-info btn-xs" data-ng-click="newCommand()" accesskey="c"><span class="glyphicon glyphicon-plus"></span> New <u>C</u>ommand</button>
              </div>
            </div>
            <div data-confirmation-modal="" data-id="sr-delete-command-confirmation" data-title="Delete Command?" data-ok-text="Delete" data-ok-clicked="deleteSelected()">Delete command &quot;{{ selectedItemName() }}&quot;?</div>
        `,
        controller: function($scope) {
            var selectedItemId = null;
            var expanded = {};
            $scope.latticeService = latticeService;
            $scope.commands = [];
            $scope.wantRpnVariables = SIREPO.APP_SCHEMA.model.rpnVariable ? true : false;

            function commandDescription(cmd, commandIndex) {
                var schema = SIREPO.APP_SCHEMA.model[commandService.commandModelName(cmd._type)];
                var res = '';
                var model = commandService.commandForId(cmd._id);
                var fields = Object.keys(model).sort();
                for (var i = 0; i < fields.length; i++) {
                    var f = fields[i];
                    if (f === 'isDisabled' || (commandService.hideCommandName && f == 'name')) {
                        continue;
                    }
                    if (angular.isDefined(model[f]) && angular.isDefined(schema[f])) {
                        if (schema[f][2] != model[f]) {
                            res += (res.length ? ",\n" : '') + f + ' = ';
                            if (schema[f][1] == 'OutputFile') {
                                res += cmd._type
                                    + (commandIndex > 1 ? commandIndex : '')
                                    + '.' + f + commandService.commandFileExtension(model);
                            }
                            else if (schema[f][1] == 'Boolean'|| schema[f][1] == 'OptionalBoolean') {
                                res += model[f] == '1' ? 'true': 'false';
                            }
                            else if (schema[f][1].indexOf('LatticeBeamlineList') >= 0) {
                                var el = latticeService.elementForId(model[f]);
                                if (el) {
                                    res += el.name;
                                }
                                else {
                                    res += '<missing beamline>';
                                }
                            }
                            else {
                                res += commandService.formatFieldValue(model[f], schema[f][1]);
                            }
                        }
                    }
                }
                return res;
            }

            function commandIndex(data) {
                return $scope.commands.findIndex(cmd => cmd._id == data._id);
            }

            function loadCommands() {
                var commands = appState.applicationState().commands;
                $scope.commands = [];
                var commandIndex = {};
                for (var i = 0; i < commands.length; i++) {
                    var cmd = commands[i];
                    if (cmd._type in commandIndex) {
                        commandIndex[cmd._type]++;
                    }
                    else {
                        commandIndex[cmd._type] = 1;
                    }
                    $scope.commands.push({
                        sim_type: SIREPO.APP_SCHEMA.simulationType,
                        sim_id: appState.models.simulation.simulationId,
                        _type: cmd._type,
                        _id: cmd._id,
                        description: commandDescription(cmd, commandIndex[cmd._type]),
                        name: cmd.name,
                        isDisabled: cmd.isDisabled,
                        command: appState.clone(cmd),
                    });
                }
            }

            function saveCommands() {
                const commands = [];
                for (var i = 0; i < $scope.commands.length; i++) {
                    const cmd = commandService.commandForId($scope.commands[i]._id);
                    cmd.isDisabled = $scope.commands[i].isDisabled === '1' ? '1' : '0';
                    commands.push(cmd);
                }
                appState.models.commands = commands;
                appState.saveChanges('commands');
            }

            function selectedItemIndex() {
                if (selectedItemId) {
                    for (var i = 0; i < $scope.commands.length; i++) {
                        if ($scope.commands[i]._id == selectedItemId) {
                            return i;
                        }
                    }
                }
                return -1;
            }

            $scope.copyCommand = cmd => {
                $scope.editCommand({...commandService.commandForId(cmd._id), ...commandService.getNextCommand(cmd._type)});
            };

            $scope.commandName = function(cmd) {
                return commandService.formatCommandName(cmd);
            };

            $scope.deleteCommand = function(data) {
                if (! data) {
                    return;
                }
                $scope.selectItem(data);
                if (commandService.canDeleteCommand(data)) {
                    $('#sr-delete-command-confirmation').modal('show');
                }
                else {
                    //TODO(pjm): set commandService.deleteCommandWarning
                    $('#sr-command-in-use-dialog').modal('show');
                }
            };

            $scope.deleteSelected = function() {
                var index = selectedItemIndex();
                if (index >= 0) {
                    selectedItemId = null;
                    $scope.commands.splice(index, 1);
                    saveCommands();
                }
            };

            $scope.dropItem = function(index, data) {
                if (! data) {
                    return;
                }
                if (data.sim_type !== SIREPO.APP_SCHEMA.simulationType) {
                    return;
                }
                if (data.sim_id !== appState.models.simulation.simulationId) {
                    // item dropped from another simulation window
                    data.command._id = latticeService.nextId();
                    data._id = data.command._id;
                    data.sim_id = appState.models.simulation.simulationId;
                    appState.models.commands.splice(index, 0, data.command);
                }
                else {
                    const prevIndex = commandIndex(data);
                    if (prevIndex < 0 || prevIndex === index) {
                        return;
                    }
                    $scope.commands.splice(prevIndex, 1);
                }
                $scope.commands.splice(index, 0, data);
                $scope.selectItem(data);
                saveCommands();
            };

            // expects a negative number to move up, positive to move down
            $scope.moveItem = function(direction, command) {
                var d = direction == 0 ? 0 : (direction > 0 ? 1 : -1);
                var currentIndex = commandIndex(command);
                var newIndex = currentIndex + d;
                if(newIndex >= 0 && newIndex < $scope.commands.length) {
                    var tmp = $scope.commands[newIndex];
                    $scope.commands[newIndex] = command;
                    $scope.commands[currentIndex] = tmp;
                    saveCommands();
                }
            };

             $scope.dragEnter = () => {
                 // detect dragging from outside this browser and clear selected item
                 if (! $scope.commands.some(r => r.isDragging)) {
                     $scope.selectItem(null);
                 }
             };

            $scope.dropLast = function(data) {
                $scope.dropItem($scope.commands.length, data);
            };

            $scope.editCommand = function(cmd) {
                commandService.editCommand(cmd);
            };

            $scope.enableItemToggleTitle = cmd => {
                return cmd.isDisabled === '1' ? 'Enable item' : 'Disable item';
            };

            $scope.expandCommand = function(cmd) {
                expanded[cmd._id] = ! expanded[cmd._id];
            };

            $scope.expandCommandTitle = cmd => {
                return $scope.isExpanded(cmd) ? 'Collapse item' : 'Expand item';
            };

            $scope.isExpandDisabled = function(cmd) {
                if (cmd.description && cmd.description.indexOf("\n") > 0) {
                    return false;
                }
                return true;
            };

            $scope.isExpanded = function(cmd) {
                return expanded[cmd._id];
            };

            $scope.isSelected = function(cmd) {
                return selectedItemId == cmd._id;
            };

            $scope.newCommand = function() {
                $('#' + panelState.modalId('newCommand')).modal('show');
            };

            $scope.selectItem = function(data) {
                selectedItemId = data ? data._id : null;
                let found = false;
                $scope.commands.forEach(cmd => {
                    if (cmd && cmd._id == selectedItemId) {
                        found = true;
                    }
                    else {
                        cmd.isMoveAfter = found;
                    }
                });
            };

            $scope.selectedItemName = function() {
                if (selectedItemId) {
                    return commandService.commandForId(selectedItemId)._type;
                }
                return '';
            };

            $scope.toggleDisableCommand = cmd => {
                cmd.isDisabled = cmd.isDisabled === '1' ? '0' : '1';
                saveCommands();
            };

            appState.whenModelsLoaded($scope, function() {
                $scope.$on('modelChanged', function(e, name) {
                    if (name == 'commands') {
                        loadCommands();
                    }
                    if (commandService.isCommandModelName(name)) {
                        var foundIt = false;
                        for (var i = 0; i < $scope.commands.length; i++) {
                            if ($scope.commands[i]._id == appState.models[name]._id) {
                                foundIt = true;
                                break;
                            }
                        }
                        if (! foundIt) {
                            var index = selectedItemIndex();
                            if (index >= 0) {
                                appState.models.commands.splice(index + 1, 0, appState.models[name]);
                            }
                            else {
                                appState.models.commands.push(appState.models[name]);
                            }
                            $scope.selectItem(appState.models[name]);
                        }
                        appState.removeModel(name);
                        appState.saveChanges('commands');
                    }
                });
                $scope.$on('cancelChanges', function(e, name) {
                    if (commandService.isCommandModelName(name)) {
                        appState.removeModel(name);
                        appState.cancelChanges('commands');
                    }
                });
                loadCommands();
            });
        },
    };
});

SIREPO.app.directive('outputFileField', function(appState, commandService) {
    return {
        restrict: 'A',
        scope: {
            field: '=outputFileField',
            model: '=',
            isMulti: '@',
        },
        template: `
            <select class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in items()"></select>
        `,
        controller: function($scope) {
            var items = [];
            var filename = '';

            $scope.items = function() {
                if (! $scope.model) {
                    return items;
                }
                var prefix = $scope.model.name;
                if ($scope.model._type) {
                    var index = 0;
                    for (var i = 0; i < appState.models.commands.length; i++) {
                        var m = appState.models.commands[i];
                        if (m._type == $scope.model._type) {
                            index++;
                            if (m == $scope.model) {
                                break;
                            }
                        }
                    }
                    prefix = $scope.model._type + (index > 1 ? index : '');
                }
                var ext = commandService.commandFileExtension($scope.model);
                var name = prefix + '.' + $scope.field + ($scope.isMulti ? '-%03ld' : '') + ext;
                if (name != filename) {
                    filename = name;
                    items = [
                        ['', 'None'],
                        ['1', name],
                    ];
                }
                return items;
            };
        },
    };
});
