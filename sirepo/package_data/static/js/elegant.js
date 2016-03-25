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
                $(selector).show(delay);
            else
                $(selector).hide(delay);
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

    // watch path depends on appState as an attribute of $scope
    $scope.appState = appState;
    $scope.$watch('appState.models.bunch.longitudinalMethod', function () {
        updateLongitudinalFields(400);
    });
});

app.controller('LatticeController', function(appState, panelState, $window, $scope) {
    var self = this;
    self.appState = appState;
    self.beamlines = [
        {
            name: 'LINACA',
            items: [
                30, 'LINA10', 'ZWAKE',
            ],
            l: 9.0,
            count: 60,
        },
        {
            name: 'LINACB',
            items: [
                80, 'LINB10', 'ZWAKE',
            ],
            l: 24.0,
            count: 160,
        },
        {
            name: 'BL',
            items: [
                 1, 'Q', 'LINACA', 'W1', 'B1', 'L1', 'W2', 'B2', 'L2', 'W3', 'B3', 'L1', 'W4', 'B4', 'W5', 'L3', 'LINACB', 'PF',
            ],
            l: 42.23,
            count: 231,
        },
        {
            name: 'BL2',
            items: [
                1, 'L1', 'W1', 'B1', 'L1', 'W2', 'B2', 'L2', 'W3', 'B3', 'L1',
            ],
            l: 9.23,
            count: 10,
        },
    ];

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

    function itemsToString(items) {
        var res = '(';
        var count = items[0];
        for (var i = 1; i < items.length; i++) {
            var item = items[i];
            if (Array.isArray(item)) {
                res += itemsToString(item);
            }
            else {
                res += item;
                if (i == items.length - 1)
                    res += ')';
                else
                    res += ',';
            }
        }
        if (count > 1)
            res = '(' + count + '*' + res + ')';
        return res;
    }

    var emptyElements = [];

    self.getElements = function() {
        if (appState.isLoaded)
            return appState.models.elements;
        return emptyElements;
    }

    self.beamlineDescription = function(beamline) {
        return itemsToString(beamline.items);
    };

    self.editItem = function(type, item) {
        appState.models[type] = item;
        panelState.showModalEditor(type, $scope);
    };

    self.itemBend = function(item) {
        if (angular.isDefined(item.angle))
            return (item.angle * 180 / Math.PI).toFixed(1);
        return '';
    };

    self.itemDescription = function(type, item) {
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

    self.itemLength = function(item) {
        if (angular.isDefined(item.l))
            return numFormat(item.l, 'm');
        return '';
    };

    self.setActiveTab = function(name) {
        self.activeTab = name;
    };

    self.activeTab = 'basic';

    self.titleForName = function(name) {
        return APP_SCHEMA.view[name].description;
    };

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

    self.createElement = function(name) {
        $('#srw-newBeamlineElement-editor').modal('hide');
        var schema = APP_SCHEMA.model[name];
        var model = {
            //TODO(pjm): give it unique "name"?
        };
        var fields = Object.keys(schema);
        for (var i = 0; i < fields.length; i++) {
            var f = fields[i];
            if (schema[f][2] != undefined)
                model[f] = schema[f][2];
        }
        appState.models[name] = model;
        panelState.showModalEditor(name, $scope);
    };

    self.newElement = function() {
        $('#srw-newBeamlineElement-editor').modal('show');
    };

    self.splitPaneHeight = function() {
        var w = $($window);
        var el = $('.s-split-pane-frame');
        return (w.height() - el.offset().top - 15) + 'px';
    };

    self.toggleElement = function(element) {
        element.expanded = ! element.expanded;
    };

    $scope.$on('modelChanged', function(e, name) {
        if (name != name.toUpperCase())
            return;
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
    });

    $(window).resize(resize);
    $scope.$on('$destroy', function() {
        $(window).off('resize', resize);
    });
});

app.directive('appHeader', function(appState) {
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
              '<li><a href data-target="#srw-simulation-editor" data-toggle="modal"><span class="glyphicon glyphicon-plus"></span> New</a></li>',
            '</ul>',
        ].join(''),
        controller: function($scope) {
            $scope.isLoaded = function() {
                return appState.isLoaded();
            };
        },
    };
});
