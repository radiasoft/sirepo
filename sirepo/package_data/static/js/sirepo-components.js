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

SIREPO.app.directive('simulationDetailPage', function(appState, $compile) {
    return {
        restrict: 'A',
        scope: {
            controller: '@',
            template: '@',
            templateUrl: '@',
        },
        link: function(scope, element) {
            scope.appState = appState;
            let template = '<div data-ng-if="appState.isLoaded()"><div data-ng-controller="'
                + scope.controller + '"';
            if (scope.template) {
                template +=  '>' + scope.template;
            }
            else if (scope.templateUrl) {
                template += ' data-ng-include="templateUrl">';
            }
            template += '</div></div>';
            element.append($compile(template)(scope));
        },
    };
});

SIREPO.app.directive('advancedEditorPane', function(appState, panelState, utilities, $compile) {
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
        template: `
            <h5 data-ng-if="::description && fieldDef == 'advanced'"><span data-text-with-math="description"></span></h5>
            <form name="form" class="form-horizontal" autocomplete="off" novalidate>
              <ul data-ng-if="pages" class="nav nav-tabs">
                <li data-ng-repeat="page in pages" role="presentation" class="{{page.class}}" data-ng-class="{active: page.isActive}"><a href data-ng-click="setActivePage(page)">{{ page.name }}</a></li>
              </ul>
              <br data-ng-if="pages" />
              <div data-ng-repeat="f in (activePage ? activePage.items : advancedFields)">
                <div class="lead text-center" data-ng-if="::isLabel(f)" style="white-space: pre-line;"><span data-text-with-math="::labelText(f)"</span></div>
                <div class="form-group form-group-sm" data-ng-if="::isField(f)" data-model-field="f" data-form="form" data-model-name="modelName" data-model-data="modelData" data-view-name="viewName"></div>
                <div data-ng-if="::isColumnField(f)" data-column-editor="" data-column-fields="f" data-model-name="modelName" data-model-data="modelData"></div>
              </div>
              <div data-ng-if="wantButtons" class="row">
                <div class="col-sm-12 text-center" data-buttons="" data-model-name="modelName" data-model-data="modelData" data-fields="advancedFields"></div>
              </div>
            </form>
        `,
        controller: function($scope, $element) {
            var viewInfo = appState.viewInfo($scope.viewName);
            var i;

            function tabSelectedEvent() {
                appState.whenModelsLoaded($scope, function() {
                    panelState.waitForUI(function() {
                        $scope.$emit('sr-tabSelected', $scope.modelName, $scope.modelData ? $scope.modelData.modelKey : null);
                    });
                });
            }

            $scope.fieldDef = $scope.fieldDef || 'advanced';
            $scope.form = angular.element($($element).find('form').eq(0));
            $scope.modelName = viewInfo.model || $scope.viewName;
            $scope.description = viewInfo.description;
            $scope.advancedFields = viewInfo[$scope.fieldDef];
            if (! $scope.advancedFields) {
                throw new Error($scope.modelName + ' view is missing ' + $scope.fieldDef + ' fields');
            }
            // create a View component for app business logic
            $element.append($compile(
                '<div ' + utilities.viewLogicName($scope.viewName)
                    + '="{{ fieldDef }}"'
                    + ' data-model-name="modelName" data-model-data="modelData">'
                    + '</div>')($scope));

            $scope.isColumnField = function(f) {
                return typeof(f) != 'string';
            };
            $scope.isField = function(f) {
                return !($scope.isColumnField(f) || $scope.isLabel(f));
            };
            $scope.isLabel = function(f) {
                if ($scope.isColumnField(f)) {
                    return false;
                }
                return f.indexOf('*') === 0;
            };
            $scope.labelText = function(f) {
                return f.substring(1);
            };
            $scope.resetActivePage = function() {
                if ($scope.pages) {
                    $scope.setActivePage($scope.pages[0]);
                }
                else {
                    tabSelectedEvent();
                }
            };
            $scope.setActivePage = function(page) {
                if ($scope.activePage) {
                    $scope.activePage.isActive = false;
                }
                $scope.activePage = page;
                page.isActive = true;
                //TODO(pjm): DEPRECATED parentController processing replaced by viewLogic
                if (appState.isLoaded() && $scope.parentController && $scope.parentController.handleModalShown) {
                    // invoke parentController after UI has been constructed
                    panelState.waitForUI(function() {
                        $scope.parentController.handleModalShown(
                            $scope.modelName, $scope.modelData ? $scope.modelData.modelKey : null);
                    });
                }
                tabSelectedEvent();
            };

            $scope.showPageNamed = (name, doShow) => {
                const p = $scope.pages.filter(p => p.name === name)[0];
                if (! p) {
                    return;
                }
                const l = $(`li.${p.class}`);
                if (doShow) {
                    l.show();
                }
                else {
                    l.hide();
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
            $scope.resetActivePage();
        },
        link: function(scope, element) {
            $(element).closest('.modal').on('show.bs.modal', scope.resetActivePage);
            scope.$on('sr.setActivePage', (event, modelName, pageNumber) => {
                if (scope.modelName === modelName && scope.pages) {
                    scope.setActivePage(scope.pages[pageNumber]);
                }
            });
            scope.$on('$destroy', function() {
                $(element).closest('.modal').off();
            });
        }
    };
});

SIREPO.app.directive('srAlert', function(errorService, uri) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div data-ng-repeat="m in errorService.MESSAGE_TYPES track by $index">
              <div data-ng-if="text(m)" class="alert"
                    data-ng-class="{'alert-warning': m === 'alert', 'alert-info': m !== 'alert'}" role="alert">
                <button type="button" class="close" data-ng-click="clear(m)" aria-label="Close">
                  <span aria-hidden="true">&times;</span>
                </button>
                <strong>{{ text(m) }}</strong>
                <span data-ng-if="m === 'subscription'">
                    <span data-plans-link="" data-link-text="Subscribe now"</span>
                </span>
              </div>
            </div>
        `,
        controller: function($scope) {
            $scope.errorService = errorService;
            $scope.clear = (alertType) => errorService.messageText(alertType, '');
            $scope.text = (alertType) => errorService.messageText(alertType);
            $scope.$on('$routeChangeSuccess', $scope.clearAlert);
        },
    };
});

SIREPO.app.directive('getStarted', function(browserStorage, stringsService) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div data-ng-show="show()" class="alert alert-dismissible sr-get-started" role="alert" data-ng-class="'alert-info'">
                <button type="button" class="close" aria-label="Close" data-ng-click="dismiss()">
                    <span aria-hidden="true">&times;</span>
                </button>
                <span>
                    <div class="text-center"><strong>Welcome to Sirepo - ${SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_SCHEMA.simulationType].longName}!</strong></div>
                    Below are some example ${SIREPO.APP_SCHEMA.strings.simulationDataTypePlural}
                    and folders containing ${SIREPO.APP_SCHEMA.strings.simulationDataTypePlural}.
                    Click on the ${SIREPO.APP_SCHEMA.strings.simulationDataType}
                    to open and view the ${SIREPO.APP_SCHEMA.strings.simulationDataType} results.
                    <span data-ng-if="SIREPO.APP_SCHEMA.constants.canCreateNewSimulation">You can create a new ${SIREPO.APP_SCHEMA.strings.simulationDataType}
                    by selecting the "${stringsService.newSimulationLabel()}" link above.</span>
                </span>
            </div>
        `,
        controller: function($scope) {
	    $scope.SIREPO = SIREPO;
            const storageKey = 'getStarted';
            let isActive = true;

            $scope.dismiss = () => {
                browserStorage.setBoolean(storageKey, false);
                //TODO(pjm): this prevents Firefox from showing the notification right after it is dismissed
                isActive = false;
            };
            $scope.show = () => {
                if (! isActive) {
                    return false;
                }
                isActive = browserStorage.getBoolean(storageKey, true);
                return isActive;
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
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
            panelTitle: '@',
        },
        template: `
            <div class="panel panel-info" id="sr-{{ viewName }}-basicEditor">
              <div class="panel-heading clearfix" data-panel-heading="{{ panelTitle }}" data-model-key="modelKey" data-view-name="{{ viewName }}"></div>
                <div class="panel-body" data-ng-hide="panelState.isHidden(modelKey)">
                  <div data-advanced-editor-pane="" data-view-name="viewName" data-want-buttons="{{ wantButtons }}" data-field-def="basic" data-model-data="modelData" data-parent-controller="parentController"></div>
                  <div data-ng-transclude=""></div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
            var viewInfo = appState.viewInfo($scope.viewName);
            if (! viewInfo) {
                throw new Error('unknown viewName: ' + $scope.viewName);
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

SIREPO.app.directive('buttons', function(appState, panelState, stringsService) {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            fields: '=',
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
        },
        template: `
            <div data-ng-show="isFormDirty()">
              <button data-ng-click="saveChanges()" class="btn btn-primary sr-button-save-cancel" data-ng-disabled="! isFormValid()">{{ ::saveButtonLabel() }}</button>
              <button data-ng-click="cancelChanges()" class="btn btn-default sr-button-save-cancel">Cancel</button>
            </div>
        `,
        controller: function($scope) {
            $scope.form = $scope.$parent.form;
            var modelKey = $scope.modelData
                ? $scope.modelData.modelKey
                : $scope.modelName;
            var fieldsByModel = panelState.getFieldsByModel(modelKey, $scope.fields);

            function changeDone() {
                $scope.form.$setPristine();
            }

            // returns an array of form elements (the DOM elements attribute is an
            // HTMLCollection)
            function getControls(form) {
                let els = form.$$element[0].elements;
                let ctls = [];
                for (let el of els) {
                    ctls.push(el);
                }
                return ctls;
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

            $scope.isFormValid = function() {
                // this is a first step in using HTML5 field validation
                let ctlsValid = getControls($scope.form)
                    .map(function (el) {
                        return el.validity.valid;
                    })
                    .reduce(function (prev, curr) {
                        return prev && curr;
                    }, true);
                return ctlsValid && $scope.form.$valid;
            };

            $scope.saveButtonLabel = () => {
                return stringsService.saveButtonLabel($scope.modelName);
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

SIREPO.app.directive('canceledDueToTimeoutAlert', function(authState) {
    return {
        restrict: 'A',
        scope: {
            seconds: '<',
            simState: '=canceledDueToTimeoutAlert',
        },
        template: `
            <div data-ng-if="showAlert()" class="alert alert-warning" role="alert">
              <h4 class="alert-heading"><b>Canceled: Maximum runtime exceeded</b></h4>
              <p>Your runtime limit is {{getTime()}}. To increase your maximum runtime, <span data-plans-link="" link-text="{{ upgradeToLink }}"></span>.</p>
            </div>
        `,
        controller: function($scope, appState) {
            $scope.upgradeToLink = `please upgrade to a ${authState.upgradeToPlan} plan`;

            $scope.getTime = function() {
                return appState.formatTime($scope.simState.getCanceledAfterSecs());
            };

            $scope.showAlert = function() {
                return $scope.simState.getCanceledAfterSecs();
            };
        },
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
            modalClosed: '&',
            isRequired: '@',
        },
        template: `
            <div class="modal fade" data-backdrop="{{ isRequired ? 'static' : true }}" id="{{ id }}" tabindex="-1" role="dialog">
              <div class="modal-dialog">
                <div class="modal-content">
                  <div class="modal-header bg-warning">
                    <button type="button" data-ng-if="! isRequired" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <span class="lead modal-title text-info">{{ title }}</span>
                  </div>
                  <div class="modal-body">
                    <div class="container-fluid">
                      <div class="row">
                        <div class="col-sm-12">
                          <div data-ng-transclude=""></div>
                        </div>
                      </div>
                      <div class="row">
                        <div class="col-sm-6 pull-right" style="margin-top: 1em">
                          <button data-ng-if="okText" data-ng-disabled="! isValid()" data-ng-click="clicked()" class="btn btn-default sr-button-size">{{ okText }}</button>
                           <button data-ng-if="! isRequired" data-dismiss="modal" class="btn btn-default sr-button-size">{{ cancelText || 'Cancel' }}</button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope, $element, $rootScope) {
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

            $($element).on('hidden.bs.modal', function() {
                $rootScope.$broadcast('sr-clearDisableAfterClick');
                if ($scope.modalClosed && angular.isFunction($scope.modalClosed())) {
                    $scope.modalClosed()();
                }
            });
        },
    };
});

SIREPO.app.directive('copyConfirmation', function(appState, fileManager, stringsService) {
    return {
        restrict: 'A',
        scope: {
            simId: '<',
            copyCfg: '=',
            disabled: '<',
        },
        template: `
            <div data-confirmation-modal="" data-id="sr-copy-confirmation" data-title="Copy {{ ::stringsService.formatKey('simulationDataType') }}" data-ok-text="Create Copy" data-ok-clicked="copy()">
              <form class="form-horizontal" autocomplete="off">
                <div class="form-group">
                <label class="col-sm-3 control-label">New Name</label>
                <div class="col-sm-9">
                  <input data-ng-disabled="disabled" data-safe-path="" class="form-control" data-ng-model="copyCfg.copyName" required/>
                  <div class="sr-input-warning" data-ng-show="showWarning">{{ warningText }}</div>
                </div>
                </div>
                <div class="form-group" data-ng-if="showFolders()">
                  <label class="col-sm-3 control-label">Folder</label>
                  <div class="col-sm-9">
                    <div data-user-folder-list="" data-model="copyCfg" data-field="'copyFolder'"></div>
                  </div>
              </div>
              </form>
            </div>
        `,
        controller: function($scope) {
            $scope.stringsService = stringsService;
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

SIREPO.app.directive('disableAfterClick', function() {
    return {
        restrict: 'A',
        transclude: true,
        template: `
            <fieldset ng-disabled="isDisabled" data-ng-click="click()"><ng-transclude></ng-transclude>
        `,
        controller: function($scope, $timeout) {
            $scope.isDisabled = false;


            $scope.click = function() {
                $scope.isDisabled = true;
            };


            $scope.$on('sr-clearDisableAfterClick', () => {
                // allow disable to be set before clearing it
                $timeout(function(){
                    $scope.isDisabled = false;
                });
            });
        },
    };
});

SIREPO.app.directive('exportPythonLink', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            reportTitle: '@',
        },
        template: `
            <a data-ng-href="{{ exportPythonUrl() }}">Export Python Code</a>
        `,
        controller: function($scope) {
            $scope.exportPythonUrl = () => {
                return panelState.pythonSourceUrl(
                    appState.models.simulation.simulationId,
                    panelState.findParentAttribute($scope, 'modelKey'),
                    $scope.reportTitle
                );
            };
        },
    };
});

SIREPO.app.directive('jobSettingsSbatchLoginAndStartSimulation', function() {
    return {
        restrict: 'A',
        scope: {
		simState: '<',
		startSimulation: '&'
        },
        template: `
            <div data-ng-if="simState.showJobSettings()">
              <div class="form-group form-group-sm">
                <div data-model-field="'jobRunMode'" data-model-name="simState.model" data-label-size="6" data-field-size="6"></div>
              </div>
              <div data-sbatch-options="simState"></div>
            </div>
            <div data-ng-if="sbatchLoginService.query('showLoginOrStatus')">
              <button ng-disabled="! sbatchLoginService.query('showLogin')" class="col-sm-6 pull-right btn btn-default" data-ng-click="loginClicked()">{{ label() }}</button>
            </div>
            <div class="col-sm-6 pull-right" data-ng-if="! sbatchLoginService.query('showLoginOrStatus')">
              <button class="btn btn-default" data-ng-click="start()">{{ startButtonLabel }}</button>
            </div>
	`,
        controller: function($scope, appState, sbatchLoginService, stringsService) {
	    $scope.sbatchLoginService = sbatchLoginService;
            $scope.startButtonLabel = stringsService.startButtonLabel($scope.simState.model);
            $scope.startWasClicked = false;
            $scope.label = () => {
                return sbatchLoginService.loginButtonLabel();
            };
            $scope.start = () => {
                $scope.startWasClicked = true;
                $scope.startSimulation();
            };
            $scope.loginClicked = () => {
                sbatchLoginService.event('loginClicked', {directiveScope: $scope});
            };
            const _jobRunModeChanged = () => {
                $scope.startWasClicked = false;
                sbatchLoginService.jobRunModeChanged($scope);
            };
            appState.whenModelsLoaded($scope, _jobRunModeChanged);
            appState.watchModelFields(
                $scope,
                [`${$scope.simState.model}.jobRunMode`],
                _jobRunModeChanged,
            );
            $scope.$on(
                'sbatchLoginEvent',
                (_, sbatchLoginEvent) => {
                    if (sbatchLoginEvent.query('showCredsForm')) {
                        $scope.loginClicked();
                    }
                    else if (sbatchLoginEvent.query('isLoggedInFromCreds')) {
                        if ($scope.startWasClicked) {
                            $scope.start();
                        }
                        else {
                            $scope.simState.resetSimulation();
                        }
                    }
                },
            );
        },
    };
});

SIREPO.app.directive('randomSeed', function() {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            form: '=',
            max: '=',
            model: '=',
            modelName: '=',
            viewName: '=',
        },
        template: `
            <div class="row">
              <div class="col-sm-3">
                <input data-string-to-number="integer" data-ng-model="model[field]" data-min="0" data-max="max" class="form-control" style="text-align: right" data-lpignore="true"/>
              </div>
              <button type="button" class="btn btn-default" data-ng-click="setSeedRandom()" title="generate random seed"><span class="glyphicon glyphicon-random"></span></button>
              <button type="button" class="btn btn-default" data-ng-click="setSeedTime()" title="use current time"><span class="glyphicon glyphicon-time"></span></button>
            </div>
        `,
        controller: function($scope) {

            $scope.setSeedRandom = () => {
                $scope.model[$scope.field] = Math.floor(Math.random() * $scope.max - 1);
            };

            $scope.setSeedTime = () => {
                $scope.model[$scope.field] = (new Date()).getTime() % $scope.max;
            };
        },
    };
});

SIREPO.app.directive('listSearch', function(panelState, utilities) {
    const searchClass = 'list-search-autocomplete';

    return {
        restrict: 'A',
        scope: {
            list: '=listSearch',
            onSelect: '&',
            placeholderText: '@',
        },
        template: `
            <div class="input-group input-group-sm">
              <span class="input-group-addon"><span class="glyphicon glyphicon-search"></span></span>
              <input class="${searchClass} form-control" placeholder="{{ placeholderText }}" />
            </div>
       `,
        controller: function($scope, $element) {
            panelState.waitForUI(() => {
                utilities.buildSearch($scope, $element, searchClass);
            });
        },
    };
});


SIREPO.app.directive('srTooltip', function(appState, mathRendering, utilities) {
    return {
        restrict: 'A',
        scope: {
            'tooltip': '@srTooltip',
            'placement': '@',
        },
        template: `
            <span data-ng-show="hasTooltip()" class="glyphicon glyphicon-info-sign sr-info-pointer"></span>
        `,
        controller: function($scope, $element) {
            let tooltipLinked = false;

            function linkTooltip() {
                $($element).find('.sr-info-pointer').tooltip({
                    title: function() {
                        var res = $scope.tooltip;
                        res = res.replace('\n', '<br>');
                        // evaluate angular text first if {{ }} is present
                        if (/\{\{.*?\}\}/.test(res)) {
                            $scope.appState = appState;
                            res = utilities.interpolateString(res, $scope);
                        }
                        if (mathRendering.textContainsMath(res)) {
                            return mathRendering.mathAsHTML(res);
                        }
                        return res;
                    },
                    html: true,
                    placement: $scope.placement || 'bottom',
                    container: 'body',
                });
                $scope.$on('$destroy', function() {
                    $($element).find('.sr-info-pointer').tooltip('destroy');
                });
            }

            $scope.hasTooltip = () => {
                if ($scope.tooltip) {
                    if (! tooltipLinked) {
                        tooltipLinked = true;
                        linkTooltip();
                    }
                    return true;
                }
                return false;
            };
        },
    };
});

SIREPO.app.directive('labelWithTooltip', function(appState, mathRendering, $interpolate) {
    return {
        restrict: 'A',
        scope: {
            'label': '@',
            'tooltip': '@',
        },
        template: `
            <label><span data-text-with-math="label" data-is-dynamic="isDynamic()"></span>&nbsp;<span data-sr-tooltip="{{ tooltip }}"></span></label>
        `,
        controller: function($scope) {
            $scope.isDynamic = () => ! ! $scope.label.match(/{{\s*.+\s*}}/);
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
            customInfo: '=',
            labelSize: '@',
            fieldSize: '@',
            form: '=',
            viewName: '=',
        },
        template: `
            <div data-ng-class="utilities.modelFieldID(modelName, field)">
            <div data-ng-show="showLabel" data-label-with-tooltip="" class="control-label" data-ng-class="labelClass" data-label="{{ info[0] }}" data-tooltip="{{ info[3] }}"></div>
            <div data-ng-switch="info[1]">
              <div data-ng-switch-when="Integer" data-ng-class="fieldClass">
                <input data-string-to-number="integer" data-ng-model="model[field]" data-min="info[4]" data-max="info[5]" class="form-control" style="text-align: right" data-lpignore="true" required />
                <div class="sr-input-warning"></div>
              </div>
              <div data-ng-switch-when="Float" data-ng-class="fieldClass">
                <input data-string-to-number="" data-ng-model="model[field]" data-min="info[4]" data-max="info[5]" class="form-control" style="text-align: right" data-lpignore="true" required />
                <div class="sr-input-warning"></div>
              </div>
              <div data-ng-switch-when="OptionalString" data-ng-class="fieldClass">
                <input data-ng-model="model[field]" class="form-control" data-lpignore="true" />
              </div>
              <div data-ng-switch-when="OptionalStringUpper" data-ng-class="fieldClass">
                <input data-ng-model="model[field]" class="form-control" ng-change="model[field] = (model[field] | uppercase)" data-lpignore="true" />
              </div>
              <div data-ng-switch-when="String" data-ng-class="fieldClass">
                <input data-ng-model="model[field]" class="form-control" data-lpignore="true" required />
              </div>
              <div data-ng-switch-when="ValidatedString" data-ng-class="fieldClass">
                <input data-validated-string="" data-field-validator-name=" utilities.modelFieldID(modelName, field)" data-ng-model="model[field]" class="form-control" data-lpignore="true" required />
                <div class="sr-input-warning" data-ng-show="! form.$valid">{{ getWarningText() }}</div>
              </div>
              <div data-ng-switch-when="SafePath" data-ng-class="fieldClass">
                <input data-safe-path="" data-ng-model="model[field]" class="form-control" data-lpignore="true" required />
                <div class="sr-input-warning" data-ng-show="showWarning">{{warningText}}</div>
              </div>
              <div data-ng-switch-when="SimulationName" data-ng-class="fieldClass">
                <input data-safe-path="" data-ng-model="model[field]" class="form-control" required data-ng-readonly="model['isExample']" data-lpignore="true" />
                <div class="sr-input-warning" data-ng-show="showWarning">{{warningText}}</div>
              </div>
              <div data-ng-switch-when="InputFile" class="col-sm-7">
                <div data-file-field="field" data-form="form" data-model="model" data-model-name="modelName"  data-selection-required="info[4]" data-empty-selection-text="No File Selected"></div>
              </div>
              <div data-ng-switch-when="Bool" class="col-sm-offset-5 col-sm-7">
                  <label><input type="checkbox" data-ng-model="model[field]"> {{ info[0] }}</label>
              </div>
              <div data-ng-switch-when="Boolean" data-ng-class="fieldClass">
                <input class="sr-bs-toggle" data-ng-open="fieldDelegate.refreshChecked()" data-ng-model="model[field]" data-bootstrap-toggle="" data-model="model" data-field="field" data-field-delegate="fieldDelegate" data-info="info" type="checkbox">
              </div>
              <div data-ng-switch-when="Color" data-ng-class="fieldClass">
                <input data-ng-if="model" type="color" data-ng-model="model[field]" class="sr-color-button">
              </div>
              <div data-ng-switch-when="ColorMap" class="col-sm-7">
                <div data-color-map-menu="" class="dropdown"></div>
              </div>
              <div data-ng-switch-when="Text" data-ng-class="fieldClass">
                <div data-collapsable-notes="" data-model="model" data-field="field" ></div>
              </div>
              <div data-ng-switch-when="UserFolder" data-ng-class="fieldClass">
                <div data-user-folder-list="" data-model="model" data-field="field"></div>
              </div>
              <div data-ng-switch-when="OptFloat" data-ng-class="fieldClass">
                <div data-optimize-float="" data-model="model" data-model-name="modelName" data-field="field" data-min="info[4]" data-max="info[5]" ></div>
              </div>
              <div data-ng-switch-when="Range" data-ng-class="fieldClass">
                  <div data-range-slider="" data-model="model" data-model-name="modelName" data-field="field" data-field-delegate="fieldDelegate"></div>
              </div>
              <div data-ng-switch-when="ValueList" data-ng-class="fieldClass">
                <div class="form-control-static" data-ng-if="model.valueList[field].length == 1">{{ model.valueList[field][0] }}</div>
                <select data-ng-if="model.valueList[field].length != 1" class="form-control" data-ng-model="model[field]" data-ng-options="item as item for item in model.valueList[field]"></select>
              </div>
              <div data-ng-switch-when="ModelArray" class="col-sm-12">
                <div data-model-array="" data-model-name="modelName" data-model="model" data-field="field"></div>
              </div>
              <div data-ng-switch-when="DateTimePicker" class="col-sm-5">
                <div data-date-time-picker="" data-model="model" data-field="field"></div>
              </div>
              <div data-ng-switch-when="PresetTimePicker" class="col-sm-7">
                <div class="text-right" data-preset-time-picker="" data-model="model" data-model-name="modelName"></div>
              </div>
              <div data-ng-switch-when="OptionalFloat" data-ng-class="fieldClass">
                <input data-string-to-number="" data-ng-model="model[field]"
                  data-min="info[4]" data-max="info[5]" class="form-control"
                  style="text-align: right" data-lpignore="true" />
              </div>
              ${SIREPO.appFieldEditors}
              <div data-ng-switch-default data-ng-class="fieldClass">
                <div data-ng-if="wantEnumButtons" class="btn-group">
                  <button type="button" class="btn sr-enum-button" data-ng-repeat="item in enum[info[1]]" data-ng-click="model[field] = item[0]" data-ng-class="{'active btn-primary': isSelectedValue(item[0]), 'btn-default': ! isSelectedValue(item[0])}">{{ item[1] }}</button>
                </div>
                <select data-ng-if="! wantEnumButtons" number-to-string class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in enum[info[1]]"></select>
                <div class="sr-input-warning"></div>
              </div>
            </div>
            </div>
        `,
        controller: function($scope, $element) {
            $scope.appState = appState;
            $scope.utilities = utilities;
            $scope.UTILS = SIREPO.UTILS;
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
                if ($scope.info[1] == "Bool") {
                    return false;
                }
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
            $scope.info = $scope.customInfo || appState.modelInfo($scope.modelName)[$scope.field];
            if (! $scope.info) {
                throw new Error('invalid model field: ' + $scope.modelName + '.' + $scope.field);
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

            // the viewLogic element is a child of advancedEditorPane, which is a parent of this field.
            // this gets the controller so the field's scope can use it
            $scope.viewLogic = angular.element($($element).closest('div[data-advanced-editor-pane]').find(
                `div[${utilities.viewLogicName($scope.viewName)}]`
            ).eq(0)).controller(`${$scope.viewName}View`);

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

SIREPO.app.directive('loadingSpinner', function() {
    return {
        restrict: 'A',
        scope: {
            sentinel: '<',
        },
        transclude: true,
        template: `
            <div data-ng-if="!sentinel" class="sr-loading-spinner">
                <img src="/static/img/sirepo_animated.gif" />
            </div>
            <ng-transclude data-ng-if="sentinel"></ng-transclude>
        `,
    };
});

SIREPO.app.directive('logoutMenu', function(authState, authService, requestSender) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <li data-ng-if="::authState.isGuestUser"><a data-ng-href="{{ ::authService.loginUrl }}"><span
                    class="glyphicon glyphicon-alert sr-small-icon"></span> Save Your Work!</a></li>
            <li data-ng-if="::! authState.isGuestUser" class="sr-logged-in-menu dropdown">
              <a href class="dropdown-toggle" data-toggle="dropdown">
                <img data-ng-if="::authState.avatarUrl" data-ng-src="{{:: authState.avatarUrl }}">
                <span data-ng-if="::! authState.avatarUrl" class="glyphicon glyphicon-user"></span>
                <span class="caret"></span>
              </a>
              <ul class="dropdown-menu">
                <li class="dropdown-header"><strong>{{ ::authState.displayName }}</strong></li>
                <li class="dropdown-header">{{ authState.paymentPlanName() }}</li>
                <li class="dropdown-header" data-ng-if="::authState.userName">{{ ::authState.userName }}</li>
                <li data-ng-if="isAdm()"><a data-ng-href="{{ getUrl('admJobs') }}">Admin Jobs</a></li>
                <li data-ng-if="isAdm()"><a data-ng-href="{{ getUrl('admUsers') }}">Admin Users</a></li>
                <li><a data-ng-click="showJobsList()" style="cursor:pointer">Jobs</a></li>
                <li><a data-ng-href="{{ ::authService.logoutUrl }}">Sign out</a></li>
              </ul>
            </li>
        `,
        controller: function($scope, panelState) {
            $scope.authState = authState;
            $scope.authService = authService;

            $scope.getUrl = (route) => {
                return requestSender.formatUrlLocal(route);
            };

            $scope.isAdm = () => authState.hasRole('adm');

            $scope.showJobsList = () => {
                $('#' + panelState.modalId('jobsListModal')).modal('show');
            };
        },
    };
});

SIREPO.app.directive('fileField', function(errorService, panelState, requestSender) {
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
        template: `
          <div class="btn-group" role="group">
            <button type="button" class="btn btn-default dropdown-toggle" data-ng-class="{'btn-invalid': selectionRequired && ! hasValidFileSelected()}" data-toggle="dropdown">{{ model[fileField] || emptySelectionText }} <span class="caret"></span></button>
            <ul class="dropdown-menu">
              <li data-ng-repeat="item in itemList()" class="sr-model-list-item"><a href data-ng-click="selectItem(item)">{{ item }}<span data-ng-show="! isSelectedItem(item)" data-ng-click="confirmDeleteItem(item, $event)" class="glyphicon glyphicon-remove"></span></a></li>
              <li class="divider"></li>
              <li data-ng-hide="selectionRequired"><a href data-ng-click="selectItem('')">{{ emptySelectionText }}</a></li>
              <li data-ng-hide="selectionRequired" class="divider"></li>
              <li><a href data-ng-click="showFileUpload()"><span class="glyphicon glyphicon-plus"></span> New</a></li>
            </ul>
          </div>
          <div data-ng-if="hasValidFileSelected()" class="btn-group" role="group">
            <div class="pull-left" data-ng-transclude=""></div>
            <div class="pull-left"><a data-ng-href="{{ downloadLibFileUrl() }}" type="button" title="Download" class="btn btn-default"><span class="glyphicon glyphicon-cloud-download"></a></div>
          </div>
          <div class="sr-input-warning" data-ng-show="selectionRequired && ! hasValidFileSelected()">Select a file</div>
        `,
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
                        'deleteLibFile',
                        function(data) {
                            $scope.isDeletingFile = false;
                            if (data.error) {
                                $scope.deleteFileError = data.error + "\n\n"
                                    + data.fileList.join("\n");
                            }
                            else {
                                var list = requestSender.getListFilesData($scope.fileType);
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

            $scope.downloadLibFileUrl = function() {
                if ($scope.model) {
                    return requestSender.formatUrl('downloadLibFile', {
                        simulation_id: 'unused',
                        simulation_type: SIREPO.APP_SCHEMA.simulationType,
                        filename: SIREPO.APP_NAME === 'srw'
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
                if ($scope.fileType && $scope.model && $scope.model[$scope.fileField]) {
                    // assume the file is valid if selected
                    if ($scope.form) {
                        $scope.form.$valid = true;
                    }
                    return true;
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
                if (requestSender.getListFilesData($scope.fileType)) {
                    return requestSender.getListFilesData($scope.fileType);
                }
                requestSender.loadListFiles(
                    $scope.fileType,
                    {
                        simulationType: SIREPO.APP_SCHEMA.simulationType,
                        fileType: $scope.fileType,
                        simulationId: 'unused',
                    },
                    sortList,
                );
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
        template: `
            <div class="sr-column-editor">
              <div class="row">
                <div class="col-sm-{{ ::head.size || 3 }}" data-ng-repeat="head in ::headings">
                  <div class="lead text-center">{{ ::head.text }}</div>
                </div>
              </div>
              <div class="form-group form-group-sm" data-ng-repeat="row in ::rows">
                <div data-ng-repeat="col in ::row">
                  <div data-ng-if="::! col.field" class="col-sm-{{ ::col.size || 3 }} control-label">
                    <div data-label-with-tooltip="" data-label="{{ ::col.label }}" data-tooltip="{{ ::col.tooltip }}"></div>
                  </div>
                  <div data-ng-if="::col.field" class="col-sm-{{ ::col.size || 3 }}"><div class="row">
                    <div data-model-field="::col.field" data-label-size="0" data-field-size="12" data-model-name="modelName" data-model-data="modelData"></div>
                  </div></div>
                </div>
              </div>
              <div>&nbsp;</div>
            </div>
        `,
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
        template: `
            <div class="modal fade" id="sr-fileUpload{{ fileType }}-editor" tabindex="-1" role="dialog" data-backdrop="static">
              <div class="modal-dialog modal-lg">
                <div class="modal-content">
                  <div class="modal-header bg-info">
                    <button type="button" class="close" data-dismiss="modal"><span data-ng-if="! isUploading">&times;</span></button>
                    <span class="lead modal-title text-info">{{ dialogTitle }}</span>
                  </div>
                  <div class="modal-body">
                    <div class="container-fluid">
                      <form>
                        <div class="form-group">
                          <label>Select File</label>
                          <input type="file" data-file-model="inputFile" data-ng-attr-accept="{{ acceptTypes() }}" />
                          <div class="text-warning" style="white-space: pre-line"><strong>{{ fileUploadError }}</strong></div>
                        </div>
                        <div data-ng-if="isUploading" class="col-sm-6 pull-right">Please Wait...</div>
                        <div class="clearfix"></div>
                        <div class="col-sm-6 pull-right">
                          <button data-ng-show="isConfirming" data-ng-click="uploadFile(inputFile)" class="btn btn-warning" data-ng-disabled="isUploading">Replace File</button>
                          <button data-ng-hide="isConfirming" data-ng-click="uploadFile(inputFile)" class="btn btn-primary sr-button-save-cancel" data-ng-disabled="isUploading">Save</button>
                          <button data-dismiss="modal" class="btn btn-default sr-button-save-cancel" data-ng-disabled="isUploading">Cancel</button>
                        </div>
                      </form>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
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
                        'uploadLibFile',
                        {
                            simulation_id: appState.models.simulation.simulationId,
                            simulation_type: SIREPO.APP_SCHEMA.simulationType,
                            file_type: $scope.fileType,
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
                            var list = requestSender.getListFilesData($scope.fileType);
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

SIREPO.app.directive('headerTooltip', function() {
    return {
        restrict: 'A',
        scope: {
            tipText: '=headerTooltip',
        },
        template: `
            <span data-ng-class="className()"></span>
        `,
        controller: function link($scope, $element) {
            $scope.className = function() {
                return 'glyphicon sr-info-pointer glyphicon-' + ({
                    canceled: 'ban-circle',
                    completed: 'ok completed-icon',
                    error: 'remove error-icon',
                    loading: 'refresh running-icon',
                    missing: 'question-sign',
                    none: 'minus',
                    pending: 'hourglass',
                    running: 'refresh running-icon'
                }[$scope.tipText] || 'info-sign');
            };

            $scope.$on('$destroy', function() {
                $($element).tooltip('destroy');
            });

            $scope.$watch('tipText', () => {
                $($element).tooltip().attr('data-original-title', $scope.tipText);
            });

            $($element).tooltip({
                title: $scope.tipText,
                html: true,
                placement: 'bottom',
            });
        },
    };
});

SIREPO.app.directive('helpButton', function(requestSender) {
    var HELP_WIKI_ROOT = 'https://github.com/radiasoft/sirepo/wiki/' + SIREPO.APP_NAME.toUpperCase() + '-';
    return {
        restrict: 'A',
        scope: {
            helpTopic: '@helpButton',
        },
        template: `
            <button type="button" data-ng-if="::showHelp()" class="close sr-help-icon" title="{{ ::helpTopic }} Help" data-ng-click="openHelp()"><span class="glyphicon glyphicon-question-sign"></span></button>
        `,
        controller: function($scope) {
            $scope.openHelp = function() {
                requestSender.newWindow(
                    HELP_WIKI_ROOT + $scope.helpTopic.replace(/\s+/, '-'),
                );
            };
            $scope.showHelp = function() {
                if ('SHOW_HELP_BUTTONS' in SIREPO) {
                    return SIREPO.SHOW_HELP_BUTTONS;
                }
                return false;
            };
        },
    };
});

SIREPO.app.directive('helpLink', function(appState) {
    return {
        restrict: 'A',
        scope: {
            constantURL: '@helpLink',
            icon: '@',
            title: '@',
        },
        template: `
            <a data-ng-if="::url" data-ng-href="{{ ::url }}" target="_blank">
              <span data-ng-class="::glyphClass"></span>
              ${SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_SCHEMA.simulationType].shortName}
               {{ ::title }}
            </a>
        `,
        controller: function($scope) {
            $scope.glyphClass = 'glyphicon glyphicon-' + $scope.icon;
            $scope.url = SIREPO.APP_SCHEMA.constants[$scope.constantURL];
        },
    };
});

SIREPO.app.directive('videoButton', function(appState, requestSender) {
    return {
        restrict: 'A',
        scope: {
            viewName: '@videoButton',
        },
        template: `
            <div data-ng-if="showLink"><button type="button" class="close sr-help-icon" data-ng-click="openVideo()" title="{{ ::tooltip }}"><span class="glyphicon glyphicon-film"></span></button></div>
        `,
        controller: function($scope) {
            var viewInfo = appState.viewInfo($scope.viewName);
            $scope.showLink = SIREPO.APP_SCHEMA.feature_config.show_video_links;
            $scope.tooltip = viewInfo.title + ' Help Video';
            $scope.openVideo = function() {
                requestSender.newWindow(viewInfo.helpVideoURL);
            };
        },
    };
});

SIREPO.app.directive('downloadCsvLink', function(appState, panelState) {
    return {
        restrict: 'A',
        template: `
            <a href data-ng-if=":: plotType() == '3d'" data-ng-click="exportCSV('x')">CSV - Horizontal Cut</a>
            <a href data-ng-if=":: plotType() == '3d'" data-ng-click="exportCSV('y')">CSV - Vertical Cut</a>
            <a href data-ng-if=":: plotType() == '3d'" data-ng-click="exportCSV('full')">CSV - Full Plot</a>
            <a href data-ng-if=":: plotType() == 'parameter'" data-ng-click="exportCSV('')">Download CSV</a>
        `,
        controller: function($scope) {

            function findReportPanelScope() {
                var s = $scope.$parent;
                while (s && ! s.reportPanel) {
                    s = s.$parent;
                }
                return s;
            }

            $scope.exportCSV = function(axis) {
                findReportPanelScope().$broadcast(
                    SIREPO.PLOTTING_CSV_EVENT,
                    axis);
            };

            $scope.plotType = function() {
                const p = panelState.findParentAttribute($scope, 'reportPanel');
                if (p == '3d') {
                    return '3d';
                } else if (p.includes('parameter')) {
                    return 'parameter';
                }
            };
        },
    };
});

SIREPO.app.directive('modalDialog', function(appState, panelState) {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            viewName: '@',
            //TODO(pjm): remove parentController everywhere
            parentController: '=',
            modalTitle: '=?',
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
        },
        template: `
            <div class="modal fade" id="{{ editorId }}" tabindex="-1" role="dialog">
              <div class="modal-dialog modal-lg">
                <div class="modal-content">
                  <div class="modal-header bg-info">
                    <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <div data-help-button="{{ helpTopic }}"></div>
                    <div data-ng-if="::hasHelpVideo" data-video-button="{{ viewName }}"></div>
                    <span class="lead modal-title text-info">{{ modalTitle }}</span>
                  </div>
                  <div class="modal-body">
                    <div class="container-fluid">
                      <div class="row">
                        <div data-ng-transclude=""></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
            function hideModal(e, name) {
                if (name == $scope.modelKey && $scope.editorId) {
                    $('#' + $scope.editorId).modal('hide');
                }
            }
            var viewInfo = appState.viewInfo($scope.viewName);
            if (! viewInfo) {
                throw new Error('missing view in schema: ' + $scope.viewName);
            }
            $scope.hasHelpVideo = viewInfo.helpVideoURL;
            $scope.helpTopic = viewInfo.title;
            // A view view may refer to a model by name, ex. SRW simulationGrid view
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
            $scope.$on('modelChanged', hideModal);
            $scope.$on('cancelChanges', hideModal);
        },
        //TODO(pjm): move link items to controller?
        link: function(scope, element) {
            $(element).on('show.bs.modal', () => {
                $(element).addClass('sr-modal-shown');
            });
            $(element).on('shown.bs.modal', function() {
                $('#' + scope.editorId + ' .form-control').first().select();
                if (scope.parentController && scope.parentController.handleModalShown) {
                    panelState.waitForUI(function() {
                        scope.parentController.handleModalShown(scope.modelName, scope.modelKey);
                    });
                }
            });
            $(element).on('hidden.bs.modal', function(o) {
                $(element).removeClass('sr-modal-shown');
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
        template: `
            <div data-modal-dialog="" data-view-name="{{ viewName }}" data-parent-controller="parentController" data-modal-title="modalTitle" data-model-data="modelData">
              <div data-advanced-editor-pane="" data-view-name="viewName" data-want-buttons="true" data-model-data="modelData" data-parent-controller="parentController"></div>
            </div>
        `,
    };
});

SIREPO.app.directive('modelField', function(appState) {
    return {
        restrict: 'A',
        scope: {
            field: '=modelField',
            modelName: '=',
            customInfo: '=?',
            labelSize: '@',
            fieldSize: '@',
            // optional, allow caller to provide path for modelKey and model data
            modelData: '=',
            form: '=',
            viewName: '=',
        },
        template: `
            <div data-field-editor="fieldName()" data-form="form" data-model-name="modelNameForField()" data-model="modelForField()" data-custom-info="customInfo" data-label-size="{{ labelSize }}" data-field-size="{{ fieldSize }}" data-view-name="viewName"></div>
        `,
        controller: function($scope) {
            let modelName = $scope.modelName;
            let field = $scope.field;
            let modelField = appState.parseModelField(field);

            if (modelField) {
                [modelName, field] = modelField;
            }

            // if this is a compound field (<field 1>.<field 2>), change the model info to reflect that
            const m = appState.parseModelField(field);
            if (m) {
                modelField = m;
                field = modelField[1];
                const t = SIREPO.APP_SCHEMA.model[$scope.modelName][modelField[0]][SIREPO.INFO_INDEX_TYPE];
                modelName = t.split('.')[1];
                $scope.customInfo = appState.modelInfo(modelName)[field];
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

SIREPO.app.directive('panelLayout', function(appState, utilities, $window) {
    return {
        restrict: 'A',
        transclude: true,
        template: `
            <div class="row">
              <div class="sr-panel-layout col-md-6 col-xl-4"></div>
              <div class="sr-panel-layout col-md-6 col-xl-4"></div>
              <div class="sr-panel-layout col-md-6 col-xl-4"></div>
              <div data-ng-transclude=""></div>
            </div>
        `,
        scope: {},
        controller: function($scope, $element) {
            var columnCount = 0;
            var panelItems = null;

            function arrangeColumns() {
                var count = 0;
                var cols = $($element).find('.sr-panel-layout');
                if (! panelItems) {
                    panelItems = $($element).find('.sr-panel-item');
                }
                panelItems.each(function(idx, item) {
                    $(cols[count]).append(item);
                    count = (count + 1) % columnCount;
                });
            }

            function windowResize() {
                if (utilities.isFullscreen()) {
                    return;
                }
                var count = 1;
                //TODO(pjm): size from bootstrap css constants
                if ($window.matchMedia('(min-width: 1600px)').matches) {
                    count = 3;
                }
                else if ($window.matchMedia('(min-width: 992px)').matches) {
                    count = 2;
                }
                if (count != columnCount) {
                    columnCount = count;
                    arrangeColumns();
                }
            }

            $scope.$on('sr-window-resize', windowResize);

            appState.whenModelsLoaded($scope, windowResize);
        },
    };
});

SIREPO.app.directive('pendingLinkToSimulations', function() {
    return {
        restrict: 'A',
        scope: {
            simState: '<',
        },
        template: `
            <div data-ng-show="simState.isStatePending()">
              <a data-ng-click="showJobsList()" style="cursor:pointer">
                <span class="glyphicon glyphicon-hourglass"></span> {{ simState.getQueueState() }} {{ simState.dots }}
              </a>
            </div>
        `,
        controller: function($scope, panelState) {
            $scope.showJobsList = function() {
                $('#' + panelState.modalId('jobsListModal')).modal('show');
            };
        },
    };
});


SIREPO.app.directive('plansLink', function() {
    return {
        restrict: 'A',
        scope: {
            linkText: '@',
        },
        template: '<a data-ng-href="{{ plansUrl }}">{{ linkText }}</a>',
        controller: function($scope) {
            $scope.plansUrl = SIREPO.APP_SCHEMA.constants.plansUrl;
        },
    };
});

SIREPO.app.directive('safePath', function() {

    // keep in sync with sirepo.srschem.py _NAME_ILLEGALS
    var unsafePathChars = '\\/|&:+?\'*"<>'.split('');
    var unsafePathWarn = ' must not include: ' +
        unsafePathChars.join(' ');
    var unsafePathRegexp = new RegExp('[\\' + unsafePathChars.join('\\') + ']');

    return {
        restrict: 'A',
        require: 'ngModel',
        link: function(scope, element, attrs, ngModel) {
            scope.showWarning = false;
            scope.warningText = '';

            function setWarningText(text) {
                scope.warningText = (scope.info ? scope.info[0] : 'Value') + text;
            }

            ngModel.$parsers.push(function (v) {
                scope.showWarning = unsafePathRegexp.test(v);
                if (scope.showWarning) {
                    setWarningText(unsafePathWarn);
                }
                else {
                    scope.showWarning = /^\.|\.$/.test(v);
                    if (scope.showWarning) {
                        setWarningText(' must not start or end with a "."');
                    }
                }
                ngModel.$setValidity('size', ! scope.showWarning);
                return v;
            });

            ngModel.$formatters.push(function (v) {
                scope.showWarning = false;
                return v;
            });
        },
    };
});

SIREPO.app.directive('showLoadingAndError', function(appState, panelState) {
    return {
        transclude: true,
        scope: {
            modelKey: '@',
        },
        template: `
            <div data-ng-class="{'sr-panel-loading': panelState.isLoading(modelKey), 'sr-panel-error': panelState.getError(modelKey), 'sr-panel-running': panelState.isRunning(modelKey), 'sr-panel-waiting': panelState.isWaiting(modelKey), 'has-transclude': hasTransclude()}" class="panel-body" data-ng-hide="panelState.isHidden(modelKey)" data-ng-if="preserveMinimized || ! panelState.isHidden(modelKey)">
              <div data-ng-show="panelState.isWaiting(modelKey)" class="lead sr-panel-wait"><span class="glyphicon glyphicon-hourglass"></span> Pending Request</div>
              <div data-ng-show="panelState.isLoading(modelKey)" class="lead sr-panel-wait"><span class="glyphicon glyphicon-hourglass"></span> {{ panelState.getStatusText(modelKey) }}</div>
              <div data-ng-show="panelState.getError(modelKey)" class="lead sr-panel-wait"><span class="glyphicon glyphicon-exclamation-sign"></span> {{ panelState.getError(modelKey) }}</div>
              <div data-ng-transclude=""></div>
            </div>
        `,
        controller: function($scope, $element) {
            const v = appState.viewInfo($scope.modelKey);
            $scope.preserveMinimized = v && v.is3d ? false: true;
            $scope.panelState = panelState;
            $scope.hasTransclude = function() {
                var el = $($element).find('div[data-ng-transclude] > div[data-ng-transclude]:not(:empty)');
                return el.children().first().length > 0;
            };
        },
    };
});

SIREPO.app.directive('simplePanel', function(appState, panelState) {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            modelName: '@simplePanel',
            modelKey: '=',
            isReport: '@',
        },
        template: `
            <div class="panel panel-info">
              <div class="panel-heading clearfix" data-panel-heading="{{ heading }}" data-model-key="modelKey || modelName" data-is-report="{{ isReport }}"></div>
                <div class="panel-body" data-ng-hide="isHidden()">
                  <div data-ng-transclude=""></div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
            var viewInfo = appState.viewInfo($scope.modelName);
            $scope.heading = viewInfo.title;
            $scope.isHidden = function() {
                return panelState.isHidden($scope.modelKey || $scope.modelName);
            };
        },
    };
});

SIREPO.app.directive('simStateProgressBar', function(appState) {
    return {
        restrict: 'A',
        scope: {
            simState: '<',
        },
        template: `
            <div class="progress">
              <div class="progress-bar {{ class() }}" role="progressbar" aria-valuenow="{{ percentComplete() }}" aria-valuemin="0" aria-valuemax="100" data-ng-attr-style="width: {{ percentComplete() }}%"></div>
            </div>
        `,
        controller: function($scope) {
            $scope.class = () => {
                if (! $scope.simState) {
                    return 'progress-bar-striped active';
                }
                if ($scope.simState.isInitializing()) {
                    return 'progress-bar-striped active';
                }
                return '';
            };

            $scope.percentComplete = () => {
                if ($scope.simState) {
                    return $scope.simState.getPercentComplete();
                }
                return '100';
            };
        },
    };
});

SIREPO.app.directive('simulationStoppedStatus', function(authState) {
    return {
        restrict: 'A',
        scope: {
            simState: '=simulationStoppedStatus',
        },
        template: `
            <div class="col-sm-12" ng-bind-html="message()"><br><br></div>
        `,
        controller: function(appState, stringsService, $sce, $scope) {

            $scope.message = function() {
                if ($scope.simState.isStatePurged()) {
                    return $sce.trustAsHtml([
                        `<div>Data purged on ${appState.formatDate($scope.simState.getDbUpdateTime())}.</div>`,
                    ].join(''));
                }

                const s = SIREPO.APP_SCHEMA.strings;
                const f = $scope.simState.getFrameCount();
                let c = f > 0 ? s.completionState : '';
                if ($scope.simState.controller.simCompletionState) {
                    c = $scope.simState.controller.simCompletionState(c);
                }
                const a = {
                    frameCount: f,
                    typeOfSimulation: stringsService.typeOfSimulation($scope.simState.model),
                    state: $scope.simState.stateAsText()
                };
                return  $sce.trustAsHtml(
                    '<div>' +
                    stringsService.formatTemplate(s.simulationState + c, a) +
                    '</div>'
                );
            };
        },
    };
});

SIREPO.app.directive('textWithMath', function(appState, mathRendering, utilities, $sce) {
    return {
        restrict: 'A',
        scope: {
            'isDynamic': '<',
            'textWithMath': '<',
        },
        // no newlines within template in case the directive is encased in a "pre" layout
        template: `<span data-ng-if="! isDynamic" data-ng-bind-html="::getHTML()"></span><span data-ng-if="isDynamic" data-ng-bind-html="getHTML()"></span>`,
        controller: function($scope) {
            $scope.appState = appState;
            $scope.getHTML = function() {
                if (! $scope.textWithMath) {
                    return '';
                }
                return $sce.trustAsHtml(mathRendering.mathAsHTML(
                    utilities.interpolateString($scope.textWithMath, $scope)
                ));
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
                return validationService.getMessageForNGModel(scope.fieldValidatorName, modelValidatorName, ngModel);
            };

            function reloadValidator() {
                validationService.reloadValidatorForNGModel(scope.fieldValidatorName, modelValidatorName, ngModel);
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

SIREPO.app.directive('viewLogModal', function() {
    return {
        restrict: 'A',
        scope: {
            logIsLoading: '<',
            logHtml: '<',
            logPath: '<',
            modalId: '<',
            downloadLog: '<'
        },
        template: `
            <div class="modal fade" id="{{ modalId }}" tabindex="-1" role="dialog">
              <div class="modal-dialog modal-lg">
                <div class="modal-content">
                  <div class="modal-header bg-warning">
                    <span class="lead modal-title text-info">Log</span>
                    <div class="sr-panel-options pull-right">
                      <a data-ng-if="downloadLog" data-ng-href="{{ downloadLog() }}" target="_blank">
                        <span class="sr-panel-heading glyphicon glyphicon-cloud-download"></span>
                      </a>
                      <button type="button" class="close" data-dismiss="modal" style="margin-left: 10px">
                        <span>&times;</span>
                      </button>
                    </div>
                  </div>
                  <div class="modal-body" scroll-to-bottom="logHtml"  style="max-height: 80vh; overflow-y:auto;">
                    <div data-ng-if="logIsLoading">Loading...</div>
                    <div data-ng-if="! logIsLoading">
                        <div data-ng-if="logPath">{{ logPath }}</div>
                        <div ng-bind-html="logHtml"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
        },
    };
});


SIREPO.app.directive('colorMapMenu', function(appState, plotting) {

    return {
        restrict: 'A',
        template: `
            <button type="button" class="btn btn-primary dropdown-toggle" type="button" data-toggle="dropdown"><span class="sr-color-map-indicator" data-ng-style="itemStyle[model[field]]"></span> {{ colorMapDescription(model[field]) }} <span class="caret"></span></button>
            <ul class="dropdown-menu sr-button-menu">
                <li data-ng-repeat="item in items" class="sr-button-menu">
                    <button type="button" class="btn btn-block"  data-ng-class="{'sr-button-menu-selected': isSelectedMap(item[0]), 'sr-button-menu-unselected': ! isSelectedMap(item[0])}" data-ng-click="setColorMap(item[0])">
                        <span class="sr-color-map-indicator" data-ng-style="itemStyle[item[0]]"></span> {{item[1]}} <span data-ng-if="isDefaultMap(item[0])" class="glyphicon glyphicon-star-empty"></span><span data-ng-if="isSelectedMap(item[0])" class="glyphicon glyphicon-ok"></span>
                    </button>
                </li>
            </ul>
        `,
        controller: function($scope) {
            var defaultMapName, enumName;

            function init() {
                var info = appState.modelInfo($scope.modelName)[$scope.field];
                if (! info) {
                    throw new Error('invalid model field: ' + $scope.modelName + '.' + $scope.field);
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
        template: `
            <div>
            <a href data-ng-click="toggleNotes()" style="text-decoration: none;">
            <span class="glyphicon" data-ng-class="{'glyphicon-chevron-down': ! showNotes, 'glyphicon-chevron-up': showNotes}" style="font-size:16px;"></span>
             <span data-ng-show="! openNotes() && hasNotes()">...</span>
             <span data-ng-show="! openNotes() && ! hasNotes()" style="font-style: italic; font-size: small">click to enter notes</span>
            </a>
            <textarea data-ng-show="openNotes()" data-ng-model="model[field]" class="form-control" style="resize: vertical; min-height: 2em;"></textarea>
            </div>
        `,
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
        template: `
            <select class="form-control" data-ng-model="model[field]" data-ng-if="! model.isExample" data-ng-options="item for item in fileManager.getUserFolderPaths()"></select>
            <div class="form-control" data-ng-if="model.isExample" readonly>{{ model.folder }}</div>
        `,
        controller: function($scope) {
            $scope.fileManager = fileManager;
        },
    };
});

SIREPO.app.directive('numberList', function(appState, utilities) {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            info: '<',
            model: '<',
            type: '@',
            count: '@',
        },
        template: `
            <div data-ng-repeat="defaultSelection in parseValues() track by $index" style="display: inline-block" >
            <label data-text-with-math="valueLabels[$index] || 'Plane ' + $index" style="margin-right: 1ex"></label>
            <input class="form-control sr-number-list" data-string-to-number="{{ numberType }}" data-ng-model="values[$index]" data-ng-change="didChange()" class="form-control" style="text-align: right;" required />
            </div>
        `,
        controller: function($scope) {
            let lastModel = null;
            $scope.values = null;
            $scope.numberType = $scope.type.toLowerCase();
            $scope.appState = appState;
            //TODO(pjm): share implementation with enumList
            $scope.valueLabels = ($scope.info[4] || '').split(/\s*,\s*/)
                .map(s => utilities.interpolateString(s, $scope));
            $scope.didChange = function() {
                $scope.field = $scope.values.join(', ');
            };
            $scope.parseValues = function() {
                // the model can change - reset the values in that case
                if (lastModel !== $scope.model) {
                    lastModel = $scope.model;
                    $scope.values = null;
                }
                if ($scope.field && ! $scope.values) {
                    $scope.values = $scope.field.split(/\s*,\s*/);
                }
                return $scope.values;
            };
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
        template: `
            <span class="sr-panel-heading">{{ simpleHeading }}</span>
            <div class="sr-panel-options pull-right">
              <a href data-ng-class="{'sr-disabled-link': utilities.isFullscreen()}" data-ng-click="panelState.toggleHidden(modelKey)" data-ng-hide="panelState.isHidden(modelKey) || utilities.isFullscreen()" title="Hide"><span class="sr-panel-heading glyphicon glyphicon-chevron-up"></span></a>
              <a href data-ng-click="panelState.toggleHidden(modelKey)" data-ng-show="panelState.isHidden(modelKey)" title="Show"><span class="sr-panel-heading glyphicon glyphicon-chevron-down"></span></a>
            </div>
            <div class="sr-panel-options pull-right" data-ng-transclude="" ></div>
        `,
        controller: function($scope) {
            $scope.panelState = panelState;
            $scope.utilities = utilities;
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
            viewName: '@',
        },
        template: `
            <div data-simple-heading="{{ panelHeading }}" data-model-key="modelKey">
              <div class="model-panel-heading-buttons"></div>
              <a href data-ng-show="hasEditor" data-ng-click="showEditor()" title="Edit"><span class="sr-panel-heading glyphicon glyphicon-pencil"></span></a>
              ${SIREPO.appPanelHeadingButtons || ''}
              <div data-ng-if="isReport" data-ng-show="hasData()" class="dropdown" style="display: inline-block">
                <a href class="dropdown-toggle" data-toggle="dropdown" title="Download"> <span class="sr-panel-heading glyphicon glyphicon-cloud-download" style="margin-bottom: 0"></span></a>
                <ul class="dropdown-menu dropdown-menu-right">
                  <li class="dropdown-header">Download Report</li>
                  <li><a href data-ng-click="downloadImage(480)">PNG - Small</a></li>
                  <li><a href data-ng-click="downloadImage(720)">PNG - Medium</a></li>
                  <li><a href data-ng-click="downloadImage(1080)">PNG - Large</a></li>
                  <li data-ng-if="::hasDataFile" role="separator" class="divider"></li>
                  <li data-ng-if="::hasDataFile"><a data-ng-href="{{ dataFileURL() }}" target="_blank">{{ dataDownloadTitle }}</a></li>
                  ${SIREPO.appDownloadLinks || ''}
                  <li data-ng-if="::hasDataFile" data-ng-repeat="l in panelDownloadLinks"><a data-ng-href="{{ dataFileURL(l.suffix) }}" target="_blank">{{ l.title }}</a></li>
                </ul>
              </div>
              <a href data-ng-if="::canFullScreen" data-ng-show="isReport && ! panelState.isHidden(modelKey)" data-ng-attr-title="{{ fullscreenIconTitle() }}" data-ng-click="toggleFullscreen()"><span class="sr-panel-heading glyphicon" data-ng-class="{'glyphicon-resize-full': ! utilities.isFullscreen(), 'glyphicon-resize-small': utilities.isFullscreen()}"></span></a>
            </div>
        `,
        controller: function($scope, $element) {
            $scope.panelState = panelState;
            $scope.utilities = utilities;
            let viewKey = $scope.viewName || $scope.modelKey;
            let dl = SIREPO.APP_SCHEMA.constants.dataDownloads || {};
            let df = ((dl._default || [])[0] || {});
            $scope.panelDownloadLinks = dl[viewKey] || [];
            $scope.dataDownloadTitle = df.title  || 'Raw Data File';
            $scope.dataDownloadSuffix = df.suffix  || '';

            // modelKey may not exist in viewInfo, assume it has an editor in that case
            var view = appState.viewInfo(viewKey);
            $scope.hasEditor = view && view.advanced.length === 0 ? false : true;
            $scope.hasDataFile = view && view.hasOwnProperty('hasDataFile') ? view.hasDataFile : true;
            $scope.canFullScreen = view && view.hasOwnProperty('canFullScreen') ? view.canFullScreen : true;

            // used for python export which lives in SIREPO.appDownloadLinks
            $scope.reportTitle = function () {
                return $scope.panelHeading;
            };

            $scope.dataFileURL = function(suffix) {
                if (appState.isLoaded()) {
                    var params = {
                        simulation_id: appState.models.simulation.simulationId,
                        simulation_type: SIREPO.APP_SCHEMA.simulationType,
                        model: $scope.modelKey,
                        frame: appState.isAnimationModelName($scope.modelKey)
                            ? frameCache.getCurrentFrame($scope.modelKey)
                            // any value is fine (ignored)
                            : -1,
                    };
                    if (suffix) {
                        params.suffix = suffix;
                    }
                    return requestSender.formatUrl('downloadRunFile', params);
                }
                return '';
            };

            $scope.downloadImage = function(height) {
                plotToPNG.downloadPNG(
                    $scope.panel,
                    height,
                    panelState.fileNameFromText($scope.panelHeading, 'png'));
            };

            $scope.hasData = function() {
                if (! plotToPNG.hasScreenshotElement($scope.panel)) {
                    return false;
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
                return utilities.isFullscreen() ? 'Exit Full Screen' : 'Full Screen';
            };

            $scope.toggleFullscreen = function() {
                if (utilities.isFullscreen()) {
                    utilities.exitFullscreen();
                } else {
                    utilities.openFullscreen($scope);
                }
            };


        },
        link: function(scope, element) {
            scope.panel = element.next();
            panelState.waitForUI(function() {
                var view = appState.viewInfo(scope.viewName || scope.modelKey);
                if (! view) {
                    var editorId = '#' + panelState.modalId(scope.modelKey);
                    if (! $(editorId).length) {
                        scope.hasEditor = false;
                    }
                }
            });
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
        template: `
            <div data-show-loading-and-error="" data-model-key="{{ modelKey }}">
              <div data-ng-switch="reportContent" class="{{ panelState.getError(modelKey) ? 'sr-hide-report' : '' }}">
                <div data-ng-switch-when="2d" data-plot2d="" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}"></div>
                <div data-ng-switch-when="3d" data-plot3d="" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}"></div>
                <div data-ng-switch-when="heatmap" data-heatmap="" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}"></div>
                <div data-ng-switch-when="particle" data-particle="" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}"></div>
                <div data-ng-switch-when="particle3d" data-particle-3d="" class="sr-plot" data-model-name="{{ modelKey }}"></div>
                <div data-ng-switch-when="parameter" data-parameter-plot="" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}"></div>
                <div data-ng-switch-when="lattice" data-lattice="" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}"></div>
                <div data-ng-switch-when="parameterWithLattice" data-parameter-with-lattice="" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}"></div>
                ${SIREPO.appReportTypes || ''}
              </div>
              <div data-ng-transclude=""></div>
            </div>
        `,
        controller: function($scope, $element) {
            $scope.panelState = panelState;
        },
    };
});

SIREPO.app.directive('reportPanel', function(appState, panelState, utilities) {
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
            viewName: '@',
        },
        template: `
            <div class="panel panel-info" data-ng-style="reportStyle">
              <div class="panel-heading clearfix" data-panel-heading="{{ reportTitle() }}" data-model-key="modelKey" data-is-report="1" data-view-name="{{ viewName }}"></div>
              <div data-report-content="{{ reportPanel }}" data-model-key="{{ modelKey }}"><div data-ng-transclude=""></div></div>
              <div data-ng-if="notes()"><span class="pull-right sr-notes" data-sr-tooltip="{{ notes() }}" data-placement="top"></span><div class="clearfix"></div></div>
        `,
        controller: function($scope) {
            $scope.reportStyle = {};

            $scope.$on('sr-full-screen', () => {
                $scope.reportStyle.position = 'fixed';
                $scope.reportStyle['z-index'] = 1000;
                $scope.reportStyle.left = 0;
                $scope.reportStyle.top = 0;
                $scope.reportStyle.width = '100%';
                $scope.reportStyle.height = '100%';
                $scope.reportStyle.overflow = 'hidden';
                panelState.waitForUI(panelState.triggerWindowResize);
            });


            $scope.$on('sr-close-full-screen', () => {
                $scope.reportStyle = {};
                panelState.waitForUI(panelState.triggerWindowResize);
            });



            if ($scope.modelName && $scope.modelName.includes('{') ) {
                throw new Error('Expected simple name for modelName, got: ' + $scope.modelName);
            }
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

SIREPO.app.directive('scrollToBottom', function ($timeout) {
    return {
	scope: {
	    scrollToBottom: "="
	},
	link: function (scope, element) {
	    scope.$watch('scrollToBottom', function (newValue, oldValue) {
		if (newValue !== oldValue) {
		    // Wait for DOM to update
		    $timeout(function () {
			element[0].scrollTop = element[0].scrollHeight;
		    }, 0);
		}
	    });
	}
    };
});


SIREPO.app.directive('appHeaderBrand', function() {
    var appInfo = SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_SCHEMA.simulationType];

    function brand() {
        return [
            '<span class="hidden-md hidden-sm">', appInfo.longName, '</span>',
            '<span class="hidden-xs hidden-lg hidden-xl">', appInfo.shortName, '</span>',
        ].join('');
    }

    return {
        restrict: 'A',
        scope: {
            appUrl: '@',
        },
        template: `
            <div class="navbar-header">
              <a class="navbar-brand" href="/"><img style="width: 40px; margin-top: -10px;" src="/static/img/sirepo.gif" alt="Sirepo"></a>
              <div class="navbar-brand navbar-brand-text">
                <div data-ng-if="appUrl">
                  <a data-ng-href="{{ appUrl }}">
                    ${brand()}
                  </a>
                </div>
                <div data-ng-if="! appUrl">
                  ${brand()}
                </div>
              </div>
            </div>
        `,
    };
});

SIREPO.app.directive('appHeaderLeft', function(appState, authState, panelState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeaderLeft',
        },
        template: `
            <ul class="nav navbar-nav" data-ng-if=":: authState.isLoggedIn">
              <li data-ng-class="{active: nav.isActive('simulations')}"><a href data-ng-click="nav.openSection('simulations')"><span class="glyphicon glyphicon-th-list"></span> {{ simulationsLinkText }}</a></li>
            </ul>
            <div data-ng-if="showTitle()" class="navbar-text">
                <a href data-ng-click="showSimulationModal()"><span data-ng-if="nav.sectionTitle()" class="glyphicon glyphicon-pencil"></span> <strong data-ng-bind="nav.sectionTitle()"></strong></a>
                <a href data-ng-click="showSimulationLink()" class="glyphicon glyphicon-link"></a>
            </div>
        `,
        controller: function($scope, stringsService) {
            $scope.authState = authState;
            $scope.simulationsLinkText = stringsService.formatKey('simulationDataTypePlural');

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

SIREPO.app.directive('appHeaderRight', function(appDataService, authState, appState, fileManager, requestSender, panelState) {
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
        template: `
            <div class="nav sr-navbar-right-flex">
              <div style="width: 16px"></div>
              <ul class="nav navbar-nav sr-navbar-right" data-ng-show="isLoaded()">
                <li data-ng-transclude="appHeaderRightSimLoadedSlot"></li>
                <li data-ng-if="hasDocumentationUrl()"><a href data-ng-click="openDocumentation()"><span
                        class="glyphicon glyphicon-book"></span> Notes</a></li>
                <li data-settings-menu="nav">
                  <app-settings data-ng-transclude="appSettingsSlot"></app-settings>
                </li>
              </ul>
              <ul class="nav navbar-nav" data-ng-show="nav.isActive('simulations')">
                <li data-ng-if="SIREPO.APP_SCHEMA.constants.canCreateNewSimulation" class="sr-new-simulation-item"><a href data-ng-click="showSimulationModal()"><span
                        class="glyphicon glyphicon-plus sr-small-icon"></span><span class="glyphicon glyphicon-file"></span>
                  {{ newSimulationLabel() }}</a></li>
                <li><a href data-ng-click="showNewFolderModal()"><span class="glyphicon glyphicon-plus sr-small-icon"></span><span
                        class="glyphicon glyphicon-folder-close"></span> New Folder</a></li>
                <li data-ng-transclude="appHeaderRightSimListSlot"></li>
              </ul>
              <ul class="nav navbar-nav sr-navbar-right">
                <li class=dropdown><a href class="dropdown-toggle" data-toggle="dropdown"><span
                        class="glyphicon glyphicon-question-sign"></span> <span class="caret"></span></a>
                  <ul class="dropdown-menu">
                    <li><a data-ng-href="mailto:{{:: SIREPO.APP_SCHEMA.feature_config.support_email }}">
                      <span class="glyphicon glyphicon-envelope"></span> Contact Support</a></li>
                    <li><a href="https://github.com/radiasoft/sirepo/issues" target="_blank"><span
                            class="glyphicon glyphicon-exclamation-sign"></span> Report a Bug</a></li>
                    <li data-help-link="helpUserManualURL" data-title="User Manual" data-icon="list-alt"></li>
                    <li data-help-link="helpUserForumURL" data-title="User Forum" data-icon="globe"></li>
                    <li data-ng-if="SIREPO.APP_SCHEMA.feature_config.show_video_links" data-help-link="helpVideoURL" data-title="Instructional Video" data-icon="film"></li>
                  </ul>
                </li>
              </ul>
              <ul data-ng-if="::authState.isLoggedIn && ! authState.guestIsOnlyMethod" class="nav navbar-nav navbar-right"
                  data-logout-menu=""></ul>
            </div>
        `,
        link: function(scope) {
           scope.nav.isLoaded = scope.isLoaded;
           scope.nav.simulationName = scope.simulationName;
           scope.nav.hasDocumentationUrl = scope.hasDocumentationUrl;
           scope.nav.openDocumentation = scope.openDocumentation;
           scope.nav.modeIsDefault = scope.modeIsDefault;
           scope.nav.newSimulationLabel = scope.newSimulationLabel;
           scope.nav.showSimulationModal = scope.showSimulationModal;
           scope.nav.showImportModal = scope.showImportModal;

           scope.fileManager = fileManager;
        },
        controller: function($scope, stringsService) {
            $scope.authState = authState;
	    $scope.SIREPO = SIREPO;
            $scope.modeIsDefault = function () {
                return appDataService.isApplicationMode('default');
            };
            $scope.newSimulationLabel = function () {
                return stringsService.newSimulationLabel();
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
                requestSender.newWindow(appState.models.simulation.documentationUrl);
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
        template: `
            <div class="form-group">
              <label>{{ description }}</label>
              <input id="file-select" type="file" data-file-model="inputFile" data-ng-attr-accept="{{ fileFormats }}">
              <br />
              <div class="text-warning" style="white-space: pre-line"><strong>{{ fileUploadError }}</strong></div>
            </div>
            <div data-ng-if="isUploading" class="col-sm-6 pull-right">Please Wait...</div>
        `,
        controller: function($scope) {
            $scope.isUploading = false;
            $scope.title = $scope.title || 'Import ZIP File';
            $scope.description = $scope.description || 'Select File';
        },
    };
});

SIREPO.app.directive('elegantImportDialog', function(appState, commandService, fileManager, fileUpload, requestSender) {
    return {
        restrict: 'A',
        scope: {
            isMadXOnly: '@',
        },
        template: `
            <div class="modal fade" data-backdrop="static" id="simulation-import" tabindex="-1" role="dialog">
              <div class="modal-dialog modal-lg">
                <div class="modal-content">
                  <div class="modal-header bg-info">
                    <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <div data-help-button="{{ title }}"></div>
                    <span class="lead modal-title text-info">{{ title }}</span>
                  </div>
                  <div class="modal-body">
                    <div class="container-fluid">
                        <form class="form-horizontal" name="importForm">
                          <div data-ng-show="filename" class="form-group">
                            <label class="col-xs-4 control-label">Importing file</label>
                            <div class="col-xs-8">
                              <p class="form-control-static">{{ filename }}</p>
                            </div>
                          </div>
                          <div data-ng-show="isState('ready') || isState('lattice')">
                            <div data-ng-show="isState('ready')" class="form-group">
                              <label>{{ fileTypes() }}</label>
                              <input id="elegant-file-import" type="file" data-file-model="elegantFile" data-ng-attr-accept="{{ acceptFileTypes() }}" />
                              <br />
                              <div class="text-warning"><strong>{{ fileUploadError }}</strong></div>
                            </div>
                            <div data-ng-show="isState('lattice')" class="form-group">
                              <label>Select Lattice File ({{ latticeFileName }})</label>
                              <input id="elegant-lattice-import" type="file" data-file-model="elegantFile" accept="{ extension }" />
                              <br />
                              <div class="text-warning"><strong>{{ fileUploadError }}</strong></div>
                            </div>
                            <div class="col-sm-6 pull-right">
                              <button data-ng-click="importElegantFile(elegantFile)" data-ng-disabled="isMissingImportFile()" class="btn btn-primary">Import File</button>
                               <button data-dismiss="modal" class="btn btn-default">Cancel</button>
                            </div>
                          </div>
                          <div data-ng-show="isState('import') || isState('load-file-lists')" class="col-sm-6 col-sm-offset-6">
                            Uploading file - please wait.
                            <br /><br />
                          </div>
                          <div data-ng-show="isState('missing-files')">
                            <p>Please upload the files below which are referenced in the ${SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_NAME].longName} file.</p>
                            <div class="form-group" data-ng-repeat="item in missingFiles">
                              <div class="col-sm-11 col-sm-offset-1">
                                <span data-ng-if="item[5] && isCorrectMissingFile(item)" class="glyphicon glyphicon-ok"></span>
                                <span data-ng-if="item[5] && ! isCorrectMissingFile(item)" class="glyphicon glyphicon-flag text-danger"></span> <span data-ng-if="item[5] && ! isCorrectMissingFile(item)" class="text-danger">Filename does not match, expected: </span>
                                <label>{{ auxFileLabel(item) }}</label> ({{ auxFileName(item) }})
                                <input type="file" data-file-model="item[5]" />
                              </div>
                            </div>
                            <div class="text-warning"><strong>{{ fileUploadError }}</strong></div>
                            <div class="col-sm-6 pull-right">
                              <button data-ng-click="importMissingFiles()" data-ng-disabled="isMissingFiles()"" class="btn btn-primary">{{ importMissingFilesButtonText() }}</button>
                               <button data-dismiss="modal" class="btn btn-default">Cancel</button>
                            </div>
                          </div>
                        </form>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
            $scope.title = 'Import ' + SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_NAME].shortName + ' File';
            // states: ready, import, lattice, load-file-lists, missing-files
            $scope.state = 'ready';

            function classifyInputFiles(model, modelType, modelName, requiredFiles) {
                var inputFiles = modelInputFiles(modelType);
                for (var i = 0; i < inputFiles.length; i++) {
                    if (model[inputFiles[i]]) {
                        if (! requiredFiles[modelType]) {
                            requiredFiles[modelType] = {};
                        }
                        if (! requiredFiles[modelType][inputFiles[i]]) {
                            requiredFiles[modelType][inputFiles[i]] = {};
                        }
                        requiredFiles[modelType][inputFiles[i]][model[inputFiles[i]]] = modelName;
                    }
                }
            }

            function hideAndRedirect() {
                $('#simulation-import').modal('hide');
                requestSender.localRedirect('lattice', {
                    ':simulationId': $scope.id,
                });
            }

            function loadFileLists() {
                $scope.state = 'load-file-lists';
                if (! $scope.missingFileLists.length) {
                    verifyMissingFiles();
                    return;
                }
                var fileType = $scope.missingFileLists.pop();
                requestSender.loadListFiles(
                    fileType,
                    {
                        simulationType: SIREPO.APP_SCHEMA.simulationType,
                        fileType: fileType,
                    },
                    loadFileLists,
                );
            }

            function modelInputFiles(type) {
                var res = [];
                var elementSchema = SIREPO.APP_SCHEMA.model[type];
                for (var f in elementSchema) {
                    if (elementSchema[f][1].indexOf('InputFile') >= 0) {
                        res.push(f);
                    }
                }
                return res;
            }

            function verifyInputFiles(data) {
                var requiredFiles = {};
                var i;
                for (i = 0; i < data.models.elements.length; i++) {
                    var el = data.models.elements[i];
                    classifyInputFiles(el, el.type, el.name, requiredFiles);
                }
                for (i = 0; i < data.models.commands.length; i++) {
                    var cmd = data.models.commands[i];
                    classifyInputFiles(cmd, commandService.commandModelName(cmd._type), cmd._type, requiredFiles);
                }
                $scope.inputFiles = [];
                for (var type in requiredFiles) {
                    for (var field in requiredFiles[type]) {
                        for (var filename in requiredFiles[type][field]) {
                            var fileType = type + '-' + field;
                            //TODO(pjm): special case for BeamInputFile which shares files between bunchFile and command_sdds_beam
                            if (type == 'command_sdds_beam' && field == 'input') {
                                fileType = 'bunchFile-sourceFile';
                            }
                            $scope.inputFiles.push([type, field, filename, fileType, requiredFiles[type][field][filename]]);
                        }
                    }
                }
                verifyFileLists();
            }

            function verifyFileLists() {
                var res = [];
                for (var i = 0; i < $scope.inputFiles.length; i++) {
                    var fileType = $scope.inputFiles[i][3];
                    if (! requestSender.getListFilesData(fileType)) {
                        res.push(fileType);
                    }
                }
                $scope.missingFileLists = res;
                loadFileLists();
            }

            function verifyMissingFiles() {
                var res = [];
                for (var i = 0; i < $scope.inputFiles.length; i++) {
                    var filename = $scope.inputFiles[i][2];
                    var fileType = $scope.inputFiles[i][3];
                    var list = requestSender.getListFilesData(fileType);
                    if (list.indexOf(filename) < 0) {
                        res.push($scope.inputFiles[i]);
                    }
                }
                if (! res.length) {
                    hideAndRedirect();
                    return;
                }
                $scope.state = 'missing-files';
                $scope.missingFiles = res.sort(function(a, b) {
                    if (a[0] < b[0]) {
                        return -1;
                    }
                    if (a[0] > b[0]) {
                        return 1;
                    }
                    if (a[1] < b[1]) {
                        return -1;
                    }
                    if (a[1] > b[1]) {
                        return 1;
                    }
                    return 0;
                });
            }

            $scope.auxFileLabel = function(item) {
                return item[2];
            };

            $scope.auxFileName = function(item) {
                return item[4]
                    + ': '
                    + (commandService.isCommandModelName(item[0])
                       ? ''
                       : (item[0] + ' '))
                    + item[1];
            };

            $scope.acceptFileTypes = () => {
                return $scope.isMadXOnly
                     ? '.madx,.seq,.zip'
                     : '.ele,.in,.lte,.madx,.seq,.zip';
            };

            $scope.fileTypes = function() {
                return (
                    $scope.isMadXOnly
                        ? 'Select Lattice (.madx, .seq),'
                        : 'Select Command (.ele), Lattice (.lte, .in, .madx, .seq),'
                ) + ` or ${SIREPO.APP_SCHEMA.productInfo.shortName} Export (.zip)`;
            };

            $scope.importElegantFile = function(elegantFile) {
                if (! elegantFile) {
                    return;
                }
                var args = {
                    folder: fileManager.getActiveFolderPath(),
                };
                if ($scope.state == 'lattice') {
                    args.arguments = JSON.stringify($scope.eleData);
                }
                else {
                    $scope.resetState();
                    $scope.filename = elegantFile.name;
                }
                $scope.state = 'import';
                fileUpload.uploadFileToUrl(
                    elegantFile,
                    args,
                    requestSender.formatUrl('importFile'),
                    function(data) {
                        if (data.error) {
                            $scope.resetState();
                            $scope.fileUploadError = data.error;
                        }
                        else if (data.importState && data.importState === "needLattice") {
                            $scope.extension = ".lte";
                            $scope.state = 'lattice';
                            $scope.elegantFile = null;
                            $scope.eleData = data.eleData;
                            $scope.latticeFileName = data.latticeFileName;
                        }
                        else {
                            $scope.id = data.models.simulation.simulationId;
                            $scope.simulationName = data.models.simulation.name;
                            verifyInputFiles(data);
                        }
                    });
            };

            $scope.importMissingFiles = function() {
                $scope.state = 'import';
                var dataResponseHandler = function(data) {
                    if (data.error) {
                        $scope.state = 'missing-files';
                        $scope.fileUploadError = data.error;
                        return;
                    }
                    // the callback may occur after the simulation has loaded and file lists cleared
                    if (requestSender.getListFilesData(data.fileType)) {
                        requestSender.getListFilesData(data.fileType).push(data.filename);
                        hideAndRedirect();
                    }
                };
                for (var i = 0; i < $scope.missingFiles.length; i++) {
                    var f = $scope.missingFiles[i][5];
                    var fileType = $scope.missingFiles[i][3];

                    fileUpload.uploadFileToUrl(
                        f,
                        null,
                        requestSender.formatUrl(
                            'uploadLibFile',
                            {
                                '<simulation_id>': $scope.id,
                                '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                                '<file_type>': fileType,
                            }),
                        dataResponseHandler);
                }
            };

            $scope.importMissingFilesButtonText = function() {
                if (! $scope.missingFiles) {
                    return '';
                }
                return 'Import File' + ($scope.missingFiles.length > 1 ? 's' : '');
            };

            $scope.isCorrectMissingFile = function(item) {
                if (! item[5]) {
                    return false;
                }
                return item[2] == item[5].name;
            };

            $scope.isMissingFiles = function() {
                if (! $scope.missingFiles) {
                    return true;
                }
                for (var i = 0; i < $scope.missingFiles.length; i++) {
                    if (! $scope.missingFiles[i][5]) {
                        return true;
                    }
                    if (! $scope.isCorrectMissingFile($scope.missingFiles[i])) {
                        return true;
                    }
                }
                return false;
            };

            $scope.isMissingImportFile = function() {
                return ! $scope.elegantFile;
            };

            $scope.isState = function(state) {
                return $scope.state == state;
            };

            $scope.resetState = function() {
                $scope.id = null;
                $scope.elegantFile = null;
                $scope.filename = '';
                $scope.simulationName = '';
                $scope.state = 'ready';
                $scope.fileUploadError = '';
                $scope.latticeFileName = '';
                $scope.inputFiles = null;
            };

            $scope.resetState();
        },
        link: function(scope, element) {
            $(element).on('show.bs.modal', function() {
                $('#elegant-file-import').val(null);
                $('#elegant-lattice-import').val(null);
                scope.resetState();
            });
            scope.$on('$destroy', function() {
                $(element).off();
            });
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
        template: `
            <div class="modal fade" id="simulation-import" tabindex="-1" role="dialog">
              <div class="modal-dialog modal-lg">
                <div class="modal-content">
                  <div class="modal-header bg-info">
                    <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <div data-help-button="{{ title }}"></div>
                    <span class="lead modal-title text-info">{{ title }}</span>
                  </div>
                  <div class="modal-body">
                    <div class="container-fluid">
                    <form data-file-loader="" data-file-formats="fileFormats" data-description="description">
                      <form name="importForm">
                        <div class="form-group">
                          <div data-ng-show="! hideMainImportSelector">
                            <label>{{ description }}</label>
                            <input id="file-import" type="file" data-file-model="inputFile" data-ng-attr-accept="{{ fileFormats }}">
                            <br />
                          </div>
                          <div class="text-warning"><strong>{{ fileUploadError }}</strong></div>
                          <div data-ng-transclude=""></div>
                        </div>
                        <div data-ng-if="isUploading" class="col-sm-6 pull-right">Please Wait...</div>
                        <div class="clearfix"></div>
                        <div class="col-sm-6 pull-right">
                          <button data-ng-click="importFile(inputFile)" class="btn btn-primary" data-ng-disabled="! inputFile || isUploading">Import File</button>
                           <button data-ng-click="inputFile = null" data-dismiss="modal" class="btn btn-default" data-ng-disabled="isUploading">Cancel</button>
                        </div>
                      </form>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($element, $scope) {
            $scope.fileUploadError = '';
            // used by sub componenets to possibly hide the "main" file import selector
            $scope.hideMainImportSelector = false;
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
                            // clear input file to avoid Chrome bug if corrected file is re-uploaded
                            $($element).find('#file-import').val('');
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
                scope.hideMainImportSelector = false;
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

SIREPO.app.directive('importOptions', function(fileUpload, requestSender) {
    return {
        restrict: 'A',
        template: `
            <div data-ng-if="hasMissingFiles()" class="form-horizontal" style="margin-top: 1em;">
              <div style="margin-bottom: 1ex; white-space: pre;">{{ additionalFileText() }}</div>
              <div data-ng-repeat="info in missingFiles">
                <div data-ng-if="! info.hasFile" class="col-sm-11 col-sm-offset-1">
                  <span data-ng-if="info.invalidFilename" class="glyphicon glyphicon-flag text-danger"></span> <span data-ng-if="info.invalidFilename" class="text-danger">Filename does not match, expected: </span>
                  <label>{{ info.filename }}</label>
                  <span data-ng-if="info.label && info.type">({{ info.label + ": " + info.type }})</span>
                  <input id="file-import" type="file" data-file-model="info.file">
                  <div data-ng-if="uploadDatafile(info)"></div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
            const simType = SIREPO.APP_SCHEMA.simulationType;
            var parentScope = $scope.$parent;
            $scope.missingFiles = null;

            function checkFiles() {
                if (parentScope.fileUploadError) {
                    var hasFiles = true;
                    $scope.missingFiles.forEach(function(f) {
                        if (! f.hasFile) {
                            hasFiles = false;
                        }
                    });
                    if (hasFiles) {
                        parentScope.fileUploadError = null;
                        parentScope.importFile(parentScope.inputFile);
                    }
                }
            }

            $scope.additionalFileText = function() {
                if ($scope.missingFiles) {
                    return `Please upload the files below which are referenced in the ${simType} file.`;
                }
            };

            $scope.uploadDatafile = function(info) {
                if (info.file.name) {
                    if (info.file.name != info.filename) {
                        if (! info.invalidFilename) {
                            info.invalidFilename = true;
                            $scope.$applyAsync();
                        }
                        return false;
                    }
                    info.invalidFilename = false;
                    parentScope.isUploading = true;
                    fileUpload.uploadFileToUrl(
                        info.file,
                        null,
                        requestSender.formatUrl(
                            'uploadLibFile',
                            {
                                // dummy id because no simulation id is available or required
                                simulation_id: SIREPO.nonSimulationId,
                                simulation_type: simType,
                                file_type: info.file_type,
                            }),
                        function(data) {
                            parentScope.isUploading = false;
                            if (data.error) {
                                parentScope.fileUploadError = data.error;
                                return;
                            }
                            info.hasFile = true;
                            checkFiles();
                        });
                    info.file = {};
                }
                return false;
            };

            $scope.hasMissingFiles = function() {
                if (parentScope.fileUploadError) {
                    if (parentScope.errorData && parentScope.errorData.missingFiles) {
                        parentScope.hideMainImportSelector = true;
                        $scope.missingFiles = [];
                        parentScope.errorData.missingFiles.forEach(function(f) {
                            f.file = {};
                            $scope.missingFiles.push(f);
                        });
                        delete parentScope.errorData;
                    }
                }
                else {
                    $scope.missingFiles = null;
                }
                return $scope.missingFiles && $scope.missingFiles.length;
            };
        },
    };
});

SIREPO.app.directive('numArray', function(appState) {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            fieldName: '=',
            info: '=',
            model: '=',
            numType: '@',
        },
        template: `
            <div data-ng-repeat="v in model[fieldName] track by $index"
              style="display: inline-block;" >
              <label data-text-with-math="info[4][$index]" data-is-dynamic="isDynamic(info[4][$index])" style="margin-right: 1ex"></label>
              <input class="form-control sr-number-list" data-string-to-number="{{ numType }}"
                data-ng-model="model[fieldName][$index]" data-min="info[5][$index]" data-max="info[6][$index]"
                style="text-align: right" required />
              <div data-ng-if="$last" class="sr-input-warning"></div>
            </div>
        `,
        controller: $scope => {
            $scope.appState = appState;
            $scope.isDynamic = label => ! ! label.match(/{{\s*.+\s*}}/);
        },
    };
});

SIREPO.app.directive('settingsMenu', function(appDataService, appState, fileManager, panelState, requestSender, stringsService, $compile, $timeout) {

    return {
        restrict: 'A',
        transclude: {
            appSettingsSlot: '?appSettings',
        },
        scope: {
            nav: '=settingsMenu',
        },
        template: `
              <ul class="nav navbar-nav sr-navbar-right">
                <li>
                  <a href class="dropdown-toggle" data-toggle="dropdown"><span class="glyphicon glyphicon-cog"></span> <span class="caret"></span></a>
                  <ul class="dropdown-menu">
                    <li class="sr-settings-submenu" data-ng-transclude="appSettingsSlot"></li>
                    <li><a href data-ng-if="nav.modeIsDefault() && canShowDocumentationUrl()" data-ng-click="showDocumentationUrl()"><span class="glyphicon glyphicon-book"></span> Simulation Documentation URL</a></li>
                    <li><a href data-ng-if="::canExportArchive()" data-ng-href="{{ exportArchiveUrl('zip') }}"><span class="glyphicon glyphicon-cloud-download"></span> Export as ZIP</a></li>
                    <li data-ng-if="::canDownloadInputFile()"><a data-ng-href="{{ pythonSourceUrl() }}"><span class="glyphicon glyphicon-cloud-download sr-nav-icon"></span> {{ ::stringsService.formatKey('simulationSource') }}</a></li>
                    <li data-ng-if="::canExportMadx()" ><a data-ng-href="{{ pythonSourceUrl('madx') }}"><span class="glyphicon glyphicon-cloud-download sr-nav-icon"></span> Export as MAD-X lattice</a></li>
                    <li data-ng-if="canCopy()"><a href data-ng-click="copyItem()"><span class="glyphicon glyphicon-copy"></span> Open as a New Copy</a></li>
                    <li data-ng-if="isExample()"><a href data-target="#reset-confirmation" data-toggle="modal"><span class="glyphicon glyphicon-repeat"></span> Discard Changes to Example</a></li>
                    <li data-ng-if="! isExample()"><a href data-target="#delete-confirmation" data-toggle="modal"><span class="glyphicon glyphicon-trash"></span> Delete</a></li>
                    <li data-ng-if="hasRelatedSimulations()" class="divider"></li>
                    <li data-ng-if="hasRelatedSimulations()" class="sr-dropdown-submenu">
                      <a href><span class="glyphicon glyphicon-menu-left"></span> Related {{ ::stringsService.formatKey('simulationDataTypePlural') }}</a>
                      <ul class="dropdown-menu">
                        <li data-ng-repeat="item in relatedSimulations"><a href data-ng-click="openRelatedSimulation(item)">{{ item.name }}</a></li>
                      </ul>
                    </li>
                  </ul>
                </li>
              </ul>
        `,
        controller: function($scope) {
            $scope.stringsService = stringsService;
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

            $scope.canDownloadInputFile = function() {
                return SIREPO.APP_SCHEMA.constants.canDownloadInputFile;
            };

            $scope.canExportArchive = () => {
                return SIREPO.APP_SCHEMA.constants.canExportArchive;
            };

            $scope.canShowDocumentationUrl = () => {
                return SIREPO.APP_SCHEMA.constants.canShowDocumentationUrl;
            };

            $scope.canExportMadx = function() {
                return SIREPO.APP_SCHEMA.constants.hasMadxExport;
            };

            $scope.exportArchiveUrl = extension => {
                return panelState.exportArchiveUrl($scope.simulationId(), `${$scope.nav.simulationName()}.${extension}`);
            };

            $scope.copyFolder = fileManager.defaultCreationFolderPath();

            $scope.showDocumentationUrl = function() {
                panelState.showModalEditor('simDoc');
            };

            $scope.simulationId = () => appState.isLoaded() ? appState.models.simulation.simulationId : null;

            $scope.pythonSourceUrl = modelName => panelState.pythonSourceUrl($scope.simulationId(), modelName);

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
                    appState.listSimulations(
                        function(data) {
                            data.some(function(item, idx) {
                                if (item.simulationId == currentSimulationId) {
                                    data.splice(idx, 1);
                                    return true;
                                }
                            });
                            $scope.relatedSimulations = data;
                        },
                        {
                            simulationType: SIREPO.APP_SCHEMA.simulationType,
                            'simulation.folder': appState.models.simulation.folder,
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

            $scope.$on('modelsUnloaded', function() {
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
        template: `
            <div data-confirmation-modal="" data-id="delete-confirmation" data-title="Delete Simulation?" data-ok-text="Delete" data-ok-clicked="deleteSimulation()">Delete simulation &quot;{{ simulationName() }}&quot;?</div>
        `,
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

SIREPO.app.directive('resetSimulationModal', function(appDataService, appState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=resetSimulationModal',
        },
        template: `
            <div data-confirmation-modal="" data-id="reset-confirmation" data-title="Reset Simulation?" data-ok-text="Discard Changes" data-ok-clicked="revertToOriginal()">Discard changes to &quot;{{ simulationName() }}&quot;?</div>
        `,
        controller: function($scope) {
            $scope.revertToOriginal = () => {
                $scope.nav.revertToOriginal(
                    appState.models.simulation.appMode || appDataService.getApplicationMode(),
                    appState.models.simulation.name);
            };
            $scope.simulationName = () => {
                if (appState.isLoaded()) {
                    return appState.models.simulation.name;
                }
                return '';
            };
        },
    };
});

SIREPO.app.directive('completeRegistration', function() {
    return {
        restrict: 'A',
        template: `
            <div class="col-sm-12 col-md-offset-2 col-md-8 col-lg-offset-3 col-lg-6">
              <form class="form-horizontal" autocomplete="off" novalidate>
                <h2 data-ng-if="isModerated">Moderation Request</h2>
                <p>Please enter your full name to complete your Sirepo registration.</p>
                <div class="form-group">
                  <label class="col-sm-3 control-label">Your full name</label>
                  <div class="col-sm-9">
                    <input name="displayName" class="form-control"
                      data-ng-model="loginConfirm.data.displayName" required/>
                    <div class="sr-input-warning" data-ng-show="showWarning">{{ loginConfirm.warningText }}</div>
                  </div>
                </div>
                <div data-ng-if="isModerated">
                    <p>To prevent abuse of our systems all new users must supply a reason for
                      requesting access to {{ shortName }}. In a few sentences please describe
                      how you plan to use {{ shortName }}</p>
                    <div class="form-group">
                      <div class="col-sm-12">
                        <textarea data-ng-model="loginConfirm.data.reason" id="requestAccessExplanation"
                          class="form-control" rows="4" cols="50" required></textarea>
                      </div>
                    </div>
                </div>
                <div class="form-group">
                  <div class="col-sm-9 col-sm-offset-3">
                   <button data-ng-click="loginConfirm.submit()" class="btn btn-primary"
                     data-ng-disabled="! canSubmit()">Submit</button>
                  </div>
                </div>
              </form>
            </div>
            <div data-confirmation-modal="" data-is-required="true"
              data-id="sr-complete-registration-done" data-title="Thank you for your request"
              data-ok-text="" data-cancel-text="">
              <p>Your response has been submitted. You will received an email from Sirepo support
                after your request has been reviewed.</p>
            </div>
        `,
        controller: function(authState, $scope) {
            $scope.shortName = SIREPO.APP_SCHEMA.productInfo.shortName;
            $scope.isModerated = authState.isModerated;

            $scope.canSubmit = () => {
                if (! $scope.loginConfirm.data.displayName) {
                    return false;
                }
                if ($scope.isModerated) {
                    return !!$scope.loginConfirm.data.reason;
                }
                return true;
            };
        },
    };
});

SIREPO.app.directive('emailLogin', function(requestSender, errorService) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div data-ng-show="isJupyterHub" class="alert alert-info col-sm-offset-2 col-sm-10" role="alert">
            We're improving your Jupyter experience by making both Jupyter and Sirepo accessible via a single email login. Simply follow the directions below to complete this process.
            </div>
            <form class="form-horizontal" autocomplete="off" novalidate>
              <div class="form-group">
                <div class="col-sm-offset-2 col-sm-10">
                  <p>Enter your institutional email address. Any email or internet address associated with providers like Gmail.com, Yahoo.com, Outlook.com, etc. will be rejected. Emails associated with <a href="https://www.state.gov/countries-of-particular-concern-special-watch-list-countries-entities-of-particular-concern" target="_blank">'Countries of Particular Concern' as designated by the US State Department</a> will also be rejected.</p>
                </div>
              </div>
              <div class="form-group">
                <label class="col-sm-2 control-label">Your Email</label>
                <div class="col-sm-10">
                  <input type="text" class="form-control" data-ng-model="data.email" required/>
                  <div class="sr-input-warning" data-ng-show="showWarning">{{ warningText }}</div>
                </div>
              </div>
              <div class="form-group">
                <div class="col-sm-offset-2 col-sm-10">
                   <div data-disable-after-click="">
                    <button data-ng-click="login()" class="btn btn-primary">Continue</button>
                  </div>
                  <p class="help-block">When you click continue, we'll send an authorization link to your inbox.</p>
                  <p class="help-block">By signing up for Sirepo you agree to Sirepo's <a href="en/privacy.html" target="_blank">privacy policy</a> and <a href="en/terms.html" target="_blank">terms and conditions</a>, and to receive informational and marketing communications from RadiaSoft. You may unsubscribe at any time.</p>
                </div>
              </div>
            </form>
            <div data-confirmation-modal="" data-is-required="true" data-id="sr-email-login-done" data-title="Check your inbox" data-ok-text="" data-cancel-text="">
              <p>We just emailed a confirmation link to {{ data.sentEmail }}. Click the link and you'll be signed in. You may close this window.</p>
            </div>
        `,
        controller: function($scope) {
            function showInvalidEmail(warningText) {
                $scope.showWarning = true;
                $scope.warningText = warningText;
                $scope.$broadcast('sr-clearDisableAfterClick');
            }

            function handleResponse(data) {
                if (data.state == 'ok') {
                    $scope.showWarning = false;
                    $scope.data.email = '';
                    $scope.form.$setPristine();
                    $('#sr-email-login-done').modal('show');
                }
                else if (data.error) {
                    showInvalidEmail(data.error);
                }
                else {
                    $scope.showWarning = true;
                    $scope.warningText = `
                        Server reported an error, please contact
                        ${SIREPO.APP_SCHEMA.feature_config.support_email}.
                    `;
                }
            }

            $scope.data = {};
            $scope.isJupyterHub = SIREPO.APP_SCHEMA.simulationType == 'jupyterhublogin';
            $scope.login = function() {
                var e = $scope.data.email;
                errorService.alertText('');
                if (! ( e && e.match(/^.+@.+\..+$/) )) {
                    showInvalidEmail('Email address is invalid. Please update and resubmit.');
                    return;
                }
                $scope.showWarning = false;
                $scope.data.sentEmail = $scope.data.email;
                requestSender.sendRequest(
                    'authEmailLogin',
                    handleResponse,
                    {
                        email: $scope.data.sentEmail,
                        simulationType: SIREPO.APP_NAME
                    },
                    handleResponse,
                );
            };
        },
        link: function(scope, element) {
            // get the angular form from within the transcluded content
            scope.form = element.find('input').eq(0).controller('form');
        }
    };
});

SIREPO.app.directive('emailLoginConfirm', function() {
    return {
        restrict: 'A',
        template: `
            <div class="row text-center">
              <p>Please click the button below to complete the login process.</p>
            </div>
            <div class="sr-input-warning" data-ng-show="showWarning">{{ loginConfirm.warningText }}</div>
            <form class="form-horizontal" autocomplete="off" novalidate>
              <div class="row text-center" style="margin-top: 10px">
                 <button data-ng-click="loginConfirm.submit()" class="btn btn-primary">Confirm</button>
              </div>
            </form>
        `,
    };
});

SIREPO.app.directive('ldapLogin', function (requestSender) {
    return {
        restrict: 'A',
        scope: {
            user: '@',
            password: '@',
        },
        template: `
            <form class="form-horizontal" autocomplete="off" novalidate>
              <div class="form-group">
                <div class="col-sm-offset-2 col-sm-10">
                  <p>Enter your LDAP login</p>
                </div>
              </div>
              <div class="form-group">
                <label class="col-sm-2 control-label">User</label>
                <div class="col-sm-10">
                  <input type="text" value='' maxlength="256" class="form-control" data-ng-model="user"/>
                </div>
              </div>
              <div class="form-group">
                <label class="col-sm-2 control-label">Password</label>
                <div class="col-sm-10">
                  <input type="password" value='' maxlength="256" class="form-control" data-ng-model="password"/>
                </div>
              </div>
              <div class="form-group">
                <div class="col-sm-offset-2 col-sm-10">
                  <div data-disable-after-click="">
                    <button data-ng-click="login()" class="btn btn-primary">Continue</button>
                  </div>
                  <div class="sr-input-warning" data-ng-show="showWarning">{{ warningText }}</div>
                  <p class="help-block">By signing up for Sirepo you agree to Sirepo's <a href="en/privacy.html" target="_blank">privacy policy</a> and <a href="en/terms.html" target="_blank">terms and conditions</a>, and to receive informational and marketing communications from RadiaSoft. You may unsubscribe at any time.</p>
                </div>
              </div>
            </form>
        `,
        controller: function ($scope) {
            function handleResponse(data) {
                if (data.state == 'ok') {
                    showWarning(data.form_error);
                }
                else {
                    showWarning(`
                        Server reported an error, please contact
                        ${SIREPO.APP_SCHEMA.feature_config.support_email}.
                    `);
                }
            }

            function showWarning(msg) {
                $scope.showWarning = true;
                $scope.warningText = msg;
                $scope.$broadcast('sr-clearDisableAfterClick');
            }

            $scope.login = function () {
                if (!$scope.user || !$scope.password) {
                    showWarning('Empty field(s)');
                }
                else {
                    $scope.showWarning = false;
                    requestSender.sendRequest(
                        'authLdapLogin',
                        handleResponse,
                        {
                            password: $scope.password,
                            simulationType: SIREPO.APP_SCHEMA.simulationType,
                            user: $scope.user
                        }
                    );
                }
            };
        },
    };
});

SIREPO.app.directive('commonFooter', function() {
    const _refreshModals = () => {
        return Object.values(SIREPO.refreshModalMap).reduce(
            (rv, x) => {
                return rv + `<div data-confirmation-modal="" data-is-required="true" data-id="${x.modal}" data-title="${x.title}" data-ok-text="Refresh" data-ok-clicked="refreshPage()">${x.msg}. Select <b>Refresh</b> to update this simulation.</div>\n`;
            },
            '',
        );
    };
    return {
        restrict: 'A',
        scope: {
            nav: '=commonFooter',
        },
        template: `
            <div data-delete-simulation-modal="nav"></div>
            <div data-reset-simulation-modal="nav"></div>
            <div data-modal-editor="" view-name="simulation" modal-title="simulationModalTitle"></div>
            <div data-sbatch-login-modal=""></div>
            <div data-jobs-list-modal="" data-title="Jobs" data-id="sr-jobsListModal-editor"></div>
        ` + _refreshModals(),
        controller: function($scope, appState, stringsService) {
            $scope.simulationModalTitle = stringsService.formatKey('simulationDataType');
            $scope.refreshPage = () => window.location.reload();
        }
    };
});


SIREPO.app.directive('simConversionModal', function(appState, requestSender) {
    return {
        restrict: 'A',
        scope: {
            convMethod: '@',
        },
        template: `
            <div data-confirmation-modal="" data-is-required="" data-id="sr-conv-dialog" data-title="Open as a New {{ title }} Simulation" data-modal-closed="resetURL()" data-cancel-text="{{ displayLink() ? 'Close' : 'Cancel' }}" data-ok-text="{{ displayLink() ? '' : 'Create' }}" data-ok-clicked="openConvertedSimulation()">
              <div data-ng-if="! displayLink()"> Create a {{ title }} simulation with an equivalent beamline? </div>
              <div data-ng-if="displayLink()">
                {{ title }} simulation created: <a data-ng-click="closeModal()" href="{{ newSimURL }}" target="_blank">{{ newSimURL }} </a>
              </div>
            </div>
        `,
        controller: function($scope) {
            $scope.newSimURL = false;
            $scope.title = $scope.convMethod == 'create_shadow_simulation' ? 'Shadow' : 'SRW';

            function createNewSim(data) {
                requestSender.sendRequest(
                    'newSimulation',
                    simData => {
                        ['simulationId', 'simulationSerial'].forEach(function(f) {
                            data.models.simulation[f] = simData.models.simulation[f];
                        });
                        data.version = simData.version;
                        requestSender.sendRequest(
                            'saveSimulationData',
                            genSimURL,
                            data);
                    },
                    newSimData(data));
            }

            function newSimData(data) {
                const res = appState.clone(data.models.simulation);
                res.simulationType = data.simulationType;
                if (! res.name){
                    res.name = 'newSim';
                }
                return res;
            }

            function genSimURL(data) {
                $scope.newSimURL = requestSender.formatUrlLocal(
                    'beamline',
                    { 'simulationId': data.models.simulation.simulationId},
                    data.simulationType
                );
            }

            $scope.closeModal = function() {
                $('#sr-conv-dialog').modal('hide');
                $scope.resetURL();
            };

            $scope.resetURL = function() {
                $scope.newSimURL = false;
            };

            $scope.openConvertedSimulation = function() {
                const d = appState.models;
                d.method = $scope.convMethod;
                requestSender.sendStatefulCompute(
                    appState,
                    createNewSim,
                    d
                );
                return false;
            };

            $scope.displayLink = function() {
                return Boolean($scope.newSimURL);
            };
        },
    };
});

SIREPO.app.directive('simulationStatusTimer', function() {
    return {
        restrict: 'A',
        scope: {
            simState: '=simulationStatusTimer',
        },
        template: `
            <span data-ng-if="simState.hasTimeData() && ! simState.isStatePurged()">
              Elapsed time: {{ appState.formatTime(simState.timeData.elapsedTime)  }}
            </span>
        `,
        controller: function($scope, appState) {
            $scope.appState = appState;
        },
    };
});

SIREPO.app.directive('downloadStatus', function() {
    return {
        restrict: 'A',
        scope: {
            simState: '=',
            label: '@',
            title: '@',
        },
        template: `
            <div data-ng-if="angular.equals(simState, {})" class="modal fade" id="sr-download-status" tabindex="-1" role="dialog">
              <div class="modal-dialog modal-sm">
                <div class="modal-content">
                  <div class="modal-header bg-warning">
                    <button type="button" class="close" data-ng-click="cancel()"><span>&times;</span></button>
                    <span class="lead modal-title text-info">{{ title }}</span>
                  </div>
                  <div class="modal-body">
                    <div class="container-fluid">
                      <div class="row">
                        <div class="col-sm-12">
                          <div>{{ label }}{{ simState.dots }}</div>
                          <div data-sim-state-progress-bar="" data-sim-state="simState"></div>
                        </div>
                      </div>
                      <div class="row">
                        <div class="col-sm-12 col-sm-offset-4">
                          <button data-ng-click="cancel()" class="btn btn-default">Cancel</button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
            $scope.cancel = () => {
                $scope.simState.cancelSimulation(() => {
                    $('#sr-download-status').modal('hide');
                });
            };

            $scope.$on('download.started', (e, simState, title, label) => {
                $scope.simState = simState;
                $scope.label = label;
                $scope.title = title;
            });
        },
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

SIREPO.app.directive('stringToNumber', function(appState) {
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
                    value = appState.formatExponential(value);
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

SIREPO.app.directive('jobsList', function(requestSender, appState, $location) {
    return {
        restrict: 'A',
        scope: {
            wantAdm: '<',
        },
        template: `
            <div>
              <table class="table">
                <thead>
                  <th data-ng-show="!wantAdm">Name</th>
                  <th data-ng-show="!wantAdm">Report</th>
                  <th data-ng-repeat="c in displayedCols">{{ data.header[c].title }}</th>
                </thead>
                <tbody>
                  <tr data-ng-repeat="j in data.jobs track by $index">
                    <td data-ng-show="!wantAdm">
                      <a ng-href="{{ getJobLink(j) }}">
                        {{ j['simName'] }}
                      </a>
                    </td>
                    <td data-ng-show="!wantAdm">
                        {{ j['reportName'] }}
                    </td>
                    <td data-ng-repeat="c in displayedCols">
                      {{ getCellContent(j, c) }}
                    </td>
                    <td data-ng-show="!wantAdm">
                      <button class="btn btn-default" data-ng-click="endSimulation(j)">End Simulation</button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <button class="btn btn-default" data-ng-click="getJobs()">Refresh</button>
            </div>
        `,
        controller: function($scope, appState, panelState) {
            function dataLoaded(data, status) {
                $scope.data = data;
                for(var job of data.jobs) {
                    job.reportName = appState.viewInfo(job.computeModel)?.title;
                }
            }

            function getUrl(simulationId, app) {
                return requestSender.formatUrlLocal(
                    'source',
                    {':simulationId': simulationId},
                    app
                );
            }

            $scope.displayedCols = $scope.wantAdm ? [
                'simulationType',
                'simulationId',
                'uid',
                'displayName',
                'startTime',
                'lastUpdateTime',
                'elapsedTime',
                'statusMessage',
                'queuedTime',
                'driverDetails',
                'isPremiumUser'
            ] : [
                'startTime',
                'lastUpdateTime',
                'elapsedTime',
                'statusMessage'
            ];

            $scope.endSimulation = function(job) {
                const r = {
                    simulationId: job.simulationId,
                    report: job.computeModel,
                    simulationType: job.simulationType,
                };
                const successCallback = () => {
                    $scope.getJobs();
                };
                const errorCallback = (request) => {
                    return (data) => {
                        srlog(`runCancel error=${data.error} from request=${request}`);
                    };
                };
                requestSender.sendRequest('runCancel', successCallback, r, errorCallback(r));
            };

            $scope.getCellContent = function(job, key) {
                const typeDispatch = {
                    DateTime: appState.formatDate,
                    Time: appState.formatTime,
                    String: function(s){return s;},
                };
                return typeDispatch[$scope.data.header[key].type](job[key]);
            };

            $scope.getJobLink = function(job) {
                return getUrl(job.simulationId, job.simulationType);
            };

            $scope.getJobs = function () {
                requestSender.sendRequest(
                    $scope.wantAdm ? 'admJobs' : 'ownJobs',
                    dataLoaded,
                    {
                        simulationType: SIREPO.APP_SCHEMA.simulationType,
                    });
            };

            appState.clearModels(appState.clone(SIREPO.appDefaultSimulationValues));
            $scope.$on('$routeChangeSuccess', () => {
                if ($location.path() == (SIREPO.APP_SCHEMA.route.admJobs)) {
                    $scope.getJobs();
                }
            });
            panelState.waitForUI(() => {
                $('#' + panelState.modalId('jobsListModal')).on('shown.bs.modal', function() {
                    $scope.getJobs();
                });
            });
        },
    };
});

SIREPO.app.directive('jobsListModal', function() {
    return {
        restrict: 'A',
        scope: {
            title: '@',
            id: '@',
        },
        template: `
            <div class="modal fade" data-ng-attr-id="{{ id }}" tabindex="-1" role="dialog">
              <div class="modal-dialog modal-lg">
                <div class="modal-content">
                  <div class="modal-header bg-info">
                    <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <span class="lead modal-title text-info">{{ title }}</span>
                  </div>
                  <div class="modal-body">
                    <div class="container-fluid">
                    <div data-jobs-list=""></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
    };
});

SIREPO.app.directive('modelArray', function() {
    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            model: '=',
            field: '=',
        },
        template: `
            <div style="position: relative; top: -25px">
              <div class="row">
                <div class="col-sm-11">
                  <div class="row">
                    <div data-ng-if="pad > 0" data-ng-attr-class="col-sm-{{ pad }}"></div>
                    <div class="col-sm-3 text-center"
                      data-ng-repeat="heading in headings track by $index">
                      <div data-label-with-tooltip="" data-label="{{ heading[0] }}"
                        data-tooltip="{{ heading[3] }}"></div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="form-group form-group-sm" data-ng-show="showRow($index)"
                data-ng-repeat="m in modelArray() track by $index">
                <div class="col-sm-11">
                  <div class="row">
                    <div data-ng-if="pad > 0" data-ng-attr-class="col-sm-{{ pad }}"></div>
                    <div class="col-sm-3" data-ng-repeat="f in fields track by $index">
                      <input data-string-to-number="" data-ng-model="m[f]" class="form-control"
                        style="text-align: right" data-lpignore="true" />
                    </div>
                  </div>
                </div>
                <div class="col-sm-1">
                  <button type="button" style="margin-left: -15px; margin-top: 5px"
                    data-ng-show="! isEmpty($index)" data-ng-click="deleteRow($index)"
                    class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span>
                  </button>
                </div>
              </div>
            </div>
        `,
        controller: function(appState, $scope) {
            const mView = SIREPO.APP_SCHEMA.view[$scope.field];
            $scope.fields = mView.advanced;
            $scope.headings = $scope.fields.map(f => SIREPO.APP_SCHEMA.model[$scope.field][f]);
            $scope.pad = (4 - $scope.fields.length) * 3;

            function initArray() {
                for (let i = 0; i < mView.maxRows; i++) {
                    model(i);
                }
            }

            function model(idx) {
                if (! $scope.modelArray()[idx]) {
                    $scope.modelArray()[idx] = {};
                }
                return $scope.modelArray()[idx];
            }

            $scope.deleteRow = idx => {
                $scope.modelArray().splice(idx, 1);
                initArray();
            };

            $scope.isEmpty = idx => {
                const m = model(idx);
                return ! $scope.fields.some(f => angular.isNumber(m[f]));
            };

            $scope.modelArray = () => {
                if (! $scope.model) {
                    return;
                }
                if (! $scope.model[$scope.field]) {
                    $scope.model[$scope.field] = [];
                    initArray();
                }
                return $scope.model[$scope.field];
            };

            $scope.showRow = idx => (idx == 0) || ! $scope.isEmpty(idx - 1);
        },
    };
});

SIREPO.app.directive('moderationRequest', function(appState, errorService, panelState) {
    return {
        restrict: 'A',
        template: `
          <form>
            <div class="form-group">
              <label for="requestAccessExplanation">{{ moderationRequestReason }}:</label>
              <textarea data-ng-show="!submitted" data-ng-model="data.reason" id="requestAccessExplanation" class="form-control" rows="4" cols="50" required></textarea>
            </div>
            <button data-ng-disabled="disableSubmit" data-ng-show="!submitted" type="submit" class="btn btn-primary" data-ng-click="submitRequest()">Submit</button>
          </form>
          <div data-ng-show="submitted">Response submitted.</div>
        `,
        controller: function(requestSender, uri, $route, $scope) {
            const _reason = () => {
                if (uri.currentRouteParam('role', '') === 'trial') {
                    return `To prevent abuse of our systems all new users must supply a reason for requesting access to ${SIREPO.APP_SCHEMA.productInfo.shortName}. In a few sentences please describe how you plan to use ${SIREPO.APP_SCHEMA.productInfo.shortName}`;
                }
                return 'Please describe your reason for requesting access';
            };

            $scope.data = {};
            $scope.submitted = false;
            $scope.disableSubmit = true;
            $scope.moderationRequestReason = _reason();
            $scope.submitRequest = function () {
                const handleResponse = (data) => {
                    if (data.state === 'error') {
                        errorService.alertText(data.error);
                    }
                };
                $scope.submitted = true;
                requestSender.sendRequest(
                    'saveModerationReason',
                    handleResponse,
                    {
                        reason: $scope.data.reason,
                        simulationType: SIREPO.APP_NAME
                    }
                );
            };

            function reasonOk(reason) {
                return reason && reason.trim().length > 4;
            }

            function validateReason() {
                $scope.disableSubmit = !reasonOk($scope.data.reason) || $scope.submitted;
            }

            $scope.$watch('data.reason', validateReason);
        },
    };
});

SIREPO.app.directive('moderationPending', function() {
    return {
        restrict: 'A',
        template: `
          <div>Your request to access {{ appName }} has been received. For additional information, contact
            <span data-support-email=""></span>.
          </div>
        `,
        controller: function(requestSender, $scope) {
            $scope.appName = SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_SCHEMA.simulationType].shortName;
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
        template: `
            <div class="input-group input-group-sm">
              <input data-string-to-number="" data-ng-model="model[field]" data-min="min" data-max="max" class="form-control" style="text-align: right" data-lpignore="true" required />
              <div class="input-group-btn">
                <button type="button" data-ng-attr-class="btn btn-{{ buttonName() }} dropdown-toggle" data-toggle="dropdown" title="Optimization Settings"><span class="glyphicon glyphicon-cog"></span></button>
                <ul class="dropdown-menu pull-right">
                  <li><a href data-ng-click="toggleCheck()" ><span data-ng-attr-class="glyphicon glyphicon-{{ checkedName() }}"></span> Select this field for optimization</a></li>
                </ul>
              </div>
            </div>
        `,
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
            fieldDelegate: '<',
            model: '=',
            modelName: '=',
        },
        template: `
            <input id="{{ modelName }}-{{ field }}-range" type="range" data-ng-model="model[field]" data-ng-change="fieldDelegate.update()">
            <span class="valueLabel">{{ model[field] }}{{ model.units }}</span>
        `,
        controller: function($scope, $element) {
            let slider;
            let delegate = null;

            function update() {
                updateReadout();
                updateSlider();
            }

            function updateSlider() {
                const r = delegate.range();
                slider.attr('min', r.min);
                slider.attr('step', r.step);
                slider.attr('max', r.max);
            }

            function updateReadout() {
                panelState.setFieldLabel($scope.modelName, $scope.field, delegate.readout());
            }

            appState.whenModelsLoaded($scope, function () {
                delegate = $scope.fieldDelegate;
                if (! delegate || $.isEmptyObject(delegate)) {
                    delegate = panelState.getFieldDelegate($scope.modelName, $scope.field);
                    $scope.fieldDelegate = delegate;
                }
                appState.watchModelFields($scope, (delegate.watchFields || []), update);
                slider = $(`#${$scope.modelName}-${$scope.field}-range`);
                update();
                // on load, the slider will coerce model values to fit the basic input model of range 0-100,
                // step 1.  This resets to the saved value
                const val = delegate.storedVal;
                if ((val || val === 0) && $scope.model[$scope.field] !== val) {
                    $scope.model[$scope.field] = val;
                    const form = $element.find('input').eq(0).controller('form');
                    if (! form) {
                        return;
                    }
                    // changing the value dirties the form; make it pristine or we'll get a spurious save button
                    form.$setPristine();
                }

                $scope.$on(`${$scope.modelName}.changed`, () => {
                    delegate.storedVal = $scope.model[$scope.field];
                });

                $scope.$on('cancelChanges', (e, d) => {
                    if (d !== $scope.modelName) {
                        return;
                    }
                    delegate.update();
                });

                $scope.$on('sliderParent.ready', function (e, m) {
                    if (m) {
                        $scope.model = m;
                    }
                    update();
                });
            });
        },
    };
});

SIREPO.app.directive('admRolesList', function() {
    return {
        restrict: 'A',
        template: `
            <div class="col-sm-12">
              <table class="table">
                <thead>
                  <th data-ng-repeat="h in headers">{{ h[1] }}</th>
                </thead>
                <tbody>
                  <tr data-ng-repeat="r in rows track by $index">
                    <td data-ng-repeat="h in headers">{{ r[h[0]] }}</td>
                    <td><button class="btn btn-default"
                      data-ng-click="setModerationStatus(r, 'approve')">Approve</button></td>
                    <td><button class="btn btn-default"
                      data-ng-click="setModerationStatus(r, 'deny')">Deny</button></td>
                    <td><button class="btn btn-default" data-ng-show="r.status!=='clarify'"
                      data-ng-click="setModerationStatus(r, 'clarify')">Clarify</button></td>
                  </tr>
                </tbody>
              </table>
              <button type="submit" class="btn btn-primary"
                data-ng-click="getModerationRequestRows()">Refresh Table</button>
            </div>
        `,
        controller: function(authState, errorService, requestSender, $scope) {
            $scope.rows = [];
            $scope.headers = [];

            $scope.getModerationRequestRows = function () {
                const handleResponse = (r) => {
                    $scope.rows = r.rows;
                    $scope.headers = SIREPO.APP_SCHEMA.common.adm.userRoleModerationColumns;
                };
                requestSender.sendRequest(
                    'getModerationRequestRows',
                    handleResponse,
                    {},
                );
            };

            $scope.setModerationStatus = function(info, status) {
                const handleResponse = (data) => {
                    if (data.state === 'error') {
                        errorService.alertText(data.error);
                    }
                    $scope.getModerationRequestRows();
                };
                requestSender.sendRequest(
                    'admModerate',
                    handleResponse,
                    {
                        uid: info.uid,
                        role: info.role,
                        status: status,
                    }
                );
            };

            if (authState.isLoggedIn) {
                $('.navbar-static-top').hide();
            }
            $scope.getModerationRequestRows();
        },
    };
});

SIREPO.app.directive('admUserList', function() {
    return {
        restrict: 'A',
        template: `
            <div class="col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2">
              <label class="pull-right"><input type="checkbox" data-ng-model="showAll"> Show all rows</label>
              <table class="table">
                <thead>
                  <th data-ng-repeat="h in header">{{ h }}</th>
                </thead>
                <tbody>
                  <tr data-ng-repeat="r in rows track by $index">
                    <td data-ng-repeat="h in header">{{ r[h] }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
        `,
        controller: function(authState, errorService, requestSender, $scope) {
            $scope.showAll = false;

            const dateString = (dateTime) => {
                return dateTime
                     ? new Date(dateTime * 1000).toLocaleDateString()
                     : '';
            };

            const loadRows = () => {
                requestSender.sendRequest(
                    'admUsers',
                    (res) => {
                        $scope.header = res.header;
                        $scope.rows = res.rows;
                        for (const r of $scope.rows) {
                            r['Creation Date'] = dateString(r['Creation Date']);
                            r.Expiration = dateString(r.Expiration);
                        }
                    },
                    {
                        showAll: $scope.showAll,
                        simulationType: SIREPO.APP_NAME
                    },
                );
            };

            $scope.$watch('showAll', loadRows);
        }
    };
});

SIREPO.app.directive('toolbar', function(appState) {
    return {
        restrict: 'A',
        scope: {
            itemFilter: '&',
            parentController: '=',
            toolbarItems: '=toolbar',
        },
        template: `
            <div class="row">
              <div class="col-sm-12">
                <div class="text-center bg-info sr-toolbar-holder">
                  <div class="sr-toolbar-section" data-ng-repeat="section in ::sectionItems">
                    <div class="sr-toolbar-section-header"><span class="sr-toolbar-section-title">{{ ::section.name }}</span></div>
                    <span data-ng-click="item.isButton ? parentController.editTool(item) : null" data-ng-repeat="item in ::section.contents | filter:showItem" class="sr-toolbar-button sr-beamline-image" data-ng-drag="{{ ! item.isButton }}" data-ng-drag-data="item">
                      <span data-toolbar-icon="" data-item="item"></span><br>{{ ::item.title }}
                    </span>
                  </div>
                  <span data-ng-repeat="item in ::standaloneItems" class="sr-toolbar-button sr-beamline-image" data-ng-drag="{{ ! item.isButton }}" data-ng-drag-data="item">
                    <span data-beamline-icon="" data-item="item"></span><br>{{ ::item.title }}
                  </span>
                </div>
              </div>
            </div>
            <div class="sr-editor-holder" style="display:none">
              <div data-ng-repeat="item in ::allItems">
                <div class="sr-beamline-editor" id="sr-{{ ::item.type }}-editor" data-beamline-item-editor="" data-model-name="{{ ::item.type }}" data-parent-controller="parentController" ></div>
              </div>
            </div>
        `,
        controller: function($scope) {
            $scope.allItems = [];
            var items = $scope.toolbarItems || SIREPO.APP_SCHEMA.constants.toolbarItems || [];

            function addItem(name, items) {
                var item = appState.setModelDefaults({type: name}, name);
                items.push(item);
                $scope.allItems.push(item);
            }

            $scope.showItem = function (item) {
                if (! $scope.itemFilter || ! angular.isFunction($scope.itemFilter())) {
                    return true;
                }
                return $scope.itemFilter()(item);
            };

            function initToolbarItems() {
                $scope.sectionItems = items.filter(function (item) {
                    return isSection(item);
                });
                $scope.standaloneItems = items.filter(function (item) {
                    return ! isSection(item);
                });
                $scope.allItems = items;
            }

            function isSection(item) {
                return item.contents && item.contents.length;
            }
            initToolbarItems();
        },
    };
});

SIREPO.app.directive('toolbarIcon', function() {
    return {
        scope: {
            item: '=',
        },
        template: '<ng-include title="{{ item.title }}" src="iconUrl()" onload="iconLoaded()"/>',
        controller: function($scope, $element) {
            var adjustmentsByType = {
            };

            $scope.iconUrl = function() {
                return '/static/svg/' +  $scope.item.type + '.svg' + SIREPO.SOURCE_CACHE_KEY;
            };

            $scope.iconLoaded = function () {
                /*
                var vb = $($element).find('svg.sr-beamline-item-icon').prop('viewBox').baseVal;
                vb.width = 100;
                vb.height = 50;
                var adjust = adjustmentsByType[$scope.item.name];
                if (adjust) {
                    vb.height += adjust[0] || 0;
                    vb.x -= adjust[1] || 0;
                    vb.y -= adjust[2] || 0;
                }

                 */
            };

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
        template: `
            <div>
                <svg data-ng-attr-height="{{ 2.0 * axisInfo.height }}" data-ng-attr-width="{{ 2.0 * axisInfo.width }}">
                    <rect data-ng-attr-x="{{ xOffset(50) }}" y="0" stroke="black" fill="none" data-ng-attr-width="{{ axisInfo.width }}" data-ng-attr-height="{{ axisInfo.height }}"></rect>
                    <line data-ng-attr-x1="{{ xOffset(0) }}" y1="50"  data-ng-attr-x2="{{ xOffset(50) }}" y2="0" stroke="black"></line>
                    <line data-ng-attr-x1="{{ xOffset(100) }}" y1="50" data-ng-attr-x2="{{ xOffset(150) }}" y2="0" stroke="black"></line>
                    <line data-ng-attr-x1="{{ xOffset(0) }}" y1="150" data-ng-attr-x2="{{ xOffset(50) }}" y2="100" stroke="black"></line>
                    <line data-ng-attr-x1="{{ xOffset(100) }}" y1="150" data-ng-attr-x2="{{ xOffset(150) }}" y2="100" stroke="black"></line>
                    <rect data-ng-attr-x="{{ xOffset(0) }}" y="50" stroke="black" fill="rgba(255, 255, 255, 0.5)" data-ng-attr-width="{{ axisInfo.width }}" data-ng-attr-height="{{ axisInfo.height }}"></rect>
                    <text data-ng-attr-x="{{ xOffset(50) }}" y="175" stroke="red">{{ axisInfo.xLabel }}</text>
                    <text x="0" y="100">{{ axisInfo.yLabel }}</text>
                    <text data-ng-attr-x="{{ xOffset(125) }}" y="125">{{ axisInfo.zLabel }}</text>
                    {{ slicePlane() }}
                </svg>
            </div>
            <span class="valueLabel">{{ model[field] }}{{ model.units }}</span>
        `,
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

SIREPO.app.directive('sbatchLoginModal', function() {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div id="sbatch-login-modal" class="modal fade" tabindex="-1" role="dialog" data-backdrop='static' data-keyboard='false'>
              <div class="modal-dialog" role="document">
                <div class="modal-content">
                  <div class="modal-header bg-warning">
                    <span class="lead modal-title text-info">{{ loginHeading() }}</span>
                    <button data-ng-click="cancel()" type="button" class="close" data-ng-disabled="! sbatchLoginService.query('showLogin')"><span>&times;</span></button>
                    </div>
                    <div class="modal-body">
                        <form name="sbatchLoginModalForm">
                            <div class="sr-input-warning">{{ warning }}</div>
                            <div class="form-group">
                                <input type="text" class="form-control" name="username" placeholder="username" autocomplete="username" data-ng-model="username" />
                            </div>
                            <div class="form-group">
                                <input type="password" class="form-control" name="password" placeholder="password" autocomplete="current-password" data-ng-model="password" />
                            </div>
                            <div class="form-group">
                                <input type="password" class="form-control" name="otp" placeholder="one time password" autocomplete="one-time-code" data-ng-show="authState.sbatchHostIsNersc" data-ng-model="otp"/>
                            </div>
                            <button  data-ng-click="submit()" class="btn btn-primary" data-ng-disabled="submitDisabled()">Submit</button>
                            <button data-ng-click="cancel()" class="btn btn-default" data-ng-disabled="! sbatchLoginService.query('showLogin')">Cancel</button>
                        <form>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function(authState, sbatchLoginService, $element, $scope) {
	    const _resetLoginFormText = () => {
		$scope.otp = '';
		$scope.password = '';
		$scope.username = '';
                $scope.warning = '';
	    };

	    const _resetLoginForm = () => {
		_resetLoginFormText();
                $scope.directiveScope = null;
		$scope.sbatchLoginModalForm.$setPristine();
	    };

	    _resetLoginFormText();
	    $scope.authState = authState;
	    $scope.sbatchLoginService = sbatchLoginService;

            $scope.cancel = () => {
                _resetLoginForm();
                sbatchLoginService.event('credsCancel');
            };

            $scope.loginHeading = () => sbatchLoginService.loginButtonLabel();

            $scope.submit = () => {
                $scope.warning = null;
                sbatchLoginService.event(
                    'credsConfirm',
                    {
                        sbatchCredentials: {
                            otp: $scope.otp,
                            password: $scope.password,
                            username: $scope.username,
                        },
                        directiveScope: $scope.directiveScope,
                    },
                );
            };
            $scope.submitDisabled = () => {
                return $scope.password.length < 1 || $scope.username.length < 1 || ! sbatchLoginService.query('showLogin');
            };

            $scope.$on('destroy', () => {
                $($element).off();
            });

            $scope.$on(
                'sbatchLoginEvent',
                (_, sbatchLoginEvent) => {
                    if (sbatchLoginEvent.query('hideCredsForm')) {
                        _resetLoginForm();
                        $('#sbatch-login-modal').modal('hide');
                    }
                    else if (sbatchLoginEvent.query('isCredsFormBlank')) {
                        _resetLoginForm();
                        $scope.directiveScope = sbatchLoginEvent.argProperty('directiveScope');
                        $('#sbatch-login-modal').modal('show');
                    }
                    else if (sbatchLoginEvent.query('isCredsFormError')) {
                        $scope.warning = sbatchLoginEvent.credsError();
                        $('#sbatch-login-modal').modal('show');
                    }
                },
            );

            $($element).on('shown.bs.modal', () => {
                $($element).find('.form-control').first().select();
            });
        },
    };

});

SIREPO.app.directive('sbatchOptions', function(appState, sbatchLoginService) {
    return {
        restrict: 'A',
        scope: {
            simState: '=sbatchOptions',
        },
        template: `
            <div data-ng-show="sbatchLoginService.query('showSbatchOptions')">
              <div class="form-group form-group-sm" data-ng-repeat="pair in sbatchFields track by $index">
                <div data-ng-repeat="sbatchField in pair" data-model-field='sbatchField' data-model-name="simState.model" data-label-size="3" data-field-size="3"></div>
              </div>
            </div>
        `,
        controller: function($scope, authState, stringsService) {
            $scope.sbatchFields = getSbatchFields();
	    $scope.sbatchLoginService = sbatchLoginService;

            function getSbatchFields() {
                const f = [...SIREPO.APP_SCHEMA.constants.sbatch.fields];
                if (authState.sbatchHostIsNersc) {
                    f.push(...SIREPO.APP_SCHEMA.constants.sbatch.nersc);
                }
                // group fields in pairs
                const g = [];
                for (let i = 0; i < f.length; i += 2) {
                    g.push(f.slice(i, i + 2));
                }
                return g;
            }

            function trimHoursAndCores() {
                var m = appState.models[$scope.simState.model];
                ['Hours', 'Cores'].forEach(function(e) {
                    var q = m.sbatchQueue;
                    var maxes = authState.sbatchQueueMaxes[e.toLowerCase()];
                    if (! (q in maxes)) {
                        return;
                    }
                    m['sbatch' + e] = Math.min(
                        m['sbatch' + e],
                        maxes[q]
                    );
                });
            }

            ['sbatchCores', 'sbatchHours', 'sbatchQueue'].forEach(function(e) {
                appState.watchModelFields($scope, [$scope.simState.model + '.' + e], trimHoursAndCores);
            });
        }
    };
});

SIREPO.app.directive('simSections', function(utilities) {

    return {
        restrict: 'A',
        transclude: true,
        template: `
            <ul data-ng-transclude="" class="nav navbar-nav sr-navbar-right" data-ng-class="{'nav-tabs': isWide()}"></ul>
        `,
        controller: function($scope) {
            $scope.isWide = function() {
                return utilities.isWide();
            };
        },
    };
});

SIREPO.app.directive('simStatusPanel', function(appState) {
    return {
        restrict: 'A',
        scope: {
            cancelCallback: '&?',
            simState: '=simStatusPanel',
            startFunction: '&?',
        },
        template: `
            <form name="form" class="form-horizontal" autocomplete="off" novalidate data-ng-show="simState.isProcessing()">
              <div data-pending-link-to-simulations="" data-sim-state="simState"></div>
              <div data-ng-show="simState.isStateRunning()">
                <div class="col-sm-12">
                  <div>
                    <div data-ng-show="simState.isInitializing()">{{ initMessage() }} {{ simState.dots }}</div>
                    <div data-ng-show="simState.getFrameCount() > 0">{{ runningMessage(); }}</div>
                    <div data-simulation-status-timer="simState"></div>
                  </div>
                  <div data-sim-state-progress-bar="" data-sim-state="simState"></div>
                </div>
              </div>
              <div class="col-sm-6 pull-right">
                <button class="btn btn-default" data-ng-click="simState.cancelSimulation(cancelCallback)">{{ stopButtonLabel() }}</button>
              </div>
            </form>
            <div data-canceled-due-to-timeout-alert="simState"></div>
            <form name="form" class="form-horizontal" autocomplete="off" novalidate data-ng-show="simState.isStopped()">
              <div data-ng-show="simState.getFrameCount() > 0" data-simulation-stopped-status="simState"><br><br></div>
              <div data-ng-show="simState.hasTimeData()">
                <div class="col-sm-12" data-simulation-status-timer="simState"></div>
              </div>
              <div data-job-settings-sbatch-login-and-start-simulation data-sim-state="simState" data-start-simulation="start()"></div>
            </form>
            <div class="clearfix"></div>
            <div class="well well-lg" style="margin-top: 5px;" data-ng-if="logFileURL()" data-ng-show="(simState.isStopped() && simState.getFrameCount() > 0) || simState.isStateError() || errorMessage()">
              <a data-ng-href="{{ logFileURL() }}" target="_blank">View {{ ::appName }} log</a>
            </div>
            <div data-ng-if="errorMessage()"><div class="text-danger"><strong>{{ ::appName }} Error:</strong></div><pre>{{ errorMessage() }}</pre></div>
            <div data-ng-if="alertMessage()"><div class="text-warning"><strong>{{ ::appName }} Alert:</strong></div><pre>{{ alertMessage() }}</pre></div>
        `,
        controller: function($scope, appState, authState, stringsService) {
            $scope.appName = SIREPO.APP_SCHEMA.appInfo[SIREPO.APP_NAME].shortName;

            function callSimState(method) {
                return $scope.simState[method] && $scope.simState[method]();
            }

            $scope.alertMessage = function() {
                return callSimState('getAlert');
            };

            $scope.canceledAfterSecs = function() {
                return callSimState('getCanceledAfterSecs');
            };

            $scope.errorMessage = function() {
                return callSimState('errorMessage');
            };

            $scope.initMessage = function() {
                const s = SIREPO.APP_SCHEMA.strings;
                return s.initMessage || `Running ${stringsService.typeOfSimulation($scope.simState.model)}`;
            };

            $scope.logFileURL = function() {
                return callSimState('logFileURL');
            };

            $scope.runningMessage = function() {
                return callSimState('runningMessage')
                    || 'Completed frame: ' + $scope.simState.getFrameCount();
            };

            $scope.start = function() {
                // The available jobRunModes can change. Default to parallel if
                // the current jobRunMode doesn't exist
                var j = appState.models[$scope.simState.model];
                if (j && j.jobRunMode && j.jobRunMode in authState.jobRunModeMap === false) {
                    j.jobRunMode = 'parallel';
                }
                if ($scope.startFunction) {
                    $scope.startFunction();
                }
                else {
                    appState.saveChanges($scope.simState.model, $scope.simState.runSimulation);
                }
            };

            $scope.stateAsText = function() {
                if ($scope.errorMessage()) {
                    return stringsService.formatTemplate(
                        SIREPO.APP_SCHEMA.strings.genericSimulationError
                    );
                }
                return callSimState('stateAsText');
            };

            $scope.stopButtonLabel = function() {
                return stringsService.stopButtonLabel($scope.simState.model);
            };
        },
    };
});

SIREPO.app.service('plotToPNG', function() {

    function screenshotElement(element, isVisible) {
        return $(element).find(`.sr-screenshot${isVisible ? ':visible' : ''}`)[0];
    }

    this.destroyVTK = element => {
        const el = screenshotElement(element);
        if (el && el.srUpdateCanvas) {
            el.srUpdateCanvas = null;
        }
    };

    this.downloadPNG = function(el, outputHeight, fileName) {
        el = screenshotElement(el, true);
        if (el.srUpdateCanvas) {
            el.srUpdateCanvas();
        }
        html2canvas(el, {
            scale: outputHeight / $(el).height(),
            backgroundColor: '#ffffff',
            ignoreElements: (element) => element.matches("path.pointer.axis") || element.matches('text.glyphicon')
        }).then(canvas => {
            canvas.toBlob(function(blob) {
                saveAs(blob, fileName);
            });
        });
    };

    this.hasScreenshotElement = element => {
        return screenshotElement(element) ? true : false;
    };

    this.initVTK = (element, renderer) => {
        const el = screenshotElement(element);
        if (! el) {
            throw new Error('Missing sr-screenshot class within vtk element');
        }
        el.srUpdateCanvas = () => {
            renderer.getRenderWindow().render();
        };
    };

});

SIREPO.app.service('fileUpload', function(authState, msgRouter) {
    this.uploadFileToUrl = function(file, args, uploadUrl, callback) {
        var fd = new FormData();
        fd.append('file', file);
        if (args) {
            for (var k in args) {
                fd.append(k, args[k]);
            }
        }
        if (file.size > authState.max_message_bytes) {
            callback({error: `File of size=${file.size} bytes is greater than maximum allowable size=${authState.max_message_bytes} bytes`});
            return;
        }
        //TODO(robnagler) formData needs to be handled properly
        msgRouter.send(uploadUrl, fd, {
            transformRequest: angular.identity,
            headers: {'Content-Type': undefined}
        }).then(
            function(response) {
                callback(response.data);
            },
            function(response) {
                callback(
                    {
                        error: `File upload failed due to server error (status=${response.status || 'unknown'})`
                    }
                );
            },
        );
    };
});

SIREPO.app.service('mathRendering', function() {
    // Renders math expressions in a plain text string using KaTeX.
    // The math expressions must be tightly bound by $, ex. $E = mc^2$
    var RE = /\$[\-\(\w\\](.*\S)?\$/;

    function encodeHTML(text) {
        return $('<div />').text(text).html();
    }

    this.mathAsHTML = function(text, options) {
        if (! this.textContainsMath(text)) {
            return encodeHTML(text);
        }
        var parts = [];
        //if (! options) {
        //    options = {};
        //}
        //options.output = 'html';
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
                throw new Error('invalid math expression');
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

SIREPO.app.service('plotRangeService', function(appState, panelState, requestSender) {
    var self = this;
    var runningModels = [];

    function setFieldRange(controller, prefix, model, field) {
        setRange(model, prefix, controller.fieldRange[field]);
    }

    function setRange(model, prefix, range) {
        if (range) {
            model[prefix + 'Size'] = range[1] - range[0];
            model[prefix + 'Offset'] = (range[0] + range[1]) / 2;
        }
    }

    function setRunningState(name) {
        appState.models[name].isRunning = 1;
        if (runningModels.indexOf(name) < 0) {
            runningModels.push(name);
        }
    }

    function setVerticalFieldRange(controller, model) {
        var range = null;
        ['y1', 'y2', 'y3'].forEach(function(f) {
            var r1 = controller.fieldRange[model[f]];
            if (! range) {
                range = r1;
            }
            else if (r1) {
                if (r1[0] < range[0]) {
                    range[0] = r1[0];
                }
                if (r1[1] > range[1]) {
                    range[1] = r1[1];
                }
            }
        });
        setRange(model, 'vertical', range);
    }

    self.computeFieldRanges = function(controller, name, percentComplete) {
        if (controller.simState.isProcessing()) {
            setRunningState(name);
        }
        // this assumes all models share same range parameters
        if (percentComplete == 100 && ! controller.isComputingRanges) {
            controller.fieldRange = null;
            controller.isComputingRanges = true;
            setRunningState(name);
            requestSender.sendAnalysisJob(
                appState,
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
                },
                {
                    method: 'compute_particle_ranges',
                    modelName: name,
                },
            );
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
                if (model.y) {
                    setFieldRange(controller, 'vertical', model, model.y);
                }
                else {
                    setVerticalFieldRange(controller, model);
                }
            }
        }
    };
});

SIREPO.app.directive('simList', function(appState, requestSender) {
    return {
        restrict: 'A',
        scope: {
            code: '@',
            model: '=',
            field: '=',
            route: '@',
        },
        template: `
            <span data-loading-spinner data-sentinel="simList">
              <div style="white-space: nowrap">
                <select style="display: inline-block" class="form-control" data-ng-model="model[field]" data-ng-options="item.simulationId as itemName(item) disable when item.invalidMsg for item in simList"></select>

                <button type="button" style="padding: 3px 10px 5px 10px; margin-top: -1px" title="View Simulation" class="btn btn-default" data-ng-click="openSimulation()"><span class="glyphicon glyphicon-eye-open"></span></button>
              </div>
            </span>
        `,
        controller: function($scope) {
            $scope.simList = null;

            // special processing of the item's name if necessary
            $scope.itemName = function(item) {
                return item.invalidMsg ? `${item.name} <${item.invalidMsg}>` : item.name;
            };

            $scope.openSimulation = function() {
                if ($scope.model && $scope.model[$scope.field]) {
                    requestSender.openSimulation(
                        $scope.code,
                        $scope.route,
                        $scope.model[$scope.field]
                    );
                }
            };
            appState.whenModelsLoaded($scope, function() {
                requestSender.sendStatefulCompute(
                    appState,
                    function(data) {
                        if (appState.isLoaded() && data.simList) {
                            $scope.simList = data.simList.sort(function(a, b) {
                                return a.name.localeCompare(b.name);
                            });
                        }
                    },
                    {
                        method: 'get_' + $scope.code + '_sim_list'
                    }
                );
            });
        },
    };
});

SIREPO.app.service('utilities', function($window, $interval, $interpolate, $rootScope) {

    var self = this;

    this.arrayMin = array => SIREPO.UTILS.arrayMin(array);

    this.arrayMax = array => SIREPO.UTILS.arrayMax(array);

    this.modelFieldID = function(modelName, fieldName) {
        return 'model-' + modelName + '-' + fieldName;
    };

    this.viewLogicName = function(viewName) {
        if (! viewName) {
            return null;
        }
        return `data-${this.camelToKebabCase(viewName)}-view`;
    };

    this.ngModelForElement = function(el) {
        return angular.element(el).controller('ngModel');
    };

    this.ngModelForInput = function(modelName, fieldName) {
        return angular.element($('.' + this.modelFieldID(modelName, fieldName) + ' input')).controller('ngModel');
    };

    this.isWide = function() {
        return $window.innerWidth > 767;
    };

    // font utilities
    this.fontSizeFromString = function(fsString) {
        if (! fsString) {
            return 0;
        }
        var units = ['px', 'pt'];
        for (var uIdx in units) {
            var unit = units[uIdx];
            var fs = parseFloat(fsString.substring(0, fsString.indexOf(unit)));
            if (! isNaN(fs)) {
                return fs;
            }
        }
        return NaN;
    };

    this.interpolateString = (str, context) => {
        context.SIREPO = SIREPO;
        return $interpolate(str)(context);
    };

    this.wordSplits = str => SIREPO.UTILS.wordSplits(str);

    this.splitCommaDelimitedString = function(str, parser=null) {
        let a = str.split(/\s*,\s*/);
        if (! parser) {
            return a;
        }
        return a.map(x => parser(x));
    };

    this.camelToKebabCase = function(v) {
        if (v.toUpperCase() == v) {
            return v.toLowerCase();
        }
        v = v.charAt(0).toLowerCase() + v.slice(1);
        v = v.replace(/\_/g, '-');
        return v.replace(/([A-Z])/g, '-$1').toLowerCase();
    };

    this.fullscreenActive = false;

    this.isFullscreen = () => {
        return this.fullscreenActive;
    };

    this.exitFullscreen = () => {
        this.fullscreenActive = false;
        $rootScope.$broadcast('sr-close-full-screen');
    };

    this.openFullscreen = (scope) => {
        this.fullscreenActive = true;
        scope.$emit('sr-full-screen');
    };

    this.buildSearch = (scope, element, searchClass, supportsMulti) => {
        function findToken(text, caretPos) {
            let n = 0;
            const tokens = text.split(/\s+/);
            for (let i = 0; i < tokens.length; ++i) {
                const t = tokens[i];
                const j = text.indexOf(t, n);
                const k = j + t.length;
                if (caretPos >= j && caretPos <= k) {
                    return {index: i, token: t};
                }
                n = k;
            }
            return null;
        }

        const s = $(element).find(`.${searchClass}`);
        // avoid spelling suggestions in Safari browser blocking the selection list
        s.attr('spellcheck', false);
        s.autocomplete({
            classes: {
                'ui-autocomplete': 'sr-dropdown',
            },
            delay: 0,
            minLength: supportsMulti ? 1 : 2,
            select: (e, ui) => {
                scope.$apply(() => {
                    // the jqueryui autocomplete wants to display the value instead of the
                    // label when a select happens. This keeps the label in place
                    e.preventDefault();
                    let val = ui.item.label;
                    if (supportsMulti) {
                        const tokens = s.val().split(/\s+/);
                        const t = findToken(s.val(), e.target.selectionStart);
                        if (t) {
                            tokens[t.index] = val;
                        }
                        val = tokens.join(' ');
                    }
                    s.val(val);
                    if (scope.onSelect) {
                        scope.onSelect()(ui.item.value);
                    }
                    // send a change event to trigger parsers
                    s[0].dispatchEvent(new Event('change'));
                });
            },
            focus: (e, ui) => {
                s.val(ui.item.label);
                return false;
            },
            source: (req, res) => {
                const text = req.term;
                const l = [...scope.list].sort((a, b) => (a.label < b.label ? -1 : 1));
                if (! supportsMulti) {
                    res(l.filter(x => {
                        return x.label.toLowerCase().includes(text.toLowerCase());
                    }));
                    return;
                }
                const t = findToken(text, s.get(0).selectionStart);
                if (t) {
                    res(l.filter(x => x.label.includes(t.token)));
                }
            },
        });
        const modal = s.closest('div[role="dialog"]');
        if (modal.length) {
            // required to have the popup appear on top and scroll along with the modal content
            s.autocomplete('option', 'appendTo', modal);
        }
        const search = {
            container: s,
            update: () => {
                s.autocomplete('option', 'disabled', ! scope.list.length);
            },
        };
        scope.$watch('list', () => {
            search.update();
        });
        return search;
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
            debounceInterval = $interval(later, milliseconds || SIREPO.debounce_timeout, 1);
        };
    };

    this.indexArray = size => SIREPO.UTILS.indexArray(size);

    this.normalize = seq => SIREPO.UTILS.normalize(seq);

    // Returns a minimal formatted json-like value
    this.objectToText = function(obj) {
        return JSON
            .stringify(obj, undefined, 2)
            .replace(/^(\{|\[)\s*\n/g, '')
            .replace(/\:\s*(\{|\[)\s*$/gm, ':')
            .replace(/^\s*(\}|\]|\[),?\s*\n/gm, '')
            .replace(/\n\s*(\}|\])\s*/g, '')
            .replace(/,$/gm, '')
            .replace(/\"/g, '');
    };

    this.roundToPlaces = (val, p) => SIREPO.UTILS.roundToPlaces(val, p);

    // Returns 0 for empty or NaN values
    this.safeNumber = (value) => {
        return ! value || isNaN(value)
             ? 0
             : value;
    };

    this.trimText = function(text, maxLines, maxLength) {
        const m = text.match(new RegExp(`^(.*\n+){${maxLines}}`));
        if (m) {
            if (m[0].length < maxLength) {
                return m[0].replace(/\n$/, '');
            }
        }
        if (text.length > maxLength) {
            return text.substring(0, maxLength);
        }
        return text;
    };

    this.unique = (arr, equals) => SIREPO.UTILS.unique(arr, equals);
});

SIREPO.app.directive('srItemHolder', function() {
    return {
        transclude: true,
        scope: {
            handleDrop: '&',
            handleDragenter: '&',
        },
        template: `
            <div class="sr-item-holder" data-sr-droppable=""
              data-handle-drop="drop(item)" data-handle-dragenter="dragenter()">
              <div data-ng-transclude=""></div>
             </div>
         `,
        controller: function($scope) {
            $scope.drop = item => {
                $scope.handleDrop({
                    item: item,
                });
            };
            $scope.dragenter = () => {
                $scope.handleDragenter();
            };
        },
    };
});

SIREPO.srDragEffect = 'move';

SIREPO.app.directive('srDraggable', function() {
    return {
        restrict: 'A',
        scope: {
            item: '=srDraggable',
            handleSelected: '&',
        },
        controller: function ($scope, $element) {
            $scope.item.isDragging = false;
            $element[0].draggable = true;

            function setSelected() {
                $scope.handleSelected({
                    item: $scope.item,
                });
                $scope.$applyAsync();
            }

            $element.on('dragstart', e => {
                e.dataTransfer.effectAllowed = SIREPO.srDragEffect;
                e.dataTransfer.setData('text', JSON.stringify($scope.item));
                $element.addClass('sr-hide-menu');
            });
            $element.on('drag', e => {
                if (! $scope.item.isDragging) {
                    $scope.item.isDragging = true;
                    $element.addClass('sr-dragging');
                    setSelected();
                }
            });
            $element.on('dragend', e => {
                $scope.item.isDragging = false;
                $element.removeClass('sr-dragging');
                $element.removeClass('sr-hide-menu');
                $scope.$applyAsync();
            });
            // need handlers for both to support desktop and tablet
            $element.on('click', setSelected);
            $element.on('mousedown', setSelected);
            $scope.$on('$destroy', () => {
                $element.off();
            });
        },
    };
});

SIREPO.app.directive('srDroppable', function() {
    return {
        restrict: 'A',
        scope: {
            handleDrop: '&',
            handleDragenter: '&',
        },
        controller: function($scope, $element) {
            let dragCount = 0;

            function updateCount(newCount) {
                dragCount = newCount;
                if (dragCount === 0) {
                    $element.removeClass('sr-drag-over');
                }
                else if (dragCount === 1) {
                    $element.addClass('sr-drag-over');
                }
            }

            $element.on('dragenter', e => {
                e.preventDefault();
                $scope.handleDragenter();
                if (e.currentTarget == $element[0]) {
                    updateCount(dragCount + 1);
                }
                $scope.$applyAsync();
            });
            $element.on('dragover', e => {
                e.preventDefault();
                e.dataTransfer.dropEffect = SIREPO.srDragEffect;
            });
            $element.on('dragleave', e => {
                if (e.currentTarget == $element[0]) {
                    updateCount(dragCount - 1);
                }
            });
            $element.on('drop', e => {
                e.preventDefault();
                updateCount(0);
                const item = JSON.parse(e.dataTransfer.getData('text'));
                if (item) {
                    $scope.handleDrop({
                        item: item,
                    });
                    $scope.$applyAsync();
                }
            });
            $scope.$on('$destroy', () => {
                $element.off();
            });
        },
    };
});

SIREPO.app.directive('dateTimePicker', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `<input data-ng-style="style" type="datetime-local" class="form-control" ng-model="dateTime" required >`,
        controller: function($scope, timeService) {
            $scope.style = window.safari ? {
                // work-around safari browser formatting problem
                'line-height': '14px',
            } : {};
            $scope.dateTime = $scope.model[$scope.field] ? timeService.unixTimeToDate($scope.model[$scope.field]) : '';
            $scope.$watch('dateTime', function(newTime, oldTime) {
                if (
                    (newTime && !oldTime) ||
                    (newTime && newTime.getTime() !== oldTime.getTime())
                ) {
                    $scope.model[$scope.field] = timeService.unixTime(newTime);
                }
            });

            $scope.$watch('model.' + $scope.field, function(newTime, oldTime) {
                if (newTime !== oldTime) {
                    $scope.dateTime = timeService.unixTimeToDate(newTime);
                }
            });
        }
    };
});

SIREPO.app.directive('presetTimePicker', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            modelName: '=',
        },
        template: `
          <button type="button" class="btn btn-info btn-xs" data-ng-click="setSearchTimeLastHour()">Last Hour</button>
          <button type="button" class="btn btn-info btn-xs" data-ng-click="setSearchTimeLastDay()">Last Day</button>
          <button type="button" class="btn btn-info btn-xs" data-ng-click="setSearchTimeLastWeek()">Last Week</button>
          <button type="button" class="btn btn-info btn-xs" data-ng-click="setSearchTimeMaxRange()">All Time</button>
        `,
        controller: function(appState, timeService, $scope) {
            $scope.setDefaultStartStopTime = () => {
                if (!$scope.model.searchStartTime && !$scope.model.searchStopTime) {
                    $scope.setSearchTimeLastHour();
                    appState.saveChanges($scope.modelName);
                }
            };

            $scope.setSearchTimeLastDay = () => {
                $scope.model.searchStartTime = timeService.roundUnixTimeToMinutes(timeService.unixTimeOneDayAgo());
                $scope.model.searchStopTime = timeService.roundUnixTimeToMinutes(timeService.unixTimeNow());
            };

            $scope.setSearchTimeLastHour = () => {
                $scope.model.searchStartTime = timeService.roundUnixTimeToMinutes(timeService.unixTimeOneHourAgo());
                $scope.model.searchStopTime = timeService.roundUnixTimeToMinutes(timeService.unixTimeNow());
            };

            $scope.setSearchTimeLastWeek = () => {
                $scope.model.searchStartTime = timeService.roundUnixTimeToMinutes(timeService.unixTimeOneWeekAgo());
                $scope.model.searchStopTime = timeService.roundUnixTimeToMinutes(timeService.unixTimeNow());
            };

            $scope.setSearchTimeMaxRange = () => {
                $scope.model.searchStartTime = timeService.roundUnixTimeToMinutes(60);
                $scope.model.searchStopTime = timeService.roundUnixTimeToMinutes(timeService.unixTimeNow());
            };

            $scope.setDefaultStartStopTime();
        }
    };
});

SIREPO.app.directive('slider', function(appState, panelState) {
    const sliderClass = 'sr-slider';
    return {
        restrict: 'A',
        scope: {
            field: '<',
            model: '=',
            min: '<',
            max: '<',
            steps: '<',
            space: '<',
            isRange: '@',
            isMulti: '@',
        },
        template: `
            <div class="${ sliderClass }" style="margin-top: 10px"></div>
            <div data-ng-show="showLabels" style="display:flex; justify-content:space-between;">
                <span>{{ formatFloat(min) }}</span>
                <span style="font-weight: bold;">{{ display(model[field]) }}</span>
                <span>{{ formatFloat(max) }}</span>
            </div>
        `,
        controller: function($scope, $element) {
            let slider = null;
            // don't show labels for simple cases, ex. opacity
            $scope.showLabels = !($scope.min === 0 && $scope.max === 1);

            function buildSlider() {
                const s = $($element).find('.' + sliderClass);
                if (! s.length) {
                    return null;
                }
                s.slider({
                    classes: {
                        'ui-slider': 'ui-widget-header',
                        'ui-slider-range': $scope.isRange ? 'sr-range-slider' : '',
                        'ui-slider-handle': $scope.isRange ? '' : 'sr-range-slider',
                    },
                    min: $scope.min,
                    max: $scope.max,
                    range: $scope.isMulti ? true : 'min',
                    slide: (e, ui) => {
                        // prevent handles from having the same value
                        if ($scope.isMulti && ui.values[0] === ui.values[1]) {
                            return false;
                        }
                        $scope.$apply(() => {
                            if ($scope.isMulti) {
                                $scope.model[$scope.field][ui.handleIndex] = ui.value;
                            }
                            else {
                                $scope.model[$scope.field] = ui.value;
                            }
                        });
                    },
                    step: ($scope.max - $scope.min) / ($scope.steps - 1),
                });
                // ensure the max is constant
                s.slider('instance').max = $scope.max;
                s.slider('option', $scope.isMulti ? 'values' : 'value', $scope.model[$scope.field]);
                slider = s;
            }

            function didChange(newValues, oldValues) {
                return newValues != null && newValues !== oldValues;
            }

            function updateRange(newValue, oldValue) {
                if (slider && didChange(newValue, oldValue)) {
                    slider.slider('option', 'min', $scope.min);
                    slider.slider('option', 'max', $scope.max);
                    slider.slider('option', 'step', ($scope.max - $scope.min) / ($scope.steps - 1));
                }
            }


            $scope.display = (val) => {
                if (Array.isArray(val)) {
                    if ($scope.space === 'log' && $scope.min > 0) {
                        val = val.map(v =>
                            SIREPO.UTILS.linearToLog(v, $scope.min, $scope.max, $scope.steps - 1));
                    }
                    return val.map(v => $scope.formatFloat(v));
                }
                return $scope.formatFloat(val);
            };

            $scope.formatFloat = (val) => SIREPO.UTILS.formatFloat(val, 4);

            panelState.waitForUI(buildSlider);

            $scope.$watch(
                'model[field]',
                (newValue, oldValue) => {
                    if (didChange(newValue, oldValue)) {
                        slider.slider('option', $scope.isMulti ? 'values' : 'value', newValue);
                    }
                }
            );

            $scope.$watch('min', updateRange);
            $scope.$watch('max', updateRange);
            $scope.$watch('steps', updateRange);

            $scope.$on('$destroy', () => {
                if (slider) {
                    slider.slider('destroy');
                    slider = null;
                }
            });
        },
    };
});

SIREPO.app.directive('supportEmail', function() {
    return {
        restrict: 'A',
        scope: {},
        template: '<a data-ng-href="mailto:{{:: supportEmail }}">{{:: supportEmail }}</a>',
        controller: function($scope) {
            $scope.supportEmail = SIREPO.APP_SCHEMA.feature_config.support_email;
        },
    };
});
