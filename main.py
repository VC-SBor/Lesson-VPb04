"""Система управления задачами (Todo-лист).

Классы:
    Task        - одна задача (название, описание, статус, приоритет, дедлайн).
    Project     - проект: список задач и участников.
    User        - пользователь: профиль, свои проекты, настройки.
    TodoManager - менеджер: создает объекты, хранит все коллекции, проверяет правила.

Как объекты взаимодействуют:
    * Project содержит список объектов Task  (project.tasks);
    * User содержит список объектов Project  (user.projects);
    * Task ссылается на User                (task.assigned_to), исполнитель может отсутствовать;
    * TodoManager создает все объекты и хранит словари users / projects / tasks по id,
      поэтому одна задача не может одновременно лежать в двух проектах.
"""

from datetime import date, datetime, timedelta


# ===========================================================================
# Task
# ===========================================================================
class Task:
    """Одна задача."""

    STATUSES = ("new", "in_progress", "done", "cancelled")
    last_id = 0  # счетчик: каждый раз дает задаче новый номер

    def __init__(self, title, description="", priority=3, due_date=None, assigned_to=None):
        # --- валидация входных данных ---
        if not title or not title.strip():
            raise ValueError("Название задачи не может быть пустым")
        if not isinstance(description, str):
            raise ValueError("Описание должно быть строкой")
        if not isinstance(priority, int) or priority < 1 or priority > 5:
            raise ValueError("Приоритет должен быть числом от 1 до 5")
        if due_date is not None and not isinstance(due_date, (date, datetime)):
            raise ValueError("Дедлайн должен быть датой (date/datetime) или None")
        if assigned_to is not None and not isinstance(assigned_to, User):
            raise ValueError("assigned_to должен быть объектом User")

        # --- атрибуты ---
        Task.last_id += 1
        self.id = Task.last_id
        self.title = title
        self.description = description
        self.status = "new"               # "new" | "in_progress" | "done" | "cancelled"
        self.priority = priority          # 1 (низкий) ... 5 (высокий)
        self.due_date = due_date          # дедлайн или None
        self.created_at = datetime.now()
        self.assigned_to = assigned_to    # объект User или None

    # --- свойства (@property) ---
    @property
    def is_done(self):
        """True, если задача выполнена. Обращаемся без скобок: task.is_done"""
        return self.status == "done"

    # --- изменение состояния ---
    def start_work(self):
        """Переводит задачу в статус "in_progress"."""
        if self.status == "done" or self.status == "cancelled":
            raise ValueError("Задача уже закрыта (статус: " + self.status + ")")
        self.status = "in_progress"

    def mark_as_done(self):
        """Переводит задачу в статус "done"."""
        if self.status == "cancelled":
            raise ValueError("Отмененную задачу нельзя завершить")
        self.status = "done"

    def mark_as_cancelled(self):
        """Переводит задачу в статус "cancelled"."""
        if self.status == "done":
            raise ValueError("Завершенную задачу нельзя отменить")
        self.status = "cancelled"

    # --- изменение данных ---
    def change_description(self, new_text):
        if not isinstance(new_text, str):
            raise ValueError("Описание должно быть строкой")
        self.description = new_text

    def set_due_date(self, due_date):
        if due_date is not None and not isinstance(due_date, (date, datetime)):
            raise ValueError("Дедлайн должен быть датой (date/datetime) или None")
        self.due_date = due_date

    def set_priority(self, level):
        if not isinstance(level, int) or level < 1 or level > 5:
            raise ValueError("Приоритет должен быть числом от 1 до 5")
        self.priority = level

    # --- проверки ---
    def is_overdue(self):
        """True, если дедлайн прошел, а задача не выполнена и не отменена."""
        if self.due_date is None or self.status == "done" or self.status == "cancelled":
            return False
        # дедлайн может быть date или datetime - сравниваем одинаковые типы
        if isinstance(self.due_date, datetime):
            return self.due_date < datetime.now()
        return self.due_date < date.today()

    def __repr__(self):
        return f"<Task #{self.id} '{self.title}' [{self.status}] P{self.priority}>"


# ===========================================================================
# Project
# ===========================================================================
class Project:
    """Проект: список задач и участников."""

    last_id = 0  # счетчик id проектов

    def __init__(self, name, owner):
        if not name or not name.strip():
            raise ValueError("Название проекта не может быть пустым")
        if not isinstance(owner, User):
            raise ValueError("Владелец проекта должен быть объектом User")

        Project.last_id += 1
        self.id = Project.last_id
        self.name = name
        self.owner = owner
        self.members = [owner]   # владелец сразу является участником
        self.tasks = []          # список объектов Task
        self.is_archived = False

    # --- работа с задачами ---
    def add_task(self, task):
        if self.is_archived:
            raise ValueError("Проект '" + self.name + "' архивирован, добавлять задачи нельзя")
        if task in self.tasks:
            raise ValueError("Задача уже есть в проекте '" + self.name + "'")
        self.tasks.append(task)

    def remove_task(self, task_id):
        """Удаляет задачу из проекта и возвращает ее (нужно для перемещения)."""
        for task in self.tasks:
            if task.id == task_id:
                self.tasks.remove(task)
                return task
        raise ValueError("В проекте '" + self.name + "' нет задачи с id=" + str(task_id))

    def get_tasks_by_status(self, status):
        """Возвращает список задач с указанным статусом."""
        if status not in Task.STATUSES:
            raise ValueError("Неизвестный статус: " + str(status))
        result = []
        for task in self.tasks:
            if task.status == status:
                result.append(task)
        return result

    def get_overdue_tasks(self):
        """Возвращает просроченные задачи проекта."""
        result = []
        for task in self.tasks:
            if task.is_overdue():
                result.append(task)
        return result

    # --- свойства (@property) ---
    @property
    def progress(self):
        """Процент выполненных задач проекта (0-100)."""
        if not self.tasks:
            return 0
        done = 0
        for task in self.tasks:
            if task.is_done:
                done += 1
        return round(done * 100 / len(self.tasks))

    # --- участники и жизненный цикл ---
    def invite_member(self, user):
        """Приглашает пользователя в проект."""
        if not isinstance(user, User):
            raise ValueError("Ожидается объект User")
        if self.is_archived:
            raise ValueError("Проект архивирован, приглашать нельзя")
        if user not in self.members:
            self.members.append(user)
        return user

    def archive(self):
        """Архивирует проект."""
        self.is_archived = True

    def __repr__(self):
        state = ", архивирован" if self.is_archived else ""
        return f"<Project #{self.id} '{self.name}', задач: {len(self.tasks)}{state}>"


# ===========================================================================
# User
# ===========================================================================
class User:
    """Пользователь системы."""

    last_id = 0  # счетчик id пользователей

    def __init__(self, username, email):
        if not username or not username.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        if not isinstance(email, str) or "@" not in email:
            raise ValueError("Некорректный email: " + str(email))

        User.last_id += 1
        self.id = User.last_id
        self.username = username
        self.email = email
        self.projects = []   # список объектов Project
        self.preferences = {
            "language": "ru",
            "timezone": "UTC",
            "notifications": True,
        }
        # менеджер заполняет эту ссылку в TodoManager.create_user()
        self.manager = None

    # --- действия через менеджер ---
    def create_project(self, name):
        """Создает проект, становясь его владельцем."""
        if self.manager is None:
            raise ValueError("Пользователь не добавлен в менеджер")
        return self.manager.create_project(name, self.id)

    def join_project(self, project_id):
        """Присоединяется к проекту, если есть приглашение."""
        if self.manager is None:
            raise ValueError("Пользователь не добавлен в менеджер")
        project = self.manager.get_project(project_id)
        if project.is_archived:
            raise ValueError("Проект '" + project.name + "' архивирован")
        if self not in project.members:
            raise ValueError("У '" + self.username + "' нет приглашения в проект")
        if project not in self.projects:
            self.projects.append(project)
        return project

    # --- настройки ---
    def update_preferences(self, new_prefs):
        """Обновляет настройки: добавляет/заменяет значения из new_prefs."""
        if not isinstance(new_prefs, dict):
            raise ValueError("Настройки должны быть словарем")
        self.preferences.update(new_prefs)
        return self.preferences

    # --- запросы ---
    def get_assigned_tasks(self):
        """Список задач, назначенных этому пользователю."""
        result = []
        if self.manager is not None:
            # смотрим все задачи менеджера
            for task in self.manager.tasks.values():
                if task.assigned_to is self:   # сравниваем ссылки на тот же объект
                    result.append(task)
        else:
            # запасной вариант для пользователя вне менеджера - через его проекты
            for project in self.projects:
                for task in project.tasks:
                    if task.assigned_to is self:
                        result.append(task)
        return result

    def __repr__(self):
        return f"<User #{self.id} '{self.username}' ({self.email})>"


# ===========================================================================
# TodoManager
# ===========================================================================
class TodoManager:
    """Центральный менеджер: создает объекты, хранит коллекции, проверяет правила."""

    def __init__(self):
        self.users = {}      # id -> User
        self.projects = {}   # id -> Project
        self.tasks = {}      # id -> Task

    # --- поиск по id ---
    def get_user(self, user_id):
        if user_id not in self.users:
            raise ValueError("Нет пользователя с id=" + str(user_id))
        return self.users[user_id]

    def get_project(self, project_id):
        if project_id not in self.projects:
            raise ValueError("Нет проекта с id=" + str(project_id))
        return self.projects[project_id]

    def get_task(self, task_id):
        if task_id not in self.tasks:
            raise ValueError("Нет задачи с id=" + str(task_id))
        return self.tasks[task_id]

    # --- пользователи ---
    def create_user(self, username, email):
        for user in self.users.values():
            if user.username == username:
                raise ValueError("Пользователь '" + username + "' уже существует")
        user = User(username, email)
        user.manager = self          # связываем пользователя с менеджером
        self.users[user.id] = user
        return user

    # --- проекты ---
    def create_project(self, name, owner_id):
        owner = self.get_user(owner_id)
        project = Project(name, owner)
        self.projects[project.id] = project
        owner.projects.append(project)
        return project

    # --- задачи ---
    def create_task(self, title, project_id, user_id=None,
                    description="", priority=3, due_date=None):
        """Создает задачу, добавляет ее в проект и (если указан) назначает на пользователя."""
        project = self.get_project(project_id)
        if project.is_archived:
            raise ValueError("Проект '" + project.name + "' архивирован")

        assigned_to = None
        if user_id is not None:
            assigned_to = self.get_user(user_id)
            if assigned_to not in project.members:
                raise ValueError(
                    "Пользователь '" + assigned_to.username + "' не состоит в проекте '"
                    + project.name + "'"
                )

        task = Task(title, description=description, priority=priority,
                    due_date=due_date, assigned_to=assigned_to)
        project.add_task(task)          # задача живет внутри проекта
        self.tasks[task.id] = task      # и попадает в общий справочник
        return task

    def complete_task(self, task_id):
        """Завершает задачу - просто вызывает ее метод mark_as_done()."""
        task = self.get_task(task_id)
        task.mark_as_done()
        return task

    def move_task_to_project(self, task_id, new_project_id):
        """Перемещает задачу из одного проекта в другой."""
        task = self.get_task(task_id)
        new_project = self.get_project(new_project_id)
        if new_project.is_archived:
            raise ValueError("Нельзя перенести задачу в архивный проект")

        # ищем проект, в котором сейчас лежит задача
        old_project = None
        for project in self.projects.values():
            if task in project.tasks:
                old_project = project
                break

        if old_project is new_project:
            raise ValueError("Задача уже находится в этом проекте")
        if old_project is not None:
            old_project.remove_task(task.id)
        new_project.add_task(task)
        return task

    def search_tasks(self, query="", filters=None):
        """Ищет задачи по тексту (название + описание) и фильтрам.

        Поддерживаемые фильтры:
            status     - статус задачи ("new", "in_progress", "done", "cancelled");
            priority   - точный приоритет (1-5);
            due_before - дедлайн не позже указанной даты.
        """
        if filters is None:
            filters = {}

        allowed = ["status", "priority", "due_before"]
        for key in filters:
            if key not in allowed:
                raise ValueError("Неизвестный фильтр: " + str(key))
        if "status" in filters and filters["status"] not in Task.STATUSES:
            raise ValueError("Неизвестный статус: " + str(filters["status"]))
        if "priority" in filters:
            p = filters["priority"]
            if not isinstance(p, int) or p < 1 or p > 5:
                raise ValueError("Приоритет должен быть числом от 1 до 5")

        text = query.strip().lower()
        result = []
        for task in self.tasks.values():
            # поиск по тексту, без учета регистра
            if text:
                if text not in task.title.lower() and text not in task.description.lower():
                    continue
            # фильтры
            if "status" in filters and task.status != filters["status"]:
                continue
            if "priority" in filters and task.priority != filters["priority"]:
                continue
            if "due_before" in filters:
                if task.due_date is None:
                    continue
                if task.due_date > filters["due_before"]:  # даты должны быть одного типа
                    continue
            result.append(task)
        return result

    def generate_report(self, user_id, period=7):
        """Отчет по задачам пользователя за последние period дней.

        Возвращает словарь со статистикой.
        """
        user = self.get_user(user_id)
        since = datetime.now() - timedelta(days=period)

        total = 0
        done = 0
        overdue = 0
        by_status = {}
        for status in Task.STATUSES:
            by_status[status] = 0

        for task in self.tasks.values():
            if task.assigned_to is not user:
                continue
            if task.created_at < since:
                continue
            total += 1
            by_status[task.status] += 1
            if task.is_done:
                done += 1
            if task.is_overdue():
                overdue += 1

        percent = round(done * 100 / total) if total else 0
        return {
            "user": user.username,
            "period_days": period,
            "total": total,
            "by_status": by_status,
            "done": done,
            "overdue": overdue,
            "percent_done": percent,
        }

    def check_overdue_and_notify(self):
        """Проверяет просроченные задачи и готовит уведомления."""
        notifications = []
        for task in self.tasks.values():
            if not task.is_overdue():
                continue
            if task.assigned_to is not None:
                recipient = task.assigned_to.username
            else:
                recipient = "исполнитель не назначен"
            notifications.append({
                "task_id": task.id,
                "title": task.title,
                "recipient": recipient,
                "due_date": task.due_date,
                "message": "Просрочена задача: " + task.title,
            })
        return notifications

    def __repr__(self):
        return (
            f"<TodoManager: пользователей={len(self.users)}, "
            f"проектов={len(self.projects)}, задач={len(self.tasks)}>"
        )


# ===========================================================================
# Пример работы системы
# ===========================================================================
def show_tasks(title, tasks):
    """Красиво выводит список задач в консоль."""
    print(title)
    if not tasks:
        print("  (задач нет)")
        return
    for task in tasks:
        if task.assigned_to is None:
            who = "не назначен"
        else:
            who = task.assigned_to.username
        if task.due_date is None:
            due = "-"
        else:
            due = task.due_date.strftime("%d.%m.%Y")
        print(f"  #{task.id} {task.status} P{task.priority} "
              f"«{task.title}» -> {who}, дедлайн: {due}")


if __name__ == "__main__":
    manager = TodoManager()

    # --- 1. Пользователи -------------------------------------------------
    print("=== 1. Создание пользователей ===")
    alice = manager.create_user("alice", "alice@example.com")
    bob = manager.create_user("bob", "bob@example.com")
    carol = manager.create_user("carol", "carol@example.com")
    print(alice)
    print(bob)
    print(carol)

    # --- 2. Проект и участники ------------------------------------------
    print("\n=== 2. Проект и участники ===")
    project = alice.create_project("Запуск сайта")   # делегирует менеджеру
    project.invite_member(bob)                        # приглашение
    bob.join_project(project.id)                      # bob соглашается
    print(project)
    print("Участники:", [u.username for u in project.members])
    print("Проекты bob:", [p.name for p in bob.projects])
    try:
        carol.join_project(project.id)                # приглашения не было
    except ValueError as error:
        print("Ошибка:", error)

    # --- 3. Задачи -------------------------------------------------------
    print("\n=== 3. Создание задач ===")
    t1 = manager.create_task(
        "Спроектировать базу данных", project.id, alice.id,
        description="ER-диаграмма, таблицы, индексы",
        priority=5, due_date=datetime.now() + timedelta(days=3))
    t2 = manager.create_task(
        "Сверстать главную страницу", project.id, bob.id,
        priority=4, due_date=datetime.now() - timedelta(days=1))   # уже просрочена
    t3 = manager.create_task(
        "Написать REST API", project.id, bob.id,
        priority=5, due_date=datetime.now() + timedelta(days=7))
    t4 = manager.create_task(
        "Настроить CI/CD", project.id, priority=2)    # без исполнителя и дедлайна
    show_tasks("Задачи проекта:", project.tasks)

    # --- 4. Статусы и дедлайны ------------------------------------------
    print("\n=== 4. Смена статусов ===")
    t1.start_work()               # new -> in_progress
    manager.complete_task(t1.id)  # менеджер вызывает t1.mark_as_done()
    t3.start_work()
    print("t1:", t1, "| is_done =", t1.is_done)       # is_done - это @property
    print("t3:", t3)
    print("t2 просрочена?", t2.is_overdue())
    show_tasks("Задачи в статусе in_progress:", project.get_tasks_by_status("in_progress"))
    show_tasks("Просроченные задачи:", project.get_overdue_tasks())
    print("Прогресс проекта:", project.progress, "%")  # progress - тоже @property

    # --- 5. Поиск и фильтры ---------------------------------------------
    print("\n=== 5. Поиск задач ===")
    show_tasks('Поиск по тексту "api":', manager.search_tasks("api"))
    show_tasks("Фильтр status = new:",
               manager.search_tasks(filters={"status": "new"}))
    show_tasks("Дедлайн в ближайшие 5 дней:",
               manager.search_tasks(filters={"due_before": datetime.now() + timedelta(days=5)}))
    try:
        manager.search_tasks(filters={"status": "ошибочный_статус"})
    except ValueError as error:
        print("Ошибка:", error)

    # --- 6. Валидация ----------------------------------------------------
    print("\n=== 6. Проверка правил ===")
    try:
        t1.set_priority(7)                       # приоритет только 1-5
    except ValueError as error:
        print("Ошибка:", error)
    try:
        manager.create_task("Новая задача", project.id, carol.id)  # carol не участник
    except ValueError as error:
        print("Ошибка:", error)

    # --- 7. Перемещение задачи ------------------------------------------
    print("\n=== 7. Перемещение задачи между проектами ===")
    personal = manager.create_project("Личное", bob.id)
    manager.move_task_to_project(t4.id, personal.id)
    print("Задача перенесена:", personal)
    show_tasks("Проект «Запуск сайта»:", project.tasks)
    show_tasks("Проект «Личное»:", personal.tasks)

    # --- 8. Настройки и задачи пользователя ------------------------------
    print("\n=== 8. Пользователь ===")
    bob.update_preferences({"language": "en", "notifications": False})
    print("Настройки bob:", bob.preferences)
    show_tasks("Задачи, назначенные bob:", bob.get_assigned_tasks())
    show_tasks("Задачи, назначенные alice:", alice.get_assigned_tasks())

    # --- 9. Отчет --------------------------------------------------------
    print("\n=== 9. Отчет по задачам bob за 7 дней ===")
    report = manager.generate_report(bob.id, period=7)
    for key, value in report.items():
        print(f"  {key}: {value}")

    # --- 10. Уведомления о просрочке -------------------------------------
    print("\n=== 10. Уведомления ===")
    for note in manager.check_overdue_and_notify():
        print(f"  {note['recipient']}: {note['message']}")

    # --- 11. Архивирование ----------------------------------------------
    print("\n=== 11. Архивирование проекта ===")
    personal.archive()
    print(personal)
    try:
        manager.create_task("Купить хлеб", personal.id)
    except ValueError as error:
        print("Ошибка:", error)

    print("\nИтог:", manager)
