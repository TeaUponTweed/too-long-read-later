import sqlite3
import time
import uuid
from contextlib import contextmanager
from typing import List

import pandas as pd


@contextmanager
def transaction(conn):
    # We must issue a "BEGIN" explicitly when running in auto-commit mode.
    conn.execute("BEGIN")
    try:
        # Yield control back to the caller.
        yield
    except:
        conn.rollback()  # Roll back all changes if an exception occurs.
        raise
    else:
        conn.commit()


def nans_to_null(df):
    return df.where(pd.notnull(df), None)


def _tmp_table_name():
    return "tmp_" + str(uuid.uuid4()).replace("-", "")


def _tmp_table(cur, columns):
    t = _tmp_table_name()
    q = f"CREATE TEMP TABLE {t} ({','.join(columns)})"
    cur.execute(q)
    return t


def update(con, table_name, df: pd.DataFrame, what: List[str], where: List[str]):
    assert sqlite3.sqlite_version_info >= (
        3,
        36,
        0,
    ), "Requires features introduced in sqlite 3.36"
    # upload data as a tmp table
    cur = con.cursor()
    df = df[where + what]
    t = _tmp_table(cur, df.columns)
    df.to_sql(t, con, if_exists="append", index=False)

    q = f"""
    UPDATE {table_name}
    SET {",".join(f"{c}={t}.{c}" for c in what)}
    FROM {t}
    WHERE {",".join(f"{table_name}.{c}={t}.{c}" for c in where)}
    """
    cur.execute(q)
    # return indexes of affected rows
    return cur.fetchall()


def insert_get_id(con, table_name, df, insert_or_ignore="OR IGNORE"):
    if df.empty:
        print(f"Not inserting from empty DataFrame into {table_name}")
        return
    cur = con.cursor()

    q = f"""
    INSERT {insert_or_ignore} INTO {table_name} ({",".join(df.columns)})
    VALUES ({",".join("?" for _ in range(len(df.columns)))})
    """
    ids = []
    # this feels really inneficient, but getting the row id out is harder than it should be
    for _, row in df.iterrows():
        cur.execute(q, row.values)
        ids.append(cur.lastrowid)

    return ids


def insert(con, table_name, df):
    df.to_sql(table_name, con, if_exists="append", index=False)


def delete(con, table_name, df, where):
    # upload data as a tmp table
    cur = con.cursor()
    df = df[where]
    t = _tmp_table(cur, df.columns)
    df.to_sql(t, con, if_exists="append", index=False)
    q = f"""
    delete from {table_name}
    where id in (
    select {table_name}.id from {table_name}
    inner join {t} on {",".join(f"{table_name}.{c}={t}.{c}" for c in where)}
    )
    """
    cur.execute(q)


def get_df(con, q):
    return pd.read_sql(q, con)
