from typing import Any
import sys
import hashlib
import re
import json
import asyncio
import aiopg
import aiohttp
import httpx
from dataclasses import dataclass, field
from random import randint

import uvicorn
import jwt
from pydantic import BaseModel
from fastapi import FastAPI, Response, status, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware




# from fastapi import FastAPI, APIRouter, Response, Request
# from starlette.background import BackgroundTask
# from fastapi.routing import APIRoute
# from starlette.types import Message
# from typing import Dict, Any
# import logging
#
#
# app = FastAPI()
# logging.basicConfig(filename="/info.log", level=logging.DEBUG)
# # logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
#
# # handler = logging.StreamHandler(sys.stdout)
# # handler.setLevel(logging.DEBUG)
# # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# # handler.setFormatter(formatter)
# # root.addHandler(handler)
#
#
#
# def log_info(req_body, res_body):
#     logging.info(req_body)
#     # logging.info(res_body)
#
#
# @app.middleware('http')
# async def some_middleware(request: Request, call_next):
#     req_body = await request.body()
#     # await set_body(request, req_body)  # not needed when using FastAPI>=0.108.0.
#     response = await call_next(request)
#
#     chunks = []
#     async for chunk in response.body_iterator:
#         chunks.append(chunk)
#     res_body = b''.join(chunks)
#
#     task = BackgroundTask(log_info, req_body, res_body)
#     return Response(
#         content=res_body,
#         status_code=response.status_code,
#         headers=dict(response.headers),
#         media_type=response.media_type,
#         background=task,
#     )




# PG_HOST = "localhost"
PG_HOST = "haproxy"
PG_DATABASE = "test_db"
PG_USER = "root"
PG_PASSWORD = "root"


SECERT_KEY = "SECERT_KEY"
ALGORITHM ="HS256"
ACCESS_TOKEN_EXPIRES_MINUTES = 800


DSN_MASTER = f'dbname={PG_DATABASE} user={PG_USER} password={PG_PASSWORD} host=haproxy port=5000'


@dataclass
class PatroniNode:
    server_name: str
    host: str
    patroni_port: int
    postgres_port: int

PATRONI_NODES_LIST = [
    PatroniNode(server_name="patroni1", host="patroni1", patroni_port=8008, postgres_port=5432),
    PatroniNode(server_name="patroni2", host="patroni2", patroni_port=8008, postgres_port=5432),
    PatroniNode(server_name="patroni3", host="patroni3", patroni_port=8008, postgres_port=5432),
]


@dataclass
class PatroniCluster:
    leader: PatroniNode
    replicas: list[PatroniNode]


class Patroni:

    def __init__(self):
        self.session = aiohttp.ClientSession()

    def get_patroni_node_by_name(self, name: str) -> PatroniNode or None:
        for x in PATRONI_NODES_LIST:
            if x.server_name == name:
                return x
        return None

    def parse_patroni_cluster_info(self, js: dict) -> PatroniCluster:
        # js = json.loads(s)
        leader = [self.get_patroni_node_by_name(x["name"]) for x in js["members"] if x["role"] == "leader"][0]
        replicas = [self.get_patroni_node_by_name(x["name"]) for x in js["members"] if x["role"] == "replica"]
        #
        # print(f"parse_patroni_cluster_info leader={leader}")
        # print(f"parse_patroni_cluster_info replicas={replicas}")
        #
        return PatroniCluster(leader=leader, replicas=replicas)

    def postgres_dsn_from_patroni_node(self, p: PatroniNode) -> str:
        dsn = f"dbname={PG_DATABASE} user={PG_USER} password={PG_PASSWORD} host={p.host} port={p.postgres_port}"
        return dsn

    # async def request(self, session, url):
    #     async with session.get(url) as response:
    #         return await response.text()

    async def request_httpx(self, client, url):
        response = await client.get(url)
        return response.text

    async def _get_patroni_cluster_info(self, host: str, port: int) -> PatroniCluster or None:
        try:
            # async with asyncio.timeout(2):
            # async with aiohttp.ClientSession() as session:
            #     async with session.get(f"http://{host}:{port}/cluster") as resp:
            #         response = await resp.text()
            #         print(f"_get_patroni_cluster_info response={response}")
            #         d = json.loads(response)
            #         patroni_cluster = self.parse_patroni_cluster_info(d)
            #         return patroni_cluster
            # session = aiohttp.ClientSession()
            # async with session.get(f"http://{host}:{port}/cluster") as resp:
            #     response = await resp.text()
            #     print(f"_get_patroni_cluster_info response={response}")
            # await session.close()

            # if not self.session:
            #     self.session = aiohttp.ClientSession()
            # resp = await self.session.get(f"http://{host}:{port}/cluster")
            # response = await resp.text()
            #
            # await self.session.close()

            # async with aiohttp.ClientSession() as session:
            #     tasks = [self.request(session, f"http://{host}:{port}/cluster")]
            #     result = await asyncio.gather(*tasks)
            #     print(result)

            async with httpx.AsyncClient() as client:
                tasks = [self.request_httpx(client, f"http://{host}:{port}/cluster")]
                result = await asyncio.gather(*tasks)
                # print(result)

                response = result[0]
                # print(f"_get_patroni_cluster_info response={response}")
                d = json.loads(response)
                patroni_cluster = self.parse_patroni_cluster_info(d)
                return patroni_cluster

        except Exception as e:
            print(f"_get_patroni_cluster_info Exception={e}")
            return None
        finally:
            if self.session:
                await self.session.close()
        # if not response:
        #     return None
        # d = json.loads(response)
        # patroni_cluster = self.parse_patroni_cluster_info(d)
        # return patroni_cluster

    async def get_patroni_cluster_info(self) -> PatroniCluster or None:
        # patroni_cluster = None
        for p in PATRONI_NODES_LIST:
            # print(f"get_patroni_cluster_info p={p}")
            try:
                patroni_cluster = await self._get_patroni_cluster_info(p.host, p.patroni_port)

                return patroni_cluster
            except Exception as e:
                # print(f"get_patroni_cluster_info Exception={e}")
                await asyncio.sleep(0.1)
        return None

    def is_write_query(self, query: str) -> bool:
        li = ["insert", "update", "delete"]
        b = any(x in query.lower() for x in li)
        return b

    async def get_dsn(self, query: str) -> str:
        # patroni_cluster = None
        # for p in PATRONI_NODES_LIST:
        #     try:
        #         patroni_cluster = await self._get_patroni_cluster_info(p.host, p.patroni_port)
        #         # print(f"get_dsn patroni_cluster={patroni_cluster}")
        #         break
        #     except Exception as e:
        #         pass

        patroni_cluster = await self.get_patroni_cluster_info()
        # print(patroni_cluster)
        if self.is_write_query(query):
            node = patroni_cluster.leader
        else:
            hi = len(patroni_cluster.replicas) - 1
            # print(f"get_dsn hi={hi}")
            # print(f"get_dsn patroni_cluster.replicas={patroni_cluster.replicas}")
            i = randint(0, hi)
            node = patroni_cluster.replicas[i]
        dsn = self.postgres_dsn_from_patroni_node(node)
        # print(dsn)
        return dsn



app = FastAPI()

# routes_to_reroute = [
#     "/",
# ]

origins = {
    "http://localhost",
    "http://localhost:3000",
}

app.add_middleware(
   CORSMiddleware,
    allow_origins = origins,
    allow_credentials =True,
    allow_methods = ["*"],
    allow_headers= ["*"],
)

class RegisterItem(BaseModel):
    username: str
    password: str
    name: str

class LoginItem(BaseModel):
    username: str
    password: str

class AuthorizedItem(BaseModel):
    username: str
    token: str

class Token(BaseModel):
    username: str
    id: int

class SearchByNameSurnameItem(BaseModel):
    name_prefix: str
    surname_prefix: str

class TestItem(BaseModel):
    data: str


app.tokens : dict[str, Token] = {}


def hash_func(s: str):
    res = hashlib.md5(s.encode('utf-8')).hexdigest()
    return res

def check_str(s: str) -> bool:
    if (len(s) > 50 or s.find(";") >= 0
            or re.findall(r"(create|drop|select|insert|update|delete)", s)):
        return False
    return True


# dsn = f'dbname={PG_DATABASE} user={PG_USER} password={PG_PASSWORD} host={PG_HOST} port=5000'

# async def get_patroni_cluster_info(host: str, port: str) -> dict[str, Any]:


# async def get_dsn() -> str:
#     async def get_patroni_cluster_info(host: str, port: str) -> dict[str, Any]:
#         for (host, port) in PATRONI_HOSTS_LIST:
#             try:
#                 d = get_patroni_cluster_info(host, port)
#                 break
#             except Exception as e:
#                 pass
#         return d

# __patroni = Patroni()


async def query_master(query: str):
    dsn = DSN_MASTER
    if not dsn:
        return None
    try:
        async with asyncio.timeout(5):
            async with aiopg.connect(dsn) as con:
                async with con.cursor() as cursor:
                    await cursor.execute(query)
                    result = []
                    async for row in cursor:
                        result.append(row)
                    return result
    except Exception as e:
        return None


async def query(query: str):
    dsn = await Patroni().get_dsn(query)
    if not dsn:
        return None
    try:
        async with asyncio.timeout(5):
            async with aiopg.connect(dsn) as con:
                async with con.cursor() as cursor:
                    await cursor.execute(query)
                    result = []
                    async for row in cursor:
                        result.append(row)
                    return result
    except Exception as e:
        return None


async def execute_sql(query: str):
    dsn = await Patroni().get_dsn(query)
    if not dsn:
        return None
    try:
        async with asyncio.timeout(5):
            async with aiopg.connect(dsn) as con:
                async with con.cursor() as cursor:
                    result = await cursor.execute(query)
                    return result
    except Exception as e:
        return None



# @app.middleware("http")
# async def some_middleware(request: Request, call_next):
#     if request.url.path in routes_to_reroute:
#         request.scope['path'] = '/welcome'
#         headers = dict(request.scope['headers'])
#         headers[b'custom-header'] = b'my custom header'
#         request.scope['headers'] = [(k, v) for k, v in headers.items()]
#
#     return await call_next(request)


@app.get("/")
def read_root():
    # response.status_code = status.HTTP_201_CREATED
    return {"Hello": "World"}


@app.post("/user/register")
async def user_register(r: RegisterItem):
    data = jsonable_encoder(r)
    username_ = data["username"]
    password_hash_ = hash_func(data["password"])
    name_ = data["name"]

    if not check_str(username_) or not check_str(password_hash_) or not check_str(name_):
        return {"message": "possible SQL injection in parameters"}

    result = await asyncio.gather(
        query(f"""
        select *
        from test_schema.backend_api_register_user(
            username_ := '{username_}',
            password_hash_ := '{password_hash_}',
            name_ := '{name_}'
        )
        """),
    )
    first_row = result[0][0]
    d = {"password_hash": password_hash_}
    if first_row[0] == "ok":
        encoded_jwt = jwt.encode(d, SECERT_KEY, algorithm=ALGORITHM)
        app.encoded_jwt = encoded_jwt

        t = Token(username=username_, id=first_row[1])
        app.tokens[encoded_jwt] = t
        return {"token": encoded_jwt}
    else:
        return {"message": first_row[0]}


@app.post("/login")
async def login(l: LoginItem):
    data = jsonable_encoder(l)
    username_ = data["username"]
    password_hash_ = hash_func(data["password"])

    if not check_str(username_) or not check_str(password_hash_):
        return {"message": "possible SQL injection in parameters"}

    result = await asyncio.gather(
        query(f"""
        select *
        from test_schema.backend_api_login_user(
            username_ := '{username_}',
            password_hash_ := '{password_hash_}'
        )
        """),
    )
    first_row = result[0][0]
    d = {"password_hash": password_hash_}
    if first_row[0] == "ok":
        encoded_jwt = jwt.encode(d, SECERT_KEY, algorithm=ALGORITHM)
        app.encoded_jwt = encoded_jwt

        t = Token(username=username_, id=first_row[1])
        app.tokens[encoded_jwt] = t

        return {"token": encoded_jwt}
    else:
        return {"message": first_row[0]}


@app.get("/user/get/{token}")
async def user_get(token: str):
    if token not in app.tokens.keys():
        return {"message": "unknown token"}

    x = app.tokens[token]
    id = x.id
    result = await asyncio.gather(
        query(f"""
        select *
        from test_schema.backend_api_get_profile_by_id(id_ := {id})
        """),
    )
    first_row = result[0][0]
    if first_row[0] == "ok":
        return {"name": first_row[1]}
    else:
        return {"message": first_row[1]}


@app.post("/user/search")
async def search_by_name_surname(x: SearchByNameSurnameItem):
    data = jsonable_encoder(x)
    name_ = data["name_prefix"]
    surname_ = data["surname_prefix"]
    result = await asyncio.gather(
        query(f"""
        select *
        from test_schema.backend_api_search_user_name_surname(name_ := '{name_}', surname_ := '{surname_}')
        """),
    )
    # result2 = []
    # for row in result:
    #     row[1] = str(row[1])
    #     row[2] = str(row[2])
    #     result2.append(row)
    d = json.dumps(result)
    # unicodedata.normalize('NFKD', x).encode('ascii', 'ignore')
    return d


@app.post("/user/master/search")
async def search_by_name_surname_master(x: SearchByNameSurnameItem):
    data = jsonable_encoder(x)
    name_ = data["name_prefix"]
    surname_ = data["surname_prefix"]
    result = await asyncio.gather(
        query_master(f"""
        select *
        from test_schema.backend_api_search_user_name_surname(name_ := '{name_}', surname_ := '{surname_}')
        """),
    )
    d = json.dumps(result)
    return d



@app.post("/test/select1")
async def test_select1(t: TestItem):
    d = jsonable_encoder(t)
    data_ = d["data"]
    if not check_str(data_):
        return {"message": "possible SQL injection in parameters"}

    result = await asyncio.gather(
        query(f"""
        select *
        from test_schema.test_insert1
        where data = '{data_}'
        limit 2
        """),
    )
    return {"message": str(result)}

@app.post("/test/insert1")
async def test_insert1(t: TestItem):
    d = jsonable_encoder(t)
    data_ = d["data"]

    if not check_str(data_):
        return {"message": "possible SQL injection in parameters"}

    cluster = await Patroni().get_patroni_cluster_info()
    if not cluster:
        return {"message": "no cluster"}

    result = await asyncio.gather(
        execute_sql(f"""
        insert into test_schema.test_insert1 (data, host) values ('{data_}', '{cluster.leader.host}')
        """),
    )
    return {"message": "inserted"}

def receive_signal(signalNumber, frame):
    print("Received:", signalNumber)
    sys.exit()

@app.on_event("startup")
async def startup_event():
    import signal
    signal.signal(signal.SIGINT, receive_signal)


if __name__ == "__main__":
    uvicorn.run(app, port=8223, host="0.0.0.0")
