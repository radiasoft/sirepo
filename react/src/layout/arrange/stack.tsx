import React from "react";
import { FunctionComponent } from "react";
import { FlexAlign, FlexJustify, FlexWrap, HorizontalStack, VerticalStack } from "../../component/reusable/stack";
import { Dependency } from "../../data/dependency";
import { SchemaLayout } from "../../utility/schema";
import { Layout, LayoutProps } from "../layout";
import { LAYOUTS } from "../layouts";
import "./stack.scss";

export type StackConfig = {
    items: SchemaLayout[],
    justifyContent?: FlexJustify,
    alignItems?: FlexAlign,
    wrap?: FlexWrap
}

export abstract class BaseStack<C extends StackConfig> extends Layout<C, {}> {
    children: Layout[];
    
    constructor(config: C) {
        super(config);
        this.children = (config.items || []).map(schemaLayout => {
            return LAYOUTS.getLayoutForSchema(schemaLayout);
        });
        
    }
} 


export type VerticalStackConfig = StackConfig;

export class VerticalStackLayout extends BaseStack<VerticalStackConfig> {
    component: FunctionComponent<{ [key: string]: any; }> = (props: LayoutProps<{}>) => {
        return (
            <VerticalStack {...this.config}>
                {
                    this.children.map((c, idx) => {
                        let LayoutElement = c.component;
                        return (
                            <LayoutElement key={idx}/>
                        )
                    })
                }
            </VerticalStack>
        )
    };
}

export type HorizontalStackConfig = StackConfig;

export class HorizontalStackLayout extends BaseStack<HorizontalStackConfig> {
    component: FunctionComponent<{ [key: string]: any; }> = (props: LayoutProps<{}>) => {
        return (
            <HorizontalStack {...this.config}>
                {
                    this.children.map((c, idx) => {
                        let LayoutElement = c.component;
                        return (
                            <LayoutElement key={idx}/>
                        )
                    })
                }
            </HorizontalStack>
        )
    };
}
