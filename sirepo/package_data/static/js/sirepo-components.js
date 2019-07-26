'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.NUMBER_REGEXP = /^\s*(\-|\+)?(\d+|(\d*(\.\d*)))([eE][+-]?\d+)?\s*$/;

SIREPO.INFO_INDEX_LABEL = 0;
SIREPO.INFO_INDEX_TYPE = 1;
SIREPO.INFO_INDEX_DEFAULT_VALUE = 2;
SIREPO.INFO_INDEX_TOOL_TIP = 3;
SIREPO.INFO_INDEX_MIN = 4;
SIREPO.INFO_INDEX_MAX = 5;

SIREPO.ENUM_INDEX_VALUE = 0;
SIREPO.ENUM_INDEX_LABEL = 1;

SIREPO.app.directive('advancedEditorPane', function(appState, panelState) {
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
            '<h5 data-ng-if="description"><span data-text-with-math="description"></span></h5>',
            '<form name="form" class="form-horizontal" autocomplete="off" novalidate>',
              '<ul data-ng-if="pages" class="nav nav-tabs">',
                '<li data-ng-repeat="page in pages" role="presentation" class="{{page.class}}" data-ng-class="{active: page.isActive}"><a href data-ng-click="setActivePage(page)">{{ page.name }}</a></li>',
              '</ul>',
              '<br data-ng-if="pages" />',
              '<div class="lead text-center" style="white-space: pre-wrap;" data-ng-if="activePage.pageDescription"><span data-text-with-math="activePage.pageDescription"</span></div>',
              '<div data-ng-repeat="f in (activePage ? activePage.items : advancedFields)">',
                '<div class="form-group form-group-sm" data-ng-if="! isColumnField(f)" data-model-field="f" data-form="form" data-model-name="modelName" data-model-data="modelData"></div>',
                '<div data-ng-if="isColumnField(f)" data-column-editor="" data-column-fields="f" data-model-name="modelName" data-model-data="modelData"></div>',
              '</div>',
              '<div data-ng-if="wantButtons" class="row">',
                '<div class="col-sm-12 text-center" data-buttons="" data-model-name="modelName" data-model-data="modelData" data-fields="advancedFields"></div>',
              '</div>',
            '</form>',
        ].join(''),
        controller: function($scope, $element) {
            var viewInfo = appState.viewInfo($scope.viewName);
            var i;
            $scope.form = angular.element($($element).find('form').eq(0));
            $scope.modelName = viewInfo.model || $scope.viewName;
            $scope.description = viewInfo.description;
            $scope.advancedFields = viewInfo[$scope.fieldDef || 'advanced'];
            if (! $scope.advancedFields) {
                throw $scope.modelName + ' view is missing ' + ($scope.fieldDef || 'advanced') + ' fields';
            }
            $scope.isColumnField = function(f) {
                return typeof(f) == 'string' ? false : true;
            };

            $scope.setActivePage = function(page) {
                if ($scope.activePage) {
                    $scope.activePage.isActive = false;
                }
                $scope.activePage = page;
                page.isActive = true;
                //TODO(pjm): deprecated parentController processing replaced by sr-tabSelected event
                if (appState.isLoaded() && $scope.parentController && $scope.parentController.handleModalShown) {
                    // invoke parentController after UI has been constructed
                    panelState.waitForUI(function() {
                        $scope.parentController.handleModalShown(
                            $scope.modelName, $scope.modelData ? $scope.modelData.modelKey : null);
                    });
                }
                if (appState.isLoaded()) {
                    panelState.waitForUI(function() {
                        $scope.$emit('sr-tabSelected', $scope.modelName, $scope.modelData ? $scope.modelData.modelKey : null);
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
                $(element).closest('.sr-beamline-editor').on('sr.resetActivePage', resetActivePage);
            }
            scope.$on('$destroy', function() {
                $(element).closest('.modal').off();
                $(element).closest('.sr-beamline-editor').off();
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
              '<button type="button" class="close" data-ng-click="clearAlert()" aria-label="Close">',
                '<span aria-hidden="true">&times;</span>',
              '</button>',
              '<strong>{{ alertText() }}</strong>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            //TODO(robnagler) bind to value in appState or vice versa
            $scope.alertText = function() {
                return errorService.alertText();
            };

            $scope.clearAlert = function() {
                errorService.alertText('');
            };

            $scope.$on('$routeChangeSuccess', $scope.clearAlert);
        },
    };
});

SIREPO.app.directive('srNotify', function(notificationService) {

    return {
        restrict: 'A',
        scope: {
            notificationName: '<',
            notificationClass: '<',
        },
        template: [
            '<div data-ng-show="notificationService.shouldPresent(notificationName)" class="alert alert-dismissible sr-notify" role="alert" data-ng-class="notificationClass">',
                '<button type="button" class="close" aria-label="Close" data-ng-click="notificationService.dismiss(notificationName)">',
                    '<span aria-hidden="true">&times;</span>',
                '</button>',
                '<span data-ng-bind-html="notificationService.getContent(notificationName)"></span>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.notificationService = notificationService;
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
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
            panelTitle: '@',
        },
        template: [
            '<div class="panel panel-info" id="{{ \'sr-\' + viewName + \'-basicEditor\' }}">',
              '<div class="panel-heading clearfix" data-panel-heading="{{ panelTitle }}" data-model-key="modelKey" data-view-name="{{ viewName }}"></div>',
                '<div class="panel-body" data-ng-hide="panelState.isHidden(modelKey)">',
                  //TODO(pjm): not really an advanced editor pane anymore, should get renamed
                  '<div data-advanced-editor-pane="" data-view-name="viewName" data-want-buttons="{{ wantButtons }}" data-field-def="basic" data-model-data="modelData" data-parent-controller="parentController"></div>',
                  '<div data-ng-transclude=""></div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var viewInfo = appState.viewInfo($scope.viewName);
            if (! viewInfo) {
                throw 'unknown viewName: ' + $scope.viewName;
            }
            $scope.modelName = viewInfo.model || $scope.viewName;
            $scope.modelKey = $scope.modelData
                ? $scope.modelData.modelKey
                : $scope.modelName;
            $scope.panelState = panelState;
            $scope.panelTitle = $scope.panelTitle || viewInfo.title;
            if (! angular.isDefined($scope.wantButtons)) {
                $scope.wantButtons = '1';
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
              '<button data-ng-click="saveChanges()" class="btn btn-primary" data-ng-disabled="! form.$valid">Save Changes</button> ',
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
            isRequired: '@',
        },
        template: [
            '<div class="modal fade" data-backdrop="{{ isRequired ? \'static\' : true }}" id="{{ id }}" tabindex="-1" role="dialog">',
              '<div class="modal-dialog">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-warning">',
                    '<button data-ng-if="! isRequired" type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
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
                          '<button data-ng-if="okText" data-ng-disabled="! isValid()" data-ng-click="clicked()" class="btn btn-default">{{ okText }}</button>',
                          ' <button data-ng-if="! isRequired" data-dismiss="modal" class="btn btn-default">{{ cancelText || \'Cancel\' }}</button>',
                        '</div>',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {
            $scope.formCtl = null;
            $scope.clicked = function() {
                if ($scope.okClicked() !== false) {
                    $('#' + $scope.id).modal('hide');
                }
            };
            $scope.isValid = function() {
                if(! $scope.formCtl) {
                    var f = $($element).find('form').eq(0);
                    $scope.formCtl = angular.element(f).controller('form');
                }
                if(! $scope.formCtl) {
                    return true;
                }
                return $scope.formCtl.$valid;
            };

            $scope.$on('$destroy', function() {
                // release modal data to prevent memory leak
                $($element).off();
            });

            $($element).on('shown.bs.modal', function() {
                $($element).find('.form-control').first().select();
            });
        },
    };
});

SIREPO.app.directive('copyConfirmation', function(appState, fileManager) {
    return {
        restrict: 'A',
        scope: {
            simId: '<',
            copyCfg: '=',
            disabled: '<',
        },
        template: [
            '<div data-confirmation-modal="" data-id="sr-copy-confirmation" data-title="Copy Simulation" data-ok-text="Create Copy" data-ok-clicked="copy()">',
              '<form class="form-horizontal" autocomplete="off">',
                '<div class="form-group">',
                '<label class="col-sm-3 control-label">New Name</label>',
                '<div class="col-sm-9">',
                  '<input data-ng-disabled="disabled" data-safe-path="" class="form-control" data-ng-model="copyCfg.copyName" required/>',
                  '<div class="sr-input-warning" data-ng-show="showWarning">{{ warningText }}</div>',
                '</div>',
                '</div>',
                '<div class="form-group" data-ng-if="showFolders()">',
                  '<label class="col-sm-3 control-label">Folder</label>',
                  '<div class="col-sm-9">',
                    '<div data-user-folder-list="" data-model="copyCfg" data-field="\'copyFolder\'"></div>',
                  '</div>',
              '</div>',
              '</form>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.showFolders = function () {
                return fileManager.getUserFolderPaths().length > 1;
            };
            $scope.copy = function() {
                appState.copySimulation(
                    $scope.simId,
                    $scope.copyCfg.completion,
                    $scope.copyCfg.copyName,
                    $scope.copyCfg.copyFolder
                );
            };
        },
    };
});

SIREPO.app.directive('labelWithTooltip', function(mathRendering) {
    return {
        restrict: 'A',
        scope: {
            'label': '@',
            'tooltip': '@',
        },
        template: [
            '<label><span data-text-with-math="label"></span>&nbsp;<span data-ng-show="tooltip" class="glyphicon glyphicon-info-sign sr-info-pointer"></span></label>',
        ],
        link: function link(scope, element) {
            if (scope.tooltip) {
                $(element).find('.sr-info-pointer').tooltip({
                    title: function() {
                        return mathRendering.mathAsHTML(scope.tooltip);
                    },
                    html: true,
                    placement: 'bottom',
                });
                scope.$on('$destroy', function() {
                    $(element).find('.sr-info-pointer').tooltip('destroy');
                });
            }
        },
    };
});

SIREPO.app.directive('fieldEditor', function(appState, keypressService, panelState, utilities) {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            field: '=fieldEditor',
            model: '=',
            customLabel: '=',
            labelSize: '@',
            fieldSize: '@',
            form: '=',
        },
        template: [
            '<div data-ng-class="utilities.modelFieldID(modelName, field)">',
            '<div data-ng-show="showLabel" data-label-with-tooltip="" class="control-label" data-ng-class="labelClass" data-label="{{ customLabel || info[0] }}" data-tooltip="{{ info[3] }}"></div>',
            '<div data-ng-switch="info[1]">',
              '<div data-ng-switch-when="Integer" data-ng-class="fieldClass">',
                '<input data-string-to-number="integer" data-ng-model="model[field]" data-min="info[4]" data-max="info[5]" class="form-control" style="text-align: right" data-lpignore="true" required />',
              '</div>',
              '<div data-ng-switch-when="Float" data-ng-class="fieldClass">',
                '<input data-string-to-number="" data-ng-model="model[field]" data-min="info[4]" data-max="info[5]" class="form-control" style="text-align: right" data-lpignore="true" required />',
              '</div>',
              //TODO(pjm): need a way to specify whether a field is option/required
              '<div data-ng-switch-when="OptionalString" data-ng-class="fieldClass">',
                '<input data-ng-model="model[field]" class="form-control" data-lpignore="true" />',
              '</div>',
              '<div data-ng-switch-when="OptionalStringUpper" data-ng-class="fieldClass">',
                '<input data-ng-model="model[field]" class="form-control" ng-change="model[field] = (model[field] | uppercase)" data-lpignore="true" />',
              '</div>',
              '<div data-ng-switch-when="String" data-ng-class="fieldClass">',
                '<input data-ng-model="model[field]" class="form-control" data-lpignore="true" required />',
              '</div>',
              '<div data-ng-switch-when="ValidatedString" data-ng-class="fieldClass">',
                '<input data-validated-string="" data-field-validator-name=" utilities.modelFieldID(modelName, field)" data-ng-model="model[field]" class="form-control" data-lpignore="true" required />',
                '<div class="sr-input-warning" data-ng-show="! form.$valid">{{ getWarningText() }}</div>',
              '</div>',
              '<div data-ng-switch-when="SafePath" data-ng-class="fieldClass">',
                '<input data-safe-path="" data-ng-model="model[field]" class="form-control" data-lpignore="true" required />',
                '<div class="sr-input-warning" data-ng-show="showWarning">{{warningText}}</div>',
              '</div>',
              '<div data-ng-switch-when="SimulationName" data-ng-class="fieldClass">',
                '<input data-safe-path="" data-ng-model="model[field]" class="form-control" required data-ng-readonly="model[\'isExample\']" data-lpignore="true" />',
                '<div class="sr-input-warning" data-ng-show="showWarning">{{warningText}}</div>',
              '</div>',
              '<div data-ng-switch-when="InputFile" class="col-sm-7">',
                '<div data-file-field="field" data-form="form" data-model="model" data-model-name="modelName"  data-selection-required="info[2]" data-empty-selection-text="No File Selected"></div>',
              '</div>',
               '<div data-ng-switch-when="Boolean" class="col-sm-7">',
                 // angular has problems initializing checkboxes - ngOpen has no effect on them, but we can use it to change the state as the models load
                 '<input class="sr-bs-toggle" data-ng-open="fieldDelegate.refreshChecked()" data-ng-model="model[field]" data-bootstrap-toggle="" data-model="model" data-field="field" data-field-delegate="fieldDelegate" data-info="info" type="checkbox">',
               '</div>',
              '<div data-ng-switch-when="ColorMap" class="col-sm-7">',
                '<div data-color-map-menu="" class="dropdown"></div>',
              '</div>',
              '<div data-ng-switch-when="Text" data-ng-class="fieldClass">',
                '<div data-collapsable-notes="" data-model="model" data-field="field" ></div>',
              '</div>',
              '<div data-ng-switch-when="UserFolder" data-ng-class="fieldClass">',
                '<div data-user-folder-list="" data-model="model" data-field="field"></div>',
              '</div>',
              '<div data-ng-switch-when="OptFloat" data-ng-class="fieldClass">',
                '<div data-optimize-float="" data-model="model" data-model-name="modelName" data-field="field" data-min="info[4]" data-max="info[5]" ></div>',
              '</div>',
              '<div data-ng-switch-when="Range" data-ng-class="fieldClass">',
                '<div data-range-slider="" data-model="model" data-model-name="modelName" data-field="field" data-units="model.units"></div>',
              '</div>',
              SIREPO.appFieldEditors || '',
              // assume it is an enum
              '<div data-ng-switch-default data-ng-class="fieldClass">',
                '<div data-ng-if="wantEnumButtons" class="btn-group">',
                  // must be a <button>, not an <a> so panelState.enableField() can disable it
                  '<button class="btn sr-enum-button" data-ng-repeat="item in enum[info[1]]" data-ng-click="model[field] = item[0]" data-ng-class="{\'active btn-primary\': isSelectedValue(item[0]), \'btn-default\': ! isSelectedValue(item[0])}">{{ item[1] }}</button>',
                '</div>',
                '<select data-ng-if="! wantEnumButtons" number-to-string class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in enum[info[1]]"></select>',
              '</div>',
            '</div>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {

            $scope.utilities = utilities;
            function fieldClass(fieldType, fieldSize, wantEnumButtons) {
                return 'col-sm-' + (fieldSize || (
                    (fieldType == 'Integer' || fieldType.indexOf('Float') >= 0)
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
            $scope.fieldProps = appState.fieldProperties($scope.modelName, $scope.field);

            // wait until the switch gets fully evaluated, then set event handlers for input fields
            // to disable keypress listener set by plots
            panelState.waitForUI(function () {
                var inputElement =  $($element).find('input');
                if(inputElement.length > 0) {
                    inputElement
                        .on('focus', function () {
                        keypressService.enableListener(false);
                    })
                        .on('blur', function () {
                        keypressService.enableListener(true);
                    });
                }
            });

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

            $scope.fieldValidatorName = utilities.modelFieldID($scope.modelName, $scope.field);

            $scope.clearViewValue = function(model) {
                model.$setViewValue('');
                model.$render();
            };

            $scope.$on('$destroy', function (event) {
                $($element).find('input').off('focus').off('blur');
            });
        },
    };
});

SIREPO.app.directive('logoutMenu', function(authState, authService, requestSender) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<li data-ng-if="::authState.isLoggedIn" class="sr-logged-in-menu dropdown">',
              '<a href class="dropdown-toggle" data-toggle="dropdown">',
                '<img data-ng-if="::authState.avatarUrl" data-ng-src="{{:: authState.avatarUrl }}">',
                '<span data-ng-if="::! authState.avatarUrl" class="glyphicon glyphicon-user"></span>',
                ' <span class="caret"></span>',
              '</a>',
              '<ul class="dropdown-menu">',
                '<li class="dropdown-header"><strong>{{ ::authState.displayName }}</strong></li>',
                '<li class="dropdown-header" data-ng-if="::authState.userName">{{ ::authState.userName }} via {{ ::authState.method }}</li>',
                '<li data-ng-if="::!guestToUserUrl"><a data-ng-href="{{ ::authService.logoutUrl }}">Sign out</a></li>',
                '<li data-ng-if="::guestToUserUrl"><a data-ng-href="{{ ::guestToUserUrl }}">Save your work!</a></li>',
              '</ul>',
            '</li>',
        ].join(''),
        controller: function($scope) {
            $scope.authState = authState;
            $scope.authService = authService;

            if (authState.method == 'guest') {
                authState.visibleMethods.some(function(method) {
                    if (method != 'guest') {
                        $scope.guestToUserUrl = requestSender.formatUrlLocal(
                            'loginWith',
                            {':method': method});
                        return true;
                    }
                });
            }
        },
    };
});

SIREPO.app.directive('fileField', function(errorService, panelState, requestSender, $http) {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            fileField: '=',
            modelName: '=',
            model: '=',
            emptySelectionText: '@',
            selectionRequired: '=',
            fileType: '@',
            form: '=',
        },
        template: [
          '<div class="btn-group" role="group">',
            '<button type="button" class="btn btn-default dropdown-toggle" data-ng-class="{\'btn-invalid\': selectionRequired && ! hasValidFileSelected()}" data-toggle="dropdown">{{ model[fileField] || emptySelectionText }} <span class="caret"></span></button>',
            '<ul class="dropdown-menu">',
              '<li data-ng-repeat="item in itemList()" class="sr-model-list-item"><a href data-ng-click="selectItem(item)">{{ item }}<span data-ng-show="! isSelectedItem(item)" data-ng-click="confirmDeleteItem(item, $event)" class="glyphicon glyphicon-remove"></span></a></li>',
              '<li class="divider"></li>',
              '<li data-ng-hide="selectionRequired"><a href data-ng-click="selectItem(null)">{{ emptySelectionText }}</a></li>',
              '<li data-ng-hide="selectionRequired" class="divider"></li>',
              '<li><a href data-ng-click="showFileUpload()"><span class="glyphicon glyphicon-plus"></span> New</a></li>',
            '</ul>',
          '</div> ',
          '<div data-ng-if="hasValidFileSelected()" class="btn-group" role="group">',
            '<div class="pull-left" data-ng-transclude=""></div>',
            '<div class="pull-left"><a data-ng-href="{{ downloadFileUrl() }}" type="button" title="Download" class="btn btn-default"><span class="glyphicon glyphicon-cloud-download"></a></div>',
          '</div>',
          '<div class="sr-input-warning" data-ng-show="selectionRequired && ! hasValidFileSelected()">Select a file</div>',
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
                        '<simulation_id>': 'unused',
                        '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        '<filename>': SIREPO.APP_NAME == 'srw'
                            ? $scope.model[$scope.fileField]
                            : $scope.fileType + '.' + $scope.model[$scope.fileField],
                    });
                }
                return '';
            };

            $scope.hasValidFileSelected = function() {
                if ($scope.selectionRequired && $scope.form) {
                    $scope.form.$valid = false;
                }
                if ($scope.fileType && $scope.model) {
                    var f = $scope.model[$scope.fileField];
                    var list = requestSender.getAuxiliaryData($scope.fileType);
                    if (f && list && list.indexOf(f) >= 0) {
                        if($scope.form) {
                            $scope.form.$valid = true;
                        }
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
                requestSender.loadAuxiliaryData(
                    $scope.fileType,
                    requestSender.formatUrl('listFiles', {
                        '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        '<file_type>': $scope.fileType,
                        '<simulation_id>': 'unused',
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
            '<div class="sr-column-editor">',
              '<div class="row">',
                '<div class="col-sm-{{ ::head.size || 3 }}" data-ng-repeat="head in ::headings">',
                  '<div class="lead text-center">{{ ::head.text }}</div>',
                '</div>',
              '</div>',
              '<div class="form-group form-group-sm" data-ng-repeat="row in ::rows">',
                '<div data-ng-repeat="col in ::row">',
                  '<div data-ng-if="::! col.field" class="col-sm-{{ ::col.size || 3 }} control-label">',
                    '<div data-label-with-tooltip="" data-label="{{ ::col.label }}" data-tooltip="{{ ::col.tooltip }}"></div>',
                  '</div>',
                  '<div data-ng-if="::col.field" class="col-sm-{{ ::col.size || 3 }}"><div class="row">',
                    '<div data-model-field="::col.field" data-label-size="0" data-field-size="12" data-model-name="modelName" data-model-data="modelData"></div>',
                  '</div></div>',
                '</div>',
              '</div>',
              '<div>&nbsp;</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {

            function initLayout() {
                var headings = [];
                var rows = [];
                for (var i = 0; i < $scope.columnFields.length; i++) {
                    var heading = $scope.columnFields[i][0];
                    headings.push({
                        text: heading,
                    });
                    for (var j = 0; j < $scope.columnFields[i][1].length; j++) {
                        if (! rows[j]) {
                            rows[j] = [{
                                label: '',
                            }];
                        }
                        var col = $scope.columnFields[i][1][j];
                        rows[j][i * 2] = getLabel(heading, col);
                        rows[j][i * 2 + 1] = {
                            field: col,
                        };
                    }
                }
                if (isOneLabelLayout(rows)) {
                    if (rows[0].length == 4) {
                        // one label, two fields
                        headings.unshift({
                            text: '',
                            size: 5,
                        });
                        rows.forEach(function(row) {
                            row[0].size = 5;
                            row.splice(2, 1);
                        });
                    }
                    else {
                        // one label, three fields
                        headings.unshift({
                            text: '',
                        });
                        rows.forEach(function(row) {
                            row.splice(4, 1);
                            row.splice(2, 1);
                        });
                    }
                }
                else {
                    // two labels, two fields
                    headings.forEach(function(h) {
                        h.size = 6;
                    });
                }
                $scope.headings = headings;
                $scope.rows = rows;
            }

            function getLabel(heading, f) {
                var m = $scope.modelName;
                var modelField = appState.parseModelField(f);
                if (modelField) {
                    m = modelField[0];
                    f = modelField[1];
                }
                var info = appState.modelInfo(m)[f];
                return {
                    label: info[0].replace(heading.replace(/ .*/, ''), ''),
                    tooltip: info[3],
                };
            }

            function isOneLabelLayout(rows) {
                for (var i = 0; i < rows.length; i++) {
                    var row = rows[i];
                    if (row[1] && row[2] && (row[0].label != row[2].label)) {
                        return false;
                    }
                }
                return true;
            }

            initLayout();
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
                          '<input type="file" data-file-model="inputFile" data-ng-attr-accept="{{ acceptTypes() }}" />',
                          '<div class="text-warning" style="white-space: pre-line"><strong>{{ fileUploadError }}</strong></div>',
                        '</div>',
                        '<div data-ng-if="isUploading" class="col-sm-6 pull-right">Please Wait...</div>',
                        '<div class="clearfix"></div>',
                        '<div class="col-sm-6 pull-right">',
                          '<button data-ng-show="isConfirming" data-ng-click="uploadFile(inputFile)" class="btn btn-warning" data-ng-disabled="isUploading">Replace File</button>',
                          '<button data-ng-hide="isConfirming" data-ng-click="uploadFile(inputFile)" class="btn btn-primary" data-ng-disabled="isUploading">Save Changes</button>',
                          ' <button data-dismiss="modal" class="btn btn-default" data-ng-disabled="isUploading">Cancel</button>',
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

            $scope.acceptTypes = function() {
                if (appState.isLoaded() && SIREPO.FILE_UPLOAD_TYPE) {
                    return SIREPO.FILE_UPLOAD_TYPE[$scope.fileType] || '';
                }
                return '';
            };

            $scope.uploadFile = function(inputFile) {
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

SIREPO.app.directive('modalEditor', function(appState, panelState) {
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
                    panelState.waitForUI(function() {
                        scope.parentController.handleModalShown(scope.modelName, scope.modelKey);
                    });
                }
            });
            $(element).on('hidden.bs.modal', function() {
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
            labelSize: '@',
            fieldSize: '@',
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
            form: '=',
        },
        template: [
            '<div data-field-editor="fieldName()" data-form="form" data-model-name="modelNameForField()" data-model="modelForField()" data-custom-label="customLabel" data-label-size="{{ labelSize }}" data-field-size="{{ fieldSize }}"></div>',
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

            $scope.fieldName = function() {
                return field;
            };
        },
    };
});

SIREPO.app.directive('msieFontDisabledDetector', function(errorService, $interval) {
    return {
        restrict: 'A',
        link: function() {
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
        link: function(scope, element, attrs, ngModel) {
            scope.showWarning = false;
            scope.warningText = '';
            ngModel.$parsers.push(function (v) {
                scope.showWarning = unsafe_path_regexp.test(v);
                if (scope.showWarning) {
                    scope.warningText = (scope.info ? scope.info[0] : 'Value') + unsafe_path_warn;
                    ngModel.$setValidity('size', false);
                }
                else {
                    ngModel.$setValidity('size', true);
                }
                return v;
            });

            ngModel.$formatters.push(function (v) {
                scope.showWarning = false;
                return v;
            });
        },
    };
});

SIREPO.app.directive('simplePanel', function(appState, panelState) {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            modelName: '@simplePanel',
        },
        template: [
            '<div class="panel panel-info">',
              '<div class="panel-heading clearfix" data-panel-heading="{{ heading }}" data-model-key="modelName"></div>',
                '<div class="panel-body" data-ng-hide="isHidden()">',
                  '<div data-ng-transclude=""></div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var viewInfo = appState.viewInfo($scope.modelName);
            $scope.heading = viewInfo.title;
            $scope.isHidden = function() {
                return panelState.isHidden($scope.modelName);
            };
        },
    };
});

SIREPO.app.directive('textWithMath', function(mathRendering, $sce) {
    return {
        restrict: 'A',
        scope: {
            'textWithMath': '<',
        },
        template: [
            '<span data-ng-bind-html="::getHTML()"></span>',
        ],
        controller: function($scope) {
            $scope.getHTML = function() {
                return $sce.trustAsHtml(mathRendering.mathAsHTML($scope.textWithMath));
            };
        },
    };
});

SIREPO.app.directive('validatedString', function(panelState, validationService) {

    return {
        restrict: 'A',
        require: 'ngModel',
        link: function(scope, element, attrs, ngModel) {

            var modelValidatorName = 'vstring';
            scope.getWarningText = function() {
                return validationService.getMessageForModel(scope.fieldValidatorName, modelValidatorName, ngModel);
            };

            function reloadValidator() {
                validationService.reloadValidatorForModel(scope.fieldValidatorName, modelValidatorName, ngModel);
            }

            // add and remove validators as needed
            var modal =  $('#' + panelState.modalId(scope.modelName));
            $(modal).on('shown.bs.modal', function() {
                reloadValidator();
            });
            $(modal).on('hidden.bs.modal', function() {
                delete ngModel.$validators[modelValidatorName];
                validationService.removeFieldValidator(scope.fieldValidatorName);
            });
        },
    };
});

SIREPO.app.directive('colorMapMenu', function(appState, plotting) {

    return {
        restrict: 'A',
        template: [
            '<button class="btn btn-primary dropdown-toggle" type="button" data-toggle="dropdown"><span class="sr-color-map-indicator" data-ng-style="itemStyle[model[field]]"></span> {{ colorMapDescription(model[field]) }} <span class="caret"></span></button>',
            '<ul class="dropdown-menu sr-button-menu">',
                '<li data-ng-repeat="item in items" class="sr-button-menu">',
                    '<button class="btn btn-block"  data-ng-class="{\'sr-button-menu-selected\': isSelectedMap(item[0]), \'sr-button-menu-unselected\': ! isSelectedMap(item[0])}" data-ng-click="setColorMap(item[0])">',
                        '<span class="sr-color-map-indicator" data-ng-style="itemStyle[item[0]]"></span> {{item[1]}} <span data-ng-if="isDefaultMap(item[0])" class="glyphicon glyphicon-star-empty"></span><span data-ng-if="isSelectedMap(item[0])" class="glyphicon glyphicon-ok"></span>',
                    '</button>',
                '</li>',
            '</ul>',
        ].join(''),
        controller: function($scope) {
            var defaultMapName, enumName;

            function init() {
                var info = appState.modelInfo($scope.modelName)[$scope.field];
                if (! info) {
                    throw 'invalid model field: ' + $scope.modelName + '.' + $scope.field;
                }
                enumName = info[SIREPO.INFO_INDEX_TYPE];
                defaultMapName = info[SIREPO.INFO_INDEX_DEFAULT_VALUE];
                $scope.items = SIREPO.APP_SCHEMA.enum[enumName];
                $scope.itemStyle = {};
                $scope.items.forEach(function(item) {
                    var mapName = item[0];
                    var map = plotting.colorMapOrDefault(mapName, defaultMapName);
                    $scope.itemStyle[mapName] = {
                        'background': 'linear-gradient(to right, ' + map.join(',') + ')',
                    };
                });
            }

            $scope.colorMapDescription = function(mapName) {
                return appState.enumDescription(enumName, mapName || defaultMapName);
            };

            $scope.isDefaultMap = function(mapName) {
                return mapName == defaultMapName;
            };

            $scope.isSelectedMap = function(mapName) {
                if ($scope.model && $scope.model[$scope.field]) {
                    return $scope.model[$scope.field] == mapName;
                }
                return $scope.isDefaultMap(mapName);
            };

            $scope.setColorMap = function(mapName) {
                $scope.model[$scope.field] = mapName;
            };

            init();
        },
    };
});

SIREPO.app.directive('collapsableNotes', function() {

    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: [
            '<div>',
            '<a href data-ng-click="toggleNotes()" style="text-decoration: none;">',
            '<span class="glyphicon" data-ng-class="{\'glyphicon-chevron-down\': ! showNotes, \'glyphicon-chevron-up\': showNotes}" style="font-size:16px;"></span>',
            ' <span data-ng-show="! openNotes() && hasNotes()">...</span>',
            ' <span data-ng-show="! openNotes() && ! hasNotes()" style="font-style: italic; font-size: small">click to enter notes</span>',
            '</a>',

            '<textarea data-ng-show="openNotes()" data-ng-model="model[field]" class="form-control" style="resize: vertical; min-height: 2em;"></textarea>',
            '</div>',
        ].join(''),
        controller: function($scope) {

            var hasOpened = false;
            $scope.showNotes = false;
            $scope.hasNotes = function () {
                return ! ! $scope.model &&
                    ! ! $scope.model[$scope.field] &&
                    ! ! $scope.model[$scope.field].length;
            };
            $scope.openNotes = function () {
                if(! hasOpened) {
                    $scope.showNotes = $scope.hasNotes();
                }
                return $scope.showNotes;
            };
            $scope.toggleNotes = function () {
                hasOpened = true;
                $scope.showNotes = ! $scope.showNotes;
            };

        },
    };
});

SIREPO.app.directive('userFolderList', function(appState, fileManager) {

    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: [
            '<select class="form-control" data-ng-model="model[field]" data-ng-if="! model.isExample" data-ng-options="item for item in fileManager.getUserFolderPaths()"></select>',
            '<div class="form-control" data-ng-if="model.isExample" readonly>{{ model.folder }}</div>',
        ].join(''),
        controller: function($scope) {
            $scope.fileManager = fileManager;
        },
    };
});


//TODO(pjm): this directive is only needed for old data which might have enum values as a number rather than string
SIREPO.app.directive('numberToString', function() {
    return {
        restrict: 'A',
        require: 'ngModel',
        link: function(scope, element, attrs, ngModel) {
            ngModel.$parsers.push(function(value) {
                if (ngModel.$isEmpty(value)) {
                    return '';
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

SIREPO.app.directive('simpleHeading', function(panelState, utilities) {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            simpleHeading: '@',
            modelKey: '=',
        },
        template: [
            '<span class="sr-panel-heading">{{ simpleHeading }}</span>',
            '<div class="sr-panel-options pull-right">',
              '<a href data-ng-class="{\'sr-disabled-link\': utilities.isFullscreen()}" data-ng-click="toggleHidden()" data-ng-hide="panelState.isHidden(modelKey) || utilities.isFullscreen()" title="Hide"><span class="sr-panel-heading glyphicon glyphicon-chevron-up"></span></a> ',
              '<a href data-ng-click="panelState.toggleHidden(modelKey)" data-ng-show="panelState.isHidden(modelKey)" title="Show"><span class="sr-panel-heading glyphicon glyphicon-chevron-down"></span></a>',
            '</div>',
            '<div class="sr-panel-options pull-right" data-ng-transclude="" ></div>',
        ].join(''),
        controller: function($scope) {
            $scope.panelState = panelState;
            $scope.utilities = utilities;
            $scope.toggleHidden = function() {
                if(! utilities.isFullscreen()) {
                    panelState.toggleHidden($scope.modelKey);
                }
            };
        },
    };
});

SIREPO.app.directive('panelHeading', function(appState, frameCache, panelState, plotToPNG, requestSender, utilities) {
    return {
        restrict: 'A',
        scope: {
            panelHeading: '@',
            modelKey: '=',
            isReport: '@',
            reportId: '<',
            viewName: '@',
        },
        template: [
            '<div data-simple-heading="{{ panelHeading }}" data-model-key="modelKey">',
              '<a href data-ng-show="hasEditor && ! utilities.isFullscreen()" data-ng-click="showEditor()" title="Edit"><span class="sr-panel-heading glyphicon glyphicon-pencil"></span></a> ',
              '<div data-ng-if="isReport" data-ng-show="hasData() && ! utilities.isFullscreen()" class="dropdown" style="display: inline-block">',
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
              SIREPO.appPanelHeadingButtons || '',
              '<a href data-ng-show="isReport && ! panelState.isHidden(modelKey)" data-ng-attr-title="{{ fullscreenIconTitle() }}" data-ng-click="toggleFullScreen()"><span class="sr-panel-heading glyphicon" data-ng-class="{\'glyphicon-resize-full\': ! utilities.isFullscreen(), \'glyphicon-resize-small\': utilities.isFullscreen()}"></span></a> ',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {
            $scope.panelState = panelState;
            $scope.utilities = utilities;

            // modelKey may not exist in viewInfo, assume it has an editor in that case
            var view = appState.viewInfo($scope.viewName || $scope.modelKey);
            $scope.hasEditor = view && view.advanced.length === 0 ? false : true;

            // used for python export which lives in SIREPO.appDownloadLinks
            $scope.reportTitle = function () {
                return $scope.panelHeading;
            };

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
                var fileName = panelState.fileNameFromText($scope.panelHeading, 'png');
                if(plotToPNG.hasCanvas($scope.reportId)) {
                    plotToPNG.downloadCanvas($scope.reportId, 0, height, fileName);
                    return;
                }
                var plot3dCanvas = $scope.panel.find('canvas')[0];
                var svg = $scope.panel.find('svg')[0];
                if (! svg || $(svg).is(':hidden')) {
                    return;
                }
                plotToPNG.downloadPNG(svg, height, plot3dCanvas, fileName);
            };

            $scope.hasData = function() {
                if (! $scope.panel.find('svg')[0]) {
                    return;
                }
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

            $scope.fullscreenIconTitle = function() {
                if(! utilities.isFullscreen()) {
                    return 'Full Screen';
                }
                return 'Exit Full Screen';
            };

            function getFullScreenElement() {
                return document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement;
            }
            $scope.toggleFullScreen = function() {
                if(panelState.isHidden($scope.modelKey)) {
                    return;
                }

                var svg = $scope.panel.find('svg')[0];
                var el = $($element).closest('div[data-report-panel] > .panel')[0];

                if(! utilities.isFullscreen()) {
                    // Firefox does its own thing
                    if(utilities.requestFullscreenFn(el) == el.mozRequestFullScreen) {
                        el.parentElement.mozRequestFullScreen();
                    }
                    else {
                        utilities.requestFullscreenFn(el).call(el);
                    }
                }
                else {
                    utilities.exitFullscreenFn().call(document);
                }
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
            reportId: '<',
            reportContent: '@',
            modelKey: '@',
        },
        template: [
            '<div data-ng-class="{\'sr-panel-loading\': panelState.isLoading(modelKey), \'sr-panel-error\': panelState.getError(modelKey), \'sr-panel-running\': panelState.isRunning(modelKey), \'has-transclude\': hasTransclude()}" class="panel-body" data-ng-hide="panelState.isHidden(modelKey)">',
              '<div data-ng-show="panelState.isLoading(modelKey)" class="lead sr-panel-wait"><span class="glyphicon glyphicon-hourglass"></span> {{ panelState.getStatusText(modelKey) }}</div>',
              '<div data-ng-show="panelState.getError(modelKey)" class="lead sr-panel-wait"><span class="glyphicon glyphicon-exclamation-sign"></span> {{ panelState.getError(modelKey) }}</div>',
              '<div data-ng-switch="reportContent" class="{{ panelState.getError(modelKey) ? \'sr-hide-report\' : \'\' }}">',
                '<div data-ng-switch-when="2d" data-plot2d="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-id="reportId"></div>',
                '<div data-ng-switch-when="3d" data-plot3d="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-id="reportId"></div>',
                '<div data-ng-switch-when="heatmap" data-heatmap="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
                '<div data-ng-switch-when="particle" data-particle="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
                '<div data-ng-switch-when="particle3d" data-particle-3d="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-id="reportId"></div>',
                '<div data-ng-switch-when="parameter" data-parameter-plot="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-id="reportId"></div>',
                '<div data-ng-switch-when="lattice" data-lattice="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
                '<div data-ng-switch-when="parameterWithLattice" data-parameter-with-lattice="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-id="reportId"></div>',
                SIREPO.appReportTypes || '',
              '</div>',
              '<div data-ng-transclude=""></div>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {
            $scope.panelState = panelState;
            $scope.hasTransclude = function() {
                var el = $($element).find('div[data-ng-transclude] > div[data-ng-transclude]:not(:empty)');
                return el.children().first().length > 0;
            };
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
            '<div class="panel panel-info" data-ng-attr-id="{{ ::reportId }}">',
              '<div class="panel-heading clearfix" data-panel-heading="{{ reportTitle() }}" data-model-key="modelKey" data-is-report="1" data-report-id="reportId"></div>',
              '<div data-report-content="{{ reportPanel }}" data-model-key="{{ modelKey }}" data-report-id="reportId"><div data-ng-transclude=""></div></div>',
              '<button data-ng-if="notes()" class="close sr-help-icon notes" title="{{ notes() }}"><span class="glyphicon glyphicon-question-sign"></span></button>',
        ].join(''),
        controller: function($scope) {

            // random id for the keypress service to track
            $scope.reportId = Math.floor(Math.random() * Number.MAX_SAFE_INTEGER);

            $scope.modelKey = $scope.modelName;
            if ($scope.modelData) {
                $scope.modelKey = $scope.modelData.modelKey;
            }
            $scope.reportTitle = function() {
                return $scope.panelTitle ? $scope.panelTitle : appState.viewInfo($scope.modelName).title;
            };
            $scope.notes = function () {
                if(appState.models[$scope.modelKey]) {
                    return appState.models[$scope.modelKey].notes;
                }
                return null;
            };
        },
    };
});

SIREPO.app.directive('appHeaderBrand', function() {
    var appInfo = SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_SCHEMA.simulationType];
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeaderBrand',
            appUrl: '@',
        },
        template: [
            '<div class="navbar-header">',
              '<a class="navbar-brand" href="/en/landing.html"><img style="width: 40px; margin-top: -10px;" src="/static/img/sirepo.gif" alt="RadiaSoft"></a>',
              '<div class="navbar-brand">',
                '<a data-ng-href="{{ appUrl || nav.sectionURL(\'simulations\') }}">',
                  '<span class="hidden-md hidden-sm">',
                    appInfo.longName,
                  '</span>',
                  '<span class="hidden-xs hidden-lg hidden-xl"',
                    appInfo.longName == appInfo.shortName
                      ? ''
                      : ' title="'+ appInfo.longName + '"',
                  '>',
                    appInfo.shortName,
                  '</span>',
                '</a>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            if (! $scope.appUrl ) {
                //TODO(rjn) need to centeralize this
                if (SIREPO.APP_NAME == 'elegant') {
                    $scope.appUrl = '/en/particle-accelerators.html';
                }
                else if (SIREPO.APP_NAME == 'srw') {
                    $scope.appUrl = '/en/xray-beamlines.html';
                }
                else {
                    $scope.appUrl = '/old#/' + SIREPO.APP_NAME;
                }
            }
        },
    };
});

SIREPO.app.directive('appHeaderLeft', function(appState, authState, panelState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeaderLeft',
            simulationsLinkText: '@',
        },
        template: [
            '<ul class="nav navbar-nav" data-ng-if=":: authState.isLoggedIn">',
              '<li data-ng-class="{active: nav.isActive(\'simulations\')}"><a href data-ng-click="nav.openSection(\'simulations\')"><span class="glyphicon glyphicon-th-list"></span> {{ simulationsLinkText }}</a></li>',
            '</ul>',
            '<div data-ng-if="showTitle()" class="navbar-text">',
                '<a href data-ng-click="showSimulationModal()"><span data-ng-if="nav.sectionTitle()" class="glyphicon glyphicon-pencil"></span> <strong data-ng-bind="nav.sectionTitle()"></strong></a> ',
                '<a href data-ng-click="showSimulationLink()" class="glyphicon glyphicon-link"></a>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.authState = authState;
            if (! $scope.simulationsLinkText) {
                $scope.simulationsLinkText = 'Simulations';
            }
            $scope.showTitle = function() {
                return appState.isLoaded();
            };
            $scope.showSimulationLink = function() {
                panelState.showModalEditor(
                    'simulationLink',
                    [
                        '<div data-confirmation-modal="" data-id="sr-simulationLink-editor" data-title="Share link for {{ nav.sectionTitle() }}" data-ok-text="Copy" data-ok-clicked="copySimulationLink()" data-cancel-text="Done">',
                            '<input id="sr-simulation-link-input" type="text" readonly="true" value="{{ nav.getLocation() }}" class="form-control input-lg" onfocus="this.select();" autofocus="true"/>',
                        '</div>',
                    ].join(''),
                    $scope
                );
            };
            $scope.copySimulationLink = function() {
                var linkInput = document.getElementById('sr-simulation-link-input');
                linkInput.focus();
                linkInput.setSelectionRange(0, 9999);
                document.execCommand('copy');
                return false;
            };
            $scope.showSimulationModal = function() {
                panelState.showModalEditor('simulation');
            };
        },
    };
});

SIREPO.app.directive('appHeaderRight', function(appDataService, appState, fileManager, panelState, $window) {

    function helpLink(url, text, icon) {
        return url
            ? ('<li><a href="' + url + '" target="_blank"><span class="glyphicon glyphicon-'
               + icon + '"></span> '
               + SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_SCHEMA.simulationType].longName + ' '
               + text + '</a></li>')
            : '';
    }
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
                // spacer to fix wrapping problem in firefox
                '<div style="width: 16px"></div>',
                // the line below has to be a ngShow, not ngIf or the transcluded slot may get rendered empty in some cases
                '<ul class="nav navbar-nav sr-navbar-right" data-ng-show="isLoaded()">',
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
                '<ul class="nav navbar-nav sr-navbar-right">',
                  '<li class=dropdown><a href class="dropdown-toggle" data-toggle="dropdown"><span class="glyphicon glyphicon-question-sign"></span> <span class="caret"></span></a>',
                    '<ul class="dropdown-menu">',
                      '<li><a href="https://github.com/radiasoft/sirepo/issues" target="_blank"><span class="glyphicon glyphicon-exclamation-sign"></span> Report a Bug</a></li>',
                      helpLink(SIREPO.USER_MANUAL_URL, 'User Manual', 'list-alt'),
                      helpLink(SIREPO.USER_FORUM_URL, 'User Forum', 'globe'),
                    '</ul>',
                  '</li>',
                '</ul>',
                '<ul data-ng-if="::! authState.isLoggedIn" class="nav navbar-nav navbar-right" data-logout-menu=""></ul>',
            '</div>',
        ].join(''),
        link: function(scope) {
           scope.nav.isLoaded = scope.isLoaded;
           scope.nav.simulationName = scope.simulationName;
           scope.nav.hasDocumentationUrl = scope.hasDocumentationUrl;
           scope.nav.openDocumentation = scope.openDocumentation;
           scope.nav.modeIsDefault = scope.modeIsDefault;
           scope.nav.showSimulationModal = scope.showSimulationModal;
           scope.nav.showImportModal = scope.showImportModal;

           scope.fileManager = fileManager;
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
                appState.models.simFolder.parent = fileManager.defaultCreationFolderPath();
                panelState.showModalEditor('simFolder');
            };
            $scope.showSimulationModal = function() {
                appState.models.simulation.folder = fileManager.defaultCreationFolderPath();
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

            $scope.showImportModal = function() {
                $('#simulation-import').modal('show');
            };
        },
    };
});

SIREPO.app.directive('fileChooser', function(appState, fileManager, fileUpload, requestSender) {
    return {
        restrict: 'A',
        scope: {
            title: '=',
            description: '=',
            fileFormats: '@',
            url: '=',
            inputFile: '=',
            validator: '&',
        },
        template: [
            '<div class="form-group">',
              '<label>{{ description }}</label>',
              '<input id="file-select" type="file" data-file-model="inputFile" data-ng-attr-accept="{{ fileFormats }}">',
              '<br />',
              '<div class="text-warning" style="white-space: pre-line"><strong>{{ fileUploadError }}</strong></div>',
            '</div>',
            '<div data-ng-if="isUploading" class="col-sm-6 pull-right">Please Wait...</div>',
        ].join(''),
        controller: function($scope) {
            $scope.isUploading = false;
            $scope.title = $scope.title || 'Import ZIP File';
            $scope.description = $scope.description || 'Select File';
        },
    };
});

SIREPO.app.directive('importDialog', function(appState, fileManager, fileUpload, requestSender) {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            title: '@',
            description: '@',
            fileFormats: '@',
        },
        template: [
            '<div class="modal fade" id="simulation-import" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<div data-help-button="{{ title }}"></div>',
                    '<span class="lead modal-title text-info">{{ title }}</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                    '<form data-file-loader="" data-file-formats="fileFormats" data-description="description">',
                      '<form name="importForm">',
                        '<div class="form-group">',
                          '<label>{{ description }}</label>',
                          '<input id="file-import" type="file" data-file-model="inputFile" data-ng-attr-accept="{{ fileFormats }}">',
                          '<br />',
                          '<div class="text-warning"><strong>{{ fileUploadError }}</strong></div>',
                          '<div data-ng-transclude=""></div>',
                        '</div>',
                        '<div data-ng-if="isUploading" class="col-sm-6 pull-right">Please Wait...</div>',
                        '<div class="clearfix"></div>',
                        '<div class="col-sm-6 pull-right">',
                          '<button data-ng-click="importFile(inputFile)" class="btn btn-primary" data-ng-disabled="! inputFile || isUploading">Import File</button>',
                          ' <button data-ng-click="inputFile = null" data-dismiss="modal" class="btn btn-default" data-ng-disabled="isUploading">Cancel</button>',
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
            $scope.title = $scope.title || 'Import ZIP File';
            $scope.description = $scope.description || 'Select File';
            $scope.importFile = function(inputFile) {
                if (! inputFile) {
                    return;
                }
                $scope.isUploading = true;
                fileUpload.uploadFileToUrl(
                    inputFile,
                    {
                        folder: fileManager.getActiveFolderPath(),
                    },
                    requestSender.formatUrl(
                        'importFile',
                        {
                            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        }),
                    function(data) {
                        $scope.isUploading = false;
                        if (data.error) {
                            $scope.fileUploadError = data.error;
                            // used by sub components to display additional data entry fields
                            $scope.errorData = data;
                        }
                        else {
                            $('#simulation-import').modal('hide');
                            $scope.inputFile = null;
                            requestSender.localRedirectHome(data.models.simulation.simulationId);
                        }
                    });
            };
        },
        link: function(scope, element) {
            $(element).on('show.bs.modal', function() {
                $('#file-import').val(null);
                scope.fileUploadError = '';
                delete scope.errorData;
                scope.isUploading = false;
            });
            scope.$on('$destroy', function() {
                $(element).off();
            });
        },
    };
});

SIREPO.app.directive('settingsMenu', function(appDataService, appState, fileManager, panelState, requestSender, $compile, $location, $window, $timeout) {

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
                    '<li><a href data-ng-click="pythonSource()"><span class="glyphicon glyphicon-cloud-download sr-nav-icon"></span> Python Source</a></li>',
                    '<li data-ng-if="canCopy()"><a href data-ng-click="copyItem()"><span class="glyphicon glyphicon-copy"></span> Open as a New Copy</a></li>',
                    '<li data-ng-if="isExample()"><a href data-target="#reset-confirmation" data-toggle="modal"><span class="glyphicon glyphicon-repeat"></span> Discard Changes to Example</a></li>',
                    '<li data-ng-if="! isExample()"><a href data-target="#delete-confirmation" data-toggle="modal"><span class="glyphicon glyphicon-trash"></span> Delete</a></li>',
                    '<li data-ng-if="hasRelatedSimulations()" class="divider"></li>',
                    '<li data-ng-if="hasRelatedSimulations()" class="sr-dropdown-submenu">',
                      '<a href><span class="glyphicon glyphicon-menu-left"></span> Related Simulations</a>',
                      '<ul class="dropdown-menu">',
                        '<li data-ng-repeat="item in relatedSimulations"><a href data-ng-click="openRelatedSimulation(item)">{{ item.name }}</a></li>',
                      '</ul>',
                    '</li>',
                  '</ul>',
                '</li>',
              '</ul>',
        ].join(''),
        controller: function($scope) {

            var currentSimulationId = null;

            // We don't add this modal unless we need it
            var copyConfModalHTML = [
                '<div id="sr-jit-copy-confirmation" data-copy-confirmation="" ',
                'data-sim-id="simulationId()" ',
                'data-copy-cfg="copyCfg" ',
                'data-disabled="! doneLoadingSimList"',
                '>',
                '</div>',
            ].join('');
            $scope.doneLoadingSimList = false;

            $scope.simulationId = function () {
                if (appState.isLoaded()) {
                    return appState.models.simulation.simulationId;
                }
                return null;
            };

            $scope.copyFolder = fileManager.defaultCreationFolderPath();

            $scope.showDocumentationUrl = function() {
                panelState.showModalEditor('simDoc');
            };
            $scope.pythonSource = function() {
                panelState.pythonSource($scope.simulationId());
            };


            $scope.relatedSimulations = [];

            $scope.canCopy = function() {
                return appDataService.canCopy();
            };

            $scope.copyCfg = {
                copyName: '',
                copyFolder: '/',
                isExample: false,
                completion: function (data) {
                    $scope.doneLoadingSimList = false;
                    requestSender.localRedirectHome(data.models.simulation.simulationId);
                },
            };

            $scope.copyItem = function() {
                // always recompile, or the scope will not match
                if(! $('#sr-jit-copy-confirmation')[0]) {
                    compileJITDialogs();
                }
                if(! $scope.doneLoadingSimList) {
                    loadList();
                }
                else {
                    loadCopyConfig();
                }
                // make sure the DOM is ready
                $timeout(function () {
                    $('#sr-copy-confirmation').modal('show');
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
                //TODO(pjm): make this more generalized - could be an app-specific tab
                if ($scope.nav.isActive('beamline')) {
                    requestSender.localRedirect('beamline', {
                        ':simulationId': item.simulationId,
                    });
                    return;
                }
                requestSender.localRedirectHome(item.simulationId);
            };

            $scope.exportArchive = function(extension) {
                $window.open(requestSender.formatUrl('exportArchive', {
                    '<simulation_id>': $scope.simulationId(),
                    '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                    '<filename>':  $scope.nav.simulationName() + '.' + extension,
                }), '_blank');
            };

            $scope.$on('simulationUnloaded', function() {
                $scope.doneLoadingSimList = false;
            });

            function compileJITDialogs() {
                $compile(copyConfModalHTML)($scope, function (el, scope) {
                    $('div[data-ng-view]').append(el);
                });
            }

            function loadCopyConfig() {
                $scope.copyCfg.copyFolder = appState.models.simulation.folder;
                $scope.copyCfg.copyName  = fileManager.nextNameInFolder(appState.models.simulation.name, appState.models.simulation.folder);
            }

            function loadList() {
                appState.listSimulations(
                    $location.search(),
                    function(data) {
                        $scope.doneLoadingSimList = true;
                        fileManager.updateTreeFromFileList(data);
                        loadCopyConfig();
                    });
            }
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

SIREPO.app.directive('resetSimulationModal', function(appDataService, appState, requestSender) {
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

SIREPO.app.directive('completeRegistration', function($window, requestSender, errorService) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div class="row text-center">',
            '<p>Please enter your full name to complete your Sirepo registration.</p>',
            '</div>',
            '<form class="form-horizontal" autocomplete="off" novalidate>',
              '<div class="row text-center">',
                '<label class="col-sm-3 control-label">Your full name</label>',
                '<div class="col-sm-7">',
                  '<input name="guestName" class="form-control" data-ng-model="data.displayName" required/>',
                  '<div class="sr-input-warning" data-ng-show="showWarning">{{ warningText }}</div>',
                '</div>',
              '</div>',
              '<div class="row text-center" style="margin-top: 10px">',
                 '<button data-ng-click="submit()" class="btn btn-primary" data-ng-disabled="! data.displayName">Submit</button>',
              '</div>',
            '</form>',
        ].join(''),
        controller: function($scope) {
            function handleResponse(data) {
                if (data.state === 'ok') {
                    $scope.showWarning = false;
                    $window.location.href = requestSender.formatUrl(
                        'root',
                        {'<simulation_type>': SIREPO.APP_SCHEMA.simulationType}
                    );
                    return;
                }
                $scope.showWarning = true;
                $scope.warningText = 'Server reported an error, please contact support@radiasoft.net.';
            }
            $scope.data = {};
            $scope.submit = function() {
                //TODO(robnagler): change button to sending
                requestSender.sendRequest(
                    'authCompleteRegistration',
                    handleResponse,
                    {
                        displayName: $scope.data.displayName,
                        simulationType: SIREPO.APP_NAME
                    }
                );
            };
        },
    };
});

SIREPO.app.directive('emailLogin', function(requestSender, errorService) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div class="row text-center">',
              '<p>Enter your email address and we\'ll send an authorization link to your inbox.</p>',
            '</div>',
            '<form class="form-horizontal" autocomplete="off" novalidate>',
              '<div class="row text-center">',
                '<label class="col-sm-3 control-label">Your Email</label>',
                '<div class="col-sm-9">',
                  '<input type="text" class="form-control" data-ng-model="data.email" required/>',
                  '<div class="sr-input-warning" data-ng-show="showWarning">{{ warningText }}</div>',
                '</div>',
              '</div>',
              '<div class="row text-center" style="margin-top: 10px">',
                 '<button data-ng-click="login()" class="btn btn-primary">Continue</button>',
              '</div>',
            '</form>',
            '<div data-confirmation-modal="" data-is-required="true" data-id="sr-email-login-done" data-title="Check your inbox" data-ok-text="" data-cancel-text="">',
              '<p>We just emailed a confirmation link to {{ data.sentEmail }}. Click the link and you\'ll be signed in. You may close this window.</p>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            function handleResponse(data) {
                if (data.state == 'ok') {
                    $scope.showWarning = false;
                    $scope.data.email = '';
                    $scope.form.$setPristine();
                    $('#sr-email-login-done').modal('show');
                }
                else {
                    $scope.showWarning = true;
                    $scope.warningText = 'Server reported an error, please contact support@radiasoft.net.';
                }
            }
            $scope.data = {};
            $scope.login = function() {
                var e = $scope.data.email;
                errorService.alertText('');
                if (! ( e && e.match(/^.+@.+\..+$/) )) {
                    $scope.showWarning = true;
                    $scope.warningText = 'Email address is invalid. Please update and resubmit.';
                    return;
                }
                $scope.showWarning = false;
                $scope.data.sentEmail = $scope.data.email;
                //TODO(robnagler): change button to sending
                requestSender.sendRequest(
                    'authEmailLogin',
                    handleResponse,
                    {
                        email: $scope.data.sentEmail,
                        simulationType: SIREPO.APP_NAME
                    }
                );
            };
        },
        link: function(scope, element) {
            // get the angular form from within the transcluded content
            scope.form = element.find('input').eq(0).controller('form');
        }
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

SIREPO.app.directive('splitPanels', function($window) {
    var GUTTER_SIZE = 20;
    var MAX_TOP_PERCENT = 85;
    var MIN_TOP_PERCENT = 15;
    var TOP_PAD = 12;
    return {
        controller: function($scope) {

            function totalHeight() {
                return $($window).height() - $scope.el.offset().top;
            }

            function childHeight(panel) {
                return panel.children().first().height();
            }

            $scope.constrainTopPanelHeight = function() {
                var topPanel = $('#sr-top-panel');
                var topHeight = topPanel.height();
                var maxHeight = childHeight(topPanel);
                var bottomPanel = $('#sr-bottom-panel');
                var bothFit = maxHeight + TOP_PAD + GUTTER_SIZE + childHeight(bottomPanel) < totalHeight();
                // if topPanel is sized too large or both panels fit in the page height
                if (topHeight > maxHeight || bothFit) {
                    // set split sizes to exactly fit the top panel
                    var splitterHeight = $scope.el.height();
                    var x = Math.min(Math.max((maxHeight + TOP_PAD) * 100 / splitterHeight, MIN_TOP_PERCENT), MAX_TOP_PERCENT);
                    $scope.split.setSizes([x, 100 - x]);
                }
                $scope.el.find('.gutter').css('visibility', bothFit ? 'hidden' : 'visible');
            };
            $scope.panelHeight = function() {
                if (! $scope.el) {
                    return '0';
                }
                // the DOM is not yet in the state to be measured, check sizes in next cycle
                // can't use $timeout() here because it causes an endless digest loop
                setTimeout($scope.constrainTopPanelHeight, 0);
                return totalHeight() + 'px';
            };
        },
        link: function(scope, element) {
            scope.el = $(element);
            scope.split = Split(['#sr-top-panel', '#sr-bottom-panel'], {
                direction: 'vertical',
                gutterSize: GUTTER_SIZE,
                snapOffset: 0,
                sizes: [25, 75],
                onDrag: scope.constrainTopPanelHeight,
            });
            scope.$on('$destroy', function() {
                scope.split.destroy();
            });
        },
    };
});

SIREPO.app.directive('stringToNumber', function() {
    return {
        restrict: 'A',
        require: 'ngModel',
        scope: {
            numberType: '@stringToNumber',
            min: '<',
            max: '<',
        },
        link: function(scope, element, attrs, ngModel) {
            function isValid(v) {
                if (v < scope.min || v > scope.max) {
                    return false;
                }
                return true;
            }

            ngModel.$parsers.push(function(value) {
                if (ngModel.$isEmpty(value))  {
                    return null;
                }
                if (SIREPO.NUMBER_REGEXP.test(value)) {
                    var v;
                    if (scope.numberType == 'integer') {
                        v = parseInt(parseFloat(value));
                        if (! isValid(v)) {
                            return undefined;
                        }
                        if (v != value) {
                            ngModel.$setViewValue(v);
                            ngModel.$render();
                        }
                        return v;
                    }
                    v = parseFloat(value);
                    if (! isValid(v)) {
                        return undefined;
                    }
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
                if (scope.numberType != 'integer') {
                    if (Math.abs(value) >= 10000 || (value != 0 && Math.abs(value) < 0.001)) {
                        value = (+value).toExponential(9).replace(/\.?0+e/, 'e');
                    }
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
            var validator = scope.validator ? scope.validator() : null;

            function setModel(file) {
                scope.$apply(function () {
                    modelSetter(scope, file);
                });
            }

            element.bind('change', function() {
                var file = element[0].files[0];
                if(! validator) {
                    setModel(file);
                    return;
                }
                validator(file).then(function (ok) {
                    setModel(ok? file : null);
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
            var isRefreshing = false;
            var offValue = enumValue(0, SIREPO.ENUM_INDEX_VALUE);
            var onValue =  enumValue(1, SIREPO.ENUM_INDEX_VALUE);
            var toggle = $(element);

            function enumValue(index, field) {
                return SIREPO.APP_SCHEMA.enum[scope.info[SIREPO.INFO_INDEX_TYPE]][index][field];
            }

            toggle.bootstrapToggle({
                off: enumValue(0, SIREPO.ENUM_INDEX_LABEL),
                on: enumValue(1, SIREPO.ENUM_INDEX_LABEL),
            });

            toggle.change(function() {
                // do not change the model if this was called from refreshChecked()
                if (! isRefreshing) {
                    scope.model[scope.field] = toggle.prop('checked') ? onValue : offValue;
                    scope.$apply();
                }
                isRefreshing = false;
            });

            // called by ngOpen in template - checkbox will not initialize properly otherwise.
            // must live in an object to invoke with isolated scope
            scope.fieldDelegate.refreshChecked = function() {
                if (scope.model && scope.field) {
                    var val = scope.model[scope.field];
                    if (val === undefined) {
                        val = scope.info[SIREPO.INFO_INDEX_DEFAULT_VALUE];
                    }
                    var isChecked = val == onValue;
                    if (toggle.prop('checked') != isChecked) {
                        isRefreshing = true;
                        toggle.bootstrapToggle(isChecked ? 'on' : 'off');
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
    };
});

SIREPO.app.directive('optimizeFloat', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            modelName: '=',
            field: '=',
            min: '=',
            max: '=',
        },
        template: [
            // keep the field the same dimensions as regular float, but offset width by button size
            '<div class="input-group input-group-sm" style="margin-right: -30px">',
              '<input data-string-to-number="" data-ng-model="model[field]" data-min="min" data-max="max" class="form-control" style="text-align: right" data-lpignore="true" required />',
              '<div class="input-group-btn">',
                '<button data-ng-attr-class="btn btn-{{ buttonName() }} dropdown-toggle" data-toggle="dropdown" type="button" title="Optimization Settings"><span class="glyphicon glyphicon-cog"></span></button>',
                '<ul class="dropdown-menu pull-right">',
                  '<li><a href data-ng-click="toggleCheck()" ><span data-ng-attr-class="glyphicon glyphicon-{{ checkedName() }}"></span> Select this field for optimization</a></li>',
                '</ul>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            function checkField() {
                return appState.optFieldName($scope.modelName, $scope.field, $scope.model);
            }
            function isChecked() {
                if (appState.isLoaded() && $scope.model) {
                    return appState.models.optimizer.enabledFields[checkField()];
                }
                return false;
            }
            $scope.buttonName = function() {
                return isChecked() ? 'primary' : 'default';
            };
            $scope.checkedName = function() {
                return isChecked() ? 'check' : 'unchecked';
            };
            $scope.toggleCheck = function() {
                var optimizer = appState.models.optimizer;
                if (optimizer.enabledFields[checkField()]) {
                    delete optimizer.enabledFields[checkField()];
                }
                else {
                    optimizer.enabledFields[checkField()] = true;
                }
                appState.saveChanges('optimizer');
            };
        },
    };
});

SIREPO.app.directive('rangeSlider', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            model: '=',
            modelName: '=',
            update: '&',
        },
        template: [
            '<input id="{{ modelName }}-{{ field }}-range" type="range" data-ng-model="model[field]" data-ng-change="update()()">',
            '<span class="valueLabel">{{ model[field] }}{{ model.units }}</span>',
        ].join(''),
        controller: function($scope) {
            //if (! $scope.model) {
            //    $scope.model = appState.models[$scope.modelName];
            //}
        },
    };
});

SIREPO.app.directive('3dSliceWidget', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            axisInfo: '<',
            field: '=',
            model: '=',
            sliceAxis: '<',
            update: '&',
        },
        template: [
            '<div>',
                '<svg data-ng-attr-height="{{ 2.0 * axisInfo.height }}" data-ng-attr-width="{{ 2.0 * axisInfo.width }}">',
                    '<rect data-ng-attr-x="{{ xOffset(50) }}" y="0" stroke="black" fill="none" data-ng-attr-width="{{ axisInfo.width }}" data-ng-attr-height="{{ axisInfo.height }}"></rect>',
                    //'<rect x="0" y="50" stroke="black" fill="rgba(255, 255, 255, 0.5)" width="100" height="100"></rect>',
                    '<line data-ng-attr-x1="{{ xOffset(0) }}" y1="50"  data-ng-attr-x2="{{ xOffset(50) }}" y2="0" stroke="black"></line>',
                    '<line data-ng-attr-x1="{{ xOffset(100) }}" y1="50" data-ng-attr-x2="{{ xOffset(150) }}" y2="0" stroke="black"></line>',
                    '<line data-ng-attr-x1="{{ xOffset(0) }}" y1="150" data-ng-attr-x2="{{ xOffset(50) }}" y2="100" stroke="black"></line>',
                    '<line data-ng-attr-x1="{{ xOffset(100) }}" y1="150" data-ng-attr-x2="{{ xOffset(150) }}" y2="100" stroke="black"></line>',
                    '<rect data-ng-attr-x="{{ xOffset(0) }}" y="50" stroke="black" fill="rgba(255, 255, 255, 0.5)" data-ng-attr-width="{{ axisInfo.width }}" data-ng-attr-height="{{ axisInfo.height }}"></rect>',
                    '<text data-ng-attr-x="{{ xOffset(50) }}" y="175" stroke="red">{{ axisInfo.xLabel }}</text>',
                    '<text x="0" y="100">{{ axisInfo.yLabel }}</text>',
                    '<text data-ng-attr-x="{{ xOffset(125) }}" y="125">{{ axisInfo.zLabel }}</text>',
                    '{{ slicePlane() }}',
                '</svg>',
            '</div>',
            '<span class="valueLabel">{{ model[field] }}{{ model.units }}</span>',
        ].join(''),
        controller: function($scope) {

            var offsets = {
                x: 25,
                y: 0
            };


            $scope.slicePlane = function() {
                var plotAxis = $scope.axisInfo.map[$scope.sliceAxis];
                var x1 = $scope.xOffset(0);
                var x2 = $scope.xOffset();
                if (plotAxis === 'z') {
                    return [
                        '<g data-ng-drag="true">',
                            '<line x1="" y1="" x2="" y2=""></line>',
                        '</g>'
                    ].join('');
                }
                return '';
            };

            $scope.xOffset = function(val) {
                return (val || 0) + (offsets.x || 0);
            };

            $scope.yOffset = function(val) {
                return (val || 0) + (offsets.y || 0);
            };

        },
    };
});

SIREPO.app.directive('simSections', function(utilities) {

    return {
        restrict: 'A',
        transclude: true,
        template: [
            '<ul data-ng-transclude="" class="nav navbar-nav sr-navbar-right" data-ng-class="{\'nav-tabs\': isWide()}"></ul>',
        ].join(''),
        controller: function($scope) {
            $scope.isWide = function() {
                return utilities.isWide();
            };
        },
    };
});

SIREPO.app.directive('simStatusPanel', function() {
    return {
        restrict: 'A',
        scope: {
            simState: '=simStatusPanel',
        },
        template: [
            '<form name="form" class="form-horizontal" autocomplete="off" novalidate data-ng-show="simState.isProcessing()">',
              '<div data-ng-show="simState.isStatePending()">',
                '<div class="col-sm-12">{{ simState.stateAsText() }} {{ simState.dots }}</div>',
              '</div>',
              '<div data-ng-show="simState.isStateRunning()">',
                '<div class="col-sm-12">',
                  '<div data-ng-show="simState.isInitializing()">{{ initMessage() }} {{ simState.dots }}</div>',
                  '<div data-ng-show="simState.getFrameCount() > 0">{{ message(true); }}</div>',
                  '<div class="progress">',
                    '<div class="progress-bar progress-bar-striped active" role="progressbar" aria-valuenow="{{ simState.getPercentComplete() }}" aria-valuemin="0" aria-valuemax="100" data-ng-attr-style="width: {{ simState.getPercentComplete() || 100 }}%">',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
              '<div class="col-sm-6 pull-right">',
                '<button class="btn btn-default" data-ng-click="simState.cancelSimulation()">End Simulation</button>',
              '</div>',
            '</form>',
            '<form name="form" class="form-horizontal" autocomplete="off" novalidate data-ng-show="simState.isStopped()">',
              '<div class="col-sm-12" data-ng-show="simState.getFrameCount() >= 1">{{ message(false); }}<br><br></div>',
              '<div data-ng-show="simState.isStateError()">',
                '<div class="col-sm-12">{{ simState.stateAsText() }}</div>',
              '</div>',
              '<div class="col-sm-6 pull-right">',
                '<button class="btn btn-default" data-ng-click="simState.runSimulation()">Start New Simulation</button>',
              '</div>',
            '</form>',
            '<div class="clearfix"></div>',
            '<div data-ng-if="errorMessage()"><div class="text-danger"><strong>{{ ::appName }} Error:</strong></div><pre>{{ errorMessage() }}</pre></div>',
        ].join(''),
        controller: function($scope) {
            $scope.appName = SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_NAME].shortName;

            function callSimState(method) {
                return $scope.simState[method] && $scope.simState[method]();
            }

            $scope.errorMessage = function() {
                return callSimState('errorMessage');
            };

            $scope.initMessage = function() {
                return callSimState('initMessage')
                    || 'Running Simulation';
            };

            $scope.message = function(isRunning) {
                if (isRunning) {
                    return callSimState('runningMessage')
                        || 'Completed frame: ' + $scope.simState.getFrameCount();
                }
                return callSimState('notRunningMessage')
                    || 'Simulation ' + $scope.simState.stateAsText() + ': ' + $scope.simState.getFrameCount() + ' animation frames';
            };
        },
    };
});

SIREPO.app.service('plotToPNG', function($http) {

    var canvases = {};

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
        d3.select(svg).classed('sr-download-png', true);
        var svgString = svg.parentNode.innerHTML;
        context.drawSvg(svgString, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(function(blob) {
            saveAs(blob, fileName);
        });
        d3.select(svg).classed('sr-download-png', false);
    }

    function pxToInteger(value) {
        value = value.replace(/px/, '');
        return parseInt(value);
    }

    // Stores canvases for updates and later use.  We use the existing reportID
    // as the key
    this.addCanvas = function(canvas, reportId) {
        if (!reportId) {
            return;
        }
        canvases[reportId] = canvas;
    };

    this.getCanvas = function(reportId) {
        return canvases[reportId];
    };

    this.getCopy = function (reportId, size) {
        var canvas = this.getCanvas(reportId);
        if(! canvas ) {
            return null;
        }

        var s = [
            parseInt(canvas.getAttribute('width')),
            parseInt(canvas.getAttribute('height'))
        ];
        size.forEach(function (dim, i) {
            var nextI = (i + 1) % 2;
            var next = size[nextI];
            if(! dim) {
                if(next) {
                    s[i] *= (next / s[nextI]);
                    s[nextI] = next;
                }
            }
        });
        var cnvCopy = document.createElement('canvas');
        var cnvCtx = cnvCopy.getContext('2d');
        cnvCopy.width = s[0];
        cnvCopy.height = s[1];
        cnvCtx.drawImage(canvas, 0, 0, s[0], s[1]);
        return cnvCopy;
    };

    this.hasCanvas = function(reportId) {
        return ! ! canvases[reportId];
    };

    this.removeCanvas = function(reportId) {
        delete canvases[reportId];
    };

    this.downloadPNG = function(svg, height, plot3dCanvas, fileName) {
        // embed all css styles into SVG node before rendering
        if (svg.firstChild.nodeName == 'STYLE') {
            downloadPlot(svg, height, plot3dCanvas, fileName);
            return;
        }
        var promises = [];
        ['sirepo.css'].concat(SIREPO.APP_SCHEMA.dynamicFiles.sirepoLibs.css || []).forEach(function(cssFile) {
            promises.push($http.get('/static/css/' + cssFile + SIREPO.SOURCE_CACHE_KEY));
        });
        var cssText = '';
        function cssResponse(response) {
            promises.shift();
            cssText += response.data;
            if (promises.length) {
                promises[0].then(cssResponse);
                return;
            }
            if (svg.firstChild.nodeName != 'STYLE') {
                var css = document.createElement('style');
                css.type = 'text/css';
                // work-around bug fix #857, canvg.js doesn't handle non-standard css
                cssText = cssText.replace('input::-ms-clear', 'ms-clear');
                css.appendChild(document.createTextNode(cssText));
                svg.insertBefore(css, svg.firstChild);
            }
            downloadPlot(svg, height, plot3dCanvas, fileName);
        }
        promises[0].then(cssResponse);
    };

    this.downloadCanvas = function(reportId, width, height, fileName)  {
        var cnv = this.getCopy(reportId, [width || 0, height || 0]);
        cnv.toBlob(function(blob) {
            saveAs(blob, fileName);
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

SIREPO.app.service('mathRendering', function() {
    // Renders math expressions in a plain text string using KaTeX.
    // The math expressions must be tightly bound by $, ex. $E = mc^2$
    var RE = /\$[\-\w\\](.*\S)?\$/;

    function encodeHTML(text) {
        return $('<div />').text(text).html();
    }

    this.mathAsHTML = function(text, options) {
        if (! this.textContainsMath(text)) {
            return encodeHTML(text);
        }
        var parts = [];

        var i = text.search(RE);
        while (i != -1) {
            if (i > 0) {
                parts.push(encodeHTML(text.slice(0, i)));
                text = text.slice(i + 1);
            }
            else {
                text = text.slice(1);
            }
            i = text.search(/\S\$/);
            if (i == -1) {
                // should never get here
                throw 'invalid math expression';
            }
            parts.push(katex.renderToString(text.slice(0, i + 1), options));
            text = text.slice(i + 2);
            i = text.search(RE);
        }
        if (text) {
            parts.push(encodeHTML(text));
        }
        return parts.join('');
    };

    this.textContainsMath = function(text) {
        return RE.test(text);
    };
});

SIREPO.app.service('keypressService', function() {

    var listeners = {};
    var reports = {};
    var activeListeners = [];
    var activeListenerId = null;

    this.addListener = function(listenerId, listener, reportId) {
        if(! reportId) {
            return;
        }
        listeners[listenerId] = listener;
        if (! reports[reportId]) {
                reports[reportId] = [];
        }
        reports[reportId].push(listenerId);
        if(activeListeners.indexOf(listenerId) < 0) {
            activeListeners.push(listenerId);
        }

        // turn off highlighting for active report panel, if any
        showPanelActive(reportForListener(activeListenerId), false);

        activeListenerId = listenerId;
        this.enableListener(true);
    };
    this.hasListener = function(listenerId) {
        return activeListeners.indexOf(listenerId) >= 0;
    };
    this.hasReport = function(reportId) {
        return ! ! reports[reportId];
    };

    this.removeListener = function(listenerId) {
        var lIndex = activeListeners.indexOf(listenerId);
        if(lIndex >= 0) {
            activeListeners.splice(lIndex, 1);
        }
        delete listeners[listenerId];

        var reportId = reportForListener(listenerId);
        showPanelActive(reportId, false);
        if(reportId) {
            reports[reportId].splice(reports[reportId].indexOf(listenerId), 1);
        }

        // activate the last one added, if any remain
        if(activeListeners.length > 0) {
            activeListenerId = activeListeners[activeListeners.length - 1];
            this.enableListener(true);
        }
        else {
            activeListenerId = null;
            this.enableListener(false);
        }
    };

    this.removeListenersForReport = function(reportId) {
        if(! reportId || ! reports[reportId]) {
            return;
        }
        var rlArr = reports[reportId];
        for(var rlIndex = 0; rlIndex < rlArr.length; ++rlIndex) {
            this.removeListener(rlArr[rlIndex]);
        }
    };
    this.removeReport = function(reportId) {
        if(! reportId) {
            return;
        }
        this.removeListenersForReport(reportId);
        delete reports[reportId];
    };


    // set the active listener, or
    // remove keydown listener from body element leaving the keys in place
    this.enableListener = function(doListen, listenerId) {
        if(! listenerId)  {
            listenerId = activeListenerId;
        }
        activeListenerId = listenerId;
        var reportId = reportForListener(activeListenerId);
        if(doListen && activeListenerId) {
            d3.select('body').on('keydown', listeners[activeListenerId]);
            showPanelActive(reportId, true);
            return;
        }
        d3.select('body').on('keydown', null);
        showPanelActive(reportId, false);
    };
    this.enableNextListener = function(direction) {
        var lIndex = activeListeners.indexOf(activeListenerId);
        if(lIndex < 0) {
            return;
        }
        this.enableListener(false);
        var d = direction < 0 ? -1 : 1;
        var newIndex = (lIndex + d + activeListeners.length) % activeListeners.length;
        this.enableListener(true, activeListeners[newIndex]);
    };

    function reportForListener(listenerId) {
        if(! listenerId) {
            return null;
        }
        for(var reportId in reports) {
            var rlIndex = reports[reportId].indexOf(listenerId);
            if(rlIndex < 0) {
                continue;
            }
            return reportId;
        }
    }

    function showPanelActive(reportId, isActive) {
        if(! reportId) {
            return;
        }
        if(isActive) {
            $('#' + reportId).addClass('sr-panel-active');
            return;
        }
        $('#' + reportId).removeClass('sr-panel-active');
    }

});

SIREPO.app.service('plotRangeService', function(appState, panelState, requestSender) {
    var self = this;
    var runningModels = [];

    function setFieldRange(controller, prefix, model, field) {
        //TODO(pjm): special case for jspec, needs to get migrated to jspec.js
        if (field == 'dpp') {
            field = 'dp/p';
        }
        var range = controller.fieldRange[field];
        if (range) {
            model[prefix + 'Size'] = range[1] - range[0];
            model[prefix + 'Offset'] = (range[0] + range[1]) / 2;
        }
    }

    self.computeFieldRanges = function(controller, name, percentComplete) {
        if (controller.simState.isProcessing()) {
            appState.models[name].isRunning = 1;
            if (runningModels.indexOf(name) < 0) {
                runningModels.push(name);
            }
        }
        // this assumes all models share same range parameters
        if (percentComplete == 100 && ! controller.isComputingRanges) {
            controller.fieldRange = null;
            controller.isComputingRanges = true;
            appState.models[name].isRunning = 1;
            requestSender.getApplicationData(
                {
                    method: 'compute_particle_ranges',
                    simulationId: appState.models.simulation.simulationId,
                    modelName: name,
                },
                function(data) {
                    controller.isComputingRanges = false;
                    if (appState.isLoaded() && data.fieldRange) {
                        if (appState.models[name].isRunning) {
                            if (runningModels.length) {
                                runningModels.forEach(function(name) {
                                    appState.models[name].isRunning = 0;
                                });
                                // refresh plots with computed field ranges
                                appState.saveChanges(runningModels);
                                runningModels = [];
                            }
                        }
                        controller.fieldRange = data.fieldRange;
                    }
                });
        }
    };

    self.processPlotRange = function(controller, name, modelKey) {
        var model = appState.models[modelKey || name];
        panelState.showRow(name, 'horizontalSize', model.plotRangeType != 'none');
        ['horizontalSize', 'horizontalOffset', 'verticalSize', 'verticalOffset'].forEach(function(f) {
            panelState.enableField(name, f, model.plotRangeType == 'fixed');
        });
        if ((model.plotRangeType == 'fit' && controller.fieldRange)
            || (model.plotRangeType == 'fixed' && ! model.horizontalSize)) {
            if (model.reportType) {
                var fields = model.reportType.split('-');
                setFieldRange(controller, 'horizontal', model, fields[0]);
                setFieldRange(controller, 'vertical', model, fields[1]);
            }
            else {
                setFieldRange(controller, 'horizontal', model, model.x);
                setFieldRange(controller, 'vertical', model, model.y || model.y1);
            }
        }
    };
});

SIREPO.app.service('utilities', function($window, $interval) {

    var self = this;

    this.modelFieldID = function (modelName, fieldName) {
        return 'model-' + modelName + '-' + fieldName;
    };

    this.isWide = function() {
        return $window.innerWidth > 767;
    };

    // font utilities
    this.fontSizeFromString = function(fsString) {
        if(! fsString) {
            return 0;
        }
        return parseFloat(fsString.substring(0, fsString.indexOf('px')));
    };

    this.wordSplits = function(str) {
        var wds = str.split(/(\s+)/);
        return wds.map(function (value, index) {
            return wds.slice(0, index).join('') + value;
        });
    };

    // fullscreen utilities
    this.getFullScreenElement = function() {
        return document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement;
    };
    this.isFullscreen = function () {
        return ! ! this.getFullScreenElement();
    };
    this.isFullscreenElement = function(el) {
        return el == this.getFullScreenElement();
    };
    this.requestFullscreenFn = function(el) {
        return el.requestFullscreen ||
            el.mozRequestFullScreen ||
            el.webkitRequestFullscreen ||
            el.msRequestFullscreen ||
            function() {
                srlog('This browser does not support full screen');
            };
        };
    this.exitFullscreenFn = function() {
        return document.exitFullscreen ||
            document.mozCancelFullScreen ||
            document.webkitExitFullscreen ||
            document.msExitFullscreen ||
            function() {
                srlog('This browser does not support full screen');
            };
    };
    this.fullscreenListenerEvent = function() {
        if(this.exitFullscreenFn() == document.mozCancelFullScreen) {
            return 'mozfullscreenchange';
        }
        if(this.exitFullscreenFn() == document.webkitExitFullscreen) {
            return 'webkitfullscreenchange';
        }
        if(this.exitFullscreenFn() == document.msExitFullscreen) {
            return 'MSFullscreenChange';
        }
        return 'fullscreenchange';
    };

    // Returns a function, that, as long as it continues to be invoked, will not
    // be triggered. The function will be called after it stops being called for
    // N milliseconds.
    // taken from http://davidwalsh.name/javascript-debounce-function
    this.debounce = function(delayedFunc, milliseconds) {
        var debounceInterval = null;
        return function() {
            var context = this, args = arguments;
            var later = function() {
                if (debounceInterval) {
                    $interval.cancel(debounceInterval);
                    debounceInterval = null;
                }
                delayedFunc.apply(context, args);
            };
            if (debounceInterval) {
                $interval.cancel(debounceInterval);
            }
            debounceInterval = $interval(later, milliseconds, 1);
        };
    };

    // returns an array containing the unique elements of the input,
    // according to a two-input equality function (null means use ===)
    this.unique = function(arr, equals) {
        var uniqueArr = [];
        arr.forEach(function (a, i) {
            var found = false;
            for(var j = 0; j < uniqueArr.length; ++j) {
                var b = uniqueArr[j];
                found = equals ? equals(a, b) : a === b;
                if(found) {
                    break;
                }
            }
            if(! found) {
                uniqueArr.push(a);
            }
        });
        return uniqueArr;
    };

});
