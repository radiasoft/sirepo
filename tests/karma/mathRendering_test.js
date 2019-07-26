'use strict';
beforeEach(module('SirepoApp'));

describe('components: mathRendering', function() {
    it('should detect math in text', inject(function(mathRendering) {
        expect(mathRendering.textContainsMath('Some text $W_E$ and math')).toEqual(true);
        expect(mathRendering.textContainsMath('$\\lambda$')).toEqual(true);
        expect(mathRendering.textContainsMath('$c$')).toEqual(true);
        expect(mathRendering.textContainsMath(' $c$')).toEqual(true);
        expect(mathRendering.textContainsMath('$c$ ')).toEqual(true);
        expect(mathRendering.textContainsMath('$-c$ ')).toEqual(true);
        expect(mathRendering.textContainsMath('$ c $')).toEqual(false);
        expect(mathRendering.textContainsMath('$c $')).toEqual(false);
        expect(mathRendering.textContainsMath('$ c$')).toEqual(false);
        expect(mathRendering.textContainsMath('$c ')).toEqual(false);
        expect(mathRendering.textContainsMath(' c$')).toEqual(false);
        expect(mathRendering.textContainsMath('')).toEqual(false);
        expect(mathRendering.textContainsMath(null)).toEqual(false);
    }));
    it('should convert text to html', inject(function(mathRendering) {
        expect(mathRendering.mathAsHTML('Some text & special <characters>'))
            .toEqual('Some text &amp; special &lt;characters&gt;');
        expect(mathRendering.mathAsHTML('')).toEqual('');
        expect(mathRendering.mathAsHTML(null)).toEqual('');
    }));
    it('should convert math to html', inject(function(mathRendering) {
        expect(mathRendering.mathAsHTML('$X$')).toEqual(
            '<span class="katex"><span class="katex-mathml"><math><semantics><mrow><mi>X</mi></mrow><annotation encoding="application/x-tex">X</annotation></semantics></math></span><span class="katex-html" aria-hidden="true"><span class="base"><span class="strut" style="height:0.68333em;vertical-align:0em;"></span><span class="mord mathdefault" style="margin-right:0.07847em;">X</span></span></span></span>');
        expect(mathRendering.mathAsHTML('<x> $X_0$ & $Y$ <z>')).toEqual(
            '&lt;x&gt; <span class="katex"><span class="katex-mathml"><math><semantics><mrow><msub><mi>X</mi><mn>0</mn></msub></mrow><annotation encoding="application/x-tex">X_0</annotation></semantics></math></span><span class="katex-html" aria-hidden="true"><span class="base"><span class="strut" style="height:0.83333em;vertical-align:-0.15em;"></span><span class="mord"><span class="mord mathdefault" style="margin-right:0.07847em;">X</span><span class="msupsub"><span class="vlist-t vlist-t2"><span class="vlist-r"><span class="vlist" style="height:0.30110799999999993em;"><span style="top:-2.5500000000000003em;margin-left:-0.07847em;margin-right:0.05em;"><span class="pstrut" style="height:2.7em;"></span><span class="sizing reset-size6 size3 mtight"><span class="mord mtight">0</span></span></span></span><span class="vlist-s">​</span></span><span class="vlist-r"><span class="vlist" style="height:0.15em;"><span></span></span></span></span></span></span></span></span></span> &amp; <span class="katex"><span class="katex-mathml"><math><semantics><mrow><mi>Y</mi></mrow><annotation encoding="application/x-tex">Y</annotation></semantics></math></span><span class="katex-html" aria-hidden="true"><span class="base"><span class="strut" style="height:0.68333em;vertical-align:0em;"></span><span class="mord mathdefault" style="margin-right:0.22222em;">Y</span></span></span></span> &lt;z&gt;');
    }));
});
