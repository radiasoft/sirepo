import React from "react";
import { FunctionComponent, useContext } from "react";
import { ArrayAliases, HandleFactoryWithArrayAliases } from "../../data/alias";
import { CSchema } from "../../data/appwrapper";
import { StoreTypes } from "../../data/data";
import { Dependency } from "../../data/dependency";
import { CHandleFactory } from "../../data/handle";
import { ArrayFieldState } from "../../store/common";
import { ModelState } from "../../store/models";
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
        let handleFactory = useContext(CHandleFactory);
        let reportsHandle = handleFactory.createHandle(watchpointReportsDependency, StoreTypes.Models).hook();
        let elementsHandle = handleFactory.createHandle(beamlineDependency, StoreTypes.Models).hook();
        let reportsValue = reportsHandle.value as ArrayFieldState<ModelState>;
        let elementsValue = elementsHandle.value as ArrayFieldState<ModelState>;
        let schema = useContext(CSchema);

        let findElementById = (id: any) => elementsValue.find(e => e.item.id == id);

        let reportElements = reportsValue.map((report, index) => {
            let id = report.item.id;
            let ele = findElementById(id);
            let position = ele.item.position;
            let cfg = createPanelConfig(`watchpointReport${index}`, `Intensity Report, ${position}`);
            return {
                id: id,
                layout: LAYOUTS.getLayoutForSchema(cfg)
            }
        }).map((e, index) => {
            let aliases: ArrayAliases = [
                {
                    realDataLocation: {
                        modelName: watchpointReportsDependency.modelName,
                        fieldName: watchpointReportsDependency.fieldName,
                        index
                    },
                    realSchemaName: "watchpointReport",
                    fake: "watchpointReport"
                }
            ];
            let aliasedHandleFactory = new HandleFactoryWithArrayAliases(schema, aliases, handleFactory);
            let Comp = e.layout.component;
            return (
                <React.Fragment key={e.id as any}>
                    <CHandleFactory.Provider value={aliasedHandleFactory}>
                        <Comp></Comp>
                    </CHandleFactory.Provider>
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
