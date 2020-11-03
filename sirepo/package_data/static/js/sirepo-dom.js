// will get rid of angular stuff like but need it initially

class SRAttribute {
    constructor(name, value) {
        this.name = name;
        this.value = value;
    }

    static attrsToString(arr) {
        let s = '';
        for (let attr of arr) {
            s += `${attr.toString()} `;
        }
        return s;
    }

    toString() {
        return `${this.name}="${this.value}"`;
    }
}

class SRElement {
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
        this.tag = tag;
        this.text = '';
    }

    addAttribute(name, value) {
        let a = this.getAttr(name);
        if (a) {
            a.value = value;
        }
        else {
            this.attrs.push(new SRAttribute(name, value));
        }
    }

    addAttributes(arr) {
        this.attrs.push(...arr);
    }

    addChild(el) {
        el.parent = this;
        this.children.push(el);
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
        if (! this.parent) {
            throw new Error(`${this}: cannot add sibling to element with no parent`);
        }
        this.parent.addChild(el);
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

    toString() {
        let s = `<${this.tag} ${SRAttribute.attrsToString(this.attrs)}>`;
        s += this.text;
        for (let c of this.children) {
            s += `${c.toString()}`;
        }
        s += `</${this.tag}>`;
        return s;
    }

    show(doShow) {
    }

}


class SRInput extends SRElement {
    constructor(tag, id, attrs, isValidated) {
        super(tag, id, attrs);
        if (isValidated) {
            this.addSibling(new SRWarning());
        }
    }
}

class SREnum extends SRInput {
    constructor(enumName, id, attrs, asButtons, isValidated) {
        if (! SIREPO.APP_SCHEMA.enum[enumName]) {
            throw new Error(`${enumName}: no such enum in schema`);
        }
        if (asButtons) {
            super('div', id, attrs, isValidated);
            this.addClasses('btn-group');
        }
        else {
            super('select', id, attrs, isValidated);
            this.addClasses('form-control');
            this.addAttribute('data-ng-model', 'model[field]');
        }
        for (let e of SIREPO.APP_SCHEMA.enum[enumName]) {
            this.addChild(asButtons ? new SREnumButton(e) : new SREnumOption(e));
        }
    }
}

class SREnumButton extends SRElement {
    constructor(enumItem) {
        super('button', null, [
            new SRAttribute('class', 'btn sr-enum-button'),
            new SRAttribute('data-ng-click', `model[field] = '${enumItem[SIREPO.ENUM_INDEX_VALUE]}'`),
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

class SREnumOption extends SRElement {
    constructor(enumItem) {
        super('option');
        this.addAttribute('label', `${enumItem[SIREPO.ENUM_INDEX_LABEL]}`);
        this.addAttribute('value', `${enumItem[SIREPO.ENUM_INDEX_VALUE]}`);
    }
}

// build selection DOM for an enum from the schema
class SRWarning extends SRElement {
    constructor(msg) {
        super('div', null, [
            new SRAttribute('class', 'sr-input-warning')
        ]);
        this.setMsg(msg || '');
    }

    setMsg(msg) {
        this.text = msg;
    }
}

SIREPO.DOM = {
    SRAttribute: SRAttribute,
    SRElement: SRElement,
    SREnum: SREnum,
    SREnumOption: SREnumOption,
    SRInput: SRInput,
    SRWarning: SRWarning,
};
