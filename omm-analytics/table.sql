create
    database omm_analytics_mainnet;
use
    omm_analytics_mainnet;
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

CREATE TABLE `omm_staking_stats`
(
    `staking`         int(11) DEFAULT NULL,
    `unstaking`       int(11) DEFAULT NULL,
    `cancelUnstaking` int(11) DEFAULT NULL,
    `timestamp`       int(11) DEFAULT NULL,
    `_index`          int(11) NOT NULL,
    PRIMARY KEY (`_index`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4;

CREATE TABLE `reserve_amount`
(
    `_index`    int(11)     NOT NULL,
    `timestamp` int(11) DEFAULT NULL,
    `deposit`   float   DEFAULT NULL,
    `borrow`    float   DEFAULT NULL,
    `repay`     float   DEFAULT NULL,
    `redeem`    float   DEFAULT NULL,
    `reserve`   varchar(10) NOT NULL,
    PRIMARY KEY (`_index`, `reserve`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4;

CREATE TABLE `reserve_stats`
(
    `_index`         int(11)     NOT NULL,
    `timestamp`      int(11) DEFAULT NULL,
    `deposit`        int(11) DEFAULT NULL,
    `borrow`         int(11) DEFAULT NULL,
    `repay`          int(11) DEFAULT NULL,
    `redeem`         int(11) DEFAULT NULL,
    `unique_address` int(11) DEFAULT NULL,
    `reserve`        varchar(10) NOT NULL,
    PRIMARY KEY (`_index`, `reserve`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4;

CREATE TABLE `timestamp_history`
(
    `_key`      varchar(10) NOT NULL,
    `timestamp` bigint(20) DEFAULT NULL,
    PRIMARY KEY (`_key`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4;


insert into timestamp_history(`_key`, `timestamp`)
values ("OMM", 1638316800000000),
       ("RESERVE", 1638316800000000);

