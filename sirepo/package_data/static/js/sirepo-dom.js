// will get rid of angular stuff like but need it initially

class UIAttribute {
    constructor(name, value) {
        this.name = name;
        this.value = value;
    }

    static attrsToTempate(arr) {
        let s = '';
        for (let attr of arr) {
            s += `${attr.toTemplate()} `;
        }
        return s;
    }

    toTemplate() {
        return `${this.name}="${this.value}"`;
    }
}

class UIElement {
    // tag name, id, attrs array
    // even though id is an attribute, give it its own parameter
    constructor(tag, id, attrs) {
        this.attrs = [];
        this.addAttributes(attrs || []);
        if (id) {
            this.addAttribute('id', id);
        }
        this.children = [];
        this.id = id;
        this.parent = null;
        this.siblings = [];
        this.tag = tag;
        this.text = '';
    }

    addAttribute(name, value) {
        let a = this.getAttr(name);
        if (a) {
            a.value = value;
        }
        else {
            this.attrs.push(new UIAttribute(name, value));
        }
    }

    addAttributes(arr) {
        this.attrs.push(...arr);
    }

    addChild(el) {
        el.parent = this;
        this.children.push(el);
        for (let s of el.siblings || []) {
            this.addChild(s);
        }
    }

    // add a class to the existing list, or set it.  Can be space-delimited
    // list
    addClasses(cl) {
        let a = this.getClasses();
        if (! a) {
            this.setClass(cl);
            return;
        }
        let arr = a.value.split(' ');
        if (arr.indexOf(cl) >= 0) {
            return;
        }
        arr.push(...cl.split(' '));
        this.setClass(arr.join(' '));
    }

    addSibling(el) {
        this.siblings.push(el);
        //if (! this.parent) {
        //    console.log('ADD TO SIBS, NOT DOM');
        //    return;
        //    //throw new Error(`${this}: cannot add sibling to element with no parent`);
        //}
        if (this.parent) {
            this.parent.addChild(el);
        }
    }

    getAttr(name) {
        for (let a of this.attrs) {
            if (a.name === name) {
                return  a;
            }
        }
        return null;
    }

    // helper
    getClasses() {
        return this.getAttr('class');
    }

    removeClasses(cl) {
        let a = this.getClasses();
        if (! a) {
            return;
        }
        let arr = a.value.split(' ');
        let clArr = cl.split(' ');
        for (let c of clArr) {
            let clIdx = arr.indexOf(c);
            if (clIdx >= 0) {
                arr.splice(clIdx, 1);
            }
        }
        this.setClass(arr.join(' '));
    }

    setClass(cl) {
        let a = this.getClasses();
        if (! a) {
            this.addAttribute('class', cl);
            return;
        }
        a.value = cl;
    }

    setText(str) {
        this.text = str;
    }

    toTemplate() {
        let s = `<${this.tag} ${UIAttribute.attrsToTempate(this.attrs)}>`;
        s += this.text;
        for (let c of this.children) {
            s += `${c.toTemplate()}`;
        }
        s += `</${this.tag}>`;
        return s;
    }

    show(doShow) {
    }

}


class UIInput extends UIElement {
    constructor(tag, id, attrs) {
        super(tag, id, attrs);
        this.addSibling(new UIWarning());
    }
}

class UIEnum extends UIInput {
    //constructor(enumName, attrs, asButtons) {
    constructor(em) {
        //if (! SIREPO.APP_SCHEMA.enum[enumName]) {
        //let em = SIREPO.APP_SCHEMA.enumModels[enumName];
        //if (! em) {
        //    throw new Error(`${enumName}: no such enum in schema`);
        //}
        //let id = `sr-${SIREPO.UTILS.camelToKebabCase(enumName)}`;
        let id = `sr-${SIREPO.UTILS.camelToKebabCase(em.name)}`;

        //if (asButtons) {
        if (em.layout === 'buttons') {
            super('div', id);
            this.addClasses('btn-group');
        }
        else {
            super('select', id);
            this.addClasses('form-control');
            this.addAttribute('data-ng-model', 'model[field]');
        }
        this.layout = em.layout;
        //for (let e of SIREPO.APP_SCHEMA.enum[enumName]) {
        for (let e of em.entries) {
            this.addChild(ENUM_LAYOUT_ELEMENTS[this.layout](e) || this.autoLayout());
        }
    }

    // will need to know about the size of the columns etc. but for now just use number of
    // entries
    autoLayout() {
        return;
    }
}


/*
class UIEnum extends UIInput {
    constructor(e) {
        let id = `sr-${SIREPO.UTILS.camelToKebabCase(e)}`;
        //if (asButtons) {
        //    super('div', id, attrs, isValidated);
        //    this.addClasses('btn-group');
        //}
        else {
            super('select', id, attrs, isValidated);
            this.addClasses('form-control');
            this.addAttribute('data-ng-model', 'model[field]');
        }
        for (let e in SIREPO.application.enums) {
            this.addChild(asButtons ? new UIEnumButton(e) : new UIEnumOption(e));
        }
    }
}
*/

class UIEnumButton extends UIElement {
    constructor(enumItem) {
        super('button', null, [
            new UIAttribute('class', 'btn sr-enum-button'),
            new UIAttribute('data-ng-click', `model[field] = '${enumItem[SIREPO.ENUM_INDEX_VALUE]}'`),
        ]);
        this.setText(`${enumItem[SIREPO.ENUM_INDEX_LABEL]}`);
    }

    setActive(isActive) {
        if (isActive) {
            this.removeClasses('btn-default');
            this.addClasses('active btn-primary');
        }
        else {
            this.removeClasses('active btn-primary');
            this.addClasses('btn-default');
        }
    }
}

class UIEnumOption extends UIElement {
    constructor(enumItem) {
        super('option');
        this.addAttribute('label', `${enumItem[SIREPO.ENUM_INDEX_LABEL]}`);
        this.addAttribute('value', `${enumItem[SIREPO.ENUM_INDEX_VALUE]}`);
    }
}

const ENUM_LAYOUT_ELEMENTS = {
    'buttons': UIEnumButton,
    'dropdown': UIEnumOption,
};

// build selection DOM for an enum from the schema
class UIWarning extends UIElement {
    constructor(msg) {
        super('div', null, [
            new UIAttribute('class', 'sr-input-warning')
        ]);
        this.setMsg(msg || '');
    }

    setMsg(msg) {
        this.text = msg;
    }
}

SIREPO.DOM = {
    UIAttribute: UIAttribute,
    UIElement: UIElement,
    UIEnum: UIEnum,
    UIEnumOption: UIEnumOption,
    UIInput: UIInput,
    UIWarning: UIWarning,
};
