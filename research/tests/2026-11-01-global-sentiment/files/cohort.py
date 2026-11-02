"""Historical PwC top 100, 31 March 2018. Rank/country frozen before test.
Aliases map recognized GKG organizations; no substring matching. Prices use listed
share classes (sometimes ADRs), not an investable reconstruction of the PwC index.
"""
import unicodedata,re
# rank | company | ticker | country | region | aliases separated by semicolons
RAW='''1|Apple|AAPL|US|North America|apple;apple inc;apple computer
2|Alphabet|GOOGL|US|North America|alphabet;alphabet inc;google;google inc;google llc
3|Microsoft|MSFT|US|North America|microsoft;microsoft corp;microsoft corporation
4|Amazon|AMZN|US|North America|amazon;amazon com;amazon com inc;amazon web services
5|Tencent|0700.HK|CN|Asia|tencent;tencent holdings;tencent holdings ltd
6|Berkshire Hathaway|BRK-B|US|North America|berkshire hathaway;berkshire hathaway inc
7|Alibaba|BABA|CN|Asia|alibaba;alibaba group;alibaba group holding
8|Facebook/Meta|META|US|North America|facebook;facebook inc;meta platforms;meta platforms inc
9|JPMorgan Chase|JPM|US|North America|jpmorgan;jp morgan;jpmorgan chase;jpmorgan chase co;jpmorgan chase company
10|Johnson & Johnson|JNJ|US|North America|johnson johnson;johnson johnson inc
11|ICBC|1398.HK|CN|Asia|icbc;industrial commercial bank of china;industrial and commercial bank of china
12|Exxon Mobil|XOM|US|North America|exxon;exxonmobil;exxon mobil;exxon mobil corp
13|Bank of America|BAC|US|North America|bank of america;bank of america corp;bank of america corporation
14|Samsung Electronics|005930.KS|KR|Asia|samsung;samsung electronics;samsung electronics co
15|Royal Dutch Shell|SHEL.L|GB|Europe|shell;royal dutch shell;shell plc;shell oil
16|Walmart|WMT|US|North America|walmart;wal mart;wal mart stores;walmart inc
17|China Construction Bank|0939.HK|CN|Asia|china construction bank;china construction bank corp
18|Wells Fargo|WFC|US|North America|wells fargo;wells fargo co;wells fargo company
19|Nestle|NESN.SW|CH|Europe|nestle;nestle sa
20|Visa|V|US|North America|visa;visa inc
21|Intel|INTC|US|North America|intel;intel corp;intel corporation
22|Anheuser-Busch InBev|ABI.BR|BE|Europe|anheuser busch inbev;ab inbev;anheuser busch inbev sa
23|Taiwan Semiconductor|2330.TW|TW|Asia|tsmc;taiwan semiconductor;taiwan semiconductor manufacturing;taiwan semiconductor manufacturing co
24|AT&T|T|US|North America|at t;at t inc
25|Chevron|CVX|US|North America|chevron;chevron corp;chevron corporation
26|PetroChina|0857.HK|CN|Asia|petrochina;petrochina co;petrochina company
27|Novartis|NOVN.SW|CH|Europe|novartis;novartis ag
28|Pfizer|PFE|US|North America|pfizer;pfizer inc
29|Toyota|7203.T|JP|Asia|toyota;toyota motor;toyota motor corp;toyota motor corporation
30|UnitedHealth Group|UNH|US|North America|unitedhealth;unitedhealth group;unitedhealthcare
31|Cisco Systems|CSCO|US|North America|cisco;cisco systems;cisco systems inc
32|Home Depot|HD|US|North America|home depot;home depot inc
33|Agricultural Bank of China|1288.HK|CN|Asia|agricultural bank of china;agricultural bank of china ltd
34|Procter & Gamble|PG|US|North America|procter gamble;procter gamble co;procter gamble company
35|Roche|ROP.SW|CH|Europe|roche;roche holding;roche holding ag;hoffmann la roche
36|Verizon Communications|VZ|US|North America|verizon;verizon communications;verizon communications inc
37|Boeing|BA|US|North America|boeing;boeing co;boeing company
38|Ping An Insurance|2318.HK|CN|Asia|ping an;ping an insurance;ping an insurance group
39|China Mobile|0941.HK|HK|Asia|china mobile;china mobile ltd
40|HSBC|HSBA.L|GB|Europe|hsbc;hsbc holdings;hsbc holdings plc
41|Oracle|ORCL|US|North America|oracle;oracle corp;oracle corporation
42|Coca-Cola|KO|US|North America|coca cola;coca cola co;coca cola company
43|Mastercard|MA|US|North America|mastercard;mastercard inc
44|Bank of China|3988.HK|CN|Asia|bank of china;bank of china ltd
45|Citigroup|C|US|North America|citigroup;citigroup inc;citibank
46|Unilever|UNA.AS|NL|Europe|unilever;unilever nv;unilever plc
48|LVMH|MC.PA|FR|Europe|lvmh;lvmh moet hennessy louis vuitton;moet hennessy louis vuitton
47|Comcast|CMCSA|US|North America|comcast;comcast corp;comcast corporation
49|PepsiCo|PEP|US|North America|pepsico;pepsico inc;pepsi cola
50|Philip Morris International|PM|US|North America|philip morris;philip morris international;philip morris international inc
51|Walt Disney|DIS|US|North America|disney;walt disney;walt disney co;walt disney company
52|AbbVie|ABBV|US|North America|abbvie;abbvie inc
53|Total|TTE.PA|FR|Europe|total sa;total energies;totalenergies;totalenergies se
54|DowDuPont|DD|US|North America|dowdupont;dow dupont;dowdupont inc
55|Merck & Co|MRK|US|North America|merck co;merck company;merck co inc;merck sharp dohme
56|IBM|IBM|US|North America|ibm;international business machines;international business machines corp
57|NVIDIA|NVDA|US|North America|nvidia;nvidia corp;nvidia corporation
58|Kweichow Moutai|600519.SS|CN|Asia|kweichow moutai;kweichow moutai co;moutai
59|BP|BP.L|GB|Europe|bp;bp plc;british petroleum
60|British American Tobacco|BATS.L|GB|Europe|british american tobacco;british american tobacco plc
61|3M|MMM|US|North America|3m;3m co;3m company
62|SAP|SAP.DE|DE|Europe|sap;sap se;sap ag
63|Netflix|NFLX|US|North America|netflix;netflix inc
64|L'Oreal|OR.PA|FR|Europe|l oreal;loreal;l oreal sa
65|McDonalds|MCD|US|North America|mcdonald;mcdonalds;mcdonald s;mcdonald corporation;mcdonald s corp
66|Novo Nordisk|NOVO-B.CO|DK|Europe|novo nordisk;novo nordisk a s
67|Amgen|AMGN|US|North America|amgen;amgen inc
68|Sinopec|0386.HK|CN|Asia|sinopec;china petroleum chemical;china petroleum chemical corp
69|Altria|MO|US|North America|altria;altria group;altria group inc
70|General Electric|GE|US|North America|general electric;general electric co;general electric company;ge aerospace
71|AmBev|ABEV3.SA|BR|Latin America|ambev;ambev sa;companhia de bebidas das americas
72|China Merchants Bank|3968.HK|CN|Asia|china merchants bank;china merchants bank co
73|Royal Bank of Canada|RY.TO|CA|North America|royal bank of canada;rbc;royal bank canada
74|BHP Billiton|BHP.AX|AU|Oceania|bhp;bhp billiton;bhp group;bhp group ltd
75|Medtronic|MDT|IE|Europe|medtronic;medtronic plc;medtronic inc
76|Siemens|SIE.DE|DE|Europe|siemens;siemens ag
77|Honeywell|HON|US|North America|honeywell;honeywell international;honeywell international inc
78|Nike|NKE|US|North America|nike;nike inc
79|Naspers|NPN.JO|ZA|Africa|naspers;naspers ltd
80|Adobe|ADBE|US|North America|adobe;adobe systems;adobe inc
81|China Life Insurance|2628.HK|CN|Asia|china life;china life insurance;china life insurance co
82|Santander|SAN.MC|ES|Europe|santander;banco santander;santander group
83|Abbott Laboratories|ABT|US|North America|abbott laboratories;abbott labs
84|Toronto-Dominion Bank|TD.TO|CA|North America|toronto dominion bank;td bank;td bank group
85|Union Pacific|UNP|US|North America|union pacific;union pacific corp;union pacific corporation
86|Bristol-Myers Squibb|BMY|US|North America|bristol myers squibb;bristol myers squibb co
87|Accenture|ACN|IE|Europe|accenture;accenture plc
88|AIA Group|1299.HK|HK|Asia|aia group;aia group ltd
89|Texas Instruments|TXN|US|North America|texas instruments;texas instruments inc
90|Sanofi|SAN.PA|FR|Europe|sanofi;sanofi sa;sanofi aventis
91|United Technologies|RTX|US|North America|united technologies;united technologies corp;united technologies corporation
92|Booking Holdings|BKNG|US|North America|booking holdings;booking holdings inc;priceline;priceline group
93|Volkswagen|VOW3.DE|DE|Europe|volkswagen;volkswagen ag;vw
94|Allianz|ALV.DE|DE|Europe|allianz;allianz se
95|Goldman Sachs|GS|US|North America|goldman sachs;goldman sachs group;goldman sachs group inc
96|Gilead Sciences|GILD|US|North America|gilead;gilead sciences;gilead sciences inc
97|Commonwealth Bank|CBA.AX|AU|Oceania|commonwealth bank;commonwealth bank of australia
98|Inditex|ITX.MC|ES|Europe|inditex;industria de diseno textil;zara
99|GlaxoSmithKline|GSK.L|GB|Europe|glaxosmithkline;glaxo smith kline;gsk;gsk plc
100|Broadcom|AVGO|US|North America|broadcom;broadcom inc;broadcom ltd'''
def norm(s):
 s=unicodedata.normalize('NFKD',s.lower());s=''.join(c for c in s if not unicodedata.combining(c))
 return re.sub(r'[^a-z0-9]+',' ',s).strip()
COHORT=[];ALIASES={}
for line in RAW.splitlines():
 rank,name,ticker,country,region,aliases=line.split('|')
 d=dict(rank=int(rank),company=name,ticker=ticker,country=country,region=region,aliases=aliases)
 # No unverified predecessor/successor portfolio reconstruction.
 d['end_date']='2019-05-31' if int(rank)==54 else '2020-04-02' if int(rank)==91 else None
 COHORT.append(d)
 for alias in aliases.split(';'):
  a=norm(alias)
  assert a not in ALIASES or ALIASES[a]==int(rank),a
  ALIASES[a]=int(rank)
assert len(COHORT)==100
