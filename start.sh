#!/bin/sh

sleep 15

psql postgresql://postgres:postgres@haproxy:5000/postgres -a -f init_postgres.sql

psql postgresql://root:root@haproxy:5000/test_db -a -f init_root.sql

iconv -f utf-8 -t utf-8 -c /src/people.v2.csv > /tmp.csv 2>/dev/null

psql postgresql://postgres:postgres@haproxy:5000/test_db -c  "copy test_schema.upload_f_names from STDIN with (delimiter ',');" < /tmp.csv

psql postgresql://root:root@haproxy:5000/test_db -a -f populate_users.sql


nohup uv run locust -f /src/locustfile.py > /locust.out 2>&1 &

nohup uv run server.py > /server.out 2>&1 &

sleep infinity
