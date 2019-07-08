epicsEnvSet("IOC","")
epicsEnvSet("TOP", ".")
epicsEnvSet("EPICS_BASE","/home/vagrant/epics")

## Load record instances
dbLoadRecords "beam_line_example.db"

iocInit
epicsEnvShow EPICS_CA_SERVER_PORT
