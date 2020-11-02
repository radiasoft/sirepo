

class SRAttribute {
    constructor(name, val) {
        this.name = name;
        this.val = val;
    }

    static attrsToString(arr) {
        return arr.map(function (attr) {
            return `${attr.toString()} `;
        });
    }

    toString() {
        return `${this.name}="${this.val}"`;
    }
}

class SRElement {
    // tag name, id, attrs map
    // even though id is an attribute, give it its own parameter
    constructor(tag, id, attrs) {
        this.attrs = [];
        if (id) {
            this.addAttribute(new SRAttribute('id', id));
        }
        this.addAttributes(attrs || []);
        this.children = [];
        this.id = id;
        this.parent = null;
        this.tag = tag;
        this.text = '';
    }

    static toStrArray(el) {
        let arr = [`<${el.tag} ${SRAttribute.attrsToString(el.attrs)}>`];
        arr.push(el.text);
        arr.push(...el.children.map(function (c) {
            return `${SRElement.toStrArray(c)}`;
        }));
        arr.push(`</${el.tag}>`);
        return arr;
    }

    addAttribute(attr) {
        this.attrs.push(attr);
    }

    addAttributes(arr) {
        this.attrs.push(...arr);
    }

    addChild(el) {
        el.parent = this;
        this.children.push(el);
    }

    addSibling(el) {
        if (! this.parent) {
            throw new Error(`${this}: cannot add sibling to element with no parent`);
        }
        this.parent.addChild(el);
    }

    setText(str) {
        this.text = str;
    }

    toString() {
        return SRElement.toStrArray(this).join('');
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
    constructor(enumName, id, asButtons, isValidated) {
        super('select', id, null, isValidated);
        if (! SIREPO.APP_SCHEMA.enum[enumName]) {
            throw new Error(`${enumName}: no such enum in schema`);
        }
        for (let e of SIREPO.APP_SCHEMA.enum[enumName]) {
            this.addChild(new SREnumOption(e));
        }
    }
}

class SREnumOption extends SRElement {
    constructor(enumItem) {
        super('option', null, [
            new SRAttribute('label', `${enumItem[SIREPO.ENUM_INDEX_LABEL]}`),
            new SRAttribute('value', `${enumItem[SIREPO.ENUM_INDEX_VALUE]}`),
        ]);
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
    SRElement: SRElement,
};

/*
export {
    SRAttribute,
    SRElement,
    SREnum,
    SREnumOption,
    SRInput,
    SRWarning,
};
*/
