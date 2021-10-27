#!/usr/bin/env python3
#This file handles the interaction with the sqlite database

import re
import inspect
import time
import sqlite3 as sql
from datetime import datetime
from dateutil import tz
from discord.channel import TextChannel

class Connection:

    def __init__(self, db):
        self.db = db
        
        self.conn = sql.connect(self.db, cached_statements=0)

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
                REACTION        INTEGER NOT NULL DEFAULT 0
            )
        """)

        c = self.conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS FINDX ON FACTS (
                ifnull(TRIGGER,'0'),
                MSG,
                REACTION
            )
        """)

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
                FOREIGN KEY (FACT) REFERENCES FACTS (ID)
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
                GUILD       INTEGER NOT NULL,
                LASTFACT    INTEGER,
                BOTROLE     INTEGER NOT NULL DEFAULT 0,
                RANDFREQ    INTEGER NOT NULL DEFAULT 5,
                CHANNEL     INTEGER NOT NULL,
                FOREIGN KEY (LASTFACT) REFERENCES FACTS (ID),
                PRIMARY KEY (GUILD, CHANNEL)
            )
        """)

        c = self.conn.execute("""
            CREATE TABLE IF NOT EXISTS SILENCED(
                GUILD       INTEGER,
                CHANNEL     INTEGER,
                DURATION    INTEGER,
                STARTED     REAL,
                PRIMARY KEY (GUILD, CHANNEL)
            )
        """)        

    def close(self):
        self.conn.close()

    def getCurrentDateTime(self):
        return(datetime.now(tz.gettz('America/Chicago')).strftime('%Y-%m-%d %H:%M:%S %Z'))

    def getShutUpDuration(self, guild, channel):
        found = False
        duration = started = None

        try:
            c = self.conn.execute("""select DURATION, STARTED from SILENCED where GUILD = ? and CHANNEL = ?""", (guild, channel))

            results = c.fetchall()

            if len(results) > 0:
                duration = results[0][0]
                started = results[0][1]
                if time.time() - started < (duration*60):
                    found = True
                else:
                    self.delShutUpRecord(guild, channel)

        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return found, duration, started

    def delShutUpRecord(self, guild, channel):
        try:
            c = self.conn.execute("""delete from SILENCED where GUILD = ? and CHANNEL = ?""", (guild, channel))
            self.conn.commit()
            success=True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

    def addShutUpRecord(self, guild, channel, duration):
        success = False

        try:
            c = self.conn.execute("""
            insert into SILENCED (GUILD, CHANNEL, DURATION, STARTED)
            values (?, ?, ?, ?)
            """, (guild, channel, duration, time.time()))
            self.conn.commit()
            success=True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)
        
        return(success)

    def initGuild(self, guild, roleID, channel):
        success = False
        try:
            c = self.conn.execute("""
            insert into GUILDSTATE (GUILD, BOTROLE, CHANNEL) 
            select ?, ?, ? where not exists (select GUILD from GUILDSTATE where GUILD = ? and CHANNEL = ?)
            """, (guild, roleID, channel, guild, channel))
            self.conn.commit()
            
            success = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(success)

    def deleteGuildState(self, guild, channel = None):
        success = False
        try:
            if channel == None:
                c = self.conn.execute("""delete from GUILDSTATE where guild = ?""", (guild,))
            else:
                c = self.conn.execute("""delete from GUILDSTATE where guild = ? and channel = ?""", (guild, channel))
            self.conn.commit()

            success = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(success)

    
    def updateFreq(self, guild, freq, channel):
        success = False

        try: 
            c = self.conn.execute("""update GUILDSTATE set RANDFREQ = ? where GUILD = ? and CHANNEL = ?""", (freq, guild, channel))
            self.conn.commit()
            success = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(success)
    
    def getFreq(self, guild, channel):
        freq = None

        try:
            c = self.conn.execute("""select RANDFREQ from GUILDSTATE where GUILD = ? and CHANNEL = ?""", (guild, channel))
            freq = c.fetchall()[0][0]
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)
        
        return(freq)
    
    def getBotRole(self, guild, channel):
        role = None

        try:
            c = self.conn.execute("""select BOTROLE from GUILDSTATE where GUILD = ? and CHANNEL = ?""", (guild, channel))
            role = c.fetchall()[0][0]
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)
        
        return(role)
    
    def setBotRole(self, guild, roleID, channel):
        success = False

        try:
            c = self.conn.execute("""update GUILDSTATE set BOTROLE = ? where GUILD = ? and CHANNEL = ?""", (roleID, guild, channel))
            self.conn.commit()
            success = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(success)

    def updateLastFact(self, guild, lastFact, channel):
        success = False

        try: 
            c = self.conn.execute("""update GUILDSTATE set LASTFACT = ? where GUILD = ? and CHANNEL = ?""", (lastFact, guild, channel))
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
            c = self.conn.execute("""select ITEM from INVENTORY where GUILD = ?""", (guild,))
            
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
            order by random() limit 1
            """, (guild,))
            
            itemList = c.fetchall()

            item = itemList[0][0] if len(itemList) == 1 else 'nothing'

            if len(itemList) == 1:
                id = itemList[0][1]

                c = self.conn.execute("""delete from INVENTORY where ID = ?""", (id,))

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
        id = None

        try:
            c = self.conn.execute("""
            insert into FACTS (MSG, NSFW, CREATOR, CREATED, CREATOR_ID)
            values (?,?,?,?,?)    
            """, (response, nsfw, creator, self.getCurrentDateTime(), creatorID))

            c = self.conn.execute("""select max(ID) from FACTS where MSG = ?""", (response,))
            results = c.fetchall()
            id = results[0][0]

            c = self.conn.execute("""
            insert into HISTORY (FACT, NEWMSG, DELETED, NSFW, USER, EDITDATE, USER_ID)
            select ID, MSG, DELETED, NSFW, CREATOR, CREATED, CREATOR_ID from FACTS where ID = ?
            """, (id,))
            self.conn.commit()

            print(f'Remembering {id}:[{response}]')
            success = True
        except sql.IntegrityError:
            success = False

            c = self.conn.execute("""select ID from FACTS where MSG = ?""", (response,))
            results = c.fetchall()
            id = results[0][0]

            known = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)
            self.conn.rollback()

        return(success, known, id)

    def addFact(self, trigger, response, nsfw, creator, creatorID, reaction):
        success = False
        known = False
        id = None

        try:
            c = self.conn.execute("""
            insert into FACTS (MSG, TRIGGER, NSFW, CREATOR, CREATED, CREATOR_ID, REACTION)
            values (?,?,?,?,?,?,?)
            """, (response, trigger, nsfw, creator, self.getCurrentDateTime(), creatorID, reaction))

            c = self.conn.execute("""select max(ID) from FACTS where MSG = ?""", (response,))
            results = c.fetchall()
            id = results[0][0]
            print(id)

            c = self.conn.execute("""
            insert into HISTORY (FACT, NEWMSG, DELETED, NSFW, USER, EDITDATE, USER_ID)
            select ID, MSG, DELETED, NSFW, CREATOR, CREATED, CREATOR_ID from FACTS where ID = ?""", (id,))
            self.conn.commit()
            print(f'Remembering {id}: [{trigger}] is [{response}]')
            success = True
        except sql.IntegrityError:
            success = False

            c = self.conn.execute("""select ID from FACTS where MSG = ? and trigger = ? and reaction = ?""", (response, trigger, reaction))
            results = c.fetchall()
            id = results[0][0]

            known = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)
            self.conn.rollback()

        return(success, known, id)

    def getFact(self, trigger, nsfw, anywhere=False):
        success = False
        msgOut = None
        id = None

        sqlIn= [0] if nsfw == 0 else [0,1]

        try:
            if trigger == None:
                # Random Factoid
                sql = f"""select ID, MSG, REACTION from FACTS 
                    where DELETED = 0 and TRIGGER is null and NSFW in ("""+','.join(str(n) for n in sqlIn)+""") 
                    order by RANDOM() limit 1"""
                c = self.conn.execute(sql)
            else:
                # Triggered Factoid

                if anywhere:
                    trigger_cond = "instr(?, TRIGGER)"
                else:
                    trigger_cond = "TRIGGER = ?"

                sql = f"""
                    select ID, MSG, REACTION from FACTS 
                    where DELETED = 0 and TRIGGER IS NOT NULL and """ + trigger_cond + """ and NSFW in ("""+','.join(str(n) for n in sqlIn)+""") 
                    order by RANDOM() limit 1
                """
                c = self.conn.execute(sql,(trigger,))

            results = c.fetchall()
            
            if len(results)==0:
                id, msgOut, reaction = None, None, None
            else:
                id, msgOut, reaction = results[0][0], results[0][1], results[0][2]
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(id, msgOut, reaction)

    def factInfo(self, id):
        try:
            c = self.conn.execute("""
                select ID, TRIGGER, MSG, NSFW, DELETED, CREATOR, CREATED, CNT, LASTCALLED, REACTION from FACTS where id = ?
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
        valid = known = matched = success = changed = False
        oldResp = newResp = None

        try:
            c = self.conn.execute("""select MSG from FACTS where id = ? limit 1""", (id,))
            results = c.fetchall()
            known = True if len(results) != 0 else False
            oldResp = results[0][0]

            srch = re.search(r'%s' % pattern, oldResp, re.I)
            print(srch)
            print(pattern)
            print(oldResp)
            if srch != None:
                matched = True
                
                try:
                    newResp = re.sub(r'%s' % pattern, repl, oldResp, re.I).strip()
                    if len(newResp) >= 4 and not newResp.startswith('!'):
                        valid = True

                        if newResp != oldResp:
                            c = self.conn.execute("""update FACTS set MSG = ? where ID = ?""", (newResp, id))

                            c = self.conn.execute("""
                            insert into HISTORY (FACT, OLDMSG, NEWMSG, DELETED, NSFW, USER, EDITDATE, USER_ID)
                            select ID, ?, ? as NEWMSG, DELETED, NSFW, ? as USER, ? as EDITDATE, ? as USER_ID 
                            from FACTS where ID = ?
                            """, (oldResp, newResp, user, self.getCurrentDateTime(), userID, id))
                            self.conn.commit()

                            success = True
                            changed = True

                except Exception as e:
                    success = False
                    print(inspect.stack()[0][3])
                    print(inspect.stack()[1][3])
                    print(e)
                    self.conn.rollback()

        except Exception as e:
            success = False
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)
            
        return([success, known, matched, valid, changed, oldResp, newResp])

    def getLastFactID(self, guild, channel):
        lastID = 0

        try:
            c = self.conn.execute("""select LASTFACT from GUILDSTATE where GUILD = ? and CHANNEL = ?""", (guild, channel))
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
                from FACTS where ID =?
                """, (user, self.getCurrentDateTime(), userID, id))
                self.conn.commit()
                
                changed = True
                success = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)
            self.conn.rollback()
        
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
                from facts where ID =?
                """, (user, self.getCurrentDateTime(), userID, id))
                self.conn.commit()
                
                success = True
        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)
            self.conn.rollback()
        
        return(success, undeleted)

    def getFactHist(self, id):
        results = []
        success = False

        try:
            c = self.conn.execute("""
            select a.FACT, b.TRIGGER, a.OLDMSG, a.NEWMSG, a.DELETED, a.NSFW, a.USER, a.EDITDATE
            from HISTORY a, FACTS b where a.FACT = ? and a.FACT = b.ID order by a.ID desc
            """, (id,))
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
            c = self.conn.execute("""select ID from FACTS where ID = ? and NSFW = ?""", (id, nsfw))
            results = c.fetchall()

            if len(results) == 1:

                c = self.conn.execute("""update FACTS set NSFW = ? where ID = ?""", (nsfw, id))
                self.conn.commit()

                changed = True
                success = True

        except Exception as e:
            print(inspect.stack()[0][3])
            print(inspect.stack()[1][3])
            print(e)

        return(success,changed)
