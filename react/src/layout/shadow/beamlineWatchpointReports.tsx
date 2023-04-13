import React, { RefObject, useRef } from "react";
import { FunctionComponent, useContext, useState } from "react";
import { ArrayAliases, HandleFactoryWithArrayAliases } from "../../data/alias";
import { CSchema } from "../../data/appwrapper";
import { StoreTypes } from "../../data/data";
import { Dependency } from "../../data/dependency";
import { FormStateHandleFactory } from "../../data/form";
import { CHandleFactory } from "../../data/handle";
import { ArrayFieldState } from "../../store/common";
import { ModelState } from "../../store/models";
import { Dictionary } from "../../utility/object";
import { Layout } from "../layout";
import { LAYOUTS } from "../layouts";

export type BeamlineWatchpointReportsConfig = {
    beamlineDependency: string,
    watchpointReportsDependency: string
}

function BeamlineWatchpointItem(props: {child: Layout, aliases: ArrayAliases} & {[key: string]: any}) {
    let { aliases, child } = props;
    let handleFactory = useContext(CHandleFactory);
    let schema = useContext(CSchema);
    let [aliasedHandleFactory, _] = useState(new FormStateHandleFactory(schema, new HandleFactoryWithArrayAliases(schema, aliases, handleFactory)));
    aliasedHandleFactory.useUpdates(BeamlineWatchpointItem)
    let Comp = child.component;
    return (
        <CHandleFactory.Provider value={aliasedHandleFactory}>
            <Comp/>
        </CHandleFactory.Provider>
    )
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

        let findElementIndexById = (id: any) => elementsValue.findIndex(e => e.item.id == id);
        let findElementById = (id: any) => elementsValue[findElementIndexById(id)]
         

        let reportLayoutsRef: RefObject<Dictionary<string, Layout>> = useRef(new Dictionary());

        reportsValue.forEach((report, index) => {
            let id = `${report.item.id}`;
            let ele = findElementById(id);
            if(!reportLayoutsRef.current.contains(id)) {
                let cfg = createPanelConfig(`watchpointReport${index}`, new Dependency("beamlineElement.position"));
                reportLayoutsRef.current.put(id, LAYOUTS.getLayoutForSchema(cfg));
            }
        })

        let reportElements = reportLayoutsRef.current.items().map((e, index) => {
            let beamlineIndex = findElementIndexById(e.key);
            let beamlineElement = findElementById(e.key);
            let aliases: ArrayAliases = [
                {
                    realDataLocation: {
                        modelName: watchpointReportsDependency.modelName,
                        fieldName: watchpointReportsDependency.fieldName,
                        index
                    },
                    realSchemaName: "watchpointReport",
                    fake: "watchpointReport"
                },
                {
                    realDataLocation: {
                        modelName: beamlineDependency.modelName,
                        fieldName: beamlineDependency.fieldName,
                        index: beamlineIndex
                    },
                    realSchemaName: beamlineElement.model,
                    fake: "beamlineElement"
                }
            ];
            
            
            return (
                <React.Fragment key={e.key as any}>
                    <BeamlineWatchpointItem child={e.value} aliases={aliases}/>
                </React.Fragment>
            )
        })

        return (<>{
            reportElements
        }</>);
    };
}

function createPanelConfig(reportName: string, titleDep: Dependency) {
    return {
        "layout": "panel",
        "config": {
            "title": `Intensity, $(${titleDep.getDependencyString()}) m`,
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
