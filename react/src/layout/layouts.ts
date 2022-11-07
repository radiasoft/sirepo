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
import React from "react";
import { SchemaView } from "../utility/schema";

export const CLayouts = React.createContext<LayoutWrapper>(undefined);

// TODO rename to LayoutsWrapper
export class LayoutWrapper {
    layouts = {
        tabs: new TabLayout(),
        fieldList: new (LayoutWithSpacing(FieldListLayout))(this),
        fieldTable: new (LayoutWithSpacing(FieldGridLayout))(this),
        panel: new (LayoutWithFormController(PanelLayout))(),
        navbarModalButton: new (LayoutWithFormController(NavBarModalButton))(),
        autoRunReport: new AutoRunReportLayout(),
        manualRunReport: new ManualRunReportLayout(),
        graph2d: new (LayoutWithDownloadButton(Graph2dFromApi))(),
        heatplot: new (LayoutWithDownloadButton(HeatplotFromApi))(),
        navTabs: new NavTabsLayout(),
        table: new TableFromApi(),
        startSimulation: new SimulationStartLayout()
    }

    constructor () {
        
    }

    getLayoutForName = (layoutName: string) => {
        let layout = this.layouts[layoutName];

        if(!layout) {
            console.error("missing layout definition for view: " + layoutName)
            return new MissingLayout();
        }

        return layout;
    }
}
