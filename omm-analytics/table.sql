create
    database omm_analytics;
use
    omm_analytics;
create table omm_staking_amount
(
    staking         float null,
    unstaking       float null,
    cancelUnstaking float null,
    timestamp       int   null,
    _index          int   not null
        primary key
);

create table omm_staking_stats
(
    staking         int null,
    unstaking       int null,
    cancelUnstaking int null,
    timestamp       int null,
    _index          int not null
        primary key
);

create table reserve_amount
(
    _index    int   not null,
    timestamp int   null,
    deposit   float null,
    borrow    float null,
    repay     float null,
    redeem    float null,
    reserve   varchar(20)   not null,
    primary key (_index, reserve)
);

create table reserve_stats
(
    _index         int not null,
    timestamp      int null,
    deposit        int null,
    borrow         int null,
    repay          int null,
    redeem         int null,
    unique_address int null,
    reserve        varchar(20) not null,
    primary key (_index, reserve)
);

create table timestamp_history
(
    _key      varchar(10) not null
        primary key,
    timestamp bigint      null
);

insert into timestamp_history ("_key", "timestamp")
values ("OMM", 1638316800000000),
       ("RESERVE", 1638316800000000);

