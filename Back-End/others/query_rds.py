import pymysql
import datetime
import boto3
from botocore.exceptions import ClientError
from pytrends.request import TrendReq

endpoint = "cloudcomputingdb.cjzmmanfltlb.us-east-1.rds.amazonaws.com"
username = "admin"
passWord = "cloudcomputingteam14"
social_media_schema = 'twitter'
region = 'us-east-1'



def get_rds(conn):
    rows = None
    with conn.cursor() as cur:
        cur.execute('use ' + social_media_schema + ';')
        result = cur.fetchall()
        conn.commit()
        # sql = 'select * from ' + social_media_schema + ' where keyword="gamestop";'
        # sql = 'select count(*) from ' + social_media_schema + ' where keyword="gamestop";'
        sql = 'select count(*) from ' + social_media_schema + ';'
        print(sql)
        try:
            cur.execute(sql)
            rows = cur.fetchall()
        except:
            print("Retrieve fails")
        cur.close()
    return rows

twitter_conn = pymysql.connect(host=endpoint, user=username, password=passWord, db=social_media_schema)
data = get_rds(twitter_conn)
print(data)