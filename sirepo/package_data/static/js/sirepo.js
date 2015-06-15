"use strict";



      // 50x60 canvas
      var graphics = {};
      graphics['draw_aperture'] = function (ctx) {
            ctx.clearRect(0, 0, 50, 60);
            ctx.fillStyle="#000000";
            ctx.fillRect(23, 0, 5, 24);
            ctx.fillRect(23, 36, 5, 24);
        };
      graphics['draw_mirror'] = function(ctx) {
            ctx.clearRect(0, 0, 50, 60);
            ctx.fillStyle="#bdd7ee";
            ctx.fillRect(23, 0, 5, 60);
            ctx.strokeStyle = "#000000";
            ctx.strokeRect(23, 0, 5, 60);
        };
      graphics['draw_lens'] = function(ctx, x, y, width, height) {
            if (x === undefined) {
                ctx.clearRect(0, 0, 50, 60);
                x = 20;
                y = 0;
                width = 10;
                height = 60;
            }
            ctx.fillStyle="#ddee00";
            ctx.strokeStyle = "#000000";
            ctx.beginPath();
            ctx.moveTo(x + width / 2, y);
            ctx.bezierCurveTo(x + width, y + 10, x + width, height - 10, x + width / 2, height);
            ctx.bezierCurveTo(x, height - 10, x, y + 10, x + width / 2, y);
            ctx.fill();
            ctx.stroke();
        };
      graphics['draw_crl'] = function(ctx) {
            ctx.clearRect(0, 0, 50, 60);
            ctx.fillStyle="#333333";
            ctx.fillRect(15, 0, 20, 60);
            graphics.draw_lens(ctx, 10, 0, 10, 60);
            graphics.draw_lens(ctx, 20, 0, 10, 60);
            graphics.draw_lens(ctx, 30, 0, 10, 60);
        };
      graphics['draw_obstacle'] = function(ctx) {
            ctx.clearRect(0, 0, 50, 60);
            ctx.fillStyle="#669999";
            ctx.fillRect(15, 20, 20, 20);
            ctx.strokeStyle = "#000000";
            ctx.strokeRect(15, 20, 20, 20);
        };
      graphics['draw_watch'] = function(ctx) {
            ctx.clearRect(0, 0, 50, 60);
            var radius = 15;
            ctx.strokeStyle = "#000000";
            ctx.beginPath();
            ctx.moveTo(5, 30);
            ctx.bezierCurveTo(15, 30 + radius, 35, 30 + radius, 45, 30);
            ctx.bezierCurveTo(35, 30 - radius, 15, 30 - radius, 5, 30);
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(25, 30, radius - 5, 0, 2 * Math.PI);
            ctx.fillStyle="#a52a2a";
            ctx.fill();
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(25, 30, 4, 0, 2 * Math.PI);
            ctx.fillStyle="#000000";
            ctx.fill();
        };

      graphics.redraw_all_icons = function() {
        window.setTimeout(function() {
            // aperture
            $(".srw-aperture-canvas").each(function(index, element) {
              graphics.draw_aperture(element.getContext("2d"));
            });
            // mirror
            $(".srw-mirror-canvas").each(function(index, element) {
              graphics.draw_mirror(element.getContext("2d"));
            });
            // lens
            $(".srw-lens-canvas").each(function(index, element) {
              graphics.draw_lens(element.getContext("2d"));
            });
            // CRL
            $(".srw-crl-canvas").each(function(index, element) {
              graphics.draw_crl(element.getContext("2d"));
            });
            // obstacle
            $(".srw-obstacle-canvas").each(function(index, element) {
              graphics.draw_obstacle(element.getContext("2d"));
            });
            // watch
            $(".srw-watch-canvas").each(function(index, element) {
              graphics.draw_watch(element.getContext("2d"));
            });
          }, 1);
      }

      $(function() {
        graphics.redraw_all_icons();
    });

    $(function() {
        if (Modernizr.touch)
            ;
        else
            $('[data-toggle="tooltip"]').tooltip();
    });

    // meta data
    var _ENUM = {
        Flux: ['Flux', 'Flux per Unit Surface'],
        IntegrationMethod: ['Manual', 'Auto-Undulator', 'Auto-Wiggler'],
        Polarization: ['Linear Horizontal', 'Linear Vertical', 'Linear 45 degrees', 'Linear 135 degrees', 'Circular Right', 'Circular Left', 'Total'],
        PowerDensityMethod: ['Near Field', 'Far Field'],
        Characteristic: [
            'Single-Electron Intensity',
            'Multi-Electron Intensity',
            'Single-Electron Flux',
            'Multi-Electron Flux',
            'Single-Electron Radiation Phase',
            'Re(E): Real part of Single-Electron Electric Field',
            'Im(E): Imaginary part of Single-Electron Electric Field',
            'Single-Electron Intensity, integrated over Time or Photon Energy (i.e. Fluence)',
        ],
    };
    var _MODEL = {
        electronBeam: {
            basic: [
                ['beamName', 'Beam Name', 'BeamList'],
                ['current',  'Current [A]', 'Float'],
            ],
            advanced: [
                ['beamName', 'Beam Name', 'BeamList'],
                ['current',  'Current [A]', 'Float'],
                ['horizontalPosition', 'Average Horizontal Position [m]', 'Float'],
                ['verticalPosition', 'Average Vertical Position [m]', 'Float'],
                ['energyDeviation', 'Average Energy Deviation [GeV]', 'Float'],
            ],
        },
        undulator: {
            basic: [
                ['period', 'Undulator Period [m]', 'Float'],
                ['length', 'Undulator Length [m]', 'Float'],
                ['horizontalAmplitude', 'Horizontal Amplitude [T]', 'Float'],
            ],
            advanced: [
                ['period', 'Undulator Period [m]', 'Float'],
                ['length', 'Undulator Length [m]', 'Float'],
                ['horizontalAmplitude', 'Horizontal Amplitude [T]', 'Float'],
            ],
        },
        intensityReport: {
            basic: [],
            advanced: [
                ['initialEnergy', 'Initial Photon Energy [eV]', 'Float'],
                ['finalEnergy', 'Final Photon Energy [eV]', 'Float'],
                ['horizontalPosition', 'Horizontal Position [m]', 'Float'],
                ['verticalPosition', 'Vertical Position [m]', 'Float'],
                ['method', 'Method for Integration', 'IntegrationMethod'],
                ['precision', 'Relative Precision', 'Float'],
                ['polarization', 'Polarization Component to Extract', 'Polarization'],
            ],
        },
        fluxReport: {
            basic: [],
            advanced: [
                ['initialEnergy', 'Initial Photon Energy [eV]', 'Float'],
                ['finalEnergy', 'Final Photon Energy [eV]', 'Float'],
                ['horizontalPosition', 'Horizontal Center Position [m]', 'Float'],
                ['horizontalApertureSize', 'Horizontal Aperture Size [m]', 'Float'],
                ['verticalPosition', 'Vertical Center Position [m]', 'Float'],
                ['verticalApertureSize', 'Vertical Aperture Size [m]', 'Float'],
                ['longitudinalPrecision', 'Longitudinal Integration Precision', 'Float'],
                ['azimuthalPrecision', 'Azimuthal Integration Precision', 'Float'],
                ['fluxType', 'Flux Calculation', 'Flux'],
                ['polarization', 'Polarization Component to Extract', 'Polarization'],
            ],
        },
        powerDensityReport: {
            basic: [],
            advanced: [
                ['horizontalPosition', 'Horizontal Center Position [m]', 'Float'],
                ['horizontalRange', 'Range of Horizontal Position [m]', 'Float'],
                ['verticalPosition', 'Vertical Center Position [m]', 'Float'],
                ['verticalRange', 'Range of Vertical Position [m]', 'Float'],
                ['precision', 'Relative Precision', 'Float'],
                ['method', 'Power Density Computation Method', 'PowerDensityMethod'],
            ],
        },
        initialIntensityReport: {
            basic: [],
            advanced: [
                ['photonEnergy', 'Photon Energy [eV]', 'Float'],
                ['horizontalPosition', 'Horizontal Center Position [m]', 'Float'],
                ['horizontalRange', 'Range of Horizontal Position [m]', 'Float'],
                ['verticalPosition', 'Vertical Center Position [m]', 'Float'],
                ['verticalRange', 'Range of Vertical Position [m]', 'Float'],
                ['sampleFactor', 'Sampling Factor', 'Float'],
                ['method', 'Method for Integration', 'IntegrationMethod'],
                ['precision', 'Relative Precision', 'Float'],
                ['polarization', 'Polarization Component to Extract', 'Polarization'],
                ['characteristic', 'Characteristic to be Extracted', 'Characteristic'],
            ],
        },
        intensityAtSampleReport: {
            basic: [],
            advanced: [],
        },
        intensityAtBPMReport: {
            basic: [],
            advanced: [],
        },
    };

    var app = angular.module('SRWApp', ['ngAnimate', 'ngDraggable']);

    app.controller('SourceController', function ($timeout) {
        var self = this;
        self.models = {
            electronBeam: {
                _visible: true,
                beamName: null,
                current: 0.5,
                horizontalPosition: 0,
                verticalPosition: 0,
                energyDeviation: 0,
            },
            undulator: {
                _visible: true,
                period: 0.02,
                length: 3,
                horizontalAmplitude: 0.88770981,
            },
            intensityReport: {
                _visible: true,
                _loading: false,
                initialEnergy: 100,
                finalEnergy: 20000,
                horizontalPosition: 0,
                verticalPosition: 0,
                method: 'Auto-Undulator',
                precision: 0.01,
                polarization: 'Total',
            },
            fluxReport: {
                _visible: true,
                _loading: false,
                initialEnergy: 100,
                finalEnergy: 20000,
                horizontalPosition: 0,
                horizontalApertureSize: 0.001,
                verticalPosition: 0,
                verticalApertureSize: 0.001,
                longitudinalPrecision: 1,
                azimuthalPrecision: 1,
                fluxType: 'Flux',
                polarization: 'Total',
            },
            powerDensityReport: {
                _visible: true,
                _loading: false,
                horizontalPosition: 0,
                horizontalRange: 0.015,
                verticalPosition: 0,
                verticalRange: 0.015,
                precision: 1,
                method: 'Near Field',
            },
            initialIntensityReport: {
                _visible: true,
                _loading: false,
                photonEnergy: 9000,
                horizontalPosition: 0,
                horizontalRange: 0.4e-03,
                verticalPosition: 0,
                verticalRange: 0.6e-03,
                sampleFactor: 1,
                method: 'Auto-Undulator',
                precision: 0.01,
                polarization: 'Total',
                characteristic: 'Single-Electron Intensity',
            },
            intensityAtSampleReport: {
                _visible: true,
                _loading: false,
            },
            intensityAtBPMReport: {
                _visible: true,
                _loading: false,
            },
        };
        self.model_info = function(name) {
            return _MODEL[name];
        };
        self.clone_model = function(name) {
            var val = name ? self.models[name] : self.models;
            return JSON.parse(JSON.stringify(val));
        }
        self.saved_model_values = self.clone_model();
        self.simulate_report_reload = function(name) {
            console.log("reload report: ", name);
            self.models[name]._loading = true;
            $timeout(function() {
                self.models[name]._loading = false;
            }, 2000 + 6000 * Math.random());
        }
        self.update_reports = function(name) {
            if (name.indexOf('Report') > 0) {
                self.simulate_report_reload(name);
            }
            else {
                for (var key in self.models) {
                    if (key.indexOf('Report') > 0) {
                        self.simulate_report_reload(key);
                    }
                }
            }
        };
        self.save_changes = function(name, update_reports) {
            console.log("save changes: ", name);
            self.saved_model_values[name] = self.clone_model(name);
            if (update_reports)
                self.update_reports(name);
        };
        self.cancel_changes = function(name) {
            console.log("cancel changes: ", name);
            self.models[name] = JSON.parse(JSON.stringify(self.saved_model_values[name]));
        };
    });

    app.directive('fieldEditor', function($http) {
        return {
            restirct: 'A',
            scope: {
                fieldEditor: '=',
                model: '=',
            },
            template: [
                // field def: [name, label, type]
                '<label class="col-sm-5 control-label">{{ fieldEditor[1] }}</label>',
                '<div data-ng-switch="fieldEditor[2]">',
                  '<div data-ng-switch-when="BeamList" class="col-sm-5">',
                    '<select class="form-control" data-ng-model="model[fieldEditor[0]]" data-ng-options="item.name for item in beams track by item.name"></select>',
                  '</div>',
                  '<div data-ng-switch-when="Float" class="col-sm-3">',
                    '<input data-ng-model="model[fieldEditor[0]]" class="form-control" style="text-align: right">',
                  '</div>',
                  // assume it is an enum
                  '<div data-ng-switch-default class="col-sm-5">',
                    '<select class="form-control" data-ng-model="model[fieldEditor[0]]" data-ng-options="item for item in enum[fieldEditor[2]] track by item"></select>',
                  '</div>',
                '</div>',
            ].join(''),
            link: function link(scope, element, attrs) {
                scope.enum = _ENUM;
                if (scope.fieldEditor[2] == 'BeamList') {
                    $http["get"]('beams.json')
                        .success(function(data, status) {
                            scope.beams = data;
                            scope.model[scope.fieldEditor[0]] = data[0];
                            scope.$parent.source.save_changes('electronBeam', false);
                        })
                        .error(function() {
                            console.log('get beams.json failed!');
                        });
                }
            },
        };
    });

    app.directive('buttons', function() {
        return {
            scope: {
                formName: '=',
                modelName: '@',
                modalId: "@",
            },
            template: [
                '<div class="col-sm-6 pull-right cssFade" data-ng-show="formName.$dirty">',
                    '<button data-ng-click="save_changes()" class="btn btn-primary">Save Changes</button> ',
                    '<button data-ng-click="cancel_changes()" class="btn btn-default">Cancel</button>',
                '</div>',
            ].join(''),
            controller: function($scope) {
                function change_done() {
                    $scope.formName.$setPristine();
                    if ($scope.modalId)
                        $('#' + $scope.modalId).modal('hide');
                }
                $scope.save_changes = function() {
                    $scope.$parent.source.save_changes($scope.modelName, true);
                    change_done();
                };
                $scope.cancel_changes = function() {
                    $scope.$parent.source.cancel_changes($scope.modelName);
                    change_done();
                };
            }
        };
    });

    app.directive('panelHeading', function() {
        return {
            restrict: 'A',
            scope: {
                panelHeading: '@',
                model: '=',
                editorId: '@',
                allowFullScreen: '@',
            },
            controller: function($scope) {
                $scope.toggleVisible = function() {
                  $scope.model['_visible'] = ! $scope.model['_visible'];
                };
                $scope.isVisible = function() {
                  return $scope.model['_visible'];
                };
                $scope.showEditor = function() {
                    $('#' + $scope.editorId).modal('show');
                };
            },
            template: [
                '<span class="lead">{{ panelHeading }}</span>',
                '<div class="srw-panel-options pull-right">',
                    '<a href data-ng-click="showEditor()" data-toggle="tooltip" title="Edit"><span class="lead glyphicon glyphicon-pencil"></span></a> ',
                    '<a href data-ng-show="allowFullScreen" data-toggle="tooltip" title="Download"><span class="lead glyphicon glyphicon-cloud-download"></span></a> ',
                    '<a href data-ng-show="allowFullScreen" data-toggle="tooltip" title="Full screen"><span class="lead glyphicon glyphicon-fullscreen"></span></a> ',
                    '<a href data-ng-click="toggleVisible()" data-ng-show="isVisible()" data-toggle="tooltip" title="Hide"><span class="lead glyphicon glyphicon-triangle-top"></span></a> ',
                    '<a href data-ng-click="toggleVisible()" data-ng-hide="isVisible()" data-toggle="tooltip" title="Show"><span class="lead glyphicon glyphicon-triangle-bottom"></span></a>',
                '</div>',
            ].join(''),
        };
    });

    app.directive('panelBody', function() {
        return {
            restrict: 'E',
            transclude: true,
            scope: {
                model: '=',
            },
            controller: function($scope) {
            },
            template: [
                '<div data-ng-class="{\'srw-panel-loading\': model._loading}" class="panel-body cssFade" data-ng-show="model._visible">',
                '<div class="lead srw-panel-wait"><span class="glyphicon glyphicon-hourglass"></span> Refreshing...</div>',
                '<ng-transclude></ng-transclude>',
                '</div>',
            ].join(''),
        };
    });


app.directive('plot2d', function($http) {

    function linspace(start, stop, nsteps) {
        var delta = (stop - start) / (nsteps - 1);
        return d3.range(start, stop + delta, delta).slice(0, nsteps);
    };

    return {
        restrict: 'A',
        scope: {},
        template: [
            '<svg></svg>',
            '<div style="margin-left: 30px" class="text-center"><strong>{{ x_range[0] | number }}</strong><input type="text" class="srw-plot2d-slider" value="" data-slider-min="0" data-slider-max="100" data-slider-step="1" data-slider-value="[0,100]" data-slider-tooltip="hide"><strong>{{ x_range[1] | number }}</strong></div>',
        ].join(''),
        controller: function($scope) {

            $scope.compute_peaks = function(json, dimensions, x_points) {
                var peak_spacing = dimensions[0] / 20;
                var min_pixel_height = dimensions[1] * .995;
                var x_peak_values = [];
                var sorted_points = d3.zip(x_points, json.points).sort(function(a, b) { return b[1] - a[1] });
                for (var i = 0; i < sorted_points.length / 2; i++) {
                    var p = sorted_points[i]
                    var x_pixel = $scope.x_axis_scale(p[0]);
                    var y_pixel = $scope.y_axis_scale(p[1]);
                    if (y_pixel >= min_pixel_height) {
                        break;
                    }
                    var found = false;
                    for (var j = 0; j < x_peak_values.length; j++) {
                        if (Math.abs(x_pixel - x_peak_values[j][2]) < peak_spacing) {
                            found = true;
                            break;
                        }
                    }
                    if (! found)
                        x_peak_values.push([p[0], p[1], x_pixel]);
                }
                //console.log("local maxes: ", x_peak_values.length);
                return x_peak_values;
            };

            $scope.init_vars = function(json, x_points) {
                $scope.points = d3.zip(x_points, json.points);
                $scope.margin = {top: 50, right: 50, bottom: 80, left: 70};
                $scope.x_range = json.x_range;
                $scope.x_units = json.x_units;

                $scope.x_axis_scale = d3.scale.linear()
                    .domain([json.x_range[0], json.x_range[1]]);
                $scope.y_axis_scale = d3.scale.linear()
                    .domain([d3.min(json.points), d3.max(json.points)]);

                var context = $scope.select('svg')
                    .append("g")
                    .attr("transform", "translate(" + $scope.margin.left + "," + $scope.margin.top + ")");

                $scope.x_axis = d3.svg.axis()
                    .scale($scope.x_axis_scale)
                    .orient("bottom");
                $scope.x_axis_grid = d3.svg.axis()
                    .scale($scope.x_axis_scale)
                    .orient("bottom");
                $scope.y_axis = d3.svg.axis()
                    .scale($scope.y_axis_scale)
                    // this causes a "number of fractional digits" error in MSIE
                    //.tickFormat(d3.format('e'))
                    .tickFormat(function (value) {
                        return value.toExponential();
                    })
                    .ticks(5)
                    .orient("left");
                $scope.y_axis_grid = d3.svg.axis()
                    .scale($scope.y_axis_scale)
                    .orient("left");

                context.append("g")
                    .attr("class", "x axis")
                context.append("g")
                    .attr("class", "x axis grid")
                context.append("g")
                    .attr("class", "y axis")
                context.append("g")
                    .attr("class", "y axis grid")

                context.append("text")
                    .attr("transform", "rotate(-90)")
                    .attr("class", "y-axis-label")
                    .attr("y", - $scope.margin.left)
                    .attr("dy", "1em")
                    .style("text-anchor", "middle")
                    .text(json.y_label);

                context.append("text")
                    .attr("class", "x-axis-label")
                    .attr("dy", "1em")
                    .style("text-anchor", "middle")
                    .text(json.x_label);

                context.append("text")
                    .attr("class", "main-title")
                    .attr("y", - $scope.margin.top / 2)
                    .style("text-anchor", "middle")
                    .text(json.title);

                $scope.graph_line = d3.svg.line()
                    .x(function(d) {return $scope.x_axis_scale(d[0])})
                    .y(function(d) {return $scope.y_axis_scale(d[1])});

                var focus = context.append("g")
                    .attr("class", "focus")
                    .style("display", "none");

                focus.append("circle")
                    .attr("r", 6);

                focus.append("text")
                    .attr("class", "focus-text")
                    .attr("x", 9)
                    .attr("dy", ".35em");

                context.append("rect")
                    .attr("class", "overlay")
                    .on("mouseover", function() { focus.style("display", null); })
                    .on("mouseout", function() { focus.style("display", "none"); })
                    .on("mousemove", mousemove);

                var viewport = context.append("svg")
                    .attr("class", "plot-viewport");

                viewport.append("path")
                    .attr("class", "line")
                    .datum($scope.points);

                var formatter = d3.format(",.0f")
                function mousemove() {
                    var x0 = $scope.x_axis_scale.invert(d3.mouse(this)[0]);
                    var local_max = null;
                    for (var i = 0; i < $scope.x_peak_values.length; i++) {
                        var v = $scope.x_peak_values[i];
                        if (local_max === null || Math.abs(v[0] - x0) < Math.abs(local_max[0] - x0)) {
                            local_max = v;
                        }
                    }
                    if (local_max) {
                        var x_pixel = $scope.x_axis_scale(local_max[0]);
                        if (x_pixel < 0 || x_pixel >= $scope.select(".plot-viewport").attr("width"))
                            return;
                        focus.attr("transform", "translate(" + x_pixel + "," + $scope.y_axis_scale(local_max[1]) + ")");
                        focus.select("text").text(formatter(local_max[0]) + " " + $scope.x_units);
                    }
                }
            };

            $scope.select = function(selector) {
                return d3.select($scope.plot_id + (selector ? (" " + selector) : ""));
            };

            $scope.slider_changed = function(ev) {
                function compute_point(value) {
                    return Math.round($scope.x_range[0] + (value / 100) * ($scope.x_range[1] - $scope.x_range[0]));
                }
                var start_x = compute_point(ev.value[0]);
                var end_x = compute_point(ev.value[1]);
                $scope.x_axis_scale.domain([start_x, end_x]);

                var min_y, max_y;
                for (var i = 0; i < $scope.points.length; i++) {
                    var p = $scope.points[i];
                    if (p[0] < start_x)
                        continue;
                    if (p[0] > end_x)
                        break;
                    if (min_y === undefined || min_y > p[1])
                        min_y = p[1];
                    if (max_y === undefined || max_y < p[1])
                        max_y = p[1];
                }
                $scope.y_axis_scale.domain([min_y, max_y]);
                $scope.resize();
            };

            $scope.main = function(json, id) {
                $scope.plot_id = '#' + id;
                $($scope.plot_id + ' .srw-plot2d-slider').slider()
                    .on('slide', $scope.slider_changed);
                var x_points = linspace(json.x_range[0], json.x_range[1], json.points.length);
                $scope.init_vars(json, x_points);
                var dimensions = $scope.resize();
                $scope.x_peak_values = $scope.compute_peaks(json, dimensions, x_points);
                $(window).resize($scope.resize);
            };

            $scope.resize = function() {
                var width = parseInt($scope.select().style("width")) - $scope.margin.left - $scope.margin.right;
                var height = parseInt($scope.select().style("height")) - $scope.margin.top - $scope.margin.bottom;
                if (height > width)
                    height = width;
                //console.log('resize: ', width, ' ', height);
                $scope.x_axis_scale.range([-0.5, width - 0.5]);
                $scope.y_axis_scale.range([height - 0.5, 0 - 0.5]).nice();

                $scope.x_axis_grid.tickSize(-height);
                $scope.y_axis_grid.tickSize(-width);
                $scope.select(".x.axis")
                    .attr("transform", "translate(0," + height + ")")
                    .call($scope.x_axis);
                $scope.select(".x.axis.grid")
                    .attr("transform", "translate(0," + height + ")")
                    .call($scope.x_axis_grid); // tickLine == gridline
                $scope.select(".y.axis")
                    .call($scope.y_axis);
                $scope.select(".y.axis.grid")
                    .call($scope.y_axis_grid);

                $scope.select(".main-title")
                    .attr("x", width / 2);
                $scope.select(".y-axis-label")
                    .attr("x", - height / 2);
                $scope.select(".x-axis-label")
                    .attr("x", width / 2)
                // font height + 12 padding...
                    .attr("y", height + 26);

                $scope.select(".plot-viewport")
                    .attr("width", width)
                    .attr("height", height);

                $scope.select(".overlay")
                    .attr("width", width)
                    .attr("height", height)

                $scope.select(".line")
                    .attr("d", $scope.graph_line);
                return [width, height];
            }

        },
        link: function link(scope, element, attrs) {
            $http["get"](attrs.plot2d)
                .success(function(data, status) {
                    scope.main(data, attrs.id);
                })
                .error(function() {
                    console.log('plot2d get failed!');
                });
        },
    };
});

app.directive('plot3d', function($http) {

    return {
        restrict: 'A',
        scope: {},
        controller: function($scope) {

            var margin = 50;

            $scope.select = function(selector) {
                return d3.select($scope.plot_id + (selector ? (" " + selector) : ""));
            };

            $scope.main = function(json, id) {
                $scope.plot_id = '#' + id;
                $scope.heatmap = [];
                var xmax = json.x_range.length - 1;
                var ymax = json.y_range.length - 1;
                $scope.x_value_min = json.x_range[0];
                $scope.x_value_max = json.x_range[xmax];
                $scope.x_value_range = json.x_range.slice(0);
                $scope.y_value_min = json.y_range[0];
                $scope.y_value_max = json.y_range[ymax];
                $scope.y_value_range = json.y_range.slice(0);

                var zmin = json.z_matrix[0][0]
                var zmax = json.z_matrix[0][0]
                for (var yi = 0; yi <= ymax; ++yi) {
                    // flip to match the canvas coordinate system (origin: top left)
                    // matplotlib is bottom left
                    $scope.heatmap[ymax - yi] = [];
                    for (var xi = 0; xi <= xmax; ++xi) {
	                var zi = json.z_matrix[yi][xi];
	                $scope.heatmap[ymax - yi][xi] = zi;
	                if (zmax < zi)
	                    zmax = zi;
	                else if (zmin > zi)
	                    zmin = zi;
                    }
                }
                $scope.init_vars(json, zmin, zmax);
                $scope.init_draw(json, zmin, zmax);
                $scope.resize();
                $(window).resize($scope.resize);
            }

            $scope.resize = function() {
                var width = parseInt($scope.select().style("width")) - 2 * margin;
                var rightpanel_margin = {left: 10, right: 40};
                var bottompanel_margin = {top: 10, bottom: 30};
                $scope.canvas_size = 2 * (width - rightpanel_margin.left - rightpanel_margin.right) / 3;
                var bottompanel_height = 2 * $scope.canvas_size / 5 + bottompanel_margin.top + bottompanel_margin.bottom;
                var rightpanel_width = $scope.canvas_size / 2 + rightpanel_margin.left + rightpanel_margin.right;
                $scope.rightpanel_xAxis.ticks(
                    width >= 700 ? 5
                        : width >= 566 ? 4
                        : width >= 433 ? 3
                        : 2);
                $scope.x_axis_scale.range([0, $scope.canvas_size - 1]);
                $scope.y_axis_scale.range([$scope.canvas_size - 1, 0]);
                $scope.bottompanel_y_scale.range([bottompanel_height - bottompanel_margin.top - bottompanel_margin.bottom - 1, 0]);
                $scope.rightpanel_x_scale.range([0, rightpanel_width - rightpanel_margin.left - rightpanel_margin.right]);
                $scope.main_xAxis.tickSize(- $scope.canvas_size - bottompanel_height + bottompanel_margin.bottom); // tickLine == gridline
                $scope.main_yAxis.tickSize(- $scope.canvas_size - rightpanel_width + rightpanel_margin.right); // tickLine == gridline
                $scope.zoom.center([$scope.canvas_size / 2, $scope.canvas_size / 2])
                    .x($scope.x_axis_scale.domain([$scope.x_value_min, $scope.x_value_max]))
                    .y($scope.y_axis_scale.domain([$scope.y_value_min, $scope.y_value_max]));
                $scope.select("canvas")
                    .style("width", $scope.canvas_size + "px")
                    .style("height", $scope.canvas_size + "px");
                $scope.select("svg")
                    .attr("width", margin * 2 + $scope.canvas_size + rightpanel_width)
                    .attr("height", margin * 2 + $scope.canvas_size + bottompanel_height)
                $scope.select(".main-title")
                    .attr("x", $scope.canvas_size / 2)
                    .attr("y", - margin / 2);
                $scope.select(".mouse-rect")
                    .attr("width", $scope.canvas_size)
                    .attr("height", $scope.canvas_size)
                    .call($scope.zoom);
                $scope.select(".y-cross-hair")
                    .attr("x1", Math.floor($scope.canvas_size/2) - 0)
                    .attr("x2", Math.floor($scope.canvas_size/2) - 0)
                    .attr("y2", $scope.canvas_size);
                $scope.select(".x-cross-hair")
                    .attr("y1", Math.floor($scope.canvas_size/2) + 0)
                    .attr("x2", $scope.canvas_size)
                    .attr("y2", Math.floor($scope.canvas_size/2) + 0);
                $scope.select(".bottompanel-rect")
                    .attr("width", $scope.canvas_size)
                    .attr("height", bottompanel_height - bottompanel_margin.top - bottompanel_margin.bottom);
                $scope.select(".bottompanel")
                    .attr("transform", "translate(0," + ($scope.canvas_size + bottompanel_margin.top) + ")");
                $scope.select(".x-axis-label")
                    .attr("x", $scope.canvas_size / 2)
                    .attr("y", bottompanel_height);
                $scope.select(".rightpanel-rect")
                    .attr("width", rightpanel_width - rightpanel_margin.left - rightpanel_margin.right)
                    .attr("height", $scope.canvas_size);
                $scope.select(".rightpanel")
                    .attr("transform", "translate(" + ($scope.canvas_size + rightpanel_margin.left) + ",0)");
                $scope.select(".x.axis.bottom")
                    .attr("transform", "translate(0," + (bottompanel_height - bottompanel_margin.top - bottompanel_margin.bottom) + ")")
                    .call($scope.bottompanel_xAxis);
                $scope.select(".x.axis.right")
                    .attr("transform", "translate(0," + $scope.canvas_size + ")")
                    .call($scope.rightpanel_xAxis);
                $scope.select(".y-axis-label")
                    .attr("x", - $scope.canvas_size / 2)
                    .attr("y", rightpanel_width + 15);
                $scope.select(".z-axis-label")
                    .attr("x", $scope.canvas_size + rightpanel_width / 2)
                    .attr("y", $scope.canvas_size + margin);
                $scope.select(".x.axis.grid")
                    .attr("transform", "translate(0," + (bottompanel_height - bottompanel_margin.top - bottompanel_margin.bottom) + ")")
                    .call($scope.zoom)
                    .call($scope.main_xAxis);
                $scope.select(".y.axis.grid")
                    .call($scope.zoom)
                    .call($scope.main_yAxis);
                $scope.select(".y.axis.right")
                    .attr("transform", "translate(" + (rightpanel_width - rightpanel_margin.left - rightpanel_margin.right) + ",0)")
                    .call($scope.rightpanel_yAxis);
                $scope.select(".y.axis.bottom")
                    .call($scope.bottompanel_yAxis);
                $scope.refresh();
            }

            $scope.init_vars = function(json, zmin, zmax) {
                var xmax = json.x_range.length - 1;
                var ymax = json.y_range.length - 1;
                $scope.x_axis_scale = d3.scale.linear()
                    .domain([$scope.x_value_min, $scope.x_value_max]);
                $scope.x_index_scale = d3.scale.linear()
                    .domain([$scope.x_value_min, $scope.x_value_max])
                    .range([0, xmax]);
                $scope.y_axis_scale = d3.scale.linear()
                    .domain([$scope.y_value_min, $scope.y_value_max]);
                $scope.y_index_scale = d3.scale.linear()
                    .domain([$scope.y_value_min, $scope.y_value_max])
                    .range([0, ymax]);
                $scope.bottompanel_y_scale = d3.scale.linear()
                    .domain([zmin, zmax]);
                $scope.rightpanel_x_scale = d3.scale.linear()
                    .domain([zmax, zmin]);
                $scope.main_xAxis = d3.svg.axis()
                    .scale($scope.x_axis_scale)
                    .orient("bottom");
                $scope.main_yAxis = d3.svg.axis()
                    .scale($scope.y_axis_scale)
                    .orient("left");
                $scope.bottompanel_xAxis = d3.svg.axis()
                    .scale($scope.x_axis_scale)
                    .orient("bottom");
                $scope.bottompanel_yAxis = d3.svg.axis()
                    .scale($scope.bottompanel_y_scale)
                    // this causes a "number of fractional digits" error in MSIE
                    //.tickFormat(d3.format('e'))
                    .tickFormat(function (value) {
                        return value.toExponential();
                    })
                    .ticks(5)
                    .orient("left");
                $scope.rightpanel_xAxis = d3.svg.axis()
                    .scale($scope.rightpanel_x_scale)
                    // this causes a "number of fractional digits" error in MSIE
                    //.tickFormat(d3.format('e'))
                    .tickFormat(function (value) {
                        return value.toExponential();
                    })
                    .ticks(5)
                    .orient("bottom");
                $scope.rightpanel_yAxis = d3.svg.axis()
                    .scale($scope.y_axis_scale)
                    .orient("right");
                $scope.zoom = d3.behavior.zoom()
                    .scaleExtent([1, 10])
                    .on("zoom", $scope.refresh);
                var root_div = $scope.select()
                    .style("position", "relative");
                $scope.canvas = root_div.append("canvas")
                    .style("position", "absolute")
                    .attr("width", json.x_range.length)
                    .attr("height", json.y_range.length)
                    .attr("transform", "translate(" + margin + "," + margin + ")")
                    .style("left", margin + "px")
                    .style("top", margin + "px");
                $scope.svg = root_div.append("svg")
                    .style("position", "relative")
                    .append("g")
                    .attr("transform", "translate(" + margin + "," + margin + ")");
                $scope.svg.append("text")
                    .attr("class", "main-title")
                    .style("text-anchor", "middle")
                    .text(json.title);
                // We make an invisible rectangle to intercept mouse events for zooming.
                $scope.mouse_rect = $scope.svg.append("rect")
                    .attr("class", "mouse-rect")
                    .style("pointer-events", "all")
                    .style("fill", "none");
                $scope.ctx = $scope.canvas.node().getContext("2d");
                $scope.imageObj = new Image();
                $scope.svg.append("line")
                    .attr("class", "y-cross-hair cross-hair")
                    .attr("y1", 0)
                    .attr("stroke-width", 1)
                    .attr("shape-rendering", "crispEdges")
                    .attr("stroke", "steelblue");
                $scope.svg.append("line")
                    .attr("class", "x-cross-hair cross-hair")
                    .attr("x1", 0)
                    .attr("stroke-width", 1)
                    .attr("shape-rendering", "crispEdges")
                    .attr("stroke", "steelblue");
                $scope.svg.append("g")
                    .attr("class", "y axis grid");
                $scope.svg.append("defs").append("clipPath")
                    .attr("id", "bottomclip")
                    .append("rect")
                    .attr("class", "bottompanel-rect");
                $scope.bottompanel_context = $scope.svg.append("g")
                    .attr("class", "bottompanel");
                // Clips the line graph
                $scope.bottompanel_context.append("path")
                    .attr("clip-path", "url(#bottomclip)");
                $scope.bottompanel_context.append("g")
                    .attr("class", "x axis bottom");
                $scope.bottompanel_context.append("g")
                    .attr("class", "x axis grid");
                $scope.bottompanel_context.append("text")
                    .attr("class", "x-axis-label")
                    .style("text-anchor", "middle")
                    .text(json.x_label);
                $scope.bottompanel_context.append("g")
                    .attr("class", "y axis bottom");
                $scope.rightpanel_context = $scope.svg.append("g")
                    .attr("class", "rightpanel");
                $scope.svg.append("defs").append("clipPath")
                    .attr("id", "rightclip")
                    .append("rect")
                    .attr("class", "rightpanel-rect");
                $scope.rightpanel_context.append("path")
                    .attr("clip-path", "url(#rightclip)");
                $scope.rightpanel_context.append("g")
                    .attr("class", "y axis right");
                $scope.rightpanel_context.append("g")
                    .attr("class", "x axis right");
                $scope.rightpanel_context.append("text")
                    .attr("class", "y-axis-label")
                    .style("text-anchor", "middle")
                    .text(json.y_label)
                    .attr("transform", "rotate(270)");
                $scope.svg.append("text")
                    .attr("class", "z-axis-label")
                    .style("text-anchor", "middle")
                    .text(json.z_label);
                $scope.bottompanel_cut_line = d3.svg.line()
                    .x(function(d) {return $scope.x_axis_scale(d[0])})
                    .y(function(d) {return $scope.bottompanel_y_scale(d[1])});
                $scope.rightpanel_cut_line = d3.svg.line()
                    .y(function(d) { return $scope.y_axis_scale(d[0]); })
                    .x(function(d) { return $scope.rightpanel_x_scale(d[1]); });
            }

            $scope.refresh = function() {
                if ($scope.imageObj.height == 0) {
                    setTimeout($scope.refresh, 300);
                    return;
                }

                var tx = 0, ty = 0, s = 1;
                if (d3.event && d3.event.translate) {
                    var t = d3.event.translate;
                    s = d3.event.scale;
                    tx = t[0];
                    ty = t[1];
                    tx = Math.min(
                        0,
                        Math.max(
                            tx,
                            $scope.canvas_size - (s * $scope.imageObj.width) / ($scope.imageObj.width / $scope.canvas_size)));
                    ty = Math.min(
                        0,
                        Math.max(
                            ty,
                            $scope.canvas_size - (s * $scope.imageObj.height) / ($scope.imageObj.height / $scope.canvas_size)));

                    var xdom = $scope.x_axis_scale.domain();
                    var ydom = $scope.y_axis_scale.domain();
                    var reset_s = 0;
                    if ((xdom[1] - xdom[0]) >= ($scope.x_value_max - $scope.x_value_min) * 0.9999) {
	                $scope.zoom.x($scope.x_axis_scale.domain([$scope.x_value_min, $scope.x_value_max]));
	                xdom = $scope.x_axis_scale.domain();

	                reset_s += 1;
                    }
                    if ((ydom[1] - ydom[0]) >= ($scope.y_value_max - $scope.y_value_min) * 0.9999) {
	                $scope.zoom.y($scope.y_axis_scale.domain([$scope.y_value_min, $scope.y_value_max]));
	                ydom = $scope.y_axis_scale.domain();
	                reset_s += 1;
                    }
                    if (reset_s == 2) {
	                $scope.mouse_rect.attr("class", "mouse-zoom");
	                // Both axes are full resolution. Reset.
	                tx = 0;
	                ty = 0;
                    }
                    else {
	                $scope.mouse_rect.attr("class", "mouse-move");
	                if (xdom[0] < $scope.x_value_min) {
                            //		tx = 0;
	                    $scope.x_axis_scale.domain([$scope.x_value_min, xdom[1] - xdom[0] + $scope.x_value_min]);
	                    xdom = $scope.x_axis_scale.domain();
	                }
	                if (xdom[1] > $scope.x_value_max) {
	                    xdom[0] -= xdom[1] - $scope.x_value_max;
	                    $scope.x_axis_scale.domain([xdom[0], $scope.x_value_max]);
	                }
	                if (ydom[0] < $scope.y_value_min) {
	                    $scope.y_axis_scale.domain([$scope.y_value_min, ydom[1] - ydom[0] + $scope.y_value_min]);
	                    ydom = $scope.y_axis_scale.domain();
	                }
	                if (ydom[1] > $scope.y_value_max) {
	                    ydom[0] -= ydom[1] - $scope.y_value_max;
	                    $scope.y_axis_scale.domain([ydom[0], $scope.y_value_max]);
	                }
                    }
                }

                $scope.ctx.clearRect(0, 0, $scope.canvas_size, $scope.canvas_size);
                if (s == 1) {
                    tx = 0;
                    ty = 0;
                    $scope.zoom.translate([tx, ty]);
                }
                $scope.ctx.drawImage(
                    $scope.imageObj,
                    tx*$scope.imageObj.width/$scope.canvas_size,
                    ty*$scope.imageObj.height/$scope.canvas_size,
                    $scope.imageObj.width*s,
                    $scope.imageObj.height*s
                );
                $scope.draw_bottompanel_cut();
                $scope.draw_rightpanel_cut();
                $scope.bottompanel_context.selectAll($scope.plot_id + " .x.axis").call($scope.bottompanel_xAxis);
                $scope.bottompanel_context.selectAll($scope.plot_id + " .y.axis").call($scope.bottompanel_yAxis);
                $scope.rightpanel_context.selectAll($scope.plot_id + " .x.axis").call($scope.rightpanel_xAxis);
                $scope.rightpanel_context.selectAll($scope.plot_id + " .y.axis").call($scope.rightpanel_yAxis);
                $scope.svg.selectAll($scope.plot_id + " .x.axis.grid").call($scope.main_xAxis);
                $scope.svg.selectAll($scope.plot_id + " .y.axis.grid").call($scope.main_yAxis);
            }

            $scope.init_draw = function(json, zmin, zmax) {
                var color = d3.scale.linear()
                    .domain([zmin, zmax])
                    .range(["#333", "#fff"]);
                var xmax = json.x_range.length - 1;
                var ymax = json.y_range.length - 1;
                // Compute the pixel colors; scaled by CSS.
                var img = $scope.ctx.createImageData(json.x_range.length, json.y_range.length);
                for (var yi = 0, p = -1; yi <= ymax; ++yi) {
	            for (var xi = 0; xi <= xmax; ++xi) {
	                var c = d3.rgb(color($scope.heatmap[yi][xi]));
	                img.data[++p] = c.r;
	                img.data[++p] = c.g;
	                img.data[++p] = c.b;
	                img.data[++p] = 255;
	            }
                }
                // Keeping pixels as nearest neighbor (as anti-aliased as we can get
                // without doing more programming) allows us to see how the marginals
                // line up when zooming in a lot.
                $scope.ctx.mozImageSmoothingEnabled = false;
                $scope.ctx.webkitImageSmoothingEnabled = false;
                $scope.ctx.msImageSmoothingEnabled = false;
                $scope.ctx.imageSmoothingEnabled = false;
                $scope.ctx.putImageData(img, 0, 0);
                $scope.imageObj.src = $scope.canvas.node().toDataURL();
            }

            $scope.draw_bottompanel_cut = function() {
                var y_bottom = $scope.y_index_scale($scope.y_axis_scale.domain()[0]);
                var y_top = $scope.y_index_scale($scope.y_axis_scale.domain()[1]);
                var yv = Math.floor(y_bottom + (y_top - y_bottom + 1)/2);
                var row = $scope.heatmap[yv];
                var xv_min = $scope.x_index_scale.domain()[0];
                var xv_max = $scope.x_index_scale.domain()[1];
                var xi_min = Math.ceil($scope.x_index_scale(xv_min));
                var xi_max = Math.floor($scope.x_index_scale(xv_max));
                var xv_range = $scope.x_value_range.slice(xi_min, xi_max + 1);
                var zv_range = row.slice(xi_min, xi_max + 1);
                $scope.bottompanel_context.select($scope.plot_id + " path")
                    .datum(d3.zip(xv_range, zv_range))
                    .attr("class", "line")
                    .attr("d", $scope.bottompanel_cut_line);
            }

            $scope.draw_rightpanel_cut = function() {
                var yv_min = $scope.y_index_scale.domain()[0];
                var yv_max = $scope.y_index_scale.domain()[1];
                var yi_min = Math.ceil($scope.y_index_scale(yv_min));
                var yi_max = Math.floor($scope.y_index_scale(yv_max));
                var x_left = $scope.x_index_scale($scope.x_axis_scale.domain()[0]);
                var x_right = $scope.x_index_scale($scope.x_axis_scale.domain()[1]);
                var xv = Math.floor(x_left + (x_right - x_left + 1)/2);
                var data = $scope.heatmap.slice(yi_min, yi_max + 1).map(function (v, i) {
                    return [$scope.y_value_range[i], v[xv]];
                });
                $scope.rightpanel_context.select($scope.plot_id + " path")
                    .datum(data)
                    .attr("class", "line")
                    .attr("d", $scope.rightpanel_cut_line);
            }
        },
        link: function link(scope, element, attrs) {
            $http["get"](attrs.plot3d)
                .success(function(data, status) {
                    scope.main(data, attrs.id);
                })
                .error(function() {
                    console.log('plot3d get failed!');
                });
        },
    };
});

app.controller('SimulationsController', function () {
    var self = this;
});

app.controller('BeamlineController', function () {
    var self = this;
    self.toolbar_items = [
        {name:'aperture', title:'Aperture'},
        {name:'crl', title:'CRL'},
        {name:'lens', title:'Lens'},
        {name:'mirror', title:'Mirror'},
        {name:'obstacle', title:'Obstacle'},
        {name:'watch', title:'Watchpoint'},
    ];
    self.beamline = [
        {id: 1, name:'aperture', title:'S0', position: 20.5, horizontalSize:0.2, verticalSize:1},
        {id: 2, name:'mirror', title:'HDM', position: 27.4},
        {id: 3, name:'aperture', title:'S1', position: 29.9, horizontalSize:0.2, verticalSize:1},
        {id: 4, name:'aperture', title:'S2', position: 34.3, horizontalSize:0.05, verticalSize:1},
        {id: 5, name:'watch', title:'BPM', position: 34.6},
        {id: 6, name:'crl', title:'CRL1', position: 35.4},
        {id: 7, name:'crl', title:'CRL2', position: 35.4},
        {id: 8, name:'lens', title:'KL', position: 44.5},
        {id: 9, name:'aperture', title:'S3', position: 48, horizontalSize:0.01, verticalSize:0.01},
        {id: 10, name:'watch', title:'Sample', position: 48.7},
    ];
    var current_id = self.beamline.length + 100;

    function add_item(item) {
        //TODO(pjm): conslidate clone()
        var new_item = $.extend(true, {}, item);
        new_item['id'] = ++current_id;
        new_item['_show_popover'] = true;
        if (self.beamline.length) {
            new_item.position = parseFloat(self.beamline[self.beamline.length - 1].position) + 1;
        }
        else {
            new_item.position = 20;
        }
        self.beamline.push(new_item);
        $('.srw-beamline-element-label').popover('hide');
    }

    self.remove_element = function(item) {
        $('.srw-beamline-element-label').popover('hide');
        self.beamline.splice(self.beamline.indexOf(item), 1);
    }

    self.drop_complete = function(data) {
        if (data && ! data['id']) {
            add_item(data);
        }
    }
    self.drop_between = function(index, data) {
        if (! data)
            return;
        //console.log("drop_between: ", index, ' ', data, ' ', data['id'] ? 'old' : 'new');
        var item;
        if (data['id']) {
            $('.srw-beamline-element-label').popover('hide');
            var curr = self.beamline.indexOf(data);
            if (curr < index)
                index--;
            self.beamline.splice(curr, 1);
            item = data;
        }
        else {
            // move last item to this index
            item = self.beamline.pop()
        }
        self.beamline.splice(index, 0, item);
        if (self.beamline.length > 1) {
            if (index === 0) {
                item.position = parseFloat(self.beamline[1].position) - 0.5;
            }
            else if (index === self.beamline.length - 1) {
                item.position = parseFloat(self.beamline[self.beamline.length - 1].position) + 0.5;
            }
            else {
                item.position = Math.round(100 * (parseFloat(self.beamline[index - 1].position) + parseFloat(self.beamline[index + 1].position)) / 2) / 100;
            }
        }
    }
});

app.directive('beamlineItem', function($compile, $timeout) {
    return {
        scope: {
            item: '=',
        },
        controller: function($scope) {
            $scope.dismiss = function() {
                $('.srw-beamline-element-label').popover('hide');
            }
        },
        link: function(scope, element, attrs) {
            graphics.redraw_all_icons();
            $(element).find('.srw-beamline-element-label').each(function (index, el) {
                $(el).popover({
                    html: true,
                    placement: 'bottom',
                    container: '.srw-popup-container-lg',
                    viewport: { selector: '.srw-beamline'},
                    content: $compile($('.srw-' + scope.item.name + '-editor').html())(scope),
                    trigger: 'manual',
                });
                $(el).click(function() {
                    $('.srw-beamline-element-label').not(this).popover('hide');
                    $(el).popover('toggle');
                });
                if (scope.item['_show_popover']) {
                    $timeout(function() {
                        var position = $(el).parent().position().left;
                        var width = $('.srw-beamline-container').width();
                        var itemWidth = $(el).width();
                        if (position + itemWidth > width) {
                            var scrollPoint = $('.srw-beamline-container').scrollLeft();
                            $('.srw-beamline-container').scrollLeft(position - width + scrollPoint + itemWidth);
                        }
                        $(el).popover('show');
                        $(el).on('shown.bs.popover', function() {
                            $('.popover-content .form-control').first().select();
                        });
                    }, 500);
                }
            });
        },
    };

});
