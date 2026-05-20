import os
import re
import glob
import logging
from pathlib import Path
from rank_bm25 import BM25Okapi
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
)
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS


class RAGEngine:
    """Движок поиска по базе знаний РБН.

    Архитектура (гибридный поиск + re-ranking):
        1. FAISS  — семантический (dense) поиск
        2. BM25   — ключевые слова (sparse) поиск
        3. Reciprocal Rank Fusion — объединение результатов
        4. Cross-Encoder re-ranker — финальная пересортировка top-K
    """

    PREFERRED_SOURCE_NAMES = {
        "RBN_MAX_BENCHMARKS_2026.md",
        "RBN_MAX_SEGMENT_BENCHMARKS_2026.csv",
        "RBN_MAX_MARKET_FLOW_BENCHMARKS_2026.md",
        "RBN_MAX_MARKET_FLOW_SEGMENTS_2026.csv",
        "RBN_MAX_MARKET_FLOW_DISTRICTS_2026.csv",
    }

    # Заголовки Markdown для structure-aware splitting
    MD_HEADERS = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
    ]

    def __init__(self, docs_dir="docs", index_dir="faiss_index"):
        self.docs_dir = docs_dir
        self.index_dir = index_dir

        self.embeddings = None
        self.reranker = None
        self.vector_store = None
        self.bm25 = None
        self.bm25_chunks = []
        self._initialized = False

    def _docs_dirs(self) -> list[str]:
        """Возвращает список директорий, где могут лежать знания для MAX-бота."""
        env_docs = os.getenv("RBN_DOCS_DIR")
        service_file = Path(__file__).resolve()
        app_root = service_file.parents[1]
        repo_root = app_root.parent

        candidates = [
            Path(env_docs) if env_docs else None,
            Path.cwd() / self.docs_dir,
            repo_root / self.docs_dir,
        ]

        resolved = []
        seen = set()
        for candidate in candidates:
            if not candidate:
                continue
            path = str(candidate.resolve())
            if path in seen:
                continue
            seen.add(path)
            if os.path.isdir(path):
                resolved.append(path)
        return resolved

    def _all_doc_files(self) -> list[str]:
        files = []
        allowed_extensions = {".pdf", ".docx", ".md", ".txt"}
        for docs_dir in self._docs_dirs():
            for f in glob.glob(os.path.join(docs_dir, "**/*.*"), recursive=True):
                ext = os.path.splitext(f)[-1].lower()
                if ext in allowed_extensions:
                    files.append(f)
        if not files:
            return []

        def sort_key(file_path: str):
            source_name = os.path.basename(file_path)
            ext = os.path.splitext(source_name)[-1].lower()
            preferred = 0 if source_name in self.PREFERRED_SOURCE_NAMES else 1
            ext_priority = 0 if ext == ".md" else 1 if ext == ".txt" else 2 if ext == ".docx" else 3
            return (preferred, ext_priority, source_name.lower())

        return sorted(set(files), key=sort_key)

    def _ensure_initialized(self):
        """Ленивая инициализация: загружает модели и индекс при первом обращении."""
        if self._initialized:
            return
        self._initialized = True

        try:
            logging.info("RAG: Инициализация моделей (Gemini Embeddings)...")
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                logging.warning("RAG: GEMINI_API_KEY не найден. RAG отключен.")
                return
                
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=api_key
            )
            self.reranker = None
            self.load_or_build_index()
            logging.info("RAG: Инициализация завершена.")
        except Exception as e:
            logging.error(
                "RAG: Не удалось загрузить модели (%s). "
                "Бот продолжит работу без RAG.",
                e,
            )
            self.embeddings = None
            self.vector_store = None
            self.bm25 = None

    # ------------------------------------------------------------------
    #  Загрузчики файлов
    # ------------------------------------------------------------------

    def get_loader(self, file_path):
        ext = os.path.splitext(file_path)[-1].lower()
        if ext == ".pdf":
            return PyPDFLoader(file_path)
        elif ext in [".docx"]:
            return Docx2txtLoader(file_path)
        elif ext in [".md", ".txt"]:
            return TextLoader(file_path)
        return None

    # ------------------------------------------------------------------
    #  Индексация
    # ------------------------------------------------------------------

    def load_or_build_index(self):
        faiss_path = os.path.join(self.index_dir, "index.faiss")
        if os.path.exists(faiss_path):
            logging.info("RAG: Загрузка существующей базы знаний...")
            self.vector_store = FAISS.load_local(
                self.index_dir,
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
            self._rebuild_bm25_from_faiss()
        else:
            logging.info("RAG: Локальная база индексов не найдена. Собираем...")
            self.rebuild_index()

    def _docs_newer_than_index(self, faiss_path: str) -> bool:
        """Проверяет, есть ли в docs/ файлы новее FAISS-индекса."""
        try:
            index_mtime = os.path.getmtime(faiss_path)
            files = self._all_doc_files()
            for f in files:
                if os.path.getmtime(f) > index_mtime:
                    logging.info("RAG: Файл обновлён: %s", os.path.basename(f))
                    return True
            return False
        except Exception as e:
            logging.warning("RAG: Ошибка проверки актуальности индекса: %s", e)
            return False

    def _rebuild_bm25_from_faiss(self):
        """Восстанавливает BM25-индекс из документов, уже загруженных в FAISS."""
        if not self.vector_store:
            return
        try:
            all_docs = list(self.vector_store.docstore._dict.values())
            self.bm25_chunks = all_docs
            tokenized = [self._tokenize(doc.page_content) for doc in all_docs]
            self.bm25 = BM25Okapi(tokenized)
            logging.info("RAG: BM25-индекс восстановлен из FAISS (%d чанков).", len(all_docs))
        except Exception as e:
            logging.warning("RAG: Не удалось восстановить BM25: %s", e)

    def rebuild_index(self):
        self._ensure_initialized()
        os.makedirs(self.index_dir, exist_ok=True)

        all_docs = []
        files = self._all_doc_files()

        if not files:
            logging.warning("RAG: Папки docs не найдены или пусты. База знаний не загружена.")
            return

        logging.info(
            "RAG: Найдено файлов для загрузки: %d | dirs=%s",
            len(files),
            ", ".join(self._docs_dirs()),
        )
        for file_path in files:
            loader = self.get_loader(file_path)
            if loader:
                try:
                    docs = loader.load()
                    # Добавляем метаданные (имя файла) к каждому документу
                    for doc in docs:
                        doc.metadata["source_name"] = os.path.basename(file_path)
                        doc.metadata["source_path"] = file_path
                    all_docs.extend(docs)
                except Exception as e:
                    logging.error("RAG: Ошибка загрузки %s: %s", file_path, e)

        if not all_docs:
            logging.warning("RAG: Не удалось извлечь текст из файлов.")
            return

        # --- Умное чанкование ---
        chunks = self._smart_split(all_docs)

        logging.info("RAG: Создание эмбеддингов для %d фрагментов...", len(chunks))

        # FAISS (dense)
        self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        self.vector_store.save_local(self.index_dir)

        # BM25 (sparse)
        self.bm25_chunks = chunks
        tokenized = [self._tokenize(doc.page_content) for doc in chunks]
        self.bm25 = BM25Okapi(tokenized)

        logging.info(
            "RAG: Гибридная база знаний собрана! FAISS + BM25 (%d чанков).",
            len(chunks),
        )

    def _smart_split(self, all_docs):
        """Разбивает документы на чанки с учётом структуры Markdown."""
        md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.MD_HEADERS,
            strip_headers=False,
        )
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
        )

        final_chunks = []
        for doc in all_docs:
            source_name = doc.metadata.get("source_name", "unknown")
            ext = os.path.splitext(source_name)[-1].lower()

            if ext == ".md":
                # Markdown-aware splitting: сначала по заголовкам, потом по размеру
                md_chunks = md_splitter.split_text(doc.page_content)
                for md_chunk in md_chunks:
                    # Добавляем заголовок раздела в метаданные
                    section = md_chunk.metadata.get("h2", md_chunk.metadata.get("h1", ""))
                    sub_chunks = text_splitter.split_documents([md_chunk])
                    for sc in sub_chunks:
                        sc.metadata["source_name"] = source_name
                        sc.metadata["section"] = section
                        sc.metadata["source_priority"] = (
                            2 if source_name in self.PREFERRED_SOURCE_NAMES else 0
                        )
                    final_chunks.extend(sub_chunks)
            else:
                # Обычное чанкование для не-Markdown файлов
                sub_chunks = text_splitter.split_documents([doc])
                for sc in sub_chunks:
                    sc.metadata["source_name"] = source_name
                    sc.metadata["source_priority"] = (
                        1 if source_name in self.PREFERRED_SOURCE_NAMES else 0
                    )
                final_chunks.extend(sub_chunks)

        return final_chunks

    # ------------------------------------------------------------------
    #  Поиск (гибридный + re-ranking)
    # ------------------------------------------------------------------

    def search_context(self, query: str, top_k: int = 3) -> str:
        """Гибридный поиск по базе знаний с re-ranking.

        Pipeline:
            1. FAISS → top-10 семантически похожих
            2. BM25  → top-10 по ключевым словам
            3. Reciprocal Rank Fusion → объединение
            4. Cross-Encoder → пересортировка → top-K
        """
        self._ensure_initialized()
        if not self.vector_store:
            return ""

        candidates = {}

        # --- Stage 1a: FAISS (dense search) ---
        try:
            faiss_results = self.vector_store.similarity_search(query, k=10)
            for rank, doc in enumerate(faiss_results):
                doc_id = id(doc)
                candidates[doc_id] = {
                    "doc": doc,
                    "rrf_score": self._rrf_score(rank) + doc.metadata.get("source_priority", 0),
                }
        except Exception as e:
            logging.warning("RAG FAISS search error: %s", e)

        # --- Stage 1b: BM25 (sparse search) ---
        if self.bm25 and self.bm25_chunks:
            try:
                tokenized_query = self._tokenize(query)
                bm25_scores = self.bm25.get_scores(tokenized_query)
                # Сортируем по убыванию скора, берём top-10
                top_indices = sorted(
                    range(len(bm25_scores)),
                    key=lambda i: bm25_scores[i],
                    reverse=True,
                )[:10]

                for rank, idx in enumerate(top_indices):
                    if bm25_scores[idx] <= 0:
                        continue
                    doc = self.bm25_chunks[idx]
                    doc_id = id(doc)
                    if doc_id in candidates:
                        candidates[doc_id]["rrf_score"] += self._rrf_score(rank)
                    else:
                        candidates[doc_id] = {
                            "doc": doc,
                            "rrf_score": self._rrf_score(rank),
                        }
            except Exception as e:
                logging.warning("RAG BM25 search error: %s", e)

        if not candidates:
            return ""

        # --- Stage 2: Сортировка по RRF-скору, берём top-10 кандидатов ---
        sorted_candidates = sorted(
            candidates.values(),
            key=lambda x: x["rrf_score"],
            reverse=True,
        )[:10]

        # --- Stage 3: Re-Ranking (Удалено для оптимизации API-first) ---
        # Просто используем результаты гибридного поиска (FAISS + BM25)
        # Они уже отсортированы по rrf_score

        # --- Формируем финальный контекст ---
        top_results = sorted_candidates[:top_k]
        context_parts = ["=== ВЫДЕРЖКИ ИЗ ВНУТРЕННИХ ДОКУМЕНТОВ РБН ==="]
        for item in top_results:
            doc = item["doc"]
            source = doc.metadata.get("source_name", "Unknown")
            section = doc.metadata.get("section", "")
            header = f"[Файл: {source}]"
            if section:
                header += f" [Раздел: {section}]"
            context_parts.append(f"{header}\n{doc.page_content}")

        return "\n\n".join(context_parts)

    # ------------------------------------------------------------------
    #  Утилиты
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Простая токенизация для BM25 (lowercase + слова)."""
        return re.findall(r"\w+", text.lower())

    @staticmethod
    def _rrf_score(rank: int, k: int = 60) -> float:
        """Reciprocal Rank Fusion score."""
        return 1.0 / (k + rank + 1)


# Синглтон для использования во всех модулях
rag_engine = RAGEngine()
