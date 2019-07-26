
// required for unit tests, normally loaded by the application in srw.html
var SIREPO = {
    APP_VERSION: '1',
    APP_NAME: 'srw',
};

// disable initial schema request
$.ajax = function() {};

SIREPO.APP_SCHEMA = {
    "version": "20160912.000000",
    "simulationType": "srw",
    "appInfo": {
        "srw": {
            "shortName": "SRW",
            "longName": "Synchrotron Radiation Workshop",
        },
    },
    "constants": {
        "clientCookie": "sirepo_cookie_js",
        "oneDayMillis": 86400000
    },
    "cookies": {
        "firstVisit": {
            "name": "1st_vis",
            "value": "a"
        },
        "getStarted": {
            "name": "strt",
            "value": "a"
        },
        "listView": {
            "name": "lv",
            "value": false,
            "valType": "b"
        },
        "login": {
            "name": "login",
            "value": "a",
            "timeout": 1
        }
    },
    "route": {
        "copyNonSessionSimulation": "/copy-non-session-simulation",
        "copySimulation": "/copy-simulation",
        "deleteSimulation": "/delete-simulation",
        "downloadDataFile": "/download-data-file/<simulation_type>/<simulation_id>/<model>/<frame>",
        "downloadFile": "/download-file/<simulation_type>/<simulation_id>/<filename>",
        "errorLogging": "/error-logging",
        "findByName": "/find-by-name/<simulation_type>/<application_mode>/<simulation_name>",
        "getApplicationData": "/get-application-data",
        "importFile": "/import-file/<simulation_type>",
        "listFiles": "/file-list/<simulation_type>/<simulation_id>/<file_type>",
        "listSimulations": "/simulation-list",
        "newSimulation": "/new-simulation",
        "pythonSource": "/python-source/<simulation_type>/<simulation_id>",
        "root": "/<simulation_type>",
        "runCancel": "/run-cancel",
        "runSimulation": "/run-simulation",
        "runStatus": "/run-status",
        "saveSimulationData": "/save-simulation",
        "simulationData": "/simulation/<simulation_type>/<simulation_id>/<pretty>",
        "simulationFrame": "/simulation-frame/<frame_id>",
        "simulationSchema": "/simulation-schema",
        "updateFolder": "/update-folder",
        "uploadFile": "/upload-file/<simulation_type>/<simulation_id>/<file_type>"
    },
    "enum": {
        "AnalyticalTreatment": [
            ["0", "0 - Standard"],
            ["1", "1 - Quadratic Term"],
            ["2", "2 - Quadratic Term - Special"],
            ["3", "3 - From Waist"],
            ["4", "4 - To Waist"]
        ],
        "ApertureShape": [
            ["r", "Rectangular"],
            ["c", "Circular"]
        ],
        "ApplicationMode": [
            ["default", "Expert"],
            ["calculator", "SR Calculator"],
            ["light-sources", "Light Source Facilities"],
            ["wavefront", "Wavefront Propagation"]
        ],
        "BeamDefinition": [
            ["t", "Twiss"],
            ["m", "Moments"]
        ],
        "Characteristic": [
            ["0", "Single-Electron Intensity"],
            ["1", "Multi-Electron Intensity (disregarding energy spread)"],
            ["4", "Single-Electron Radiation Phase"],
            ["5", "Re(E): Real part of Single-Electron Electric Field"],
            ["6", "Im(E): Imaginary part of Single-Electron Electric Field"]
        ],
        "CRLMaterial": [
            ["User-defined", "User-defined"],
            ["Al", "Al"],
            ["Be", "Be"],
            ["B", "B"],
            ["C", "C"],
            ["Cu", "Cu"],
            ["Li", "Li"],
            ["Mo", "Mo"],
            ["Si", "Si"],
            ["SiO2", "SiO2"],
            ["W", "W"]
        ],
        "CRLMethod": [
            ["server", "Server http://henke.lbl.gov"],
            ["file", "Saved data file"],
            ["calculation", "Calculate analytically"]
        ],
        "CRLShape": [
            ["1", "Parabolic"],
            ["2", "Circular"]
        ],
        "CrystalMaterial": [
            ["Unknown", "Unknown"],
            ["Si (SRW)", "Silicon (SRW)"],
            ["Silicon (X0h)", "Silicon (X0h server)"],
            ["Germanium (X0h)", "Germanium (X0h server)"],
            ["Diamond (X0h)", "Diamond (X0h server)"]
        ],
        "DriftCalculationMethod": [
            ["auto", "Automatic"],
            ["manual", "Manual"]
        ],
        "EstimateTimeMomentParameters": [
            ["auto", "Automatic"],
            ["manual", "Manual"]
        ],
        "FieldUnits": [
            ["0", "Arbitrary Units"],
            ["1", "ph/s/.1%bw/mm²"],
            ["2", "J/eV/mm²"]
        ],
        "Flux": [
            ["1", "Flux"],
            ["2", "Flux per Unit Surface"]
        ],
        "FluxMethod": [
            ["1", "Auto-Undulator"],
            ["2", "Auto-Wiggler"],
            ["-1", "Use Approximate Method"]
        ],
        "FocalPlane": [
            ["1", "Horizontal"],
            ["2", "Vertical"],
            ["3", "Both"]
        ],
        "FiberFocalPlane": [
            ["1", "Horizontal (fiber is parallel to vertical axis)"],
            ["2", "Vertical (fiber is parallel to horizontal axis)"],
            ["3", "Both"]
        ],
        "GaussianBeamPolarization": [
            ["1", "Linear Horizontal"],
            ["2", "Linear Vertical"],
            ["3", "Linear 45 degrees"],
            ["4", "Linear 135 degrees"],
            ["5", "Circular Right"],
            ["6", "Circular Left"]
        ],
        "IntensityMethod": [
            ["0", "Manual"],
            ["1", "Auto-Undulator"],
            ["2", "Auto-Wiggler"]
        ],
        "MagneticField": [
            ["1", "Approximate"],
            ["2", "Accurate (tabulated)"]
        ],
        "MillerIndicesRange": [
            ["0", "0"],
            ["1", "1"],
            ["2", "2"],
            ["3", "3"],
            ["4", "4"],
            ["5", "5"],
            ["6", "6"],
            ["7", "7"],
            ["8", "8"],
            ["9", "9"],
            ["10", "10"],
            ["-1", "-1"],
            ["-2", "-2"],
            ["-3", "-3"],
            ["-4", "-4"],
            ["-5", "-5"],
            ["-6", "-6"],
            ["-7", "-7"],
            ["-8", "-8"],
            ["-9", "-9"],
            ["-10", "-10"]
        ],
        "MirrorApertureShape": [
            ["r", "Rectangular"],
            ["e", "Elliptical"]
        ],
        "MirrorOrientation": [
            ["x", "Horizontal"],
            ["y", "Vertical"]
        ],
        "MultipoleOrientation": [
            ["n", "Horizontal"],
            ["s", "Vertical"]
        ],
        "PlotAxis": [
            ["x", "Horizontal"],
            ["y", "Vertical"]
        ],
        "Polarization": [
            ["0", "Linear Horizontal"],
            ["1", "Linear Vertical"],
            ["2", "Linear 45 degrees"],
            ["3", "Linear 135 degrees"],
            ["4", "Circular Right"],
            ["5", "Circular Left"],
            ["6", "Total"]
        ],
        "PowerDensityMethod": [
            ["1", "Near Field"],
            ["2", "Far Field"]
        ],
        "RandomGenerationMethod": [
            ["1", "Standard Pseudo-Random Number Generator"],
            ["2", "Halton Sequences"],
            ["3", "LPtau sequences (to be implemented)"]
        ],
        "SamplingMethod": [
            ["1", "Automatic"],
            ["2", "Manual"]
        ],
        "SimulationState": [
            ["initial", "Initial State"],
            ["running", "Running"],
            ["completed", "Completed"],
            ["canceled", "Canceled"]
        ],
        "SourceType": [
            ["u", "Electron Beam with Idealized Undulator"],
            ["t", "Electron Beam with Tabulated Undulator"],
            ["m", "Electron Beam with Dipole"],
            ["g", "Gaussian Beam"]
        ],
        "StokesParameter": [
            ["0", "Coordinate"],
            ["1", "Angular"]
        ],
        "Symmetry": [
            ["1", "Symmetrical"],
            ["-1", "Anti-symmetrical"]
        ],
        "UndulatorType": [
            ["u_i", "Idealized"],
            ["u_t", "Tabulated"]
        ]
    },
    "model": {
        "aperture": {
            "title": ["Element Name", "String"],
            "position": ["Nominal Position [m]", "Float"],
            "shape": ["Shape", "ApertureShape"],
            "horizontalSize": ["Horizontal Size [mm]", "Float"],
            "verticalSize": ["Vertical Size [mm]", "Float"],
            "horizontalOffset": ["Horizontal Offset [mm]", "Float"],
            "verticalOffset": ["Vertical Offset [mm]", "Float"]
        },
        "crl": {
            "title": ["Element Name", "String"],
            "position": ["Nominal Position [m]", "Float"],
            "focalPlane": ["Focal Plane", "FocalPlane"],
            "material": ["Material of the CRL", "CRLMaterial"],
            "method": ["Method of Getting Delta/Attenuation Length", "CRLMethod"],
            "refractiveIndex": ["Refractive Index Decrement of Material", "Float", "", "Tooltip"],
            "attenuationLength": ["Attenuation Length [m]", "Float", "", "Tooltip"],
            "focalDistance": ["CRL Focal Distance [m]", "Float"],
            "absoluteFocusPosition": ["CRL Focus Position from Source [m]", "Float"],
            "shape": ["Shape", "CRLShape"],
            "horizontalApertureSize": ["Horizontal Aperture Size [mm]", "Float"],
            "verticalApertureSize": ["Vertical Aperture Size [mm]", "Float"],
            "radius": ["Radius on Tip of Parabola [m]", "Float"],
            "tipRadius": ["Radius on Tip of Parabola [µm]", "Float"],
            "numberOfLenses": ["Number of Lenses", "Integer"],
            "wallThickness": ["Wall Thickness at Tip of Parabola [m]", "Float"],
            "tipWallThickness": ["Wall Thickness at Tip of Parabola [µm]", "Float"]
        },
        "crystal": {
            "title": ["Element Name", "String"],
            "position": ["Nominal Position [m]", "Float"],
            "material": ["", "CrystalMaterial"],
            "h": ["h", "MillerIndicesRange"],
            "k": ["k", "MillerIndicesRange"],
            "l": ["l", "MillerIndicesRange"],
            "energy": ["Average photon energy the crystal should be oriented for [eV]", "Float"],
            "grazingAngle": ["Diffraction plane angle [rad]", "Float"],
            "asymmetryAngle": ["Asymmetry angle [rad]", "Float"],
            "rotationAngle": ["Rotation angle [rad]", "Float"],
            "crystalThickness": ["Crystal thickness [m]", "Float"],
            "dSpacing": ["Crystal reflecting planes d-spacing [A]", "Float"],
            "psi0r": ["0-th Fourier component", "Float"],
            "psi0i": ["0-th Fourier component", "Float"],
            "psiHr": ["H-th Fourier component", "Float"],
            "psiHi": ["H-th Fourier component", "Float"],
            "psiHBr": ["-H-th Fourier component", "Float"],
            "psiHBi": ["-H-th Fourier component", "Float"],
            "nvx": ["Horizontal coordinate", "Float"],
            "nvy": ["Vertical coordinate", "Float"],
            "nvz": ["Longitudinal coordinate", "Float"],
            "tvx": ["Horizontal coordinate", "Float"],
            "tvy": ["Vertical coordinate", "Float"],
            "heightProfileFile": ["Height Profile Data File", "MirrorFile"],
            "orientation": ["Orientation of Reflection Plane", "MirrorOrientation"],
            "heightAmplification": ["Height Amplification Coefficient", "Float"]
        },
        "electronBeam": {
            "beamSelector": ["Beam Name", "BeamList"],
            "name": ["Beam Name", "String"],
            "energy": ["Energy [GeV]", "Float"],
            "current": ["Current [A]", "Float"],
            "energyDeviation": ["Average Energy Deviation [GeV]", "Float"],
            "rmsSpread": ["RMS Energy Spread", "Float"],
            "horizontalPosition": ["Average Horizontal Position [mm]", "Float"],
            "verticalPosition": ["Average Vertical Position [mm]", "Float"],
            "driftCalculationMethod": ["Drift Calculation Method", "DriftCalculationMethod"],
            "drift": ["Drift [m]", "Float"],
            "beamDefinition": ["Beam Definition by", "BeamDefinition"],
            "horizontalEmittance": ["Horizontal Emittance [nm]", "Float"],
            "horizontalBeta": ["Horizontal Beta [m]", "Float"],
            "horizontalAlpha": ["Horizontal Alpha [rad]", "Float"],
            "horizontalDispersion": ["Horizontal Dispersion [m]", "Float"],
            "horizontalDispersionDerivative": ["Horizontal Dispersion Derivative [rad]", "Float"],
            "verticalEmittance": ["Vertical Emittance [nm]", "Float"],
            "verticalBeta": ["Vertical Beta [m]", "Float"],
            "verticalAlpha": ["Vertical Alpha [rad]", "Float"],
            "verticalDispersion": ["Vertical Dispersion [m]", "Float"],
            "verticalDispersionDerivative": ["Vertical Dispersion Derivative [rad]", "Float"],
            "rmsSizeX": ["RMS Size [µm]", "Float"],
            "rmsDivergX": ["RMS Divergence [µrad]", "Float"],
            "xxprX": ["<(x-<x>)(x'-<x'>)> [nm]", "Float"],
            "rmsSizeY": ["RMS Size [µm]", "Float"],
            "rmsDivergY": ["RMS Divergence [µrad]", "Float"],
            "xxprY": ["<(x-<x>)(x'-<x'>)> [nm]", "Float"]
        },
        "ellipsoidMirror": {
            "title": ["Element Name", "String"],
            "position": ["Nominal Position [m]", "Float"],
            "firstFocusLength": ["Distance from Source to Mirror Center (p) [m]", "Float"],
            "focalLength": ["Distance from Mirror Center to Second Focus (q) [m]", "Float"],
            "tangentialSize": ["Tangential Size [m]", "Float"],
            "sagittalSize": ["Sagittal Size [m]", "Float"],
            "grazingAngle": ["Grazing Angle [mrad]", "Float"],
            "normalVectorX": ["Horizontal", "Float"],
            "normalVectorY": ["Vertical", "Float"],
            "normalVectorZ": ["Longitudinal", "Float"],
            "tangentialVectorX": ["Horizontal", "Float"],
            "tangentialVectorY": ["Vertical", "Float"],
            "heightProfileFile": ["Height Profile Data File", "MirrorFile"],
            "orientation": ["Orientation of Reflection Plane", "MirrorOrientation"],
            "heightAmplification": ["Height Amplification Coefficient", "Float"]
        },
        "fiber": {
            "title": ["Element Name", "String"],
            "position": ["Nominal Position [m]", "Float"],
            "focalPlane": ["Plane of Focusing", "FiberFocalPlane"],
            "method": ["Method of Getting Delta/Attenuation Length", "CRLMethod"],
            "externalMaterial": ["External Material", "CRLMaterial"],
            "externalRefractiveIndex": ["Refractive Index Decrement", "Float", "", "Tooltip"],
            "externalAttenuationLength": ["Attenuation Length [m]", "Float", "", "Tooltip"],
            "externalDiameter": ["External Diameter [m]", "Float"],
            "coreMaterial": ["Core Material", "CRLMaterial"],
            "coreRefractiveIndex": ["Refractive Index Decrement", "Float", "", "Tooltip"],
            "coreAttenuationLength": ["Attenuation Length [m]", "Float", "", "Tooltip"],
            "coreDiameter": ["Core Diameter [m]", "Float"],
            "horizontalCenterPosition": ["Horizontal Center Position [m]", "Float"],
            "verticalCenterPosition": ["Vertical Center Position [m]", "Float"]
        },
        "fluxAnimation": {
            "distanceFromSource": ["Distance From Source [m]", "Float"],
            "initialEnergy": ["Initial Photon Energy [eV]", "Float"],
            "finalEnergy": ["Final Photon Energy [eV]", "Float"],
            "photonEnergyPointCount": ["Number of Points vs Photon Energy", "Integer"],
            "numberOfMacroElectrons": ["Number of Macro-Electrons", "Integer", "", "Number of macro-electrons for calculation of spectrum in case of arbitrary input magnetic field"],
            "horizontalPosition": ["Horizontal Center Position [mm]", "Float"],
            "horizontalApertureSize": ["Horizontal Aperture Size [mm]", "Float"],
            "verticalPosition": ["Vertical Center Position [mm]", "Float"],
            "verticalApertureSize": ["Vertical Aperture Size [mm]", "Float"],
            "initialHarmonic": ["Initial UR Spectral Harmonic", "Integer"],
            "finalHarmonic": ["Final UR Spectral Harmonic", "Integer"],
            "longitudinalPrecision": ["Longitudinal Integration Precision", "Float"],
            "azimuthalPrecision": ["Azimuthal Integration Precision", "Float"],
            "magneticField": ["Magnetic Field Treatment", "MagneticField"],
            "method": ["Flux Computation Method", "FluxMethod"],
            "precision": ["Relative Precision", "Float"],
            "fluxType": ["Entity to Calculate", "Flux"],
            "polarization": ["Polarization Component to Extract", "Polarization"]
        },
        "fluxReport": {
            "distanceFromSource": ["Distance From Source [m]", "Float"],
            "initialEnergy": ["Initial Photon Energy [eV]", "Float"],
            "finalEnergy": ["Final Photon Energy [eV]", "Float"],
            "photonEnergyPointCount": ["Number of Points vs Photon Energy", "Integer"],
            "horizontalPosition": ["Horizontal Center Position [mm]", "Float"],
            "horizontalApertureSize": ["Horizontal Aperture Size [mm]", "Float"],
            "verticalPosition": ["Vertical Center Position [mm]", "Float"],
            "verticalApertureSize": ["Vertical Aperture Size [mm]", "Float"],
            "initialHarmonic": ["Initial UR Spectral Harmonic", "Integer"],
            "finalHarmonic": ["Final UR Spectral Harmonic", "Integer"],
            "longitudinalPrecision": ["Longitudinal Integration Precision", "Float"],
            "azimuthalPrecision": ["Azimuthal Integration Precision", "Float"],
            "fluxType": ["Entity to Calculate", "Flux"],
            "polarization": ["Polarization Component to Extract", "Polarization"]
        },
        "gaussianBeam": {
            "waistX": ["Horizontal Waist Offset [µm]", "Float"],
            "waistY": ["Vertical Waist Offset [µm]", "Float"],
            "waistZ": ["Longitudinal Waist Position [µm]", "Float"],
            "waistAngleX": ["Horizontal Beam Angle [mrad]", "Float"],
            "waistAngleY": ["Vertical Beam Angle [mrad]", "Float"],
            "energyPerPulse": ["Energy per Pulse [J]", "Float"],
            "polarization": ["Polarization", "GaussianBeamPolarization"],
            "rmsSizeX": ["Horizontal RMS Waist [µm]", "Float"],
            "rmsSizeY": ["Vertical RMS Waist [µm]", "Float"],
            "rmsPulseDuration": ["RMS Pulse Duration [ps]", "Float"]
        },
        "grating": {
            "title": ["Element Name", "String"],
            "position": ["Nominal Position [m]", "Float"],
            "tangentialSize": ["Tangential Size [m]", "Float"],
            "sagittalSize": ["Sagittal Size [m]", "Float"],
            "grazingAngle": ["Grazing Angle [mrad]", "Float"],
            "normalVectorX": ["Horizontal", "Float"],
            "normalVectorY": ["Vertical", "Float"],
            "normalVectorZ": ["Longitudinal", "Float"],
            "tangentialVectorX": ["Horizontal", "Float"],
            "tangentialVectorY": ["Vertical", "Float"],
            "diffractionOrder": ["Diffraction Order", "Float"],
            "grooveDensity0": ["Groove Density a0", "Float"],
            "grooveDensity1": ["Groove Density a1y", "Float"],
            "grooveDensity2": ["Groove Density a2y²", "Float"],
            "grooveDensity3": ["Groove Density a3y³", "Float"],
            "grooveDensity4": ["Groove Density a4y⁴", "Float"]
        },
        "initialIntensityReport": {
            "polarization": ["Polarization Component to Extract", "Polarization"],
            "characteristic": ["Characteristic to be Extracted", "Characteristic"],
            "fieldUnits": ["Intensity Units", "FieldUnits"]
        },
        "intensityReport": {
            "distanceFromSource": ["Distance From Source [m]", "Float"],
            "initialEnergy": ["Initial Photon Energy [eV]", "Float"],
            "finalEnergy": ["Final Photon Energy [eV]", "Float"],
            "photonEnergyPointCount": ["Number of Points vs Photon Energy", "Integer"],
            "horizontalPosition": ["Horizontal Position [mm]", "Float"],
            "verticalPosition": ["Vertical Position [mm]", "Float"],
            "magneticField": ["Magnetic Field Treatment", "MagneticField"],
            "method": ["Single-Electron Spectrum Computation Method", "IntensityMethod"],
            "precision": ["Relative Precision", "Float"],
            "polarization": ["Polarization Component to Extract", "Polarization"],
            "fieldUnits": ["Intensity Units", "FieldUnits"]
        },
        "lens": {
            "title": ["Element Name", "String"],
            "position": ["Nominal Position [m]", "Float"],
            "horizontalFocalLength": ["Horizontal Focal Length [m]", "Float"],
            "verticalFocalLength": ["Vertical Focal Length [m]", "Float"],
            "horizontalOffset": ["Horizontal Offset [mm]", "Float"],
            "verticalOffset": ["Vertical Offset [mm]", "Float"]
        },
        "mirror": {
            "title": ["Element Name", "String"],
            "position": ["Nominal Position [m]", "Float"],
            "heightProfileFile": ["Height Profile Data File", "MirrorFile"],
            "orientation": ["Orientation of Reflection Plane", "MirrorOrientation"],
            "grazingAngle": ["Grazing Angle [mrad]", "Float"],
            "heightAmplification": ["Height Amplification Coefficient", "Float"],
            "horizontalTransverseSize": ["Horizontal Transverse Size [mm]", "Float"],
            "verticalTransverseSize": ["Vertical Transverse Size [mm]", "Float"]
        },
        "mirrorReport": {},
        "multiElectronAnimation": {
            "stokesParameter": ["Representation of Stokes Parameters", "StokesParameter"],
            "numberOfMacroElectrons": ["Number of Macro-Electrons", "Integer", "", "Number of macro-electrons (coherent wavefronts) for calculation of multi-electron wavefront propagation"]
        },
        "multipole": {
            "field": ["Magnetic Field [T]", "Float"],
            "distribution": ["Orientation", "MultipoleOrientation"],
            "length": ["Effective Length [m]", "Float"]
        },
        "obstacle": {
            "title": ["Element Name", "String"],
            "position": ["Nominal Position [m]", "Float"],
            "shape": ["Shape", "ApertureShape"],
            "horizontalSize": ["Horizontal Size [mm]", "Float"],
            "verticalSize": ["Vertical Size [mm]", "Float"],
            "horizontalOffset": ["Horizontal Offset [mm]", "Float"],
            "verticalOffset": ["Vertical Offset [mm]", "Float"]
        },
        "powerDensityReport": {
            "distanceFromSource": ["Distance From Source [m]", "Float"],
            "horizontalPosition": ["Horizontal Center Position [mm]", "Float"],
            "horizontalRange": ["Range of Horizontal Position [mm]", "Float"],
            "verticalPosition": ["Vertical Center Position [mm]", "Float"],
            "verticalRange": ["Range of Vertical Position [mm]", "Float"],
            "precision": ["Relative Precision", "Float"],
            "method": ["Power Density Computation Method", "PowerDensityMethod"],
            "horizontalPointCount": ["Number of Points vs Horizontal Position", "Integer"],
            "verticalPointCount": ["Number of Points vs Vertical Position", "Integer"]
        },
        "simulation": {
            "name": ["Name", "String"],
            "sourceType": ["Source Type", "SourceType"],
            "photonEnergy": ["Photon Energy [eV]", "Float"],
            "facility": ["Facility", "String"],
            "isExample": ["Is Example Simulation", "String"],
            "sampleFactor": ["Sampling Factor", "Float"],
            "horizontalPointCount": ["Number of Points vs Horizontal Position", "Integer"],
            "verticalPointCount": ["Number of Points vs Vertical Position", "Integer"],
            "outOfSessionSimulationId": ["Out of Session Simulation ID", "String"],
            "samplingMethod": ["Sampling Method", "SamplingMethod"],
            "horizontalPosition": ["Horizontal Center Position [mm]", "Float"],
            "horizontalRange": ["Range of Horizontal Position [mm]", "Float"],
            "verticalPosition": ["Vertical Center Position [mm]", "Float"],
            "verticalRange": ["Range of Vertical Position [mm]", "Float"],
            "documentationUrl": ["Documentation URL", "OptionalString"]
        },
        "simulationFolder": {
            "name": ["Folder Name", "String"]
        },
        "simulationStatus": {
        },
        "sourceIntensityReport": {
            "distanceFromSource": ["Distance From Source [m]", "Float"],
            "polarization": ["Polarization Component to Extract", "Polarization"],
            "characteristic": ["Characteristic to be Extracted", "Characteristic"],
            "fieldUnits": ["Intensity Units", "FieldUnits"],
            "magneticField": ["Magnetic Field Treatment", "MagneticField"],
            "precision": ["Relative Precision", "Float"]
        },
        "sphericalMirror": {
            "title": ["Element Name", "String"],
            "position": ["Nominal Position [m]", "Float"],
            "radius": ["Radius of Surface Curvature [m]", "Float"],
            "tangentialSize": ["Tangential Size [m]", "Float"],
            "sagittalSize": ["Sagittal Size [m]", "Float"],
            "grazingAngle": ["Grazing Angle [mrad]", "Float"],
            "normalVectorX": ["Horizontal", "Float"],
            "normalVectorY": ["Vertical", "Float"],
            "normalVectorZ": ["Longitudinal", "Float"],
            "tangentialVectorX": ["Horizontal", "Float"],
            "tangentialVectorY": ["Vertical", "Float"],
            "heightProfileFile": ["Height Profile Data File", "MirrorFile"],
            "orientation": ["Orientation of Reflection Plane", "MirrorOrientation"],
            "heightAmplification": ["Height Amplification Coefficient", "Float"]
        },
        "tabulatedUndulator": {
            "undulatorType": ["Type of Undulator", "UndulatorType"],
            "undulatorParameter": ["Deflecting Parameter (K)", "Float"],
            "gap": ["Magnetic Gap [mm]", "Float"],
            "phase": ["Magnet Arrays Shift [mm]", "Float"],
            "period": ["Period [mm]", "Float"],
            "length": ["Length [m]", "Float"],
            "longitudinalPosition": ["Longitudinal Central Position [m]", "Float"],
            "horizontalAmplitude": ["Horizontal Magnetic Field [T]", "Float"],
            "horizontalInitialPhase": ["Initial Horizontal Phase [rad]", "Float"],
            "horizontalSymmetry": ["Horizontal Symmetry", "Symmetry"],
            "verticalAmplitude": ["Vertical Magnetic Field [T]", "Float"],
            "verticalInitialPhase": ["Initial Vertical Phase [rad]", "Float"],
            "verticalSymmetry": ["Vertical Symmetry", "Symmetry"],
            "magneticFile": ["Magnetic Data File", "MagneticZipFile"],
            "indexFile": ["Magnetic Zip Index File", "String"]
        },
        "trajectoryReport": {
            "timeMomentEstimation": ["Estimate Time Moment Parameters", "EstimateTimeMomentParameters"],
            "initialTimeMoment": ["Initial Time Moment (c*t) for Electron Trajectory Calculation [m]", "Float"],
            "finalTimeMoment": ["Final Time Moment (c*t) for Electron Trajectory Calculation [m]", "Float"],
            "numberOfPoints": ["Number of Points for Trajectory Calculation", "Integer"],
            "plotAxis": ["Axis to plot", "PlotAxis"],
            "magneticField": ["Magnetic Field Treatment", "MagneticField"]
        },
        "undulator": {
            "undulatorParameter": ["Deflecting Parameter (K)", "Float"],
            "period": ["Period [mm]", "Float"],
            "length": ["Length [m]", "Float"],
            "longitudinalPosition": ["Longitudinal Central Position [m]", "Float"],
            "horizontalAmplitude": ["Horizontal Magnetic Field [T]", "Float"],
            "horizontalSymmetry": ["Horizontal Symmetry", "Symmetry"],
            "horizontalInitialPhase": ["Initial Horizontal Phase [rad]", "Float"],
            "verticalAmplitude": ["Vertical Magnetic Field [T]", "Float"],
            "verticalSymmetry": ["Vertical Symmetry", "Symmetry"],
            "verticalInitialPhase": ["Initial Vertical Phase [rad]", "Float"]
        },
        "watch": {
            "title": ["Element Name", "String"],
            "position": ["Nominal Position [m]", "Float"]
        },
        "watchpointReport": {
            "polarization": ["Polarization Component to Extract", "Polarization"],
            "characteristic": ["Characteristic to be Extracted", "Characteristic"],
            "fieldUnits": ["Intensity Units", "FieldUnits"]
        }
    },
    "view": {
        "aperture": {
            "title": "Aperture",
            "basic": [],
            "advanced": [
                "title",
                "position",
                "shape",
                [
                    ["Horizontal", [
                        "horizontalSize",
                        "horizontalOffset"
                    ]],
                    ["Vertical", [
                        "verticalSize",
                        "verticalOffset"
                    ]]
                ]
            ]
        },
        "crl": {
            "title": "CRL",
            "basic": [],
            "advanced": [
                "title",
                "position",
                "focalPlane",
                "material",
                "method",
                "refractiveIndex",
                "attenuationLength",
                "focalDistance",
                "absoluteFocusPosition",
                "shape",
                "horizontalApertureSize",
                "verticalApertureSize",
                "tipRadius",
                "numberOfLenses",
                "tipWallThickness"
            ]
        },
        "crystal": {
            "title": "Crystal",
            "basic": [],
            "advanced": [
                ["Main Parameters", [
                    "title",
                    "position",
                    [
                        ["Material of the crystal", [
                            "material"
                        ]],
                        ["Miller's indices", [
                            "h",
                            "k",
                            "l"
                        ]]
                    ],
                    "energy",
                    "grazingAngle",
                    "asymmetryAngle",
                    "rotationAngle",
                    "crystalThickness",
                    "dSpacing",
                    [
                        ["Real part of crystal polarizability", [
                            "psi0r",
                            "psiHr",
                            "psiHBr"
                        ]],
                        ["Imaginary part of crystal polarizability", [
                            "psi0i",
                            "psiHi",
                            "psiHBi"
                        ]]
                    ],
                    [
                        ["Outward normal vector", [
                            "nvx",
                            "nvy",
                            "nvz"
                        ]],
                        ["Central tangential vector", [
                            "tvx",
                            "tvy"
                        ]]
                    ]
                ]],
                ["Height Profile", [
                    "heightProfileFile",
                    "orientation",
                    "heightAmplification"
                ]]
            ]
        },
        "electronBeam": {
            "title": "Electron Beam",
            "basic": [
                "beamSelector"
            ],
            "advanced": [
                "name",
                "energy",
                "current",
                "energyDeviation",
                "rmsSpread",
                "horizontalPosition",
                "verticalPosition",
                "driftCalculationMethod",
                "drift",
                "beamDefinition",
                [
                    ["Horizontal Twiss Parameters", [
                        "horizontalEmittance",
                        "horizontalBeta",
                        "horizontalAlpha",
                        "horizontalDispersion",
                        "horizontalDispersionDerivative"
                    ]],
                    ["Vertical Twiss Parameters", [
                        "verticalEmittance",
                        "verticalBeta",
                        "verticalAlpha",
                        "verticalDispersion",
                        "verticalDispersionDerivative"
                    ]]
                ],
                [
                    ["Horizontal Moments", [
                        "rmsSizeX",
                        "rmsDivergX",
                        "xxprX"
                    ]],
                    ["Vertical Moments", [
                        "rmsSizeY",
                        "rmsDivergY",
                        "xxprY"
                    ]]
                ]
            ]
        },
        "ellipsoidMirror": {
            "title": "Ellipsoid Mirror",
            "basic": [],
            "advanced": [
                ["Dimensions", [
                    "title",
                    "position",
                    "firstFocusLength",
                    "focalLength",
                    "tangentialSize",
                    "sagittalSize",
                    "grazingAngle",
                    [
                        ["Coordinates of Central Normal Vector", [
                            "normalVectorX",
                            "normalVectorY",
                            "normalVectorZ"
                        ]],
                        ["Coordinates of Central Tangential Vector", [
                            "tangentialVectorX",
                            "tangentialVectorY"
                        ]]
                    ]
                ]],
                ["Mirror Error", [
                    "heightProfileFile",
                    "orientation",
                    "heightAmplification"
                ]]
            ]
        },
        "fiber": {
            "title": "Fiber",
            "basic": [],
            "advanced": [
                "title",
                "position",
                "focalPlane",
                "horizontalCenterPosition",
                "verticalCenterPosition",
                "method",
                [
                    ["External", [
                        "externalMaterial",
                        "externalRefractiveIndex",
                        "externalAttenuationLength",
                        "externalDiameter"
                    ]],
                    ["Core", [
                        "coreMaterial",
                        "coreRefractiveIndex",
                        "coreAttenuationLength",
                        "coreDiameter"
                    ]]
                ]
            ]
        },
        "fluxAnimation": {
            "title": "Spectral Flux for Finite Emittance Electron Beam",
            "basic": [],
            "advanced": [
                ["Main", [
                    "distanceFromSource",
                    "initialEnergy",
                    "finalEnergy",
                    "photonEnergyPointCount",
                    "numberOfMacroElectrons",
                    [
                        ["Horizontal", [
                            "horizontalPosition",
                            "horizontalApertureSize"
                        ]],
                        ["Vertical", [
                            "verticalPosition",
                            "verticalApertureSize"
                        ]]
                    ],
                    "fluxType",
                    "polarization"
                ]],
                ["Accuracy", [
                    "magneticField",
                    "method",
                    "precision",
                    "initialHarmonic",
                    "finalHarmonic",
                    "longitudinalPrecision",
                    "azimuthalPrecision"
                ]]
            ]
        },
        "fluxReport": {
            "title": "Flux Report",
            "basic": [],
            "advanced": [
                ["Main", [
                    "distanceFromSource",
                    "initialEnergy",
                    "finalEnergy",
                    "photonEnergyPointCount",
                    [
                        ["Horizontal", [
                            "horizontalPosition",
                            "horizontalApertureSize"
                        ]],
                        ["Vertical", [
                            "verticalPosition",
                            "verticalApertureSize"
                        ]]
                    ],
                    "fluxType",
                    "polarization"
                ]],
                ["Accuracy", [
                    "initialHarmonic",
                    "finalHarmonic",
                    "longitudinalPrecision",
                    "azimuthalPrecision"
                ]]
            ]
        },
        "gaussianBeam": {
            "title": "Gaussian Beam",
            "basic": [
                "simulation.photonEnergy",
                "energyPerPulse"
            ],
            "advanced": [
                "simulation.photonEnergy",
                "energyPerPulse",
                "polarization",
                "rmsPulseDuration",
                "waistZ",
                [
                    ["Horizontal", [
                        "rmsSizeX",
                        "waistX",
                        "waistAngleX"
                    ]],
                    ["Vertical", [
                        "rmsSizeY",
                        "waistY",
                        "waistAngleY"
                    ]]
                ]
            ]
        },
        "grating": {
            "title": "Grating",
            "basic": [],
            "advanced": [
                ["Main Parameters", [
                    "title",
                    "position",
                    "tangentialSize",
                    "sagittalSize",
                    "grazingAngle",
                    [
                        ["Coordinates of Central Normal Vector", [
                            "normalVectorX",
                            "normalVectorY",
                            "normalVectorZ"
                        ]],
                        ["Coordinates of Central Tangential Vector", [
                            "tangentialVectorX",
                            "tangentialVectorY"
                        ]]
                    ]
                ]],
                ["Additional Parameters", [
                    "diffractionOrder",
                    "grooveDensity0",
                    "grooveDensity1",
                    "grooveDensity2",
                    "grooveDensity3",
                    "grooveDensity4"
                ]]
            ]
        },
        "initialIntensityReport": {
            "title": "Initial Intensity Report",
            "basic": [],
            "advanced": [
                "simulation.photonEnergy",
                "polarization",
                "characteristic",
                "fieldUnits"
            ]
        },
        "intensityReport": {
            "title": "Single-Electron Spectrum Report",
            "basic": [],
            "advanced": [
                ["Main", [
                    "distanceFromSource",
                    "initialEnergy",
                    "finalEnergy",
                    "photonEnergyPointCount",
                    "polarization",
                    "fieldUnits",
                    [
                        ["Horizontal", [
                            "horizontalPosition"
                        ]],
                        ["Vertical", [
                            "verticalPosition"
                        ]]
                    ]
                ]],
                ["Accuracy", [
                    "magneticField",
                    "method",
                    "precision"
                ]]
            ]
        },
        "lens": {
            "title": "Lens",
            "basic": [],
            "advanced": [
                "title",
                "position",
                [
                    ["Horizontal", [
                        "horizontalFocalLength",
                        "horizontalOffset"
                    ]],
                    ["Vertical", [
                        "verticalFocalLength",
                        "verticalOffset"
                    ]]
                ]
            ]
        },
        "mirror": {
            "title": "Flat Mirror",
            "basic": [],
            "advanced": [
                "title",
                "position",
                "heightProfileFile",
                "orientation",
                "grazingAngle",
                "heightAmplification",
                "horizontalTransverseSize",
                "verticalTransverseSize"
            ]
        },
        "mirrorReport": {
            "title": "Mirror",
            "basic": [],
            "advanced": []
        },
        "multipole": {
            "title": "Dipole",
            "basic": [
                "field",
                "length",
                "distribution"
            ],
            "advanced": []
        },
        "multiElectronAnimation": {
            "title": "Partially Coherent Intensity Report",
            "basic": [],
            "advanced": [
                "simulation.photonEnergy",
                "stokesParameter",
                "numberOfMacroElectrons"
            ]
        },
        "obstacle": {
            "title": "Obstacle",
            "basic": [],
            "advanced": [
                "title",
                "position",
                "shape",
                [
                    ["Horizontal", [
                        "horizontalSize",
                        "horizontalOffset"
                    ]],
                    ["Vertical", [
                        "verticalSize",
                        "verticalOffset"
                    ]]
                ]
            ]
        },
        "powerDensityReport": {
            "title": "Power Density Report",
            "basic": [],
            "advanced": [
                ["Main", [
                    "distanceFromSource",
                    [
                        ["Horizontal", [
                            "horizontalPosition",
                            "horizontalRange",
                            "horizontalPointCount"
                        ]],
                        ["Vertical", [
                            "verticalPosition",
                            "verticalRange",
                            "verticalPointCount"
                        ]]
                    ]
                ]],
                ["Accuracy", [
                    "method",
                    "precision"
                ]]
            ]
        },
        "simulation": {
            "title": "Source",
            "advanced": [
                "name",
                "sourceType"
            ]
        },
        "simulationFolder": {
            "title": "New Folder",
            "advanced": [
                "name"
            ]
        },
        "simulationDocumentation": {
            "model": "simulation",
            "title": "Simulation Documentation",
            "advanced": [
                "documentationUrl"
            ]
        },
        "simulationGrid": {
            "model": "simulation",
            "title": "Initial Wavefront Simulation Grid",
            "advanced": [
                "photonEnergy",
                "samplingMethod",
                "sampleFactor",
                [
                    ["Horizontal", [
                        "horizontalPosition",
                        "horizontalRange",
                        "horizontalPointCount"
                    ]],
                    ["Vertical", [
                        "verticalPosition",
                        "verticalRange",
                        "verticalPointCount"
                    ]]
                ]
            ]
        },
        "simulationStatus": {
            "title": "Simulation Status",
            "advanced": []
        },
        "sourceIntensityReport": {
            "title": "Intensity Report",
            "basic": [],
            "advanced": [
                ["Main", [
                    "distanceFromSource",
                    "simulation.photonEnergy",
                    "polarization",
                    "characteristic",
                    "fieldUnits",
                    "simulation.samplingMethod",
                    "simulation.sampleFactor",
                    [
                        ["Horizontal", [
                            "simulation.horizontalPosition",
                            "simulation.horizontalRange",
                            "simulation.horizontalPointCount"
                        ]],
                        ["Vertical", [
                            "simulation.verticalPosition",
                            "simulation.verticalRange",
                            "simulation.verticalPointCount"
                        ]]
                    ]
                ]],
                ["Accuracy", [
                    "magneticField",
                    "precision"
                ]]
            ]
        },
        "sphericalMirror": {
            "title": "Spherical Mirror",
            "basic": [],
            "advanced": [
                ["Main Parameters", [
                    "title",
                    "position",
                    "radius",
                    "tangentialSize",
                    "sagittalSize",
                    "grazingAngle",
                    [
                        ["Coordinates of Central Normal Vector", [
                            "normalVectorX",
                            "normalVectorY",
                            "normalVectorZ"
                        ]],
                        ["Coordinates of Central Tangential Vector", [
                            "tangentialVectorX",
                            "tangentialVectorY"
                        ]]
                    ]
                ]],
                ["Mirror Error", [
                    "heightProfileFile",
                    "orientation",
                    "heightAmplification"
                ]]
            ]
        },
        "tabulatedUndulator": {
            "title": "Undulator (Idealized or Tabulated)",
            "basic": [
                "undulatorType",
                "undulatorParameter",
                "gap",
                "phase",
                "period",
                "length",
                "longitudinalPosition",
                "magneticFile",
                [
                    ["Horizontal", [
                        "horizontalAmplitude",
                        "horizontalInitialPhase",
                        "horizontalSymmetry"
                    ]],
                    ["Vertical", [
                        "verticalAmplitude",
                        "verticalInitialPhase",
                        "verticalSymmetry"
                    ]]
                ]
            ],
            "advanced": []
        },
        "trajectoryReport": {
            "title": "Electron Trajectory Report",
            "basic": [],
            "advanced": [
                ["Main", [
                    "timeMomentEstimation",
                    "initialTimeMoment",
                    "finalTimeMoment",
                    "numberOfPoints",
                    "plotAxis"
                ]],
                ["Accuracy", [
                    "magneticField"
                ]]
            ]
        },
        "undulator": {
            "title": "Idealized Undulator",
            "basic": [
                "undulatorParameter",
                "period",
                "length",
                "longitudinalPosition",
                [
                    ["Horizontal", [
                        "horizontalAmplitude",
                        "horizontalInitialPhase",
                        "horizontalSymmetry"
                    ]],
                    ["Vertical", [
                        "verticalAmplitude",
                        "verticalInitialPhase",
                        "verticalSymmetry"
                    ]]
                ]
            ],
            "advanced": []
        },
        "watch": {
            "title": "Watchpoint",
            "basic": [],
            "advanced": [
                "title",
                "position"
            ]
        },
        "watchpointReport": {
            "title": "Watchpoint Report",
            "basic": [],
            "advanced": [
                "simulation.photonEnergy",
                "polarization",
                "characteristic",
                "fieldUnits"
            ]
        }
    }
};
