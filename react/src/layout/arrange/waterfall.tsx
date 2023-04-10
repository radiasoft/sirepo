import { FunctionComponent, MutableRefObject, RefObject, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Dependency } from "../../data/dependency";
import { SchemaLayout } from "../../utility/schema";
import { Layout, LayoutProps } from "../layout";
import { LAYOUTS } from "../layouts";
import React from "react";
import { Breakpoint, resolveBreakpoint, useWindowSize } from "../../hook/breakpoint";
import "./waterfall.scss";


export type WaterfallConfig = {
    items: SchemaLayout[],
    breakpoints?: {[breakpointName: string]: number},
    gutters?: {
        vertical?: string | number,
        horizontal?: string | number
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
    
    getMarginStyles = (): string => {
        if(!this.config.gutters) {
            return "";
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
            ret['margin-left'] = h;
            ret['margin-right'] = h;
        }
        if(this.config.gutters.vertical) {
            let v = formatValue(this.config.gutters.vertical);
            ret['margin-top'] = v;
            ret['margin-bottom'] = v;
        }

        return Object.entries(ret).map(([name, value]) => `${name}: ${value}`).join("; ")
    }

    waterfallBins = (props: { children: React.ReactNode }) => {
        let windowSize = useWindowSize();
        let breakpoint = resolveBreakpoint(windowSize);
        let numBins = this.numBinsForBreakpoint(breakpoint);

        let bins: JSX.Element[] = [];
        for(let b = 0; b < numBins; b++) {
            bins.push(<div key={b}>

            </div>)
        }

        let gridStyle = {
            "gridTemplateColumns": bins.map(() => `${(100/bins.length).toFixed(2)}%`).join(" "),
            "gridTemplateRows": "1fr"
        }

        useEffect(() => {
            if(!containerRef.current) {
                return () => {};
            }

            if(!waterfallRef.current) {
                return () => {};
            }

            let binEles = Array.from(waterfallRef.current.children);

            let container = containerRef.current;
            // needs to be done this way, avoids mutating length during for loop
            let children = Array.from(container.children);
            let cleanups = [];
            children.forEach((e, i) => {
                let b = binEles[i % binEles.length];
                b.appendChild(e);
                e.setAttribute("style", this.getMarginStyles())
                cleanups.push(() => {
                    container.appendChild(e);
                })
            })

            return () => cleanups.forEach(c => c())
        }, [bins.length])

        let waterfallRef = useRef<HTMLDivElement>();
        let containerRef = useRef<HTMLDivElement>();

        return (
            <>
                <div style={gridStyle} ref={waterfallRef} className="sr-waterfall-container">
                    {bins}
                </div>
                <div style={{display: "none"}} ref={containerRef}>
                    {props.children}
                </div>
            </>
        )
    }

    component: FunctionComponent<{ [key: string]: any; }> = (props: LayoutProps<{}>) => {
        
        let c: JSX.Element[] = this.children.map((c, idx) => {
            let LayoutComponent = c.component;
            return <LayoutComponent key={idx}/>
        });
        

        let WaterfallBins = this.waterfallBins;

        return (
            <WaterfallBins>{c}</WaterfallBins>
        )
    };
}
