-- sqlite3 auth.db < auth_db.sql
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE db_upgrade_t (
	name VARCHAR(100) NOT NULL,
	created DATETIME NOT NULL,
	PRIMARY KEY (name)
);
INSERT INTO db_upgrade_t VALUES('_20230203_drop_spa_session','2025-03-19 22:32:15.690599');
INSERT INTO db_upgrade_t VALUES('_20231120_deploy_flash_update','2025-03-19 22:32:15.691594');
INSERT INTO db_upgrade_t VALUES('_20240322_remove_github_auth','2025-03-19 22:32:15.693918');
INSERT INTO db_upgrade_t VALUES('_20240507_cloudmc_to_openmc','2025-03-19 22:32:15.700669');
INSERT INTO db_upgrade_t VALUES('_20240524_add_role_user','2025-03-19 22:32:15.702552');
INSERT INTO db_upgrade_t VALUES('_20250114_add_role_plan_trial','2025-03-19 22:32:15.704129');
CREATE TABLE auth_email_user_t (
	unverified_email VARCHAR(255) NOT NULL,
	uid VARCHAR(8),
	user_name VARCHAR(255),
	token VARCHAR(16),
	expires DATETIME,
	PRIMARY KEY (unverified_email),
	UNIQUE (uid),
	UNIQUE (user_name),
	UNIQUE (token)
);
INSERT INTO auth_email_user_t VALUES('vagrant@localhost.localdomain','Uh4mhMWU','vagrant@localhost.localdomain',NULL,NULL);
CREATE TABLE jupyterhub_user_t (
	uid VARCHAR(8) NOT NULL,
	user_name VARCHAR(100) NOT NULL,
	PRIMARY KEY (uid),
	UNIQUE (user_name)
);
CREATE TABLE stripe_payment_t (
	user_payment_key VARCHAR(12) NOT NULL,
	invoice_id VARCHAR(255) NOT NULL,
	uid VARCHAR(100) NOT NULL,
	amount_paid INTEGER NOT NULL,
	created DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	customer_id VARCHAR(255) NOT NULL,
	subscription_id VARCHAR(255) NOT NULL,
	subscription_name VARCHAR(255) NOT NULL,
	PRIMARY KEY (user_payment_key),
	UNIQUE (invoice_id)
);
CREATE TABLE stripe_subscription_t (
	stripe_subscription_key VARCHAR(12) NOT NULL,
	uid VARCHAR(100),
	customer_id VARCHAR(255) NOT NULL,
	checkout_session_id VARCHAR(255),
	subscription_id VARCHAR(255) NOT NULL,
	creation_reason VARCHAR(100) DEFAULT 'payments_checkout_session_status_complete',
	created DATETIME NOT NULL,
	revocation_reason VARCHAR(100),
	revoked DATETIME,
	role VARCHAR(100) NOT NULL,
	PRIMARY KEY (stripe_subscription_key)
);
CREATE TABLE user_registration_t (
	uid VARCHAR(8) NOT NULL,
	created DATETIME NOT NULL,
	display_name VARCHAR(100),
	PRIMARY KEY (uid)
);
INSERT INTO user_registration_t VALUES('Uh4mhMWU','2025-03-19 22:32:38.278432','asdfasdf');
CREATE TABLE user_role_t (
	uid VARCHAR(8) NOT NULL,
	role VARCHAR(100) NOT NULL,
	expiration DATETIME,
	PRIMARY KEY (uid, role)
);
INSERT INTO user_role_t VALUES('Uh4mhMWU','user',NULL);
INSERT INTO user_role_t VALUES('Uh4mhMWU','trial','1751-06-04 22:38:11.428733');
CREATE TABLE user_role_moderation_t (
	uid VARCHAR(8) NOT NULL,
	role VARCHAR(100) NOT NULL,
	status VARCHAR(100) NOT NULL,
	moderator_uid VARCHAR(8),
	last_updated DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (uid, role)
);
INSERT INTO user_role_moderation_t VALUES('Uh4mhMWU','trial','approve','Uh4mhMWU','2025-03-19 22:32:51');
COMMIT;
