import { useContext } from "react";
import { LayoutProps, View } from "./layout";
import { Tab, Tabs } from "react-bootstrap";
import { useShown } from "../hook/shown";
import React from "react";
import { CModelsWrapper } from "../data/wrapper";
import { ValueSelectors } from "../hook/string";
import { SchemaView } from "../utility/schema";
import { LAYOUTS } from "./layouts";

export type TabConfig = {
    items: SchemaView[],
    name: string,
    shown: string
}

export type TabsConfig = {
    tabs: TabConfig[]
}

export class TabLayout extends View<TabsConfig, {}> {
    getFormDependencies = () => {
        let fields = [];

        for (let tab of this.config.tabs) {
            for (let schemaView of tab.items) {
                fields.push(...LAYOUTS.getLayoutForSchemaView(schemaView).getFormDependencies());
            }
        }

        return fields;
    }

    component = (props: LayoutProps<{}>) => {
        let tabs = this.config.tabs;

        let tabEls = [];

        let firstTabKey = undefined;

        let modelsWrapper = useContext(CModelsWrapper);

        for (let tabConfig of tabs) {
            let { name, items: schemaViews, shown: shownConfig } = tabConfig;

            let shown = useShown(shownConfig, true, modelsWrapper, ValueSelectors.Models);

            let layoutElements = schemaViews.map((schemaView, idx) => {
                let ele = LAYOUTS.getLayoutForSchemaView(schemaView)
                let LayoutElement = ele.component;
                return <LayoutElement key={idx}></LayoutElement>
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
