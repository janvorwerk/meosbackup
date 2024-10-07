# meosbackup

## Why would I need this?

For orienteering race timing, [Meos](https://www.melin.nu/meos/en/) is my first choice option.

It has a client-server mode allowing several laptops to work on the same races on a local network. In that mode, there is a MySQL database server running on one of the computers.

Despite all the nice features, I identified one major drawback: for the builtin backup to work, you *must keep at least one Meos application open on each race of your event at all times*, with the builtin **backup service running**. This means that the builtin backup service must also be restarted whenever you restart Meos.

When you organise several races on the same day/period, you may be switching races several times in order to perform changes to all races (on-site registration for instance, ...).

My experience is that we tend to forget to restart Meos services from time to time.

The goal of `meosbackup` is to perform this backup in the background for all races, letting your start/stop/restart Meos as you need without having to worry about backups.

## Principle

In client-server mode, Meos stores all data in MySQL. For a given race all data are stored a separate database. Meos also keeps tracks of all races inside yet another database called `meosmain`. 

To perform a backup, you therefore need to backup the `meosmain` database, and the database of all races you may be modifying during the day(s). `meosbackup` will perform that backup every minute on a removable storage media (USB stick of SD card for instance).

In the event of a server crash, or a human mistake, you want to be able restore the database without additional stress. So you should have **another instance of MySQL server** ready on a spare computer. In that disaster event, the restore procedure is simple because with every backup `meosbackup` also generates recovery instructions on the same removable storage media.

Obviously, you should **test the restore procedure** on the spare computer!

## Prerequisites

You need to install
  * Python 3 with:
    * mysql-connector-python
    * shedule

Use:

    pip install mysql-connector-python
    pip install schedule

(you may need to use `pip3` instead)

Add `mysqldump` folder to the PATH


## MySQL install on Ubuntu

See https://dev.mysql.com/doc/refman/8.0/en/server-system-variables.html#sysvar_lower_case_table_names


    sudo debconf-set-selections <<< "mysql-server mysql-server/lowercase-table-names select Enabled"
    sudo apt instll mysql-server
    sudo mysql

then on the SQL prompt

    create user meos IDENTIFIED WITH mysql_native_password BY 'themeospassword';
    GRANT ALL PRIVILEGES ON * . * TO meos;
    FLUSH PRIVILEGES;


To restore on another server:

    mysql -u meos < output/meosmain_<date>.dump.sql
    mysql -u meos < output/2021_the_race_<date>.dump.sql

