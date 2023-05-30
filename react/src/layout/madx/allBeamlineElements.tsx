import React, { useContext, useState } from "react";
import { FunctionComponent } from "react";
import { Badge, Button, Container, Form, Modal, Tab, Table, Tabs } from "react-bootstrap";
import { useDispatch, useStore } from "react-redux";
import { formActionFunctions } from "../../component/reusable/form";
import { HoverController } from "../../component/reusable/hover";
import { Panel, ViewPanelActionButtons } from "../../component/reusable/panel";
import { ArrayAliases, HandleFactoryWithArrayAliases, HandleFactoryWithOverrides } from "../../data/alias";
import { CSchema } from "../../data/appwrapper";
import { getValueSelector, newModelFromSchema, revertDataStructure, StoreTypes } from "../../data/data";
import { Dependency } from "../../data/dependency";
import { formStateFromModelState, FormStateHandleFactory } from "../../data/form";
import { CHandleFactory } from "../../data/handle";
import { useCoupledState } from "../../hook/coupling";
import { ArrayFieldElement, ArrayFieldState } from "../../store/common";
import { ModelState } from "../../store/models";
import { Layout } from "../layout";
import { LAYOUTS } from "../layouts";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import "./allBeamlineElements.scss";
import "./beamlines.scss";
import { FormFieldState, FormModelState } from "../../store/formState";
import { cloneDeep } from "lodash";
import { SchemaModel } from "../../utility/schema";

export type TemplateSettings = {
    type: string,
    name: string,
    modelName: string,
    items: SchemaLayoutJson[]
}

export type MadxAllBeamlineElementsConfig = {
    elementsDependency: string,
    selectedBeamlineDependency: string,
    beamlinesDependency: string,
    templateGroups: {
        name: string,
        types: string[]
    }[],
    elementTemplates: TemplateSettings[]
}

export type MadxBeamlineElementEditorCommonProps = {
    template: TemplateSettings,
    onHide: () => void
}

export function MadxBeamlineElementEditor(props: MadxBeamlineElementEditorCommonProps & {
    aliases: ArrayAliases
}) {
    let parentHandleFactory = useContext(CHandleFactory);
    let schema = useContext(CSchema);

    let handleFactory = new HandleFactoryWithArrayAliases(schema, props.aliases, parentHandleFactory);
    let formHandleFactory = new FormStateHandleFactory(schema, handleFactory);

    let store = useStore();
    return (
        <CHandleFactory.Provider value={formHandleFactory}>
            <MadxBeamlineElementEditorBase
            template={props.template}
            onHide={props.onHide}
            formSave={() => {
                formHandleFactory.save(store.getState(), store.dispatch);
                props.onHide();
            }}
            formCancel={() => {
                formHandleFactory.cancel(store.getState(), store.dispatch);
                props.onHide();
            }}
            canSave={formHandleFactory.isValid(store.getState())}
            />
        </CHandleFactory.Provider>
        
    )
}

export function MadxBeamlineNewElementEditor(props: MadxBeamlineElementEditorCommonProps & { onComplete: (modelState: ModelState, model: string) => void, name: string, id: number }) {
    let parentHandleFactory = useContext(CHandleFactory);
    let schema = useContext(CSchema);
    let store = useStore();
    let dispatch = useDispatch();
    let overridesHandleFactory = new HandleFactoryWithOverrides(schema, [
        {
            fake: props.template.modelName,
            value: newModelFromSchema(schema.models[props.template.modelName], { name: props.name, _id: props.id }),
            onSave: (v) => props.onComplete(v, props.template.modelName)
        }
    ], parentHandleFactory);

    return (
        <CHandleFactory.Provider value={overridesHandleFactory}>
            <MadxBeamlineElementEditorBase 
            template={props.template}
            onHide={props.onHide}
            canSave={overridesHandleFactory.isValid(store.getState())}
            formSave={() => {
                overridesHandleFactory.save(store.getState(), dispatch)
                props.onHide();
            }}
            formCancel={props.onHide}
            />
        </CHandleFactory.Provider>
    )
}

// TODO: garsuga, this is more generic than i thought, can easily be made into a common component
export function MadxBeamlineElementEditorBase(props: MadxBeamlineElementEditorCommonProps & {
    formSave: () => void,
    formCancel: () => void,
    canSave: boolean
}) {
    let [layouts, _, updated] = useCoupledState(props.template, () => {
        if(!props.template) { 
            return undefined;
        }
        return props.template.items.map((i, idx) => {
            return LAYOUTS.getLayoutForSchema(i);
        })
    })

    if(!(props.template && layouts)) {
        return <></>
    }
    
    return (
        <Modal show={props.template !== undefined} onHide={props.onHide}>
            <Modal.Header>
                {props.template.name}
            </Modal.Header>
            <Modal.Body>
                <div style={{ margin: "10px" }}>
                    {layouts.map((l, idx) => {
                        let Comp = l.component;
                        return <Comp key={idx}/>;
                    })}
                    <ViewPanelActionButtons onSave={props.formSave} onCancel={props.formCancel} canSave={props.canSave}/>
                </div>
            </Modal.Body>
            
        </Modal>
    )
}

export function getTemplateSettingsByType(type: string, templates: TemplateSettings[]) {
    let ret = templates.find(t => {
        return t.type == type
    });
    if(!ret) {
        throw new Error(`could not find template settings for type=${type}, ${JSON.stringify(templates)}`)
    }
    return ret;
}

function getElementDescription(element: ModelState, modelSchema: SchemaModel): string {
    return Object.entries(element).filter(([name, ]) => !(name == 'name' || name == 'l' || name == 'angle'))
    .sort(([a, ], [b, ]) => a.localeCompare(b))
    .filter(([name, value]) => name in modelSchema && value !== modelSchema[name].defaultValue)
    .map(([name, value]) => `${name}=${value}`).join(", ");
}

export class MadxAllBeamlineElementsLayout extends Layout<MadxAllBeamlineElementsConfig, {}> {
    constructor(config: MadxAllBeamlineElementsConfig) {
        super(config);
    }

    component: FunctionComponent<{ [key: string]: any; }> = (props) => {
        let handleFactory = useContext(CHandleFactory) as FormStateHandleFactory;
        handleFactory.useUpdates(MadxAllBeamlineElementsLayout);
        let store = useStore();
        let dispatch = useDispatch();
        let schema = useContext(CSchema);
        //let activeBeamlineId = handleFactory.createHandle(new Dependency(this.config.activeBeamlineDependency), StoreTypes.Models).hook().value;
        let elementsHandle = handleFactory.createHandle(new Dependency(this.config.elementsDependency), StoreTypes.FormState).hook();
        let elementsValue = revertDataStructure(elementsHandle.value, getValueSelector(StoreTypes.FormState)) as ArrayFieldState<ModelState>;
        let beamlinesHandle = handleFactory.createHandle(new Dependency(this.config.beamlinesDependency), StoreTypes.FormState).hook();
        let beamlinesValue = revertDataStructure(beamlinesHandle.value, getValueSelector(StoreTypes.FormState)) as ArrayFieldState<ModelState>;
        let selectedBeamlineHandle = handleFactory.createHandle(new Dependency(this.config.selectedBeamlineDependency), StoreTypes.Models).hook();

        let [newElementModalShown, updateNewElementModalShown] = useState(false);
        let [shownModalTemplate, updateShownModalTemplate] = useState<TemplateSettings>(undefined);
        let defaultGroup = this.config.templateGroups?.length > 0 ? this.config.templateGroups[0].name : undefined;

        let uniqueNameForType = (type: string) => {
            let maxId = elementsValue.filter(e => e.model.charAt(0) === type.charAt(0)).reduce<number>((prev: number, cur: ArrayFieldElement<ModelState>, idx) => {
                let numberPart = (/.*?(\d*).*?/g).exec(cur.item.name as string)[1];
                return Math.max(prev, parseInt(numberPart.length > 0 ? numberPart : "0"))
            }, 1);
            return `${type.charAt(0)}${maxId + 1}`
        }

        let findNextId = () => {
            let _allItems = [...elementsValue, ...beamlinesValue];
            return _allItems.reduce((prev, cur) => Math.max(prev, parseInt((cur.item._id || cur.item.id) as string)), 0);
        }

        

        let addNewElement = (template: TemplateSettings, modelValue: ModelState, model: string) => {
            console.log(`adding beamline element with type=${template.type}`, modelValue);

            let nv = [...(elementsHandle.value.value as any[])];
            let v = {
                item: formStateFromModelState(modelValue),
                model: model
            }
            console.log("nv before", nv);
            console.log("V", v);

            nv.push(v)
            
            elementsHandle.write({
                ...elementsHandle.value,
                value: nv
            }, store.getState(), dispatch);
        }

        let addElementToBeamline = (elementId: number | string, beamlineId: number) => {
            console.log("adding element", elementId);
            let v = cloneDeep(beamlinesHandle.value) as FormFieldState<ArrayFieldState<FormModelState>>;
            let beamline = v.value.find(b => b.item.id.value == beamlineId);
            console.log("before add", beamline.item.items.value);
            beamline.item.items.value.push(elementId);
            console.log("after add", beamline.item.items.value);
            beamlinesHandle.write(v, store.getState(), dispatch);
        }

        let removeElement = (elementId: number | string) => {
            let v = cloneDeep(beamlinesHandle.value) as FormFieldState<ArrayFieldState<FormModelState>>;
            let changed = false;
            v.value.forEach(b => {
                let idx = b.item.items.value.findIndex(e => e == elementId);
                if(idx > 0) {
                    changed = true;
                    let v = [...b.item.items.value];
                    v.splice(idx, 1);
                    b.item.items.value = v;
                }
            });
            if(changed) {
                beamlinesHandle.write(v, store.getState(), dispatch);
            }
            
            let nv = [...(elementsHandle.value.value as any[])];
            let idx = nv.findIndex(e => e.item._id.value == elementId);
            nv.splice(idx, 1);
            elementsHandle.write({
                ...elementsHandle.value,
                value: nv
            }, store.getState(), dispatch);
        }

        let [shownElement, updateShownElement] = useState<{
            template: TemplateSettings,
            aliases: ArrayAliases
        }>(undefined);

        return (
            <>
                <Modal show={newElementModalShown} onHide={() => updateNewElementModalShown(false)}>
                    <Modal.Header>
                        New Beamline Element
                    </Modal.Header>
                    <Modal.Body>
                        <Tabs defaultActiveKey={defaultGroup}>
                            {
                                this.config.templateGroups?.map(tg => {
                                    return (
                                        <Tab eventKey={tg.name} title={tg.name} key={tg.name}>
                                            <div className="d-flex flex-row" style={{ margin: "10px", flexWrap: "wrap", gap: ".5rem" }}>
                                            {
                                                ([...new Set(tg.types)].sort((a,b) => a.localeCompare(b))).map(t => {
                                                    let s = getTemplateSettingsByType(t, this.config.elementTemplates);
                                                    return (    
                                                        <Button key={`${t}`} variant="outline-secondary" onClick={() => {
                                                            updateShownModalTemplate(s)
                                                        }}>
                                                            {s.name}
                                                        </Button>
                                                    )
                                                })
                                            }
                                            </div>
                                            
                                        </Tab>
                                    )
                                })
                            }
                        </Tabs>
                    </Modal.Body>
                </Modal>
                {
                    shownModalTemplate && (
                        <MadxBeamlineNewElementEditor name={uniqueNameForType(shownModalTemplate.type)} id={findNextId()} onHide={() => {
                            updateShownModalTemplate(undefined);
                            updateNewElementModalShown(false);
                        }} template={shownModalTemplate} onComplete={(mv, m) => addNewElement(shownModalTemplate, mv, m)}/>
                    )
                }
                {shownElement && <MadxBeamlineElementEditor aliases={shownElement.aliases} template={shownElement.template} onHide={() => updateShownElement(undefined)}/>}
                <div className="d-flex flex-column">
                    <div className="d-flex flex-row flew-nowrap justify-content-right">
                        <Button variant="primary" size="sm" onClick={() => updateNewElementModalShown(true)}>New Element</Button>
                    </div>
                    <div>
                        <Table className="overflow-scroll w-100" style={{ maxHeight: "80vh" }}>
                            <thead style={{position: "sticky", top: "0", background: "#fff"}}>
                                <tr>
                                    <th>Name</th>
                                    <th>Description</th>
                                    <th>Length</th>
                                    <th>Bend</th>
                                </tr>
                            </thead>
                            <HoverController>
                                {
                                    (hover) => {
                                        return [...new Set(elementsValue.map((ev: ArrayFieldElement<ModelState>) => ev.model))].sort((a: string, b: string) => a.localeCompare(b)).map((category: string) => {
                                            return (
                                                <tbody key={category}>
                                                    <tr>
                                                        <td>
                                                            <span>
                                                                {category}
                                                            </span>
                                                        </td>
                                                    </tr>
                                                    {
                                                        elementsValue.filter(ev => ev.model == category).map((ev: ArrayFieldElement<ModelState>) => {
                                                            let id = ev.item._id as string;
                                                            let description = getElementDescription(ev.item, schema.models[ev.model]);
                                                            let elementsDependency = new Dependency(this.config.elementsDependency);
                                                            let template = ev.item.type !== undefined ? getTemplateSettingsByType((ev.item.type as string), this.config.elementTemplates) : undefined;
                                                            let aliases: ArrayAliases = ev.item.type !== undefined ? [
                                                                {
                                                                    realSchemaName: ev.item.type as string,
                                                                    realDataLocation: {
                                                                        modelName: elementsDependency.modelName,
                                                                        fieldName: elementsDependency.fieldName,
                                                                        index: elementsValue.findIndex(e => e.item._id === id)
                                                                    },
                                                                    fake: ev.item.type as string
                                                                }
                                                            ] : undefined;
                                                            return (
                                                                <React.Fragment key={id}>
                                                                    <tr onMouseEnter={() => hover.aquireHover(id)} onMouseLeave={() => hover.releaseHover(id)}>
                                                                        <td>
                                                                            <h6>
                                                                                <Badge bg="secondary">
                                                                                    {ev.item.name as string}
                                                                                </Badge>
                                                                            </h6>
                                                                        </td>
                                                                        <td className="table-cell">
                                                                            <span title={description} className="table-text">{description}</span>
                                                                        </td>
                                                                        <td className="table-cell">
                                                                            <span className="table-text">{ev.item.l !== undefined ? `${(ev.item.l)}m` : ""}</span>
                                                                        </td>
                                                                        <td className="table-cell">
                                                                            <span className="table-text">{ev.item.angle !== undefined ? `${ev.item.angle}` : ""}</span>
                                                                        </td>
                                                                    </tr>
                                                                    {
                                                                        hover.checkHover(id) && (
                                                                            <tr className="popover-buttons-outer" onMouseEnter={() => hover.aquireHover(id)} onMouseLeave={() => hover.releaseHover(id)}>
                                                                                <td className="popover-buttons">
                                                                                    <Button className="popover-button" size="sm" onClick={() => addElementToBeamline(id, selectedBeamlineHandle.value as number)}>
                                                                                        Add To Beamline
                                                                                    </Button>
                                                                                    <Button className="popover-button" size="sm" onClick={() => {
                                                                                            updateShownElement({
                                                                                                template,
                                                                                                aliases
                                                                                            })
                                                                                        }
                                                                                    }>
                                                                                        Edit
                                                                                    </Button>
                                                                                    <Button className="popover-button" size="sm" variant="danger" onClick={() => removeElement(id)}>
                                                                                        <FontAwesomeIcon icon={Icon.faClose}/>
                                                                                    </Button>
                                                                                </td>
                                                                            </tr>
                                                                        )
                                                                    }
                                                                </React.Fragment>
                                                                
                                                            )
                                                        })
                                                    }
                                                </tbody>
                                            )
                                            
                                        })
                                    }
                                }
                            </HoverController>
                        </Table>
                    </div>
                </div>
            </>
            
        )
    }
}
