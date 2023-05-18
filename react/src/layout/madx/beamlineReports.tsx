import React, { FunctionComponent, useContext, useEffect, useRef, useState } from "react";
import { CReportEventManager, ReportEventManager } from "../../data/report";
import { Layout } from "../layout";
import { v4 as uuidv4 } from 'uuid';
import { CRouteHelper } from "../../utility/route";
import { ResponseHasState } from "../../utility/compute";
import { useDispatch, useSelector, useStore } from "react-redux";
import { modelActions, modelSelectors } from "../../store/models";
import { CHandleFactory } from "../../data/handle";
import { newModelFromSchema, StoreTypes } from "../../data/data";
import { CSchema } from "../../data/appwrapper";
import { LAYOUTS } from "../layouts";
import { HandleFactoryWithOverrides, HandleFactoryWithSimpleAliases } from "../../data/alias";
import { Dependency } from "../../data/dependency";

export type MadxBeamlineReportConfig = {
    type: 'histogram' | 'matchSummary' | 'graph2d',
    items: SchemaLayoutJson[],
    outputInfoUsage: {
        modelAlias: string,
        schemaModel: string,
        xDependency: string,
        xDefault: string,
        y1Dependency: string,
        y1Default: string,
        y2Dependency: string,
        y2Default: string,
        y3Dependency: string,
        y3Default: string
    }
}

export type MadxBeamlineReportsConfig = {
    animationGroup: string,
    reports: MadxBeamlineReportConfig[]
}

export type OutputInfo = {
    filename: string,
    isHistogram: boolean,
    modelKey: string,
    pageCount: number,
    plottableColumns: string[],
    _version: string
}

export type OutputInfos = OutputInfo[]

export class MadxBeamlineReportsLayout extends Layout<MadxBeamlineReportsConfig> {
    childLayouts: {[key: string]: Layout[]} = undefined;

    constructor(config: MadxBeamlineReportsConfig) {
        super(config);

        this.childLayouts = Object.fromEntries(this.config.reports.map(r => {
            return [
                r.type,
                (r.items || []).map(i => LAYOUTS.getLayoutForSchema(i))
            ]
        }))
    }

    component: FunctionComponent<{ [key: string]: any; }> = (props) => {
        let reportEventManager = useContext(CReportEventManager);
        let routeHelper = useContext(CRouteHelper);
        let reportEventsVersionRef = useRef(uuidv4());

        // make sure this component receives the first update
        let customReportEventManager = new ReportEventManager(routeHelper);

        let [lastSimulationData, updateLastSimulationData] = useState<ResponseHasState>(undefined);
        let [outputInfo, updateOutputInfo] = useState<OutputInfos>(undefined);

        useEffect(() => {
            reportEventManager.addListener(reportEventsVersionRef.current, this.config.animationGroup, {
                onReportData: (simulationData) => {
                    updateOutputInfo(simulationData.outputInfo as OutputInfos);
                    updateLastSimulationData(simulationData);
                }
            })

            return () => {
                reportEventManager.clearListenersForKey(reportEventsVersionRef.current);
            }
        }, [])

        useEffect(() => {
            if(lastSimulationData !== undefined) {
                customReportEventManager.handleSimulationData(this.config.animationGroup, lastSimulationData);
            }
        }, [lastSimulationData])

        return (
            <CReportEventManager.Provider value={customReportEventManager}>
                {(outputInfo || []).map(o => {
                    let type = (o.isHistogram ? "heatplot" : "graph2d");
                    let config = this.config.reports.find(r => r.type === type);

                    return (
                        <MadxBeamlineReportComponent key={o.modelKey} outputInfo={o} config={config} childLayouts={this.childLayouts[config.type]}/>
                    )
                })}
            </CReportEventManager.Provider>
        )
    }
}

export function MadxBeamlineReportComponent(props: {
    config: MadxBeamlineReportConfig,
    outputInfo: OutputInfo,
    childLayouts: Layout[]
}) {
    // update the report model to make sure it exists
    // also add x, y1,...
    // render child layouts

    let handleFactory = useContext(CHandleFactory);
    let schema = useContext(CSchema);
    let store = useStore();
    let dispatch = useDispatch();

    let chosenNames = [];
    let setPlotColumn = (dep: Dependency, defaultColumn: string) => {
        let m = handleFactory.createModelHandle(dep.modelName, StoreTypes.Models).initialize(store.getState()).value;

        if(m) {
            let handle = handleFactory.createHandle(dep, StoreTypes.Models).initialize(store.getState());
            let v = handle.value;
            if(v !== undefined) {
                chosenNames.push(v);
                return;
            }
        } else {
            m = newModelFromSchema(schema.models[props.config.outputInfoUsage.schemaModel], {});
            dispatch(modelActions.updateModel({
                name: dep.modelName,
                value: m
            }))
        }
        
        let v = undefined;
        if(defaultColumn) {
            v = defaultColumn;
        } else {
            v = props.outputInfo.plottableColumns.find(n => !chosenNames.includes(n));
        }
        chosenNames.push(v);
        handleFactory.createHandle(dep, StoreTypes.Models).initialize(store.getState()).write(v, store.getState(), dispatch);
    }

    let [hasInit, updateHasInit] = useState<boolean>(false);

    useEffect(() => {
        ["x", "y1", "y2", "y3"].forEach(n => {
            setPlotColumn(new Dependency(props.config.outputInfoUsage[`${n}Dependency`]), props.config.outputInfoUsage[`${n}Default`] || undefined)
        })

        updateHasInit(true);
    })

    let aliasedHandleFactory = new HandleFactoryWithSimpleAliases(schema, [{
        real: props.outputInfo.modelKey,
        fake: props.config.outputInfoUsage.modelAlias
    }], handleFactory);

    let overridesHandleFactory = new HandleFactoryWithOverrides(schema, [{
        value: {
            modelName: props.outputInfo.modelKey,
            title: "Report"
        },
        fake: "outputInfo"
    }], aliasedHandleFactory);

    return (
        <>
            <CHandleFactory.Provider value={overridesHandleFactory}>
            {hasInit && (
                <>
                    {(props.childLayouts || []).map((l, i) => {
                        let Comp = l.component;
                        return <Comp key={i}/>
                    })}
                </>
            )}
            </CHandleFactory.Provider>
        </>
    )
}
