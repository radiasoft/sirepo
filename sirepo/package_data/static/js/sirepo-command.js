'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.factory('commandService', function(appState) {
    var self = {};
    var COMMAND_PREFIX = 'command_';

    self.commandFileExtension = function(command) {
        //TODO(pjm): each app will need to supply this - different for opal

        //TODO(pjm): keep in sync with template/elegant.py _command_file_extension()
        if (command) {
            if (command._type == 'save_lattice') {
                return '.lte';
            }
            else if (command._type == 'global_settings') {
                return '.txt';
            }
        }
        return '.sdds';
    };

    self.commandModelName = function(type) {
        return COMMAND_PREFIX + type;
    };

    self.isCommandModelName = function(name) {
        return name.indexOf(COMMAND_PREFIX) === 0;
    };

    return self;
});

SIREPO.app.directive('commandTab', function() {
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
            '<div data-element-picker="" data-controller="controller" data-title="New Command" data-id="sr-newCommand-editor" data-small-element-class="col-sm-3"></div>',
        ].join(''),
    };
});

SIREPO.app.directive('commandTable', function(appState, commandService, latticeService, panelState) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div class="sr-command-table">',
              '<div class="pull-right">',
                '<button class="btn btn-info btn-xs" data-ng-click="newCommand()" accesskey="c"><span class="glyphicon glyphicon-plus"></span> New <u>C</u>ommand</button>',
              '</div>',
              '<p class="lead text-center"><small><em>drag and drop commands or use arrows to reorder the list</em></small></p>',
              '<table class="table table-hover" style="width: 100%; table-layout: fixed">',
                '<tr data-ng-repeat="cmd in commands">',
                  '<td data-ng-drop="true" data-ng-drop-success="dropItem($index, $data)" data-ng-drag-start="selectItem($data)">',
                    '<div class="sr-button-bar-parent pull-right"><div class="sr-button-bar"><button class="btn btn-info btn-xs"  data-ng-disabled="$index == 0" data-ng-click="moveItem(-1, cmd)"><span class="glyphicon glyphicon-arrow-up"></span></button> <button class="btn btn-info btn-xs" data-ng-disabled="$index == commands.length - 1" data-ng-click="moveItem(1, cmd)"><span class="glyphicon glyphicon-arrow-down"></span></button> <button class="btn btn-info btn-xs sr-hover-button" data-ng-click="editCommand(cmd)">Edit</button> <button data-ng-click="expandCommand(cmd)" data-ng-disabled="isExpandDisabled(cmd)" class="btn btn-info btn-xs"><span class="glyphicon" data-ng-class="{\'glyphicon-chevron-up\': isExpanded(cmd), \'glyphicon-chevron-down\': ! isExpanded(cmd)}"></span></button> <button data-ng-click="deleteCommand(cmd)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div></div>',
                    '<div class="sr-command-icon-holder" data-ng-drag="true" data-ng-drag-data="cmd">',
                      '<a style="cursor: move; -moz-user-select: none; font-size: 14px" class="badge sr-badge-icon" data-ng-class="{\'sr-item-selected\': isSelected(cmd) }" href data-ng-click="selectItem(cmd)" data-ng-dblclick="editCommand(cmd)">{{ cmd._type }}</a>',
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
            $scope.commands = [];

            function commandDescription(cmd, commandIndex) {
                var schema = SIREPO.APP_SCHEMA.model[commandService.commandModelName(cmd._type)];
                var res = '';
                var model = commandForId(cmd._id);
                var fields = Object.keys(model).sort();
                for (var i = 0; i < fields.length; i++) {
                    var f = fields[i];
                    if (angular.isDefined(model[f]) && angular.isDefined(schema[f])) {
                        if (schema[f][2] != model[f]) {
                            res += (res.length ? ",\n" : '') + f + ' = ';
                            if (schema[f][1] == 'OutputFile') {
                                res += cmd._type
                                    + (commandIndex > 1 ? commandIndex : '')
                                    + '.' + f + commandService.commandFileExtension(model);
                            }
                            else if (schema[f][1] == 'LatticeBeamlineList') {
                                var el = latticeService.elementForId(model[f]);
                                if (el) {
                                    res += el.name;
                                }
                                else {
                                    res += '<missing beamline>';
                                }
                            }
                            else {
                                res += model[f];
                            }
                        }
                    }
                }
                return res;
            }

            function commandForId(id) {
                for (var i = 0; i < appState.models.commands.length; i++) {
                    var c = appState.models.commands[i];
                    if (c._id == id) {
                        return c;
                    }
                }
                return null;
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
                    });
                }
            }

            function saveCommands() {
                var commands = [];
                for (var i = 0; i < $scope.commands.length; i++) {
                    commands.push(commandForId($scope.commands[i]._id));
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

            $scope.deleteCommand = function(data) {
                if (! data) {
                    return;
                }
                $scope.selectItem(data);
                $('#sr-delete-command-confirmation').modal('show');
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
                var modelName = commandService.commandModelName(cmd._type);
                appState.models[modelName] = commandForId(cmd._id);
                panelState.showModalEditor(modelName);
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
                    return commandForId(selectedItemId)._type;
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
