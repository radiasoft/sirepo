// Common code to all tests
var snapshot = require('protractor-snapshot');

module.exports = {
    snapshot: function () {
        snapshot.source();
    }
};
