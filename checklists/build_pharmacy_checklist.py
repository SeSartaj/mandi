"""Build the pharmacy (hospital pharmacy) inspection XLSForm.

Source: "چک لست ملی بازرسی دواخانه های شفاخانه ها – سال ۱۴۰۵" (AFDA / MoPH).

Run with the project virtualenv:

    .venv/bin/python checklists/build_pharmacy_checklist.py

The workbook is written next to this script as
`pharmacy_inspection_checklist_1405.xlsx` and can be uploaded to Mandi
(Checklists -> Add checklist -> Deploy).
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

OUTPUT = Path(__file__).with_name("pharmacy_inspection_checklist_1405.xlsx")

SURVEY_HEADERS = [
    "type",
    "name",
    "label::Dari (fa)",
    "label::English (en)",
    "hint::Dari (fa)",
    "hint::English (en)",
    "required",
    "appearance",
    "relevant",
    "calculation",
]

CHOICE_HEADERS = ["list_name", "name", "label::Dari (fa)", "label::English (en)"]

SETTINGS = [
    ["form_title", "form_id", "version", "default_language", "mandi_establishment_filter"],
    [
        "چک لست ملی بازرسی دواخانه های شفاخانه ها ۱۴۰۵",
        "pharmacy_inspection_1405",
        "2026110801",
        "Dari (fa)",
        "kind = 'pharmacy'",
    ],
]

CHOICES = [
    # Assessment list: 1 = met, 0 = not met, 2 = not observed (تطبیق نشد)
    ["yn", "1", "۱ – تکمیل / مطابق", "1 - Met"],
    ["yn", "0", "۰ – نخیر / عدم مطابقت", "0 - Not met"],
    ["yn", "2", "تطبیق نشد", "Not observed"],
    ["yes_no", "yes", "بلی", "Yes"],
    ["yes_no", "no", "نخیر", "No"],
    ["grade", "1", "درجه اول", "First grade"],
    ["grade", "2", "درجه دو", "Second grade"],
    ["grade", "3", "درجه سه", "Third grade"],
    ["grade", "9", "سایر", "Other"],
    [
        "inspection_type",
        "initial",
        "اولیه / جامع",
        "Initial / comprehensive",
    ],
    ["inspection_type", "brief", "مختصر یا کوتاه", "Brief"],
    ["inspection_type", "followup", "تعقیبی", "Follow-up"],
    ["inspection_type", "special", "ویژه", "Special"],
    ["freq", "regular", "مکرر", "Regularly"],
    ["freq", "irregular", "بطور نامنظم", "Irregularly"],
    ["freq", "none", "هیچ ثبت نمیشود", "Never recorded"],
]

# ---------------------------------------------------------------------------
# Survey definition
# ---------------------------------------------------------------------------
# Each scored requirement is a select_one yn question named q<index>.
# Sections 2-8 are scored exactly like the paper checklist.
# ---------------------------------------------------------------------------

SECTIONS = [
    {
        "title_fa": "۲. جواز فعالیت",
        "title_en": "2. Licence to operate",
        "intro_fa": "جواز فعالیت و کارت مسئول فنی را مطابق الزامات قوانین ارزیابی کنید. "
        "۱ = تکمیل، ۰ = نخیر، تطبیق نشد = مشاهده نگردید.",
        "intro_en": "Assess the licence and the technical manager card against the "
        "regulations. 1 = met, 0 = not met, not observed = could not be verified.",
        "max_score": 5,
        "questions": [
            (
                "آیا مکتوب افتتاح (امتیاز) شفاخانه موجود است؟ (ماده ۲۰ مقرره دواخانه سال ۱۳۸۵)",
                "Is the pharmacy opening letter (licence) available? (Article 20, Pharmacy Regulation 1385)",
            ),
            (
                "آیا مکتوب افتتاح (امتیاز) شفاخانه در محل مناسب و قابل دید نصب است؟ (ماده ۲۰ مقرره دواخانه سال ۱۳۸۵)",
                "Is the opening letter displayed in a suitable, visible place? (Article 20)",
            ),
            (
                "آیا کارت فعالیت تجدید شده و نافذ مسئول فنی موجود است؟ (ماده ۲۰ مقرره دواخانه سال ۱۳۸۵)",
                "Is a renewed, valid technical manager activity card available? (Article 20)",
            ),
            (
                "آیا کارت فعالیت تجدید شده و نافذ مسئول فنی در محل مناسب و قابل دید نصب است؟ (ماده ۲۰)",
                "Is the technical manager activity card displayed in a suitable, visible place? (Article 20)",
            ),
            (
                "آیا درجه تحصیل مسئول فنی مطابق به درجه دواخانه میباشد؟ (ماده ۹ مقرره دواخانه سال ۱۳۸۵)",
                "Does the technical manager's qualification match the pharmacy grade? (Article 9)",
            ),
        ],
    },
    {
        "title_fa": "۳. بازرسی عمومی و قانونی بودن ادویه موجود در دواخانه",
        "title_en": "3. General inspection and legality of the medicines present",
        "intro_fa": "بطور تصادفی حد اقل پنج قلم ادویه را جهت بازرسی انتخاب نمائید. "
        "۱ = تکمیل، ۰ = نخیر. در صورت مشکوک بودن، فورم نمونه برداری (ضمیمه ۱) را خانه پری کنید.",
        "intro_en": "Select at least five medicines at random. 1 = met, 0 = not met. "
        "If a medicine is suspected, complete the sampling form (Annex 1).",
        "max_score": 5,
        "questions": [
            (
                "آیا تمام ادویه بازرسی شده شامل لست ملی ادویه مجاز است؟ (ماده ۹ قانون ادویه سال ۱۳۸۷)",
                "Are all inspected medicines on the national authorised medicines list? (Article 9, Medicines Law 1387)",
            ),
            (
                "آیا مواد مخدر (ضمیمه ۴) و مشروبات الکولی در دواخانه برای فروش وجود ندارد؟ (ماده ۴۴)",
                "Are narcotics (Annex 4) and alcoholic beverages absent from sale? (Article 44)",
            ),
            (
                "آیا ادویه تقلبی و غیر معیاری در دواخانه برای فروش وجود ندارد؟ (ماده ۴۴)",
                "Are counterfeit or substandard medicines absent from sale? (Article 44)",
            ),
            (
                "آیا لوازم غیر طبی در دواخانه برای فروش وجود ندارد؟ (ماده ۲ و ۱۸ مقرره دواخانه سال ۱۳۸۵)",
                "Are non-medical items absent from sale? (Articles 2 and 18, Pharmacy Regulation 1385)",
            ),
            (
                "آیا تمام ادویه بازرسی شده از تاسیسات دوایی دارای مجوز خریداری شده است؟ (ماده ۲۱ مقرره ۱۳۸۵ و فصل ۱۵ پالیسی ملی تضمین کیفیت ۱۳۹۴)",
                "Were all inspected medicines purchased from licensed facilities? (Article 21 and chapter 15 of the national quality assurance policy 1394)",
            ),
        ],
    },
    {
        "title_fa": "۴. آزمایش لیبل ادویه",
        "title_en": "4. Medicine labelling",
        "intro_fa": "بطور تصادفی حد اقل پنج قلم ادویه را از نظر لیبل، ورق معلوماتی و تاریخ انقضا بررسی کنید. "
        "۱ = تکمیل، ۰ = نخیر.",
        "intro_en": "Inspect at least five medicines for labelling, package insert and expiry date. "
        "1 = met, 0 = not met.",
        "max_score": 4,
        "questions": [
            (
                "آیا لیبل تمام ادویه بازرسی شده به یکی از لسان های رسمی کشور یا انگلیسی تحریر شده است؟ (فصل دوم رهنمود ثبت ادویه سال ۱۳۹۳)",
                "Are all inspected labels written in an official language or English? (Chapter 2, medicine registration guideline 1393)",
            ),
            (
                "آیا لیبل تمام ادویه مطابق شرایط لیبل گذاری مقرره و رهنمود ثبت ادویه است؟ (ماده ۲۴ مقرره تولید و تورید ۱۳۸۵)",
                "Do all labels meet the labelling requirements? (Article 24, production and import regulation 1385)",
            ),
            (
                "آیا ورق معلوماتی تمام ادویه مطابق شرایط ذکر شده در مقرره و رهنمود ثبت ادویه است؟ (ماده ۲۵)",
                "Do all package inserts meet the requirements? (Article 25)",
            ),
            (
                "آیا تمام ادویه بازرسی شده دارای تاریخ انقضای معتبر میباشد؟ (فصل ۷ پالیسی ملی تضمین کیفیت ۱۳۹۴)",
                "Do all inspected medicines have a valid expiry date? (Chapter 7, national quality assurance policy 1394)",
            ),
        ],
    },
    {
        "title_fa": "۵. مدیریت ادویه مخدر و تحت کنترول و سایر مستند سازی",
        "title_en": "5. Narcotics and controlled medicines management and documentation",
        "intro_fa": "نگهداری، ثبت و مستند سازی ادویه مخدر و تحت کنترول (کتگوری ۲) را بررسی کنید. "
        "۱ = تکمیل، ۰ = نخیر.",
        "intro_en": "Check the storage, recording and documentation of narcotics and controlled "
        "medicines (category 2). 1 = met, 0 = not met.",
        "max_score": 6,
        "questions": [
            (
                "آیا حد اقل یک الماری ویژه و قفل شدنی برای نگهداری ادویه مخدر و تحت کنترول وجود دارد؟ (فصل ۵ و ۱۲ پالیسی ملی ۱۳۹۵)",
                "Is there at least one locked cabinet dedicated to narcotics and controlled medicines? (Chapters 5 and 12)",
            ),
            (
                "آیا تمام ادویه مخدر و تحت کنترول در الماری ویژه قفل شدنی ذخیره شده است؟ (فصل ۵ و ۱۲)",
                "Are all narcotics and controlled medicines stored in the locked cabinet? (Chapters 5 and 12)",
            ),
            (
                "آیا تمام ادویه مخدر بازرسی شده دارای تاریخ انقضای معتبر است؟ (حد اقل سه قلم را چک کنید)",
                "Do all inspected narcotics have a valid expiry date? (check at least three items)",
            ),
            (
                "آیا دواخانه دارای کتاب ثبت ادویه مخدر و تحت کنترول میباشد؟ (ماده ۱۵ و ۳۵ مقرره ۱۳۸۵)",
                "Does the pharmacy keep a narcotics and controlled medicines register? (Articles 15 and 35)",
            ),
            (
                "آیا نسخه های ادویه مخدر و تحت کنترول بشکل درست درج کتاب ثبت شده است؟ (جدید ترین نسخه را بازرسی کنید)",
                "Are narcotic prescriptions correctly recorded in the register? (inspect the latest prescription)",
            ),
            (
                "آیا نسخه های ادویه مخدر از دسترس اشخاص غیر مسئول حفظ و نگهداری شده است؟ (ماده ۱۵)",
                "Are narcotic prescriptions kept out of reach of unauthorised persons? (Article 15)",
            ),
            (
                "آیا کتاب ثبت نسخه سایر ادویه غیر از ادویه مخدر موجود است؟ (ماده ۱۵ و ۳۵)",
                "Is there a prescription register for other medicines? (Articles 15 and 35)",
            ),
            (
                "آیا بل های خرید اقلام دوایی از تورید کننده گان و تولید کننده گان ثبت شده موجود است؟ (ماده ۲۱)",
                "Are purchase invoices from registered suppliers and manufacturers available? (Article 21)",
            ),
        ],
        "unscored": [6, 7],  # 5.7 and 5.8 are documented but not part of the index
    },
    {
        "title_fa": "۶. شرایط نگهداری (تذخیر ادویه)",
        "title_en": "6. Storage conditions",
        "intro_fa": "شرایط نگهداری ادویه را مطابق الزامات ارزیابی کنید. ۱ = تکمیل، ۰ = نخیر.",
        "intro_en": "Assess storage conditions against the requirements. 1 = met, 0 = not met.",
        "max_score": 7,
        "questions": [
            (
                "آیا درجه حرارت داخل دواخانه مطابق شرایط لیبل گذاری (۱۵ الی ۲۵ درجه یا منوط به اقلیم الی ۳۰ درجه) است؟ (ماده ۱۷ مقرره ۱۳۸۵ و ماده ۵۰ قانون ۱۳۸۷)",
                "Is the temperature inside the pharmacy within the labelled storage conditions (15-25 C, up to 30 C)? (Article 17 and Article 50)",
            ),
            (
                "آیا برای ثبت درجه حرارت دواخانه ترمامیتر وجود دارد؟ (ماده ۱۷ و ماده ۵۰)",
                "Is there a thermometer for recording the pharmacy temperature? (Article 17 and Article 50)",
            ),
            (
                "آیا دواخانه دارای یخچال (های) فعال برای نگهداری ادویه حساس در برابر حرارت میباشد؟ (ماده ۱۷ و ماده ۵۰)",
                "Does the pharmacy have working refrigerators for heat-sensitive medicines? (Article 17 and Article 50)",
            ),
            (
                "آیا ادویه حساس در برابر حرارت در داخل یخچال (ها) نگهداری و ذخیره میشوند؟ (ماده ۱۷ و ماده ۵۰)",
                "Are heat-sensitive medicines stored inside the refrigerator(s)? (Article 17 and Article 50)",
            ),
            (
                "آیا تمام ادویه موجود در یخچال (ها) دارای تاریخ انقضای معتبر است؟ (حد اقل سه قلم را چک کنید)",
                "Do all medicines in the refrigerator(s) have a valid expiry date? (check at least three)",
            ),
            (
                "آیا برای ثبت درجه حرارت یخچال (ها) ترمامیتر موجود است؟ (ماده ۱۷ و ماده ۵۰)",
                "Is there a thermometer for recording the refrigerator temperature? (Article 17 and Article 50)",
            ),
            (
                "آیا محل مناسب و جداگانه برای نگهداری ادویه تاریخ گذشته، مستردی، دوباره جمع آوری شده و قرنطین شده موجود و نشانی شده است؟ (پالیسی ۱۳۹۵ و فصل ۷)",
                "Is there a separate, labelled area for expired, returned, recalled and quarantined medicines?",
            ),
        ],
        # index (1-based question number) -> frequency sub-question
        "frequency_after": {2: "pharmacy", 6: "fridge"},
    },
    {
        "title_fa": "۷. وضعیت عمومی ساختمان دواخانه",
        "title_en": "7. General condition of the pharmacy building",
        "intro_fa": "وضعیت ساختمان دواخانه را برای ذخیره ادویه ارزیابی کنید. ۱ = تکمیل، ۰ = نخیر.",
        "intro_en": "Assess the building for medicine storage. 1 = met, 0 = not met.",
        "max_score": 8,
        "questions": [
            (
                "آیا دواخانه در محل کروکی شده فعالیت مینماید؟ (ماده ۷ مقرره ۱۳۸۵)",
                "Does the pharmacy operate at its approved (mapped) location? (Article 7)",
            ),
            (
                "آیا مساحت دواخانه مطابق درجه مربوطه است؟ (ماده ۱۹ قانون ۱۳۸۷: درجه اول ۵۳، درجه دو ۴۳، درجه سه ۳۸، سایر ۲۴ متر مربع)",
                "Does the floor area match the grade? (Article 19: first 53, second 43, third 38, other 24 m2)",
            ),
            (
                "آیا شفاخانه دارای مهر است؟ (ماده ۳۵ مقرره ۱۳۸۵)",
                "Does the pharmacy have an official stamp? (Article 35)",
            ),
            (
                "آیا شفاخانه لوحه معیاری دارد؟ (ماده ۳۵ مقرره ۱۳۸۵)",
                "Does the pharmacy have a standard signboard? (Article 35)",
            ),
            (
                "آیا از محیط داخلی دواخانه بحیث معاینه خانه استفاده نمیگردد؟ (ماده ۹ مقرره ۱۳۸۵)",
                "Is the pharmacy interior free of use as an examination room? (Article 9)",
            ),
            (
                "آیا دیوارها، کف و سقف در وضعیت خوب و بدون علایم رطوبت و ترکیدگی است؟ (ماده ۱۷ و ماده ۵۰)",
                "Are walls, floor and ceiling in good condition without damp or cracks? (Article 17 and Article 50)",
            ),
            (
                "آیا تمام محیط دواخانه پاک است؟ (ماده ۱۸ مقرره ۱۳۸۵)",
                "Is the whole pharmacy clean? (Article 18)",
            ),
            (
                "آیا سیستم تهویه هوا موجود و بطور مناسب کار میکند؟ (ماده ۱۷ مقرره ۱۳۸۵)",
                "Is ventilation present and working properly? (Article 17)",
            ),
        ],
    },
    {
        "title_fa": "۸. کارمندان و خدمات",
        "title_en": "8. Staff and services",
        "intro_fa": "وضعیت کارمندان و خدمات دواخانه را ارزیابی کنید. ۱ = تکمیل، ۰ = نخیر.",
        "intro_en": "Assess pharmacy staff and services. 1 = met, 0 = not met.",
        "max_score": 5,
        "questions": [
            (
                "آیا مسئول فنی حین بازرسی در دواخانه حضور دارد؟ (ماده ۳ مقرره ۱۳۸۵)",
                "Is the technical manager present during the inspection? (Article 3)",
            ),
            (
                "آیا مسئول فنی ملبس به چپن سفید پاک میباشد؟ (ماده ۲۶ مقرره ۱۳۸۵)",
                "Is the technical manager wearing a clean white coat? (Article 26)",
            ),
            (
                "آیا مسئول فنی هنگام توزیع ادویه معلومات ضروری و هدایات واضح در مورد ادویه تجویز شده به مریض میدهد؟ (ماده ۲۶)",
                "Does the technical manager give clear instructions about dispensed medicines? (Article 26)",
            ),
            (
                "آیا در نسخه (های) اجرا شده قیمت ادویه تحریر و مزین به مهر دواخانه میباشد؟ (ماده ۲۶)",
                "Do dispensed prescriptions show the price and the pharmacy stamp? (Article 26)",
            ),
            (
                "آیا فیصدی مفاد فروش ادویه و لوازم طبی مطابق احکام قانون است؟ (بیشتر از ۱۵ فیصد قیمت خرید نمیباشد - ماده ۱۷ قانون ۱۳۸۷)",
                "Is the profit margin within the legal limit of 15% of the purchase price? (Article 17)",
            ),
        ],
    },
]

REFERENCE_BOOKS = [
    (
        "قانون ادویه (جریده رسمی ۹۶۳، مورخ ۲۹ عقرب ۱۳۸۷)",
        "Medicines Law (Official Gazette 963, 29 Aqrab 1387)",
    ),
    (
        "مقرره دواخانه (جریده رسمی ۹۱۶، مورخ ۵ حوت ۱۳۸۵)",
        "Pharmacy Regulation (Official Gazette 916, 5 Hoot 1385)",
    ),
    ("لست ملی ادویه مجاز (۱۳۹۳)", "National authorised medicines list (1393)"),
    ("لست ملی ادویه اساسی (۱۳۹۳)", "National essential medicines list (1393)"),
    ("فورمولیر ملی افغان (۱۳۹۴)", "Afghan national formulary (1394)"),
    ("رهنمود ملی تداوی معیاری (۱۳۹۲)", "National standard treatment guideline (1392)"),
    ("پالیسی ملی دوایی (۱۳۹۳)", "National medicines policy (1393)"),
    (
        "پالیسی ملی تضمین کیفیت محصولات دوایی (۱۳۹۴)",
        "National quality assurance policy for medicines (1394)",
    ),
    (
        "پالیسی ملی ادویه مخدر و تحت کنترول (۱۳۹۵)",
        "National narcotics and controlled medicines policy (1395)",
    ),
    (
        "پالیسی ملی مدیریت و امحای مصئون زباله های دوایی (۱۳۹۵)",
        "National policy on safe medicine waste management (1395)",
    ),
]

# Section -> name used in the score calculations
SECTION_KEYS = ["license", "legality", "label", "narcotics", "storage", "building", "staff"]


def point(question_name: str) -> str:
    return f"if(${{{question_name}}} = '1', 1, 0)"


def build_survey():
    rows = [SURVEY_HEADERS]
    q_index = 0

    def add(excel_type, name, label_fa, label_en, hint_fa="", hint_en="",
            required="", appearance="", relevant="", calculation=""):
        rows.append(
            [
                excel_type,
                name,
                label_fa,
                label_en,
                hint_fa,
                hint_en,
                required,
                appearance,
                relevant,
                calculation,
            ]
        )

    def group_start(name, label_fa, label_en):
        add("begin_group", name, label_fa, label_en)

    def group_end(name):
        add("end_group", name, "", "")

    def note(name, label_fa, label_en=""):
        add("note", name, label_fa, label_en)

    # ------------------------------------------------------------------ meta
    add("start", "start", "", "")
    add("end", "end", "", "")
    add("today", "today", "", "")

    # --------------------------------------------------- 1. general details
    group_start("general", "۱. معلومات عمومی", "1. General information")
    add(
        "text",
        "pharmacy_name",
        "اسم دواخانه / شفاخانه",
        "Pharmacy / hospital pharmacy name",
        required="yes",
    )
    add(
        "text",
        "license_number",
        "شماره مکتوب افتتاح (شماره امتیاز)",
        "Opening letter (licence) number",
        required="yes",
    )
    add("date", "established_date", "تاریخ تاسیس شفاخانه", "Date established")
    add(
        "select_one grade",
        "pharmacy_grade",
        "نوع دواخانه ثبت شده",
        "Registered pharmacy grade",
        required="yes",
    )
    add(
        "date",
        "inspection_date",
        "تاریخ بازرسی",
        "Inspection date",
        hint_fa="تاریخ میلادی ثبت میشود و در سیستم به شمسی نمایش داده میشود.",
        hint_en="Stored in the Gregorian calendar and shown in the Shamsi calendar.",
        required="yes",
    )
    add(
        "date",
        "last_inspection_date",
        "تاریخ آخرین بازرسی",
        "Date of last inspection",
        hint_fa="در صورت موجودیت.",
        hint_en="If known.",
    )
    add("time", "inspection_start_time", "زمان آغاز بازرسی", "Inspection start time")
    add(
        "select_one inspection_type",
        "inspection_type",
        "نوع بازرسی",
        "Type of inspection",
        required="yes",
    )
    add("text", "province", "ولایت", "Province", required="yes")
    add("text", "district", "ولسوالی / ناحیه", "District", required="yes")
    add("text", "village", "قریه", "Village")
    add("text", "road", "سرک", "Road")
    add("text", "street", "کوچه", "Street / alley")
    add(
        "geopoint",
        "gps_location",
        "طول و عرض البلد (GPS)",
        "GPS coordinates",
        hint_fa="در صورت موجودیت وسیله GPS ثبت کنید.",
        hint_en="Capture if a GPS device is available.",
    )
    add("text", "address", "آدرس فزیکی", "Physical address", required="yes")
    add("text", "phone", "شماره تیلفون", "Phone number", required="yes")
    add("text", "email", "آدرس الکترونیکی", "Email address")
    add("text", "owner_name", "اسم مالک شفاخانه", "Owner name", required="yes")
    add(
        "text",
        "technical_manager_name",
        "اسم مسئول فنی دواخانه",
        "Technical manager name",
        required="yes",
    )
    add(
        "text",
        "technical_manager_card",
        "شماره کارت مسئول فنی",
        "Technical manager card number",
    )
    group_end("general")

    # ------------------------------------------------------ scored sections
    score_rows = []
    max_rows = []

    for section_index, section in enumerate(SECTIONS):
        key = SECTION_KEYS[section_index]
        group = f"sec{section_index + 2}"
        group_start(group, section["title_fa"], section["title_en"])
        if section.get("intro_fa"):
            note(f"{group}_intro", section["intro_fa"], section.get("intro_en", ""))

        # Expose the section title and position as data so Mandi can label and
        # order the section index without knowing the form.
        add(
            "calculate",
            f"order_{key}",
            "",
            "",
            calculation=str(section_index + 2),
        )
        if "'" not in section["title_fa"]:
            add(
                "calculate",
                f"title_{key}",
                "",
                "",
                calculation=f"'{section['title_fa']}'",
            )

        names = []
        unscored = set(section.get("unscored", []))
        for position, (label_fa, label_en) in enumerate(section["questions"], start=1):
            q_index += 1
            name = f"q{section_index + 2}_{position}"
            names.append(name)
            add(
                "select_one yn",
                name,
                label_fa,
                label_en,
                required="yes",
                appearance="horizontal-compact",
            )

            if position == 5 and key == "narcotics":
                # 5.5 only applies when the register book exists (5.4).
                rows[-1][8] = "${q5_4} = '1'"
            if position == 4 and key == "narcotics":
                rows[-1][4] = "در صورتیکه جواب «۰» باشد، در سوال ۵.۵ \"تطبیق نشد\" بنویسید."
                rows[-1][5] = "If the answer is 0, record \"not observed\" for 5.5."
            if position == 5 and key == "license":
                rows[-1][4] = "در صورتیکه کارت مسئول فنی موجود نباشد، \"تطبیق نشد\" انتخاب کنید."
                rows[-1][5] = "If the card is unavailable, select \"not observed\"."

            frequency = section.get("frequency_after", {}).get(position)
            if frequency:
                add(
                    "select_one freq",
                    f"{name}_freq",
                    "در صورتیکه بلی، چند مراتبه درجه حرارت ثبت میگردد؟",
                    "If yes, how often is the temperature recorded?",
                    required="yes",
                    relevant=f"${{{name}}} = '1'",
                )

        scored = [
            names[i]
            for i in range(len(names))
            if (i + 1) not in unscored
        ]
        expression = " + ".join(point(item) for item in scored)
        score_rows.append((f"score_{key}", expression))

        # Denominator adjustments mirror the paper checklist.
        if key == "license":
            max_rows.append(
                (f"max_{key}", f"if(${{q2_5}} = '', 5, if(${{q2_5}} = '2', 4, 5))")
            )
        elif key == "narcotics":
            max_rows.append(
                (f"max_{key}", f"if(${{q5_4}} = '1', 6, 5)")
            )
        elif key == "staff":
            max_rows.append(
                (
                    f"max_{key}",
                    " ".join(
                        [
                            "5",
                            "- if(${q8_3} = '2', 1, 0)",
                            "- if(${q8_4} = '2', 1, 0)",
                            "- if(${q8_5} = '2', 1, 0)",
                        ]
                    ),
                )
            )
        else:
            max_rows.append((f"max_{key}", str(section["max_score"])))

        group_end(group)

    # ------------------------------------------------- 9. reference documents
    group_start("sec9", "۹. موجودیت کتب ماخذ", "9. Availability of reference documents")
    note(
        "sec9_intro",
        "از کارمندان دواخانه بخواهید کتب ماخذ ذیل را حاضر نمایند. این بخش ضرورت به نمره دهی ندارد.",
        "Ask the pharmacy staff to present the following reference documents. "
        "This section is not scored.",
    )
    for position, (label_fa, label_en) in enumerate(REFERENCE_BOOKS, start=1):
        add("select_one yes_no", f"q9_{position}", label_fa, label_en, required="yes",
            appearance="horizontal-compact")
    group_end("sec9")

    # ------------------------------------------------------------- 10. scores
    group_start("scoring", "۱۰. نمره دهی", "10. Scoring")

    for name, expression in score_rows:
        add("calculate", name, "", "", calculation=expression)
    for name, expression in max_rows:
        add("calculate", name, "", "", calculation=expression)
    for key in SECTION_KEYS:
        add(
            "calculate",
            f"pct_{key}",
            "",
            "",
            calculation=(
                f"if(${{max_{key}}} > 0, round(100 * ${{score_{key}}} div ${{max_{key}}}, 1), 0)"
            ),
        )
    add(
        "calculate",
        "score_total",
        "",
        "",
        calculation=" + ".join(f"${{score_{key}}}" for key in SECTION_KEYS),
    )
    add(
        "calculate",
        "max_total",
        "",
        "",
        calculation=" + ".join(f"${{max_{key}}}" for key in SECTION_KEYS),
    )
    add(
        "calculate",
        "result_pct",
        "",
        "",
        calculation="if(${max_total} > 0, round(100 * ${score_total} div ${max_total}, 1), 0)",
    )
    group_end("scoring")

    # -------------------------------------------- 11. other observations
    group_start("observations", "۱۱. سایر مشاهدات و ملاحظات", "11. Other observations")
    add(
        "text",
        "other_observations",
        "سایر مشاهدات و ملاحظات",
        "Other observations",
        appearance="multiline",
    )
    group_end("observations")

    # ---------------------------------------------- 12. inspection team advice
    group_start("sec12", "۱۲. هدایات تیم بازرسی", "12. Inspection team advice")
    note(
        "actions_intro",
        "مواردیکه نیاز به اصلاح دارد و اقدامات توافق شده با محدوده زمانی را ثبت کنید.",
        "Record the issues that need correction and the agreed actions with a timeframe.",
    )
    add("begin_repeat", "actions", "موارد قابل اصلاح", "Corrective actions")
    add("text", "issue_found", "مواردیکه نیاز به توجه و اصلاحات دارد", "Issue needing attention",
        appearance="multiline")
    add("text", "agreed_action", "اقدامات توافق شده با محدوده زمانی",
        "Agreed action and timeframe", appearance="multiline")
    add("end_repeat", "actions", "", "")
    group_end("sec12")

    # ------------------------------------------------ 13. owner commitment
    group_start("sec13", "۱۳. تعهد مالک و مسئول فنی دواخانه",
                "13. Owner and technical manager commitment")
    note(
        "commitment_text",
        "من تصدیق مینمایم که معلومات، مشاهدات و ملاحظات ذکر شده در این فورم درست بوده "
        "و موارد شناسایی شده با اقدامات اصلاحی به آن موافق میباشیم.",
        "I confirm that the information, observations and remarks recorded in this form "
        "are correct and that the identified issues and corrective actions are agreed.",
    )
    add(
        "select_one yes_no",
        "owner_confirms",
        "آیا مالک و مسئول فنی این فورم را تایید نمودند؟",
        "Did the owner and the technical manager confirm this form?",
        required="yes",
        appearance="horizontal-compact",
    )
    add("text", "owner_signature_name", "اسم مالک / مدیر اداری", "Owner / administrative manager name",
        relevant="${owner_confirms} = 'yes'")
    add("text", "technical_manager_signature_name", "اسم مسئول فنی",
        "Technical manager name", relevant="${owner_confirms} = 'yes'")
    group_end("sec13")

    # ------------------------------------------------------------ 14. wrap up
    group_start("sec14", "۱۴. اتمام کار و ۱۵. بازرسی کنندگان",
                "14. Completion and 15. Inspectors")
    add("time", "inspection_end_time", "وقت ختم کار", "Inspection end time")
    add("begin_repeat", "inspectors", "بازرسی کنندگان", "Inspectors")
    add("text", "inspector_name", "اسم بازرسی کننده", "Inspector name")
    add("text", "inspector_position", "موقف بازرسی", "Inspector position")
    add("date", "inspector_date", "تاریخ", "Date")
    add("text", "inspector_signature", "امضاء (نام و تاییدیه)",
        "Signature (type full name to confirm)", appearance="multiline")
    add("end_repeat", "inspectors", "", "")
    group_end("sec14")

    # -------------------------------------------------------- annex 1 samples
    group_start("annex1", "ضمیمه ۱. فورم جمع آوری نمونه های مشکوک",
                "Annex 1. Sampling form for suspected medicines")
    note(
        "annex1_intro",
        "در صورت مشکوک بودن ادویه، نمونه را برای آزمایشات لابراتواری ثبت کنید.",
        "Record samples for laboratory testing when a medicine is suspected.",
    )
    add("begin_repeat", "samples", "نمونه ها", "Samples")
    add("text", "sample_generic_name", "نام جنریک", "Generic name")
    add("text", "sample_trade_name", "نام تجارتی", "Trade name")
    add("text", "sample_batch", "شماره بچ", "Batch number")
    add("date", "sample_production_date", "تاریخ تولید", "Manufacturing date")
    add("date", "sample_expiry_date", "تاریخ انقضاء", "Expiry date")
    add("text", "sample_quantity", "مقدار", "Quantity")
    add("text", "sample_manufacturer", "تولید کننده", "Manufacturer")
    add("text", "sample_supplier", "تورید کننده", "Supplier")
    add("text", "sample_quarantined", "مقدار مجموعی قرنطین شده",
        "Total quarantined quantity")
    add("end_repeat", "samples", "", "")
    group_end("annex1")

    add(
        "note",
        "thank_you",
        "از مالک، مسئول فنی و سایر کارکنان دواخانه که در تکمیل این چک لست همکاری نمودند تشکر نمائید.",
        "Thank the owner, technical manager and staff for supporting this inspection.",
    )

    return rows


def style_sheet(sheet, widths, freeze="A2"):
    header_fill = PatternFill("solid", fgColor="DDEBF7")
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    sheet.freeze_panes = freeze


def main():
    workbook = Workbook()

    survey = workbook.active
    survey.title = "survey"
    for row in build_survey():
        survey.append(row)
    style_sheet(survey, [26, 34, 62, 56, 43, 40, 10, 22, 26, 52])

    choices = workbook.create_sheet("choices")
    choices.append(CHOICE_HEADERS)
    for row in CHOICES:
        choices.append(row)
    style_sheet(choices, [14, 22, 34, 30])

    settings = workbook.create_sheet("settings")
    for row in SETTINGS:
        settings.append(row)
    style_sheet(settings, [62, 34, 14, 16, 34])

    workbook.save(OUTPUT)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
