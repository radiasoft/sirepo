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

export class TabLayout extends View<TabsConfig> {
    getFormDependencies = (config: TabsConfig) => {
        let fields = [];

        for (let tab of config.tabs) {
            for (let layoutConfig of tab.items) {
                let ele = this.layoutsWrapper.getLayoutForName(layoutConfig.layout);
                fields.push(...ele.getFormDependencies(layoutConfig, this.layoutsWrapper));
            }
        }

        return fields;
    }

    component = (props: LayoutProps<TabsConfig>) => {
        let { config } = props;

        let tabs = config.tabs;

        let tabEls = [];

        let firstTabKey = undefined;

        let modelsWrapper = useContext(CModelsWrapper);

        let shownFn = useShown;

        for (let tabConfig of tabs) {
            let { name, items: layoutConfigs, shown: shownConfig } = tabConfig;

            let shown = shownFn(shownConfig, true, modelsWrapper, ValueSelectors.Models);

            let layoutElements = layoutConfigs.map((layoutConfig, idx) => {
                let ele = this.layoutsWrapper.getLayoutForName(layoutConfig.layout)
                let LayoutElement = ele.component;
                return <LayoutElement key={idx} config={layoutConfig.config}></LayoutElement>
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
