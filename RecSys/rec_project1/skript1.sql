-- Удаляем таблицы в обратном порядке зависимостей, если они существуют (для полной очистки)
DROP TABLE IF EXISTS movie_crew CASCADE;
DROP TABLE IF EXISTS movie_cast CASCADE;
DROP TABLE IF EXISTS movie_keywords CASCADE;
DROP TABLE IF EXISTS movie_genres CASCADE;
DROP TABLE IF EXISTS ratings CASCADE;
DROP TABLE IF EXISTS movies CASCADE;
DROP TABLE IF EXISTS people CASCADE;
DROP TABLE IF EXISTS keywords CASCADE;
DROP TABLE IF EXISTS genres CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Таблица пользователей
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY
);

-- Таблица жанров (справочник)
CREATE TABLE genres (
    genre_id INTEGER PRIMARY KEY, -- Используем ID из CSV, если они консистентны. Или SERIAL, если будем добавлять.
                                -- Для TMDB жанры имеют стабильные ID.
    name VARCHAR(255) NOT NULL UNIQUE
);

-- Таблица ключевых слов (справочник)
CREATE TABLE keywords (
    keyword_id INTEGER PRIMARY KEY, -- Используем ID из CSV
    name VARCHAR(255) NOT NULL -- Уникальность имени здесь не гарантируется, разные ID могут иметь одинаковые name
);

-- Таблица людей (актеры, съемочная группа - справочник)
CREATE TABLE people (
    person_id INTEGER PRIMARY KEY, -- Это id из credits.csv
    name VARCHAR(500) NOT NULL,
    gender INTEGER,
    profile_path VARCHAR(255)
);

-- Таблица фильмов (основная информация)
CREATE TABLE movies (
    movie_id INTEGER PRIMARY KEY,       -- Это movieId из links_small.csv и ratings_small.csv
    tmdb_id INTEGER UNIQUE,             -- Это id из movies_metadata.csv (TMDB ID)
    imdb_id VARCHAR(20) UNIQUE,         -- Это imdbId из links_small.csv
    title VARCHAR(500) NOT NULL,
    overview TEXT,
    release_date DATE,
    runtime INTEGER,
    original_language VARCHAR(10),
    poster_path VARCHAR(255),
    popularity REAL,
    vote_average_tmdb REAL,
    vote_count_tmdb INTEGER,
    status VARCHAR(50),
    tagline TEXT
);

-- Таблица оценок
CREATE TABLE ratings (
    rating_id SERIAL PRIMARY KEY, -- Автоинкремент для уникальности каждой записи оценки
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    rating REAL NOT NULL CHECK (rating >= 0.5 AND rating <= 5.0),
    timestamp_val BIGINT,
    CONSTRAINT uq_user_movie_rating UNIQUE (user_id, movie_id)
);

-- Связующая таблица Фильмы-Жанры
CREATE TABLE movie_genres (
    movie_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,
    PRIMARY KEY (movie_id, genre_id)
);

-- Связующая таблица Фильмы-Ключевые слова
CREATE TABLE movie_keywords (
    movie_id INTEGER NOT NULL, -- Сюда будем писать наш movies.movie_id после маппинга tmdb_id -> movie_id
    keyword_id INTEGER NOT NULL,
    PRIMARY KEY (movie_id, keyword_id)
);

-- Связующая таблица Актерский состав фильма
CREATE TABLE movie_cast (
    movie_cast_id SERIAL PRIMARY KEY,
    movie_id INTEGER NOT NULL,    -- Сюда будем писать наш movies.movie_id после маппинга tmdb_id -> movie_id
    person_id INTEGER NOT NULL,
    character_name VARCHAR(1000),
    cast_order INTEGER
);

-- Связующая таблица Съемочная группа фильма
CREATE TABLE movie_crew (
    movie_crew_id SERIAL PRIMARY KEY,
    movie_id INTEGER NOT NULL,    -- Сюда будем писать наш movies.movie_id после маппинга tmdb_id -> movie_id
    person_id INTEGER NOT NULL,
    job VARCHAR(255),
    department VARCHAR(255)
);

-- Добавление внешних ключей

ALTER TABLE ratings
    ADD CONSTRAINT fk_ratings_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_ratings_movie FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE;

ALTER TABLE movie_genres
    ADD CONSTRAINT fk_moviegenres_movie FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_moviegenres_genre FOREIGN KEY (genre_id) REFERENCES genres(genre_id) ON DELETE CASCADE;

ALTER TABLE movie_keywords
    ADD CONSTRAINT fk_moviekeywords_movie FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_moviekeywords_keyword FOREIGN KEY (keyword_id) REFERENCES keywords(keyword_id) ON DELETE CASCADE;

ALTER TABLE movie_cast
    ADD CONSTRAINT fk_moviecast_movie FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_moviecast_person FOREIGN KEY (person_id) REFERENCES people(person_id) ON DELETE CASCADE;

ALTER TABLE movie_crew
    ADD CONSTRAINT fk_moviecrew_movie FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_moviecrew_person FOREIGN KEY (person_id) REFERENCES people(person_id) ON DELETE CASCADE;

-- Дополнительные индексы для ускорения (если PostgreSQL не создает их автоматически для FK)
CREATE INDEX IF NOT EXISTS idx_ratings_user_id ON ratings(user_id);
CREATE INDEX IF NOT EXISTS idx_ratings_movie_id ON ratings(movie_id);

CREATE INDEX IF NOT EXISTS idx_movie_genres_movie_id ON movie_genres(movie_id);
CREATE INDEX IF NOT EXISTS idx_movie_genres_genre_id ON movie_genres(genre_id);

CREATE INDEX IF NOT EXISTS idx_movie_keywords_movie_id ON movie_keywords(movie_id);
CREATE INDEX IF NOT EXISTS idx_movie_keywords_keyword_id ON movie_keywords(keyword_id);

CREATE INDEX IF NOT EXISTS idx_movie_cast_movie_id ON movie_cast(movie_id);
CREATE INDEX IF NOT EXISTS idx_movie_cast_person_id ON movie_cast(person_id);

CREATE INDEX IF NOT EXISTS idx_movie_crew_movie_id ON movie_crew(movie_id);
CREATE INDEX IF NOT EXISTS idx_movie_crew_person_id ON movie_crew(person_id);

CREATE INDEX IF NOT EXISTS idx_movies_tmdb_id ON movies(tmdb_id); -- Для быстрого поиска по tmdb_id