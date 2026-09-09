"""Create an Excel draft from Ozon product links.

The workbook is intentionally generated with the Python standard library so the
project does not need an Excel dependency just for a one-off catalog draft.
"""

from __future__ import annotations

import csv
import re
import zipfile
from html import escape
from pathlib import Path
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "data"
XLSX_PATH = OUTPUT_DIR / "ozon_products_draft.xlsx"
CSV_PATH = OUTPUT_DIR / "ozon_products_draft.csv"

COLUMNS = [
    "Категория",
    "Название товара",
    "Артикул / SKU",
    "Цена",
    "Старая цена",
    "Остаток",
    "Краткое описание",
    "Полное описание",
    "Характеристики",
    "Главное фото",
    "Доп. фото",
    "На главную",
    "Активен",
    "Ozon ID",
    "Модель",
    "Цвет",
    "Ссылка на Ozon",
    "Что проверить",
]

PRODUCTS = [
    {
        "url": "https://www.ozon.ru/product/karaoke-kolonka-s-mikrofonom-ws-858-mikrofon-blyutuz-bluetooth-4-stilya-golosa-5-ch-raboty-1333468769/",
        "category": "Караоке-микрофоны",
        "name": "Караоке-колонка с микрофоном WS-858 Bluetooth, 4 стиля голоса",
        "model": "WS-858",
        "color": "",
        "features": "4 стиля голоса; до 5 ч работы",
        "kind": "karaoke",
    },
    {
        "url": "https://www.ozon.ru/product/karaoke-kolonka-s-mikrofonom-ws-858-mikrofon-blyutuz-bluetooth-4-stilya-golosa-5-ch-raboty-zoloto-1325227075/",
        "category": "Караоке-микрофоны",
        "name": "Караоке-колонка с микрофоном WS-858 Bluetooth, золотая",
        "model": "WS-858",
        "color": "золото",
        "features": "4 стиля голоса; до 5 ч работы",
        "kind": "karaoke",
    },
    {
        "url": "https://www.ozon.ru/product/karaoke-kolonka-s-mikrofonom-wster-ws-669-mikrofon-dlya-karaoke-4-golosa-podsvetka-rozovoe-zoloto-1325227070/",
        "category": "Караоке-микрофоны",
        "name": "Караоке-колонка с микрофоном WSTER WS-669, розовое золото",
        "model": "WS-669",
        "color": "розовое золото",
        "features": "4 голоса; подсветка",
        "kind": "karaoke",
    },
    {
        "url": "https://www.ozon.ru/product/karaoke-kolonka-s-mikrofonom-ws-669-mikrofon-dlya-karaoke-bluetooth-4-golosa-podsvetka-zolotoy-1325227072/",
        "category": "Караоке-микрофоны",
        "name": "Караоке-колонка с микрофоном WS-669 Bluetooth, золотая",
        "model": "WS-669",
        "color": "золотой",
        "features": "4 голоса; подсветка",
        "kind": "karaoke",
    },
    {
        "url": "https://www.ozon.ru/product/karaoke-kolonka-s-mikrofonom-ws-858-mikrofon-blyutuz-bluetooth-4-stilya-golosa-5-ch-raboty-chernyy-1333468764/",
        "category": "Караоке-микрофоны",
        "name": "Караоке-колонка с микрофоном WS-858 Bluetooth, черная",
        "model": "WS-858",
        "color": "черный",
        "features": "4 стиля голоса; до 5 ч работы",
        "kind": "karaoke",
    },
    {
        "url": "https://www.ozon.ru/product/karaoke-kolonka-s-mikrofonom-ws-1828-mikrofon-dlya-karaoke-bluetooth-4-golosa-podsvetka-zolotoy-1325227012/",
        "category": "Караоке-микрофоны",
        "name": "Караоке-колонка с микрофоном WS-1828 Bluetooth, золотая",
        "model": "WS-1828",
        "color": "золотой",
        "features": "4 голоса; подсветка",
        "kind": "karaoke",
    },
    {
        "url": "https://www.ozon.ru/product/karaoke-kolonka-s-mikrofonom-ws-669-mikrofon-dlya-karaoke-bluetooth-4-golosa-podsvetka-chernyy-1325227078/",
        "category": "Караоке-микрофоны",
        "name": "Караоке-колонка с микрофоном WS-669 Bluetooth, черная",
        "model": "WS-669",
        "color": "черный",
        "features": "4 голоса; подсветка",
        "kind": "karaoke",
    },
    {
        "url": "https://www.ozon.ru/product/karaoke-kolonka-s-mikrofonom-ws-1828-mikrofon-dlya-karaoke-bluetooth-4-golosa-podsvetka-krasnyy-1325227051/",
        "category": "Караоке-микрофоны",
        "name": "Караоке-колонка с микрофоном WS-1828 Bluetooth, красная",
        "model": "WS-1828",
        "color": "красный",
        "features": "4 голоса; подсветка",
        "kind": "karaoke",
    },
    {
        "url": "https://www.ozon.ru/product/karaoke-kolonka-s-mikrofonom-ws-2911-mikrofon-blyutuz-bluetooth-4-stilya-golosa-krasnyy-1325226979/",
        "category": "Караоке-микрофоны",
        "name": "Караоке-колонка с микрофоном WS-2911 Bluetooth, красная",
        "model": "WS-2911",
        "color": "красный",
        "features": "4 стиля голоса",
        "kind": "karaoke",
    },
    {
        "url": "https://www.ozon.ru/product/karaoke-kolonka-s-mikrofonom-ws-1828-mikrofon-dlya-karaoke-bluetooth-4-golosa-podsvetka-belyy-1325226993/",
        "category": "Караоке-микрофоны",
        "name": "Караоке-колонка с микрофоном WS-1828 Bluetooth, белая",
        "model": "WS-1828",
        "color": "белый",
        "features": "4 голоса; подсветка",
        "kind": "karaoke",
    },
    {
        "url": "https://www.ozon.ru/product/besprovodnaya-kolonka-mashina-ws-1967-ford-mustang-gt-bluetooth-red-1396829540/",
        "category": "Портативные колонки",
        "name": "Беспроводная колонка-машина WS-1967 Ford Mustang GT Bluetooth, красная",
        "model": "WS-1967",
        "color": "красный",
        "features": "дизайн Ford Mustang GT",
        "kind": "speaker_car",
    },
    {
        "url": "https://www.ozon.ru/product/karaoke-kolonka-s-mikrofonom-ws-1828-mikrofon-dlya-karaoke-bluetooth-4-golosa-podsvetka-chernyy-1325227006/",
        "category": "Караоке-микрофоны",
        "name": "Караоке-колонка с микрофоном WS-1828 Bluetooth, черная",
        "model": "WS-1828",
        "color": "черный",
        "features": "4 голоса; подсветка",
        "kind": "karaoke",
    },
    {
        "url": "https://www.ozon.ru/product/besprovodnaya-kolonka-mashina-ws-591-mercedes-g63-bluetooth-krasnaya-1396389692/",
        "category": "Портативные колонки",
        "name": "Беспроводная колонка-машина WS-591 Mercedes G63 Bluetooth, красная",
        "model": "WS-591",
        "color": "красный",
        "features": "дизайн Mercedes G63",
        "kind": "speaker_car",
    },
    {
        "url": "https://www.ozon.ru/product/besprovodnaya-kolonka-mashina-ws-596-bluetooth-bezhevaya-1396970414/",
        "category": "Портативные колонки",
        "name": "Беспроводная колонка-машина WS-596 Bluetooth, бежевая",
        "model": "WS-596",
        "color": "бежевый",
        "features": "дизайн автомобиля",
        "kind": "speaker_car",
    },
    {
        "url": "https://www.ozon.ru/product/besprovodnaya-kolonka-mashina-ws-1967-ford-mustang-gt-bluetooth-sinyaya-1396828254/",
        "category": "Портативные колонки",
        "name": "Беспроводная колонка-машина WS-1967 Ford Mustang GT Bluetooth, синяя",
        "model": "WS-1967",
        "color": "синий",
        "features": "дизайн Ford Mustang GT",
        "kind": "speaker_car",
    },
    {
        "url": "https://www.ozon.ru/product/besprovodnaya-kolonka-mashina-ws-300sl-bluetooth-serebristaya-1397009749/",
        "category": "Портативные колонки",
        "name": "Беспроводная колонка-машина WS-300SL Bluetooth, серебристая",
        "model": "WS-300SL",
        "color": "серебристый",
        "features": "дизайн автомобиля",
        "kind": "speaker_car",
    },
    {
        "url": "https://www.ozon.ru/product/besprovodnaya-kolonka-mashina-ws-1968-bluetooth-golubaya-1396869934/",
        "category": "Портативные колонки",
        "name": "Беспроводная колонка-машина WS-1968 Bluetooth, голубая",
        "model": "WS-1968",
        "color": "голубой",
        "features": "дизайн автомобиля",
        "kind": "speaker_car",
    },
    {
        "url": "https://www.ozon.ru/product/besprovodnaya-kolonka-mashina-ws-1968-bluetooth-belaya-1396875539/",
        "category": "Портативные колонки",
        "name": "Беспроводная колонка-машина WS-1968 Bluetooth, белая",
        "model": "WS-1968",
        "color": "белый",
        "features": "дизайн автомобиля",
        "kind": "speaker_car",
    },
    {
        "url": "https://www.ozon.ru/product/besprovodnaya-kolonka-mashina-ws-1967-ford-mustang-gt-bluetooth-chernaya-1396827392/",
        "category": "Портативные колонки",
        "name": "Беспроводная колонка-машина WS-1967 Ford Mustang GT Bluetooth, черная",
        "model": "WS-1967",
        "color": "черный",
        "features": "дизайн Ford Mustang GT",
        "kind": "speaker_car",
    },
    {
        "url": "https://www.ozon.ru/product/besprovodnaya-kolonka-mashina-ws-592-chevrolet-bumblebee-bluetooth-chernaya-1396309176/",
        "category": "Портативные колонки",
        "name": "Беспроводная колонка-машина WS-592 Chevrolet Bumblebee Bluetooth, черная",
        "model": "WS-592",
        "color": "черный",
        "features": "дизайн Chevrolet Bumblebee",
        "kind": "speaker_car",
    },
    {
        "url": "https://www.ozon.ru/product/besprovodnaya-kolonka-mashina-ws-592-chevrolet-bumblebee-bluetooth-zheltaya-1396270108/",
        "category": "Портативные колонки",
        "name": "Беспроводная колонка-машина WS-592 Chevrolet Bumblebee Bluetooth, желтая",
        "model": "WS-592",
        "color": "желтый",
        "features": "дизайн Chevrolet Bumblebee",
        "kind": "speaker_car",
    },
    {
        "url": "https://www.ozon.ru/product/besprovodnaya-kolonka-mashina-ws-300sl-bluetooth-izumrudnaya-1396998245/",
        "category": "Портативные колонки",
        "name": "Беспроводная колонка-машина WS-300SL Bluetooth, изумрудная",
        "model": "WS-300SL",
        "color": "изумрудный",
        "features": "дизайн автомобиля",
        "kind": "speaker_car",
    },
    {
        "url": "https://www.ozon.ru/product/besprovodnaya-kolonka-mashina-ws-596-bluetooth-serebristaya-1396967098/",
        "category": "Портативные колонки",
        "name": "Беспроводная колонка-машина WS-596 Bluetooth, серебристая",
        "model": "WS-596",
        "color": "серебристый",
        "features": "дизайн автомобиля",
        "kind": "speaker_car",
    },
]

INSTRUCTION_ROWS = [
    ["Поле", "Как заполнять"],
    ["Цена", "Поставить вашу актуальную цену продажи. Сейчас поле оставлено пустым."],
    ["Старая цена", "Заполнять только для скидки. Если скидки нет, оставить пустым."],
    ["Остаток", "Поставить реальный остаток на складе."],
    ["Главное фото / Доп. фото", "Использовать свои фото или фото, на которые у вас есть права."],
    ["Активен", "Поменять на 'да' только после проверки цены, остатка, фото и описания."],
    ["Описание", "Тексты в таблице написаны заново, без дословного копирования Ozon."],
    ["Что проверить", "Список фактов, которые лучше сверить по поставке или карточке товара."],
]


def ozon_id_from_url(url: str) -> str:
    match = re.search(r"-(\d+)/?$", urlparse(url).path)
    return match.group(1) if match else ""


def short_description(product: dict[str, str]) -> str:
    if product["kind"] == "karaoke":
        return (
            f"Портативный Bluetooth-микрофон {product['model']} с динамиком "
            "для караоке, праздников и записи голоса."
        )
    return (
        f"Портативная Bluetooth-колонка {product['model']} в форме автомобиля "
        "для музыки дома, на работе и в поездке."
    )


def full_description(product: dict[str, str]) -> str:
    if product["kind"] == "karaoke":
        return (
            f"{product['name']} объединяет микрофон и компактную колонку. "
            "Модель подключается к смартфону по Bluetooth и подходит для караоке, "
            "домашних вечеринок, детских праздников и записи коротких голосовых "
            "фрагментов. Перед публикацией карточки уточните комплектацию, емкость "
            "аккумулятора, разъемы и фактическое время работы по вашей поставке."
        )
    return (
        f"{product['name']} — компактная беспроводная колонка в автомобильном "
        "дизайне. Ее удобно использовать как настольную колонку, подарок или "
        "аксессуар для поездок. Перед публикацией карточки уточните мощность, "
        "время работы, комплектацию, разъемы и поддержку карт памяти по вашей "
        "поставке."
    )


def specifications(product: dict[str, str], ozon_id: str) -> str:
    base_specs = [
        f"Модель: {product['model']}",
        f"Цвет: {product['color'] or 'уточнить'}",
        "Подключение: Bluetooth",
        f"Особенности: {product['features']}",
        f"Ozon ID источника: {ozon_id}",
    ]
    if product["kind"] == "karaoke":
        base_specs.insert(1, "Тип: караоке-микрофон с колонкой")
    else:
        base_specs.insert(1, "Тип: портативная Bluetooth-колонка")
    return "; ".join(base_specs)


def review_notes(product: dict[str, str]) -> str:
    common = "цена; остаток; фото; комплектация; гарантия"
    if product["kind"] == "karaoke":
        return f"{common}; емкость аккумулятора; время работы; разъемы; мощность динамика"
    return f"{common}; мощность; время работы; разъемы; поддержка microSD/USB"


def product_row(product: dict[str, str]) -> list[str]:
    ozon_id = ozon_id_from_url(product["url"])
    return [
        product["category"],
        product["name"],
        f"OZON-{ozon_id}",
        "",
        "",
        "",
        short_description(product),
        full_description(product),
        specifications(product, ozon_id),
        "",
        "",
        "нет",
        "нет",
        ozon_id,
        product["model"],
        product["color"],
        product["url"],
        review_notes(product),
    ]


def column_letter(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def cell_xml(row_number: int, column_number: int, value, style: int | None = None) -> str:
    reference = f"{column_letter(column_number)}{row_number}"
    style_attr = f' s="{style}"' if style is not None else ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{reference}"{style_attr}><v>{value}</v></c>'
    text = escape(str(value or ""))
    return (
        f'<c r="{reference}" t="inlineStr"{style_attr}>'
        f'<is><t xml:space="preserve">{text}</t></is></c>'
    )


def sheet_xml(rows: list[list[str]], widths: list[int]) -> str:
    cols = "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(widths, start=1)
    )
    sheet_data = []
    for row_number, row in enumerate(rows, start=1):
        cells = [
            cell_xml(row_number, column_number, value, style=1 if row_number == 1 else None)
            for column_number, value in enumerate(row, start=1)
        ]
        sheet_data.append(f'<row r="{row_number}">{"".join(cells)}</row>')

    max_column = column_letter(max(len(row) for row in rows))
    dimension = f"A1:{max_column}{len(rows)}"
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="{dimension}"/>
  <sheetViews>
    <sheetView workbookViewId="0">
      <pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>
      <selection pane="bottomLeft"/>
    </sheetView>
  </sheetViews>
  <cols>{cols}</cols>
  <sheetData>{"".join(sheet_data)}</sheetData>
  <autoFilter ref="{dimension}"/>
</worksheet>"""


def workbook_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Товары" sheetId="1" r:id="rId1"/>
    <sheet name="Инструкция" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>"""


def workbook_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def root_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""


def content_types_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""


def styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><name val="Calibri"/></font>
  </fonts>
  <fills count="2">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFE8EEF7"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="2">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="1" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
  </cellXfs>
</styleSheet>"""


def create_workbook(rows: list[list[str]]) -> None:
    product_widths = [24, 58, 18, 12, 14, 10, 60, 90, 80, 24, 32, 14, 12, 16, 14, 16, 64, 60]
    instruction_widths = [28, 100]
    with zipfile.ZipFile(XLSX_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml())
        archive.writestr("_rels/.rels", root_rels_xml())
        archive.writestr("xl/workbook.xml", workbook_xml())
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml())
        archive.writestr("xl/styles.xml", styles_xml())
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml(rows, product_widths))
        archive.writestr("xl/worksheets/sheet2.xml", sheet_xml(INSTRUCTION_ROWS, instruction_widths))


def create_csv(rows: list[list[str]]) -> None:
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerows(rows)


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    rows = [COLUMNS, *[product_row(product) for product in PRODUCTS]]
    create_workbook(rows)
    create_csv(rows)
    print(f"Created {XLSX_PATH.relative_to(ROOT_DIR)}")
    print(f"Created {CSV_PATH.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()
