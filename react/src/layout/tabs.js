import { ContextLayouts } from "../context";
import { useContext } from "react";
import { View } from "./layout";
import { Tab, Tabs } from "react-bootstrap";

export class TabLayout extends View {
    getFormDependencies = (config, layouts) => {
        let fields = [];

        for (let tab of config.tabs) {
            for (let layoutConfig of tab.items) {
                let ele = layouts.getLayoutForConfig(layoutConfig);
                fields.push(...ele.getFormDependencies(layoutConfig, layouts));
            }
        }

        return fields;
    }

    component = (props) => {
        let { config } = props;

        let tabs = config.tabs;

        let layouts = useContext(ContextLayouts);

        let tabEls = [];

        let firstTabKey = undefined;

        for (let tabConfig of tabs) {
            let name = tabConfig.name;
            let layoutConfigs = tabConfig.items;
            let layoutElements = layoutConfigs.map((layoutConfig, idx) => {
                let ele = layouts.getLayoutForConfig(layoutConfig)
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
