'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;
SIREPO.PLOTTING_LINE_CSV_EVENT = 'plottingLineoutCSV';
SIREPO.DEFAULT_COLOR_MAP = 'viridis';

SIREPO.app.factory('plotting', function(appState, frameCache, panelState, utilities, requestQueue, simulationQueue, $interval, $rootScope, $window) {

    var INITIAL_HEIGHT = 400;
    var MAX_PLOTS = 11;
    var COLOR_MAP = {
        grayscale: ['#333', '#fff'],
        afmhot: colorsFromString('0000000200000400000600000800000a00000c00000e00001000001200001400001600001800001a00001c00001e00002000002200002400002600002800002a00002c00002e00003000003200003400003600003800003a00003c00003e00004000004200004400004600004800004a00004c00004e00005000005200005400005600005800005a00005c00005e00006000006200006400006600006800006a00006c00006e00007000007200007400007600007800007a00007c00007e00008000008202008404008607008808008a0a008c0d008e0f009010009212009414009617009818009a1a009c1d009e1f00a02000a22200a42400a62700a82800aa2a00ac2d00ae2f00b03000b23200b43400b63700b83800ba3a00bc3d00be3f00c04000c24200c44400c64600c84800ca4a00cc4d00ce4e00d05000d25200d45400d65600d85800da5a00dc5d00de5e00e06000e26200e46400e66600e86800ea6a00ec6d00ee6e00f07000f27200f47400f67600f87800fa7a00fc7d00fe7e00ff8001ff8203ff8405ff8607ff8809ff8b0bff8c0dff8e0fff9011ff9213ff9415ff9617ff9919ff9b1bff9c1dff9e1fffa021ffa223ffa425ffa627ffa829ffab2bffac2dffae2fffb031ffb233ffb435ffb637ffb939ffbb3bffbc3dffbe3fffc041ffc243ffc445ffc647ffc849ffcb4bffcc4dffce4fffd051ffd253ffd455ffd657ffd959ffdb5bffdc5dffde5fffe061ffe263ffe465ffe667ffe869ffeb6bffec6dffee6ffff071fff273fff475fff677fff979fffb7bfffc7dfffe7fffff81ffff83ffff85ffff87ffff89ffff8bffff8dffff8fffff91ffff93ffff95ffff97ffff99ffff9bffff9dffff9fffffa1ffffa3ffffa5ffffa7ffffa9ffffabffffadffffafffffb1ffffb3ffffb5ffffb7ffffb9ffffbbffffbdffffbfffffc1ffffc3ffffc5ffffc7ffffc9ffffcbffffcdffffcfffffd1ffffd3ffffd5ffffd7ffffd9ffffdbffffddffffdfffffe1ffffe3ffffe5ffffe7ffffe9ffffebffffedffffeffffff1fffff3fffff5fffff7fffff9fffffbfffffdffffff'),
        coolwarm: colorsFromString('3b4cc03c4ec23d50c33e51c53f53c64055c84257c94358cb445acc455cce465ecf485fd14961d24a63d34b64d54c66d64e68d84f69d9506bda516ddb536edd5470de5572df5673e05875e15977e35a78e45b7ae55d7ce65e7de75f7fe86180e96282ea6384eb6485ec6687ed6788ee688aef6a8bef6b8df06c8ff16e90f26f92f37093f37295f47396f57597f67699f6779af7799cf87a9df87b9ff97da0f97ea1fa80a3fa81a4fb82a6fb84a7fc85a8fc86a9fc88abfd89acfd8badfd8caffe8db0fe8fb1fe90b2fe92b4fe93b5fe94b6ff96b7ff97b8ff98b9ff9abbff9bbcff9dbdff9ebeff9fbfffa1c0ffa2c1ffa3c2fea5c3fea6c4fea7c5fea9c6fdaac7fdabc8fdadc9fdaec9fcafcafcb1cbfcb2ccfbb3cdfbb5cdfab6cefab7cff9b9d0f9bad0f8bbd1f8bcd2f7bed2f6bfd3f6c0d4f5c1d4f4c3d5f4c4d5f3c5d6f2c6d6f1c7d7f0c9d7f0cad8efcbd8eeccd9edcdd9eccedaebcfdaead1dae9d2dbe8d3dbe7d4dbe6d5dbe5d6dce4d7dce3d8dce2d9dce1dadce0dbdcdedcdddddddcdcdedcdbdfdbd9e0dbd8e1dad6e2dad5e3d9d3e4d9d2e5d8d1e6d7cfe7d7cee8d6cce9d5cbead5c9ead4c8ebd3c6ecd3c5edd2c3edd1c2eed0c0efcfbfefcebdf0cdbbf1cdbaf1ccb8f2cbb7f2cab5f2c9b4f3c8b2f3c7b1f4c6aff4c5adf5c4acf5c2aaf5c1a9f5c0a7f6bfa6f6bea4f6bda2f7bca1f7ba9ff7b99ef7b89cf7b79bf7b599f7b497f7b396f7b194f7b093f7af91f7ad90f7ac8ef7aa8cf7a98bf7a889f7a688f6a586f6a385f6a283f5a081f59f80f59d7ef59c7df49a7bf4987af39778f39577f39475f29274f29072f18f71f18d6ff08b6ef08a6cef886bee8669ee8468ed8366ec8165ec7f63eb7d62ea7b60e97a5fe9785de8765ce7745be67259e57058e46e56e36c55e36b54e26952e16751e0654fdf634ede614ddd5f4bdc5d4ada5a49d95847d85646d75445d65244d55042d44e41d24b40d1493fd0473dcf453ccd423bcc403acb3e38ca3b37c83836c73635c53334c43032c32e31c12b30c0282fbe242ebd1f2dbb1b2cba162bb8122ab70d28b50927b40426'),
        jet: colorsFromString('00008000008400008900008d00009200009600009b00009f0000a40000a80000ad0000b20000b60000bb0000bf0000c40000c80000cd0000d10000d60000da0000df0000e30000e80000ed0000f10000f60000fa0000ff0000ff0000ff0000ff0000ff0004ff0008ff000cff0010ff0014ff0018ff001cff0020ff0024ff0028ff002cff0030ff0034ff0038ff003cff0040ff0044ff0048ff004cff0050ff0054ff0058ff005cff0060ff0064ff0068ff006cff0070ff0074ff0078ff007cff0080ff0084ff0088ff008cff0090ff0094ff0098ff009cff00a0ff00a4ff00a8ff00acff00b0ff00b4ff00b8ff00bcff00c0ff00c4ff00c8ff00ccff00d0ff00d4ff00d8ff00dcfe00e0fb00e4f802e8f406ecf109f0ee0cf4eb0ff8e713fce416ffe119ffde1cffdb1fffd723ffd426ffd129ffce2cffca30ffc733ffc436ffc139ffbe3cffba40ffb743ffb446ffb149ffad4dffaa50ffa753ffa456ffa05aff9d5dff9a60ff9763ff9466ff906aff8d6dff8a70ff8773ff8377ff807aff7d7dff7a80ff7783ff7387ff708aff6d8dff6a90ff6694ff6397ff609aff5d9dff5aa0ff56a4ff53a7ff50aaff4dadff49b1ff46b4ff43b7ff40baff3cbeff39c1ff36c4ff33c7ff30caff2cceff29d1ff26d4ff23d7ff1fdbff1cdeff19e1ff16e4ff13e7ff0febff0ceeff09f1fc06f4f802f8f500fbf100feed00ffea00ffe600ffe200ffde00ffdb00ffd700ffd300ffd000ffcc00ffc800ffc400ffc100ffbd00ffb900ffb600ffb200ffae00ffab00ffa700ffa300ff9f00ff9c00ff9800ff9400ff9100ff8d00ff8900ff8600ff8200ff7e00ff7a00ff7700ff7300ff6f00ff6c00ff6800ff6400ff6000ff5d00ff5900ff5500ff5200ff4e00ff4a00ff4700ff4300ff3f00ff3b00ff3800ff3400ff3000ff2d00ff2900ff2500ff2200ff1e00ff1a00ff1600ff1300fa0f00f60b00f10800ed0400e80000e40000df0000da0000d60000d10000cd0000c80000c40000bf0000bb0000b60000b20000ad0000a80000a400009f00009b00009600009200008d0000890000840000800000'),
        viridis: colorsFromString('44015444025645045745055946075a46085c460a5d460b5e470d60470e6147106347116447136548146748166848176948186a481a6c481b6d481c6e481d6f481f70482071482173482374482475482576482677482878482979472a7a472c7a472d7b472e7c472f7d46307e46327e46337f463480453581453781453882443983443a83443b84433d84433e85423f854240864241864142874144874045884046883f47883f48893e49893e4a893e4c8a3d4d8a3d4e8a3c4f8a3c508b3b518b3b528b3a538b3a548c39558c39568c38588c38598c375a8c375b8d365c8d365d8d355e8d355f8d34608d34618d33628d33638d32648e32658e31668e31678e31688e30698e306a8e2f6b8e2f6c8e2e6d8e2e6e8e2e6f8e2d708e2d718e2c718e2c728e2c738e2b748e2b758e2a768e2a778e2a788e29798e297a8e297b8e287c8e287d8e277e8e277f8e27808e26818e26828e26828e25838e25848e25858e24868e24878e23888e23898e238a8d228b8d228c8d228d8d218e8d218f8d21908d21918c20928c20928c20938c1f948c1f958b1f968b1f978b1f988b1f998a1f9a8a1e9b8a1e9c891e9d891f9e891f9f881fa0881fa1881fa1871fa28720a38620a48621a58521a68522a78522a88423a98324aa8325ab8225ac8226ad8127ad8128ae8029af7f2ab07f2cb17e2db27d2eb37c2fb47c31b57b32b67a34b67935b77937b87838b9773aba763bbb753dbc743fbc7340bd7242be7144bf7046c06f48c16e4ac16d4cc26c4ec36b50c46a52c56954c56856c66758c7655ac8645cc8635ec96260ca6063cb5f65cb5e67cc5c69cd5b6ccd5a6ece5870cf5773d05675d05477d1537ad1517cd2507fd34e81d34d84d44b86d54989d5488bd6468ed64590d74393d74195d84098d83e9bd93c9dd93ba0da39a2da37a5db36a8db34aadc32addc30b0dd2fb2dd2db5de2bb8de29bade28bddf26c0df25c2df23c5e021c8e020cae11fcde11dd0e11cd2e21bd5e21ad8e219dae319dde318dfe318e2e418e5e419e7e419eae51aece51befe51cf1e51df4e61ef6e620f8e621fbe723fde725'),
        // String.repeat() not available in all browsers
        contrast: colorsFromString('000000' + Array(255).join('ffffff')),
    };

    function colorsFromString(s) {
        return s.match(/.{6}/g).map(function(x) {
            return "#" + x;
        });
    }

    function initAnimation(scope) {
        scope.prevFrameIndex = -1;
        scope.isPlaying = false;
        var requestData = scope.requestData || function() {
            if (! scope.hasFrames()) {
                return;
            }
            var index = frameCache.getCurrentFrame(scope.modelName);
            if (frameCache.getCurrentFrame(scope.modelName) == scope.prevFrameIndex) {
                return;
            }
            scope.prevFrameIndex = index;
            frameCache.getFrame(scope.modelName, index, scope.isPlaying, function(index, data) {
                if (scope.element) {
                    if (data.error) {
                        panelState.setError(scope.modelName, data.error);
                        return;
                    }
                    panelState.setError(scope.modelName, null);
                    scope.load(data);
                    if (data.summaryData) {
                        $rootScope.$broadcast(scope.modelName + '.summaryData', data.summaryData);
                    }
                }
                if (scope.isPlaying) {
                    scope.advanceFrame(1);
                }
            });
        };
        scope.advanceFrame = function(increment, stopPlaying) {
            if (stopPlaying) {
                scope.isPlaying = false;
            }
            var next = frameCache.getCurrentFrame(scope.modelName) + increment;
            if (next < 0 || next > frameCache.getFrameCount(scope.modelName) - 1) {
                scope.isPlaying = false;
                return;
            }
            frameCache.setCurrentFrame(scope.modelName, next);
            requestData();
        };
        scope.defaultFrame = function() {
            if (scope.getDefaultFrame) {
                frameCache.setCurrentFrame(scope.modelName, scope.getDefaultFrame());
                requestData();
            }
            else {
                scope.lastFrame();
            }
        };
        scope.firstFrame = function() {
            scope.isPlaying = false;
            frameCache.setCurrentFrame(scope.modelName, 0);
            if (scope.modelChanged) {
                scope.modelChanged();
            }
            requestData();
        };
        scope.hasFrames = function() {
            return frameCache.isLoaded() && frameCache.getFrameCount(scope.modelName) > 0;
        };
        scope.hasManyFrames = function() {
            if (SIREPO.SINGLE_FRAME_ANIMATION && SIREPO.SINGLE_FRAME_ANIMATION.indexOf(scope.modelName) >= 0) {
                return false;
            }
            if (appState.isLoaded() && appState.models[scope.modelName].showAllFrames == '1') {
                return false;
            }
            return frameCache.isLoaded() && frameCache.getFrameCount(scope.modelName) > 1;
        };
        scope.isFirstFrame = function() {
            return frameCache.getCurrentFrame(scope.modelName) === 0;
        };
        scope.isLastFrame = function() {
            return frameCache.getCurrentFrame(scope.modelName) == frameCache.getFrameCount(scope.modelName) - 1;
        };
        scope.lastFrame = function() {
            scope.isPlaying = false;
            frameCache.setCurrentFrame(scope.modelName, frameCache.getFrameCount(scope.modelName) - 1);
            requestData();
        };
        scope.togglePlay = function() {
            scope.isPlaying = ! scope.isPlaying;
            if (scope.isPlaying) {
                if (scope.isLastFrame()) {
                    frameCache.setCurrentFrame(scope.modelName, 0);
                    requestData();
                }
                else {
                    scope.advanceFrame(1);
                }
            }
        };
        scope.$on('framesCleared', function() {
            scope.prevFrameIndex = -1;
            if (scope.clearData) {
                scope.clearData();
            }
        });
        scope.$on('modelsLoaded', requestData);
        scope.$on('framesLoaded', function(event, oldFrameCount) {
            if (scope.prevFrameIndex < 0 || oldFrameCount === 0) {
                scope.defaultFrame();
            }
            else if (scope.prevFrameIndex > frameCache.getFrameCount(scope.modelName)) {
                scope.firstFrame();
            }
            // go to the next last frame, if the current frame was the previous last frame
            else if (
                frameCache.getCurrentFrame(scope.modelName) >= oldFrameCount - 1
                || frameCache.getCurrentFrame(scope.modelName) == frameCache.getFrameCount(scope.modelName) - 2
            ) {
                scope.defaultFrame();
            }
        });
        return requestData;
    }

    function initPlot(scope) {
        var interval = null;
        var requestData = function(forceRunCount) {
            //TODO(pjm): see #1155
            // Don't request data if saving sim (data will be requested again when the save is complete)
            // var qi = requestQueue.getCurrentQI('requestQueue');
            // if (qi && qi.params && qi.params.urlOrParams === 'saveSimulationData') {
            //     return;
            // }
            var priority = getCurrentPriority();
            interval = $interval(function() {
                if (interval) {
                    $interval.cancel(interval);
                    interval = null;
                }
                if (! scope.element) {
                    return;
                }
                panelState.requestData(scope.modelName, function(data) {
                    if (! scope.element) {
                        return;
                    }
                    forceRunCount = forceRunCount || 0;
                    if (data.x_range) {
                        scope.clearData();
                        scope.load(data);
                        if (data.summaryData) {
                            $rootScope.$broadcast(scope.modelName + '.summaryData', data.summaryData);
                        }
                    }
                    else if (forceRunCount++ <= 2) {
                        // try again, probably bad data
                        panelState.clear(scope.modelName);
                        requestData(forceRunCount);
                    }
                    else {
                        panelState.setError(scope.modelName, 'server error: incomplete result');
                        srlog('incomplete response: ', data);
                    }
                }, forceRunCount ? true : false);
            }, 50 + priority * 10, 1);
        };
        function getCurrentPriority() {
            var current = scope.$parent;
            while (current) {
                if (current.getRequestPriority) {
                    return current.getRequestPriority();
                }
                if (current.requestPriority) {
                    return current.requestPriority;
                }
                current = current.$parent;
            }
            return 0;
        }

        return requestData;
    }

    function linearlySpacedArray(start, stop, nsteps) {
        if (nsteps < 1) {
            throw "linearlySpacedArray: steps " + nsteps + " < 1";
        }
        var delta = (stop - start) / (nsteps - 1);
        var res = d3.range(nsteps).map(function(d) { return start + d * delta; });
        res[res.length - 1] = stop;

        if (res.length != nsteps) {
            throw "linearlySpacedArray: steps " + nsteps + " != " + res.length;
        }
        return res;
    }

    function normalizeValues(yValues, shift) {
        var yMin = Math.min.apply(Math, yValues);
        var yMax = Math.max.apply(Math, yValues);
        var yRange = yMax - yMin;
        for (var i = 0; i < yValues.length; i++) {
            yValues[i] = (yValues[i] - yMin) / yRange - shift;  // roots are at Y=0
        }
        return yValues;
    }

    function setupSelector(scope, element) {
        scope.element = element[0];
        scope.select = function(selector) {
            var e = d3.select(scope.element);
            return selector ? e.select(selector) : e;
        };
    }

    var self = {
        COLOR_MAP: COLOR_MAP,

        addConvergencePoints: function(select, parentClass, pointsList, points) {
            var i;
            if (points.length > 1 && SIREPO.PLOTTING_SUMMED_LINEOUTS) {
                var newPoints = [];
                var dist = (points[1][0] - points[0][0]) / 2.0;
                newPoints.push(points[0]);
                var prevY = points[0][1];
                for (i = 1; i < points.length; i++) {
                    var p = points[i];
                    if (prevY != p[1]) {
                        var x = p[0] - dist;
                        newPoints.push([x, prevY], [x, p[1]]);
                        prevY = p[1];
                    }
                }
                newPoints.push(points[points.length - 1]);
                points = newPoints;
            }
            pointsList.splice(0, 0, points);
            if (pointsList.length > MAX_PLOTS) {
                pointsList = pointsList.slice(0, MAX_PLOTS);
            }
            for (i = 0; i < MAX_PLOTS; i++) {
                select(parentClass + ' .line-' + i).datum(pointsList[i] || []);
            }
            return pointsList;
        },

        calculateFWHM: function(xValues, yValues) {
            yValues = normalizeValues(yValues, 0.5);
            var positive = yValues[0] > 0;
            var listOfRoots = [];
            for (var i = 0; i < yValues.length; i++) {
                var currentPositive = yValues[i] > 0;
                if (currentPositive !== positive) {
                    listOfRoots.push(xValues[i - 1] + (xValues[i] - xValues[i - 1]) / (Math.abs(yValues[i]) + Math.abs(yValues[i - 1])) * Math.abs(yValues[i - 1]));
                    positive = !positive;
                }
            }
            var fwhm = NaN;
            if (listOfRoots.length >= 2) {
                fwhm = Math.abs(listOfRoots[listOfRoots.length - 1] - listOfRoots[0]);
            }
            return fwhm;
        },

        colorMapFromModel: function(modelName) {

            var model = appState.models[modelName];
            var modelMap = model ? model.colorMap : null;

            var modelDefaultMap;
            var info = SIREPO.APP_SCHEMA.model[modelName];
            if (info) {
                var mapInfo = info.colorMap;
                modelDefaultMap = mapInfo ? mapInfo[SIREPO.INFO_INDEX_DEFAULT_VALUE] : null;
            }

            return this.colorMapOrDefault(modelMap, modelDefaultMap);
        },

        colorMapNameOrDefault: function(mapName, defaultMapName) {
            return mapName || defaultMapName || SIREPO.PLOTTING_COLOR_MAP || SIREPO.DEFAULT_COLOR_MAP;
        },

        colorMapOrDefault: function(mapName, defaultMapName) {
            return COLOR_MAP[this.colorMapNameOrDefault(mapName, defaultMapName)];
        },

        colorScaleForPlot: function(plotRange, modelName) {
            var m = appState.models[modelName];
            var zMin = plotRange.min;
            var zMax = plotRange.max;
            if (m.colorRangeType == 'fixed') {
                zMin = m.colorMin;
                zMax = m.colorMax;
            }
            var colorMap = this.colorMapFromModel(modelName);
            return d3.scale.linear()
                .domain(linearlySpacedArray(zMin, zMax, colorMap.length))
                .range(colorMap)
                .clamp(true);
        },

        colorsFromHexString: function(color, range) {
            if (! (/^#([0-9a-f]{2}){3}$/i).test(color)) {
                throw color + ': Invalid color string';
            }
            return color.match((/[0-9a-f]{2}/ig)).map(function(h) {
                return parseInt(h, 16) / (range || 1.0);
            });
        },

        constrainFullscreenSize: function(scope, plotWidth, aspectRatio) {
            if (utilities.isFullscreen()) {
                // rough size of the panel heading, panel margins and rounded corners
                var panelTitleSize = 50 + 2 * 15 + 2 * 4;
                if (scope.isAnimation && scope.hasFrames()) {
                    // animation buttons
                    panelTitleSize += 34;
                }
                var fsel = $(utilities.getFullScreenElement());
                var height = fsel.height() - scope.margin.top - scope.margin.bottom - panelTitleSize;
                if (height < plotWidth * aspectRatio) {
                    return height / aspectRatio;
                }
            }
            return plotWidth;
        },

        drawImage: function(xAxisScale, yAxisScale, width, height, xValues, yValues, canvas, cacheCanvas, alignOnPixel) {
            var xZoomDomain = xAxisScale.domain();
            var xDomain = [xValues[0], xValues[xValues.length - 1]];
            var yZoomDomain = yAxisScale.domain();
            var yDomain = [yValues[0], yValues[yValues.length - 1]];
            var zoomWidth = xZoomDomain[1] - xZoomDomain[0];
            var zoomHeight = yZoomDomain[1] - yZoomDomain[0];
            canvas.width = width;
            canvas.height = height;
            var xPixelSize = alignOnPixel ? ((xDomain[1] - xDomain[0]) / zoomWidth * width / xValues.length) : 0;
            var yPixelSize = alignOnPixel ? ((yDomain[1] - yDomain[0]) / zoomHeight * height / yValues.length) : 0;
            var ctx = canvas.getContext('2d');
            ctx.imageSmoothingEnabled = false;
            ctx.msImageSmoothingEnabled = false;
            ctx.drawImage(
                cacheCanvas,
                -(xZoomDomain[0] - xDomain[0]) / zoomWidth * width - xPixelSize / 2,
                -(yDomain[1] - yZoomDomain[1]) / zoomHeight * height - yPixelSize / 2,
                (xDomain[1] - xDomain[0]) / zoomWidth * width + xPixelSize,
                (yDomain[1] - yDomain[0]) / zoomHeight * height + yPixelSize);
        },

        ensureDomain: function(domain) {
            if (domain[0] == domain[1]) {
                domain[0] -= (domain[0] || 1);
                domain[1] += (domain[1] || 1);
            }
            return domain;
        },

        exportCSV: function(fileName, heading, points) {
            fileName = fileName.replace(/\s+$/, '').replace(/(\_|\W|\s)+/g, '-') + '.csv';
            // format csv heading values within quotes
            var res = '"' + heading.map(function(v) {
                return v.replace(/"/g, '');
            }).join('","') + '"' + "\n";
            points.forEach(function(row) {
                res += row[0].toExponential(9) + ',' + row[1].toExponential(9) + "\n";
            });
            saveAs(new Blob([res], {type: "text/csv;charset=utf-8"}), fileName);
        },

        // returns an array of substrings of str that fit in the given width. The provided d3Text selection
        // must be part of the document so its size can be calculated
        fitSplit: function(str, d3Text, width) {
            if (!str || str.length === 0) {
                return [];
            }
            var splits = utilities.wordSplits(str).reverse();
            var split;
            for (var i = 0; i < splits.length; ++i) {
                var s = splits[i];
                var w = d3Text.text(s).node().getBBox().width;
                if (w <= width) {
                    split = s;
                    break;
                }
            }
            if (!split) {
                return [];
            }
            return $.merge([split], self.fitSplit(str.substring(split.length), d3Text, width));
        },

        formatValue: function(v, formatter, ordinateFormatter) {
            var fmt = formatter ? formatter : d3.format('.3f');
            var ordfmt = ordinateFormatter ? ordinateFormatter : d3.format('.3e');
            if (v < 1 || v > 1000000) {
                return ordfmt(v);
            }
            return fmt(v);
        },

        getAspectRatio: function(modelName, json) {
            if (appState.isLoaded() && appState.applicationState()[modelName]) {
                var ratioEnum = appState.applicationState()[modelName].aspectRatio;
                if (ratioEnum) {
                    return parseFloat(ratioEnum);
                }
            }
            return json.aspectRatio || 1.0;
        },

        initialHeight: function(scope) {
            return scope.isAnimation ? 1 : INITIAL_HEIGHT;
        },

        initImage: function(plotRange, heatmap, cacheCanvas, imageData, modelName) {
            var colorScale = this.colorScaleForPlot(plotRange, modelName);
            var xSize = heatmap[0].length;
            var ySize = heatmap.length;
            var img = imageData;

            for (var yi = 0, p = -1; yi < ySize; ++yi) {
                for (var xi = 0; xi < xSize; ++xi) {
                    var c = d3.rgb(colorScale(heatmap[yi][xi]));
                    img.data[++p] = c.r;
                    img.data[++p] = c.g;
                    img.data[++p] = c.b;
                    img.data[++p] = 255;
                }
            }
            cacheCanvas.getContext('2d').putImageData(img, 0, 0);
            return colorScale;
        },

        linkPlot: function(scope, element) {
            setupSelector(scope, element);
            scope.isAnimation = appState.isAnimationModelName(scope.modelName);
            var requestData;

            if (scope.isClientOnly) {
                requestData = function() {};
            }
            else if (scope.isAnimation) {
                requestData = initAnimation(scope);
            }
            else {
                requestData = initPlot(scope);
            }

            scope.windowResize = utilities.debounce(function() {
                scope.resize();
            }, 250);

            scope.broadcastEvent = function(args) {
                scope.$broadcast('sr-plotEvent', args);
            };

            scope.$on('$destroy', function() {
                scope.destroy();
                $(d3.select(scope.element).select('svg').node()).off();
                scope.element = null;
                $($window).off('resize', scope.windowResize);
            });

            scope.$on(
                scope.modelName + '.changed',
                function() {
                    scope.prevFrameIndex = -1;
                    if (scope.modelChanged) {
                        scope.modelChanged();
                    }
                    panelState.clear(scope.modelName);
                    requestData();
                });
            scope.isLoading = function() {
                if (scope.isAnimation) {
                    return false;
                }
                return panelState.isLoading(scope.modelName);
            };
            $($window).resize(scope.windowResize);
            // #777 catch touchstart on outer svg nodes to prevent browser zoom on ipad
            $(d3.select(scope.element).select('svg').node()).on('touchstart touchmove', function(event) {
                event.preventDefault();
                event.stopPropagation();
            });
            scope.init();
            if (appState.isLoaded()) {
                if (scope.isAnimation && scope.defaultFrame) {
                    scope.defaultFrame();
                }
                else {
                    requestData();
                }
            }
            // let the parent and child scope know the plot is ready.
            // used by parameterWithLattice
            scope.$emit('sr-plotLinked');
            // used by interactiveOverlay, focusCircle, popupReport
            scope.$broadcast('sr-plotLinked');
        },

        linearlySpacedArray: linearlySpacedArray,

        min2d: function(data) {
            return d3.min(data, function(row) {
                return d3.min(row);
            });
        },

        max2d: function(data) {
            return d3.max(data, function(row) {
                return d3.max(row);
            });
        },

        recalculateDomainFromPoints: function(yScale, points, xDomain, invertAxis) {
            var ydom;

            for (var i = 0; i < points.length; i++) {
                var d = points[i];
                if (d[0] > xDomain[1] || d[0] < xDomain[0]) {
                    continue;
                }
                if (ydom) {
                    if (d[1] < ydom[0]) {
                        ydom[0] = d[1];
                    }
                    else if (d[1] > ydom[1]) {
                        ydom[1] = d[1];
                    }
                }
                else {
                    ydom = [d[1], d[1]];
                }
            }
            if (ydom && ydom[0] != ydom[1]) {
                if (ydom[0] > 0) {
                    ydom[0] = 0;
                }
                if (invertAxis) {
                    var x = ydom[0];
                    ydom[0] = ydom[1];
                    ydom[1] = x;
                }
                yScale.domain(ydom).nice();
            }
        },

        refreshConvergencePoints: function(select, parentClass, graphLine) {
            for (var i = 0; i < MAX_PLOTS; i++) {
                select(parentClass + ' .line-' + i).attr('d', graphLine);
            }
        },

        setupSelector: setupSelector,

        tickFontSize: function(node) {
            var defaultSize = 12;
            if (! node || ! node[0] || ! node[0][0]) {
                return defaultSize;
            }
            if (node.style) {
                return utilities.fontSizeFromString(node.style('font-size')) || defaultSize;
            }
            return defaultSize;
        },

        ticks: function(axis, width, isHorizontalAxis) {
            var spacing = isHorizontalAxis ? 80 : 50;
            var n = Math.max(Math.round(width / spacing), 2);
            axis.ticks(n);
        },

        // ensures the axis domain fits in the fullDomain
        // returns true if size is reset to full
        trimDomain: function(axisScale, fullDomain) {
            var dom = axisScale.domain();
            var zoomSize = dom[1] - dom[0];

            if (zoomSize >= (fullDomain[1] - fullDomain[0])) {
                axisScale.domain(fullDomain);
                return true;
            }
            if (dom[0] < fullDomain[0]) {
                axisScale.domain([fullDomain[0], zoomSize + fullDomain[0]]);
            }
            if (dom[1] > fullDomain[1]) {
                axisScale.domain([fullDomain[1] - zoomSize, fullDomain[1]]);
            }
            return false;
        },

        vtkPlot: function(scope, element) {

            scope.element = element[0];
            var requestData = initAnimation(scope);

            scope.windowResize = utilities.debounce(function() {
                scope.resize();
            }, 250);

            scope.$on('$destroy', function() {
                scope.destroy();
                scope.element = null;
                $($window).off('resize', scope.windowResize);
            });

            scope.$on(
                scope.modelName + '.changed',
                function() {
                    scope.prevFrameIndex = -1;
                    if (scope.modelChanged) {
                        scope.modelChanged();
                    }
                    panelState.clear(scope.modelName);
                    requestData();
                });
            scope.isLoading = function() {
                return panelState.isLoading(scope.modelName);
            };
            $($window).resize(scope.windowResize);

            scope.init();
            if (appState.isLoaded()) {
                requestData();
            }
        },

    };

    return self;
});

SIREPO.app.directive('animationButtons', function() {
    return {
        restrict: 'A',
        template: [
            '<div data-ng-if="isAnimation && hasManyFrames()" style="width: 100%;" class="text-center">',
              '<button type="button" class="btn btn-default" data-ng-disabled="isFirstFrame()" data-ng-click="firstFrame()"><span class="glyphicon glyphicon-backward"></span></button>',
              '<button type="button" class="btn btn-default" data-ng-disabled="isFirstFrame()" data-ng-click="advanceFrame(-1, true)"><span class="glyphicon glyphicon-step-backward"></span></button>',
              '<button type="button" class="btn btn-default" data-ng-click="togglePlay()"><span class="glyphicon glyphicon-{{ isPlaying ? \'pause\' : \'play\' }}"></span></button>',
              '<button type="button" class="btn btn-default" data-ng-disabled="isLastFrame()" data-ng-click="advanceFrame(1, true)"><span class="glyphicon glyphicon-step-forward"></span></button>',
              '<button type="button" class="btn btn-default" data-ng-disabled="isLastFrame()" data-ng-click="lastFrame()"><span class="glyphicon glyphicon-forward"></span></button>',
            '</div>',
        ].join(''),
    };
});

SIREPO.app.directive('colorPicker', function() {
    return {
        restrict: 'A',
        scope: {
            color: '=',
            defaultColor: '<'
        },
        template: [
            '<div>',
                '<button class="dropdown-toggle sr-color-button" data-ng-style="bgColorStyle()" data-toggle="dropdown"></button>',
                '<ul class="dropdown-menu">',
                    '<div class="container col-sm-8">',
                        '<div data-ng-repeat="r in range(rows) track by $index" class="row">',
                            '<li data-ng-repeat="c in range(cols) track by $index" style="display: inline-block">',
                                '<button data-ng-if="pcIndex(r, c) < pickerColors.length" class="sr-color-button" data-ng-class="{\'selected\': getColor(color).toUpperCase() == getPickerColor(r, c).toUpperCase()}" data-ng-style="bgColorStyle(getPickerColor(r, c))" data-ng-click="setColor(getPickerColor(r, c))"></button>',
                            '</li>',
                        '<div>',
                    '<div>',
                '</ul>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {

            $scope.pickerColors = [
                '#000000', '#222222', '#444444', '#666666', '#888888', '#aaaaaa', '#cccccc', '#ffffff',
                '#0000ff', '#337777', '#3377bf', '#6992ff', '#33bb33', '#33ff33', '#00ff00', '#bbff77',
                '#ffff00', '#fff44f', '#ffbb77', '#ffa500', '#ff0000', '#bb33ff', '#ff77ff', '#f3d4c8',
            ];

            $scope.cols = 8;
            $scope.rows = Math.ceil($scope.pickerColors.length / $scope.cols);
            $scope.range = function(n) {
                var arr = [];
                for (var i = 0; i < n; ++i) {
                    arr.push(i);
                }
                return arr;
            };
            $scope.pcIndex = function(row, col) {
                return $scope.cols * row + col;
            };

            $scope.getPickerColor = function(row, col) {
                return $scope.pickerColors[$scope.pcIndex(row, col)];
            };
            $scope.getColor = function(color) {
                return color || $scope.color || $scope.defaultColor;
            };

            $scope.bgColorStyle = function(c) {
                return {
                    'background-color': $scope.getColor(c)
                };
            };

            $scope.setColor = function(color) {
                $scope.color = color;
            };
        },
    };
});

SIREPO.app.service('plot2dService', function(layoutService, panelState, plotting, utilities) {

    this.init2dPlot = function($scope, attrs) {
        var colorbar, zoom;
        // default scope values
        $.extend($scope, {
            aspectRatio: 4.0 / 7,
            zoomContainer: '.overlay',
        });
        $.extend($scope, attrs);
        $scope.width = $scope.height = 0;
        $scope.dataCleared = true;
        $scope.axes = {
            x: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh),
            y: layoutService.plotAxis($scope.margin, 'y', 'left', refresh),
        };

        function init() {
            document.addEventListener(utilities.fullscreenListenerEvent(), refresh);
            $scope.select('svg').attr('height', plotting.initialHeight($scope));
            $.each($scope.axes, function(dim, axis) {
                axis.init();
                axis.grid = axis.createAxis();
            });
            $scope.graphLine = d3.svg.line()
                .x(function(d) {
                    return $scope.axes.x.scale(d[0]);
                })
                .y(function(d) {
                    return $scope.axes.y.scale(d[1]);
                });
            resetZoom();
        }

        function refresh() {
            if (! $scope.axes.x.domain) {
                return;
            }
            if (layoutService.plotAxis.allowUpdates) {
                var width = parseInt($scope.select().style('width')) - $scope.margin.left - $scope.margin.right;
                if (isNaN(width)) {
                    return;
                }
                $scope.width = plotting.constrainFullscreenSize($scope, width, $scope.aspectRatio);
                $scope.height = $scope.aspectRatio * $scope.width;
                $scope.select('svg')
                    .attr('width', $scope.width + $scope.margin.left + $scope.margin.right)
                    .attr('height', $scope.height + $scope.margin.top + $scope.margin.bottom);
                $scope.axes.x.scale.range([0, $scope.width]);
                $scope.axes.y.scale.range([$scope.height, 0]);
                $scope.axes.x.grid.tickSize(-$scope.height);
                $scope.axes.y.grid.tickSize(-$scope.width);
            }
            var isFullSize = plotting.trimDomain($scope.axes.x.scale, $scope.axes.x.domain);
            if (isFullSize) {
                $scope.setYDomain();
            }
            else if ($scope.recalculateYDomain) {
                $scope.recalculateYDomain();
            }
            $scope.select($scope.zoomContainer)
                .classed('mouse-zoom', isFullSize)
                .classed('mouse-move-ew', ! isFullSize);
            resetZoom();
            $scope.select($scope.zoomContainer).call(zoom);
            $.each($scope.axes, function(dim, axis) {
                axis.updateLabelAndTicks({
                    width: $scope.width,
                    height: $scope.height,
                }, $scope.select);
                axis.grid.ticks(axis.tickCount);
                $scope.select('.' + dim + '.axis.grid').call(axis.grid);
            });
            if ($scope.wantColorbar) {
                colorbar.barlength($scope.height)
                    .origin([0, 0]);
                $scope.pointer = $scope.select('.colorbar').call(colorbar);
            }
            $scope.refresh();
        }

        function resetZoom() {
            zoom = $scope.axes.x.createZoom($scope);
            if ($scope.isZoomXY) {
                zoom.y($scope.axes.y.scale);
            }
        }

        $scope.clearData = function() {
            $scope.dataCleared = true;
            $scope.axes.x.domain = null;
        };

        $scope.destroy = function() {
            zoom.on('zoom', null);
            $($scope.element).find($scope.zoomContainer).off();
            // not part of all plots, just parameterPlot
            $($scope.element).find('.sr-plot-legend-item text').off();
            document.removeEventListener(utilities.fullscreenListenerEvent(), refresh);
        };

        $scope.resize = function() {
            if ($scope.select().empty()) {
                return;
            }
            refresh();
        };

        if (! $scope.setYDomain) {
            $scope.setYDomain = function() {
                $scope.axes.y.scale.domain($scope.axes.y.domain).nice();
            };
        }

        $scope.updatePlot = function(json) {
            $scope.dataCleared = false;
            $.each($scope.axes, function(dim, axis) {
                axis.parseLabelAndUnits(json[dim + '_label']);
                $scope.select('.' + dim + '-axis-label').text(json[dim + '_label']);
            });
            $scope.select('.main-title').text(json.title);
            $scope.select('.sub-title').text(json.subtitle);
            if ($scope.wantColorbar) {
                var colorMap = plotting.colorMapFromModel($scope.modelName);
                $scope.colorScale = d3.scale.linear()
                    .domain(plotting.linearlySpacedArray(json.v_min, json.v_max, colorMap.length))
                    .range(colorMap);
                colorbar = Colorbar()
                    .scale($scope.colorScale)
                    .thickness(30)
                    .margin({top: 10, right: 60, bottom: 20, left: 10})
                    .orient("vertical");
            }
            panelState.waitForUI($scope.resize);
        };

        init();
    };
});

SIREPO.app.service('focusPointService', function(plotting) {
    var svc = this;

    svc.dataCoordsToMouseCoords = function(focusPoint) {
        var mouseX, mouseY;
        if (focusPoint.config.invertAxis) {
            mouseX = focusPoint.config.yAxis.scale(focusPoint.data.y);
            mouseY = focusPoint.config.xAxis.scale(focusPoint.data.x);
        }
        else {
            mouseX = focusPoint.config.xAxis.scale(focusPoint.data.x);
            mouseY = focusPoint.config.yAxis.scale(focusPoint.data.y);
        }
        return {
            x: mouseX,
            y: mouseY
        };
    };

    svc.formatFocusPointData = function(focusPoint, xLabel, yLabel, xUnits, yUnits) {
        var xl = xLabel || focusPoint.config.xLabel || 'X';
        var yl = yLabel || focusPoint.config.yLabel || 'Y';
        var xu = processUnit(xUnits || focusPoint.config.xAxis.units);
        var yu = processUnit(yUnits || focusPoint.config.yAxis.units);
        var fmt = {
            xText: formatDatum(xl, focusPoint.data.x, xu),
            yText: formatDatum(yl, focusPoint.data.y, yu),
        };
        if (SIREPO.PLOTTING_SHOW_FWHM) {
            fmt.fwhmText = formatFWHM(focusPoint.data.fwhm, focusPoint.config.xAxis.units);
        }
        return fmt;
    };

    svc.hideFocusPoint = function(plotScope, killFocus) {
        plotScope.broadcastEvent({
            name: 'hideFocusPointInfo',
            killFocus: killFocus,
        });
        if (plotScope.hideFocusPointText) {
            plotScope.hideFocusPointText();
        }
    };

    svc.loadFocusPoint = function(focusPoint, axisPoints, preservePoint, plotScope) {
        var hideAfterLoad = ! focusPoint.load(axisPoints, preservePoint);
        if (hideAfterLoad) {
            svc.hideFocusPoint(plotScope);
        }
    };

    svc.moveFocusPoint = function(plotScope, focusPoint) {
        plotScope.broadcastEvent({
            name: 'moveFocusPointInfo',
            focusPoint: focusPoint,
        });
        if (plotScope.showFocusPointText) {
            plotScope.showFocusPointText(focusPoint);
        }
    };

    svc.refreshFocusPoint = function(focusPoint, plotScope, isMainFocus, geometry) {
        plotScope.broadcastEvent({
            name: 'showFocusPointInfo',
            focusPoint: focusPoint,
            isMainFocus: isMainFocus,
            geometry: geometry,
        });
    };

    svc.setupFocusPoint = function(xAxis, yAxis, invertAxis, name) {
        return {
            config: {
                name: name,
                color: 'steelblue',
                invertAxis: invertAxis,
                xAxis: xAxis,
                yAxis: yAxis,
                xLabel: '',
                yLabel: '',
            },
            data: {
                focusIndex: -1,
                isActive: false,
            },
            load: function(axisPoints, preservePoint) {
                if (preservePoint && (axisPoints.length != (this.config.points || []).length)) {
                    preservePoint = false;
                }
                this.config.points = axisPoints;
                if (preservePoint) {
                    return true;
                }
                return false;
            },
            move: function(step) {
                if (! this.data.isActive) {
                    return false;
                }
                if (this.config.invertAxis) {
                    step = -step;
                }
                var newIndex = this.data.focusIndex + step;
                if (newIndex < 0 || newIndex >= this.config.points.length) {
                    return false;
                }
                this.data.focusIndex = newIndex;
                return true;
            },
            unset: function() {
                this.data.focusIndex = -1;
                this.data.isActive = false;
            },
        };
    };

    svc.updateFocus = function(focusPoint, mouseX, mouseY, strategy) {
        // lastClickX determines if the user is panning or clicking on a point
        if (! focusPoint.config.points || Math.abs(focusPoint.data.lastClickX - d3.event[focusPoint.config.invertAxis ? 'clientY' : 'clientX']) > 10) {
            return false;
        }
        var x = focusPoint.config.xAxis.scale.invert(mouseX);
        strategy = strategy || 'maximum';
        var spread = strategy == 'maximum' ? 10 : 100;
        var xMin = focusPoint.config.xAxis.scale.invert(mouseX - spread);
        var xMax = focusPoint.config.xAxis.scale.invert(mouseX + spread);
        if (xMin > xMax) {
            var swap = xMin;
            xMin = xMax;
            xMax = swap;
        }
        var domain = focusPoint.config.xAxis.scale.domain();
        if (xMin < domain[0]) {
            xMin = domain[0];
        }
        if (xMax > domain[1]) {
            xMax = domain[1];
        }

        focusPoint.data.focusIndex = -1;
        var selectedPoint;
        for (var i = 0; i < focusPoint.config.points.length; i++) {
            var p = focusPoint.config.points[i];
            if (p[0] > xMax || p[0] < xMin) {
                continue;
            }
            if (strategy == 'maximum') {
                if (! selectedPoint || p[1] > selectedPoint[1]) {
                    selectedPoint = p;
                    focusPoint.data.focusIndex = i;
                    focusPoint.data.isActive = true;
                }
            }
            else if (strategy == 'closest') {
                if (! selectedPoint || (Math.abs(p[0] - x) < Math.abs(selectedPoint[0] - x))) {
                    selectedPoint = p;
                    focusPoint.data.focusIndex = i;
                    focusPoint.data.isActive = true;
                }
            }
            else {
                throw 'invalid focus point strategy: ' + strategy;
            }
        }
        if (selectedPoint) {
            return svc.updateFocusData(focusPoint);
        }
        return false;
    };

    svc.updateFocusData = function(focusPoint) {
        if (! focusPoint.data.isActive) {
            return false;
        }

        var p = focusPoint.config.points[focusPoint.data.focusIndex];
        var domain = focusPoint.config.xAxis.scale.domain();
        if (!p || p[0] < domain[0] || p[0] > domain[1]) {
            return false;
        }

        focusPoint.data.x = p[0];
        focusPoint.data.y = p[1];
        focusPoint.data.fwhm = fwhmFromLocalVals(focusPoint);
        return true;
    };

    function formatDatum(label, val, units) {
        return val || val === 0 ? label + ' = ' + plotting.formatValue(val) + (units || '') : '';
    }

    function formatFWHM(fwhm, units) {
        return fwhm ? 'FWHM = ' + d3.format('.6s')(fwhm) + (units || '') : '';
    }

    function fwhmFromLocalVals(focusPoint) {

        var points = focusPoint.config.points;
        var focusIndex = focusPoint.data.focusIndex;

        var xValues = [];
        var yValues = [];
        for (var i = 0; i < points.length; i++) {
            xValues.push(points[i][0]);
            yValues.push(points[i][1]);
        }

        // Find the local maximum and the left and right minima:
        var peakIndex = null;
        var rightMinIndex = null;
        var leftMinIndex = null;
        if (focusIndex < xValues.length - 1 && focusIndex > 0) { // check if the index is within the range
            if (points[focusIndex][1] < points[focusIndex - 1][1] || points[focusIndex][1] < points[focusIndex + 1][1]) { // step on the left and on the right to see if it's a local maximum
                // It's not a local maximum!
                if (points[focusIndex][1] < points[focusIndex - 1][1]) { // we are on the right from the maximum
                    for (i = focusIndex; i > 0; i--) { // <<< go to the left to find the maximum
                        if (points[i-1][1] < points[i][1]) { // we crossed the maximum and started to descend
                            // ^ <<< - we reached the maximum:
                            peakIndex = i;
                            break;
                        }
                    }
                }
                else { // we are on the left from the maximum
                    for (i = focusIndex + 1; i < xValues.length; i++) { // >>> go to the right to find the maximum
                        if (points[i-1][1] > points[i][1]) { // we crossed the maximum and started to descend
                            // >>> ^ - we reached the maximum:
                            peakIndex = i - 1;
                            break;
                        }
                    }
                }
            }
            else {
                // ^ - we are at the local maximum.
                peakIndex = focusIndex;
            }

            // >>> go to the right from the peak to find the right minimum:
            for (i = peakIndex + 1; i < xValues.length; i++) {
                if (points[i-1][1] < points[i][1]) {
                    // >>> v - we reached the right minimum:
                    rightMinIndex = i - 1;
                    break;
                }
            }
            if (! rightMinIndex) {
                rightMinIndex = xValues.length - 1;
            }

            // <<< go to the left to find the left minimum:
            for (i = peakIndex; i > 0; i--) {
                if (points[i-1][1] > points[i][1]) {
                    // v <<< - we reached the left minimum:
                    leftMinIndex = i;
                    break;
                }
            }
            if (! leftMinIndex) {
                leftMinIndex = 0;
            }
        }
        // Calculate the FWHM for the selected peak (between the left and the right minima - v^v):
        if (peakIndex) {
            var localXValues = [];
            var localYValues = [];
            for (i = leftMinIndex; i <= rightMinIndex; i++) {
                localXValues.push(points[i][0]);
                localYValues.push(points[i][1]);
            }
            return plotting.calculateFWHM(localXValues, localYValues);
        }
        return NaN;
    }

    function processUnit(unit) {
        if (! unit) {
            return null;
        }
        // units that are "1/<unit>" become "<unit>-1" (otherwise the "1" looks like part of the value)
        // Once laTeX is handled we won't need this kind of thing
        var isInverse = /^1\/([a-zA-Z]+)$/;
        var m = unit.match(isInverse);
        if (m) {
            return m[1] + '-1';
        }
        return unit;
    }

});

SIREPO.app.service('layoutService', function(plotting, utilities) {

    var svc = this;

    svc.parseLabelAndUnits = function(label) {
        var units = '';
        var match = label.match(/\[(.*?)\]/);
        if (match) {
            units = match[1];
            label = label.replace(/\s*\[.*?\]/, '');
        }
        return {
            label: label,
            units: units
        };
    };

    svc.plotAxis = function(margin, dimension, orientation, refresh) {
        var MAX_TICKS = 10;
        var ZERO_REGEX = /^\-?0(\.0+)?(e\+0)?$/;
        // global value, don't allow margin updates during zoom/pad handling
        svc.plotAxis.allowUpdates = true;

        var self = {};
        var debouncedRefresh = utilities.debounce(function() {
            var sum = margin.left + margin.right;
            refresh();
            if (sum != margin.left + margin.right) {
                refresh();
            }
        }, 500);

        function applyUnit(v, unit) {
            return unit ? unit.scale(v) : v;
        }

        function calcFormat(count, unit, base, isBaseFormat) {
            var code = 'e';
            var tickValues = self.scale.ticks(count);
            var v0 = applyUnit(tickValues[0] - (base || 0), unit);
            var v1 = applyUnit(tickValues[tickValues.length - 1] - (base || 0), unit);
            var p0 = valuePrecision(v0);
            var p1 = valuePrecision(v1);
            var decimals = valuePrecision(applyUnit(tickValues[1] - tickValues[0], unit));
            if (isBaseFormat || useFloatFormat(decimals)) {
                if ((v0 == 0 && useFloatFormat(p1)) || (v1 == 0 && useFloatFormat(p0)) || (useFloatFormat(p0) && useFloatFormat(p1))) {
                    code = 'f';
                }
            }
            else {
                if (p0 == 0) {
                    decimals -= p1;
                }
                else if (p1 == 0) {
                    decimals -= p0;
                }
                else {
                    decimals -= Math.max(p0, p1);
                }
            }
            decimals = decimals < 0 ? Math.abs(decimals) : 0;
            return {
                decimals: decimals,
                code: code,
                unit: unit,
                tickValues: tickValues,
                format: d3.format('.' + decimals + code),
            };
        }

        function calcTickCount(format, canvasSize, unit, base, fontSize) {
            var d = self.scale.domain();
            var width = Math.max(
                4,
                Math.max(format(applyUnit(d[0] - (base || 0), unit)).length, format(applyUnit(d[1] - (base || 0), unit)).length)
            );
            var tickCount;
            if (dimension == 'x') {
                tickCount = Math.min(MAX_TICKS, Math.round(canvasSize.width / (width * fontSize)));
            }
            else {
                tickCount = Math.min(MAX_TICKS, Math.round(canvasSize.height / (5 * fontSize)));
            }
            return Math.max(2, tickCount);
        }

        //TODO(pjm): this could be refactored, moving the base recalc out
        function calcTicks(formatInfo, canvasSize, unit, fontSize) {
            var d = self.scale.domain();
            var tickCount = calcTickCount(formatInfo.format, canvasSize, unit, null, fontSize);
            formatInfo = calcFormat(tickCount, unit);
            if (formatInfo.decimals > 3) {
                var baseFormat = calcFormat(tickCount, unit, null, true).format;
                var base = midPoint(formatInfo, d);
                if (unit) {
                    unit = d3.formatPrefix(Math.max(Math.abs(d[0] - base), Math.abs(d[1] - base)), 0);
                }
                formatInfo = calcFormat(tickCount, unit, base);
                tickCount = calcTickCount(formatInfo.format, canvasSize, unit, base, fontSize);
                var f2 = calcFormat(tickCount, unit);
                base = midPoint(f2, d);
                if (unit) {
                    unit = d3.formatPrefix(Math.max(Math.abs(d[0] - base), Math.abs(d[1] - base)), 0);
                }
                formatInfo = calcFormat(tickCount, unit, base);
                formatInfo.base = base;
                formatInfo.baseFormat = baseFormat;
            }
            if ((orientation == 'left' || orientation == 'right') && ! canvasSize.isPlaying) {
                var w = Math.max(formatInfo.format(applyUnit(d[0] - (formatInfo.base || 0), unit)).length, formatInfo.format(applyUnit(d[1] - (formatInfo.base || 0), unit)).length);
                margin[orientation] = (w + 6) * (fontSize / 2);
            }
            self.svgAxis.ticks(tickCount);
            self.tickCount = tickCount;
            self.svgAxis.tickFormat(function(v) {
                var res = formatInfo.format(applyUnit(v - (formatInfo.base || 0), unit));
                // format zero values as '0'
                if (ZERO_REGEX.test(res)) {
                    return '0';
                }
                return res.replace(/e\+0$/, '');
            });
            self.unitSymbol = formatInfo.unit ? formatInfo.unit.symbol : '';
            return formatInfo;
        }

        function midPoint(formatInfo, domain) {
            // find the tickValue which is closest to the domain midpoint
            var mid = domain[0] + (domain[1] - domain[0]) / 2;
            var values = formatInfo.tickValues;
            var v = (values.length - 1) / 2;
            var i1 = Math.floor(v);
            var i2 = Math.ceil(v);
            if (Math.abs(values[i1] - mid) > Math.abs(values[i2] - mid)) {
                return values[i2];
            }
            return values[i1];
        }

        function useFloatFormat(logV) {
            return logV >= -2 && logV <= 3;
        }

        function valuePrecision(v) {
            Math.log10 = Math.log10 || function(x) {
                return Math.log(x) * Math.LOG10E;
            };
            return Math.floor(Math.log10(Math.abs(v || 1)));
        }

        self.createAxis = function(orient) {
            return d3.svg.axis().scale(self.scale).orient(orient || orientation);
        };

        self.createZoom = function() {
            return d3.behavior.zoom()[dimension](self.scale)
                .on('zoom', function() {
                    // don't update the plot margins during zoom/pad
                    svc.plotAxis.allowUpdates = false;
                    refresh();
                    svc.plotAxis.allowUpdates = true;
                    // schedule a refresh to adjust margins later
                    debouncedRefresh();
                });
        };

        self.init = function() {
            self.scale = d3.scale.linear();
            self.svgAxis = self.createAxis();
        };

        self.parseLabelAndUnits = function(label) {
            var lu = svc.parseLabelAndUnits(label);
            self.units = lu.units;
            self.unitSymbol = '';
            self.label = lu.label;
        };

        function baseLabel() {
            // remove any parenthesis first, ex. "p (mec)" --> "p"
            var label = self.label.replace(/\s\(.*/, '');
            var res = label.length > 4 ? dimension : label;
            // padding is unicode thin-space
            return res ? ('< ' + res + ' >') : '';
        }

        self.updateLabelAndTicks = function(canvasSize, select, cssPrefix) {
            if (svc.plotAxis.allowUpdates) {
                // update the axis to get the tick font size from the css
                select((cssPrefix || '') + '.' + dimension + '.axis').call(self.svgAxis);
                var fontSize = plotting.tickFontSize(select('.sr-plot .axis text'));
                var formatInfo, unit;
                if (self.units) {
                    var d = self.scale.domain();
                    unit = d3.formatPrefix(Math.max(Math.abs(d[0]), Math.abs(d[1])), 0);
                    formatInfo = calcTicks(calcFormat(MAX_TICKS, unit), canvasSize, unit, fontSize);
                    select('.' + dimension + '-axis-label').text(
                        self.label + (formatInfo.base ? (' - ' + baseLabel()) : '')
                        + ' [' + formatInfo.unit.symbol + self.units + ']');
                }
                else {
                    formatInfo = calcTicks(calcFormat(MAX_TICKS), canvasSize, null, fontSize);
                    if (self.label) {
                        select('.' + dimension + '-axis-label').text(
                            self.label + (formatInfo.base ? (' - ' + baseLabel()) : ''));
                    }
                }
                var formattedBase = '';
                if (formatInfo.base) {
                    var label = baseLabel();
                    if (label) {
                        label += ' = ';
                    }
                    else {
                        if (formatInfo.base > 0) {
                            label = '+';
                        }
                    }
                    formattedBase = label + formatInfo.baseFormat(applyUnit(formatInfo.base, unit));
                    formattedBase = formattedBase.replace(/0+$/, '');
                    formattedBase = formattedBase.replace(/0+e/, 'e');
                    if (unit) {
                        formattedBase += unit.symbol + self.units;
                    }
                }
                if (! self.noBaseFormat) {
                    select('.' + dimension + '-base').text(formattedBase);
                }
            }
            select((cssPrefix || '') + '.' + dimension + '.axis').call(self.svgAxis);
        };

        return self;
    };
});

SIREPO.app.directive('columnForAspectRatio', function(appState) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@columnForAspectRatio',
        },
        transclude: true,
        template: [
            '<div class="{{ columnClass() }}">',
              '<div data-ng-transclude=""></div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.columnClass = function() {
                if (appState.isLoaded()) {
                    var ratio = parseFloat(appState.applicationState()[$scope.modelName].aspectRatio);
                    if (ratio <= 0.5) {
                        return 'col-md-12 col-xl-8';
                    }
                }
                return 'col-md-6 col-xl-4';
            };
        }
    };
});

SIREPO.app.directive('interactiveOverlay', function(focusPointService, keypressService, plotting, $timeout) {
    return {
        restrict: 'A',
        scope: {
            reportId: '<',
            focusPoints: '=',
            focusStrategy: '=',
        },
        controller: function($scope, $element) {
            if (! $scope.focusPoints) {
                // interactiveOverlay only applies if focusPoints are defined on the plot
                return;
            }
            plotting.setupSelector($scope, $element);

            // random id for this listener
            var listenerId = Math.floor(Math.random() * Number.MAX_SAFE_INTEGER);
            var geometries = [];
            var plotScope;

            function copyToClipboard() {
                if (! $scope.focusPoints || $scope.focusPoints.length === 0) {
                    return;
                }
                var focusHint = plotScope.select('.focus-hint');
                var focusText = plotScope.select('.focus-text');
                focusText.style('display', 'none');
                var inputField = $('<textarea>');
                $('body').append(inputField);

                var fmtText = '';
                $scope.focusPoints.forEach(function(fp, fpIndex) {
                    var fpt = plotScope.formatFocusPointData(fp);
                    if (fpIndex === 0) {
                        fmtText = fmtText + fpt.xText + '\n';
                    }
                    fmtText = fmtText + fpt.yText;
                    if (fpt.fwhmText) {
                        fmtText = fmtText + ', ' + fpt.fwhmText;
                    }
                    fmtText = fmtText + '\n';
                });
                inputField.val(fmtText).select();
                try {
                    document.execCommand('copy');
                    focusHint.style('display', null);
                    focusHint.text('Copied to clipboard');
                    $timeout(function() {
                        focusHint.style('display', 'none');
                        focusText.style('display', null);
                    }, 1000);
                }
                catch (e) {
                }
                inputField.remove();
            }

            function init() {
                if ($scope.focusPoints) {
                    $scope.focusPoints.forEach(function(fp) {
                        geometries.push(setupGeometry());
                    });
                }
                $scope.select()
                    .on('mousedown', onMouseDown)
                    .on('click', onClick)
                    .on('dblclick', copyToClipboard);
            }

            function onClick() {
                /*jshint validthis: true*/
                if (d3.event.defaultPrevented) {
                    // ignore event if drag is occurring
                    return;
                }
                // start listening on clicks instead of mouseover
                keypressService.addListener(listenerId, onKeyDown, $scope.reportId);

                if ($scope.focusPoints) {
                    for (var fpIndex = 0; fpIndex < $scope.focusPoints.length; ++fpIndex) {
                        var fp = $scope.focusPoints[fpIndex];
                        var geometry = geometries[fpIndex];
                        if (! geometry) {
                            geometry = setupGeometry();
                            geometries[fpIndex] = geometry;
                        }
                        var axisIndex =  fp.config.invertAxis ? 1 : 0;
                        geometry.mouseX = d3.mouse(this)[axisIndex];
                        geometry.mouseY = d3.mouse(this)[1 - axisIndex];
                        if (focusPointService.updateFocus(fp, geometry.mouseX, geometry.mouseY, $scope.focusStrategy)) {
                            focusPointService.refreshFocusPoint(fp, plotScope, true, geometry);
                            if (plotScope.showFocusPointText) {
                                plotScope.showFocusPointText(fp);
                            }
                        }
                    }
                }
            }

            function onKeyDown() {
                var keyCode = d3.event.keyCode;
                var shiftFactor = d3.event.shiftKey ? 10 : 1;

                // do some focusPoint-independent work outside the loop
                if (keyCode == 27) { // escape
                    removeKeyListener();
                }
                if (keyCode == 9) {  // tab
                    keypressService.enableNextListener(d3.event.shiftKey ? -1 : 1);
                    d3.event.preventDefault();
                }
                for (var fpIndex = 0; fpIndex < $scope.focusPoints.length; ++fpIndex) {
                    if (!$scope.focusPoints[fpIndex].data.isActive) {
                        return;
                    }
                    var doUpdate = false;
                    var fp = $scope.focusPoints[fpIndex];
                    var geometry = geometries[fpIndex];
                    if (keyCode == 27) { // escape
                        fp.unset();
                        focusPointService.hideFocusPoint(plotScope);
                    }
                    if (keyCode == 37 || keyCode == 40) { // left & down
                        fp.move(-1 * shiftFactor);
                        doUpdate = true;
                        d3.event.preventDefault();
                    }
                    if (keyCode == 39 || keyCode == 38) { // right & up
                        fp.move(1 * shiftFactor);
                        doUpdate = true;
                        d3.event.preventDefault();
                    }
                    if (doUpdate) {
                        if (focusPointService.updateFocusData(fp)) {
                            focusPointService.moveFocusPoint(plotScope, fp);
                        }
                        else {
                            focusPointService.hideFocusPoint(plotScope);
                        }
                    }
                }
            }

            function onMouseDown() {
                if ($scope.focusPoints) {
                    $scope.focusPoints.forEach(function(fp) {
                        fp.data.lastClickX = d3.event[fp.config.invertAxis ? 'clientY' : 'clientX'];
                    });
                }
            }

            function removeKeyListener() {
                keypressService.removeListener(listenerId);
            }

            function setupGeometry() {
                return {
                    mouseX: 0,
                    mouseY: 0,
                };
            }

            init();

            $scope.$on('$destroy', function(event) {
                keypressService.removeReport($scope.reportId);
            });

            $scope.$on('sr-plotLinked', function(event) {
                plotScope = event.targetScope;
                //TODO(pjm): shouldn't put on plot scope, but needed by popupReport
                plotScope.copyToClipboard = copyToClipboard;
            });

            $scope.$on('sr-plotEvent', function(event, args) {
                if (args.name == 'hideFocusPointInfo') {
                    if (args.killFocus) {
                        removeKeyListener();
                    }
                }
            });
        },
    };
});

SIREPO.app.directive('focusCircle', function(focusPointService, plotting) {
    return {
        restrict: 'A',
        scope: {
            focusPoint: '=',
            isSoloPoint: '@',
        },
        // no "template", svg element outside a <svg> element don't work in MS Edge 38.14393
        controller: function($scope, $element) {
            plotting.setupSelector($scope, $element);
            var defaultCircleSize = $scope.select('circle').attr('r');

            function hideFocusCircle() {
                $scope.select().style('display', 'none');
            }

            function setInfoVisible(isVisible) {
                // don't invoke hideFocusCircle() - we want the data in place
                $scope.select('circle').style('opacity', isVisible ? 1.0 : 0.0);
            }

            function showFocusCircle(isMainFocus) {
                $scope.select().style('display', null);
                if (! focusPointService.updateFocusData($scope.focusPoint)) {
                    hideFocusCircle();
                    return;
                }
                var circle = $scope.select('circle');
                if (isMainFocus) {
                    circle.attr('r', defaultCircleSize);
                }
                else {
                    circle.attr('r', defaultCircleSize - 2);
                }
                circle.style('stroke', $scope.focusPoint.config.color);
                var mouseCoords = focusPointService.dataCoordsToMouseCoords($scope.focusPoint);
                $scope.select().attr('transform', 'translate(' + mouseCoords.x + ',' + mouseCoords.y + ')');
            }

            $scope.$on('sr-plotEvent', function(event, args) {
                if (args.name == 'showFocusPointInfo') {
                    if ($scope.isSoloPoint) {
                        if (args.focusPoint == $scope.focusPoint) {
                            showFocusCircle(args.isMainFocus);
                        }
                        else if (args.isMainFocus) {
                            hideFocusCircle();
                            $scope.focusPoint.unset();
                        }
                    }
                    else {
                        showFocusCircle(args.isMainFocus);
                    }
                }
                else if (args.name == 'hideFocusPointInfo') {
                    hideFocusCircle();
                }
                else if (args.name == 'moveFocusPointInfo') {
                    if (args.focusPoint == $scope.focusPoint) {
                        showFocusCircle();
                    }
                }
                else if (args.name == 'setInfoVisible') {
                    if (args.focusPoint == $scope.focusPoint) {
                        setInfoVisible(args.isVisible);
                    }
                }
            });
        },
    };
});

SIREPO.app.directive('popupReport', function(focusPointService, plotting) {
    return {
        restrict: 'A',
        scope: {
            focusPoints: '=',
        },
        template: [
            '<g class="popup-group">',
              '<g data-is-svg="true" data-ng-drag="true" data-ng-drag-data="focusPoints" data-ng-drag-success="dragDone($data, $event)">',
                '<g>',
                  '<rect class="report-window" rx="4px" ry="4px" x="0" y="0"></rect>',
                  '<g ng-drag-handle="">',
                    '<rect class="report-window-title-bar" x="1" y="1"></rect>',
                    '<text class="report-window-title-icon report-window-close close" y="0" dy="1em" dx="-1em">&#215;</text>',
                    '<text class="report-window-title-icon report-window-copy" y="0" dy="1.5em" dx="0.5em">',
                      '&#xe205;',
                    '</text>',
                  '</g>',
                '</g>',
                '<g class="text-block">',
                  '<text id="x-text" class="focus-text-popup" x="0" dx="0.5em"> </text>',
                  '<g class="text-group" data-ng-repeat="fp in focusPoints">',
                  // the space value is needed for PNG download on MSIE 11
                    '<g data-ng-attr-id="y-text-{{$index}}"></g>',
                    '<g class="fwhm-text-group">',
                      '<text data-ng-attr-id="fwhm-text-{{$index}}" class="focus-text-popup" x="0" dx="0.5em"> </text>',
                    '</g>',
                  '</g>',
                '</g>',
              '</g>',
              // this element is used to check the size of strings for wrapping.  It cannot be hidden or the size
              // will be 0, so instead we make the text transparent
              '<text class="hidden-txt-layout" fill="none"></text>',
            '</g>',
        ].join(''),
        controller: function($scope, $element) {
            if (! $scope.focusPoints) {
                // popupReport only applies if focusPoints are defined on the plot
                return;
            }
            plotting.setupSelector($scope, $element);

            var borderWidth = 1;
            var didDragToNewPositon = false;
            var moveEventDetected = false;
            var popupMargin = 4;
            var textMargin = 8;
            var titleBarHeight = 24;
            var dgElement;
            var group;
            var plotScope;

            function closePopup() {
                focusPointService.hideFocusPoint(plotScope, true);
            }

            function copyToClipboard() {
                $scope.select('.report-window-copy')
                    .transition()
                    .delay(0)
                    .duration(100)
                    .style('fill', 'white')
                    .transition()
                    .style('fill', null);
                plotScope.copyToClipboard();
            }

            function currentXform() {
                var xform = {
                    tx: NaN,
                    ty: NaN
                };
                var reportTransform = group.attr('transform');
                if (reportTransform) {
                    var xlateIndex = reportTransform.indexOf('translate(');
                    if (xlateIndex >= 0) {
                        var tmp = reportTransform.substring('translate('.length);
                        var coords = tmp.substring(0, tmp.indexOf(')'));
                        var delimiter = coords.indexOf(',') >= 0 ? ',' : ' ';
                        xform.tx = parseFloat(coords.substring(0, coords.indexOf(delimiter)));
                        xform.ty = parseFloat(coords.substring(coords.indexOf(delimiter) + 1));
                    }
                }
                return xform;
            }

            function hidePopup() {
                didDragToNewPositon = false;
                $scope.select().style('display', 'none');
            }

            function init() {
                $scope.focusPoints.allowClone = false;
                group = $scope.select('.popup-group');
                dgElement = angular.element(group.select('g').node());
                group.select('.report-window-close')
                    .on('click', closePopup);
                group.select('.report-window-copy')
                    .on('click', copyToClipboard);
            }

            function movePopup() {
                // move in response to arrow keys - but if user dragged the window we assume they don't
                // want it to track the focus point
                if (didDragToNewPositon) {
                    refreshText();
                }
                else {
                    // just use the first focus point
                    var mouseCoords = focusPointService.dataCoordsToMouseCoords($scope.focusPoints[0]);
                    var xf = currentXform();
                    if (! isNaN(xf.tx) && ! isNaN(xf.ty)) {
                        showPopup({mouseX: mouseCoords.x, mouseY: xf.ty}, true);
                    }
                }
            }

            function popupTitleSize() {
                 return {
                    width: popupWindowSize().width - 2 * borderWidth,
                    height: titleBarHeight
                };
            }

            function popupWindowSize() {
                var bbox = group.select('.text-block').node().getBBox();
                var maxWidth = parseFloat($scope.select().attr('width')) - 2 * popupMargin;
                var maxHeight = parseFloat($scope.select().attr('height')) - 2 * popupMargin;
                return {
                    width: Math.min(maxWidth, bbox.width + 2 * textMargin),
                    height: Math.min(maxHeight, titleBarHeight + bbox.height + 2 * textMargin)
                };
            }

            function refreshText() {
                // format data
                var maxWidth = selectAttr('width') - 2 * popupMargin - 2 * textMargin;

                // all focus points share the same x value
                var xText = plotScope.formatFocusPointData($scope.focusPoints[0]).xText;
                var hNode = $scope.select('.hidden-txt-layout');
                var tNode = group.select('#x-text')
                    .text(xText)
                    .style('fill', '#000000')
                    .attr('y', popupTitleSize().height)
                    .attr('dy', '1em');
                var tSize = tNode.node().getBBox();
                var txtY = tSize.y + tSize.height;
                $scope.focusPoints.forEach(function(fp, fpIndex) {
                    var color = fp.config.color;
                    var fmtText = plotScope.formatFocusPointData(fp);
                    var fits = plotting.fitSplit(fmtText.yText, hNode, maxWidth);
                    var yGrp = group.select('#y-text-' + fpIndex);
                    yGrp.selectAll('text').remove();
                    fits.forEach(function(str) {
                        tNode = yGrp.append('text')
                            .text(str)
                            .attr('class', 'focus-text-popup')
                            .style('fill', color)
                            .attr('x', 0)
                            .attr('dx', '0.5em')
                            .attr('y', txtY)
                            .attr('dy', '1em');
                        txtY += tNode.node().getBBox().height;
                    });

                    tNode = group.select('#fwhm-text-' + fpIndex)
                        .text(fmtText.fwhmText)
                        .style('fill', color)
                        .attr('y', txtY)
                        .attr('dy', '1em');
                    txtY += (tNode.node().getBBox().height + textMargin);
                });
                hNode.text('');
                refreshWindow();
            }

            function refreshWindow() {
                var size = popupWindowSize();
                $scope.select('.report-window')
                    .attr('width', size.width)
                    .attr('height', size.height);
                var tSize = popupTitleSize();
                $scope.select('.report-window-title-bar')
                    .attr('width', tSize.width)
                    .attr('height', tSize.height);
                $scope.select('.report-window-close')
                    .attr('x', size.width);
            }

            function selectAttr(name) {
                return parseFloat($scope.select().attr(name));
            }

            function setInfoVisible(pIndex, isVisible) {
                // don't completely hide for now, so it's clear the data exists
                var textAlpha = isVisible ? 1.0 : 0.4;
                group.select('#x-text-' + pIndex).style('opacity', textAlpha);
                group.select('#y-text-' + pIndex).style('opacity', textAlpha);
                group.select('#fwhm-text-' + pIndex).style('opacity', textAlpha);
            }

            function showPopup(geometry, isReposition) {
                $scope.select().style('display', 'block');
                refreshText();
                if (didDragToNewPositon && ! isReposition) {
                    return;
                }
                // set position and size
                var newX = Math.max(popupMargin, geometry.mouseX);
                var newY = Math.max(popupMargin, geometry.mouseY);
                var rptWindow = group.select('.report-window');
                var tbw = parseFloat(rptWindow.attr('width'));
                var tbh = parseFloat(rptWindow.attr('height'));

                newX = Math.min(selectAttr('width') - tbw - popupMargin, newX);
                newY = Math.min(selectAttr('height') - tbh - popupMargin, newY);
                group.attr('transform', 'translate(' + newX + ',' + newY + ')');
                group.select('.report-window-title-bar').attr('width', tbw - 2 * borderWidth);
            }

            $scope.dragDone = function($data, $event) {
                didDragToNewPositon = true;
                var xf = currentXform();
                if (moveEventDetected) {
                    showPopup({mouseX: xf.tx + $event.tx, mouseY: xf.ty + $event.ty}, true);
                }
                moveEventDetected = false;
            };

            init();

            $scope.$on('sr-plotEvent', function(event, args) {
                if (! group.node()) {
                    // special handler for Internet Explorer which can't resolve group
                    return;
                }
                if (args.name == 'showFocusPointInfo') {
                    if (args.geometry) {
                        showPopup(args.geometry);
                    }
                }
                else if (args.name == 'hideFocusPointInfo') {
                    hidePopup();
                }
                else if (args.name == 'moveFocusPointInfo') {
                    movePopup();
                }
                else if (args.name == 'setInfoVisible') {
                    setInfoVisible(args.index, args.isVisible);
                }
            });

            $scope.$on('sr-plotLinked', function(event) {
                plotScope = event.targetScope;
            });

            $scope.$on('$destroy', function() {
                group.select('.report-window-close')
                    .on('click', null);
                group.select('.report-window-copy')
                    .on('click', null);
            });

            // ngDraggable interprets even clicks as starting a drag event - we don't want to do transforms later
            // unless we really moved it
            $scope.$on('draggable:move', function(event, obj) {
                // all popups will hear this event, so confine logic to this one
                if (obj.element[0] == dgElement[0]) {
                    moveEventDetected = true;
                }
            });
        },
    };
});

SIREPO.app.directive('plot2d', function(focusPointService, plotting, plot2dService) {
    return {
        restrict: 'A',
        scope: {
            reportId: '<',
            modelName: '@',
        },
        templateUrl: '/static/html/plot2d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            var points;
            $scope.focusPoints = [];

            $scope.formatFocusPointData = function(fp) {
                return focusPointService.formatFocusPointData(fp);
            };

            $scope.init = function() {
                plot2dService.init2dPlot($scope, {
                    margin: {top: 50, right: 10, bottom: 50, left: 75},
                });
                $scope.focusPoints.push(
                    focusPointService.setupFocusPoint($scope.axes.x, $scope.axes.y, false));
            };

            $scope.load = function(json) {
                var xPoints = json.x_points
                    ? json.x_points
                    : plotting.linearlySpacedArray(json.x_range[0], json.x_range[1], json.points.length);
                var xdom = [json.x_range[0], json.x_range[1]];
                if (!($scope.axes.x.domain && $scope.axes.x.domain[0] == xdom[0] && $scope.axes.x.domain[1] == xdom[1])) {
                    $scope.axes.x.domain = xdom;
                    points = [];
                    $scope.axes.x.scale.domain(xdom);
                }
                if (!SIREPO.PLOTTING_SHOW_CONVERGENCE_LINEOUTS) {
                    points = [];
                }
                var ymin = d3.min(json.points);
                if (ymin > 0) {
                    ymin = 0;
                }
                $scope.axes.y.domain = [ymin, d3.max(json.points)];
                $scope.axes.y.scale.domain($scope.axes.y.domain).nice();
                var p = d3.zip(xPoints, json.points);
                plotting.addConvergencePoints($scope.select, '.plot-viewport', points, p);

                $scope.focusPoints.forEach(function(fp) {
                    focusPointService.loadFocusPoint(fp, p, true, $scope);
                    fp.config.xLabel = json.x_label;
                    fp.config.yLabel = json.y_label;
                });

                $scope.updatePlot(json);
            };

            $scope.recalculateYDomain = function() {
                plotting.recalculateDomainFromPoints($scope.axes.y.scale, points[0], $scope.axes.x.scale.domain());
            };

            $scope.refresh = function() {
                plotting.refreshConvergencePoints($scope.select, '.plot-viewport', $scope.graphLine);
                for (var fpIndex = 0; fpIndex < $scope.focusPoints.length; ++fpIndex) {
                    focusPointService.refreshFocusPoint($scope.focusPoints[fpIndex], $scope);
                }
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('plot3d', function(appState, focusPointService, layoutService, plotting, utilities) {
    return {
        restrict: 'A',
        scope: {
            reportId: '<',
            modelName: '@',
        },
        templateUrl: '/static/html/plot3d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            var MIN_PIXEL_RESOLUTION = 10;
            $scope.margin = {
                top: 50,
                left: 50,
                right: 45,
                bottom: 30,
            };
            $scope.pad = 10;
            $scope.noLabelPad = -18;
            // will be set to the correct size in resize()
            $scope.canvasSize = {
                width: 0,
                height: 0,
            };
            $scope.titleCenter = 0;
            $scope.subTitleCenter = 0;
            $scope.rightPanelWidth = $scope.bottomPanelHeight = 55;
            $scope.dataCleared = true;
            $scope.wantCrossHairs = ! SIREPO.PLOTTING_SUMMED_LINEOUTS;
            $scope.focusTextCloseSpace = 18;
            $scope.focusPoints = [];

            var canvas, ctx, fullDomain, heatmap, lineOuts, prevDomain, xyZoom;
            var cacheCanvas, imageData;
            var aspectRatio = 1.0;
            var axes = {
                x: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh),
                y: layoutService.plotAxis($scope.margin, 'y', 'right', refresh),
                bottomY: layoutService.plotAxis($scope.margin, 'y', 'left', refresh),
                rightX: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh),
            };
            axes.rightX.noBaseFormat = true;
            axes.bottomY.noBaseFormat = true;

            var cursorShape = {
                '11': 'mouse-move-ew',
                '10': 'mouse-move-e',
                '01': 'mouse-move-w',
                '22': 'mouse-move-ns',
                '20': 'mouse-move-n',
                '02': 'mouse-move-s',
            };

            function adjustZoomToCenter(scale) {
                // if the domain is almost centered on 0.0 (within 10%) adjust zoom and offset to center
                var domain = scale.domain();
                if (domain[0] < 0 && domain[1] > 0) {
                    var width = domain[1] - domain[0];
                    var diff = (domain[0] + domain[1]) / width;
                    if (diff > 0 && diff < 0.1) {
                        domain[1] = -domain[0];
                    }
                    else if (diff > -0.1 && diff < 0) {
                        domain[0] = -domain[1];
                    }
                    else {
                        return;
                    }
                    scale.domain(domain);
                }
            }

            function centerNode(node, defaultCtr) {
                // center the node over the image; if node is too large, center it over whole plot
                if (node && ! (node.style && node.style.display == 'none')) {
                    var width = node.getBBox().width;
                    var ctr = $scope.canvasSize.width / 2;
                    if (width > $scope.canvasSize.width) {
                        ctr += $scope.rightPanelWidth / 2;
                    }
                    return ctr;
                }
                if (defaultCtr) {
                    return defaultCtr;
                }
                return 0;
            }

            function centerSubTitle() {
                $scope.subTitleCenter = centerNode(select('text.sub-title').node(), $scope.subTitleCenter);
            }

            function centerTitle() {
                $scope.titleCenter = centerNode(select('text.main-title').node(), $scope.titleCenter);
            }

            function clipDomain(scale, axisName) {
                var domain = fullDomain[axisName == 'x' ? 0 : 1];
                var domainSize = domain[1] - domain[0];
                var fudgeFactor = domainSize * 0.001;
                var d = scale.domain();
                var canMove = axisName == 'x' ? [1, 1] : [2, 2];

                if (d[0] - domain[0] <= fudgeFactor) {
                    canMove[0] = 0;
                    d[1] -= d[0] - domain[0];
                    d[0] = domain[0];
                }
                if (domain[1] - d[1] <= fudgeFactor) {
                    canMove[1] = 0;
                    d[0] -= d[1] - domain[1];
                    if (d[0] - domain[0] <= fudgeFactor) {
                        canMove[0] = 0;
                        d[0] = domain[0];
                    }
                    d[1] = domain[1];
                }
                scale.domain(d);
                var cursorKey = '' + canMove[0] + canMove[1];
                var className = 'mouse-rect-' + axisName;
                select('rect.' + className).attr('class', className + ' ' + (cursorShape[cursorKey] || 'mouse-zoom'));
                return canMove[0] + canMove[1];
            }

            function drawBottomPanelCut() {
                var row;
                var yBottom = axes.y.indexScale(axes.y.scale.domain()[0]);
                var yTop = axes.y.indexScale(axes.y.scale.domain()[1]);
                var yv = Math.round(yBottom + (yTop - yBottom) / 2);
                if (SIREPO.PLOTTING_SUMMED_LINEOUTS) {
                    row = sumRegion(
                        true,
                        Math.floor(yBottom + 0.5),
                        Math.ceil(yTop - 0.5),
                        Math.floor(axes.x.indexScale(axes.x.scale.domain()[0])),
                        Math.ceil(axes.x.indexScale(axes.x.scale.domain()[1])));
                }
                else {
                    row = heatmap[axes.y.values.length - 1 - yv];
                }
                var points = d3.zip(axes.x.values, row);
                plotting.recalculateDomainFromPoints(axes.bottomY.scale, points, axes.x.scale.domain());
                drawLineout('x', yv, points, axes.x.cutLine);
                focusPointService.loadFocusPoint($scope.focusPointX, points, true, $scope);
            }

            function drawLineout(axis, key, points, cutLine) {
                if (! lineOuts[axis] || ! SIREPO.PLOTTING_SHOW_CONVERGENCE_LINEOUTS) {
                    lineOuts[axis] = {};
                }
                var axisClass = axis == 'x' ? '.bottom-panel' : '.right-panel';
                if (lineOuts[axis][key]) {
                    if (! appState.deepEquals(points, lineOuts[axis][key][0])) {
                        lineOuts[axis][key] = plotting.addConvergencePoints(select, axisClass, lineOuts[axis][key], points);
                    }
                }
                else {
                    lineOuts[axis] = {};
                    lineOuts[axis][key] = plotting.addConvergencePoints(select, axisClass, [], points);
                }
                plotting.refreshConvergencePoints(select, axisClass, cutLine);
            }

            function drawRightPanelCut() {
                var xLeft = axes.x.indexScale(axes.x.scale.domain()[0]);
                var xRight = axes.x.indexScale(axes.x.scale.domain()[1]);
                var xv = Math.round(xLeft + (xRight - xLeft) / 2);
                var points;

                if (SIREPO.PLOTTING_SUMMED_LINEOUTS) {
                    points = d3.zip(axes.y.values, sumRegion(
                        false,
                        Math.floor(axes.y.indexScale(axes.y.scale.domain()[0])),
                        Math.ceil(axes.y.indexScale(axes.y.scale.domain()[1])),
                        Math.floor(xLeft + 0.5),
                        Math.ceil(xRight - 0.5))).reverse();
                }
                else {
                    points = heatmap.map(function(v, i) {
                        return [axes.y.values[axes.y.values.length - 1 - i], v[xv]];
                    });
                }
                plotting.recalculateDomainFromPoints(axes.rightX.scale, points, axes.y.scale.domain(), true);
                drawLineout('y', xv, points, axes.y.cutLine);
                focusPointService.loadFocusPoint($scope.focusPointY, points, true, $scope);
            }

            function exceededMaxZoom(scale, axisName) {
                var domain = fullDomain[axisName == 'x' ? 0 : 1];
                var domainSize = domain[1] - domain[0];
                var d = scale.domain();
                var pixels = (axisName == 'x' ? axes.x.values : axes.y.values).length * (d[1] - d[0]) / domainSize;
                return pixels < MIN_PIXEL_RESOLUTION;
            }

            function refresh() {
                if (! fullDomain) {
                    return;
                }
                if (layoutService.plotAxis.allowUpdates && ! $scope.isPlaying) {
                    var width = parseInt(select().style('width')) - $scope.margin.left - $scope.margin.right - $scope.pad;
                    if (! heatmap || isNaN(width)){
                        return;
                    }
                    width = plotting.constrainFullscreenSize($scope, width, aspectRatio);
                    var panelSize = 2 * width / 3;
                    $scope.canvasSize.width = panelSize;
                    $scope.canvasSize.height = panelSize * aspectRatio;
                    $scope.bottomPanelHeight = 2 * panelSize / 5 + $scope.pad + $scope.margin.bottom;
                    $scope.rightPanelWidth = panelSize / 2 + $scope.pad + $scope.margin.right;
                    axes.x.scale.range([0, $scope.canvasSize.width]);
                    axes.y.scale.range([$scope.canvasSize.height, 0]);
                    axes.bottomY.scale.range([$scope.bottomPanelHeight - $scope.pad - $scope.margin.bottom - 1, 0]);
                    axes.rightX.scale.range([0, $scope.rightPanelWidth - $scope.pad - $scope.margin.right]);
                }
                if (prevDomain && (exceededMaxZoom(axes.x.scale, 'x') || exceededMaxZoom(axes.y.scale, 'y'))) {
                    restoreDomain(axes.x.scale, prevDomain[0]);
                    restoreDomain(axes.y.scale, prevDomain[1]);
                }
                if (clipDomain(axes.x.scale, 'x') + clipDomain(axes.y.scale, 'y')) {
                    select('rect.mouse-rect-xy').attr('class', 'mouse-rect-xy mouse-move');
                }
                else {
                    select('rect.mouse-rect-xy').attr('class', 'mouse-rect-xy mouse-zoom');
                }
                plotting.drawImage(axes.x.scale, axes.y.scale, $scope.canvasSize.width, $scope.canvasSize.height, axes.x.values, axes.y.values, canvas, cacheCanvas, true);
                drawBottomPanelCut();
                drawRightPanelCut();

                axes.x.updateLabelAndTicks({
                    height: $scope.bottomPanelHeight,
                    width: $scope.canvasSize.width,
                }, select, '.bottom-panel ');
                axes.y.updateLabelAndTicks({
                    width: $scope.rightPanelWidth,
                    height: $scope.canvasSize.height,
                }, select, '.right-panel ');
                axes.bottomY.updateLabelAndTicks({
                    height: $scope.bottomPanelHeight,
                    width: $scope.canvasSize.width,
                    isPlaying: $scope.isPlaying,
                }, select, '.bottom-panel ');
                axes.rightX.updateLabelAndTicks({
                    width: $scope.rightPanelWidth - $scope.margin.right,
                    height: $scope.canvasSize.height,
                }, select, '.right-panel ');

                if (layoutService.plotAxis.allowUpdates) {
                    axes.x.grid.ticks(axes.x.tickCount);
                    axes.y.grid.ticks(axes.y.tickCount);
                    axes.x.grid.tickSize(- $scope.canvasSize.height - $scope.bottomPanelHeight + $scope.margin.bottom); // tickLine == gridline
                    axes.y.grid.tickSize(- $scope.canvasSize.width - $scope.rightPanelWidth + $scope.margin.right); // tickLine == gridline
                }
                resetZoom();
                select('.mouse-rect-xy').call(xyZoom);
                select('.mouse-rect-x').call(axes.x.zoom);
                select('.mouse-rect-y').call(axes.y.zoom);
                select('.right-panel .x.axis').call(axes.rightX.svgAxis);
                select('.x.axis.grid').call(axes.x.grid);
                select('.y.axis.grid').call(axes.y.grid);
                focusPointService.refreshFocusPoint($scope.focusPointX, $scope);
                focusPointService.refreshFocusPoint($scope.focusPointY, $scope);
                prevDomain = [
                    axes.x.scale.domain(),
                    axes.y.scale.domain(),
                ];
                centerTitle();
                centerSubTitle();
            }

            function resetZoom() {
                xyZoom = axes.x.createZoom($scope).y(axes.y.scale);
                axes.x.zoom = axes.x.createZoom($scope);
                axes.y.zoom = axes.y.createZoom($scope);
            }

            function resizefocusPointText() {
                var maxSize = 14;
                var minSize = 9;
                var focusText = select('.focus-text');
                var fs = focusText.style('font-size');

                var currentFontSize = utilities.fontSizeFromString(fs);
                var newFontSize = currentFontSize;

                var textWidth = focusText.node().getComputedTextLength();
                var pct = ($scope.canvasSize.width - $scope.focusTextCloseSpace) / textWidth;

                newFontSize *= pct;
                newFontSize = Math.max(minSize, newFontSize);
                newFontSize = Math.min(maxSize, newFontSize);
                focusText.style('font-size', newFontSize + 'px');
            }

            function restoreDomain(scale, oldValue) {
                var d = scale.domain();
                d[0] = oldValue[0];
                d[1] = oldValue[1];
            }

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            function sumRegion(isWidth, bottom, top, left, right) {
                var points = [];
                var max = isWidth ? right : top;
                for (var i = 0; i <= max; i++) {
                    points[i] = 0;
                }
                for (i = bottom; i <= top; i++) {
                    for (var j = left; j <= right; j++) {
                        var index = isWidth ? j : i;
                        points[index] += heatmap[axes.y.values.length - 1 - i][j];
                    }
                }
                return points;
            }

            $scope.clearData = function() {
                $scope.dataCleared = true;
                fullDomain = null;
                lineOuts = {};
            };

            $scope.destroy = function() {
                xyZoom.on('zoom', null);
                axes.x.zoom.on('zoom', null);
                axes.y.zoom.on('zoom', null);
                document.removeEventListener(utilities.fullscreenListenerEvent(), refresh);
            };

            $scope.formatFocusPointData = function(fp) {
                return focusPointService.formatFocusPointData(
                    fp,
                    fp.config.xAxis.label,
                    select('.z-axis-label').text()
                );
            };

            $scope.hideFocusPointText = function() {
                select('.focus-text').text('');
                select('.focus-text-close').style('display', 'none');
                select('.sub-title').style('display', 'block');
            };

            $scope.hideFocusPoints = function() {
                focusPointService.hideFocusPoint($scope, true);
                $scope.focusPointX.unset();
                $scope.focusPointY.unset();
            };

            $scope.init = function() {
                document.addEventListener(utilities.fullscreenListenerEvent(), refresh);
                select('svg').attr('height', plotting.initialHeight($scope));
                axes.x.init();
                axes.y.init();
                axes.bottomY.init();
                axes.rightX.init();
                axes.x.indexScale = d3.scale.linear();
                axes.y.indexScale = d3.scale.linear();
                axes.x.grid = axes.x.createAxis();
                axes.y.grid = axes.y.createAxis('left');
                resetZoom();
                canvas = select('canvas').node();
                ctx = canvas.getContext('2d');
                cacheCanvas = document.createElement('canvas');
                axes.x.cutLine = d3.svg.line()
                    .x(function(d) {return axes.x.scale(d[0]);})
                    .y(function(d) {return axes.bottomY.scale(d[1]);});
                axes.y.cutLine = d3.svg.line()
                    .y(function(d) { return axes.y.scale(d[0]);})
                    .x(function(d) { return axes.rightX.scale(d[1]);});

                $scope.focusPointX = focusPointService.setupFocusPoint(axes.x, axes.bottomY, false, $scope.modelName + '-fp-X');
                $scope.focusPointY = focusPointService.setupFocusPoint(axes.y, axes.rightX, true, $scope.modelName + '-fp-Y');
                select('.focus-text-close')
                    .on('click', $scope.hideFocusPoints);
           };

            $scope.load = function(json) {
                prevDomain = null;
                $scope.dataCleared = false;
                aspectRatio = plotting.getAspectRatio($scope.modelName, json);
                heatmap = appState.clone(json.z_matrix).reverse();
                var newFullDomain = [
                    [json.x_range[0], json.x_range[1]],
                    [json.y_range[0], json.y_range[1]],
                ];
                if ((axes.y.values && axes.y.values.length != json.z_matrix.length)
                    || ! appState.deepEquals(fullDomain, newFullDomain)) {
                    fullDomain = newFullDomain;
                    lineOuts = {};
                    axes.x.values = plotting.linearlySpacedArray(fullDomain[0][0], fullDomain[0][1], json.x_range[2]);
                    axes.y.values = plotting.linearlySpacedArray(fullDomain[1][0], fullDomain[1][1], json.y_range[2]);
                    axes.x.scale.domain(fullDomain[0]);
                    axes.x.indexScale.domain(fullDomain[0]);
                    axes.y.scale.domain(fullDomain[1]);
                    axes.y.indexScale.domain(fullDomain[1]);
                    adjustZoomToCenter(axes.x.scale);
                    adjustZoomToCenter(axes.y.scale);
                }
                var xmax = axes.x.values.length - 1;
                var ymax = axes.y.values.length - 1;
                axes.x.indexScale.range([0, xmax]);
                axes.y.indexScale.range([0, ymax]);
                cacheCanvas.width = axes.x.values.length;
                cacheCanvas.height = axes.y.values.length;
                imageData = ctx.getImageData(0, 0, cacheCanvas.width, cacheCanvas.height);
                select('.main-title').text(json.title);
                select('.sub-title').text(json.subtitle);
                axes.x.parseLabelAndUnits(json.x_label);
                select('.x-axis-label').text(json.x_label);
                axes.y.parseLabelAndUnits(json.y_label);
                select('.y-axis-label').text(json.y_label);
                select('.z-axis-label').text(json.z_label);
                var zmin = plotting.min2d(heatmap);
                var zmax = plotting.max2d(heatmap);

                //TODO(pjm): for now, we always want the lower range to be 0
                if (zmin > 0) {
                    zmin = 0;
                }
                axes.bottomY.scale.domain([zmin, zmax]).nice();
                axes.rightX.scale.domain([zmax, zmin]).nice();
                plotting.initImage({ min: zmin, max: zmax }, heatmap, cacheCanvas, imageData, $scope.modelName);
                $scope.resize();
                $scope.resize();
            };

            $scope.modelChanged = function() {
                // clear lineOuts
                $scope.clearData();
            };

            $scope.resize = function() {
                if (select().empty()) {
                    return;
                }
                refresh();
            };

            $scope.showFocusPointText = function(focusPoint) {
                select('.focus-text-close').style('display', 'block');

                var focusText = select('.focus-text');
                var fmtTxt = focusPointService.formatFocusPointData(focusPoint);
                var xyfText = fmtTxt.xText + ', ' + fmtTxt.yText;
                if (fmtTxt.fwhmText) {
                    xyfText = xyfText + ', ' + fmtTxt.fwhmText;
                }
                if (focusPoint == $scope.focusPointX) {
                    xyfText = xyfText + ' ↓';
                }
                if (focusPoint == $scope.focusPointY) {
                    xyfText = xyfText + ' →';
                }
                select('.sub-title').style('display', 'none');
                focusText.text(xyfText);
                resizefocusPointText();
            };

            $scope.$on(SIREPO.PLOTTING_LINE_CSV_EVENT, function(evt, axisName) {
                var keys = Object.keys(lineOuts[axisName]);
                var points = lineOuts[axisName][keys[0]][0];
                var xHeading = select('.' + axisName + '-axis-label').text();
                plotting.exportCSV(
                    xHeading,
                    [xHeading + ' [' + $scope.xunits +']', select('.z-axis-label').text()],
                    points);
            });
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('heatmap', function(appState, layoutService, plotting, utilities) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/heatplot.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            // will be set to the correct size in resize()
            $scope.canvasSize = {
                width: 0,
                height: 0,
            };
            $scope.dataCleared = true;
            $scope.margin = {top: 50, left: 70, right: 100, bottom: 50};

            document.addEventListener(utilities.fullscreenListenerEvent(), refresh);

            var aspectRatio = 1.0;
            var canvas, ctx, amrLine, heatmap, mouseMovePoint, pointer, zoom;
            var cacheCanvas, imageData;
            var colorbar;
            var axes = {
                x: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh),
                y: layoutService.plotAxis($scope.margin, 'y', 'left', refresh),
            };

            function colorbarSize() {
                var tickFormat = colorbar.tickFormat();
                if (! tickFormat) {
                    return 0;
                }
                var maxLength = colorbar.scale().ticks().reduce(function(size, v) {
                    return Math.max(size, tickFormat(v).length);
                }, 0);
                var textSize = Math.max(25, maxLength * plotting.tickFontSize(select('.sr-plot .axis text')));
                var res = textSize + colorbar.thickness() + colorbar.margin().left;
                colorbar.margin().right = res;
                return res;
            }

            function getRange(values) {
                return [values[0], values[values.length - 1]];
            }

            var mouseMove = utilities.debounce(function() {
                /*jshint validthis: true*/
                if (! heatmap || heatmap[0].length <= 2) {
                    return;
                }
                var point = mouseMovePoint;
                var xRange = getRange(axes.x.values);
                var yRange = getRange(axes.y.values);
                var x0 = axes.x.scale.invert(point[0] - 1);
                var y0 = axes.y.scale.invert(point[1] - 1);
                var x = Math.round((heatmap[0].length - 1) * (x0 - xRange[0]) / (xRange[1] - xRange[0]));
                var y = Math.round((heatmap.length - 1) * (y0 - yRange[0]) / (yRange[1] - yRange[0]));
                try {
                    pointer.pointTo(heatmap[heatmap.length - 1 - y][x]);
                }
                catch (err) {
                    // ignore range errors due to mouse move after heatmap is reset
                }
            }, 100);

            function refresh() {
                if (layoutService.plotAxis.allowUpdates && ! $scope.isPlaying) {
                    var width = parseInt(select().style('width')) - $scope.margin.left - $scope.margin.right;
                    if (! heatmap || isNaN(width)) {
                        return;
                    }
                    width = plotting.constrainFullscreenSize($scope, width, aspectRatio);
                    $scope.canvasSize.width = width;
                    $scope.canvasSize.height = width * aspectRatio;
                    axes.x.scale.range([0, $scope.canvasSize.width]);
                    axes.y.scale.range([$scope.canvasSize.height, 0]);
                }
                if (plotting.trimDomain(axes.x.scale, getRange(axes.x.values))
                    + plotting.trimDomain(axes.y.scale, getRange(axes.y.values))) {
                    select('.mouse-rect').attr('class', 'mouse-rect mouse-zoom');
                }
                else {
                    select('.mouse-rect').attr('class', 'mouse-rect mouse-move');
                }
                plotting.drawImage(axes.x.scale, axes.y.scale, $scope.canvasSize.width, $scope.canvasSize.height, axes.x.values, axes.y.values, canvas, cacheCanvas, ! SIREPO.PLOTTING_HEATPLOT_FULL_PIXEL);
                select('.line-amr-grid').attr('d', amrLine);
                resetZoom();
                select('.mouse-rect').call(zoom);
                $scope.canvasSize.isPlaying = $scope.isPlaying;
                $.each(axes, function(dim, axis) {
                    axis.updateLabelAndTicks($scope.canvasSize, select);
                });
                if (showColorBar()) {
                    if (layoutService.plotAxis.allowUpdates) {
                        colorbar.barlength($scope.canvasSize.height).origin([$scope.canvasSize.width + $scope.margin.right, 0]);
                        // must remove the element to reset the margins
                        select('svg.colorbar').remove();
                        pointer = select('.colorbar').call(colorbar);
                        $scope.margin.right = colorbarSize();
                    }
                }
                else {
                    select('svg.colorbar').remove();
                    $scope.margin.right = 20;
                }
            }

            function resetZoom() {
                zoom = axes.x.createZoom($scope).y(axes.y.scale);
            }

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            function setColorScale() {
                var plotMin = plotting.min2d(heatmap);
                var plotMax = plotting.max2d(heatmap);
                if (plotMin == plotMax) {
                    plotMax = (plotMin || 1e-6) * 10;
                }
                var colorScale = plotting.initImage(
                    {
                        min: plotMin,
                        max: plotMax,
                    },
                    heatmap, cacheCanvas, imageData, $scope.modelName);
                colorbar.scale(colorScale);
            }

            function showColorBar() {
                if (appState.isLoaded()) {
                    return appState.models[$scope.modelName].colorMap != 'contrast';
                }
                return false;
            }

            $scope.clearData = function() {
                $scope.dataCleared = true;
                $scope.prevFrameIndex = -1;
            };

            $scope.destroy = function() {
                $('.mouse-rect').off();
                zoom.on('zoom', null);
                document.removeEventListener(utilities.fullscreenListenerEvent(), refresh);
            };

            $scope.init = function() {
                select('svg').attr('height', plotting.initialHeight($scope));
                $.each(axes, function(dim, axis) {
                    axis.init();
                });
                resetZoom();
                canvas = select('canvas').node();
                select('.mouse-rect').on('mousemove', function() {
                    // mouseMove is debounced, so save the point before calling
                    mouseMovePoint = d3.mouse(this);
                    mouseMove();
                });
                ctx = canvas.getContext('2d');
                cacheCanvas = document.createElement('canvas');
                colorbar = Colorbar()
                    .margin({top: 10, right: 100, bottom: 20, left: 10})
                    .thickness(30)
                    .orient('vertical');
                amrLine = d3.svg.line()
                    .defined(function(d) { return d !== null; })
                    .x(function(d) {
                        return axes.x.scale(d[0]);
                    })
                    .y(function(d) {
                        return axes.y.scale(d[1]);
                    });
            };

            $scope.load = function(json) {
                $scope.dataCleared = false;
                aspectRatio = plotting.getAspectRatio($scope.modelName, json);
                heatmap = appState.clone(json.z_matrix).reverse();
                select('.main-title').text(json.title);
                select('.sub-title').text(json.subtitle);
                $.each(axes, function(dim, axis) {
                    axis.values = plotting.linearlySpacedArray(json[dim + '_range'][0], json[dim + '_range'][1], json[dim + '_range'][2]);
                    axis.parseLabelAndUnits(json[dim + '_label']);
                    select('.' + dim + '-axis-label').text(json[dim + '_label']);
                    axis.scale.domain(getRange(axis.values));
                });
                cacheCanvas.width = axes.x.values.length;
                cacheCanvas.height = axes.y.values.length;
                imageData = ctx.getImageData(0, 0, cacheCanvas.width, cacheCanvas.height);
                select('.z-axis-label').text(json.z_label);
                select('.frequency-label').text(json.frequency_title);
                setColorScale();

                var amrLines = [];
                if (json.amr_grid) {
                    for (var i = 0; i < json.amr_grid.length; i++) {
                        var p = json.amr_grid[i];
                        amrLines.push([p[0][0], p[1][0]]);
                        amrLines.push([p[0][1], p[1][0]]);
                        amrLines.push([p[0][1], p[1][1]]);
                        amrLines.push(null);
                    }
                }
                select('.line-amr-grid').datum(amrLines);
                $scope.resize();
                $scope.resize();
            };

            $scope.resize = function() {
                if (select().empty()) {
                    return;
                }
                refresh();
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('parameterPlot', function(appState, focusPointService, layoutService, mathRendering, plotting, plot2dService) {
    return {
        restrict: 'A',
        scope: {
            reportId: '<',
            modelName: '@',
        },
        templateUrl: '/static/html/plot2d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope, $element) {
            var includeForDomain = [];
            var plotLabels = [];
            var childPlots = {};

            $scope.focusPoints = [];
            $scope.focusStrategy = 'closest';
            $scope.latexTitle = '';
            $scope.wantLegend = true;

            function build2dPointsForPlot(plotIndex) {
                var pts = [];
                for (var ptIndex = 0; ptIndex < $scope.axes.x.points.length; ++ptIndex) {
                    pts.push([
                        $scope.axes.x.points[ptIndex],
                        $scope.axes.y.plots[plotIndex].points[ptIndex]
                    ]);
                }
                return pts;
            }

            function createLegend(plots) {
                plotLabels.length = 0;
                var legend = $scope.select('.sr-plot-legend');
                legend.selectAll('.sr-plot-legend-item').remove();
                if (plots.length == 1) {
                    return;
                }
                var itemWidth;
                plots.forEach(function(plot, i) {
                    if(plot._parent) {
                        return;
                    }
                    plotLabels.push(plot.label);
                    var item = legend.append('g').attr('class', 'sr-plot-legend-item');
                    item.append('text')
                        .attr('class', 'focus-text-popup glyphicon plot-visibility')
                        .attr('x', 8)
                        .attr('y', 17 + i * 20)
                        .text(vIconText(true))
                        .on('click', function() {
                            togglePlot(i);
                        });
                    itemWidth = item.node().getBBox().width;
                    item.append('circle')
                        .attr('r', 5)
                        .attr('cx', 24 + itemWidth)
                        .attr('cy', 10 + i * 20)
                        .style('stroke', plot.color)
                        .style('fill', plot.color);
                    itemWidth = item.node().getBBox().width;
                    item.append('text')
                        .attr('class', 'focus-text')
                        .attr('x', 12 + itemWidth)
                        .attr('y', 16 + i * 20)
                        .text(plot.label);
                });
            }

            function includeDomain(pIndex, doInclude) {
                var domainIndex = includeForDomain.indexOf(pIndex);
                if (! doInclude) {
                    if (domainIndex >= 0) {
                        includeForDomain.splice(domainIndex, 1);
                    }
                }
                else {
                    if (domainIndex < 0) {
                        includeForDomain.push(pIndex);
                    }
                }
            }

            function isPlotVisible(pIndex) {
                return parseFloat(plotPath(pIndex).style('opacity')) < 1;
            }

            function plotPath(pIndex) {
                return d3.select(selectAll('.plot-viewport .param-plot')[0][pIndex]);
            }

            function selectAll(selector) {
                var e = d3.select($scope.element);
                return selector ? e.selectAll(selector) : e;
            }

            function setPlotVisible(pIndex, isVisible) {
                // disable last toggle - meaningless to show no plots
                if (includeForDomain.length == 1 && includeForDomain[0] == pIndex) {
                    return;
                }
                plotPath(pIndex).style('opacity', isVisible ? 1.0 : 0.0);
                vIcon(pIndex).text(vIconText(isVisible));

                if ($scope.axes.y.plots && $scope.axes.y.plots[pIndex]) {
                    includeDomain(pIndex, isVisible);
                    if (includeForDomain.length == 1) {
                        vIcon(includeForDomain[0]).style('fill', '#aaaaaa');
                    }
                    else {
                        selectAll('.sr-plot-legend .plot-visibility').style('fill', null);
                    }
                    $scope.recalculateYDomain();
                    $scope.resize();
                }
                $scope.broadcastEvent({
                    name: 'setInfoVisible',
                    isVisible: isVisible,
                    focusPoint: $scope.focusPoints[pIndex],
                    index: pIndex,
                });
            }

            function togglePlot(pIndex) {
                setPlotVisible(pIndex, isPlotVisible(pIndex));
                (childPlots[pIndex] || []).forEach(function (i) {
                    setPlotVisible(i, isPlotVisible(i));
                });
            }

            function vIcon(pIndex) {
                return d3.select(selectAll('.sr-plot-legend .plot-visibility')[0][pIndex]);
            }

            function vIconText(isVisible) {
                // e067 == checked box, e157 == empty box
                return isVisible ? '\ue067' : '\ue157';
            }

            // get the broadest domain from the visible plots
            function visibleDomain() {
                var ydomMin = Math.min.apply(null,
                    includeForDomain.map(function(index) {
                        return Math.min.apply(null, $scope.axes.y.plots[index].points);
                    })
                );
                var ydomMax = Math.max.apply(null,
                    includeForDomain.map(function(index) {
                        return Math.max.apply(null, $scope.axes.y.plots[index].points);
                    })
                );
                return plotting.ensureDomain([ydomMin, ydomMax]);
            }

            $scope.formatFocusPointData = function(fp) {
                var yLabel = plotLabels[$scope.focusPoints.indexOf(fp)];
                var lu = {};
                if (yLabel) {
                    lu = layoutService.parseLabelAndUnits(yLabel);
                    yLabel = lu.label;
                }
                fp.config.yLabel = yLabel;
                return focusPointService.formatFocusPointData(fp, fp.config.xAxis.label, yLabel, null, lu.units);
            };

            // interface used by parameterWithLattice
            $scope.getXAxis = function() {
                return $scope.axes.x;
            };

            $scope.init = function() {
                plot2dService.init2dPlot($scope, {
                    margin: {top: 50, right: 23, bottom: 50, left: 75},
                });
                // override graphLine to work with multiple point sets
                $scope.graphLine = d3.svg.line()
                    .x(function(d, i) {
                        return $scope.axes.x.scale($scope.axes.x.points[i]);
                    })
                    .y(function(d) {
                        return $scope.axes.y.scale(d);
                    });
            };

            $scope.load = function(json) {
                includeForDomain.length = 0;
                // data may contain 2 plots (y1, y2) or multiple plots (plots)
                var plots = json.plots || [
                    {
                        points: json.points[0],
                        label: json.y1_title,
                        color: '#1f77b4',
                    },
                    {
                        points: json.points[1],
                        label: json.y2_title,
                        color: '#ff7f0e',
                    },
                ];
                if (plots.length == 1 && ! json.y_label) {
                    json.y_label = plots[0].label;
                }
                $scope.axes.x.points = json.x_points
                    || plotting.linearlySpacedArray(json.x_range[0], json.x_range[1], json.x_range[2] || json.points.length);
                var xdom = [json.x_range[0], json.x_range[1]];
                //TODO(pjm): onRefresh indicates a beamline overlay, needs improvement
                if ($scope.onRefresh) {
                    // beamline overlay always starts at position 0
                    xdom[0] = 0;
                }
                $scope.axes.x.domain = xdom;
                $scope.axes.x.scale.domain(xdom);
                plotting.ensureDomain(json.y_range);
                $scope.axes.y.domain = [json.y_range[0], json.y_range[1]];
                $scope.axes.y.scale.domain($scope.axes.y.domain).nice();

                var viewport = $scope.select('.plot-viewport');
                viewport.selectAll('.line').remove();
                viewport.selectAll('.scatter-point').remove();
                createLegend(plots);
                plots.forEach(function(plot, i) {
                    var strokeWidth = 2.0;
                    if(plot.style === 'scatter') {
                        var pg = viewport.append('g')
                            .attr('class', 'param-plot');
                            pg.selectAll('.scatter-point')
                                .data(plot.points)
                                .enter()
                                    .append('circle')
                                    .attr('cx', $scope.graphLine.x())
                                    .attr('cy', $scope.graphLine.y())
                                    .attr('r', 2)
                                    .attr('class', 'scatter-point line-color')
                    }
                    else {
                        viewport.append('path')
                            .attr('class', 'param-plot line line-color')
                            .style('stroke', plot.color)
                            .style('stroke-width', strokeWidth)
                            .datum(plot.points);
                    }
                    if(plot._parent) {
                        strokeWidth = 1.0;
                        var parent = plots.filter(function (p, j) {
                            return j !== i && p.label === plot._parent;
                        })[0];
                        if(parent) {
                            var pIndex = plots.indexOf(parent);
                            var cp = childPlots[pIndex] || [];
                            cp.push(i);
                            childPlots[pIndex] = cp;
                        }
                    }
                    // must create extra focus points here since we don't know how many to make
                    var name = $scope.modelName + '-fp-' + i;
                    if (! $scope.focusPoints[i]) {
                        $scope.focusPoints[i] = focusPointService.setupFocusPoint($scope.axes.x, $scope.axes.y, false, name);
                    }

                    // make sure everything is visible when reloading
                    includeDomain(i, true);
                    setPlotVisible(i, true);
                });
                $scope.axes.y.plots = plots;
                for (var fpIndex = 0; fpIndex < $scope.focusPoints.length; ++fpIndex) {
                    if (fpIndex < plots.length) {
                        $scope.focusPoints[fpIndex].config.color = plots[fpIndex].color;
                        focusPointService.loadFocusPoint($scope.focusPoints[fpIndex], build2dPointsForPlot(fpIndex), false, $scope);
                    }
                    else {
                        focusPointService.loadFocusPoint($scope.focusPoints[fpIndex], [], false, $scope);
                    }
                }
                
                $($element).find('.latex-title').eq(0).html(mathRendering.mathAsHTML(json.latex_label, {displayMode: true}));

                //TODO(pjm): onRefresh indicates an embedded header, needs improvement
                $scope.margin.top = json.title
                    ? 50
                    : $scope.onRefresh
                        ? 65
                        : 20;
                $scope.margin.bottom = 50 + 20 * plots.length;
                $scope.updatePlot(json);
            };

            $scope.recalculateYDomain = function() {
                var ydom;
                var xdom = $scope.axes.x.scale.domain();
                var xPoints = $scope.axes.x.points;
                var plots = $scope.axes.y.plots;
                for (var i = 0; i < xPoints.length; i++) {
                    var x = xPoints[i];
                    if (x > xdom[1] || x < xdom[0]) {
                        continue;
                    }
                    for (var d in includeForDomain) {
                        var j = includeForDomain[d];
                        var y = plots[j].points[i];
                        if (ydom) {
                            if (y < ydom[0]) {
                                ydom[0] = y;
                            }
                            else if (y > ydom[1]) {
                                ydom[1] = y;
                            }
                        }
                        else {
                            ydom = [y, y];
                        }
                    }
                }
                if (ydom && ydom[0] != ydom[1]) {
                    if (ydom[0] > 0 && $scope.axes.y.domain[0] == 0) {
                        ydom[0] = 0;
                    }
                    $scope.axes.y.scale.domain(ydom).nice();
                }
            };

            $scope.refresh = function() {
                $scope.select('.plot-viewport').selectAll('.line').attr('d', $scope.graphLine);
                $scope.select('.plot-viewport').selectAll('.scatter-point').attr('d', $scope.graphLine)
                    .attr('cx', $scope.graphLine.x())
                    .attr('cy', $scope.graphLine.y());
                $scope.focusPoints.forEach(function(fp) {
                    focusPointService.refreshFocusPoint(fp, $scope);
                });
                if ($scope.onRefresh) {
                    $scope.onRefresh();
                }
            };

            $scope.setYDomain = function() {
                var model = appState.models[$scope.modelName];
                if (model && (model.plotRangeType == 'fixed' || model.plotRangeType == 'fit')) {
                    $scope.axes.y.scale.domain($scope.axes.y.domain).nice();
                }
                else {
                    $scope.axes.y.scale.domain(visibleDomain()).nice();
                }
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('particle', function(plotting, plot2dService) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/plot2d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            var allPoints;

            $scope.init = function() {
                plot2dService.init2dPlot($scope, {
                    margin: {top: 50, right: 23, bottom: 50, left: 75},
                });
            };

            $scope.load = function(json) {
                allPoints = [];
                var xdom = [json.x_range[0], json.x_range[1]];
                $scope.axes.x.domain = xdom;
                $scope.axes.x.scale.domain(xdom);
                $scope.axes.y.domain = [json.y_range[0], json.y_range[1]];
                $scope.axes.y.scale.domain($scope.axes.y.domain).nice();
                var viewport = $scope.select('.plot-viewport');
                viewport.selectAll('.line').remove();
                var isFixedX = ! Array.isArray(json.x_points[0]);
                var i;
                var lineClass = json.points.length > 20 ? 'line line-7' : 'line line-0';
                var points;
                for (i = 0; i < json.points.length; i++) {
                    points = d3.zip(
                        isFixedX ? json.x_points : json.x_points[i],
                        json.points[i]);
                    viewport.append('path').attr('class', lineClass).datum(points);
                    allPoints.push(points);
                }
                if (json.lost_x && json.lost_x.length) {
                    for (i = 0; i < json.lost_x.length; i++) {
                        points = d3.zip(json.lost_x[i], json.lost_y[i]);
                        viewport.append('path').attr('class', 'line line-reflected').datum(points);
                        allPoints.push(points);
                    }
                    // absorbed/reflected legend
                    $scope.select('svg')
                        .append('circle').attr('class', 'line-absorbed').attr('r', 5).attr('cx', 8).attr('cy', 10);
                    $scope.select('svg')
                        .append('text').attr('class', 'focus-text').attr('x', 16).attr('y', 16)
                        .text('Absorbed');
                    $scope.select('svg')
                        .append('circle').attr('class', 'line-reflected').attr('r', 5).attr('cx', 8).attr('cy', 30);
                    $scope.select('svg')
                        .append('text').attr('class', 'focus-text').attr('x', 16).attr('y', 36)
                        .text('Reflected');
                }
                $scope.updatePlot(json);
            };

            $scope.recalculateYDomain = function() {
                var ydom;
                var xdom = $scope.axes.x.scale.domain();
                allPoints.forEach(function(points) {
                    points.forEach(function(p) {
                        var x = p[0];
                        var y = p[1];
                        if (x >= xdom[0] && x <= xdom[1]) {
                            if (ydom) {
                                if (y < ydom[0]) {
                                    ydom[0] = y;
                                }
                                else if (y > ydom[1]) {
                                    ydom[1] = y;
                                }
                            }
                            else {
                                ydom = [y, y];
                            }
                        }
                    });
                });
                if (ydom && ydom[0] != ydom[1]) {
                    if (ydom[0] > 0 && $scope.axes.y.domain[0] == 0) {
                        ydom[0] = 0;
                    }
                    $scope.axes.y.scale.domain(ydom).nice();
                }
            };

            $scope.refresh = function() {
                $scope.select('.plot-viewport').selectAll('.line').attr('d', $scope.graphLine);
            };
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

// NOTE: the vtk and warp coordinate systems are related the following way:
//    vtk X (left to right) = warp Z
//    vtk Y (bottom to top) = warp X
//    vtk Z (out to in) = warp Y
//TODO(mvk): This directive should move to sirepo-plotting-vtk
SIREPO.app.directive('particle3d', function(appState, panelState, requestSender, frameCache, plotting, vtkPlotting, layoutService, utilities, geometry, plotToPNG, $timeout) {

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            reportId: '<',
        },
        templateUrl: '/static/html/particle3d.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope, $element) {

            var d3self;
            var xzAspectRatio = 4.0 / 7.0;
            $scope.margin = {top: 50, right: 23, bottom: 50, left: 75};
            $scope.width = $scope.height = 0;
            $scope.axesMargins = {
                x: { width: 16.0, height: 0.0 },
                y: { width: 0.0, height: 16.0 }
            };

            // little test boxes are useful for translating vtk space to screen space
            $scope.testBoxes = [];

            // The side of the plot facing the user
            $scope.side = 'y';
            $scope.xdir = 1;
            $scope.ydir = 1;
            $scope.zdir = 1;

            $scope.canInteract = true;
            $scope.interactionStyle = function() {
                if (! $scope.canInteract) {
                    return {
                        'cursor': 'not-allowed'
                    };
                }
                return {
                    'cursor': 'pointer'
                };
            };

            $scope.dataCleared = true;

            $scope.hasReflected = false;
            $scope.showAbsorbed = true;
            $scope.showReflected = true;
            $scope.showImpact = true;
            $scope.showConductors = true;

            // these are in screen/vtk coords, not lab coords
            //TODO(mvk): should refer only to lab coords outside of plotting-vtk (?)
            var axes = {
                x: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh, utilities),
                y: layoutService.plotAxis($scope.margin, 'y', 'left', refresh, utilities),
                z: layoutService.plotAxis($scope.margin, 'z', 'bottom', refresh, utilities)
            };
            var axisCfg = {};
            var boundAxes = {};

            // rendering
            var fsRenderer = null;
            var renderWindow = null;
            var mainView = null;
            var renderer = null;
            var cam = null;
            var camPos = [0, 0, 1];
            var camViewUp = [0, 1, 0];
            var camFP = [0, 0, 0];
            var camZoom = 1.3;
            var lastCamPos = camPos;
            var lastCamViewUp = camViewUp;
            var lastCamFP = camFP;
            var lastCamZoom = camZoom;
            var interactor;

            // planes
            var gridPlaneBundles = [];

            var startPlaneBundle = null;
            var endPlaneBundle = null;

            // conductors (boxes)
            var conductorBundles = [];
            var conductorActors = [];

            // lines
            var absorbedLineBundle;
            var reflectedLineBundle;

            // spheres
            var impactSphereActors = [];

            // outline
            var outlineSource = null;
            var outlineBundle = null;
            var vpOutline = null;

            // orientation cube/axis
            var orientationMarker = null;

            // geometry
            var coordMapper = vtkPlotting.coordMapper();

            // data
            var numPoints = 0;
            var pointData = {};
            var fieldData = {};
            var xmin = 0.0;  var xmax = 1.0;
            var ymin = 0.0;  var ymax = 1.0;
            var zmin = 0.0;  var zmax = 1.0;

            var heatmap = [];
            var fieldXFactor = 1.0;
            var fieldZFactor = 1.0;
            var fieldYFactor = 1.0;
            var fieldColorScale = null;
            var indexMaps = [];

            var minZSpacing = Number.MAX_VALUE;

            var impactSphereSize = 0.0125 * xzAspectRatio;
            var zoomUnits = 0;
            var didPan = false;
            var sceneRect;
            var sceneArea;
            var screenRect;
            var malSized = false;
            var offscreen = false;
            var picker = vtk.Rendering.Core.vtkPicker.newInstance();

            // colors - vtk uses a range of 0-1 for RGB components
            var zeroVoltsColor = vtk.Common.Core.vtkMath.hex2float(SIREPO.APP_SCHEMA.constants.zeroVoltsColor);
            var voltsColor = vtk.Common.Core.vtkMath.hex2float(SIREPO.APP_SCHEMA.constants.nonZeroVoltsColor);
            var particleTrackColor = vtk.Common.Core.vtkMath.hex2float(SIREPO.APP_SCHEMA.constants.particleTrackColor);
            var reflectedParticleTrackColor = vtk.Common.Core.vtkMath.hex2float(SIREPO.APP_SCHEMA.constants.reflectedParticleTrackColor);

            // this canvas is the one created by vtk
            var canvas3d;

            // we keep this one updated with a copy of the vtk canvas
            var snapshotCanvas;
            var snapshotCtx;

            document.addEventListener(utilities.fullscreenListenerEvent(), refresh);

            $scope.requestData = function() {
                if (! $scope.hasFrames()) {
                    return;
                }
                frameCache.getFrame($scope.modelName, 0, false, function(index, data) {
                    if ($scope.element) {
                        if (data.error) {
                            panelState.setError($scope.modelName, data.error);
                            return;
                        }
                        panelState.setError($scope.modelName, null);
                        pointData = data;
                        frameCache.getFrame('fieldAnimation', 0, false, function(index, data) {
                            if ($scope.element) {
                                if (data.error) {
                                    panelState.setError($scope.modelName, data.error);
                                    return;
                                }
                                panelState.setError($scope.modelName, null);
                                fieldData = data;
                                $scope.load();
                            }
                        });
                    }
                });
            };

            $scope.init = function() {

                d3self = d3.selectAll($element);

                var rw = angular.element($($element).find('.sr-plot-particle-3d .vtk-canvas-holder'))[0];
                fsRenderer = vtk.Rendering.Misc.vtkFullScreenRenderWindow.newInstance({
                    background: [1, 1, 1, 1],
                    container: rw,
                    listenWindowResize: false,
                });
                renderer = fsRenderer.getRenderer();
                renderer.getLights()[0].setLightTypeToSceneLight();
                renderWindow = fsRenderer.getRenderWindow();
                interactor = renderWindow.getInteractor();
                mainView = renderWindow.getViews()[0];

                cam = renderer.get().activeCamera;

                rw.addEventListener('dblclick', resetAndDigest);

                var worldCoord = vtk.Rendering.Core.vtkCoordinate.newInstance({
                    renderer: renderer
                });
                worldCoord.setCoordinateSystemToWorld();

                var isDragging = false;
                var isPointerUp = true;
                rw.onpointerdown = function(evt) {
                    isDragging = false;
                    isPointerUp = false;
                };
                rw.onpointermove = function(evt) {
                    if (isPointerUp) {
                        return;
                    }
                    isDragging = true;
                    didPan = didPan || evt.shiftKey;
                    $scope.side = null;
                    utilities.debounce(refresh, 100)();
                };
                rw.onpointerup = function(evt) {
                    if (! isDragging) {
                        // use picker to display info on objects
                    }
                    isDragging = false;
                    isPointerUp = true;
                    refresh(true);
                };
                rw.onwheel = function(evt) {
                    var camPos = cam.getPosition();

                    // If zoom needs to be halted or limited, it can be done here.  For now track the "zoom units"
                    // for managing refreshing and resetting
                    if (! malSized) {
                        zoomUnits += evt.deltaY;
                    }
                    utilities.debounce(
                        function() {
                            refresh(true);
                        },
                        100)();
                };

                //warpVTKService.initScene(coordMapper, renderer);

                // the emitter plane
                startPlaneBundle = coordMapper.buildPlane();
                startPlaneBundle.actor.getProperty().setColor(zeroVoltsColor[0], zeroVoltsColor[1], zeroVoltsColor[2]);
                //startPlaneBundle.actor.getProperty().setOpacity(0.5);
                startPlaneBundle.actor.getProperty().setLighting(false);
                renderer.addActor(startPlaneBundle.actor);

                // the collector plane
                endPlaneBundle = coordMapper.buildPlane();
                endPlaneBundle.actor.getProperty().setColor(voltsColor[0], voltsColor[1], voltsColor[2]);
                //endPlaneBundle.actor.getProperty().setOpacity(0.5);
                endPlaneBundle.actor.getProperty().setLighting(false);
                renderer.addActor(endPlaneBundle.actor);

                // a box around the elements, for visual clarity
                outlineBundle = coordMapper.buildBox();
                outlineSource =  outlineBundle.source;

                outlineBundle.actor.getProperty().setColor(1, 1, 1);
                outlineBundle.actor.getProperty().setEdgeVisibility(true);
                outlineBundle.actor.getProperty().setEdgeColor(0, 0, 0);
                outlineBundle.actor.getProperty().setFrontfaceCulling(true);
                outlineBundle.actor.getProperty().setLighting(false);
                renderer.addActor(outlineBundle.actor);

                vpOutline = vtkPlotting.vpBox(outlineBundle.source, renderer);

                // a little widget that mirrors the orientation (not the scale) of the scence
                var axesActor = vtk.Rendering.Core.vtkAxesActor.newInstance();
                orientationMarker = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
                    actor: axesActor,
                    interactor: renderWindow.getInteractor()
                });
                orientationMarker.setEnabled(true);
                orientationMarker.setViewportCorner(
                    vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.TOP_RIGHT
                );
                orientationMarker.setViewportSize(0.08);
                orientationMarker.setMinPixelSize(100);
                orientationMarker.setMaxPixelSize(300);

                // 6 grid planes indexed by dimension then side
                for (var d = 0; d < 3; ++d) {
                    var dpb = [];
                    for (var s = 0; s < 1; ++s) {
                        var pb = coordMapper.buildPlane();
                        pb.actor.getProperty().setColor(0, 0, 0);
                        pb.actor.getProperty().setLighting(false);
                        pb.actor.getProperty().setRepresentationToWireframe();
                        renderer.addActor(pb.actor);
                        dpb.push(pb);
                    }
                    gridPlaneBundles.push(dpb);
                }

                absorbedLineBundle = coordMapper.buildActorBundle();
                reflectedLineBundle = coordMapper.buildActorBundle();

                canvas3d = $($element).find('canvas')[0];

                // this canvas is used to store snapshots of the 3d canvas
                snapshotCanvas = document.createElement('canvas');
                snapshotCtx = snapshotCanvas.getContext('2d');
                plotToPNG.addCanvas(snapshotCanvas, $scope.reportId);
            };

            $scope.load = function() {
                $scope.dataCleared = false;

                vtkPlotting.removeActors(renderer, impactSphereActors);
                vtkPlotting.removeActors(renderer, conductorActors);

                impactSphereActors = [];
                conductorActors = [];
                conductorBundles = [];

                if (!pointData) {
                    return;
                }

                var xpoints = pointData.points;
                xmin = pointData.y_range[0];
                xmax = pointData.y_range[1];

                var zpoints = pointData.x_points;
                zmin = pointData.x_range[0];
                zmax = pointData.x_range[1];

                var ypoints = pointData.z_points;
                ymin = pointData.z_range[0];
                ymax = pointData.z_range[1];

                var lcoords = [];
                var lostCoords = [];
                zpoints.forEach(function(z, i) {
                    lcoords.push(geometry.transpose([xpoints[i], ypoints[i], zpoints[i]]));
                });
                pointData.lost_z.forEach(function(z, i) {
                    lostCoords.push(geometry.transpose([pointData.lost_y[i], pointData.lost_z[i], pointData.lost_x[i]]));
                });

                axisCfg = {
                    x: {
                        dimLabel: 'z',
                        label: pointData.x_label,
                        min: zmin,
                        max: zmax,
                        numPoints: zpoints.length,
                        screenDim: 'x',
                    },
                    y: {
                        dimLabel: 'x',
                        label: pointData.y_label,
                        min: xmin,
                        max: xmax,
                        numPoints: xpoints.length,
                        screenDim: 'y',
                    },
                    z: {
                        dimLabel: 'y',
                        label: pointData.z_label,
                        min: ymin,
                        max: ymax,
                        numPoints: ypoints.length,
                        screenDim: 'x',
                    },
                };

                var grid = appState.models.simulationGrid;
                var yzAspectRatio =  grid.channel_height / grid.channel_width;

                // vtk makes things fit so it does not particularly care about the
                // absolute sizes of things - except that really small values (e.g. 10^-7) don't scale
                // up properly.  We use these scaling factors to overcome that problem

                // This defines how axes are mapped...
                var t1 = geometry.transform(SIREPO.PLOT_3D_CONFIG.coordMatrix);

                // ...this scales the new axes
                var t2 = geometry.transform(
                     [
                        [1.0 / Math.abs(zmax - zmin), 0, 0],
                        [0, xzAspectRatio / Math.abs(xmax - xmin), 0],
                        [0, 0, yzAspectRatio * xzAspectRatio / Math.abs(ymax - ymin)]
                    ]
                );
                coordMapper = vtkPlotting.coordMapper(t2.compose(t1));

                coordMapper.setPlane(startPlaneBundle,
                    [xmin, ymin, zmin],
                    [xmin, ymax, zmin],
                    [xmax, ymin, zmin]
                );
                coordMapper.setPlane(endPlaneBundle,
                    [xmin, ymin, zmax],
                    [xmin, ymax, zmax],
                    [xmax, ymin, zmax]
                );

                var padding = 0.01;
                var spsOrigin = startPlaneBundle.source.getOrigin();
                var epsOrigin = endPlaneBundle.source.getOrigin();
                var epsP1 = endPlaneBundle.source.getPoint1();
                var epsP2 = endPlaneBundle.source.getPoint2();

                var osXLen = Math.abs(epsOrigin[0] - spsOrigin[0]) + padding;
                var osYLen = Math.abs(epsP2[1] - epsP1[1]) + padding;
                var osZLen = Math.abs(epsP2[2] - epsP1[2]) + padding;
                var osCtr = [];
                epsOrigin.forEach(function(o, i) {
                    osCtr.push((o - spsOrigin[i]) / 2.0);
                });

                outlineBundle.setLength([
                    Math.abs(epsOrigin[0] - spsOrigin[0]) + padding,
                    Math.abs(epsP2[1] - epsP1[1]) + padding,
                    Math.abs(epsP2[2] - epsP1[2]) + padding
                ]);
                outlineBundle.setCenter(osCtr);

                for (var d = 0; d < 3; ++d) {
                    for (var s = 0; s < 1; ++s) {
                        var pb = gridPlaneBundles[d][s];
                        var gpOrigin = s == 0 ?
                            [osCtr[0] - osXLen/2.0, osCtr[1] - osYLen/2.0, osCtr[2] - osZLen/2.0] :
                            [osCtr[0] + osXLen/2.0, osCtr[1] + osYLen/2.0, osCtr[2] + osZLen/2.0];
                        var gpP1 = [0,0,1];
                        var gpP2 = [0,1,0];
                        switch (2*d + s) {
                            // bottom
                            case 0:
                                gpP1 = [osCtr[0] + osXLen/2.0, osCtr[1] - osYLen/2.0, osCtr[2] - osZLen/2.0];
                                gpP2 = [osCtr[0] - osXLen/2.0, osCtr[1] - osYLen/2.0, osCtr[2] + osZLen/2.0];
                                break;
                            // top
                            case 1:
                                gpP1 = [osCtr[0] - osXLen/2.0, osCtr[1] + osYLen/2.0, osCtr[2] + osZLen/2.0];
                                gpP2 = [osCtr[0] + osXLen/2.0, osCtr[1] + osYLen/2.0, osCtr[2] - osZLen/2.0];
                                break;
                            // left
                            case 2:
                                gpP1 = [osCtr[0] - osXLen/2.0, osCtr[1] - osYLen/2.0, osCtr[2] + osZLen/2.0];
                                gpP2 = [osCtr[0] - osXLen/2.0, osCtr[1] + osYLen/2.0, osCtr[2] - osZLen/2.0];
                                break;
                            // right
                            case 3:
                                gpP1 = [osCtr[0] + osXLen/2.0, osCtr[1] + osYLen/2.0, osCtr[2] - osZLen/2.0];
                                gpP2 = [osCtr[0] + osXLen/2.0, osCtr[1] - osYLen/2.0, osCtr[2] + osZLen/2.0];
                                break;
                            // back
                            case 4:
                                gpP1 = [osCtr[0] + osXLen/2.0, osCtr[1] - osYLen/2.0, osCtr[2] - osZLen/2.0];
                                gpP2 = [osCtr[0] - osXLen/2.0, osCtr[1] + osYLen/2.0, osCtr[2] - osZLen/2.0];
                                break;
                            // front
                            case 5:
                                gpP1 = [osCtr[0] - osXLen/2.0, osCtr[1] + osYLen/2.0, osCtr[2] + osZLen/2.0];
                                gpP2 = [osCtr[0] + osXLen/2.0, osCtr[1] - osYLen/2.0, osCtr[2] + osZLen/2.0];
                                break;
                            default:
                                break;
                        }
                        // all coords are within vtk, so use the default (identity) coordMapper
                        vtkPlotting.coordMapper().setPlane(pb, gpOrigin, gpP1, gpP2);
                    }
                }

                // evenly spaced points to be linearly interpolated between the data, for
                // purposes of coloring lines with the field colors
                var numInterPoints = 50;

                for (var dim in axes) {
                    var cfg = axisCfg[dim];
                    axes[dim].init();
                    axes[dim].svgAxis.tickSize(0);
                    axes[dim].values = plotting.linearlySpacedArray(cfg.min, cfg.max, cfg.numPoints);
                    axes[dim].scale.domain([cfg.min, cfg.max]);
                    axes[dim].parseLabelAndUnits(cfg.label);
                }

                minZSpacing = Math.abs((zmax - zmin)) / numInterPoints;
                var nearestIndex = 0;
                indexMaps = [];

                // linearly interpolate the data
                for (var i = 0; i < lcoords.length; ++i) {
                    var ptsArr = lcoords[i];

                    var newIndexMap = {0:0};
                    var lastNearestIndex = 0;
                    nearestIndex = 1;
                    var newZ = ptsArr[0][2];
                    var finalZ = ptsArr[ptsArr.length-1][2];
                    var j = 1;

                    // ASSUMES MONOTONICALLY INCREASING Z
                    while (newZ <= finalZ) {
                        newZ = ptsArr[0][2] + j * minZSpacing;
                        nearestIndex = 1;  // start at the beginning
                        lastNearestIndex = 1;
                        var checkZ = ptsArr[nearestIndex][2];
                        while (nearestIndex < ptsArr.length && checkZ < newZ) {
                            if (! newIndexMap[nearestIndex]) {
                                // ensures we don't skip any indices, mapping them to the nearest previously mapped value
                                newIndexMap[nearestIndex] = indexValPriorTo(newIndexMap, nearestIndex, 1) || 0;
                            }
                            ++nearestIndex;
                            checkZ = (ptsArr[nearestIndex] || [])[2];
                        }
                        if (nearestIndex != lastNearestIndex) {
                            lastNearestIndex = nearestIndex;
                        }

                        var lo = Math.max(0, nearestIndex - 1);
                        var hi = Math.min(ptsArr.length-1, nearestIndex);
                        var p = ptsArr[lo];
                        var nextP = ptsArr[hi];
                        var dzz = nextP[2] - p[2];
                        var newP = [0, 0, newZ];
                        for (var ci = 0; ci < 2; ++ci) {
                            newP[ci] = dzz ? p[ci] + (newP[2] - p[2]) * (nextP[ci] - p[ci]) / dzz : p[ci];
                        }
                        ptsArr.splice(lo + 1, 0, newP);

                        newIndexMap[hi] = j;
                        ++j;
                    }
                    newIndexMap[ptsArr.length-1] = indexValPriorTo(newIndexMap, nearestIndex, 1);
                    indexMaps.push(newIndexMap);
                }

                // distribute the heat map evenly over the interpolated points
                heatmap = appState.clone(fieldData.z_matrix).reverse();
                var hm_zlen = heatmap.length;
                var hm_xlen = heatmap[0].length;
                var hm_ylen = numInterPoints;
                fieldXFactor = hm_xlen / numInterPoints;
                fieldZFactor = hm_zlen / numInterPoints;
                fieldYFactor = hm_ylen / numInterPoints;

                var hm_zmin = Math.max(0, plotting.min2d(heatmap));
                var hm_zmax = plotting.max2d(heatmap);
                fieldColorScale = plotting.colorScaleForPlot({ min: hm_zmin, max: hm_zmax }, 'particle3d');

                setLinesFromPoints(absorbedLineBundle, lcoords, null, true);
                if (pointData.lost_x) {
                    $scope.hasReflected = pointData.lost_x.length > 0;
                    setLinesFromPoints(reflectedLineBundle, lostCoords, reflectedParticleTrackColor, false);
                }

                function scaleWithShave(a) {
                    var shave = 0.01;
                    return (1.0 - shave) * a / cFactor;
                }

                function scaleConductor(a) {
                    return a / cFactor;
                }

                // build conductors -- make them a tiny bit small so the edges do not bleed into each other
                for (var cIndex = 0; cIndex < appState.models.conductors.length; ++cIndex) {
                    var conductor = appState.models.conductors[cIndex];

                    // lengths and centers are in µm
                    var cFactor = 1000000.0;
                    var cModel = null;
                    var cColor = [0, 0, 0];
                    var cEdgeColor = [0, 0, 0];
                    for (var ctIndex = 0; ctIndex < appState.models.conductorTypes.length; ++ctIndex) {
                        if (appState.models.conductorTypes[ctIndex].id == conductor.conductorTypeId) {
                            cModel = appState.models.conductorTypes[ctIndex];
                            var vColor = vtk.Common.Core.vtkMath.hex2float(cModel.color || SIREPO.APP_SCHEMA.constants.nonZeroVoltsColor);
                            var zColor = vtk.Common.Core.vtkMath.hex2float(cModel.color || SIREPO.APP_SCHEMA.constants.zeroVoltsColor);
                            cColor = cModel.voltage == 0 ? zColor : vColor;
                            break;
                        }
                    }
                    if (cModel) {
                        var bl = [cModel.xLength, cModel.yLength, cModel.zLength].map(scaleWithShave);
                        var bc = [conductor.xCenter, conductor.yCenter, conductor.zCenter].map(scaleConductor);

                        var bb = coordMapper.buildBox(bl, bc);
                        conductorBundles.push(bb);
                        bb.actor.getProperty().setColor(cColor[0], cColor[1], cColor[2]);
                        bb.actor.getProperty().setEdgeVisibility(true);
                        bb.actor.getProperty().setEdgeColor(cEdgeColor[0], cEdgeColor[1], cEdgeColor[2]);
                        bb.actor.getProperty().setLighting(false);
                        bb.actor.getProperty().setOpacity(0.80);
                        conductorActors.push(bb.actor);
                    }
                }

                // do an initial render
                renderWindow.render();

                // wait to initialize after the render so the world to viewport transforms are ready
                vpOutline.initializeWorld();

                refresh(true);
            };

            function setLinesFromPoints(bundle, points, color, includeImpact) {
                if (! bundle) {
                    return;
                }

                var k = 0;
                var dataPoints = [];
                var dataLines = [];
                var dataColors = [];
                for (var i = 0; i < points.length; ++i) {
                    var l = points[i].length;
                    for (var j = 0; j < l; ++j) {
                        ++numPoints;
                        if (j < l - 1) {
                            k = j + 1;
                            pushLineData(points[i][j], points[i][k], color || colorAtIndex(indexMaps[i][j]));
                        }
                    }
                    if (l > j) {
                        k = j - 1;
                        ++numPoints;
                        pushLineData(points[i][k], points[i][l - 1], color || colorAtIndex(indexMaps[i][k]));
                    }
                    if (includeImpact) {
                        k = points[i].length - 1;
                        impactSphereActors.push(coordMapper.buildSphere(points[i][k], impactSphereSize, color || colorAtIndex(indexMaps[i][k])).actor);
                    }
                }
                var p32 = window.Float32Array.from(dataPoints);
                var l32 = window.Uint32Array.from(dataLines);
                var pd = vtk.Common.DataModel.vtkPolyData.newInstance();
                pd.getPoints().setData(p32, 3);
                pd.getLines().setData(l32);
                bundle.mapper.setInputData(pd);

                if (color) {
                    bundle.mapper.setScalarVisibility(false);
                    bundle.actor.getProperty().setColor(color[0], color[1], color[2]);
                }
                else {
                    bundle.mapper.setScalarVisibility(true);
                    var carr = vtk.Common.Core.vtkDataArray.newInstance({
                        numberOfComponents: 3,
                        values: dataColors,
                        dataType: vtk.Common.Core.vtkDataArray.VtkDataTypes.UNSIGNED_CHAR
                    });

                    // lines live in "cells"
                    pd.getCellData().setScalars(carr);
                }

                function pushLineData(p1, p2, c) {
                    // we always have two points per line
                    dataLines.push(2);
                    dataLines.push(dataPoints.length / 3, 1 + dataPoints.length / 3);
                    [p1, p2].forEach(function(p) {
                        coordMapper.xform.doTransform(p).forEach(function(a) {
                            dataPoints.push(a);
                        });
                    });

                    // scalar colors are unsigned chars, not floats like for every other part of vtk
                    c.forEach(function(comp) {
                        dataColors.push(Math.floor(255*comp));
                    });
                }
            }
            function indexValPriorTo(map, startIndex, spacing) {
                var k = startIndex - spacing;
                var prevVal = map[k];
                while(k >= 0 && (prevVal == null || prevVal === 'undefined')) {
                    k -= spacing;
                    prevVal = map[k];
                }
                return prevVal;
            }
            function colorAtIndex(index) {
                var fieldxIndex = Math.min(heatmap[0].length-1, Math.floor(fieldXFactor * index));
                var fieldzIndex = Math.min(heatmap.length-1, Math.floor(fieldZFactor * index));
                var fieldyIndex = Math.floor(fieldYFactor * index);
                return plotting.colorsFromHexString(fieldColorScale(heatmap[fieldzIndex][fieldxIndex]), 255.0);
            }

            $scope.vtkCanvasGeometry = function() {
                var vtkCanvasHolder = $($element).find('.vtk-canvas-holder')[0];
                return {
                    pos: $(vtkCanvasHolder).position(),
                    size: {
                        width: $(vtkCanvasHolder).width(),
                        height: $(vtkCanvasHolder).height()
                    }
                };
            };

            function refresh(doCacheCanvas) {

                var width = parseInt($($element).css('width')) - $scope.margin.left - $scope.margin.right;
                $scope.width = plotting.constrainFullscreenSize($scope, width, xzAspectRatio);
                $scope.height = xzAspectRatio * $scope.width;

                var vtkCanvasHolderSize = {
                    width: $('.vtk-canvas-holder').width(),
                    height: $('.vtk-canvas-holder').height()
                };

                screenRect = geometry.rect(
                    geometry.point(
                        $scope.axesMargins.x.width,
                        $scope.axesMargins.y.height
                    ),
                    geometry.point(
                        vtkCanvasHolderSize.width - $scope.axesMargins.x.width,
                        vtkCanvasHolderSize.height - $scope.axesMargins.y.height
                    )
                );

                var vtkCanvasSize = {
                    width: $scope.width + $scope.margin.left + $scope.margin.right,
                    height: $scope.height + $scope.margin.top + $scope.margin.bottom
                };

                select('.vtk-canvas-holder svg')
                    .attr('width', vtkCanvasSize.width)
                    .attr('height', vtkCanvasSize.height);

                // Note that vtk does not re-add actors to the renderer if they already exist
                vtkPlotting.addActor(renderer, absorbedLineBundle.actor);
                vtkPlotting.addActor(renderer, reflectedLineBundle.actor);
                vtkPlotting.addActors(renderer, conductorActors);
                vtkPlotting.addActors(renderer, impactSphereActors);

                vtkPlotting.showActor(renderWindow, absorbedLineBundle.actor, $scope.showAbsorbed);
                vtkPlotting.showActors(renderWindow, impactSphereActors, $scope.showAbsorbed && $scope.showImpact);
                vtkPlotting.showActor(renderWindow, reflectedLineBundle.actor, $scope.showReflected);
                vtkPlotting.showActors(renderWindow, conductorActors, $scope.showConductors, 0.80);

                // reset camera will negate zoom and pan but *not* rotation
                if (zoomUnits == 0 && ! didPan) {
                    renderer.resetCamera();
                }
                renderWindow.render();

                sceneRect =  vpOutline.boundingRect();

                // initial area of scene
                if (! sceneArea) {
                    sceneArea = sceneRect.area();
                }

                offscreen = ! (
                    sceneRect.intersectsRect(screenRect) ||
                    screenRect.containsRect(sceneRect) ||
                    sceneRect.containsRect(screenRect)
                );
                var a = sceneRect.area() / sceneArea;
                malSized = a < 0.1 || a > 7.5;
                $scope.canInteract = ! offscreen && ! malSized;
                if ($scope.canInteract) {
                    lastCamPos = cam.getPosition();
                    lastCamViewUp = cam.getViewUp();
                    lastCamFP = cam.getFocalPoint();
                }
                else {
                    setCam(lastCamPos, lastCamFP ,lastCamViewUp);
                }

                refreshAxes();

                // do this after the axes are set so the number of sections in the grids
                // match the new number of ticks
                refreshGridPlanes();

                if (SIREPO.APP_SCHEMA.feature_config.display_test_boxes) {
                    $scope.testBoxes = [

                        /*
                        {
                            x: xAxisLeft, //clippedXEnds[0][0],
                            y: xAxisTop, //clippedXEnds[0][1],
                            color: "red"
                        },
                        {
                            x: xAxisRight, //clippedXEnds[1][0],
                            y: xAxisBottom, //clippedXEnds[1][1],
                            color: "blue"
                        },
                        */
                        /*
                        {
                            x: yAxisLeft, //clippedYEnds[0][0],
                            y: yAxisTop, //clippedYEnds[0][1],
                            color: "red"
                        },
                        {
                            x: yAxisRight, //clippedYEnds[1][0],
                            y: yAxisBottom, //clippedYEnds[1][1],
                            color: "blue"
                        },
                        */
                        /*
                        {
                            x: clippedYEnds[0][0],
                            y: clippedYEnds[0][1],
                            color: "red"
                        },
                        {
                            x: clippedYEnds[1][0],
                            y: clippedYEnds[1][1],
                            color: "blue"
                        },
                        */
                        /*
                        {
                            x: screenYEnds.left[0],
                            y: screenYEnds.left[1],
                            color: "red"
                        },
                        {
                            x: screenYEnds.right[0],
                            y: screenYEnds.right[1],
                            color: "blue"
                        },
                        */
                        /*
                         {
                            x: clippedZEnds[0][0],
                            y: clippedZEnds[0][1],
                            color: "red"
                        },
                        {
                            x: clippedZEnds[1][0],
                            y: clippedZEnds[1][1],
                            color: "blue"
                        },
                        */
                        /*
                        {
                            x: zAxisLeft,
                            y: zAxisTop,
                            color: "red"
                        },
                        {
                            x: zAxisRight,
                            y: zAxisBottom,
                            color: "blue"
                        }
                        */
                    ];

                }

                if (doCacheCanvas) {
                    cacheCanvas();
                }
            }

            function refreshAxes() {

                // If an axis is shorter than this, don't display it -- the ticks will
                // be cramped and unreadable
                var minAxisDisplayLen = 50;

                var b = ['z'];
                //for (var i in b) {  // use to test inidividual axes
                for (var i in geometry.basis) {

                    //var dim = b[i];
                    var dim = geometry.basis[i];

                    var screenDim = axisCfg[dim].screenDim;
                    var isHorizontal = screenDim === 'x';
                    var axisEnds = isHorizontal ? ['◄', '►'] : ['▼', '▲'];
                    var perpScreenDim = isHorizontal ? 'y' : 'x';

                    var showAxisEnds = false;
                    var axisSelector = '.' + dim + '.axis';
                    var axisLabelSelector = '.' + dim + '-axis-label';

                    // sort the external edges so we'll preferentially pick the left and bottom
                    var externalEdges = vpOutline.externalVpEdgesForDimension(dim)
                        .sort(edgeSorter(perpScreenDim, ! isHorizontal));
                    var seg = geometry.bestEdgeAndSectionInBounds(externalEdges, screenRect, dim, false);

                    if (! seg) {
                        // all possible axis ends offscreen, so try a centerline
                        var cl = vpOutline.vpCenterLineForDimension(dim);
                        seg = geometry.bestEdgeAndSectionInBounds([cl], screenRect, dim, false);
                        if (! seg) {
                            // don't draw axes
                            select(axisSelector).style('opacity', 0.0);
                            select(axisLabelSelector).style('opacity', 0.0);
                            continue;
                        }
                        showAxisEnds = true;
                    }
                    select(axisSelector).style('opacity', 1.0);

                    var fullSeg = seg.full;
                    var clippedSeg = seg.clipped;
                    var reverseOnScreen = shouldReverseOnScreen(dim, seg.index, screenDim);
                    var sortedPts = geometry.sortInDimension(clippedSeg.points(), screenDim, false);
                    var axisLeft = sortedPts[0].x;
                    var axisTop = sortedPts[0].y;
                    var axisRight = sortedPts[1].x;
                    var axisBottom = sortedPts[1].y;

                    var newRange = Math.min(fullSeg.length(), clippedSeg.length());
                    var radAngle = Math.atan(clippedSeg.slope());
                    if (! isHorizontal) {
                        radAngle -= Math.PI / 2;
                        if (radAngle < -Math.PI / 2) {
                            radAngle += Math.PI;
                        }
                    }
                    var angle = (180 * radAngle / Math.PI);

                    var allPts = geometry.sortInDimension(fullSeg.points().concat(clippedSeg.points()), screenDim, false);

                    var limits = reverseOnScreen ? [axisCfg[dim].max, axisCfg[dim].min] : [axisCfg[dim].min, axisCfg[dim].max];
                    var newDom = [axisCfg[dim].min, axisCfg[dim].max];
                    // 1st 2, last 2 points
                    for (var m = 0; m < allPts.length; m += 2) {
                        // a point may coincide with its successor
                        var d = allPts[m].dist(allPts[m+1]);
                        if (d != 0) {
                            var j = Math.floor(m / 2);
                            var k = reverseOnScreen ? 1 - j : j;
                            var l1 = limits[j];
                            var l2 = limits[1 - j];
                            var part = (l1 - l2) * d / fullSeg.length();
                            var newLimit = l1 - part;
                            newDom[k] = newLimit;
                        }
                    }
                    var xform = 'translate(' + axisLeft + ',' + axisTop + ') ' +
                        'rotate(' + angle + ')';

                    axes[dim].scale.domain(newDom).nice();
                    axes[dim].scale.range([reverseOnScreen ? newRange : 0, reverseOnScreen ? 0 : newRange]);

                    // this places the axis tick labels on the appropriate side of the axis
                    var outsideCorner = geometry.sortInDimension(vpOutline.vpCorners(), perpScreenDim, isHorizontal)[0];
                    var bottomOrLeft = outsideCorner.equals(sortedPts[0]) || outsideCorner.equals(sortedPts[1]);
                    if (isHorizontal) {
                        axes[dim].svgAxis.orient(bottomOrLeft ? 'bottom' : 'top');
                    }
                    else {
                        axes[dim].svgAxis.orient(bottomOrLeft ? 'left' : 'right');
                    }


                    if (showAxisEnds) {
                        axes[dim].svgAxis.ticks(0);
                        select(axisSelector).call(axes[dim].svgAxis);
                    }
                    else {
                        axes[dim].updateLabelAndTicks({
                            width: newRange,
                            height: newRange
                        }, select);
                    }

                    select(axisSelector).attr('transform', xform);

                    var dimLabel = axisCfg[dim].dimLabel;
                    d3self.selectAll(axisSelector + '-end')
                        .style('opacity', showAxisEnds ? 1 : 0);

                    var tf = axes[dim].svgAxis.tickFormat();
                    if (tf) {
                        select(axisSelector + '-end.low')
                            .text(axisEnds[0] + ' ' + dimLabel + ' ' + tf(reverseOnScreen ? newDom[1] : newDom[0]) + axes[dim].unitSymbol + axes[dim].units)
                            .attr('x', axisLeft)
                            .attr('y', axisTop)
                            .attr('transform', 'rotate(' + (angle) + ', ' + axisLeft + ', ' + axisTop + ')');

                        select(axisSelector + '-end.high')
                            .attr('text-anchor', 'end')
                            .text(tf(reverseOnScreen ? newDom[0] : newDom[1]) + axes[dim].unitSymbol + axes[dim].units + ' ' + dimLabel + ' ' + axisEnds[1])
                            .attr('x', axisRight)
                            .attr('y', axisBottom)
                            .attr('transform', 'rotate(' + (angle) + ', ' + axisRight + ', ' + axisBottom + ')');
                    }

                    // counter-rotate the tick labels
                    var labels = d3self.selectAll(axisSelector + ' text');
                    labels.attr('transform', 'rotate(' + (-angle) + ')');
                    select(axisSelector + ' .domain').style({'stroke': 'none'});
                    select(axisSelector).style('opacity', newRange < minAxisDisplayLen ? 0 : 1);

                    var labelSpace = 2 * plotting.tickFontSize(select(axisSelector + '-label'));
                    var labelSpaceX = (isHorizontal ? Math.sin(radAngle) : Math.cos(radAngle)) * labelSpace;
                    var labelSpaceY = (isHorizontal ? Math.cos(radAngle) : Math.sin(radAngle)) * labelSpace;
                    var labelX = axisLeft + (bottomOrLeft ? -1 : 1) * labelSpaceX + (axisRight - axisLeft) / 2.0;
                    var labelY = axisTop + (bottomOrLeft ? 1 : -1) * labelSpaceY + (axisBottom - axisTop) / 2.0;
                    var labelXform = 'rotate(' + (isHorizontal ? 0 : -90) + ' ' + labelX + ' ' + labelY + ')';

                    select('.' + dim + '-axis-label')
                        .attr('x', labelX)
                        .attr('y', labelY)
                        .attr('transform', labelXform)
                        .style('opacity', (showAxisEnds || newRange < minAxisDisplayLen) ? 0 : 1);
                }
            }

            function edgeSorter(dim, shouldReverse) {
                return function(e1, e2) {
                    if (! e1) {
                        if (! e2) {
                            return 0;
                        }
                        return 1;
                    }
                    if (! e2) {
                        return -1;
                    }
                    var pt1 = geometry.sortInDimension(e1.points(), dim, shouldReverse)[0];
                    var pt2 = geometry.sortInDimension(e2.points(), dim, shouldReverse)[0];
                    return (shouldReverse ? -1 : 1) * (pt2[dim] - pt1[dim]);
                };
            }

            function shouldReverseOnScreen(dim, index, screenDim) {
                var currentEdge = vpOutline.vpEdgesForDimension(dim)[index];
                var currDiff = currentEdge.points()[1][screenDim] - currentEdge.points()[0][screenDim];
                return currDiff < 0;
            }

            // Redraw the grid planes to match the number of tick marks
            // on the axes
            function refreshGridPlanes() {

                var numX = Math.max($($element).find('.x.axis .tick').length - 1, 1);
                var numY = Math.max($($element).find('.y.axis .tick').length - 1, 1);
                var numZ = Math.max($($element).find('.z.axis .tick').length - 1, 1);
                for (var d = 0; d < 3; ++d) {
                    for (var s = 0; s < 1; ++s) {
                        var ps = gridPlaneBundles[d][s].source;
                        var xres = 2;
                        var yres = 2;
                        switch (2*d + s) {
                            // bottom, top
                            case 0: case 1:
                                xres = numX;
                                yres = numZ;
                                break;
                            // left, right
                            case 2: case 3:
                                xres = numZ;
                                yres = numY;
                                break;
                            // back, front
                            case 4: case 5:
                                xres = numX;
                                yres = numY;
                                break;
                            default:
                                break;
                        }
                        ps.setXResolution(xres);
                        ps.setYResolution(yres);
                    }
                }
            }

            function resetAndDigest() {
                $scope.$apply(reset);
            }
            function reset() {
                camPos = [0, 0, 1];
                camViewUp = [0, 1, 0];
                $scope.side = 'y';
                $scope.xdir = 1;  $scope.ydir = 1;  $scope.zdir = 1;
                resetCam();
            }
            function resetCam() {
                setCam(camPos, [0,0,0], camViewUp);
                cam.zoom(1.3);
                renderer.resetCamera();
                zoomUnits = 0;
                didPan = false;
                orientationMarker.updateMarkerOrientation();
                refresh(true);
            }
            function setCam(pos, fp, vu) {
                cam.setPosition(pos[0], pos[1], pos[2]);
                cam.setFocalPoint(fp[0], fp[1], fp[2]);
                cam.setViewUp(vu[0], vu[1], vu[2]);
            }
            function cacheCanvas() {
                if (! snapshotCtx) {
                    return;
                }
                var w = parseInt(canvas3d.getAttribute('width'));
                var h = parseInt(canvas3d.getAttribute('height'));
                snapshotCanvas.width = w;
                snapshotCanvas.height = h;
                // this call makes sure the buffer is fresh (it appears)
                fsRenderer.getOpenGLRenderWindow().traverseAllPasses();
                snapshotCtx.drawImage(canvas3d, 0, 0, w, h);
            }

            function resetZoom() {
            }

            $scope.clearData = function() {
            };

            $scope.destroy = function() {
                document.removeEventListener(utilities.fullscreenListenerEvent(), refresh);
                var rw = angular.element($($element).find('.sr-plot-particle-3d .vtk-canvas-holder'))[0];
                rw.removeEventListener('dblclick', resetAndDigest);
                $($element).off();
                fsRenderer.getInteractor().unbindEvents();
                fsRenderer.delete();
                plotToPNG.removeCanvas($scope.reportId);
            };

            $scope.resize = function() {
                refresh(false);
            };

            $scope.toggleAbsorbed = function() {
                $scope.showAbsorbed = ! $scope.showAbsorbed;
                vtkPlotting.showActor(renderWindow, absorbedLineBundle.actor, $scope.showAbsorbed);
                vtkPlotting.showActors(renderWindow, impactSphereActors, $scope.showAbsorbed && $scope.showImpact);
            };
            $scope.toggleImpact = function() {
                $scope.showImpact = ! $scope.showImpact;
                vtkPlotting.showActors(renderWindow, impactSphereActors, $scope.showAbsorbed && $scope.showImpact);
            };
            $scope.toggleReflected = function() {
                $scope.showReflected = ! $scope.showReflected;
                vtkPlotting.showActor(renderWindow, reflectedLineBundle.actor, $scope.showReflected);
            };
            $scope.toggleConductors = function() {
                $scope.showConductors = ! $scope.showConductors;
                vtkPlotting.showActors(renderWindow, conductorActors, $scope.showConductors, 0.80);
            };


            $scope.xdir = 1;  $scope.ydir = 1;  $scope.zdir = 1;
            $scope.side = 'y';
            $scope.showSide = function(side) {
                var dir = side === 'x' ? $scope.xdir : (side === 'y' ? $scope.ydir : $scope.zdir);
                if ( side == $scope.side ) {
                    dir *= -1;
                    if (side === 'x') {
                        $scope.xdir = dir;
                    }
                    if (side === 'y') {
                        $scope.ydir = dir;
                    }
                    if (side === 'z') {
                        $scope.zdir = dir;
                    }
                }
                $scope.side = side;

                camPos = side === 'x' ? [0, dir, 0] : (side === 'y' ? [0, 0, dir] : [dir, 0, 0] );
                camViewUp = side === 'x' ? [0, 0, 1] : [0, 1, 0];
                resetCam();
            };

            $scope.mode = 'move';
            $scope.selectMode = function(mode) {
                $scope.mode = mode;
                // turn off interactor?
            };

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }


        },

        link: function link(scope, element) {
            plotting.vtkPlot(scope, element);
        },
    };
});
