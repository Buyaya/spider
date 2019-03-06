import requests
import re
import os
import json
from multiprocessing import Pool
from fontTools.ttLib import TTFont

def get_one_response(url):
    headers = {
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                     '(KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
    }
    response = requests.get(url,headers = headers)
    if response.status_code == 200:
        data = response.content
        return data
    return None

# 下载新字体
def dow_font(data):
    pattern = re.compile(r"url\('(.*?)'\) format\('woff'\)")
    font_url = re.findall(pattern,data)[0]
    font_url = "http:" + font_url
    font_name = font_url.split('/')[-1]
    file_list = os.listdir('./fonts')
    if font_name not in file_list:
        print('不在字体库中,下载...',font_name)
        response = get_one_response(font_url)
        with open('./fonts/' + font_name, 'wb') as f:
            f.write(response)
            f.close()
    newFont = TTFont('./fonts/' + font_name)
    return newFont

# 字体破解
def crk_font(newFont, data):
    baseFont = TTFont('./be72b0e480d2416358ab91e576f7237f2076.woff')
    uniList = newFont['cmap'].tables[0].ttFont.getGlyphOrder()
    numList = []
    baseNumList = ['1','8','0','4','9','7','2','6','3','5',]
    baseUniCode = ['uniF837','uniE187','uniE7B7','uniF300','uniF4BD','uniEEF9','uniE94E','uniE9E2','uniE6C5','uniE649']
    for i in range(1,12):
        newGlyph = newFont['glyf'][uniList[i]]
        for j in range(10):
            baseGlyph = baseFont['glyf'][baseUniCode[j]]
            if newGlyph == baseGlyph:
                numList.append(baseNumList[j])
                break
    rowList = []
    for i in uniList[2:]:
        i = i.replace('uni','&#x').lower() + ';'
        rowList.append(i)

    dictory = dict(zip(rowList,numList))

    for key in dictory:
        if key in data:
            data = data.replace(key,str(dictory[key]))
    return data

def parse_one_data(data):
    pattern = re.compile('<dd>.*?board-index.*?>(\d+)</i>.*?title="(.*?)".*?data-src="(.*?)"'
                         '.*?class="star">(.*?)</p>.*?class="releasetime">(.*?)</p>.*?class="stonefont">'
                         '(.*?)</span>.*?class="stonefont">(.*?)</span>.*?</dd>',re.S)

    items = re.findall(pattern,data)

    for item in items:
        yield {
            '排名:': item[0],
            '电影名:': item[1],
            '封面:': item[2],
            '主演:': item[3].strip()[3:],
            '上映时间:': item[4].strip()[5:],
            '本月新增想看:': item[5],
            '总想看:': item[6]
        }

def write_to_file(content):
    with open('result.txt','a',encoding="utf-8") as f:
        f.write(json.dumps(content,ensure_ascii=False) + '\n')
        f.close()

def main(offset):
    url = 'https://maoyan.com/board/6?offset=' + str(offset)
    data = get_one_response(url).decode('utf-8')
    newFont = dow_font(data)
    data = crk_font(newFont,data)
    for item in parse_one_data(data):
        print(item)
        write_to_file(item)

if __name__ == '__main__':
    for i in range(5):
        main(i * 10)
