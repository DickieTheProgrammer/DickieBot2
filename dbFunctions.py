#!/usr/bin/env python3
#This file handles the interaction with the sqlite database

import sqlite3 as sql
from datetime import datetime
from dateutil import tz

class Connection:

    def __init__(self, db):
        self.db = db
        
        self.conn = sql.connect(self.db)

        c = self.conn.cursor()

        ###TESTING ONLY
        try:
            c = self.conn.execute("""drop table FACTS""")
        except:
            None
        
        try:
            c = self.conn.execute("""drop table HISTORY""")
        except:
            None
        
        try:
            c = self.conn.execute("""drop table INVENTORY""")
        except:
            None
        ###TESTING ONLY

        c = self.conn.execute("""
            CREATE TABLE IF NOT EXISTS FACTS (
                ID              INTEGER PRIMARY KEY AUTOINCREMENT,
                MSG             VARCHAR2(2000) NOT NULL,
                TRIGGER         VARCHAR2(2000),
                SFW             INTEGER NOT NULL DEFAULT 0,
                DELETED         INTEGER NOT NULL DEFAULT 0,
                CNT             INTEGER NOT NULL DEFAULT 0,
                CREATOR         VARCHAR2(37),
                CREATED         VARCHAR2(23), /* YYYY-MM-DD HH:MI:SS TZ */
                LASTCALLED      VARCHAR2(23), /* YYYY-MM-DD HH:MI:SS TZ */
                CREATOR_ID      VARCHAR2(37),
                DISCRIMINATOR   INTEGER
            )
        """)
        c = self.conn.execute("""
            CREATE TABLE IF NOT EXISTS HISTORY (
                ID              INTEGER PRIMARY KEY AUTOINCREMENT,
                FACT            INTEGER NOT NULL,
                OLDMSG          VARCHAR2(2000),
                NEWMSG          VARCHAR2(2000),
                DELETED         INTEGER NOT NULL DEFAULT 0,
                USER            VARCHAR2(37),
                EDITDATE        VARCHAR2(23), /* YYYY-MM-DD HH:MI:SS TZ */
                USER_ID         VARCHAR2(37),
                DISCRIMINATOR   INTEGER,
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
                DATEADDED   VARCHAR2(23), /* YYYY-MM-DD HH:MI:SS TZ */
                USER_ID      VARCHAR2(37),
                DISCRIMINATOR   INTEGER
            )
        """)

    def addToInventory(self, guild, user, item, userID, disc):
        success = False
        currentDateStr = datetime.now(tz.gettz('America/Chicago')).strftime('%Y-%m-%d %H:%M:%S %Z')
        
        try:
            c = self.conn.execute("""
                INSERT INTO INVENTORY (GUILD,ITEM,USER,DATEADDED,USER_ID,DISCRIMINATOR)
                values(?,?,?,?,?,?)
                """,(guild,item,user,currentDateStr,userID,disc))
                
            self.conn.commit()

            success = True
        except Exception as e:
            success = False
            print(e)
        
        return(success)

    def getInventory(self,guild):
        allItems = None
        success = False