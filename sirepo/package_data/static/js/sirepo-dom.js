'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

// will get rid of angular stuff but need it initially

class UIAttribute {  //extends UIOutput {
    constructor(name, value) {
        this.name = name;
        this.setValue(value);
    }

    static attrsToTemplate(arr) {
        let s = '';
        for (let attr of arr) {
            s += `${attr.toTemplate()} `;
        }
        return s;
    }

    setValue(value) {
        this.value = value;
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
        if (! a) {
            a = new UIAttribute(name, value);
            this.attrs[name] = a;
        }
        a.setValue(value);
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

    addChildren(arr) {
        for (let c of arr) {
            this.addChild(c);
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
        if (this.parent) {
            this.siblings.push(el);
            this.parent.addChild(el);
        }
    }

    clearChildren() {
        this.children = [];
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

    getIdSelector() {
        return `#${this.id}`;
    }

    getSibling(id) {
        for (let x of this.siblings) {
            if (x.id === id) {
                return  x;
            }
        }
        return null;
    }

    removeAttribute(name) {
        delete this.attrs[name];
    }

    removeChild(id) {
        let c = this.getChild(id);
        if (c) {
            this.children.splice(this.children.indexOf(c), 1);
        }
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

    removeSibling(id) {
        let s = this.getSibling(id);
        if (s) {
            this.siblings.splice(this.children.indexOf(s), 1);
            if (this.parent) {
                this.parent.removeChild(id);
            }
        }
    }

    setAttribute(name, val) {
        this.getAttr(name).setValue(val);
    }

    setClass(cl) {
        let a = this.getClasses();
        if (! a) {
            this.addAttribute('class', cl);
            return;
        }
        a.setValue(cl);
    }

    setText(str) {
        this.text = str;  //this.encode(str);
    }

    toDOM() {
        return document.getElementById(this.id);
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

// wrapper for html strings. No parsing (yet)
class UIRawHTML {
    constructor(html) {
        this.html = html;
    }

    toTemplate() {
        return this.html;
    }
}

class UIInput extends UIElement {
    constructor(id, type, initVal, attrs) {
        super('input', id, attrs);
        this.addAttribute('type', type);
        this.addAttribute('value', initVal);
        this.addSibling(new UIWarning());
    }

    getValue() {
        return this.toDOM().value;
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

class UISelect extends UIElement {
    constructor(id, attrs, options=[]) {
        super('select', id, attrs);
        this.addChildren(options);
    }

    // sugar
    addOption(o) {
        this.addChild(o);
    }

    addOptions(arr) {
        this.addChildren(arr);
    }
}

class UISelectOption extends UIElement {
    constructor(id, label, value) {
        super('option', id, [
            new UIAttribute('label', label),
            new UIAttribute('value', value),
        ]);

    }
}

class UIEnumOption extends UISelectOption {
    constructor(id, enumItem) {
        super(id, `${enumItem[1]}`, `${enumItem[0]}`);
    }
}


class SVGContainer extends UIElement {
    constructor(id, width, height) {
        super('svg', id, [
            new UIAttribute('width', width),
            new UIAttribute('height', height),
        ]);
    }
}

class SVGGroup extends UIElement {
    constructor(id) {
        super('g', id);
    }
}

class SVGPath extends UIElement {
    constructor(id, points, offsets=[0, 0], doClose=false, strokeColor='black', fillColor='none') {
        super('path', id);
        this.doClose = doClose;
        this.fillColor = fillColor;
        this.offsets = offsets;
        this.points = points;
        this.scales = [1.0, 1.0];
        this.strokeColor = strokeColor;

        this.addAttribute('d', '');
        this.addAttribute('fill', fillColor);
        this.addAttribute('stroke', strokeColor);
        this.update();
    }

    closestCorner(x, y) {
        let d = Number.MAX_VALUE;
        let closest = null;
        for (let c of this.corners) {
            let d2 = (c[0] - x) * (c[0] - x) + (c[1] - y) * (c[1] - y);
            if (d2 < d) {
                d = d2;
                closest = c;
            }
        }
        return closest;
    }

    closestLines(x, y) {
        return this.linesWithCorner(this.closestCorner(x, y));
    }

    linesWithCorner(c) {
        let lines = [];
        for (let l of this.lines) {
            if (l[0] == c || l[1] == c) {
                lines.push(l);
            }
        }
        return lines;
    }

    /**
     * Scale and offset the point at the given index
     * @param {number} i - point index
     * @returns {[number, number]} - scaled and offset point
     */
    pathPointAt(i) {
        return this.pathPoint(this.points[i]);
    }

    /**
     * Scale and offset the given point
     * @param {[number, number]} p - point
     * @returns {[number, number]} - scaled and offset point
     */
    pathPoint(p) {
        return [0, 1].map(j => this.offsets[j] + this.scales[j] * p[j]);
    }

    /**
     * Scaled and offset points
     * @returns {[[number, number]]} - scaled and offset points
     */
    pathPoints() {
        return this.points.map(p => this.pathPoint(p));
    }

    /**
     * The string assigned to the 'd' attrribute
     * @returns {string} - the string
     */
    pathString(doClose) {
        let c = this.pathPointAt(0);
        this.corners = [c];
        this.lines = [];
        let p = `M${c[0]},${c[1]} `;
        for (let i = 1; i < this.points.length; ++i) {
            c = this.pathPointAt(i);
            this.lines.push([c, this.corners[this.corners.length - 1]]);
            this.corners.push(c);
            p += `L${c[0]},${c[1]} `;
        }
        if (doClose || this.doClose) {
            this.lines.push([this.corners[this.corners.length - 1], this.corners[0]]);
            p += 'z';
        }
        return p;
    }

    setFill(color) {
        this.fillColor = color;
        this.setAttribute('fill', this.fillColor);
    }

    setScales(scales) {
        this.scales = scales;
    }

    setStroke(color) {
        this.strokeColor = color;
        this.setAttribute('stroke', this.strokeColor);
    }

    update() {
        this.getAttr('d').setValue(this.pathString());
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

class SVGShapeButton extends UIElement {
    constructor(id, size, onclick) {
        super('button', id, [
            new SIREPO.DOM.UIAttribute('data-ng-click', `${onclick}()`),
        ]);
        this.svg = new SIREPO.DOM.SVGContainer(`${id}-svg`, size, size);
        this.addChild(this.svg);
        this.shape = null;
    }

    setShape(s) {
        this.shape = s;
        $(`${this.svg.getIdSelector()}`).html(this.shape.toTemplate());
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
        this.borderStyle = borderStyle;
        this.cellWidth = cellWidth;
        this.cellHeight = cellHeight;
        this.headerOffset = header.length ? cellHeight : 0;
        this.numRows = numRows;
        this.numCols = numCols;
        this.padding = cellPadding;
        this.x = x;
        this.y = y;

        for (let j = 0; j < header.length; ++j) {
            this.addChild(new SVGRect(
                null,
                x + j * cellWidth,
                y,
                cellWidth,
                cellHeight,
                'stroke:lightgrey; fill:lightgrey',
                true
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
                this.addChild(new SVGRect(
                    this.cellBorderId(i, j),
                    x + j * cellWidth,
                    y + this.headerOffset + i * cellHeight,
                    cellWidth,
                    cellHeight,
                    'stroke:black; fill:none',
                    false
                ));
                this.addChild(new SVGText(
                    this.cellId(i, j),
                    x + j * cellWidth + this.padding,
                    y + this.headerOffset + cellHeight + i * cellHeight - this.padding
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

    cellBorderId(i, j) {
        return `${this.cellId(i, j)}-border`;
    }

    getCell(i, j) {
        return $(`#${this.cellId(i, j)}`);
    }

    getCellBorder(i, j) {
        return $(`#${this.cellBorderId(i, j)}`);
    }

    setCell(i, j, val, color=null, opacity=0.0, borderWidth=1.0) {
        let cid  = this.cellId(i, j);
        let c = this.getChild(cid);
        this.getChild(this.cellId(i, j)).setText(val);
        this.getCellBorder(i, j).css('fill', color).css('fill-opacity', opacity).css('stroke-width', borderWidth);
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
    SVGContainer: SVGContainer,
    SVGGroup:SVGGroup,
    SVGPath: SVGPath,
    SVGRect: SVGRect,
    SVGShapeButton: SVGShapeButton,
    SVGTable: SVGTable,
    SVGText: SVGText,
    UIAttribute: UIAttribute,
    UIMatch: UIMatch,
    UIElement: UIElement,
    UIEnum: UIEnum,
    UIEnumOption: UIEnumOption,
    UIInput: UIInput,
    UIRawHTML: UIRawHTML,
    UISelect: UISelect,
    UISelectOption: UISelectOption,
    UIWarning: UIWarning,
};
