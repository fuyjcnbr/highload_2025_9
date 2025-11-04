#!/bin/sh

sleep 15

psql postgresql://postgres:postgres@haproxy:5000/postgres -a -f init_postgres.sql

psql postgresql://root:root@haproxy:5000/test_db -a -f init_root.sql

nohup uv run server.py > /server.out 2>&1 &

sleep infinity
