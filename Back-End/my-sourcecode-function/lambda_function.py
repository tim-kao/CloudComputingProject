import requests
import json
import datetime
import boto3
import text2emotion as te
import pymysql

# API endpoint
PUSHSHIFT_REDDIT_URL = 'https://api.pushshift.io/reddit/search/submission/'

# Data analyzer setting
CHECK_EMPTY_TEXT_BY_TITLE = True
SKIP_LINE = '\n'
MIN_ANALYSIS_STR_LEN = 20
data_list = ['id', 'full_link', 'author_fullname', 'title', 'num_comments', 'score', 'url']
emotion_list = ['Happy', 'Angry', 'Surprise', 'Sad', 'Fear']

# elasticsearch path
es_url = 'https://search-social-media-es-2rwlned2gcap5gofltxb2ahmv4.us-east-1.es.amazonaws.com'
es_username = 'admin'
es_password = 'Cloudcomputingteam14!'

# rds info
rds_host = 'cloudcomputingdb.cjzmmanfltlb.us-east-1.rds.amazonaws.com'
rds_user = 'admin'
rds_password = 'cloudcomputingteam14'
region = 'us-east-1'
table_name = 'reddit'

'''
https://api.pushshift.io/reddit/search/submission/
?subreddit=2007scape
&sort=asc
&sort_type=created_utc
&after=1538352000
&before=1541030399
&size=1000
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
            if CHECK_EMPTY_TEXT_BY_TITLE:
                article_text = datum['title'] + SKIP_LINE + datum['selftext']
            else:
                article_text = datum['selftext']
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
                           json.dumps({"id": row['id'], "keyword": "apple"}) + \
                           '\n'
    return es_json
    # {"index": {"_index": "reddit", "_type": "_doc", "_id": "vulYgQzS8RlpsQtwEtgRwA"}}
    # {"id": "vulYgQzS8RlpsQtwEtgRwA", "keyword": "apple"}


def data_qa(data):
    for item in data_list:
        if item not in data:
            return False
    return True


def extract_reddit_data(**kwargs):
    # Open a file for JSON output
    # file = open('submissions.json', 'a')
    rows = []
    response = fetchObjects(**kwargs)
    result = 0
    if response.status_code == 200 and json.loads(response.text)['data']:
        print('Find ', len(json.loads(response.text)['data']), 'articles to process')
        es_json = data_handler(response, rows, '', kwargs['subreddit'])
        rds_handler(rows)
        es_response = es_handler(es_json, kwargs['subreddit'])
        if es_response.status_code == 200:
            print('Elasticsearch commitment succeeds')
        else:
            print('Elasticsearch commitment fails')
        result = len(rows)
    return result


def time_handler(start, end):
    now = datetime.datetime.utcnow()
    first_day = datetime.timedelta(start)
    last_day = datetime.timedelta(end)
    time_from = int(datetime.datetime.timestamp(now - first_day))
    time_by = int(datetime.datetime.timestamp(now - last_day))

    return time_by, time_from


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
                           db=table_name,
                           connect_timeout=5,
                           cursorclass=pymysql.cursors.DictCursor)
    # mySQL query insert example insert into reddit values ("m5yrsj",
    # "https://www.reddit.com/r/Tesla/comments/m5yrsj/going_on_my_first_road_trip_in_my_mylr_next_week/",
    # "t2_1521kr", "Going on my first road trip in my MYLR next week. What is the generally safe battery threshold?
    # Using ABRP to plan route but feeling uneasy about going down to 10% before stopping to charge!", 2, 1,
    # "https://i.redd.it/50q8tphxvan61.jpg", "tesla", 191, "2021-03-16T02:22:55", "MIXED", 0.15299846231937408,
    # 0.2308955043554306, 0.26710405945777893, 0.349001944065094, 0.17, 0.0, 0.17, 0.0, 0.67);

    with conn.cursor() as cur:
        cur.execute('use ' + table_name + ';')
        result = cur.fetchall()
        conn.commit()
        for row in rows:
            sql = 'insert into ' + table_name + ' values ('
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


def es_handler(es_json, keyword, username=es_username, password=es_password, url=es_url):
    # response = requests.post(es_url, auth=HTTPBasicAuth(username, password), json=json, headers=headers)
    headers = {'Content-Type': 'application/json'}
    index = 'keyword'
    endpoint = url + '/_bulk'
    response = requests.post(endpoint, auth=(username, password), data=es_json, headers=headers)

    return response


def data_producer(days, keyword, daily_size):
    total = 0
    for period in range(days):
        before, after = time_handler(period + 1, period)
        res = extract_reddit_data(subreddit=keyword, sort_type='score', sort='desc',
                                  size=daily_size, before=before, after=after)
        total += res
        print("Commit: ", res, "rows for keyword [" + keyword + "] from the recent day ",
              (period + 1), " to recent day", period)
    print("Total ", total, "rows committed for keyword[" + keyword + "]")


# keywords = ['tesla', 'apple', 'google']
keywords = ['apple', 'google']

for keyword in keywords:
    data_producer(90, keyword, 1000)

# sort_type = "score", "num_comments", "created_utc"
