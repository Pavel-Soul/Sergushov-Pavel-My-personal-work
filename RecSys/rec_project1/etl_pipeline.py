import pandas as pd
from sqlalchemy import create_engine, text
import json
import ast 
import os
from tqdm import tqdm 

# --- 1. Конфигурация ---
DB_USER = 'postgres'
DB_PASSWORD = '0000'
DB_HOST = 'localhost'
DB_PORT = '5433'
DB_NAME = 'movie_recsys_db' 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

MOVIES_METADATA_PATH = os.path.join(DATA_DIR, 'movies_metadata.csv')
LINKS_SMALL_PATH = os.path.join(DATA_DIR, 'links_small.csv')
RATINGS_SMALL_PATH = os.path.join(DATA_DIR, 'ratings_small.csv')
CREDITS_PATH = os.path.join(DATA_DIR, 'credits.csv')
KEYWORDS_PATH = os.path.join(DATA_DIR, 'keywords.csv')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

print(f"Подключение к БД: {DB_NAME} на {DB_HOST}:{DB_PORT}")

# --- 2. Вспомогательные функции ---
def safe_json_loads(data_str, default_val=None):
    if pd.isna(data_str):
        return default_val
    try:
        return ast.literal_eval(data_str)
    except (ValueError, SyntaxError):
        try:
            return json.loads(data_str.replace("'", '"'))
        except (json.JSONDecodeError, TypeError):
            return default_val

# --- 3. Загрузка и обработка данных ---

# ========================================
# Шаг 3.1: Загрузка ссылок (links_small.csv) для сопоставления ID
# ========================================
print("\nОбработка links_small.csv...")
tmdb_to_movieid_map = {}
movieid_to_tmdb_map = {}
try:
    links_df = pd.read_csv(LINKS_SMALL_PATH, dtype={'movieId': int, 'tmdbId': 'Int64'}) # Читаем tmdbId как Int64 для поддержки NaN
    links_df.dropna(subset=['tmdbId', 'movieId'], inplace=True)
    links_df['tmdbId'] = links_df['tmdbId'].astype(int)
    tmdb_to_movieid_map = pd.Series(links_df.movieId.values, index=links_df.tmdbId).to_dict()
    movieid_to_tmdb_map = pd.Series(links_df.tmdbId.values, index=links_df.movieId).to_dict()
    print(f"Загружено {len(links_df)} ссылок. Созданы словари для маппинга ID.")
except FileNotFoundError:
    print(f"ОШИБКА: Файл {LINKS_SMALL_PATH} не найден!")
    exit()

# ========================================
# Шаг 3.2: Загрузка метаданных фильмов (movies_metadata.csv)
# и связанных данных (genres, movie_genres)
# ========================================
print("\nОбработка movies_metadata.csv...")
try:
    dtype_spec = {'id': str, 'popularity': str, 'adult':str, 'video':str}
    movies_meta_df = pd.read_csv(MOVIES_METADATA_PATH, usecols=[
        'id', 'title', 'overview', 'release_date', 'runtime',
        'original_language', 'poster_path', 'popularity',
        'vote_average', 'vote_count', 'status', 'tagline', 'genres', 'imdb_id'
    ], dtype=dtype_spec)
    print(f"Прочитано {len(movies_meta_df)} записей из movies_metadata.csv")

    movies_meta_df['id'] = pd.to_numeric(movies_meta_df['id'], errors='coerce')
    movies_meta_df.dropna(subset=['id'], inplace=True)
    movies_meta_df['id'] = movies_meta_df['id'].astype(int)
    movies_meta_df.rename(columns={'id': 'tmdb_id'}, inplace=True)

    movies_meta_df['movie_id'] = movies_meta_df['tmdb_id'].map(tmdb_to_movieid_map)
    movies_meta_df.dropna(subset=['movie_id'], inplace=True)
    movies_meta_df['movie_id'] = movies_meta_df['movie_id'].astype(int)
    movies_meta_df.drop_duplicates(subset=['movie_id'], keep='first', inplace=True)
    print(f"После маппинга с links и удаления дубликатов осталось {len(movies_meta_df)} фильмов.")

    movies_meta_df['release_date'] = pd.to_datetime(movies_meta_df['release_date'], errors='coerce')
    movies_meta_df['runtime'] = pd.to_numeric(movies_meta_df['runtime'], errors='coerce').fillna(0).astype(int)
    movies_meta_df['popularity'] = pd.to_numeric(movies_meta_df['popularity'], errors='coerce').fillna(0).astype(float)
    movies_meta_df['vote_average'] = pd.to_numeric(movies_meta_df['vote_average'], errors='coerce').fillna(0).astype(float)
    movies_meta_df['vote_count'] = pd.to_numeric(movies_meta_df['vote_count'], errors='coerce').fillna(0).astype(int)

    movies_to_load = movies_meta_df[[
        'movie_id', 'tmdb_id', 'imdb_id', 'title', 'overview', 'release_date',
        'runtime', 'original_language', 'poster_path', 'popularity',
        'vote_average', 'vote_count', 'status', 'tagline'
    ]].copy()
    movies_to_load.rename(columns={
        'vote_average': 'vote_average_tmdb',
        'vote_count': 'vote_count_tmdb'
    }, inplace=True)

    print(f"Загрузка {len(movies_to_load)} записей в таблицу 'movies'...")
    movies_to_load.to_sql('movies', engine, if_exists='append', index=False, chunksize=1000)
    print("Данные для 'movies' загружены.")

    print("Обработка и загрузка жанров...")
    all_genres_map = {} # Используем словарь для уникальности по ID: genre_id -> name
    movie_genre_relations = []

    for index, row in tqdm(movies_meta_df.iterrows(), total=movies_meta_df.shape[0], desc="Парсинг жанров"):
        current_movie_id = row['movie_id']
        genres_data = safe_json_loads(row['genres'], default_val=[])
        for genre_info in genres_data:
            if isinstance(genre_info, dict) and 'id' in genre_info and 'name' in genre_info:
                genre_id = int(genre_info['id']) # Убедимся что ID это int
                genre_name = str(genre_info['name']).strip()
                if genre_name and genre_id not in all_genres_map: # Добавляем только если ID уникален
                    all_genres_map[genre_id] = genre_name
                # Связь добавляем всегда, если жанр валиден
                if genre_name:
                     movie_genre_relations.append({'movie_id': current_movie_id, 'genre_id': genre_id})
    
    if all_genres_map:
        genres_df = pd.DataFrame(list(all_genres_map.items()), columns=['genre_id', 'name'])
        print(f"Загрузка {len(genres_df)} уникальных записей в таблицу 'genres'...")
        genres_df.to_sql('genres', engine, if_exists='append', index=False, chunksize=1000)
        print("Данные для 'genres' загружены.")

    if movie_genre_relations:
        movie_genres_df = pd.DataFrame(movie_genre_relations)
        movie_genres_df.drop_duplicates(inplace=True)
        print(f"Загрузка {len(movie_genres_df)} записей в таблицу 'movie_genres'...")
        movie_genres_df.to_sql('movie_genres', engine, if_exists='append', index=False, chunksize=1000)
        print("Данные для 'movie_genres' загружены.")

except FileNotFoundError:
    print(f"ОШИБКА: Файл {MOVIES_METADATA_PATH} не найден!")
except Exception as e:
    print(f"Произошла ошибка при обработке movies_metadata.csv: {e}")
    raise # Перевыбрасываем ошибку для отладки

# ========================================
# Шаг 3.3: Загрузка рейтингов (ratings_small.csv)
# и пользователей (users)
# ========================================
print("\nОбработка ratings_small.csv...")
try:
    ratings_df = pd.read_csv(RATINGS_SMALL_PATH, usecols=['userId', 'movieId', 'rating', 'timestamp'])
    print(f"Прочитано {len(ratings_df)} записей из ratings_small.csv")

    # Фильтруем рейтинги, оставляя только те, для которых фильмы есть в нашей таблице movies
    # (т.е. те movieId, которые были в links_small и потом попали в movies_to_load)
    valid_movie_ids_in_db = movies_to_load['movie_id'].unique() # Берем ID из уже подготовленного movies_to_load
    ratings_df = ratings_df[ratings_df['movieId'].isin(valid_movie_ids_in_db)]
    print(f"После фильтрации по существующим фильмам осталось {len(ratings_df)} рейтингов.")

    # --- Загрузка пользователей ('users') ---
    # Извлекаем уникальные userId из отфильтрованных рейтингов
    users_to_load = pd.DataFrame(ratings_df['userId'].unique(), columns=['user_id'])
    print(f"Загрузка {len(users_to_load)} записей в таблицу 'users'...")
    users_to_load.to_sql('users', engine, if_exists='append', index=False, chunksize=1000)
    print("Данные для 'users' загружены.")

    # --- Подготовка и загрузка рейтингов ('ratings') ---
    ratings_to_load = ratings_df.rename(columns={
        'userId': 'user_id',
        'movieId': 'movie_id',
        'timestamp': 'timestamp_val'
    })
    print(f"Загрузка {len(ratings_to_load)} записей в таблицу 'ratings'...")
    ratings_to_load.to_sql('ratings', engine, if_exists='append', index=False, chunksize=10000) # Больший chunksize для ratings
    print("Данные для 'ratings' загружены.")

except FileNotFoundError:
    print(f"ОШИБКА: Файл {RATINGS_SMALL_PATH} не найден!")
except Exception as e:
    print(f"Произошла ошибка при обработке ratings_small.csv: {e}")
    raise

# ========================================
# Шаг 3.4: Загрузка ключевых слов (keywords.csv)
# и связей (movie_keywords)
# ========================================
print("\nОбработка keywords.csv...")
try:
    keywords_file_df = pd.read_csv(KEYWORDS_PATH) # колонки: id, keywords
    print(f"Прочитано {len(keywords_file_df)} записей из keywords.csv")
    keywords_file_df.rename(columns={'id': 'tmdb_id'}, inplace=True)

    all_keywords_map = {} # keyword_id -> name
    movie_keyword_relations = []

    for index, row in tqdm(keywords_file_df.iterrows(), total=keywords_file_df.shape[0], desc="Парсинг ключевых слов"):
        tmdb_id = row['tmdb_id']
        # Находим наш movie_id по tmdb_id
        current_movie_id = tmdb_to_movieid_map.get(tmdb_id)
        if current_movie_id is None or current_movie_id not in valid_movie_ids_in_db: # Пропускаем, если фильма нет в нашей БД
            continue

        keywords_data = safe_json_loads(row['keywords'], default_val=[])
        for kw_info in keywords_data:
            if isinstance(kw_info, dict) and 'id' in kw_info and 'name' in kw_info:
                keyword_id = int(kw_info['id'])
                keyword_name = str(kw_info['name']).strip()
                if keyword_name and keyword_id not in all_keywords_map:
                    all_keywords_map[keyword_id] = keyword_name
                if keyword_name:
                    movie_keyword_relations.append({'movie_id': current_movie_id, 'keyword_id': keyword_id})

    if all_keywords_map:
        keywords_df = pd.DataFrame(list(all_keywords_map.items()), columns=['keyword_id', 'name'])
        print(f"Загрузка {len(keywords_df)} уникальных записей в таблицу 'keywords'...")
        keywords_df.to_sql('keywords', engine, if_exists='append', index=False, chunksize=1000)
        print("Данные для 'keywords' загружены.")

    if movie_keyword_relations:
        movie_keywords_df = pd.DataFrame(movie_keyword_relations)
        movie_keywords_df.drop_duplicates(inplace=True)
        print(f"Загрузка {len(movie_keywords_df)} записей в таблицу 'movie_keywords'...")
        movie_keywords_df.to_sql('movie_keywords', engine, if_exists='append', index=False, chunksize=10000)
        print("Данные для 'movie_keywords' загружены.")

except FileNotFoundError:
    print(f"ОШИБКА: Файл {KEYWORDS_PATH} не найден!")
except Exception as e:
    print(f"Произошла ошибка при обработке keywords.csv: {e}")
    raise

# ========================================
# Шаг 3.5: Загрузка информации о съемочной группе (credits.csv)
# и связанных данных (people, movie_cast, movie_crew)
# ========================================
print("\nОбработка credits.csv...")
try:
    credits_df = pd.read_csv(CREDITS_PATH) # колонки: cast, crew, id
    print(f"Прочитано {len(credits_df)} записей из credits.csv")
    credits_df.rename(columns={'id': 'tmdb_id'}, inplace=True)

    all_people_map = {} # person_id -> (name, gender, profile_path)
    movie_cast_relations = []
    movie_crew_relations = []

    for index, row in tqdm(credits_df.iterrows(), total=credits_df.shape[0], desc="Парсинг credits"):
        tmdb_id = row['tmdb_id']
        current_movie_id = tmdb_to_movieid_map.get(tmdb_id)
        if current_movie_id is None or current_movie_id not in valid_movie_ids_in_db:
            continue

        # Обработка cast
        cast_data = safe_json_loads(row['cast'], default_val=[])
        for person_info in cast_data:
            if isinstance(person_info, dict) and 'id' in person_info and 'name' in person_info:
                person_id = int(person_info['id'])
                person_name = str(person_info['name']).strip()
                if person_name and person_id not in all_people_map:
                    all_people_map[person_id] = {
                        'name': person_name,
                        'gender': person_info.get('gender'), # Может быть None
                        'profile_path': person_info.get('profile_path') # Может быть None
                    }
                if person_name:
                    movie_cast_relations.append({
                        'movie_id': current_movie_id,
                        'person_id': person_id,
                        'character_name': person_info.get('character'),
                        'cast_order': person_info.get('order')
                    })
        
        # Обработка crew
        crew_data = safe_json_loads(row['crew'], default_val=[])
        for person_info in crew_data:
            if isinstance(person_info, dict) and 'id' in person_info and 'name' in person_info:
                person_id = int(person_info['id'])
                person_name = str(person_info['name']).strip()
                if person_name and person_id not in all_people_map:
                     all_people_map[person_id] = {
                        'name': person_name,
                        'gender': person_info.get('gender'),
                        'profile_path': person_info.get('profile_path')
                    }
                if person_name:
                    movie_crew_relations.append({
                        'movie_id': current_movie_id,
                        'person_id': person_id,
                        'job': person_info.get('job'),
                        'department': person_info.get('department')
                    })

    if all_people_map:
        people_list = []
        for pid, data in all_people_map.items():
            people_list.append({
                'person_id': pid,
                'name': data['name'],
                'gender': data['gender'],
                'profile_path': data['profile_path']
            })
        people_df = pd.DataFrame(people_list)
        print(f"Загрузка {len(people_df)} уникальных записей в таблицу 'people'...")
        people_df.to_sql('people', engine, if_exists='append', index=False, chunksize=1000)
        print("Данные для 'people' загружены.")

    if movie_cast_relations:
        movie_cast_df = pd.DataFrame(movie_cast_relations)
        movie_cast_df.drop_duplicates(subset=['movie_id', 'person_id', 'character_name'], inplace=True) # Простая проверка на дубли
        print(f"Загрузка {len(movie_cast_df)} записей в таблицу 'movie_cast'...")
        movie_cast_df.to_sql('movie_cast', engine, if_exists='append', index=False, chunksize=10000)
        print("Данные для 'movie_cast' загружены.")

    if movie_crew_relations:
        movie_crew_df = pd.DataFrame(movie_crew_relations)
        movie_crew_df.drop_duplicates(subset=['movie_id', 'person_id', 'job', 'department'], inplace=True) # Простая проверка на дубли
        print(f"Загрузка {len(movie_crew_df)} записей в таблицу 'movie_crew'...")
        movie_crew_df.to_sql('movie_crew', engine, if_exists='append', index=False, chunksize=10000)
        print("Данные для 'movie_crew' загружены.")

except FileNotFoundError:
    print(f"ОШИБКА: Файл {CREDITS_PATH} не найден!")
except Exception as e:
    print(f"Произошла ошибка при обработке credits.csv: {e}")
    raise

print("\n--- ETL-процесс завершен ---")