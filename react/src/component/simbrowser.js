import { trimPathSeparators, joinPath } from "../utility/path";
import React, { useContext } from "react";
import {
    Accordion,
    Container,
    Row,
    Col
} from "react-bootstrap";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import { Link, Route, Routes, useResolvedPath, Navigate, useParams } from "react-router-dom";
import { SimulationRoot } from "./simulation";
import { CRelativeRouterHelper, RouteHelper } from "../utility/route";
import "./simbrowser.scss";
import { NavbarLeftContainerId } from "./reusable/navbar";
import { CSimulationList } from "../data/appwrapper";
import { Portal } from "./reusable/portal";

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
        simulation.folder = trimPathSeparators(simulation.folder, { front: true, end: true });
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
    let { tree, isRoot, path } = props;

    let routeHelper = useContext(CRelativeRouterHelper);

    let childElements = [];
    for(let child of tree.children) {
        if(child.children) {
            let [, ...restPath] = path;
            childElements.push(<SimulationTreeViewFolder key={joinPath(child.folder, child.name)} tree={child} path={restPath}/>);
        } else {
            childElements.push(<SimulationTreeViewItem key={joinPath(child.folder, child.name)} item={child}/>);
        }
    }

    let subpath = routeHelper.getRelativePath(joinPath('/simulations', encodeURI(tree.folder)));
    let shouldBeOpen = isRoot || (path.length > 0 && path[0] === tree.name);

    return <Accordion defaultActiveKey={shouldBeOpen ? '0' : undefined}>
        <Accordion.Item eventKey="0">
            <Accordion.Header>
                <Link to={subpath} key={subpath}>{tree.name}</Link>
            </Accordion.Header>
            <Accordion.Body>
                {childElements}
            </Accordion.Body>
        </Accordion.Item>
    </Accordion>
}

function SimulationTreeViewItem(props) {
    let { item } = props;
    let routeHelper = useContext(CRelativeRouterHelper);

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

    let routeHelper = useContext(CRelativeRouterHelper);

    let path = routeHelper.getRelativePath(tree.simulationId)

    return (
        <Link to={path}>
            <div className="sr-sim-icon-view-base sr-sim-icon-view-folder">
                <div className="sr-sim-icon-view-icon-outer">
                    <FontAwesomeIcon className="sr-sim-icon-view-icon sr-sim-icon-view-folder-icon" icon={Icon.faFile}/>
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
    let { tree, path } = props;
    path = path || [];
    let { simulationFolder } = useParams();

    let childFn = props.children || (() => undefined);

    if(simulationFolder) {
        path.push(simulationFolder);
        let matchedFolder = tree.children.find(c => c.children && c.name === simulationFolder);

        if(!matchedFolder) {
            return <>Folder {simulationFolder} not found!</> //TODO 404
        } else {
            tree = matchedFolder;
        }
    }

    let el = childFn({routedTree: tree, routedPath: path})
    // TODO: this calls childFn even if route is not a match
    return (
        <Routes>
            <Route path="/" element={
                <>{el}</>
            }/>
            <Route path="/:simulationFolder/*" element={
                <SimulationFolderRouter tree={tree} path={path}>{props.children}</SimulationFolderRouter>
            }/>
        </Routes>
    )
}

function SimulationRouteHeader(props) {
    let { path } = props;
    let routeHelper = useContext(CRelativeRouterHelper);

    let prevSegments = [];
    let elements = (path || []).map(pathSegment => {
        let routePath = routeHelper.getRelativePath(joinPath('/simulations', ...prevSegments, pathSegment));
        prevSegments.push(pathSegment);
        return (
            <React.Fragment key={routePath}>
                <span className="sr-sim-route-header-separator sr-sim-route-header-text">/</span>
                <Link to={routePath}>
                    <span className="sr-sim-route-header-segment sr-sim-route-header-text">
                        {pathSegment}
                    </span>
                </Link>
            </React.Fragment>
        )
    })

    return (
        <div className="sr-sim-route-header">
            {elements}
        </div>
    )
}

function SimulationBrowser(props) {
    let { tree } = props;

    return (
        <SimulationFolderRouter tree={tree}>
            {({routedTree, routedPath}) => {
                return (
                    <>
                        <Portal targetId={NavbarLeftContainerId} className="order-4">
                            <SimulationRouteHeader path={routedPath}/>
                        </Portal>
                        <div className="sr-sim-browser-outer">
                            <Container fluid className="sr-sim-browser">
                                <Row sm={2}>
                                    <Col sm={4}>
                                        <SimulationTreeViewFolder isRoot={true} className="sr-sim-tree-view" tree={tree} path={routedPath}/>
                                    </Col>
                                    <Col sm={8}>
                                        <SimulationIconView tree={routedTree} path={routedPath}/>
                                    </Col>
                                </Row>
                            </Container>
                        </div>
                    </>

                )
            }}
        </SimulationFolderRouter>
    )
}

function SimulationRootWrapper(props) {
    let { id } = useParams();
    return <SimulationRoot key={id} simulationId={id}/> // TODO: error/missing handling
}

export function SimulationBrowserRoot(props) {
    let simulationList = useContext(CSimulationList);
    let simulationTree = buildSimulationsTree(simulationList);
    let pathPrefix = useResolvedPath('');

    let routeHelper = new RouteHelper(pathPrefix);
    let child = (
        <CRelativeRouterHelper.Provider value={routeHelper}>
            <Routes>
                <Route path="/" element={
                    <Navigate to={`simulations`}></Navigate>
                }/>
                <Route path="/simulations/*" element={<SimulationBrowser tree={simulationTree} />}/>
                <Route path="/simulations/:simulationFolder/*" element={<SimulationBrowser tree={simulationTree} />}/>
                <Route path="/:id/*" element={
                    <SimulationRootWrapper simulationList={simulationList}/>
                }/>
            </Routes>
        </CRelativeRouterHelper.Provider>
    )

    return (
        <>
            {child}
        </>
    );
}
