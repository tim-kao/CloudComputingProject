import time
from datetime import datetime,date
dt = datetime.now()
import praw
from settings import SETTINGS
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import numpy as np
from matplotlib import pyplot as plt
from scipy import polyval, polyfit
import pickle



reddit = praw.Reddit(client_id=SETTINGS['REDDIT_CLIENT_ID'],
                     client_secret=SETTINGS['REDDIT_CLIENT_SECRET'],
                     user_agent=SETTINGS['REDDIT_USER_AGENT'])

subreddit = reddit.subreddit("streetwear")
brand = SETTINGS['BRAND']

#--------------time-----------------------------------
start_date = date(dt.year, dt.month, dt.day)
end_date = date(dt.year-1, dt.month, dt.day)

print("Analyzing {} trends from {} to {}" .format(brand,end_date,start_date))

unixtime_present = time.mktime(start_date.timetuple())
unixtime_past = time.mktime(end_date.timetuple())

times = [unixtime_past]
for i in range(11):
    times.append(times[i]+2.628e+6)
times.append(unixtime_present)

sampletimes = [unixtime_past]
for i in range(6):
    sampletimes.append(sampletimes[i]+2*(2.628e+6))

sampletimes = times

print("Time intervals: ",sampletimes)
print(len(sampletimes))
#------------------------------------------------

def altspell(brand):
    spellings = [brand.upper(),brand + "s"]
    if " " in brand:
        acro = "".join(word[0] for word in brand.split())
    spellings.append(acro.upper())
    return spellings

spellings = altspell(brand)

print("Looking through spellings: ",spellings)

#---------Analysis-----------------------------------------------------------------------
analyzer = SentimentIntensityAnalyzer()


def analyze(item):
    snt = analyzer.polarity_scores(item)
    return [snt["compound"],snt["pos"],snt["neg"]]


#--------------------------------------------------------------------------------

submissions_analysed = 0
comments_analysed = 0
months = []


#testcode================================
"""
#search_results = subreddit.search(query = "comme de garcon")

#54print(search_results.next())
#print(reddit.submission(id = "66vv2f").title)

results = subreddit.submissions(sampletimes[0],sampletimes[1],extra_query="title:'{}'".format(spellings[2]))
#results = subreddit.search("and timestamp:{}..{} selftext:'comme de garcon".format(sampletimes[0],sampletimes[1]),sort = 'relevance',syntax= "cloudsearch")
for submission in results:
    print(submission.title)
    print(0)

print("\n done")
"""

for i in range(12): #iterating through months

    comment_scores = []
    count = []
    post_count = 0
    cmt_count = 0
    months.append([])

    sub_com_scores = []
    for altspell in spellings: #iterating through different spellings
        submissions = subreddit.submissions(start = sampletimes[i], end = sampletimes[i+1], extra_query= "title:'{}'".format(altspell))
        for submission in submissions:
            post_count+=1

            print("Analyzing '{}'".format(submission.title))
            sub_com_scores = []
            submission.comments.replace_more(limit=0)

            for comment in submission.comments.list(): #returns top level comments
                cmt_count+=1
                score = analyze(comment.body)
                if score[0]  != 0:
                    sub_com_scores.append(score)


            print("Comment scores for:{}\n{}\n ".format(submission.title,sub_com_scores))

            comment_scores.append(sub_com_scores)

    count.append(post_count)
    count.append(cmt_count)
    months[i].extend([count])


    compound  =  []
    for sub in comment_scores:
        if len(sub) != 0:
            for comment in sub:
                compound.append(comment[0])
        else:
            del sub

    score_ar = np.array(compound)
    avg = np.mean(score_ar)
    months[i].extend([comment_scores])

    print("Month {} results: {} \n  counts: {}".format(i, avg, months[i][0]))
    print("Month:", months[i])

#PICKLE--------------------------------------------------------------------------------
"""
with open("months.txt","wb") as storage:
    pickle.dump(months,storage)

"""
#ANALYSIS -----------------------------------------------------------------

comp_value = []
pos_value = []
neg_value = []
popularity = []


for month in months:
    popularity.append(month[0])
    avg = []
    for subs in month[1]: #iterating through comment scores
        for comment in subs:
            avg.append(comment[0])

    avg = np.array(avg)
    avg = np.mean(avg)
    comp_value.append(avg)

n = len(comp_value)
y = comp_value

x = np.linspace(0,1,n)
plt.plot(x, y, '.')

plt.show()

a, b, c, d= polyfit(x, y, 3)
y_pred = polyval([a, b, c, d], x)

x_out = np.linspace(0, 2, 20)
y_pred = polyval([a, b, c, d], x_out)

fig = plt.figure()
ax1 = fig.add_subplot(111)

ax1.plot(x, y, 'g.', x_out, y_pred, 'b-' )


