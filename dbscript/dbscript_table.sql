-- 테이블목록
-- 	1. regions : 지역
-- 	2. car_registrations : 수소차 누적 데이터
-- 	3. hydrogen_charging_station : 수소 충전소
-- 	4. faq : faq
-- 	5. crawl_stat : 충전소 크롤링 데이터

create database crawler_db
	default character set utf8mb4
    collate utf8mb4_unicode_ci;
    
use crawler_db;

-- 테이블 작성 // regions : 지역
create table regions (
	region_id	smallint	primary key auto_increment,
    region_name varchar(20) not null unique    
);

create table car_registrations(
	id bigint primary key auto_increment,
    region_id smallint not null,
    stat_year smallint not null,
    count int default 0,
    
    foreign key (region_id) 
    references regions (region_id),
    
    unique key uq_stat (region_id, stat_year)   
);
 
 create table hydrogen_charging_station(
	id int primary key auto_increment,
    region_id smallint not null,
    station_name varchar(100) not null,
    address varchar(255),
    lat decimal(10, 7),
    lon decimal(10, 7),
 );
 
 -- 외래키 추가
 alter table hydrogen_charging_station
 add constraint region
 foreign key (region_id)
 references regions (region_id);
 
 create table faq(
	faq_id int primary key auto_increment,
    question text not null,
    answer text
 );
 
 
 create table crawl_stat(
	crawl_id int primary key auto_increment,
    target_type varchar(30) not null,
    last_crawled_at datetime,
    check (target_type in ('car_registration', 'station', 'faq'))
 );

 
 -- 확인용
 select * from regions;
 select * from car_registrations;
 select * from hydrogen_charging_station;
 select * from faq;
 select * from crawl_stat;
 
 SELECT COUNT(*) FROM hydrogen_charging_station;
SELECT * FROM hydrogen_charging_station LIMIT 5;
 -- 초기화 쿼리문
 truncate table regions;
 truncate table car_registrations;
 truncate table hydrogen_charging_station;
 truncate table faq;
 truncate table crawl_stat;