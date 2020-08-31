'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="OutputFile" data-ng-class="fieldClass">',
          '<div data-output-file-field="field" data-model="model"></div>',
        '</div>',
    ].join('');
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
        appState.models[modelName] = self.commandForId(item._id);
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

    self.isCommandModelName = latticeService.isCommandModelName;

    return self;
});

SIREPO.app.directive('commandTab', function(latticeService, commandService) {
    return {
        restrict: 'A',
        scope: {
            controller: '=',
        },
        template: [
            '<div class="container-fluid">',
              '<div class="row">',
                '<div class="col-md-8 col-md-offset-2 col-xl-6 col-xl-offset-3">',
                  '<div class="panel panel-info">',
                    '<div class="panel-heading"><span class="sr-panel-heading">Commands</span></div>',
                    '<div class="panel-body">',
                      '<div data-command-table=""></div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
            '<div data-var-editor=""></div>',
            '<div data-confirmation-modal="" data-id="sr-var-in-use-dialog" data-title="Variable in Use" data-ok-text="" data-cancel-text="Close">{{ latticeService.deleteVarWarning  }} and can not be deleted.</div>',
            '<div data-confirmation-modal="" data-id="sr-command-in-use-dialog" data-title="Command in Use" data-ok-text="" data-cancel-text="Close">{{ commandService.deleteCommandWarning  }} and can not be deleted.</div>',
            '<div data-element-picker="" data-controller="controller" data-title="New Command" data-id="sr-newCommand-editor" data-small-element-class="col-sm-3"></div>',
        ].join(''),
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
        template: [
            '<div class="sr-command-table">',
            '<div class="pull-right">',
                '<button data-ng-if=":: wantRpnVariables" class="btn btn-info btn-xs" data-ng-click="latticeService.showRpnVariables()"><span class="glyphicon glyphicon-list-alt"></span> Variables</button> ',
                '<button class="btn btn-info btn-xs" data-ng-click="newCommand()" accesskey="c"><span class="glyphicon glyphicon-plus"></span> New <u>C</u>ommand</button>',
              '</div>',
              '<p class="lead text-center"><small><em>drag and drop commands or use arrows to reorder the list</em></small></p>',
              '<table class="table table-hover" style="width: 100%; table-layout: fixed">',
                '<tr data-ng-repeat="cmd in commands">',
                  '<td data-ng-drop="true" data-ng-drop-success="dropItem($index, $data)" data-ng-drag-start="selectItem($data)">',
                    '<div class="sr-button-bar-parent pull-right"><div class="sr-button-bar"><button class="btn btn-info btn-xs"  data-ng-disabled="$index == 0" data-ng-click="moveItem(-1, cmd)"><span class="glyphicon glyphicon-arrow-up"></span></button> <button class="btn btn-info btn-xs" data-ng-disabled="$index == commands.length - 1" data-ng-click="moveItem(1, cmd)"><span class="glyphicon glyphicon-arrow-down"></span></button> <button class="btn btn-info btn-xs sr-hover-button" data-ng-click="editCommand(cmd)">Edit</button> <button data-ng-click="expandCommand(cmd)" data-ng-disabled="isExpandDisabled(cmd)" class="btn btn-info btn-xs"><span class="glyphicon" data-ng-class="{\'glyphicon-chevron-up\': isExpanded(cmd), \'glyphicon-chevron-down\': ! isExpanded(cmd)}"></span></button> <button data-ng-click="deleteCommand(cmd)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div></div>',
                    '<div class="sr-command-icon-holder" data-ng-drag="true" data-ng-drag-data="cmd">',
                      '<a style="cursor: move; -moz-user-select: none; font-size: 14px" class="badge sr-badge-icon" data-ng-class="{\'sr-item-selected\': isSelected(cmd) }" href data-ng-click="selectItem(cmd)" data-ng-dblclick="editCommand(cmd)">{{ commandName(cmd) }}</a>',
                    '</div>',
                    '<div data-ng-show="! isExpanded(cmd) && cmd.description" style="margin-left: 3em; margin-right: 1em; color: #777; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ cmd.description }}</div>',
                    '<div data-ng-show="isExpanded(cmd) && cmd.description" style="color: #777; margin-left: 3em; white-space: pre-wrap">{{ cmd.description }}</div>',
                  '</td>',
                '</tr>',
                '<tr><td style="height: 3em" data-ng-drop="true" data-ng-drop-success="dropLast($data)"> </td></tr>',
              '</table>',
              '<div data-ng-show="commands.length > 2" class="pull-right">',
                '<button class="btn btn-info btn-xs" data-ng-click="newCommand()" accesskey="c"><span class="glyphicon glyphicon-plus"></span> New <u>C</u>ommand</button>',
              '</div>',
            '</div>',
            '<div data-confirmation-modal="" data-id="sr-delete-command-confirmation" data-title="Delete Command?" data-ok-text="Delete" data-ok-clicked="deleteSelected()">Delete command &quot;{{ selectedItemName() }}&quot;?</div>',
        ].join(''),
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
                    if (commandService.hideCommandName && f == 'name') {
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
                return $scope.commands.indexOf(data);
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
                        _type: cmd._type,
                        _id: cmd._id,
                        description: commandDescription(cmd, commandIndex[cmd._type]),
                        name: cmd.name,
                    });
                }
            }

            function saveCommands() {
                var commands = [];
                for (var i = 0; i < $scope.commands.length; i++) {
                    commands.push(commandService.commandForId($scope.commands[i]._id));
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
                var i = commandIndex(data);
                data = $scope.commands.splice(i, 1)[0];
                if (i < index) {
                    index--;
                }
                $scope.commands.splice(index, 0, data);
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

            $scope.dropLast = function(data) {
                if (! data) {
                    return;
                }
                data = $scope.commands.splice(commandIndex(data), 1)[0];
                $scope.commands.push(data);
                saveCommands();
            };

            $scope.editCommand = function(cmd) {
                commandService.editCommand(cmd);
            };

            $scope.isExpanded = function(cmd) {
                return expanded[cmd._id];
            };

            $scope.expandCommand = function(cmd) {
                expanded[cmd._id] = ! expanded[cmd._id];
            };

            $scope.isExpandDisabled = function(cmd) {
                if (cmd.description && cmd.description.indexOf("\n") > 0) {
                    return false;
                }
                return true;
            };

            $scope.isSelected = function(cmd) {
                return selectedItemId == cmd._id;
            };

            $scope.newCommand = function() {
                $('#' + panelState.modalId('newCommand')).modal('show');
            };

            $scope.selectItem = function(cmd) {
                selectedItemId = cmd._id;
            };

            $scope.selectedItemName = function() {
                if (selectedItemId) {
                    return commandService.commandForId(selectedItemId)._type;
                }
                return '';
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
        },
        template: [
            '<select class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in items()"></select>',
        ].join(''),
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
                var name = prefix + '.' + $scope.field + ext;
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
