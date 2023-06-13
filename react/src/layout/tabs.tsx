import { LayoutProps, Layout } from "./layout";
import { Tab, Tabs } from "react-bootstrap";
import { useShown } from "../hook/shown";
import React from "react";
import { SchemaLayout } from "../utility/schema";
import { LAYOUTS } from "./layouts";
import { StoreTypes } from "../data/data";

export type TabConfig = {
    items: SchemaLayout[],
    name: string,
    shown: string
}

export type TabsConfig = {
    tabs: TabConfig[]
}

export type TabConfigWithLayouts = {
    layouts: Layout[]
} & TabConfig

export class TabLayout extends Layout<TabsConfig, {}> {
    tabs: TabConfigWithLayouts[];

    constructor(config: TabsConfig) {
        super(config);

        this.tabs = config.tabs.map(tab => {
            return {
                ...tab,
                layouts: tab.items.map(LAYOUTS.getLayoutForSchema)
            }
        })
    }

    component = (props: LayoutProps<{}>) => {

        let tabEls = [];

        let firstTabKey = undefined;

        for (let tabConfig of this.tabs) {
            let { name, shown: shownConfig, layouts } = tabConfig;

            let shown = useShown(shownConfig, true, StoreTypes.Models);

            let layoutElements = layouts.map((layout, idx) => {
                let LayoutElement = layout.component;
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
            <Tabs className="mb-3" defaultActiveKey={firstTabKey}>
                {tabEls}
            </Tabs>
        )
    }
}
