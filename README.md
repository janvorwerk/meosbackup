# meosbackup

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

