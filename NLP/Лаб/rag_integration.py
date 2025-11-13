# rag_integration.py
import os
import faiss
import pickle
import subprocess
import argparse
from typing import List, Tuple
from sentence_transformers import SentenceTransformer

os.environ["TOKENIZERS_PARALLELISM"] = "false"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
OLLAMA_MODEL_NAME = "qwen2.5:1.5b" # Ваша модель
INDEX_PATH = "faiss_index.idx"
CHUNKS_PATH = "doc_chunks.pkl"
KNOWLEDGE_PATH_DEFAULT = "База_Знаний.txt"
FALLBACK_MIN_LENGTH = 20
K_RETRIEVAL = 3
RETRY_ON_EMPTY = 1
OLLAMA_TIMEOUT = 60
PROMPT_PREVIEW_LEN = 200

# Функции split_into_chunks, build_faiss_index, load_index, retrieve_relevant, generate_with_ollama, fallback_logic
# ОСТАЮТСЯ ТАКИМИ ЖЕ, КАК В ПРЕДЫДУЩИХ ОБСУЖДЕНИЯХ (где они были синхронными)

def split_into_chunks(text: str, max_tokens: int = 300) -> List[str]:
    paragraphs = text.split("\n\n")
    chunks, current, current_len = [], [], 0
    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len > max_tokens * 5 and current:
            chunks.append("\n\n".join(current))
            current, current_len = [para], para_len
        else:
            current.append(para)
            current_len += para_len
    if current:
        chunks.append("\n\n".join(current))
    return chunks

def build_faiss_index(knowledge_path: str = KNOWLEDGE_PATH_DEFAULT):
    if not os.path.isfile(knowledge_path):
        print(f"[BUILD_FAISS] Файл знаний '{knowledge_path}' не найден. Пожалуйста, создайте его.")
        # Решение: создать пустой файл, если его нет, чтобы избежать ошибки дальше,
        # но предупредить пользователя.
        try:
            with open(knowledge_path, 'w', encoding='utf-8') as f:
                f.write("# Это автоматически созданный пустой файл базы знаний.\n# Пожалуйста, наполните его релевантной информацией.\n")
            print(f"[BUILD_FAISS] Создан пустой файл '{knowledge_path}'.")
        except IOError as e:
            raise FileNotFoundError(f"Не удалось создать файл знаний '{knowledge_path}': {e}")

    with open(knowledge_path, encoding="utf-8") as f:
        text = f.read()
    
    chunks = split_into_chunks(text)
    if not chunks or (len(chunks) == 1 and not chunks[0].strip()): # Проверка на пустые или почти пустые чанки
        print(f"[BUILD_FAISS] В файле '{knowledge_path}' не найдено достаточно контента для создания индекса. Индекс не будет построен.")
        # Очищаем старые файлы индекса, если они есть, чтобы не использовать устаревший индекс
        if os.path.exists(INDEX_PATH): os.remove(INDEX_PATH)
        if os.path.exists(CHUNKS_PATH): os.remove(CHUNKS_PATH)
        return False # Возвращаем False, если индекс не построен

    print(f"[BUILD_FAISS] Создаем эмбеддинги для {len(chunks)} фрагментов...")
    emb_model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = emb_model.encode(chunks, show_progress_bar=True)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    faiss.write_index(index, INDEX_PATH)
    with open(CHUNKS_PATH, "wb") as f:
        pickle.dump(chunks, f)
    print(f"[BUILD_FAISS] Индекс и фрагменты сохранены: {INDEX_PATH}, {CHUNKS_PATH}")
    return True # Индекс успешно построен

def load_index() -> Tuple[faiss.IndexFlatL2, List[str], SentenceTransformer]:
    if not os.path.isfile(INDEX_PATH) or not os.path.isfile(CHUNKS_PATH):
        print(f"[LOAD_INDEX] Файлы индекса '{INDEX_PATH}' или фрагментов '{CHUNKS_PATH}' не найдены.")
        print(f"[LOAD_INDEX] Пожалуйста, сначала создайте индекс командой: python rag_integration.py build-index --file {KNOWLEDGE_PATH_DEFAULT}")
        raise FileNotFoundError("Индекс или фрагменты не найдены. Запустите build-index.")
    index = faiss.read_index(INDEX_PATH)
    with open(CHUNKS_PATH, "rb") as f:
        chunks = pickle.load(f)
    emb_model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"[LOAD_INDEX] Загружен индекс с {len(chunks)} фрагментами.")
    return index, chunks, emb_model

def retrieve_relevant(query: str, k: int = K_RETRIEVAL) -> List[str]:
    try:
        index, chunks, emb_model = load_index()
    except FileNotFoundError:
        print("[RAG_RETRIEVE] Ошибка: индекс не загружен. Релевантные фрагменты не могут быть извлечены.")
        return []
        
    print(f"[RAG_RETRIEVE] Поиск {k} релевантных фрагментов для: '{query}'")
    q_emb = emb_model.encode([query])
    _, indices = index.search(q_emb, k)
    relevant = [chunks[i] for i in indices[0] if 0 <= i < len(chunks)]
    print(f"[RAG_RETRIEVE] Найдено {len(relevant)} релевантных фрагментов.")
    # for i, frag in enumerate(relevant, 1):
    #     snippet = frag[:100].replace("\n", " ")
    #     print(f"  {i}. {snippet}...")
    return relevant

def generate_with_ollama(prompt: str, model: str = OLLAMA_MODEL_NAME) -> str:
    print(f"[OLLAMA_GEN] Отправка промта (модель: {model}) длиной {len(prompt)} символов (первые {PROMPT_PREVIEW_LEN}):")
    print(prompt[:PROMPT_PREVIEW_LEN] + "...")
    last_err = "Неизвестная ошибка"
    for attempt in range(RETRY_ON_EMPTY + 1):
        print(f"[OLLAMA_GEN] Ollama попытка {attempt+1}/{RETRY_ON_EMPTY+1}...")
        try:
            proc = subprocess.run(
                ["ollama", "run", model],
                input=prompt,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=OLLAMA_TIMEOUT,
                check=False
            )
        except subprocess.TimeoutExpired:
            print(f"[OLLAMA_GEN] Ollama timeout after {OLLAMA_TIMEOUT}s")
            last_err = "Тайм-аут при обращении к Ollama."
            continue
        except FileNotFoundError:
            print("[OLLAMA_GEN] Ошибка: команда 'ollama' не найдена. Убедитесь, что Ollama установлена и доступна в PATH.")
            return "Ошибка: Ollama не доступна."

        if proc.returncode != 0:
            last_err = proc.stderr.strip() if proc.stderr else "Неизвестная ошибка Ollama."
            print(f"[OLLAMA_GEN] Ollama error (code {proc.returncode}): {last_err}")
            if "model" in last_err.lower() and ("not found" in last_err.lower() or "pull" in last_err.lower()):
                 print(f"[OLLAMA_GEN] Модель {model} не найдена. Попробуйте: ollama pull {model}")
                 return f"Ошибка: Модель Ollama '{model}' не найдена. Пожалуйста, убедитесь, что она загружена (`ollama pull {model}`)."
            continue
        
        text = proc.stdout.strip()
        if text:
            print("[OLLAMA_GEN] Ответ получен от Ollama.")
            return text
            
    print(f"[OLLAMA_GEN] Ollama вернул пустой ответ после нескольких попыток. Последняя ошибка: {last_err}")
    return f"К сожалению, не удалось получить ответ от языковой модели. ({last_err})"

def fallback_logic(user_query: str) -> str:
    return "К сожалению, я не смог найти ответ на ваш вопрос в базе знаний или сгенерировать его. Пожалуйста, попробуйте переформулировать вопрос или обратитесь к оператору через главное меню."

# ОСНОВНАЯ СИНХРОННАЯ ФУНКЦИЯ RAG
def rag_response(user_query: str) -> str:
    print(f"[RAG_RESPONSE] Получен запрос: {user_query}")
    relevant_chunks = retrieve_relevant(user_query)

    if not relevant_chunks:
        print("[RAG_RESPONSE] Релевантные фрагменты не найдены. Попытка генерации без контекста.")
        system_msg_no_context = "Ты — ассистент IT-поддержки. Постарайся ответить на вопрос пользователя, даже если у тебя нет специфической информации из базы знаний."
        prompt_no_context = f"{system_msg_no_context}\n\nПользователь: \"{user_query}\"\nАссистент:"
        response = generate_with_ollama(prompt_no_context)
    else:
        system_msg = "Ты — полезный ассистент IT-поддержки. Внимательно изучи предоставленную ниже информацию из базы знаний и используй её, чтобы как можно точнее и полнее ответить на вопрос пользователя. Не придумывай информацию, которой нет в базе знаний. Если информации недостаточно, укажи это."
        knowledge = "\n\n---\n\n".join(relevant_chunks)
        prompt = f"{system_msg}\n\n## Информация из Базы Знаний:\n{knowledge}\n\n## Вопрос Пользователя:\n\"{user_query}\"\n\n## Ответ Ассистента (на основе Базы Знаний):"
        response = generate_with_ollama(prompt)

    print(f"[RAG_RESPONSE] Ответ от LLM длиной {len(response)} символов.")
    # print(f"[RAG_RESPONSE] Начало ответа: {response[:200]}")

    is_fallback_response = False
    if len(response) < FALLBACK_MIN_LENGTH:
        is_fallback_response = True
    
    negative_keywords = [
        "не знаю", "нет информации", "не могу помочь", "не удалось найти",
        "недостаточно данных", "базе знаний нет", "затрудняюсь ответить",
        "не могу ответить", "нет ответа", "не уверен", "ollama", "ошибка:", # Добавил двоеточие к ошибке
        "к сожалению, не удалось получить ответ" # Фраза из generate_with_ollama
    ]
    # Проверяем точное вхождение ключевых слов, чтобы избежать ложных срабатываний
    response_lower = response.lower()
    if any(keyword in response_lower for keyword in negative_keywords):
        is_fallback_response = True
        print(f"[RAG_RESPONSE] Обнаружен негативный ключ в ответе LLM.")

    if is_fallback_response:
        print("[RAG_RESPONSE] Ответ LLM неудовлетворительный или слишком короткий. Переход к фоллбэку.")
        return fallback_logic(user_query)
        
    return response

# CLI интерфейс для сборки индекса (оставляем как есть для удобства)
def main_cli():
    parser = argparse.ArgumentParser(description="RAG module CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    parser_build = subparsers.add_parser("build-index", help="Build FAISS index from knowledge file")
    parser_build.add_argument("--file", default=KNOWLEDGE_PATH_DEFAULT, help=f"Path to knowledge txt file (default: {KNOWLEDGE_PATH_DEFAULT})")
    # Команда query через CLI здесь не так важна, так как основная логика будет в боте
    
    args = parser.parse_args()
    if args.command == "build-index":
        build_faiss_index(args.file)
    else:
        parser.print_help()

if __name__ == "__main__":
    main_cli()
#python rag_integration.py build-index --file База_Знаний.txt
#python rag_integration.py query --model qwen2.5-coder:3b
#pip install -U huggingface_hub[hf_xet]
#KNOWLEDGE_PATH = "База_Знаний.txt"