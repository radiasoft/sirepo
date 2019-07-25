epicsEnvSet("IOC","")
epicsEnvSet("TOP", ".")

## Load record instances
dbLoadRecords "beam_line_example.db"

iocInit
epicsEnvShow EPICS_CA_SERVER_PORT
