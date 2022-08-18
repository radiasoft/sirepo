import { Link, Route, Routes, useRoutes, Navigate, useParams, useMatch, useLocation, useResolvedPath } from "react-router-dom";
import { Row, Col, Container, Accordion, Card } from "react-bootstrap";
import { ContextRelativeRouterHelper, ContextSimulationListPromise } from "../components/context";
import { useContext, useState, useEffect } from "react";
import { SimulationRoot } from "./simulation";
import { joinPath, removeSeparators, RouteHelper } from "../helper";
import { ViewGrid } from "../components/simulation";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import "./simbrowser.scss"

function buildSimulationsTree(simulations) {
    let root = {
        name: '/',
        folder: '',
        children: []
    }

    let createFolderIfNotExists = (tree, folderName, fullFolderPath) => {
        if(tree.children === undefined) {
            tree.children = [];
        }
        let findChild = () => tree.children.find(c => c.name === folderName);
        if(!findChild()) {
            tree.children.push({ name: folderName, folder: fullFolderPath, children: [] });
        } 
        return findChild();
    }

    let placeItemIntoFolder = (simulation) => {
        simulation.folder = removeSeparators(simulation.folder, { start: true, end: true });
        let paths = simulation.folder.split('/');

        let tree = root;

        let fullPath = '';
        for(let segment of paths) {
            if(!segment || segment.length === 0) continue; // handle leading and double? /
            fullPath = joinPath(fullPath, segment);
            tree = createFolderIfNotExists(tree, segment, fullPath);
        }

        tree.children = tree.children || [];
        tree.children.push(simulation);
    }

    for(let item of simulations) {
        placeItemIntoFolder(item);
    }

    return root;
}

function SimulationTreeViewFolder(props) {
    let { tree, pathPrefix, isRoot } = props;

    let childElements = [];
    for(let child of tree.children) {
        if(child.children) {
            let nextPrefix = isRoot ? undefined : joinPath(pathPrefix, tree.name);
            childElements.push(<SimulationTreeViewFolder key={joinPath(child.folder, child.name)} pathPrefix={nextPrefix} tree={child}/>);
        } else {
            childElements.push(<SimulationTreeViewItem key={joinPath(child.folder, child.name)} item={child}/>);
        }
    }

    let subpath = joinPath('./', encodeURI(joinPath(isRoot ? undefined : pathPrefix, tree.name)));

    return <Accordion>
        <Accordion.Header>
            <Link to={subpath} key={subpath}>{tree.name}</Link>
        </Accordion.Header>
        <Accordion.Body>
            {childElements}
        </Accordion.Body>
    </Accordion>
}

function SimulationTreeViewItem(props) {
    let { item } = props;
    let routeHelper = useContext(ContextRelativeRouterHelper);

    let path = routeHelper.getRelativePath(joinPath('source', item.simulationId));

    return (
        <div className="sr-sim-tree-view-item">
            <Link to={path} key={path}>{item.name}</Link>
        </div>
    )
}

function SimulationIconView(props) {
    let { tree } = props;

    let elements = tree.children.map(c => {
        if(c.children) {
            return <SimulationIconViewFolder key={joinPath(c.folder, c.name)} tree={c}/>
        } else {
            return <SimulationIconViewItem key={joinPath(c.folder, c.name)} tree={c}/>
        }
    })

    return (
        <div className="sr-sim-icon-view">
            {elements}
        </div>
    )
}

function SimulationIconViewFolder(props) {
    let { tree } = props;

    return (
        <Link to={joinPath('./', tree.name)}>
            <div className="sr-sim-icon-view-base sr-sim-icon-view-folder">
                <div className="sr-sim-icon-view-icon-outer">
                    <FontAwesomeIcon className="sr-sim-icon-view-icon sr-sim-icon-view-folder-icon" icon={Icon.faFolder}/>
                </div>
                <div className="sr-sim-icon-view-name text-center">
                    <span>
                        {tree.name}
                    </span>
                </div>
            </div>
        </Link>
    )
}

function SimulationIconViewItem(props) {
    let { tree } = props;

    let routeHelper = useContext(ContextRelativeRouterHelper);

    let path = routeHelper.getRelativePath(joinPath('source', tree.simulationId))

    return (
        <Link to={path}>
            <div className="sr-sim-icon-view-base sr-sim-icon-view-folder">
                <div className="sr-sim-icon-view-icon-outer">
                    <FontAwesomeIcon className="sr-sim-icon-view-icon sr-sim-icon-view-folder-icon" icon={Icon.faFolder}/>
                </div>
                <div className="sr-sim-icon-view-name text-center">
                    <span>
                        {tree.name}
                    </span>
                </div>
            </div>
        </Link>
    )
}

function SimulationFolderRouter(props) {
    let { tree } = props;
    let { simulationFolder } = useParams();

    let childFn = props.children || (() => undefined);

    if(simulationFolder) {
        let matchedFolder = tree.children.find(c => c.children && c.name === simulationFolder);

        if(!matchedFolder) { 
            return <>Folder {simulationFolder} not found!</> //TODO 404
        } else {
            tree = matchedFolder;
        }
    }

    return (
        <Routes>
            <Route path="/" exact element={
                <>{childFn(tree)}</>
            }/>
            <Route path="/:simulationFolder/*" element={
                <SimulationFolderRouter tree={tree}/>
            }/>
        </Routes>
    )
}

const SimulationBrowser = (props) => {
    let { tree } = props; 
    return (
        <div className="sr-sim-browser-outer">
            <div className="sr-sim-browser-header">

            </div>
            <Container className="sr-sim-browser">
                <Row sm={2}>
                    <Col sm={4}>
                        <SimulationTreeViewFolder isRoot={true} className="sr-sim-tree-view" tree={tree}/>
                    </Col>
                    <Col sm={8}>
                        <SimulationFolderRouter tree={tree}>
                            {(routedTree) => {
                                return <SimulationIconView tree={routedTree}/>
                            }}
                        </SimulationFolderRouter>
                    </Col>
                </Row>
            </Container>
        </div>
        
    )
}

function SimulationRootWrapper(props) {
    let { simulationList } = props;
    let { id } = useParams();
    

    let simulation = simulationList.find(sim => sim.simulationId === id);
     
    return <SimulationRoot simulation={simulation}/> // TODO: error/missing handling
}

export function SimulationBrowserRoot(props) {
    let simulationListPromise = useContext(ContextSimulationListPromise);
    let [simInfo, updateSimInfo] = useState(undefined);
    let pathPrefix = useResolvedPath('');
    useEffect(() => {
        simulationListPromise.then(simulationList => {
            let tree = buildSimulationsTree(simulationList);
            // cause render on promise finish to hopefully recalculate routing
            updateSimInfo({
                simulationList,
                simulationTree: tree
            })
        })
    }, []);

    let routeHelper = new RouteHelper(pathPrefix);
    let child = undefined;

    if(simInfo) {
        child = (
            <ContextRelativeRouterHelper.Provider value={routeHelper}>
                <Routes>
                    <Route path="/" exact element={
                        <Navigate to={`simulations`}></Navigate>
                    }/>
                    <Route path="/simulations" element={<SimulationBrowser tree={simInfo.simulationTree} />}/>
                    <Route path="/simulations/:simulationFolder/*" element={<SimulationBrowser tree={simInfo.simulationTree} />}/>
                    <Route path="/source/:id" element={
                        <SimulationRootWrapper simulationList={simInfo.simulationList}/>
                    }/>
                </Routes>
            </ContextRelativeRouterHelper.Provider>
        )
    } else {
        child = <>Loading...</>
    }

    return child;
}