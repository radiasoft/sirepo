import { pollRunReport } from "../utility/compute";


export class ReportEventManager {
    constructor() {
        this.reportEventListeners = {};
    }

    onReportData = (report, callback) => {
        let reportListeners = this.reportEventListeners[report] || [];
        reportListeners.push(callback);
        this.reportEventListeners[report] = reportListeners;
    }

    startReport = ({
        appName,
        models,
        simulationId,
        report
    }) => {
        pollRunReport({
            appName,
            models,
            simulationId,
            report,
            pollInterval: 500,
            callback: (simulationData) => {
                let reportListeners = this.reportEventListeners[report] || [];
                for(let reportListener of reportListeners) {
                    reportListener(simulationData);
                }
            }
        })
    }
}
