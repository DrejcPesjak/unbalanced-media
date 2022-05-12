'''
from googletrans import Translator
translator = Translator()
tr = translator.translate("Danes sem jedel pašteto Argeto za zajtrk.", src='sl')
print(tr.text)

from textblob import TextBlob
from bs4 import BeautifulSoup
TextBlob(tr.text).sentiment
'''



''' list of political parties, and their memebers '''
#ime stranke, kratica stranke, predsednik ime in naziv, vplivni člani 
df = pd.read_csv("/home/drew99/Documents/programs_code/neuravnotezenost_slovenskih_medjiev/stranke.csv")
df = df[['Stranka .1','Stranka .2','Predsednik ']].iloc[1:]
df = df.drop(19)
df['Stranka .1'] = df['Stranka .1'].str.replace('\[(.*?)\]','',regex=True)
df['Stranka .2'] = df['Stranka .2'].str.replace('\[(.*?)\]','',regex=True)
df['Predsednik '] = df['Predsednik '].str.replace('\[(.*?)\]','',regex=True)
df = df.rename(columns={'Stranka .1':'Kratica stranke', 'Stranka .2':'Ime stranke', 'Predsednik ':'Predsednik'})



import requests
base="https://www.24ur.com"
'''
html = requests.get("https://www.24ur.com/novice/volitve").content
soup = BeautifulSoup(html)
a_elems = soup.select("div.news-list__item a")
urls=[]
for a in a_elems:
	url = a.get('href')
	urls.append(url)
'''

''' get article urls '''
#export PATH=$PATH:/home/drew99/Documents/programs_code/neuravnotezenost_slovenskih_medjiev/
import time
from bs4 import BeautifulSoup
from selenium import webdriver
options = webdriver.FirefoxOptions()
options.add_argument('--headless')
#browser = webdriver.Firefox(options=options, executable_path='/home/drew99/Documents/programs_code/neuravnotezenost_slovenskih_medjiev/geckodriver')
browser = webdriver.Firefox(options=options)
urls=[]
for i in range(1,20):
	#url="https://www.24ur.com/arhiv/novice/volitve?stran="+str(i)
	url="https://www.24ur.com/iskanje?q=politika&stran="+str(i)
	browser.get(url)
	time.sleep(3)
	html = browser.page_source
	soup = BeautifulSoup(html, 'lxml')
	#a_elems = soup.select("div.timeline__right a")
	a_elems = soup.select("main div div:nth-child(3) a")
	for a in a_elems:
		url = a.get('href')
		urls.append(url)

urls = list(filter(None, urls))
urls = list(filter(lambda x: ('/video?video=' not in x), urls))
#<div class="article__summary">
#<h1 class="article__title">
#<onl-article-body class="article__body-dynamic dev-article-contents"> span p
#<div class="article__tags"><a class="article__tag" href="/iskanje?q=volitve2022"> VOLITVE2022 </a><!----><!---->
#<meta name="keywords" content="soočenje, svet, odločitev 2022, dejstva">

''' get article text '''
import pandas as pd
df = pd.DataFrame(columns=['Url','Naslov','Povzetek','Besedilo'])
#keys=[]
for u in urls:
	browser.get(base+u)
	time.sleep(3)
	html = browser.page_source
	soup = BeautifulSoup(html, 'lxml')
	
	titles = []
	#try if any of these selectors catch the title
	titles.append(soup.select('.article__title'))
	titles.append(soup.select('.onl-article-title'))
	titles.append(soup.select("div h1"))
	filtered = list(filter(lambda x: (len(x)>0), titles))
	if filtered:
		title = filtered[0][0].getText()
	else:
		continue;
	summary = soup.select('.article__summary')
	if summary:
		summary = summary[0].getText()
	else:
		summary = soup.select('.article__body .px-article-head')[0].getText()
	texts = soup.select('.article__body-dynamic span p')
	text=""
	for para in texts:
		text += para.getText() + "\n"
	#es = soup.select('meta[name="keywords"]')
	#if len(es)>0:
	#	keys.append(es[0].get('content'))
	df = df.append({'Url':base+u, 'Naslov':title, 'Povzetek':summary, 'Besedilo':text}, ignore_index=True)


#keywords=[]
#for i in keys:
#     keywords.extend(i.lower().split(', '))
#
#keywords=set(keywords)


ixs=[]
for i,r in df.iterrows():
	if len(r['Besedilo'])<10:
		ixs.append(i)

df = df.drop(ixs)


''' TRANSLATE text slo->eng'''
import pandas as pd
df=pd.read_csv("novice.csv")
from googletrans import Translator
translator = Translator()
dfeng = pd.DataFrame(columns=['Url','Title','Summary','Text'])
for i,r in df.iterrows():
	title = translator.translate(r['Naslov'], src='sl').text
	summary = translator.translate(r['Povzetek'], src='sl').text
	besedilo = r['Besedilo']
	txt=""
	if len(besedilo)>15000:
		txt = translate15k(translator,besedilo)
	else:
		txt = translator.translate(besedilo, src='sl').text
	dfeng = dfeng.append({'Url':r['Url'], 'Title':title, 'Summary':summary, 'Text':txt}, ignore_index=True)

def translate15k(translator, text):
	l = len(text)
	r = l//15000 +1
	isplit = l//r
	trans = ""
	s=0;e=0
	while s<l and e<l:
		e = s+isplit if s+isplit < l else l #be careful to not go index out of bounds
		enew = text.rfind('\n',s,e) #find end of parapgraph
		trans += translator.translate(text[s:enew]).text + '\n' #translate
		s=enew
	return trans

dfsloeng = pd.concat([df.reset_index(drop=True),dfeng.drop('Url',axis=1)], axis=1)
dfsloeng.to_csv("newsnovice.csv",index=False)


''' get stranke in text '''
allstr=""
for i in range(len(dfstr2)):
	a = ','.join(dfstr2.iloc[i])
	allstr += "{:<2525}".format(a) #2525 is length of the longest sequence, pad everything to that size


#re.findall('\((.*?)\)',txt)
#'sds' in txt.lower().split()
#'naša dežela' in txt.lower()
#allstr.index('dobra država')//2525
#print(e.text, e.label_) #PERSON, ORG, GPE(Geopolitical entity, i.e. countries, cities, states)
#kratice.extend(re.findall('\((.*?)\)',txt))
import re
import string
import regex #not same as re
import pandas as pd
import numpy as np
from textblob import TextBlob
import spacy
nlp = spacy.load("en_core_web_sm")
dfnew = pd.read_csv("newsnovice.csv")
dfstr2 = pd.read_csv("stranke_finall.csv")
dfstr2 = dfstr2.apply(lambda x: x.astype(str).str.lower())

dfnew2 = dfnew.copy()
dfnew2['Stranke']=""
dfnew2['Stevilo pojavitev']=""
dfnew2['Max stranka']=""
dfnew2['Sentiment']=np.nan
dfnew2['Subjektivnost']=-1.0

for i in range(len(dfnew2)):
	txt = dfnew.loc[i,'Besedilo'].lower() #slovenian text
	txte = dfnew.loc[i,'Text'].lower() #english text
	kratice = []
	kratice.extend(get_str_from_people(txte,dfstr2,allstr,nlp))
	kratice.extend(get_str_from_brackets(txt,dfstr2))
	kratice.extend(get_str_from_txt(txt,dfstr2))
	kratice.extend(get_str_from_txt_name(txt,dfstr2))
	print(i,kratice)
	if len(kratice)<1:
		continue;
	values, counts = np.unique(kratice, return_counts=True)
	print(values,counts)
	#avg_str = values[np.where(counts>np.mean(counts))[0]]
	#avg1_str = values[np.where(counts>np.mean(counts)+1)[0]]
	max_str = values[np.argmax(counts)]
	#
	so = TextBlob(txte).sentiment
	#
	dfnew2.loc[i,'Stranke'] = ",".join(values)
	dfnew2.loc[i,'Stevilo pojavitev'] = ",".join([str(x) for x in counts])
	#list(map(int, st_pojavitev.split(",")))  #reverse operation
	dfnew2.loc[i,'Max stranka'] = max_str
	dfnew2.loc[i,'Sentiment'] = so.polarity #-1 negative, 0 neutral, 1 positive
	dfnew2.loc[i,'Subjektivnost'] = so.subjectivity #0 objective, 1 subjective




def get_str_from_people(txte,dfstr2,allstr,nlp):
	doc = nlp(txte)
	kr = []
	for e in doc.ents:
		if len(e.text.split())>1 and e.label_=='PERSON':
			if e.text.lower() in allstr:
				i = allstr.index(e.text.lower())//2525
				kr.append(dfstr2.loc[i,'Kratica stranke'])
			else:
				ee = re.sub(r'[()]', '', e.text.lower()) #remove all parentheses
				for i in range(1,3): #up to 3 differences
					l = regex.findall('(?:' + ee + '){e<=' + str(i) + '}', allstr)
					if len(l)>0:
						i = allstr.index(l[0])//2525
						kr.append(dfstr2.loc[i,'Kratica stranke'])
						break;
	return kr


def get_str_from_brackets(txt,dfstr2):
	#stranke napisane v oklepajih
	besede = re.findall('\((.*?)\)',txt)
	imena = list(dfstr2['Ime stranke'])
	kratice = list(dfstr2['Kratica stranke'])
	krat = []
	for k in besede:
		if k in imena:
			i = dfstr2.index[dfstr2['Ime stranke'] == k].tolist()[0]
			krat.append(dfstr2.loc[i,'Kratica stranke'])
		elif k in kratice:
			krat.append(k)
	return krat


def get_str_from_txt(txt,dfstr2):
	#kratice strank kjerkoli (split->ena beseda)
	#https://stackoverflow.com/a/43934982
	kratice=[]
	translator = str.maketrans(string.punctuation, ' '*len(string.punctuation)) #remove punctuations
	splt = txt.translate(translator).split()
	for k in dfstr2['Kratica stranke']:
		if k in splt:
			kratice.extend([k]*splt.count(k))
	return kratice


def get_str_from_txt_name(txt,dfstr2):
	#pojavitev celotnega imena stranke v besedilu
	kratice=[]
	for i,k in dfstr2[['Kratica stranke','Ime stranke']].iterrows():
		ime = k['Ime stranke']
		kra = k['Kratica stranke']
		if ime in txt:
			kratice.extend([kra]*txt.count(ime))
	return kratice


''' graph sentiment per political party '''
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
dfnew2 = pd.read_csv("24ur_data.csv")
dg = dfnew2.dropna()
g = dg[['Max stranka','Sentiment']]
#plot everything
g.plot(kind='scatter',x='Max stranka',y='Sentiment',color='red', ylim=[-1,1])
plt.show()


#plot only articles where mostly 1 party was mentioned
ix=[]
for i,k in dg.iterrows():
	r=k['Stevilo pojavitev']
	if len(r)<1:
		continue;
	l=list(map(int, r.split(",")))
	l=np.array(l)
	lp1=np.where(l>np.mean(l)+1)[0]
	lp3=np.where(l>np.mean(l)+3)[0]
	if len(lp1)==1 and len(lp3)==1:
		ix.append(i)
		print(i,lp1, k['Stranke'].split(',')[lp1[0]])

for i,z in dg.iterrows():
	if(len(z['Stranke'].split(','))==1 and len(z['Stranke'])>0):
		ix.append(i)
		print(i,z['Stranke'])

ix.sort()

t=dfnew2.iloc[ix]
g=t[['Max stranka','Sentiment']]