// will get rid of angular stuff but need it initially

class UIEnvironment {
    constructor(sanitizer=null) {
        this.sanitizer = sanitizer;
    }

    newInstance(className, ...args) {
        if (className === 'UIEnvironment') {
            return this;
        }
        //return new SIREPO.DOM[className](this, ...args);
        return new SIREPO.DOM[className](...args);
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

class UIAttribute {  //extends UIOutput {
    constructor(name, value) {
        //super();
        this.name = name;
        this.value = value;
    }

    static attrsToTemplate(arr) {
        let s = '';
        for (let attr of arr) {
            s += `${attr.toTemplate()} `;
        }
        return s;
    }

    toTemplate() {
        //return `${this.encode(this.name)}="${this.encode(this.value)}"`;
        return `${this.name}="${this.value}"`;
    }
}

class UIElement {  //extends UIOutput {
    // tag name, id, attrs array
    // even though id is an attribute, give it its own parameter
    constructor(tag, id, attrs) {
        //super();
        //this.attrs = [];
        // key-value map to manage attributes
        //srdbg('bld el', tag, id, attrs);
        this.attrs = {};
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
        //srdbg('got a', name, a);
        if (! a) {
            a = new UIAttribute(name, value);
            this.attrs[name] = a;
        }
        a.value = value;
    }

    addAttributes(arr) {
        for (let a of arr) {
            this.addAttribute(a.name, a.value);
        }
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
        return this.attrs[name];
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
        this.text = str;  //this.encode(str);
    }

    toTemplate() {
        let t = this.tag;  //this.encode(this.tag);
        let s = `<${t} ${UIAttribute.attrsToTemplate(Object.values(this.attrs))}>`;
        s += this.text;
        for (let c of this.children) {
            s += c.toTemplate();
        }
        s += `</${t}>`;
        for (let c of this.siblings) {
            s += c.toTemplate();
        }
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



class SVGGroup extends UIElement {
    constructor(id) {
        super('g', id);
    }
}

class SVGRect extends UIElement {
    constructor(id, x, y, width, height, style, doRound) {
        super('rect', id);
        if (doRound) {
            this.addAttributes([
                new UIAttribute('rx', 4),
                new UIAttribute('ry', 4),
            ]);
        }
        this.update(x, y, width, height, style);
    }

    update(x, y, width, height, style) {
        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
        this.style = style;
        for (let n of ['x', 'y', 'width', 'height', 'style']) {
            this.addAttribute(n, this[n]);
        }
    }

}


class SVGText extends UIElement {
    constructor(id, x, y, str = '') {
        super('text', id, [
            new UIAttribute('x', x),
            new UIAttribute('y', y),
        ]);
        this.setText(str);
    }
}

// fixed size
class SVGTable extends SVGGroup {
    constructor(id, x, y, cellWidth, cellHeight, cellPadding, numRows, numCols, borderStyle, doRoundBorder, header = []) {
        if (! numCols || ! numRows) {
            throw new Error(`Table must have at least 1 row and 1 column (${numRows} x ${numCols} given)`);
        }
        super(id);
        this.border = new SVGRect(this.borderId(), x, y, 0, 0, borderStyle, doRoundBorder);
        this.padding = cellPadding;
        this.cellWidth = cellWidth;
        this.cellHeight = cellHeight;
        this.numRows = numRows;
        this.numCols = numCols;
        this.borderStyle = borderStyle;
        this.headerOffset = header.length ? cellHeight : 0;

        for (let j = 0; j < header.length; ++j) {
            this.addChild(new SVGRect(
                null,
                x + j * cellWidth,
                y,
                cellWidth,
                cellHeight, 'stroke:lightgrey; fill:lightgrey', true
            ));
            let hdr = new SVGText(
            `${this.id}-header`,
                x + j * cellWidth + this.padding,
                y + cellHeight - this.padding,
                header[j]
            );
            hdr.addAttribute('font-weight', 'bold');
            this.addChild(hdr);
        }
        for (let i = 0; i < numRows; ++i) {
            for (let j = 0; j < numCols; ++j) {
                this.addChild(new SVGText(
                    this.cellId(i, j),
                    x + j * cellWidth + this.padding,
                    y + this.headerOffset + cellHeight + i * cellHeight - this.padding
                ));
                this.addChild(new SVGRect(
                    `${this.cellId(i, j)}-border`,
                    x + j * cellWidth,
                    y + this.headerOffset + i * cellHeight,
                    cellWidth,
                    cellHeight,
                    'stroke:black; fill:none',
                    false
                ));
            }
        }

        // add border last so it covers edges
        this.addChild(this.border);
        this.update(x, y);
    }

    borderId() {
        return `${this.id}-border`;
    }

    cellId(i, j) {
        return `${this.id}-${i}-${j}`;
    }

    getCell(i, j) {
        return $(`#${this.cellId(i, j)}`);
    }

    getCellBorder(i, j) {
        return $(`#${this.cellId(i, j)}-border`);
    }


    setCell(i, j, val, color=null) {
        let cid  = this.cellId(i, j);
        let c = this.getChild(cid);
        this.getChild(this.cellId(i, j)).setText(val);
        this.getCellBorder(i, j).css('fill', color);
    }

    setBorderStyle(style) {
        this.borderStyle = style;
        this.update(this.x, this.y);
    }

    update(x, y) {
        this.border.update(
            x,
            y,
            this.numCols * this.cellWidth,
            this.headerOffset + this.numRows * this.cellHeight,
            this.borderStyle
        );
    }

}

SIREPO.DOM = {
    SVGRect: SVGRect,
    SVGTable: SVGTable,
    SVGText: SVGText,
    UIAttribute: UIAttribute,
    UIMatch: UIMatch,
    UIElement: UIElement,
    UIEnum: UIEnum,
    UIEnumOption: UIEnumOption,
    UIEnvironment: UIEnvironment,
    UIInput: UIInput,
    UIWarning: UIWarning,
};
