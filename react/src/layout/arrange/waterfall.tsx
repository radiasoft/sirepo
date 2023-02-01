import { FunctionComponent, useRef, useState } from "react";
import { Dependency } from "../../data/dependency";
import { SchemaLayout } from "../../utility/schema";
import { Layout, LayoutProps } from "../layout";
import { LAYOUTS } from "../layouts";
import { Dimension, useRefSize } from "../../utility/component";
import React from "react";
import { Breakpoint, resolveBreakpoint, useWindowSize } from "../../hook/breakpoint";
import { VerticalStack } from "../../component/reusable/stack";
import "./waterfall.scss";
import { debounce } from "../../utility/debounce";


export type WaterfallConfig = {
    items: SchemaLayout[],
    breakpoints?: {[breakpointName: string]: number},
    gutters?: {
        vertical?: string | number,
        horizontal?: string | number
    }
}

export type WaterfallRef = {
    element: JSX.Element,
    dimension: Dimension,
    ref: React.RefObject<HTMLElement>
}

type WaterfallBin = {
    calculatedSize: number,
    items: WaterfallRef[];
}

class WaterfallController {
    private refs: WaterfallRef[];
    private breakpoint: Breakpoint;
    private windowSize: number;
    private waterfallBins: WaterfallBin[];
    private hasAllSizes: boolean = false;

    constructor(private config: WaterfallConfig) {}

    assignViewsToBinsSerial = () => {
        this.refs.forEach((r, idx) => {
            let bi = idx % this.waterfallBins.length;
            this.waterfallBins[bi].items.push(r);
        })
    }

    windowSizeUpdateCallback = debounce((s: number) => {
        this.windowSize = s;
        this.assignViewsToBins();
    }, 250)

    assignViewsToBins = () => {
        this.waterfallBins.forEach(bin => bin.items = []);

        if(!this.hasAllSizes) {
            this.assignViewsToBinsSerial();
            return;
        }

        let findSmallestBinSmallerThan = (s: number) => {
            return this.waterfallBins.filter(b => b.calculatedSize < s).reduce((prev, cur) => {
                if(!prev) {
                    return cur;
                }
                if(cur.calculatedSize < prev.calculatedSize) {
                    return cur;
                }
                return prev;
            }, undefined);
        }
        
        for(let ri = 0; ri < this.refs.length; ri++) {
            let ref = this.refs[ri];
            let s = ref.dimension.height;
            let bin = this.waterfallBins[ri % this.waterfallBins.length];
            //let betterBin = findSmallestBinSmallerThan(bin.calculatedSize - s); // TODO: this resizing works but it appears buggy to the user, need better algorithm
            //bin = betterBin || bin;
            bin.items.push(ref);
            bin.calculatedSize += s;
        }
    }

    numBinsForBreakpoint(breakpoint: Breakpoint) {
        let bins = 1; // TODO: place default somewhere
        if(!this.config.breakpoints) {
            //return bins;
            return bins;
        }

        let k = ['xs', 'sm', 'md', 'lg', 'xl', 'xxl'];
        if(!k.includes(breakpoint)) {
            throw new Error(`unknown window breakpoint=${breakpoint}`)
        }
        for(let i = 0; i < k.indexOf(breakpoint); i++) {
            if(Object.keys(this.config.breakpoints).includes(k[i])) {
                bins = this.config.breakpoints[k[i]];
            }
        }

        return bins;
    }

    createBins = (n: number) => {
        this.waterfallBins = [];
        for(let i = 0; i < n; i++) {
            this.waterfallBins.push({
                calculatedSize: 0,
                items: []
            });
        }
    }

    updateRefs = (refs: WaterfallRef[], windowSize: number) => {
        let breakpoint = resolveBreakpoint(windowSize);
        let hasAllSizes = !refs.map(ref => !!ref.dimension).includes(false);
        this.refs = refs;
        //this.refs = refs;

        if(this.breakpoint !== breakpoint) {
            // redo bins
            this.createBins(this.numBinsForBreakpoint(breakpoint));
            // redo assignment
            this.assignViewsToBins();
        } else {
            
            // if gained completeness, redo assignment
            if(!this.hasAllSizes && hasAllSizes) {
                this.hasAllSizes = hasAllSizes;
                this.assignViewsToBins();
            }
            // if changed window size, redo assignment
            if(this.windowSize !== windowSize) {
                this.windowSizeUpdateCallback(windowSize);
            }
        }
        
        this.breakpoint = breakpoint;
        this.windowSize = windowSize;

        return this.waterfallBins;
    }
}

export class WaterfallLayout extends Layout<WaterfallConfig, {}> {
    children: Layout[];

    constructor(config: WaterfallConfig) {
        super(config);
        this.children = (config.items || []).map(schemaLayout => {
            return LAYOUTS.getLayoutForSchema(schemaLayout);
        });
    }


    getFormDependencies(): Dependency[] {
        return (this.children || []).flatMap(c => c.getFormDependencies());
    }
    
    getMarginStyles = (): {[key: string]: string} => {
        if(!this.config.gutters) {
            return {};
        }

        let formatValue = (v: number | string) => {
            if(typeof(v) === 'number') {
                return `${v}px`;
            }
            return v;
        }

        let ret = {};
        if(this.config.gutters.horizontal) {
            let h = formatValue(this.config.gutters.horizontal);
            ret['marginLeft'] = h;
            ret['marginRight'] = h;
        }
        if(this.config.gutters.vertical) {
            let v = formatValue(this.config.gutters.vertical);
            ret['marginTop'] = v;
            ret['marginBottom'] = v;
        }

        return ret;
    }

    component: FunctionComponent<{ [key: string]: any; }> = (props: LayoutProps<{}>) => {

        let windowSize = useWindowSize();
        let c: WaterfallRef[] = this.children.map((c, idx) => {
            let componentRef = useRef<HTMLDivElement>()
            let [dim,] = useRefSize(componentRef);
            let LayoutComponent = c.component;
            return {
                element: (
                    <div ref={componentRef} key={idx} style={this.getMarginStyles()}>
                        <LayoutComponent/>
                    </div>
                ),
                dimension: dim,
                ref: componentRef
            }
        });

        let [controller, ] = useState<WaterfallController>(() => new WaterfallController(this.config));
        let bins = controller.updateRefs(c, windowSize);

        let eles = bins.map((bin, idx) => {
            return (
                <VerticalStack key={`${bins.length} / ${idx}`}>
                    {bin.items.map(item => item.element)}
                </VerticalStack>
            )
        })

        let gridStyle = {
            "gridTemplateColumns": bins.map(() => `${(100/bins.length).toFixed(2)}%`).join(" "),
            "gridTemplateRows": "1fr"
        }

        return (
            <div style={gridStyle} className="sr-waterfall-container">
                {eles}
            </div>
        )
    };
}
