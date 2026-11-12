'use strict';
beforeEach(module('SirepoApp'));

describe('Proxy login handoff', function() {
    it('should retain the method chooser in mixed deployments', inject(function($controller) {
        const requestSender = {
            localRedirect: jasmine.createSpy('localRedirect'),
        };
        $controller('LoginController', {
            authService: {},
            authState: {isLoggedIn: false, visibleMethods: ['header', 'email']},
            requestSender: requestSender,
        });
        expect(requestSender.localRedirect).not.toHaveBeenCalled();
    }));

    it('should select a sole header method through the normal login page', inject(function($controller) {
        const requestSender = {
            localRedirect: jasmine.createSpy('localRedirect'),
        };
        $controller('LoginController', {
            authService: {},
            authState: {isLoggedIn: false, visibleMethods: ['header']},
            requestSender: requestSender,
        });
        expect(requestSender.localRedirect).toHaveBeenCalledWith(
            'loginWith', {':method': 'header'}
        );
    }));

    it('should navigate through the proxy rather than send an API login request', inject(function($controller) {
        const requestSender = {
            globalRedirect: jasmine.createSpy('globalRedirect'),
            sendRequest: jasmine.createSpy('sendRequest'),
        };
        $controller('LoginWithController', {
            authState: {},
            errorService: {},
            requestSender: requestSender,
            uri: {currentRouteParam: () => 'header'},
        });
        expect(requestSender.globalRedirect).toHaveBeenCalledWith(
            'authHeaderLogin', {simulation_type: SIREPO.APP_SCHEMA.simulationType}
        );
        expect(requestSender.sendRequest).not.toHaveBeenCalled();
    }));
});
