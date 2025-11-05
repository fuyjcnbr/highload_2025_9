
insert into test_schema.users (username, birth_dt, city, name, surname, password_hash)
select username
	,birth_dt
	,city
	,split_part(username, ' ', 2) as name
	,split_part(username, ' ', 1) as surname
	,md5('lala') as password_hash
from test_schema.upload_f_names;
