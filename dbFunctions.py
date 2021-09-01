#!/usr/bin/env python3
#This file handles the interaction with the sqlite database

import re
import inspect
import sqlite3 as sql
from datetime import datetime
from dateutil import tz
from discord.channel import TextChannel

class Connection:

    def __init__(self, db):
        self.db = db
        
        self.conn = sql.connect(self.db)

        c = self.conn.cursor()

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

        c = self.conn.execute("""drop table HISTORY""")
        self.conn.commit()
        c = self.conn.execute("""
            CREATE TABLE IF NOT EXISTS HISTORY (
                ID              INTEGER PRIMARY KEY AUTOINCREMENT,
                FACT            INTEGER NOT NULL,
                OLDMSG          VARCHAR2(2000),
                NEWMSG          VARCHAR2(2000),
                DELETED         INTEGER NOT NULL DEFAULT 0,
                NSFW            INTEGER NOT NULL DEFAULT 0,
                USER            VARCHAR2(37),
                EDITDATE        VARCHAR2(23), /* YYYY-MM-DD HH:MI:SS TZ */
                USER_ID         VARCHAR2(37),
                FOREIGN KEY (ID) REFERENCES FACTS (ID)
            )
        """)

        c = self.conn.execute("""
            CREATE TABLE IF NOT EXISTS INVENTORY(
                ID          INTEGER PRIMARY KEY AUTOINCREMENT,
                GUILD       INTEGER NOT NULL,
                ITEM        VARCHAR2(100),
                USER        VARCHAR2(37),
                DATEADDED   VARCHAR2(23), /* YYYY-MM-DD HH:MI:SS TZ */
                USER_ID     VARCHAR2(37)
            )
        """)

        c = self.conn.execute("""
            CREATE TABLE IF NOT EXISTS GUILDSTATE(
                GUILD       INTEGER PRIMARY KEY,
                LASTFACT    INTEGER,
                BOTROLE     INTEGER NOT NULL DEFAULT 0,
                RANDFREQ    INTEGER NOT NULL DEFAULT 5,
                FOREIGN KEY (LASTFACT) REFERENCES FACTS (ID)
            )
        """)

    def getCurrentDateTime(self):
        return(datetime.now(tz.gettz('America/Chicago')).strftime('%Y-%m-%d %H:%M:%S %Z'))

    def initGuild(self, guild, roleID):
        success = False
        try:
            c = self.conn.execute("""
            insert into GUILDSTATE (GUILD, BOTROLE) 
            select ?, ? where not exists (select GUILD from GUILDSTATE where GUILD = ?)""", (guild, roleID, guild))
            self.conn.commit()

            success = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(success)
    
    def updateFreq(self, guild, freq):
        success = False

        try: 
            c = self.conn.execute("""update GUILDSTATE set RANDFREQ = ? where GUILD = ?""", (freq, guild))
            self.conn.commit()
            success = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(success)
    
    def getFreq(self, guild):
        freq = None

        try:
            c = self.conn.execute("""select RANDFREQ from GUILDSTATE where GUILD = ?""", (guild,))
            freq = c.fetchall()[0][0]
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)
        
        return(freq)
    
    def getBotRole(self, guild):
        role = None

        try:
            c = self.conn.execute("""select BOTROLE from GUILDSTATE where GUILD = ?""", (guild,))
            role = c.fetchall()[0][0]
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)
        
        return(role)
    
    def setBotRole(self, guild, roleID):
        success = False

        try:
            c = self.conn.execute("""update GUILDSTATE set BOTROLE = ? where GUILD = ?""", (roleID, guild))
            self.conn.commit()
            success = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(success)

    def updateLastFact(self, guild, lastFact):
        success = False

        try: 
            c = self.conn.execute("""update GUILDSTATE set LASTFACT = ? where GUILD = ?""", (lastFact, guild))
            self.conn.commit()
            success = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(success)

    def addToInventory(self, guild, user, item, userID):
        success = False
        
        try:
            c = self.conn.execute("""
            INSERT INTO INVENTORY (GUILD,ITEM,USER,DATEADDED,USER_ID)
            values(?,?,?,?,?)
            """, (guild, item, user, self.getCurrentDateTime(), userID))
                
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
            """, (guild,))
            
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

            item = itemList[0][0] if len(itemList) == 1 else 'nothing'

            if len(itemList) == 1:
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
            c = self.conn.execute("""select USER_ID from INVENTORY where ITEM = ? and GUILD = ?""", (item, guild))

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
    
    def addRandFact(self, response, nsfw, creator, creatorID):
        success = False
        known = False

        try:
            c = self.conn.execute("""
            insert into FACTS (MSG, NSFW, CREATOR, CREATED, CREATOR_ID)
            values (?,?,?,?,?)    
            """, (response, nsfw, creator, self.getCurrentDateTime(), creatorID))

            c = self.conn.execute("""select max(ID) from FACTS where MSG = ?""", (response,))
            results = c.fetchall
            maxID = results[0][0]

            c = self.conn.execute("""
            insert into HISTORY (FACT, NEWMSG, DELETED, NSFW, USER, EDITDATE, USER_ID)
            (select ID, MSG, DELETED, NSFW, USER, CREATED, USER_ID from FACTS where ID = ?)""", (maxID))

            self.conn.commit()

            print(f'Remembering {maxID}:[{response}]')
            success = True
        except sql.IntegrityError:
            success = False
            known = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(success, known, maxID)

    def addFact(self, trigger, response, nsfw, creator, creatorID):
        success = False
        known = False

        try:
            c = self.conn.execute("""
            insert into FACTS (MSG, TRIGGER, NSFW, CREATOR, CREATED, CREATOR_ID)
            values (?,?,?,?,?,?)
            """, (response, trigger, nsfw, creator, self.getCurrentDateTime(), creatorID))

            c = self.conn.execute("""select max(ID) from FACTS where MSG = ?""", (response,))
            results = c.fetchall
            maxID = results[0][0]

            c = self.conn.execute("""
            insert into HISTORY (FACT, NEWMSG, DELETED, NSFW, USER, EDITDATE, USER_ID)
            (select ID, MSG, DELETED, NSFW, USER, CREATED, USER_ID from FACTS where ID = ?)""", (maxID))

            self.conn.commit()

            print(f'Remembering {maxID}: [{trigger}] is [{response}]')
            success = True
        except sql.IntegrityError:
            success = False
            known = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(success, known, maxID)

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
            c = self.conn.execute("""update FACTS set LASTCALLED=?, CNT = CNT + 1 where ID = ?""", (self.getCurrentDateTime(), id))
            self.conn.commit()
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

    def modFact(self, id, pattern, repl, user, userID):
        known = matched = success = changed = False
        oldResp = newResp = None

        try:
            c = self.conn.execute("""select MSG from FACTS where id = ? limit 1""", (id,))
            results = c.fetchall()
            known = True if len(results) != 0 else False
            oldResp = results[0][0]

            if re.search(r'%s' % pattern, oldResp, re.I) != None:
                matched = True
                
                try:
                    newResp = re.sub(r'%s' % pattern, repl, oldResp, re.I).strip()
                    
                    if newResp != oldResp:
                        c = self.conn.execute("""update FACTS set MSG = ? where ID = ?""", (newResp, id))
                        self.conn.commit()

                        c = self.conn.execute("""
                        insert into HISTORY (FACT, OLDMSG, NEWMSG, DELETED, NSFW, USER, EDITDATE, USER_ID)
                        select ID, MSG, ? as NEWMSG, DELETED, NSFW, ? as USER, ? as EDITDATE, ? as USER_ID 
                        from FACTS where ID = ?""", (newResp, user, self.getCurrentDateTime(), userID, id))
                        self.conn.commit()

                        success = True
                        changed = True

                except Exception as e:
                    success = False
                    print(inspect.stack()[0][3])
                    print(inspect.stack()[1][3])
                    print(e)

        except Exception as e:
            success = False
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)
            
        return([success, known, matched, changed, oldResp, newResp])

    def getLastFactID(self, guild):
        lastID = 0

        try:
            c = self.conn.execute("""select LASTFACT from GUILDSTATE where GUILD = ?""", (guild,))
            results = c.fetchall()
            lastID = results[0][0]
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(lastID)
        
    def delFact(self, id, user, userID, deleted):
        changed = success = False

        try:
            c = self.conn.execute("""select ID from FACTS where DELETED = ? and ID = ?""", (deleted, id))
            results = c.fetchall()

            if results == None or len(results) == 0:
                c = self.conn.execute("""update FACTS set DELETED = ? where ID = ?""", (deleted, id))

                c = self.conn.execute("""
                insert into HISTORY (FACT, OLDMSG, DELETED, NSFW, USER, EDITDATE, USER_ID)
                select ID as FACT, MSG as OLDMSG, DELETED, NSFW, ? as USER, ? as EDITDATE, ? as USER_ID
                from FACTS where ID =?""", (user, self.getCurrentDateTime(), userID, id))

                self.conn.commit()
                
                changed = True
                success = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)
        
        return(success, changed)

    def undelFact(self, id, user, userID):
        undeleted = success = False
        
        try:
            c = self.conn.execute("""select ID from FACTS where DELETED = 0 and ID = ?""", (id,))
            results = c.fetchall()

            if results != None and len(results) == 1:
                undeleted = True
            else:
                c = self.conn.execute("""update FACTS set DELETED = 0 where ID = ?""", (id,))

                c = self.conn.execute("""
                insert into HISTORY (FACT, OLDMSG, DELETED, NSFW, USER, EDITDATE, USER_ID)
                select ID, MSG, DELETED, NSFW, ? as USER, ? as EDITDATE, ? as USER_ID
                from facts where ID =?""", (user, self.getCurrentDateTime(), userID, id))

                self.conn.commit()
                
                success = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)
        
        return(success, undeleted)

    def getFactHist(self, id):
        results = []
        success = False

        try:
            c = self.conn.execute("""
            select a.FACT, b.TRIGGER, a.OLDMSG, a.NEWMSG, a.DELETED, a.NSFW, a.USER, a.EDITDATE
            from HISTORY a, FACTS b where a.FACT = ? and a.FACT = b.ID order by ID desc""", (id,))
            success = True
            results = c.fetchall()
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)
        
        return(success,results)

    def toggleNSFW(self, id, nsfw):
        results = []
        success = changed = False

        try:
            c = self.conn.execute("""
            select ID from FACTS where ID = ? and NSFW = ?""", (id, nsfw))
            results = c.fetchall()

            if len(results) == 0:
                changed = True

                c = self.conn.execute("""
                update FACTS set NSFW = ? where ID = ?""", (nsfw, id))
                self.conn.commit()

                success = True

        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(success,changed)