// var $snapshot = require('protractor-snapshot');
// $snapshot.source();
// e.getText().then(console.log);

describe('SRW-Library', function() {
    it('show-library', function() {
        var e;
        var expect_ev = '1.234';
        browser.get('http://localhost:8000/srw');
        element.all(by.repeater('item in simulations.fileTree'))
            .all(by.cssContainingText('a', 'Wavefront Propagation'))
            .first()
            .click();
        element.all(by.repeater('item in simulations.activeFolder.children'))
            .all(by.cssContainingText('.s-item-text', 'Diffraction by an Aperture'))
            .first()
            .click();
        element.all(by.css('.model-simulation-photonEnergy input'))
            .first()
            .clear()
            .sendKeys(expect_ev);
        element(by.id('s-gaussianBeam-basicEditor'))
            .element(by.cssContainingText('button', 'Save Changes'))
            .click();
        e = element.all(by.cssContainingText('div.panel-heading', 'Intensity Report'))
            .first()
            .element(by.xpath('..'))
            .element(by.css('text.main-title'));
        expect(e.getText()).toBe('E=' + expect_ev + ' eV');
        /*
        /*
        var link = element(by.css("a[data-ng-click='toggleEditMode()']"));
        // e.getText().then(console.log);
        // expect(e.getText()).toBe('Intensity Report, 0.5m');
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
