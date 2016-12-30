describe('srw1', function() {
    it('show-library', function() {
        var b = require('./base');
        var e;
        // Set and expect photon energy to change
        var expect_ev = '1.234';
        var EC = protractor.ExpectedConditions;
        // need root uri
        browser.get(browser.params.uri + '/srw');
        // Select a folder in simulations folder browser
        element(by.css('ul.s-nav-sidebar-root'))
            .element(by.xpath('..'))
            .element(by.cssExactText('a', 'Wavefront Propagation'))
            .click();
        // Select a simulation in simulations file browser
        element(by.linkText('Diffraction by an Aperture'))
            .click();
        // Save specific report panel
        var report = element(by.cssExactText('span.s-panel-heading', 'Intensity Report, 0.5m'))
            .element(by.xpath('../..'));
        // Report param editor
        report.element(by.css('.panel-heading a[title="Edit"]'))
            .click();
        // Modal pop up panel
        e = element(by.cssContainingText('.modal-header', 'Intensity Report'))
            .element(by.xpath('../..'));
        // Wait for it to be available
        browser.wait(EC.elementToBeClickable(e), 500);
        // Find the form on the panel
        var form = e.element(by.css('form'));
        // Photon Energy form label within the main form
        e = form.element(by.cssContainingText('label', 'Photon Energy [eV]'));
        // Photon Energy form field
        e = e.element(by.xpath('../../div/div/input'));
        // Clear the field
        e.clear();
        // Wait for it to be marked as invalid
        // visibilityOf() doesn't seem to be as reliable as elementToBeClickable()
        browser.wait(EC.elementToBeClickable(e.element(by.xpath('..')).element(by.css('input.ng-invalid'))), 500);
        // Enter the expected value to the field
        e.sendKeys(expect_ev);
        // Wait for the field to be valid
        browser.wait(EC.elementToBeClickable(e.element(by.xpath('..')).element(by.css('input.ng-valid'))), 500);
        // Wait for the Save Changes button to be clickable again
        e = form.element(by.cssExactText('button', 'Save Changes'));
        browser.wait(EC.elementToBeClickable(e), 500);
        e.click();
        // Wait for the report to be visible
        browser.wait(EC.elementToBeClickable(report), 1000);
        // Wait for the hourglass "Simulating..." to show up
        browser.wait(EC.elementToBeClickable(report.element(by.css('span.glyphicon-hourglass'))), 1000);
        // Wait for hourglass to go away
        browser.wait(EC.invisibilityOf(report.element(by.css('span.glyphicon-hourglass'))), 10000);
        // Get the title element
        e = report.element(by.css('text.main-title'));
        // Assert the expected value is in the report title
        expect(e.getText()).toBe('E=' + expect_ev + ' eV');
        return;
    });
});
