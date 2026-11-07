# Monitoring and Inspection System 
Monitoring and Inspection system will help AFDA overcome this problem: the inspection process is manual and ad hoc, the data is not collected properly, and their is favoritism and corruption in how an food or drug establishment is inspected. 

we have currently the following important establishments:
1. pharmacies
2. wholesalers
3. importers
4. factories

# Architecture
i have the following architecture in my mind:
the monitoring and inspection system will have the following main components: 
- mandi backend: we'll implmenet this backend in django, and it will be the main database of inspection histories and reporting. 
- mandi frontend: this will be the frontend for the mandi backend. 
- mandi data collection: this will be the kobo collect and kobo backend (kpi) which will be used for data collection. this will pull data from the mandi backend, and share the collected data with mandi backend. or maybe mandi backend will pull some data from it. 
- the mandi backend will then fetch more details for each establishment from another three systems: survey systems which has around 20 thousand pharmacies and 3000 wholesalers, archive system which only has registered and completely legal pharmacies and wholesalers, 300 pharmacies, and then licensing system, the new system, which has registered 5 factories and 951 pharmacies, and 214 importers. 


for now we'll be using kobo for data collection, but we might add other data collection tools as well in the future. 

vocabolary: 
Drug Establishment (تأسیسات دوایی): any entity that is involved in the production, importing, distribution and selling of pharmaceutical drugs. 
Food Establishments (تأسیسات غذایی): any entity that is involved with food production, storage, distribution. 
Afda: afghanistan food and drug authority: afghanistans regulatory authority. previously it was independent, but recently it was merged under the afghanistans ministry of Public Health. 
