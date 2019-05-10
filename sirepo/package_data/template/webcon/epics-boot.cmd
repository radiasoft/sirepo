epicsEnvSet("IOC","")
epicsEnvSet("TOP", ".")
epicsEnvSet("EPICS_BASE","/home/vagrant/epics")

## Register all support components
dbLoadDatabase "beam_line_example.dbd"
beam_line_example_registerRecordDeviceDriver pdbbase

## Load record instances
dbLoadTemplate "user.substitutions"
dbLoadRecords "beam_line_exampleVersion.db", "user=vagrant"

iocInit
