"""Локальное превью каталога TheMealDB — те же рецепты и картинки, что у бота."""

from __future__ import annotations

import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from i18n import area_label, category_label
from mealdb import Meal, MealDBClient

HOST = "127.0.0.1"
PORT = 8765
client = MealDBClient()


def esc(value: str | None) -> str:
    return html.escape(value or "", quote=True)


def layout(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ru" translate="no">
<head>
  <meta charset="utf-8">
  <meta name="google" content="notranslate">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <style>
    :root {{
      --bg: #fff7ef;
      --card: #ffffff;
      --ink: #2b2118;
      --muted: #7a6858;
      --accent: #d35400;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: var(--bg);
      color: var(--ink);
    }}
    header {{
      padding: 24px 20px 8px;
      max-width: 1100px;
      margin: 0 auto;
    }}
    h1, h2 {{ margin: 0 0 8px; }}
    p.lead {{ color: var(--muted); margin-top: 0; }}
    form {{
      display: flex;
      gap: 8px;
      margin: 16px 0 8px;
    }}
    input[type=search] {{
      flex: 1;
      padding: 12px 14px;
      border: 1px solid #e6d3c2;
      border-radius: 12px;
      font-size: 16px;
    }}
    button, .btn {{
      background: var(--accent);
      color: white;
      border: 0;
      border-radius: 12px;
      padding: 12px 16px;
      text-decoration: none;
      display: inline-block;
      font-size: 16px;
    }}
    main {{
      max-width: 1100px;
      margin: 0 auto 48px;
      padding: 0 20px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: var(--card);
      border-radius: 18px;
      overflow: hidden;
      box-shadow: 0 8px 24px rgba(80, 40, 10, 0.08);
      text-decoration: none;
      color: inherit;
    }}
    .card img {{
      width: 100%;
      aspect-ratio: 1;
      object-fit: cover;
      display: block;
      background: #f3e6d8;
    }}
    .card .meta, .recipe .meta {{
      padding: 12px 14px 16px;
    }}
    .muted {{ color: var(--muted); font-size: 14px; }}
    .recipe img.hero {{
      width: 100%;
      max-height: 420px;
      object-fit: cover;
      border-radius: 18px;
    }}
    .recipe ul {{ padding-left: 18px; }}
    .ingredients {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 10px;
      padding: 0;
      list-style: none;
    }}
    .ingredients li {{
      background: white;
      border-radius: 12px;
      padding: 8px 10px;
      display: flex;
      gap: 8px;
      align-items: center;
    }}
    .ingredients img {{ width: 36px; height: 36px; object-fit: contain; }}
    nav a {{ color: var(--accent); }}
  </style>
</head>
<body>
  <header>
    <p class="muted"><a href="/">TheMealDB</a> · рецепты и картинки</p>
    <h1>{esc(title)}</h1>
    <form action="/search" method="get">
      <input type="search" name="q" placeholder="Например: pasta, chicken, cake" value="">
      <button type="submit">Найти</button>
      <a class="btn" href="/random">Случайный</a>
    </form>
  </header>
  <main>{body}</main>
</body>
</html>"""


def meal_card(meal: Meal | object) -> str:
    image = getattr(meal, "image_url", None) or ""
    meal_id = getattr(meal, "id", "")
    name = getattr(meal, "name", "")
    extra = ""
    category = getattr(meal, "category", None)
    area = getattr(meal, "area", None)
    if category or area:
        extra = f'<div class="muted">{esc(category_label(category))} · {esc(area_label(area))}</div>'
    return f"""
    <a class="card" href="/recipe/{esc(meal_id)}">
      <img src="{esc(image)}" alt="{esc(name)}">
      <div class="meta">
        <strong>{esc(name)}</strong>
        {extra}
      </div>
    </a>"""


def home_page() -> str:
    categories = client.categories()
    cards = []
    for item in categories:
        cards.append(
            f"""
            <a class="card" href="/category/{esc(item.name)}">
              <img src="{esc(item.thumbnail)}" alt="{esc(item.name)}">
              <div class="meta"><strong>{esc(category_label(item.name))}</strong></div>
            </a>"""
        )
    return layout(
        "Рецепты TheMealDB",
        '<p class="lead">Те же блюда и изображения, которые отправляет Telegram-бот.</p>'
        f'<div class="grid">{"".join(cards)}</div>',
    )


def search_page(query: str) -> str:
    meals = client.search(query) if query else []
    if not meals:
        body = f"<p>По запросу «{esc(query)}» ничего не найдено.</p>"
    else:
        body = f'<div class="grid">{"".join(meal_card(meal) for meal in meals)}</div>'
    return layout(f"Поиск: {query or '…'}", body)


def category_page(name: str) -> str:
    meals = client.filter_by_category(name)
    cards = "".join(meal_card(meal) for meal in meals)
    return layout(category_label(name), f'<div class="grid">{cards}</div>')


def recipe_page(meal_id: str) -> str:
    meal = client.lookup(meal_id)
    if meal is None:
        return layout("Не найдено", "<p>Рецепт не найден.</p>")
    ingredients = "".join(
        f"""<li>
            <img src="{esc(item.sized_image_url('small'))}" alt="{esc(item.name)}">
            <span><strong>{esc(item.name)}</strong><br>
            <span class="muted">{esc(item.measure)}</span></span>
        </li>"""
        for item in meal.ingredients
    )
    instructions = "<p>" + esc(meal.instructions).replace("\n", "<br>") + "</p>"
    links = []
    if meal.youtube:
        links.append(f'<a href="{esc(meal.youtube)}">YouTube</a>')
    if meal.source:
        links.append(f'<a href="{esc(meal.source)}">Источник</a>')
    body = f"""
    <article class="recipe">
      <img class="hero" src="{esc(meal.image_url)}" alt="{esc(meal.name)}">
      <p class="muted">{esc(category_label(meal.category))} · {esc(area_label(meal.area))}</p>
      <h2>Ингредиенты</h2>
      <ul class="ingredients">{ingredients}</ul>
      <h2>Приготовление</h2>
      {instructions}
      <p>{' · '.join(links)}</p>
    </article>"""
    return layout(meal.name, body)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        print(f"[preview] {self.address_string()} {args[0] if args else ''}")

    def _send(self, content: str, status: int = 200) -> None:
        data = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)

        try:
            if path == "/":
                self._send(home_page())
                return
            if path == "/search":
                self._send(search_page((query.get("q") or [""])[0].strip()))
                return
            if path == "/random":
                meal = client.random()
                if meal is None:
                    self._send(layout("Ошибка", "<p>Не удалось получить рецепт.</p>"), 502)
                    return
                self.send_response(302)
                self.send_header("Location", f"/recipe/{meal.id}")
                self.end_headers()
                return
            if path.startswith("/category/"):
                self._send(category_page(path.removeprefix("/category/")))
                return
            if path.startswith("/recipe/"):
                self._send(recipe_page(path.removeprefix("/recipe/")))
                return
            self._send(layout("404", "<p>Страница не найдена.</p>"), 404)
        except Exception as exc:  # noqa: BLE001
            self._send(layout("Ошибка", f"<p>{esc(str(exc))}</p>"), 500)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Превью TheMealDB: http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстанавливаю превью")
    finally:
        server.server_close()
        client.close()


if __name__ == "__main__":
    main()
