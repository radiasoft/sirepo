import { FieldGridLayout, FieldListLayout } from "./form";
import { Graph2dFromApi } from "./graph2d";
import { MissingLayout } from "./missing";
import { PanelLayout } from "./panel";
import { AutoRunReportLayout } from "./report";
import { TabLayout } from "./tabs";
import { SpacedLayout } from "./utility";

let SpacedFieldListLayout = SpacedLayout(FieldListLayout);
let SpacedFieldGridLayout = SpacedLayout(FieldGridLayout);

export class Layouts {
    constructor () { 
        this.components = {
            tabs: new TabLayout(),
            fieldList: new SpacedFieldListLayout(),
            fieldTable: new SpacedFieldGridLayout(),
            panel: new PanelLayout(),
            autoRunReport: new AutoRunReportLayout(),
            graph2d: new Graph2dFromApi()
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
