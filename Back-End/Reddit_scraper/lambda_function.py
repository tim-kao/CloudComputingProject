import requests
import json
import datetime
import boto3
import text2emotion as te
import pymysql

# API endpoint
PUSHSHIFT_REDDIT_URL = 'https://api.pushshift.io/reddit/search/submission/'

# Data analyzer setting
CHECK_TITLE = True
SKIP_LINE = '\n'
MIN_ANALYSIS_STR_LEN = 20
data_list = ['id', 'full_link', 'author_fullname', 'title', 'num_comments', 'score', 'url']
emotion_list = ['Happy', 'Angry', 'Surprise', 'Sad', 'Fear']
subreddit_list = ['Trading', 'Daytrading', 'Forex', 'EliteTraders', 'finance', 'GlobalOffensiveTrade',
                  'stocks', 'StockMarket', 'algotrading', 'trading212', 'stock', 'invest', 'investing',
                  'wallstreetbets', 'personalfinance']
# subreddit_list = ['wallstreetbets']
scrape_size = 100
#subreddit_list = ['investing']
# elasticsearch path
es_url = 'https://search-social-media-es-2rwlned2gcap5gofltxb2ahmv4.us-east-1.es.amazonaws.com'
es_username = 'admin'
es_password = 'Cloudcomputingteam14!'

# rds info
rds_host = 'cloudcomputingdb.cjzmmanfltlb.us-east-1.rds.amazonaws.com'
rds_user = 'admin'
rds_password = 'cloudcomputingteam14'
region = 'us-east-1'
social_media = 'reddit'
event_schema = 'event'
record_table = 'commit'
# comprehend
MAX_COMPREHEND_TEXT_LEN = 4800

'''
https://api.pushshift.io/reddit/search/submission/
?subreddit=investing
&sort=asc
&sort_type=created_utc
&after=1538352000
&before=1541030399
&size=1000
&text=tesla
sort_type=score&sort=desc
sort_type=num_comments&sort=desc
'''

def fetchObjects(**kwargs):
    # Default paramaters for API query
    params = {
        'sort_type': 'created_utc',
        'sort': 'asc',
        'size': 1000
    }

    # Add additional paramters based on function arguments
    for key, value in kwargs.items():
        params[key] = value

    # Print API query paramaters
    print(params)

    # Set the type variable based on function input
    # The type can be 'comment' or 'submission', default is 'comment'
    type = 'comment'
    if 'type' in kwargs and kwargs['type'].lower() == 'submission':
        type = 'submission'

    # Perform an API request
    response = requests.get(PUSHSHIFT_REDDIT_URL, params=params, timeout=30)
    # Check the status code, if successful, process the data
    return response


def data_handler(response, rows, es_json, keyword):
    data = json.loads(response.text)['data']
    for num, datum in enumerate(data):
        if data_qa(datum):
            if CHECK_TITLE:
                article_text = datum['title'] + SKIP_LINE + datum['selftext']
            else:
                article_text = datum['selftext']
            article_text = article_text.replace('\n\n', '')[:MAX_COMPREHEND_TEXT_LEN]

            if article_text and len(article_text) > MIN_ANALYSIS_STR_LEN:
                row = dict()
                # Data population
                for item in data_list:
                    row[item] = datum[item]
                row['keyword'] = keyword
                row['text_len'] = len(article_text)
                row['post_time'] = datetime.datetime.utcfromtimestamp(datum['retrieved_on']).strftime(
                    "%Y-%m-%dT%H:%M:%S")

                # Sentiment analysis
                try:
                    response_comprehend = sentiment_handler(article_text)
                    row['sentiment_overall'] = response_comprehend['Sentiment']
                    row['sentimentScore_Positive'] = response_comprehend['SentimentScore']['Positive']
                    row['sentimentScore_Negative'] = response_comprehend['SentimentScore']['Negative']
                    row['sentimentScore_Neutral'] = response_comprehend['SentimentScore']['Neutral']
                    row['sentimentScore_Mixed'] = response_comprehend['SentimentScore']['Mixed']

                    # Emotion Analysis
                    emotion = te.get_emotion(article_text)
                    for item in emotion_list:
                        row['emotion_' + item] = emotion[item]

                    # dump
                    print('#', num, 'Sentiment:', row['sentiment_overall'], ', emotion:', emotion)
                    rows.append(row)

                    es_json += json.dumps({"index": {"_index": "reddit", "_type": "_doc", "_id": row['id']}}) + \
                               '\n' + \
                               json.dumps({"id": row['id'], "keyword": row['keyword']}) + \
                               '\n'
                except:
                    print("Comprehend fails, the procedure would skip this article.\n The article content:",
                          article_text)

    return es_json
    # {"index": {"_index": "reddit", "_type": "_doc", "_id": "vulYgQzS8RlpsQtwEtgRwA"}}
    # {"id": "vulYgQzS8RlpsQtwEtgRwA", "keyword": "apple"}

# check data integrity and availability
def data_qa(data):
    for item in data_list:
        if item not in data:
            return False
    return True

# request through api
def extract_reddit_data(**kwargs):
    # Open a file for JSON output
    # file = open('submissions.json', 'a')
    rows = []
    response = fetchObjects(**kwargs)
    result = 0
    if response.status_code == 200 and json.loads(response.text)['data']:
        print('Find ', len(json.loads(response.text)['data']), 'articles to process')
        es_json = data_handler(response, rows, '', kwargs['selftext'])
        rds_handler(rows)
        """
        es_response = es_handler(es_json)
        if es_response.status_code == 200:
            print('Elasticsearch commitment succeeds')
        else:
            print('Elasticsearch commitment fails')
        result = len(rows)
        """
    return result


def get_timestamp(date_time_instance):
    return int(datetime.datetime.timestamp(date_time_instance))


def sentiment_handler(text):
    client = boto3.client('comprehend')
    response = client.detect_sentiment(
        Text=text,
        LanguageCode='en'
    )
    return response


def rds_handler(rows):
    conn = pymysql.connect(host=rds_host,
                           user=rds_user,
                           passwd=rds_password,
                           db=social_media,
                           connect_timeout=5,
                           cursorclass=pymysql.cursors.DictCursor)
    with conn.cursor() as cur:
        cur.execute('use ' + social_media + ';')
        result = cur.fetchall()
        conn.commit()
        for row in rows:
            sql = 'insert into ' + social_media + ' values ('
            for value in row.values():
                if not isinstance(value, str):
                    sql += str(value) + ', '
                else:
                    sql += '"' + value.replace('"', "'") + '", '
            sql = sql[:-2] + ');'
            print(sql)
            try:
                cur.execute(sql)
                result = cur.fetchone()
                conn.commit()

            except:
                print("duplicate PK, update row")

        cur.close()

#   obselete
def es_handler(es_json, username=es_username, password=es_password, url=es_url):
    # response = requests.post(es_url, auth=HTTPBasicAuth(username, password), json=json, headers=headers)
    headers = {'Content-Type': 'application/json'}
    endpoint = url + '/_bulk'
    response = requests.post(endpoint, auth=(username, password), data=es_json, headers=headers)

    return response


def get_last_commit():
    num, date_time = None, None
    conn = pymysql.connect(host=rds_host,
                           user=rds_user,
                           passwd=rds_password,
                           db=event_schema,
                           connect_timeout=5,
                           cursorclass=pymysql.cursors.DictCursor)
    with conn.cursor() as cur:
        cur.execute('use ' + event_schema + ';')
        result = cur.fetchall()
        conn.commit()
        sql = 'select * from ' + record_table + ' order by commit_id desc;'
        try:
            cur.execute(sql)
            rows = cur.fetchall()
            num = rows[0]['commit_id']
            date_time = rows[0]['commit_date']
        except:
            print("Retrieve fails")
        cur.close()
        return num, date_time


def record_last_commit(num, timestamp):
    date_time = datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%dT%H:%M:%S")
    conn = pymysql.connect(host=rds_host,
                           user=rds_user,
                           passwd=rds_password,
                           db=event_schema,
                           connect_timeout=5,
                           cursorclass=pymysql.cursors.DictCursor)
    with conn.cursor() as cur:
        cur.execute('use ' + event_schema + ';')
        result = cur.fetchall()
        conn.commit()
        sql = 'insert into ' + record_table + ' values (' + str(num) + ', "' + str(date_time) + '");'

        try:
            cur.execute(sql)
            result = cur.fetchone()
            conn.commit()
        except:
            print("Retrieve fails")
        cur.close()
        return result


def data_producer(keyword, last_commit_timestamp, now_timestamp):
    count = 0
    for subreddit in subreddit_list:
        rows = extract_reddit_data(subreddit=subreddit, sort_type='score', sort='desc',
                                  size=scrape_size, before=now_timestamp, after=last_commit_timestamp,
                                  title=keyword, selftext=keyword)
        count += rows
        print("Commit: ", rows, "rows for keyword [" + keyword + "] from the recent day ")
    print("Total ", count, "rows committed for keyword[" + keyword + "]")

def lambda_handler(event, context):

    # checkout the latest commitment (utc+0)
    now_date_time = datetime.datetime.utcnow()
    now_timestamp = get_timestamp(now_date_time)
    commit_id, last_commit_date = get_last_commit()
    last_commit_timestamp = get_timestamp(last_commit_date)

    # Go through every keyword in the list

    # Time complexity O(KTLA), K # of keywords, T # of time period, L # of subreddits, A # of articles per time period
    keywords = ['tesla', 'apple', 'google', 'amazon', 'yahoo', 'facebook', 'nvidia', 'gold', 'oil', 'GameStop']
    # keywords = ['GameStop']
    for keyword in keywords:
        data_producer(keyword, last_commit_timestamp, now_timestamp)
    # record this commitment
    record_last_commit(commit_id + 1, now_timestamp)

