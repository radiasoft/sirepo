'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.NUMBER_REGEXP = /^\s*(\-|\+)?(\d+|(\d*(\.\d*)))([eE][+-]?\d+)?\s*$/;

SIREPO.app.directive('advancedEditorPane', function(appState, $timeout) {
    return {
        restrict: 'A',
        scope: {
            viewName: '=',
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
                '<li data-ng-repeat="page in pages" role="presentation" class="{{page.class}}" data-ng-class="{active: page.isActive}"><a href data-ng-click="setActivePage(page)">{{ page.name }}</a></li>',
              '</ul>',
              '<br data-ng-if="pages" />',
              '<div data-ng-repeat="f in (activePage ? activePage.items : advancedFields)">',
                '<div class="form-group form-group-sm" data-ng-if="! isColumnField(f)" data-model-field="f" data-model-name="modelName" data-model-data="modelData"></div>',
                '<div data-ng-if="isColumnField(f)" data-column-editor="" data-column-fields="f" data-model-name="modelName" data-model-data="modelData"></div>',
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
                if ($scope.activePage) {
                    $scope.activePage.isActive = false;
                }
                $scope.activePage = page;
                page.isActive = true;
                if (appState.isLoaded() && $scope.parentController && $scope.parentController.handleModalShown) {
                    // invoke parentController after UI has been constructed
                    $timeout(function() {
                        $scope.parentController.handleModalShown($scope.modelName);
                    });
                }
            };
            // named tabs
            if ($scope.advancedFields.length && $scope.isColumnField($scope.advancedFields[0]) && ! $scope.isColumnField($scope.advancedFields[0][0])) {
                $scope.pages = [];
                var pageCount = 0;
                for (i = 0; i < $scope.advancedFields.length; i++) {
                    pageCount++;
                    var page = {
                        name: $scope.advancedFields[i][0],
                        items: [],
                        class: $scope.modelName + '-page-' + pageCount,
                    };
                    $scope.pages.push(page);
                    var fields = $scope.advancedFields[i][1];
                    for (var j = 0; j < fields.length; j++) {
                        page.items.push(fields[j]);
                    }
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
            if ($scope.pages) {
                $scope.setActivePage($scope.pages[0]);
            }
        },
        link: function(scope, element) {
            var resetActivePage = function() {
                if (scope.pages) {
                    scope.setActivePage(scope.pages[0]);
                }
            };
            if (scope.pages) {
                $(element).closest('.modal').on('show.bs.modal', resetActivePage);
                //TODO(pjm): need a generalized case for this
                $(element).closest('.srw-editor-holder').on('sr.resetActivePage', resetActivePage);
            }
            scope.$on('$destroy', function() {
                $(element).closest('.modal').off();
                $(element).closest('.srw-editor-holder').off();
            });
        }
    };
});

SIREPO.app.directive('srAlert', function(errorService) {
    return {
        restrict: 'A',
        scope: {},
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
                return errorService.alertText();
            };
            return;
        },
    };
});

SIREPO.app.directive('basicEditorPanel', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            viewName: '@',
        },
        template: [
            '<div class="panel panel-info" id="{{ \'sr-\' + viewName + \'-basicEditor\' }}">',
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

SIREPO.app.directive('buttons', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            fields: '=',
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
        },
        template: [
            '<div class="col-sm-6 pull-right sr-buttons" data-ng-show="isFormDirty()">',
              '<button data-ng-click="saveChanges()" class="btn btn-primary" data-ng-class="{\'disabled\': ! form.$valid}">Save Changes</button> ',
              '<button data-ng-click="cancelChanges()" class="btn btn-default">Cancel</button>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.form = $scope.$parent.form;
            var modelKey = $scope.modelData
                ? $scope.modelData.modelKey
                : $scope.modelName;
            var fieldsByModel = panelState.getFieldsByModel(modelKey, $scope.fields);

            function changeDone() {
                $scope.form.$setPristine();
            }

            $scope.cancelChanges = function() {
                appState.cancelChanges(Object.keys(fieldsByModel));
            };

            $scope.isFormDirty = function() {
                if ($scope.form.$dirty) {
                    return true;
                }
                return appState.areFieldsDirty(fieldsByModel);
            };

            $scope.saveChanges = function() {
                if ($scope.form.$valid) {
                    appState.saveChanges(Object.keys(fieldsByModel));
                }
            };

            $scope.$on(modelKey + '.changed', changeDone);
            $scope.$on('cancelChanges', function(e, name) {
                if (name == modelKey) {
                    changeDone();
                }
            });
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
            '<label>{{ label }} <span data-ng-show="tooltip" class="glyphicon glyphicon-info-sign sr-info-pointer"></span></label>',
        ],
        link: function link(scope, element) {
            if (scope.tooltip) {
                $(element).find('span').tooltip({
                    title: function() {
                        return scope.tooltip;
                    },
                    placement: 'bottom',
                });
                scope.$on('$destroy', function() {
                    $(element).find('span').tooltip('destroy');
                });
            }
        },
    };
});

SIREPO.app.directive('fieldEditor', function(appState, panelState, requestSender) {
    return {
        restirct: 'A',
        scope: {
            modelName: '=',
            field: '=fieldEditor',
            model: '=',
            customLabel: '=',
            labelSize: "@",
            fieldSize: "@",
        },
        template: [
            '<div class="model-{{modelName}}-{{field}}">',
            '<div data-ng-show="showLabel" data-label-with-tooltip="" class="control-label" data-ng-class="labelClass" data-label="{{ customLabel || info[0] }}" data-tooltip="{{ info[3] }}"></div>',
            '<div data-ng-switch="info[1]">',
              '<div data-ng-switch-when="Integer" data-ng-class="fieldClass">',
                '<input data-string-to-number="integer" data-ng-model="model[field]" class="form-control" style="text-align: right" required />',
              '</div>',
              '<div data-ng-switch-when="Float" data-ng-class="fieldClass">',
                '<input data-string-to-number="" data-ng-model="model[field]" class="form-control" style="text-align: right" required />',
              '</div>',
              //TODO(pjm): need a way to specify whether a field is option/required
              '<div data-ng-switch-when="OptionalString" data-ng-class="fieldClass">',
                '<input data-ng-model="model[field]" class="form-control" />',
              '</div>',
              '<div data-ng-switch-when="String" data-ng-class="fieldClass">',
                '<input data-ng-model="model[field]" class="form-control" required />',
              '</div>',
              '<div data-ng-switch-when="InputFile" class="col-sm-7">',
                '<div data-file-field="field" data-model="model" data-model-name="modelName" data-empty-selection-text="No File Selected"></div>',
              '</div>',
              SIREPO.appFieldEditors || '',
              // assume it is an enum
              '<div data-ng-switch-default data-ng-class="fieldClass">',
                '<div data-ng-if="wantEnumButtons" class="btn-group">',
                  '<a href class="btn sr-enum-button" data-ng-repeat="item in enum[info[1]]" data-ng-click="model[field] = item[0]" data-ng-class="{\'active btn-primary\': isSelectedValue(item[0]), \'btn-default\': ! isSelectedValue(item[0])}">{{ item[1] }}</a>',
                '</div>',
                '<select data-ng-if="! wantEnumButtons" number-to-string class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in enum[info[1]]"></select>',
              '</div>',
            '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {

            function fieldClass(fieldType, fieldSize, wantEnumButtons) {
                return 'col-sm-' + (fieldSize || (
                    (fieldType == 'Integer' || fieldType == 'Float')
                        ? '3'
                        : wantEnumButtons
                            ? '7'
                            : '5'
                ));
            }

            function showLabel(labelSize) {
                if (labelSize === '') {
                    return true;
                }
                return labelSize > 0;
            }

            function wantEnumButtons(fieldType, labelSize) {
                var hasLabelSizeOverride = labelSize ? true : false;
                var e = SIREPO.APP_SCHEMA.enum[fieldType];
                if (! e || e.length > 3 || hasLabelSizeOverride) {
                    return false;
                }
                var textSize = 0;
                for (var i = 0; i < e.length; i++) {
                    textSize += e[i][1].length;
                    if (textSize > 20) {
                        return false;
                    }
                }
                return true;
            }

            $scope.enum = SIREPO.APP_SCHEMA.enum;
            // field def: [label, type]
            $scope.info = appState.modelInfo($scope.modelName)[$scope.field];
            if (! $scope.info) {
                throw 'invalid model field: ' + $scope.modelName + '.' + $scope.field;
            }
            $scope.labelClass = 'col-sm-' + ($scope.labelSize || '5');
            $scope.wantEnumButtons = wantEnumButtons($scope.info[1], $scope.labelSize);
            $scope.fieldClass = fieldClass($scope.info[1], $scope.fieldSize, $scope.wantEnumButtons);
            $scope.showLabel = showLabel($scope.labelSize);
            $scope.isSelectedValue = function(value) {
                if ($scope.model && $scope.field) {
                    return $scope.model[$scope.field] == value;
                }
                return false;
            };
        },
    };
});

SIREPO.app.directive('loginMenu', function(requestSender) {
    return {
        restirct: 'A',
        scope: {},
        template: [
              '<li data-ng-if="isLoggedIn()" class="sr-logged-in-menu dropdown"><a href class="dropdown-toggle" data-toggle="dropdown"></span><img data-ng-src="https://avatars.githubusercontent.com/{{ userState.userName }}?size=40"</img> <span class="caret"></span></a>',
                '<ul class="dropdown-menu">',
                  '<li class="dropdown-header">Signed in as <strong>{{ userState.userName }}</strong></li>',
                  '<li class="divider"></li>',
                  '<li><a data-ng-href="{{ logoutURL }}">Sign out</a></li>',
                '</ul>',
              '</li>',
              '<li data-ng-if="isLoggedOut()" class="dropdown"><a href class="dropdown-toggle" data-toggle="dropdown"><span class="glyphicon glyphicon-user"></span> <span class="caret"></span></a>',
                '<ul class="dropdown-menu">',
                  '<li><a data-ng-href="{{ githubLoginURL() }}">Sign In with <strong>GitHub</strong></a></li>',
                '</ul>',
              '</li>',
        ].join(''),
        controller: function($scope) {
            $scope.userState = SIREPO.userState;
            $scope.githubLoginURL = function() {
                return requestSender.formatAuthUrl('github');
            };
            $scope.logoutURL = requestSender.formatUrl('oauthLogout', {
                '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
            });
            $scope.isLoggedIn = function() {
                return $scope.userState && $scope.userState.loginState == 'logged_in';
            };
            $scope.isLoggedOut = function() {
                return $scope.userState && ! $scope.isLoggedIn();
            };
        },
    };
});

SIREPO.app.directive('fileField', function(appState, panelState, requestSender, $http, errorService) {
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
            wantImageFile: '=',
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
            '<a data-ng-href="{{ downloadFileUrl() }}" type="button" title="Download" class="btn btn-default"><span class="glyphicon glyphicon-cloud-download"></a>',
            '<a href target="_self" title="Download Processed Image" class="btn btn-default" data-ng-if="wantImageFile" data-ng-click="downloadProcessedImage()"><span class="glyphicon glyphicon-filter"></span></a>',
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

            $scope.downloadProcessedImage = function() {
                if (!appState.isLoaded()) {
                    return;
                }
                var m = $scope.model.imageFile.match(/(([^\/]+)\.\w+)$/);
                if (!m) {
                    throw $scope.model.imageFile + ': invalid imageFile name';
                }
                var fn = m[2] + '_processed.tif';
                var url = requestSender.formatUrl({
                    routeName: 'getApplicationData',
                    '<filename>': fn
                });
                var err = function (response) {
                    errorService.alertText('Download failed: status=' + response.status);
                };
                //TODO: Error handling
                $http.post(
                    url,
                    {
                        'simulationId': appState.models.simulation.simulationId,
                        'simulationType': SIREPO.APP_SCHEMA.simulationType,
                        'method': 'processedImage',
                        'baseImage': m[1]
                    },
                    {responseType: 'blob'}
                ).then(
                    function (response) {
                        if (response.status == 200) {
                            saveAs(response.data, fn);
                            return;
                        }
                        err(response);
                    },
                    err);
            };

            $scope.hasValidFileSelected = function() {
                if ($scope.fileType && $scope.model) {
                    var f = $scope.model[$scope.fileField];
                    var list = requestSender.getAuxiliaryData($scope.fileType);
                    if (f && list && list.indexOf(f) >= 0) {
                        return true;
                    }
                }
                return false;
            };
            $scope.itemList = function() {
                if (! $scope.fileType) {
                    $scope.fileType = $scope.modelName + '-' + $scope.fileField;
                }
                if (requestSender.getAuxiliaryData($scope.fileType)) {
                    return requestSender.getAuxiliaryData($scope.fileType);
                }
                if (! appState.isLoaded()) {
                    return null;
                }
                requestSender.loadAuxiliaryData(
                    $scope.fileType,
                    requestSender.formatUrl('listFiles', {
                        '<simulation_id>': appState.models.simulation.simulationId,
                        '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        '<file_type>': $scope.fileType,
                    }));
                return null;
            };
            $scope.selectItem = function(item) {
                $scope.model[$scope.fileField] = item;
            };
            $scope.showFileUpload = function() {
                panelState.showModalEditor(
                    'fileUpload' + $scope.fileType,
                    '<div data-file-upload-dialog="" data-dialog-title="Upload File" data-file-type="fileType" data-model="model" data-field="fileField"></div>', $scope);
            };
            $scope.showFileReport = function() {
                //TODO(pjm): uncouple from beamline controller
                findParentAttribute('beamline').showFileReport($scope.fileType, $scope.model);
            };
        },
    };
});

SIREPO.app.directive('columnEditor', function(appState) {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            columnFields: '=',
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
        },
        template: [
            '<div data-ng-if="! oneLabelLayout" class="row">',
              '<div class="col-sm-6" data-ng-repeat="col in columnFields">',
                '<div class="lead text-center" data-ng-class="columnHeadingClass()">{{ col[0] }}</div>',
                '<div class="form-group form-group-sm" data-ng-repeat="f in col[1]">',
                  '<div data-model-field="f" data-label-size="7" data-field-size="5" data-custom-label="columnLabels[$parent.$index][$index]" data-model-name="modelName" data-model-data="modelData"></div>',
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
                  '<div data-model-field="f" data-label-size="7" data-field-size="5" data-custom-label="columnLabels[0][$index]" data-model-name="modelName" data-model-data="modelData"></div>',
                '</div>',
              '</div>',
              '<div class="col-sm-3">',
                '<div class="lead text-center" data-ng-class="columnHeadingClass()">{{ columnFields[1][0] }}</div>',
                '<div class="form-group form-group-sm" data-ng-repeat="f in columnFields[1][1]">',
                  '<div data-model-field="f" data-label-size="0" data-field-size="12" data-model-name="modelName" data-model-data="modelData"></div>',
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
                    if ($scope.columnLabels[0][i] != $scope.columnLabels[1][i]) {
                        return false;
                    }
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
            '<div class="modal fade" id="sr-fileUpload{{ fileType }}-editor" tabindex="-1" role="dialog">',
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
                if (! inputFile) {
                    return;
                }
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
                        $('#sr-fileUpload' + $scope.fileType + '-editor').modal('hide');
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
        restrict: 'A',
        scope: {
            helpTopic: '@helpButton',
        },
        template: [
            '<button class="close sr-help-icon" title="{{ helpTopic }} Help" data-ng-click="openHelp()"><span class="glyphicon glyphicon-question-sign"></span></button>',
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

SIREPO.app.directive('modalEditor', function(appState, panelState, $timeout) {
    return {
        restrict: 'A',
        scope: {
            viewName: '@',
            parentController: '=',
            modalTitle: '=?',
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
                        '<div data-advanced-editor-pane="" data-view-name="viewName" data-want-buttons="true" data-model-data="modelData" data-parent-controller="parentController"></div>',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            function hideModal() {
                if ($scope.editorId) {
                    $('#' + $scope.editorId).modal('hide');
                }
            }
            var viewInfo = appState.viewInfo($scope.viewName);
            if (! viewInfo) {
                throw 'missing view in schema: ' + $scope.viewName;
            }
            $scope.helpTopic = viewInfo.title;
            //TODO(pjm): cobbled-together to allow a view to refer to a model by name, ex. SRW simulationGrid view
            $scope.modelName = viewInfo.model || $scope.viewName;
            $scope.modelKey = $scope.modelName;
            $scope.editorId = 'sr-' + $scope.viewName + '-editor';
            if ($scope.modelData) {
                $scope.modelKey = $scope.modelData.modelKey;
                $scope.editorId = 'sr-' + $scope.modelKey + '-editor';
            }
            if (! $scope.modalTitle) {
                $scope.modalTitle = viewInfo.title;
            }
            $scope.$on('modelChanged', function (e, name) {
                if (name == $scope.modelKey) {
                    hideModal();
                }
            });
            $scope.$on('cancelChanges', hideModal);
        },
        link: function(scope, element) {
            $(element).on('shown.bs.modal', function() {
                $('#' + scope.editorId + ' .form-control').first().select();
                if (scope.parentController && scope.parentController.handleModalShown) {
                    $timeout(function() {
                        scope.parentController.handleModalShown(scope.modelName, scope.modelKey);
                    });
                }
            });
            $(element).on('hidden.bs.modal', function(e) {
                // ensure that a dismissed modal doesn't keep changes
                // ok processing will have already saved data before the modal is hidden
                var viewInfo = appState.viewInfo(scope.viewName);
                var fieldsByModel = panelState.getFieldsByModel(scope.modelKey, viewInfo.advanced);
                appState.cancelChanges(Object.keys(fieldsByModel));
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
        restrict: 'A',
        scope: {
            field: '=modelField',
            modelName: '=',
            customLabel: '=',
            labelSize: "@",
            fieldSize: "@",
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
        },
        template: [
            '<div data-field-editor="fieldName()" data-model-name="modelNameForField()" data-model="modelForField()" data-custom-label="customLabel" data-label-size="{{ labelSize }}" data-field-size="{{ fieldSize }}"></div>',
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
                if ($scope.modelData && ! modelField) {
                    return $scope.modelData.getData();
                }
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

SIREPO.app.directive('msieFontDisabledDetector', function(errorService, $interval) {
    return {
        restrict: 'A',
        link: function(scope, element) {
            //TODO(pjm): remove timeout hack, needed for MSIE and Edge
            $interval(
                function () {
                    if (! new Detector().detect('Glyphicons Halflings')) {
                        errorService.alertText('Font download has been disabled for this browser. Application icons will not be displayed correctly as a result. Either enable font download on the Internet Options / Security Settings menu or switch to a different browser, such as Google Chrome or Microsoft Edge.');
                    }
                },
                5000,
                1);
        },
    };
});

SIREPO.app.directive('numberToString', function() {
    return {
        restrict: 'A',
        require: 'ngModel',
        link: function(scope, element, attrs, ngModel) {
            ngModel.$parsers.push(function(value) {
                if (ngModel.$isEmpty(value)) {
                    return null;
                }
                return '' + value;
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

SIREPO.app.directive('panelHeading', function(appState, frameCache, panelState, requestSender, plotToPNG, $window) {
    return {
        restrict: 'A',
        scope: {
            panelHeading: '@',
            modelKey: '=',
            allowFullScreen: '@',
        },
        template: [
            '<span class="sr-panel-heading">{{ panelHeading }}</span>',
            '<div class="sr-panel-options pull-right">',
              '<a href data-ng-show="hasEditor" data-ng-click="showEditor()" title="Edit"><span class="sr-panel-heading glyphicon glyphicon-pencil"></span></a> ',
              '<div data-ng-if="allowFullScreen" data-ng-show="hasData()" class="dropdown" style="display: inline-block">',
                '<a href class="dropdown-toggle" data-toggle="dropdown" title="Download"> <span class="sr-panel-heading glyphicon glyphicon-cloud-download" style="margin-bottom: 0"></span></a> ',
                '<ul class="dropdown-menu dropdown-menu-right">',
                  '<li class="dropdown-header">Download Report</li>',
                  '<li><a href data-ng-click="downloadImage(480)">PNG - Small</a></li>',
                  '<li><a href data-ng-click="downloadImage(720)">PNG - Medium</a></li>',
                  '<li><a href data-ng-click="downloadImage(1080)">PNG - Large</a></li>',
                  '<li role="separator" class="divider"></li>',
                  '<li><a data-ng-href="{{ dataFileURL() }}" target="_blank">Raw Data File</a></li>',
                  SIREPO.APP_NAME == 'srw'
                      ? '<li><a href data-ng-click="srwExportPython()">Export Python Code</a></li>'
                      : '',
                '</ul>',
              '</div>',
              //'<a href data-ng-show="allowFullScreen" title="Full screen"><span class="sr-panel-heading glyphicon glyphicon-fullscreen"></span></a> ',
              '<a href data-ng-click="panelState.toggleHidden(modelKey)" data-ng-hide="panelState.isHidden(modelKey)" title="Hide"><span class="sr-panel-heading glyphicon glyphicon-triangle-top"></span></a> ',
              '<a href data-ng-click="panelState.toggleHidden(modelKey)" data-ng-show="panelState.isHidden(modelKey)" title="Show"><span class="sr-panel-heading glyphicon glyphicon-triangle-bottom"></span></a>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            // modelKey may not exist in viewInfo, assume it has an editor in that case
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
                if (! svg) {
                    return;
                }
                var fileName = $scope.panelHeading.replace(/(\_|\W|\s)+/g, '-') + '.png';
                var plot3dCanvas = $scope.reportPanel.find('canvas')[0];
                plotToPNG.downloadPNG(svg, height, plot3dCanvas, fileName);
            };
            $scope.srwExportPython = function() {
                $window.open(requestSender.formatUrl('pythonSource', {
                    '<simulation_id>': appState.models.simulation.simulationId,
                    '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                    '<model>': $scope.modelKey,
                }), '_blank');
            };
            $scope.hasData = function() {
                if (appState.isLoaded()) {
                    if (appState.isAnimationModelName($scope.modelKey)) {
                        return frameCache.getFrameCount() > 0;
                    }
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
            '<div data-ng-class="{\'sr-panel-loading\': panelState.isLoading(modelKey), \'sr-panel-error\': panelState.getError(modelKey), \'sr-panel-running\': panelState.isRunning(modelKey)}" class="panel-body" data-ng-hide="panelState.isHidden(modelKey)">',
              '<div data-ng-show="panelState.isLoading(modelKey)" class="lead sr-panel-wait"><span class="glyphicon glyphicon-hourglass"></span> {{ panelState.getStatusText(modelKey) }}</div>',
              '<div data-ng-show="panelState.getError(modelKey)" class="lead sr-panel-wait"><span class="glyphicon glyphicon-exclamation-sign"></span> {{ panelState.getError(modelKey) }}</div>',
              '<div data-ng-switch="reportContent" class="{{ panelState.getError(modelKey) ? \'sr-hide-report\' : \'\' }}">',
                '<div data-ng-switch-when="2d" data-plot2d="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
                '<div data-ng-switch-when="3d" data-plot3d="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
                '<div data-ng-switch-when="heatmap" data-heatmap="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
                '<div data-ng-switch-when="lattice" data-lattice="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
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
            requestPriority: '@',
        },
        template: [
            '<div class="panel panel-info">',
              '<div class="panel-heading clearfix" data-panel-heading="{{ reportTitle() }}" data-model-key="modelKey" data-allow-full-screen="1"></div>',
              '<div data-report-content="{{ reportPanel }}" data-model-key="{{ modelKey }}"><div data-ng-transclude=""></div></div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.modelKey = $scope.modelName;
            if ($scope.modelData) {
                $scope.modelKey = $scope.modelData.modelKey;
            }
            $scope.reportTitle = function() {
                return $scope.panelTitle ? $scope.panelTitle : appState.viewInfo($scope.modelName).title;
            };
        },
    };
});

SIREPO.app.directive('appHeaderLeft', function(panelState, appState, requestSender) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeaderLeft',
        },
        template: [
            '<ul class="nav navbar-nav" data-ng-if="showMenu()">',
              '<li data-ng-class="{active: nav.isActive(\'simulations\')}"><a href data-ng-click="nav.openSection(\'simulations\')"><span class="glyphicon glyphicon-th-list"></span> Simulations</a></li>',
            '</ul>',
            '<div data-ng-if="showTitle()" class="navbar-text"><a href data-ng-click="showSimulationModal()"><span data-ng-if="nav.sectionTitle()" class="glyphicon glyphicon-pencil"></span> <strong data-ng-bind="nav.sectionTitle()"></strong></a> <a href="{{ nav.sectionURL() }}" class="glyphicon glyphicon-link"></a></div>',
        ].join(''),
        controller: function($scope) {
            $scope.showMenu = function() {
                return ! SIREPO.IS_LOGGED_OUT;
            };
            $scope.showSimulationModal = function() {
                panelState.showModalEditor('simulation');
            };
            $scope.showTitle = function() {
                return ! $scope.nav.isActive('simulations');
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
                if (ngModel.$isEmpty(value))  {
                    return null;
                }
                if (SIREPO.NUMBER_REGEXP.test(value)) {
                    var v;
                    if (scope.numberType == 'integer') {
                        v = parseInt(value);
                        if (v != value) {
                            ngModel.$setViewValue(v);
                            ngModel.$render();
                        }
                        return v;
                    }
                    v = parseFloat(value);
                    if (isFinite(v)) {
                        return v;
                    }
                }
                return undefined;
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

SIREPO.app.directive('fileModel', ['$parse', function ($parse) {
    return {
        restrict: 'A',
        link: function(scope, element, attrs) {
            var model = $parse(attrs.fileModel);
            var modelSetter = model.assign;
            element.bind('change', function() {
                scope.$apply(function() {
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
        $http.get('/static/css/sirepo.css' + SIREPO.SOURCE_CACHE_KEY)
            .then(function(response) {
                if (svg.firstChild.nodeName != 'STYLE') {
                    var css = document.createElement('style');
                    css.type = 'text/css';
                    css.appendChild(document.createTextNode(response.data));
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
        }).then(
            function(response) {
                callback(response.data);
            },
            function() {
                //TODO(pjm): error handling
                srlog('file upload failed');
            });
    };
});
