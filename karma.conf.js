// Karma configuration
// Generated on Tue Jul 21 2015 19:52:26 GMT+0000 (UCT)

// before running the first time:
//   npm install karma --save-dev
//   npm install karma-jasmine --save-dev
//   npm install karma-chrome-launcher
// then:
//   ./node_modules/karma/bin/karma start --single-run

module.exports = function(config) {
  config.set({

    // base path that will be used to resolve all patterns (eg. files, exclude)
    basePath: '',


    // frameworks to use
    // available frameworks: https://npmjs.org/browse/keyword/karma-adapter
    frameworks: ['jasmine'],


    // list of files / patterns to load in the browser
    files: [
        'sirepo/package_data/static/js/angular-1.4.2.js',
        'sirepo/package_data/static/js/angular-animate-1.4.2.js',
        'sirepo/package_data/static/js/angular-route-1.4.2.js',
        'sirepo/package_data/static/js/jquery-2.1.4.js',
        'sirepo/package_data/static/js/bootstrap-3.3.4.js',
        'sirepo/package_data/static/js/ngDraggable.js',
        'sirepo/package_data/static/js/modernizr-touch-2.8.3.min.js',
        'sirepo/package_data/static/js/bootstrap-slider-2.0.0.js',
        'sirepo/package_data/static/js/angular-d3.js',
        'sirepo/package_data/static/js/stacktrace-0.6.4.js',
        'sirepo/package_data/static/js/split-pane-0.6.1.js',
        'sirepo/package_data/static/js/angular-split-pane-1.2.0.js',
        'tests/helpers/globals.js',
        'sirepo/package_data/static/js/sirepo.js',
        'sirepo/package_data/static/js/sirepo-plotting.js',
        'sirepo/package_data/static/js/sirepo-components.js',
        'sirepo/package_data/static/js/sirepo-plotting.js',
        'sirepo/package_data/static/js/srw.js',
        'tests/helpers/angular/*.js',
        'tests/**/*.js',
    ],


    // list of files to exclude
    exclude: [
    ],

    // preprocess matching files before serving them to the browser
    // available preprocessors: https://npmjs.org/browse/keyword/karma-preprocessor
    preprocessors: {
    },


    // test results reporter to use
    // possible values: 'dots', 'progress'
    // available reporters: https://npmjs.org/browse/keyword/karma-reporter
    reporters: ['progress'],


    // web server port
    port: 8002,


    // enable / disable colors in the output (reporters and logs)
    colors: true,


    // level of logging
    // possible values: config.LOG_DISABLE || config.LOG_ERROR || config.LOG_WARN || config.LOG_INFO || config.LOG_DEBUG
    logLevel: config.LOG_INFO,


    // enable / disable watching file and executing tests whenever any file changes
    autoWatch: true,


    // start these browsers
    // available browser launchers: https://npmjs.org/browse/keyword/karma-launcher
    browsers: ['Chrome'],


    // Continuous Integration mode
    // if true, Karma captures browsers, runs the tests and exits
    singleRun: false
  })
}
