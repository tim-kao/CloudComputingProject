
import requests
import json
import datetime
import boto3
import text2emotion as te
import pymysql

# rds info
rds_host = 'cloudcomputingdb.cjzmmanfltlb.us-east-1.rds.amazonaws.com'
rds_user = 'admin'
rds_password = 'cloudcomputingteam14'
region = 'us-east-1'
table_name = 'reddit'



def rds_delete():
    conn = pymysql.connect(host=rds_host,
                           user=rds_user,
                           passwd=rds_password,
                           db=table_name,
                           connect_timeout=5,
                           cursorclass=pymysql.cursors.DictCursor)

    with conn.cursor() as cur:
        cur.execute('use ' + table_name + ';')
        result = cur.fetchall()
        conn.commit()
        cur.execute('Truncate table ' + table_name + ';')
        result = cur.fetchall()


rds_delete()