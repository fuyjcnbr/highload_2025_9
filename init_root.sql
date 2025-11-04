

create extension pg_trgm;

create schema test_schema;

create table test_schema.users (
	id bigserial primary key
	,username text
	,password_hash text

	,name text
	,surname text
	,birth_dt date
	,sex text
	,hobby text
	,city text
	,pages text
);


create table test_schema.upload_f_names (
    username text,
    birth_dt date,
    city text
);

create table test_schema.test_insert1 (
	id bigserial primary key
	,data text
	,ts timestamp default clock_timestamp()
	,host text
);




CREATE OR REPLACE FUNCTION test_schema.backend_api_register_user(username_ text, password_hash_ text, name_ text)
RETURNS TABLE (msg text, id bigint) AS $$
declare
	i_ int;
	id_ bigint;
BEGIN
	select count(*)
	into i_
	from test_schema.users a
	where a.username = username_;

	if i_ > 0 then
		return query values ('user already exists', null::bigint);
		return;
	end if;

	insert into test_schema.users (username, password_hash, name)
	select username_, password_hash_, name_
	returning test_schema.users.id
	into id_;

	return query values ('ok', id_);
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION test_schema.backend_api_login_user(username_ text, password_hash_ text)
RETURNS TABLE (msg text, id bigint, name text) AS $$
declare
	i_ int;
BEGIN
	select count(*)
	into i_
	from test_schema.users a
	where a.username = username_
	and a.password_hash = password_hash_;

	if i_ = 0 then
		return query values ('invalid creds', null::bigint, null);
	elsif i_ > 1 then
		return query values ('panic: > 1 user with the same creds', null::bigint, null);
	end if;

	return query
	select 'ok' as msg
		,a.id::bigint
		,a.name
	from test_schema.users a
	where a.username = username_
	and a.password_hash = password_hash_
	;

END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION test_schema.backend_api_get_profile_by_id(id_ bigint)
RETURNS TABLE (msg text, name text) AS $$
declare
	i_ int;
BEGIN
	select count(*)
	into i_
	from test_schema.users a
	where a.id = id_;

	if i_ = 0 then
		return query values ('invalid id', null);
	elsif i_ > 1 then
		return query values ('panic: > 1 user with the same ids', null);
	end if;

	return query
	select 'ok' as msg
		,a.name
	from test_schema.users a
	where a.id = id_
	;

END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION test_schema.backend_api_search_user_name_surname(name_ text, surname_ text)
RETURNS TABLE (id bigint, name text, surname text) AS $$
BEGIN

	return query
	select a.id
		,a.name
		,a.surname
	from test_schema.users a
	where lower(a.name) like lower(name_) || '%'
	and lower(a.surname) like lower(surname_) || '%'
	order by a.id
	;

END;
$$ LANGUAGE plpgsql;


