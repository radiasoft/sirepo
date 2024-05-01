'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.controller('JupyterHubLoginController', function(requestSender) {
    var self = this;

    srdbg("in controller");
    self.isLoading = true;
    srdbg("1 calling redirect");
    requestSender.sendRequest(
        'redirectJupyterHub',
        () => {self.isLoading = false; srdbg("2 called redirect");}
    );

    self.redir = () => {
        requestSender.sendRequest('redirectJupyterHub');
    };
});

SIREPO.app.directive('appHeader', function(jupyterhubloginService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: `
            <div data-app-header-brand="nav"></div>
            <div data-app-header-right="nav"></div>
        `
    };
});

SIREPO.app.factory('jupyterhubloginService', function(appState, requestSender) {
    const self = {};
    appState.setAppService(self);
    return self;
});
