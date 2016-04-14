'use strict';

app_local_routes.lattice = '/lattice/:simulationId';

app.config(function($routeProvider, localRoutesProvider) {
    var localRoutes = localRoutesProvider.$get();
    $routeProvider
        .when(localRoutes.source, {
            controller: 'ElegantSourceController as source',
            templateUrl: '/static/html/elegant-source.html?' + SIREPO_APP_VERSION,
        })
        .when(localRoutes.lattice, {
            controller: 'LatticeController as lattice',
            templateUrl: '/static/html/elegant-lattice.html?' + SIREPO_APP_VERSION,
        });
});

app.controller('ElegantSourceController', function(appState, $scope) {
    var self = this;
    var longitudinalFields = ['sigma_s', 'sigma_dp', 'dp_s_coupling', 'emit_z', 'beta_z', 'alpha_z'];

    function showFields(fields, delay) {
        for (var i = 0; i < longitudinalFields.length; i++) {
            var f = longitudinalFields[i];
            var selector = '.model-bunch-' + f;
            if (fields.indexOf(f) >= 0)
                $(selector).closest('.form-group').show(delay);
            else
                $(selector).closest('.form-group').hide(delay);
        }
    }

    function updateLongitudinalFields(delay) {
        if (! appState.isLoaded())
            return;
        var method = appState.models['bunch']['longitudinalMethod'];
        if (parseInt(method) == 1)
            showFields(['sigma_s', 'sigma_dp', 'dp_s_coupling'], delay);
        else if (parseInt(method) == 2)
            showFields(['sigma_s', 'sigma_dp', 'alpha_z'], delay);
        else
            showFields(['emit_z', 'beta_z', 'alpha_z'], delay);
    }

    self.bunchReports = [
        {id: 1},
        {id: 2},
        {id: 3},
        {id: 4},
    ];

    self.handleModalShown = function() {
        updateLongitudinalFields(0);
    };

    var modelAccessByItemId = {};

    self.modelAccess = function(itemId) {
        if (modelAccessByItemId[itemId])
            return modelAccessByItemId[itemId];
        var modelKey = 'bunchReport' + itemId;
        modelAccessByItemId[itemId] = {
            modelKey: modelKey,
            getData: function() {
                return appState.models[modelKey];
            },
        };
        return modelAccessByItemId[itemId];
    };

    // watch path depends on appState as an attribute of $scope
    $scope.appState = appState;
    $scope.$watch('appState.models.bunch.longitudinalMethod', function () {
        updateLongitudinalFields(400);
    });
});

app.controller('LatticeController', function(appState, panelState, $window, $scope) {
    var self = this;
    self.appState = appState;

    self.activeTab = 'basic';

    self.basicNames = [
        'CSBEND', 'CSRCSBEND', 'CSRDRIFT',
        'DRIF', 'ECOL', 'KICKER',
        'MARK', 'QUAD', 'SEXT',
        'WATCH', 'WIGGLER',
    ];

    self.advancedNames = [
        'ALPH', 'BMAPXY', 'BUMPER', 'CENTER',
        'CEPL', 'CHARGE', 'CLEAN', 'CORGPIPE',
        'CWIGGLER', 'DSCATTER', 'EDRIFT', 'ELSE',
        'EMATRIX', 'EMITTANCE', 'ENERGY', 'FLOOR',
        'FMULT', 'FRFMODE', 'FTABLE', 'FTRFMODE',
        'GFWIGGLER', 'HISTOGRAM', 'HKICK', 'HMON',
        'IBSCATTER', 'ILMATRIX', 'KOCT', 'KPOLY',
        'KQUAD', 'KQUSE', 'KSBEND', 'KSEXT',
        'LMIRROR', 'LSCDRIFT', 'LSRMDLTR', 'LTHINLENS',
        'MAGNIFY', 'MALIGN', 'MAPSOLENOID', 'MATR',
        'MATTER', 'MAXAMP', 'MBUMPER', 'MHISTOGRAM',
        'MODRF', 'MONI', 'MRFDF', 'MULT',
        'NIBEND', 'NISEPT', 'OCTU', 'PEPPOT',
        'PFILTER', 'QUFRINGE', 'RAMPP', 'RAMPRF',
        'RBEN', 'RCOL', 'RECIRC', 'REFLECT',
        'REMCOR', 'RFCA', 'RFCW', 'RFDF',
        'RFMODE', 'RFTM110', 'RFTMEZ0', 'RIMULT',
        'RMDF', 'ROTATE', 'SAMPLE', 'SBEN',
        'SCATTER', 'SCMULT', 'SCRAPER', 'SCRIPT',
        'SOLE', 'SREFFECTS', 'STRAY', 'TFBDRIVER',
        'TFBPICKUP', 'TMCF', 'TRCOUNT', 'TRFMODE',
        'TRWAKE', 'TUBEND', 'TWISS', 'TWLA',
        'TWMTA', 'TWPL', 'UKICKMAP', 'VKICK',
        'VMON', 'WAKE', 'ZLONGIT', 'ZTRANSVERSE',
    ];

    self.allNames = self.basicNames.concat(self.advancedNames).sort();

    self.activeBeamline = null;

    function beamlineChanged() {
        console.log('beamline changed: ', appState.models.elegantBeamline.name);
        var items = []
        self.activeBeamline = items;
        if (! appState.models.beamlines)
            appState.models.beamlines = [];
        appState.models.beamlines.push({
            name: appState.models.elegantBeamline.name,
            items: items,
            l: 0,
            count: 0,
        });
    }

    function elementChanged(name) {
        var elementGroup;
        if (! appState.models.elements)
            appState.models.elements = [];
        var elements = appState.models.elements;

        for (var i = 0; i < elements.length; i++) {
            if (elements[i].type == name) {
                elementGroup = elements[i];
                break;
            }
        }
        if (! elementGroup) {
            elementGroup = {
                type: name,
                expanded: true,
                items: [],
            };
            elements.push(elementGroup);
            elementGroup.items.push(appState.models[name]);
        }
        else {
            var found = false;
            for (var i = 0; i < elementGroup.items.length; i++) {
                if (elementGroup.items[i].name == appState.models[name].name) {
                    found = true;
                    break;
                }
            }
            if (! found)
                elementGroup.items.push(appState.models[name]);
        }
        elements.sort(function(a, b) {
            if (a.name > b.name)
                return 1;
            if (a.name < b.name)
                return -1
            return 0;
        });
        appState.saveChanges('elements');
    }

    function isElementModel(name) {
        return name == name.toUpperCase();
    }

    function itemsToString(items) {
        var res = '(';
        if (! items.length)
            res += ' ';
        for (var i = 0; i < items.length; i++) {
            var item = items[i];
            res += items[i].name;
            if (i != items.length - 1)
                res += ',';
        }
        res += ')';
        return res;
    }

    //TODO(pjm): use library for this
    function numFormat(num, units) {
        if (num < 1) {
            num *= 1000;
            units = 'm' + units;
        }
        return num.toFixed(0) + units;
    }

    function resize() {
        //TODO(pjm): causes $digest already in progress
        $scope.$apply();
    }

    var emptyElements = [];

    self.addToBeamline = function(item) {
        self.activeBeamline.push(self.beamlineNewItem(item.name));
    };

    self.beamlineDescription = function(beamline) {
        return itemsToString(beamline.items);
    };

    self.createElement = function(type) {
        $('#s-newBeamlineElement-editor').modal('hide');
        var schema = APP_SCHEMA.model[type];
        var model = {
            //TODO(pjm): give it unique "name"?
        };
        // set model defaults from schema
        var fields = Object.keys(schema);
        for (var i = 0; i < fields.length; i++) {
            var f = fields[i];
            if (schema[f][2] != undefined)
                model[f] = schema[f][2];
        }
        self.editElement(type, model);
    };

    self.editElement = function(type, item) {
        appState.models[type] = item;
        panelState.showModalEditor(type, $scope);
    };

    self.elementBend = function(item) {
        if (angular.isDefined(item.angle))
            return (item.angle * 180 / Math.PI).toFixed(1);
        return '';
    };

    self.elementDescription = function(type, item) {
        if (! item)
            return 'null';
        var schema = APP_SCHEMA.model[type];
        var res = '';
        var fields = Object.keys(item).sort();
        for (var i = 0; i < fields.length; i++) {
            var f = fields[i];
            if (f == 'name' || f == 'l' || f == 'angle' || f.indexOf('$') >= 0)
                continue;
            if (angular.isDefined(item[f]))
                if (schema[f][2] != item[f])
                    res += (res.length ? ',' : '') + f + '=' + item[f];
        }
        return res;
    };

    self.elementLength = function(item) {
        if (angular.isDefined(item.l))
            return numFormat(item.l, 'm');
        return '';
    };

    self.getElements = function() {
        if (appState.isLoaded)
            return appState.models.elements;
        return emptyElements;
    }

    self.setActiveTab = function(name) {
        self.activeTab = name;
    };

    self.titleForName = function(name) {
        return APP_SCHEMA.view[name].description;
    };

    self.newBeamline = function() {
        appState.models['elegantBeamline'] = {};
        panelState.showModalEditor('elegantBeamline', $scope);
    };

    self.newElement = function() {
        $('#s-newBeamlineElement-editor').modal('show');
    };

    self.panelTitle = function(value) {
        return value;
    };

    self.splitPaneHeight = function() {
        var w = $($window);
        var el = $('.s-split-pane-frame');
        return (w.height() - el.offset().top - 15) + 'px';
    };

    self.toggleElement = function(element) {
        element.expanded = ! element.expanded;
    };

    $scope.$on('cancelChanges', function(e, name) {
        if (isElementModel(name))
            appState.cancelChanges('elements');
    });

    $scope.$on('modelChanged', function(e, name) {
        if (name == 'elegantBeamline')
            beamlineChanged();
        if (isElementModel(name))
            elementChanged(name);
    });

    $(window).resize(resize);
    $scope.$on('$destroy', function() {
        $(window).off('resize', resize);
    });


    // beamline editor
    var nextId = 100;
    var selectedItem = null;

    self.beamlineIsSelected = function(item) {
        if (selectedItem)
            return item.id == selectedItem.id;
        return false;
    };

    self.beamlineNewItem = function(name) {
        console.log('beamlineNewItem: ', name);
        var item = {
            name: name,
            id: nextId++,
        };
        selectedItem = item;
        return item;
    };

    self.beamlineSetSelectedItem = function(item) {
        selectedItem = item;
    };


});

app.directive('appHeader', function(appState, panelState) {
    return {
        restirct: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: [
            '<div class="navbar-header">',
              '<a class="navbar-brand" href data-ng-click="nav.openSection(\'simulations\')"><img style="width: 40px; margin-top: -10px;" src="/static/img/radtrack.gif" alt="radiasoft"></a>',
              '<div class="navbar-brand"><a href data-ng-click="nav.openSection(\'simulations\')">elegant</a></div>',
            '</div>',
            '<div data-app-header-left="nav"></div>',
            '<ul class="nav navbar-nav navbar-right" data-ng-show="isLoaded()">',
              '<li data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
              '<li data-ng-class="{active: nav.isActive(\'lattice\')}"><a href data-ng-click="nav.openSection(\'lattice\')"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>',
            '</ul>',
            '<ul class="nav navbar-nav navbar-right" data-ng-show="nav.isActive(\'simulations\')">',
              '<li><a href data-ng-click="showSimulationModal"><span class="glyphicon glyphicon-plus"></span> New</a></li>',
            '</ul>',
        ].join(''),
        controller: function($scope) {
            $scope.isLoaded = function() {
                return appState.isLoaded();
            };
            $scope.showSimulationModal = function() {
                panelState.showModalEditor('simulation');
            };
        },
    };
});

app.directive('beamlineEditor', function() {
    return {
        restirct: 'A',
        scope: {
            lattice: '=controller',
            beamline: '=',
        },
        template: [
            '<div class="panel-body cssFade" data-ng-drop="true" data-ng-drop-success="dropPanel($data)" data-ng-drag-start="dragStart($data)">',
              '<p class="lead text-center"><small><em>drag and drop elements here to define the beamline</em></small></p>',
              '<div data-ng-click="selectItem(item)" data-ng-drag="true" data-ng-drag-data="item" data-ng-repeat="item in beamline" class="elegant-beamline-element" data-ng-class="{\'elegant-beamline-element-group\': item.inRepeat }" data-ng-drop="true" data-ng-drop-success="dropItem($index, $data)">',
                '<div class="s-drop-left">&nbsp;</div>',
                '<span data-ng-if="item.repeatCount" class="s-count">{{ item.repeatCount }}</span>',
                '<div style="display: inline-block; cursor: move; -moz-user-select: none" class="badge elegant-beamline-element-with-count" data-ng-class="{\'elegant-item-selected\': isSelected(item)}"><span>{{ item.name }}</span></div>',
              '</div>',
              '<div class="elegant-beamline-element s-last-drop" data-ng-drop="true" data-ng-drop-success="dropLast($data)"><div class="s-drop-left">&nbsp;</div></div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var isDragNew = false;

            $scope.dragStart = function(data) {
                isDragNew = ! data.id;
                $scope.selectItem(data);
            };
            $scope.dropItem = function(index, data) {
                if (! data)
                    return;
                if (data.id) {
                    var curr = $scope.beamline.indexOf(data);
                    if (curr < index)
                        index--;
                    $scope.beamline.splice(curr, 1);
                }
                else {
                    var lastIndex = $scope.beamline.length - 1;
                    if (isDragNew && $scope.beamline[lastIndex].name == data.name) {
                        data = $scope.beamline[lastIndex];
                        $scope.beamline.splice(lastIndex, 1);
                    }
                    else
                        data = $scope.lattice.beamlineNewItem(data.name);
                }
                $scope.selectItem(data);
                $scope.beamline.splice(index, 0, data);
            };
            $scope.dropLast = function(data) {
                if (! data || ! data.id)
                    return;
                var curr = $scope.beamline.indexOf(data);
                $scope.beamline.splice(curr, 1);
                $scope.beamline.push(data);
                $scope.selectItem(data);
            };
            $scope.dropPanel = function(data) {
                if (! data || data.id)
                    return;
                $scope.beamline.push($scope.lattice.beamlineNewItem(data.name));
            };
            $scope.isSelected = function(item) {
                return $scope.lattice.beamlineIsSelected(item);
            };
            $scope.selectItem = function(item) {
                $scope.lattice.beamlineSetSelectedItem(item);
            };
        },
    };
});
