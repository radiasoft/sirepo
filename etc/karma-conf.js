// Karma configuration
// Generated on Tue Jul 21 2015 19:52:26 GMT+0000 (UCT)
// before running the first time:
//   npm install karma --save-dev
//   npm install karma-jasmine --save-dev
//   npm install karma-phantomjs-launcher
//   npm install jasmine-core --save-dev
// then:
//   ./node_modules/karma/bin/karma start etc/karma-conf.js

module.exports = function(config) {
  config.set({

    // base path that will be used to resolve all patterns (eg. files, exclude)
    basePath: '..',


    // frameworks to use
    // available frameworks: https://npmjs.org/browse/keyword/karma-adapter
    frameworks: ['jasmine'],


    // list of files / patterns to load in the browser
    files: [
        'sirepo/package_data/static/js/ext/angular.js',
        'sirepo/package_data/static/js/ext/angular-route.js',
        'sirepo/package_data/static/js/ext/angular-cookies.js',
        'sirepo/package_data/static/js/ext/angular-sanitize.js',
        'sirepo/package_data/static/js/ext/jquery-2.2.4.js',
        'sirepo/package_data/static/js/ext/bootstrap-3.3.7.js',
        'sirepo/package_data/static/js/ext/ngDraggable.js',
        'sirepo/package_data/static/js/ext/angular-d3.js',
        'sirepo/package_data/static/js/ext/angular-vtk.js',
        'sirepo/package_data/static/js/ext/colorbar.js',
        'sirepo/package_data/static/js/ext/Blob.js',
        'sirepo/package_data/static/js/ext/canvas-toBlob.js',
        'sirepo/package_data/static/js/ext/FileSaver.js',
        'sirepo/package_data/static/js/ext/canvg-and-dependencies.js',
        'sirepo/package_data/static/js/ext/stacktrace-0.6.4.js',
        'sirepo/package_data/static/js/ext/bootstrap-toggle.js',
        'tests/helpers/globals.js',
        'sirepo/package_data/static/js/sirepo.js',
        'sirepo/package_data/static/js/sirepo-components.js',
        'sirepo/package_data/static/js/sirepo-plotting.js',
        'sirepo/package_data/static/js/sirepo-geometry.js',
        'sirepo/package_data/static/js/srw.js',
        'sirepo/package_data/static/js/ext/d3-3.5.9.js',
        'sirepo/package_data/static/js/ext/katex.js',
        'tests/helpers/angular/*.js',
        'tests/karma/**/*.js',
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

    client: {
        captureConsole: true
    },


    // web server port
    port: 8000,


    // enable / disable colors in the output (reporters and logs)
    colors: false,


    // level of logging
    // possible values: config.LOG_DISABLE || config.LOG_ERROR || config.LOG_WARN || config.LOG_INFO || config.LOG_DEBUG
    logLevel: config.LOG_INFO,


    // enable / disable watching file and executing tests whenever any file changes
    autoWatch: true,


    // start these browsers
    // available browser launchers: https://npmjs.org/browse/keyword/karma-launcher
    //browsers: ['Chrome'],
    browsers: ['PhantomJS'],
    // Continuous Integration mode
    // if true, Karma captures browsers, runs the tests and exits
    singleRun: true
  })
}
