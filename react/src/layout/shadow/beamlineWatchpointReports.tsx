import React, { RefObject, useRef } from "react";
import { FunctionComponent, useContext, useState } from "react";
import { ArrayAliases, HandleFactoryOverrides, HandleFactoryWithArrayAliases, HandleFactoryWithOverrides } from "../../data/alias";
import { CSchema } from "../../data/appwrapper";
import { StoreTypes } from "../../data/data";
import { Dependency } from "../../data/dependency";
import { FormStateHandleFactory } from "../../data/form";
import { CHandleFactory } from "../../data/handle";
import { useCoupledState } from "../../hook/coupling";
import { ArrayFieldState } from "../../store/common";
import { ModelState } from "../../store/models";
import { Layout } from "../layout";
import { LAYOUTS } from "../layouts";

export type ShadowWatchpointReportsConfig = {
    beamlineDependency: string,
    watchpointReportsDependency: string
}

function ShadowBeamlineWatchpointItem(props: {beamlineIndex: number, aliases: ArrayAliases, overrides: HandleFactoryOverrides, child: Layout} & {[key: string]: any}) {
    let { aliases, overrides, child, beamlineIndex } = props;
    let handleFactory = useContext(CHandleFactory);
    let schema = useContext(CSchema);
    let createHandleFactory = () => new FormStateHandleFactory(schema, 
        new HandleFactoryWithArrayAliases(schema, aliases, 
            new HandleFactoryWithOverrides(schema, overrides, handleFactory)
        )
    )
    let [aliasedHandleFactory, _, indexChanged] = useCoupledState(beamlineIndex, createHandleFactory);

    if(indexChanged) {
        return <></>
    }

    aliasedHandleFactory.useUpdates(ShadowBeamlineWatchpointItem)
    let Comp = child.component;
    return (
        <CHandleFactory.Provider value={aliasedHandleFactory}>
            <Comp/>
        </CHandleFactory.Provider>
    )
}

export class ShadowBeamlineWatchpointReports extends Layout<ShadowWatchpointReportsConfig, {}> {
    private reportLayout: Layout;

    constructor(config: ShadowWatchpointReportsConfig) {
        super(config);

        this.reportLayout = LAYOUTS.getLayoutForSchema(createPanelConfig(new Dependency("iteration.index"), new Dependency("beamlineElement.position"), new Dependency("beamlineElement.id")))
    }

    component: FunctionComponent<{ [key: string]: any; }> = (props) => {
        let watchpointReportsDependency = new Dependency(this.config.watchpointReportsDependency);
        let beamlineDependency = new Dependency(this.config.beamlineDependency);
        let handleFactory = useContext(CHandleFactory);
        let reportsHandle = handleFactory.createHandle(watchpointReportsDependency, StoreTypes.Models).hook();
        let elementsHandle = handleFactory.createHandle(beamlineDependency, StoreTypes.Models).hook();
        let elementsValue = elementsHandle.value as ArrayFieldState<ModelState>;

        let findElementIndexById = (id: any) => elementsValue.findIndex(e => e.item.id == id);
        let findElementById = (id: any) => elementsValue[findElementIndexById(id)];

        let comps = (reportsHandle.value as ArrayFieldState<ModelState>).map(i => i.item).map((report, index) => {
            let id = report.id;
            let beamlineIndex = findElementIndexById(id);
            let beamlineElement = findElementById(id);
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

            let overrides: HandleFactoryOverrides = [
                {
                    fake: "iteration",
                    value: {
                        index
                    }
                }
            ]
            
            return (
                <ShadowBeamlineWatchpointItem beamlineIndex={beamlineIndex} key={`watchpointReport${id}`} aliases={aliases} overrides={overrides} child={this.reportLayout}/>
            )
        })

        return (<>{
            comps
        }</>);
    };
}

function createPanelConfig(indexDep: Dependency, titleDep: Dependency, idDep: Dependency) {
    return {
        "layout": "panel",
        "config": {
            "title": `Intensity, $(${titleDep.getDependencyString()}) m`,
            "basic": [
                {
                    "layout": "autoRunReport",
                    "config": {
                        "report": `watchpointReport$(${indexDep.getDependencyString()})`,
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
