import { FieldGridLayout, FieldListLayout, LayoutWithFormController } from "./form";
import { Graph2dFromApi } from "./graph2d";
import { HeatplotFromApi } from "./heatplot";
import { MissingLayout } from "./missing";
import { PanelLayout } from "./panel";
import { AutoRunReportLayout, ManualRunReportLayout, SimulationStartLayout } from "./report";
import { TabLayout } from "./tabs";
import { LayoutWithSpacing } from "./spaced";
import { NavBarModalButton, NavTabsLayout } from "./navbar";
import { TableFromApi } from "./table";
import { LayoutWithDownloadButton } from "./download";

export class Layouts {
    constructor () {
        this.components = {
            tabs: new TabLayout(this),
            fieldList: new (LayoutWithSpacing(FieldListLayout))(this),
            fieldTable: new (LayoutWithSpacing(FieldGridLayout))(this),
            panel: new (LayoutWithFormController(PanelLayout))(this),
            navbarModalButton: new (LayoutWithFormController(NavBarModalButton))(this),
            autoRunReport: new AutoRunReportLayout(this),
            manualRunReport: new ManualRunReportLayout(this),
            graph2d: new (LayoutWithDownloadButton(Graph2dFromApi))(this),
            heatplot: new (LayoutWithDownloadButton(HeatplotFromApi))(this),
            navTabs: new NavTabsLayout(this),
            table: new TableFromApi(this),
            startSimulation: new SimulationStartLayout(this)
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
