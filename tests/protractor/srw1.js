describe('SRW Library', function() {
    it('show library', function() {
        browser.get('http://localhost:8000/srw');
        var folders = element.all(by.repeater('item in simulations.fileTree'));
        console.log(folders.first().getText());
    });
});
