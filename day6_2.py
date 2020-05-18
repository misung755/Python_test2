# 이미지 파일 다운로드 받아서 검색하기 + DB + 세션(로그인)
from flask import Flask, render_template, request, session, redirect
from konlpy.tag import Kkma
import requests
import re
from bs4 import BeautifulSoup
import os
import pymysql
from datetime import date, datetime, timedelta

app = Flask(__name__, template_folder='templates')
app.env = 'development'
app.debug = True
app.secret_key = 'misung' # 아무 문자열해도 됨
kkma = Kkma()

db = pymysql.connect(
    user='root',
    passwd='12345678',
    host='localhost',
    db='web',
    charset='utf8',
    cursorclass=pymysql.cursors.DictCursor
)

def get_menu():
    cursor = db.cursor()
    cursor.execute("select id, title from topic order by title desc")
    return cursor.fetchall()

@app.route('/')
def index():
    return render_template('index2.html', 
                            menu=get_menu(),
                            user=session.get('user'))

@app.route('/<cid>')
def content(cid):
    cursor = db.cursor()
    cursor.execute(f"""
        select id, title, description, created, author_id from topic
        where id = '{ cid }'
    """)
    content = cursor.fetchone()
    return render_template('template.html', 
                            menu=get_menu(),
                            content=content)

@app.route('/login', methods=['get', 'post'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    cursor = db.cursor()
    cursor.execute(f"""
        select id, name, profile from author
        where name = '{ request.form['userid'] }' and
              password = SHA2('{ request.form['password'] }', 256)
    """)
    user = cursor.fetchone()
    if user:
        session['user'] = user
        return redirect('/')
    else:
        return render_template('login.html', msg="로그인 정보를 확인하세요")

@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/')

@app.route('/download/<keyword>', methods=['get', 'post'])
def download(keyword):
    if request.method == 'GET':
        return render_template('download.html', keyword=keyword)

    url = 'https://search.naver.com/search.naver'
    query = dict(where='image', sm='tab_jum', query=keyword)

    res = requests.get(url, params=query)
    soup = BeautifulSoup(res.content, 'html.parser')
    img_links = [tag.get('data-source') 
                 for tag in soup.select('img._img')]

    # 디렉토리 생성 
    os.makedirs(f'static/download/{keyword}', exist_ok=True)

    # 이미지 다운로드
    for i, link in enumerate(img_links):
        res = requests.get(link)
        with open(f'static/download/{keyword}/{i}.jpg', 'wb') as f:
            f.write(res.content)

    return render_template('download.html', 
        keyword=keyword, img_links=img_links)

@app.route('/news/ranking', methods=['get', 'post'])
def news():
    if request.method == "GET":
        return render_template("news.html")

    def get_news(news_date =''):
        url = 'https://media.daum.net/ranking/'
        query = {'regDate':news_date} 
        res = requests.get(url, params=query)
        #https://media.daum.net/ranking/?regDate=20200518
    
        soup =  BeautifulSoup(res.content, 'html.parser')
    
        extracts = [dict(
            title = re.sub('\s+', ' ', a.get_text().replace('\n', '')),
            link = a['href']
        ) for a in soup.select('a.link_txt')]
        return extracts

    news_date = request.form.get('news_date')
    print(news_date)
    extracts = get_news(news_date)


    return render_template("news.html", soup = extracts)

@app.route('/news/words')
def words():
    words = []

    news_url = request.args.get('url')
    res = requests.get(news_url)
    soup = BeautifulSoup(res.content, 'html.parser')
    soup = soup.select('p')

    words = [s.get_text() for s in soup]
    words = ' '.join(words).strip()

    words = kkma.pos(words) # nouns는 중복 제거
    words = [w for w in words if w[1] in ['NNG', 'NNP']]

    words = [(w, words.count(w)) for w in set(words)]
    
    # 정렬하기(정렬하려면 리스트형식만 가능)
    words = sorted(words, key = lambda x: x[1], reverse=True)

    return render_template("word_count.html", soup = words)

app.run()