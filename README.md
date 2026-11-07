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



kobo toolbox will get the establishment names from the mandi backend, and then most of the inspection data will stay in the kobo toolbox, we will only pull the summary or results of the data, whatever is most important, to the mandi backend. mandi backend will have the list of establishments. 



for now we'll be using kobo for data collection, but we might add other data collection tools as well in the future. 

vocabolary: 
Drug Establishment (تأسیسات دوایی): any entity that is involved in the production, importing, distribution and selling of pharmaceutical drugs. 
Food Establishments (تأسیسات غذایی): any entity that is involved with food production, storage, distribution. 
Afda: afghanistan food and drug authority: afghanistans regulatory authority. previously it was independent, but recently it was merged under the afghanistans ministry of Public Health. 

in afghanistan government agencies their is a specific organization structure: 

1. Executive Leadership Level

• Wazir (وزیر - Minister): The absolute political and administrative head of the entire Ministry.
• Muyeeniat (معینیت - Deputy Ministry): This is the office of a Muyeen (معین), which translates to Deputy Minister. A single ministry usually has several Muyeeniat offices divided by portfolio (e.g., Muyeeniat-e-Maleyee for Finance/Administration, Muyeeniat-e-Tadreesee for Academic Affairs). This corresponds to Grade Extra (بست فوق العاده) or Grade 1 (بست یک) in senior executive rankings.

2. General Directorate Level

• Riyasat-e-Umoomi (ریاست عمومی - General Directorate): Beneath the Deputy Minister sit the massive umbrella departments.
• Rais-e-Umoomi (رئیس عمومی - Director General): The individual heading a General Directorate. They manage multiple smaller directorates and report directly to the Muyeen. This typically ranks as Grade 1 (بست یک) or Grade 2 (بست دو).

3. Directorate Level

• Riyasat (ریاست - Directorate / Department): The standard operational unit of a ministry handling a specific function (e.g., Directorate of Human Resources, Directorate of Information Technology).
• Rais (رئیس - Director): The head of a specific department. The Rais ensures that the strategies outlined by the executive leadership are executed. This role sits firmly at Grade 2 (بست دو).

4. Sub-Directorate & Management Level

• Ameryat (آمریت - Sub-Directorate / Sub-Department): Directorates are broken down into smaller specialized units called Ameryat.
• Amer (آمر - Manager / Head of Section): The person in charge of an Ameryat. They manage specialized technical teams and correspond to Grade 3 (بست سه).
• Mudiryat (مدیریت - Directorate Office / Unit): The baseline unit for specific daily administrative, operational, or logistical tasks.
• Mudir (مدیر - Director / Supervisor / Officer): The supervisor or desk officer in charge of a Mudiryat. The Mudir oversees frontline personnel, processes applications, manages archives, or executes specific procedural work. This spans Grade 4 (بست چهار) down to Grade 6 (بست شش) depending on the scale and location of the office.


## Questions and answers

### 1. When the same establishment appears in the survey, archive, and licensing systems, how should Mandi identify it as the same establishment? If their details disagree, which source should it trust?

the mandi doesn't have to automatically map an establishment with other systems, it will be manually done by an employee. the mandi will show their details as it is in those systems. for example for a pharmacy, the mandi will have its name, and then a section for "details from survey system", "details from licensing system", "details from archive system" when they are connected. if not mapped, the mandi frontend will show an option, let's say "connect this pharmacy with archive system", and then he'll get a list of pharmacies from archive system, search it and select a pharmacy in archive system that represents it. and so on

### 2. What is the inspection process, from deciding which establishment to inspect through reviewing the findings and following up?

the director will give target that each establishment has to be thoroughly inspected how many times per year. also, sometimes he might order his employee to inspect an establishment due to a report of mis-behavior. later, we might add auto suggestion for inspection, planning inspection teams, but initially it will be manually, and they will use the reports of current inspections.

### 3. How should Mandi help prevent favoritism and corruption? Who assigns inspectors, who reviews their findings, and who can change submitted inspections?

currently there is a problem that employees doesn't properly inspect, fill the inspection forms not in the establishment and bring it to office and fill it, doesn't go for inspection and lie, doesn't bring any evidence and the director has to trust them. initially i don't want to digitalize everything for them. i just want to give them the tools which they can use to fill the checklist digitally, convert the checklists to kobo forms. later, gradually we'll add more digitalization. right now, i'm only thinking of one step so someone has to approve the data entry.

### 4. What should move between Mandi and KoBo, and in which direction? Do inspectors need to collect data offline?

the mandi will provide the list of establisihment, so i can map form entries back to mandi establishments, and kobo will provide the form results.

### 5. What must the first release include? Will it cover only drug establishments, or food establishments too?

the initial release focuses on digitalizig the checklists and checklist results, knowing which establishments have been inspected, by whom, which hasn't been.

### 6. What counts as “inspected”: a submitted checklist or an approved one?

both. we'll differentiate which are approved and which not.&#x20;

### 7. Who approves entries, and what happens when they reject one?

nothing special, i'll decide them later.&#x20;

### 8. Which results must Mandi retain to report inspection coverage and findings?

the mandi will decide which data it needs from the kobo

### 9. How will each KoBo submission reliably carry the Mandi establishment ID?

the kobo will pull or preload the list of each establishment based on form, like one form question, user will search and select.


## Local review build

The first implementation milestone is ready for local review: Django/PostgreSQL backend with business logic in services, and a React frontend adapted from the AFDA CMS setup. It includes establishment records and manual source links, inspection summaries and approval, inspection coverage, employee creation, a core geography app, and checklist XLSForm uploads. Live integrations and actual checklist conversion follow review.

- [Run and review the system](docs/development.md)
- [Implementation plan](docs/implementation-plan.md)
- [Requirement review and drift corrections](docs/implementation-review.md)
- [Checklist findings](docs/checklist-review-findings.txt)
