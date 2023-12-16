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
    },
    padding: string
}

export class WaterfallLayout extends Layout<WaterfallConfig, {}> {
    children: Layout[];

    constructor(config: WaterfallConfig) {
        super(config);
        this.children = (config.items || []).map(schemaLayout => {
            return LAYOUTS.getLayoutForSchema(schemaLayout);
        });
    }

    formatValue = (v: number | string) => {
        if(typeof(v) === 'number') {
            return `${v}px`;
        }
        return v;
    }

    numColumnsForBreakpoint(breakpoint: Breakpoint) {
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

    component: FunctionComponent<{ [key: string]: any; }> = (props: LayoutProps<{}>) => {
        let c: JSX.Element[] = this.children.map((c, idx) => {
            let LayoutComponent = c.component;
            return <LayoutComponent key={idx}/>
        });

        let windowSize = useWindowSize();
        let breakpoint = resolveBreakpoint(windowSize);
        let numColumns = this.numColumnsForBreakpoint(breakpoint);

        let containerRef = useRef<HTMLDivElement>();

        let fixupStyles = () => {
            if(containerRef.current) {
                let children = [...containerRef.current.children];
                children.map(c => c as HTMLElement).forEach(c => {
                    c.style.width = "100%";
                    c.style.padding = "0";
                    c.style.marginBottom = this.formatValue(this.config.gutters.vertical);
                    c.style.boxSizing = "border-box";
                    c.style.breakInside = "avoid";
                })
            }  
        }

        useEffect(() => {
            if(containerRef.current) {
                fixupStyles();
                let observer = new MutationObserver((mutations) => {
                    fixupStyles();
                })
                observer.observe(containerRef.current, { childList: true });
                return () => observer.disconnect();
            }
            return () => {}
        })

        return (
            <>
                <div style={{
                    listStyle: "none",
                    columnGap: this.formatValue(this.config.gutters.horizontal),
                    padding: this.formatValue(this.config.padding),
                    columnCount: `${numColumns}`
                }} ref={containerRef}>
                    {c}
                </div>
            </>
        )
    };
}
