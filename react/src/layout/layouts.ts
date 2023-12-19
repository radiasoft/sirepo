import { FieldGridLayout, FieldListLayout, LayoutWithFormController } from "./form";
import { Graph2dFromApi } from "./report/graph2d";
import { HeatplotFromApi } from "./report/heatplot";
import { MissingLayout } from "./missing";
import { PanelLayout } from "./panel";
import { AutoRunReportLayout, ManualRunReportLayout, SimulationStartLayout } from "./report";
import { TabLayout } from "./tabs";
import { LayoutWithSpacing } from "./spaced";
import { MultiPanelLayout } from "./multipanel";
import { NavBarModalButton, NavTabsLayout } from "./navbar";
import { TableFromApi } from "./report/table";
import { LayoutWithDownloadButton } from "./download";
import { LayoutType, Layout } from "./layout";
import { SchemaLayout } from "../utility/schema";
import { TextLayout } from "./text";
import { HorizontalStackLayout, VerticalStackLayout } from "./arrange/stack";
import { ColumnLayout } from "./arrange/column";
import { WaterfallLayout } from "./arrange/waterfall";
import { Histogram2dFromApi } from "./report/histogram2d";
import { ShadowBeamlineWatchpointReports } from "./shadow/beamlineWatchpointReports";
import { ShadowBeamlineLayout } from "./shadow/beamline";
import { MadxAllBeamlineElementsLayout } from "./madx/allBeamlineElements";
import { MadxBeamlinesPickerLayout } from "./madx/beamlinesPicker";
import { MadxBeamlineElementsLayout } from "./madx/beamlineElements";
import { MadxBeamlineReportsLayout } from "./madx/beamlineReports";


// TODO rename to LayoutsWrapper
class LayoutWrapper {
    layouts: {[key:string]: LayoutType<unknown, unknown>} = {
        tabs: TabLayout,
        fieldList: LayoutWithSpacing(FieldListLayout),
        fieldTable: LayoutWithSpacing(FieldGridLayout),
        panel: LayoutWithFormController(PanelLayout),
        multiPanel: LayoutWithDownloadButton(MultiPanelLayout),
        navbarModalButton: LayoutWithFormController(NavBarModalButton),
        autoRunReport: AutoRunReportLayout,
        manualRunReport: ManualRunReportLayout,
        graph2d: LayoutWithDownloadButton(Graph2dFromApi),
        heatplot: LayoutWithDownloadButton(HeatplotFromApi),
        graph2dPlain: Graph2dFromApi,
        heatplotPlain: HeatplotFromApi,
        histogram2d: Histogram2dFromApi,
        navTabs: NavTabsLayout,
        table: TableFromApi,
        startSimulation: SimulationStartLayout,
        text: TextLayout,
        column: ColumnLayout,
        hStack: HorizontalStackLayout,
        vStack: VerticalStackLayout,
        waterfall: WaterfallLayout,
        shadowBeamlineWatchpointReports: ShadowBeamlineWatchpointReports,
        shadowBeamline: LayoutWithFormController(ShadowBeamlineLayout),
        madxAllBeamlineElements: LayoutWithFormController(MadxAllBeamlineElementsLayout),
        madxBeamlinesPicker: MadxBeamlinesPickerLayout,
        madxBeamlineElements: LayoutWithFormController(MadxBeamlineElementsLayout),
        madxBeamlineReports: MadxBeamlineReportsLayout
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

export function createLayouts<T>(obj: T, fieldName?: string): T & { layouts: Layout[] } {
    fieldName = fieldName || "items";
    let v = obj[fieldName];
    if(Array.isArray(v)) {
        v = v.map(x => LAYOUTS.getLayoutForSchema(x));
    } else {
        v = [LAYOUTS.getLayoutForSchema(v)];
    }
    return {
        ...obj,
        layouts: v
    }
}

export const LAYOUTS = new LayoutWrapper();
