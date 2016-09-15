'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.NUMBER_REGEXP = /^\s*(\-|\+)?(\d+|(\d*(\.\d*)))([eE][+-]?\d+)?\s*$/;

SIREPO.app.directive('advancedEditorPane', function(appState, $timeout) {
    return {
        scope: {
            viewName: '=',
            isReadOnly: '=',
            parentController: '=',
            wantButtons: '@',
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
            // 'basic' or 'advanced' (default)
            fieldDef: '@',
        },
        template: [
            '<h5 data-ng-if="description">{{ description }}</h5>',
            '<form name="form" class="form-horizontal" novalidate>',
              '<ul data-ng-if="pages" class="nav nav-tabs">',
                '<li data-ng-repeat="page in pages" role="presentation" data-ng-class="{active: page.isActive}"><a href data-ng-click="setActivePage(page)">{{ page.name }}</a></li>',
              '</ul>',
              '<br data-ng-if="pages" />',
              '<div data-ng-repeat="f in (activePage ? activePage.items : advancedFields)">',
                '<div class="form-group form-group-sm" data-ng-if="! isColumnField(f)" data-model-field="f" data-model-name="modelName" data-model-data="modelData" data-is-read-only="isReadOnly"></div>',
                '<div data-ng-if="isColumnField(f)" data-column-editor="" data-column-fields="f" data-model-name="modelName" data-model-data="modelData" data-is-read-only="isReadOnly"></div>',
              '</div>',
              '<div data-ng-if="wantButtons" data-buttons="" data-model-name="modelName" data-model-data="modelData" data-fields="advancedFields"></div>',
            '</form>',
        ].join(''),
        controller: function($scope) {
            var viewInfo = appState.viewInfo($scope.viewName);
            var i;
            $scope.modelName = viewInfo.model || $scope.viewName;
            $scope.description = viewInfo.description;
            $scope.advancedFields = viewInfo[$scope.fieldDef || 'advanced'];

            $scope.isColumnField = function(f) {
                return typeof(f) == 'string' ? false : true;
            };

            $scope.setActivePage = function(page) {
                if ($scope.activePage)
                    $scope.activePage.isActive = false;
                $scope.activePage = page;
                page.isActive = true;
                if ($scope.parentController && $scope.parentController.handleModalShown) {
                    // invoke parentController after UI has been constructed
                    $timeout(function() {
                        $scope.parentController.handleModalShown($scope.modelName);
                    });
                }
            };
            // named tabs
            if ($scope.advancedFields.length && $scope.isColumnField($scope.advancedFields[0]) && ! $scope.isColumnField($scope.advancedFields[0][0])) {
                $scope.pages = [];
                for (i = 0; i < $scope.advancedFields.length; i++) {
                    var page = {
                        name: $scope.advancedFields[i][0],
                        items: [],
                    };
                    $scope.pages.push(page);
                    var fields = $scope.advancedFields[i][1];
                    for (var j = 0; j < fields.length; j++)
                        page.items.push(fields[j]);
                }
            }
            // fieldsPerTab
            else if (viewInfo.fieldsPerTab && $scope.advancedFields.length > viewInfo.fieldsPerTab) {
                $scope.pages = [];
                var index = 0;
                var items;
                for (i = 0; i < $scope.advancedFields.length; i++) {
                    if (i % viewInfo.fieldsPerTab === 0) {
                        index += 1;
                        items = [];
                        $scope.pages.push({
                            name: 'Page ' + index,
                            items: items,
                        });
                    }
                    items.push($scope.advancedFields[i]);
                }
            }
            if ($scope.pages)
                $scope.setActivePage($scope.pages[0]);
        },
        link: function(scope, element) {
            var resetActivePage = function() {
                if (scope.pages)
                    scope.setActivePage(scope.pages[0]);
            };
            if (scope.pages) {
                $(element).closest('.modal').on('show.bs.modal', resetActivePage);
                //TODO(pjm): need a generalized case for this
                $(element).closest('.srw-editor-holder').on('s.resetActivePage', resetActivePage);
            }
        }
    };
});

SIREPO.app.directive('srAlert', function(appState) {
    return {
        restrict: 'A',
        scope: {
            alertText: '=',
        },
        template: [
            '<div data-ng-show="alertText()" class="alert alert-warning alert-dismissible" role="alert">',
              '<button type="button" class="close" data-dismiss="alert" aria-label="Close">',
                '<span aria-hidden="true">&times;</span>',
              '</button>',
              '<strong>{{ alertText() }}</strong>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            //TODO(robnagler) timeout the alert
            //TODO(robnagler) bind to value in appState or vice versa
            $scope.alertText = function() {
                return appState.alertText();
            };
            return;
        },
    };
});

SIREPO.app.directive('basicEditorPanel', function(appState, panelState) {
    return {
        scope: {
            viewName: '@',
        },
        template: [
            '<div class="panel panel-info" id="{{ \'s-\' + viewName + \'-basicEditor\' }}">',
              '<div class="panel-heading clearfix" data-panel-heading="{{ panelTitle }}" data-model-key="modelName"></div>',
                '<div class="panel-body" data-ng-hide="panelState.isHidden(modelName)">',
                  //TODO(pjm): not really an advanced editor pane anymore, should get renamed
                  '<div data-advanced-editor-pane="" data-view-name="viewName" data-want-buttons="true" data-field-def="basic"></div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var viewInfo = appState.viewInfo($scope.viewName);
            $scope.modelName = viewInfo.model || $scope.viewName;
            $scope.panelState = panelState;
            $scope.panelTitle = viewInfo.title;
        },
    };
});

SIREPO.app.directive('buttons', function(appState) {
    return {
        scope: {
            modelName: '=',
            fields: '=',
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
        },
        template: [
            '<div class="col-sm-6 pull-right" data-ng-show="form.$dirty">',
              '<button data-ng-click="saveChanges()" class="btn btn-primary" data-ng-class="{\'disabled\': ! form.$valid}">Save Changes</button> ',
              '<button data-ng-click="cancelChanges()" class="btn btn-default">Cancel</button>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.form = $scope.$parent.form;
            var modelKey = $scope.modelName;

            if ($scope.modelData)
                modelKey = $scope.modelData.modelKey;

            function extractModel(field, modelNames) {
                var modelField = appState.parseModelField(field);
                if (modelField)
                    modelNames[modelField[0]] = true;
            }

            function iterateFields(field) {
                var i;
                // may be a string field, [tab-name, [cols]], or [[col-header, [cols]], [col-header, [cols]]]
                if (typeof(field) == 'string')
                    extractModel(field, modelNames);
                else {
                    // [name, [cols]]
                    if (typeof(field[0]) == 'string') {
                        for (i = 0; i < field[1].length; i++)
                            iterateFields(field[1][i]);
                    }
                    // [[name, [cols]], [name, [cols]], ...]
                    else {
                        for (i = 0; i < field.length; i++)
                            iterateFields(field[i]);
                    }
                }
            }

            var modelNames = {};
            modelNames[modelKey] = true;
            for (var i = 0; i < $scope.fields.length; i++)
                iterateFields($scope.fields[i]);
            modelNames = Object.keys(modelNames);

            function changeDone() {
                $scope.form.$setPristine();
            }
            $scope.saveChanges = function() {
                if ($scope.form.$valid)
                    appState.saveChanges(modelNames);
            };
            $scope.cancelChanges = function() {
                appState.cancelChanges(modelNames);
            };
            $scope.$on(modelKey + '.changed', changeDone);
            $scope.$on('cancelChanges', changeDone);
        }
    };
});

SIREPO.app.directive('confirmationModal', function() {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            id: '@',
            title: '@',
            okText: '@',
            okClicked: '&',
            cancelText: '@',
        },
        template: [
            '<div class="modal fade" id="{{ id }}" tabindex="-1" role="dialog">',
              '<div class="modal-dialog">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-warning">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<span class="lead modal-title text-info">{{ title }}</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<div class="row">',
                        '<div class="col-sm-12">',
                          '<div data-ng-transclude=""></div>',
                        '</div>',
                      '</div>',
                      '<div class="row">',
                        '<div class="col-sm-6 pull-right" style="margin-top: 1em">',
                          '<button data-ng-if="okText" data-dismiss="modal" data-ng-click="okClicked()" class="btn btn-default">{{ okText }}</button>',
                          ' <button data-dismiss="modal" class="btn btn-default">{{ cancelText || \'Cancel\' }}</button>',
                        '</div>',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
    };
});

SIREPO.app.directive('labelWithTooltip', function() {
    return {
        restrict: 'A',
        scope: {
            'label': '@',
            'tooltip': '@',
        },
        template: [
            '<label>{{ label }} <span data-ng-show="tooltip" class="glyphicon glyphicon-info-sign s-info-pointer"></span></label>',
        ],
        link: function link(scope, element) {
            if (scope.tooltip) {
                $(element).find('span').tooltip({
                    title: function() {
                        return scope.tooltip;
                    },
                    placement: 'bottom',
                });
            }
        },
    };
});

SIREPO.app.directive('fieldEditor', function(appState, panelState, requestSender, rpnService) {
    return {
        restirct: 'A',
        scope: {
            modelName: '=',
            field: '=fieldEditor',
            model: '=',
            customLabel: '=',
            labelSize: "@",
            fieldSize: "@",
            isReadOnly: "=",
        },
        template: [
            '<div class="model-{{modelName}}-{{field}}">',
            '<div data-ng-show="showLabel()" data-label-with-tooltip="" class="control-label" data-ng-class="labelClass" data-label="{{ customLabel || info[0] }}" data-tooltip="{{ info[3] }}"></div>',
            '<div data-ng-switch="info[1]">',
              '<div data-ng-switch-when="BeamList" data-ng-class="fieldClass">',
                '<div class="dropdown">',
                  '<button class="btn btn-default dropdown-toggle form-control" type="button" data-toggle="dropdown">{{ model[field] }} <span class="caret"></span></button>',
                  '<ul class="dropdown-menu">',
                    '<li class="dropdown-header">Predefined Electron Beams</li>',
                    '<li data-ng-repeat="item in requestSender.getAuxiliaryData(\'beams\') track by item.name">',
                      '<a href data-ng-click="srwSelectBeam(item)">{{ item.name }}</a>',
                    '</li>',
                    '<li class="divider"></li>',
                    '<li class="dropdown-header">User Defined Electron Beams</li>',
                    '<li data-ng-repeat="item in appState.models.electronBeams track by item.name">',
                      '<a href data-ng-click="srwSelectBeam(item)">{{ item.name }}</a>',
                    '</li>',
                    '<li><a href data-ng-click="srwNewUserDefinedBeam()"><span class="glyphicon glyphicon-plus"></span> New</a></li>',
                  '</ul>',
                '</div>',
              '</div>',
              '<div data-ng-switch-when="Float" data-ng-class="fieldClass">',
                '<input data-string-to-number="" data-ng-model="model[field]" class="form-control" style="text-align: right" required data-ng-readonly="isReadOnly" />',
              '</div>',
              '<div data-ng-switch-when="Integer" data-ng-class="fieldClass">',
                '<input data-string-to-number="integer" data-ng-model="model[field]" class="form-control" style="text-align: right" required data-ng-readonly="isReadOnly" />',
              '</div>',
              '<div data-ng-switch-when="MirrorFile" class="col-sm-7">',
                '<div data-file-field="field" data-file-type="mirror" data-want-file-report="true" data-model="model" data-selection-required="modelName == \'mirror\'" data-empty-selection-text="No Mirror Error"></div>',
              '</div>',
              '<div data-ng-switch-when="MagneticZipFile" class="col-sm-7">',
                '<div data-file-field="field" data-file-type="undulatorTable" data-model="model" data-selection-required="true" data-empty-selection-text="Select Magnetic Zip File"></div>',
              '</div>',
              '<div data-ng-switch-when="String" data-ng-class="fieldClass">',
                '<input data-ng-model="model[field]" class="form-control" required data-ng-readonly="isReadOnly" />',
              '</div>',
              '<div data-ng-switch-when="StringArray" data-ng-class="fieldClass">',
                '<input data-ng-model="model[field]" class="form-control" required data-ng-readonly="isReadOnly" />',
              '</div>',
              '<div data-ng-switch-when="InputFile" class="col-sm-7">',
                '<div data-file-field="field" data-model="model" data-model-name="modelName" data-empty-selection-text="No File Selected"></div>',
              '</div>',
              '<div data-ng-switch-when="InputFileXY" class="col-sm-7">',
                  '<div style="display: inline-block" data-file-field="field" data-model="model" data-model-name="modelName" data-empty-selection-text="No File Selected"></div>',
                  ' <label style="margin: 0 1ex">X</label> ',
                  '<input data-ng-model="model[fieldX()]" style="display: inline-block; width: 8em" class="form-control" />',
                  ' <label style="margin: 0 1ex">Y</label> ',
                  '<input data-ng-model="model[fieldY()]" style="display: inline-block; width: 8em" class="form-control" />',
              '</div>',
              '<div data-ng-switch-when="BeamInputFile" class="col-sm-7">',
                '<div data-file-field="field" data-model="model" data-file-type="bunchFile-sourceFile" data-empty-selection-text="No File Selected"></div>',
              '</div>',
              '<div data-ng-switch-when="OutputFile" data-ng-class="fieldClass">',
                '<div data-output-file-field="field" data-model="model"></div>',
              '</div>',
              '<div data-ng-switch-when="ValueList" data-ng-class="fieldClass">',
                '<select class="form-control" data-ng-model="model[field]" data-ng-options="item as item for item in model[\'values\']"></select>',
              '</div>',
              //TODO(pjm): need a way to specify whether a field is option/required
              '<div data-ng-switch-when="OptionalString" data-ng-class="fieldClass">',
                '<input data-ng-model="model[field]" class="form-control" data-ng-readonly="isReadOnly" />',
              '</div>',
              '<div data-ng-switch-when="RPNValue">',
                '<div data-ng-class="fieldClass">',
                  '<input data-rpn-value="" data-ng-model="model[field]" class="form-control" style="text-align: right" required data-ng-readonly="isReadOnly" />',
                 '</div>',
                '<div class="col-sm-2"><div class="form-control-static pull-right">{{ elegantComputedRpnValue(); }}</div></div>',
              '</div>',
              '<div data-ng-switch-when="RPNBoolean" data-ng-class="fieldClass">',
                '<select class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in elegantRpnBooleanValues()"></select>',
              '</div>',
              '<div data-ng-switch-when="ElegantBeamlineList" data-ng-class="fieldClass">',
                '<select class="form-control" data-ng-model="model[field]" data-ng-options="item.id as item.name for item in elegantBeamlineList()"></select>',
              '</div>',
              '<div data-ng-switch-when="ElegantLatticeList" data-ng-class="fieldClass">',
                '<select class="form-control" data-ng-model="model[field]" data-ng-options="name as name for name in elegantLatticeList()"></select>',
              '</div>',
              // assume it is an enum
              '<div data-ng-switch-default data-ng-class="fieldClass">',
                '<select number-to-string class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in enum[info[1]]"></select>',
              '</div>',
            '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
            $scope.requestSender = requestSender;
            // field def: [label, type]
            $scope.info = appState.modelInfo($scope.modelName)[$scope.field];
            $scope.labelClass = 'col-sm-' + ($scope.labelSize || '5');
            $scope.fieldClass = 'col-sm-' + ($scope.fieldSize || (isNumber($scope.info[1]) ? '3' : '5'));

            function isNumber(type) {
                return type == 'Integer' || type == 'Float';
            }
            $scope.elegantBeamlineList = function() {
                if (! appState.isLoaded() || ! $scope.model)
                    return null;
                if (! $scope.model[$scope.field]
                    && appState.models.beamlines
                    && appState.models.beamlines.length) {
                    $scope.model[$scope.field] = appState.models.beamlines[0].id;
                }
                return appState.models.beamlines;
            };
            $scope.elegantLatticeList = function() {
                if (! appState.isLoaded() || ! $scope.model)
                    return null;
                var runSetupId = $scope.model._id;
                var res = ['Lattice'];
                var index = 0;
                for (var i = 0; i < appState.models.commands.length; i++) {
                    var cmd = appState.models.commands[i];
                    if (cmd._id == runSetupId)
                        break;
                    if (cmd._type == 'save_lattice') {
                        index++;
                        if (cmd.filename)
                            res.push('save_lattice' + (index > 1 ? ('.' + index) : ''));
                    }
                }
                if (! $scope.model[$scope.field])
                    $scope.model[$scope.field] = res[0];
                return res;
            };
            $scope.elegantComputedRpnValue = function() {
                return rpnService.getRpnValueForField($scope.model, $scope.field);
            };
            $scope.elegantRpnBooleanValues = function() {
                return rpnService.getRpnBooleanForField($scope.model, $scope.field);
            };
            $scope.emptyList = [];
            $scope.fieldX = function() {
                return $scope.field + 'X';
            };
            $scope.fieldY = function() {
                return $scope.field + 'Y';
            };
            $scope.showLabel = function() {
                if ($scope.labelSize === '')
                    return true;
                return $scope.labelSize > 0;
            };
            $scope.srwNewUserDefinedBeam = function() {
                // copy the current beam, rename and show editor
                var newBeam = appState.clone(appState.models.electronBeam);
                delete newBeam.isReadOnly;
                newBeam.name = 'Beam Name';
                newBeam.id = appState.maxId(appState.models.electronBeams) + 1;
                appState.models.electronBeams.push(newBeam);
                appState.models.electronBeam = newBeam;
                panelState.showModalEditor('electronBeam');
            };
            $scope.srwSelectBeam = function(item) {
                appState.models.electronBeam = item;
                item[$scope.field] = item.name;
                $scope.$parent.$parent.form.$setDirty();
            };
        },
        link: function link(scope, element) {
            scope.enum = SIREPO.APP_SCHEMA.enum;
            if (scope.info && scope.info[1] == 'BeamList')
                requestSender.loadAuxiliaryData('beams', '/static/json/beams.json');
        },
    };
});

//TODO(pjm): directive specific to elegant
SIREPO.app.directive('outputFileField', function(appState) {
    return {
        restirct: 'A',
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

            function fileExtension() {
                if ($scope.model && $scope.model._type == 'save_lattice')
                    return '.lte';
                return '.sdds';
            }

            $scope.items = function() {
                if (! $scope.model)
                    return items;
                var prefix = $scope.model.name;
                if ($scope.model._type) {
                    var index = 0;
                    for (var i = 0; i < appState.models.commands.length; i++) {
                        var m = appState.models.commands[i];
                        if (m._type == $scope.model._type) {
                            index++;
                            if (m == $scope.model)
                                break;
                        }
                    }
                    prefix = $scope.model._type + (index > 1 ? index : '');
                }
                var name = prefix + '.' + $scope.field + fileExtension();
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

SIREPO.app.directive('fileField', function(appState, panelState, requestSender) {
    return {
        restrict: 'A',
        scope: {
            fileField: '=',
            modelName: '=',
            model: '=',
            emptySelectionText: '@',
            selectionRequired: '=',
            fileType: '@',
            wantFileReport: '=',
        },
        template: [
          '<div class="btn-group" role="group">',
            '<button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown">{{ model[fileField] || emptySelectionText }} <span class="caret"></span></button>',
            '<ul class="dropdown-menu">',
              '<li data-ng-repeat="item in itemList()"><a href data-ng-click="selectItem(item)">{{ item }}</a></li>',
              '<li class="divider"></li>',
              '<li data-ng-hide="selectionRequired"><a href data-ng-click="selectItem(null)">{{ emptySelectionText }}</a></li>',
              '<li data-ng-hide="selectionRequired" class="divider"></li>',
              '<li><a href data-ng-click="showFileUpload()"><span class="glyphicon glyphicon-plus"></span> New</a></li>',
            '</ul>',
          '</div> ',
          '<div data-ng-if="hasValidFileSelected()" class="btn-group" role="group">',
            '<button type="button" title="View Graph" class="btn btn-default" data-ng-if="wantFileReport" data-ng-click="showFileReport()"><span class="glyphicon glyphicon-eye-open"></span></button>',
            '<a data-ng-href="{{ downloadFileUrl() }}" type="button" title="Download" class="btn btn-default""><span class="glyphicon glyphicon-cloud-download"></a>',
          '</div>',
        ].join(''),
        controller: function($scope) {

            function findParentAttribute(name) {
                var scope = $scope;
                while (scope && ! scope[name]) {
                    scope = scope.$parent;
                }
                return scope[name];
            }

            $scope.downloadFileUrl = function() {
                if ($scope.model) {
                    return requestSender.formatUrl('downloadFile', {
                        '<simulation_id>': appState.models.simulation.simulationId,
                        '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        '<filename>': SIREPO.APP_NAME == 'srw'
                            ? $scope.model[$scope.fileField]
                            : $scope.fileType + '.' + $scope.model[$scope.fileField],
                    });
                }
                return '';
            };
            $scope.hasValidFileSelected = function() {
                if ($scope.fileType && $scope.model) {
                    var f = $scope.model[$scope.fileField];
                    var list = requestSender.getAuxiliaryData($scope.fileType);
                    if (f && list && list.indexOf(f) >= 0)
                        return true;
                }
                return false;
            };
            $scope.itemList = function() {
                if (! $scope.fileType)
                    $scope.fileType = $scope.modelName + '-' + $scope.fileField;
                if (requestSender.getAuxiliaryData($scope.fileType))
                    return requestSender.getAuxiliaryData($scope.fileType);
                if (! appState.isLoaded())
                    return $scope.emptyList;
                requestSender.loadAuxiliaryData(
                    $scope.fileType,
                    requestSender.formatUrl('listFiles', {
                        '<simulation_id>': appState.models.simulation.simulationId,
                        '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        '<file_type>': $scope.fileType,
                    }));
                return $scope.emptyList;
            };
            $scope.selectItem = function(item) {
                $scope.model[$scope.fileField] = item;
                findParentAttribute('form').$setDirty();
            };
            $scope.showFileUpload = function() {
                panelState.showModalEditor(
                    'fileUpload' + $scope.fileType,
                    '<div data-file-upload-dialog="" data-dialog-title="Upload File" data-file-type="fileType" data-model="model" data-field="fileField"></div>', $scope);
                findParentAttribute('form').$setDirty();
            };
            $scope.showFileReport = function() {
                findParentAttribute('beamline').showFileReport($scope.fileType, $scope.model);
            };
        },
    };
});

SIREPO.app.directive('columnEditor', function(appState) {
    return {
        scope: {
            modelName: '=',
            columnFields: '=',
            isReadOnly: '=',
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
        },
        template: [
            '<div data-ng-if="! oneLabelLayout" class="row">',
              '<div class="col-sm-6" data-ng-repeat="col in columnFields">',
                '<div class="lead text-center" data-ng-class="columnHeadingClass()">{{ col[0] }}</div>',
                '<div class="form-group form-group-sm" data-ng-repeat="f in col[1]">',
                  '<div data-model-field="f" data-label-size="7" data-field-size="5" data-custom-label="columnLabels[$parent.$index][$index]" data-model-name="modelName" data-model-data="modelData" data-is-read-only="isReadOnly"></div>',
                '</div>',
              '</div>',
            '</div>',
            '<div data-ng-if="oneLabelLayout" class="row">',
              '<div class="col-sm-7 col-sm-offset-1">',
                '<div class="row">',
                  '<div class="col-sm-5 col-sm-offset-7">',
                    '<div class="lead text-center" data-ng-class="columnHeadingClass()">{{ columnFields[0][0] }}</div>',
                  '</div>',
                '</div>',
                '<div class="form-group form-group-sm" data-ng-repeat="f in columnFields[0][1]">',
                  '<div data-model-field="f" data-label-size="7" data-field-size="5" data-custom-label="columnLabels[0][$index]" data-model-name="modelName" data-model-data="modelData" data-is-read-only="isReadOnly"></div>',
                '</div>',
              '</div>',
              '<div class="col-sm-3">',
                '<div class="lead text-center" data-ng-class="columnHeadingClass()">{{ columnFields[1][0] }}</div>',
                '<div class="form-group form-group-sm" data-ng-repeat="f in columnFields[1][1]">',
                  '<div data-model-field="f" data-label-size="0" data-field-size="12" data-model-name="modelName" data-model-data="modelData" data-is-read-only="isReadOnly"></div>',
                '</div>',
              '</div>',
            '</div>',
            '<div>&nbsp;</div>',
        ].join(''),
        controller: function($scope) {

            function createLabels() {
                var res = [];
                for (var i = 0; i < $scope.columnFields.length; i++) {
                    var heading = $scope.columnFields[i][0];
                    res[i] = [];
                    for (var j = 0; j < $scope.columnFields[i][1].length; j++) {
                        var col = $scope.columnFields[i][1][j];
                        res[i][j] = getLabel(heading, col);
                    }
                }
                return res;
            }

            function getLabel(heading, f) {
                var m = $scope.modelName;
                var modelField = appState.parseModelField(f);
                if (modelField) {
                    m = modelField[0];
                    f = modelField[1];
                }
                var info = appState.modelInfo(m)[f];
                var label = info[0];
                heading = heading.replace(/ .*/, '');
                label = label.replace(heading, '');
                return label;
            }

            function isOneLabelLayout() {
                for (var i = 0; i < $scope.columnLabels[0].length; i++) {
                    if ($scope.columnLabels[0][i] != $scope.columnLabels[1][i])
                        return false;
                }
                return true;
            }

            $scope.columnLabels = createLabels();
            $scope.oneLabelLayout = isOneLabelLayout();
            $scope.columnHeadingClass = function() {
                return 'model-' + $scope.modelName + '-column-heading';
            };
        },
    };
});

SIREPO.app.directive('fileUploadDialog', function(appState, fileUpload, requestSender) {
    return {
        restrict: 'A',
        scope: {
            dialogTitle: '@',
            parentController: '=',
            fileType: '=',
            model: '=',
            field: '=',
        },
        template: [
            '<div class="modal fade" id="s-fileUpload{{ fileType }}-editor" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<span class="lead modal-title text-info">{{ dialogTitle }}</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<form>',
                        '<div class="form-group">',
                          '<label>Select File</label>',
                          '<input type="file" data-file-model="inputFile" />',
                          '<div class="text-warning"><strong>{{ fileUploadError }}</strong></div>',
                        '</div>',
                        '<div data-ng-if="isUploading" class="col-sm-6 pull-right">Please Wait...</div>',
                        '<div class="clearfix"></div>',
                        '<div class="col-sm-6 pull-right">',
                          '<button data-ng-click="uploadFile(inputFile)" class="btn btn-primary" data-ng-class="{\'disabled\': isUploading}">Save Changes</button>',
                          ' <button data-dismiss="modal" class="btn btn-default" data-ng-class="{\'disabled\': isUploading}">Cancel</button>',
                        '</div>',
                      '</form>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.fileUploadError = '';
            $scope.isUploading = false;

            $scope.uploadFile = function(inputFile) {
                if (! inputFile)
                    return;
                $scope.isUploading = true;
                fileUpload.uploadFileToUrl(
                    inputFile,
                    null,
                    requestSender.formatUrl(
                        'uploadFile',
                        {
                            '<simulation_id>': appState.models.simulation.simulationId,
                            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                            '<file_type>': $scope.fileType,
                        }),
                    function(data) {
                        $scope.isUploading = false;
                        if (data.error) {
                            $scope.fileUploadError = data.error;
                            return;
                        }
                        requestSender.getAuxiliaryData($scope.fileType).push(data.filename);
                        $scope.model[$scope.field] = data.filename;
                        $('#s-fileUpload' + $scope.fileType + '-editor').modal('hide');
                    });
            };
        },
        link: function(scope, element) {
            $(element).on('show.bs.modal', function() {
                scope.fileUploadError = '';
                scope.inputFile = null;
                $(element).find("input[type='file']").val(null);
            });
            scope.$on('$destroy', function() {
                $(element).off();
                $(element).detach();
            });
        },
    };
});

SIREPO.app.directive('helpButton', function($window) {
    var HELP_WIKI_ROOT = 'https://github.com/radiasoft/sirepo/wiki/' + SIREPO.APP_NAME.toUpperCase() + '-';
    return {
        scope: {
            helpTopic: '@helpButton',
        },
        template: [
            '<button class="close s-help-icon" title="{{ helpTopic }} Help" data-ng-click="openHelp()"><span class="glyphicon glyphicon-question-sign"></span></button>',
        ].join(''),
        controller: function($scope) {
            $scope.openHelp = function() {
                $window.open(
                    HELP_WIKI_ROOT + $scope.helpTopic.replace(/\s+/, '-'),
                    '_blank');
            };
        },
    };
});

SIREPO.app.directive('modalEditor', function(appState) {
    return {
        scope: {
            viewName: '@',
            isReadOnly: '=',
            parentController: '=',
            modalTitle: '=',
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
        },
        template: [
            '<div class="modal fade" id="{{ editorId }}" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
  	            '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<div data-help-button="{{ helpTopic }}"></div>',
	            '<span class="lead modal-title text-info">{{ modalTitle }}</span>',
	          '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<div class="row">',
                        '<div data-advanced-editor-pane="" data-view-name="viewName" data-is-read-only="isReadOnly" data-want-buttons="true" data-model-data="modelData" data-parent-controller="parentController"></div>',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            function hideModal() {
                if ($scope.editorId)
                    $('#' + $scope.editorId).modal('hide');
            }
            var viewInfo = appState.viewInfo($scope.viewName);
            $scope.helpTopic = viewInfo.title;
            //TODO(pjm): cobbled-together to allow a view to refer to a model by name, ex. SRW simulationGrid view
            $scope.modelName = viewInfo.model || $scope.viewName;
            $scope.modelKey = $scope.modelName;
            $scope.editorId = 's-' + $scope.viewName + '-editor';
            if ($scope.modelData) {
                $scope.modelKey = $scope.modelData.modelKey;
                $scope.editorId = 's-' + $scope.modelKey + '-editor';
            }
            if (! $scope.modalTitle)
                $scope.modalTitle = viewInfo.title;
            $scope.$on('modelChanged', function (e, name) {
                if (name == $scope.modelKey)
                    hideModal();
            });
            $scope.$on('cancelChanges', hideModal);
        },
        link: function(scope, element) {
            $(element).on('shown.bs.modal', function() {
                if (! scope.isReadOnly)
                    $('#' + scope.editorId + ' .form-control').first().select();
                if (scope.parentController && scope.parentController.handleModalShown)
                    scope.parentController.handleModalShown(scope.modelName, scope.modelKey);
            });
            $(element).on('hidden.bs.modal', function(e) {
                // ensure that a dismissed modal doesn't keep changes
                // ok processing will have already saved data before the modal is hidden
                appState.cancelChanges(scope.modelKey);
                scope.$apply();
            });
            scope.$on('$destroy', function() {
                // release modal data to prevent memory leak
                $(element).off();
                $('.modal').modal('hide').removeData('bs.modal');
            });
        },
    };
});

SIREPO.app.directive('modelField', function(appState) {
    return {
        scope: {
            field: '=modelField',
            modelName: '=',
            customLabel: '=',
            labelSize: "@",
            fieldSize: "@",
            isReadOnly: "=",
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
        },
        template: [
            '<div data-field-editor="fieldName()" data-model-name="modelNameForField()" data-model="modelForField()" data-is-read-only="isReadOnly" data-custom-label="customLabel" data-label-size="{{ labelSize }}" data-field-size="{{ fieldSize }}"></div>',
        ].join(''),
        controller: function($scope) {
            var modelName = $scope.modelName;
            var field = $scope.field;
            var modelField = appState.parseModelField(field);

            if (modelField) {
                modelName = modelField[0];
                field = modelField[1];
            }

            $scope.modelForField = function() {
                if ($scope.modelData && ! modelField)
                    return $scope.modelData.getData();
                return appState.models[modelName];
            };

            $scope.modelNameForField = function() {
                return modelName;
            };

            $scope.fieldName = function(f) {
                return field;
            };
        },
    };
});

SIREPO.app.directive('numberToString', function() {
    return {
        restrict: 'A',
        require: 'ngModel',
        link: function(scope, element, attrs, ngModel) {
            ngModel.$parsers.push(function(value) {
                if (ngModel.$isEmpty(value))
                    return null;
                return '' + value;
            });
            ngModel.$formatters.push(function(value) {
                if (ngModel.$isEmpty(value))
                    return value;
                return value.toString();
            });
        }
    };
});

SIREPO.app.directive('panelHeading', function(appState, frameCache, panelState, requestSender, plotToPNG) {
    return {
        restrict: 'A',
        scope: {
            panelHeading: '@',
            modelKey: '=',
            allowFullScreen: '@',
        },
        template: [
            '<span class="s-panel-heading">{{ panelHeading }}</span>',
            '<div class="s-panel-options pull-right">',
              '<a href data-ng-show="hasEditor" data-ng-click="showEditor()" title="Edit"><span class="s-panel-heading glyphicon glyphicon-pencil"></span></a> ',
              '<div data-ng-if="allowFullScreen" data-ng-show="hasData()" class="dropdown" style="display: inline-block">',
                '<a href class="dropdown-toggle" data-toggle="dropdown" title="Download"> <span class="s-panel-heading glyphicon glyphicon-cloud-download" style="margin-bottom: 0"></span></a> ',
                '<ul class="dropdown-menu dropdown-menu-right">',
                  '<li class="dropdown-header">Download Report</li>',
                  '<li><a href data-ng-click="downloadImage(480)">PNG - Small</a></li>',
                  '<li><a href data-ng-click="downloadImage(720)">PNG - Medium</a></li>',
                  '<li><a href data-ng-click="downloadImage(1080)">PNG - Large</a></li>',
                  '<li role="separator" class="divider"></li>',
                  '<li><a data-ng-href="{{ dataFileURL() }}" target="_blank">Raw Data File</a></li>',
                '</ul>',
              '</div>',
              //'<a href data-ng-show="allowFullScreen" title="Full screen"><span class="s-panel-heading glyphicon glyphicon-fullscreen"></span></a> ',
              '<a href data-ng-click="panelState.toggleHidden(modelKey)" data-ng-hide="panelState.isHidden(modelKey)" title="Hide"><span class="s-panel-heading glyphicon glyphicon-triangle-top"></span></a> ',
              '<a href data-ng-click="panelState.toggleHidden(modelKey)" data-ng-show="panelState.isHidden(modelKey)" title="Show"><span class="s-panel-heading glyphicon glyphicon-triangle-bottom"></span></a>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.hasEditor = appState.viewInfo($scope.modelKey)
                && appState.viewInfo($scope.modelKey).advanced.length === 0 ? false : true;
            $scope.panelState = panelState;

            $scope.dataFileURL = function() {
                if (appState.isLoaded()) {
                    return requestSender.formatUrl('downloadDataFile', {
                        '<simulation_id>': appState.models.simulation.simulationId,
                        '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        '<model>': $scope.modelKey,
                        '<frame>': appState.isAnimationModelName($scope.modelKey)
                            ? frameCache.getCurrentFrame($scope.modelKey)
                            : -1,
                    });
                }
                return '';
            };
            $scope.downloadImage = function(height) {
                var svg = $scope.reportPanel.find('svg')[0];
                if (! svg)
                    return;
                var fileName = $scope.panelHeading.replace(/(\_|\W|\s)+/g, '-') + '.png';
                var plot3dCanvas = $scope.reportPanel.find('canvas')[0];
                plotToPNG.downloadPNG(svg, height, plot3dCanvas, fileName);
            };
            $scope.hasData = function() {
                if (appState.isLoaded()) {
                    if (appState.isAnimationModelName($scope.modelKey))
                        return frameCache.getFrameCount() > 0;
                    return ! panelState.isLoading($scope.modelKey);
                }
                return false;
            };
            $scope.showEditor = function() {
                panelState.showModalEditor($scope.modelKey);
            };
        },
        link: function(scope, element) {
            scope.reportPanel = element.next();
        },
    };
});

SIREPO.app.directive('reportContent', function(panelState) {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            reportContent: '@',
            modelKey: '@',
        },
        template: [
            '<div data-ng-class="{\'s-panel-loading\': panelState.isLoading(modelKey), \'s-panel-error\': panelState.getError(modelKey)}" class="panel-body" data-ng-hide="panelState.isHidden(modelKey)">',
              '<div data-ng-show="panelState.isLoading(modelKey)" class="lead s-panel-wait"><span class="glyphicon glyphicon-hourglass"></span> Simulating...</div>',
              '<div data-ng-show="panelState.getError(modelKey)" class="lead s-panel-wait"><span class="glyphicon glyphicon-exclamation-sign"></span> {{ panelState.getError(modelKey) }}</div>',
              '<div data-ng-switch="reportContent" class="{{ panelState.getError(modelKey) ? \'s-hide-report\' : \'\' }}">',
                '<div data-ng-switch-when="2d" data-plot2d="" class="s-plot" data-model-name="{{ modelKey }}"></div>',
                '<div data-ng-switch-when="3d" data-plot3d="" class="s-plot" data-model-name="{{ modelKey }}"></div>',
                '<div data-ng-switch-when="heatmap" data-heatmap="" class="s-plot" data-model-name="{{ modelKey }}"></div>',
                '<div data-ng-switch-when="lattice" data-lattice="" class="s-plot" data-model-name="{{ modelKey }}"></div>',
              '</div>',
              '<div data-ng-transclude=""></div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.panelState = panelState;
        },
    };
});

SIREPO.app.directive('reportPanel', function(appState) {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            reportPanel: '@',
            modelName: '@',
            panelTitle: '@',
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
        },
        template: [
            '<div class="panel panel-info">',
              '<div class="panel-heading clearfix" data-panel-heading="{{ reportTitle() }}" data-model-key="modelKey" data-allow-full-screen="1"></div>',
              '<div data-report-content="{{ reportPanel }}" data-model-key="{{ modelKey }}"><div data-ng-transclude=""></div></div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.modelKey = $scope.modelName;
            if ($scope.modelData)
                $scope.modelKey = $scope.modelData.modelKey;
            $scope.reportTitle = function() {
                return $scope.panelTitle ? $scope.panelTitle : appState.viewInfo($scope.modelName).title;
            };
        },
    };
});

SIREPO.app.service('rpnService', function(appState, requestSender, $rootScope) {
    var rpnBooleanValues = null;

    this.computeRpnValue = function(value, callback) {
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
                    if (appState.isLoaded())
                        appState.models.rpnCache[value] = data.result;
                }
                callback(data.result, data.error);
            });
    };

    this.getRpnBooleanForField = function(model, field) {
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

    this.getRpnValue = function(v) {
        if (angular.isUndefined(v))
            return v;
        if (v in appState.models.rpnCache)
            return appState.models.rpnCache[v];
        var value = parseFloat(v);
        if (isNaN(value))
            return undefined;
        return value;
    };

    this.getRpnValueForField = function(model, field) {
        if (appState.isLoaded() && model && field) {
            var v = model[field];
            if (SIREPO.NUMBER_REGEXP.test(v))
                return '';
            return this.getRpnValue(v);
        }
        return '';
    };

    this.recomputeCache = function(varName, value) {
        var recomputeRequired = false;
        var re = new RegExp("\\b" + varName + "\\b");
        for (var k in appState.models.rpnCache) {
            if (k == varName)
                appState.models.rpnCache[k] = value;
            else if (k.match(re))
                recomputeRequired = true;
        }
        if (! recomputeRequired)
            return;
        requestSender.getApplicationData(
            {
                method: 'recompute_rpn_cache_values',
                cache: appState.models.rpnCache,
                variables: appState.models.rpnVariables,
            },
            function(data) {
                if (appState.isLoaded() && data.cache)
                    appState.models.rpnCache = data.cache;
            });
    };

    $rootScope.$on('rpnVariables.changed', function() {
        rpnBooleanValues = null;
    });
});

SIREPO.app.directive('rpnValue', function(appState, rpnService) {
    var requestIndex = 0;
    return {
        restrict: 'A',
        require: 'ngModel',
        link: function(scope, element, attrs, ngModel) {
            var rpnVariableName = scope.modelName == 'rpnVariable' ? scope.model.name : null;
            ngModel.$parsers.push(function(value) {
                if (ngModel.$isEmpty(value))
                    return null;
                if (SIREPO.NUMBER_REGEXP.test(value)) {
                    ngModel.$setValidity('', true);
                    var v = parseFloat(value);
                    if (rpnVariableName)
                        rpnService.recomputeCache(rpnVariableName, v);
                    return v;
                }
                requestIndex++;
                var currentRequestIndex = requestIndex;
                rpnService.computeRpnValue(value, function(v, err) {
                    // check for a stale request
                    if (requestIndex != currentRequestIndex)
                        return;
                    ngModel.$setValidity('', err ? false : true);
                    if (rpnVariableName && ! err)
                        rpnService.recomputeCache(rpnVariableName, v);
                });
                return value;
            });
            ngModel.$formatters.push(function(value) {
                if (ngModel.$isEmpty(value))
                    return value;
                return value.toString();
            });
        }
    };
});

SIREPO.app.directive('appHeaderLeft', function(panelState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeaderLeft',
        },
        template: [
            '<ul class="nav navbar-nav">',
              '<li data-ng-class="{active: nav.isActive(\'simulations\')}"><a href data-ng-click="nav.openSection(\'simulations\')"><span class="glyphicon glyphicon-th-list"></span> Simulations</a></li>',
            '</ul>',
            '<div data-ng-if="showTitle()" class="navbar-text"><a href data-ng-click="showSimulationModal()"><span data-ng-if="nav.sectionTitle()" class="glyphicon glyphicon-pencil"></span> <strong data-ng-bind="nav.sectionTitle()"></strong></a></div>',
        ].join(''),
        controller: function($scope) {
            $scope.showSimulationModal = function() {
                panelState.showModalEditor('simulation');
            };
            $scope.showTitle = function() {
                if ($scope.nav.isActive('simulations'))
                    return false;
                return true;
            };
        },
    };
});

SIREPO.app.directive('simulationStatusTimer', function() {
    return {
        restrict: 'A',
        scope: {
            timeData: '=simulationStatusTimer',
        },
        template: [
            '<span data-ng-if="timeData.elapsedTime != null">',
              'Elapsed time: {{ timeData.elapsedDays }} {{ timeData.elapsedTime | date:\'HH:mm:ss\' }}',
            '</span>',
        ].join(''),
    };
});

SIREPO.app.directive('stringToNumber', function() {
    return {
        restrict: 'A',
        require: 'ngModel',
        scope: {
            numberType: '@stringToNumber',
        },
        link: function(scope, element, attrs, ngModel) {
            ngModel.$parsers.push(function(value) {
                if (ngModel.$isEmpty(value))
                    return null;
                if (SIREPO.NUMBER_REGEXP.test(value)) {
                    if (scope.numberType == 'integer') {
                        var v = parseInt(value);
                        if (v != value) {
                            ngModel.$setViewValue(v);
                            ngModel.$render();
                        }
                        return v;
                    }
                    return parseFloat(value);
                }
                return undefined;
            });
            ngModel.$formatters.push(function(value) {
                if (ngModel.$isEmpty(value))
                    return value;
                return value.toString();
            });
        }
    };
});

SIREPO.app.directive('fileModel', ['$parse', function ($parse) {
    return {
        restrict: 'A',
        link: function(scope, element, attrs) {
            var model = $parse(attrs.fileModel);
            var modelSetter = model.assign;
            element.bind('change', function(){
                scope.$apply(function(){
                    modelSetter(scope, element[0].files[0]);
                });
            });
        }
    };
}]);

SIREPO.app.service('plotToPNG', function($http) {

    function downloadPlot(svg, height, plot3dCanvas, fileName) {
        var canvas = document.createElement('canvas');
        var context = canvas.getContext("2d");
        var scale = height / parseInt(svg.getAttribute('height'));
        canvas.width = parseInt(svg.getAttribute('width')) * scale;
        canvas.height = parseInt(svg.getAttribute('height')) * scale;
        context.fillStyle = '#FFFFFF';
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.fillStyle = '#000000';

        if (plot3dCanvas) {
            var el = $(plot3dCanvas);
            context.drawImage(
                plot3dCanvas, pxToInteger(el.css('left')) * scale, pxToInteger(el.css('top')) * scale,
                pxToInteger(el.css('width')) * scale, pxToInteger(el.css('height')) * scale);
        }
        var svgString = svg.parentNode.innerHTML;
        context.drawSvg(svgString, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(function(blob) {
            saveAs(blob, fileName);
        });
    }

    function pxToInteger(value) {
        value = value.replace(/px/, '');
        return parseInt(value);
    }

    this.downloadPNG = function(svg, height, plot3dCanvas, fileName) {
        // embed sirepo.css style within SVG for first download, css file is cached by browser
        $http.get('/static/css/sirepo.css?' + SIREPO.APP_VERSION)
            .success(function(data) {
                if (svg.firstChild.nodeName != 'STYLE') {
                    var css = document.createElement('style');
                    css.type = 'text/css';
                    css.appendChild(document.createTextNode(data));
                    svg.insertBefore(css, svg.firstChild);
                }
                downloadPlot(svg, height, plot3dCanvas, fileName);
            });
    };
});

SIREPO.app.service('fileUpload', function($http) {
    this.uploadFileToUrl = function(file, args, uploadUrl, callback) {
        var fd = new FormData();
        fd.append('file', file);
        if (args) {
            for (var k in args) {
                fd.append(k, args[k]);
            }
        }
        $http.post(uploadUrl, fd, {
            transformRequest: angular.identity,
            headers: {'Content-Type': undefined}
        })
            .success(callback)
            .error(function(){
                //TODO(pjm): error handling
                srlog('file upload failed');
            });
    };
});
