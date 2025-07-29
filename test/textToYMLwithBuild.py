import xml.etree.ElementTree as ET
from datetime import datetime

INPUT_FILE = "clients/ОЗОН/output2404/output.txt"
YML_OUTPUT_FILE = "clients/ОЗОН/output2404/output.yml"

def parse_line(line):
    parts = line.strip().split("|")
    if len(parts) < 4:  # Минимум min_qty, sid, name и хотя бы один barcode или "Нет штрихкодов"
        return None
    min_qty = parts[0]
    sid = parts[1]
    name = parts[2]
    barcodes = parts[3:] if parts[3] != "Нет штрихкодов" else []
    return {"min_qty": min_qty, "sid": sid, "name": name, "barcodes": barcodes}

def create_yml():
    # Запрашиваем название сборки
    build_name = input("Введите название сборки (до 10 символов): ").strip()[:10]
    # Запрашиваем значение для дополнительного тега
    custom_tag_value = input("Введите значение дополнительного тега (до 10 символов): ").strip()[:10]
    
    result = []
    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        for line in file:
            data = parse_line(line)
            if data:
                result.append(data)

    root = ET.Element("yml_catalog", date=datetime.utcnow().isoformat() + "+00:00")
    shop = ET.SubElement(root, "shop")
    offers = ET.SubElement(shop, "offers")

    for item in result:
        offer = ET.SubElement(offers, "offer", id=str(item["sid"]))
        ET.SubElement(offer, "name").text = item["name"]
        # Добавляем тег <oshiptag> с color="yellow" для названия сборки
        if build_name:  # Добавляем только если значение не пустое
            oshiptag = ET.SubElement(offer, "oshiptag")
            oshiptag.set("color", "yellow")
            oshiptag.text = build_name
        # Добавляем тег <oshiptag> с color="green" для min_qty > 1
        try:
            min_qty_int = int(item["min_qty"])
            if min_qty_int > 1:
                oshiptag = ET.SubElement(offer, "oshiptag")
                oshiptag.set("color", "green")
                oshiptag.text = str(item["min_qty"])[:10]
        except ValueError:
            print(f"Предупреждение: min_qty для SID {item['sid']} не является числом: {item['min_qty']}")
        # Добавляем дополнительный тег <oshiptag> с color="yellow"
        if custom_tag_value:  # Добавляем только если значение не пустое
            oshiptag = ET.SubElement(offer, "oshiptag")
            oshiptag.set("color", "yellow")
            oshiptag.text = custom_tag_value
        # Добавляем штрихкоды
        for barcode in item["barcodes"]:
            ET.SubElement(offer, "barcode").text = barcode

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(YML_OUTPUT_FILE, encoding="utf-8", xml_declaration=True)
    print(f"YML сохранён в {YML_OUTPUT_FILE}")

if __name__ == "__main__":
    create_yml()