import { Layout } from "../layout";

export type MadxBeamlineElementsConfig = {
    beamlinesDependency: string,
    elementsDependency: string,
    elementsTemplates: {
        group: string,
        type: string,
        name: string,
        items: SchemaLayoutJson[]
    }[]
}

export class MadxBeamlineElementsLayout extends Layout<MadxBeamlineElementsConfig, {}> {
    constructor(config: MadxBeamlineElementsConfig) {
        super(config);
    }


}
