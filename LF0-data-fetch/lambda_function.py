import json
import boto3
import pytrends
from pytrends.request import TrendReq
import pymysql
import sys

endpoint = "cloudcomputingdb.cjzmmanfltlb.us-east-1.rds.amazonaws.com"
username = "admin"
passWord = "cloudcomputingteam14"
database_name = "reddit"

connection = pymysql.connect(host=endpoint, user=username, password=passWord, db=database_name)

# import pytrends package
# get keyword from frontend
# request keyword via pytrend for search data from Google
# transform table to json format
# pass json format to frontend for graph display

def set_response(code, body):
    return {
        'statusCode': code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(body)
    }


def googlePop(query_text):
    # connect to Google Search API
    # pytrend = TrendReq(hl='en-US', tz=360)
    try:
        pytrend = TrendReq(hl='', tz=360)
        query_text_list = [query_text]
        pytrend.build_payload(query_text_list, cat=0, timeframe='today 1-m', geo='', gprop='')  # first param is a list
        # get keyword search date, value from Google

        preload = pytrend.interest_over_time()
        print("Google Search: data retreive success")
    except:
        print("Error from Google Search: too many search request, please try later")
        return []

    preload_cleaned = preload.drop(columns=["isPartial"])

    # transfer to json format
    preload_2_json = json.loads(preload_cleaned.to_json(orient='table'))['data']

    # modify format of "date"
    for data in preload_2_json:
        for key, value in data.items():
            if key == "date":
                data[key] = value[0:10]
        data['value'] = data.pop(query_text)

    # another way to write this loop:
    # for data in preload_2_json:
    #     data["date"] = data["date"][0:10]

    return preload_2_json


def generateListDate(year, month):#generate dates in a month
    listDate = []
    list31 = ['01', '03', '05', '07', '08', '10', '12']
    for i in range(1,10):
            strDate = year + '-' + month + '-0' + str(i)
            listDate.append(strDate)
    for i in range(10, 29):
            strDate = year + '-' + month + '-' + str(i)
            listDate.append(strDate)
    
    if year == '2021'and month == '02':
        return listDate
    
    elif year == '2020'and month == '02':
        listDate.append('2020-02-29')
        return listDate
    
    elif month in list31:
        for i in range(29, 32):
            strDate = year + '-' + month + '-' + str(i)
            listDate.append(strDate)
        return listDate
    else:
        for i in range(29, 31):
            strDate = year + '-' + month + '-' + str(i)
            listDate.append(strDate)
        return listDate


def senEmo(query_text):

    cursor = connection.cursor() #connect database
    print("RDB connected")

    listSenEmo = ['sentimentScore_Positive', 'sentimentScore_Negative', 'sentimentScore_Neutral', 
                        'sentimentScore_Mixed', 'emotion_Happy', 'emotion_Angry', 'emotion_Surprise', 
                        'emotion_Sad', 'emotion_Fear']
    keyWord = query_text

    list_tmp = []
    list_put_all = []
    dict_tmp = {}
    rows = []

    year = '2021' #input from user
    month = '01' #input from user

    for i in range(9): #iterate all sentiment and emotion
        listDate = generateListDate(year, month)
        for j in range(len(listDate) - 1): #iterate all datetime
            print("!!! loop start")
            sqlStr = "select avg(" + listSenEmo[i] + ") from reddit where keyword = '" + keyWord + "' and post_time between '" + listDate[j] + "' and '" + listDate[j+1] + "'"
            print(sqlStr)
            cursor.execute(sqlStr)
            print(cursor.execute(sqlStr))
            rows = cursor.fetchall()
            print("!!! rows = ", rows)
            dict_tmp['date'] = listDate[j]
            dict_tmp['value'] = rows[0][0]
            dict_copy = dict_tmp.copy()
            list_tmp.append(dict_copy)
        list_put_all.append(list_tmp.copy())

        list_tmp.clear()
        dict_tmp.clear()
    
    # print(list_put_all)
    # preload_2_json = json.dumps(list_put_all)
    # print(preload_2_json)
    # return preload_2_json
    return list_put_all


def lambda_handler(event, context):
    # print('####START####')
    search = event['queryStringParameters']
    if not search:
        return set_response(400, "Bad request, there was nothing in the query params")
    query_text = search['q']  # query_text is string
    print("0000", query_text)
    # query_text_list = [query_text]
    # print(query_text_list)
    
    graphList = []
    graphList.append(googlePop(query_text))
    if len(graphList[0]) == 0:
        return set_response(444, "Error from Google Search: too many search request, please try later")
    print(graphList)
    print("Google Search Popularity Completed")

    graphList.extend(senEmo(query_text))
    print("2222", graphList)
   
    return set_response(200, graphList)
