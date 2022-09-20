import { FieldGridLayout, FieldListLayout, LayoutWithFormController } from "./form";
import { Graph2dFromApi } from "./graph2d";
import { MissingLayout } from "./missing";
import { PanelLayout } from "./panel";
import { AutoRunReportLayout } from "./report";
import { TabLayout } from "./tabs";
import { LayoutWithSpacing } from "./spaced";
import { NavTabsLayout } from "./navbar";

export class Layouts {
    constructor () { 
        this.components = {
            tabs: new TabLayout(this),
            fieldList: new (LayoutWithSpacing(FieldListLayout))(this),
            fieldTable: new (LayoutWithSpacing(FieldGridLayout))(this),
            panel: new (LayoutWithFormController(PanelLayout))(this),
            autoRunReport: new AutoRunReportLayout(this),
            graph2d: new Graph2dFromApi(this),
            navTabs: new NavTabsLayout(this)
        }
    }

    getLayoutForConfig = (config) => {
        if(!config.layout) {
            throw new Error(`layout not present in config: ${JSON.stringify(config)}`);
        }

        let layout = this.components[config.layout];

        if(!layout) {
            console.error("missing layout definition for view: " + config.layout)
            return new MissingLayout();
        }

        return layout;
    }
}
