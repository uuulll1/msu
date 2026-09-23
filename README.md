# Конспектариум — неофициальный студенческий портал МГУ

Площадка для обмена конспектами и учебными материалами с форумом.
На старте — механико-математический факультет и три специальности:
«Математика», «Механика», «Фундаментальные математика и механика» (ФМиМФ).

> **Неофициальный студенческий ресурс. Не является сайтом МГУ.**
> Проект не использует герб, логотип и другую официальную символику университета.

## Возможности

- Иерархия **Факультет → Специальность → Курс → Семестр → Предмет → Материалы**.
- Материалы: название, предмет, преподаватель, семестр, тип (конспект лекций, семинары,
  билеты, шпаргалка, задачи), файл, описание, автор, дата, счётчик скачиваний, теги.
- Встроенный просмотр прямо на странице: PDF во фрейме, изображения, Markdown (с формулами), TeX (исходник).
- Форум: у каждого предмета своя ветка; темы, ответы, цитирование, «в ответ на», предпросмотр, LaTeX.
- Лайки и комментарии к материалам.
- Регистрация, вход, профиль со списком загрузок (у владельца — со статусами модерации).
- Поиск по названию, предмету, преподавателю и тегам с фильтрами (факультет, специальность,
  предмет, тип, семестр, тег) и сортировкой.
- Модерация: новые материалы получают статус «На проверке», модераторы одобряют их в Django admin
  (массовые действия «Одобрить / Отклонить / Вернуть на проверку»).
- Markdown + LaTeX (KaTeX) в описаниях, комментариях и постах, безопасный рендер.
- Тёмная и светлая тема (системная + переключатель), адаптивная вёрстка, бургер-меню.

## Стек

| Компонент | Выбор |
|---|---|
| Backend | Django 5.2 LTS (Python 3.11+) |
| БД | SQLite в разработке, PostgreSQL в продакшене (через `DATABASE_URL`) |
| Шаблоны | Django templates + чистый CSS (CSS-переменные), ~100 строк JS |
| Формулы | KaTeX 0.18 (лежит в `static/vendor/katex`, без CDN) |
| Markdown | Python-Markdown + очистка HTML через `nh3` |
| Статика | WhiteNoise |
| Продакшен | gunicorn (+ nginx на VPS) |

## Структура проекта

```
msu/
├── manage.py
├── requirements.txt
├── .env.example                 # пример переменных окружения
├── build.sh                     # сборка для Render
├── render.yaml                  # Blueprint для Render
├── deploy/                      # примеры nginx и systemd для VPS
├── config/                      # настройки проекта
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py / asgi.py
├── core/                        # главная, «О проекте», Markdown, общие утилиты
│   ├── markdown.py              # безопасный рендер Markdown + LaTeX
│   ├── middleware.py            # Content-Security-Policy и др. заголовки
│   ├── context_processors.py
│   ├── utils.py                 # транслитерация slug, нормализация поиска
│   ├── templatetags/            # |markdown, |filesize, |plural_ru, query_transform
│   └── management/commands/seed_portal.py   # стартовые данные
├── catalog/                     # факультеты, специальности, курсы, семестры, предметы
├── materials/                   # материалы, теги, лайки, комментарии, модерация
│   ├── validators.py            # проверка типа/размера/содержимого файлов
│   └── signals.py               # поисковый индекс, удаление файлов
├── forum/                       # темы и сообщения
├── accounts/                    # пользователь, регистрация, профиль
├── templates/                   # все шаблоны (base, partials, по приложениям, errors)
└── static/
    ├── css/main.css             # дизайн-система, темы, адаптив
    ├── js/theme-init.js, main.js
    ├── img/favicon.svg
    └── vendor/katex/
```

## Схема моделей

```
catalog.Faculty (name, short_name, slug, description, order, is_active)
  └─< catalog.Specialty (faculty FK, name, short_name, slug, code, degree,
  │                      duration_years, description, order, is_active)
  │     └─< catalog.Course (specialty FK, number)            ← «курс» = год обучения
  │           └─< catalog.Semester (course FK, number) >─< catalog.Subject  (M2M «subjects»)
  └─< catalog.Subject (faculty FK, name, slug, description, is_active)
        ├─< materials.Material (title, subject FK, semester FK?, teacher, material_type,
        │     │                 academic_year, description, file, original_filename,
        │     │                 file_size, tags M2M, author FK, created_at, updated_at,
        │     │                 downloads_count, status, moderation_note,
        │     │                 moderated_by FK, moderated_at, search_text)
        │     ├─< materials.MaterialLike (material FK, user FK)  unique(material, user)
        │     ├─< materials.Comment (material FK, author FK, body, created_at, is_hidden)
        │     └>─< materials.Tag (name, slug)
        └─< forum.Topic (subject FK, title, author FK, created_at, last_activity_at,
              │          is_pinned, is_locked, views_count)
              └─< forum.Post (topic FK, author FK, body, reply_to FK→Post,
                              created_at, updated_at, is_edited, is_hidden)

accounts.User (AbstractUser + email unique, bio, specialty FK?, study_year)
```

Ключевые решения:

- **Предмет принадлежит факультету**, а с семестрами связан «многие-ко-многим». Матанализ
  читается у всех трёх специальностей, но материалы и ветка форума у него общие.
- **Ветка форума = предмет**: отдельной модели раздела нет, новый предмет автоматически получает форум.
- **Новый факультет — это данные, а не код.** Добавьте факультет, специальность и предметы в админке
  (у специальности есть действие «Создать курсы и семестры по сроку обучения») или допишите словарь
  в `FACULTIES` в `seed_portal.py`. URL-адреса строятся из slug'ов: `/f/<факультет>/<специальность>/<курс>/<семестр>/`.

## Безопасность

- **XSS.** Markdown рендерится на сервере, затем HTML очищается `nh3` по белому списку тегов и
  атрибутов (разрешены только `http/https/mailto`-ссылки, классы — только служебные). Формулы
  вырезаются до Markdown и возвращаются экранированными. Дополнительно — заголовок
  `Content-Security-Policy` без `unsafe-inline` для скриптов, KaTeX запускается с `trust: false`.
- **CSRF.** Все изменяющие действия — только POST с `{% csrf_token %}` (включая выход и лайки).
- **Файлы.** Разрешены `.pdf .tex .md .png .jpg .jpeg .gif .webp` до 50 МБ. Проверяется содержимое:
  сигнатура PDF, открытие изображения через Pillow с совпадением формата, UTF-8 и отсутствие
  двоичных данных у текстовых файлов. SVG и HTML запрещены. Файлы хранятся под случайными именами
  и **не раздаются напрямую** — только через представления с проверкой статуса модерации;
  `.tex/.md` отдаются как `text/plain`, везде `X-Content-Type-Options: nosniff`.
- **Кликджекинг.** `X-Frame-Options: DENY` для всего сайта, кроме просмотра PDF (`SAMEORIGIN`).

## Локальный запуск

Требуется Python 3.11+.

```bash
git clone <адрес репозитория> msu-portal
cd msu-portal

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # DJANGO_DEBUG=True уже указан

python manage.py migrate
python manage.py seed_portal       # мехмат, специальности, предметы, демо-контент
python manage.py createsuperuser   # ваш администратор

python manage.py runserver
```

Откройте http://127.0.0.1:8000. Админ-панель: http://127.0.0.1:8000/admin/.

Демо-пользователи (создаёт `seed_portal`, пароль `demo-password-2026`):

| Логин | Роль |
|---|---|
| `student_anna`, `student_boris` | студенты |
| `moderator` | модератор (группа «Модераторы», доступ в админку) |

Только структура, без демо-контента: `python manage.py seed_portal --no-demo`.

Тесты: `python manage.py test`.

## Модерация

1. Пользователь загружает материал → статус «На проверке». Материал виден только автору и модераторам.
2. Модератор открывает «Очередь модерации» в меню пользователя или
   `/admin/materials/material/?status=pending`, отмечает материалы и выбирает действие
   «Одобрить» или «Отклонить» (можно оставить «комментарий модератора» — его увидит автор).
3. Если автор редактирует опубликованный материал, он снова уходит на проверку.

Чтобы сделать пользователя модератором: в админке включите «Статус персонала» и добавьте его
в группу «Модераторы» (группу с правами создаёт `seed_portal`). Загрузки модераторов публикуются сразу.

## Переход на PostgreSQL

```bash
pip install -r requirements.txt    # psycopg уже в списке
# в .env:
DATABASE_URL=postgres://user:password@localhost:5432/msu_portal
python manage.py migrate
python manage.py seed_portal --no-demo
```

Перенос данных из SQLite: `python manage.py dumpdata --natural-foreign --exclude contenttypes
--exclude auth.permission > data.json`, затем на новой БД `python manage.py loaddata data.json`
(и скопируйте каталог `media/`).

## Деплой на Render

1. Загрузите репозиторий на GitHub.
2. В Render: **New → Blueprint**, выберите репозиторий. `render.yaml` создаст PostgreSQL,
   веб-сервис и постоянный диск `/var/data` для загруженных файлов (диск есть только на платных планах;
   на бесплатном плане загруженные файлы пропадут при перезапуске).
3. `DJANGO_SECRET_KEY` генерируется автоматически, адрес `*.onrender.com` добавляется
   в `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` сам. Для своего домена задайте
   `DJANGO_ALLOWED_HOSTS=portal.example.com` и `DJANGO_CSRF_TRUSTED_ORIGINS=https://portal.example.com`.
4. После первого деплоя откройте **Shell** сервиса и выполните `python manage.py createsuperuser`.

## Деплой на VPS (Ubuntu + nginx + gunicorn)

```bash
sudo apt install python3-venv python3-pip postgresql nginx
sudo -u postgres createuser -P msu_portal
sudo -u postgres createdb -O msu_portal msu_portal

sudo mkdir -p /srv/msu-portal && sudo chown $USER /srv/msu-portal
git clone <адрес репозитория> /srv/msu-portal && cd /srv/msu-portal
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

cat > .env <<'ENV'
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<длинная случайная строка>
DJANGO_ALLOWED_HOSTS=example.com,www.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
DATABASE_URL=postgres://msu_portal:<пароль>@localhost:5432/msu_portal
DJANGO_MEDIA_ROOT=/srv/msu-portal/media
ENV

.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --no-input
.venv/bin/python manage.py seed_portal --no-demo
.venv/bin/python manage.py createsuperuser
sudo chown -R www-data:www-data /srv/msu-portal/media

sudo cp deploy/msu-portal.service /etc/systemd/system/
sudo systemctl enable --now msu-portal
sudo cp deploy/nginx.conf /etc/nginx/sites-available/msu-portal   # поправьте server_name
sudo ln -s /etc/nginx/sites-available/msu-portal /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo apt install certbot python3-certbot-nginx && sudo certbot --nginx -d example.com -d www.example.com
```

Обновление: `git pull && .venv/bin/pip install -r requirements.txt && .venv/bin/python manage.py migrate
&& .venv/bin/python manage.py collectstatic --no-input && sudo systemctl restart msu-portal`.

Ключ для `DJANGO_SECRET_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(50))"`.

После настройки HTTPS можно увеличить `DJANGO_HSTS_SECONDS` (например, до `31536000`).

## Переменные окружения

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `DJANGO_DEBUG` | режим отладки | `False` |
| `DJANGO_SECRET_KEY` | секретный ключ (обязателен при `DEBUG=False`) | — |
| `DJANGO_ALLOWED_HOSTS` | домены через запятую | `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | источники с протоколом | — |
| `DATABASE_URL` | строка подключения к БД | SQLite `db.sqlite3` |
| `DJANGO_MEDIA_ROOT` | каталог загруженных файлов | `./media` |
| `DJANGO_SECURE_SSL_REDIRECT` | редирект на HTTPS | `True` при `DEBUG=False` |
| `DJANGO_HSTS_SECONDS` | срок HSTS | `3600` |
| `DJANGO_DISABLE_CSP` | отключить CSP (для отладки) | `False` |
