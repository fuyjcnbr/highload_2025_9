FROM ubuntu:24.04

RUN apt update


###############python
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN apt -y install python3-pip
RUN python -m pip install --break-system-packages uv


RUN apt -y install sudo postgresql-client


# COPY uv.lock /uv.lock
COPY pyproject.toml /pyproject.toml

RUN uv sync


COPY start.sh /start.sh
COPY server.py /server.py
COPY test_cluster_insert.py /test_cluster_insert.py
COPY init_postgres.sql /init_postgres.sql
COPY init_root.sql /init_root.sql
# COPY create.sql /create.sql
# COPY create_fdw.sql /create_fdw.sql
COPY populate_users.sql /populate_users.sql



RUN mkdir /src


# EXPOSE 5432
# EXPOSE 8223

ENTRYPOINT sh start.sh && /bin/bash
