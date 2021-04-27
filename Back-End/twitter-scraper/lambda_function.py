# Twitter webscrape code
import pandas as pd
import itertools
import datetime as dt
import boto3
import pymysql
import tweepy
import text2emotion as te

# rds info to upload
rds_host = 'cloudcomputingdb.cjzmmanfltlb.us-east-1.rds.amazonaws.com'
rds_user = 'admin'
rds_password = 'cloudcomputingteam14'
region = 'us-east-1'

# our search terms, using syntax for Twitter's Advanced Search
keywords = ['tesla', 'apple', 'google', 'amazon', 'yahoo', 'facebook', 'nvidia', 'gold', 'oil', 'GameStop']

def get_last_commit(conn):
    date_time = None
    with conn.cursor() as cur:
        cur.execute('use event;')
        result = cur.fetchall()
        conn.commit()
        sql = 'select commit_date from commit where commit_id="twitter";'
        try:
            cur.execute(sql)
            rows = cur.fetchall()
            date_time = rows[0]['commit_date']
        except:
            print("Retrieve fails")
        cur.close()
        return date_time

def record_last_commit(conn, timestamp):
    date_time = timestamp.strftime("%Y-%m-%dT%H:%M:%S")
    with conn.cursor() as cur:
        cur.execute('use event;')
        result = cur.fetchall()
        conn.commit()
        sql = 'update commit set commit_date ="' + str(date_time) + \
              '" where commit_id="twitter";'

        try:
            cur.execute(sql)
            result = cur.fetchone()
            conn.commit()
        except:
            print("Retrieve fails")
        cur.close()
        return result

def get_tweets(key, n_scrape=1000, min_retweets=1):
    consumer_key = "ZzA1NFUgzvQZhR689ejKK16D1"
    consumer_secret = "0HewH88GQbBAwymoHgcy4Dy2KIMx5lwMlxSxJgLT2plc8cYHTz"
    access_token = "1385975364124561410-0bug8kykezY7bw839zuIe7BPdnkgpz"
    access_token_secret = "qO1DY0mqK8PkU3GtHTvbWZUGmG22LIioFYUiZtt5pNYh8"
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth,wait_on_rate_limit=True)

    text_query = key + ' min_retweets:' + str(min_retweets) + ' -filter:retweets -filter:replies lang:en'
    try:
        # Creation of query method using parameters
        tweets = tweepy.Cursor(api.search,q=text_query).items(n_scrape)

        # Pulling information from tweets iterable object
        tweets_list = [[tweet.id, tweet.text, tweet.created_at, tweet.favorite_count,
            tweet.retweet_count, tweet.user.screen_name] for tweet in tweets]
      
        tweets_df = pd.DataFrame(tweets_list, columns = ['id', 'content', 'date',
            'reply_count', 'retweet_count', 'user'])
        
        return tweets_df

    except BaseException as e:
        print('failed on_status,',str(e))
        return None

    print(tweets_df)

def filter_tweets(df, last_date, n_res=50):
    # convert to a DataFrame and keep only relevant columns
    df = df.sort_values(['retweet_count', 'reply_count'], ascending=[False, False])

    # Get only since the last scrape
    df = df[df['date'] >= last_date]

    # Top n_res results
    df = df.head(n_res)
    df.reset_index(drop=True, inplace=True)
    
    print(min(df['date']), max(df['date']))
    
    return df

def get_tweets_filtered(key, last_date, n_scrape, n_res, min_retweets=0):

    df = get_tweets(key, n_scrape, min_retweets=min_retweets)
    filtered = filter_tweets(df, last_date, n_res)
    
    print("Scraped for", key, "From", last_date, " - ", n_scrape, "scraped", filtered.shape[0], "tweets kept.")
    
    return filtered.to_dict()

def rds_handler(rows):
    conn = pymysql.connect(host=rds_host,
                           user=rds_user,
                           passwd=rds_password,
                           db='twitter',
                           connect_timeout=5,
                           cursorclass=pymysql.cursors.DictCursor)

    table_name = 'twitter' # test if test
    
    with conn.cursor() as cur:
        cur.execute('use ' + 'twitter' + ';')
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

def data_to_upload(dic, key, n_res, comprehend):
    to_upload = []
        
    for i in range(n_res):
        tweet = dic['content'][i]
        row = {}
        
        row['id'] = dic['id'][i]
        row['keyword'] = key
        row['post_time'] = dic['date'][i].strftime(
                    "%Y-%m-%dT%H:%M:%S")
        row['reply_count'] = dic['reply_count'][i]
        row['retweet_count'] = dic['retweet_count'][i]
        row['user'] = dic['user'][i]
        row['url'] = 'https://twitter.com/twitter/statuses/' + str(dic['id'][i])

        # Emotional Analysis
        emotion = te.get_emotion(tweet)
        for emot in ['Happy', 'Angry', 'Surprise', 'Sad', 'Fear']:
            row['emotion_' + emot] = emotion[emot]
        
        # Sentiment Analysis
        response = comprehend.detect_sentiment(
            Text=tweet,
            LanguageCode='en'
        )
        row['sentiment_overall'] = response['Sentiment']
        row['sentimentScore_Positive'] = response['SentimentScore']['Positive']
        row['sentimentScore_Negative'] = response['SentimentScore']['Negative']
        row['sentimentScore_Neutral'] = response['SentimentScore']['Neutral']
        row['sentimentScore_Mixed'] = response['SentimentScore']['Mixed']
        
        to_upload += [row]
        
    return to_upload

def lambda_handler(event, context):

    comprehend = boto3.client('comprehend')

    commit_conn = pymysql.connect(host=rds_host,
                           user=rds_user,
                           passwd=rds_password,
                           db='event',
                           connect_timeout=5,
                           cursorclass=pymysql.cursors.DictCursor)

    last_date = get_last_commit(commit_conn)#.replace(tzinfo=dt.timezone.utc)
    now_date = dt.datetime.now()#.replace(tzinfo=dt.timezone.utc)

    print("Populating for dates -",last_date, "to", now_date)

    n_res = 10
    n_scrape = 100
    min_retweets = 5

    for key in event['keys']:

            dic = get_tweets_filtered(key, last_date, n_scrape = n_scrape,
                n_res = n_res, min_retweets=min_retweets)

            if 'date' in dic.keys(): n = len(dic['date'])
            else: n = 0
            
            to_upload = data_to_upload(dic, key, n, comprehend)

            rds_handler(to_upload)
            
            print("Completed scrape -", key, "-", len(to_upload), "entries uploaded.")

    if event['last_commit'] == 1:
        # we want 15 minutes back because thats when triggers happened
        now_date = now_date - dt.timedelta(minutes=15)
        now_date_str = now_date.strftime("%Y-%m-%dT%H:%M:%S")
        record_last_commit(commit_conn, now_date)
        print("Updated last commit time", now_date_str)
            
    return {'status':200}



