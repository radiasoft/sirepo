exports.config = {
    framework: 'jasmine',
    seleniumAddress: 'http://localhost:4444/wd/hub',
    specs: ['tests/protractor/**/*.js'],
    jasmineNodeOpts: {
        showColors: 0
    },
    capabilities: {
        browserName: 'chrome',
        loggingPrefs: {
            browser: 'ALL'
        }
    },
    // Custom parameters for test. You can override on command line --params.sr_uri=https:/...
    params: {
        uri: 'http://localhost:8000',
        save: function() {
            var $snapshot = require('protractor-snapshot');
            $snapshot.source();
        }
    },
    plugins: [
        {
            package: 'protractor-console-plugin',
            failOnWarning: true,
            failOnError: true
        },
        {
            package: 'protractor-console',
            logLevels: ['debug', 'info', 'warning', 'severe']
        }
    ],
    protractorSnapshotOpts: {

        // base format for created files
        // replaces %suiteName%, %suiteId%, %specName%, %specId%, %browser%, %resolution% and %increment% with their respective values
        basename: '%suiteName%-%specName%-%increment%',

        image: {

                // where to put the screenshots, used by the default callback
            target: './run/protractor-snapshot',

            // default callbacks to handle the screenshot data
            callbacks: [
                function (instance, png, customConfig) {
                    // instance = $snapshot instance
                    // png = image data
                    // customConfig = argument provided to .image()
                },

                // by default this callback is configured
                require('protractor-snapshot').saveImage
            ]
        },

        source: {

                // where to put the html snapshots, used by the default callback
            target: './run/protractor-snapshot',

            // remove <meta name="fragment" content="!"> elements from the HTML snapshots
            removeMetaFragments: false,

            // default callbacks to handle snapshot data
            callbacks: [
                function (instance, html, customConfig) {
                    // instance = $snapshot instance
                    // html = html contents of page as string
                    // customConfig = argument provided to .source()
                },

                // by default this callback is configured
                require('protractor-snapshot').saveSource
            ]
        },

        // what resolution to turn back to after cycle(), [width, height, type]
        // type can be 'window' for outer window size, or 'viewport' for viewport size
        defaultResolution: [700, 700, 'window'],

        // supported resolutions, array of [width, height, type]
        // type can be 'window' for outer window size, or 'viewport' for viewport size
        resolutions: [
            [1366, 768, 'window'],
            [320, 568, 'viewport']
        ],

        // function or array of function, executed on first call of image() or source()
        // each function receives the ProtractorSnapshot instance as argument so you can use its config
        onInit: function ($snapshot) {
            $snapshot.clearTarget('./run/protractor-snapshot');
        },

        // write a log of all created snapshots, set to false to disable
        report: './run/protractor-snapshot/report.json'
    },

    onPrepare: function () {
        // For Jasmine V2 a reporter needs to be added to be able to access the suite/spec names
        var $protractorSnapshot = require('protractor-snapshot');
        $protractorSnapshot.addReporter();
        // Disable animations for better reliability: https://gist.github.com/ariel-symphony/4acfc04813c89d60e7a4
        var disableNgAnimate = function() {
            angular
                .module('disableNgAnimate', [])
                .run(['$animate', function($animate) {
                    $animate.enabled(false);
                }]);
        };
        var disableCssAnimate = function() {
            angular
                .module('disableCssAnimate', [])
                .run(function() {
                    var style = document.createElement('style');
                    style.type = 'text/css';
                    style.innerHTML = '* {' +
                        '-webkit-transition: none !important;' +
                        '-moz-transition: none !important' +
                        '-o-transition: none !important' +
                        '-ms-transition: none !important' +
                        'transition: none !important' +
                        '}';
                    document.getElementsByTagName('head')[0].appendChild(style);
                });
        };
        browser.addMockModule('disableNgAnimate', disableNgAnimate);
        browser.addMockModule('disableCssAnimate', disableCssAnimate);
    }
}
