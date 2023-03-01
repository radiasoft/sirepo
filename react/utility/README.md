# Schema Conversion Script
## Setup
```npm install -g typescript commander```
## Build
```tsc --target es6 --moduleResolution node convertschema.ts```
## Run
```node convertschema.js <infile> [-o, --output <outfile>]```
## Usage
After converting a schema file the `model` and `type` sections are ready to use. For views, two sections are handled, `view` and `unhandled`.
### Unhandled
This section contains all views that could not be converted with the script. They will need to be manually updated to the new format.
### View
Views are converted panel-wise from the old format. This section contains all of the panels in the new format. Additional steps are needed to complete the schema conversion.
* A `navTabs` layout needs to be created and the panels need to be separated between the tabs.
* Panels within each tab need to be placed inside a `waterfall` layout.
* Panels need a `title` attribute in their `config`.
* A `navbarModalButton` is needed to allow the simulation to be renamed.
* Report layouts need to be added to panels that would typically contain them. These are not defined in the schema in the old format.
* Hiding and showing logic for panels, fields, reports, etc, needs to be defined.
