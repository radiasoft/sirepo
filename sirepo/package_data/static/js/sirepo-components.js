'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.NUMBER_REGEXP = /^\s*(\-|\+)?(\d+|(\d*(\.\d*)))([eE][+-]?\d+)?\s*$/;

SIREPO.INFO_INDEX_LABEL = 0;
SIREPO.INFO_INDEX_TYPE = 1;
SIREPO.INFO_INDEX_DEFAULT_VALUE = 2;

SIREPO.ENUM_INDEX_VALUE = 0;
SIREPO.ENUM_INDEX_LABEL = 1;

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
            '<form name="form" class="form-horizontal" autocomplete="off" novalidate>',
              '<ul data-ng-if="pages" class="nav nav-tabs">',
                '<li data-ng-repeat="page in pages" role="presentation" class="{{page.class}}" data-ng-class="{active: page.isActive}"><a href data-ng-click="setActivePage(page)">{{ page.name }}</a></li>',
              '</ul>',
              '<br data-ng-if="pages" />',
              '<div class="lead text-center" style="white-space: pre-wrap;" data-ng-if="activePage.pageDescription">{{ activePage.pageDescription }}</div>',
              '<div data-ng-repeat="f in (activePage ? activePage.items : advancedFields)">',
                '<div class="form-group form-group-sm" data-ng-if="! isColumnField(f)" data-model-field="f" data-model-name="modelName" data-model-data="modelData"></div>',
                '<div data-ng-if="isColumnField(f)" data-column-editor="" data-column-fields="f" data-model-name="modelName" data-model-data="modelData"></div>',
              '</div>',
              '<div class="col-sm-6 pull-right" data-ng-if="wantButtons" data-buttons="" data-model-name="modelName" data-model-data="modelData" data-fields="advancedFields"></div>',
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
                        // tab page headings are indicated with a leading '*' character
                        if (fields[j].indexOf('*') === 0) {
                            page.pageDescription = fields[j].substring(1);
                        }
                        else {
                            page.items.push(fields[j]);
                        }
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

SIREPO.app.directive('srNotify', function(notificationService) {

    return {
        restrict: 'A',
        template: [
                '<div data-ng-show="notificationService.hasNext()" class="alert alert-success alert-dismissible sr-notify" role="alert">',
                '<button type="button" class="close" aria-label="Close" data-ng-click="notificationService.dismiss()">',
                    '<span aria-hidden="true">&times;</span>',
                '</button>',
                '<span data-ng-show="setContent()" id="notification-content"></span>',
                '</div>',
        ].join(''),
        controller: function($scope) {

            $scope.notificationService = notificationService;
            $scope.setContent = function() {
                $('#notification-content').html(notificationService.currentContent());
                return true;
            };
        },
    };
});

SIREPO.app.directive('basicEditorPanel', function(appState, panelState) {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            viewName: '@',
            parentController: '=',
            wantButtons: '@',
        },
        template: [
            '<div class="panel panel-info" id="{{ \'sr-\' + viewName + \'-basicEditor\' }}">',
              '<div class="panel-heading clearfix" data-panel-heading="{{ panelTitle }}" data-model-key="modelName"></div>',
                '<div class="panel-body" data-ng-hide="panelState.isHidden(modelName)">',
                  //TODO(pjm): not really an advanced editor pane anymore, should get renamed
                  '<div data-advanced-editor-pane="" data-view-name="viewName" data-want-buttons="{{ wantButtonsEval }}" data-field-def="basic" data-parent-controller="parentController"></div>',
              '<div data-ng-transclude=""></div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var viewInfo = appState.viewInfo($scope.viewName);
            $scope.modelName = viewInfo.model || $scope.viewName;
            $scope.panelState = panelState;
            $scope.panelTitle = viewInfo.title;
            if ($scope.wantButtons === null || $scope.wantButtons === undefined) {
                $scope.wantButtonsEval = '1';
            }
            else {
                $scope.wantButtonsEval = $scope.wantButtons;
            }
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
            '<div data-ng-show="isFormDirty()">',
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
                          '<button data-ng-if="okText" data-ng-click="clicked()" class="btn btn-default">{{ okText }}</button>',
                          ' <button data-dismiss="modal" class="btn btn-default">{{ cancelText || \'Cancel\' }}</button>',
                        '</div>',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.clicked = function() {
                if ($scope.okClicked() !== false) {
                    $('#' + $scope.id).modal('hide');
                }
            };
        },
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
                    html: scope.tooltip.indexOf('</') >= 0,
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
        restrict: 'A',
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
              '<div data-ng-switch-when="OptionalStringUpper" data-ng-class="fieldClass">',
                '<input data-ng-model="model[field]" class="form-control" ng-change="model[field] = (model[field] | uppercase)" />',
              '</div>',
              '<div data-ng-switch-when="String" data-ng-class="fieldClass">',
                '<input data-ng-model="model[field]" class="form-control" required />',
              '</div>',
              '<div data-ng-switch-when="SafePath" data-ng-class="fieldClass">',
                '<input data-safe-path="" data-ng-model="model[field]" class="form-control" required />',
                '<div class="sr-input-warning" data-ng-show="showWarning">{{warningText}}</div>',
              '</div>',
              '<div data-ng-switch-when="InputFile" class="col-sm-7">',
                '<div data-file-field="field" data-model="model" data-model-name="modelName" data-empty-selection-text="No File Selected"></div>',
              '</div>',
               '<div data-ng-switch-when="Boolean" class="col-sm-7">',
                 // angular has problems initializing checkboxes - ngOpen has no effect on them, but we can use it to change the state as the models load
                 '<input class="sr-bs-toggle" data-ng-open="! model[field] || fieldDelegate.refreshChecked()" data-ng-model="model[field]" data-bootstrap-toggle="" data-model="model" data-field="field" data-field-delegate="fieldDelegate" data-info="info" type="checkbox" data-toggle="toggle" data-on="{{onValue}}" data-off="{{offValue}}">',
               '</div>',
              '<div data-ng-switch-when="ColorMap" class="col-sm-7">',
                '<div data-color-map-menu="" class="dropdown"></div>',
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
                if (! e || e.length == 1 || e.length > 3 || hasLabelSizeOverride) {
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
            $scope.fieldDelegate = {};
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

            $scope.clearViewValue = function(model) {
                model.$setViewValue('');
                model.$render();
            };
        },
    };
});

SIREPO.app.directive('loginMenu', function(requestSender, notificationService) {

    var sr_login_notify_cookie = 'net.sirepo.login_notify_timeout';
    var sr_login_notify_timeout = 1*24*60*60*1000;
    var sr_login_notify_content = '<strong>To save your work, log into GitHub</strong><span class="glyphicon glyphicon-hand-up sr-notify-pointer"></span>';

    return {
        restrict: 'A',
        scope: {},
        template: [
              '<li data-ng-if="isLoggedIn()" class="sr-logged-in-menu dropdown"><a href class="dropdown-toggle" data-toggle="dropdown"></span><img data-ng-src="https://avatars.githubusercontent.com/{{ userState.userName }}?size=40"</img> <span class="caret"></span></a>',
                '<ul class="dropdown-menu">',
                  '<li class="dropdown-header">Signed in as <strong>{{ userState.userName }}</strong></li>',
                  '<li class="divider"></li>',
                  '<li><a data-ng-href="{{ logoutURL }}" data-ng-click="doLogoutTasks()">Sign out</a></li>',
                '</ul>',
              '</li>',
              '<li data-ng-if="isLoggedOut()" class="dropdown"  data-ng-class="{\'alert-success\': notificationService.currentNotification == loginNotification}">',
                '<a href class="dropdown-toggle" data-toggle="dropdown"><span class="glyphicon glyphicon-user"></span> <span class="caret"></span></a>',
                '<ul class="dropdown-menu">',
                  '<li><a data-ng-href="{{ githubLoginURL() }}" data-ng-click="doLoginTasks()">Sign In with <strong>GitHub</strong></a></li>',
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
            $scope.doLogoutTasks = function() {
                $scope.loginNotification.active = true;
                notificationService.sleepNotification($scope.loginNotification);
            };
            $scope.doLoginTasks = function() {
                $scope.loginNotification.active = false;
                notificationService.dismissNotification($scope.loginNotification);
            };

            $scope.notificationService = notificationService;
            $scope.sr_login_notify_cookie = sr_login_notify_cookie;
            $scope.loginNotification = {
                name: sr_login_notify_cookie,
                timeout: sr_login_notify_timeout,
                content: sr_login_notify_content,
                active: $scope.isLoggedOut(),
                recurs: true,
            };
            notificationService.addNotification($scope.loginNotification);

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
              '<li data-ng-repeat="item in itemList()" class="sr-model-list-item"><a href data-ng-click="selectItem(item)">{{ item }}<span data-ng-show="! isSelectedItem(item)" data-ng-click="confirmDeleteItem(item, $event)" class="glyphicon glyphicon-remove"></span></a></li>',
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
            var modalId = null;
            $scope.isDeletingFile = false;

            function sortList(list) {
                if (list) {
                    list.sort(function(a, b) {
                        return a.localeCompare(b);
                    });
                }
            }

            $scope.confirmDeleteItem = function(item, $event) {
                $scope.deleteFileError = '';
                $scope.isDeletingFile = false;
                $event.stopPropagation();
                $event.preventDefault();
                $scope.deleteItem = item;
                var modelKey = 'fileDelete' + $scope.fileType;
                modalId = panelState.modalId(modelKey);
                panelState.showModalEditor(
                    modelKey,
                    '<div data-confirmation-modal="" data-id="' + modalId + '" data-title="Delete File?" data-ok-text="Delete" data-ok-clicked="deleteSelected()"><div style="white-space: pre-line"><span data-ng-if="isDeletingFile" class="glyphicon glyphicon-hourglass"></span> {{ confirmDeleteText() }}</div></div>', $scope);
            };

            $scope.confirmDeleteText = function() {
                if ($scope.deleteFileError) {
                    return $scope.deleteFileError;
                }
                return $scope.isDeletingFile
                    ? ('Deleting file "' + $scope.deleteItem + '". Please wait.')
                    : ('Delete file "' + $scope.deleteItem + '"?');
            };

            $scope.deleteSelected = function() {
                if (! $scope.isDeletingFile) {
                    $scope.isDeletingFile = true;
                    requestSender.sendRequest(
                        'deleteFile',
                        function(data) {
                            $scope.isDeletingFile = false;
                            if (data.error) {
                                $scope.deleteFileError = data.error + "\n\n"
                                    + data.fileList.join("\n");
                            }
                            else {
                                var list = requestSender.getAuxiliaryData($scope.fileType);
                                list.splice(list.indexOf($scope.deleteItem), 1);
                                $('#' + modalId).modal('hide');
                            }
                        },
                        {
                            simulationId: appState.models.simulation.simulationId,
                            simulationType: SIREPO.APP_SCHEMA.simulationType,
                            fileType: $scope.fileType,
                            fileName: $scope.deleteItem,
                        });
                }
                return false;
            };

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
                var fn = m[2] + '_processed.' + $scope.model.outputImageFormat;
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
                        'baseImage': m[1],
                        'model': $scope.model,
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
            $scope.isSelectedItem = function(item) {
                if ($scope.model) {
                    return item == $scope.model[$scope.fileField];
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
                    }), sortList);
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
                panelState.findParentAttribute($scope, 'beamline').showFileReport($scope.fileType, $scope.model);
            };

            $scope.$on('$destroy', function() {
                if (modalId) {
                    $('#' + modalId).remove();
                }
            });
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

SIREPO.app.directive('fileUploadDialog', function(appState, fileUpload, panelState, requestSender) {
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
                          '<div class="text-warning" style="white-space: pre-line"><strong>{{ fileUploadError }}</strong></div>',
                        '</div>',
                        '<div data-ng-if="isUploading" class="col-sm-6 pull-right">Please Wait...</div>',
                        '<div class="clearfix"></div>',
                        '<div class="col-sm-6 pull-right">',
                          '<button data-ng-show="isConfirming" data-ng-click="uploadFile(inputFile, true)" class="btn btn-warning" data-ng-disabled="isUploading">Replace File</button>',
                          '<button data-ng-hide="isConfirming" data-ng-click="uploadFile(inputFile)" class="btn btn-primary" data-ng-disabled="isUploading">Save Changes</button>',
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
            $scope.isConfirming = false;

            $scope.uploadFile = function(inputFile, isConfirmed) {
                if (! inputFile) {
                    return;
                }
                $scope.isUploading = true;
                fileUpload.uploadFileToUrl(
                    inputFile,
                    $scope.isConfirming
                        ? {
                            confirm: $scope.isConfirming,
                        }
                        : null,
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
                            if (data.fileList) {
                                $scope.fileUploadError += "\n\n" + data.fileList.join("\n");
                                $scope.isConfirming = true;
                            }
                            return;
                        }
                        if ($scope.model[$scope.field] != data.filename) {
                            $scope.model[$scope.field] = data.filename;
                            var list = requestSender.getAuxiliaryData($scope.fileType);
                            if (list.indexOf(data.filename) < 0) {
                                list.push(data.filename);
                            }
                        }
                        else {
                            // force the reports to update, the model fields are unchanged
                            appState.updateReports();
                        }
                        $('#' + panelState.modalId('fileUpload' + $scope.fileType)).modal('hide');
                    });
            };
        },
        link: function(scope, element) {
            $(element).on('show.bs.modal', function() {
                scope.isConfirming = false;
                scope.isUploading = false;
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

SIREPO.app.directive('lineoutCsvLink', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            axis: '@lineoutCsvLink',
        },
        template: [
            '<a href data-ng-show=":: is3dPlot()" data-ng-click="exportLineout()">CSV - {{:: axisName }} Cut</a>',
        ].join(''),
        controller: function($scope) {

            function findReportPanelScope() {
                var s = $scope.$parent;
                while (s && ! s.reportPanel) {
                    s = s.$parent;
                }
                return s;
            }

            $scope.axisName = $scope.axis == 'x' ? 'Horizontal' : 'Vertical';

            $scope.exportLineout = function() {
                findReportPanelScope().$broadcast(SIREPO.PLOTTING_LINE_CSV_EVENT, $scope.axis);
            };

            $scope.is3dPlot = function() {
                return panelState.findParentAttribute($scope, 'reportPanel') == '3d';
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
            $scope.editorId = panelState.modalId($scope.viewName);
            if ($scope.modelData) {
                $scope.modelKey = $scope.modelData.modelKey;
                $scope.editorId = panelState.modalId($scope.modelKey);
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

SIREPO.app.directive('safePath', function() {

    var unsafe_path_chars = '\\/|&:+?\'"<>'.split('');
    var unsafe_path_warn = ' must not include any of the following: ' +
        unsafe_path_chars.join(' ');
    var unsafe_path_regexp = new RegExp('[\\' + unsafe_path_chars.join('\\') + ']');

    return {
        restrict: 'A',
        require: 'ngModel',
        link: function(scope, element, attrs, ngModel, $sce) {

            scope.showWarning = false;
            scope.warningText = '';

            ngModel.$validators.safe = function(value) {
                scope.showWarning = unsafe_path_regexp.test(value);
                if( scope.showWarning ) {
                    scope.warningText = (scope.info ? scope.info[0] : 'Value') + unsafe_path_warn;
                }
                return !scope.showWarning;
            };

            // broadcast by root scope
            scope.$on('cancelChanges', function(e, name) {
                //TODO(pjm): need something other than clearViewValue()
                // otherwise cancelChanges event could cause appState.models.simulation.name to get
                // cleared unexpectantly, for now guarding with cancel on simulation or simFolder models
                if (name == 'simulation' || name == 'simFolder') {
                    scope.showWarning = false;
                    // appears that invalid text will not be cleared unless we do this
                    scope.clearViewValue(ngModel);
                }
            });
        },
    };
});

SIREPO.app.directive('colorMapMenu', function(appState, plotting) {

    return {
        restrict: 'A',
        template: [
            '<button class="btn btn-primary dropdown-toggle" type="button" data-toggle="dropdown"><span class="sr-color-map-indicator" data-ng-style="colorMapStyle(model[field])"></span> {{ plotting.colorMapNameOrDefault(model[field], reportDefaultMap) }} <span class="caret"></span></button>',
            '<ul class="dropdown-menu sr-button-menu">',
                '<li data-ng-repeat="item in enum[info[1]]" class="sr-button-menu">',
                    '<button class="btn btn-block"  data-ng-class="{\'sr-button-menu-selected\': isSelectedMap(item[0]), \'sr-button-menu-unselected\': ! isSelectedMap(item[0])}" data-ng-click="setColorMap(item[0])">',
                        '<span class="sr-color-map-indicator" data-ng-style="colorMapStyle(item[0])"></span> {{item[1]}} <span data-ng-if="isDefaultMap(item[0])" class="glyphicon glyphicon-star-empty"></span><span data-ng-if="isSelectedMap(item[0])" class="glyphicon glyphicon-ok"></span>',
                    '</button>',
                '</li>',
            '</ul>',
        ].join(''),
        controller: function($scope) {

            $scope.enum = SIREPO.APP_SCHEMA.enum;
            $scope.info = appState.modelInfo($scope.modelName)[$scope.field];
            $scope.reportDefaultMap = $scope.info[SIREPO.INFO_INDEX_DEFAULT_VALUE];
            if (!$scope.info) {
                throw 'invalid model field: ' + $scope.modelName + '.' + $scope.field;
            }
            $scope.isSelectedValue = function(value) {
                return $scope.model[$scope.field] == value;
            };
            $scope.isSelectedMap = function(mapName) {
                if($scope.model && $scope.model[$scope.field]) {
                    return $scope.isSelectedValue(mapName);
                }
                return $scope.isDefaultMap(mapName);
            };
            $scope.isDefaultMap = function(mapName) {
                return plotting.colorMapNameOrDefault(mapName, $scope.reportDefaultMap) === plotting.colorMapNameOrDefault(null, $scope.reportDefaultMap);
            };
            $scope.setColorMap = function(mapName) {
                $scope.model[$scope.field] = mapName;
            };

            $scope.plotting = plotting;
            $scope.colorMapStyle = function(mapName) {

                var map = plotting.colorMapOrDefault(mapName, $scope.reportDefaultMap);
                if (! map) {
                    return {};
                }

                var css = 'linear-gradient(to right, ' + map[0];
                for(var i = 1; i < map.length; ++i) {
                    css += ', ';
                    css += map[i];
                }
                css += ')';
                return {
                    'background': css,
                };

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
SIREPO.app.directive('panelHeading', function(appState, frameCache, panelState, requestSender, plotToPNG) {
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
                  SIREPO.appDownloadLinks || '',
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

            $scope.dataFileURL = function(suffix) {
                if (appState.isLoaded()) {
                    var params = {
                        '<simulation_id>': appState.models.simulation.simulationId,
                        '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        '<model>': $scope.modelKey,
                        '<frame>': appState.isAnimationModelName($scope.modelKey)
                            ? frameCache.getCurrentFrame($scope.modelKey)
                            : -1,
                    };
                    if (suffix) {
                        params['<suffix>'] = suffix;
                    }
                    return requestSender.formatUrl('downloadDataFile', params);
                }
                return '';
            };
            $scope.downloadImage = function(height) {
                var svg = $scope.panel.find('svg')[0];
                if (! svg) {
                    return;
                }
                var fileName = $scope.panelHeading.replace(/(\_|\W|\s)+/g, '-') + '.png';
                var plot3dCanvas = $scope.panel.find('canvas')[0];
                plotToPNG.downloadPNG(svg, height, plot3dCanvas, fileName);
            };
            $scope.hasData = function() {
                if (appState.isLoaded()) {
                    if (panelState.isHidden($scope.modelKey)) {
                        return false;
                    }
                    if (appState.isAnimationModelName($scope.modelKey)) {
                        return frameCache.getFrameCount($scope.modelKey) > 0;
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
            scope.panel = element.next();
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
                //TODO(pjm): these reports are specific to the elegant/hellweg apps
                '<div data-ng-switch-when="lattice" data-lattice="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
                '<div data-ng-switch-when="particle" data-particle="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
                '<div data-ng-switch-when="parameter" data-parameter-plot="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
                '<div data-ng-switch-when="conductorGrid" data-conductor-grid="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
                '<div data-ng-switch-when="dicom" data-dicom-plot="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
                '<div data-ng-switch-when="impactDensity" data-impact-density-plot="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
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

SIREPO.app.directive('appHeaderBrand', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeaderBrand',
            appUrl: '@',
        },
        template: [
            '<div class="navbar-header">',
              '<a class="navbar-brand" href="/#about"><img style="width: 40px; margin-top: -10px;" src="/static/img/radtrack.gif" alt="radiasoft"></a>',
              '<div class="navbar-brand">',
                '<a data-ng-href="{{ appUrl || nav.sectionURL(\'simulations\') }}">',
                  SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_SCHEMA.simulationType].longName,
                '</a>',
              '</div>',
            '</div>',
        ].join(''),
    };
});

SIREPO.app.directive('appHeaderLeft', function(panelState, appState, requestSender, $window) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeaderLeft',
            simulationsLinkText: '@',
        },
        template: [
            '<ul class="nav navbar-nav" data-ng-if="showMenu()">',
              '<li data-ng-class="{active: nav.isActive(\'simulations\')}"><a href data-ng-click="nav.openSection(\'simulations\')"><span class="glyphicon glyphicon-th-list"></span> {{ simulationsLinkText }}</a></li>',
            '</ul>',
            '<div data-ng-if="showTitle()" class="navbar-text">',
                '<a href data-ng-click="showSimulationModal()"><span data-ng-if="nav.sectionTitle()" class="glyphicon glyphicon-pencil"></span> <strong data-ng-bind="nav.sectionTitle()"></strong></a> ',
                '<a href data-ng-click="showSimulationLink()" class="glyphicon glyphicon-link"></a>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            if (! $scope.simulationsLinkText) {
                $scope.simulationsLinkText = 'Simulations';
            }
            $scope.showMenu = function() {
                return ! SIREPO.IS_LOGGED_OUT;
            };
            $scope.showTitle = function() {
                return ! $scope.nav.isActive('simulations');
            };
            $scope.showSimulationLink = function() {
                panelState.showModalEditor(
                    'simulationLink',
                    [
                        '<div data-confirmation-modal="" data-id="sr-simulationLink-editor" data-title="Share link for {{ nav.sectionTitle() }}" data-cancel-text="OK">',
                            '<input id="sr-simulation-link-input" type="text" readonly="true"',
                                'value="',
                                    $window.location.href,
                                '"',
                                'class="form-control input-lg" onfocus="this.select();" autofocus="true"/>',
                        '</div>',
                    ].join(''),
                    $scope
                );
            };
            $scope.showSimulationModal = function() {
                panelState.showModalEditor('simulation');
            };
        },
    };
});

SIREPO.app.directive('appHeaderRight', function(panelState, appState, appDataService, $window) {
    return {
        restrict: 'A',
        transclude: {
            appHeaderRightSimLoadedSlot: '?appHeaderRightSimLoaded',
            appHeaderRightSimListSlot: '?appHeaderRightSimList',
            appSettingsSlot: '?appSettings',
        },
        scope: {
            nav: '=appHeaderRight',
        },
        template: [
            '<div class="nav sr-navbar-right-flex">',
                '<ul class="nav navbar-nav" data-ng-show="isLoaded()">',
                    '<li data-ng-transclude="appHeaderRightSimLoadedSlot"></li>',
                    '<li data-ng-if="hasDocumentationUrl()"><a href data-ng-click="openDocumentation()"><span class="glyphicon glyphicon-book"></span> Notes</a></li>',
                    '<li data-settings-menu="nav">',
                        '<app-settings data-ng-transclude="appSettingsSlot"></app-settings>',
                    '</li>',
                '</ul>',
                '<ul class="nav navbar-nav" data-ng-show="nav.isActive(\'simulations\')">',
                    '<li><a href data-ng-click="showSimulationModal()"><span class="glyphicon glyphicon-plus sr-small-icon"></span><span class="glyphicon glyphicon-file"></span> New Simulation</a></li>',
                    '<li><a href data-ng-click="showNewFolderModal()"><span class="glyphicon glyphicon-plus sr-small-icon"></span><span class="glyphicon glyphicon-folder-close"></span> New Folder</a></li>',
                    '<li data-ng-transclude="appHeaderRightSimListSlot"></li>',
                '</ul>',
                '<ul class="nav navbar-nav navbar-right" data-login-menu="" data-ng-if="modeIsDefault()"></ul>',
            '</div>',
        ].join(''),
        link: function(scope) {
           scope.nav.isLoaded = scope.isLoaded;
           scope.nav.simulationName = scope.simulationName;
           scope.nav.hasDocumentationUrl = scope.hasDocumentationUrl;
           scope.nav.openDocumentation = scope.openDocumentation;
           scope.nav.modeIsDefault = scope.modeIsDefault;
           scope.nav.showSimulationModal = scope.showSimulationModal;
        },
        controller: function($scope) {

            $scope.modeIsDefault = function () {
                return appDataService.isApplicationMode('default');
            };
            $scope.isLoaded = function() {
                if ($scope.nav.isActive('simulations')) {
                    return false;
                }
                return appState.isLoaded();
            };
            $scope.simulationName = function() {
                if (appState.isLoaded()) {
                    return appState.models.simulation.name;
                }
                return '';
            };
            $scope.showNewFolderModal = function() {
                panelState.showModalEditor('simFolder');
            };
            $scope.showSimulationModal = function() {
                panelState.showModalEditor('simulation');
            };

            $scope.hasDocumentationUrl = function() {
                if (appState.isLoaded()) {
                    return appState.models.simulation.documentationUrl;
                }
                return false;
            };
            $scope.openDocumentation = function() {
                $window.open(appState.models.simulation.documentationUrl, '_blank');
            };
        },
    };
});

SIREPO.app.directive('settingsMenu', function(appState, appDataService, panelState, requestSender, $location, $window) {

    return {
        restrict: 'A',
        transclude: {
            appSettingsSlot: '?appSettings',
        },
        scope: {
            nav: '=settingsMenu',
        },
        template: [
              '<ul class="nav navbar-nav sr-navbar-right">',
                '<li>',
                  '<a href class="dropdown-toggle" data-toggle="dropdown"><span class="glyphicon glyphicon-cog"></span> <span class="caret"></span></a>',
                  '<ul class="dropdown-menu">',
                    //  App-specific settings are transcluded here
                    '<li class="sr-settings-submenu" data-ng-transclude="appSettingsSlot"></li>',
                    '<li><a href data-ng-if="nav.modeIsDefault()" data-ng-click="showDocumentationUrl()"><span class="glyphicon glyphicon-book"></span> Simulation Documentation URL</a></li>',
                    '<li><a href data-ng-click="exportArchive(\'zip\')"><span class="glyphicon glyphicon-cloud-download"></span> Export as ZIP</a></li>',
                    '<li data-ng-if="canCopy()"><a href data-ng-click="copy()"><span class="glyphicon glyphicon-copy"></span> Open as a New Copy</a></li>',
                    '<li data-ng-if="isExample()"><a href data-target="#reset-confirmation" data-toggle="modal"><span class="glyphicon glyphicon-repeat"></span> Discard Changes to Example</a></li>',
                    '<li data-ng-if="! isExample()"><a href data-target="#delete-confirmation" data-toggle="modal"><span class="glyphicon glyphicon-trash"></span> Delete</a></li>',
                    '<li data-ng-if="hasRelatedSimulations()" class="divider"></li>',
                    '<li data-ng-if="hasRelatedSimulations()" class="sr-dropdown-submenu">',
                      '<a href><span class="glyphicon glyphicon-chevron-left"></span> Related Simulations</a>',
                      '<ul class="dropdown-menu">',
                        '<li data-ng-repeat="item in relatedSimulations"><a href data-ng-click="openRelatedSimulation(item)">{{ item.name }}</a></li>',
                      '</ul>',
                    '</li>',
                  '</ul>',
                '</li>',
              '</ul>',
        ].join(''),
        controller: function($scope) {
            var self = this;
            var currentSimulationId = null;

            function simulationId() {
                return appState.models.simulation.simulationId;
            }
            function simulationName() {
                return appState.models.simulation.name;
            }

            $scope.showDocumentationUrl = function() {
                panelState.showModalEditor('simDoc');
            };

            $scope.relatedSimulations = [];

            $scope.canCopy = function() {
                return appDataService.canCopy();
            };
            $scope.copy = function() {
                appState.copySimulation(
                    simulationId(),
                    function(data) {
                        requestSender.localRedirect('source', {
                            ':simulationId': data.models.simulation.simulationId,
                        });
                    });
            };

            $scope.hasRelatedSimulations = function() {
                if (appState.isLoaded()) {
                    if (currentSimulationId == appState.models.simulation.simulationId) {
                        return $scope.relatedSimulations.length > 0;
                    }
                    currentSimulationId = appState.models.simulation.simulationId;
                    requestSender.sendRequest(
                        'listSimulations',
                        function(data) {
                            for (var i = 0; i < data.length; i++) {
                                var item = data[i];
                                if (item.simulationId == currentSimulationId) {
                                    data.splice(i, 1);
                                    break;
                                }
                            }
                            $scope.relatedSimulations = data;
                        },
                        {
                            simulationType: SIREPO.APP_SCHEMA.simulationType,
                            search: {
                                'simulation.folder': appState.models.simulation.folder,
                            },
                        });
                }
                return false;
            };

            $scope.isExample = function() {
                if (appState.isLoaded()) {
                    return appState.models.simulation.isExample;
                }
                return false;
            };

            $scope.openRelatedSimulation = function(item) {
                if ($scope.nav.isActive('beamline')) {
                    requestSender.localRedirect('beamline', {
                        ':simulationId': item.simulationId,
                    });
                    return;
                }
                requestSender.localRedirect('source', {
                    ':simulationId': item.simulationId,
                });
            };

            $scope.exportArchive = function(extension) {
                $window.open(requestSender.formatUrl('exportArchive', {
                    '<simulation_id>': simulationId(),
                    '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                    '<filename>':  $scope.nav.simulationName() + '.' + extension,
                }), '_blank');
            };
        },
    };
});


SIREPO.app.directive('deleteSimulationModal', function(appState, $location) {
    return {
        restrict: 'A',
        scope: {
            nav: '=deleteSimulationModal',
        },
        template: [
            '<div data-confirmation-modal="" data-id="delete-confirmation" data-title="Delete Simulation?" data-ok-text="Delete" data-ok-clicked="deleteSimulation()">Delete simulation &quot;{{ simulationName() }}&quot;?</div>',
        ].join(''),
        controller: function($scope) {
            $scope.deleteSimulation = function() {
                appState.deleteSimulation(
                    appState.models.simulation.simulationId,
                    function() {
                        $location.path('/simulations');
                    });
            };
            $scope.simulationName = function() {
                if (appState.isLoaded()) {
                    return appState.models.simulation.name;
                }
                return '';
            };
        },
    };
});

SIREPO.app.directive('resetSimulationModal', function(appState, requestSender, appDataService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=resetSimulationModal',
        },
        template: [
            '<div data-confirmation-modal="" data-id="reset-confirmation" data-title="Reset Simulation?" data-ok-text="Discard Changes" data-ok-clicked="revertToOriginal()">Discard changes to &quot;{{ simulationName() }}&quot;?</div>',
        ].join(''),
        controller: function($scope) {
            function revertSimulation() {
                $scope.nav.revertToOriginal(
                    appDataService.getApplicationMode(),
                    appState.models.simulation.name);
            }

            $scope.revertToOriginal = function() {
                var resetData = appDataService.appDataForReset();
                if (resetData) {
                    requestSender.getApplicationData(resetData, revertSimulation);
                }
                else {
                    revertSimulation();
                }
            };
            $scope.simulationName = function() {
                if (appState.isLoaded()) {
                    return appState.models.simulation.name;
                }
                return '';
            };
        },
    };
});


SIREPO.app.directive('commonFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=commonFooter',
        },
        template: [
            '<div data-delete-simulation-modal="nav"></div>',
            '<div data-reset-simulation-modal="nav"></div>',
        ].join(''),
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

SIREPO.app.directive('bootstrapToggle', function() {

    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '<',
            fieldDelegate: '=',
            info: '<',
        },
        link: function(scope, element) {

            var toggle = $(element);
            scope.isRefreshing = false;

            toggle.bootstrapToggle({
                on: scope.onValue,
                off: scope.offValue,
            });

            toggle.change(function() {
                // do not change the model if this was called from refreshChecked()
                if(! scope.isRefreshing) {
                    scope.model[scope.field] = toggle.prop('checked') ? '1' : '0';
                    scope.$apply();
                }
                scope.isRefreshing = false;
            });

            // called by ngOpen in template - checkbox will not initialize properly otherwise.
            // must live in an object to invoke with isolated scope
            scope.fieldDelegate.refreshChecked = function() {
                if(scope.model && scope.field) {
                    var val = scope.model[scope.field];
                    // don't refresh the toggle state if it did not change
                    if(toggle.prop('checked') != val) {
                        scope.isRefreshing = true;
                        toggle.bootstrapToggle(val != 0 ? 'on' : 'off');
                    }
                }
                return true;
            };

            scope.$on('$destroy', function() {
                if (toggle) {
                    //TODO(pjm): off() needed before destroy or memory is not released?
                    toggle.off();
                    toggle.bootstrapToggle('destroy');
                }
            });
        },
        controller: function($scope) {
            $scope.onValue = toggleValueAlias(1);
            $scope.offValue = toggleValueAlias(0);
            function toggleValueAlias(on) {
                return SIREPO.APP_SCHEMA.enum[$scope.info[SIREPO.INFO_INDEX_TYPE]][on][SIREPO.ENUM_INDEX_LABEL];
            }
        },
    };
});


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
                    // work-around bug fix #857, canvg.js doesn't handle non-standard css
                    response.data = response.data.replace('input::-ms-clear', 'ms-clear');
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

SIREPO.app.service('utilities', function() {

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
        // TODO(mvk): other types here, for now just accept everything
        return true;
    };

});
