/*
 * Vermilion Gruntfile
 * http://vermilion.com
 */

/**
 * Grunt Module
 */
module.exports = function(grunt) {

  'use strict';

  // Project configuration.
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
    sass: {
      dest: {
        options: {
          style: 'expanded',
          sourcemap: 'file'
        },
        files: {
          './css/landing.css' : './css/landing.scss',
        }
      }
    },
    watch: {
      styles: {
        files: ['./css/*.scss'],
        tasks: ['sass'],
      },
    }
  });

  // Load plugins here
  grunt.loadNpmTasks('grunt-contrib-sass');
  grunt.loadNpmTasks('grunt-contrib-watch');


  // Default task(s).
  grunt.registerTask('default', ['sass']);
  grunt.registerTask('dev', ['watch']);

  };
