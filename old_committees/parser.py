# -*- coding: utf-8 -*-
import cookielib
import os
import csv
import re
import urllib2
from pyth.plugins.rtf15.reader import Rtf15Reader
from pyth.plugins.plaintext.writer import PlaintextWriter

approvedLine = u'.*?\d+[^%].*?[^(לא)] אושר[הו/.].*?'
hebrewNo = u' לא '
headerColumns = ['תאריך', 'ישיבה']


def parse():
    committeeIds = {}
    for csvDir, _, csvFiles in os.walk('./csv'):
        for csvFileName in csvFiles:
            if not re.match('\w+\d{4}\.csv$', csvFileName):
                continue

            year = csvFileName[7:11]
            committeeIds[year] = set()

            with open(os.path.join(csvDir, csvFileName)) as csvFile:
                for row in csv.reader(csvFile):
                    committeeId = row[8]
                    if row[6] == '2' and committeeId != '0':
                        committeeIds[year].add(committeeId)
    dictionary = {}
    with open('./log.txt', 'w+') as outputFile:
        for rtfDir, _, rtfFiles in os.walk('./rtf'):
            for fileName in rtfFiles:
                if not fileName.endswith('.rtf'):
                    continue

                year = fileName[:4]
                if year not in dictionary:
                    dictionary[year] = {}

                with open(os.path.join(rtfDir, fileName)) as rtfFile:
                    parsedName = re.findall(u'\d+', fileName)
                    date, meetingId = str('/'.join(parsedName[0:3][::-1])), parsedName[-1] if len(parsedName) > 3 else '00'
                    try:
                        doc = Rtf15Reader.read(rtfFile)
                    except Exception:
                        continue

                    for line in PlaintextWriter.write(doc):
                        line = unicode(line, encoding='utf-8')
                        if len(line) < 95 and re.match(approvedLine, line):
                            res = list(set(re.findall(u'\d+', line)) & committeeIds[year])
                            if len(res) > 0:
                                outputFile.write(fileName + ': ' + line.encode('utf-8'))
                                for requestId in res:
                                    dictionary[year][requestId] = [date, meetingId]

    for csvDir, _, csvFiles in os.walk('./csv'):
        for csvFileName in csvFiles:
            if not re.match('\w+\d{4}\.csv$', csvFileName):
                continue

            year = csvFileName[7:11]
            if not year in dictionary:
                continue

            with open(os.path.join(csvDir, csvFileName)) as csvFile:
                with open(os.path.join(csvDir, csvFileName[:-4] + '_out' + csvFileName[-4:]), 'w+') as outputCsv:
                    writer = csv.writer(outputCsv)
                    reader = csv.reader(csvFile)
                    writer.writerow(reader.next() + headerColumns)
                    for row in csv.reader(csvFile):
                        committeeId = '' if len(row) < 9 else row[8]
                        writer.writerow(
                            row + (['', ''] if committeeId not in dictionary[year] else dictionary[year][committeeId]))


def get_protocols_page(page, page_num):
    print('getting page number ' + str(page_num))
    FILES_BASE_URL = "http://www.knesset.gov.il/protocols/"
    res = []
    max_linked_page = max([int(r) for r in re.findall("'Page\$(\d*)",page)])
    last_page = False
    if max_linked_page < page_num:
        last_page = True

    # trim the page to the results part
    start = page.find(r'id="gvProtocol"')
    end = page.find(r'javascript:__doPostBack')
    page = page[start:end]
    date_text = ''
    comittee = ''
    subject = ''
    # find interesting parts
    matches = re.findall(r'<span id="gvProtocol(.*?)</span>|OpenDoc(.*?)\);',page, re.DOTALL)
    for (span,link) in matches:
        if len(span): # we are parsing a matched span - committee info
            if span.find(r'ComName')>0:
                comittee = span[span.find(r'>')+1:]
            if span.find(r'lblDate')>0:
                date_text = span[span.find(r'>')+1:]
            if span.find(r'lblSubject')>0:
                if span.find(r'<Table')>0: # this subject is multiline so they show it a a table
                    subject = ' '.join(re.findall(r'>([^<]*)<',span)) # extract text only from all table elements
                else:
                    subject = span[span.find(r'>')+1:] # no table, just take the text
        else: # we are parsing a matched link - comittee protocol url
            if (link.find(r'html')>0)or(link.find(r'rtf')>0):
                html_url = FILES_BASE_URL + re.search(r"'\.\./([^']*)'", link).group(1)
                res.append([date_text, comittee, subject, html_url]) # this is the last info we need, so add data to results
                date_text = ''
                comittee = ''
                subject = ''
    return (last_page, res)


def get_protocols(max_page=1000):
    SEARCH_URL = "http://www.knesset.gov.il/protocols/heb/protocol_search.aspx"
    cj = cookielib.LWPCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    urllib2.install_opener(opener)

    # get the search page to extract legal "viewstate" and "event validation" strings. need to pass them so the search will work
    page = urllib2.urlopen(SEARCH_URL).read().decode('windows-1255').encode('utf-8')

    event_validation = urllib2.quote(re.search(r'id="__EVENTVALIDATION" value="([^"]*)"', page).group(1)).replace('/','%2F')
    view_state = urllib2.quote(re.search(r'id="__VIEWSTATE" value="([^"]*)"', page).group(1)).replace('/','%2F')
    financeCommitteeId = 2

    # define date range
    params = "__VIEWSTATE=%s&ComId=%d&knesset_id=-1&DtFrom=01%%2F01%%2F2008&DtTo=31%%2F12%%2F2010&__EVENTVALIDATION=%s" % (view_state, financeCommitteeId, event_validation)
    print(params)

    page = urllib2.urlopen(SEARCH_URL,params).read().decode('windows-1255').encode('utf-8')
    event_validation = urllib2.quote(re.search(r'id="__EVENTVALIDATION" value="([^"]*)"', page).group(1)).replace('/','%2F')
    view_state = urllib2.quote(re.search(r'id="__VIEWSTATE" value="([^"]*)"', page).group(1)).replace('/','%2F')

    # hit the search
    params = "btnSearch=%%E7%%E9%%F4%%E5%%F9&__EVENTTARGET=&__EVENTARGUMENT=&__LASTFOCUS=&__VIEWSTATE=%s&ComId=%d&knesset_id=-1&DtFrom=01%%2F01%%2F2008&DtTo=31%%2F12%%2F2010&subj=&__EVENTVALIDATION=%s" % (view_state, financeCommitteeId, event_validation)
    page = urllib2.urlopen(SEARCH_URL,params).read().decode('windows-1255').encode('utf-8')
    event_validation = urllib2.quote(re.search(r'id="__EVENTVALIDATION" value="([^"]*)"', page).group(1)).replace('/','%2F')
    view_state = urllib2.quote(re.search(r'id="__VIEWSTATE" value="([^"]*)"', page).group(1)).replace('/','%2F')
    page_num = 1
    (last_page, page_res) = get_protocols_page(page, page_num)
    res = page_res[:]

    while (not last_page) and (page_num < max_page):
        page_num += 1
        params = "__EVENTTARGET=gvProtocol&__EVENTARGUMENT=Page%%24%d&__LASTFOCUS=&__VIEWSTATE=%s&ComId=%d&knesset_id=-1&DtFrom=01%%2F01%%2F2008&DtTo=31%%2F12%%2F2010&subj=&__EVENTVALIDATION=%s" % (page_num, view_state, financeCommitteeId, event_validation)
        page = urllib2.urlopen(SEARCH_URL,params).read().decode('windows-1255').encode('utf-8')
        # update EV and VS
        event_validation = urllib2.quote(re.search(r'id="__EVENTVALIDATION" value="([^"]*)"', page).group(1)).replace('/','%2F')
        view_state = urllib2.quote(re.search(r'id="__VIEWSTATE" value="([^"]*)"', page).group(1)).replace('/','%2F')
        # parse the page
        (last_page, page_res) = get_protocols_page(page, page_num)
        res.extend(page_res)

    for (date_string, com, topic, link) in res:
        get_committee_protocol_text(link)

def get_committee_protocol_text(url):
    if url.find('html'):
        url = url.replace('html','rtf')

    count = 0
    flag = True
    while count<10 and flag:
        try:
            response = urllib2.urlopen(url).read()
            with open('./rtf/'+url[url.rfind('/')+1:], 'w+') as committeeFile:
                print('got: ' + url)
                committeeFile.write(response)
            flag = False
        except Exception:
            print('exception')
            count += 1

if __name__ == '__main__':
    # get_protocols takes a *long* time with many timeouts in the middle. Be aware, and consider limiting the number of pages
    # get_protocols()
    parse()