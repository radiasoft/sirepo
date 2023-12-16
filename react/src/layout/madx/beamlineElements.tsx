import { FunctionComponent, useContext, useState } from "react";
import { getValueSelector, revertDataStructure, StoreTypes } from "../../data/data";
import { FormStateHandleFactory } from "../../data/form";
import { CHandleFactory } from "../../data/handle";
import { Layout } from "../layout";
import { getTemplateSettingsByType, MadxBeamlineElementEditor, TemplateSettings } from "./allBeamlineElements";
import { Dependency } from "../../data/dependency";
import { ArrayFieldElement, ArrayFieldState } from "../../store/common";
import { ModelState } from "../../store/models";
import React from "react";
import { Badge } from "react-bootstrap";
import { useCoupledState } from "../../hook/coupling";
import { useDispatch, useStore } from "react-redux";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import { LAYOUTS } from "../layouts";
import { ArrayAliases } from "../../data/alias";
import { HoverController } from "../../component/reusable/hover";
import { FormFieldState, FormModelState } from "../../store/formState";
import { cloneDeep } from "lodash";

export type MadxBeamlineElmenetsConfig = {
    selectedBeamlineDependency: string,
    beamlinesDependency: string,
    elementsDependency: string,
    elementTemplates: TemplateSettings[]
}

export class MadxBeamlineElementsLayout extends Layout<MadxBeamlineElmenetsConfig> {
    component: FunctionComponent<{ [key: string]: any; }> = (props) => {
        let handleFactory = useContext(CHandleFactory) as FormStateHandleFactory;
        let store = useStore();
        let dispatch = useDispatch();
        let isDirty = handleFactory.isDirty();

        let selectedBeamlineHandle = handleFactory.createHandle(new Dependency(this.config.selectedBeamlineDependency), StoreTypes.Models).hook();
        // handles case where selected beamline changes and form is dirty
        let _ = useCoupledState(selectedBeamlineHandle.value, () => {
            if(isDirty) {
                handleFactory.cancel(store.getState(), dispatch);
            }
            return selectedBeamlineHandle.value;
        })
        let beamlinesHandle = handleFactory.createHandle(new Dependency(this.config.beamlinesDependency), StoreTypes.FormState).hook();
        let beamlinesValue = revertDataStructure(beamlinesHandle.value, getValueSelector(StoreTypes.FormState)) as ArrayFieldState<ModelState>;
        let elementsDependency = new Dependency(this.config.elementsDependency);
        let elementsHandle = handleFactory.createHandle(elementsDependency, StoreTypes.FormState).hook();
        let elementsValue = revertDataStructure(elementsHandle.value, getValueSelector(StoreTypes.FormState)) as ArrayFieldState<ModelState>;

        let _allItems = [...elementsValue, ...beamlinesValue];
        let findBeamlineOrElementById = (id: number): ArrayFieldElement<ModelState> => {
            return _allItems.find(i => i.item.id === id || i.item._id === id);
        }

        let currentBeamline = beamlinesValue.find(beam => beam.item.id === selectedBeamlineHandle.value).item;
        let removeElement = (index: number) => {
            let bv = cloneDeep(beamlinesHandle.value) as FormFieldState<ArrayFieldState<FormModelState>>;
            let b = bv.value.find(b => b.item.id.value === selectedBeamlineHandle.value);
            console.log("b", b);
            let v = [...b.item.items.value];
            v.splice(index, 1);
            b.item.items.value = v;
            beamlinesHandle.write(bv, store.getState(), dispatch);
        }

        console.log("during update", currentBeamline.items);
        console.log("elements during update", _allItems.map(i => i.item.id || i.item._id))
        let beamlineElements = (currentBeamline.items as number[]).map(findBeamlineOrElementById)

        let [shownElement, updateShownElement] = useState<{
            template: TemplateSettings,
            aliases: ArrayAliases
        }>(undefined);

        return (
            <>
                <div className="d-flex flex-row" style={{ flexWrap: "wrap", rowGap: "1rem" }}>
                    <HoverController>
                        {
                            (hover) => {
                                return beamlineElements.map((e, idx) => {
                                    let id = (e.item._id !== undefined ? e.item._id : e.item.id) as number;
                                    let template = e.item.type !== undefined ? getTemplateSettingsByType((e.item.type as string), this.config.elementTemplates) : undefined;
                                    let aliases: ArrayAliases = e.item.type !== undefined ? [
                                        {
                                            realSchemaName: e.item.type as string,
                                            realDataLocation: {
                                                modelName: elementsDependency.modelName,
                                                fieldName: elementsDependency.fieldName,
                                                index: elementsValue.findIndex(e => e.item._id === id)
                                            },
                                            fake: e.item.type as string
                                        }
                                    ] : undefined;
                                    return (
                                        <div key={`${id}-${idx}`} className="d-flex flex-row flex-nowrap" onMouseEnter={() => hover.aquireHover(idx)} onMouseLeave={() => hover.releaseHover(idx)}>
                                            <Badge bg="primary" onDoubleClick={() => {
                                                    updateShownElement({
                                                        template,
                                                        aliases
                                                    })
                                                }
                                            }>
                                                {`${e.item.name as string}`}
                                            </Badge>
                                            <div style={{width: "25px", height: "25px", marginLeft: "5px"}}>
                                                <div style={{ display: hover.checkHover(idx) ? "block" : "none" }}>
                                                    <FontAwesomeIcon icon={Icon.faClose} onClick={() => removeElement(idx)}/>
                                                </div>
                                            </div>
                                        </div>
                                    )
                                })
                            }
                        }
                    </HoverController>
                </div>
                {shownElement && <MadxBeamlineElementEditor aliases={shownElement.aliases} template={shownElement.template} onHide={() => updateShownElement(undefined)}/>}
            </>
        )
    }
}
