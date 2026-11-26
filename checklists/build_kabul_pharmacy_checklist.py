"""Build the Kabul pharmacy field checklist (evidence, scoring, audit trail).

This is a compact field form for Kabul pharmacies. It reuses three scored
sections of the national pharmacy checklist
(``pharmacy_inspection_checklist_1405.xlsx``) and adds:

* an automatic GPS point captured when the form opens (``start-geopoint``),
  plus a required point taken at the pharmacy entrance;
* automatic start/end metadata and a calculated inspection duration, so the
  collector is never asked for dates or times;
* pharmacy selection with the establishment details Mandi injects on deploy;
* the evidence photographs (front, licence on the wall, three interior
  directions);
* 0/1 scoring per section with automatic percentages per section and overall;
* a repeat group for samples taken and medicines quarantined;
* the inspecting employees with finger signatures.

Every group is a ``field-list``: one section per screen. Labels, hints and
choices are provided in Dari (default), Pashto and English.

Run with the project virtualenv:

    .venv/bin/python checklists/build_kabul_pharmacy_checklist.py

The workbook is written next to this script as
``kabul_pharmacy_checklist.xlsx`` and can be uploaded to Mandi
(Checklists -> Add checklist -> Deploy).
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

OUTPUT = Path(__file__).with_name("kabul_pharmacy_checklist.xlsx")

SURVEY_HEADERS = [
    "type",
    "name",
    "label::Dari (fa)",
    "label::Pashto (ps)",
    "label::English (en)",
    "hint::Dari (fa)",
    "hint::Pashto (ps)",
    "hint::English (en)",
    "required",
    "default",
    "appearance",
    "parameters",
    "relevant",
    "calculation",
    "choice_filter",
]

CHOICE_HEADERS = [
    "list_name",
    "name",
    "label::Dari (fa)",
    "label::Pashto (ps)",
    "label::English (en)",
]

SETTINGS = [
    ["form_title", "form_id", "version", "default_language", "mandi_establishment_filter"],
    [
        "چک لست بازرسی دواخانه های شهر کابل",
        "kabul_pharmacy_inspection",
        "2026112602",
        "Dari (fa)",
        "kind = 'pharmacy'",
    ],
]

CHOICES = [
    # 1/0/2: the percentage of a section is score / number of applicable questions.
    ["yn", "1", "۱ – مطابق / تکمیل", "۱ – سم / بشپړ", "1 - Met"],
    ["yn", "0", "۰ – عدم مطابقت", "۰ – نه سم", "0 - Not met"],
    ["yn", "2", "۲ – قابل تطبیق نیست", "۲ – د تطبیق وړ نه دی", "2 - Not applicable"],
    [
        "sample_action",
        "sample",
        "نمونه برداری برای لابراتوار",
        "د لابراتوار لپاره نمونه اخیستل",
        "Sample for laboratory testing",
    ],
    [
        "sample_action",
        "quarantine",
        "قرنطین ادویه",
        "د درملو قرنطین",
        "Medicine quarantined",
    ],
]

# ---------------------------------------------------------------------------
# Scored sections (taken from the national pharmacy checklist)
# ---------------------------------------------------------------------------
# Text tuples are always (Dari, Pashto, English).
# Every question is a select_one yn and scores 1 for "1" and 0 for "0".

SECTIONS = [
    {
        "key": "license",
        "order": 1,
        "group": "sec_license",
        "title": ("جواز فعالیت", "د فعالیت جواز", "Licence to operate"),
        "intro": (
            "جواز فعالیت و کارت مسئول فنی را بررسی کنید. ۱ = مطابق، ۰ = عدم مطابقت، "
            "۲ = قابل تطبیق نیست.",
            "د فعالیت جواز او د تخنیکي مسئول کارت وګورئ. ۱ = سم، ۰ = نه سم، "
            "۲ = د تطبیق وړ نه دی.",
            "Check the licence and the technical manager card. 1 = met, 0 = not met, "
            "2 = not applicable.",
        ),
        "source": (
            "منبع: چک لست ملی – بخش ۲",
            "سرچینه: ملي چک لست – ۲ برخه",
            "Source: national checklist, section 2",
        ),
        "questions": [
            (
                "آیا مکتوب افتتاح (جواز فعالیت) دواخانه موجود است؟ (ماده ۲۰ مقرره دواخانه ۱۳۸۵)",
                "ایا د درملتون د پرانیستې لیک (د فعالیت جواز) شته؟ "
                "(د ۱۳۸۵ کال د درملتون مقررې ۲۰ ماده)",
                "Is the pharmacy opening letter (licence) available? (Article 20)",
            ),
            (
                "آیا مکتوب افتتاح در محل مناسب و قابل دید نصب شده است؟ (ماده ۲۰)",
                "ایا د پرانیستې لیک په مناسب او ښکاره ځای لګول شوی دی؟ (۲۰ ماده)",
                "Is the opening letter displayed in a suitable, visible place? (Article 20)",
            ),
            (
                "آیا کارت فعالیت تجدید شده و نافذ مسئول فنی موجود است؟ (ماده ۲۰)",
                "ایا د تخنیکي مسئول نوی شوی او معتبر د فعالیت کارت شته؟ (۲۰ ماده)",
                "Is a renewed, valid technical manager activity card available? (Article 20)",
            ),
            (
                "آیا کارت مسئول فنی در محل مناسب و قابل دید نصب است؟ (ماده ۲۰)",
                "ایا د تخنیکي مسئول کارت په مناسب او ښکاره ځای لګول شوی دی؟ (۲۰ ماده)",
                "Is the technical manager card displayed in a suitable, visible place? (Article 20)",
            ),
            (
                "آیا درجه تحصیل مسئول فنی مطابق درجه دواخانه است؟ (ماده ۹)",
                "ایا د تخنیکي مسئول زده کړې کچه د درملتون له درجې سره سمه ده؟ (۹ ماده)",
                "Does the technical manager's qualification match the pharmacy grade? (Article 9)",
            ),
        ],
    },
    {
        "key": "storage",
        "order": 2,
        "group": "sec_storage",
        "title": ("شرایط نگهداری ادویه", "د درملو د ساتنې شرایط", "Medicine storage conditions"),
        "intro": (
            "شرایط نگهداری ادویه را مطابق لیبل و الزامات بررسی کنید. ۱ = مطابق، "
            "۰ = عدم مطابقت، ۲ = قابل تطبیق نیست.",
            "د درملو د ساتنې شرایط د لیبل او غوښتنو سره سم وګورئ. ۱ = سم، ۰ = نه سم، "
            "۲ = د تطبیق وړ نه دی.",
            "Check storage against the label and the requirements. 1 = met, 0 = not met, "
            "2 = not applicable.",
        ),
        "source": (
            "منبع: چک لست ملی – بخش ۶",
            "سرچینه: ملي چک لست – ۶ برخه",
            "Source: national checklist, section 6",
        ),
        "questions": [
            (
                "آیا درجه حرارت داخل دواخانه مطابق شرایط لیبل گذاری است؟ "
                "(۱۵ الی ۲۵ درجه، منوط به اقلیم الی ۳۰ درجه – ماده ۱۷ و ماده ۵۰)",
                "ایا د درملتون دننه تودوخه د لیبل له شرایطو سره سمه ده؟ "
                "(۱۵ تر ۲۵ درجو، د اقلیم له مخې تر ۳۰ درجو – ۱۷ او ۵۰ ماده)",
                "Is the temperature inside the pharmacy within the labelled storage conditions? "
                "(15-25 C, up to 30 C - Article 17 and Article 50)",
            ),
            (
                "آیا برای ثبت درجه حرارت دواخانه ترمامیتر موجود است؟ (ماده ۱۷ و ماده ۵۰)",
                "ایا د درملتون د تودوخې ثبتولو لپاره ترمامیتر شته؟ (۱۷ او ۵۰ ماده)",
                "Is a thermometer available for recording the pharmacy temperature? "
                "(Article 17 and Article 50)",
            ),
            (
                "آیا یخچال فعال برای نگهداری ادویه حساس در برابر حرارت موجود است؟ "
                "(ماده ۱۷ و ماده ۵۰)",
                "ایا د تودوخې حساسو درملو ساتلو لپاره فعال یخچال شته؟ (۱۷ او ۵۰ ماده)",
                "Is there a working refrigerator for heat-sensitive medicines? "
                "(Article 17 and Article 50)",
            ),
            (
                "آیا ادویه حساس در برابر حرارت در داخل یخچال نگهداری می‌شود؟ (ماده ۱۷ و ماده ۵۰)",
                "ایا تودوخې ته حساس درمل په یخچال کې ساتل کېږي؟ (۱۷ او ۵۰ ماده)",
                "Are heat-sensitive medicines stored inside the refrigerator? "
                "(Article 17 and Article 50)",
            ),
            (
                "آیا محل جداگانه و نشانی شده برای ادویه تاریخ گذشته، مستردی و قرنطین شده موجود است؟ "
                "(فصل ۷ پالیسی ملی تضمین کیفیت ۱۳۹۴)",
                "ایا د تاریخ تېرو، بېرته راستانه شوو او قرنطین شوو درملو لپاره جلا او په نښه شوی "
                "ځای شته؟ (د ۱۳۹۴ کال د کیفیت تضمین ملي پالیسي، ۷ فصل)",
                "Is there a separate, labelled area for expired, returned and quarantined "
                "medicines? (Chapter 7, national quality assurance policy 1394)",
            ),
        ],
    },
    {
        "key": "premises",
        "order": 3,
        "group": "sec_premises",
        "title": (
            "پاکی و وضعیت عمومی دواخانه",
            "د درملتون پاکوالی او عمومي حالت",
            "Cleanliness and general condition",
        ),
        "intro": (
            "وضعیت ساختمان و پاکی دواخانه را بررسی کنید. ۱ = مطابق، ۰ = عدم مطابقت، "
            "۲ = قابل تطبیق نیست.",
            "د درملتون د ودانۍ حالت او پاکوالی وګورئ. ۱ = سم، ۰ = نه سم، "
            "۲ = د تطبیق وړ نه دی.",
            "Check the building condition and cleanliness. 1 = met, 0 = not met, "
            "2 = not applicable.",
        ),
        "source": (
            "منبع: چک لست ملی – بخش ۷",
            "سرچینه: ملي چک لست – ۷ برخه",
            "Source: national checklist, section 7",
        ),
        "questions": [
            (
                "آیا دواخانه در محل کروکی شده جواز فعالیت می‌کند؟ (ماده ۷ مقرره ۱۳۸۵)",
                "ایا درملتون په خپل نقشه شوي ځای کې فعالیت کوي؟ (د ۱۳۸۵ مقررې ۷ ماده)",
                "Does the pharmacy operate at its approved (mapped) location? (Article 7)",
            ),
            (
                "آیا دواخانه لوحه معیاری دارد؟ (ماده ۳۵ مقرره ۱۳۸۵)",
                "ایا درملتون معیاري لوحه لري؟ (د ۱۳۸۵ مقررې ۳۵ ماده)",
                "Does the pharmacy have a standard signboard? (Article 35)",
            ),
            (
                "آیا دیوارها، کف و سقف در وضعیت خوب و بدون علایم رطوبت و ترکیدگی است؟ "
                "(ماده ۱۷ و ماده ۵۰)",
                "ایا دیوالونه، پوړ او چت په ښه حالت او له لندبل او درزونو پرته دي؟ (۱۷ او ۵۰ ماده)",
                "Are walls, floor and ceiling in good condition without damp or cracks? "
                "(Article 17 and Article 50)",
            ),
            (
                "آیا تمام محیط دواخانه پاک است؟ (ماده ۱۸ مقرره ۱۳۸۵)",
                "ایا د درملتون ټول چاپېریال پاک دی؟ (د ۱۳۸۵ مقررې ۱۸ ماده)",
                "Is the whole pharmacy clean? (Article 18)",
            ),
            (
                "آیا سیستم تهویه هوا موجود و بطور مناسب کار می‌کند؟ (ماده ۱۷ مقرره ۱۳۸۵)",
                "ایا د هوا د بدلون سیستم شته او سم کار کوي؟ (د ۱۳۸۵ مقررې ۱۷ ماده)",
                "Is ventilation present and working properly? (Article 17)",
            ),
        ],
    },
]

DARI_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def number(value: int) -> str:
    """Dari/Pashto numeral for section headings, matching the paper checklist."""
    return str(value).translate(DARI_DIGITS)


def point(question_name: str) -> str:
    return f"if(${{{question_name}}} = '1', 1, 0)"


def build_survey():
    rows = [SURVEY_HEADERS]
    totals = []

    def add(excel_type, name, label_fa="", label_ps="", label_en="",
            hint_fa="", hint_ps="", hint_en="", required="", default="",
            appearance="", parameters="", relevant="", calculation="",
            choice_filter=""):
        rows.append(
            [
                excel_type,
                name,
                label_fa,
                label_ps,
                label_en,
                hint_fa,
                hint_ps,
                hint_en,
                required,
                default,
                appearance,
                parameters,
                relevant,
                calculation,
                choice_filter,
            ]
        )

    def group_start(name, labels, appearance="field-list"):
        add("begin_group", name, *labels, appearance=appearance)

    def group_end():
        add("end_group", "")

    def note(name, labels, hint=("", "", ""), relevant=""):
        add("note", name, *labels, *hint, relevant=relevant)

    def photo(name, labels, hints):
        add(
            "image",
            name,
            *labels,
            *hints,
            required="yes",
            appearance="new",
            parameters="max-pixels=1600",
        )

    # ------------------------------------------------------------- metadata
    # Automatic values: opening/closing date-time, user, device and the
    # background GPS point taken when the form is opened. The collector is
    # never asked for a date or a time.
    add("start", "start")
    add("end", "end")
    add("today", "today")
    add("username", "username")
    add("deviceid", "deviceid")
    add("start-geopoint", "start_location")

    # ------------------------------------------------- 1. visit and pharmacy
    group_start(
        "visit",
        (
            "۱. انتخاب دواخانه",
            "۱. د درملتون ټاکنه",
            "1. Pharmacy",
        ),
    )
    # Mandi injects the establishment details group (province, district,
    # licence number and dates, grade, owner, technical manager) directly
    # after this question when the checklist is deployed.
    add(
        "select_one_from_file establishments.csv",
        "establishment_id",
        "دواخانه را انتخاب کنید",
        "درملتون وټاکئ",
        "Select the pharmacy",
        "نام دواخانه را جستجو کنید؛ بعد از انتخاب، معلومات ثبت شده آن نمایش داده می‌شود.",
        "د درملتون نوم ولټوئ؛ له ټاکنې وروسته یې ثبت شوي معلومات ښکاري.",
        "Search the pharmacy; its registered details appear after selection.",
        required="yes",
        appearance="search",
        choice_filter="kind = 'pharmacy'",
    )
    note(
        "pharmacy_scope_note",
        (
            "این فورم برای دواخانه های شهر کابل است. اگر ولایت و ولسوالی نمایش داده شده کابل نیست، "
            "دواخانه درست را انتخاب کنید.",
            "دا فورم د کابل ښار درملتونونو لپاره دی. که ښودل شوې ولایت او ولسوالي کابل نه وي، "
            "سم درملتون وټاکئ.",
            "This form is for pharmacies in Kabul city. If the province and district shown "
            "are not in Kabul, select the correct pharmacy.",
        ),
    )
    group_end()

    # ------------------------------------------------- 2. location and media
    group_start(
        "evidence",
        (
            "۲. موقعیت و عکس های شواهد",
            "۲. موقعیت او د شاهد عکسونه",
            "2. Location and evidence photographs",
        ),
    )
    note(
        "evidence_intro",
        (
            "نقطه موقعیت بطور خودکار هنگام باز شدن فورم ثبت می‌شود. علاوه بر آن، موقعیت را در ورودی "
            "دواخانه ثبت کنید و عکس های ذیل را در همین بازرسی بگیرید.",
            "د موقعیت نقطه د فورم پرانیستلو پر مهال اتوماتیک ثبت کېږي. سربېره پردې، موقعیت د درملتون "
            "په دروازه کې ثبت کړئ او لاندې عکسونه په همدې پلټنه کې واخلئ.",
            "The location point is recorded automatically when the form opens. Also capture "
            "the point at the pharmacy entrance and take the photographs below during this visit.",
        ),
    )
    add(
        "geopoint",
        "pharmacy_location",
        "موقعیت GPS دواخانه (در ورودی)",
        "د درملتون GPS موقعیت (په دروازه کې)",
        "Pharmacy GPS point (at the entrance)",
        "در ورودی دواخانه با GPS وسیله ثبت کنید؛ از انتخاب دستی روی نقشه خودداری کنید.",
        "د درملتون په دروازه کې د وسیلې GPS ثبت کړئ؛ له لاسي نقشې ټاکنې ډډه وکړئ.",
        "Capture at the pharmacy entrance with the device GPS; avoid manual map placement.",
        required="yes",
    )
    photo(
        "pharmacy_front_photo",
        (
            "عکس نمای بیرونی دواخانه و لوحه",
            "د درملتون د باندې مخ او لوحې عکس",
            "Photo of the pharmacy front and signboard",
        ),
        (
            "نام دواخانه و درب ورودی در عکس واضح باشد.",
            "د درملتون نوم او ننوتلو دروازه دې په عکس کې ښکاره وي.",
            "The pharmacy name and entrance must be clearly visible.",
        ),
    )
    photo(
        "licence_wall_photo",
        (
            "عکس جواز فعالیت نصب شده روی دیوار",
            "په دیوال لګول شوي جواز عکس",
            "Photo of the licence affixed to the wall",
        ),
        (
            "عکس از محل نصب جواز بگیرید؛ اگر جواز نصب نشده، محل خالی دیوار را عکس بگیرید.",
            "د جواز د لګولو ځای عکس واخلئ؛ که جواز نه وي لګول شوی، د دیوال تش ځای عکس واخلئ.",
            "Photograph where the licence is affixed; if it is not displayed, photograph "
            "the empty wall area.",
        ),
    )
    photo(
        "interior_photo_entry",
        (
            "عکس جهت اول از داخل دواخانه: رو به درب ورودی",
            "د درملتون له داخل لومړی لوری: د ننوتلو دروازې ته مخامخ",
            "Interior photo 1: facing the entrance door",
        ),
        (
            "از داخل دواخانه رو به درب ورودی عکس بگیرید.",
            "د درملتون له داخله د ننوتلو دروازې ته مخامخ عکس واخلئ.",
            "Stand inside the pharmacy and photograph towards the entrance door.",
        ),
    )
    photo(
        "interior_photo_shelves",
        (
            "عکس جهت دوم از داخل دواخانه: رو به قفسه های ادویه",
            "د درملتون له داخل دویم لوری: د درملو الماریو ته مخامخ",
            "Interior photo 2: facing the medicine shelves",
        ),
        (
            "قفسه ها و چیدمان ادویه واضح باشد.",
            "المارۍ او د درملو ترتیب دې ښکاره وي.",
            "The shelves and the medicine arrangement must be clear.",
        ),
    )
    photo(
        "interior_photo_storage",
        (
            "عکس جهت سوم از داخل دواخانه: رو به یخچال و محل قرنطین",
            "د درملتون له داخل درېیم لوری: یخچال او د قرنطین ځای ته مخامخ",
            "Interior photo 3: facing the refrigerator and quarantine area",
        ),
        (
            "یخچال، ترمامیتر و محل ادویه قرنطین شده را در عکس نشان دهید (در صورت موجودیت).",
            "یخچال، ترمامیتر او د قرنطین شوو درملو ځای په عکس کې وښایئ (که شته).",
            "Show the refrigerator, thermometer and quarantined medicines if present.",
        ),
    )
    group_end()

    # ------------------------------------------------ 3-5. scored sections
    for index, section in enumerate(SECTIONS, start=1):
        group_start(
            section["group"],
            (
                f"{number(index + 2)}. {section['title'][0]}",
                f"{number(index + 2)}. {section['title'][1]}",
                f"{index + 2}. {section['title'][2]}",
            ),
        )
        note(f"{section['group']}_intro", section["intro"])
        note(f"{section['group']}_source", section["source"])
        # Data fields so Mandi can label and order the section index.
        add("calculate", f"order_{section['key']}", calculation=str(section["order"]))
        add(
            "calculate",
            f"title_{section['key']}",
            calculation=f"'{section['title'][0]}'",
        )

        names = []
        for position, labels in enumerate(section["questions"], start=1):
            name = f"q_{section['key']}_{position}"
            names.append(name)
            add("select_one yn", name, *labels, required="yes")
        totals.append((section["key"], names))
        group_end()

    # --------------------------------------------------------- 6. scoring
    # The scores are calculated but never displayed: the collector sees no
    # percentage, Mandi shows the index on the submission and dashboard only.
    for key, names in totals:
        add("calculate", f"score_{key}", calculation=" + ".join(point(name) for name in names))
        not_applicable = "".join(f" - if(${{{name}}} = '2', 1, 0)" for name in names)
        add("calculate", f"max_{key}", calculation=f"{len(names)}{not_applicable}")
        add(
            "calculate",
            f"pct_{key}",
            calculation=f"if(${{max_{key}}} > 0, round(100 * ${{score_{key}}} div ${{max_{key}}}, 1), 0)",
        )
    add(
        "calculate",
        "score_total",
        calculation=" + ".join(f"${{score_{key}}}" for key, _ in totals),
    )
    add(
        "calculate",
        "max_total",
        calculation=" + ".join(f"${{max_{key}}}" for key, _ in totals),
    )
    add(
        "calculate",
        "result_pct",
        calculation="if(${max_total} > 0, round(100 * ${score_total} div ${max_total}, 1), 0)",
    )

    # ---------------------------------------- 7. samples and quarantined stock
    group_start(
        "samples",
        (
            "۶. نمونه برداری و قرنطین ادویه",
            "۶. د نمونو اخیستل او د درملو قرنطین",
            "6. Samples and quarantined medicines",
        ),
        appearance="",
    )
    note(
        "samples_intro",
        (
            "۶. نمونه برداری و قرنطین ادویه — برای هر دوا که نمونه برداری یا قرنطین می‌شود یک ردیف "
            "ثبت کنید. در صورتیکه موردی وجود ندارد، این بخش را خالی بگذارید.",
            "۶. د نمونو اخیستل او د درملو قرنطین — د هر درمل لپاره چې نمونه ترې اخیستل کېږي یا "
            "قرنطین کېږي یوه کرښه ثبت کړئ. که هیڅ مورد نه وي، دا برخه تشه پرېږدئ.",
            "6. Samples and quarantined medicines - record one row per medicine that is sampled "
            "or quarantined. Leave this section empty when there is nothing to record.",
        ),
    )
    add(
        "begin_repeat",
        "sample_items",
        "اقلام نمونه برداری / قرنطین شده",
        "نمونه اخیستل شوي / قرنطین شوي توکي",
        "Sampled / quarantined items",
        appearance="field-list",
    )
    add(
        "select_one sample_action",
        "sample_action",
        "نوع اقدام",
        "د اقدام ډول",
        "Action taken",
        required="yes",
    )
    add(
        "text",
        "sample_medicine_name",
        "نام دوا (جنریک و تجارتی)",
        "د درمل نوم (جنریک او سوداګریز)",
        "Medicine name (generic and trade)",
        required="yes",
    )
    add("text", "sample_batch", "شماره بچ", "د بچ شمېره", "Batch number")
    add("date", "sample_expiry_date", "تاریخ انقضا", "د پای نېټه", "Expiry date")
    add(
        "integer",
        "sample_quantity",
        "مقدار ثبت شده در فورم نمونه برداری / قرنطین",
        "په نمونه اخیستلو / قرنطین فورم کې ثبت شوی مقدار",
        "Quantity recorded in the sampling / quarantine form",
    )
    add(
        "text",
        "sample_unit",
        "واحد (تابلیت، شیشه، جعبه و غیره)",
        "واحد (ټابلیټ، شیشه، بکس او نور)",
        "Unit (tablet, bottle, box, ...)",
    )
    add(
        "text",
        "sample_seal",
        "شماره مهر و موم یا لیبل قرنطین",
        "د مهر او موم شمېره یا د قرنطین لیبل",
        "Seal or quarantine label number",
    )
    add(
        "text",
        "sample_reason",
        "دلیل نمونه برداری یا قرنطین",
        "د نمونې اخیستلو یا قرنطین دلیل",
        "Reason for sampling or quarantine",
        appearance="multiline",
        required="yes",
    )
    add(
        "image",
        "sample_photo",
        "عکس دوا، لیبل و تاریخ انقضا",
        "د درمل، لیبل او د پای نېټې عکس",
        "Photo of the medicine, label and expiry date",
        "لیبل و تاریخ انقضا واضح باشد.",
        "لیبل او د پای نېټه دې ښکاره وي.",
        "The label and expiry date must be clear.",
        appearance="new",
        parameters="max-pixels=1600",
    )
    add("end_repeat", "sample_items")
    group_end()

    # ------------------------------------------------ 8. inspectors and signs
    group_start(
        "inspectors",
        (
            "۷. کارمندان بازرسی کننده و امضاء",
            "۷. پلټونکي کارکوونکي او لاسلیک",
            "7. Inspecting employees and signatures",
        ),
        appearance="",
    )
    note(
        "inspectors_intro",
        (
            "۷. کارمندان بازرسی کننده و امضاء — اسم و امضای تمام کارمندانی که این بازرسی را "
            "انجام داده‌اند ثبت شود.",
            "۷. پلټونکي کارکوونکي او لاسلیک — د هغو ټولو کارکوونکو نوم او لاسلیک ثبت کړئ چې دا "
            "پلټنه یې کړې ده.",
            "7. Inspecting employees and signatures - record the name and signature of every "
            "employee who carried out this inspection.",
        ),
    )
    add(
        "begin_repeat",
        "inspector_items",
        "بازرسی کنندگان",
        "پلټونکي",
        "Inspectors",
        appearance="field-list",
    )
    add("text", "inspector_name", "اسم و تخلص", "نوم او تخلص", "Full name", required="yes")
    add(
        "image",
        "inspector_signature",
        "امضاء",
        "لاسلیک",
        "Signature",
        "با انگشت در کادر امضاء کنید.",
        "په لاسلیک کادر کې په ګوته لاسلیک وکړئ.",
        "Sign with a finger in the signature box.",
        required="yes",
        appearance="signature",
        parameters="max-pixels=1024",
    )
    add("end_repeat", "inspector_items")
    group_end()

    # --------------------------------------------------- 9. audit and closure
    group_start(
        "audit",
        (
            "۸. سابقه بازرسی (خودکار)",
            "۸. د پلټنې سابقه (اتوماتیک)",
            "8. Audit trail (automatic)",
        ),
    )
    note(
        "audit_intro",
        (
            "معلومات ذیل بطور خودکار توسط دستگاه ثبت می‌شود و قابل ویرایش نیست. "
            "تاریخ و زمان آغاز و ختم و مدت بازرسی بطور خودکار محاسبه می‌شود.",
            "لاندې معلومات د وسیلې له خوا اتوماتیک ثبت کېږي او د سمون وړ نه دي. "
            "د پیل او پای نېټه، وخت او د پلټنې موده اتوماتیک حساب کېږي.",
            "The values below are recorded automatically by the device and cannot be edited. "
            "The start/end date-time and the inspection duration are calculated automatically.",
        ),
    )
    add("calculate", "audit_user", calculation="${username}")
    note(
        "audit_user_note",
        ("کاربر ثبت کننده: ${audit_user}", "ثبت کوونکی کارن: ${audit_user}",
         "Recorded by user: ${audit_user}"),
        relevant="string-length(${audit_user}) > 0",
    )
    add("calculate", "audit_device", calculation="${deviceid}")
    note(
        "audit_device_note",
        ("شناسه وسیله: ${audit_device}", "د وسیلې پېژند: ${audit_device}",
         "Device ID: ${audit_device}"),
        relevant="string-length(${audit_device}) > 0",
    )
    add("calculate", "audit_started", calculation="${start}")
    note(
        "audit_started_note",
        ("زمان آغاز بازرسی: ${audit_started}", "د پلټنې د پیل وخت: ${audit_started}",
         "Inspection started at: ${audit_started}"),
    )
    add("calculate", "audit_start_point", calculation="${start_location}")
    note(
        "audit_start_point_note",
        ("نقطه خودکار آغاز: ${audit_start_point}", "د پیل اتوماتیک نقطه: ${audit_start_point}",
         "Automatic location at form start: ${audit_start_point}"),
        relevant="string-length(${audit_start_point}) > 0",
    )
    # Duration is never asked: it is the difference between the automatic end
    # and start timestamps (falling back to "now" while the form is still open).
    add(
        "calculate",
        "inspection_duration_minutes",
        "مدت بازرسی (دقیقه)",
        "د پلټنې موده (دقیقې)",
        "Inspection duration (minutes)",
        calculation=(
            "if(${end} = '', "
            "round((decimal-date-time(now()) - decimal-date-time(${start})) * 1440, 0), "
            "round((decimal-date-time(${end}) - decimal-date-time(${start})) * 1440, 0))"
        ),
    )
    note(
        "duration_note",
        (
            "مدت بازرسی: ${inspection_duration_minutes} دقیقه",
            "د پلټنې موده: ${inspection_duration_minutes} دقیقې",
            "Inspection duration: ${inspection_duration_minutes} minutes",
        ),
    )
    group_end()

    note(
        "thank_you",
        (
            "از مالک، مسئول فنی و کارمندان دواخانه که در این بازرسی همکاری نمودند تشکر نمائید.",
            "د درملتون له مالک، تخنیکي مسئول او کارکوونکو چې په دې پلټنه کې یې همکاري وکړه مننه وکړئ.",
            "Thank the owner, technical manager and staff for supporting this inspection.",
        ),
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


def build_workbook():
    workbook = Workbook()

    survey = workbook.active
    survey.title = "survey"
    for row in build_survey():
        survey.append(row)
    style_sheet(survey, [34, 30, 52, 46, 50, 42, 42, 44, 10, 12, 20, 16, 28, 52, 26])

    choices = workbook.create_sheet("choices")
    choices.append(CHOICE_HEADERS)
    for row in CHOICES:
        choices.append(row)
    style_sheet(choices, [20, 20, 40, 36, 40])

    settings = workbook.create_sheet("settings")
    for row in SETTINGS:
        settings.append(row)
    style_sheet(settings, [40, 30, 16, 20, 34])

    return workbook


def main():
    build_workbook().save(OUTPUT)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
