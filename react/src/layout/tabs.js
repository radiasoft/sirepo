import { useContext } from "react";
import { View } from "./layout";
import { Tab, Tabs } from "react-bootstrap";
import { useShown } from "../hook/shown";
import React from "react";
import { CModelsWrapper } from "../data/wrapper";
import { ValueSelectors } from "../hook/string";

export class TabLayout extends View {
    getFormDependencies = (config) => {
        let fields = [];

        for (let tab of config.tabs) {
            for (let layoutConfig of tab.items) {
                let ele = this.layoutsWrapper.getLayoutForName(layoutConfig.layout);
                fields.push(...ele.getFormDependencies(layoutConfig, this.layoutsWrapper));
            }
        }

        return fields;
    }

    component = (props) => {
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
