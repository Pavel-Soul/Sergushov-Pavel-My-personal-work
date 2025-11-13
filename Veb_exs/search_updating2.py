from google import genai
from google.genai import types
import openpyxl
from datetime import datetime
import time
from random import uniform

API_KEY = "*****"  
client = genai.Client(api_key=API_KEY)

grounding_tool = types.Tool(
    google_search=types.GoogleSearch()
)

def generate_content(prompt, model="gemini-2.5-pro"): #flash 
    config = types.GenerateContentConfig(
        tools=[grounding_tool]
    )
    
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config, 
    )
    return response.text

def update_excel_file(input_file, sheet_name, start_row, end_row, save_as_new_file=True):
    print(f"Загрузка файла '{input_file}'")
    try:
        workbook = openpyxl.load_workbook(input_file)
    except FileNotFoundError:
        print(f"Ошибка: Файл '{input_file}' не найден.")
        return

    sheet = workbook[sheet_name]
    current_date = datetime.now().strftime("%d.%m.%Y")
    print(f"Начинаем обновление (дата проверки: {current_date})")
    print("-" * 50)

    for row_index in range(start_row, end_row + 1):
        raw_value = sheet[f"C{row_index}"].value
        if not raw_value:
            print(f"Пропускаем пустую строку {row_index}")
            continue

        raw_value = str(raw_value)
        print(f"Обновление строки {row_index}: {raw_value.splitlines()[0]}")
        prompt = f"""
        Ты — технический писатель, который создает лаконичные и точные справочные карточки по нейросетям.
        Твоя задача — выполнить два действия:
        1. Взять старую версию карточки для нейросети и актуализировать её, используя свежую информацию из интернета. Ты должен полностью сохранить исходную структуру, форматирование, теги <b> и набор эмодзи.
        2. Кратко, в 1-2 предложениях, описать, ЧТО ИМЕННО ты обновил (например: "Обновлена версия до 4.0, добавлена функция X, изменена цена").

        Вот старая версия карточки (используй её как шаблон формата):
        ---
        {raw_value}
        ---
        Теперь, используя поиск в интернете, найди самую свежую информацию на {current_date} и сгенерируй ответ СТРОГО в следующем формате, используя разделители [UPDATED_CARD] и [CHANGELOG]:

        [UPDATED_CARD]
        (здесь ОБНОВЛЕННАЯ карточка, с сохранением форматирования)

        [CHANGELOG]
        (здесь краткое описание изменений)
        """
        try:
            full_response = generate_content(prompt)
            if "[CHANGELOG]" in full_response and "[UPDATED_CARD]" in full_response:
                parts = full_response.split("[CHANGELOG]")
                updated_card_text = parts[0].replace("[UPDATED_CARD]", "").strip()
                changelog_text = parts[1].strip()

                sheet[f"C{row_index}"].value = updated_card_text
                sheet[f"D{row_index}"].value = changelog_text
                
                print(f"Успешно обновлено.")
                print(f"   Изменения: {changelog_text}")

            else:
                print("Ошибка: Модель вернула неправильный ответ")

        except Exception as e:
            print(f"Ошибка обновления строки {row_index}: {e}")

        time.sleep(uniform(1, 3))
        print("-" * 30)

    if save_as_new_file:
        output_filename = f"Нейросети_{current_date.replace('.', '_')}.xlsx"
        try:
            workbook.save(output_filename)
            print("=" * 50)
            print(f"Все изменения сохранены в: {output_filename}")
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
    else:
        try:
            workbook.save(input_file)
            print("=" * 50) 
            print(f"Все изменения сохранены в исходном файле: {input_file}")
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

if __name__ == "__main__":
    input_file = "Нейросети.xlsx"
    sheet_name = "Лист1" 
    start_row = 3
    end_row = 30
    update_excel_file(input_file, sheet_name, start_row, end_row, save_as_new_file=True)