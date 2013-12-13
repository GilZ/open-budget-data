# -*- coding: utf-8 -*-
import os
import csv
import random
import re
from pyth.plugins.rtf15.reader import Rtf15Reader
from pyth.plugins.plaintext.writer import PlaintextWriter

approvedLine = u'.*?\d+[^%].*?[^(לא)] אושרה.*?'
approved = u' אושרה '
hebrewNo = u' לא '
headerColumns = ['תאריך', 'ישיבה']

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
                if re.match('[1-9]+', committeeId):
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
                # if random.random() < 0.2:
                    parsedName = re.findall(u'\d+', fileName)
                    meetingId, date = str(parsedName.pop()), str('/'.join(parsedName[::-1]))
                    doc = Rtf15Reader.read(rtfFile)
                    for line in PlaintextWriter.write(doc):
                        line = unicode(line, encoding='utf-8')
                        if re.match(approvedLine, line):
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
            with open(os.path.join(csvDir, csvFileName[:-4]+'_out'+csvFileName[-4:]), 'w+') as outputCsv:
                writer = csv.writer(outputCsv)
                reader = csv.reader(csvFile)
                writer.writerow(reader.next() + headerColumns)
                for row in csv.reader(csvFile):
                    committeeId = '' if len(row) < 9 else row[8]
                    # print([] if committeeId not in dictionary[year] else dictionary[year][committeeId])
                    writer.writerow(row + (['', ''] if committeeId not in dictionary[year] else dictionary[year][committeeId]))
