#!/usr/bin/env python3
# This file handles the interaction with the sqlite database

import re
import time
import sqlite3 as sql
import logging
from datetime import datetime
from dateutil import tz


class Connection:
    def __init__(self, db):
        self.db = db

        self.conn = sql.connect(self.db, cached_statements=0)

        c = self.conn.execute(
            """
            PRAGMA user_version;
        """
        )
        user_version = c.fetchone()[0]
        logging.info(f"DB is open with schema version {user_version}")

        if user_version == 0:
            logging.info(
                "Brand new db, or the db predates user_version tracking. creating tables."
            )
            self.conn.execute(
                """
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
                    REACTION        INTEGER NOT NULL DEFAULT 0,
                    MATCH_ANYWHERE  INTEGER NOT NULL DEFAULT 0
                )
            """
            )

            self.conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS FINDX ON FACTS (
                    ifnull(TRIGGER,'0'),
                    MSG,
                    REACTION
                )
            """
            )

            self.conn.execute(
                """
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
                    OLDTRIGGER      VARCHAR2(2000),
                    NEWTRIGGER      VARCHAR2(2000),
                    FOREIGN KEY (FACT) REFERENCES FACTS (ID)
                )
            """
            )

            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS INVENTORY(
                    ID          INTEGER PRIMARY KEY AUTOINCREMENT,
                    GUILD       INTEGER NOT NULL,
                    ITEM        VARCHAR2(100),
                    USER        VARCHAR2(37),
                    DATEADDED   VARCHAR2(23), /* YYYY-MM-DD HH:MI:SS TZ */
                    USER_ID     VARCHAR2(37)
                )
            """
            )

            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS GUILDSTATE(
                    GUILD       INTEGER NOT NULL,
                    LASTFACT    INTEGER,
                    BOTROLE     INTEGER NOT NULL DEFAULT 0,
                    RANDFREQ    INTEGER NOT NULL DEFAULT 5,
                    CHANNEL     INTEGER NOT NULL,
                    FOREIGN KEY (LASTFACT) REFERENCES FACTS (ID),
                    PRIMARY KEY (GUILD, CHANNEL)
                )
            """
            )

            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS SILENCED(
                    GUILD       INTEGER,
                    CHANNEL     INTEGER,
                    DURATION    INTEGER,
                    STARTED     REAL,
                    PRIMARY KEY (GUILD, CHANNEL)
                )
            """
            )

            self.conn.execute(
                """
                PRAGMA user_version = 3
            """
            )
            user_version = 3

        if user_version <= 1:
            logging.info("Upgrading to schema v2 (MATCH_ANYWHERE)")
            self.conn.execute(
                """
                ALTER TABLE FACTS ADD COLUMN MATCH_ANYWHERE INTEGER NOT NULL DEFAULT 0
            """
            )
            self.conn.execute(
                """
                PRAGMA user_version = 2
            """
            )
            user_version = 2

        if user_version <= 2:
            logging.info("Upgrading to schema v3 (TRIGGER HISTORY)")
            self.conn.execute(
                """
                ALTER TABLE HISTORY ADD COLUMN OLDTRIGGER VARCHAR2(2000)
            """
            )
            self.conn.execute(
                """
                ALTER TABLE HISTORY ADD COLUMN NEWTRIGGER VARCHAR2(2000)
            """
            )
            self.conn.execute(
                """UPDATE HISTORY SET OLDTRIGGER = (SELECT TRIGGER FROM FACTS WHERE ID = HISTORY.ID)"""
            )
            self.conn.commit()
            self.conn.execute(
                """
                PRAGMA user_version = 3
            """
            )
            user_version = 3

        logging.debug("I am leaving my schema-updating era")

    def close(self):
        self.conn.close()

    def getCurrentDateTime(self):
        return datetime.now(tz.gettz("America/Chicago")).strftime(
            "%Y-%m-%d %H:%M:%S %Z"
        )

    def getShutUpDuration(self, guild, channel):
        found = False
        duration = started = None

        try:
            c = self.conn.execute(
                """select DURATION, STARTED from SILENCED where GUILD = ? and CHANNEL = ?""",
                (guild, channel),
            )

            results = c.fetchall()

            if len(results) > 0:
                duration = results[0][0]
                started = results[0][1]
                if time.time() - started < (duration * 60):
                    found = True
                else:
                    self.delShutUpRecord(guild, channel)

        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

        return found, duration, started

    def delShutUpRecord(self, guild, channel):
        try:
            self.conn.execute(
                """delete from SILENCED where GUILD = ? and CHANNEL = ?""",
                (guild, channel),
            )
            self.conn.commit()
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

    def addShutUpRecord(self, guild, channel, duration):
        success = False

        try:
            self.conn.execute(
                """
            insert into SILENCED (GUILD, CHANNEL, DURATION, STARTED)
            values (?, ?, ?, ?)
            """,
                (guild, channel, duration, time.time()),
            )
            self.conn.commit()
            success = True
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

        return success

    def initGuild(self, guild, roleID, channel):
        success = False
        try:
            self.conn.execute(
                """
            insert into GUILDSTATE (GUILD, BOTROLE, CHANNEL)
            select ?, ?, ? where not exists (select GUILD from GUILDSTATE where GUILD = ? and CHANNEL = ?)
            """,
                (guild, roleID, channel, guild, channel),
            )
            self.conn.commit()

            success = True
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

        return success

    def deleteGuildState(self, guild, channel=None):
        success = False
        try:
            if channel is None:
                self.conn.execute(
                    """delete from GUILDSTATE where guild = ?""", (guild,)
                )
            else:
                self.conn.execute(
                    """delete from GUILDSTATE where guild = ? and channel = ?""",
                    (guild, channel),
                )
            self.conn.commit()

            success = True
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

        return success

    def updateFreq(self, guild, freq, channel):
        success = False

        try:
            self.conn.execute(
                """update GUILDSTATE set RANDFREQ = ? where GUILD = ? and CHANNEL = ?""",
                (freq, guild, channel),
            )
            self.conn.commit()
            success = True
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

        return success

    def getFreq(self, guild, channel):
        freq = None

        try:
            c = self.conn.execute(
                """select RANDFREQ from GUILDSTATE where GUILD = ? and CHANNEL = ?""",
                (guild, channel),
            )
            freq = c.fetchall()[0][0]
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

        return freq

    def getBotRole(self, guild, channel):
        role = None

        try:
            c = self.conn.execute(
                """select BOTROLE from GUILDSTATE where GUILD = ? and CHANNEL = ?""",
                (guild, channel),
            )
            role = c.fetchall()[0][0]
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

        return role

    def setBotRole(self, guild, roleID, channel):
        success = False

        try:
            self.conn.execute(
                """update GUILDSTATE set BOTROLE = ? where GUILD = ? and CHANNEL = ?""",
                (roleID, guild, channel),
            )
            self.conn.commit()
            success = True
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

        return success

    def updateLastFact(self, guild, lastFact, channel):
        success = False

        try:
            self.conn.execute(
                """update GUILDSTATE set LASTFACT = ? where GUILD = ? and CHANNEL = ?""",
                (lastFact, guild, channel),
            )
            self.conn.commit()
            success = True
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

        return success

    def addToInventory(self, guild, user, item, userID):
        success = False

        try:
            self.conn.execute(
                """
            INSERT INTO INVENTORY (GUILD, ITEM, USER, DATEADDED, USER_ID)
            values(?,?,?,?,?)
            """,
                (guild, item, user, self.getCurrentDateTime(), userID),
            )
            self.conn.commit()

            logging.info("Given [" + item + "]")
            success = True
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

        return success

    def getInventory(self, guild):
        itemList = None

        try:
            c = self.conn.execute(
                """select ITEM from INVENTORY where GUILD = ?""", (guild,)
            )

            itemList = c.fetchall()
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

        return itemList

    def getInventoryItem(self, guild):
        itemList = None
        item = None

        try:
            c = self.conn.execute(
                """
            select ITEM, ID from INVENTORY where GUILD = ?
            order by random() limit 1
            """,
                (guild,),
            )

            itemList = c.fetchall()

            item = itemList[0][0] if len(itemList) == 1 else "nothing"

            if len(itemList) == 1:
                id = itemList[0][1]

                c = self.conn.execute("""delete from INVENTORY where ID = ?""", (id,))

                self.conn.commit()

        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

        return item

    def getItemDonor(self, guild, item):
        donors = []

        try:
            c = self.conn.execute(
                """select USER_ID from INVENTORY where ITEM = ? and GUILD = ?""",
                (item, guild),
            )

            results = c.fetchall()
            results = [" ".join(elem) for elem in results]
            if len(results) > 0:
                for i in results:
                    donors.append(i)
                donors = list(set(donors))
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")
            donors = None

        return donors

    def addRandFact(self, response, nsfw, creator, creatorID):
        success = False
        known = False
        id = None
        deleted = 0

        try:
            c = self.conn.execute(
                """
            insert into FACTS (MSG, NSFW, CREATOR, CREATED, CREATOR_ID)
            values (?,?,?,?,?)
            """,
                (response, nsfw, creator, self.getCurrentDateTime(), creatorID),
            )

            c = self.conn.execute(
                """select max(ID) from FACTS where MSG = ?""", (response,)
            )
            results = c.fetchall()
            id = results[0][0]

            c = self.conn.execute(
                """
            insert into HISTORY (FACT, NEWMSG, DELETED, NSFW, USER, EDITDATE, USER_ID, NEWTRIGGER)
            select ID, MSG, DELETED, NSFW, CREATOR, CREATED, CREATOR_ID, TRIGGER from FACTS where ID = ?
            """,
                (id,),
            )
            self.conn.commit()

            logging.info(
                f"Remembering {id}:[{response}]".encode("ascii", "ignore").decode(
                    "ascii"
                )
            )
            success = True
        except sql.IntegrityError:
            success = False

            c = self.conn.execute(
                """select ID, DELETED from FACTS where MSG = ?""", (response,)
            )
            results = c.fetchall()
            id = results[0][0]
            deleted = results[0][1]

            if deleted:
                self.undelFact(id, creator, creatorID)

            known = True
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")
            self.conn.rollback()

        return (success, known, id, deleted)

    def addFact(
        self, trigger, response, nsfw, creator, creatorID, reaction, match_anywhere
    ):
        success = False
        known = False
        id = None
        deleted = 0

        try:
            c = self.conn.execute(
                """
            insert into FACTS (MSG, TRIGGER, NSFW, CREATOR, CREATED, CREATOR_ID, REACTION, MATCH_ANYWHERE)
            values (?,?,?,?,?,?,?,?)
            """,
                (
                    response,
                    trigger,
                    nsfw,
                    creator,
                    self.getCurrentDateTime(),
                    creatorID,
                    reaction,
                    match_anywhere,
                ),
            )

            c = self.conn.execute(
                """select max(ID) from FACTS where MSG = ?""", (response,)
            )
            results = c.fetchall()
            id = results[0][0]

            c = self.conn.execute(
                """
            insert into HISTORY (FACT, NEWMSG, DELETED, NSFW, USER, EDITDATE, USER_ID, NEWTRIGGER)
            select ID, MSG, DELETED, NSFW, CREATOR, CREATED, CREATOR_ID, TRIGGER from FACTS where ID = ?
            """,
                (id,),
            )
            self.conn.commit()
            logging.info(f"Remembering {id}: [{trigger}] is [{response}]")
            success = True
        except sql.IntegrityError:
            success = False

            c = self.conn.execute(
                """select ID, DELETED from FACTS where MSG = ? and trigger = ? and reaction = ?""",
                (response, trigger, reaction),
            )
            results = c.fetchall()
            id = results[0][0]
            deleted = results[0][1]

            if deleted:
                self.undelFact(id, creator, creatorID)

            known = True
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")
            self.conn.rollback()

        return (success, known, id, deleted)

    def getFact(self, trigger, nsfwIn, omitNothing):
        msgOut = None
        id = None
        reaction = None
        nsfwOut = 0

        sqlIn = [0] if nsfwIn == 0 else [0, 1]

        try:
            if trigger is None:
                # Random Factoid
                sql = (
                    """select ID, MSG, REACTION, NSFW from FACTS
                    where DELETED = 0 and TRIGGER is null and NSFW in ("""
                    + ",".join(str(n) for n in sqlIn)
                    + """)
                    and (("""
                    + str(omitNothing)
                    + """=1 and MSG not like '%$item%') or """
                    + str(omitNothing)
                    + """<>1)
                    order by RANDOM() limit 1
                """
                )
                c = self.conn.execute(sql)
            else:
                # Triggered Factoid
                sql = (
                    """
                    select ID, MSG, REACTION, NSFW from FACTS
                    where DELETED = 0 and TRIGGER IS NOT NULL and (TRIGGER = ? or (MATCH_ANYWHERE = 1 and instr(?, TRIGGER))) and NSFW in ("""
                    + ",".join(str(n) for n in sqlIn)
                    + """)
                    and (("""
                    + str(omitNothing)
                    + """=1 and MSG not like '%$item%') or """
                    + str(omitNothing)
                    + """<>1)
                    order by RANDOM() limit 1
                """
                )
                c = self.conn.execute(
                    sql,
                    (
                        trigger,
                        trigger,
                    ),
                )

            results = c.fetchall()

            if len(results) == 0:
                id, msgOut, reaction, nsfwOut = None, None, None, None
            else:
                id, msgOut, reaction, nsfwOut = (
                    results[0][0],
                    results[0][1],
                    results[0][2],
                    results[0][3],
                )
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

        return (id, msgOut, reaction, nsfwOut)

    def factInfo(self, id):
        try:
            c = self.conn.execute(
                """
                select ID, TRIGGER, MSG, NSFW, DELETED, CREATOR, CREATED, CNT, LASTCALLED, REACTION from FACTS where id = ?
            """,
                (id,),
            )

            # Convert list of tuples into list
            results = [item for t in c.fetchall() for item in t]

        except Exception as e:  # noqa: F841
            results = None
            logging.exception("Exception occurred.")

        return results

    def updateLastCalled(self, id):
        try:
            self.conn.execute(
                """update FACTS set LASTCALLED=?, CNT = CNT + 1 where ID = ?""",
                (self.getCurrentDateTime(), id),
            )
            self.conn.commit()
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

    def modFact(self, id, pattern, repl, user, userID, subType):
        valid = known = matched = success = changed = False
        oldText = newText = None

        colToChange = "TRIGGER" if subType.lower() == "t" else "MSG"

        try:
            c = self.conn.execute(
                f"""select {colToChange} from FACTS where id = ? limit 1""", (id,)
            )
            results = c.fetchall()
            known = True if len(results) != 0 else False
            oldText = results[0][0]

            srch = re.search(r"%s" % pattern, oldText, re.I)

            if srch is not None:
                matched = True

                try:
                    newText = re.sub(r"%s" % pattern, repl, oldText, re.I).strip()
                    if len(newText) >= 4 and not newText.startswith("!"):
                        valid = True

                        queryParams = (
                            oldText,
                            newText,
                            user,
                            self.getCurrentDateTime(),
                            userID,
                            id,
                        )

                        if newText != oldText:
                            c = self.conn.execute(
                                f"""update FACTS set {colToChange} = ? where ID = ?""",
                                (newText, id),
                            )

                            if subType == "t":
                                c = self.conn.execute(
                                    """
                                    insert into HISTORY (FACT, OLDTRIGGER, NEWTRIGGER, DELETED, NSFW, USER, EDITDATE, USER_ID, OLDMSG)
                                    select ID, ? as OLDTRIGGER, ? as NEWTRIGGER, DELETED, NSFW, ? as USER, ? as EDITDATE, ? as USER_ID, MSG
                                    from FACTS where ID = ?
                                """,
                                    queryParams,
                                )
                            else:
                                c = self.conn.execute(
                                    """
                                    insert into HISTORY (FACT, OLDMSG, NEWMSG, DELETED, NSFW, USER, EDITDATE, USER_ID, OLDTRIGGER)
                                    select ID, ? as OLDMSG, ? as NEWMSG, DELETED, NSFW, ? as USER, ? as EDITDATE, ? as USER_ID, TRIGGER
                                    from FACTS where ID = ?
                                """,
                                    queryParams,
                                )
                            self.conn.commit()

                            success = True
                            changed = True

                except Exception as e:  # noqa: F841
                    success = False
                    logging.exception("Exception occurred.")
                    self.conn.rollback()

        except Exception as e:  # noqa: F841
            success = False
            logging.exception("Exception occurred.")

        return [success, known, matched, valid, changed, oldText, newText]

    def getLastFactID(self, guild, channel):
        lastID = 0

        try:
            c = self.conn.execute(
                """select LASTFACT from GUILDSTATE where GUILD = ? and CHANNEL = ?""",
                (guild, channel),
            )
            results = c.fetchall()
            lastID = results[0][0]
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

        return lastID

    def delFact(self, id, user, userID, deleted):
        changed = success = False

        try:
            c = self.conn.execute(
                """select ID from FACTS where DELETED = ? and ID = ?""", (deleted, id)
            )
            results = c.fetchall()

            if results is None or len(results) == 0:
                c = self.conn.execute(
                    """update FACTS set DELETED = ? where ID = ?""", (deleted, id)
                )

                c = self.conn.execute(
                    """
                    insert into HISTORY (FACT, OLDMSG, DELETED, NSFW, USER, EDITDATE, USER_ID, OLDTRIGGER)
                    select ID as FACT, MSG as OLDMSG, DELETED, NSFW, ? as USER, ? as EDITDATE, ? as USER_ID, TRIGGER
                    from FACTS where ID =?
                """,
                    (user, self.getCurrentDateTime(), userID, id),
                )
                self.conn.commit()

                changed = True
                success = True
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")
            self.conn.rollback()

        return (success, changed)

    def undelFact(self, id, user, userID):
        undeleted = success = False

        try:
            c = self.conn.execute(
                """select ID from FACTS where DELETED = 0 and ID = ?""", (id,)
            )
            results = c.fetchall()

            if results is not None and len(results) == 1:
                undeleted = True
            else:
                c = self.conn.execute(
                    """update FACTS set DELETED = 0 where ID = ?""", (id,)
                )

                c = self.conn.execute(
                    """
                    insert into HISTORY (FACT, OLDMSG, DELETED, NSFW, USER, EDITDATE, USER_ID, OLDTRIGGER)
                    select ID, MSG, DELETED, NSFW, ? as USER, ? as EDITDATE, ? as USER_ID, TRIGGER
                    from facts where ID =?
                """,
                    (user, self.getCurrentDateTime(), userID, id),
                )
                self.conn.commit()

                success = True
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")
            self.conn.rollback()

        return (success, undeleted)

    def getFactHist(self, id):
        results = []
        success = False

        try:
            c = self.conn.execute(
                """
                select a.FACT, a.OLDTRIGGER, a.OLDMSG, a.NEWMSG, a.DELETED, a.NSFW, a.USER, a.EDITDATE, a.NEWTRIGGER
                from HISTORY a where a.FACT = ? order by a.ID desc
            """,
                (id,),
            )
            success = True
            results = c.fetchall()
        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

        return (success, results)

    def toggleNSFW(self, id, nsfw):
        results = []
        success = changed = False

        try:
            c = self.conn.execute(
                """select ID from FACTS where ID = ? and NSFW = ?""", (id, nsfw)
            )
            results = c.fetchall()

            if len(results) == 0:

                c = self.conn.execute(
                    """update FACTS set NSFW = ? where ID = ?""", (nsfw, id)
                )
                self.conn.commit()

                changed = True

            success = True

        except Exception as e:  # noqa: F841
            logging.exception("Exception occurred.")

        return (success, changed)
