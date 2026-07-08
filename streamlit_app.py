import os
import re
import uuid
import unicodedata
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from databricks.sdk import WorkspaceClient


# ------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ------------------------------------------------------------

st.set_page_config(
    page_title="Asistente de Traspasos AFORE",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ------------------------------------------------------------
# CONSTANTES VISUALES PROFUTURO
# ------------------------------------------------------------

LOGO_PATH = "assets/profuturo_logo_horizontal.png"
ICON_PATH = "assets/profuturo_logo.png"

PROFUTURO_COLORS = {
    "blue": "#004B8D",
    "dark_blue": "#002B5C",
    "deep_blue": "#003B73",
    "light_blue": "#00A6D6",
    "gold": "#F6B221",
    "orange": "#F28C28",
    "gray": "#6B7280",
    "light_gray": "#F3F6FA",
    "white": "#FFFFFF",
    "text": "#1A1A1A"
}

PROFUTURO_COLOR_SEQUENCE = [
    PROFUTURO_COLORS["blue"],
    PROFUTURO_COLORS["gold"],
    PROFUTURO_COLORS["light_blue"],
    PROFUTURO_COLORS["orange"],
    PROFUTURO_COLORS["dark_blue"],
    PROFUTURO_COLORS["gray"]
]

AFORE_CODE_MAP = {
    "552": "Banamex",
    "568": "Profuturo",
    "556": "Coppel",
    "594": "Azteca",
    "578": "SURA",
    "602": "Inbursa",
    "607": "Principal",
    "586": "PensionISSSTE",
    "617": "XXI Banorte",
    "530": "Citibanamex"
}

MONTH_ORDER = {
    "enero": 1, "ene": 1, "jan": 1, "january": 1,
    "febrero": 2, "feb": 2, "february": 2,
    "marzo": 3, "mar": 3, "march": 3,
    "abril": 4, "abr": 4, "apr": 4, "april": 4,
    "mayo": 5, "may": 5,
    "junio": 6, "jun": 6, "june": 6,
    "julio": 7, "jul": 7, "july": 7,
    "agosto": 8, "ago": 8, "aug": 8, "august": 8,
    "septiembre": 9, "setiembre": 9, "sep": 9, "sept": 9, "september": 9,
    "octubre": 10, "oct": 10, "october": 10,
    "noviembre": 11, "nov": 11, "november": 11,
    "diciembre": 12, "dic": 12, "dec": 12, "december": 12
}

MONTH_SHORT_NAMES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
}


def parse_month_to_number(value):
    """
    Convierte valores de mes a número, aunque vengan como:
    1, 1.0, Ene, Feb 1, febrero, 2025-02-01 o timestamps.
    """
    if pd.isna(value):
        return None

    # Mes numérico: 1, 2, 3...
    try:
        month_num = int(float(str(value).strip()))
        if 1 <= month_num <= 12:
            return month_num
    except Exception:
        pass

    raw = str(value).strip()
    raw_norm = normalize_text(raw)
    raw_norm = re.sub(r"[^a-z0-9\s]", " ", raw_norm)
    raw_norm = re.sub(r"\s+", " ", raw_norm).strip()
    first_token = raw_norm.split()[0] if raw_norm else raw_norm

    if first_token in MONTH_ORDER:
        return MONTH_ORDER[first_token]

    # Fecha completa o timestamp.
    try:
        parsed = pd.to_datetime(value, errors="coerce")
        if not pd.isna(parsed):
            return int(parsed.month)
    except Exception:
        pass

    return None


TIME_COLUMN_EXACT_NAMES = {
    "fecha", "date", "periodo", "mes", "month", "anio", "ano", "año", "year"
}


# ------------------------------------------------------------
# LOGO
# ------------------------------------------------------------

if os.path.exists(LOGO_PATH) and os.path.exists(ICON_PATH):
    try:
        st.logo(LOGO_PATH, size="large", icon_image=ICON_PATH)
    except Exception:
        pass
elif os.path.exists(ICON_PATH):
    try:
        st.logo(ICON_PATH, size="large", icon_image=ICON_PATH)
    except Exception:
        pass


# ------------------------------------------------------------
# ESTILO VISUAL
# ------------------------------------------------------------

def inject_profuturo_theme():
    st.markdown(
        """
        <style>
        :root {
            --profuturo-blue: #004B8D;
            --profuturo-dark-blue: #002B5C;
            --profuturo-deep-blue: #003B73;
            --profuturo-gold: #F6B221;
            --profuturo-bg: #F7F9FC;
        }

        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 3rem;
            max-width: 1280px;
        }

        .profuturo-header {
            background: linear-gradient(135deg, #003B73 0%, #004B8D 62%, #006CB8 100%);
            padding: 28px 32px;
            border-radius: 22px;
            color: white;
            margin-bottom: 22px;
            box-shadow: 0 14px 34px rgba(0, 43, 92, 0.22);
            border: 1px solid rgba(255,255,255,0.14);
        }

        .profuturo-eyebrow {
            color: #F6B221;
            font-size: 0.86rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .profuturo-title {
            font-size: 2.25rem;
            font-weight: 850;
            margin: 0;
            line-height: 1.12;
        }

        .profuturo-subtitle {
            font-size: 1.02rem;
            line-height: 1.55;
            max-width: 1020px;
            margin-top: 12px;
            color: rgba(255,255,255,0.93);
        }

        .profuturo-pill {
            display: inline-block;
            background: rgba(246, 178, 33, 0.16);
            color: #FFE09A;
            border: 1px solid rgba(246, 178, 33, 0.42);
            padding: 5px 11px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 800;
            margin-top: 14px;
            margin-right: 8px;
        }

        .profuturo-card {
            background: #FFFFFF;
            border: 1px solid rgba(0, 75, 141, 0.12);
            border-radius: 18px;
            padding: 16px 18px;
            box-shadow: 0 8px 22px rgba(0, 43, 92, 0.07);
            margin-bottom: 14px;
        }

        section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(246, 178, 33, 0.24);
        }

        div[data-testid="stChatMessage"] {
            border-radius: 18px;
        }

        .stButton > button {
            border-radius: 999px;
            border: 1px solid rgba(246, 178, 33, 0.65);
            background-color: rgba(246, 178, 33, 0.05);
        }

        .stButton > button:hover {
            border: 1px solid #F6B221;
            background-color: rgba(246, 178, 33, 0.14);
        }

        .stDownloadButton > button {
            border-radius: 999px;
            border: 1px solid rgba(0, 75, 141, 0.35);
        }

        div[data-testid="stExpander"] {
            border-radius: 14px;
            border: 1px solid rgba(0, 75, 141, 0.14);
        }

        div[data-testid="stMetric"] {
            background: #FFFFFF;
            border: 1px solid rgba(0, 75, 141, 0.14);
            border-radius: 16px;
            padding: 14px 16px;
            box-shadow: 0 8px 18px rgba(0, 43, 92, 0.06);
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_profuturo_header():
    st.markdown(
        """
        <div class="profuturo-header">
            <div class="profuturo-eyebrow">Profuturo · Talk2YourData</div>
            <h1 class="profuturo-title">Asistente de Traspasos AFORE</h1>
            <div class="profuturo-subtitle">
                Consulta información de traspasos mediante lenguaje natural.
                El asistente interpreta preguntas de negocio, consulta Databricks Genie
                y presenta respuestas con contexto analítico, tablas y visualizaciones.
            </div>
            <span class="profuturo-pill">Genie AI</span>
            <span class="profuturo-pill">Traspasos AFORE</span>
            <span class="profuturo-pill">Análisis conversacional</span>
        </div>
        """,
        unsafe_allow_html=True
    )


# ------------------------------------------------------------
# AUXILIARES GENERALES
# ------------------------------------------------------------

def normalize_text(text: str) -> str:
    text = str(text).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return text


def prettify_label(label: str) -> str:
    label = str(label).replace("_", " ").strip()
    label = re.sub(r"\s+", " ", label)
    return label.title()


def get_secret_or_env(name: str, default: str = "") -> str:
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name, default)


def load_databricks_config():
    raw_config = {
        "DATABRICKS_HOST": get_secret_or_env("DATABRICKS_HOST"),
        "DATABRICKS_TOKEN": get_secret_or_env("DATABRICKS_TOKEN"),
        "GENIE_SPACE_ID": get_secret_or_env("GENIE_SPACE_ID")
    }

    missing = [key for key, value in raw_config.items() if not value]

    if missing:
        st.error(
            "Faltan variables de conexión en Streamlit Secrets: "
            + ", ".join(missing)
            + ". Verifica la configuración de secrets antes de continuar."
        )
        st.stop()

    return {
        "host": raw_config["DATABRICKS_HOST"],
        "token": raw_config["DATABRICKS_TOKEN"],
        "space_id": raw_config["GENIE_SPACE_ID"]
    }


def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None
    if "last_raw_response" not in st.session_state:
        st.session_state.last_raw_response = None
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = None
    if "feedback" not in st.session_state:
        st.session_state.feedback = {}
    st.session_state.react_logs = []
    if "react_logs" not in st.session_state:
        st.session_state.react_logs = []


def reset_chat():
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.session_state.last_raw_response = None
    st.session_state.pending_prompt = None
    st.session_state.feedback = {}
    st.session_state.react_logs = []


def normalize_host(host: str) -> str:
    host = host.strip().rstrip("/")
    if host and not host.startswith("http"):
        host = f"https://{host}"
    return host


def get_attr(obj, *names, default=None):
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def to_dict(obj):
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_dict(x) for x in obj]
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    if hasattr(obj, "as_dict"):
        try:
            return obj.as_dict()
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        return {k: to_dict(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    return str(obj)


def format_number(value) -> str:
    try:
        value = float(value)
        if value.is_integer():
            return f"{value:,.0f}"
        return f"{value:,.2f}"
    except Exception:
        return str(value)


# ------------------------------------------------------------
# MAPEO, LIMPIEZA Y FORMATO
# ------------------------------------------------------------

def normalize_afore_code(value):
    if pd.isna(value):
        return None
    value_str = str(value).strip()
    if value_str.endswith(".0"):
        value_str = value_str[:-2]
    return value_str


def map_afore_code(value):
    code = normalize_afore_code(value)
    if code is None:
        return value
    return AFORE_CODE_MAP.get(code, code)


def is_afore_code_column(col: str) -> bool:
    norm = normalize_text(col)
    return norm in [
        "cve_afore", "cve afore", "cveafore", "cve_afore2", "cve afore2", "cveafore2",
        "cve_instituto", "cve instituto", "cveinstituto", "clave_afore", "clave afore",
        "clave_instituto", "clave instituto"
    ]


def get_afore_display_column_name(col: str) -> str:
    norm = normalize_text(col)
    if "afore2" in norm:
        return "AFORE Relacionada"
    if "instituto" in norm:
        return "Instituto"
    return "AFORE"


def enrich_afore_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    df_enriched = df.copy()
    for col in list(df_enriched.columns):
        if is_afore_code_column(col):
            new_col = get_afore_display_column_name(col)
            if new_col in df_enriched.columns:
                continue
            df_enriched[new_col] = df_enriched[col].apply(map_afore_code)
            ordered_cols = [new_col] + [c for c in df_enriched.columns if c != new_col]
            df_enriched = df_enriched[ordered_cols]
    return df_enriched


def prettify_afore_text(text: str) -> str:
    if not text:
        return text

    enriched_text = text
    for code, name in AFORE_CODE_MAP.items():
        patterns = [
            rf"\bCVE_AFORE\s*[:=]?\s*{code}(\s*\([^)]*\))?",
            rf"\bCVE_INSTITUTO\s*[:=]?\s*{code}(\s*\([^)]*\))?",
            rf"\bCVE AFORE\s*[:=]?\s*{code}(\s*\([^)]*\))?",
            rf"\bCVE INSTITUTO\s*[:=]?\s*{code}(\s*\([^)]*\))?",
            rf"\bclave\s*{code}(\s*\([^)]*\))?"
        ]
        for pattern in patterns:
            enriched_text = re.sub(pattern, f"{name} ({code})", enriched_text, flags=re.IGNORECASE)
    return enriched_text


def clean_markdown_artifacts(text: str) -> str:
    if not text:
        return text
    cleaned = text
    cleaned = re.sub(r"(?<!\*)\*(?!\*)([^*\n]+?)(?<!\*)\*(?!\*)", r"\1", cleaned)
    cleaned = re.sub(r"(?<!_)_(?!_)([^_\n]+?)(?<!_)_(?!_)", r"\1", cleaned)
    cleaned = re.sub(r"\s+([,.:%])", r"\1", cleaned)
    cleaned = re.sub(r"(\d)([A-Za-zÁÉÍÓÚáéíóúÑñ])", r"\1 \2", cleaned)
    return cleaned


def is_month_column(column_name: str) -> bool:
    return normalize_text(column_name) in ["mes", "month"]


def is_month_number_column(series: pd.Series, column_name: str) -> bool:
    if not is_month_column(column_name):
        return False
    numeric = pd.to_numeric(series, errors="coerce")
    if len(series) == 0:
        return False
    return numeric.notna().mean() >= 0.70 and numeric.dropna().between(1, 12).all()


def is_month_name_value(value) -> bool:
    if pd.isna(value):
        return False
    raw = normalize_text(str(value)).strip()
    first_token = raw.split()[0] if raw else raw
    return first_token in MONTH_ORDER


def is_month_text_column(series: pd.Series, column_name: str) -> bool:
    if not is_month_column(column_name):
        return False
    valid = series.dropna()
    if len(valid) == 0:
        return False
    return valid.apply(is_month_name_value).mean() >= 0.60


def format_month_value_for_display(value):
    if pd.isna(value):
        return ""
    raw = str(value).strip()
    raw_norm = normalize_text(raw)
    try:
        month_num = int(float(raw))
        if 1 <= month_num <= 12:
            return MONTH_SHORT_NAMES[month_num]
    except Exception:
        pass
    first_token = raw_norm.split()[0] if raw_norm else raw_norm
    if first_token in MONTH_ORDER:
        return MONTH_SHORT_NAMES[MONTH_ORDER[first_token]]
    try:
        parsed_date = pd.to_datetime(value, errors="coerce")
        if not pd.isna(parsed_date):
            return MONTH_SHORT_NAMES.get(parsed_date.month, raw)
    except Exception:
        pass
    return raw


def is_year_column(series: pd.Series, column_name: str) -> bool:
    if normalize_text(column_name) not in ["anio", "ano", "año", "year"]:
        return False
    numeric = pd.to_numeric(series, errors="coerce")
    if len(series) == 0:
        return False
    return numeric.notna().mean() >= 0.70 and numeric.dropna().between(1900, 2100).all()


def format_year_value(value):
    if pd.isna(value):
        return ""
    try:
        return str(int(float(value)))
    except Exception:
        return str(value)


def is_date_like_column(series: pd.Series, column_name: str) -> bool:
    if is_month_column(column_name) or is_month_number_column(series, column_name):
        return False
    norm = normalize_text(column_name)
    if any(keyword in norm for keyword in ["fecha", "periodo", "date"]):
        parsed = pd.to_datetime(series, errors="coerce", utc=True)
        return len(series) > 0 and parsed.notna().mean() >= 0.50
    return pd.api.types.is_datetime64_any_dtype(series)


def format_date_es(value, column_name: str = ""):
    if pd.isna(value):
        return ""
    try:
        date_value = pd.to_datetime(value, errors="coerce")
        if pd.isna(date_value):
            return value
        month = MONTH_SHORT_NAMES.get(date_value.month, "")
        if any(keyword in normalize_text(column_name) for keyword in ["mes", "periodo"]):
            return f"{month} {date_value.year}"
        return f"{date_value.day:02d} {month} {date_value.year}"
    except Exception:
        return value


def is_money_column(col: str) -> bool:
    norm = normalize_text(col)
    return any(k in norm for k in ["monto", "mdp", "saldo", "valor", "importe", "dinero"])


def is_percent_column(col: str) -> bool:
    norm = normalize_text(col)
    return any(k in norm for k in ["porcentaje", "participacion", "part_", "part ", "pct", "share"])


def is_count_column(col: str) -> bool:
    norm = normalize_text(col)
    return any(k in norm for k in ["cuentas", "traspasos", "conteo", "cantidad", "registros", "recibidos", "cedidos"])


def format_numeric_for_display(value, col: str):
    if pd.isna(value):
        return ""
    try:
        number = float(value)
    except Exception:
        return value
    if is_money_column(col):
        return f"${number:,.2f}"
    if is_percent_column(col):
        if abs(number) <= 1:
            number = number * 100
        return f"{number:,.1f}%"
    if is_count_column(col):
        return f"{number:,.0f}"
    if number.is_integer():
        return f"{number:,.0f}"
    return f"{number:,.2f}"


def prettify_table_column_name(col: str) -> str:
    custom_names = {
        "total_traspasos": "Total Traspasos",
        "total_cuentas": "Total Cuentas",
        "total_cuentas_recibidas": "Total Cuentas Recibidas",
        "total_monto": "Total Monto",
        "participacion": "Participación",
        "mes": "Mes",
        "fecha": "Fecha",
        "periodo": "Periodo",
        "anio": "Año",
        "ano": "Año",
        "cve_afore": "Clave AFORE",
        "cve_instituto": "Clave Instituto"
    }
    norm = normalize_text(col)
    if norm in custom_names:
        return custom_names[norm]
    return prettify_label(col)


def normalize_numeric_text(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", "").replace("\u202f", "").replace("−", "-")
    text = re.sub(r"^\((.*)\)$", r"-\1", text)
    text = re.sub(r"(?i)millones\s*de\s*pesos", "", text)
    text = re.sub(r"(?i)millones", "", text)
    text = re.sub(r"(?i)pesos", "", text)
    text = re.sub(r"(?i)mdp", "", text)
    text = text.replace("$", "").replace("%", "").replace(",", "")
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[^0-9.\-]", "", text)
    if text.count(".") > 1:
        parts = text.split(".")
        text = "".join(parts[:-1]) + "." + parts[-1]
    return text


def coerce_series_to_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    return pd.to_numeric(series.apply(normalize_numeric_text), errors="coerce")


def should_skip_numeric_conversion(col: str) -> bool:
    norm = normalize_text(col)
    if str(col).startswith("_"):
        return True
    if norm in {"mes", "month", "anio", "ano", "año", "year", "fecha", "date", "periodo"}:
        return True
    if is_afore_code_column(col):
        return True
    if any(keyword in norm for keyword in ["cve", "clave", "codigo", "code"]):
        return True
    if norm in {"id", "row_id", "registro_id"}:
        return True
    return False


def is_metric_like_column(col: str) -> bool:
    norm = normalize_text(col)
    metric_keywords = [
        "traspasos", "traspaso", "cuentas", "cuenta", "monto", "mdp", "total",
        "valor", "importe", "saldo", "participacion", "porcentaje", "promedio",
        "neto", "neta", "recibidos", "recibido", "cedidos", "cedido", "out", "in"
    ]
    return any(keyword in norm for keyword in metric_keywords)


def convert_metric_columns_to_numeric(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df_converted = df.copy()
    for col in list(df_converted.columns):
        if should_skip_numeric_conversion(col):
            continue
        if pd.api.types.is_datetime64_any_dtype(df_converted[col]):
            continue
        numeric = coerce_series_to_numeric(df_converted[col])
        numeric_ratio = numeric.notna().mean() if len(numeric) > 0 else 0
        threshold = 0.40 if is_metric_like_column(col) else 0.75
        if numeric_ratio >= threshold:
            df_converted[col] = numeric
    return df_converted


def prepare_dataframe_for_display(df: pd.DataFrame, hide_technical_codes: bool = True) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    display_df = enrich_afore_columns(df)
    columns_to_drop = []

    if hide_technical_codes:
        for col in display_df.columns:
            if is_afore_code_column(col):
                columns_to_drop.append(col)

    if columns_to_drop:
        display_df = display_df.drop(columns=columns_to_drop, errors="ignore")

    for col in list(display_df.columns):
        if is_year_column(display_df[col], col):
            display_df[col] = display_df[col].apply(format_year_value)

    for col in list(display_df.columns):
        if is_month_column(col):
            display_df[col] = display_df[col].apply(format_month_value_for_display)
        elif is_month_number_column(display_df[col], col):
            display_df[col] = display_df[col].apply(format_month_value_for_display)

    for col in list(display_df.columns):
        if is_date_like_column(display_df[col], col):
            display_df[col] = display_df[col].apply(lambda x: format_date_es(x, col))

    for col in list(display_df.columns):
        if is_year_column(display_df[col], col):
            display_df[col] = display_df[col].apply(format_year_value)
            continue
        if pd.api.types.is_numeric_dtype(display_df[col]):
            display_df[col] = display_df[col].apply(lambda x: format_numeric_for_display(x, col))
        else:
            numeric = coerce_series_to_numeric(display_df[col])
            if len(display_df) > 0 and numeric.notna().mean() >= 0.70:
                display_df[col] = numeric.apply(lambda x: format_numeric_for_display(x, col))

    rename_map = {col: prettify_table_column_name(col) for col in display_df.columns}
    display_df = display_df.rename(columns=rename_map)

    priority_cols = [
        col for col in display_df.columns
        if normalize_text(col) in [
            "afore", "afore relacionada", "instituto", "afore nombre", "instituto nombre"
        ]
    ]
    other_cols = [col for col in display_df.columns if col not in priority_cols]
    return display_df[priority_cols + other_cols]


# ------------------------------------------------------------
# PROMPT PARA GENIE
# ------------------------------------------------------------

def build_genie_prompt(user_prompt: str, deep_thinking: bool) -> str:
    if not deep_thinking:
        return user_prompt

    return f"""
Actúa como un analista experto en datos de traspasos AFORE usando el contexto, instrucciones, SQL Expressions y SQL Queries validadas que ya existen dentro de este Genie Space.

Antes de responder, revisa si la pregunta del usuario se parece a alguno de los ejemplos SQL validados o patrones de respuesta definidos en las instrucciones del Space. Si existe una coincidencia o una pregunta similar, usa ese ejemplo como referencia principal para construir la consulta y la respuesta.

Prioriza la lógica ya documentada en el Genie Space sobre inferencias generales. En especial:
1. Usa las definiciones de negocio, métricas y filtros ya configurados en las instrucciones y SQL Expressions.
2. Apóyate en los SQL Queries validados como guía para resolver preguntas similares.
3. Respeta la diferencia entre traspasos recibidos/IN y traspasos cedidos/OUT.
4. Si el usuario pregunta por una AFORE sin especificar origen o destino, interpreta por defecto que se refiere a traspasos recibidos, salvo que use términos como cedidos, salientes, perdidos, OUT, origen o desde.
5. Si la pregunta involucra Profuturo, identifica claramente si debe tratarse como AFORE destino, AFORE origen o entidad de comparación.
6. Para análisis mensuales, ordena los resultados cronológicamente.
7. Para comparativos, usa periodos equivalentes y explica claramente contra qué se está comparando.
8. Si la pregunta puede responderse con una tabla, devuelve resultados estructurados con columnas claras y nombres descriptivos.
9. Si hay ambigüedad, responde indicando el supuesto utilizado en lugar de inventar una interpretación.
10. Evita inventar datos o definiciones fuera del contexto configurado en el Space.

Entrega la respuesta en formato ejecutivo:
- Primero da el resultado directo.
- Después incluye una breve interpretación.
- Si aplica, menciona cualquier supuesto usado.
- Si aplica, devuelve una tabla que facilite la visualización en Streamlit.

Pregunta del usuario:
{user_prompt}
""".strip()


# ------------------------------------------------------------
# RESPUESTA DE GENIE Y EXTRACCIÓN TABULAR
# ------------------------------------------------------------

def extract_text_from_genie_response(response) -> str:
    attachments = get_attr(response, "attachments", default=[]) or []
    text_parts = []

    for attachment in attachments:
        text_obj = get_attr(attachment, "text")
        if text_obj:
            content = get_attr(text_obj, "content")
            if isinstance(text_obj, str):
                content = text_obj
            if content:
                text_parts.append(str(content))

    if text_parts:
        return "\n\n".join(text_parts)
    return "Genie procesó la solicitud, pero no devolvió una respuesta textual clara."


def extract_sql_from_genie_response(response) -> list[str]:
    attachments = get_attr(response, "attachments", default=[]) or []
    sql_queries = []

    for attachment in attachments:
        query_obj = get_attr(attachment, "query")
        if query_obj:
            sql_text = get_attr(query_obj, "query") or get_attr(query_obj, "sql") or get_attr(query_obj, "statement")
            if sql_text:
                sql_queries.append(str(sql_text))

    return sql_queries


def get_query_attachment_ids(response) -> list[str]:
    attachments = get_attr(response, "attachments", default=[]) or []
    attachment_ids = []

    for attachment in attachments:
        query_obj = get_attr(attachment, "query")
        if query_obj:
            attachment_id = get_attr(attachment, "attachment_id") or get_attr(attachment, "id")
            if attachment_id:
                attachment_ids.append(str(attachment_id))

    return attachment_ids


def find_first_key(obj, target_key):
    if isinstance(obj, dict):
        if target_key in obj:
            return obj[target_key]
        for value in obj.values():
            result = find_first_key(value, target_key)
            if result is not None:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = find_first_key(item, target_key)
            if result is not None:
                return result
    return None


def unwrap_cell(value):
    if isinstance(value, dict):
        for key in ["value", "string_value", "str_value", "long_value", "double_value", "decimal_value", "boolean_value"]:
            if key in value:
                return unwrap_cell(value[key])
        if len(value) == 1:
            return unwrap_cell(next(iter(value.values())))
        return str(value)
    return value


def extract_dataframe_from_query_result(query_result):
    raw = to_dict(query_result)
    if not raw:
        return None

    data_array = find_first_key(raw, "data_array")
    columns_raw = find_first_key(raw, "columns")

    if not data_array:
        return None

    if isinstance(data_array, list) and len(data_array) > 0:
        if all(isinstance(row, dict) for row in data_array):
            rows = [{k: unwrap_cell(v) for k, v in row.items()} for row in data_array]
            return pd.DataFrame(rows)

        column_names = []
        if isinstance(columns_raw, list):
            for idx, col in enumerate(columns_raw):
                if isinstance(col, dict):
                    column_names.append(
                        col.get("name")
                        or col.get("display_name")
                        or col.get("column_name")
                        or f"col_{idx + 1}"
                    )
                else:
                    column_names.append(str(col))

        clean_rows = []
        for row in data_array:
            if isinstance(row, list):
                clean_rows.append([unwrap_cell(v) for v in row])
            else:
                clean_rows.append(unwrap_cell(row))

        if not column_names and clean_rows and isinstance(clean_rows[0], list):
            column_names = [f"col_{i + 1}" for i in range(len(clean_rows[0]))]

        try:
            return pd.DataFrame(clean_rows, columns=column_names)
        except Exception:
            return pd.DataFrame(clean_rows)

    return None


# ------------------------------------------------------------
# VISUALIZACIONES AUTOMÁTICAS CON PLANNER ROBUSTO
# ------------------------------------------------------------

def add_period_column_if_possible(df_chart: pd.DataFrame) -> pd.DataFrame:
    """
    Crea _periodo_grafico cuando existe Año + Mes.
    Esta columna es la que permite graficar correctamente tendencias mensuales
    aunque todos los registros pertenezcan al mismo año.
    """
    df_out = df_chart.copy()
    normalized_cols = {col: normalize_text(col) for col in df_out.columns}

    year_candidates = [
        col for col, norm in normalized_cols.items()
        if norm in ["anio", "ano", "año", "year"]
    ]
    month_candidates = [
        col for col, norm in normalized_cols.items()
        if norm in ["mes", "month"]
    ]

    if not year_candidates or not month_candidates:
        return df_out

    year_col = year_candidates[0]
    month_col = month_candidates[0]

    years = pd.to_numeric(
        df_out[year_col].astype(str).str.replace(",", "", regex=False),
        errors="coerce"
    )
    months = df_out[month_col].apply(parse_month_to_number)

    period = pd.to_datetime(
        {"year": years, "month": months, "day": 1},
        errors="coerce"
    )

    if len(df_out) > 0 and period.notna().mean() >= 0.50:
        df_out["_periodo_grafico"] = period

    return df_out

def prepare_dataframe_for_charts(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    df_chart = enrich_afore_columns(df)
    df_chart = df_chart.copy()
    df_chart.columns = [str(col).strip() for col in df_chart.columns]

    for col in list(df_chart.columns):
        norm = normalize_text(col)
        if norm not in TIME_COLUMN_EXACT_NAMES:
            continue
        if is_year_column(df_chart[col], col) or is_month_number_column(df_chart[col], col) or is_month_text_column(df_chart[col], col):
            continue
        if norm in ["fecha", "date", "periodo"]:
            parsed_dates = pd.to_datetime(df_chart[col], errors="coerce", utc=True)
            if len(df_chart) > 0 and parsed_dates.notna().mean() >= 0.50:
                df_chart[col] = parsed_dates.dt.tz_convert(None)

    df_chart = add_period_column_if_possible(df_chart)
    df_chart = convert_metric_columns_to_numeric(df_chart)
    return df_chart


def infer_chart_intent(user_prompt: str, assistant_text: str = "") -> dict:
    text = normalize_text(f"{user_prompt} {assistant_text}")
    intent = {
        "metric_family": None,
        "secondary_metric_family": None,
        "is_time_series": False,
        "is_ranking": False,
        "is_comparison": False,
        "is_participation": False,
        "is_net": False,
        "is_average": False,
        "is_distribution": False,
        "prefers_top": False,
        "prefer_scatter": False
    }

    has_participation = any(k in text for k in ["participacion", "porcentaje", "share", "distribucion", "distribución", "%"])
    has_money = any(k in text for k in ["monto", "mdp", "dinero", "valor monetario", "importe", "pesos", "saldo"])
    has_count = any(k in text for k in ["cuentas", "numero de cuentas", "número de cuentas", "traspasos", "registros"])

    if has_participation:
        intent["metric_family"] = "participacion"
        intent["is_participation"] = True
        if has_money:
            intent["secondary_metric_family"] = "monto"
        elif has_count:
            intent["secondary_metric_family"] = "cuentas"
    elif has_money:
        intent["metric_family"] = "monto"
    elif has_count:
        intent["metric_family"] = "cuentas"

    if any(k in text for k in ["neto", "neta", "netas", "netos", "resultado neto"]):
        intent["is_net"] = True

    if any(k in text for k in ["promedio", "promedio semanal", "semanal"]):
        intent["is_average"] = True

    if any(k in text for k in [
        "por mes", "mensual", "mes a mes", "tendencia", "evolucion", "evolución",
        "por año", "anual", "año a año", "periodo", "periodos", "cada mes"
    ]):
        intent["is_time_series"] = True

    if any(k in text for k in ["mayor", "menor", "ranking", "top", "principales", "más", "mas", "mejor", "peor", "lider", "líder"]):
        intent["is_ranking"] = True
        intent["prefers_top"] = True

    if any(k in text for k in ["compara", "comparar", "comparativo", "contra", "entre", "vs", "versus"]):
        intent["is_comparison"] = True

    if any(k in text for k in ["distribucion", "distribución", "proporcion", "proporción", "reparto"]):
        intent["is_distribution"] = True

    if any(k in text for k in ["relacion", "relación", "correlacion", "correlación", "dispersion", "dispersión", "scatter"]):
        intent["prefer_scatter"] = True

    return intent


def get_numeric_columns(df: pd.DataFrame) -> list[str]:
    if df is None or df.empty:
        return []

    numeric_cols = []
    for col in list(df.columns):
        if should_skip_numeric_conversion(col):
            continue
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_cols.append(col)
            continue
        numeric = coerce_series_to_numeric(df[col])
        numeric_ratio = numeric.notna().mean() if len(numeric) > 0 else 0
        threshold = 0.40 if is_metric_like_column(col) else 0.75
        if numeric_ratio >= threshold:
            df[col] = numeric
            numeric_cols.append(col)
    return numeric_cols


def get_categorical_columns(df: pd.DataFrame) -> list[str]:
    categorical_cols = []
    if df is None or df.empty:
        return categorical_cols

    for col in df.columns:
        norm = normalize_text(col)
        if str(col).startswith("_"):
            continue
        if is_afore_code_column(col):
            continue
        if norm in {"fecha", "date", "periodo", "anio", "ano", "año", "year", "mes", "month"}:
            continue
        if pd.api.types.is_numeric_dtype(df[col]) or pd.api.types.is_datetime64_any_dtype(df[col]):
            continue
        if df[col].nunique(dropna=True) >= 1:
            categorical_cols.append(col)
    return categorical_cols


def find_time_column(df: pd.DataFrame):
    """
    Detecta la mejor dimensión temporal para graficar.
    Prioridad:
    1) _periodo_grafico si existe, para series Año + Mes.
    2) fecha/periodo/date.
    3) mes/month.
    4) año/year solo si no hay mes.
    Esto evita graficar 12 meses apilados en un solo punto de año.
    """
    if df is None or df.empty:
        return None

    if "_periodo_grafico" in df.columns:
        return "_periodo_grafico"

    # 1. Fechas o periodos explícitos.
    for col in df.columns:
        norm = normalize_text(col)
        if norm not in ["fecha", "date", "periodo"]:
            continue

        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col

        parsed = pd.to_datetime(df[col], errors="coerce", utc=True)
        if len(df) > 0 and parsed.notna().mean() >= 0.50:
            df[col] = parsed.dt.tz_convert(None)
            return col

    # 2. Mes antes que año. Si hay una columna Mes, es la mejor para preguntas mensuales.
    for col in df.columns:
        norm = normalize_text(col)
        if norm not in ["mes", "month"]:
            continue

        if is_month_number_column(df[col], col) or is_month_text_column(df[col], col):
            return col

    # 3. Año como último recurso temporal.
    for col in df.columns:
        norm = normalize_text(col)
        if norm not in ["anio", "ano", "año", "year"]:
            continue

        if is_year_column(df[col], col):
            return col

    return None

def metric_score(col: str, intent: dict) -> int:
    norm = normalize_text(col)
    score = 0
    if should_skip_numeric_conversion(col):
        return -999

    family = intent.get("metric_family")
    if family == "monto":
        if any(k in norm for k in ["monto", "mdp", "valor", "importe", "saldo"]):
            score += 120
        if any(k in norm for k in ["cuentas", "traspasos", "registros"]):
            score -= 50
    elif family == "cuentas":
        if any(k in norm for k in ["cuentas", "traspasos", "registros", "cantidad", "conteo", "recibidos", "cedidos"]):
            score += 120
        if any(k in norm for k in ["monto", "mdp", "valor", "importe", "saldo"]):
            score -= 50
    elif family == "participacion":
        if any(k in norm for k in ["participacion", "porcentaje", "part", "pct", "share"]):
            score += 140
        if intent.get("secondary_metric_family") == "monto" and any(k in norm for k in ["monto", "mdp"]):
            score += 35
        if intent.get("secondary_metric_family") == "cuentas" and any(k in norm for k in ["cuentas", "traspasos"]):
            score += 35

    if intent.get("is_net") and any(k in norm for k in ["neto", "neta", "netas", "netos"]):
        score += 50
    if intent.get("is_average") and any(k in norm for k in ["promedio", "avg", "media"]):
        score += 50
    if "semanal" in norm and intent.get("is_average"):
        score += 25
    if any(k in norm for k in ["total", "acumulado"]):
        score += 12

    if family is None:
        fallback_order = [
            ("participacion", 70), ("porcentaje", 70), ("monto", 60), ("mdp", 60),
            ("valor", 55), ("cuentas", 50), ("traspasos", 50), ("recibidos", 45),
            ("cedidos", 45), ("total", 35)
        ]
        for keyword, value in fallback_order:
            if keyword in norm:
                score += value

    return score


def choose_measure_column(numeric_cols: list[str], intent: dict) -> str | None:
    if not numeric_cols:
        return None
    scored = sorted([(metric_score(col, intent), col) for col in numeric_cols], key=lambda x: x[0], reverse=True)
    return scored[0][1]


def choose_category_column(df: pd.DataFrame, categorical_cols: list[str], intent: dict, max_categories: int = 30) -> str | None:
    if not categorical_cols:
        return None

    valid_cols = [col for col in categorical_cols if df[col].nunique(dropna=True) <= max_categories]
    if not valid_cols:
        return None

    priority_keywords = [
        "afore contraparte", "contraparte", "afore relacionada", "afore", "instituto",
        "destino", "origen", "administradora", "zona", "canal", "grupo", "categoria", "segmento"
    ]

    if intent.get("is_ranking") or intent.get("is_comparison"):
        for keyword in priority_keywords[:7]:
            for col in valid_cols:
                if keyword in normalize_text(col):
                    return col

    for keyword in priority_keywords:
        for col in valid_cols:
            if keyword in normalize_text(col):
                return col
    return valid_cols[0]


def sort_for_chart(df: pd.DataFrame, x_col: str) -> pd.DataFrame:
    df_sorted = df.copy()
    if x_col == "_periodo_grafico":
        return df_sorted.sort_values(x_col)
    if pd.api.types.is_datetime64_any_dtype(df_sorted[x_col]):
        return df_sorted.sort_values(x_col)
    if is_year_column(df_sorted[x_col], x_col):
        df_sorted["_orden_anio"] = pd.to_numeric(df_sorted[x_col], errors="coerce")
        return df_sorted.sort_values("_orden_anio").drop(columns=["_orden_anio"])
    if is_month_column(x_col):
        df_sorted["_orden_mes"] = df_sorted[x_col].astype(str).map(lambda x: MONTH_ORDER.get(normalize_text(x).split()[0], None))
        if df_sorted["_orden_mes"].notna().any():
            return df_sorted.sort_values("_orden_mes").drop(columns=["_orden_mes"])
    if pd.api.types.is_numeric_dtype(df_sorted[x_col]):
        return df_sorted.sort_values(x_col)
    return df_sorted


def has_positive_and_negative_values(df: pd.DataFrame, value_col: str) -> bool:
    values = pd.to_numeric(df[value_col], errors="coerce").dropna()
    if values.empty:
        return False
    return values.min() < 0 and values.max() > 0


def format_plot_text_value(value, col: str):
    if pd.isna(value):
        return ""
    try:
        number = float(value)
    except Exception:
        return str(value)
    if is_money_column(col):
        return f"${number:,.2f}"
    if is_percent_column(col):
        if abs(number) <= 1:
            number = number * 100
        return f"{number:,.1f}%"
    return f"{number:,.0f}" if number.is_integer() else f"{number:,.2f}"


def style_plotly_figure(fig, title: str):
    fig.update_layout(
        title={"text": title, "x": 0.02, "xanchor": "left", "font": {"size": 20, "color": PROFUTURO_COLORS["dark_blue"]}},
        template="plotly_white",
        height=460,
        margin=dict(l=20, r=20, t=70, b=40),
        font=dict(size=13, color=PROFUTURO_COLORS["text"]),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(0, 75, 141, 0.10)", zeroline=False, title_font=dict(color=PROFUTURO_COLORS["dark_blue"]), tickfont=dict(color="#374151"))
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(0, 75, 141, 0.10)", zeroline=False, title_font=dict(color=PROFUTURO_COLORS["dark_blue"]), tickfont=dict(color="#374151"))
    return fig


def render_kpi_cards(df: pd.DataFrame, numeric_cols: list[str], intent: dict | None = None):
    if df is None or df.empty:
        return
    intent = intent or {}
    st.subheader("Resumen visual")

    context_cols = [
        col for col in df.columns
        if normalize_text(col) in [
            "afore", "afore relacionada", "instituto", "afore nombre", "instituto nombre", "contraparte", "afore contraparte"
        ]
    ]

    if context_cols:
        context_col = context_cols[0]
        st.markdown(
            f"""
            <div class="profuturo-card">
                <div style="font-size:0.9rem; color:#6B7280; font-weight:700;">{prettify_label(context_col)}</div>
                <div style="font-size:2rem; color:#002B5C; font-weight:800;">{df.iloc[0][context_col]}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    if not numeric_cols:
        return

    chosen = choose_measure_column(numeric_cols, intent)
    display_cols = [chosen] + [col for col in numeric_cols if col != chosen]
    display_cols = display_cols[:4]
    cols = st.columns(len(display_cols))

    for idx, metric_col in enumerate(display_cols):
        value = df.iloc[0][metric_col]
        with cols[idx]:
            st.metric(label=prettify_label(metric_col), value=format_numeric_for_display(value, metric_col))


def render_heatmap_if_possible(df: pd.DataFrame, value_col: str, chart_key: str):
    origin_col = None
    destination_col = None
    for col in df.columns:
        norm = normalize_text(col)
        if "origen" in norm and origin_col is None:
            origin_col = col
        if "destino" in norm and destination_col is None:
            destination_col = col

    if not origin_col or not destination_col:
        return False
    if df[origin_col].nunique(dropna=True) > 30 or df[destination_col].nunique(dropna=True) > 30:
        return False

    pivot = df.pivot_table(index=origin_col, columns=destination_col, values=value_col, aggfunc="sum", fill_value=0)
    if pivot.empty:
        return False

    fig = px.imshow(
        pivot,
        text_auto=True,
        aspect="auto",
        color_continuous_scale=["#F7F9FC", PROFUTURO_COLORS["light_blue"], PROFUTURO_COLORS["blue"], PROFUTURO_COLORS["dark_blue"]],
        labels=dict(x=prettify_label(destination_col), y=prettify_label(origin_col), color=prettify_label(value_col))
    )
    fig = style_plotly_figure(fig, title=f"Cruce de {prettify_label(origin_col)} vs {prettify_label(destination_col)}")
    st.subheader("Visualización")
    st.plotly_chart(fig, use_container_width=True, key=f"heatmap_{chart_key}")
    return True


def render_bar_chart(df_chart: pd.DataFrame, category_col: str, value_col: str, chart_key: str, title: str, divergent: bool = False, top_n: int = 15):
    bar_df = df_chart[[category_col, value_col]].dropna().copy()
    if bar_df.empty:
        return
    bar_df = bar_df.groupby(category_col, as_index=False)[value_col].sum()
    if divergent:
        bar_df = bar_df.sort_values(value_col, ascending=True)
    else:
        bar_df = bar_df.sort_values(value_col, ascending=False).head(top_n).sort_values(value_col, ascending=True)
    bar_df["_texto_valor"] = bar_df[value_col].apply(lambda x: format_plot_text_value(x, value_col))

    fig = px.bar(
        bar_df,
        x=value_col,
        y=category_col,
        orientation="h",
        text="_texto_valor",
        labels={category_col: prettify_label(category_col), value_col: prettify_label(value_col)},
        color_discrete_sequence=[PROFUTURO_COLORS["blue"]]
    )
    fig.update_traces(texttemplate="%{text}", textposition="outside", cliponaxis=False, marker_line_width=0)
    if divergent:
        fig.add_vline(x=0, line_width=1, line_dash="dash", line_color="rgba(0, 43, 92, 0.55)")
    fig = style_plotly_figure(fig, title=title)
    st.subheader("Visualización")
    st.plotly_chart(fig, use_container_width=True, key=f"bar_{chart_key}")


def format_time_axis_labels(plot_df: pd.DataFrame, time_col: str):
    x_col = time_col
    out = plot_df.copy()
    if is_year_column(out[time_col], time_col):
        x_col = "_anio_label"
        out[x_col] = out[time_col].apply(format_year_value)
    elif time_col == "_periodo_grafico":
        x_col = "_periodo_label"
        out[x_col] = out[time_col].dt.strftime("%b %Y")
    elif is_month_column(time_col):
        x_col = "_mes_label"
        out[x_col] = out[time_col].apply(format_month_value_for_display)
    return out, x_col


def render_period_bar_chart(df_chart: pd.DataFrame, time_col: str, value_col: str, chart_key: str):
    plot_df = sort_for_chart(df_chart, time_col)
    plot_df, x_col = format_time_axis_labels(plot_df, time_col)
    plot_df["_texto_valor"] = plot_df[value_col].apply(lambda x: format_plot_text_value(x, value_col))
    fig = px.bar(
        plot_df,
        x=x_col,
        y=value_col,
        text="_texto_valor",
        labels={x_col: "Periodo" if time_col == "_periodo_grafico" else prettify_label(time_col), value_col: prettify_label(value_col)},
        color_discrete_sequence=[PROFUTURO_COLORS["blue"]]
    )
    fig.update_traces(texttemplate="%{text}", textposition="outside", cliponaxis=False, marker_line_width=0)
    fig.update_xaxes(type="category")
    fig = style_plotly_figure(fig, title=f"Comparativo de {prettify_label(value_col)}")
    st.subheader("Visualización")
    st.plotly_chart(fig, use_container_width=True, key=f"period_bar_{chart_key}")


def render_line_chart(df_chart: pd.DataFrame, time_col: str, value_col: str, color_col: str | None, chart_key: str):
    plot_df = sort_for_chart(df_chart, time_col)
    plot_df, x_col = format_time_axis_labels(plot_df, time_col)
    labels = {x_col: "Periodo" if time_col == "_periodo_grafico" else prettify_label(time_col), value_col: prettify_label(value_col)}
    if color_col:
        labels[color_col] = prettify_label(color_col)
    fig = px.line(
        plot_df,
        x=x_col,
        y=value_col,
        color=color_col,
        markers=True,
        labels=labels,
        color_discrete_sequence=PROFUTURO_COLOR_SEQUENCE
    )
    fig.update_traces(line=dict(width=3), marker=dict(size=8))
    fig.update_xaxes(type="category")
    fig = style_plotly_figure(fig, title=f"Tendencia de {prettify_label(value_col)}")
    st.subheader("Visualización")
    st.plotly_chart(fig, use_container_width=True, key=f"line_{chart_key}")


def render_pie_chart(df_chart: pd.DataFrame, category_col: str, value_col: str, chart_key: str):
    fig = px.pie(
        df_chart,
        names=category_col,
        values=value_col,
        hole=0.45,
        labels={category_col: prettify_label(category_col), value_col: prettify_label(value_col)},
        color_discrete_sequence=PROFUTURO_COLOR_SEQUENCE
    )
    fig = style_plotly_figure(fig, title=f"Distribución de {prettify_label(value_col)}")
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.subheader("Visualización")
    st.plotly_chart(fig, use_container_width=True, key=f"pie_{chart_key}")


def render_manual_visualization_controls(
    df_chart: pd.DataFrame,
    chart_key: str,
    numeric_cols: list[str],
    categorical_cols: list[str],
    default_value_col: str | None,
    default_category_col: str | None,
    default_time_col: str | None
):
    if not numeric_cols:
        return

    with st.expander("Ajustar visualización", expanded=False):
        chart_options = ["Barras", "Línea", "Dona", "Dispersión"]
        c1, c2, c3 = st.columns(3)

        with c1:
            default_chart_index = 0
            if default_time_col and default_time_col in df_chart.columns and df_chart[default_time_col].nunique(dropna=True) >= 3:
                default_chart_index = chart_options.index("Línea")
            chart_type = st.selectbox("Tipo de gráfica", chart_options, index=default_chart_index, key=f"manual_type_{chart_key}")

        with c2:
            default_y_index = numeric_cols.index(default_value_col) if default_value_col in numeric_cols else 0
            y_col = st.selectbox("Métrica", numeric_cols, index=default_y_index, format_func=prettify_label, key=f"manual_y_{chart_key}")

        with c3:
            x_options = []

            # Primero todas las columnas temporales útiles, incluyendo Mes y _periodo_grafico.
            for col in df_chart.columns:
                norm = normalize_text(col)
                if col == "_periodo_grafico" or norm in TIME_COLUMN_EXACT_NAMES:
                    x_options.append(col)

            # Después dimensiones categóricas.
            x_options.extend(categorical_cols)

            x_options = list(dict.fromkeys([col for col in x_options if col in df_chart.columns]))

            if not x_options:
                st.info("No hay columnas categóricas o temporales disponibles para ajustar la visualización.")
                return

            default_x = default_time_col or default_category_col or x_options[0]
            default_x_index = x_options.index(default_x) if default_x in x_options else 0
            x_col = st.selectbox("Eje / categoría", x_options, index=default_x_index, format_func=prettify_label, key=f"manual_x_{chart_key}")

        manual_df = df_chart.dropna(subset=[x_col, y_col]).copy()
        if manual_df.empty:
            st.info("No hay datos suficientes para generar la visualización ajustada.")
            return

        if chart_type == "Línea":
            render_line_chart(manual_df, time_col=x_col, value_col=y_col, color_col=None, chart_key=f"manual_{chart_key}")
        elif chart_type == "Dona":
            if manual_df[x_col].nunique(dropna=True) <= 12:
                render_pie_chart(manual_df, category_col=x_col, value_col=y_col, chart_key=f"manual_{chart_key}")
            else:
                st.info("La dona funciona mejor con 12 categorías o menos. Usa barras para este caso.")
        elif chart_type == "Dispersión":
            if len(numeric_cols) >= 2:
                other_numeric = [col for col in numeric_cols if col != y_col]
                x_numeric = st.selectbox("Métrica eje X", other_numeric, format_func=prettify_label, key=f"manual_scatter_x_{chart_key}")
                fig = px.scatter(manual_df, x=x_numeric, y=y_col, labels={x_numeric: prettify_label(x_numeric), y_col: prettify_label(y_col)}, color_discrete_sequence=PROFUTURO_COLOR_SEQUENCE)
                fig = style_plotly_figure(fig, title=f"Relación entre {prettify_label(x_numeric)} y {prettify_label(y_col)}")
                st.plotly_chart(fig, use_container_width=True, key=f"manual_scatter_{chart_key}")
            else:
                st.info("Se requieren al menos dos métricas numéricas para una dispersión.")
        else:
            render_bar_chart(manual_df, category_col=x_col, value_col=y_col, chart_key=f"manual_{chart_key}", title=f"Ranking por {prettify_label(y_col)}", divergent=has_positive_and_negative_values(manual_df, y_col))


def render_smart_visualization(df: pd.DataFrame, chart_key: str, user_prompt: str = "", assistant_text: str = ""):
    if df is None or df.empty:
        return

    intent = infer_chart_intent(user_prompt, assistant_text)
    df_chart = prepare_dataframe_for_charts(df)

    numeric_cols = get_numeric_columns(df_chart)
    categorical_cols = get_categorical_columns(df_chart)
    time_col = find_time_column(df_chart)
    value_col = choose_measure_column(numeric_cols, intent)

    if not numeric_cols or value_col is None:
        st.info("No pude generar una visualización automática con esta tabla. Puedes revisar los datos en la tabla de resultados.")
        return

    if len(df_chart) == 1:
        render_kpi_cards(df_chart, numeric_cols, intent)
        render_manual_visualization_controls(df_chart, chart_key, numeric_cols, categorical_cols, value_col, None, time_col)
        return

    category_col = choose_category_column(df_chart, categorical_cols, intent)
    unique_time_count = df_chart[time_col].nunique(dropna=True) if time_col and time_col in df_chart.columns else 0

    # 1) Serie temporal real: Año+Mes, Mes, Periodo o fecha con 3+ puntos.
    if time_col and unique_time_count >= 3:
        color_col = None
        for col in categorical_cols:
            unique_count = df_chart[col].nunique(dropna=True)
            if 1 < unique_count <= 12 and any(keyword in normalize_text(col) for keyword in ["afore", "origen", "destino", "grupo", "categoria", "instituto", "contraparte"]):
                color_col = col
                break
        render_line_chart(df_chart=df_chart, time_col=time_col, value_col=value_col, color_col=color_col, chart_key=chart_key)
        render_manual_visualization_controls(df_chart, chart_key, numeric_cols, categorical_cols, value_col, category_col, time_col)
        return

    # 2) Comparativo de pocos periodos: barras por periodo.
    if time_col and unique_time_count >= 1 and not category_col:
        render_period_bar_chart(df_chart=df_chart, time_col=time_col, value_col=value_col, chart_key=chart_key)
        render_manual_visualization_controls(df_chart, chart_key, numeric_cols, categorical_cols, value_col, category_col, time_col)
        return

    # 3) Categorías: barras, o dona solo si es distribución/participación.
    if category_col:
        divergent = has_positive_and_negative_values(df_chart, value_col)
        if intent.get("is_distribution") and intent.get("is_participation") and df_chart[category_col].nunique(dropna=True) <= 8 and not divergent:
            render_pie_chart(df_chart, category_col, value_col, chart_key)
        else:
            if divergent:
                title = f"Comparativo de {prettify_label(value_col)}"
            elif intent.get("is_ranking") or intent.get("prefers_top"):
                title = f"Ranking por {prettify_label(value_col)}"
            else:
                title = f"Comparativo por {prettify_label(category_col)}"
            render_bar_chart(df_chart=df_chart, category_col=category_col, value_col=value_col, chart_key=chart_key, title=title, divergent=divergent, top_n=10 if intent.get("is_ranking") else 15)
        render_manual_visualization_controls(df_chart, chart_key, numeric_cols, categorical_cols, value_col, category_col, time_col)
        return

    # 4) Heatmap si aplica y no hubo otra opción mejor.
    if not intent.get("is_ranking") and not intent.get("is_comparison") and render_heatmap_if_possible(df_chart, value_col, chart_key):
        render_manual_visualization_controls(df_chart, chart_key, numeric_cols, categorical_cols, value_col, category_col, time_col)
        return

    # 5) Dispersión solo si el usuario lo pidió explícitamente.
    if intent.get("prefer_scatter") and len(numeric_cols) >= 2:
        x_col = numeric_cols[0] if numeric_cols[0] != value_col else numeric_cols[1]
        fig = px.scatter(df_chart, x=x_col, y=value_col, labels={x_col: prettify_label(x_col), value_col: prettify_label(value_col)}, color_discrete_sequence=PROFUTURO_COLOR_SEQUENCE)
        fig = style_plotly_figure(fig, title=f"Relación entre {prettify_label(x_col)} y {prettify_label(value_col)}")
        st.subheader("Visualización")
        st.plotly_chart(fig, use_container_width=True, key=f"scatter_{chart_key}")
        render_manual_visualization_controls(df_chart, chart_key, numeric_cols, categorical_cols, value_col, category_col, time_col)
        return

    # 6) Fallback: barras por registro.
    temp_df = df_chart.reset_index().rename(columns={"index": "Registro"})
    temp_df["_texto_valor"] = temp_df[value_col].apply(lambda x: format_plot_text_value(x, value_col))
    fig = px.bar(temp_df, x="Registro", y=value_col, text="_texto_valor", labels={"Registro": "Registro", value_col: prettify_label(value_col)}, color_discrete_sequence=[PROFUTURO_COLORS["blue"]])
    fig.update_traces(texttemplate="%{text}", textposition="outside", cliponaxis=False, marker_line_width=0)
    fig = style_plotly_figure(fig, title=f"Visualización de {prettify_label(value_col)}")
    st.subheader("Visualización")
    st.plotly_chart(fig, use_container_width=True, key=f"fallback_bar_{chart_key}")
    render_manual_visualization_controls(df_chart, chart_key, numeric_cols, categorical_cols, value_col, category_col, time_col)


# ------------------------------------------------------------
# CONEXIÓN CON GENIE
# ------------------------------------------------------------

def ask_genie(host: str, token: str, space_id: str, prompt: str, show_sql: bool = False):
    host = normalize_host(host)
    client = WorkspaceClient(host=host, token=token)
    timeout = timedelta(minutes=10)

    if st.session_state.conversation_id is None:
        response = client.genie.start_conversation_and_wait(space_id=space_id, content=prompt, timeout=timeout)
        st.session_state.conversation_id = get_attr(response, "conversation_id")
    else:
        response = client.genie.create_message_and_wait(space_id=space_id, conversation_id=st.session_state.conversation_id, content=prompt, timeout=timeout)

    st.session_state.last_raw_response = to_dict(response)
    response_text = extract_text_from_genie_response(response)
    sql_queries = extract_sql_from_genie_response(response)
    message_id = get_attr(response, "id") or get_attr(response, "message_id")
    attachment_ids = get_query_attachment_ids(response)
    dataframes = []

    if message_id and attachment_ids:
        for attachment_id in attachment_ids:
            try:
                query_result = client.genie.get_message_attachment_query_result(
                    space_id=space_id,
                    conversation_id=st.session_state.conversation_id,
                    message_id=message_id,
                    attachment_id=attachment_id
                )
                df = extract_dataframe_from_query_result(query_result)
                if df is not None and not df.empty:
                    dataframes.append(df)
            except Exception as e:
                if show_sql:
                    st.warning(f"No se pudo recuperar el resultado tabular para attachment_id={attachment_id}: {e}")

    return {"text": response_text, "sql": sql_queries, "dataframes": dataframes, "raw": st.session_state.last_raw_response}


# ------------------------------------------------------------
# ORQUESTADOR REACT: VALIDACIÓN + REINTENTO CONTROLADO
# ------------------------------------------------------------

def get_profuturo_codes() -> list[str]:
    """
    Obtiene las claves que en el catálogo local estén asociadas a Profuturo.
    Esto evita quemar una sola clave si el catálogo cambia entre fuentes.
    """
    codes = [code for code, name in AFORE_CODE_MAP.items() if normalize_text(name) == "profuturo"]
    return codes or ["534"]


def response_has_any_code(result: dict, codes: list[str]) -> bool:
    text = normalize_text(result.get("text", ""))
    sql_text = normalize_text(" ".join(result.get("sql", []) or []))
    joined = f"{text} {sql_text}"
    return any(str(code) in joined for code in codes)


def has_table_result(result: dict) -> bool:
    dataframes = result.get("dataframes", []) or []
    return any(df is not None and not df.empty for df in dataframes)


def validate_genie_result(user_prompt: str, result: dict) -> list[str]:
    """
    Valida señales básicas de consistencia de negocio.
    No reemplaza los benchmarks de Databricks; funciona como un filtro ligero antes de mostrar la respuesta.
    """
    issues = []
    question = normalize_text(user_prompt)
    text = normalize_text(result.get("text", ""))
    sql_text = normalize_text(" ".join(result.get("sql", []) or []))
    combined = f"{text} {sql_text}"

    profuturo_codes = get_profuturo_codes()

    if "profuturo" in question and not response_has_any_code(result, profuturo_codes):
        issues.append(
            "La pregunta menciona Profuturo, pero la respuesta/SQL no muestra una clave AFORE asociada a Profuturo. "
            f"Valida el filtro usando el catálogo local: Profuturo = {', '.join(profuturo_codes)}."
        )

    if any(k in question for k in ["neto", "neta", "netas", "netos"]):
        net_definition_present = any(k in combined for k in ["in - out", "in-out", "recibidos - cedidos", "recibido - cedido"] )
        if not net_definition_present:
            issues.append("La pregunta usa NETO; valida y explica que NETO = IN - OUT / recibidos - cedidos.")

    if any(k in question for k in ["monto", "mdp", "pesos", "importe"]):
        if any(k in text for k in ["cuentas", "numero de cuentas", "número de cuentas"]) and not any(k in text for k in ["monto", "mdp", "pesos", "importe"]):
            issues.append("La pregunta pide monto, pero la respuesta parece enfocarse en cuentas. No mezclar monto con cuentas.")

    if any(k in question for k in ["cuentas", "numero de cuentas", "número de cuentas", "traspasos"]):
        if any(k in text for k in ["monto", "mdp", "pesos", "importe"]) and not any(k in text for k in ["cuentas", "traspasos"]):
            issues.append("La pregunta pide cuentas/traspasos, pero la respuesta parece enfocarse en monto. No mezclar cuentas con monto.")

    if "mensual" in question and "acumulado" in text and "supuesto" not in text:
        issues.append("La pregunta parece mensual, pero la respuesta menciona acumulado sin explicar el supuesto.")

    if "acumulado" in question and "mensual" in text and "supuesto" not in text:
        issues.append("La pregunta parece acumulada, pero la respuesta menciona mensual sin explicar el supuesto.")

    if not text.strip() or "no devolvió una respuesta textual clara" in text:
        issues.append("Genie no devolvió una respuesta textual clara.")

    if any(k in question for k in ["por mes", "mensual", "ranking", "top", "compara", "comparativo", "participacion", "participación"]) and not has_table_result(result):
        issues.append("La pregunta normalmente requiere tabla para validar/graficar, pero Genie no devolvió resultado tabular.")

    return issues


def build_correction_prompt(user_prompt: str, previous_result: dict, issues: list[str], iteration: int) -> str:
    profuturo_codes = ", ".join(get_profuturo_codes())
    previous_text = previous_result.get("text", "")
    previous_sql = previous_result.get("sql", []) or []

    return f"""
Actúa como analista experto de traspasos AFORE. Estás en una iteración de revisión tipo ReAct.

Objetivo:
Corregir o confirmar la respuesta anterior antes de mostrarla al usuario final.

Pregunta original del usuario:
{user_prompt}

Respuesta anterior de Genie:
{previous_text}

SQL generado anteriormente:
{previous_sql}

Problemas detectados por el validador:
{issues}

Reglas obligatorias de negocio:
1. IN = traspasos recibidos.
2. OUT = traspasos cedidos / salientes.
3. NETO = IN - OUT.
4. Profuturo debe filtrarse con la clave del catálogo configurado: {profuturo_codes}.
5. No mezcles cuentas con monto.
6. No mezcles mensual con acumulado.
7. Si la pregunta es ambigua, declara el supuesto usado.
8. Usa las instrucciones, SQL Expressions, SQL Queries y benchmarks validados del Genie Space como referencia principal.
9. Si aplica, devuelve una tabla estructurada para que Streamlit pueda graficar.

Entrega una respuesta ejecutiva corregida:
- Resultado directo.
- Interpretación breve.
- Supuesto usado, si aplica.
- Tabla estructurada, si aplica.

Iteración de revisión: {iteration}
""".strip()


def ask_genie_with_react(
    host: str,
    token: str,
    space_id: str,
    user_prompt: str,
    deep_thinking: bool = True,
    show_sql: bool = False,
    max_iterations: int = 2
):
    """
    Orquesta el flujo:
    Pregunta -> Genie -> Validación -> Corrección controlada -> Respuesta final.

    Nota: cada iteración usa la misma conversación de Genie para conservar contexto.
    """
    first_prompt = build_genie_prompt(user_prompt=user_prompt, deep_thinking=deep_thinking)

    result = ask_genie(
        host=host,
        token=token,
        space_id=space_id,
        prompt=first_prompt,
        show_sql=show_sql
    )

    react_log = []

    if not deep_thinking or max_iterations <= 0:
        result["react_iterations"] = 0
        result["react_issues"] = []
        result["react_log"] = react_log
        return result

    for iteration in range(1, max_iterations + 1):
        issues = validate_genie_result(user_prompt, result)
        react_log.append({
            "iteration": iteration,
            "issues": issues,
            "had_table": has_table_result(result),
            "sql_count": len(result.get("sql", []) or [])
        })

        if not issues:
            result["react_iterations"] = iteration - 1
            result["react_issues"] = []
            result["react_log"] = react_log
            return result

        correction_prompt = build_correction_prompt(
            user_prompt=user_prompt,
            previous_result=result,
            issues=issues,
            iteration=iteration
        )

        result = ask_genie(
            host=host,
            token=token,
            space_id=space_id,
            prompt=correction_prompt,
            show_sql=show_sql
        )

    final_issues = validate_genie_result(user_prompt, result)
    result["react_iterations"] = max_iterations
    result["react_issues"] = final_issues
    result["react_log"] = react_log
    return result


# ------------------------------------------------------------
# RENDER DE RESPUESTAS COMPLETAS
# ------------------------------------------------------------

def render_feedback_controls(message_id: str):
    current_feedback = st.session_state.feedback.get(message_id)
    c1, c2, c3 = st.columns([1, 1, 6])
    with c1:
        if st.button("👍", key=f"thumbs_up_{message_id}", help="Marcar respuesta como correcta"):
            st.session_state.feedback[message_id] = "correcta"
            st.rerun()
    with c2:
        if st.button("👎", key=f"thumbs_down_{message_id}", help="Marcar respuesta como incorrecta"):
            st.session_state.feedback[message_id] = "incorrecta"
            st.rerun()
    with c3:
        if current_feedback:
            st.caption(f"Feedback registrado: **{current_feedback}**")


def render_assistant_artifacts(message: dict, message_index: int, show_charts: bool, show_sql: bool, show_debug: bool):
    message_id = message.get("id", f"msg_{message_index}")
    dataframes = message.get("dataframes", []) or []

    if dataframes:
        for df_idx, df in enumerate(dataframes, start=1):
            chart_key = f"{message_id}_{df_idx}"

            if show_charts:
                render_smart_visualization(df, chart_key=chart_key, user_prompt=message.get("user_prompt", ""), assistant_text=message.get("content", ""))

            with st.expander(f"Ver tabla de resultados {df_idx}", expanded=False):
                display_df = prepare_dataframe_for_display(df, hide_technical_codes=True)
                st.caption(f"{len(df):,} filas · {len(display_df.columns):,} columnas visibles")
                st.dataframe(display_df, use_container_width=True, hide_index=True)

                csv_original = df.to_csv(index=False).encode("utf-8")
                csv_display = display_df.to_csv(index=False).encode("utf-8")
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button(label=f"Descargar datos originales {df_idx}", data=csv_original, file_name=f"resultado_original_{message_id}_{df_idx}.csv", mime="text/csv", key=f"download_original_{message_id}_{df_idx}")
                with c2:
                    st.download_button(label=f"Descargar tabla formateada {df_idx}", data=csv_display, file_name=f"resultado_formateado_{message_id}_{df_idx}.csv", mime="text/csv", key=f"download_display_{message_id}_{df_idx}")

    if show_sql and message.get("sql"):
        with st.expander("SQL generado por Genie"):
            for sql_idx, sql in enumerate(message["sql"], start=1):
                st.code(sql, language="sql")

    if show_debug and message.get("raw"):
        with st.expander("Respuesta cruda de Genie"):
            st.json(message["raw"])

    if show_debug and message.get("react_log"):
        with st.expander("Validación ReAct"):
            st.json({
                "react_iterations": message.get("react_iterations", 0),
                "react_issues": message.get("react_issues", []),
                "react_log": message.get("react_log", [])
            })

    if message.get("role") == "assistant" and message_id != "welcome":
        render_feedback_controls(message_id)


def build_conversation_export() -> str:
    lines = ["# Conversación - Asistente de Traspasos AFORE", "", f"Fecha de exportación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]

    for idx, message in enumerate(st.session_state.messages, start=1):
        role = message.get("role", "unknown")
        content = message.get("content", "")

        if role == "user":
            lines.append(f"## Pregunta {idx}")
            lines.append(content)
            lines.append("")
        elif role == "assistant":
            lines.append(f"## Respuesta {idx}")
            lines.append(content)
            lines.append("")
            dataframes = message.get("dataframes", []) or []
            if dataframes:
                lines.append("### Tablas devueltas")
                for df_idx, df in enumerate(dataframes, start=1):
                    lines.append(f"- Tabla {df_idx}: {len(df):,} filas · {len(df.columns):,} columnas originales")
                lines.append("")
            sql_queries = message.get("sql", []) or []
            if sql_queries:
                lines.append("### SQL generado")
                for sql in sql_queries:
                    lines.append(f"```sql\n{sql}\n```")
                lines.append("")
            feedback_value = st.session_state.feedback.get(message.get("id"))
            if feedback_value:
                lines.append(f"Feedback: {feedback_value}")
                lines.append("")

    return "\n".join(lines)


# ------------------------------------------------------------
# INTERFAZ
# ------------------------------------------------------------

inject_profuturo_theme()
init_session_state()
databricks_config = load_databricks_config()

with st.sidebar:
    st.markdown("### Centro de control")
    st.caption("Configura cómo quieres consultar y visualizar la información.")

    deep_thinking = st.toggle(
        "Deep thinking",
        value=True,
        help="No activa el Agent Mode real de Genie, pero guía a Genie para apoyarse en instrucciones, SQL Expressions y SQL Queries validadas."
    )
    st.caption("Modo actual: análisis más detallado y contextual." if deep_thinking else "Modo actual: respuesta rápida y directa.")

    max_react_iterations = st.slider(
        "Iteraciones ReAct",
        min_value=0,
        max_value=3,
        value=2,
        help="Número máximo de revisiones automáticas antes de mostrar la respuesta. Recomendado: 1 o 2."
    )

    show_charts = st.toggle(
        "Mostrar visualizaciones automáticas",
        value=True,
        help="Genera gráficos automáticamente cuando Genie devuelve resultados tabulares."
    )

    st.divider()

    show_sql = st.toggle("Mostrar SQL generado", value=False, help="Útil para validación técnica contra Power BI o consultas manuales.")
    show_debug = st.toggle("Mostrar respuesta cruda", value=False, help="Solo para pruebas técnicas.")

    st.divider()
    st.markdown("### Preguntas sugeridas")

    suggested_questions = [
        "¿Cuántos traspasos recibió Profuturo en 2025 por mes?",
        "¿Qué AFORE recibió más traspasos durante 2025?",
        "¿Cuáles fueron las principales AFORE origen hacia Profuturo en 2025?",
        "¿Cuál fue la participación de Profuturo en los traspasos recibidos de 2025?",
        "Compara los traspasos de Profuturo entre 2024 y 2025."
    ]

    for i, question in enumerate(suggested_questions, start=1):
        if st.button(question, key=f"suggested_question_{i}"):
            st.session_state.pending_prompt = question
            st.rerun()

    st.divider()

    export_text = build_conversation_export()
    st.download_button(label="Descargar conversación", data=export_text.encode("utf-8"), file_name="conversacion_traspasos_afore.md", mime="text/markdown", use_container_width=True)

    if st.button("Nueva conversación", use_container_width=True):
        reset_chat()
        st.rerun()

    st.caption("La conexión con Databricks Genie está configurada por detrás mediante secrets.")

render_profuturo_header()


# ------------------------------------------------------------
# MENSAJE INICIAL
# ------------------------------------------------------------

if len(st.session_state.messages) == 0:
    st.session_state.messages.append({
        "id": "welcome",
        "role": "assistant",
        "content": (
            "Hola. Soy el asistente conversacional de análisis de **traspasos AFORE** de Profuturo.\n\n"
            "Puedo ayudarte a consultar información sobre traspasos recibidos, traspasos cedidos, "
            "participación, comparativos mensuales, comportamiento por AFORE, origen/destino y "
            "tendencias del mercado.\n\n"
            "Cuando la respuesta incluya datos estructurados, generaré tablas y visualizaciones "
            "automáticas para facilitar el análisis."
        ),
        "dataframes": [],
        "sql": [],
        "raw": {},
        "created_at": datetime.now().isoformat()
    })


# ------------------------------------------------------------
# HISTORIAL DE CHAT
# ------------------------------------------------------------

for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_assistant_artifacts(message=message, message_index=idx, show_charts=show_charts, show_sql=show_sql, show_debug=show_debug)


# ------------------------------------------------------------
# INPUT DEL USUARIO
# ------------------------------------------------------------

typed_prompt = st.chat_input("Pregunta algo sobre traspasos...")
prompt = typed_prompt

if st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if prompt:
    user_message = {"id": str(uuid.uuid4()), "role": "user", "content": prompt, "created_at": datetime.now().isoformat()}
    st.session_state.messages.append(user_message)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            spinner_text = "Consultando Genie con validación ReAct..." if deep_thinking else "Consultando Genie..."

            with st.spinner(spinner_text):
                result = ask_genie_with_react(
                    host=databricks_config["host"],
                    token=databricks_config["token"],
                    space_id=databricks_config["space_id"],
                    user_prompt=prompt,
                    deep_thinking=deep_thinking,
                    show_sql=show_sql,
                    max_iterations=max_react_iterations if deep_thinking else 0
                )

            assistant_text = clean_markdown_artifacts(prettify_afore_text(result["text"]))
            enriched_dataframes = [enrich_afore_columns(df) for df in result.get("dataframes", [])]

            assistant_message = {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": assistant_text,
                "user_prompt": prompt,
                "dataframes": enriched_dataframes,
                "sql": result.get("sql", []),
                "raw": result.get("raw", {}),
                "deep_thinking": deep_thinking,
                "react_iterations": result.get("react_iterations", 0),
                "react_issues": result.get("react_issues", []),
                "react_log": result.get("react_log", []),
                "created_at": datetime.now().isoformat()
            }

            st.markdown(assistant_text)
            render_assistant_artifacts(message=assistant_message, message_index=len(st.session_state.messages), show_charts=show_charts, show_sql=show_sql, show_debug=show_debug)
            st.session_state.messages.append(assistant_message)

        except Exception as e:
            error_text = str(e)
            if "PENDING_WAREHOUSE" in error_text:
                error_message = (
                    "La pregunta sí llegó a Genie, pero el SQL Warehouse no quedó listo a tiempo. "
                    "Revisa que el warehouse asignado al Genie Space esté encendido y disponible.\n\n"
                    f"Detalle técnico: `{e}`"
                )
            elif "PERMISSION" in error_text.upper() or "FORBIDDEN" in error_text.upper():
                error_message = (
                    "No pude completar la consulta porque parece haber un problema de permisos. "
                    "Revisa el acceso al Genie Space, SQL Warehouse o tablas utilizadas.\n\n"
                    f"Detalle técnico: `{e}`"
                )
            elif "TIMEOUT" in error_text.upper() or "TIMED OUT" in error_text.upper():
                error_message = (
                    "La consulta tardó más de lo esperado. Intenta reformular la pregunta o validar "
                    "que el SQL Warehouse esté disponible.\n\n"
                    f"Detalle técnico: `{e}`"
                )
            else:
                error_message = (
                    "No pude completar la consulta con Genie. "
                    "Revisa permisos del Genie Space, acceso al SQL Warehouse o disponibilidad de Databricks.\n\n"
                    f"Detalle técnico: `{e}`"
                )

            st.error(error_message)
            st.session_state.messages.append({
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": error_message,
                "user_prompt": prompt,
                "dataframes": [],
                "sql": [],
                "raw": {},
                "deep_thinking": deep_thinking,
                "created_at": datetime.now().isoformat()
            })
