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
}

// wrap an element with conditional element
class UIMatch extends UIElement {
    constructor(value, el) {
        super('div', null, [
            new UIAttribute('data-ng-switch-when', value),
            new UIAttribute('data-ng-class', 'fieldClass'),
        ]);
        this.addChild(el);
    }
}

class UIInput extends UIElement {
    constructor(tag, id, attrs) {
        super(tag, id, attrs);
        this.addSibling(new UIWarning());
    }
}

class UIEnum extends UIInput {
    static ENUM_LAYOUT_PROPS() {
        return {
            buttons: {
                entryClass: UIEnumButton,
                element: 'div',
                elementClasses: 'btn-group',
            },
            dropdown: {
                entryClass: UIEnumOption,
                element: 'select',
                elementClasses: 'form-control',
            },
        };
    }

    constructor(model) {
        const lp = UIEnum.ENUM_LAYOUT_PROPS();
        let props = lp[model.layout] || UIEnum.autoLayout(model);
        super(props.element, `sr-${SIREPO.UTILS.camelToKebabCase(model.name)}`);
        this.addClasses(props.elementClasses);
        if (model.layout === 'buttons') {
            this.addAttribute('data-ng-model', 'model[field]');
        }
        for (let e of model.entries) {
            this.addChild(new props.entryClass(e));
        }
    }

    // will need to know about the size of the columns etc. but for now just use number of
    // entries
    static autoLayout(model) {
        const lp = UIEnum.ENUM_LAYOUT_PROPS();
        if (model.entries.length < 4) {
            return lp.buttons;
        }
        else {
            return lp.dropdown;
        }
    }
}

class UIEnumButton extends UIElement {
    constructor(enumItem) {
        let v = `${enumItem.value}`;
        super('button', null, [
            new UIAttribute('class', 'btn sr-enum-button'),
            new UIAttribute('data-ng-click', `model[field] = '${v}'`),
            new UIAttribute(
                'data-ng-class',
                `{'active btn-primary': isSelectedValue('${v}'), 'btn-default': ! isSelectedValue('${v}')}`
            ),
        ]);
        this.setText(`${enumItem.label}`);
    }
}

class UIEnumOption extends UIElement {
    constructor(enumItem) {
        super('option');
        this.addAttribute('label', `${enumItem.label}`);
        this.addAttribute('value', `${enumItem.value}`);
    }
}


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
    UIMatch: UIMatch,
    UIElement: UIElement,
    UIEnum: UIEnum,
    UIEnumOption: UIEnumOption,
    UIInput: UIInput,
    UIWarning: UIWarning,
};
