import { FieldGridLayout, FieldListLayout, LayoutWithFormController } from "./form";
import { Graph2dFromApi } from "./report/graph2d";
import { HeatplotFromApi } from "./report/heatplot";
import { MissingLayout } from "./missing";
import { PanelLayout } from "./panel";
import { AutoRunReportLayout, ManualRunReportLayout, SimulationStartLayout } from "./report";
import { TabLayout } from "./tabs";
import { LayoutWithSpacing } from "./spaced";
import { NavBarModalButton, NavTabsLayout } from "./navbar";
import { TableFromApi } from "./report/table";
import { LayoutWithDownloadButton } from "./download";
import { LayoutType, Layout } from "./layout";
import { SchemaLayout } from "../utility/schema";
import { TextLayout } from "./text";
import { ColumnBreakLayout } from "./columnbreak";
import { HorizontalStackLayout, VerticalStackLayout } from "./arrange/stack";
import { WaterfallLayout } from "./arrange/waterfall";


// TODO rename to LayoutsWrapper
class LayoutWrapper {
    layouts: {[key:string]: LayoutType<unknown, unknown>} = {
        tabs: TabLayout,
        fieldList: LayoutWithSpacing(FieldListLayout),
        fieldTable: LayoutWithSpacing(FieldGridLayout),
        panel: LayoutWithFormController(PanelLayout),
        navbarModalButton: LayoutWithFormController(NavBarModalButton),
        autoRunReport: AutoRunReportLayout,
        manualRunReport: ManualRunReportLayout,
        graph2d: LayoutWithDownloadButton(Graph2dFromApi),
        heatplot: LayoutWithDownloadButton(HeatplotFromApi),
        navTabs: NavTabsLayout,
        table: TableFromApi,
        startSimulation: SimulationStartLayout,
        text: TextLayout,
        columnBreak: ColumnBreakLayout,
        hStack: HorizontalStackLayout,
        vStack: VerticalStackLayout,
        waterfall: WaterfallLayout
    }

    constructor () {

    }

    getLayoutTypeForName = <C, P>(layoutName: string): LayoutType<C, P> => {
        let layout = this.layouts[layoutName];

        if(!layout) {
            console.error("missing layout definition for name: " + layoutName)
            return MissingLayout;
        }

        return layout as LayoutType<C, P>;
    }

    getLayoutForSchema = <C, P>(schemaLayout: SchemaLayout): Layout<C, P> => {
        let layout = this.getLayoutTypeForName(schemaLayout.layout) as LayoutType<C, P>;
        return new layout(schemaLayout.config);
    }
}

export const LAYOUTS = new LayoutWrapper();
