import React from "react";
import { FunctionComponent, useContext } from "react";
import { ModelsAccessor } from "../../data/accessor";
import { Dependency } from "../../data/dependency";
import { CFormStateWrapper } from "../../data/wrapper";
import { FormModelState } from "../../store/formState";
import { SchemaLayout } from "../../utility/schema";
import { AliasedFormControllerWrapper, FormControllerAliases } from "../form";
import { ArrayField } from "../input/array";
import { Layout } from "../layout";
import { LAYOUTS } from "../layouts";

export type BeamlineWatchpointReportsConfig = {
    beamlineDependency: string,
    watchpointReportsDependency: string
}

export class BeamlineWatchpointReports extends Layout<BeamlineWatchpointReportsConfig, {}> {
    component: FunctionComponent<{ [key: string]: any; }> = (props) => {
        let watchpointReportsDependency = new Dependency(this.config.watchpointReportsDependency);
        let beamlineDependency = new Dependency(this.config.beamlineDependency);
        let formStateWrapper = useContext(CFormStateWrapper);
        let accessor = new ModelsAccessor(formStateWrapper, [watchpointReportsDependency, beamlineDependency]);
        let reportsValue: ArrayField<FormModelState> = accessor.getFieldValue(watchpointReportsDependency) as any as ArrayField<FormModelState>;
        let elementsValue: ArrayField<FormModelState> = accessor.getFieldValue(beamlineDependency) as any as ArrayField<FormModelState>;

        let findElementById = (id: number) => elementsValue.find(e => e.item.id.value === id);

        let reportElements = (reportsValue as any[]).map((report, index) => {
            let id = report.item.id.value;
            let ele = findElementById(id);
            let position = ele.item.position.value;
            let cfg = createPanelConfig(`watchpointReport${index}`, `Intensity Report, ${position}`);
            return {
                id: id,
                layout: LAYOUTS.getLayoutForSchema(cfg)
            }
        }).map((e, index) => {
            let aliases: FormControllerAliases = [
                {
                    real: {
                        modelName: watchpointReportsDependency.modelName,
                        fieldName: watchpointReportsDependency.fieldName,
                        index
                    },
                    fake: "watchpointReport",
                    realSchemaName: "watchpointReport"
                }
            ];
            let Comp = e.layout.component;
            return (
                <React.Fragment key={e.id}>
                    <AliasedFormControllerWrapper aliases={aliases}>
                        <Comp></Comp>
                    </AliasedFormControllerWrapper>
                </React.Fragment>
            )
        })

        return (<>{
            reportElements
        }</>);
    };
}

function createPanelConfig(reportName: string, title: string) {
    return {
        "layout": "panel",
        "config": {
            "title": title,
            "basic": [
                {
                    "layout": "autoRunReport",
                    "config": {
                        "report": reportName,
                        "dependencies": [
                            "beamline.*",
                            "bendingMagnet.*",
                            "electronBeam.*",
                            "geometricSource.*",
                            "rayFilter.*",
                            "simulation.*",
                            "sourceDivergence.*",
                            "undulator.*",
                            "undulatorBeam.*",
                            "wiggler.*",
                            "initialIntensityReport.*"
                        ],
                        "reportLayout": {
                            "layout": "heatplot"
                        }
                    }
                }
            ],
            "advanced": [
                {
                    "layout": "fieldTable",
                    "config": {
                        "columns": [
                            "Horizontal Axis",
                            "Vertical Axis"
                        ],
                        "rows": [
                            {
                                "label": "Value to Plot",
                                "fields": [
                                    "watchpointReport.x",
                                    "watchpointReport.y"
                                ]
                            }
                        ]
                    }
                },
                {
                    "layout": "fieldList",
                    "config": {
                        "fields": [
                            "watchpointReport.weight",
                            "watchpointReport.histogramBins",
                            "watchpointReport.overrideSize"
                        ]
                    }
                },
                {
                    "layout": "fieldTable",
                    "config": {
                        "columns": [
                            "Horizontal Axis",
                            "Vertical Axis"
                        ],
                        "rows": [
                            {
                                "label": "Horizontal Size [mm]",
                                "fields": [
                                    "watchpointReport.horizontalSize",
                                    "watchpointReport.verticalSize"
                                ]
                            },
                            {
                                "label": "Horizontal Offset [mm]",
                                "fields": [
                                    "watchpointReport.horizontalOffset",
                                    "watchpointReport.verticalOffset"
                                ]
                            }
                        ]
                    }
                },
                {
                    "layout": "fieldList",
                    "config": {
                        "fields": [
                            "watchpointReport.aspectRatio",
                            "watchpointReport.colorMap",
                            "watchpointReport.notes"
                        ]
                    }
                }
            ]
        }
    }
}
