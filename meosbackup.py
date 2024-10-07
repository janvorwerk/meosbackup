#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#    Copyright (C) 2021  Jan Vorwerk
#
#    This file is part of 'meosbackup'
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

import codecs
import logging
import os
import re
import schedule
import subprocess
import textwrap
import time

import mysql.connector

LOGGER = logging.getLogger(__name__)

_HOST = 'localhost'  # '192.168.1.161'
_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'backups')
_INTERVAL_S = 60

# For development purposes...
_DAYS_AGO = 3
_DRY_RUN = False
_LOG_LEVEL = logging.INFO

def _build_file_name(dump_name, *, output_folder):
    '''Builds the file name for all dumps'''
    date_time = time.strftime('%Y-%m-%d_%H-%M-%S',time.localtime())
    return os.path.join(output_folder, f'{date_time}___{dump_name}.dump.sql')    


def __normalize(name):
    '''Replaces all spaces and dashes in the file names'''
    return re.sub('[ -]+', '_', name)


class MeosServer:
    '''
    Wraps a connection to a MeOS MySQL database
    '''
    def __init__(self, *, user='meos', password='', host='localhost', port=3306):
        try:
            self._user = user
            self._password = password
            LOGGER.debug('Connecting to %s...', host)
            self._conn = mysql.connector.connect(
                database='meosmain',
                user=user,
                password=password,
                host=host,
                port=port
            )
            if self._conn.is_connected():
                LOGGER.info('Connected to MeOS database, %s:%d', self._conn.server_host, self._conn.server_port)
        except mysql.connector.Error as e:
            self._conn = None
            LOGGER.error(e)
            raise e
    
    def disconnect(self):
        '''Closes the DB connection'''
        self._conn.close()
        LOGGER.info('Disconnected from MeOS database, %s:%d', self._conn.server_host, self._conn.server_port)


    def _select(self, *columns, from_table, where='', limit=1000):
        '''Wraps a SELECT statement to return a list of dicts rather than a list of tuples'''
        query = f'''select {', '.join(columns)} from {from_table} {where}'''
        LOGGER.debug('Executing %s', query)
        try:
            cursor = self._conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchmany(limit)
            result = [{item : r[index] for index, item in enumerate(columns)} for r in rows]
            return result
        finally:
            cursor.close()
    
    def list_races(self, *, after_days_ago):
        '''Lists the races in the MeOS database'''
        res = self._select('name', 'annotation', 'nameid',
            from_table='meosmain.oevent',
            where=f"where `Date` > ( CURDATE() + INTERVAL -{after_days_ago} DAY )"
            )
        for r in res:
            LOGGER.debug(r)
        return res
    
    def dump_database(self, *, database, output):
        '''Calls mysqldump to dump one database'''
        cmd = ['mysqldump',
            '--host', self._conn.server_host,
            '--port', str(self._conn.server_port),
            '--user', self._user,
            '--databases', database,
            '--result-file', output]
        LOGGER.debug("Executing %s", ' '.join(cmd))
        if self._password:  # avoid --password arg w/o a value
            cmd += [
                '--password', self._password
            ]
        if not _DRY_RUN:
            run = subprocess.run(cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf8'
                )
            if run.stdout:
                LOGGER.info(run.stdout)
            if run.stderr:
                LOGGER.error('Command returned (%d): %s', run.returncode, run.stderr)
            run.check_returncode()


def backup(*, host, after_days_ago, output_folder):
    '''Performs a backup of all races that are more recent
    than after_days_ago, along with a backup of the meosmain
    database'''
    LOGGER.info("=========== Backup of to %s", output_folder)
    with codecs.open(os.path.join(output_folder, 'HOW_TO_RESTORE.txt'), 'w', encoding='utf8') as helpf:
        try:
            meos = MeosServer(host=host)
            output=_build_file_name('meosmain', output_folder=output_folder)
            meos.dump_database(database='meosmain', output=output)
            LOGGER.info("Backup of 'meosmain' to '%s'... DONE", output)
            helpf.write(textwrap.dedent(f'''\
                ======== HOW TO RESTORE LOST RACES ========

                To restore the latest __list__ of races, run:
                        
                    mysql -u meos < {output}

            '''))
            races = meos.list_races(after_days_ago=after_days_ago)
            for r in races:
                if re.match(r'^[-_]+$', r['name']):  # I use this DB name as a visual separator
                    continue
                dump_name = f"{__normalize(r['name'])}"
                if r['annotation']:
                    dump_name += f"___{__normalize(r['annotation'])}"
                output = _build_file_name(dump_name, output_folder=output_folder)
                LOGGER.debug("Backup of '%s' (%s) to '%s'...", r['name'], r['annotation'], output)
                meos.dump_database(database=r['nameid'], output=output)
                LOGGER.info("Backup of '%s' (%s) to '%s'... DONE", r['name'], r['annotation'], output)
                helpf.write(textwrap.dedent(f'''\

                    To restore the latest race called '{r['name']}'
                            
                        mysql -u meos < {output}

                '''))
        finally:
            meos.disconnect()
        helpf.write(textwrap.dedent(f'''\

            Note:  to restore the former versions of any races, simply use a previous date!
        '''))

def backup_loop(*, destination):
    '''Repeatedly runs backups'''
    os.makedirs(destination, exist_ok=True)

    schedule.every(_INTERVAL_S).seconds.do(backup,
        host=_HOST,
        after_days_ago=_DAYS_AGO,
        output_folder=destination)

    schedule.run_all()  # run once w/o delay
    try:
        while True:
            n = schedule.idle_seconds()
            if n is None:
                # no more jobs
                break
            elif n > 0:
                # sleep exactly the right amount of time
                time.sleep(n)
            schedule.run_pending()
    except KeyboardInterrupt:
        LOGGER.info("Interrupted by KeyboardInterrupt")


if __name__ == '__main__':
    logformat = '%(asctime)s %(module)s %(levelname)s %(message)s'
    logging.basicConfig(level=_LOG_LEVEL, format=logformat)
    
    backup_loop(destination=_FOLDER)
