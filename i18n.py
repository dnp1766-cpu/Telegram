"""Русские подписи для категорий и кухонь TheMealDB."""

from __future__ import annotations

CATEGORY_RU: dict[str, str] = {
    "Beef": "Говядина",
    "Breakfast": "Завтрак",
    "Chicken": "Курица",
    "Dessert": "Десерт",
    "Goat": "Козлятина",
    "Lamb": "Баранина",
    "Miscellaneous": "Разное",
    "Pasta": "Паста",
    "Pork": "Свинина",
    "Seafood": "Морепродукты",
    "Side": "Гарнир",
    "Starter": "Закуска",
    "Vegan": "Веган",
    "Vegetarian": "Вегетарианское",
}

AREA_RU: dict[str, str] = {
    "American": "Американская",
    "British": "Британская",
    "Canadian": "Канадская",
    "Chinese": "Китайская",
    "Croatian": "Хорватская",
    "Dutch": "Голландская",
    "Egyptian": "Египетская",
    "Filipino": "Филиппинская",
    "French": "Французская",
    "German": "Немецкая",
    "Greek": "Греческая",
    "Indian": "Индийская",
    "Irish": "Ирландская",
    "Italian": "Итальянская",
    "Jamaican": "Ямайская",
    "Japanese": "Японская",
    "Kenyan": "Кенийская",
    "Malaysian": "Малайзийская",
    "Mexican": "Мексиканская",
    "Moroccan": "Марокканская",
    "Netherlands": "Нидерландская",
    "Polish": "Польская",
    "Portuguese": "Португальская",
    "Russian": "Русская",
    "Spanish": "Испанская",
    "Thai": "Тайская",
    "Tunisian": "Тунисская",
    "Turkish": "Турецкая",
    "Ukrainian": "Украинская",
    "Unknown": "Не указана",
    "Vietnamese": "Вьетнамская",
}

# TheMealDB list.php?a=list сейчас отдаёт сотни стран.
# В боте показываем только кухни, по которым обычно есть рецепты.
FEATURED_AREAS: tuple[str, ...] = (
    "American",
    "British",
    "Canadian",
    "Chinese",
    "Croatian",
    "Dutch",
    "Egyptian",
    "Filipino",
    "French",
    "Greek",
    "Indian",
    "Irish",
    "Italian",
    "Jamaican",
    "Japanese",
    "Kenyan",
    "Malaysian",
    "Mexican",
    "Moroccan",
    "Polish",
    "Portuguese",
    "Russian",
    "Spanish",
    "Thai",
    "Tunisian",
    "Turkish",
    "Ukrainian",
    "Vietnamese",
)


def category_label(name: str | None) -> str:
    if not name:
        return "Без категории"
    return CATEGORY_RU.get(name, name)


def area_label(name: str | None) -> str:
    if not name:
        return "Кухня не указана"
    return AREA_RU.get(name, name)
