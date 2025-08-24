PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE material (
	material_id BIGINT NOT NULL,
	uid VARCHAR(8) NOT NULL,
	created DATETIME NOT NULL,
	material_name VARCHAR(100) NOT NULL,
	is_plasma_facing BOOLEAN NOT NULL,
	structure VARCHAR(100),
	microstructure VARCHAR(500),
	processing_steps VARCHAR(500),
	is_neutron_source_dt BOOLEAN,
	neutron_wall_loading VARCHAR(32),
	availability_factor FLOAT,
	is_bare_tile BOOLEAN,
	is_homogenized_wcll BOOLEAN,
	is_homogenized_hcpb BOOLEAN,
	is_homogenized_divertor BOOLEAN,
	density_g_cm3 FLOAT NOT NULL,
	is_atom_pct BOOLEAN NOT NULL,
	PRIMARY KEY (material_id)
);
INSERT INTO material VALUES(1001,'TODO RJN','2025-07-23 17:08:21.707047','Eurofer 97',0,NULL,NULL,NULL,1,'DEMO',35.0,1,0,1,0,7.625,0);
INSERT INTO material VALUES(2001,'TODO RJN','2025-07-23 18:00:22.323114','Tungsten carbide',1,NULL,NULL,NULL,1,'ITER',0.25,1,0,1,0,15.630000000000000781,1);
CREATE TABLE material_component (
	material_component_id BIGINT NOT NULL,
	material_id BIGINT NOT NULL,
	material_component_name VARCHAR(8) NOT NULL,
	max_pct FLOAT,
	min_pct FLOAT,
	target_pct FLOAT NOT NULL,
	PRIMARY KEY (material_component_id),
	UNIQUE (material_id, material_component_name),
	FOREIGN KEY(material_id) REFERENCES material (material_id)
);
INSERT INTO material_component VALUES(1002,1001,'c',NULL,NULL,0.11000000000000000055);
INSERT INTO material_component VALUES(2002,1001,'cr',NULL,NULL,9.0);
INSERT INTO material_component VALUES(3002,1001,'w',NULL,NULL,1.1000000000000000888);
INSERT INTO material_component VALUES(4002,1001,'mn',NULL,NULL,0.4000000000000000222);
INSERT INTO material_component VALUES(5002,1001,'v',0.25,0.14999999999999999444,0.2000000000000000111);
INSERT INTO material_component VALUES(6002,1001,'ta',NULL,NULL,0.11999999999999999555);
INSERT INTO material_component VALUES(7002,1001,'n',NULL,NULL,0.029999999999999998889);
INSERT INTO material_component VALUES(8002,1001,'p',0.005000000000000000104,0.0,0.005000000000000000104);
INSERT INTO material_component VALUES(9002,1001,'s',0.005000000000000000104,0.0,0.005000000000000000104);
INSERT INTO material_component VALUES(10002,1001,'b',0.0020000000000000000416,0.0,0.0020000000000000000416);
INSERT INTO material_component VALUES(11002,1001,'o',0.010000000000000000208,0.0,0.010000000000000000208);
INSERT INTO material_component VALUES(12002,1001,'fe',NULL,NULL,88.847999999999998973);
INSERT INTO material_component VALUES(13002,1001,'nb',0.005000000000000000104,0.0,0.005000000000000000104);
INSERT INTO material_component VALUES(14002,1001,'mo',0.005000000000000000104,0.0,0.005000000000000000104);
INSERT INTO material_component VALUES(15002,1001,'ni',0.010000000000000000208,0.0,0.010000000000000000208);
INSERT INTO material_component VALUES(16002,1001,'cu',0.010000000000000000208,0.0,0.010000000000000000208);
INSERT INTO material_component VALUES(17002,1001,'al',0.010000000000000000208,0.0,0.010000000000000000208);
INSERT INTO material_component VALUES(18002,1001,'ti',0.020000000000000000416,0.0,0.020000000000000000416);
INSERT INTO material_component VALUES(19002,1001,'si',0.050000000000000002775,0.0,0.050000000000000002775);
INSERT INTO material_component VALUES(20002,1001,'co',0.010000000000000000208,0.0,0.010000000000000000208);
INSERT INTO material_component VALUES(21002,1001,'as',0.012500000000000000693,0.0,0.012500000000000000693);
INSERT INTO material_component VALUES(22002,1001,'sn',0.012500000000000000693,0.0,0.012500000000000000693);
INSERT INTO material_component VALUES(23002,1001,'sb',0.012500000000000000693,0.0,0.012500000000000000693);
INSERT INTO material_component VALUES(24002,1001,'zr',0.012500000000000000693,0.0,0.012500000000000000693);
INSERT INTO material_component VALUES(25002,2001,'w182',NULL,NULL,13.210271999999999792);
INSERT INTO material_component VALUES(26002,2001,'w183',NULL,NULL,7.1400180000000004199);
INSERT INTO material_component VALUES(27002,2001,'w184',NULL,NULL,15.350419999999999731);
INSERT INTO material_component VALUES(28002,2001,'w186',NULL,NULL,14.299599999999999866);
INSERT INTO material_component VALUES(29002,2001,'c12',NULL,NULL,49.999690000000001077);
CREATE TABLE material_property (
	material_property_id BIGINT NOT NULL,
	material_id BIGINT NOT NULL,
	property_name VARCHAR(100) NOT NULL,
	property_unit VARCHAR(32) NOT NULL,
	doi_or_url VARCHAR(500),
	source VARCHAR(32),
	pointer VARCHAR(32),
	comments VARCHAR(5000),
	PRIMARY KEY (material_property_id),
	UNIQUE (material_id, property_name),
	FOREIGN KEY(material_id) REFERENCES material (material_id)
);
INSERT INTO material_property VALUES(1003,1001,'composition_density','g/cm3','https://tinyurl.com/4uchnhx9','NOM','T1','Density is available as function of temperature; value is given at 500 C');
INSERT INTO material_property VALUES(2003,1001,'composition','1','10.1016/j.fusengdes.2018.06.027','NOM','T5.1',NULL);
INSERT INTO material_property VALUES(3003,1001,'density','kg/m3','https://tinyurl.com/4uchnhx9','NOM','T1',NULL);
INSERT INTO material_property VALUES(4003,1001,'thermal_conductivity','W/m/K','https://tinyurl.com/4uchnhx9','EXP','T20.1',NULL);
CREATE TABLE material_property_value (
	material_property_value_id BIGINT NOT NULL,
	material_property_id BIGINT NOT NULL,
	value FLOAT NOT NULL,
	uncertainty FLOAT,
	temperature_k FLOAT NOT NULL,
	neutron_fluence_1_cm2 FLOAT NOT NULL,
	PRIMARY KEY (material_property_value_id),
	FOREIGN KEY(material_property_id) REFERENCES material_property (material_property_id)
);
INSERT INTO material_property_value VALUES(1004,3003,7.7439999999999997726,NULL,293.14999999999997726,0.0);
INSERT INTO material_property_value VALUES(2004,3003,7.75,NULL,323.14999999999997725,0.0);
INSERT INTO material_property_value VALUES(3004,3003,7.7400000000000002131,NULL,373.14999999999997725,0.0);
INSERT INTO material_property_value VALUES(4004,3003,7.7229999999999998649,NULL,473.14999999999997727,0.0);
INSERT INTO material_property_value VALUES(5004,3003,7.6909999999999998365,NULL,573.14999999999997727,0.0);
INSERT INTO material_property_value VALUES(6004,3003,7.6570000000000000284,NULL,673.14999999999997727,0.0);
INSERT INTO material_property_value VALUES(7004,3003,7.625,NULL,773.14999999999997727,0.0);
INSERT INTO material_property_value VALUES(8004,3003,7.5919999999999996376,NULL,873.14999999999997727,0.0);
INSERT INTO material_property_value VALUES(9004,3003,7.5590000000000001634,NULL,973.14999999999997727,0.0);
INSERT INTO material_property_value VALUES(10004,4003,28.079999999999998294,NULL,293.14999999999997726,0.0);
INSERT INTO material_property_value VALUES(11004,4003,28.859999999999999431,NULL,323.14999999999997725,0.0);
INSERT INTO material_property_value VALUES(12004,4003,29.780000000000001136,NULL,373.14999999999997725,0.0);
INSERT INTO material_property_value VALUES(13004,4003,30.379999999999999006,NULL,473.14999999999997727,0.0);
INSERT INTO material_property_value VALUES(14004,4003,30.010000000000001563,NULL,573.14999999999997727,0.0);
INSERT INTO material_property_value VALUES(15004,4003,29.469999999999998863,NULL,673.14999999999997727,0.0);
INSERT INTO material_property_value VALUES(16004,4003,29.579999999999998295,NULL,773.14999999999997727,0.0);
INSERT INTO material_property_value VALUES(17004,4003,31.120000000000000994,NULL,873.14999999999997727,0.0);
CREATE TABLE independent_variable (
	independent_variable_id BIGINT NOT NULL,
	material_property_id BIGINT NOT NULL,
	name VARCHAR(100) NOT NULL,
	units VARCHAR(32) NOT NULL,
	PRIMARY KEY (independent_variable_id),
	UNIQUE (material_property_id, name),
	FOREIGN KEY(material_property_id) REFERENCES material_property (material_property_id)
);
CREATE TABLE independent_variable_value (
	independent_variable_value_id BIGINT NOT NULL,
	independent_variable_id BIGINT NOT NULL,
	material_property_value_id BIGINT NOT NULL,
	value FLOAT NOT NULL,
	PRIMARY KEY (independent_variable_value_id),
	UNIQUE (independent_variable_id, material_property_value_id),
	FOREIGN KEY(independent_variable_id) REFERENCES independent_variable (independent_variable_id),
	FOREIGN KEY(material_property_value_id) REFERENCES material_property_value (material_property_value_id)
);
CREATE UNIQUE INDEX ix_material_material_name ON material (material_name);
CREATE INDEX ix_material_created ON material (created);
CREATE INDEX ix_material_uid ON material (uid);
CREATE INDEX ix_material_component_material_id ON material_component (material_id);
CREATE INDEX ix_material_property_material_id ON material_property (material_id);
CREATE INDEX ix_material_property_value_material_property_id ON material_property_value (material_property_id);
CREATE INDEX ix_independent_variable_material_property_id ON independent_variable (material_property_id);
CREATE INDEX ix_independent_variable_value_independent_variable_id ON independent_variable_value (independent_variable_id);
CREATE INDEX ix_independent_variable_value_material_property_value_id ON independent_variable_value (material_property_value_id);
COMMIT;
