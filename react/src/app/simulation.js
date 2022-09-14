import { useContext, useState, useEffect } from "react";
import { ContextSimulationListPromise,
        ContextSimulationInfoPromise, 
        ContextAppName, 
        ContextAppInfo, 
        ContextAppViewBuilder,
        ContextModels,
        ContextRelativeRouterHelper} from "../components/context";
import { mapProperties, RouteHelper } from "../helper";
import { FormStateInitializer } from "../components/form";
import { Row, Col, Container, Navbar, Nav } from "react-bootstrap";
import { Models } from "../dependency";
import {
    selectModel,
    updateModel,
    selectModels,
} from "../models";
import { useResolvedPath } from "react-router-dom";

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

export function SimulationOuter(props) {
    let appInfo = useContext(ContextAppInfo);
    let appName = useContext(ContextAppName);

    let simBrowerRelativeRouter = useContext(ContextRelativeRouterHelper);

    let pathPrefix = useResolvedPath('');
    let currentRelativeRouter = new RouteHelper(pathPrefix);

    let titleCaseAppName = appName.split(" ").map(word => {
        return word.substring(0,1).toUpperCase() + (word.length > 1 ? word.substring(1) : "");
    }).join(" ");

    // TODO: navbar should route to home, when one is made
    return (
        <Container>
            <Navbar>
                <Container>
                    <Navbar.Brand href={simBrowerRelativeRouter.getCurrentPath()}>
                        <img
                        alt=""
                        src="/react/img/sirepo.gif"
                        width="30"
                        height="30"
                        className="d-inline-block align-top"
                        />{' '}
                        {titleCaseAppName}
                    </Navbar.Brand>
                    <Nav variant="tabs">

                    </Nav>
                </Container>
            </Navbar>
            <ContextRelativeRouterHelper.Provider value={currentRelativeRouter}>
                {props.children}
            </ContextRelativeRouterHelper.Provider>
        </Container>
        
    )

}

export function SimulationRoot(props) {
    let { simulation } = props;

    let appInfo = useContext(ContextAppInfo);
    let viewBuilder = useContext(ContextAppViewBuilder);
    let { schema } = appInfo;

    let viewComponents = schema.views.map((view) => viewBuilder.buildComponentForView(view));

    let buildSimulationRoot = (simulation) => {
        return SimulationInfoInitializer(
            FormStateInitializer({ schema })(
                () => {
                    return <ViewGrid views={viewComponents}/>
                }
            )
        );
    }

    let SimulationChild = buildSimulationRoot(simulation);

    return (
        <SimulationOuter>
            <SimulationChild/>
        </SimulationOuter>
    )
}
