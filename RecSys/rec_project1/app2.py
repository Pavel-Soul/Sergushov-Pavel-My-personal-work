import streamlit as st
import pandas as pd
import numpy as np
import pickle
import os
import random
import requests

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(layout="wide", page_title="Movie Recommender", page_icon="🎬")

# --- Константы ---
ARTIFACTS_DIR = "streamlit_app_artifacts"
EMOJI_PLACEHOLDERS = ['🍿', '🎬', '🎞️', '🎟️', '🎭', '🎥', '📺', '🌟', '👽', '🤖', '🧙', '🧛', '🧟', '🕵️']

# --- Загрузка артефактов ---
@st.cache_data
def load_artifacts():
    # (Код этой функции остается без изменений)
    artifacts = {}
    files_to_load = {
        'cosine_sim_matrix': ('cosine_similarity_matrix.npy', np.load),
        'movie_indices': ('movie_indices.pkl', pickle.load),
        'movie_titles': ('movie_titles.pkl', pickle.load),
        'movies_display_info': ('movies_display_info.pkl', pd.read_pickle),
        'svd_model': ('svd_model.pkl', pickle.load),
        'surprise_trainset': ('surprise_full_trainset.pkl', pickle.load),
        'ratings_data': ('ratings_data.pkl', pd.read_pickle),
        'movie_stats': ('movie_stats.pkl', pd.read_pickle)
    }
    try:
        for key, (filename, load_func) in files_to_load.items():
            path = os.path.join(ARTIFACTS_DIR, filename)
            if not os.path.exists(path):
                st.error(f"Критическая ошибка: Файл артефакта не найден - {path}."); return None
            if load_func == np.load: artifacts[key] = load_func(path)
            elif load_func == pd.read_pickle: artifacts[key] = load_func(path)
            else:
                with open(path, 'rb') as f: artifacts[key] = load_func(f)
        artifacts['matrix_idx_to_movie_id'] = pd.Series(artifacts['movie_indices'].index, index=artifacts['movie_indices'].values)
        artifacts['example_user_ids'] = {"Новичок": 668, "Жанровый Энтузиаст": 564, "Киноман": 547}
        return artifacts
    except Exception as e: st.error(f"Ошибка при загрузке артефактов: {e}"); return None

artifacts = load_artifacts()

# --- Функции рекомендаций  ---
def get_content_based_recommendations_st(movie_id, top_n=10):
    if artifacts is None or artifacts.get('cosine_sim_matrix') is None: return pd.DataFrame()
    cosine_sim_matrix, movie_indices_map, movie_titles_map, matrix_idx_to_movie_id_map = artifacts['cosine_sim_matrix'], artifacts['movie_indices'], artifacts['movie_titles'], artifacts['matrix_idx_to_movie_id']
    if movie_id not in movie_indices_map: return pd.DataFrame()
    idx = movie_indices_map[movie_id]
    sim_scores = sorted(list(enumerate(cosine_sim_matrix[idx])), key=lambda x: x[1], reverse=True)
    top_similar_movies_indices = [i[0] for i in sim_scores[1:top_n+1]]
    recommended_movie_ids = [matrix_idx_to_movie_id_map.get(i) for i in top_similar_movies_indices]
    valid_recs = [(mid, score[1]) for mid, score in zip(recommended_movie_ids, sim_scores[1:top_n+1]) if mid is not None]
    if not valid_recs: return pd.DataFrame()
    df = pd.DataFrame(valid_recs, columns=['movie_id', 'similarity_score'])
    df['title'] = df['movie_id'].map(artifacts['movie_titles'])
    return df

def get_top_n_collaborative_recommendations_st(user_id, top_n=10):
    if artifacts is None or artifacts.get('svd_model') is None: return pd.DataFrame()
    model, trainset, all_movie_titles = artifacts['svd_model'], artifacts['surprise_trainset'], artifacts['movie_titles']
    try: user_inner_id = trainset.to_inner_uid(user_id)
    except ValueError: return pd.DataFrame()
    user_rated_items_inner_ids = {item_inner_id for (item_inner_id, _) in trainset.ur[user_inner_id]}
    all_movie_inner_ids = list(trainset.all_items())
    predictions = [(trainset.to_raw_iid(iid), model.predict(user_id, trainset.to_raw_iid(iid)).est) for iid in all_movie_inner_ids if iid not in user_rated_items_inner_ids]
    predictions.sort(key=lambda x: x[1], reverse=True)
    return pd.DataFrame([{'movie_id': mid, 'title': all_movie_titles.get(mid, "N/A"), 'estimated_rating': est} for mid, est in predictions[:top_n]])

def get_hybrid_recommendations_st(user_id, example_movie_id, top_n=10, n_recs=20):
    if artifacts is None: return pd.DataFrame()
    content_recs_df = get_content_based_recommendations_st(example_movie_id, top_n=n_recs)
    cf_recs_df = get_top_n_collaborative_recommendations_st(user_id, top_n=n_recs)
    hybrid_scores = {}
    if not content_recs_df.empty:
        for i, row in content_recs_df.iterrows():
            points = n_recs - i; hybrid_scores[row['movie_id']] = {'score': points, 'title': row['title']}
    if not cf_recs_df.empty:
        for i, row in cf_recs_df.iterrows():
            points = n_recs - i
            if row['movie_id'] in hybrid_scores: hybrid_scores[row['movie_id']]['score'] += points
            else: hybrid_scores[row['movie_id']] = {'score': points, 'title': row['title']}
    if not hybrid_scores: return pd.DataFrame()
    recs_list = [{'movie_id': mid, 'title': data['title'], 'hybrid_score': data['score']} for mid, data in hybrid_scores.items()]
    hybrid_df = pd.DataFrame(recs_list); hybrid_df.sort_values(by='hybrid_score', ascending=False, inplace=True)
    return hybrid_df[hybrid_df['movie_id'] != example_movie_id].head(top_n)

# ---  функция для проверки URL с кэшированием ---
@st.cache_data
def is_poster_available(url):
    try:
        response = requests.head(url, timeout=2)
        return response.status_code == 200
    except requests.RequestException:
        return False

# --- функции отображения ---
def display_recommendations(recs_df, score_column_name='score'):
    if recs_df.empty: st.info("Нет рекомендаций для отображения."); return
    movies_info = artifacts.get('movies_display_info')
    if movies_info is None: st.dataframe(recs_df); return
    base_poster_url = "https://image.tmdb.org/t/p/w185" 
    cols_per_row = 5
    for i in range(0, len(recs_df), cols_per_row):
        row_items = recs_df.iloc[i:i+cols_per_row]
        cols = st.columns(len(row_items))
        for idx, (col, (_, rec_row)) in enumerate(zip(cols, row_items.iterrows())):
            movie_detail = movies_info[movies_info['movie_id'] == rec_row['movie_id']]
            with col:
                title = movie_detail['title'].iloc[0] if not movie_detail.empty else rec_row.get('title', 'N/A')
                st.subheader(title)
                st.caption(f"(ID: {rec_row['movie_id']})")
                
                poster_path, overview, genres = None, None, None
                if not movie_detail.empty:
                    path_val = movie_detail['poster_path'].iloc[0]
                    if pd.notna(path_val) and isinstance(path_val, str) and path_val.startswith('/'): poster_path = path_val
                    overview_val = movie_detail['overview'].iloc[0]
                    if pd.notna(overview_val) and overview_val != '': overview = overview_val
                    genres_val = movie_detail['genres_list'].iloc[0]
                    if pd.notna(genres_val) and genres_val != '': genres = genres_val

                full_url = base_poster_url + poster_path if poster_path else None
                
                # ИСПРАВЛЕНИЕ: Замена st.image на более надежный HTML-блок
                if full_url and is_poster_available(full_url):
                    st.markdown(f'<img src="{full_url}" style="width: 100%; height: 278px; object-fit: cover; border-radius: 8px;">', unsafe_allow_html=True)
                else:
                    st.markdown(f'''
                        <div style="display: flex; align-items: center; justify-content: center; height: 278px; border-radius: 8px; background-color: #262730;">
                            <span style="font-size: 96px;">{random.choice(EMOJI_PLACEHOLDERS)}</span>
                        </div>
                    ''', unsafe_allow_html=True)
                
                if score_column_name in rec_row: st.caption(f"Score: {rec_row[score_column_name]:.3f}")
                with st.expander("Детали"):
                    if genres: st.write(f"**Жанры:** {genres}")
                    if overview: st.write(f"**Описание:** {overview}")
                    if not genres and not overview: st.write("Дополнительная информация отсутствует.")

# --- ЛОГИКА UI STREAMLIT (без изменений) ---
if artifacts is None: st.error("Критическая ошибка: Не удалось загрузить артефакты. Приложение не может работать."); st.stop()
def login_as(persona_name): st.session_state.app_stage = 'main_app'; st.session_state.user_persona = persona_name; st.session_state.user_id = artifacts['example_user_ids'][persona_name]
def logout(): st.session_state.app_stage = 'login_screen'; st.session_state.user_persona = None; st.session_state.user_id = None
if 'app_stage' not in st.session_state: st.session_state.app_stage = 'login_screen'; st.session_state.user_persona = None; st.session_state.user_id = None
if st.session_state.app_stage == 'login_screen':
    st.title("🎬 Добро пожаловать в Систему Рекомендаций!"); st.header("Пожалуйста, выберите ваш профиль, чтобы продолжить")
    col1, col2, col3 = st.columns(3, gap="large")
    with col1:
        with st.container(border=True): st.markdown("<h3 style='text-align: center;'>Я Новичок 🎟️</h3>", unsafe_allow_html=True); st.caption("Только начинаю, покажите мне самое популярное!"); st.button("Выбрать профиль 'Новичок'", use_container_width=True, type="primary", on_click=login_as, args=("Новичок",), key="login_newbie")
    with col2:
        with st.container(border=True): st.markdown("<h3 style='text-align: center;'>Я Жанровый Энтузиаст 🚀</h3>", unsafe_allow_html=True); st.caption("Люблю научную фантастику и ищу что-то похожее."); st.button("Выбрать профиль 'Энтузиаст'", use_container_width=True, type="primary", on_click=login_as, args=("Жанровый Энтузиаст (Sci-Fi)",), key="login_enthusiast")
    with col3:
        with st.container(border=True): st.markdown("<h3 style='text-align: center;'>Я Киноман 🧐</h3>", unsafe_allow_html=True); st.caption("Смотрел много всего, удивите меня!"); st.button("Выбрать профиль 'Киноман'", use_container_width=True, type="primary", on_click=login_as, args=("Киноман / Эксплорер",), key="login_cinephile")
elif st.session_state.app_stage == 'main_app':
    st.sidebar.success(f"Вы вошли как:\n**{st.session_state.user_persona}**"); st.sidebar.caption(f"Ваш User ID: {st.session_state.user_id}"); st.sidebar.button("Выйти и сменить профиль", on_click=logout, use_container_width=True); st.sidebar.markdown("---"); st.sidebar.info("Лабораторная работа по Рекомендательным Системам.")
    st.title(f"🎬 Рекомендации для '{st.session_state.user_persona}'")
    if 'all_movie_titles_list' not in st.session_state: st.session_state.all_movie_titles_list = ["--- Выберите фильм ---"] + sorted([f"{artifacts['movie_titles'].get(mid, f'ID {mid} без названия')} (ID: {mid})" for mid in artifacts['movie_indices'].index])
    reco_type = st.selectbox("Выберите тип рекомендаций:",["--- Выберите ---","Персональные для меня (Коллаборативная фильтрация)","Похожие на фильм, который мне нравится (Контентная фильтрация)","Гибридные (лучшее из двух миров)"])
    if reco_type == "Персональные для меня (Коллаборативная фильтрация)":
        st.subheader(f"Персональные рекомендации для вас");
        with st.spinner("Подбираем фильмы на основе ваших оценок..."): svd_recs = get_top_n_collaborative_recommendations_st(int(st.session_state.user_id));
        display_recommendations(svd_recs, score_column_name='estimated_rating')
    elif reco_type == "Похожие на фильм, который мне нравится (Контентная фильтрация)":
        st.subheader("Найдите фильмы, похожие на..."); selected_movie_display = st.selectbox("Выберите фильм-пример:", options=st.session_state.all_movie_titles_list)
        if selected_movie_display != "--- Выберите фильм ---":
            example_movie_id = int(selected_movie_display.split("(ID: ")[1][:-1])
            with st.spinner(f"Ищем фильмы, похожие на '{artifacts['movie_titles'].get(example_movie_id)}'..."): cb_recs = get_content_based_recommendations_st(example_movie_id);
            display_recommendations(cb_recs, score_column_name='similarity_score')
    elif reco_type == "Гибридные (лучшее из двух миров)":
        st.subheader("Получите гибридные рекомендации"); st.info("Этот метод сочетает ваши персональные предпочтения и схожесть контента фильмов. Выберите фильм-пример.")
        selected_movie_display_hybrid = st.selectbox("Сначала выберите фильм-пример для контентной части:", options=st.session_state.all_movie_titles_list, key="hybrid_movie_select")
        if selected_movie_display_hybrid != "--- Выберите фильм ---":
            try:
                example_movie_id_hybrid = int(selected_movie_display_hybrid.split("(ID: ")[1][:-1])
                st.write(f"Теперь мы скомбинируем фильмы, похожие на **'{artifacts['movie_titles'].get(example_movie_id_hybrid)}'**, с вашими личными предпочтениями.")
                with st.spinner("Создаем магию гибридных рекомендаций..."): hybrid_recs = get_hybrid_recommendations_st(user_id=int(st.session_state.user_id), example_movie_id=example_movie_id_hybrid)
                display_recommendations(hybrid_recs, score_column_name='hybrid_score')
            except (IndexError, ValueError): st.error("Некорректный формат выбранного фильма-примера. Пожалуйста, выберите из списка.")