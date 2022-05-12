''' get article urls '''
#export PATH=$PATH:/home/drew99/Documents/programs_code/neuravnotezenost_slovenskih_medjiev/
import time
from bs4 import BeautifulSoup
from selenium import webdriver
options = webdriver.FirefoxOptions()
options.add_argument('--headless')
browser = webdriver.Firefox(options=options)
urls=[]
for i in range(1,20):
	url="https://nova24tv.si/rubrika/slovenija/politika/page/"+str(i)+"/"
	browser.get(url)
	time.sleep(3)
	html = browser.page_source
	soup = BeautifulSoup(html, 'lxml')
	a_elems = soup.select("#n24tv-masonry div div div div div.n24tv-article-thumbnail a")
	a_elems.extend(soup.select("#n24tv-content div div div div.n24tv-article-title a"))
	for a in a_elems:
		url = a.get('href')
		urls.append(url)



''' get article text '''
import pandas as pd
df = pd.DataFrame(columns=['Url','Naslov','Povzetek','Besedilo'])
for u in urls[0:]:
	browser.get(u)
	time.sleep(3)
	html = browser.page_source
	soup = BeautifulSoup(html, 'lxml')
	
	title = soup.select('h1')[0].getText()
	summary = soup.select('.post-content > p:first-of-type')[0].getText()
	texts = soup.select('.post-content > p:not(:first-of-type)')
	text=""
	for para in texts:
		text += para.getText() + "\n"
	text = text.replace(u'\xa0', u' ')
	df = df.append({'Url':u, 'Naslov':title, 'Povzetek':summary, 'Besedilo':text}, ignore_index=True)


ixs=[]
for i,r in df.iterrows():
	if len(r['Besedilo'])<10:
		ixs.append(i)

df = df.drop(ixs)