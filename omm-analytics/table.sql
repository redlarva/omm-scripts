CREATE TABLE `omm_staking_amount`
(
    `staking`         float   DEFAULT NULL,
    `unstaking`       float   DEFAULT NULL,
    `cancelUnstaking` float   DEFAULT NULL,
    `timestamp`       int(11) DEFAULT NULL,
    `_index`          int(11) NOT NULL,
    PRIMARY KEY (`_index`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4;

CREATE TABLE `omm_staking_count`
(
    `staking`         int(11) DEFAULT NULL,
    `unstaking`       int(11) DEFAULT NULL,
    `cancelUnstaking` int(11) DEFAULT NULL,
    `timestamp`       int(11) DEFAULT NULL,
    `_index`          int(11) NOT NULL,
    PRIMARY KEY (`_index`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4;

CREATE TABLE `timestamp_history`
(
    `_key`      varchar(10) NOT NULL,
    `timestamp` bigint(20) DEFAULT NULL,
    PRIMARY KEY (`_key`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4;

