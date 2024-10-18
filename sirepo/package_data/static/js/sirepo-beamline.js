'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.factory('beamlineService', function(appState, panelState, validationService, $window, $rootScope) {
    var self = this;
    var canEdit = true;
    //TODO(pjm) keep in sync with template_common.DEFAULT_INTENSITY_DISTANCE
    // consider moving to "constant" section of schema
    var DEFAULT_INTENSITY_DISTANCE = 20;
    self.activeItem = null;

    // Try to detect mobile/tablet devices using Mozilla recommendation below
    // https://developer.mozilla.org/en-US/docs/Web/HTTP/Browser_detection_using_the_user_agent
    var isTouchscreen = /Mobi|Silk/i.test($window.navigator.userAgent);

    self.copyElement = function(item) {
        var newItem = appState.clone(item);
        newItem.id = appState.maxId(appState.models.beamline) + 1;
        newItem.showPopover = true;
        appState.models.beamline.splice(
            appState.models.beamline.indexOf(item) + 1,
            0,
            newItem);
        self.dismissPopup();
    };

    self.createWatchModel = itemId => {
        const n = self.watchpointReportName(itemId);
        if (! appState.models[n]) {
            appState.models[n] = appState.setModelDefaults(
                appState.cloneModel('initialIntensityReport'),
                'watchpointReport',
            );
        }
    };

    self.dismissPopup = function() {
        $('.srw-beamline-element-label').popover('hide');
    };

    self.getActiveItemTitle = function() {
        if (self.activeItem && self.activeItem.title) {
            return self.activeItem.title;
        }
        return '';
    };

    self.getItemById = function(id) {
        var savedModelValues = appState.applicationState();
        if(! id || ! savedModelValues.beamline) {
            return null;
        }
        return savedModelValues.beamline.filter(function (item) {
            return item.id == id;
        })[0];
    };

    self.getReportTitle = function(modelName, itemId) {
        if (itemId == 0
            && SIREPO.INITIAL_INTENSITY_REPORT_TITLE) {
            return SIREPO.INITIAL_INTENSITY_REPORT_TITLE;
        }
        var savedModelValues = appState.applicationState();
        if (itemId && savedModelValues.beamline) {
            for (var i = 0; i < savedModelValues.beamline.length; i += 1) {
                if (savedModelValues.beamline[i].id == itemId) {
                    return 'Intensity ' + savedModelValues.beamline[i].title + ', '
                        + savedModelValues.beamline[i].position + ' m';
                }
            }
        }
        var model = savedModelValues[modelName];
        var distance = '';
        if (model && 'distanceFromSource' in model) {
            distance = ', ' + model.distanceFromSource + ' m';
        }
        else if (appState.isAnimationModelName(modelName)) {
            if (savedModelValues.beamline.length) {
                var item = model.watchpointId ? self.getItemById(model.watchpointId) : savedModelValues.beamline[savedModelValues.beamline.length - 1];
                distance = ', ' + item.position + ' m';
            }
        }
        else if (modelName == 'initialIntensityReport' || (modelName == 'watchpointReport' && itemId == 0)) {
            if (savedModelValues.beamline && savedModelValues.beamline.length) {
                distance = ', ' + savedModelValues.beamline[0].position + ' m';
            }
            else {
                if ('models' in appState && 'simulation' in appState.models && 'distanceFromSource' in appState.models.simulation) {
                    distance = ', ' + appState.models.simulation.distanceFromSource + ' m';
                }
                else {
                    distance = ', ' + DEFAULT_INTENSITY_DISTANCE + ' m';
                }
            }
            modelName = 'initialIntensityReport';
        }
        return appState.viewInfo(modelName).title + distance;
    };

    self.getWatchItems = function() {
        if (appState.isLoaded()) {
            var beamline = appState.applicationState().beamline;
            var res = [];
            self.createWatchModel(0);
            for (var i = 0; i < beamline.length; i++) {
                if (self.isWatchpointReportElement(beamline[i])) {
                    res.push(beamline[i]);
                    self.createWatchModel(beamline[i].id);
                }
            }
            return res;
        }
        return [];
    };
    self.getWatchReports = function() {
        var items = self.getWatchItems();
        var rpts = [];
        for(var iIndex = 0; iIndex < items.length;  ++iIndex) {
            rpts.push(self.watchpointReportName(items[iIndex].id));
        }
        return rpts;
    };
    self.getWatchIds = function() {
        return self.getWatchItems().map(function (item) {
            return item.id;
        });
    };

    self.isActiveItem = function(itemType) {
        return self.activeItem && self.activeItem.type == itemType;
    };

    self.isActiveItemValid = function() {
        return self.isItemValid(self.activeItem);
    };

    self.isBeamlineValid = function() {
        var models = appState.models;
        if (! models.beamline ) {
            return true;
        }
        for (var i = 0; i < models.beamline.length; ++i) {
            var item = models.beamline[i];
            if (! self.isItemValid(item)) {
                return false;
            }
        }
        return true;
    };

    self.isEditable = function() {
        return canEdit;
    };

    self.isItemValid = function(item) {
        if (! item) {
            return false;
        }
        var type = item.type;
        var fields = SIREPO.APP_SCHEMA.model[type];
        for (var field in fields) {
            var fieldType = fields[field][1];
            if (! validationService.validateFieldOfType(item[field], fieldType)) {
                return false;
            }
        }
        return true;
    };

    self.isTouchscreen = function() {
        return isTouchscreen;
    };

    self.isWatchpointReportElement = item => {
        if (SIREPO.BEAMLINE_WATCHPOINT_REPORT_ELEMENTS) {
            return SIREPO.BEAMLINE_WATCHPOINT_REPORT_ELEMENTS.includes(item.type);
        }
        return item.type == 'watch';
    };

    self.removeActiveItem = function() {
        if (self.activeItem) {
            self.removeElement(self.activeItem);
        }
    };

    self.removeElement = function(item) {
        self.dismissPopup();
        appState.models.beamline.splice(appState.models.beamline.indexOf(item), 1);
    };

    self.setActiveItem = function(item) {
        self.activeItem = item;
    };

    self.setEditable = function(value) {
        canEdit = value;
    };

    self.setupWatchpointDirective = function($scope) {
        var modelKey = self.watchpointReportName($scope.itemId);
        $scope.modelAccess = {
            modelKey: modelKey,
            getData: function() {
                return appState.models[modelKey];
            },
        };

        $scope.reportTitle = function() {
            return self.getReportTitle('watchpointReport', $scope.itemId);
        };
    };

    self.watchBeamlineField = function($scope, model, beamlineFields, callback, filterOldUndefined) {
        $scope.beamlineService = self;
        beamlineFields.forEach(function(f) {
            $scope.$watch('beamlineService.activeItem.' + f, function (newValue, oldValue) {
                if (appState.isLoaded() && newValue !== null && newValue !== undefined && newValue != oldValue) {
                    if (filterOldUndefined && oldValue === undefined) {
                        return;
                    }
                    var item = self.activeItem;
                    if (item && item.type == model) {
                        callback(item);
                    }
                }
            });
        });
    };

    self.watchpointReportName = function(id) {
        return (SIREPO.BEAMLINE_WATCHPOINT_MODEL_PREFIX || 'watchpointReport') + id;
    };
    return self;
});

SIREPO.app.directive('beamlineBuilder', function(appState, beamlineService, panelState) {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            parentController: '=beamlineBuilder',
            beamlineModels: '=',
            showActiveWatchpoints: '<',
            activeWatchpointTitle: '@',
       },
        template: `
            <div class="srw-beamline text-center" data-ng-drop="true" data-ng-drop-success="dropComplete($data, $event)">
              <div data-ng-transclude=""></div>
              <p class="lead text-center">{{ beamlineName }} definition area
                <button title="Download beamline as PNG" class="btn btn-default btn-sm" data-ng-if="showPNGDownloadLink()" data-ng-click="createBeamlinePNG()"><span class="glyphicon glyphicon-cloud-download"></span></button><br>
                <small data-ng-if="beamlineService.isEditable()"><em>drag and drop optical elements here to define the {{ beamlineName }}</em></small></p>
              <div class="srw-beamline-container">
                <div style="display: inline-block" data-ng-repeat="item in getBeamline() track by item.id">
                  <div data-ng-if="$first" class="srw-drop-between-zone" data-ng-drop="true" data-ng-drop-success="dropBetween(0, $data, $event)"> </div><div data-ng-drag="::beamlineService.isEditable()" data-ng-drag-data="item" data-item="item" data-beamline-item=""
                    data-show-active-watchpoints="showActiveWatchpoints" data-active-watchpoint-title="{{ activeWatchpointTitle }}" data-is-watchpoint-active="isWatchpointActive(item)" data-set-watchpoint-active="setWatchpointActive(item)"
                    class="srw-beamline-element {{ beamlineService.isTouchscreen() ? '' : 'srw-hover' }}"
                    data-ng-class="{'srw-disabled-item': item.isDisabled, 'srw-beamline-invalid': ! beamlineService.isItemValid(item)}" oncontextmenu="return false">
                  </div><div class="srw-drop-between-zone" data-ng-attr-style="width: {{ dropBetweenWidth }}px"  data-ng-drop="true" data-ng-drop-success="dropBetween($index + 1, $data, $event)"> </div>
                </div>
            </div>
            <div class="row"><div class="srw-popup-container-lg col-sm-10 col-md-8 col-lg-6"></div></div>
              <div class="row">
                <form>
                  <div class="col-md-6 col-sm-8 pull-right" data-ng-show="checkIfDirty()">
                    <button data-ng-click="saveBeamlineChanges()" class="btn btn-primary sr-button-save-cancel" data-ng-show="beamlineService.isBeamlineValid()">Save</button>
                    <button data-ng-click="cancelBeamlineChanges()" class="btn btn-default sr-button-save-cancel">Cancel</button>
                  </div>
                </form>
              </div>
            </div>
        `,
        controller: function($scope, $rootScope) {
            $scope.beamlineName = (SIREPO.APP_SCHEMA.strings.beamlineTabName || 'beamline').toLowerCase();
            $scope.setWatchpointActive = function(item) {
                if(! $scope.parentController.setWatchpointActive) {
                    return;
                }
                return $scope.parentController.setWatchpointActive(item);
            };
            $scope.isWatchpointActive = function(item) {
                return $scope.parentController.isWatchpointActive(item);
            };

            $scope.beamlineService = beamlineService;
            $scope.dropBetweenWidth = 20;
            function addItem(item) {
                var newItem = appState.clone(item);
                newItem.id = appState.maxId(appState.models.beamline) + 1;
                newItem.showPopover = true;
                if (appState.models.beamline.length) {
                    newItem.position = parseFloat(appState.models.beamline[appState.models.beamline.length - 1].position) + 1;
                }
                else {
                    if ('distanceFromSource' in appState.models.simulation) {
                        newItem.position = appState.models.simulation.distanceFromSource;
                    }
                    else {
                        newItem.position = 20;
                    }
                }
                if (newItem.type == 'ellipsoidMirror') {
                    newItem.firstFocusLength = newItem.position;
                }
                if (beamlineService.isWatchpointReportElement(newItem)) {
                    beamlineService.createWatchModel(newItem.id);
                }
                appState.models.beamline.push(newItem);
                beamlineService.dismissPopup();
            }

            $scope.cancelBeamlineChanges = function() {
                beamlineService.dismissPopup();
                appState.cancelChanges($scope.beamlineModels);
            };
            $scope.createBeamlinePNG = function() {
                var container = $('.srw-beamline-container');
                // adds special class which formats beamline for printing
                container.addClass('srw-beamline-container-png');
                domtoimage.toBlob(container[0])
                    .then(function(blob) {
                        container.removeClass('srw-beamline-container-png');
                        window.saveAs(blob, panelState.fileNameFromText(appState.models.simulation.name, 'png'));
                    })
                    .catch(function(error) {
                        container.removeClass('srw-beamline-container-png');
                    });
            };
            $scope.dropComplete = function(data) {
                if (data && ! data.id) {
                    addItem(data);
                }
            };
            $scope.getBeamline = function() {
                if (appState.models.beamline) {
                    $scope.dropBetweenWidth = appState.models.beamline.length > 8 ? 10 : 20;
                }
                return appState.models.beamline;
            };
            $scope.hasBeamlineElements = function() {
                if (appState.models.beamline) {
                    return appState.models.beamline.length > 0;
                }
                return false;
            };
            $scope.dropBetween = function(index, data, event) {
                if (! data) {
                    return;
                }
                var item;
                if (data.id) {
                    beamlineService.dismissPopup();
                    if (event.event.ctrlKey) {
                        item = appState.clone(data);
                        item.id = appState.maxId(appState.models.beamline) + 1;
                    }
                    else {
                        var curr = appState.models.beamline.indexOf(data);
                        if (curr < index) {
                            index--;
                        }
                        appState.models.beamline.splice(curr, 1);
                        item = data;
                    }
                }
                else {
                    // move last item to this index
                    item = appState.models.beamline.pop();
                }
                appState.models.beamline.splice(index, 0, item);
                if (appState.models.beamline.length > 1) {
                    if (index === 0) {
                        item.position = parseFloat(appState.models.beamline[1].position) - 0.5;
                    }
                    else if (index === appState.models.beamline.length - 1) {
                        item.position = parseFloat(appState.models.beamline[appState.models.beamline.length - 1].position) + 0.5;
                    }
                    else {
                        item.position = Math.round(100 * (parseFloat(appState.models.beamline[index - 1].position) + parseFloat(appState.models.beamline[index + 1].position)) / 2) / 100;
                    }
                }
            };
            $scope.checkIfDirty = function() {
                var isDirty = false;
                if ($scope.beamlineModels) {
                    var savedValues = appState.applicationState();
                    var models = appState.models;
                    $scope.beamlineModels.forEach(function(name) {
                        if (! appState.deepEquals(savedValues[name], models[name])) {
                            isDirty = true;
                        }
                    });
                }
                return isDirty;
            };
            $scope.showPNGDownloadLink = function() {
                return appState.isLoaded() && appState.models.beamline.length;
            };

            function isWatchpointReportModelName(name) {
                return name.indexOf('watchpointReport') >= 0
                    || name.indexOf('beamlineAnimation') >= 0;
            }

            $scope.saveBeamlineChanges = function() {
                // sort beamline based on position
                appState.models.beamline.sort(function(a, b) {
                    return parseFloat(a.position) - parseFloat(b.position);
                });
                // culls and saves watchpoint models
                var watchpoints = {
                    // the first beamineAnimation is the initialIntensityReport equivalent
                    beamlineAnimation0: true,
                };
                for (var i = 0; i < appState.models.beamline.length; i++) {
                    var item = appState.models.beamline[i];
                    if (beamlineService.isWatchpointReportElement(item)) {
                        watchpoints[beamlineService.watchpointReportName(item.id)] = true;
                    }
                }
                var savedModelValues = appState.applicationState();
                for (var modelName in appState.models) {
                    if (isWatchpointReportModelName(modelName) && ! watchpoints[modelName]) {
                        // deleted watchpoint, remove the report model
                        delete appState.models[modelName];
                        delete savedModelValues[modelName];
                        continue;
                    }
                    if (isWatchpointReportModelName(modelName)) {
                        savedModelValues[modelName] = appState.cloneModel(modelName);
                    }
                }
                $scope.parentController.prepareToSave();
                appState.saveChanges($scope.beamlineModels);
            };

            $rootScope.$on('saveLattice', (e, d) => {
                $scope.saveBeamlineChanges();
            });
        },
    };
});

SIREPO.app.directive('beamlineIcon', function() {
    return {
        scope: {
            item: '=',
        },
        template: `
            <div data-ng-if="::isSVG">
              <data-ng-include src="::iconUrl" data-onload="iconLoaded()"/>
            </div>
            <div data-ng-if="::! isSVG">
              <img class="srw-beamline-item-icon" data-ng-attr-src="{{ ::iconUrl }}"/>
            </div>
        `,
        controller: function($scope, $element) {
            var adjustmentsByType = {
                // height, x, y
                aperture: [15, 5, 5],
                crl: [0, 5, 2],
                crystal: [-20, 28, -20],
                ellipsoidMirror: [0, 10, 10],
                fiber: [15],
                grating: [-20, 20, -5],
                lens: [5],
                mask: [5, 0, 5],
                mirror: [15, 5, 12],
                mirror2: [15],
                obstacle: [-15, 10, -2],
                sample: [20, -10, 10],
                sphericalMirror: [10, 10, 7],
                splitter: [-10, 5, 0],
                telescope: [5],
                toroidalMirror: [15, 0, 7],
                watch: [0, 15, 10],
                zonePlate: [20, -10, -5],
            };

            function iconUrl() {
                // use <icon> or <type>.svg
                var icon = $scope.item.icon || $scope.item.type;
                if (icon.indexOf('.') < 0) {
                    icon += '.svg';
                }
                if (icon.indexOf('.svg') >= 0) {
                    $scope.isSVG = icon.search('.svg');
                    icon = '/static/svg/' + icon;
                }
                else {
                    icon = '/static/img/' + icon;
                }
                return icon + SIREPO.SOURCE_CACHE_KEY;
            }

            $scope.iconLoaded = function () {
                var vb = $($element).find('svg.srw-beamline-item-icon').prop('viewBox').baseVal;
                vb.width = 100;
                vb.height = 50;
                var adjust = adjustmentsByType[$scope.item.type];
                if (adjust) {
                    vb.height += adjust[0] || 0;
                    vb.x -= adjust[1] || 0;
                    vb.y -= adjust[2] || 0;
                }
            };

            $scope.iconUrl = iconUrl();
        },
    };
});

SIREPO.app.directive('beamlineItem', function(beamlineService, $timeout, $rootScope) {
    return {
        scope: {
            item: '=',
            showActiveWatchpoints: '<',
            activeWatchpointTitle: '@',
            isWatchpointActive: '&',
            setWatchpointActive: '&',
        },
        template: `
            <span class="srw-beamline-badge badge">{{ item.position ? item.position + ' m' : (item.position === 0 ? '0 m' : '⚠ ') }}</span>
            <span data-ng-if="showItemButtons()" data-ng-click="beamlineService.removeElement(item)" class="srw-beamline-close-icon srw-beamline-toggle glyphicon glyphicon-remove-circle" title="Delete Element"></span>
            <span data-ng-if="showItemButtons()" data-ng-click="beamlineService.copyElement(item)" class="srw-beamline-copy-icon srw-beamline-toggle glyphicon glyphicon-duplicate" title="Copy Element"></span>
            <span data-ng-if="showItemButtons() && showActiveIcon(item)" data-ng-click="setWatchpointActive(item)" class="srw-beamline-report-icon srw-beamline-toggle glyphicon glyphicon-ok" data-ng-class="{'srw-beamline-report-icon-active': isWatchpointActive(item)}" title="{{ activeWatchpointTitle }}"></span>
            <span data-ng-if="showItemButtons()" data-ng-click="toggleDisableElement(item)" class="srw-beamline-disable-icon srw-beamline-toggle glyphicon" data-ng-class="{'glyphicon-ok-circle': item.isDisabled, ' glyphicon-ban-circle': ! item.isDisabled}" title="{{ enableItemToggleTitle() }}"></span>
            <div class="srw-beamline-image">
              <span data-beamline-icon="" data-item="item"></span>
            </div>
            <div data-ng-attr-id="srw-item-{{ item.id }}" class="srw-beamline-element-label">{{ (beamlineService.isItemValid(item) ? '' : '⚠ ') + item.title }}<span class="caret"></span></div>
        `,
        controller: function($scope, $element) {
            $scope.beamlineService = beamlineService;
            $scope.showItemButtons = function() {
                return beamlineService.isEditable();
            };
            $scope.toggleDisableElement = function(item) {
                if (item.isDisabled) {
                    delete item.isDisabled;
                }
                else {
                    item.isDisabled = true;
                }
            };
            $scope.showActiveIcon = function(item) {
                return item.type === 'watch' && $scope.showActiveWatchpoints;
            };
        },
        link: function(scope, element) {
            var el = $(element).find('.srw-beamline-element-label');
            el.on('click', togglePopover);
            el.popover({
                trigger: 'manual',
                html: true,
                placement: 'bottom',
                container: '.srw-popup-container-lg',
                viewport: { selector: '.srw-beamline'},
                content: function() {
                    return $('#srw-' + scope.item.type + '-editor');
                },
                // adds sr-beamline-popover class to standard template
                template: '<div class="popover sr-beamline-popover" role="tooltip"><div class="arrow"></div><h3 class="popover-title"></h3><div class="popover-content"></div></div>'
            }).on('show.bs.popover', function() {
                $('.srw-beamline-element-label').not(el).popover('hide');
                beamlineService.setActiveItem(scope.item);
                $rootScope.$broadcast('sr.setActivePage', scope.item.type, 0);
            }).on('shown.bs.popover', function() {
                $('.popover-content .form-control').first().select();
            }).on('hide.bs.popover', function() {
                beamlineService.setActiveItem(null);
                var editor = el.data('bs.popover').getContent();
                // return the editor to the editor-holder so it will be available for the
                // next element of this type
                if (editor) {
                    $('.srw-editor-holder').append(editor);
                }
            });

            function togglePopover() {
                if (beamlineService.activeItem) {
                    beamlineService.setActiveItem(null);
                    // clears the active item and invoke watchers before setting new active item
                    scope.$apply();
                }
                el.popover('toggle');
                scope.$apply();
            }
            scope.enableItemToggleTitle = function () {
                return (scope.item.isDisabled ? 'Enable' : 'Disable') + ' Element';
            };
            if (beamlineService.isTouchscreen()) {
                var hasTouchMove = false;
                $(element).bind('touchstart', function() {
                    hasTouchMove = false;
                });
                $(element).bind('touchend', function() {
                    if (! hasTouchMove) {
                        togglePopover();
                    }
                    hasTouchMove = false;
                });
                $(element).bind('touchmove', function() {
                    hasTouchMove = true;
                });
            }
            else {
                $(element).find('.srw-beamline-image').click(function() {
                    togglePopover();
                });
            }
            if (scope.item.showPopover) {
                delete scope.item.showPopover;
                // when the item is added, it may have been dropped between items
                // don't show the popover until the position has been determined
                $timeout(function() {
                    var position = el.parent().position().left;
                    var width = $('.srw-beamline-container').width();
                    var itemWidth = el.width();
                    if (position + itemWidth > width) {
                        var scrollPoint = $('.srw-beamline-container').scrollLeft();
                        $('.srw-beamline-container').scrollLeft(position - width + scrollPoint + itemWidth);
                    }
                    el.popover('show');
                }, 500);
            }
            scope.$on('$destroy', function() {
                if (beamlineService.isTouchscreen()) {
                    $(element).bind('touchstart', null);
                    $(element).bind('touchend', null);
                    $(element).bind('touchmove', null);
                }
                else {
                    $(element).find('.srw-beamline-image').off();
                    $(element).off();
                }
                var el = $(element).find('.srw-beamline-element-label');
                el.off();
                var popover = el.data('bs.popover');
                // popover has a memory leak with $tip user_data which needs to be cleaned up manually
                if (popover && popover.$tip) {
                    popover.$tip.removeData('bs.popover');
                }
                el.popover('destroy');
            });
        },
    };
});

SIREPO.app.directive('beamlineItemEditor', function(appState, beamlineService) {
    return {
        scope: {
            modelName: '@',
            parentController: '=',
        },
        template: `
            <div>
              <button type="button" class="close" data-ng-click="beamlineService.dismissPopup()"><span>&times;</span></button>
              <div data-help-button="{{ title }}"></div>
              <form name="form" class="form-horizontal" autocomplete="off" novalidate>
                <div class="sr-beamline-element-title">{{ title }}</div>
                <div data-advanced-editor-pane="" data-view-name="modelName" data-model-data="modelAccess" data-parent-controller="parentController"></div>
                <div class="form-group">
                  <div class="col-sm-offset-6 col-sm-3">
                    <button ng-click="beamlineService.dismissPopup()" style="width: 100%" type="submit" class="btn btn-primary" data-ng-disabled="! form.$valid">Close</button>
                  </div>
                </div>
                <div class="form-group" data-ng-show="beamlineService.isTouchscreen() && beamlineService.isEditable()">
                  <div class="col-sm-offset-6 col-sm-3">
                    <button ng-click="beamlineService.removeActiveItem()" style="width: 100%" type="submit" class="btn btn-danger">Delete</button>
                  </div>
                </div>
              </form>
            </div>
        `,
        controller: function($scope) {
            $scope.beamlineService = beamlineService;
            $scope.title = appState.viewInfo($scope.modelName).title;
            $scope.modelAccess = {
                modelKey: $scope.modelName,
                getData: function() {
                    return beamlineService.activeItem;
                },
            };
            $scope.cancelItemChanges = function() {
                appState.cancelChanges('beamline');
                beamlineService.dismissPopup();
            };
        },
    };
});

SIREPO.app.directive('beamlineReports', function(beamlineService) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div data-column-for-aspect-ratio="initialIntensityReport">
              <div data-report-panel="3d" data-request-priority="1" data-model-name="initialIntensityReport" data-panel-title="{{ beamlineService.getReportTitle('initialIntensityReport') }}"></div>
            </div>
            <div data-ng-if="! item.isDisabled" data-ng-repeat="item in beamlineService.getWatchItems() track by item.id">
              <div data-watchpoint-report="" data-item-id="item.id"></div>
              <div class="clearfix hidden-xl" data-ng-hide="$index % 2"></div>
              <div class="clearfix visible-xl" data-ng-hide="($index - 1) % 3"></div>
            </div>
        `,
        controller: function($scope) {
            $scope.beamlineService = beamlineService;
        },
    };
});

SIREPO.app.directive('beamlineToolbar', function(appState) {
    return {
        restrict: 'A',
        scope: {
            toolbarItemNames: '=beamlineToolbar',
            parentController: '=',
        },
        template: `
            <div class="row">
              <div class="col-sm-12">
                <div class="text-center bg-info sr-toolbar-holder">
                  <div class="sr-toolbar-section" data-ng-repeat="section in ::sectionItems">
                    <div class="sr-toolbar-section-header"><span class="sr-toolbar-section-title">{{ ::section[0] }}</span></div>
                    <span data-ng-repeat="item in ::section[1]" class="srw-toolbar-button srw-beamline-image" data-ng-drag="true" data-ng-drag-data="item">
                      <span data-beamline-icon="" data-item="item"></span>{{ ::item.title }}
                    </span>
                  </div>
                  <span data-ng-repeat="item in ::standaloneItems" class="srw-toolbar-button srw-beamline-image" data-ng-drag="true" data-ng-drag-data="item">
                    <span data-beamline-icon="" data-item="item"></span>{{ ::item.title }}
                  </span>
                </div>
              </div>
            </div>
            <div class="srw-editor-holder" style="display:none">
              <div data-ng-repeat="item in ::allItems">
                <div class="sr-beamline-editor" id="srw-{{ ::item.type }}-editor" data-beamline-item-editor="" data-model-name="{{ ::item.type }}" data-parent-controller="parentController" ></div>
              </div>
            </div>
        `,
        controller: function($scope) {
            $scope.allItems = [];
            function addItem(name, items) {
                var featureName = name + '_in_toolbar';
                if (featureName in SIREPO.APP_SCHEMA.feature_config) {
                    if (! SIREPO.APP_SCHEMA.feature_config[featureName]) {
                        return;
                    }
                }
                var item = appState.setModelDefaults({type: name}, name);
                var MIRROR_TYPES = ['mirror', 'sphericalMirror', 'ellipsoidMirror', 'toroidalMirror'];
                if (MIRROR_TYPES.indexOf(item.type) >= 0) {
                    item.title = item.title.replace(' Mirror', '');
                }
                items.push(item);
                $scope.allItems.push(item);
            }

            function initToolbarItems() {
                var sections = [];
                var standalone = [];
                $scope.toolbarItemNames.forEach(function(section) {
                    var items = [];
                    if (angular.isArray(section)) {
                        section[1].forEach(function(name) {
                            addItem(name, items);
                        });
                        sections.push([section[0], items]);
                    }
                    else {
                        addItem(section, standalone);
                    }
                });
                $scope.sectionItems = sections;
                $scope.standaloneItems = standalone;
            }

            initToolbarItems();
        },
    };
});

SIREPO.app.directive('watchpointModalEditor', function(beamlineService) {
    return {
        scope: {
            parentController: '=',
            itemId: '=',
        },
        template: `
            <div data-modal-editor="" view-name="{{ modelName }}" data-parent-controller="parentController" data-model-data="modelAccess" data-modal-title="reportTitle()"></div>
        `,
        controller: function($scope) {
            $scope.modelName = $scope.itemId ? 'watchpointReport' : 'initialIntensityReport';
            beamlineService.setupWatchpointDirective($scope);
        },
    };
});

SIREPO.app.directive('watchpointReport', function(beamlineService) {
    return {
        scope: {
            itemId: '=',
        },
        template: `
            <div data-column-for-aspect-ratio="{{ watchpointModelName }}">
              <div data-report-panel="{{ modelAccess.getData().reportType || '3d' }}" data-request-priority="2" data-model-name="{{ modelName }}" data-model-data="modelAccess" data-panel-title="{{ reportTitle() }}"></div>
            </div>
        `,
        controller: function($scope) {
            $scope.modelName = $scope.itemId ? 'watchpointReport' : 'initialIntensityReport';
            beamlineService.setupWatchpointDirective($scope);
            $scope.watchpointModelName = $scope.modelAccess.modelKey;
        },
    };
});

SIREPO.app.directive('watchPointList', function(appState, beamlineService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <select class="form-control" data-ng-model="model[field]" data-ng-options="item.id as wpOptionTitle(item) for item in watchItems"></select>
        `,
        controller: function($scope, $element) {
            $scope.watchItems = null;
            $scope.wpOptionTitle = function(item) {
                return item.title + ' (' + item.position + 'm)';
            };
            function updateWatchItems() {
                // need a clone of the items because the ngOptions modifies the values
                $scope.watchItems = appState.clone(beamlineService.getWatchItems());
            }
            appState.whenModelsLoaded($scope, updateWatchItems);
            $scope.$on('modelChanged', updateWatchItems);
        },
    };
});

SIREPO.app.directive('beamlineAnimation', function(appState, frameCache, panelState, persistentSimulation) {
    return {
        restrict: 'A',
        scope: {},
        template: `
          <div class="col-sm-3">
            <div data-canceled-due-to-timeout-alert="simState"></div>
            <div data-simulation-stopped-status="simState"></div>
            <div class="col-sm-12" data-simulation-status-timer="simState"></div>
            <button class="btn btn-default pull-right" data-ng-click="start()" data-ng-show="simState.isStopped()">Start New Simulation</button>
            <button class="btn btn-default pull-right" data-ng-click="simState.cancelSimulation()" data-ng-show="simState.isProcessing()">End Simulation</button>
          </div>
          <div class="col-sm-5 col-md-4 col-lg-3" style="margin-top: 1ex">
            <div data-pending-link-to-simulations="" data-sim-state="simState"></div>
            <div data-ng-show="simState.isStateRunning()" data-sim-state-progress-bar="" data-sim-state="simState"></div>
            <div data-ng-show="simState.isStateError()">{{ simState.errorMessage() }}</div>
          </div>
          <div style="margin-bottom: 1em" class="clearfix"></div>
          <div data-ng-repeat="report in reports" data-ng-if="simState.hasFrames()">
            <div data-watchpoint-report="" data-item-id="report.id" data-ng-if="showReport(report)"></div>
            <div class="clearfix hidden-xl" data-ng-hide="($index + 1) % 2"></div>
            <div class="clearfix visible-xl" data-ng-hide="($index + 1) % 3"></div>
          </div>
        `,
        controller: function($scope, $rootScope) {
            let errorMessage;
            $scope.reports = [];
            $scope.simScope = $scope;
            $scope.simComputeModel = 'beamlineAnimation';
            $scope.$on('framesCleared', () => {
                $scope.reports = [];
            });

            $scope.showReport = report => {
                if ($scope.simState.isStateRunning()) {
                    return true;
                }
                return frameCache.getFrameCount(report.modelAccess.modelKey) !== SIREPO.nonDataFileFrame;
            };

            $scope.start = function() {
                $rootScope.$broadcast('saveLattice', appState.models);
                appState.models.simulation.framesCleared = false;
                appState.saveChanges(
                    [$scope.simState.model, 'simulation'],
                    $scope.simState.runSimulation);
            };

            $scope.simHandleStatus = (data) => {
                function getReport(id) {
                    for(const r of $scope.reports) {
                        if (id === r.id) {
                            return r;
                        }
                    }
                    return null;
                }

                if (appState.models.simulation.framesCleared) {
                    return;
                }
                errorMessage = data.error;
                if (! data.outputInfo) {
                    return;
                }

                for (let i = 0; i < data.outputInfo.length; i++) {
                    let info = data.outputInfo[i];
                    if (! getReport(info.id)) {
                        $scope.reports.push(
                            {
                                id: info.id,
                                modelAccess: {
                                    modelKey: info.modelKey,
                                },
                            }
                        );
                    }
                    frameCache.setFrameCount(
                        info.waitForData ? SIREPO.nonDataFileFrame : (info.frameCount || 1),
                        info.modelKey
                    );
                    panelState.setWaiting(info.modelKey, ! ! info.waitForData);
                }
                frameCache.setFrameCount(data.frameCount || 0);
            };

            $scope.simState = persistentSimulation.initSimulationState($scope);
            $scope.simState.errorMessage = () => errorMessage;

            $scope.$on('modelChanged', (e, name) => {
                if (! appState.isReportModelName(name)) {
                    if (frameCache.getFrameCount() > 0) {
                        frameCache.setFrameCount(0);
                        appState.models.simulation.framesCleared = true;
                        appState.saveQuietly('simulation');
                    }
                }
            });
        },
    };
});
