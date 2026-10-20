# Система управления задачами (Todo-лист)

Учебный проект на Python с использованием ООП: пользователи создают проекты,
добавляют в них задачи, меняют статусы, ищут задачи, строят отчёты
и получают уведомления о просрочках.

- `architecture.md` — описание архитектуры (классы, атрибуты, методы, взаимодействие).
- `main.py` — полный код программы и пример её работы.

## Как запустить

```bash
python main.py
```

В конце файла находится демонстрация: создаются пользователи, проект и задачи,
меняются статусы, выполняются поиск, отчёт и проверка просрочек.

---

## Какие классы используются

| Класс | Назначение |
|-------|-----------|
| `Task` | отдельная задача: хранит данные и меняет своё состояние |
| `Project` | проект: список задач и участников, жизненный цикл задач |
| `User` | пользователь: профиль, свои проекты, настройки |
| `TodoManager` | центральный менеджер: создаёт объекты, хранит все коллекции, проверяет правила |

### Task

Атрибуты: `id`, `title`, `description`, `status`, `priority`, `due_date`,
`created_at`, `assigned_to`.

Методы: `mark_as_done()`, `mark_as_cancelled()`, `start_work()`,
`change_description(new_text)`, `set_due_date(date)`, `set_priority(level)`,
`is_overdue()`.

Плюс свойство `is_done` (см. раздел «@property» ниже).

Статусы: `"new"` → `"in_progress"` → `"done"` или `"cancelled"`.
Приоритет: от `1` (низкий) до `5` (высокий).

### Project

Атрибуты: `id`, `name`, `owner`, `members`, `tasks`, `is_archived`.

Методы: `add_task(task)`, `remove_task(task_id)`, `get_tasks_by_status(status)`,
`get_overdue_tasks()`, `archive()`, `invite_member(user)`.

Плюс свойство `progress` — процент выполненных задач.

### User

Атрибуты: `id`, `username`, `email`, `projects`, `preferences`.

Методы: `create_project(name)`, `join_project(project_id)`,
`update_preferences(new_prefs)`, `get_assigned_tasks()`.

### TodoManager

Атрибуты: `users`, `projects`, `tasks` — словари объектов по `id`.

Методы: `create_task()`, `complete_task()`, `move_task_to_project()`,
`search_tasks()`, `generate_report()`, `check_overdue_and_notify()`
(плюс вспомогательные `create_user()`, `create_project()`, `get_user()`,
`get_project()`, `get_task()`).

---

## Как объекты взаимодействуют

```
TodoManager ── создаёт и хранит ──► User, Project, Task  (словари по id)

User  1 ──── много ►  Project       user.projects
Project 1 ── много ►  Task          project.tasks
Task   * ──── 0..1 ►  User          task.assigned_to
```

- `Project.tasks` — список объектов `Task`: проект группирует и фильтрует свои задачи.
- `User.projects` — список объектов `Project`, где пользователь участвует.
- `Task.assigned_to` — ссылка на `User` или `None` (исполнитель не назначен).
- `TodoManager` — единственный вход в систему: он создаёт объекты, связывает их
  и следит, чтобы задача не оказалась в двух проектах одновременно.
  Классы при этом не дублируют логику друг друга: менеджер **делегирует**
  работу методам объектов (например, `complete_task()` просто вызывает
  `task.mark_as_done()`).

---

## Примеры работы

### 1. Пользователи, проект, участники

```python
from main import TodoManager

manager = TodoManager()

alice = manager.create_user("alice", "alice@example.com")
bob = manager.create_user("bob", "bob@example.com")
carol = manager.create_user("carol", "carol@example.com")

project = alice.create_project("Запуск сайта")  # alice становится владельцем
project.invite_member(bob)                      # приглашение
bob.join_project(project.id)                    # bob соглашается

print([u.username for u in project.members])    # ['alice', 'bob']
print([p.name for p in bob.projects])           # ['Запуск сайта']

carol.join_project(project.id)                  # приглашения не было...
# ValueError: У 'carol' нет приглашения в проект
```

### 2. Создание задач

```python
from datetime import datetime, timedelta

t1 = manager.create_task(
    "Спроектировать базу данных", project.id, alice.id,
    description="ER-диаграмма, таблицы, индексы",
    priority=5, due_date=datetime.now() + timedelta(days=3))

t2 = manager.create_task(
    "Сверстать главную страницу", project.id, bob.id,
    priority=4, due_date=datetime.now() - timedelta(days=1))  # уже просрочена

t3 = manager.create_task(
    "Написать REST API", project.id, bob.id,
    priority=5, due_date=datetime.now() + timedelta(days=7))

t4 = manager.create_task(
    "Настроить CI/CD", project.id, priority=2)  # без исполнителя и дедлайна
```

Задача сразу попадает в `project.tasks` и в общий справочник `manager.tasks`.

### 3. Смена статусов и дедлайны

```python
t1.start_work()               # new -> in_progress
manager.complete_task(t1.id)  # делегирует задаче метод mark_as_done()

print(t1.is_done)        # True   (это @property, скобки не нужны)
print(t2.is_overdue())   # True   (дедлайн прошёл, задача не выполнена)

project.get_tasks_by_status("in_progress")  # задачи в работе
project.get_overdue_tasks()                 # просроченные задачи
print(project.progress)                     # 25 (%): 1 задача из 4 выполнена
```

Недопустимые переходы отлавливаются:

```python
t1.mark_as_cancelled()
# ValueError: Завершенную задачу нельзя отменить
```

### 4. Поиск и фильтры

```python
manager.search_tasks("api")                          # текст ищется в title и description
manager.search_tasks(filters={"status": "new"})      # по статусу
manager.search_tasks(filters={"priority": 5})        # по приоритету
manager.search_tasks(filters={
    "due_before": datetime.now() + timedelta(days=5)})  # дедлайн не позже даты

manager.search_tasks(filters={"status": "плохой"})   # ValueError: Неизвестный статус
```

### 5. Перемещение задачи между проектами

```python
personal = manager.create_project("Личное", bob.id)
manager.move_task_to_project(t4.id, personal.id)

# t4 убрана из "Запуск сайта" и добавлена в "Личное" —
# задача не может находиться в двух проектах одновременно
```

### 6. Настройки и задачи пользователя

```python
bob.update_preferences({"language": "en", "notifications": False})
# {'language': 'en', 'timezone': 'UTC', 'notifications': False}

bob.get_assigned_tasks()   # задачи, назначенные именно bob
```

### 7. Отчёт

```python
manager.generate_report(bob.id, period=7)
```

```text
user: bob
period_days: 7
total: 2
by_status: {'new': 1, 'in_progress': 1, 'done': 0, 'cancelled': 0}
done: 0
overdue: 1
percent_done: 0
```

### 8. Уведомления о просрочке

```python
manager.check_overdue_and_notify()
```

```text
bob: Просрочена задача: Сверстать главную страницу
```

### 9. Архивирование проекта

```python
personal.archive()
manager.create_task("Купить хлеб", personal.id)
# ValueError: Проект 'Личное' архивирован
```

---

## Правила валидации

Программа не даёт выполнить некорректное действие и объясняет причину
(везде выбрасывается `ValueError` с русским описанием):

| Правило | Пример ошибки |
|---------|---------------|
| Название задачи/проекта не пустое | `Название задачи не может быть пустым` |
| Приоритет — целое число от 1 до 5 | `Приоритет должен быть числом от 1 до 5` |
| Статус из списка `Task.STATUSES` | `Неизвестный статус: ошибка` |
| Нельзя отменить завершённую задачу | `Завершенную задачу нельзя отменить` |
| Пользователь обязан состоять в проекте | `Пользователь 'carol' не состоит в проекте` |
| Вход в проект только по приглашению | `У 'carol' нет приглашения в проект` |
| В архивный проект нельзя добавлять задачи | `Проект 'Личное' архивирован` |
| Имя пользователя уникально | `Пользователь 'alice' уже существует` |
| Только известные фильтры поиска | `Неизвестный фильтр: ...` |

---

## @property

Свойства выглядят как атрибуты, но вычисляются на лету — к ним обращаются
без скобок:

```python
t1.is_done        # True/False: статус == "done"
project.progress  # 0-100: какой процент задач проекта выполнен
```

Это удобно: состояние не хранится отдельно и поэтому не может «разойтись»
с настоящим статусом задачи.
