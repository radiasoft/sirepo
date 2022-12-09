import React from "react"
import { compileSchemaFromJson, mergeSchemaJson, Schema } from "../utility/schema"

export type ApiSimulation = {
    documentationUrl: string,
    folder: string,
    isExample: boolean,
    lastModified: number,
    name: string,
    notes: string,
    simulationId: string,
    simulationSerial: number
}

export type SimulationListItem = {
    folder: string,
    isExample: boolean,
    name: string,
    simulationId: string,
    simulation: ApiSimulation
}

export type LoginStatus = {
    isLoggedIn: boolean,
    loginRedirect?: string
}

export const CSimulationList = React.createContext<SimulationListItem[]>(undefined);
export const CSimulationInfoPromise = React.createContext<Promise<any>>(undefined);
export const CAppName = React.createContext<string>(undefined);
export const CSchema = React.createContext<Schema>(undefined);

export class AppWrapper {
    constructor(private appName: string) {

    }

    getAppRootLink: () => string = () => {
        return `/react/${this.appName}`;
    }

    getSchema = (): Promise<Schema> => {
        return new Promise<Schema>((resolve, reject) => {
            Promise.all([
                fetch(`/static/react-json/common-schema.json`),
                fetch(`/static/react-json/${this.appName}-schema.json`)
            ]).then(([commonResp, appResp]) => {
                Promise.all([
                    commonResp.json(), 
                    appResp.json()
                ]).then(([commonJson, appJson]) => {
                    let schemaJson = mergeSchemaJson(commonJson, appJson)
                    resolve(compileSchemaFromJson(schemaJson));
                })
            })
        })
    }

    private simulationListPromise: () => Promise<Response> = () => {
        return new Promise((resolve, reject) => {
            fetch('/simulation-list', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    simulationType: this.appName
                })
            }).then(async (resp) => {
                resolve(resp);
            })
        })
    }

    getSimulationList = (): Promise<SimulationListItem[]> => {
        return new Promise((resolve, reject) => {
            this.simulationListPromise().then(async (resp) => {
                let simulationList = await resp.json() as SimulationListItem[];
                resolve(simulationList);
            })
        })
    }

    // TODO @garsuga: this should be its own api call, http errors should be used to signal login missing
    getIsLoggedIn: () => Promise<LoginStatus> = () => {
        return new Promise((resolve, reject) => {
            this.simulationListPromise().then(async (resp) => {
                let r = await resp.json();
                if(r.state) {
                    if(r.state === "srException") {
                        resolve({ isLoggedIn: false, loginRedirect: r.srException.routeName })
                    } else {
                        throw new Error(`unknown state=${JSON.stringify(r.state)} in simulation list response=${JSON.stringify(r)}`);
                    }
                } else {
                    resolve({ isLoggedIn: true });
                }
            })
        })
    }

    doGuestLogin = (): Promise<void> => {
        return new Promise<void>((resolve, reject) => fetch(`/auth-guest-login/${this.appName}`).then(() => resolve()));
    }
}
