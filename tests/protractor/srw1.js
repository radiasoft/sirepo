var $snapshot = require('protractor-snapshot');

describe('SRW-Library', function() {
    it('show-library', function() {
        browser.get('http://localhost:8000/srw');
        var e = element.all(by.repeater('item in simulations.fileTree'))
            .all(by.cssContainingText('ul li a', 'Wavefront Propagation'))
            .first();
        e.getText().then(console.log);
        $snapshot.source();
        e = e.click();
        $snapshot.source();
        var e1 = element.all(by.repeater('item in simulations.activeFolder.children'))
            .all(by.cssContainingText('.s-item-text', 'Diffraction by an Aperture'))
            .first();
        e1.getText().then(console.log);
        $snapshot.source();
        e1.click();
        $snapshot.source();
        //var ec = protractor.ExpectedConditions;
        // Waits for the element with id 'abc' to be present on the dom.
        // browser.wait(ec.presenceOf($('#s-gaussianBeam-basicEditor')), 5000);
        var e = element.all(by.cssContainingText('.s-panel-heading', 'Intensity Report'))
            .first();
        // e.getText().then(console.log);
        expect(e.getText()).toBe('Intensity Report, 0.5m');
        //expect(
        //
        //
        /*
        var click = element.all(by.cssContainingText('a', '/')).first();
        click.getTagName().then(console.log);
        // var click = element(by.cssContainingText('a', '/'));

        click.click();
        // console.log(click.getTagName());
        click = element.all(by.cssContainingText('*', 'Diffraction')).first();
        click.click();
        */
    });
});
