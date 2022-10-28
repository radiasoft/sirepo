import { ContextLayouts } from "../context";
import { useContext } from "react";
import { View } from "./layout";
import { Tab, Tabs } from "react-bootstrap";

export class TabLayout extends View {
    getFormDependencies = (config) => {
        let fields = [];

        for (let tab of config.tabs) {
            for (let layoutConfig of tab.items) {
                let ele = this.layoutsWrapper.getLayoutForConfig(layoutConfig);
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

        for (let tabConfig of tabs) {
            let name = tabConfig.name;
            let layoutConfigs = tabConfig.items;
            let layoutElements = layoutConfigs.map((layoutConfig, idx) => {
                let ele = this.layoutsWrapper.getLayoutForConfig(layoutConfig)
                let LayoutElement = ele.component;
                return <LayoutElement key={idx} config={layoutConfig}></LayoutElement>
            })
            firstTabKey = firstTabKey || name;
            tabEls.push(
                <Tab key={name} eventKey={name} title={name}>
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
