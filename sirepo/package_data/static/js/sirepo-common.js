'use strict';

// Common code shared between the landing page app and the various sirepo apps

window.cookieconsent.initialise({
    //TODO(pjm): set cookie domain?
    content: {
        //TODO(pjm): update with links to terms of service when available
        message: 'This site uses cookies to deliver our services. By using our site, you acknowledge that you accept our use of cookies.',
        dismiss: 'I accept',
        link: null,
    },
    cookie: {
        name: 'sr_cookieconsent',
    },
    palette: {
        popup: {
            background: "#000",
        },
        button: {
            background: "#286090",
        },
    },
});
