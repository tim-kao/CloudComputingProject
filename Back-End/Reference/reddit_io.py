import time, sys, requests, io
from selenium import webdriver
from bs4 import BeautifulSoup

searchTerm = sys.argv[1]
subreddit = sys.argv[2]
year = int(sys.argv[3])
startDateEpoch = int(time.mktime((year,1,1,0,0,0,0,0,0))) #start date for search
endDateEpoch = int(time.time()) #current date for end date ###use time.mktime((whatever year you want,1,1,0,0,0,0,0,0)) instead of time.time()
size = 5000 #size limit

url = 'https://redditsearch.io/?term={}&dataviz=false&aggs=false&subreddits={}&searchtype=posts&search=true&start={}&end={}&size={}'.format(searchTerm,subreddit,startDateEpoch,endDateEpoch,size) #url for search
#browser driver controller
driver = webdriver.Firefox()
driver.get(url)
time.sleep(5) #delay added to wait for the page to complete loading
html = driver.page_source
soup = BeautifulSoup(html, 'html.parser')

#searching and extracting data from html source
contents = soup.find_all('div', class_='content')
titles = soup.find_all('div', class_='title')
dates = soup.find_all('time', class_='date')

#file saving
with io.open("redditsearch.csv", "w", encoding="utf-8") as f:
	for con, tit, dat in zip(contents, titles, dates):
		f.write(str(con['data-link'])+', '+str(tit.string)+', '+str(tit['data-url'])+', '+str(dat['title'])+'\n')

#close webdriver
driver.quit()