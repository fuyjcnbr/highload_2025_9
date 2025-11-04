

patroni.env копия с https://github.com/patroni/patroni.git

docker-compose.yml основан на https://github.com/patroni/patroni.git


## Сборка 


### Собираем образ patroni 

```commandline
git clone https://github.com/patroni/patroni.git
cd patroni
docker build -t patroni .
```

### Собираем образ домашки (http сервер + объекты в БД)

```commandline
cd ~/PycharmProjects/highload_hw_9
docker build --no-cache --squash -t highload_hw_9 -f Dockerfile .
```

### Запускаем docker compose

```commandline
docker compose -f docker-compose.yml up --force-recreate
```

## Подготовка

### Смотрим список контейнеров

```commandline
docker container list
```

### Проверяем etcd (на любом контейнере etcd)

```commandline
docker exec -it <etcd container id> etcdctl member list -wtable
```

### Проверяем patroni (на любом контейнере patroni)

```commandline
docker exec -it <patroni container id> patronictl list
```

## Эксперимент 1: kill -9

### На контейнере лидера patroni ищем основной процесс postgres

```commandline
ps -ef | grep postgres | grep data
```

### На контейнере highload_hw_9 запускаем скрипт для тестовых insert'ов

```commandline
uv run /src/test_cluster_insert.py
```

### На контейнере лидера patroni убиваем postgres с помощью ранее найденного PID'а

```commandline
kill -9 <postgres pid>
```

### На контейнере highload_hw_9 ждём немного и останавливаем скрипт для тестовых insert'ов

ctrl+c



### В sql ide смотрим, сколько пропущенных записей (через haproxy localhost:5000 test_db root/root)

```sql
select (max(id) - min(id) + 1) - count(distinct id) as total_missed_values
from test_schema.test_insert1
```

2


### Смотрим на сами записи

```sql
select *
from test_schema.test_insert1
order by ts asc
limit 70
```

или

```sql
select *
from test_schema.test_insert1
order by id asc
limit 70
```


|id| data    | ts| host|
| -------- |---------| -------- | ------- |
|491	| data6	  | 2025-11-04 14:28:12.980	| patroni3 |
|492	| data7	  | 2025-11-04 14:28:13.353	| patroni3 |
|495	| data24  | 2025-11-04 14:28:19.507	| patroni3 |
|496	| data25  | 2025-11-04 14:28:19.875	| patroni3 |

Видно, что хост патрони переподключил тот же (лидер не поменялся).

Сам postgres потерял 2 записи (видно по id).
Фактически не дошло до postgres'а 24 - 7 - 1 - 2 = 14 записей.

Картина идентична на всех репликах.


## Эксперимент 2: patronictl switchover


### На контейнере highload_hw_9 запускаем скрипт для тестовых insert'ов

```commandline
uv run /src/test_cluster_insert.py
```

### На контейнере лидера patroni переключаем лидера

```commandline
patronictl switchover --leader patroni3 --candidate patroni2
```

### На контейнере highload_hw_9 ждём немного и останавливаем скрипт для тестовых insert'ов

ctrl+c


### В sql ide смотрим, сколько пропущенных записей (через haproxy localhost:5000 test_db root/root)

```sql
select (max(id) - min(id) + 1) - count(distinct id) as total_missed_values
from test_schema.test_insert1
```

16

### Смотрим на сами записи

```sql
select *
from test_schema.test_insert1
order by id asc
limit 70
```

|id| data    | ts| host|
| -------- |---------| -------- | ------- |
|513	| data16	| 2025-11-04 14:37:49.655	| patroni3 |
|514	| data17	| 2025-11-04 14:37:50.026	| patroni3 |
|531	| data22	| 2025-11-04 14:37:51.851	| patroni2 |
|532	| data23	| 2025-11-04 14:37:52.221	| patroni2 |

По полю host видно, что лидер поменялся.
По id видно, что postgres потерял 16 записей.
Но судя по полю data (где фактически потеряно 4 записи), воможно, 
16 - это задвоения, полученные на разных репликах во время переключения лидера.





