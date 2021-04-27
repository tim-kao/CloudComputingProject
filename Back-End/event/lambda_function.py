import pymysql
import datetime
import boto3
from botocore.exceptions import ClientError
from pytrends.request import TrendReq

endpoint = "cloudcomputingdb.cjzmmanfltlb.us-east-1.rds.amazonaws.com"
username = "admin"
passWord = "cloudcomputingteam14"
event_db = "event"
twitter_db = 'twitter'
reddit_db = "reddit"
record_table = 'commit'
event_table = 'event_table'
social_media_schema = 'reddit'
region = 'us-east-1'
metric = ['pos', 'neg', 'neutral', 'mixed', 'happy', 'angry', 'surprise', 'sad', 'fear']


def google_search(keyword_list, time_range):
    pytrend = TrendReq()
    pytrend.build_payload(keyword_list, cat=0, timeframe=time_range, geo='', gprop='')
    df = pytrend.interest_over_time()
    df = df.drop(columns=["isPartial"])
    result = dict()
    for keyword in keyword_list:
        result[keyword] = df[keyword].mean()
    return result


def get_last_commit(conn):
    date_time = None
    with conn.cursor() as cur:
        cur.execute('use ' + event_db + ';')
        result = cur.fetchall()
        conn.commit()
        sql = 'select commit_date from ' + record_table + ' where commit_id="' + social_media_schema + '";'
        try:
            cur.execute(sql)
            rows = cur.fetchall()
            date_time = rows[0][0]
        except:
            print("Retrieve fails")
        cur.close()
    return date_time


def get_recent_date(conn, table, from_date, to_date):
    cursor = conn.cursor()  # connect database
    sql_query = "select keyword, url," + \
                "AVG(sentimentScore_Positive) as Positive, " + \
                "AVG(sentimentScore_Negative) as Negative," + \
                "AVG(sentimentScore_Neutral) as neutral, " + \
                "AVG(sentimentScore_Mixed) as mixed," + \
                "AVG(emotion_Happy) as happy," + \
                "AVG(emotion_Angry) as angry," + \
                "AVG(emotion_Surprise) as surprise," + \
                "AVG(emotion_Sad) as sad," + \
                "AVG(emotion_Fear) as fear " + \
                "FROM " + table + " where post_time between " + \
                 "('" + str(from_date) + "') and ('" + str(to_date) + \
                 "') group by keyword; "
    print(sql_query)
    cursor.execute(sql_query)
    rows = cursor.fetchall()
    d = dict()
    for row in rows:
        h = dict()
        h['url'] = row[1]
        for i, key in enumerate(metric):
            h[key] = row[i + 2]
        d[row[0]] = h.copy()
    return d


def lambda_handler(event, context):
    event_conn = pymysql.connect(host=endpoint, user=username, password=passWord, db=event_db)
    reddit_conn = pymysql.connect(host=endpoint, user=username, password=passWord, db=reddit_db)
    twitter_conn = pymysql.connect(host=endpoint, user=username, password=passWord, db=twitter_db)
    sms_conn = boto3.client('ses', region_name=region)
    # now_date_time = datetime.datetime.utcnow()
    # check between the last committed time and a day before it
    to_date = get_last_commit(event_conn)
    from_date = to_date - datetime.timedelta(days=1)
    reddit_rows = get_recent_date(reddit_conn, reddit_db, from_date, to_date)
    twitter_rows = get_recent_date(twitter_conn, twitter_db, from_date, to_date)
    rows = {**twitter_rows, **reddit_rows}
    # rows is a dict of dict
    print(rows)
    if not rows:
        return
    # get google trend
    chk_time_interval = from_date.strftime("%Y-%m-%dT%H") + ' ' + to_date.strftime("%Y-%m-%dT%H")
    items = list(rows.keys())
    popularity = dict()
    for i in range(0, len(items), 5):
        popularity = {**popularity, **google_search(items[i: min(i + 5, len(items))], chk_time_interval)}
    print(popularity)
    # check subscription
    cursor = event_conn.cursor()
    sql_query = 'select * from ' + event_table + ";"
    # print(sql_query)
    cursor.execute(sql_query)
    subscriptions = cursor.fetchall()
    for subscription in subscriptions:
        keyword = subscription[1]
        found = True
        if keyword in rows:
            for i in range(3, len(subscription)):
                if subscription[i]:
                    if i == 3:
                        if popularity[keyword] < subscription[i]:
                            found = False
                    else:
                        if rows[keyword][metric[i - 4]] < subscription[i]:
                            found = False
                    if not found:
                        break
        else:
            found = False
        if found:
            print('Trigger the threshold')
            if sms_handler(rows[keyword], subscription, sms_conn):
                delete_subscription(subscription, event_conn)
    event_conn.close()
    reddit_conn.close()
    return {
        'statusCode': 200
    }


def sms_handler(message, subscription, conn):
    # Replace sender@example.com with your "From" address.
    # This address must be verified with Amazon SES.
    SENDER = 'a3-tim@tim2021.de'

    email_addr = subscription[2]
    # If necessary, replace us-west-2 with the AWS Region you're using for Amazon SES.
    AWS_REGION = "us-east-1"

    # The subject line for the email.
    SUBJECT = "Event notification for your subscription"

    content = 'Your subscription has been satisfied and the details are shown in the following: \r\n' \
            + '<1> subscription time: ' + str(subscription[0]) + '\r\n' \
            + '<2> keyword: ' + subscription[1] + '\r\n' \
            + '<3> recommended article:' + message['url'] + '\r\n'
    for i in range(3, len(subscription)):
        if subscription[i]:
            if i == 3:
                content += '<4> popularity: ' + str(subscription[i]) + '\r\n'
            else:
                content += '<' + str(i + 1) + '>' + metric[i - 4] + ': ' + str(subscription[i]) + '\r\n'
    print(content)
    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = content

    # The HTML body of the email.
    BODY_HTML = content

    # The character encoding for the email.
    CHARSET = "UTF-8"

    # Try to send the email.
    try:
        # Provide the contents of the email.
        response = conn.send_email(
            Destination={
                'ToAddresses': [
                    email_addr,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': content,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
            # If you are not using a configuration set, comment or delete the
            # following line
            # ConfigurationSetName=CONFIGURATION_SET,
        )
    # Display an error if something goes wrong.
        print("Email sent! Message ID:")
        print(response['MessageId'])
        return True

    except ClientError as e:

        print(e.response['Error']['Message'])
        return False

def delete_subscription(subscription, conn):
    # date_time = datetime.datetime.utcfromtimestamp(subscription[0]).strftime("%Y-%m-%dT%H:%M:%S")
    with conn.cursor() as cur:
        cur.execute('use ' + event_db + ';')
        result = cur.fetchall()
        conn.commit()
        sql = 'delete from ' + event_table + ' where date=("' + str(subscription[0]) + '") and ' + \
              'keyword="' + subscription[1] + '" and ' + \
              'email="' + subscription[2] + '";'
        print(sql)
        try:
            cur.execute(sql)
            result = cur.fetchone()
            conn.commit()
            print('Deletion succeeds')
        except:
            print("Deletion fails")
        cur.close()
        return result
