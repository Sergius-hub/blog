# Импорт встроенной библиотеки для работы веб-сервера
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict

# Для начала определим настройки запуска
hostName = "localhost"  # Адрес для доступа по сети
serverPort = 8080  # Порт для доступа по сети

# Базовая директория проекта (где лежит server.py)
BASE_DIR = Path(__file__).parent


class Magazine:
    def __init__(self, templates_dir: str = None, static_dir: str = None) -> None:
        self.templates_dir = (
            Path(templates_dir) if templates_dir else BASE_DIR / "web" / "templates"
        )
        self.static_dir = (
            Path(static_dir) if static_dir else BASE_DIR / "web" / "static"
        )

        self.mime_types = {
            ".css": "text/css",
            ".js": "application/javascript",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".woff": "font/woff",
            ".woff2": "font/woff2",
            ".ttf": "font/ttf",
        }

        # Кэш шаблонов (загружаем один раз при старте)
        self._templates_cache: Dict[str, str] = {}

        # Предзагружаем базовые шаблоны
        self._load_base_templates()

        # Таблица маршрутов: путь -> (шаблон, заголовок)
        self.routes: Dict[str, tuple[str, str]] = {
            "/": ("main_page.html", "Главная"),
            "/categories": ("categories.html", "Категории"),
            "/orders": ("orders.html", "Заказы"),
            "/contacts": ("contacts.html", "Контакты"),
        }

    def get_static_file(self, path: str) -> tuple[bytes | None, str]:
        """Отдаёт статический файл."""
        relative = path.replace("/web/static/", "", 1)
        file_path = (self.static_dir / relative).resolve()
        print(f"📦 Ищу: {file_path} | Существует: {file_path.exists()}")
        # Защита от выхода за пределы папки static
        if not str(file_path).startswith(str(self.static_dir.resolve())):
            return None, ""

        if not file_path.exists() or not file_path.is_file():
            return None, ""

        mime = self.mime_types.get(file_path.suffix, "application/octet-stream")
        return file_path.read_bytes(), mime

    def _load_base_templates(self) -> None:
        """Загружает базовые шаблоны в кэш."""
        self._templates_cache["base.html"] = self._read_template("base.html")
        self._templates_cache["main_page.html"] = self._read_template("main_page.html")
        self._templates_cache["navbar.html"] = self._read_template("navbar.html")
        self._templates_cache["categories.html"] = self._read_template(
            "categories.html"
        )
        self._templates_cache["orders.html"] = self._read_template("orders.html")
        self._templates_cache["contacts.html"] = self._read_template("contacts.html")
        self._templates_cache["404.html"] = self._read_template("404.html")

    def _read_template(self, filename: str) -> str:
        """Читает файл шаблона с диска."""
        file_path = self.templates_dir / filename
        return file_path.read_text(encoding="utf-8")

    def _get_template(self, filename: str) -> str:
        """Получает шаблон из кэша или загружает с диска."""
        if filename not in self._templates_cache:
            self._templates_cache[filename] = self._read_template(filename)
        return self._templates_cache[filename]

    def _render_template(self, title: str, **context) -> str:
        """
        Рендерит шаблон с подстановкой переменных.
        """
        base_template = self._get_template("base.html")

        # Подставляем title
        result = base_template.replace("{title}", title)

        # Подставляем все переменные из контекста
        for key, value in context.items():
            result = result.replace(f"{{{key}}}", str(value))

        return result

    def _get_page(self, content_template: str, title: str) -> str:
        """
        Получает полную страницу: базовый шаблон + навбар + контент.
        """
        # Загружаем контент страницы
        content = self._get_template(content_template)

        # Загружаем навбар
        navbar = self._templates_cache["navbar.html"]

        # Рендерим базовый шаблон с подстановкой
        return self._render_template(title, navbar=navbar, content=content)

    def get_404_page(self):
        return self._get_template("404.html")

    def handle_request(self, path: str) -> tuple[str, int]:
        """
        Обрабатывает запрос и возвращает (html, status_code).
        """
        if path in self.routes:
            template_name, title = self.routes[path]
            html = self._get_page(template_name, title)
            return html, 200
        else:
            html = self.get_404_page()
            return html, 404


class MyServer(BaseHTTPRequestHandler):
    """
    Специальный класс, который отвечает за
    обработку входящих запросов от клиентов
    """

    magazine_instance = Magazine()

    def do_GET(self):

        # Убираем query string (?foo=bar)
        self.path = self.path.split("?")[0]

        # Игнорируем favicon
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        # Статические файлы
        if self.path.startswith("/web/static/"):
            content, mime = self.magazine_instance.get_static_file(self.path)

            if content:
                self.send_response(200)
                self.send_header("Content-type", mime)
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_response(404)
                self.end_headers()
            return

        """ Метод для обработки входящих GET-запросов """
        html, status = self.magazine_instance.handle_request(self.path)

        self.send_response(status)  # Отправка кода ответа
        self.send_header(
            "Content-type", "text/html; charset=utf-8"
        )  # Отправка типа данных, который будет передаваться
        self.end_headers()  # Завершение формирования заголовков ответа
        self.wfile.write(html.encode("utf-8"))  # Тело ответа


if __name__ == "__main__":
    # Инициализация веб-сервера, который будет по заданным параметрах в сети
    # принимать запросы и отправлять их на обработку специальному классу, который был описан выше
    webServer = HTTPServer((hostName, serverPort), MyServer)
    print("Server started http://%s:%s" % (hostName, serverPort))

    try:
        # Cтарт веб-сервера в бесконечном цикле прослушивания входящих запросов
        webServer.serve_forever()
    except KeyboardInterrupt:
        # Корректный способ остановить сервер в консоли через сочетание клавиш Ctrl + C
        pass

    # Корректная остановка веб-сервера, чтобы он освободил адрес и порт в сети, которые занимал
    webServer.server_close()
    print("Server stopped.")
