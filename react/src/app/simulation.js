import { useContext, useState, useEffect } from "react";
import { ContextSimulationListPromise,
        ContextSimulationInfoPromise, 
        ContextAppName, 
        ContextAppInfo, 
        ContextAppViewBuilder,
        ContextModels} from "../components/context";
import { mapProperties } from "../helper";
import { FormStateInitializer } from "../components/form";
import { Row, Col, Container } from "react-bootstrap";
import { Models } from "../dependency";
import {
    selectModel,
    updateModel,
    selectModels,
} from "../models";

export function ViewGrid(props) {
    let { views, ...otherProps } = props;
    let viewPanels = Object.entries(views).map(([id, view]) => {
        let View = view;
        return (
            <Col md={6} className="mb-3" key={id}>
                <View {...otherProps}/>
            </Col>
        )
    });
    return (
        <Container fluid className="mt-3">
            <Row>
                {viewPanels}
            </Row>
        </Container>
    )
}

function SimulationInfoInitializer(child) {
    return (props) => {
        let contextFn = useContext;
        let stateFn = useState;
        let effectFn = useEffect;

        let simulationListPromise = contextFn(ContextSimulationListPromise);
        
        let [simulationInfoPromise, updateSimulationInfoPromise] = stateFn(undefined);
        let [hasInit, updateHasInit] = stateFn(false);
        let appName = contextFn(ContextAppName);

        let modelsWrapper = new Models({
            modelActions: {
                updateModel
            },
            modelSelectors: {
                selectModel,
                selectModels
            }
        })

        effectFn(() => {
            updateSimulationInfoPromise(new Promise((resolve, reject) => {
                simulationListPromise.then(simulationList => {
                    let simulation = simulationList[0];
                    let { simulationId } = simulation;
                    // TODO: why 0
                    fetch(`/simulation/${appName}/${simulationId}/0/source`).then(async (resp) => {
                        let simulationInfo = await resp.json();
                        let { models } = simulationInfo;

                        for(let [modelName, model] of Object.entries(models)) {
                            modelsWrapper.updateModel(modelName, model);
                        }

                        resolve({...simulationInfo, simulationId});
                        updateHasInit(true);
                    })
                })
            }))
        }, [])

        let ChildComponent = child;
        return hasInit && simulationInfoPromise && (
            <ContextModels.Provider value={modelsWrapper}>
                <ContextSimulationInfoPromise.Provider value={simulationInfoPromise}>
                    <ChildComponent {...props}>

                    </ChildComponent>
                </ContextSimulationInfoPromise.Provider>
            </ContextModels.Provider>
        )
    }
}

export function SimulationRoot(props) {
    let { simulation } = props;

    let appInfo = useContext(ContextAppInfo);
    let viewBuilder = useContext(ContextAppViewBuilder);
    let { schema } = appInfo;

    let viewInfos = mapProperties(schema.views, (viewName, view) => {
        return {
            view,
            viewName: viewName
        }
    })
    let viewComponents = mapProperties(viewInfos, (viewName, viewInfo) => viewBuilder.buildComponentForView(viewInfo));

    let buildSimulationRoot = (simulation) => {
        return SimulationInfoInitializer(
            FormStateInitializer({ viewInfos, schema })(
                () => {
                    return <ViewGrid views={Object.values(viewComponents)}/>
                }
            )
        );
    }

    let SimulationChild = buildSimulationRoot(simulation);

    return <SimulationChild></SimulationChild>
}
