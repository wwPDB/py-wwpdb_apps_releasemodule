##
# File:  DbApiUtil.py
# Date:  04-May-2015
# Updates:
##
"""
Providing general APIs for database access

This software was developed as part of the World Wide Protein Data Bank
Common Deposition and Annotation System Project

Copyright (c) 2015 wwPDB

This software is provided under a Creative Commons Attribution 3.0 Unported
License described at http://creativecommons.org/licenses/by/3.0/.

"""
__docformat__ = "restructuredtext en"
__author__ = "Zukang Feng"
__email__ = "zfeng@rcsb.rutgers.edu"
__license__ = "Creative Commons Attribution 3.0 Unported"
__version__ = "V0.07"

import contextlib
import os
import sys
import time
import datetime
import MySQLdb


class DbApiUtil(object):
    def __init__(self, dbServer=None, dbHost=None, dbName=None, dbUser=None, dbPw=None, dbSocket=None, dbPort=None, verbose=False, log=sys.stderr):
        """
        """
        self.__debug = False
        self.__Nretry = 5
        self.__dbServer = dbServer
        self.__dbHost = dbHost
        self.__dbName = dbName
        self.__dbUser = dbUser
        self.__dbPw = dbPw
        self.__dbSocket = dbSocket
        self.__dbPort = dbPort
        self.__verbose = verbose  # pylint: disable=unused-private-member
        self.__lfh = log
        self.__schemaMap = {}
        self.__dbState = 0

        with contextlib.suppress(Exception):
            self.__dbPort = int(self.__dbPort)
        #
        self.__dbcon = None
        #
        if (self.__debug):
            self.__lfh.write("\n+DbApiUtil.__init__() using socket %r\n" % self.__dbSocket)
            self.__lfh.write("+DbApiUtil.__init__() using socket environment reference %r\n" % os.getenv("SITE_DB_SOCKET", None))
        #
        self.__getConnect()

    def __getConnect(self):
        """
        """
        try:
            if self.__dbSocket is None:
                self.__dbcon = MySQLdb.connect(db="%s" % self.__dbName, user="%s" % self.__dbUser, passwd="%s" % self.__dbPw,
                                               port=self.__dbPort, host="%s" % self.__dbHost, local_infile=1, connect_timeout=5)
            else:
                self.__dbcon = MySQLdb.connect(db="%s" % self.__dbName, user="%s" % self.__dbUser, passwd="%s" % self.__dbPw,
                                               port=self.__dbPort, host="%s" % self.__dbHost, unix_socket="%s" % self.__dbSocket, local_infile=1, connect_timeout=5)
            #
            self.__dbState = 0
        except MySQLdb.Error as e:
            self.__lfh.write("+DbApiUtil.getConnect(): Connection error %d: %s\n" % (e.args[0], e.args[1]))
            self.__lfh.write("+DbApiUtil.getConnect(): Connection failed using server %s host %s dsn %s user %s pw %s port %d socket %s\n"
                             % (self.__dbServer, self.__dbHost, self.__dbName, self.__dbUser, self.__dbPw, self.__dbPort, self.__dbSocket, ))
            self.__dbcon = None
        #

    def __reConnect(self):
        """
        """
        self.close()
        #
        for i in range(1, self.__Nretry):
            try:
                self.__getConnect()
                if self.__dbcon is not None:
                    return True
                #
            except MySQLdb.Error:
                self.__lfh.write("+DbApiUtil.reConnect() Cannot get re-connection : trying again\n")
                time.sleep(2 * i)
            #
        #
        return False

    def __runSelectSQL(self, query):
        """
        """
        if self.__dbcon is None:
            return None
        #
        try:
            self.__dbcon.commit()
            curs = self.__dbcon.cursor(MySQLdb.cursors.DictCursor)
            curs.execute(query)
            rows = curs.fetchall()
            return rows
        except MySQLdb.Error as e:
            self.__dbState = e.args[0]
            self.__lfh.write("Database error %d: %s\n" % (e.args[0], e.args[1]))
            return None
        #

    def __runUpdateSQL(self, query):
        """
        """
        if self.__dbcon is None:
            return None
        #
        try:
            curs = self.__dbcon.cursor()
            curs.execute("set autocommit=0")
            _nrows = curs.execute(query)  # noqa: F841
            self.__dbcon.commit()
            curs.execute("set autocommit=1")
            curs.close()
            return "OK"
        except MySQLdb.Error as e:
            self.__dbState = e.args[0]
            self.__lfh.write("Database error %d: %s\n" % (e.args[0], e.args[1]))
            try:
                self.__dbcon.rollback()
            except MySQLdb.Error:
                pass
            #
            return None
        #

    def setSchemaMap(self, schemaMap):
        """
        """
        self.__schemaMap = schemaMap

    def runSelectSQL(self, sql):
        """ method to run a query
        """
        for retry in range(1, self.__Nretry):
            ret = self.__runSelectSQL(sql)
            if ret is None:
                if self.__dbState > 0:
                    time.sleep(retry * 2)
                    if not self.__reConnect():
                        return None
                else:
                    return None
                #
            else:
                for myD in ret:
                    # We make copy of the keys to avoid "dictionary changed size during iteration"
                    items = list(myD.keys())
                    for item in items:
                        if not myD[item]:
                            del myD[item]
                        #
                    #
                #
                return ret
            #
        #
        return None

    def runUpdateSQL(self, sql):
        """ method to run a query
        """
        for retry in range(1, self.__Nretry):
            ret = self.__runUpdateSQL(sql)
            if ret is None:
                if self.__dbState > 0:
                    time.sleep(retry * 2)
                    if not self.__reConnect():
                        return None
                else:
                    return None
                #
            else:
                return ret
            #
        #
        return None

    def runUpdate(self, table=None, where=None, data=None):
        if not table:
            return None
        #
        if (not where) and (not data):
            return None
        #
        rowExists = False
        if where:
            sql = "select * from " + str(table) + " where " + " and ".join(["%s = '%s'" % (k, str(v).replace("'", "\\'")) for k, v in where.items()])
            rows = self.runSelectSQL(sql)
            if rows and len(rows) > 0:
                rowExists = True
            #
        #
        if rowExists and (not data):
            return "OK"
        #
        if rowExists:
            sql = "update " + str(table) + " set " + ",".join(["%s = '%s'" % (k, str(v).replace("'", "\\'")) for k, v in data.items()])
            if where:
                sql += " where " + " and ".join(["%s = '%s'" % (k, str(v).replace("'", "\\'")) for k, v in where.items()])
            #
        else:
            sql = "insert into " + str(table) + " (" + ",".join(["%s" % (k) for k, v in where.items()])
            if data:
                sql += "," + ",".join(["%s" % (k) for k, v in data.items()])
            #
            sql += ") values (" + ",".join(["'%s'" % (str(v).replace("'", "\\'")) for k, v in where.items()])
            if data:
                sql += "," + ",".join(["'%s'" % (str(v).replace("'", "\\'")) for k, v in data.items()])
            #
            sql += ")"
        #
        return self.runUpdateSQL(sql.replace("'NULL'", "NULL").replace("'null'", "null"))

    def runUpdateSQLwithKey(self, key=None, parameter=()):
        """
        """
        if (not key) or (not self.__schemaMap) or (key not in self.__schemaMap):
            return None
        #
        sql = self.__schemaMap[key]
        if parameter:
            sql = self.__schemaMap[key] % parameter
        #
        return self.runUpdateSQL(sql)

    def selectData(self, key=None, parameter=()):
        """
        """
        if (not key) or (not self.__schemaMap) or (key not in self.__schemaMap):
            return None
        #
        sql = self.__schemaMap[key]
        if parameter:
            sql = self.__schemaMap[key] % parameter
        #
        return self.runSelectSQL(sql)

    def close(self):
        """
        """
        if self.__dbcon is None:
            return
        #
        try:
            self.__dbcon.close()
        except MySQLdb.Error:
            self.__lfh.write("+DbApiUtil.close() DB connection lost - cannot close\n")
            self.__lfh.write("+DbApiUtil.close() Re-connecting to the database ..\n")
            self.__lfh.write("+DbApiUtil.close() UTC time = %s\n" % datetime.datetime.utcnow())
        #
