// will get rid of angular stuff but need it initially

class UIEnvironment {
    constructor(sanitizer=null) {
        this.sanitizer = sanitizer;
    }

    newInstance(className, ...args) {
        if (className === 'UIEnvironment') {
            return this;
        }
        return new SIREPO.DOM[className](this, ...args);
    }

    sanitize(str) {
        return this.sanitizer ? this.sanitizer(str) : str;
    }
}

// any UI stuff seen on screen
class UIOutput {
    constructor(env = null) {
        this.env = env;
    }

    encode(str) {
        const ENTITY_MAP = {
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '"': '&quot;',
          "'": '&#39;',
          '/': '&#x2F;',
          '`': '&#x60;',
          '=': '&#x3D;'
        };
        return String(str).replace(/[&<>"'`=\/]/g, function (s) {
            return ENTITY_MAP[s];
        });
    }


    sanitize(str) {
        return this.env.sanitize(str);
    }
}

class UIAttribute extends UIOutput {
    constructor(env, name, value) {
        super(env);
        this.name = name;
        this.value = value;
    }

    static attrsToTempate(arr) {
        let s = '';
        for (let attr of arr) {
            s += attr.toTemplate();
        }
        return s;
    }

    toTemplate() {
        return `${this.encode(this.name)}="${this.encode(this.value)}"`;
    }
}

class UIElement extends UIOutput {
    // tag name, id, attrs array
    // even though id is an attribute, give it its own parameter
    constructor(env, tag, id, attrs) {
        super(env);
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
            this.attrs.push(this.env.newInstance('UIAttribute', name, value));
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
        for (let x of this.attrs) {
            if (x.name === name) {
                return  x;
            }
        }
        return null;
    }

    getChild(id) {
        for (let x of this.children) {
            if (x.id === id) {
                return  x;
            }
        }
        return null;
    }

    // helper
    getClasses() {
        return this.getAttr('class');
    }

    getSibling(id) {
        for (let x of this.siblings) {
            if (x.id === id) {
                return  x;
            }
        }
        return null;
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
        this.text = this.encode(str);
    }

    toTemplate() {
        let t = this.encode(this.tag);
        let s = `<${t} ${UIAttribute.attrsToTempate(this.attrs)}>`;
        s += this.text;
        for (let c of this.children) {
            s += c.toTemplate();
        }
        s += `</${t}>`;
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

    static enumMatch(name) {
        return new UIMatch(name, new UIEnum(new SIREPO.APP.SREnum(name)));
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



class SVGRect extends UIElement {
    constructor(id, x, y, width, height) {
        super('rect', id);
        this.update(x, y, width, height);
    }

    update(x, y, width, height) {
        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
        this.addAttributes([
            new UIAttribute('x', x),
            new UIAttribute('y', y),
            new UIAttribute('width', width),
            new UIAttribute('height', height)
        ]);
    }

}

class SVGTable extends SVGRect {
    constructor(id, x, y, numRows, numCols) {
        super('rect', id, 0, 0, 0, 0);
        this.padding = 2;
        this.cellWidth = 2 * this.padding;
        this.cellHeight = 2 * this.padding;
        this.cells = [];
        this.update(x, y, numRows, numCols);
    }

    cellId(i, j) {
        return `${this.id}-${i}-${j}`;
    }

    setCell(i, j, val) {

    }



    update(x, y, numRows, numCols) {
        super.update(
            x,
            y,
            this.padding + numCols * (this.cellWidth + this.padding),
            this.padding + numRows * (this.cellHeight + this.padding)
        );
        let w = this.padding;
        for (let i = 0; i < numRows; ++i) {
            let h = this.padding + i * this.cellHeight;
            for (let j = 0; j < numCols; ++j) {
                let cId = this.cellId(i, j);
                let c = this.getSibling();
                if (! c) {
                    //c = new SVGRect(cId, )
                }
            }
        }
    }


}

SIREPO.DOM = {
    UIAttribute: UIAttribute,
    UIMatch: UIMatch,
    UIElement: UIElement,
    UIEnum: UIEnum,
    UIEnumOption: UIEnumOption,
    UIEnvironment: UIEnvironment,
    UIInput: UIInput,
    UIWarning: UIWarning,
};
