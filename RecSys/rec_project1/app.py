import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import ast # Для безопасного парсинга строк как литералов Python
from wordcloud import WordCloud, STOPWORDS
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity, linear_kernel
from surprise import Reader, Dataset, SVD
from surprise.model_selection import cross_validate
import os # Для работы с путями к файлам
from io import StringIO # Для перехвата вывода .info()

# --- Конфигурация страницы Streamlit ---
st.set_page_config(layout="wide", page_title="Рекомендательная система фильмов")
st.title("🎬 Рекомендательная система фильмов")

# --- Путь к данным (относительно app.py) ---
DATA_PATH = 'data/'

# --- Функции для загрузки и обработки данных (с кешированием) ---

@st.cache_data
def load_raw_data(data_path):
    """Загружает исходные CSV файлы."""
    movies_path = os.path.join(data_path, 'movies_metadata.csv')
    keywords_path = os.path.join(data_path, 'keywords.csv')
    credits_path = os.path.join(data_path, 'credits.csv')
    ratings_path = os.path.join(data_path, 'ratings_small.csv')
    # links_path = os.path.join(data_path, 'links.csv') # Если понадобится
    # links_small_path = os.path.join(data_path, 'links_small.csv') # Если понадобится

    try:
        movies_df = pd.read_csv(movies_path, low_memory=False)
        keywords_df = pd.read_csv(keywords_path)
        credits_df = pd.read_csv(credits_path)
        ratings_small_df = pd.read_csv(ratings_path)
        # links_df = pd.read_csv(links_path)
        # links_small_df = pd.read_csv(links_small_path)
        st.success("Сырые данные успешно загружены!")
        return movies_df, keywords_df, credits_df, ratings_small_df
    except FileNotFoundError as e:
        st.error(f"Ошибка: Файл не найден - {e}. Убедитесь, что файлы CSV находятся в папке '{data_path}'.")
        st.stop()
    except Exception as e:
        st.error(f"Произошла ошибка при загрузке данных: {e}")
        st.stop()

def safe_literal_eval(x):
    """Безопасно парсит строку как литерал Python (список/словарь)."""
    if isinstance(x, str):
        try:
            x_safe = x.replace('None', "'None'").replace('True', "'True'").replace('False', "'False'")
            if x_safe.startswith("'[") and x_safe.endswith("]'"):
                 x_safe = x_safe[1:-1]
            elif x_safe.startswith('"[') and x_safe.endswith(']"'):
                 x_safe = x_safe[1:-1]
            evaluated = ast.literal_eval(x_safe)
            if isinstance(evaluated, list):
                if all(isinstance(item, dict) for item in evaluated) or not evaluated:
                    return evaluated
            return []
        except (ValueError, SyntaxError, TypeError):
            return []
    elif pd.isna(x):
         return []
    elif isinstance(x, list):
        return x
    return []

@st.cache_data
def preprocess_and_merge_data(_movies_df_raw, _keywords_df_raw, _credits_df_raw): # Добавил _ чтобы избежать конфликта имен с глобальными
    """Выполняет предобработку и слияние данных."""
    movies_df = _movies_df_raw.copy()
    keywords_df = _keywords_df_raw.copy()
    credits_df = _credits_df_raw.copy()

    movies_df = movies_df.drop_duplicates(subset='id', keep='first')
    movies_df['id_numeric'] = pd.to_numeric(movies_df['id'], errors='coerce')
    movies_df = movies_df.dropna(subset=['id_numeric'])
    movies_df['id'] = movies_df['id_numeric'].astype('int64')
    movies_df = movies_df.drop(columns=['id_numeric'])

    movies_df = movies_df.dropna(subset=['title'])
    movies_df['overview'] = movies_df['overview'].fillna('')
    movies_df['tagline'] = movies_df['tagline'].fillna('')
    movies_df['genres'] = movies_df['genres'].fillna('[]')
    movies_df['release_date'] = pd.to_datetime(movies_df['release_date'], errors='coerce')
    movies_df = movies_df.dropna(subset=['release_date'])

    numeric_cols_fill_zero = ['vote_average', 'vote_count', 'popularity', 'budget', 'revenue', 'runtime']
    for col in numeric_cols_fill_zero:
        movies_df[col] = pd.to_numeric(movies_df[col], errors='coerce').fillna(0)

    movies_df['budget'] = movies_df['budget'].astype(int)
    movies_df['vote_count'] = movies_df['vote_count'].astype(int)

    movies_df = movies_df[movies_df['adult'] == 'False']
    movies_df = movies_df.drop('adult', axis=1)

    keywords_df['id'] = pd.to_numeric(keywords_df['id'], errors='raise').astype('int64')
    credits_df['id'] = pd.to_numeric(credits_df['id'], errors='raise').astype('int64')

    movies_merged = movies_df.merge(credits_df, on='id', how='inner')
    movies_merged = movies_merged.merge(keywords_df, on='id', how='inner')

    features_to_parse = ['genres', 'cast', 'crew', 'keywords']
    for feature in features_to_parse:
        if feature in movies_merged.columns:
            movies_merged[feature] = movies_merged[feature].apply(safe_literal_eval)

    def get_director(x):
        if isinstance(x, list):
            for i in x:
                if isinstance(i, dict) and i.get('job') == 'Director':
                    return i.get('name', '')
        return ''

    def get_list_from_dict_list(x, key='name'):
         if isinstance(x, list):
             return [str(i.get(key, '')) for i in x if isinstance(i, dict) and i.get(key) is not None]
         return []

    def get_top_actors(x, n=3):
        actors_list = get_list_from_dict_list(x, key='name')
        return actors_list[:n]

    movies_merged['director'] = movies_merged['crew'].apply(get_director)
    movies_merged['actors'] = movies_merged['cast'].apply(get_top_actors)
    movies_merged['genres_list'] = movies_merged['genres'].apply(get_list_from_dict_list)
    movies_merged['keywords_list'] = movies_merged['keywords'].apply(get_list_from_dict_list)

    def clean_name(name):
        if isinstance(name, str):
            cleaned = name.lower().replace(' ', '')
            return cleaned
        return ''

    def clean_list_of_names(lst):
        if isinstance(lst, list):
            return [cleaned for name in lst if (cleaned := clean_name(name))]
        return []

    movies_merged['director_clean'] = movies_merged['director'].apply(clean_name)
    movies_merged['actors_clean'] = movies_merged['actors'].apply(clean_list_of_names)
    movies_merged['genres_clean'] = movies_merged['genres_list'].apply(clean_list_of_names)
    movies_merged['keywords_clean'] = movies_merged['keywords_list'].apply(clean_list_of_names)

    def create_soup(x):
        director = [x['director_clean']] * 3 if x['director_clean'] else []
        return ' '.join(director + x['actors_clean'] + x['genres_clean'] + x['keywords_clean'])

    movies_merged['metadata_soup'] = movies_merged.apply(create_soup, axis=1)

    movies_merged = movies_merged.dropna(subset=['title'])
    movies_merged = movies_merged[movies_merged['title'] != '']
    indices = pd.Series(movies_merged.index, index=movies_merged['title']).drop_duplicates()

    st.success("Предобработка и слияние данных завершены!")
    return movies_merged, indices

# --- Кеширование моделей и матриц ---
@st.cache_resource
def get_tfidf_model_and_matrix(_data): # Используем _data чтобы не конфликтовать
    """Создает и кеширует TF-IDF модель и матрицу для описаний."""
    tfidf_vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
    tfidf_matrix = tfidf_vectorizer.fit_transform(_data['overview'])
    return tfidf_vectorizer, tfidf_matrix

@st.cache_resource
def get_count_model_and_matrix(_data): # Используем _data
    """Создает и кеширует CountVectorizer модель и матрицу для 'супа метаданных'."""
    count_vectorizer_soup = CountVectorizer(stop_words='english')
    count_matrix_soup = count_vectorizer_soup.fit_transform(_data['metadata_soup'])
    return count_vectorizer_soup, count_matrix_soup

@st.cache_resource
def train_svd_model(_ratings_df): # Используем _ratings_df
    """Обучает и кеширует SVD модель."""
    reader = Reader(rating_scale=(1, 5))
    data = Dataset.load_from_df(_ratings_df[['userId', 'movieId', 'rating']], reader)
    trainset = data.build_full_trainset()
    alg = SVD()
    alg.fit(trainset)
    return alg, trainset

# --- Загрузка и обработка данных ---
with st.spinner('Загрузка сырых данных...'):
    movies_df_raw, keywords_df_raw, credits_df_raw, ratings_small_df = load_raw_data(DATA_PATH)

with st.spinner('Предобработка и слияние данных... Это может занять некоторое время.'):
    movies_merged_df, indices = preprocess_and_merge_data(
        movies_df_raw, keywords_df_raw, credits_df_raw
    )

# --- Получение моделей и матриц (после обработки данных) ---
with st.spinner('Создание TF-IDF матрицы...'):
    tfidf_vectorizer, tfidf_matrix = get_tfidf_model_and_matrix(movies_merged_df)
with st.spinner('Создание Count матрицы для метаданных...'):
    count_vectorizer_soup, count_matrix_soup = get_count_model_and_matrix(movies_merged_df)
with st.spinner('Обучение SVD модели...'):
    svd_alg, svd_trainset = train_svd_model(ratings_small_df)

# --- Словарь ID -> Название ---
# Убедимся, что используем правильные ID для маппинга с ratings_small
# Предполагаем, что 'id' в movies_merged_df соответствует 'movieId' в ratings_small_df
# В реальном проекте может потребоваться маппинг через links.csv
movie_id_to_title = pd.Series(movies_merged_df.title.values, index=movies_merged_df.id).to_dict()

# --- Сайдбар для навигации ---
st.sidebar.title("Навигация")
app_mode = st.sidebar.selectbox("Выберите раздел:",
                                ["Обзор данных и визуализации",
                                 "Простой рекомендер (Топ фильмов)",
                                 "Контентный рекомендер (Описание)",
                                 "Контентный рекомендер (Метаданные)",
                                 "Коллаборативная фильтрация (SVD)"])

# --- Основная часть приложения ---

if app_mode == "Обзор данных и визуализации":
    st.header("Обзор данных и визуализации")

    st.subheader("Первые 5 строк обработанного датасета:")
    st.dataframe(movies_merged_df.head())

    st.subheader("Информация об обработанном датасете:")
    buffer = StringIO()
    movies_merged_df.info(buf=buffer)
    s = buffer.getvalue()
    st.text(s)

    st.subheader("Визуализации")

    # --- График 1: Топ-20 Жанров ---
    with st.expander("Распределение жанров (Топ-20)"):
        st.write("Гистограмма самых популярных жанров.")
        try:
            all_genres = [genre for sublist in movies_merged_df['genres_list'] if isinstance(sublist, list) for genre in sublist if genre]
            if all_genres:
                genres_counts = pd.Series(all_genres).value_counts()
                fig1, ax1 = plt.subplots(figsize=(12, 8))
                sns.barplot(x=genres_counts.head(20).values, y=genres_counts.head(20).index, ax=ax1)
                ax1.set_title('Рис.1 Топ-20 самых популярных жанров фильмов')
                ax1.set_xlabel('Количество фильмов')
                ax1.set_ylabel('Жанр')
                plt.tight_layout()
                st.pyplot(fig1)
            else:
                st.warning("Нет данных о жанрах для построения графика.")
        except Exception as e:
            st.error(f"Ошибка при построении графика жанров: {e}")

    # --- График 2: Распределение оценок ---
    with st.expander("Распределение оценок пользователей (ratings_small)"):
        st.write("Гистограмма оценок из датасета `ratings_small.csv`.")
        try:
            fig2, ax2 = plt.subplots(figsize=(10, 6))
            sns.histplot(ratings_small_df['rating'], bins=10, kde=False, ax=ax2)
            ax2.set_title('Рис.2 Распределение оценок пользователей (ratings_small)')
            ax2.set_xlabel('Оценка')
            ax2.set_ylabel('Количество оценок')
            ax2.set_xticks(np.arange(0.5, 5.5, 0.5))
            ax2.grid(True, axis='y')
            st.pyplot(fig2)
        except Exception as e:
            st.error(f"Ошибка при построении графика оценок: {e}")

    # --- График 3: Матрица корреляции ---
    with st.expander("Матрица корреляции числовых признаков"):
        st.write("Тепловая карта корреляции между основными числовыми признаками фильмов.")
        try:
            numeric_cols = ['budget', 'popularity', 'revenue', 'runtime', 'vote_average', 'vote_count']
            valid_numeric_cols = [col for col in numeric_cols if col in movies_merged_df.columns and pd.api.types.is_numeric_dtype(movies_merged_df[col])]
            if len(valid_numeric_cols) > 1:
                correlation_matrix = movies_merged_df[valid_numeric_cols].corr()
                fig3, ax3 = plt.subplots(figsize=(8, 6))
                sns.heatmap(correlation_matrix, annot=True, linewidths=.25, fmt=".2f", cmap='coolwarm', ax=ax3)
                ax3.set_title('Рис.3 Матрица корреляции')
                st.pyplot(fig3)
            else:
                st.warning("Не найдено достаточно числовых столбцов для построения матрицы корреляции.")
        except Exception as e:
            st.error(f"Ошибка при построении матрицы корреляции: {e}")

    # --- График 4: Облако ключевых слов ---
    with st.expander("Облако ключевых слов"):
        st.write("Облако наиболее часто встречающихся ключевых слов.")
        try:
            all_keywords = [keyword for sublist in movies_merged_df['keywords_list'] if isinstance(sublist, list) for keyword in sublist if keyword]
            keywords_text = ' '.join(filter(None, all_keywords))

            if keywords_text:
                stopwords = set(STOPWORDS)
                wordcloud = WordCloud(width=800, height=400, background_color='white', stopwords=stopwords,
                                      max_words=150, collocations=False).generate(keywords_text)
                fig4, ax4 = plt.subplots(figsize=(15, 7))
                ax4.imshow(wordcloud, interpolation='bilinear')
                ax4.axis('off')
                ax4.set_title('Рис.4 Облако слов из ключевых слов сюжета')
                st.pyplot(fig4)
            else:
                st.warning("Нет данных для построения облака ключевых слов.")
        except Exception as e:
            st.error(f"Ошибка при построении облака слов: {e}")

    # --- График 5: Рейтинг vs Количество голосов ---
    with st.expander("Зависимость рейтинга от количества голосов"):
         st.write("Диаграмма рассеяния, показывающая связь между средним рейтингом и количеством голосов.")
         try:
             fig5, ax5 = plt.subplots(figsize=(10, 6))
             # Фильтруем для наглядности, убирая фильмы с очень малым числом голосов
             plot_data = movies_merged_df[movies_merged_df['vote_count'] > 10]
             sns.scatterplot(x='vote_average', y='vote_count', data=plot_data, alpha=0.3, edgecolor=None, ax=ax5)
             ax5.set_title('Рис.5 Средний рейтинг vs Количество голосов (vote_count > 10)')
             ax5.set_xlabel('Средний рейтинг (vote_average)')
             ax5.set_ylabel('Количество голосов (vote_count)')
             st.pyplot(fig5)
         except Exception as e:
             st.error(f"Ошибка при построении диаграммы рассеяния: {e}")


elif app_mode == "Простой рекомендер (Топ фильмов)":
    st.header("Простой рекомендер (Топ фильмов по взвешенному рейтингу)")
    st.markdown("""
    Эта система рекомендует фильмы, имеющие наилучший рейтинг с учетом количества голосов (по формуле IMDb).
    Она не учитывает индивидуальные предпочтения пользователя, а показывает общепризнанные хиты.
    Можно отфильтровать топ по жанру.
    """)

    # Расчет C и m
    C = movies_merged_df['vote_average'].mean()
    # Используем перцентиль из ноутбука, но убедимся, что vote_count - int
    m = movies_merged_df['vote_count'].astype(int).quantile(0.95)

    st.write(f"Средний рейтинг по всем фильмам (C): {C:.2f}")
    st.write(f"Минимальное количество голосов для включения (m, 95-й перцентиль): {int(m)}")

    # Функция для расчета взвешенного рейтинга
    def weighted_rating(x, m=m, C=C):
        v = x['vote_count']
        R = x['vote_average']
        # Формула IMDb
        return (v / (v + m) * R) + (m / (v + m) * C)

    # Создаем копию для расчета и фильтрации
    qualified_movies = movies_merged_df.copy()
    qualified_movies['weighted_rating'] = qualified_movies.apply(weighted_rating, axis=1)

    # Фильтрация по m
    qualified_movies = qualified_movies[qualified_movies['vote_count'] >= m]

    # Выбор жанра
    # Собираем уникальные жанры из списка списков
    all_genres_list = sorted(list(set([genre for sublist in movies_merged_df['genres_list'] if isinstance(sublist, list) for genre in sublist if genre])))
    genre_options = ['Все жанры'] + all_genres_list
    selected_genre = st.selectbox("Выберите жанр для фильтрации:", genre_options)

    # Выбор количества рекомендаций
    top_n_simple = st.slider("Количество рекомендаций:", 5, 50, 15, key="slider_simple")

    # Фильтрация по жанру, если выбран не "Все жанры"
    if selected_genre != 'Все жанры':
        # Фильтруем строки, где выбранный жанр присутствует в списке 'genres_list'
        qualified_movies_genre = qualified_movies[qualified_movies['genres_list'].apply(lambda x: selected_genre in x if isinstance(x, list) else False)]
    else:
        qualified_movies_genre = qualified_movies

    # Сортировка и вывод
    qualified_movies_genre = qualified_movies_genre.sort_values('weighted_rating', ascending=False)

    st.subheader(f"Топ-{top_n_simple} фильмов{' жанра ' + selected_genre if selected_genre != 'Все жанры' else ''}:")
    # Выбираем нужные колонки для отображения
    display_cols_simple = ['title', 'vote_count', 'vote_average', 'weighted_rating', 'release_date', 'genres_list']
    st.dataframe(qualified_movies_genre[display_cols_simple].head(top_n_simple))


elif app_mode == "Контентный рекомендер (Описание)":
    st.header("Контентный рекомендер (на основе описания сюжета)")
    st.markdown("""
    Эта система рекомендует фильмы, похожие на выбранный вами по содержанию их описаний (overview).
    Используется TF-IDF для векторизации текстов и косинусное сходство для поиска похожих.
    """)

    # Выбор фильма (используем отсортированный список уникальных названий из индекса)
    movie_list_content = sorted(indices.index.tolist())
    default_movie_overview = 'The Godfather' if 'The Godfather' in movie_list_content else movie_list_content[0]
    selected_movie_overview = st.selectbox("Выберите фильм, чтобы найти похожие:", movie_list_content, index=movie_list_content.index(default_movie_overview))

    # Выбор количества рекомендаций
    top_n_content_overview = st.slider("Количество рекомендаций:", 5, 20, 10, key="slider_overview")

    # Функция для получения рекомендаций
    # Кешируем вычисление сходства для выбранного фильма
    @st.cache_data
    def get_content_recommendations_overview(title, _indices_map, _tfidf_mat): # Используем _ для кеширования
        if title not in _indices_map:
            return f"Фильм '{title}' не найден в индексе."
        idx = _indices_map[title]
        # Вычисляем сходство только для выбранного фильма со всеми остальными
        cosine_sim = cosine_similarity(_tfidf_mat[idx], _tfidf_mat)
        # Преобразуем в список пар (индекс, сходство)
        sim_scores = list(enumerate(cosine_sim[0]))
        # Сортируем
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        return sim_scores

    # Получение и вывод рекомендаций
    if selected_movie_overview:
        with st.spinner(f"Поиск фильмов, похожих на '{selected_movie_overview}'..."):
            sim_scores_overview = get_content_recommendations_overview(selected_movie_overview, indices, tfidf_matrix)
            if isinstance(sim_scores_overview, str): # Обработка ошибки
                 st.error(sim_scores_overview)
            else:
                 # Отбираем топ N, исключая сам фильм
                 sim_scores_overview = sim_scores_overview[1:top_n_content_overview+1]
                 movie_indices_overview = [i[0] for i in sim_scores_overview]
                 recommendations_df = movies_merged_df.iloc[movie_indices_overview][['title', 'release_date', 'vote_average', 'overview']]
                 # Добавляем столбец со сходством
                 recommendations_df['similarity'] = [f"{i[1]:.3f}" for i in sim_scores_overview]

                 st.subheader(f"Топ-{top_n_content_overview} фильмов, похожих на '{selected_movie_overview}':")
                 st.dataframe(recommendations_df)


elif app_mode == "Контентный рекомендер (Метаданные)":
    st.header("Контентный рекомендер (на основе 'супа' метаданных)")
    st.markdown("""
    Эта система рекомендует фильмы, похожие на выбранный вами, используя комбинацию метаданных:
    режиссер (с большим весом), топ-3 актера, жанры и ключевые слова.
    Используется CountVectorizer и косинусное сходство.
    """)

    # Выбор фильма
    movie_list_soup = sorted(indices.index.tolist())
    default_movie_soup = 'Fight Club' if 'Fight Club' in movie_list_soup else movie_list_soup[0]
    selected_movie_soup = st.selectbox("Выберите фильм, чтобы найти похожие:", movie_list_soup, index=movie_list_soup.index(default_movie_soup))

    # Выбор количества рекомендаций
    top_n_content_soup = st.slider("Количество рекомендаций:", 5, 20, 10, key="slider_soup")

    # Функция для получения рекомендаций (с кешированием расчета сходства)
    @st.cache_data
    def get_content_recommendations_soup(title, _indices_map, _count_mat): # Используем _ для кеширования
        if title not in _indices_map:
            return f"Фильм '{title}' не найден в индексе."
        idx = _indices_map[title]
        # Вычисляем сходство только для выбранного фильма
        cosine_sim_soup = cosine_similarity(_count_mat[idx], _count_mat)
        sim_scores_soup = list(enumerate(cosine_sim_soup[0]))
        sim_scores_soup = sorted(sim_scores_soup, key=lambda x: x[1], reverse=True)
        return sim_scores_soup

    # Получение и вывод рекомендаций
    if selected_movie_soup:
        with st.spinner(f"Поиск фильмов, похожих на '{selected_movie_soup}'..."):
            sim_scores_soup_result = get_content_recommendations_soup(selected_movie_soup, indices, count_matrix_soup)

            if isinstance(sim_scores_soup_result, str):
                 st.error(sim_scores_soup_result)
            else:
                 sim_scores_soup_result = sim_scores_soup_result[1:top_n_content_soup+1]
                 movie_indices_soup = [i[0] for i in sim_scores_soup_result]
                 # Выбираем колонки для отображения
                 display_cols_soup = ['title', 'director', 'actors', 'genres_list', 'keywords_list', 'vote_average']
                 recommendations_soup_df = movies_merged_df.iloc[movie_indices_soup][display_cols_soup]
                 recommendations_soup_df['similarity'] = [f"{i[1]:.3f}" for i in sim_scores_soup_result]

                 st.subheader(f"Топ-{top_n_content_soup} фильмов, похожих на '{selected_movie_soup}':")
                 st.dataframe(recommendations_soup_df)


elif app_mode == "Коллаборативная фильтрация (SVD)":
    st.header("Коллаборативная фильтрация (SVD)")
    st.markdown("""
    Эта система рекомендует фильмы на основе предпочтений похожих пользователей, используя алгоритм SVD.
    Она обучается на данных из `ratings_small.csv`. Введите ID пользователя (от 1 до 671), чтобы получить персональные рекомендации.
    **Примечание:** Рекомендации основаны только на фильмах, присутствующих в `ratings_small.csv`.
    """)

    # Ввод ID пользователя
    max_user_id = ratings_small_df['userId'].max()
    user_id_svd = st.number_input(f"Введите ID пользователя (1-{max_user_id}):", min_value=1, max_value=max_user_id, value=1, step=1)

    # Выбор количества рекомендаций
    top_n_svd = st.slider("Количество рекомендаций:", 5, 20, 10, key="slider_svd")

    # Функция для получения рекомендаций SVD
    # Кешируем результат для конкретного пользователя и N
    @st.cache_data

    def get_svd_recommendations(user_id, _ratings_df, _movie_id_title_map, _alg, _trainset, top_n=10):
        # Получаем внутренний ID пользователя, если он есть в трейнсете
        try:
            user_inner_id = _trainset.to_inner_uid(user_id)
        except ValueError:
            return f"Пользователь с ID={user_id} не найден в обучающем наборе данных."

        # Получаем список ID фильмов, которые пользователь УЖЕ оценил (используем внешние ID)
        user_rated_movie_ids = set(_ratings_df[_ratings_df['userId'] == user_id]['movieId'].tolist())

        # Получаем список ВСЕХ уникальных ID фильмов из обучающего набора (внутренние ID)
        all_movie_inner_ids = list(_trainset.all_items())

        # Предсказываем рейтинги для всех фильмов, которые пользователь НЕ оценил
        predictions = []
        for movie_inner_id in all_movie_inner_ids:
            # Преобразуем внутренний ID фильма обратно во внешний
            movie_id = _trainset.to_raw_iid(movie_inner_id)
            if movie_id not in user_rated_movie_ids:
                predicted_rating = _alg.predict(user_id, movie_id).est
                predictions.append((movie_id, predicted_rating))

        # Сортируем предсказания по рейтингу
        predictions.sort(key=lambda x: x[1], reverse=True)

        # Отбираем топ-N
        top_recommendations = predictions[:top_n]

        # Формируем результат с названиями
        recommended_output = []
        for movie_id, predicted_rating in top_recommendations:
            movie_title = _movie_id_title_map.get(movie_id, f"ID: {movie_id} (Название не найдено)")
            recommended_output.append({"Название": movie_title, "Предсказанный рейтинг": f"{predicted_rating:.2f}"})

        return pd.DataFrame(recommended_output)

    # Получение и вывод рекомендаций по кнопке
    if st.button("Получить рекомендации SVD"):
        with st.spinner(f"Генерация рекомендаций для пользователя {user_id_svd}..."):
            recommendations_svd = get_svd_recommendations(user_id_svd, ratings_small_df, movie_id_to_title, svd_alg, svd_trainset, top_n_svd)
            if isinstance(recommendations_svd, str): # Если вернулась строка ошибки
                st.error(recommendations_svd)
            elif recommendations_svd.empty:
                 st.warning(f"Не удалось сгенерировать рекомендации для пользователя {user_id_svd}. Возможно, для него нет неоцененных фильмов в обучающем наборе.")
            else:
                st.subheader(f"Топ-{top_n_svd} рекомендаций для пользователя {user_id_svd}:")
                st.dataframe(recommendations_svd)

# --- Подвал (опционально) ---
st.sidebar.markdown("---")
st.sidebar.info("Лабораторная работа №2 по Рекомендательным системам.")