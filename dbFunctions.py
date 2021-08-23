#!/usr/bin/env python3
#This file handles the interaction with the sqlite database

import sqlite3 as sql

class Connection:

    def __init__(self,db):
        self.db = db
        
        self.conn = sql.connect(self.db)

        c = self.conn.cursor()

        c = self.conn.execute("""
            CREATE TABLE IF NOT EXISTS FACTS (
                ID          INTEGER PRIMARY KEY AUTOINCREMENT,
                MSG         VARCHAR2(2000),
                TRIGGER     VARCHAR2(2000),
                SFW         INTEGER DEFAULT 0,
                DELETED     INTEGER DEFAULT 0,
                CNT         INTEGER DEFAULT 0,
                CREATOR     VARCHAR2(37),
                CREATED     VARCHAR2(23), /* YYYY-MM-DD HH:MI:SS CST */
                LASTCALLED  VARCHAR2(23)  /* YYYY-MM-DD HH:MI:SS CST */
            )
        """)

        c = self.conn.execute("""
            CREATE TABLE IF NOT EXISTS HISTORY (
                ID          INTEGER PRIMARY KEY AUTOINCREMENT,
                FACT        INTEGER NOT NULL,
                OLDMSG      VARCHAR2(2000),
                NEWMSG      VARCHAR2(2000),
                USER        VARCHAR2(37),
                EDITDATE    VARCHAR2(23),
                FOREIGN KEY (FACT)
                    REFERENCES FACTS (id)
            )
        """)

        c = self.conn.execute("""
            CREATE TABLE IF NOT EXISTS INVENTORY(
                ID          INTEGER PRIMARY KEY AUTOINCREMENT,
                GUILD       INTEGER NOT NULL,
                ITEM        VARCHAR2(100),
                USER        VARCHAR2(37),
                DATEADDED   VARCHAR2(23)
            )
        """)


