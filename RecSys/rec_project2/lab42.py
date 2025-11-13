# lab4/2.py
import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity
import os

# --- Константы и Настройки ---
FEATURES_PATH = 'best_model_features.npy'
IDS_PATH = 'product_ids.npy'
METADATA_PATH_PROCESSED = 'processed_metadata.pkl'
TOP_N_RECOMMENDATIONS = 6 # Сколько рекомендаций показывать

# --- Функции ---

@st.cache_data # Кэшируем данные, чтобы не грузить их каждый раз
def load_data(features_path, ids_path, metadata_path):
    """Загружает эмбеддинги, ID и метаданные."""
    if not os.path.exists(features_path) or \
       not os.path.exists(ids_path) or \
       not os.path.exists(metadata_path):
        st.error("Ошибка: Один или несколько файлов данных не найдены! "
                 f"Убедитесь, что '{features_path}', '{ids_path}' и '{metadata_path}' "
                 "находятся в той же папке, что и скрипт streamlit.")
        return None, None, None

    try:
        features = np.load(features_path)
        product_ids = np.load(ids_path, allow_pickle=True).tolist() # Загружаем ID, преобразуем в список
        metadata_df = pd.read_pickle(metadata_path)

        # Важная проверка: соответствие размеров
        if features.shape[0] != len(product_ids) or len(product_ids) != len(metadata_df):
             st.error(f"Ошибка: Несоответствие размеров загруженных данных! "
                      f"Фичи: {features.shape[0]}, ID: {len(product_ids)}, Метаданные: {len(metadata_df)}")
             return None, None, None

        # Убедимся, что ID в metadata_df соответствует порядку product_ids
        metadata_df = metadata_df.set_index('id').loc[product_ids].reset_index()

        return features, product_ids, metadata_df
    except Exception as e:
        st.error(f"Ошибка при загрузке данных: {e}")
        return None, None, None

def get_recommendations_streamlit(product_id, features_matrix, product_ids_list, metadata_df, top_n):
    """Находит top_n похожих товаров для streamlit."""
    try:
        product_idx = product_ids_list.index(product_id)
        product_features = features_matrix[product_idx].reshape(1, -1)
        similarities = cosine_similarity(product_features, features_matrix)[0]
        most_similar_indices = np.argsort(similarities)[::-1]
        recommended_indices = [idx for idx in most_similar_indices if idx != product_idx][:top_n]

        # Возвращаем DataFrame с рекомендованными товарами и их схожестью
        recs_df = metadata_df.iloc[recommended_indices].copy()
        recs_df['similarity'] = similarities[recommended_indices]
        return recs_df

    except ValueError:
        st.warning(f"Товар с ID {product_id} не найден в данных.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Ошибка при получении рекомендаций: {e}")
        return pd.DataFrame()

# --- Основное приложение Streamlit ---

st.set_page_config(layout="wide", page_title="Рекомендательная система одежды")

st.title("👕 Рекомендательная система одежды")
st.write("Выберите товар по фильтрам или ID, чтобы увидеть похожие.")

# Загрузка данных
features, product_ids, df_metadata = load_data(FEATURES_PATH, IDS_PATH, METADATA_PATH_PROCESSED)

# Если данные не загрузились, останавливаем приложение
if features is None or product_ids is None or df_metadata is None:
    st.stop()

# --- Боковая панель с фильтрами ---
st.sidebar.header("Фильтры товаров")

# Получаем уникальные значения для фильтров (исключая возможные ошибки)
try:
    all_master_categories = ['Любая'] + sorted(df_metadata['masterCategory'].unique().tolist())
    all_sub_categories = ['Любая'] + sorted(df_metadata['subCategory'].unique().tolist())
    all_seasons = ['Любой'] + sorted(df_metadata['season'].dropna().unique().tolist()) # Добавил dropna() на всякий случай
    all_genders = ['Любой'] + sorted(df_metadata['gender'].dropna().unique().tolist())
    all_usages = ['Любое'] + sorted(df_metadata['usage'].dropna().unique().tolist())
except KeyError as e:
    st.sidebar.error(f"Ошибка: Отсутствует необходимая колонка в метаданных: {e}. Фильтрация невозможна.")
    all_master_categories, all_sub_categories, all_seasons, all_genders, all_usages = [['Любая']]*5


# Создаем виджеты фильтров
selected_master_category = st.sidebar.selectbox("Основная категория:", all_master_categories)
selected_sub_category = st.sidebar.selectbox("Подкатегория:", all_sub_categories)
selected_season = st.sidebar.selectbox("Сезон:", all_seasons)
selected_gender = st.sidebar.selectbox("Пол:", all_genders)
selected_usage = st.sidebar.selectbox("Назначение:", all_usages)

# Фильтрация DataFrame
df_filtered = df_metadata.copy()
if selected_master_category != 'Любая':
    df_filtered = df_filtered[df_filtered['masterCategory'] == selected_master_category]
if selected_sub_category != 'Любая':
    df_filtered = df_filtered[df_filtered['subCategory'] == selected_sub_category]
if selected_season != 'Любой':
    df_filtered = df_filtered[df_filtered['season'] == selected_season]
if selected_gender != 'Любой':
    df_filtered = df_filtered[df_filtered['gender'] == selected_gender]
if selected_usage != 'Любое':
    df_filtered = df_filtered[df_filtered['usage'] == selected_usage]

# --- Выбор товара ---
st.header("Выберите товар для рекомендации")

if df_filtered.empty:
    st.warning("По заданным фильтрам товары не найдены. Попробуйте изменить критерии.")
else:
    # Создаем список для выбора: "ID - Название"
    product_options = {
        f"{row['id']} - {str(row['productDisplayName'])[:50]}...": row['id']
        for index, row in df_filtered.iterrows()
    }
    selected_product_display = st.selectbox(
        "Найденные товары:",
        options=list(product_options.keys()),
        index=0
    )

    # Получаем ID выбранного товара
    selected_product_id = product_options.get(selected_product_display)

    # --- Отображение выбранного товара и рекомендаций ---
    if selected_product_id:
        st.subheader("Выбранный товар:")
        selected_product_data = df_metadata[df_metadata['id'] == selected_product_id].iloc[0]

        col1, col2 = st.columns([1, 3])

        with col1:
            try:
                image = Image.open(selected_product_data['image_path'])
                # ИЗМЕНЕНИЕ ЗДЕСЬ:
                st.image(image, use_container_width=True)
            except FileNotFoundError:
                st.error("Изображение не найдено.")
            except Exception as e:
                st.error(f"Ошибка загрузки изображения: {e}")

        with col2:
            st.markdown(f"**ID:** {selected_product_data['id']}")
            st.markdown(f"**Название:** {selected_product_data.get('productDisplayName', 'N/A')}")
            st.markdown(f"**Категория:** {selected_product_data.get('masterCategory', 'N/A')} / {selected_product_data.get('subCategory', 'N/A')}")
            st.markdown(f"**Тип:** {selected_product_data.get('articleType', 'N/A')}")
            st.markdown(f"**Пол:** {selected_product_data.get('gender', 'N/A')} | **Сезон:** {selected_product_data.get('season', 'N/A')} | **Назначение:** {selected_product_data.get('usage', 'N/A')}")
            st.markdown(f"**Цвет:** {selected_product_data.get('baseColour', 'N/A')} | **Год:** {selected_product_data.get('year', 'N/A')}")


        st.subheader("Рекомендованные товары:")
        recommendations_df = get_recommendations_streamlit(
            selected_product_id, features, product_ids, df_metadata, TOP_N_RECOMMENDATIONS
        )

        if not recommendations_df.empty:
            cols = st.columns(TOP_N_RECOMMENDATIONS)
            for i, (index, row) in enumerate(recommendations_df.iterrows()):
                with cols[i]:
                    st.markdown(f"**ID:** {row['id']}")
                    try:
                        rec_image = Image.open(row['image_path'])
                        # И ИЗМЕНЕНИЕ ЗДЕСЬ:
                        st.image(rec_image, use_container_width=True, caption=f"{row['subCategory']} (Sim: {row['similarity']:.3f})")
                    except FileNotFoundError:
                        st.error(f"Img ID:{row['id']} not found")
                    except Exception as e:
                        st.error(f"Err ID:{row['id']}")

        else:
            st.info("Не удалось найти рекомендации для этого товара.")

# Дополнительная информация
st.sidebar.markdown("---")
st.sidebar.info(f"Система работает на выборке из **{len(df_metadata)}** товаров.")