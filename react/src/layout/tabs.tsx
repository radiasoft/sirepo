import { useContext } from "react";
import { LayoutProps, View } from "./layout";
import { Tab, Tabs } from "react-bootstrap";
import { useShown } from "../hook/shown";
import React from "react";
import { CModelsWrapper } from "../data/wrapper";
import { ValueSelectors } from "../hook/string";
import { SchemaView } from "../utility/schema";

export type TabConfig = {
    items: SchemaView[],
    name: string,
    shown: string
}

export type TabsConfig = {
    tabs: TabConfig[]
}

export class TabLayout extends View<TabsConfig, {}> {
    getFormDependencies = (config: TabsConfig) => {
        let fields = [];

        for (let tab of config.tabs) {
            for (let schemaView of tab.items) {
                let ele = this.layoutsWrapper.getLayoutForName(schemaView.layout);
                fields.push(...ele.getFormDependencies(schemaView.config));
            }
        }

        return fields;
    }

    component = (props: LayoutProps<TabsConfig, {}>) => {
        let { config } = props;

        let tabs = config.tabs;

        let tabEls = [];

        let firstTabKey = undefined;

        let modelsWrapper = useContext(CModelsWrapper);

        let shownFn = useShown;

        for (let tabConfig of tabs) {
            let { name, items: schemaViews, shown: shownConfig } = tabConfig;

            let shown = shownFn(shownConfig, true, modelsWrapper, ValueSelectors.Models);

            let layoutElements = schemaViews.map((schemaView, idx) => {
                let ele = this.layoutsWrapper.getLayoutForName(schemaView.layout)
                let LayoutElement = ele.component;
                return <LayoutElement key={idx} config={schemaView.config}></LayoutElement>
            })
            firstTabKey = firstTabKey || name;
            tabEls.push(
                <Tab className={!shown ? 'd-none' : undefined} key={name} eventKey={name} title={name}>
                    {layoutElements}
                </Tab>
            )
        }

        return (
            <Tabs defaultActiveKey={firstTabKey}>
                {tabEls}
            </Tabs>
        )
    }
}
