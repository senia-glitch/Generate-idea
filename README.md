# reqpipe — конвейер «сырая идея → функциональные требования»

Рабочий прототип системы по эталонной схеме [`requirements-pipeline.html`](requirements-pipeline.html):
сырая идея проходит исследование, стратегию, формализацию и каскад проверок качества и превращается в
формализованный, согласованный и полный набор функциональных требований (SRS) для системы, превосходящей
конкурентов. Этапы выполняют AI-агенты **Claude Code** и **OpenCode**; LLM по умолчанию не выбраны —
используется модель, настроенная в самом агенте.

## Что работает из коробки, а что нужно сделать руками

| | |
|---|---|
| ✅ Само | Пакет ставится одной командой в любое окружение Python 3.11+; команда `reqpipe`, демо без LLM |
| ✅ Само | После `reqpipe install-skills --global` оба агента видят скиллы в любой папке и вызывают пакет из вашего виртуального окружения без его активации |
| ✋ Руками | Скиллы не ставятся при `pip install` — pip не пишет в профиль агентов. Нужен один шаг: [шаг 6](#шаг-6-подключить-скиллы-к-агентам) |
| ✋ Руками | Агенты (Claude Code или OpenCode) устанавливаются и авторизуются отдельно: [шаг 5](#шаг-5-установить-и-авторизовать-агента) |
| ✋ Руками | Тест с реальными пользователями (этап 5.5) — внешний: результаты сессий присылаете вы |

---

## Установка с нуля — по шагам

Пример ниже ставит пакет в **пустое виртуальное окружение в отдельной папке на рабочем столе**
(`reqpipe-env`), а работа с идеей идёт в другой папке (`my-idea`). Команды для Windows — в PowerShell,
для macOS и Linux — в терминале.

### Шаг 1. Проверить Python 3.11 или новее

Windows (PowerShell):

```powershell
python --version
```

macOS / Linux:

```bash
python3 --version
```

Если Python нет или версия ниже 3.11 — установите с [python.org](https://www.python.org/downloads/).
На Windows в установщике отметьте **Add python.exe to PATH**.

### Шаг 2. Создать папку на рабочем столе и пустое виртуальное окружение

Windows (PowerShell; путь к рабочему столу берётся из системы, в том числе если он в OneDrive):

```powershell
$desk = [Environment]::GetFolderPath('Desktop')
New-Item -ItemType Directory -Force "$desk\reqpipe-env" | Out-Null
Set-Location "$desk\reqpipe-env"
python -m venv .venv
```

macOS / Linux:

```bash
mkdir -p ~/Desktop/reqpipe-env && cd ~/Desktop/reqpipe-env
python3 -m venv .venv
```

Окружение `.venv` пустое и изолированное. Активировать его не нужно: дальше всё вызывается через Python
этого окружения по полному пути.

### Шаг 3. Установить пакет с GitHub в это окружение

Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install https://github.com/senia-glitch/Generate-idea/archive/refs/heads/main.zip
```

macOS / Linux:

```bash
.venv/bin/python -m pip install https://github.com/senia-glitch/Generate-idea/archive/refs/heads/main.zip
```

Git для этого не нужен. Если Git есть, можно и так: `… -m pip install git+https://github.com/senia-glitch/Generate-idea.git`.

### Шаг 4. Проверить установку

Windows:

```powershell
.\.venv\Scripts\reqpipe.exe doctor
```

macOS / Linux:

```bash
.venv/bin/reqpipe doctor
```

`doctor` покажет версию, как вызывается эта установка, найдены ли агенты `claude` и `opencode` и
установлены ли скиллы. Агентов и скиллов пока может не быть — это шаги 5 и 6.

### Шаг 5. Установить и авторизовать агента

Достаточно одного агента; можно оба.

**Claude Code** — установка (подробнее: [code.claude.com/docs/en/setup](https://code.claude.com/docs/en/setup);
на Windows желательно поставить и [Git for Windows](https://git-scm.com/download/win) — тогда агент работает
через Bash, иначе через PowerShell):

Windows (PowerShell):

```powershell
irm https://claude.ai/install.ps1 | iex
```

macOS / Linux:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Затем один раз запустите `claude` и войдите в аккаунт.

**OpenCode** — установка (подробнее: [opencode.ai/docs](https://opencode.ai/docs)); нужен Node.js:

```bash
npm install -g opencode-ai
```

Затем подключите провайдера модели:

```bash
opencode auth login
```

### Шаг 6. Подключить скиллы к агентам

Windows:

```powershell
.\.venv\Scripts\reqpipe.exe install-skills --global
```

macOS / Linux:

```bash
.venv/bin/reqpipe install-skills --global
```

Команда кладёт скиллы `reqpipe-pipeline` (ведёт конвейер) и `reqpipe-stage` (выполняет один этап):

* для Claude Code — в `~/.claude/skills/`;
* для OpenCode — в `~/.config/opencode/skills/` (у OpenCode эта папка приоритетнее `~/.claude/skills`,
  поэтому каждый агент получает свою версию).

В скиллы записывается точный вызов этой установки — `"<путь>/.venv/…/python" -m reqpipe`, — поэтому агент
найдёт пакет в любой папке, даже если окружение не активировано. Если вы переместите или пересоздадите
`reqpipe-env`, повторите этот шаг. Если агент уже был открыт — перезапустите его.

Скиллы только для одного проекта вместо всего профиля: `install-skills --dest <папка проекта>`.

### Шаг 7. Создать папку для идеи и запустить агента

Windows:

```powershell
New-Item -ItemType Directory -Force "$desk\my-idea" | Out-Null
Set-Location "$desk\my-idea"
claude
```

macOS / Linux:

```bash
mkdir -p ~/Desktop/my-idea && cd ~/Desktop/my-idea && claude
```

Вместо `claude` можно запустить `opencode`. Напишите агенту:

> Запусти конвейер требований для идеи: сервис записи к врачу без звонков

Агент сам подхватит скилл `reqpipe-pipeline` (явно: `/reqpipe-pipeline` в Claude Code, `@reqpipe-pipeline`
в OpenCode), создаст рабочую область `my-idea\.reqpipe`, будет выполнять этапы и спрашивать вас на
контрольных точках. Claude Code при первых командах `reqpipe` попросит разрешение — выберите «разрешать
всегда» для них. Результат — `my-idea\.reqpipe\output\SRS.md`.

### Шаг 8 (вариант). Пакет сам вызывает агентов — без диалога

Каждый этап запускается отдельной неинтерактивной сессией агента; на контрольных точках `run` спрашивает
вас в терминале.

Windows:

```powershell
$rp = "$desk\reqpipe-env\.venv\Scripts\reqpipe.exe"
Set-Location "$desk\my-idea"
& $rp init --idea-text "Сервис записи к врачу без звонков" --executor claude-code
& $rp run
```

macOS / Linux:

```bash
cd ~/Desktop/my-idea
~/Desktop/reqpipe-env/.venv/bin/reqpipe init --idea-text "Сервис записи к врачу без звонков" --executor claude-code
~/Desktop/reqpipe-env/.venv/bin/reqpipe run
```

С OpenCode — `--executor opencode` (в OpenCode должна быть выбрана модель по умолчанию, либо укажите
`model` в `.reqpipe/reqpipe.toml`). Коды выхода `run`: 0 — готово, 3 — ждём решения человека, 1 — ошибка.

### Шаг 9 (по желанию). Проверить всю цепочку без LLM

Mock-исполнитель отвечает эталонными данными: весь конвейер проходит за секунды, бесплатно.

Windows:

```powershell
Set-Location "$desk\reqpipe-env"
.\.venv\Scripts\reqpipe.exe init -w demo --idea-text "Тест" --executor mock --autonomous
.\.venv\Scripts\reqpipe.exe run -w demo
```

macOS / Linux:

```bash
cd ~/Desktop/reqpipe-env
.venv/bin/reqpipe init -w demo --idea-text "Тест" --executor mock --autonomous
.venv/bin/reqpipe run -w demo
```

### Обновление

Windows:

```powershell
Set-Location "$desk\reqpipe-env"
.\.venv\Scripts\python.exe -m pip install --upgrade --force-reinstall https://github.com/senia-glitch/Generate-idea/archive/refs/heads/main.zip
.\.venv\Scripts\reqpipe.exe install-skills --global
```

macOS / Linux:

```bash
cd ~/Desktop/reqpipe-env
.venv/bin/python -m pip install --upgrade --force-reinstall https://github.com/senia-glitch/Generate-idea/archive/refs/heads/main.zip
.venv/bin/reqpipe install-skills --global
```

### Удаление

Удалите папку `reqpipe-env` и папки скиллов `reqpipe-pipeline`, `reqpipe-stage` из `~/.claude/skills/`
и `~/.config/opencode/skills/`.

---

## Правила архитектуры

| Схема | Система |
|---|---|
| Дорожка (фаза) | **Домен** — пакет `reqpipe/domains/<домен>/` |
| Карточка | **Элемент** — модуль домена, объект `Element` |
| Стрелка | **Контракт** — `Consumes(источник, тип артефакта, поля)` у элемента-потребителя |
| Пунктир-возврат | **Петля** — `Loop(адресат, метка)` у фильтра |

* Связь между элементами существует **только** как контракт; реестр проверяет, что тип артефакта в
  контракте совпадает с выходом источника, а граф прямых контрактов ацикличен.
* Домен импортирует из другого домена **только** его `contracts.py` — проверяется тестом.
* Эталон `requirements-pipeline.html` **не изменяется** (SHA-256 зафиксирован в `reqpipe/reference.py`).
  `reqpipe check-reference` и тест `tests/test_reference.py` сверяют: 32 карточки = 32 элемента,
  9 дорожек = 9 доменов, 33 стрелки = 33 контракта, все 6 петель схемы реализованы.

| Фаза | Домен | Элементы |
|---|---|---|
| Вход | `intake` | 0 сырая идея |
| 1 | `clarification` | 1.1 интервью · 1.2 постановка проблемы |
| 2 | `research` | 2.1 конкуренты · 2.2 голос пользователя · 2.3 предметная область · 2.4 регуляторика · 2.5 G0 верификация фактов |
| 3 | `strategy` | 3.1 gap-анализ · 3.2 ценностное предложение и критерии превосходства · 3.3 персоны |
| 4 | `formalization` | 4.1 Story Map · 4.2 модель данных · 4.3 требования · 4.4 критерии приёмки · 4.5 автотесты |
| 5 | `quality` | G1 линтер · G2 красная команда · G3 полнота · G4 симуляция · G5 тест с людьми · G6 бенчмарк |
| 6 | `agreement` | 6.1 реализуемость · 6.2 приоритизация · 6.3 дебаты · 6.4 baseline |
| Выход | `result` | ✓ сборка SRS |
| Сквозной слой | `platform` | оркестратор · менеджер контекста · база знаний · граф трассируемости · контрольные точки |

## Настройки (`.reqpipe/reqpipe.toml`)

* `executor` — `manual` (ведёт агент) · `claude-code` · `opencode` · `mock`.
* Модель: пусто — модель по умолчанию в агенте. Задать: `[executor."claude-code"] model = "opus"`,
  `[executor.opencode] model = "provider/model"`.
* Этап на другом агенте (например, независимый критик G2): `[elements.critic]` → `executor = "opencode"`.
* `autonomous = true` (или `reqpipe autonomy on`) — решения на контрольных точках принимает агент-арбитр:
  по правилам (`arbiter = "rules"`) или агентом (`arbiter = "executor"`); решения с уверенностью ниже
  `arbiter_min_confidence` попадают в SRS как «просмотреть людям».
* `max_loop_iterations` — бюджет возвратов на каждую петлю; исчерпан — решает человек или арбитр.
* `parallel = 4` — четыре агента фазы 2 работают одновременно.
* `context_budget_chars` — бюджет пакета контекста; больше — менеджер контекста сокращает и оставляет
  ссылки на полные артефакты.

### Тест с реальными пользователями (G5)

Агент собирает кликабельный прототип (`output/prototype/index.html`) и план; результаты сессий приходят
извне: `reqpipe submit-external usertest results.json` (схема — `reqpipe schema usertest --external`) или
командой сервиса немодерируемого тестирования `user_test_command = "my_panel {plan} {out}"`. Пропуск —
только явным решением `reqpipe waive usertest --reason "…"`, это отметка в SRS. Арбитру пропускать тест
запрещено, пока не включено `allow_waive_user_test`.

## Рабочая область

```
.reqpipe/
  reqpipe.toml  idea.md  state.json  decisions.jsonl
  tasks/<этап>.vN.md     задача агенту: карточка схемы + пакет контекста + схема ответа
  schemas/<этап>.json    JSON-схема ответа (контракт)
  results/<этап>.json    сюда агент пишет ответ в режиме manual
  artifacts/<этап>.vN.json  версии артефактов
  logs/                  сырые ответы агентов
  output/  SRS.md  requirements.json  spec.json  trace.json  tests/  prototype/
```

## Команды

`init` · `status` · `next` · `submit` · `submit-external` · `approve` · `reject` · `waive` · `rerun` ·
`run` · `autonomy on|off` · `spec` (домены, контракты, петли) · `schema <этап>` · `check-reference` ·
`install-skills [--global]` · `doctor`. Все поддерживают `-w <папка>` и `--json`.

## Доработки требований относительно схемы

* Возврат из G0 уходит тому исследовательскому агенту, чей факт не подтвердился (на схеме нарисована петля
  к 2.1; к 2.2–2.4 — уточнения). Также добавлены возвраты G2, G4, G5 и G3 → 4.3 — так, как описано в текстах
  карточек («уходит на доработку»).
* Данные идут строго по стрелкам: начиная с 4.5 по цепочке передаётся пакет спецификации `SpecBundle`
  (требования, сценарии, тесты, каталог ID для трассировки, журнал фильтров, риски, решения).
* Каждый фильтр сочетает вердикт агента с детерминированными проверками: G1 — словарь размытых слов, EARS,
  атомарность; G3 — трассировка ID (боли ≥ 4, обязательства, истории, сущности, сценарии, тесты);
  G6 — взвешенная оценка по критериям из 3.2 и паритет по базовым функциям рынка.
* Агент возвращает только то, что требует мышления; сборка артефактов (каталоги, Opportunity Score, RICE,
  условия выпуска baseline, SRS) — детерминированная.

## Ограничения прототипа

* Вход — только текст (распознавание речи не подключено).
* База знаний — файловое хранилище версий; векторного поиска нет, менеджер контекста сжимает
  детерминированно, без LLM-суммаризации.
* В режиме `run` интервью 1.1 не может спросить автора: открытые вопросы показываются на контрольной точке,
  ответы передаются через `reqpipe reject clarify --comment "ответы…"`. Настоящий диалог — в режиме,
  когда конвейер ведёт агент (шаг 7).
* В Claude Code каждая неинтерактивная сессия несёт накладные расходы на системный промпт (порядка $0,3 на
  первый вызов без кеша) — учитывайте это сверх оценки калькулятора на схеме.

## Разработка

```bash
git clone https://github.com/senia-glitch/Generate-idea.git
cd Generate-idea
python -m pip install -e ".[dev]"
reqpipe install-skills --dest .
python -m pytest
reqpipe check-reference
```
