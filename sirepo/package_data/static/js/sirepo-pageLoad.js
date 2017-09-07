'use strict';

var pageLoaderTimeout = null;
var showPageLoader = function () {
    var pageLoader = document.getElementsByClassName('sr-page-load')[0];
    if (pageLoaderTimeout) {
        return;
    }
    console.log('starting timer to show page loader');
    pageLoaderTimeout = setTimeout(function () {
        pageLoader.style.display = 'block';
    },
        1000
    );
};
var hidePageLoader = function () {
    clearTimeout(pageLoaderTimeout);
    pageLoaderTimeout = null;
    var pageLoader = document.getElementsByClassName('sr-page-load')[0];
    pageLoader.style.display = 'none';
};