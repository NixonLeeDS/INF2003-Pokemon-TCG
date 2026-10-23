from contextlib import contextmanager

import pymysql
from pymongo import MongoClient

from config import Config


def mysql_connection(with_database=True, autocommit=True):
    kwargs = {
        "host": Config.MARIADB_HOST,
        "port": Config.MARIADB_PORT,
        "user": Config.MARIADB_USER,
        "password": Config.MARIADB_PASSWORD,
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": autocommit,
        "connect_timeout": 3,
        "read_timeout": 10,
        "write_timeout": 10,
    }
    if with_database:
        kwargs["database"] = Config.MARIADB_DATABASE
    return pymysql.connect(**kwargs)


@contextmanager
def mysql_cursor(autocommit=True):
    conn = mysql_connection(autocommit=autocommit)
    try:
        with conn.cursor() as cursor:
            yield conn, cursor
    finally:
        conn.close()


def mongo_database():
    client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000, socketTimeoutMS=10000)
    return client, client[Config.MONGODB_DATABASE]
