#!/usr/bin/env python3
#This file handles the interaction with the sqlite database

import random
import inspect
import sqlite3 as sql
from datetime import datetime
from dateutil import tz

class Connection:

    def __init__(self, db):
        self.db = db
        
        self.conn = sql.connect(self.db)

        c = self.conn.cursor()

        ###TESTING ONLY
        #try:
        #    c = self.conn.execute("""drop table FACTS""")
        #except:
        #    None
        
        try:
            c = self.conn.execute("""drop table HISTORY""")
        except:
            None
        
        #try:
        #    c = self.conn.execute("""drop table INVENTORY""")
        #except:
        #    None
        ###TESTING ONLY

        c = self.conn.execute("""
            CREATE TABLE IF NOT EXISTS FACTS (
                ID              INTEGER PRIMARY KEY AUTOINCREMENT,
                MSG             VARCHAR2(2000) NOT NULL,
                TRIGGER         VARCHAR2(2000),
                NSFW            INTEGER NOT NULL DEFAULT 0,
                DELETED         INTEGER NOT NULL DEFAULT 0,
                CNT             INTEGER NOT NULL DEFAULT 0,
                CREATOR         VARCHAR2(37),
                CREATED         VARCHAR2(23), /* YYYY-MM-DD HH:MI:SS TZ */
                LASTCALLED      VARCHAR2(23), /* YYYY-MM-DD HH:MI:SS TZ */
                CREATOR_ID      VARCHAR2(37),
                UNIQUE (MSG, TRIGGER)
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
                USER_ID      VARCHAR2(37)
            )
        """)

    def getCurrentDateTime(self):
        return(datetime.now(tz.gettz('America/Chicago')).strftime('%Y-%m-%d %H:%M:%S %Z'))

    def addToInventory(self, guild, user, item, userID):
        success = False
        
        try:
            c = self.conn.execute("""
                INSERT INTO INVENTORY (GUILD,ITEM,USER,DATEADDED,USER_ID)
                values(?,?,?,?,?)
                """,(guild,item,user,self.getCurrentDateTime(),userID))
                
            self.conn.commit()

            print('Given [' + item + ']')
            success = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)
        
        return(success)

    def getInventory(self, guild):   
        itemList = None  
        
        try:
            c = self.conn.execute("""
                select ITEM from INVENTORY where GUILD = ?
                """,(guild,))
            
            itemList = c.fetchall()
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(itemList)

    def getInventoryItem(self, guild):
        itemList = None
        item = None

        try:
            c = self.conn.execute("""
                select ITEM, ID from INVENTORY where GUILD = ?
                order by RANDOM() limit 1
                """, (guild,))
            
            itemList = c.fetchall()

            item = itemList[0][0] if len(itemList)==1 else 'nothing'

            if item != 'nothing':
                id = itemList[0][1]

                c = self.conn.execute("""
                    delete from INVENTORY where ID = ?
                """,(id,))

                self.conn.commit()

        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(item)

    def getItemDonor(self, guild, item):
        donors = []

        try:
            c = self.conn.execute("""select USER_ID from INVENTORY where ITEM = ? and GUILD = ?""",(item,guild))

            results = c.fetchall()
            results = [' '.join(elem) for elem in results]
            if len(results)>0:
                for i in results: donors.append(i)
                donors = list(set(donors))
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)
            donors = None

        return(donors)

    def getRandomFact(self, nsfw):
        id = None
        msgOut = None

        sqlIn= [0] if nsfw == 0 else [0,1]

        try:
            c = self.conn.execute(f"""
                select ID, MSG from facts 
                where DELETED = 0 and TRIGGER is null and NSFW in ("""+','.join(sqlIn)+""") 
                order by random() limit 1
            """,(sqlIn))

            results = c.fetchall()
            id = results[0][0]
            msgOut = results[0][1]
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(id,msgOut)
    
    def addRandFact(self, response, nsfw, creator, creatorID):
        success = False
        known = False

        try:
            c = self.conn.execute("""
                insert into FACTS (MSG, NSFW, CREATOR, CREATED, CREATOR_ID)
                values (?,?,?,?,?)    
            """, (response, nsfw, creator, self.getCurrentDateTime(), creatorID))

            self.conn.commit()

            print('Remembering [' + response + ']')
            success = True
        except sql.IntegrityError:
            success = False
            known = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(success, known)
        

    def addFact(self, trigger, response, nsfw, creator, creatorID):
        success = False
        known = False

        try:
            c = self.conn.execute("""
                insert into FACTS (MSG, TRIGGER, NSFW, CREATOR, CREATED, CREATOR_ID)
                values (?,?,?,?,?,?)
            """, (response, trigger, nsfw, creator, self.getCurrentDateTime(), creatorID))
            self.conn.commit()

            print('Remembering [' + trigger + '] is [' + response + ']')
            success = True
        except sql.IntegrityError:
            success = False
            known = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(success, known)

    def getFact(self, trigger, nsfw):
        success = False
        msgOut = None
        id = None

        sqlIn= [0] if nsfw == 0 else [0,1]

        try:
            if trigger == None:
                # Random Factoid
                c = self.conn.execute(f"""
                    select ID, MSG from FACTS 
                    where DELETED = 0 and TRIGGER is null and NSFW in ("""+','.join(str(n) for n in sqlIn)+""") 
                    order by random() limit 1
                """)
            else:
                # Triggered Factoid
                c = self.conn.execute(f"""
                    select ID, MSG from FACTS 
                    where DELETED = 0 and TRIGGER IS NOT NULL and TRIGGER = ? and NSFW in ("""+','.join(str(n) for n in sqlIn)+""") 
                    order by random() limit 1
                """, (trigger,))
            results = c.fetchall()
            if len(results)==0:
                id, msgOut = None, None
            else:
                id, msgOut = results[0][0], results[0][1]
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(id,msgOut)

    def factInfo(self, id):
        try:
            c = self.conn.execute("""
                select ID, TRIGGER, MSG, NSFW, DELETED, CREATOR, CREATED, CNT, LASTCALLED from FACTS where id = ?
            """, (id,))

            # Convert list of tuples into list
            results = [item for t in c.fetchall() for item in t]
            
        except Exception as e:
            results = None

            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(results)

    def updateLastCalled(self,id):
        try:
            c = self.conn.execute("""update FACTS set LASTCALLED=?, CNT = CNT + 1 where ID = ?""",(self.getCurrentDateTime(),id))
            self.conn.commit()
        except:
            None