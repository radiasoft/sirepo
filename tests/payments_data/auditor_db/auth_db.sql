-- sqlite3 auth.db < auth_db.sql
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE db_upgrade_t (
	name VARCHAR(100) NOT NULL,
	created DATETIME NOT NULL,
	PRIMARY KEY (name)
);
INSERT INTO db_upgrade_t VALUES('_20230203_drop_spa_session','2025-03-19 22:58:59.856605');
INSERT INTO db_upgrade_t VALUES('_20231120_deploy_flash_update','2025-03-19 22:58:59.857578');
INSERT INTO db_upgrade_t VALUES('_20240322_remove_github_auth','2025-03-19 22:58:59.858780');
INSERT INTO db_upgrade_t VALUES('_20240507_cloudmc_to_openmc','2025-03-19 22:58:59.863567');
INSERT INTO db_upgrade_t VALUES('_20240524_add_role_user','2025-03-19 22:58:59.865407');
INSERT INTO db_upgrade_t VALUES('_20250114_add_role_plan_trial','2025-03-19 22:58:59.867011');
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
INSERT INTO stripe_payment_t VALUES('pmt_2ApddQ3Hh57E','in_1R4Vak2MoUThcATgVIGGT3hR','Uh4mhMWU',9900,'2025-03-19 23:00:18','cus_RySVdgQl8WUcSS','sub_1R4Vak2MoUThcATgfFcvdllF','Sirepo Basic');
CREATE TABLE user_registration_t (
	uid VARCHAR(8) NOT NULL,
	created DATETIME NOT NULL,
	display_name VARCHAR(100),
	PRIMARY KEY (uid)
);
INSERT INTO user_registration_t VALUES('Uh4mhMWU','2025-03-19 22:59:24.965566','test');
CREATE TABLE user_role_t (
	uid VARCHAR(8) NOT NULL,
	role VARCHAR(100) NOT NULL,
	expiration DATETIME,
	PRIMARY KEY (uid, role)
);
INSERT INTO user_role_t VALUES('Uh4mhMWU','user',NULL);
INSERT INTO user_role_t VALUES('Uh4mhMWU','trial','1997-11-01 23:03:49.592268');
INSERT INTO user_role_t VALUES('Uh4mhMWU','basic','1997-11-01 23:03:58.207326');
CREATE TABLE user_role_moderation_t (
	uid VARCHAR(8) NOT NULL,
	role VARCHAR(100) NOT NULL,
	status VARCHAR(100) NOT NULL,
	moderator_uid VARCHAR(8),
	last_updated DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (uid, role)
);
INSERT INTO user_role_moderation_t VALUES('Uh4mhMWU','trial','approve','tGOGpEqB','2025-03-19 22:59:41');
CREATE TABLE stripe_subscription_t (
	stripe_subscription_key VARCHAR(16) NOT NULL,
	uid VARCHAR(8),
	customer_id VARCHAR(255) NOT NULL,
	checkout_session_id VARCHAR(255),
	subscription_id VARCHAR(255) NOT NULL,
	creation_reason VARCHAR(100) NOT NULL,
	created DATETIME NOT NULL,
	revocation_reason VARCHAR(100),
	revoked DATETIME,
	role VARCHAR(100) NOT NULL,
	PRIMARY KEY (stripe_subscription_key)
);
INSERT INTO stripe_subscription_t VALUES('sbs_QhRwyIldKeBR','Uh4mhMWU','cus_RySVdgQl8WUcSS','cs_test_a15I4Nqtfo5jQbS2BcYdfJ3xGdZ5yj337BdXMWWjNNgjGsAKXypAeDpP8K','sub_1R4Vak2MoUThcATgfFcvdllF','payments_checkout_session_status_complete','2025-03-19 23:00:13.993620',NULL,NULL,'basic');
COMMIT;
