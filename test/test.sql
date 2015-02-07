DELIMITER $$

DROP PROCEDURE IF EXISTS `accounts.get_by_login`$$
CREATE PROCEDURE `accounts.get_by_login` (`login` VARCHAR(255)) COMMENT 'returns object'
BEGIN
  SELECT
      accounts.login,
      accounts.local_id AS `id`,
      accounts.server_url
    FROM accounts WHERE accounts.login = `login`;

  IF FOUND_ROWS() = 0 THEN
    CALL __throw('Unauthorized', 'Invalid credentials.');
  END IF;

END$$

DROP PROCEDURE IF EXISTS `accounts.get_desc`$$
CREATE PROCEDURE `accounts.get_desc` (`login` VARCHAR(255)) COMMENT 'returns merge: object, object'
BEGIN
  SELECT 2 INTO a2 FROM t2 WHERE k=1;
  SELECT 1 AS version;
  SELECT
      accounts.login,
      accounts.local_id AS `id`,
      accounts.server_url
    FROM accounts WHERE accounts.login = `login`;
END$$

DROP PROCEDURE IF EXISTS `accounts.__try_update_existed`$$
CREATE PROCEDURE `accounts.__try_update_existed` (login VARCHAR(255), `local_id` BIGINT, `server_url` VARCHAR(1024))
leave_proc: BEGIN
  DECLARE existed_local_id BIGINT;
  DECLARE existed_server_url VARCHAR(1024);
  DECLARE CONTINUE HANDLER FOR 1062 CALL __throw('Conflict', 'The account with such login already exists.');
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET existed_local_id = NULL;

  SELECT accounts.local_id, accounts.server_url INTO existed_local_id, existed_server_url FROM accounts WHERE accounts.login = login FOR UPDATE;

  IF existed_server_url = server_url THEN
    -- account on same server with different email, therefore the old one has been already deleted
    UPDATE accounts SET accounts.local_id = local_id WHERE accounts.login = login;
    LEAVE leave_proc;
  END IF;

  IF existed_server_url IS NOT NULL AND existed_server_url != server_url THEN
    CALL __throw('Conflict', 'The account with such login already exists.');
  END IF;

  SELECT accounts.local_id, accounts.server_url INTO existed_local_id, existed_server_url FROM accounts
    WHERE accounts.local_id = local_id AND accounts.server_url = server_url FOR UPDATE;

  IF existed_local_id IS NOT NULL THEN
    -- same account, email is changed
    UPDATE accounts SET accounts.login = login WHERE accounts.local_id = local_id AND accounts.server_url = server_url;
    LEAVE leave_proc;
  END IF;

  CALL __throw('TryAgain', 'State was changed, try again.');
END$$


DROP PROCEDURE IF EXISTS `accounts.register`$$
CREATE PROCEDURE `accounts.register` (login VARCHAR(255), local_id BIGINT, server_url VARCHAR(1024))
BEGIN
  DECLARE CONTINUE HANDLER FOR 1062 CALL accounts.__try_update_existed(login, local_id, server_url);
  INSERT INTO accounts (`login`, local_id, `server_url`) VALUES (login, local_id, server_url);
END$$


DROP PROCEDURE IF EXISTS `accounts.update`$$
CREATE PROCEDURE `accounts.update` () COMMENT "args (`name` VARCHAR(10), `t` BOOLEAN); returns object"
BEGIN
  DECLARE CONTINUE HANDLER FOR 1062 CALL accounts.__try_update_existed(login, local_id, server_url);
  INSERT INTO accounts (`login`, local_id, `server_url`) VALUES (login, local_id, server_url);
END$$


DELIMITER ;
