describe('srw1', function() {
    it('show-library', function() {
        var b = require('./base');
        var e;
        var expect_ev = '1.234';
        var EC = protractor.ExpectedConditions;
        // everything should be a visible string
        // waiting should be implicit
        //   .. test for not there then can't wait
        // something should be clickable
        // rendering is very slow
        browser.get(browser.params.uri + '/srw');
/*
  browser.manage().logs().get('browser').then(function(browserLog) {
            console.log('browser log: ' + require('util').inspect(browserLog));
        });
*/
        element(by.css('ul.s-nav-sidebar-root'))
            .element(by.xpath('..'))
            .element(by.linkText('Wavefront Propagation'))
            .click();
        element(by.linkText('Diffraction by an Aperture'))
            .click();
        var report = element(by.cssContainingText('.panel-heading', 'Intensity Report, 0.5m'))
            .element(by.xpath('..'));
        report.element(by.css('.panel-heading a[title="Edit"]'))
            .click();
        e = element(by.cssContainingText('.modal-header', 'Intensity Report'))
            .element(by.xpath('../..'));
        browser.wait(EC.elementToBeClickable(e), 3000);
        var form = e.element(by.linkText('Main'))
            .element(by.xpath('../../../../form'));
        e = form.element(by.cssContainingText('label', 'Photon Energy [eV]'));
        expect(e.getText()).toBe('Photon Energy [eV]')
//TODO: test for browser position. Should be relative
        e = e.element(by.xpath('../../div/div/input'));
        browser.wait(EC.elementToBeClickable(e), 5000);
        e.getWebElement().then(function (we) {});
        e.clear()
            .sendKeys(expect_ev);
        e = form.element(by.cssContainingText('button', 'Save Changes'))
            .click();
        //e.getWebElement().then(function (we) {});
        browser.wait(EC.visibilityOf(element(by.css('.glyphicon-hourglass'))), 1000);
        browser.wait(EC.invisibilityOf(element(by.css('.glyphicon-hourglass'))), 10000);
        e = report.element(by.css('text.main-title'));
        b.snapshot();
        expect(e.getText()).toBe('E=' + expect_ev + ' eV');
        return;
    });
});
