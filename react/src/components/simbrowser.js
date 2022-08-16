import { Link, Route, Routes, useRoutes, Navigate, useParams } from "react-router-dom";
import { Row, Col, Container, Accordion } from "react-bootstrap";
import { ContextSimulationListPromise } from "./context";
import { useContext, useState, useEffect } from "react";
import { SimulationRoot } from "../app/simulation";

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

/**
 * @param {string} str 
 */
let removeSeparators = (str, {front=true, end=true}) => {
    while(front && str.length > 0 && str.substring(0, 1) === '/') {
        str = str.substring(1);
    }
    while(end && str.length > 0 && str.substring(str.length - 1) === '/') {
        str = str.substring(0, str.length - 1);
    }
    return str;
}

/**
 * @param  {...string} paths 
 */
function joinPath(...paths) {
    let path = '';

    paths = paths || [];
    for(let i = 0; i < paths.length; i++) {
        let p = paths[i];
        if(p) {
            let tp = removeSeparators(p, { front: i !== 0 });
            if(tp.trim().length > 0) {
                path += (i > 0 ? '/' : '') + tp;
            }
        }
    }

    return path;
}

function SimulationTreeViewFolder(props) {
    let { tree } = props;

    let childElements = [];
    for(let child of tree.children) {
        if(child.children) {
            childElements.push(<SimulationTreeViewFolder tree={child}/>);
        } else {
            childElements.push(<SimulationTreeViewItem item={child}/>);
        }
    }

    let subpath = joinPath('./', encodeURI(tree.folder));

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

    let path = joinPath('/source', item.simulationId);

    return (
        <Link to={path} key={path}>{item.name}</Link>
    )
}

const createSimulationPathSubtreeView = (treeRoot, path) => {
    const createTreeFolderView = (item) => {
        const fullPath = "/simulations/" + path + "/" + item.name;
        return (
            <Link to={fullPath} key={fullPath}>{item.name}</Link>
        )
    }

    const createTreeSimulationView = (item) => {
        const fullPath = "/source/" + item.name
        return (
            <div>
                <Link to={fullPath} key={fullPath}>{item.name}</Link>
            </div>
        )
    }

    const isFolder = (item) => {
        return item.children;
    }

    if(!isFolder(treeRoot)) {
        return createTreeSimulationView(treeRoot);
    } else {
        const subPath = path ? path + "/" + treeRoot.name : treeRoot.name;
        const els = treeRoot.children.map(child => createSimulationPathSubtreeView(child, subPath));
        return (
            <>
                {createTreeFolderView(treeRoot)}
                <div className="sr-path-subtree">
                    {els}
                </div>
            </>
        )
    }
}

const SimulationPathTreeView = (props) => {
    return (
        <div className={props.className}>
            {createSimulationPathSubtreeView(props.tree, props.path)}
        </div>
    )
}

const SimulationPathIconView = (props) => {
    const els = props.tree.children.map(child => (
        <Col>
            <Link to={props.path ? props.path + "/" + child.name : child.name}>
                <div className="sr-simulation-browser-thumbnail">
                    <div className="sr-simulation-browser-thumbnail-title">
                        {child.name}
                    </div>
                    <div className="sr-simulation-browser-thumbnail-footer">
                        {child.children ? 'Folder' : 'Item'}
                    </div>
                </div>
            </Link>
        </Col>
    ))

    return (
        <Container className={(props.className && "") + " container-fluid"}>
            <Row className="row-cols-4">
                {els}
            </Row>
        </Container>
    )
}

function SimulationBrowserOuter(props) {
    let { simulationList, simulationTree } = props;
    /**
     * 
     * @param {{
     *     name: string,
     *     folder: string,
     *     children: []
     * }} subtree 
     * @returns 
     */
    let subtreeRoute = (subtree) => {
        //var subpath = path ? path + "/" + subtree.name : subtree.name;
        let element = <SimulationBrowser tree={subtree} path={subtree.folder}></SimulationBrowser>
        if(subtree.children) {
            return {
                path: encodeURI(subtree.name),
                children: [
                    {
                        index: true,
                        element
                    },
                    ...(subtree.children.filter(c => c.children !== undefined).map(child => subtreeRoute(child)))
                ]
            }
        }
        return {
            path: subtree.name,
            element
        }
    }
    let routes = [
        subtreeRoute(simulationTree), 
        /*{
            path: "/",
            element: <SimulationBrowser tree={simulationTree} path=""></SimulationBrowser>
        },*/
        {
            path: "*",
            element: <>Not Found!</>
        }
    ]
    let el = useRoutes(routes);
    return el
}

const SimulationBrowser = (props) => {
    let { tree, path } = props; 
    return (
        <Container className="sr-simulation-browser">
            <Row sm={2}>
                <Col sm={4}>
                    <SimulationTreeViewFolder className="sr-simulation-browser-tree" tree={tree}/>
                </Col>
                <Col sm={8}></Col>
            </Row>
        </Container>
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
    useEffect(() => {
        simulationListPromise.then(simulationList => {
            let tree = buildSimulationsTree(simulationList);
            console.log(tree);
            // cause render on promise finish to hopefully recalculate routing
            updateSimInfo({
                simulationList,
                simulationTree: tree
            })
        })
    }, []);

    let child = undefined;

    if(simInfo) {
        child = (
            <Routes>
                <Route path="/" exact element={
                    <Navigate to="/simulations"></Navigate>
                }></Route>
                <Route path="simulations/*" element={
                    <SimulationBrowserOuter simulationList={simInfo.simulationList} simulationTree={simInfo.simulationTree}></SimulationBrowserOuter>
                }></Route>
                <Route path="source/:id" element={
                    <SimulationRootWrapper simulationList={simInfo.simulationList}/>
                }></Route>
            </Routes>
        )
    } else {
        child = <>Loading...</>
    }

    return child;
}