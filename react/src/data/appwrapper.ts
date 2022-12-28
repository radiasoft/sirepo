import React from "react"
import { SimulationInfo } from "../component/simulation"
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

export type AuthMethod = "basic" | "bluesky" | "email" | "github" | "guest";

export type LoginStatus = {
    avatarUrl: string | null,
    displayName: string | null,
    guestIsOnlyMethod: boolean,
    isGuestUser: boolean,
    isLoggedIn: boolean,
    isLoginExpired: boolean,
    paymentPlan: string,
    jobRunModeMap: {[runType: string]: string},
    method: AuthMethod | null,
    needCompleteRegistration: boolean,
    roles: string[],
    slackUri: string,
    userName: string | null,
    visibleMethod: AuthMethod,
    uid: string | null
}

export const CSimulationList = React.createContext<SimulationListItem[]>(undefined);
export const CSimulationInfoPromise = React.createContext<Promise<SimulationInfo>>(undefined);
export const CAppName = React.createContext<string>(undefined);
export const CSchema = React.createContext<Schema>(undefined);
export const CLoginStatus = React.createContext<LoginStatus>(undefined);

export class AppWrapper {
    constructor(private appName: string) {

    }

    // TODO: this should he housed elsewhere
    getPaymentPlanName = (paymentPlan: string, schema: Schema): string => {
        return schema.constants.paymentPlans[paymentPlan];
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
    getLoginStatus: () => Promise<LoginStatus> = async () => {
        return await fetch('/auth-state2').then(async (resp) => await resp.json() as LoginStatus)
    }

    doGuestLogin = (): Promise<void> => {
        return fetch(`/auth-guest-login/${this.appName}`).then();
    }

    doEmailLogin = (email: string): Promise<void> => {
        return fetch(`/auth-email-login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email,
                simulationType: this.appName
            })
        }).then();
    }
}
