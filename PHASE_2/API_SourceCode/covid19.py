import pandas as pd
import json
import datetime
import urllib
import requests
import re
from bs4 import BeautifulSoup   # to scrape data from html requests
from datetime import timedelta, datetime
from collections import OrderedDict
from operator import *

from countries import countries
from countryISO import *

from pytrends.request import TrendReq

# match covid-19 countries with country Code
def identify_country(country):
    switcher = {
        "Diamond Princess": "Cruise Ship",
        "Cote d'Ivoire": "Ivory Coast",
        "Holy See": "Holy See",
        "Korea, South": "South Korea",
        "Kosovo": "",
        "Taiwan*": "Taiwan",
        "West Bank and Gaza": "",
    }

    return switcher.get(country, country)

# main covid-19 data
def generate_data():
    GIT = 'https://raw.githubusercontent.com/'
    PATH = 'CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports/'
    TODAY = datetime.now()
    FILENAME = '{:02d}-{:02d}-{}.csv'.format(TODAY.month, TODAY.day, TODAY.year)
    URL = '{}{}{}'.format(GIT, PATH, FILENAME)

    r = requests.get(URL)
    while not r.ok:
        TODAY = TODAY - timedelta(days=1)
        FILENAME = '{:02d}-{:02d}-{}.csv'.format(TODAY.month, TODAY.day, TODAY.year)
        URL = '{}{}{}'.format(GIT, PATH, FILENAME)
        r = requests.get(URL)

    df = pd.read_csv(URL, error_bad_lines=False)

    dataset = {}
    total = {}
    total['Confirmed'] = 0
    total['Deaths'] = 0
    total['Recovered'] = 0
    for index, row in df.iterrows():
        convert_country = identify_country(row['Country_Region'])
        convert_country = re.sub('\,', '', convert_country)
        convert_country = re.sub('\"', '', convert_country)
        data = dataset.get(convert_country, False)
        if not data:
            data = {}
            data['Code'] = ISO_3_to_2(countries.get(convert_country, ""))

            data['Confirmed'] = row['Confirmed']
            data['Deaths'] = row['Deaths']
            data['Recovered'] = row['Recovered']
            data['Active'] = row['Active']
            dataset[convert_country] = data
        else:
            dataset[convert_country]['Confirmed'] += row['Confirmed']
            dataset[convert_country]['Deaths'] += row['Deaths']
            dataset[convert_country]['Recovered'] += row['Recovered']
            dataset[convert_country]['Active'] += row['Active']

    return OrderedDict(sorted(dataset.items(), reverse=True, key=lambda x: getitem(x[1], 'Confirmed')))

# get 10 worst covid-19 affected area
def head_generate_data():
    dataset = generate_data()
    while len(dataset) > 10:
        dataset.popitem()
    return dataset

# get covid-19
def generate_total():
    GIT = 'https://raw.githubusercontent.com/'
    PATH = 'CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports/'
    TODAY = datetime.now()
    FILENAME = '{:02d}-{:02d}-{}.csv'.format(TODAY.month, TODAY.day, TODAY.year)
    URL = '{}{}{}'.format(GIT, PATH, FILENAME)
    r = requests.get(URL)
    while not r.ok:
        TODAY = TODAY - timedelta(days=1)
        FILENAME = '{:02d}-{:02d}-{}.csv'.format(TODAY.month, TODAY.day, TODAY.year)
        URL = '{}{}{}'.format(GIT, PATH, FILENAME)
        r = requests.get(URL)

    df = pd.read_csv(URL, error_bad_lines=False)

    total = {}
    total['Confirmed'], total['Deaths'], total['Recovered'], total['Active'] = 0, 0, 0, 0
    for index, row in df.iterrows():
        total['Confirmed'] += row['Confirmed']
        total['Deaths'] += row['Deaths']
        total['Recovered'] += row['Recovered']
        total['Active'] += row['Active']

    return total

# validate date
def validate_date(d):
    try:
        date = datetime.strptime(d, "%Y-%m-%d")
        if date > datetime.now():
            return False;
        return True
    except ValueError:
        return False

def json_to_string(s):
    ret = str(s)
    ret = re.sub('\'', '\"', ret)
    return ret

# Formats NSW covid19 count in json (make compatible with geoJSON)
# Formats 50 latest confirmed cases in NSW
def nsw_positive_cases():
    resource_id = '2776dbb8-f807-4fb2-b1ed-184a6fc2c8aa'; # Location and source
    get_limit = requests.get('https://data.nsw.gov.au/data/api/3/action/datastore_search?resource_id={}&limit=20'.format(resource_id))
    limit = get_limit.json()['result']['total']
    r = requests.get('https://data.nsw.gov.au/data/api/3/action/datastore_search?resource_id={}&limit={}'.format(resource_id, limit))
    dataset = {}
    records = r.json()['result']['records']
    for i in records:
        nsw_lga__3 = re.sub('\(A\)|\(C\)|\(NSW\)', '', i['lga_name19']).strip().lower()
        data = dataset.get(nsw_lga__3, False)
        if not data:
            tmp = {}
            tmp['count'] = 1
            tmp['date'] = i['notification_date']
            dataset[nsw_lga__3] = tmp
        else:
            dataset[nsw_lga__3]['count'] += 1
            dataset[nsw_lga__3]['latest_confirmed'] = i['notification_date']

    latest_cases = requests.get('https://data.nsw.gov.au/data/api/3/action/datastore_search?resource_id={}&limit={}&offset={}'.format(resource_id, limit, limit-50))
    dataset_2 = {}
    data = []
    records = latest_cases.json()['result']['records']
    for i in records:
        nsw_lga__3 = re.sub('\(A\)|\(C\)|\(NSW\)', '', i['lga_name19']).strip().lower()
        tmp = {}
        tmp['nsw_lga__3'] = nsw_lga__3 if nsw_lga__3 != "" else "unknown"
        tmp['postcode'] = i['postcode'] if not i['postcode'] is None else "unknown"
        tmp['notification_date'] = i['notification_date']
        tmp['likely_source_of_infection'] = i['likely_source_of_infection']
        data.append(tmp);
    dataset_2['records'] = data
    return dataset, dataset_2

# Formats WA covid19 count in json (make compatible with geoJSON)
def wa_positive_cases():
    cases = requests.get('https://interactive.guim.co.uk/covidfeeds/wa.json'.format())
    json = {}
    for i in cases.json():
        tmp = {}
        tmp['count'] = i['count']
        tmp['date'] = i['date']
        json[re.sub('\([ACTS]\)', '', i['place']).strip().lower()] = tmp
    return json

# Formats VIC covid19 count in json (make compatible with geoJSON)
def vic_positive_cases():
    cases = requests.get('https://interactive.guim.co.uk/covidfeeds/victoria.json'.format())
    json = {}
    for i in cases.json():
        tmp = {}
        tmp['count'] = i['count']
        tmp['date'] = i['date']
        json[re.sub('\([ACTSB]\)|\(RC\)', '', i['place']).strip().lower()] = tmp
    return json

# Formats QLD covid19 count in json (make compatible with geoJSON)
def qld_positive_cases():
    cases = requests.get('https://interactive.guim.co.uk/covidfeeds/queensland.json'.format())
    json = {}
    for i in cases.json():
        tmp = {}
        tmp['count'] = i['count']
        tmp['date'] = i['date']
        json[re.sub('\([ACTSB]\)|\(RC\)', '', i['place']).strip().lower()] = tmp
    return json

# get times_series of Australian states
def au_time_series():
    cases = requests.get('https://interactive.guim.co.uk/docsdata/1q5gdePANXci8enuiS4oHUJxcxC13d6bjMRSicakychE.json'.format())
    json = {}
    json['ACT'] = []
    json['NSW'] = []
    json['VIC'] = []
    json['TAS'] = []
    json['WA'] = []
    json['SA'] = []
    json['QLD'] = []
    records = cases.json()['sheets']['updates']
    for record in records:
        tmp = {}
        tmp['date'] = record['Date']
        tmp['cases'] = 0 if record['Cumulative case count'] == '' else int(record['Cumulative case count'])
        tmp['deaths'] = 0 if record['Cumulative deaths'] == '' else int(record['Cumulative deaths'])
        tmp['recovered'] = 0 if record['Recovered (cumulative)'] == '' else int(record['Recovered (cumulative)'])
        tmp['tests'] = 0 if record['Tests conducted (total)'] == '' else int(record['Tests conducted (total)'])
        tmp['hospitalised'] = 0 if record['Hospitalisations (count)'] == '' else int(record['Hospitalisations (count)'])
        print(record['State'])
    return json

# get latest totals of australian covid-19
def australia_latest():
    cases = requests.get('https://interactive.guim.co.uk/docsdata/1q5gdePANXci8enuiS4oHUJxcxC13d6bjMRSicakychE.json'.format())
    records = cases.json()['sheets']['latest totals']
    main = {}
    states = {}
    for record in records:
        if(record['State or territory'] != 'National'):
            tmp = {}
            tmp['cases'] = 0 if record['Confirmed cases (cumulative)'] == '' else int(record['Confirmed cases (cumulative)'])
            tmp['deaths'] = 0 if record['Deaths'] == '' else int(record['Deaths'])
            tmp['recovered'] = 0 if record['Recovered'] == '' else int(record['Recovered'])
            tmp['tests'] = 0 if record['Tests conducted'] == '' else int(record['Tests conducted'])
            tmp['hospitalised'] = 0 if record['Current hospitalisation'] == '' else int(record['Current hospitalisation'])
            states[record['State or territory']] = tmp
        else:
            main['last_updated'] = record['Last updated']
    main['states'] = states

    latest_deaths = cases.json()['sheets']['deaths']
    arr = []
    for death in latest_deaths:
        arr.append({
            'state': death['State'],
            'date': death['Date of death'],
            'details': death['Details'],
            'source': death['Source']
        });
    main['deaths'] = arr

    sites = {}
    sources = cases.json()['sheets']['sources']
    for source in sources:
        sites[source['state']] = source['daily update']

    return main, sites

# Get details for helping stop coronavirus
advices = [
    {'icon': 'fa-hands-wash', 'tip': 'Wash your hands often'},
    {'icon': 'fa-people-arrows', 'tip': 'Practise social distancing'},
    {'icon': 'fa-handshake-slash', 'tip': 'Avoid touching your faces and others'},
    {'icon': 'fa-virus', 'tip': 'Wear mask to limit exposure when going outside'},
    {'icon': 'fa-stethoscope', 'tip': 'If you have sick, stay home and call your doctor'},
    {'icon': 'fa-user-slash', 'tip': 'Be sure to follow your country\\\'s social gathering limit'},
]
def generateSafetyAdvices():
    json = {}
    json['advices'] = advices
    json['length'] = len(advices)
    return json

# Using another team's API to obtain more articles
def getNewArticles(start, end):
    # TODAY = datetime.now()
    # LASTWEEK = TODAY - timedelta(days=7)
    # URL = "https://teletubbies-who-api.herokuapp.com/article"
    # URL = "https://api.todo.cf/v1/article"
    URL = "http://api.sixtyhww.com:3000/search"

    # PARAMS = {
    #     "teamName": "API-demic",
    #     "startDate": start,
    #     "endDate": end,
    #     "key": "coronavirus",
    #     "pageSize": "20"
    # }

    BODY = {
        "start_date": start,
        "end_date": end,
        "keyTerms": "coronavirus",
        # "pagination": "0-10"
    }
    # r = requests.get(url = URL, params = PARAMS)
    r = requests.post(url = URL, json=BODY)

    json = {}
    json['articles'] = []
    print(r.url)
    print(r.json())
    if(r.status_code == 400):
        return json
    for article in r.json():
        tmp = {}
        tmp['url'] = article['url']
        tmp['date_of_publication'] = article['date_of_publication']
        tmp['headline'] = article['headline']
        # tmp['main_text'] = article['main_text']
        # tmp['reports'] = article['reports']
        json['articles'].append(tmp)

    return json

# Using another team's API to obtain more articles
def getOurNewArticles(start, end):
   URL = "http://api-demic.herokuapp.com/v1.1/articles"
   PARAMS = {
       "start_date": start,
       "end_date": end,
       "key_term": "coronavirus",
       "limit": "100"
   }
   r = requests.get(url = URL, params = PARAMS)

   json = {}
   json['articles'] = []
   if(r.status_code == 400):
       return json
   articles = r.json()['articles']
   for article in reversed(articles):
       tmp = {}
       tmp['url'] = article['url']
       tmp['date_of_publication'] = article['date_of_publication']
       tmp['headline'] = article['headline']
       tmp['main_text'] = article['main_text']
       # tmp['reports'] = article['reports']
       json['articles'].append(tmp)

   return json

def get_trending_searches():
    list = []
    pytrends = TrendReq(hl='en-US', tz=360)
    pytrends.build_payload(kw_list=['coronavirus'])
    related_queries = pytrends.related_queries()

    for i in related_queries.values():
        df =  i['top']
        for index, row in df.iterrows():
            # print(row['query'])
            list.append(row['query'])

    return list
