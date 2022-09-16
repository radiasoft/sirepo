export class TabLayout extends View {
    getFormDependencies = (config) => {
        let fields = [];

        for (let tab of config.tabs) {
            for (let layoutConfig of tab.items) {
                let ele = elementForLayoutName(layoutConfig.layout);
                fields.push(...ele.getDependencies(layoutConfig));
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
            let layouts = tabConfig.items;
            let layoutElements = layouts.map((layoutConfig, idx) => {
                let ele = elementForLayoutName(layoutConfig.layout)
                let LayoutElement = ele.element;
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
