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
        is_public BOOLEAN,
        is_featured BOOLEAN,
	PRIMARY KEY (material_id)
);
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
