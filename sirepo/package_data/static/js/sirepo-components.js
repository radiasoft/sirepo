'use strict';

app.directive('advancedEditorPane', function(appState, $timeout) {
    return {
        scope: {
            viewName: '=',
            isReadOnly: '=',
            parentController: '=',
            wantButtons: '@',
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
        },
        template: [
            '<h5 data-ng-if="description">{{ description }}</h5>',
            '<form name="form" class="form-horizontal" novalidate>',
              '<ul data-ng-if="pages" class="nav nav-tabs">',
                '<li data-ng-repeat="page in pages" role="presentation" data-ng-class="{active: page.isActive}"><a href data-ng-click="setActivePage(page)">{{ page.name }}</a></li>',
              '</ul>',
              '<br />',
              '<div data-ng-repeat="f in (activePage ? activePage.items : advancedFields)">',
                '<div class="form-group form-group-sm" data-ng-if="! isColumnField(f)" data-model-field="f" data-model-name="modelName" data-model-data="modelData" data-is-read-only="isReadOnly"></div>',
                '<div data-ng-if="isColumnField(f)" data-column-editor="" data-column-fields="f" data-model-name="modelName" data-model-data="modelData" data-is-read-only="isReadOnly"></div>',
              '</div>',
              '<div data-ng-if="wantButtons" data-buttons="" data-model-name="modelName" data-model-data="modelData" data-fields="advancedFields"></div>',
            '</form>',
        ].join(''),
        controller: function($scope) {
            var viewInfo = appState.viewInfo($scope.viewName);
            $scope.modelName = viewInfo.model || $scope.viewName;
            $scope.description = viewInfo.description;
            $scope.advancedFields = viewInfo.advanced;

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
            if ($scope.isColumnField($scope.advancedFields[0]) && ! $scope.isColumnField($scope.advancedFields[0][0])) {
                $scope.pages = [];
                for (var i = 0; i < $scope.advancedFields.length; i++) {
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
                for (var i = 0; i < $scope.advancedFields.length; i++) {
                    if (i % viewInfo.fieldsPerTab == 0) {
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

app.directive('basicEditorPanel', function(appState, panelState) {
    return {
        scope: {
            viewName: '@',
        },
        template: [
            '<div class="panel panel-info">',
              '<div class="panel-heading clearfix" data-panel-heading="{{ panelTitle }}" data-model-key="modelName"></div>',
              '<div class="panel-body cssFade" data-ng-hide="panelState.isHidden(modelName)">',
                '<form name="form" class="form-horizontal" novalidate>',
                  '<div class="form-group form-group-sm" data-ng-repeat="f in basicFields">',
                    '<div data-model-field="f" data-model-name="modelName"></div>',
                  '</div>',
                  '<div data-buttons="" data-model-name="modelName" data-fields="basicFields"></div>',
                '</form>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var viewInfo = appState.viewInfo($scope.viewName);
            $scope.modelName = viewInfo.model || $scope.viewName;
            $scope.panelState = panelState;
            $scope.basicFields = viewInfo.basic;
            $scope.panelTitle = viewInfo.title;
        },
    };
});

app.directive('buttons', function(appState) {
    return {
        scope: {
            modelName: '=',
            fields: '=',
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
        },
        template: [
            '<div class="col-sm-6 pull-right cssFade" data-ng-show="form.$dirty">',
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
                // may be a string field, [tab-name, [cols]], or [[col-header, [cols]], [col-header, [cols]]]
                if (typeof(field) == 'string')
                    extractModel(field, modelNames);
                else {
                    // [name, [cols]]
                    if (typeof(field[0]) == 'string') {
                        for (var i = 0; i < field[1].length; i++)
                            iterateFields(field[1][i]);
                    }
                    // [[name, [cols]], [name, [cols]], ...]
                    else {
                        for (var i = 0; i < field.length; i++)
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

app.directive('confirmationModal', function() {
    return {
        restrict: 'A',
        scope: {
            id: '@',
            title: '@',
            text: '@',
            okText: '@',
            okClicked: '&',
        },
        template: [
            '<div class="modal fade" id="{{ id }}" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-warning">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<span class="lead modal-title text-info">{{ title }}</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<div class="row">',
                        '<div class="col-sm-6 col-sm-offset-3">',
                          '<p>{{ text }}</p>',
                        '</div>',
                      '</div>',
                      '<div class="row">',
                        '<div class="col-sm-6 pull-right">',
                          '<button data-dismiss="modal" data-ng-click="okClicked()" class="btn btn-default">{{ okText }}</button>',
                          ' <button data-dismiss="modal" class="btn btn-default">Cancel</button>',
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

app.directive('labelWithTooltip', function() {
    return {
        restrict: 'A',
        scope: {
            'label': '@',
            'tooltip': '@',
        },
        template: [
            '<label>{{ label }} <span ng-show="tooltip" class="glyphicon glyphicon-info-sign s-info-pointer"></span></label>',
        ],
        link: function link(scope, element) {
            if (scope.tooltip) {
                $(element).find('span').tooltip({
                    title: scope.tooltip,
                    placement: 'bottom',
                });
            }
        },
    };
});

app.directive('fieldEditor', function(appState, panelState, requestSender) {
    return {
        restirct: 'A',
        scope: {
            modelName: '=',
            field: '=fieldEditor',
            model: '=',
            customLabel: '=',
            labelSize: "@",
            numberSize: "@",
            isReadOnly: "=",
        },
        template: [
            '<div class="model-{{modelName}}-{{field}}">',
            '<div data-label-with-tooltip="" class="col-sm-{{ labelSize || \'5\' }} control-label" data-label="{{ customLabel || info[0] }}" data-tooltip="{{ info[3] }}"></div>',
            '<div data-ng-switch="info[1]">',
              '<div data-ng-switch-when="BeamList" class="col-sm-5">',
                '<div class="dropdown">',
                  '<button class="btn btn-default dropdown-toggle form-control" type="button" data-toggle="dropdown">{{ model[field] }} <span class="caret"></span></button>',
                  '<ul class="dropdown-menu">',
                    '<li class="dropdown-header">Predefined Electron Beams</li>',
                    '<li data-ng-repeat="item in requestSender.getAuxiliaryData(\'beams\') track by item.name">',
                      '<a href data-ng-click="selectBeam(item)">{{ item.name }}</a>',
                    '</li>',
                    '<li class="divider"></li>',
                    '<li class="dropdown-header">User Defined Electron Beams</li>',
                    '<li data-ng-repeat="item in appState.models.electronBeams track by item.name">',
                      '<a href data-ng-click="selectBeam(item)">{{ item.name }}</a>',
                    '</li>',
                    '<li><a href data-ng-click="newUserDefinedBeam()"><span class="glyphicon glyphicon-plus"></span> New</a></li>',
                  '</ul>',
                '</div>',
              '</div>',
              '<div data-ng-switch-when="Float" class="col-sm-{{ numberSize || \'3\' }}">',
                '<input string-to-number="" data-ng-model="model[field]" class="form-control" style="text-align: right" required data-ng-readonly="isReadOnly">',
              '</div>',
              '<div data-ng-switch-when="Integer" class="col-sm-{{ numberSize || \'3\' }}">',
                '<input string-to-number="integer" data-ng-model="model[field]" class="form-control" style="text-align: right" required data-ng-readonly="isReadOnly">',
              '</div>',
              '<div data-ng-switch-when="MirrorFile" class="col-sm-7">',
                '<div data-file-field="field" data-file-type="mirror" data-want-file-report="true" data-model="model" data-selection-required="modelName == \'mirror\'" data-empty-selection-text="No Mirror Error"></div>',
              '</div>',
              '<div data-ng-switch-when="MagneticZipFile" class="col-sm-7">',
                '<div data-file-field="field" data-file-type="undulatorTable" data-model="model" data-selection-required="true" data-empty-selection-text="Select Magnetic Zip File"></div>',
              '</div>',
              '<div data-ng-switch-when="String" class="col-sm-5">',
                '<input data-ng-model="model[field]" class="form-control" required data-ng-readonly="isReadOnly">',
              '</div>',
              '<div data-ng-switch-when="InputFile" class="col-sm-7">',
                '<div data-file-field="field" data-model="model" data-model-name="modelName" data-empty-selection-text="No File Selected"></div>',
              '</div>',
              '<div data-ng-switch-when="OutputFile" class="col-sm-5">',
                '<div data-output-file-field="field" data-model="model"></div>',
              '</div>',
              '<div data-ng-switch-when="ValueList" class="col-sm-5">',
                '<select class="form-control" data-ng-model="model[field]" data-ng-options="item as item for item in model[\'values\']"></select>',
              '</div>',
              //TODO(pjm): need a way to specify whether a field is option/required
              '<div data-ng-switch-when="OptionalString" class="col-sm-5">',
                '<input data-ng-model="model[field]" class="form-control" data-ng-readonly="isReadOnly">',
              '</div>',
              // assume it is an enum
              '<div data-ng-switch-default class="col-sm-5">',
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
            $scope.selectBeam = function(item) {
                appState.models.electronBeam = item;
                item[$scope.field] = item.name;
                $scope.$parent.$parent.form.$setDirty();
            };
            $scope.emptyList = [];
            $scope.newUserDefinedBeam = function() {
                // copy the current beam, rename and show editor
                var newBeam = appState.clone(appState.models.electronBeam);
                delete newBeam.isReadOnly;
                newBeam.name = 'Beam Name';
                newBeam.id = appState.maxId(appState.models.electronBeams) + 1;
                appState.models.electronBeams.push(newBeam);
                appState.models.electronBeam = newBeam;
                panelState.showModalEditor('electronBeam');
            };
        },
        link: function link(scope, element) {
            scope.enum = APP_SCHEMA.enum;
            if (scope.info && scope.info[1] == 'BeamList')
                requestSender.loadAuxiliaryData('beams', '/static/json/beams.json');
        },
    };
});

app.directive('outputFileField', function() {
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

            $scope.items = function() {
                if (! $scope.model)
                    return items;
                var name = $scope.model.name + '.' + $scope.field + '.sdds';
                if (name != filename) {
                    filename = name;
                    items = [
                        ['', 'None'],
                        [name, name],
                    ];
                }
                return items;
            };
        },
    };
});

app.directive('fileField', function(appState, panelState, requestSender) {
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
          '<div data-ng-if="model[fileField]" class="btn-group" role="group">',
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
                        '<simulation_type>': APP_SCHEMA.simulationType,
                        '<filename>': SIREPO_APP_NAME == 'srw'
                            ? $scope.model[$scope.fileField]
                            : $scope.fileType + '.' + $scope.model[$scope.fileField],
                    });
                }
                return '';
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
                        '<simulation_type>': APP_SCHEMA.simulationType,
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

app.directive('columnEditor', function(appState) {
    return {
        scope: {
            modelName: '=',
            columnFields: '=',
            isReadOnly: '=',
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
        },
        template: [
            '<div class="row">',
              '<div class="col-sm-6" data-ng-repeat="col in columnFields">',
                '<div class="lead text-center">{{ col[0] }}</div>',
                '<div class="form-group form-group-sm" data-ng-repeat="f in col[1]">',
                  '<div data-model-field="f" data-label-size="7" data-number-size="5" data-custom-label="customLabel(col[0], f)" data-model-name="modelName" data-model-data="modelData" data-is-read-only="isReadOnly"></div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
            $scope.customLabel = function(heading, f) {
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
            };
        },
    };
});

app.directive('fileUploadDialog', function(appState, fileUpload, requestSender) {
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
                          '<input type="file" data-file-model="inputFile">',
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
                    '',
                    requestSender.formatUrl(
                        'uploadFile',
                        {
                            '<simulation_id>': appState.models.simulation.simulationId,
                            '<simulation_type>': APP_SCHEMA.simulationType,
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

app.directive('helpButton', function($window) {
    var HELP_WIKI_ROOT = 'https://github.com/radiasoft/sirepo/wiki/' + SIREPO_APP_NAME.toUpperCase() + '-';
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

app.directive('modalEditor', function(appState) {
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
            $scope.$on('modelChanged', hideModal);
            $scope.$on('cancelChanges', hideModal);
        },
        link: function(scope, element) {
            $(element).on('shown.bs.modal', function() {
                if (! scope.isReadOnly)
                    $('#' + scope.editorId + ' .form-control').first().select();
                if (scope.parentController && scope.parentController.handleModalShown)
                    scope.parentController.handleModalShown(scope.modelName);
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

app.directive('modelField', function(appState) {
    return {
        scope: {
            field: '=modelField',
            modelName: '=',
            customLabel: '=',
            labelSize: "@",
            numberSize: "@",
            isReadOnly: "=",
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
        },
        template: [
            '<div data-field-editor="fieldName()" data-model-name="modelNameForField()" data-model="modelForField()" data-is-read-only="isReadOnly" data-custom-label="customLabel" data-label-size="{{ labelSize }}" data-number-size="{{ numberSize }}"></div>',
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
            }

            $scope.modelNameForField = function() {
                return modelName;
            }

            $scope.fieldName = function(f) {
                return field;
            };
        },
    };
});

app.directive('numberToString', function() {
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

app.directive('panelHeading', function(appState, frameCache, panelState, requestSender, plotToPNG) {
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
                && appState.viewInfo($scope.modelKey).advanced.length == 0 ? false : true;
            $scope.panelState = panelState;

            $scope.dataFileURL = function() {
                if (appState.isLoaded()) {
                    return requestSender.formatUrl('downloadDataFile', {
                        '<simulation_id>': appState.models.simulation.simulationId,
                        '<simulation_type>': APP_SCHEMA.simulationType,
                        '<model>': $scope.modelKey,
                        '<frame>': appState.isAnimationModelName($scope.modelKey)
                            ? frameCache.getCurrentFrame($scope.modelKey)
                            : -1,
                    });
                }
                return '';
            },
            $scope.downloadImage = function(height) {
                var svg = $scope.reportPanel.find('svg')[0];
                if (! svg)
                    return;
                var fileName = $scope.panelHeading.replace(/(\_|\W|\s)+/g, '-') + '.png'
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

app.directive('reportContent', function(panelState) {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            reportContent: '@',
            modelKey: '@',
        },
        template: [
            '<div data-ng-class="{\'s-panel-loading\': panelState.isLoading(modelKey), \'s-panel-error\': panelState.getError(modelKey)}" class="panel-body cssFade" data-ng-hide="panelState.isHidden(modelKey)">',
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

app.directive('reportPanel', function(appState) {
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

app.directive('appHeaderLeft', function(panelState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeaderLeft',
        },
        template: [
            '<ul class="nav navbar-nav">',
              '<li data-ng-class="{active: nav.isActive(\'simulations\')}"><a href data-ng-click="nav.openSection(\'simulations\')"><span class="glyphicon glyphicon-th-list"></span> Simulations</a></li>',
            '</ul>',
            '<div class="navbar-text"><a href data-ng-click="showSimulationModal()"><span ng-if="nav.sectionTitle()" class="glyphicon glyphicon-pencil"></span> <strong data-ng-bind="nav.sectionTitle()"></strong></a></div>',
        ].join(''),
        controller: function($scope) {
            $scope.showSimulationModal = function() {
                panelState.showModalEditor('simulation');
            };
        },
    };
});

app.directive('simulationStatusTimer', function() {
    return {
        restrict: 'A',
        scope: {
            timeData: '=simulationStatusTimer',
        },
        template: [
            '<span data-ng-if="timeData.elapsedTime">',
              'Elapsed time: {{ timeData.elapsedDays }} {{ timeData.elapsedTime | date:\'HH:mm:ss\' }}',
            '</span>',
        ].join(''),
    };
});

app.directive('stringToNumber', function() {
    var NUMBER_REGEXP = /^\s*(\-|\+)?(\d+|(\d*(\.\d*)))([eE][+-]?\d+)?\s*$/;
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
                if (NUMBER_REGEXP.test(value)) {
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

app.directive('fileModel', ['$parse', function ($parse) {
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

app.service('plotToPNG', function($http) {

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
        $http.get('/static/css/sirepo.css?' + SIREPO_APP_VERSION)
            .success(function(data) {
                if (svg.firstChild.nodeName != 'STYLE') {
                    var css = document.createElement('style');
                    css.type = 'text/css';
                    css.appendChild(document.createTextNode(data));
                    svg.insertBefore(css, svg.firstChild);
                }
                downloadPlot(svg, height, plot3dCanvas, fileName);
            });
    }
});

app.service('fileUpload', function($http) {
    this.uploadFileToUrl = function(file, args, uploadUrl, callback) {
        var fd = new FormData();
        fd.append('file', file);
        fd.append('arguments', args)
        $http.post(uploadUrl, fd, {
            transformRequest: angular.identity,
            headers: {'Content-Type': undefined}
        })
            .success(callback)
            .error(function(){
                //TODO(pjm): error handling
                console.log('file upload failed');
            });
    }
});
