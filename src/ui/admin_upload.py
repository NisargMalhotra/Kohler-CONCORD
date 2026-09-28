"""
KOHLER CONCORD — Admin Knowledge Base Uploader.

Lets authorized admins (HR Manager, Legal Counsel) upload CSV files
to add new documents to the enterprise knowledge base.
"""

import logging
from typing import List, Optional

import pandas as pd
import streamlit as st

from src.config import Domain, Persona, Document, PERSONA_ACCESS_LEVELS
from src.knowledge_base.chunker import DocumentChunker

logger = logging.getLogger(__name__)

# Roles that can access the admin upload
_ADMIN_ROLES = {Persona.HR_MANAGER, Persona.LEGAL_COUNSEL}

# Auto-detection mappings for common CSV column names
_CONTENT_COLUMNS = [
    "content", "text", "policy_text", "policy text",
    "description", "body", "document",
]
_ID_COLUMNS = [
    "clause_id", "clause id", "policy_id", "policy id",
    "id", "section_id", "section id", "code",
]
_TITLE_COLUMNS = [
    "title", "name", "heading", "section", "topic", "subject",
]


def is_admin(persona: Persona) -> bool:
    """Check if the current persona has admin upload access."""
    return persona in _ADMIN_ROLES


def _auto_detect_column(
    columns: List[str], candidates: List[str]
) -> Optional[str]:
    """Try to auto-detect a column by matching against known names."""
    cols_lower = {c.lower().strip(): c for c in columns}
    for candidate in candidates:
        if candidate in cols_lower:
            return cols_lower[candidate]
    return None


def render_admin_upload(vector_store) -> None:
    """Render the admin knowledge base upload interface."""
    st.markdown("## 📤 Upload Knowledge Base")
    st.caption(
        "Upload a CSV file to add new documents to the enterprise knowledge base. "
        "The data will be chunked, embedded, and indexed — and automatically secured "
        "by the Trust Layer based on the domain and access level you select."
    )

    # ── Domain and access level selection ─────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        domain = st.selectbox(
            "📁 Domain",
            options=[d.value for d in Domain],
            help="All uploaded content will be tagged with this domain "
                 "for routing and permission checks.",
        )
    with col2:
        persona = st.session_state.get("active_persona")
        allowed_levels = PERSONA_ACCESS_LEVELS.get(persona, ["public"])
        access_level = st.selectbox(
            "🔒 Access Level",
            options=allowed_levels,
            help="Controls which roles can see this content. "
                 "Follows existing permission rules.",
        )

    st.divider()

    # ── File uploader ─────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        help="Each row will become a document. You'll map columns "
             "to content and metadata below.",
    )

    if uploaded is None:
        st.info(
            "Upload a CSV to get started. Expected columns: "
            "content/text, clause_id, title (optional)."
        )
        return

    # ── Parse CSV ─────────────────────────────────────────────────────
    try:
        df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"❌ Failed to read CSV: {e}")
        return

    if df.empty:
        st.error("❌ The CSV file is empty.")
        return

    st.success(
        f"✅ Loaded **{len(df)} rows** and **{len(df.columns)} columns**: "
        f"{', '.join(df.columns)}"
    )

    # ── Column mapping ────────────────────────────────────────────────
    st.markdown("### Column Mapping")
    st.caption(
        "Map your CSV columns to the required fields. "
        "We'll try to auto-detect common names."
    )

    columns = list(df.columns)

    # Auto-detect
    auto_content = _auto_detect_column(columns, _CONTENT_COLUMNS)
    auto_id = _auto_detect_column(columns, _ID_COLUMNS)
    auto_title = _auto_detect_column(columns, _TITLE_COLUMNS)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        content_col = st.selectbox(
            "📝 Content column *",
            options=columns,
            index=columns.index(auto_content) if auto_content else 0,
            help="The main text content of each document.",
        )
    with col_b:
        id_options = ["(auto-generate)"] + columns
        default_id_idx = (
            id_options.index(auto_id)
            if auto_id and auto_id in id_options
            else 0
        )
        clause_id_col = st.selectbox(
            "🏷️ Clause ID column",
            options=id_options,
            index=default_id_idx,
            help="Unique identifier for each clause/section. "
                 "Leave as auto-generate if not available.",
        )
    with col_c:
        title_options = ["(none)"] + columns
        default_title_idx = (
            title_options.index(auto_title)
            if auto_title and auto_title in title_options
            else 0
        )
        title_col = st.selectbox(
            "📌 Title column",
            options=title_options,
            index=default_title_idx,
            help="Optional title/heading for each section.",
        )

    # ── Preview ───────────────────────────────────────────────────────
    st.markdown("### Preview")
    st.dataframe(df.head(3), use_container_width=True)

    # ── Process button ────────────────────────────────────────────────
    st.divider()
    if st.button(
        "🚀 Process & Upload to Knowledge Base",
        type="primary",
        use_container_width=True,
    ):
        _process_upload(
            df=df,
            content_col=content_col,
            clause_id_col=(
                clause_id_col if clause_id_col != "(auto-generate)" else None
            ),
            title_col=title_col if title_col != "(none)" else None,
            domain=domain,
            access_level=access_level,
            vector_store=vector_store,
        )


def _process_upload(
    df: pd.DataFrame,
    content_col: str,
    clause_id_col: Optional[str],
    title_col: Optional[str],
    domain: str,
    access_level: str,
    vector_store,
) -> None:
    """Parse, chunk, and upsert CSV data into the vector store."""

    # Validate content column
    if content_col not in df.columns:
        st.error(f"❌ Content column '{content_col}' not found in CSV.")
        return

    # Drop rows with empty content
    df_clean = df.dropna(subset=[content_col])
    df_clean = df_clean[df_clean[content_col].astype(str).str.strip() != ""]

    if df_clean.empty:
        st.error("❌ All rows have empty content. Nothing to upload.")
        return

    skipped = len(df) - len(df_clean)

    with st.spinner("Processing..."):
        # Build Document objects
        documents: List[Document] = []
        for idx, row in df_clean.iterrows():
            content = str(row[content_col]).strip()
            clause_id = (
                str(row[clause_id_col]).strip()
                if clause_id_col and clause_id_col in row.index
                else f"CSV-{domain.upper()}-{idx + 1:03d}"
            )
            title = (
                str(row[title_col]).strip()
                if title_col and title_col in row.index
                else ""
            )

            metadata = {
                "clause_id": clause_id,
                "domain": domain,
                "access_level": access_level,
                "source_file": "csv_upload",
                "title": title,
            }

            documents.append(Document(content=content, metadata=metadata))

        # Chunk
        chunker = DocumentChunker()
        chunks = chunker.chunk_documents(documents)

        # Upsert into vector store
        try:
            ids = []
            texts = []
            metadatas = []
            for chunk in chunks:
                chunk_id = chunk.metadata.get(
                    "chunk_id", f"csv_{hash(chunk.content)}"
                )
                ids.append(chunk_id)
                texts.append(chunk.content)
                flat = {
                    k: (
                        str(v)
                        if not isinstance(v, (str, int, float, bool))
                        else v
                    )
                    for k, v in chunk.metadata.items()
                }
                metadatas.append(flat)

            vector_store.collection.upsert(
                ids=ids, documents=texts, metadatas=metadatas
            )
        except Exception as e:
            st.error(f"❌ Failed to index documents: {e}")
            logger.error(f"CSV upload index error: {e}")
            return

    # ── Confirmation ──────────────────────────────────────────────────
    st.success(
        f"✅ **Upload complete!**\n\n"
        f"- **Rows processed:** {len(df_clean)} "
        f"({skipped} skipped due to empty content)\n"
        f"- **Chunks created:** {len(chunks)}\n"
        f"- **Domain:** {domain}\n"
        f"- **Access Level:** {access_level}\n"
        f"- **Total vectors in store:** {vector_store.collection.count()}"
    )

    # Sample preview
    st.markdown("#### Sample Chunks")
    for i, chunk in enumerate(chunks[:3]):
        with st.expander(
            f"Chunk {i + 1}: {chunk.metadata.get('clause_id', '?')}",
            expanded=(i == 0),
        ):
            st.markdown(
                chunk.content[:300]
                + ("…" if len(chunk.content) > 300 else "")
            )
            st.caption(
                f"Domain: {chunk.metadata.get('domain')} | "
                f"Access: {chunk.metadata.get('access_level')} | "
                f"Source: csv_upload"
            )
