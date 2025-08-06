MATERIALS = {
    "Eurofer 97": {
        "availability_factor": 35.0,
        "components": {
            "Al": {
                "max_pct": 0.01,
                "min_pct": 0.0,
                "target_pct": 0.01
            },
            "As": {
                "max_pct": 0.0125,
                "min_pct": 0.0,
                "target_pct": 0.0125
            },
            "B": {
                "max_pct": 0.002,
                "min_pct": 0.0,
                "target_pct": 0.002
            },
            "C": {
                "max_pct": None,
                "min_pct": None,
                "target_pct": 0.11
            },
            "Co": {
                "max_pct": 0.01,
                "min_pct": 0.0,
                "target_pct": 0.01
            },
            "Cr": {
                "max_pct": None,
                "min_pct": None,
                "target_pct": 9.0
            },
            "Cu": {
                "max_pct": 0.01,
                "min_pct": 0.0,
                "target_pct": 0.01
            },
            "Fe": {
                "max_pct": None,
                "min_pct": None,
                "target_pct": 88.848
            },
            "Mn": {
                "max_pct": None,
                "min_pct": None,
                "target_pct": 0.4
            },
            "Mo": {
                "max_pct": 0.005,
                "min_pct": 0.0,
                "target_pct": 0.005
            },
            "N": {
                "max_pct": None,
                "min_pct": None,
                "target_pct": 0.03
            },
            "Nb": {
                "max_pct": 0.005,
                "min_pct": 0.0,
                "target_pct": 0.005
            },
            "Ni": {
                "max_pct": 0.01,
                "min_pct": 0.0,
                "target_pct": 0.01
            },
            "O": {
                "max_pct": 0.01,
                "min_pct": 0.0,
                "target_pct": 0.01
            },
            "P": {
                "max_pct": 0.005,
                "min_pct": 0.0,
                "target_pct": 0.005
            },
            "S": {
                "max_pct": 0.005,
                "min_pct": 0.0,
                "target_pct": 0.005
            },
            "Sb": {
                "max_pct": 0.0125,
                "min_pct": 0.0,
                "target_pct": 0.0125
            },
            "Si": {
                "max_pct": 0.05,
                "min_pct": 0.0,
                "target_pct": 0.05
            },
            "Sn": {
                "max_pct": 0.0125,
                "min_pct": 0.0,
                "target_pct": 0.0125
            },
            "Ta": {
                "max_pct": None,
                "min_pct": None,
                "target_pct": 0.12
            },
            "Ti": {
                "max_pct": 0.02,
                "min_pct": 0.0,
                "target_pct": 0.02
            },
            "V": {
                "max_pct": 0.25,
                "min_pct": 0.15,
                "target_pct": 0.2
            },
            "W": {
                "max_pct": None,
                "min_pct": None,
                "target_pct": 1.1
            },
            "Zr": {
                "max_pct": 0.0125,
                "min_pct": 0.0,
                "target_pct": 0.0125
            }
        },
        "created": "2025-07-23T17:08:21Z",
        "density_g_cm3": 7.625,
        "is_bare_tile": True,
        "is_homogenized_divertor": False,
        "is_homogenized_hcpb": True,
        "is_homogenized_wcll": False,
        "is_neutron_source_dt": True,
        "is_plasma_facing": False,
        "microstructure": None,
        "neutron_wall_loading": "DEMO",
        "processing_steps": None,
        "properties": {
            "composition": {
                "comments": None,
                "doi_or_url": "10.1016/j.fusengdes.2018.06.027",
                "pointer": "T5.1",
                "property_unit": "1",
                "source": "NOM"
            },
            "composition_density": {
                "comments": "Density is available as function of temperature; value is given at 500 C",
                "doi_or_url": "https://tinyurl.com/4uchnhx9",
                "pointer": "T1",
                "property_unit": "g/cm3",
                "source": "NOM"
            },
            "density": {
                "comments": None,
                "doi_or_url": "https://tinyurl.com/4uchnhx9",
                "neutron_fluence_1_cm2": [
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0
                ],
                "pointer": "T1",
                "property_unit": "kg/m3",
                "source": "NOM",
                "temperature_k": [
                    293.15,
                    323.15,
                    373.15,
                    473.15,
                    573.15,
                    673.15,
                    773.15,
                    873.15,
                    973.15
                ],
                "uncertainty": [
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None
                ],
                "value": [
                    7.744,
                    7.75,
                    7.74,
                    7.723,
                    7.691,
                    7.657,
                    7.625,
                    7.592,
                    7.559
                ]
            },
            "thermal_conductivity": {
                "comments": None,
                "doi_or_url": "https://tinyurl.com/4uchnhx9",
                "neutron_fluence_1_cm2": [
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0
                ],
                "pointer": "T20.1",
                "property_unit": "W/m/K",
                "source": "EXP",
                "temperature_k": [
                    293.15,
                    323.15,
                    373.15,
                    473.15,
                    573.15,
                    673.15,
                    773.15,
                    873.15
                ],
                "uncertainty": [
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None
                ],
                "value": [
                    28.08,
                    28.86,
                    29.78,
                    30.38,
                    30.01,
                    29.47,
                    29.58,
                    31.12
                ]
            }
        },
        "structure": None,
        "uid": "TODO RJN"
    },
    "Tungsten carbide": {
        "availability_factor": 0.25,
        "components": {
            "C12": {
                "max_pct": None,
                "min_pct": None,
                "target_pct": 6.127008411630046
            },
            "W182": {
                "max_pct": None,
                "min_pct": None,
                "target_pct": 24.54479762377749
            },
            "W183": {
                "max_pct": None,
                "min_pct": None,
                "target_pct": 13.339273342108234
            },
            "W184": {
                "max_pct": None,
                "min_pct": None,
                "target_pct": 28.83514746621842
            },
            "W186": {
                "max_pct": None,
                "min_pct": None,
                "target_pct": 27.153773156265803
            }
        },
        "created": "2025-07-23T18:00:22Z",
        "density_g_cm3": 15.63,
        "is_bare_tile": True,
        "is_homogenized_divertor": False,
        "is_homogenized_hcpb": True,
        "is_homogenized_wcll": False,
        "is_neutron_source_dt": True,
        "is_plasma_facing": True,
        "microstructure": None,
        "neutron_wall_loading": "ITER",
        "processing_steps": None,
        "properties": {},
        "structure": None,
        "uid": "TODO RJN"
    }
}
