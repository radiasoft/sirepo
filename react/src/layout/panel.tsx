import { useContext } from "react";
import { interpolate } from "../utility/string";
import { LayoutProps, Layout } from "./layout";
import { useDispatch, useStore } from "react-redux";
import { EditorPanel, EditorPanelProps } from "../component/reusable/panel";
import "./panel.scss";
import React from "react";
import { SchemaLayout } from "../utility/schema";
import { LAYOUTS } from "./layouts";
import { useShown } from "../hook/shown";
import { StoreTypes } from "../data/data";
import { CHandleFactory } from "../data/handle";
import { FormStateHandleFactory } from "../data/form";

export type PanelConfig = {
    basic: SchemaLayout[],
    advanced: SchemaLayout[],
    title: string,
    shown: string
}


export class PanelLayout extends Layout<PanelConfig, {}> {
    basic?: Layout[];
    advanced?: Layout[];

    constructor(config: PanelConfig) {
        super(config);
        this.basic = (!!config.basic) ? config.basic.map(LAYOUTS.getLayoutForSchema) : undefined;
        this.advanced = (!!config.advanced) ? config.advanced.map(LAYOUTS.getLayoutForSchema) : undefined;
    }

    component = (props: LayoutProps<{}>) => {
        let formHandleFactory = useContext(CHandleFactory) as FormStateHandleFactory;
        formHandleFactory.useUpdates(PanelLayout);

        let shown = useShown(this.config.shown, true, StoreTypes.Models);

        let store = useStore();
        let dispatch = useDispatch();

        let title = interpolate(this.config.title).withDependencies(formHandleFactory, StoreTypes.Models).raw();

        let mapLayoutsToComponents = (views: Layout[]) => views.map((child, idx) => {
            let LayoutComponent = child.component;
            return <LayoutComponent key={idx}></LayoutComponent>;
        });

        let mainChildren = (!!this.basic) ? mapLayoutsToComponents(this.basic) : undefined;
        let modalChildren = (!!this.advanced) ? mapLayoutsToComponents(this.advanced) : undefined;

        let formProps: EditorPanelProps = {
            submit: (() => formHandleFactory.save(store.getState(), dispatch)),
            cancel: (() => formHandleFactory.cancel(store.getState(), dispatch)),
            showButtons: formHandleFactory.isDirty(),
            formValid: formHandleFactory.isValid(store.getState()),
            mainChildren,
            modalChildren,
            title: title || this.name,
            id: this.name
        }

        return (
            <>
                {
                    shown && <EditorPanel {...formProps}/>
                }
            </>
            
        )
    }
}
