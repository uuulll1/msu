"""
Заполнение базы стартовыми данными.

    python manage.py seed_portal            # структура + демо-контент
    python manage.py seed_portal --no-demo  # только структура (факультет, специальности, предметы)

Команда идемпотентна: повторный запуск ничего не дублирует.
Чтобы добавить новый факультет, достаточно дописать словарь в FACULTIES.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.models import Faculty, Semester, Specialty, Subject
from forum.models import Post, Topic
from materials.models import Comment, Material, MaterialLike, Tag

# ---------------------------------------------------------------------------
# Учебная структура
# ---------------------------------------------------------------------------

# Предметы первого курса: slug → (название, семестры, описание)
MECHMAT_FIRST_YEAR = {
    "matematicheskiy-analiz": (
        "Математический анализ",
        [1, 2],
        "Теория пределов, непрерывность, дифференциальное и интегральное исчисление "
        "функций одной переменной, числовые и функциональные ряды.",
    ),
    "algebra": (
        "Алгебра",
        [1, 2],
        "Комплексные числа, многочлены, системы линейных уравнений, определители, "
        "группы, кольца и поля.",
    ),
    "analiticheskaya-geometriya": (
        "Аналитическая геометрия",
        [1],
        "Векторная алгебра, прямые и плоскости, кривые и поверхности второго порядка, "
        "аффинные преобразования.",
    ),
    "lineynaya-algebra-i-geometriya": (
        "Линейная алгебра и геометрия",
        [2],
        "Линейные пространства и отображения, жорданова форма, евклидовы и унитарные "
        "пространства, квадратичные формы.",
    ),
    "diskretnaya-matematika": (
        "Дискретная математика",
        [1, 2],
        "Комбинаторика, булевы функции, графы, элементы теории кодирования.",
    ),
    "vvedenie-v-matematicheskuyu-logiku": (
        "Введение в математическую логику",
        [2],
        "Логика высказываний и предикатов, формальные теории, теорема о полноте, "
        "элементы теории алгоритмов.",
    ),
    "programmirovanie": (
        "Практикум на ЭВМ",
        [1, 2],
        "Основы программирования, алгоритмы и структуры данных, практические задания.",
    ),
    "istoriya": (
        "История России",
        [1],
        "Общеобразовательный курс.",
    ),
    "inostrannyy-yazyk": (
        "Иностранный язык",
        [1, 2],
        "Английский язык для математиков и механиков: чтение научных текстов, грамматика.",
    ),
}

FACULTIES = [
    {
        "slug": "mechmat",
        "name": "Механико-математический факультет",
        "short_name": "Мехмат",
        "description": (
            "Один из крупнейших математических факультетов. На портале собраны студенческие "
            "материалы по математическим и механическим дисциплинам."
        ),
        "specialties": [
            {
                "slug": "matematika",
                "name": "Математика",
                "short_name": "Математика",
                "degree": Specialty.Degree.BACHELOR,
                "duration_years": 4,
                "description": (
                    "Фундаментальная подготовка по анализу, алгебре, геометрии, топологии, "
                    "дифференциальным уравнениям, теории вероятностей и математической логике."
                ),
            },
            {
                "slug": "mehanika",
                "name": "Механика",
                "short_name": "Механика",
                "degree": Specialty.Degree.BACHELOR,
                "duration_years": 4,
                "description": (
                    "Теоретическая механика, механика сплошных сред, гидро- и аэродинамика, "
                    "теория упругости и математическое моделирование."
                ),
            },
            {
                "slug": "fmimf",
                "name": "Фундаментальные математика и механика",
                "short_name": "ФМиМФ",
                "degree": Specialty.Degree.SPECIALIST,
                "duration_years": 6,
                "description": (
                    "Углублённая программа, объединяющая математическую и механическую "
                    "подготовку с ранней научной специализацией."
                ),
            },
        ],
        # Предметы первого курса одинаковы для всех трёх специальностей
        "first_year_subjects": MECHMAT_FIRST_YEAR,
    },
]

# ---------------------------------------------------------------------------
# Демонстрационный контент
# ---------------------------------------------------------------------------

DEMO_PASSWORD = "demo-password-2026"

DEMO_MATERIALS = [
    {
        "title": "Лекции по математическому анализу, 1 семестр",
        "subject": "matematicheskiy-analiz",
        "semester": 1,
        "type": Material.Type.LECTURES,
        "teacher": "Иванов И. И.",
        "tags": ["пределы", "непрерывность", "производная"],
        "file": ("matan-lectures-1.pdf", "pdf"),
        "downloads": 214,
        "description": (
            "Полный конспект лекций первого семестра.\n\n"
            "**Содержание:**\n\n"
            "1. Вещественные числа, аксиома полноты\n"
            "2. Предел последовательности, теорема Больцано — Вейерштрасса\n"
            "3. Предел и непрерывность функции\n"
            "4. Производная, формула Тейлора:\n\n"
            "$$f(x) = \\sum_{k=0}^{n} \\frac{f^{(k)}(x_0)}{k!}(x-x_0)^k + o\\big((x-x_0)^n\\big)$$"
        ),
    },
    {
        "title": "Билеты к экзамену по алгебре (зима)",
        "subject": "algebra",
        "semester": 1,
        "type": Material.Type.EXAM_TICKETS,
        "teacher": "Петрова А. С.",
        "tags": ["экзамен", "многочлены", "определители"],
        "file": ("algebra-tickets.md", "md"),
        "downloads": 167,
        "description": "Программа экзамена с краткими ответами. Формат Markdown — читается прямо на сайте.",
    },
    {
        "title": "Шпаргалка: кривые второго порядка",
        "subject": "analiticheskaya-geometriya",
        "semester": 1,
        "type": Material.Type.CHEATSHEET,
        "teacher": "Сидоров П. П.",
        "tags": ["кривые второго порядка", "коллоквиум"],
        "file": ("conics-cheatsheet.tex", "tex"),
        "downloads": 98,
        "description": "Канонические уравнения эллипса $\\frac{x^2}{a^2}+\\frac{y^2}{b^2}=1$, гиперболы и параболы. Исходник в LaTeX.",
    },
    {
        "title": "Задачи к семинарам по дискретной математике",
        "subject": "diskretnaya-matematika",
        "semester": 1,
        "type": Material.Type.PROBLEMS,
        "teacher": "Кузнецов В. В.",
        "tags": ["комбинаторика", "графы"],
        "file": ("discrete-problems.pdf", "pdf"),
        "downloads": 76,
        "description": "Подборка задач с семинаров: биномиальные коэффициенты $\\binom{n}{k}$, формула включений-исключений, деревья.",
    },
    {
        "title": "Разбор семинаров: линейные отображения",
        "subject": "lineynaya-algebra-i-geometriya",
        "semester": 2,
        "type": Material.Type.SEMINARS,
        "teacher": "Петрова А. С.",
        "tags": ["линейные отображения", "жорданова форма"],
        "file": ("linalg-seminars.md", "md"),
        "downloads": 53,
        "description": "Решения типовых задач: матрица оператора, ядро и образ, $\\dim V = \\dim\\ker\\varphi + \\dim\\operatorname{Im}\\varphi$.",
    },
    {
        "title": "Конспект: логика высказываний",
        "subject": "vvedenie-v-matematicheskuyu-logiku",
        "semester": 2,
        "type": Material.Type.LECTURES,
        "teacher": "Смирнов Д. А.",
        "tags": ["логика", "исчисление высказываний"],
        "file": ("logic-lectures.pdf", "pdf"),
        "downloads": 41,
        "description": "Синтаксис и семантика, теорема о дедукции, полнота исчисления высказываний.",
    },
    {
        "title": "Ряды: признаки сходимости (на проверке)",
        "subject": "matematicheskiy-analiz",
        "semester": 2,
        "type": Material.Type.CHEATSHEET,
        "teacher": "Иванов И. И.",
        "tags": ["ряды"],
        "file": ("series-tests.md", "md"),
        "downloads": 0,
        "status": Material.Status.PENDING,
        "description": "Пример материала, ожидающего модерации. Виден только автору и модераторам.",
    },
]

DEMO_TOPICS = [
    {
        "subject": "matematicheskiy-analiz",
        "title": "Как доказать, что $\\lim_{n\\to\\infty} \\sqrt[n]{n} = 1$?",
        "author": "student_anna",
        "pinned": False,
        "posts": [
            ("student_anna", "Никак не получается аккуратно доказать $\\lim\\limits_{n\\to\\infty} \\sqrt[n]{n} = 1$. Подскажите идею?"),
            (
                "student_boris",
                "Положите $\\sqrt[n]{n} = 1 + \\alpha_n$, $\\alpha_n \\ge 0$. По биному Ньютона\n\n"
                "$$n = (1+\\alpha_n)^n \\ge \\frac{n(n-1)}{2}\\alpha_n^2,$$\n\n"
                "откуда $0 \\le \\alpha_n \\le \\sqrt{\\frac{2}{n-1}} \\to 0$.",
            ),
            ("student_anna", "Спасибо, очень изящно!"),
        ],
    },
    {
        "subject": "algebra",
        "title": "Правила ветки и полезные ссылки",
        "author": "moderator",
        "pinned": True,
        "posts": [
            (
                "moderator",
                "Добро пожаловать в ветку по **алгебре**!\n\n"
                "- пишите формулы в LaTeX: `$x^2$` → $x^2$;\n"
                "- перед вопросом загляните в раздел материалов;\n"
                "- не публикуйте ответы к текущим контрольным.",
            ),
        ],
    },
    {
        "subject": "analiticheskaya-geometriya",
        "title": "Когда коллоквиум?",
        "author": "student_boris",
        "pinned": False,
        "posts": [
            ("student_boris", "Кто-нибудь знает дату коллоквиума в этом семестре?"),
            ("student_anna", "Говорили, что в конце октября, но лучше уточнить у семинариста."),
        ],
    },
]


# ---------------------------------------------------------------------------
# Генерация демо-файлов
# ---------------------------------------------------------------------------


def build_demo_pdf(title: str, lines: list[str]) -> bytes:
    """
    Собирает минимальный корректный одностраничный PDF без внешних библиотек.
    Используется стандартный шрифт Helvetica, поэтому текст — латиницей.
    """

    def esc(text):
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    stream_lines = ["BT", "/F1 22 Tf", "72 760 Td", f"({esc(title)}) Tj", "/F1 12 Tf", "0 -36 Td"]
    for line in lines:
        stream_lines.append(f"({esc(line)}) Tj")
        stream_lines.append("0 -18 Td")
    stream_lines.append("ET")
    stream = "\n".join(stream_lines).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_start = len(output)
    output += f"xref\n0 {len(objects) + 1}\n".encode()
    output += b"0000000000 65535 f \n"
    for offset in offsets:
        output += f"{offset:010d} 00000 n \n".encode()
    output += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode()
    )
    return bytes(output)


DEMO_TEXT_FILES = {
    "algebra-tickets.md": (
        "# Билеты к экзамену по алгебре\n\n"
        "## Билет 1\n\n"
        "1. Поле комплексных чисел. Формула Муавра: $(\\cos\\varphi + i\\sin\\varphi)^n = "
        "\\cos n\\varphi + i \\sin n\\varphi$.\n"
        "2. Задача: найти все корни уравнения $z^6 = -1$.\n\n"
        "## Билет 2\n\n"
        "1. Определитель: определение и свойства. Разложение по строке.\n"
        "2. Задача: вычислить определитель Вандермонда\n\n"
        "$$\\det\\big(x_i^{j-1}\\big)_{i,j=1}^n = \\prod_{1\\le i<j\\le n} (x_j - x_i).$$\n\n"
        "## Билет 3\n\n"
        "1. Кольцо многочленов. Алгоритм Евклида, НОД.\n"
        "2. Основная теорема алгебры (формулировка).\n"
    ),
    "linalg-seminars.md": (
        "# Семинары: линейные отображения\n\n"
        "**Задача 1.** Найти матрицу оператора дифференцирования $D$ в базисе "
        "$1, x, x^2, x^3$ пространства $\\mathbb{R}_3[x]$.\n\n"
        "*Решение.* $D(x^k) = k x^{k-1}$, поэтому\n\n"
        "$$[D] = \\begin{pmatrix} 0 & 1 & 0 & 0 \\\\ 0 & 0 & 2 & 0 \\\\ 0 & 0 & 0 & 3 \\\\ 0 & 0 & 0 & 0 \\end{pmatrix}.$$\n\n"
        "**Задача 2.** Доказать, что $\\operatorname{rk}(AB) \\le \\min(\\operatorname{rk}A, \\operatorname{rk}B)$.\n"
    ),
    "series-tests.md": (
        "# Признаки сходимости рядов\n\n"
        "- Признак Даламбера: $\\lim \\left|\\frac{a_{n+1}}{a_n}\\right| < 1$.\n"
        "- Радикальный признак Коши: $\\varlimsup \\sqrt[n]{|a_n|} < 1$.\n"
        "- Интегральный признак, признаки Лейбница, Абеля и Дирихле.\n"
    ),
    "conics-cheatsheet.tex": (
        "\\documentclass[a4paper,11pt]{article}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage[russian]{babel}\n"
        "\\usepackage{amsmath}\n"
        "\\begin{document}\n"
        "\\section*{Кривые второго порядка}\n"
        "\\begin{align*}\n"
        "  &\\text{Эллипс:}    && \\frac{x^2}{a^2} + \\frac{y^2}{b^2} = 1, \\quad e = \\frac{c}{a} < 1,\\\\\n"
        "  &\\text{Гипербола:} && \\frac{x^2}{a^2} - \\frac{y^2}{b^2} = 1, \\quad e > 1,\\\\\n"
        "  &\\text{Парабола:}  && y^2 = 2px, \\quad e = 1.\n"
        "\\end{align*}\n"
        "\\end{document}\n"
    ),
}

DEMO_PDF_CONTENT = {
    "matan-lectures-1.pdf": (
        "Mathematical Analysis - Lectures, Semester 1",
        [
            "Demo file generated by seed_portal.",
            "1. Real numbers and the completeness axiom.",
            "2. Limits of sequences. Bolzano-Weierstrass theorem.",
            "3. Limits and continuity of functions.",
            "4. Derivatives. Taylor formula.",
        ],
    ),
    "discrete-problems.pdf": (
        "Discrete Mathematics - Seminar Problems",
        [
            "Demo file generated by seed_portal.",
            "1. Prove that sum_k C(n,k) = 2^n.",
            "2. Count surjections from an n-set onto a k-set.",
            "3. Prove that a tree with n vertices has n-1 edges.",
        ],
    ),
    "logic-lectures.pdf": (
        "Introduction to Mathematical Logic",
        [
            "Demo file generated by seed_portal.",
            "1. Propositional formulas and truth tables.",
            "2. The deduction theorem.",
            "3. Completeness of propositional calculus.",
        ],
    ),
}


class Command(BaseCommand):
    help = "Заполняет базу: мехмат, три специальности, предметы 1 курса и демо-контент."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-demo",
            action="store_true",
            help="Не создавать демонстрационных пользователей, материалы и темы форума.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Учебная структура"))
        subjects = self.seed_structure()
        self.seed_moderators_group()

        if options["no_demo"]:
            self.stdout.write(self.style.SUCCESS("Готово (без демо-контента)."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("Демонстрационный контент"))
        users = self.seed_users()
        self.seed_materials(subjects, users)
        self.seed_forum(subjects, users)
        self.stdout.write(self.style.SUCCESS("Готово!"))
        self.stdout.write(
            f"Демо-пользователи: student_anna, student_boris, moderator (пароль: {DEMO_PASSWORD})"
        )

    # --- Структура ---

    def seed_structure(self):
        subjects = {}
        for order, data in enumerate(FACULTIES):
            faculty, created = Faculty.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "short_name": data["short_name"],
                    "description": data["description"],
                    "order": order,
                },
            )
            self._report(faculty, created)

            # Предметы факультета
            for slug, (name, _, description) in data["first_year_subjects"].items():
                subject, created = Subject.objects.update_or_create(
                    faculty=faculty, slug=slug, defaults={"name": name, "description": description}
                )
                subjects[slug] = subject
                if created:
                    self.stdout.write(f"  + предмет: {name}")

            for spec_order, spec in enumerate(data["specialties"]):
                specialty, created = Specialty.objects.update_or_create(
                    faculty=faculty,
                    slug=spec["slug"],
                    defaults={
                        "name": spec["name"],
                        "short_name": spec["short_name"],
                        "degree": spec["degree"],
                        "duration_years": spec["duration_years"],
                        "description": spec["description"],
                        "order": spec_order,
                    },
                )
                self._report(specialty, created)
                specialty.ensure_structure()

                # Привязываем предметы первого курса к семестрам 1 и 2
                for slug, (_, semester_numbers, _) in data["first_year_subjects"].items():
                    for number in semester_numbers:
                        semester = Semester.objects.get(course__specialty=specialty, number=number)
                        semester.subjects.add(subjects[slug])
        return subjects

    def seed_moderators_group(self):
        group, _ = Group.objects.get_or_create(name="Модераторы")
        codenames = [
            "view_material", "change_material", "delete_material",
            "view_comment", "change_comment", "delete_comment",
            "view_tag", "add_tag", "change_tag",
            "view_topic", "change_topic", "delete_topic",
            "view_post", "change_post", "delete_post",
            "view_subject", "view_semester",
        ]
        permissions = Permission.objects.filter(codename__in=codenames)
        group.permissions.set(permissions)
        self.stdout.write(f"  группа «Модераторы»: {permissions.count()} прав")
        return group

    # --- Демо ---

    def seed_users(self):
        User = get_user_model()
        mechmat = Faculty.objects.get(slug="mechmat")
        math = Specialty.objects.get(faculty=mechmat, slug="matematika")
        mech = Specialty.objects.get(faculty=mechmat, slug="mehanika")
        specs = {
            "student_anna": ("Анна", "Королёва", math, 1),
            "student_boris": ("Борис", "Лебедев", mech, 1),
            "moderator": ("Модератор", "", None, None),
        }
        users = {}
        for username, (first, last, specialty, year) in specs.items():
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "first_name": first,
                    "last_name": last,
                    "specialty": specialty,
                    "study_year": year,
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                if username == "moderator":
                    user.is_staff = True  # доступ в админку для модерации
                user.save()
                if username == "moderator":
                    user.groups.add(Group.objects.get(name="Модераторы"))
            users[username] = user
            self._report(user, created)
        return users

    def seed_materials(self, subjects, users):
        mechmat_math = Specialty.objects.get(faculty__slug="mechmat", slug="matematika")
        now = timezone.now()
        for index, data in enumerate(DEMO_MATERIALS):
            if Material.objects.filter(title=data["title"]).exists():
                continue
            filename, kind = data["file"]
            if kind == "pdf":
                title, lines = DEMO_PDF_CONTENT[filename]
                content = build_demo_pdf(title, lines)
            else:
                content = DEMO_TEXT_FILES[filename].encode("utf-8")

            author = users["student_anna"] if index % 2 == 0 else users["student_boris"]
            status = data.get("status", Material.Status.APPROVED)
            material = Material(
                title=data["title"],
                subject=subjects[data["subject"]],
                semester=Semester.objects.get(course__specialty=mechmat_math, number=data["semester"]),
                material_type=data["type"],
                teacher=data["teacher"],
                academic_year="2025/2026",
                description=data["description"],
                author=author,
                status=status,
                downloads_count=data["downloads"],
                original_filename=filename,
                created_at=now - timedelta(days=len(DEMO_MATERIALS) - index),
            )
            if status == Material.Status.APPROVED:
                material.moderated_by = users["moderator"]
                material.moderated_at = now
            material.file.save(filename, ContentFile(content), save=False)
            material.save()
            material.tags.set([Tag.objects.get_or_create(name=name)[0] for name in data["tags"]])
            self.stdout.write(f"  + материал: {material.title}")

            if status == Material.Status.APPROVED and index < 3:
                MaterialLike.objects.get_or_create(material=material, user=users["student_boris"])
                MaterialLike.objects.get_or_create(material=material, user=users["moderator"])
                Comment.objects.create(
                    material=material,
                    author=users["student_boris"] if author != users["student_boris"] else users["student_anna"],
                    body="Спасибо! Особенно помог разбор с формулой $\\varepsilon$–$\\delta$.",
                )

    def seed_forum(self, subjects, users):
        now = timezone.now()
        for index, data in enumerate(DEMO_TOPICS):
            if Topic.objects.filter(title=data["title"]).exists():
                continue
            started = now - timedelta(days=3 - index, hours=5)
            topic = Topic.objects.create(
                subject=subjects[data["subject"]],
                title=data["title"],
                author=users[data["author"]],
                is_pinned=data["pinned"],
                created_at=started,
                views_count=20 + index * 7,
            )
            moment = started
            for author, body in data["posts"]:
                Post.objects.create(topic=topic, author=users[author], body=body, created_at=moment)
                moment += timedelta(hours=2)
            topic.last_activity_at = moment
            topic.save(update_fields=["last_activity_at"])
            self.stdout.write(f"  + тема: {topic.title}")

    def _report(self, obj, created):
        mark = "+" if created else "·"
        self.stdout.write(f"  {mark} {obj._meta.verbose_name}: {obj}")
